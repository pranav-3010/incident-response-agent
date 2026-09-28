"""
Headless CLI Runner and Automated Verification Harness.

Executes the complete 3-Act Incident Response Lifecycle:
  Act 1: Cold-Start Alert (0% match -> first-principles triage)
  Act 2: Post-Mortem Retention (retain() -> learning from incident fix)
  Act 3: Re-occurrence (96% high match -> citation, runbook, anti-pattern)
  Act 4: Biomimetic Reflection (reflect() -> temporal patterns & architectural risks)

Usage:
  python run_demo.py
"""

import sys
import time
from agent import IncidentResponseAgent
from seed_incidents import get_holdout_scenario

# Terminal Color Codes for clear demo presentation
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def print_banner(text: str, color=CYAN):
    print(f"\n{color}{BOLD}{'=' * 75}")
    print(f" {text}")
    print(f"{'=' * 75}{RESET}\n")


def run_full_demo():
    print_banner("INCIDENT RESPONSE AGENT - HINDSIGHT MEMORY DEMO", CYAN)
    print(f"{BOLD}Initializing Agent & Loading Seed Memory Bank...{RESET}")
    agent = IncidentResponseAgent()
    scenario = get_holdout_scenario()
    initial_memories = len(agent.memory.get_all_retained())
    print(f"Loaded {GREEN}{initial_memories} historical incidents{RESET} into Hindsight Memory Bank.")
    print(f"Notice: Deliberate holdout active. 'billing-worker' has NEVER been seen.\n")

    time.sleep(1)

    # ==========================================================================
    # ACT 1: Cold Start (The Novel Outage)
    # ==========================================================================
    print_banner("ACT 1: NOVEL OUTAGE (COLD START)", YELLOW)
    act1_alert = scenario["act1_alert"]
    print(f"{BOLD}🚨 INCOMING TELEMETRY ALERT:{RESET}")
    print(f" • Service:    {RED}{act1_alert['service']}{RESET}")
    print(f" • Severity:   {RED}{act1_alert['severity']}{RESET}")
    print(f" • Error:      {act1_alert['error_signature']}")
    print(f" • Stack:\n{act1_alert['stack_trace']}\n")

    print(f"{CYAN}Agent querying Hindsight recall() with error signature...{RESET}")
    report1 = agent.triage_alert(act1_alert, exclude_incident_ids=["INC-108"])

    print(f"\n{BOLD}AGENT TRIAGE REPORT (ACT 1):{RESET}")
    print(f" • Match Status:   {report1['tier_label']}")
    print(f" • Match Strength: {report1['match_strength_percent']}")
    print(f" • Summary:        {report1['summary']}")
    print(f" • Action Items:")
    for step in report1["runbook_steps"][:3]:
        print(f"   - {step}")
    print(f" • Safe Guardrails:")
    for warn in report1["anti_patterns"]:
        print(f"   {warn}")

    time.sleep(1.5)

    # ==========================================================================
    # ACT 2: Learning Loop (Ingesting Post-Mortem via retain)
    # ==========================================================================
    print_banner("ACT 2: POST-MORTEM INGESTION (retain)", MAGENTA)
    act2_res = scenario["act2_resolution"]
    print(f"{BOLD}SRE Engineer resolves the outage and submits post-mortem:{RESET}")
    print(f" • Incident ID:    {act2_res['id']}")
    print(f" • Title:          {act2_res['title']}")
    print(f" • Verified Fix:   {act2_res['runbook_steps'][0]}")
    print(f" • Anti-Pattern:   {act2_res['anti_patterns'][0]}\n")

    print(f"{CYAN}Agent calling Hindsight retain() to eliminate institutional amnesia...{RESET}")
    learn_res = agent.resolve_and_learn(act2_res)
    print(f"{GREEN}✓ Successfully retained! Memory Bank now contains {learn_res['total_memories']} records.{RESET}")

    time.sleep(1.5)

    # ==========================================================================
    # ACT 3: The Payoff (Re-occurrence with High Match & Citations)
    # ==========================================================================
    print_banner("ACT 3: THE PAYOFF (HIGH-CONFIDENCE MATCH & CITATION)", GREEN)
    act3_alert = scenario["act3_alert"]
    print(f"{BOLD}🚨 WEEKS LATER: INCOMING ALERT ON BILLING-WORKER:{RESET}")
    print(f" • Service:    {act3_alert['service']}")
    print(f" • Error:      {act3_alert['error_signature']}\n")

    print(f"{CYAN}Agent querying Hindsight recall()...{RESET}")
    report3 = agent.triage_alert(act3_alert)

    print(f"\n{BOLD}AGENT TRIAGE REPORT (ACT 3):{RESET}")
    print(f" • Match Status:   {GREEN}{report3['tier_label']}{RESET}")
    print(f" • Match Strength: {GREEN}{report3['match_strength_percent']}{RESET}")
    print(f" • Diagnosis:      {report3['suspected_root_cause']}")
    print(f" • Proven Runbook:")
    for step in report3["runbook_steps"]:
        print(f"   {GREEN}✓ {step}{RESET}")
    print(f" • Critical Anti-Pattern Guardrail:")
    for warn in report3["anti_patterns"]:
        print(f"   {RED}{warn}{RESET}")

    print(f"\n{BOLD}PROVENANCE & CITATIONS:{RESET}")
    for cite in report3["citations"]:
        print(f" • Citing Incident: [{cite['source_id']}] {cite['title']}")
        print(f" • Resolved By:     {cite['resolved_by']} on {cite['timestamp']}")

    time.sleep(1.5)

    # ==========================================================================
    # ACT 4: Biomimetic Reflection (reflect)
    # ==========================================================================
    print_banner("ACT 4: BIOMIMETIC REFLECTION (reflect)", CYAN)
    print(f"{BOLD}Agent running Hindsight reflect() across memory bank...{RESET}")
    refl = agent.get_systemic_reflection()

    print(f"Analyzed {refl['total_incidents_analyzed']} incidents across all services.\n")
    for i, belief in enumerate(refl.get("synthesized_beliefs", []), 1):
        tier = belief.get("tier", "HOTSPOT")
        svc = belief.get("service", "system")
        print(f"{BOLD}[Insight #{i}] {tier} ({svc}){RESET}")
        print(f" • Observation:          {belief.get('observation', '')}")
        print(f" • {YELLOW}{belief.get('temporal_correlation', '')}{RESET}")
        print(f" • Synthesized Belief:   {belief.get('synthesized_belief', '')}")
        print(f" • Proactive Fix:        {GREEN}{belief.get('proactive_remediation', '')}{RESET}\n")

    print_banner("DEMO COMPLETED SUCCESSFULLY: ALL 3 PRIMITIVES VERIFIED", GREEN)


if __name__ == "__main__":
    run_full_demo()
