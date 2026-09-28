# 🛡️ Incident Response Agent

> **An Autonomous SRE Copilot Powered by Hindsight Memory**  
> Eliminating *Institutional Amnesia* in DevOps and Site Reliability Engineering by moving from stateless triage to continuous biomimetic learning.

[![Hindsight Powered](https://img.shields.io/badge/Memory-Hindsight-blue)](https://github.com/vectorize-io/hindsight)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Streamlit UI](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io)

---

## 📌 Executive Summary & The Problem

At 3:00 AM on a weekend, when production alerts fire, on-call engineers face a brutal reality: **Institutional Amnesia**.

* Critical knowledge about past outages is fragmented across closed Jira tickets, 200-message Slack threads, and outdated wiki pages.
* The senior engineer who solved the exact same Redis connection leak or Kafka rebalance storm 4 months ago is either asleep or has left the company.
* Stateless AI chatbots fail dangerously in this scenario: they spit out generic textbook checklists (*"Check your database cables"*) and can recommend destructive actions like blind reboots that make outages 10x worse.

**The Incident Response Agent** solves this by establishing a permanent, learning SRE brain using **[Hindsight](https://github.com/vectorize-io/hindsight)**. It recalls proven runbooks in seconds, warns against historical anti-patterns, and continuously reflects across all incidents to uncover systemic architectural vulnerabilities.

---

## 🧠 How Hindsight Memory Powers the Agent

Unlike simple RAG (Retrieval-Augmented Generation) which treats memory as a dumb bag of embeddings, this agent utilizes **Hindsight's three biomimetic memory primitives**:

```
                              [ Production Telemetry / Alert ]
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │ Incident Response Agent │
                                └────────────┬────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
     1. recall()                     2. retain()                     3. reflect()
  (Associative Retrieval)        (Episodic Learning)            (Systemic Mental Models)
             │                               │                               │
  Multi-strategy search fuses     When an incident is            Analyzes memory banks to
  error signatures, stack         resolved, the post-mortem,     synthesize temporal patterns
  traces, and service taxonomy.   root cause, and verified fix   (e.g., "3 of 4 payment crashes
  Calculates calibrated           are stored permanently in      happened within 48h of auth
  Match Strength (0–100%).        Hindsight memory bank.         middleware deployments").
             │                               │                               │
             ▼                               ▼                               ▼
  [ Actionable Runbook +          [ Closes Institutional         [ Proactive CI/CD Guardrails
    Anti-Pattern Warnings ]         Amnesia Gap ]                  & Architectural Fixes ]
```

### 1. `recall()` — Multi-Strategy Retrieval with Match Strength
When an alert hits, the agent queries Hindsight using parallel vector embeddings, BM25 keyword matching, and service taxonomy. It yields a calibrated **Match Strength**:
* 🟢 **High Match ($\ge 80\%$)**: Cites historical incident ID, verified runbook steps, and exact engineer who resolved it.
* 🟡 **Moderate Match ($50\% - 79\%$)**: Surfaces partial architectural overlap across shared services.
* ⚪ **Cold Start ($< 50\%$)**: Transparently identifies novel issues and engages first-principles triage without hallucinating.

### 2. `retain()` — Episodic Post-Mortem Retention
When an incident is resolved, the agent ingests the verified post-mortem into Hindsight. This ensures the company's collective intelligence increases with every single outage.

### 3. `reflect()` — Evolving Beliefs & Temporal Risk Detection
Hindsight's reflection engine connects the dots across disparate incidents over time:
> *"Temporal Correlation: 3 separate connection pool failures in `payment-service` occurred within 18–36 hours of deploying updates to `auth-middleware`. Recommendation: Mandate connection pool exhaustion health-checks in CI/CD pipeline."*

---

## 🎬 The 3-Act Demo Progression (How to Demo)

The agent features a built-in 3-act progression to clearly demonstrate the memory learning curve:

| Act | Stage | Scenario | Agent Behavior |
| :---: | :--- | :--- | :--- |
| **Act 1** | **Cold Start** | Novel Kubernetes `OOMKilled` (Exit Code 137) in `billing-worker`. | **0% Match**. Honestly admits zero historical precedent; provides safe, first-principles SRE triage. |
| **Act 2** | **Learning Loop** | Engineer fixes issue with cursor chunking (`BATCH_CHUNK_SIZE=500`) and logs post-mortem. | Calls Hindsight **`retain()`**. Closes the knowledge gap. Memory bank updates in real time. |
| **Act 3** | **The Payoff** | Weeks later, similar batch memory spike occurs in `billing-worker`. | **96% High Match!** Instantly surfaces proven runbook, cites INC-108, and warns: ⚠️ *DO NOT scale pod replicas (causes DB lock starvation).* |

---

## 📊 Dataset Provenance

The seed memory bank is loaded with **realistic synthetic SRE incident trajectories** with production Kubernetes and microservice telemetry, inspired by failure-injection scenarios from the OpenSRE dataset (`quantranger/opensre-incident-trajectories`).

* Includes realistic services: `payment-service`, `api-gateway`, `order-db`, `inventory-worker`, `search-indexer`.
* The Act 1 `billing-worker` failure mode is **deliberately held out** of the seed set to guarantee an authentic cold-start demonstration.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10 or higher
* (Optional) Hindsight Cloud API Key (Get \$50 free credits with code `MEMHACK99` at [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io))
* (Optional) Groq API Key from [console.groq.com](https://console.groq.com)

> **Resilient Dual-Mode:** If API keys are not provided, the application automatically runs in a self-contained local simulation mode with identical behavior. It **never** crashes due to missing keys or rate limits.

### 1. Clone & Set Up Virtual Environment
```bash
git clone <your-repo-url>
cd incident-response-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
```bash
cp .env.example .env
# Edit .env to add your HINDSIGHT_API_KEY and GROQ_API_KEY
```

### 3. Run the Headless CLI Demo (Automated Test Harness)
```bash
python run_demo.py
```

### 4. Launch the Interactive Web Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📁 Repository Structure

```
incident-response-agent/
├── README.md                 # Complete system documentation & architecture
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── config.py                 # Configuration loader with auto-fallback detection
├── seed_incidents.py         # Realistic SRE dataset with deliberate holdout
├── memory_adapter.py       # Hindsight API wrapper (retain, recall, reflect)
├── agent.py                  # Core SRE diagnostic reasoning engine
├── run_demo.py               # Headless CLI demo runner & automated test harness
└── app.py                    # Streamlit interactive showcase dashboard
```

---

## 🔗 Official References
* **Hindsight GitHub:** [https://github.com/vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)
* **Hindsight Documentation:** [https://hindsight.vectorize.io/](https://hindsight.vectorize.io/)
* **Vectorize Agent Memory:** [https://vectorize.io/what-is-agent-memory](https://vectorize.io/what-is-agent-memory)
