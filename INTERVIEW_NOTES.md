# Interview Preparation Notes: Autonomous AI Task Worker

This document provides concise, high-signal engineering rationales, architectural explanations, and tradeoff analyses for technical hiring evaluations.

---

## 1. Architecture Questions

### Q1: Why this architecture?
**Answer**:
The architecture separates concerns into a clear pipeline:
`Goal Specification -> Validated Planning -> Dynamic Parameter Resolution -> Sandboxed Tool Execution -> Independent Verification`.

In enterprise automation (such as accounting or ERP data entry), probabilistic language models cannot be granted direct write access to database state. By decoupling planning from execution and inserting deterministic validation barriers (Pydantic schemas, parameter resolvers, and independent SQL verifiers), we achieve the flexibility of LLM reasoning with the strict reliability guarantees required for enterprise systems.

---

### Q2: How does the agent decide next actions?
**Answer**:
Next action decisions are governed by a state machine driven by three layers:
1. **ActionPlan Generation**: The planner analyzes the user goal and available tool schemas to emit an ordered sequence of `ActionStep` records. Data dependencies between steps are expressed as symbolic path references (`$steps.<tool_name>.result.<field>`).
2. **Runtime Execution & Dynamic Resolution**: The executor resolves symbolic references just before executing each step. If a step requires approval (`consequential: true`), execution halts.
3. **Observation & Replanning**: If a tool fails or yields empty results, the runtime inspects the execution trace and invokes the replanner. The replanner determines whether to `RETRY` (for transient errors), `SUBSTITUTE_STEP` (for query relaxation), `REQUEST_CLARIFICATION` (for semantic ambiguity), or `TERMINATE` (on fatal faults).

---

### Q3: Why not LangChain or LangGraph?
**Answer**:
Frameworks like LangChain and LangGraph add significant abstraction overhead, hidden prompts, opaque state transitions, and heavy external dependencies that make auditing and enterprise hardening difficult:
1. **Control & Predictability**: In financial operations, every state transition, tool call, and retry must be deterministic and auditable.
2. **Minimal Dependency Footprint**: Our system relies exclusively on Python standard libraries, Pydantic for validation, and SQLite for persistence, eliminating framework lock-in and dependency bloat.
3. **Transparent Debugging**: All execution traces, latencies, and parameter mappings are visible and debuggable without digging through multi-layer framework internals.
4. **Resilience**: Custom parameter resolution and replanning loops allow us to implement bounded recovery (`MAX_REPLANNING_ATTEMPTS = 2`) without infinite agent cycles.

---

### Q4: How do you prevent hallucinated actions?
**Answer**:
Hallucination prevention is enforced through three strict defense mechanisms:
1. **Closed Tool Registry Sandbox**: The agent cannot execute arbitrary shell commands, Python code, or unregistered tools. Any tool name not explicitly declared in `ToolRegistry` raises `PermissionDeniedError`.
2. **Pydantic Schema Validation**: Every input argument is strictly validated against the tool's Pydantic schema before invocation. Malformed or hallucinated arguments fail immediately before reaching business logic.
3. **Dynamic Reference Grounding**: Steps receive actual outputs from previous tools through `$steps...` references resolved directly against verified in-memory/persisted execution outputs, preventing the LLM from inventing fake invoice IDs, amounts, or vendor names.

---

### Q5: How do you verify success?
**Answer**:
We use an **Independent Outcome Verification** pattern:
- The agent does **not** grade its own homework or trust a tool's boolean return value.
- After a payable record is committed, the separate `OutcomeVerifier` component directly queries SQLite and performs an out-of-band audit.
- It cross-checks four distinct attributes against the original source invoice document:
  1. Exact invoice number equality
  2. Normalized vendor string matching
  3. Floating-point numerical amount comparison (within $0.005 tolerance)
  4. Exact due date match
- If any attribute diverges, the task is marked as failed, regardless of what the executor reported.

---

### Q6: How would this scale to production?
**Answer**:
Scaling to enterprise production requires five straightforward architectural steps:
1. **Storage Layer**: Migrate SQLite to **PostgreSQL** with connection pooling (`pgbouncer`), row-level locking, and transactional read-replicas.
2. **Distributed Queue & Orchestration**: Replace the in-process execution loop with a distributed task orchestrator like **Temporal**, **Celery**, or **Argo Workflows** to manage durable execution, checkpointing, and retries across worker nodes.
3. **ERP Connectors**: Replace the local filesystem invoice tools with OAuth-authenticated connectors to NetSuite, SAP, Workday, and cloud document repositories (AWS S3, Azure Blob).
4. **Security & RBAC**: Integrate SSO/OIDC for human-in-the-loop approvals, with role-based permissions governing who can approve consequential financial updates based on transaction amounts.
5. **Observability**: Stream execution traces into **OpenTelemetry** and Grafana for real-time latency, error budgeting, and model drift tracking.

