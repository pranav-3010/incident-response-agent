"""
OpenSRE Dataset Loader.

Parses and exposes the 197 real-world and synthetic SRE postmortem trajectories
from the OpenSRE benchmark (Slack, Cloudflare, GitHub, CircleCI, Datadog, Kubernetes).
"""

import json
import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger("OpenSRELoader")

DEFAULT_DATASET_PATH = os.path.join(os.path.dirname(__file__), "opensre_trajectories.jsonl")


def _parse_record(d: Dict[str, Any], idx: int) -> Dict[str, Any]:
    scenario_id = d.get("scenario_id") or f"OPENSRE-{idx+1:03d}"
    company = d.get("source_company") or "Kubernetes/Infra"
    raw_name = d.get("incident", "").replace("_", " ").title()
    label = f"[{company}] {raw_name} ({scenario_id})"

    ans = d.get("answer", "")
    rc_m = re.search(r"\*\*ROOT_CAUSE:\*\*\s*(.*?)(?=\n\n|\*\*ROOT_CAUSE_CATEGORY:|$)", ans, re.DOTALL | re.IGNORECASE)
    fix_m = re.search(r"\*\*FIX:\*\*\s*(.*?)(?=\n\n|$)", ans, re.DOTALL | re.IGNORECASE)

    rc = rc_m.group(1).strip() if rc_m else ""
    fix = fix_m.group(1).strip() if fix_m else ""

    # Extract symptoms / timeline
    tl_m = re.search(r"(\*\*Timeline:?\*\*.*?(?=\n\n\*\*|\n\n--|\Z))", ans, re.DOTALL | re.IGNORECASE)
    ev_m = re.search(r"(\*\*Evidence:?\*\*.*?(?=\n\n\*\*|\n\n--|\Z))", ans, re.DOTALL | re.IGNORECASE)
    telemetry = tl_m.group(1).strip() if tl_m else (ev_m.group(1).strip() if ev_m else ans[:400])

    category = d.get("true_category", "system")
    difficulty = d.get("difficulty", 3)
    trap_actions = d.get("trap_actions", [])

    return {
        "id": scenario_id,
        "label": label,
        "company": company,
        "title": f"{company}: {raw_name}",
        "service": company.lower().replace("/", "-").replace(" ", "-"),
        "severity": "CRITICAL" if difficulty >= 4 else "HIGH",
        "category": category,
        "error_signature": f"CRITICAL_ALERT: {company} service degradation ({category}) - {raw_name}",
        "stack_trace": telemetry,
        "root_cause": rc or "Identified via multi-stage probe analysis.",
        "fix": fix or "Follow standard recovery runbook.",
        "runbook_steps": [fix] if fix else ["Inspect pod health", "Roll back suspect release", "Verify telemetry SLOs"],
        "anti_patterns": trap_actions if trap_actions else ["Avoid manual pod restarts before logs/traces are collected."],
        "source_url": d.get("source_url"),
        "difficulty": difficulty,
        "tools_used": d.get("tools_used", []),
        "source": d.get("source", "real"),
    }


@lru_cache(maxsize=1)
def load_opensre_incidents(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads and caches all incidents from the OpenSRE dataset file."""
    path = filepath or DEFAULT_DATASET_PATH
    if not os.path.exists(path):
        logger.warning(f"OpenSRE dataset not found at {path}")
        return []

    incidents = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_data = json.loads(line)
                    incidents.append(_parse_record(raw_data, idx))
                except Exception as ex:
                    logger.debug(f"Failed to parse line {idx}: {ex}")
        logger.info(f"Loaded {len(incidents)} OpenSRE incidents from {path}")
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")

    return incidents


def get_opensre_incident_by_id(scenario_id: str, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches a specific OpenSRE incident by its scenario ID."""
    all_incidents = load_opensre_incidents(filepath)
    for inc in all_incidents:
        if inc["id"] == scenario_id:
            return inc
    return None


def convert_opensre_to_hindsight_format(opensre_item: Dict[str, Any]) -> Dict[str, Any]:
    """Converts an OpenSRE record to the schema expected by HindsightMemoryClient.retain()."""
    return {
        "id": opensre_item.get("id"),
        "title": opensre_item.get("title"),
        "service": opensre_item.get("service"),
        "severity": opensre_item.get("severity", "HIGH"),
        "error_signature": opensre_item.get("error_signature"),
        "stack_trace": opensre_item.get("stack_trace"),
        "root_cause": opensre_item.get("root_cause"),
        "runbook_steps": opensre_item.get("runbook_steps", []),
        "anti_patterns": opensre_item.get("anti_patterns", []),
        "resolved_by": f"OpenSRE Benchmark ({opensre_item.get('company', 'SRE')})",
        "deployment_context": f"Difficulty: {opensre_item.get('difficulty')}/5. Source: {opensre_item.get('source_url') or 'Synthetic'}",
    }
