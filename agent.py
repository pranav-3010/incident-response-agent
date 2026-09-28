"""
Incident Response Agent Engine.

Coordinates the reasoning loop between:
  1. Incoming alerts & error stack traces
  2. Hindsight Memory Client (retain, recall, reflect)
  3. Diagnostic Reasoning (Groq LLM / SRE Diagnostic Template)

Calculates calibrated match strength, generates proven runbooks,
surfaces critical anti-pattern warnings, and provides verifiable citations.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config import GROQ_API_KEY, GROQ_MODEL, IS_MOCK_GROQ
from memory_adapter import HindsightMemoryClient

logger = logging.getLogger("IncidentAgent")


class IncidentResponseAgent:
    """
    Autonomous Incident Response & SRE Copilot powered by Hindsight Memory.
    """

    def __init__(self, memory_client: Optional[HindsightMemoryClient] = None):
        self.memory = memory_client or HindsightMemoryClient()
        self.groq_client = None
        self._init_groq()

    def _init_groq(self):
        """Initializes Groq client if an API key is provided."""
        if not IS_MOCK_GROQ and GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
                logger.info(f"Groq Diagnostic Engine initialized with {GROQ_MODEL}")
            except Exception as e:
                logger.warning(f"Could not initialize Groq ({e}). Using built-in diagnostic engine.")
                self.groq_client = None
        else:
            logger.info("Using Built-in SRE Diagnostic Reasoning Engine (no Groq key needed).")

    def triage_alert(self, alert: Dict[str, Any], exclude_incident_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Main entry point: Triages an incoming alert by querying Hindsight memory
        and producing a confidence-scored diagnostic report with runbook and warnings.
        """
        service = str(alert.get("service") or alert.get("component") or "unknown-service").strip()
        error_sig = str(alert.get("error_signature") or alert.get("error_message") or alert.get("error") or "").strip()
        stack_trace = str(alert.get("stack_trace") or alert.get("stack") or alert.get("logs") or "").strip()
        timestamp = str(alert.get("timestamp") or datetime.now(timezone.utc).isoformat())

        normalized_alert = {
            **alert,
            "service": service,
            "error_signature": error_sig,
            "stack_trace": stack_trace,
            "timestamp": timestamp,
        }

        # Construct clean diagnostic query for Hindsight recall()
        diagnostic_query = f"{error_sig} {stack_trace[:150]}".strip()
        if not diagnostic_query:
            diagnostic_query = service

        # ======================================================================
        # Step 1: Query Hindsight Associative Memory (recall)
        # ======================================================================
        recall_candidates = self.memory.recall(query=diagnostic_query, service=service, error_signature=error_sig)
        if exclude_incident_ids:
            recall_candidates = [
                c for c in recall_candidates
                if c.get("incident", {}).get("id") not in exclude_incident_ids
            ]

        top_match = recall_candidates[0] if recall_candidates else None
        match_strength = top_match["match_strength"] if top_match else 0.0

        # ======================================================================
        # Step 2: Determine Match Tier & Enforce 0% Cold-Start Guarantee
        # ======================================================================
        if match_strength >= 0.75:
            tier = "HIGH_CONFIDENCE_MATCH"
            tier_label = "🟢 High Match (Historical Runbook Found)"
        elif match_strength >= 0.50:
            tier = "MODERATE_MATCH"
            tier_label = "🟡 Moderate Match (Partial Architectural Overlap)"
        else:
            tier = "COLD_START"
            tier_label = "⚪ Cold Start (Novel Incident - First-Principles Triage)"
            match_strength = 0.0
            top_match = None

        # If live Groq client is active, use Groq to dynamically synthesize the diagnosis
        if self.groq_client and not IS_MOCK_GROQ:
            try:
                return self._call_groq_diagnosis(
                    alert=normalized_alert,
                    tier=tier,
                    tier_label=tier_label,
                    match_strength=match_strength,
                    matched_candidate=top_match,
                )
            except Exception as e:
                logger.warning(f"Groq API call failed ({e}). Falling back to built-in synthesis.")

        # Built-in Fallback Synthesis (Used when offline or no API key provided)
        return self._synthesize_fallback_diagnosis(
            alert=normalized_alert,
            tier=tier,
            tier_label=tier_label,
            match_strength=match_strength,
            matched_candidate=top_match,
        )

    def _call_groq_diagnosis(
        self,
        alert: Dict[str, Any],
        tier: str,
        tier_label: str,
        match_strength: float,
        matched_candidate: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Uses Groq LLM (e.g. Llama 3.3 70B / Qwen) to generate dynamic SRE triage
        reasoning grounded directly in Hindsight memory evidence.
        """
        service = alert.get("service", "unknown-service")
        error_sig = alert.get("error_signature", "")
        stack_trace = alert.get("stack_trace", "")
        pct_label = round(match_strength * 100)

        system_prompt = (
            "You are an elite Site Reliability Engineer (SRE) Copilot. "
            "You diagnose production outages using persistent memory from Hindsight. "
            "Analyze the incoming telemetry alert and the historical memory candidates retrieved from Hindsight. "
            "Output your answer in clean JSON with keys: "
            "'summary', 'suspected_root_cause', 'runbook_steps' (list), and 'anti_patterns' (list)."
        )

        if tier == "COLD_START" or not matched_candidate:
            user_prompt = (
                f"INCOMING OUTAGE ALERT:\nService: {service}\nError: {error_sig}\nStack:\n{stack_trace}\n\n"
                "HINDSIGHT MEMORY RESULT: 0% Match. No historical precedents found.\n"
                "Provide a transparent first-principles SRE triage checklist and safe inspection steps without guessing."
            )
        elif tier == "MODERATE_MATCH":
            matched_inc = matched_candidate["incident"]
            user_prompt = (
                f"INCOMING OUTAGE ALERT:\nService: {service}\nError: {error_sig}\nStack:\n{stack_trace}\n\n"
                f"HINDSIGHT RECALLED MEMORY ({pct_label}% Moderate Match - Partial Architectural Precedent):\n"
                f"Matched Incident: {matched_inc.get('id')} - {matched_inc.get('title')}\n"
                f"Historical Root Cause: {matched_inc.get('root_cause')}\n"
                f"Historical Runbook Steps:\n- " + "\n- ".join(matched_inc.get("runbook_steps", [])) + "\n"
                f"Historical Anti-Patterns:\n- " + "\n- ".join(matched_inc.get("anti_patterns", [])) + "\n\n"
                "CAUTION: This is a MODERATE match representing partial architectural or symptom similarity. "
                "The current failure mode may differ fundamentally from this historical incident. "
                "Do NOT assume identical root cause or prescribe the historical runbook blindly. "
                "Synthesize a cautious, exploratory triage plan that evaluates whether this precedent applies, "
                "points out critical differences, and prescribes safe non-destructive diagnostic commands to confirm the root cause."
            )
        else:
            matched_inc = matched_candidate["incident"]
            user_prompt = (
                f"INCOMING OUTAGE ALERT:\nService: {service}\nError: {error_sig}\nStack:\n{stack_trace}\n\n"
                f"HINDSIGHT RECALLED MEMORY ({pct_label}% High Confidence Match):\n"
                f"Matched Incident: {matched_inc.get('id')} - {matched_inc.get('title')}\n"
                f"Historical Root Cause: {matched_inc.get('root_cause')}\n"
                f"Historical Runbook Steps:\n- " + "\n- ".join(matched_inc.get("runbook_steps", [])) + "\n"
                f"Historical Anti-Patterns:\n- " + "\n- ".join(matched_inc.get("anti_patterns", [])) + "\n\n"
                "Synthesize a targeted, authoritative remediation plan citing this historical evidence."
            )

        chat_completion = self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = json.loads(chat_completion.choices[0].message.content)

        top_match_info = None
        citations = []
        hindsight_evidence = None
        if tier != "COLD_START" and matched_candidate:
            matched_inc = matched_candidate["incident"]
            top_match_info = {
                "incident_id": matched_inc.get("id"),
                "title": matched_inc.get("title"),
                "service": matched_inc.get("service"),
                "match_strength": match_strength,
                "incident": matched_inc,
            }
            citations.append({
                "source_id": matched_inc.get("id"),
                "title": matched_inc.get("title"),
                "service": matched_inc.get("service"),
                "resolved_by": matched_inc.get("resolved_by") or "SRE On-Call Team",
                "timestamp": matched_inc.get("timestamp"),
                "deployment_context": matched_inc.get("deployment_context"),
                "root_cause": matched_inc.get("root_cause"),
                "error_signature": matched_inc.get("error_signature"),
            })
            hindsight_evidence = {
                "matched_reasons": matched_candidate.get("matched_reasons", [
                    "Scored via Hindsight Cross-Encoder Reranker",
                    "Retrieved via Vectorize Multi-Strategy Search"
                ]),
                "retained_at": matched_candidate.get("retained_at") or matched_inc.get("timestamp"),
                "original_error_signature": matched_inc.get("error_signature"),
                "match_strength": match_strength,
                "match_strength_percent": f"{round(match_strength * 100)}%",
            }

        return {
            "tier": tier,
            "tier_label": tier_label,
            "match_strength": match_strength,
            "match_strength_percent": f"{round(match_strength * 100)}%",
            "top_match": top_match_info,
            "summary": content.get("summary", ""),
            "suspected_root_cause": content.get("suspected_root_cause", ""),
            "runbook_steps": content.get("runbook_steps", []),
            "anti_patterns": content.get("anti_patterns", []),
            "citations": citations,
            "hindsight_evidence": hindsight_evidence,
            "generated_by": f"Groq ({GROQ_MODEL})",
        }

    def _synthesize_fallback_diagnosis(
        self,
        alert: Dict[str, Any],
        tier: str,
        tier_label: str,
        match_strength: float,
        matched_candidate: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Built-in fallback synthesis used when running offline or without an API key.
        """
        service = str(alert.get("service") or "unknown-service")
        error_sig = str(alert.get("error_signature") or "")
        pct_label = round(match_strength * 100)

        # CASE 1: COLD START (No past precedent)
        if tier == "COLD_START":
            return {
                "tier": tier,
                "tier_label": tier_label,
                "match_strength": match_strength,
                "match_strength_percent": f"{pct_label}%",
                "top_match": None,
                "summary": (
                    f"No historical incidents in memory bank match this error on '{service}'. "
                    "Operating in Cold-Start Fallback Mode: Engaging first-principles SRE triage."
                ),
                "suspected_root_cause": (
                    "Unknown novel failure mode. Based on error signature, check container resource "
                    "constraints, JVM memory limits, or external endpoint timeouts."
                ),
                "runbook_steps": [
                    f"Step 1: Check pod termination reason (`kubectl describe pod -l app={service}`)",
                    "Step 2: Inspect kernel ring buffer for OOM events (`dmesg -T | grep -i oom`)",
                    "Step 3: Review Git diff of recent deployments in namespace within last 24h",
                    "Step 4: Once resolved, log post-mortem into Hindsight to prevent amnesia for future on-call engineers.",
                ],
                "anti_patterns": [
                    "⚠️ Avoid blindly restarting without capturing heap dump or logs (`/tmp/heap.hprof`).",
                    "⚠️ Do not modify production resource limits without verifying database connection impacts.",
                ],
                "citations": [],
                "hindsight_evidence": None,
            }

        matched_inc = matched_candidate["incident"]
        top_match_info = {
            "incident_id": matched_inc.get("id"),
            "title": matched_inc.get("title"),
            "service": matched_inc.get("service"),
            "match_strength": match_strength,
            "incident": matched_inc,
        }

        # CASE 2: MODERATE MATCH (Partial Architectural Overlap)
        if tier == "MODERATE_MATCH":
            return {
                "tier": tier,
                "tier_label": tier_label,
                "match_strength": match_strength,
                "match_strength_percent": f"{pct_label}%",
                "top_match": top_match_info,
                "summary": (
                    f"Partial architectural overlap identified in Hindsight memory ({pct_label}% Match). "
                    f"Related to {matched_inc.get('id')}: '{matched_inc.get('title')}'. "
                    "Proceed with caution: symptoms may share architectural characteristics without having the same root cause."
                ),
                "suspected_root_cause": (
                    f"Potential architectural correlation with {matched_inc.get('id')}: {matched_inc.get('root_cause')} "
                    "(Verification required)."
                ),
                "runbook_steps": [
                    f"Verify whether current symptoms match {matched_inc.get('id')} failure mode before executing actions.",
                    *matched_inc.get("runbook_steps", []),
                ],
                "anti_patterns": [
                    "⚠️ Do not apply historical runbook blindly without verifying that the root cause is identical.",
                    *matched_inc.get("anti_patterns", []),
                ],
                "citations": [
                    {
                        "source_id": matched_inc.get("id"),
                        "title": matched_inc.get("title"),
                        "service": matched_inc.get("service"),
                        "resolved_by": matched_inc.get("resolved_by") or "SRE On-Call Team",
                        "timestamp": matched_inc.get("timestamp"),
                        "deployment_context": matched_inc.get("deployment_context"),
                        "root_cause": matched_inc.get("root_cause"),
                        "error_signature": matched_inc.get("error_signature"),
                    }
                ],
                "hindsight_evidence": {
                    "matched_reasons": matched_candidate.get("matched_reasons", [
                        "Partial architectural overlap",
                        "Retrieved via Hindsight Memory"
                    ]),
                    "retained_at": matched_candidate.get("retained_at") or matched_inc.get("timestamp"),
                    "original_error_signature": matched_inc.get("error_signature"),
                    "match_strength": match_strength,
                    "match_strength_percent": f"{pct_label}%",
                },
            }

        # CASE 3: HIGH CONFIDENCE MATCH (Found in Hindsight Memory)
        return {
            "tier": tier,
            "tier_label": tier_label,
            "match_strength": match_strength,
            "match_strength_percent": f"{pct_label}%",
            "top_match": top_match_info,
            "summary": (
                f"Historical precedent identified in Hindsight memory with {pct_label}% match strength. "
                f"This matches {matched_inc.get('id')}: '{matched_inc.get('title')}'."
            ),
            "suspected_root_cause": matched_inc.get("root_cause"),
            "runbook_steps": matched_inc.get("runbook_steps", []),
            "anti_patterns": matched_inc.get("anti_patterns", []),
            "citations": [
                {
                    "source_id": matched_inc.get("id"),
                    "title": matched_inc.get("title"),
                    "service": matched_inc.get("service"),
                    "resolved_by": matched_inc.get("resolved_by") or "SRE On-Call Team",
                    "timestamp": matched_inc.get("timestamp"),
                    "deployment_context": matched_inc.get("deployment_context"),
                    "root_cause": matched_inc.get("root_cause"),
                    "error_signature": matched_inc.get("error_signature"),
                }
            ],
            "hindsight_evidence": {
                "matched_reasons": matched_candidate.get("matched_reasons", [
                    "Scored via Hindsight Cross-Encoder Reranker",
                    "Retrieved via Vectorize Multi-Strategy Search"
                ]),
                "retained_at": matched_candidate.get("retained_at") or matched_inc.get("timestamp"),
                "original_error_signature": matched_inc.get("error_signature"),
                "match_strength": match_strength,
                "match_strength_percent": f"{pct_label}%",
            },
        }

    # ==========================================================================
    # PRIMITIVE 1 Integration: retain() - Save Post-Mortem
    # ==========================================================================
    def resolve_and_learn(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests a verified post-mortem / fix into Hindsight memory.
        This closes the learning loop and ensures the agent gets smarter.
        """
        result = self.memory.retain(incident_data)
        logger.info(f"Learned new post-mortem: {incident_data.get('id')} ({incident_data.get('title')})")
        return {
            "status": "success",
            "message": f"Incident {incident_data.get('id')} successfully retained into Hindsight memory bank.",
            "retained_id": incident_data.get("id"),
            "total_memories": len(self.memory.get_all_retained()),
        }

    # ==========================================================================
    # PRIMITIVE 3 Integration: reflect() - Synthesize Architectural Insights
    # ==========================================================================
    def get_systemic_reflection(self, topic: str = "systemic failure patterns and deployment risks") -> Dict[str, Any]:
        """
        Triggers Hindsight's biomimetic reflection engine to uncover
        temporal patterns, recurring deployment bottlenecks, and systemic risks.
        """
        return self.memory.reflect(topic=topic)


if __name__ == "__main__":
    agent = IncidentResponseAgent()
    print("Agent initialized successfully.")
