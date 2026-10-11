# 3-Minute Live Demonstration Script

**Project**: Autonomous AI Task Worker (CentrAlign AI Challenge)  
**Presenter**: Candidate  
**Total Duration**: 3:00 Minutes  

---

## ⏱️ [0:00 - 0:30] Problem & Architecture Explanation

> *"Good morning. Today I am presenting the Autonomous AI Task Worker—an enterprise automation agent designed to handle administrative workflows like invoice processing and accounts payable entry with strict reliability guarantees."*
>
> *"Unconstrained LLM agents often fail in enterprise settings due to hallucinations, runaway loops, and accidental state mutations. We solved this with an architecture that decouples planning from execution:
> 1. A planner that generates structured Action Plans with dynamic parameter references.
> 2. A sandboxed tool registry preventing arbitrary execution.
> 3. Human-in-the-loop gates for consequential financial actions.
> 4. An independent outcome verifier that queries the SQLite database directly before declaring success."*

---

## ⏱️ [0:30 - 2:00] Live Task Execution (Flagship Happy Path)

> *"Let's see this in action on the Streamlit dashboard."*

1. **Reset Demo Environment [0:30 - 0:40]**:
   - *Action*: Click **"Reset Demo Environment"** in the sidebar.
   - *Spoken*: *"First, notice our Demo Controls in the sidebar. I'll click 'Reset Demo Environment' to demonstrate our clean, repeatable test state. All payables and execution traces are purged."*

2. **Submit Goal [0:40 - 1:00]**:
   - *Action*: Select sample prompt `1. Process Acme Invoice (Standard Workflow)`:
     `"Find the latest invoice from Acme Technologies, extract amount and due date, enter it into payable system, and confirm completion."`
   - *Action*: Click **"Execute Autonomous Task"**.
   - *Spoken*: *"The planner decomposes this request into four distinct steps. Notice how Step 2 does not use hardcoded filenames—it references `$steps.search_invoices.result.matches[0].filename` through our dynamic parameter resolver."*

3. **Human Approval Safeguard [1:00 - 1:30]**:
   - *Observation*: The system executes steps 1-3, discovers `INV-2024-002_Acme_Technologies.txt`, parses `$2,750.50` due `2024-12-15`, and halts with status **`APPROVAL_REQUIRED`**.
   - *Spoken*: *"Notice that the agent halted automatically before touching the accounts payable ledger. Because `create_payable_record` is marked consequential, our system requires human sign-off. It displays the exact extracted payload: $2,750.50 due December 15, 2024."*

4. **Approval & Independent Verification [1:30 - 2:00]**:
   - *Action*: Click **"✅ Approve & Continue"**.
   - *Observation*: Step 4 executes. The status badge turns green (`SUCCESSFUL`). The Independent Verification card renders:
     - Record ID: 1
     - Invoice Number: `INV-2024-002` (Matched)
     - Vendor: `ACME TECHNOLOGIES INC.` (Matched)
     - Total Amount: `$2,750.50` (Matched within 0.005 tolerance)
     - Due Date: `2024-12-15` (Matched)
   - *Spoken*: *"The record is created. But crucially, our system does not trust the tool's return value. Our independent verifier performed a direct SQL query against SQLite, validating that the committed record perfectly matches the source invoice file."*

---

## ⏱️ [2:00 - 2:30] Failure Handling & Interactive Clarification

> *"Now let's examine resilience and interactive clarification."*

1. **Trigger Ambiguous Scenario [2:00 - 2:15]**:
   - *Action*: Select sample prompt `3. Ambiguous Vendor Invoice (Clarification Flow)`:
     `"Find the latest invoice from Alpha Logistics, extract amount and enter into payable system."`
   - *Action*: Click **"Execute Autonomous Task"**.
   - *Observation*: The agent analyzes the invoice, detects multiple conflicting entities, and halts with status **`CLARIFICATION_REQUIRED`**.
   - *Spoken*: *"Rather than guessing or corrupting data, the system enters `CLARIFICATION_REQUIRED`. It renders the reason and missing fields in the UI with a dedicated clarification input box."*

2. **Resume Task with Human Guidance [2:15 - 2:30]**:
   - *Action*: In the clarification text box, type: `Process Acme Technologies`.
   - *Action*: Click **"🚀 Submit Clarification & Resume Task"**.
   - *Observation*: The system resumes the existing task ID, dynamically replans the steps, executes the clarified workflow, and completes with verified success.
   - *Spoken*: *"We provide human guidance, click Resume, and the agent continues the same task lifecycle to completion without restarting."*

---

## ⏱️ [2:30 - 3:00] Technical Summary & Engineering Takeaways

> *"To summarize our technical highlights:
> - **Zero Framework Bloat**: Pure Python, Pydantic v2, and SQLite.
> - **Domain-Agnostic Executor**: The executor has zero knowledge of invoice fields—it relies on generic `$steps...` path resolution.
> - **Bounded Recovery**: A strict 2-attempt replanning limit guarantees termination.
> - **Complete Test Coverage**: 24 automated pytest tests verifying tool sandboxing, duplicate prevention, dynamic resolution, and tampering detection.
>
> Thank you, and I look forward to your questions."*