---

## 2. Technical Deep Dive

### Planner (`ActionPlanner`)
- **Role**: Translates freeform user intent into an `ActionPlan` containing typed `ActionStep` definitions.
- **Implementation**: Utilizes an OpenAI-compatible API with structured JSON output instructions. When an API key is unavailable or the endpoint fails, it falls back to a deterministic planner that produces an identical schema-compliant action plan, ensuring zero downtime and 100% testability.
- **Reference Binding**: Rather than baking static values into steps, the planner outputs dynamic references (`$steps.search_invoices.result.matches[0].filename`).

### Dynamic Parameter Resolver (`src/agent/resolver.py`)
- **Role**: Domain-agnostic parameter engine decoupling tool execution from workflow specifics.
- **Capabilities**:
  - Supports dot-notation and array index bracket syntax (e.g., `matches[0].filename`).
  - Preserves native Python primitive types (`float`, `int`, `list`, `dict`), ensuring Pydantic schema validation succeeds without string coercion issues.
  - Recursively resolves nested dictionary and list arguments.

### Tool Registry (`ToolRegistry`)
- **Role**: Security sandbox perimeter.
- **Capabilities**:
  - Enforces explicit tool registration.
  - Validates all invocation payloads against tool-specific Pydantic schemas.
  - Intercepts and categorizes exceptions into `RecoverableToolError` vs non-recoverable `ToolExecutionError`.

### Execution Engine (`AutonomousExecutor`)
- **Role**: State machine orchestrator managing step execution, retries, approval halts, and recovery replanning.
- **States**: `PENDING`, `IN_PROGRESS`, `APPROVAL_REQUIRED`, `CLARIFICATION_REQUIRED`, `SUCCESSFUL`, `FAILED`.
- **Bounded Autonomy**: Limits tool retries to `MAX_RETRIES = 3` and replanning loops to `MAX_REPLANNING_ATTEMPTS = 2`.

### Human Approval Flow (HITL)
- **Role**: Prevents unintended state-changing mutations.
- **Mechanism**: Steps flagged with `consequential: True` (e.g., ledger writes) cause the executor to pause, save current progress to SQLite with status `APPROVAL_REQUIRED`, and display a confirmation dialog in the Streamlit UI.
- **Resumption**: When the human approves, the executor reloads the task by ID and resumes precisely at the consequential step without re-executing completed read-only steps.

### Replanning Mechanism (`ActionPlanner.replan`)
- **Role**: Autonomous runtime error recovery.
- **Triggers**: Tool execution exceptions or empty search results.
- **Actions**:
  - `RETRY`: Backoff and retry transient faults.
  - `SUBSTITUTE_STEP`: Adjust arguments (e.g., relax search strings from "Acme Technologies Corp" to "Acme Technologies").
  - `REQUEST_CLARIFICATION`: Halt with clear prompts when entity ambiguity is detected.
  - `TERMINATE`: Terminate cleanly if maximum recovery budget is exhausted.

### Outcome Verifier (`OutcomeVerifier`)
- **Role**: Independent auditor ensuring system state aligns with physical or digital source documents.
- **Mechanism**: Reads directly from SQLite, completely bypassing previous step outputs, and validates 4 business-critical invariant fields.

---

## 3. Tradeoffs

| Decision | Option Chosen | Alternative Considered | Tradeoff Analysis |
| :--- | :--- | :--- | :--- |
| **Storage Engine** | **SQLite** | PostgreSQL / DynamoDB | **Chosen for**: Zero external setup, self-contained single-file portability, instant unit testing.<br>**Tradeoff**: Concurrency is limited by single-writer file locks; unsuitable for high-throughput distributed workers. |
| **Agent Autonomy** | **Bounded Autonomy** (`MAX_REPLAN = 2`, `MAX_RETRIES = 3`) | Unlimited Autonomous Loops | **Chosen for**: Guaranteed termination, predictable token costs, zero runaway loops, and safety in financial workflows.<br>**Tradeoff**: Requires human intervention on complex compound failures that might theoretically self-resolve after 5+ iterations. |
| **Validation Architecture** | **Deterministic Safeguards + Pydantic** | LLM-as-a-Judge / Self-Reflection | **Chosen for**: 100% deterministic mathematical and schema correctness; immune to prompt drift, jailbreaks, or hallucinations.<br>**Tradeoff**: Less adaptable to completely unforeseen schema formats without updating tool models. |
| **Workflow Engine** | **Custom Modular Python Engine** | LangChain / LangGraph / CrewAI | **Chosen for**: Full visibility, zero bloat, instant startup, precise trace logging, and complete control over state transitions.<br>**Tradeoff**: Must maintain custom graph/loop logic rather than relying on community-maintained abstractions. |
