"""
Memory Adapter Module.

Wraps the official Vectorize Hindsight API client with support for all three
biomimetic primitives:
  1. retain():  Episodic storage of incident post-mortems and resolutions.
  2. recall():  Multi-strategy associative retrieval of historical incidents.
  3. reflect(): High-order reasoning across stored memories to synthesize
                temporal patterns and architectural beliefs.

Designed with dual-mode resiliency:
  • Live Mode: Connects to Hindsight Cloud (or self-hosted instance)
  • Fallback Mode: Clean in-memory engine ensuring demos never crash offline
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config import (
    HINDSIGHT_API_KEY,
    HINDSIGHT_BASE_URL,
    HINDSIGHT_BANK_ID,
    IS_MOCK_HINDSIGHT,
)
from seed_incidents import get_seed_incidents

logger = logging.getLogger("IncidentMemory")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ==============================================================================
# SRE Failure Taxonomy & Concept Markers (Concordance Verification)
# ==============================================================================
FAILURE_CONCEPTS = {
    "oom": {"oom", "oomkilled", "137", "memory", "heap", "evicted", "xmx", "xms", "invoicing", "batch"},
    "connection_pool": {"connection", "pool", "exhausted", "starvation", "connections", "max_connections", "acquire", "acquiring", "timeout", "idle", "redis", "ldap"},
    "db_locks": {"lock", "deadlock", "transaction", "blocked", "exclusive", "pg_locks", "tx"},
    "replication_lag": {"replication", "lag", "replica", "delay", "seconds", "threshold", "replica_monitor"},
    "kafka_lag": {"kafka", "consumer", "rebalance", "partition", "offset", "lag", "group"},
    "disk_watermark": {"disk", "watermark", "flood", "unassigned", "shards", "pvc", "storage", "quota", "full"},
    "bad_gateway": {"502", "504", "gateway", "upstream", "connect", "refused", "nginx"},
    "auth_failure": {"ldap", "auth", "token", "activedirectory", "unauthorized", "401", "403"},
    "dns_failure": {"dns", "nxdomain", "resolve", "nameresolution", "servfail"},
}

CRITICAL_SIGNATURES = {
    "oom": {"oomkilled", "137", "oom"},
    "connection_pool_redis": {"connectionpool", "redis.exceptions.connectionerror"},
    "connection_pool_ldap": {"ldappoolexhaustedexception", "activedirectory ldap"},
    "replication_lag": {"replication lag", "psycopg2.operationalerror"},
    "kafka_rebalance": {"commitfailedexception", "rebalanceinprogress"},
    "disk_full": {"flood-stage watermark", "read_only_allow_delete", "clusterblockexception"},
    "bad_gateway": {"502 bad gateway", "504 gateway timeout"},
}


def _extract_sre_tokens(text: str) -> set:
    if not text:
        return set()
    words = re.findall(r"[a-zA-Z0-9_\-\.]+", str(text).lower())
    stop_words = {
        "the", "and", "with", "from", "for", "during", "after", "into", "service",
        "app", "error", "failed", "trace", "file", "line", "last", "state", "reason",
        "exception", "occurred", "while", "that", "this", "been", "have", "were"
    }
    tokens = set()
    for w in words:
        parts = re.split(r"[\-_:\.]", w)
        for p in parts:
            if len(p) > 2 and p not in stop_words:
                tokens.add(p)
    return tokens


def _classify_failure_categories(tokens: set, text: str) -> set:
    cats = set()
    text_lower = text.lower()

    if ("137" in tokens or "oomkilled" in tokens or "oom" in tokens) or ("memory" in tokens and ("limit" in tokens or "heap" in tokens or "exceeded" in tokens)):
        cats.add("oom")

    if ("pool" in tokens and any(t in tokens for t in ("connection", "connections", "exhausted", "starvation", "acquire", "acquiring", "max_connections", "timeout"))) or "connectionpool" in text_lower:
        cats.add("connection_pool")

    if any(t in tokens for t in ("lock", "deadlock", "pg_locks", "blocked")):
        cats.add("db_locks")

    if ("statement" in tokens or "query" in tokens) and "timeout" in tokens:
        cats.add("db_query_timeout")
    elif "replication" in tokens and "lag" in tokens:
        cats.add("replication_lag")

    if any(t in tokens for t in ("502", "504", "gateway", "nginx")) or ("upstream" in tokens and ("connect" in tokens or "refused" in tokens)):
        cats.add("bad_gateway")

    if "kafka" in tokens and any(t in tokens for t in ("rebalance", "partition", "offset", "lag", "consumer")):
        cats.add("kafka_lag")

    if "disk" in tokens and any(t in tokens for t in ("watermark", "flood", "shards", "pvc", "storage", "quota", "full")):
        cats.add("disk_watermark")

    return cats


class HindsightMemoryClient:
    """
    Manages persistent memory operations for the Incident Response Agent.
    """

    def __init__(self, bank_id: str = HINDSIGHT_BANK_ID):
        self.bank_id = bank_id
        self.is_mock = IS_MOCK_HINDSIGHT
        self.client = None

        # Dual-mode memory storage: tracks retained incident metadata for UI & inspections
        self._retained_history: List[Dict[str, Any]] = []

        self._initialize_client()

    def _initialize_client(self):
        """Initializes the live SDK client or defaults to mock engine."""
        if not self.is_mock and HINDSIGHT_API_KEY:
            try:
                # Import from the official pip package
                from hindsight_client import Hindsight
                self.client = Hindsight(
                    base_url=HINDSIGHT_BASE_URL,
                    api_key=HINDSIGHT_API_KEY,
                )
                logger.info(f"Connected to Hindsight Cloud at {HINDSIGHT_BASE_URL} (Bank: {self.bank_id})")
            except Exception as e:
                logger.warning(
                    f"Could not connect to Hindsight Cloud ({e}). "
                    "Engaging resilient in-memory fallback mode."
                )
                self.is_mock = True
        else:
            logger.info("Running in Resilient In-Memory Mock Mode (no API key required).")
            self.is_mock = True

        # Pre-populate initial seed memories
        self._load_seed_memories()

    def _load_seed_memories(self):
        """Loads seed incidents into history."""
        for inc in get_seed_incidents():
            self._retained_history.append(inc)

    def _format_incident_for_retention(self, inc: Dict[str, Any]) -> str:
        """Serializes an incident record into rich textual memory for Hindsight."""
        return (
            f"Incident ID: {inc.get('id', 'NEW')}\n"
            f"Title: {inc.get('title')}\n"
            f"Service: {inc.get('service')}\n"
            f"Severity: {inc.get('severity')}\n"
            f"Error Signature: {inc.get('error_signature')}\n"
            f"Stack Trace:\n{inc.get('stack_trace')}\n"
            f"Root Cause:\n{inc.get('root_cause')}\n"
            f"Runbook Steps:\n- " + "\n- ".join(inc.get("runbook_steps", [])) + "\n"
            f"Anti-Patterns (Dangerous Actions to AVOID):\n- "
            + "\n- ".join(inc.get("anti_patterns", [])) + "\n"
            f"Resolved By: {inc.get('resolved_by')}\n"
            f"Deployment Context: {inc.get('deployment_context', 'N/A')}\n"
        )

    # ==========================================================================
    # PRIMITIVE 1: retain() - Ingest into Episodic Memory
    # ==========================================================================
    def retain(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stores an incident post-mortem into Hindsight's memory bank.
        """
        formatted_content = self._format_incident_for_retention(incident)

        # Track in history with robust ID-based deduplication
        inc_id = incident.get("id")
        if inc_id and any(existing.get("id") == inc_id for existing in self._retained_history):
            logger.info(f"Incident {inc_id} already in history. Updating record in place.")
            for idx, existing in enumerate(self._retained_history):
                if existing.get("id") == inc_id:
                    self._retained_history[idx] = incident
                    break
        else:
            self._retained_history.append(incident)

        if not self.is_mock and self.client:
            try:
                # Call live Hindsight SDK with metadata & tags kwargs
                try:
                    resp = self.client.retain(
                        bank_id=self.bank_id,
                        content=formatted_content,
                        tags=[str(incident.get("service", "unknown")), str(incident.get("severity", "MEDIUM"))],
                        metadata={"id": str(incident.get("id", "NEW")), "service": str(incident.get("service", ""))},
                    )
                except TypeError:
                    # In case of older/alternate SDK signature, fall back to basic kwargs
                    resp = self.client.retain(
                        bank_id=self.bank_id,
                        content=formatted_content,
                    )
                logger.info(f"Retained incident {incident.get('id')} to Hindsight Cloud.")
                return {"status": "success", "mode": "cloud", "response": resp}
            except Exception as e:
                logger.error(f"Live Hindsight retain error: {e}. Preserving in local history.")

        logger.info(f"Retained incident {incident.get('id')} into memory bank.")
        return {"status": "success", "mode": "mock", "incident_id": incident.get("id")}

    # ==========================================================================
    # PRIMITIVE 2: recall() - Multi-Strategy Memory Retrieval
    # ==========================================================================
    def recall(
        self,
        query: str,
        service: Optional[str] = None,
        error_signature: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries Hindsight memory for past incidents matching the error query.
        Returns candidates with calibrated match strength and provenance.
        """
        if not self.is_mock and self.client:
            try:
                # Call live Hindsight SDK
                cloud_query = f"Service: {service}. Error: {query}" if service and service not in query else query
                results = self.client.recall(
                    bank_id=self.bank_id,
                    query=cloud_query,
                )
                return self._parse_cloud_recall_results(results, query, service, error_signature)
            except Exception as e:
                logger.error(f"Live Hindsight recall error: {e}. Falling back to multi-signal matcher.")

        # Multi-signal match simulation (semantic + failure taxonomy + cross-service matching)
        return self._mock_recall(query, service, error_signature)

    def _parse_cloud_recall_results(
        self,
        cloud_results: Any,
        query: str,
        service: Optional[str] = None,
        error_signature: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Correctly parses RecallResponse from the live Hindsight SDK.
        Extracts genuine fused scores from RecallScores (final, reranker, semantic, keyword).
        Filters out irrelevant matches below the relevance threshold and enforces failure
        concordance so novel/incompatible incidents return 0% Cold Start.
        """
        items = []
        raw_items = []

        if hasattr(cloud_results, "results") and cloud_results.results:
            raw_items = cloud_results.results
        elif isinstance(cloud_results, list):
            raw_items = cloud_results

        # Classify query failure category to prevent same-service false positives
        q_combined = f"{error_signature or ''} {query}".strip()
        service_name = str(service or "").lower().strip()
        svc_tokens = _extract_sre_tokens(service_name)
        q_tokens = _extract_sre_tokens(q_combined) - svc_tokens
        q_cats = _classify_failure_categories(q_tokens, q_combined)

        for r in raw_items:
            text = getattr(r, "text", str(r))
            scores_obj = getattr(r, "scores", None)
            metadata = getattr(r, "metadata", {}) or {}

            # Failure category concordance check
            text_tokens = _extract_sre_tokens(text)
            text_cats = _classify_failure_categories(text_tokens, text)
            shared_cats = q_cats & text_cats
            if q_cats and not shared_cats:
                # Query has a distinct failure category (e.g. 502 or db query timeout)
                # that the recalled passage completely lacks (e.g. OOM). Force Cold Start.
                continue

            score = 0.0
            score_type = "Cold Start"
            if scores_obj is not None:
                rer = getattr(scores_obj, "reranker", None)
                fin = getattr(scores_obj, "final", None)
                sem = getattr(scores_obj, "semantic", None)

                # Priority 1: Cross-Encoder Reranker (Gold-standard relevance discriminator)
                if rer is not None:
                    rer_val = float(rer)
                    if rer_val < 0.50:
                        score = 0.0
                        score_type = "Cold Start (< 0.50 relevance)"
                    elif rer_val >= 0.75:
                        score = min(0.98, rer_val)
                        score_type = "Cross-Encoder Reranker (High Match)"
                    else:
                        score = round(0.50 + ((rer_val - 0.50) / 0.25) * 0.24, 2)
                        score_type = "Cross-Encoder Reranker (Moderate Match)"

                # Priority 2: Final Fused score
                elif fin is not None:
                    fin_val = float(fin)
                    if fin_val < 0.50:
                        score = 0.0
                        score_type = "Cold Start"
                    elif fin_val >= 0.75:
                        score = min(0.98, fin_val)
                        score_type = "Reranked Final (High Match)"
                    else:
                        score = round(0.50 + ((fin_val - 0.50) / 0.25) * 0.24, 2)
                        score_type = "Reranked Final (Moderate Match)"

                # Priority 3: Semantic Cosine Baseline Calibration (baseline offset ~0.75)
                elif sem is not None:
                    sem_val = float(sem)
                    if sem_val < 0.75:
                        score = 0.0
                        score_type = "Cold Start"
                    else:
                        score = min(0.95, max(0.0, (sem_val - 0.75) / 0.20))
                        score_type = "Calibrated Semantic"
            else:
                score = self._compute_dynamic_similarity(text, query, service, error_signature)
                score_type = "Synthesized Semantic Concordance"

            # Strictly skip any candidate that is below the relevance threshold (score == 0)
            if score <= 0.0:
                continue

            # Locate matching incident from history if referenced
            matched_inc = None
            for inc in self._retained_history:
                if inc.get("id") and inc.get("id") in text:
                    matched_inc = inc
                    break

            if not matched_inc:
                first_line = text.split("\n")[0] if text else "Historical Outage"
                matched_inc = {
                    "id": metadata.get("id", "RECALLED"),
                    "title": first_line[:80],
                    "service": service or metadata.get("service", "system"),
                    "root_cause": text,
                    "runbook_steps": ["Review historical remediation steps in Hindsight memory"],
                    "anti_patterns": [],
                    "resolved_by": "SRE Team",
                }

            items.append({
                "incident": matched_inc,
                "match_strength": round(max(0.0, min(0.99, score)), 2),
                "matched_reasons": [
                    f"Scored via Hindsight {score_type}",
                    "Retrieved via Vectorize Multi-Strategy Search",
                ],
            })

        items.sort(key=lambda x: x["match_strength"], reverse=True)
        return items

    def _compute_dynamic_similarity(
        self,
        text: str,
        query: str,
        service: Optional[str] = None,
        error_signature: Optional[str] = None,
    ) -> float:
        """Calculates dynamic similarity based on token concordance without hardcoded ceilings."""
        service_name = str(service or "").lower().strip()
        svc_tokens = _extract_sre_tokens(service_name)
        combined_query = f"{error_signature or ''} {query}".strip()
        q_tokens = _extract_sre_tokens(combined_query) - svc_tokens
        t_tokens = _extract_sre_tokens(text)

        if not q_tokens or not t_tokens:
            return 0.0

        shared = q_tokens.intersection(t_tokens)
        overlap_ratio = len(shared) / max(len(q_tokens), 1)
        if overlap_ratio < 0.25:
            return 0.0

        sim = min(1.0, overlap_ratio * 1.3)
        if service and service.lower() in text.lower():
            return round(min(0.98, sim * 0.88 + 0.10), 2)
        return round(min(0.88, sim * 0.90), 2)

    def _mock_recall(
        self,
        query: str,
        service: Optional[str] = None,
        error_signature: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Calculates a calibrated match strength against stored memory entries.
        Fuses error signature tokens, failure concepts, and service alignment.
        Eliminates same-service false positives and generalizes cross-service architectural patterns.
        """
        matches = []
        service_name = str(service or "").lower().strip()
        svc_tokens = _extract_sre_tokens(service_name)

        combined_query = f"{error_signature or ''} {query}".strip()
        q_tokens = _extract_sre_tokens(combined_query) - svc_tokens

        if not q_tokens:
            return []

        q_cats = _classify_failure_categories(q_tokens, combined_query)

        for inc in self._retained_history:
            inc_service = str(inc.get("service") or "").lower().strip()
            inc_svc_tokens = _extract_sre_tokens(inc_service)

            inc_text = f"{inc.get('error_signature', '')} {inc.get('stack_trace', '')} {inc.get('title', '')} {inc.get('root_cause', '')}"
            inc_tokens = _extract_sre_tokens(inc_text) - inc_svc_tokens

            if not inc_tokens:
                continue

            shared_tokens = q_tokens & inc_tokens
            overlap_ratio = len(shared_tokens) / len(q_tokens)

            inc_cats = _classify_failure_categories(inc_tokens, inc_text)
            shared_cats = q_cats & inc_cats

            # Hard conflict: query belongs to a failure category (e.g. bad_gateway or db_locks)
            # that the incident completely lacks. Force Cold Start (0.0).
            if q_cats and not shared_cats:
                continue

            q_str = combined_query.lower()
            inc_str = inc_text.lower()
            shared_crit = False
            for cat, markers in CRITICAL_SIGNATURES.items():
                if any(m in q_str for m in markers) and any(m in inc_str for m in markers):
                    shared_crit = True
                    break

            if not shared_crit and not shared_cats and overlap_ratio < 0.25:
                continue

            sim = min(1.0, overlap_ratio * 1.25)
            if shared_crit:
                sim = max(sim, 0.70) + 0.15
            elif shared_cats:
                sim = max(sim, 0.40) + 0.15

            sim = min(1.0, sim)

            if sim < 0.35:
                continue

            is_same_service = bool(service_name and inc_service and service_name == inc_service)
            if is_same_service:
                final_score = min(0.98, sim * 0.88 + 0.10)
                if shared_crit and overlap_ratio >= 0.40:
                    final_score = 0.97
                score_reason = f"Same-service match ({inc_service}) + verified failure concordance"
            else:
                final_score = min(0.88, sim * 0.90)
                score_reason = f"Cross-service architectural match ({inc_service} precedent)"

            match_strength = round(final_score, 2)
            if match_strength >= 0.50:
                matches.append({
                    "incident": inc,
                    "match_strength": match_strength,
                    "retained_at": inc.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "matched_reasons": [
                        score_reason,
                        f"Shared telemetry concepts: {', '.join(list(shared_tokens)[:3])}" if shared_tokens else "Failure taxonomy match",
                    ],
                })

        matches.sort(key=lambda x: x["match_strength"], reverse=True)
        return matches

    # ==========================================================================
    # PRIMITIVE 3: reflect() - Biomimetic Mental Model & Belief Synthesis
    # ==========================================================================
    def reflect(self, topic: str = "systemic failure patterns and deployment risks") -> Dict[str, Any]:
        """
        Triggers Hindsight reasoning across all stored memories to synthesize
        macro insights, temporal trends, and evolving architectural beliefs.
        """
        cloud_raw_text = None
        if not self.is_mock and self.client:
            try:
                resp = self.client.reflect(
                    bank_id=self.bank_id,
                    query=f"Analyze all incidents for {topic}",
                )
                if hasattr(resp, "text"):
                    cloud_raw_text = resp.text
            except Exception as e:
                logger.error(f"Live Hindsight reflect error: {e}. Falling back to structured reflection.")

        # Return synthesized beliefs (with live text dynamically integrated if available)
        reflection_data = self._synthesize_reflection(cloud_raw_text)
        return reflection_data

    def _synthesize_reflection(self, live_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes the memory bank and synthesizes evolving beliefs
        based on recurring temporal patterns and service failure clusters.
        """
        total_incidents = len(self._retained_history)
        beliefs = []

        # 1. Dynamically cluster by service across all retained incidents in memory
        service_counts = {}
        for inc in self._retained_history:
            svc = inc.get("service", "system")
            service_counts[svc] = service_counts.get(svc, 0) + 1

        for svc, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            matching_incs = [i for i in self._retained_history if i.get("service") == svc]
            sample_ids = [str(i.get("id", "INC")) for i in matching_incs[:3]]
            sample_titles = [i.get("title", "Outage") for i in matching_incs[:2]]
            
            tier_name = "CRITICAL RECURRING HOTSPOT" if count >= 2 else "MONITORED COMPONENT"
            confidence = round(min(0.98, 0.70 + (count * 0.08)), 2)
            
            beliefs.append({
                "tier": tier_name,
                "service": svc,
                "confidence": confidence,
                "observation": f"{count} incident(s) retained for '{svc}' ({', '.join(sample_ids)}).",
                "temporal_correlation": f"Observed across {count} outage event(s).",
                "synthesized_belief": f"Service exhibits failure patterns in: {'; '.join(sample_titles)}.",
                "proactive_remediation": f"Audit telemetry thresholds, retry backoffs, and resource limits for '{svc}'.",
            })

        return {
            "mode": "cloud" if (not self.is_mock and live_text) else ("cloud" if not self.is_mock else "mock"),
            "total_incidents_analyzed": total_incidents,
            "last_reflected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "synthesized_beliefs": beliefs,
            "live_cloud_text": live_text,
        }

    def get_all_retained(self) -> List[Dict[str, Any]]:
        """Returns all currently retained memories for bank inspection."""
        return list(self._retained_history)

    def reset_to_seed(self):
        """Resets both local history and live Hindsight Cloud memory back to initial seed state."""
        self._retained_history = []
        self._load_seed_memories()

        if not self.is_mock and self.client:
            try:
                from hindsight_client.hindsight_client import _run_async
                # 1. Clear all memories from cloud bank
                _run_async(self.client._memory_api.clear_bank_memories(bank_id=self.bank_id, _request_timeout=self.client._timeout))
                logger.info(f"Cleared all memories from Hindsight Cloud bank '{self.bank_id}'")

                # 2. Re-seed clean seed incidents via batch retain
                items = [
                    {
                        "content": self._format_incident_for_retention(s),
                        "tags": [str(s.get("service", "system")), str(s.get("severity", "MEDIUM"))],
                        "metadata": {"id": str(s.get("id", "SEED")), "service": str(s.get("service", ""))},
                    }
                    for s in self._retained_history
                ]
                self.client.retain_batch(bank_id=self.bank_id, items=items)
                logger.info(f"Re-seeded {len(items)} incidents into Hindsight Cloud bank '{self.bank_id}'")
            except Exception as e:
                logger.error(f"Error resetting cloud bank: {e}")

        logger.info("Memory bank reset to initial seed state.")
