# 3-Minute Live Demonstration Script

**Project**: Autonomous AI Task Worker (CentrAlign AI Challenge)  
**Presenter**: Candidate  
**Total Duration**: 3:00 Minutes  

---

## ⏱️ [0:00 - 0:30] Introduction & Value Proposition

> *"Good morning. This system is an autonomous AI worker that converts high-level business goals into verified actions."*
>
> *"In enterprise operations, routine document processing and financial accounting workflows suffer from human bottlenecks. But deploying unconstrained LLMs directly to databases is risky because of hallucinations, silent data corruption, and unintended commits.*
>
> *Our architecture solves this through five pillars:*
> 1. *An AI Planner formulating structured ActionPlans with dynamic parameter references.*
> 2. *A Sandboxed Tool Registry enforcing permission boundaries.*
> 3. *Human-in-the-Loop gates before consequential database writes.*
> 4. *An Independent Outcome Verifier that audits database records directly against source files.*
> 5. *Execution Intelligence observability so evaluators always see whether the live LLM or deterministic fallback was active."*

---

## ⏱️ [0:30 - 2:00] Live Flagship Workflow Execution

> *"Let's see this in action on the dashboard."*

1. **Observe Execution Intelligence [0:30 - 0:45]**:
   - *Point to*: The sidebar **Execution Intelligence** card.
   - *Spoken*: *"Notice in the sidebar that our LLM Client is live and connected via Groq (`openai/gpt-oss-120b`). If the network or API key is absent, the system transparently logs Deterministic Fallback without failing."*

2. **Run Flagship Acme Invoice Goal [0:45 - 1:15]**:
   - *Action*: Select quick preset `📌 Acme Tech (Latest)`:
     `"Find the latest invoice from Acme Technologies, extract the amount and due date, enter it into the company payable system, and confirm completion."`
   - *Action*: Click **"🚀 Execute Autonomous Worker"**.
   - *Spoken*: *"The LLM decomposes the goal into sequential steps. Notice how data pipes between steps dynamically—step 2 references `$steps.search_invoices.result.latest.filename` rather than using hardcoded values."*

3. **Human Approval Safeguard [1:15 - 1:40]**:
   - *Observation*: The agent executes steps 1–3, extracts `$2,750.50` due `2024-10-31`, and halts with status **`⚠️ APPROVAL REQUIRED`**.
   - *Spoken*: *"Notice that the agent stopped automatically before writing to the ledger. Creating a payable is flagged consequential, so the system displays the extracted payload and pauses for human approval."*

4. **Approve & Independent Verification [1:40 - 2:00]**:
   - *Action*: Click **"✅ Approve & Commit to Accounts Payable"**.
   - *Observation*: Status transitions to **`✅ SUCCESSFUL`**. The Independent Outcome Verification card renders green checks for:
     - Invoice Number match
     - Vendor match
     - Numerical amount match ($2,750.50)
     - Due date match
   - *Spoken*: *"The record is committed. Crucially, the system does not simply trust the tool's return code. Our independent verifier queried SQLite directly, confirming that the committed payable record perfectly matches the source invoice document."*

---

## ⏱️ [2:00 - 2:30] Failure Handling & Interactive Clarification

> *"Now let's examine error recovery and the interactive clarification loop."*

1. **Trigger Ambiguous Scenario [2:00 - 2:15]**:
   - *Action*: Select quick preset `❓ Ambiguous Vendor`:
     `"Find the latest invoice from Alpha Logistics, extract amount and enter into payable system."`
   - *Action*: Click **"🚀 Execute Autonomous Worker"**.
   - *Observation*: The agent parses the document, discovers conflicting entities, and halts in **`❓ CLARIFICATION REQUIRED`**.
   - *Spoken*: *"Instead of guessing or entering corrupt data, the agent halts with a clarification prompt explaining the ambiguity."*

2. **Provide Guidance & Resume [2:15 - 2:30]**:
   - *Action*: In the clarification input box, type: `Process Acme Technologies`
   - *Action*: Click **"🚀 Submit Clarification & Resume Task"**.
   - *Observation*: The agent resumes the existing task ID, dynamically replans the remaining steps, and completes verified execution.
   - *Spoken*: *"We supply the missing information, resume the task, and the agent completes execution without losing state."*

---

## ⏱️ [2:30 - 3:00] Architecture, Safety Boundary & Scalability

> *"To wrap up, what makes this architecture enterprise-ready:*
> - *LLM Safety Boundary: The LLM understands intent and formulates plans; deterministic Python handles permission validation, file sandboxing, and database transactions. The LLM can never execute arbitrary code.*
> - *Bounded Autonomy: The recovery loop is strictly bounded to 2 replanning attempts, eliminating runaway agent loops.*
> - *Production Path: SQLite is easily swapped for PostgreSQL, and the in-process execution loop cleanly ports to distributed workers like Temporal or Celery.*
>
> *Thank you, and I welcome any questions."*
