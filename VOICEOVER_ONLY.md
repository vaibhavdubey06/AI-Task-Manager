# 🎙️ Narration-Only Script: Autonomous AI Task Worker

**Purpose**: Read aloud while recording your voiceover track separately.  
**Target Speaking Pace**: Calm, conversational, and articulate (~135–140 words per minute).  
**Markers**: `[PAUSE]` indicates a 2–3 second pause while an on-screen button click, spinner, or reload occurs.

---

### [0:00 – 0:20] Introduction

"Hello! Today I'm demonstrating the Autonomous AI Task Worker, built for the CentrAlign AI engineering challenge.

Enterprise back-offices spend thousands of hours manually processing invoices and updating ledgers. Rather than just generating instructions, this agent accepts high-level business goals and autonomously executes them through controlled, sandboxed tools."

---

### [0:20 – 0:45] Architecture & Execution Intelligence

"Looking at the sidebar, our Execution Intelligence panel displays the active planning mode. Here, live LLM planning is enabled through Groq. If credentials are ever missing or unreachable, the system transparently discloses deterministic fallback without crashing.

All capabilities are constrained by an explicit tool registry. Unregistered tools and arbitrary code execution are strictly blocked by Pydantic schema validation.

I'll reset the environment so we begin with a clean database."

`[PAUSE 2 SECONDS — Database reset confirmation]`

---

### [0:45 – 1:35] End-to-End Execution

"Let's trigger our flagship task: finding the latest invoice from Acme Technologies, extracting the amount and due date, entering it into accounts payable, and verifying completion.

When we launch the worker, the planner analyzes the goal and decomposes it into an ActionPlan."

`[PAUSE 3 SECONDS — Agent plans and executes initial steps]`

"Notice the intelligence bar confirming live LLM planning. The planner doesn't hardcode filenames; it emits dynamic parameter references, such as `steps.search_invoices.result.latest.filename`.

Our generic parameter resolver evaluates those references at runtime. Step 1 discovered the latest invoice text file. Step 2 read its content. Step 3 extracted the structured financial data. Crucially, the agent extracts real invoice attributes instead of hallucinating values."

---

### [1:35 – 2:05] Human Approval & Verification

"Before modifying business state, the system automatically halts. Because creating a payable is flagged consequential, it pauses in `APPROVAL_REQUIRED` and displays the exact extracted payload for human review.

I'll approve the commit. The worker resumes and executes the database insert."

`[PAUSE 2 SECONDS — Committing record and running verifier]`

"Notice that the agent does not grade its own work. Our independent verifier queried SQLite directly and cross-checked all four financial fields against the source invoice document, confirming a verified match."

---

### [2:05 – 2:35] Reliability & Interactive Clarification

"Now let's observe resilience. We'll run an ambiguous document with multiple billing parties and no definite due date."

`[PAUSE 2 SECONDS — Step execution encounters ambiguity]`

"Instead of guessing or entering corrupted data, the worker halts in `CLARIFICATION_REQUIRED`. Our replanning engine isolates the missing information and requests guidance.

I'll provide clarification: 'Process Acme Technologies'."

`[PAUSE 2 SECONDS — Resuming task with guidance]`

"When we submit, the worker resumes the same task lifecycle, adapts the remaining plan, and completes execution."

---

### [2:35 – 3:00] Key Engineering Decisions & Conclusion

"Architecturally, this system enforces four core principles: controlled autonomy through sandboxed tools, dynamic parameter propagation between steps, bounded replanning capped at two recovery attempts, and independent SQL verification.

In production, this architecture scales to PostgreSQL and distributed workflow engines like Temporal. Reliable AI employees require deterministic guardrails around probabilistic intelligence.

Thank you!"
