"""
Incident Response Agent - Interactive Showcase Dashboard.

A Streamlit web application showcasing the 3-Act Incident Response Lifecycle,
multi-strategy recall with match strength calibration, post-mortem retention,
and biomimetic reflection on systemic architectural risks.
"""

import streamlit as st

# Page Configuration MUST be the first Streamlit command executed
st.set_page_config(
    page_title="Incident Response Agent | Powered by Hindsight",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import time
from typing import Dict, Any
from datetime import datetime, timezone

from config import get_status
from agent import IncidentResponseAgent
from seed_incidents import get_seed_incidents, get_holdout_scenario
from opensre_loader import (
    load_opensre_incidents,
    get_opensre_incident_by_id,
    convert_opensre_to_hindsight_format,
)

# Custom Styling for SRE / Terminal aesthetic
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #2d3342;
        margin-bottom: 12px;
    }
    .badge-high {
        background-color: #1b472e;
        color: #4ade80;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-cold {
        background-color: #374151;
        color: #9ca3af;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .warning-box {
        background-color: #451a1a;
        border-left: 4px solid #ef4444;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 10px;
        color: #fca5a5;
    }
    .runbook-box {
        background-color: #132e22;
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 10px;
        color: #6ee7b7;
    }
    .reflection-card {
        background-color: #182635;
        border: 1px solid #2563eb;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


def render_citations_and_evidence(result: Dict[str, Any], bank_id: str):
    """
    Renders comprehensive historical provenance, past failure modes,
    and Hindsight retrieval rationale for matched incidents.
    """
    citations = result.get("citations", [])
    evidence = result.get("hindsight_evidence")

    if not citations and not evidence:
        return

    st.subheader("🏛️ Historical Citations & Provenance Evidence")
    st.caption("Verifiable audit trail proving this diagnosis is grounded directly in past production incident memory:")

    for cite in citations:
        source_id = cite.get("source_id", "INC-HISTORICAL")
        title = cite.get("title", "Past Incident Post-Mortem")
        resolved_by = cite.get("resolved_by") or "SRE On-Call Team"
        ts = cite.get("timestamp")
        date_str = f" • 📅 {ts}" if ts and str(ts).lower() != "none" else ""
        context = cite.get("deployment_context")
        root_cause = cite.get("root_cause")

        st.markdown(f"""
        <div style="background-color: #161b26; border: 1px solid #2563eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="background-color: #1e3a8a; color: #93c5fd; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-family: monospace; font-size: 0.9rem;">
                    🔖 {source_id}
                </span>
                <span style="color: #9ca3af; font-size: 0.85rem;">
                    👤 Resolved by: <b style="color: #e5e7eb;">{resolved_by}</b>{date_str}
                </span>
            </div>
            <h4 style="margin: 8px 0 6px 0; color: #f3f4f6;">{title}</h4>
            {f'<p style="color: #d1d5db; font-size: 0.9rem; margin-bottom: 6px;"><b>Past Root Cause:</b> {root_cause}</p>' if root_cause else ''}
            {f'<p style="color: #9ca3af; font-size: 0.85rem; margin-bottom: 0;"><b>Deployment Context:</b> {context}</p>' if context and str(context).lower() != "none" else ''}
        </div>
        """, unsafe_allow_html=True)

    # Retrieval Rationale Expander
    if evidence:
        reasons = evidence.get("matched_reasons", [])
        orig_sig = evidence.get("original_error_signature")
        match_str = evidence.get("match_strength_percent") or result.get("match_strength_percent", "N/A")

        with st.expander("🔍 Hindsight Retrieval Rationale & Match Signals", expanded=True):
            c_r1, c_r2 = st.columns([1, 2])
            with c_r1:
                st.markdown(f"**Match Confidence:** `{match_str}`")
                st.markdown(f"**Memory Bank:** `{bank_id}`")
                if evidence.get("retained_at"):
                    st.markdown(f"**Retained In Memory:** `{evidence['retained_at']}`")
            with c_r2:
                st.markdown("**Hindsight Associative Search Signals:**")
                if reasons:
                    for r in reasons:
                        st.markdown(f"- 🎯 {r}")
                else:
                    st.markdown("- 🎯 Retrieved via Vectorize Multi-Strategy Search (Vector + BM25 Keyword + Cross-Encoder Reranker)")
                if orig_sig:
                    st.caption(f"Historical Error Signature: `{orig_sig[:120]}`")


# ==============================================================================
# State Management
# ==============================================================================
if "agent" not in st.session_state:
    st.session_state.agent = IncidentResponseAgent()

if "act1_result" not in st.session_state:
    st.session_state.act1_result = None

if "act2_completed" not in st.session_state:
    st.session_state.act2_completed = False

if "act3_result" not in st.session_state:
    st.session_state.act3_result = None

agent = st.session_state.agent
scenario = get_holdout_scenario()


# ==============================================================================
# Sidebar - System Status & Controls
# ==============================================================================
with st.sidebar:
    st.title("🛡️ Ops Hindsight")
    st.caption("Autonomous Incident Memory Copilot")
    st.divider()

    status = get_status()
    st.subheader("System Status")
    st.markdown(f"**Memory Engine:** `{status['hindsight_mode']}`")
    st.markdown(f"**Bank ID:** `{status['hindsight_bank']}`")
    st.markdown(f"**Diagnostic Model:** `{status['groq_mode']}`")

    total_memories = len(agent.memory.get_all_retained())
    st.metric("Retained Memories in Bank", total_memories)

    st.divider()
    if st.button("🔄 Reset Memory Bank to Seed", use_container_width=True):
        with st.spinner("Resetting local memory and wiping Hindsight Cloud bank..."):
            agent.memory.reset_to_seed()
            st.session_state.act1_result = None
            st.session_state.act2_completed = False
            st.session_state.act3_result = None
            st.session_state.last_triage_result = None
            st.session_state.last_triage_opensre = None
            st.session_state.auto_retained_title = None
            if "reflection_cache" in st.session_state:
                del st.session_state["reflection_cache"]
            st.success("Memory bank reset to initial clean seed state!")
            time.sleep(0.4)
            st.rerun()

    st.divider()
    st.subheader("Official Resources")
    st.markdown("- [Hindsight GitHub](https://github.com/vectorize-io/hindsight)")
    st.markdown("- [Hindsight Docs](https://hindsight.vectorize.io/)")
    st.markdown("- [Vectorize Agent Memory](https://vectorize.io/what-is-agent-memory)")


# ==============================================================================
# Main Navigation Tabs
# ==============================================================================
tab_demo, tab_triage, tab_reflect, tab_bank = st.tabs([
    "🚀 3-Act Demo Progression",
    "🔍 Live Incident Triage",
    "🧠 Biomimetic Reflection",
    "🗄️ Memory Bank Explorer",
])


# ==============================================================================
# TAB 1: 3-Act Demo Progression (The Core Learning Story)
# ==============================================================================
with tab_demo:
    st.header("The Learning Arc: From Cold Start to Institutional Memory")
    st.write(
        "Demonstrating Hindsight's core memory lifecycle: "
        "**Act 1 (Cold Start)** ➔ **Act 2 (retain)** ➔ **Act 3 (recall with proven runbook & anti-pattern guardrails)**."
    )
    st.divider()

    col1, col2, col3 = st.columns(3)

    # --------------------------------------------------------------------------
    # ACT 1
    # --------------------------------------------------------------------------
    with col1:
        st.subheader("Act 1: Cold Start")
        st.caption("A novel outage hits. Memory bank has never seen this error.")

        act1_alert = scenario["act1_alert"]
        with st.expander("View Incoming Alert Telemetry", expanded=False):
            st.code(
                f"Service: {act1_alert['service']}\n"
                f"Severity: {act1_alert['severity']}\n"
                f"Error: {act1_alert['error_signature']}\n\n"
                f"{act1_alert['stack_trace']}",
                language="bash",
            )

        if st.button("1️⃣ Triage Novel Alert (Act 1)", use_container_width=True):
            with st.spinner("Querying Hindsight recall()..."):
                time.sleep(0.4)
                st.session_state.act1_result = agent.triage_alert(
                    act1_alert,
                    exclude_incident_ids=["INC-108"] if not st.session_state.act2_completed else None
                )

        if st.session_state.act1_result:
            r1 = st.session_state.act1_result
            st.markdown(f'<span class="badge-cold">{r1["tier_label"]}</span>', unsafe_allow_html=True)
            st.metric("Match Strength", r1["match_strength_percent"])
            st.info(r1["summary"])

            st.markdown("**First-Principles Triage Actions:**")
            for step in r1["runbook_steps"][:3]:
                st.markdown(f"- {step}")

    # --------------------------------------------------------------------------
    # ACT 2
    # --------------------------------------------------------------------------
    with col2:
        st.subheader("Act 2: Learning Loop")
        st.caption("On-call engineer fixes the issue and logs the post-mortem into Hindsight.")

        act2_res = scenario["act2_resolution"]
        with st.expander("View Verified Post-Mortem & Fix", expanded=False):
            st.markdown(f"**Incident ID:** `{act2_res['id']}`")
            st.markdown(f"**Root Cause:** {act2_res['root_cause']}")
            st.markdown(f"**Fix:** `{act2_res['runbook_steps'][0]}`")
            st.markdown(f"**Learned Anti-Pattern:** `{act2_res['anti_patterns'][0]}`")

        if not st.session_state.act1_result:
            st.warning("Complete Act 1 first to trigger the learning cycle.")
        else:
            if st.button("2️⃣ Retain Post-Mortem in Hindsight (Act 2)", use_container_width=True):
                with st.spinner("Calling Hindsight retain()..."):
                    time.sleep(0.4)
                    agent.resolve_and_learn(act2_res)
                    st.session_state.act2_completed = True
                    st.success("✓ Post-Mortem successfully retained into Hindsight!")
                    st.rerun()

        if st.session_state.act2_completed:
            st.success(f"✓ **Memory Bank Updated!** Total: {len(agent.memory.get_all_retained())} incidents.")
            st.markdown("""
            **What just happened?**
            Hindsight ingested the post-mortem into its episodic memory bank.
            The institutional amnesia gap has been closed for future on-call engineers.
            """)

    # --------------------------------------------------------------------------
    # ACT 3
    # --------------------------------------------------------------------------
    with col3:
        st.subheader("Act 3: The Payoff")
        st.caption("Weeks later, a similar crash occurs. Agent recalls the proven fix.")

        act3_alert = scenario["act3_alert"]
        with st.expander("View Recurring Alert Telemetry", expanded=False):
            st.code(
                f"Service: {act3_alert['service']}\n"
                f"Error: {act3_alert['error_signature']}\n\n"
                f"{act3_alert['stack_trace']}",
                language="bash",
            )

        if not st.session_state.act2_completed:
            st.warning("Complete Act 2 to observe Hindsight recall in action.")
        else:
            if st.button("3️⃣ Triage Recurring Alert (Act 3)", use_container_width=True):
                with st.spinner("Querying Hindsight recall()..."):
                    time.sleep(0.4)
                    st.session_state.act3_result = agent.triage_alert(act3_alert)

        if st.session_state.act3_result:
            r3 = st.session_state.act3_result
            st.markdown(f'<span class="badge-high">{r3["tier_label"]}</span>', unsafe_allow_html=True)
            st.metric("Match Strength", r3["match_strength_percent"])

            st.markdown(f"**Diagnosis:** {r3['suspected_root_cause']}")

            # Runbook Box
            st.markdown('<div class="runbook-box"><b>Proven Historical Runbook:</b><br>' +
                        '<br>'.join([f"✓ {s}" for s in r3['runbook_steps']]) +
                        '</div>', unsafe_allow_html=True)

            # Anti-Pattern Warning
            st.markdown('<div class="warning-box"><b>⚠️ Critical Anti-Pattern Guardrail:</b><br>' +
                        '<br>'.join(r3['anti_patterns']) +
                        '</div>', unsafe_allow_html=True)

            # Citations & Evidence
            render_citations_and_evidence(r3, agent.memory.bank_id)


# ==============================================================================
# ==============================================================================
# TAB 2: Live Incident Triage Console
# ==============================================================================
with tab_triage:
    st.header("🔍 Live Incident Triage Console")
    st.write("Diagnose production incidents live with **Groq LLM** + **Hindsight Cloud Memory**.")

    triage_source = st.radio(
        "Incident Telemetry Source:",
        [
            "🌐 OpenSRE Benchmark Dataset (197 Real Outages: Slack, Cloudflare, GitHub, etc.)",
            "💾 Retained Memory Bank (Seed & Stored Postmortems)",
            "✍️ Custom Outage Input",
        ],
        horizontal=True,
    )

    opensre_list = load_opensre_incidents()
    available_incidents = agent.memory.get_all_retained()

    default_service = "slack"
    default_error = ""
    default_stack = ""
    selected_opensre_item = None

    if "OpenSRE" in triage_source and opensre_list:
        opensre_options = [inc["label"] for inc in opensre_list]
        selected_label = st.selectbox(
            f"Select an Outage Trajectory ({len(opensre_list)} available):",
            opensre_options,
            index=0,
        )
        selected_opensre_item = next((inc for inc in opensre_list if inc["label"] == selected_label), None)
        if selected_opensre_item:
            default_service = selected_opensre_item["service"]
            default_error = selected_opensre_item["error_signature"]
            default_stack = selected_opensre_item["stack_trace"]

            with st.expander("ℹ️ Ground Truth Outage Specs (OpenSRE Dataset)", expanded=False):
                c_i1, c_i2, c_i3 = st.columns(3)
                with c_i1:
                    st.markdown(f"**Company:** `{selected_opensre_item['company']}`")
                with c_i2:
                    st.markdown(f"**Category:** `{selected_opensre_item['category']}`")
                with c_i3:
                    st.markdown(f"**Difficulty:** `{selected_opensre_item['difficulty']}/5`")
                if selected_opensre_item.get("source_url"):
                    st.markdown(f"**Postmortem URL:** [{selected_opensre_item['source_url']}]({selected_opensre_item['source_url']})")
                if selected_opensre_item.get("trap_actions"):
                    st.markdown("**Known Anti-Patterns / Traps in Outage:**")
                    for trap in selected_opensre_item["trap_actions"]:
                        st.warning(f"⚠️ {trap}")

    elif "Retained Memory Bank" in triage_source:
        retained_options = [
            f"{s.get('id', 'NEW')} - {s.get('title', 'Outage')} ({s.get('service', 'system')})"
            for s in available_incidents
        ]
        if retained_options:
            selected_ret = st.selectbox("Select a Saved Memory Record:", retained_options)
            inc_id = selected_ret.split(" - ")[0]
            selected_seed = next((s for s in available_incidents if s.get("id") == inc_id), None)
            if selected_seed:
                default_service = selected_seed.get("service", "api-gateway")
                default_error = selected_seed.get("error_signature", "")
                default_stack = selected_seed.get("stack_trace", "")
        else:
            st.info("No retained memories found.")
    else:
        default_service = "api-gateway"
        default_error = "502 Bad Gateway: Connection refused to upstream pod"
        default_stack = "[error] connect() failed (111: Connection refused) while connecting to upstream"

    col_svc, col_err = st.columns([1, 2])
    with col_svc:
        input_service = st.text_input("Microservice / Component", value=default_service)
    with col_err:
        input_error = st.text_input("Error Signature", value=default_error)

    input_stack = st.text_area("Stack Trace / Telemetry Logs", value=default_stack, height=130)

    col_triage_btn, col_auto_retain = st.columns([2, 1])
    with col_auto_retain:
        st.write("")
        auto_retain = st.checkbox(
            "⚡ Auto-retain to Cloud Memory",
            value=False,
            help="Automatically commit this incident's resolution to Hindsight Cloud on triage. "
                 "Leave off while testing match strength, otherwise re-triaging the same alert will "
                 "match against the copy it just stored and always show a near-perfect score.",
        )
    with col_triage_btn:
        run_triage = st.button("🚀 Run Diagnostic Triage with Groq & Hindsight", use_container_width=True)

    if run_triage:
        custom_alert = {
            "service": input_service,
            "error_signature": input_error,
            "stack_trace": input_stack,
        }
        with st.spinner("Executing Groq LLM reasoning + Hindsight recall()..."):
            res = agent.triage_alert(custom_alert)
            st.session_state.last_triage_result = res
            st.session_state.last_triage_opensre = selected_opensre_item
            st.session_state.auto_retained_title = None

            # ------------------------------------------------------------------
            # Auto-Retention into Hindsight Cloud
            # ------------------------------------------------------------------
            if auto_retain:
                if selected_opensre_item:
                    item_to_retain = convert_opensre_to_hindsight_format(selected_opensre_item)
                else:
                    item_to_retain = {
                        "id": f"INC-{int(time.time())}",
                        "title": f"{input_service}: {input_error[:45]}",
                        "service": input_service,
                        "severity": "HIGH",
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "error_signature": input_error,
                        "stack_trace": input_stack,
                        "root_cause": res.get("suspected_root_cause", "Diagnosed by Groq"),
                        "runbook_steps": res.get("runbook_steps", []),
                        "anti_patterns": res.get("anti_patterns", []),
                        "resolved_by": "Autonomous SRE Copilot (Groq)",
                        "deployment_context": "Auto-retained during live triage session.",
                    }
                agent.resolve_and_learn(item_to_retain)
                st.session_state.auto_retained_title = item_to_retain.get("title", "Incident")

    if st.session_state.get("last_triage_result"):
        res = st.session_state["last_triage_result"]

        if st.session_state.get("auto_retained_title"):
            st.success(
                f"⚡ **Auto-Retained into Hindsight Cloud!** Successfully committed "
                f"**'{st.session_state['auto_retained_title']}'** into memory bank `{agent.memory.bank_id}`. "
                "The agent will now permanently remember this failure mode and its verified fix."
            )

        col_t1, col_t2 = st.columns([1, 3])
        with col_t1:
            st.metric("Match Strength", res["match_strength_percent"])
            st.markdown(f"**Tier:** `{res['tier']}`")
        with col_t2:
            st.markdown(f"### {res['tier_label']}")
            st.write(res["summary"])

        st.subheader("Diagnosis & Root Cause")
        st.write(res["suspected_root_cause"])

        st.subheader("Actionable Remediation Runbook")
        for step in res["runbook_steps"]:
            st.markdown(f"- {step}")

        if res["anti_patterns"]:
            st.subheader("⚠️ Guardrails & Anti-Patterns to Avoid")
            for warn in res["anti_patterns"]:
                st.error(warn)

        if res.get("citations") or res.get("hindsight_evidence"):
            render_citations_and_evidence(res, agent.memory.bank_id)

        # Manual retain button if auto_retain was unchecked
        if not auto_retain:
            if st.session_state.get("last_triage_opensre"):
                item_to_retain = convert_opensre_to_hindsight_format(st.session_state["last_triage_opensre"])
            else:
                item_to_retain = {
                    "id": f"INC-{int(time.time())}",
                    "title": f"{input_service}: {input_error[:45]}",
                    "service": input_service,
                    "severity": "HIGH",
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "error_signature": input_error,
                    "stack_trace": input_stack,
                    "root_cause": res.get("suspected_root_cause", "Diagnosed by Groq"),
                    "runbook_steps": res.get("runbook_steps", []),
                    "anti_patterns": res.get("anti_patterns", []),
                    "resolved_by": "Autonomous SRE Copilot (Groq)",
                    "deployment_context": "Retained manually via live triage session.",
                }
            st.divider()
            if st.button(f"📥 Manually Retain '{item_to_retain['title']}' to Hindsight Cloud Bank", use_container_width=True):
                with st.spinner("Retaining postmortem to Hindsight Cloud..."):
                    agent.resolve_and_learn(item_to_retain)
                    st.success(f"✓ '{item_to_retain['title']}' permanently retained in Hindsight Cloud Memory! You can now re-run triage to observe the high-confidence recall.")
                    time.sleep(0.4)
                    st.rerun()


# ==============================================================================
# TAB 3: Biomimetic Reflection (Mental Models & Systemic Risk)
# ==============================================================================
with tab_reflect:
    st.header("🧠 Biomimetic Reflection Engine (`reflect`)")
    st.write(
        "Hindsight does not just perform lookups. Its `reflect()` primitive reasons across all "
        "accumulated memories to synthesize **temporal failure correlations** and **evolving architectural beliefs**."
    )
    st.divider()

    # Interactive Reflection Topic Selector
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        reflection_topic = st.selectbox(
            "Select Reflection Inquiry Focus:",
            [
                "Systemic failure patterns and deployment risks across all services",
                "Kubernetes and network infrastructure faults (DNS, conntrack, iptables)",
                "Chronic operator anti-patterns and harmful recovery actions",
                "Database locks, read replica lag, and cache/connection exhaustion",
                "Custom Question to Reflection Engine...",
            ]
        )
        if reflection_topic == "Custom Question to Reflection Engine...":
            custom_topic = st.text_input("Enter your custom reflection query:", value="What are the common vulnerabilities across our services?")
            query_to_send = custom_topic
        else:
            query_to_send = reflection_topic

    with col_top2:
        st.write("")
        st.write("")
        btn_reflect = st.button("⚡ Run Hindsight Reflection", use_container_width=True)

    if btn_reflect:
        with st.spinner(f"🧠 Querying Hindsight Cloud Reflection Engine across memory bank for: '{query_to_send}'..."):
            st.session_state.reflection_cache = agent.get_systemic_reflection(topic=query_to_send)
            st.session_state.last_reflection_topic = query_to_send

    if "reflection_cache" not in st.session_state or not isinstance(st.session_state.reflection_cache, dict):
        st.session_state.reflection_cache = agent.get_systemic_reflection()
        st.session_state.last_reflection_topic = "Systemic failure patterns and deployment risks"

    refl = st.session_state.reflection_cache
    if not isinstance(refl, dict):
        refl = agent.get_systemic_reflection()
        st.session_state.reflection_cache = refl

    st.markdown(
        f"**Memory Bank:** `{agent.memory.bank_id}` | "
        f"**Total Incidents Analyzed:** `{refl.get('total_incidents_analyzed', len(agent.memory.get_all_retained()))}` | "
        f"**Active Focus:** *{st.session_state.get('last_reflection_topic', 'Systemic Patterns')}* | "
        f"**Last Reflected:** `{refl.get('last_reflected_at', 'Now')}`"
    )
    st.divider()

    # If live cloud / engine reflection text is available, render the full report in beautiful markdown!
    if refl.get("live_cloud_text"):
        st.markdown("### 🌐 Hindsight Biomimetic Reflection Report")
        st.markdown(refl["live_cloud_text"])
        st.divider()

    # Render dynamic service clusters
    st.markdown("### 🔍 Clustered Architectural Hotspots & Beliefs")
    for i, belief in enumerate(refl.get("synthesized_beliefs", []), 1):
        tier = belief.get("tier", "CRITICAL RECURRING HOTSPOT")
        svc = belief.get("service", "system")
        raw_conf = belief.get("confidence", 0.85)
        try:
            conf_pct = round(float(raw_conf) * 100)
        except (ValueError, TypeError):
            conf_pct = 85
        obs = belief.get("observation", f"Incident pattern retained for '{svc}'.")
        corr = belief.get("temporal_correlation", "Observed across outage events.")
        syn_belief = belief.get("synthesized_belief", "Service exhibits recurring failure patterns.")
        remed = belief.get("proactive_remediation", f"Audit telemetry thresholds, retry backoffs, and resource limits for '{svc}'.")

        st.markdown(f"""
        <div class="reflection-card">
            <h4>[Hotspot #{i}] {tier} — <code>{svc}</code> (Confidence: {conf_pct}%)</h4>
            <p><b>Observation:</b> {obs}</p>
            <p style="color: #fbbf24;"><b>Correlation:</b> {corr}</p>
            <p><b>Synthesized Belief:</b> {syn_belief}</p>
            <p style="color: #34d399;"><b>Proactive Architectural Fix:</b> {remed}</p>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# TAB 4: Memory Bank Explorer
# ==============================================================================
with tab_bank:
    st.header("🗄️ Hindsight Memory Bank Explorer")
    st.write("Inspect all episodic memory records currently stored in the agent's memory bank.")

    all_memories = agent.memory.get_all_retained()

    # --------------------------------------------------------------------------
    # Fast Ingestion from OpenSRE Benchmark Dataset
    # --------------------------------------------------------------------------
    with st.expander("📥 Ingest from OpenSRE Benchmark Dataset (197 Real Outages)", expanded=False):
        st.write("Retain real-world postmortems from companies like Slack, Cloudflare, GitHub, CircleCI directly into Hindsight Cloud.")
        opensre_items = load_opensre_incidents()
        c_os1, c_os2 = st.columns([3, 1])
        with c_os1:
            os_select_label = st.selectbox(
                "Choose Outage to Retain:",
                [item["label"] for item in opensre_items],
                key="tab4_opensre_select"
            )
        with c_os2:
            st.write("")
            st.write("")
            btn_os_retain = st.button("📥 Retain to Bank", key="tab4_os_retain_btn", use_container_width=True)

        if btn_os_retain and os_select_label:
            matched_item = next((item for item in opensre_items if item["label"] == os_select_label), None)
            if matched_item:
                converted = convert_opensre_to_hindsight_format(matched_item)
                with st.spinner("Retaining to Hindsight Cloud..."):
                    agent.resolve_and_learn(converted)
                    st.success(f"✓ Successfully retained '{converted['title']}' to Hindsight Cloud Bank!")
                    time.sleep(0.4)
                    st.rerun()

    # --------------------------------------------------------------------------
    # Interactive Ingestion Form: Log New Custom Post-Mortem into Hindsight
    # --------------------------------------------------------------------------
    with st.expander("➕ Log New Custom Incident & Post-Mortem into Memory", expanded=False):
        st.write("Teach the agent a new incident failure mode, root cause, and verified fix.")

        # Compute next unique ID (INC-109, INC-110, ...)
        max_num = 107
        for m in all_memories:
            m_id = m.get("id", "")
            if m_id.startswith("INC-") and m_id[4:].isdigit():
                max_num = max(max_num, int(m_id[4:]))
        suggested_id = f"INC-{max_num + 1}"

        with st.form("new_incident_form", clear_on_submit=True):
            col_f1, col_f2 = st.columns([1, 3])
            with col_f1:
                f_id = st.text_input("Incident ID", value=suggested_id, disabled=True)
            with col_f2:
                f_title = st.text_input("Incident Title *", placeholder="e.g. Stripe Webhook Timeout Spike")

            col_f3, col_f4 = st.columns(2)
            with col_f3:
                f_service = st.text_input("Microservice / Component *", placeholder="e.g. payment-service, auth-api")
            with col_f4:
                f_severity = st.selectbox("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])

            f_error = st.text_input("Error Signature *", placeholder="e.g. stripe.error.APIConnectionError: Connection to Stripe API timed out")
            f_stack = st.text_area("Stack Trace / Telemetry Logs (Optional)", placeholder="Paste traceback or logs here...", height=70)
            f_root = st.text_area("Root Cause *", placeholder="Why did it happen? (e.g. DNS resolution timeout in AWS us-east-1 NAT gateway)", height=70)
            f_runbook = st.text_area("Runbook Steps (one per line) *", placeholder="Step 1: Failover webhook endpoints to secondary gateway\nStep 2: Restart NAT instance\nStep 3: Verify webhook ack rate in Stripe Dashboard", height=80)
            f_anti = st.text_area("Anti-Patterns to Avoid (one per line)", placeholder="DO NOT retry webhooks with zero backoff; creates upstream API rate limits", height=60)
            f_author = st.text_input("Resolved By", value="On-Call SRE Engineer")

            submitted = st.form_submit_button("💾 Save Custom Incident to Hindsight Memory", use_container_width=True)

        if submitted:
            if not (f_title.strip() and f_service.strip() and f_error.strip() and f_root.strip() and f_runbook.strip()):
                st.error("Please fill in all required fields (*) before saving.")
            else:
                new_incident = {
                    "id": suggested_id,
                    "title": f_title.strip(),
                    "service": f_service.strip(),
                    "severity": f_severity,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "error_signature": f_error.strip(),
                    "stack_trace": f_stack.strip() or f"Error Signature: {f_error.strip()}",
                    "root_cause": f_root.strip(),
                    "runbook_steps": [s.strip() for s in f_runbook.split("\n") if s.strip()],
                    "anti_patterns": [a.strip() for a in f_anti.split("\n") if a.strip()],
                    "resolved_by": f_author.strip() or "SRE Engineer",
                    "deployment_context": "Logged manually via SRE Console.",
                }
                agent.resolve_and_learn(new_incident)
                st.success(f"✓ Incident {suggested_id} ('{f_title}') successfully retained into Hindsight memory!")
                time.sleep(0.3)
                st.rerun()

    st.divider()
    st.caption(f"Showing {len(all_memories)} retained incident records in memory bank.")

    for inc in all_memories:
        with st.expander(f"[{inc.get('id', 'NEW')}] {inc.get('title')} ({inc.get('service')}) - {inc.get('severity')}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Timestamp:** `{inc.get('timestamp')}`")
                st.markdown(f"**Resolved By:** `{inc.get('resolved_by')}`")
                st.markdown(f"**Deployment Context:** {inc.get('deployment_context')}")
            with c2:
                st.markdown(f"**Error Signature:** `{inc.get('error_signature')}`")
            st.markdown(f"**Root Cause:** {inc.get('root_cause')}")
            st.markdown("**Runbook Steps:**")
            for s in inc.get("runbook_steps", []):
                st.markdown(f"- {s}")
            if inc.get("anti_patterns"):
                st.markdown("**Anti-Patterns:**")
                for a in inc.get("anti_patterns", []):
                    st.markdown(f"- ⚠️ {a}")
