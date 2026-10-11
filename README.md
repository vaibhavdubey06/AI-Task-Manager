# Autonomous AI Task Worker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent%20Storage-003B57.svg)](https://www.sqlite.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.7+-E92063.svg)](https://docs.pydantic.dev/)
[![Pytest](https://img.shields.io/badge/tests-24%20passed-brightgreen.svg)](https://pytest.org/)

**CentrAlign AI Engineering Challenge Submission: Autonomous AI Task Worker**

> 💡 **Repository Recommendation Note**:  
> **Current Repository Name**: `AI-Task-Manager`  
> **Recommended Repository Name**: `Autonomous-AI-Task-Worker`  
> **Rationale**: This project is not a personal todo or productivity task manager; it is an **autonomous digital enterprise worker** that translates business objectives into verified actions, interacts with financial ledgers, enforces permission boundaries, and verifies business outcomes.

---

## Project Overview

Modern enterprise back-offices are burdened with high-volume, repetitive data entry and document reconciliation workflows (such as accounts payable processing and invoice auditing). While Large Language Models (LLMs) excel at natural-language reasoning, unconstrained autonomous agents frequently fail in enterprise production because of hallucinations, silent failures, lack of guardrails, and accidental mutations to production databases.

The **Autonomous AI Task Worker** bridges the gap between probabilistic AI reasoning and deterministic enterprise execution. It demonstrates an autonomous agent architecture with:
1. **Dynamic Planning**: Translates goals into structured, validated plans with data references (`$steps...`).
2. **Deterministic Execution & Tool Sandboxing**: Restricts tool calls to an allowlist with strict Pydantic schemas.
3. **Human-in-the-Loop Safeguards**: Pauses state-changing financial transactions for human sign-off.
4. **Independent Outcome Verification**: Verifies database state against source documents before reporting success.
5. **Bounded Replanning & Clarification**: Recovers from runtime failures within a strict bound (`MAX_REPLANNING_ATTEMPTS = 2`) and prompts for interactive clarification when ambiguities arise.

---

## 🎥 3-Minute Demonstration Video

A complete 3-minute video recording of the autonomous agent in action—showcasing live Groq LLM planning, human-in-the-loop approval, independent verification, and interactive clarification:

![CentrAlign AI Autonomous Task Worker Demo Walkthrough](demo_walkthrough.webp)

---

## 🛡️ LLM Safety Boundary

Enterprise systems cannot permit non-deterministic models to directly execute arbitrary code or mutate financial ledgers. This system enforces a strict separation of concerns:

```
┌────────────────────────────────────────────────────────┐
│            PROBABILISTIC REASONING (LLM)               │
│  - Understands user intent and business context        │
│  - Formulates structured ActionPlans                   │
│  - Suggests failure recovery & replanning strategies   │
└──────────────────────────┬─────────────────────────────┘
                           │ Outputs Structured Pydantic JSON
                           ▼
┌────────────────────────────────────────────────────────┐
│             DETERMINISTIC SYSTEM CORE                  │
│  - Validates tool calls against Pydantic schemas       │
│  - Enforces permissions via ToolRegistry sandbox       │
│  - Pauses for Human Approval on consequential actions  │
│  - Executes tools & logs persistent traces             │
│  - Independently audits SQL database against files     │
│  - Controls recovery bounds (MAX_REPLANNING = 2)       │
└────────────────────────────────────────────────────────┘
```

- **The LLM is responsible for**:
  - Understanding user intent and natural language objectives
  - Generating structured execution plans with dynamic reference tokens
  - Suggesting recovery actions when tools encounter unexpected data
- **The deterministic system is responsible for**:
  - Validating tool calls against schema allowlists
  - Executing actual operations and enforcing permissions
  - Guarding consequential state changes with human approvals
  - Independently verifying persistent database state
- **Core Safety Invariant**: **The LLM cannot directly modify business state or execute arbitrary code.**

---

## Architecture Diagram

```
User
 │
Streamlit Interface
 │
AI Planner (Groq / OpenAI / Deterministic Fallback)
 │
Execution Engine (AutonomousExecutor)
 │
Dynamic Parameter Resolver ($steps.<tool>.result.<field>)
 │
Tool Registry (Sandbox Security Boundary)
 │
Tools (search_invoices, read_invoice, extract_invoice_data, create_payable_record)
 │
Database (SQLite / company.db)
 │
Independent Verifier (OutcomeVerifier SQL Audit)
```

---

## Demo Workflow

Flagship task:
> **"Find the latest invoice from Acme Technologies, extract the amount and due date, enter it into the company payable system, and confirm completion."**

1. **Goal Formulation**: The planner ingests the goal and queries the LLM with registered tool schemas.
2. **Action Plan Generation**: Emits an ordered `ActionPlan` with dynamic parameter references:
   - Step 1: `search_invoices(vendor_name="Acme Technologies")`
   - Step 2: `read_invoice(filename="$steps.search_invoices.result.latest.filename")`
   - Step 3: `extract_invoice_data(raw_content="$steps.read_invoice.result.content", filename="$steps.read_invoice.result.filename")`
   - Step 4: `create_payable_record(...)` (`consequential: true`).
3. **Execution & Observation**: Tool outputs are recorded into `StepResult` containers.
4. **Human Approval Safeguard**: Before committing to Accounts Payable, the agent enters `APPROVAL_REQUIRED` and displays the invoice summary ($2,750.50 due 2024-10-31) in the UI.
5. **Approval & Write**: User clicks "Approve & Commit". The record is inserted into SQLite.
6. **Independent Verification**: `OutcomeVerifier` queries SQLite directly and audits invoice number, vendor, numerical amount, and due date.
7. **Final Verified Response**: Status transitions to `SUCCESSFUL`.

---

## Key Engineering Decisions

### 1. Why Bounded Autonomy Over Unrestricted Loops
Unbounded agent loops risk infinite retries, hallucinated rabbit holes, and runaway API spend. We cap retries at `MAX_RETRIES = 3` and dynamic recovery replanning at `MAX_REPLANNING_ATTEMPTS = 2`. If unresolved, the system halts cleanly in `CLARIFICATION_REQUIRED` or `FAILED`.

### 2. Why Human Approval Before State-Changing Actions
Financial commitments (creating payable records) cannot rely purely on probabilistic LLM inferences. Tools marked `consequential: true` cause the engine to freeze execution and request human review before writing to the database.

### 3. Why Independent Verification
Agents must not grade their own homework. The `OutcomeVerifier` runs as a distinct post-execution phase that queries the database directly (bypassing LLM interpretation) and cross-checks 4 invariant financial attributes against the source file.

### 4. Why Explicit Tool Registry (Sandbox Boundary)
Allowing an agent to emit arbitrary Python scripts or bash commands creates critical security vulnerabilities (RCE, prompt injection). `ToolRegistry` enforces an allowlist: only registered tools with explicit Pydantic schemas can execute.

### 5. Why Deterministic Safeguards Around LLM Behavior
LLMs provide flexible translation and planning, but should not control financial math, SQL transactions, or system state transitions. All parameter validation, type coercion, retry math, and database integrity rules are implemented deterministically in Python.

---

## Reliability Features

- **Exponential Backoff & Retries**: Distinguishes transient I/O exceptions (`RecoverableToolError`) from non-recoverable schema faults, retrying up to 3 times before triggering replanning.
- **Dynamic Failure Replanning**: When a tool fails or yields zero matches, the failure context is analyzed by the replanner to retry with relaxed parameters or substitute steps without restarting from scratch.
- **Interactive Clarification**: Ambiguous vendor entities or incomplete records halt with `CLARIFICATION_REQUIRED`, presenting a dedicated UI prompt for user guidance and resuming the same task instance.
- **Duplicate Prevention & Idempotency**: Database-level unique constraints `UNIQUE(vendor_name, invoice_number)` prevent duplicate ledger entries on retries or re-executions.
- **Execution Traces**: Every tool invocation records step number, tool name, resolved parameters, outputs, errors, latencies, and timestamps directly to SQLite for post-mortem auditing.
- **Execution Intelligence Observability**: Every task explicitly displays whether initial planning and replanning used live LLM intelligence (`LLM_PLANNING`) or deterministic offline logic (`DETERMINISTIC_FALLBACK`), with transparent fallback reasons.

---

## Security

- **Zero Arbitrary Code Execution**: No `eval()`, `exec()`, or unsanitized shell invocations.
- **Pydantic Schema Validation**: Every input argument and output payload is strictly validated at runtime against strongly-typed Pydantic schemas.
- **Path Traversal Sandboxing**: Invoice file access is strictly constrained to the authorized `data/invoices/` directory; attempts to traverse outside (`../../`) are blocked.
- **Credential Isolation**: LLM API keys and configuration parameters are loaded via environment variables (`.env`) and never committed to version control.

---

## Testing & Verification

The suite includes **24 automated tests** covering unit, integration, and end-to-end failure scenarios.

```bash
pytest -v
```

| Test Module | Tests | Scenarios Covered |
| :--- | :---: | :--- |
| `tests/test_database.py` | 3 | CRUD operations, duplicate payable rejection, task & trace persistence |
| `tests/test_tools.py` | 8 | Invoice discovery, multi-format reading (JSON/TXT), malformed JSON handling, ambiguity detection, tool registry sandboxing |
| `tests/test_resolver.py` | 3 | Dot and bracket path traversal, primitive type preservation, novel non-invoice tool-to-tool workflows |
| `tests/test_replanning.py` | 4 | Vendor search relaxation recovery, `MAX_REPLANNING_ATTEMPTS` enforcement, interactive clarification resumption, demo environment reset |
| `tests/test_scenarios.py` | 6 | E2E core Acme workflow with HITL approval, duplicate execution blocking, missing file handling, malformed invoice recovery, transient failure backoff, independent verifier tampering detection |

---

## Limitations

- **Simulated Back-Office Environment**: Operates against local file stores and an embedded SQLite database rather than live ERP APIs (SAP, NetSuite, Workday).
- **Limited Tool Ecosystem**: Focused on document parsing and payable ledgering; broader workflows (bank reconciliation, general ledger) require additional tool definitions.
- **SQLite Concurrency**: SQLite file locking is suited for demonstration and single-worker setups; enterprise production requires PostgreSQL.
- **Bounded Replanning Scope**: Up to 2 replanning attempts are permitted to ensure termination; complex compound multi-tool failures require human intervention.

---

## Future Work

- **Enterprise ERP Connectors**: Native adapters for SAP S/4HANA, NetSuite SuiteTalk REST APIs, and Workday.
- **PostgreSQL & Distributed Workers**: Migrate to an event-driven task queue (Celery, Temporal) with transactional PostgreSQL persistence.
- **Computer-Use & Browser Layer**: Enable autonomous navigation of legacy web portals that lack REST APIs.
- **Multi-Modal Document Parsing**: Integrate vision models (LayoutLM, Gemini Vision) to parse non-standard scanned PDF and image receipts.
- **Richer Verification Engine**: Add multi-way reconciliation against purchase orders (3-way PO matching).

---

## 🛠️ Demo Data Reset & Evaluation Instructions

### 1. Setup Environment
```bash
# Clone and navigate to project root
cd AI-Task-Manager

# Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key (Optional)
Copy `.env.example` to `.env`. Supports Groq, OpenAI, or any OpenAI-compatible provider:
```env
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=openai/gpt-oss-120b
```
*(If no API key is provided, the system seamlessly operates using its deterministic offline planner).*

### 3. Run Automated Tests
```bash
pytest -v
```

### 4. Launch Streamlit Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Reset Demo Environment
1. In the sidebar under **Demo Controls**, click **"Reset Demo Environment"**.
2. All tasks, traces, and payable records are purged for a clean test run.
