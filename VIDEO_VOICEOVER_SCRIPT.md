# 🎬 Video Voiceover & Action Script: Autonomous AI Task Worker

**Project**: Autonomous AI Task Worker  
**Repository**: [https://github.com/vaibhavdubey06/AI-Task-Manager](https://github.com/vaibhavdubey06/AI-Task-Manager)  
**Target Duration**: 3 minutes (180 seconds, max 3:15)  
**Target Audience**: CentrAlign AI Engineering Evaluation Team  
**Estimated Spoken Word Count**: ~415 words (delivered at a natural pace of ~135–140 words/minute with designated pauses for system processing)

---

## 📌 Demonstration Overview

This script is structured into six synchronized segments matching the project's actual architecture and UI states:
1. **0:00–0:20**: Introduction & The Core Problem
2. **0:20–0:45**: System Architecture & Execution Intelligence
3. **0:45–1:35**: End-to-End Execution (Flagship Acme Workflow)
4. **1:35–2:05**: Human Approval & Independent Verification
5. **2:05–2:35**: Reliability, Error Handling & Interactive Clarification
6. **2:35–3:00**: Key Engineering Decisions & Production Roadmap

---

## ⏱️ Detailed Segment-by-Segment Production Guide

### Segment 1: Introduction & The Core Problem (0:00 – 0:20)
- **Approximate Duration**: 20 seconds
- **Word Count**: 48 words
- **Processing Pause**: None

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **0:00–0:08** | Browser open at `http://localhost:8501`. Top banner visible: `⚡ Autonomous AI Task Worker`. | Cursor rests on the top header: `Autonomous AI Task Worker • Verified Autonomous Execution Loop`. | *"Hello! Today I'm demonstrating the Autonomous AI Task Worker, built for the CentrAlign AI engineering challenge."* | Clean hero banner displayed with `Production Ready` badge. | No |
| **0:08–0:20** | Main dashboard view showing the text area and quick presets. | Slowly circle the cursor over the **Natural Language Task Description** area. | *"Enterprise back-offices spend thousands of hours manually processing invoices and updating ledgers. Rather than just generating instructions, this agent accepts high-level business goals and autonomously executes them through controlled, sandboxed tools."* | Task description input box and preset buttons clearly visible. | No |

---

### Segment 2: Architecture & Execution Intelligence (0:20 – 0:45)
- **Approximate Duration**: 25 seconds
- **Word Count**: 58 words
- **Processing Pause**: 2 seconds after reset

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **0:20–0:32** | Left sidebar open, showing **Execution Intelligence** and **Permitted Tool Registry**. | Move cursor to sidebar. Highlight the green card: `Mode: 🟢 LLM Planning Enabled`, `Model: openai/gpt-oss-120b` (or active model), and `Fallback: Not Used`. | *"Looking at the sidebar, our Execution Intelligence panel displays the active planning mode. Here, live LLM planning is enabled through Groq. If credentials are ever missing or unreachable, the system transparently discloses deterministic fallback without crashing."* | Status card clearly shows model name and fallback state. | No |
| **0:32–0:40** | Sidebar: `🛡️ Permitted Tool Registry` section. | Click to expand `search_invoices (✅ Safe)` and `create_payable_record (⚠️ Consequential)`. | *"All capabilities are constrained by an explicit tool registry. Unregistered tools and arbitrary code execution are strictly blocked by Pydantic schema validation."* | Expanders open, displaying tool descriptions and input schemas. | No |
| **0:40–0:45** | Sidebar bottom: `🧹 Demo Controls`. | Click the button: `🔄 Reset Demo Environment`. | *(Brief pause while clicking)* *"I'll reset the environment so we begin with a clean database."* | Green toast: `Database wiped clean!`. SQLite tables emptied. | Yes (2s) |

---

### Segment 3: End-to-End Execution (0:45 – 1:35)
- **Approximate Duration**: 50 seconds
- **Word Count**: 118 words
- **Processing Pause**: 3–4 seconds while agent plans and executes steps 1–3

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **0:45–0:55** | Main workspace: `🎯 Quick Test Presets`. | Click preset: `📌 Acme Tech (Latest)`. | *"Let's trigger our flagship task: finding the latest invoice from Acme Technologies, extracting the amount and due date, entering it into accounts payable, and verifying completion."* | Text area populates with the Acme prompt. | No |
| **0:55–1:00** | Main workspace: Action buttons. | Click the primary red button: `🚀 Execute Autonomous Worker`. | *"When we launch the worker, the planner analyzes the goal and decomposes it into an ActionPlan."* | Spinner appears: `Autonomous Agent planning and executing steps...`. | Yes (3s) |
| **1:00–1:15** | Screen updates. Active task banner renders: `Task ID: <code>`, `Objective: ...`. Execution Intelligence bar appears. | Move cursor across the **Task Execution Intelligence Bar** (`🟢 LLM Planning Active`, model name). | *"Notice the intelligence bar confirming live LLM planning. The planner doesn't hardcode filenames; it emits dynamic parameter references, such as `$steps.search_invoices.result.latest.filename`."* | Green pill confirms live LLM planning; dynamic plan visible below. | No |
| **1:15–1:35** | Middle of page: Validated Action Plan table and Step Execution cards. | Scroll down to the `📋 Validated Action Plan` table, showing steps 1 through 4. | *"Our generic parameter resolver evaluates those references at runtime. Step 1 discovered the latest invoice text file. Step 2 read its content. Step 3 extracted the structured financial data. Crucially, the agent extracts real invoice attributes instead of hallucinating values."* | Action plan table displays steps, tools, reasoning, and consequential flags. | No |

---

### Segment 4: Human Approval & Independent Verification (1:35 – 2:05)
- **Approximate Duration**: 30 seconds
- **Word Count**: 72 words
- **Processing Pause**: 2 seconds after clicking approve

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **1:35–1:48** | Top alert: `### ⚠️ Human-in-the-Loop Approval Required`. Details show Vendor: `ACME TECHNOLOGIES INC.`, Invoice: `INV-2024-002`, Amount: `$2,750.50 USD`, Due Date: `2024-10-31`. | Hover over the transaction details card. Point to `$2,750.50` and `2024-10-31`. | *"Before modifying business state, the system automatically halts. Because creating a payable is flagged consequential, it pauses in `APPROVAL_REQUIRED` and displays the exact extracted payload for human review."* | Amber warning box with transaction breakdown and approval buttons. | No |
| **1:48–1:55** | Approval buttons: `✅ Approve & Commit...` and `❌ Reject...`. | Click: `✅ Approve & Commit to Accounts Payable`. | *(Click button)* *"I'll approve the commit. The worker resumes and executes the database insert."* | Spinner: `Resuming task with human approval...`. Page reloads. | Yes (2s) |
| **1:55–2:05** | Status badge turns green: `✅ Task Completed & Verified`. Side-by-side cards: Extracted Invoice Details & Independent Verification Evidence. | Scroll down to `🔍 Independent Verification Evidence`. Point to the 4 green metric checks (`Invoice Number`, `Vendor Name`, `Amount`, `Due Date`). | *"Notice that the agent does not grade its own work. Our independent verifier queried SQLite directly and cross-checked all four financial fields against the source invoice document, confirming a verified match."* | Status is `SUCCESSFUL`. All four checks display `✅ MATCH`. Sidebar ledger displays Record ID `#1`. | No |

---

### Segment 5: Reliability & Interactive Clarification (2:05 – 2:35)
- **Approximate Duration**: 30 seconds
- **Word Count**: 72 words
- **Processing Pause**: 2–3 seconds during initial run and resumption

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **2:05–2:15** | Scroll back up to `🎯 Quick Test Presets`. | Click preset: `❓ Ambiguous Vendor`. Then click: `🚀 Execute Autonomous Worker`. | *"Now let's observe resilience. We'll run an ambiguous document with multiple billing parties and no definite due date."* | Task executes steps 1–2, encounters ambiguity in step 3. | Yes (2s) |
| **2:15–2:23** | Screen updates. Amber box: `### ❓ User Clarification Required`. Status badge: `❓ Clarification Required`. | Point to the text: `**Reason:** Ambiguous invoice: multiple billing parties identified...`. | *"Instead of guessing or entering corrupted data, the worker halts in `CLARIFICATION_REQUIRED`. Our replanning engine isolates the missing information and requests guidance."* | Explanatory message and text input field appear. | No |
| **2:23–2:30** | Text input field: `Your Clarification / Guidance:`. | Click the box, type: `Process Acme Technologies`. | *(Typing guidance)* *"I'll provide clarification: 'Process Acme Technologies'."* | Text typed into input box. | No |
| **2:30–2:35** | Action button under clarification field. | Click: `🚀 Submit Clarification & Resume Task`. | *"When we submit, the worker resumes the same task lifecycle, adapts the remaining plan, and completes execution."* | Task resumes, replans, and reaches approval cleanly. | Yes (2s) |

---

### Segment 6: Key Engineering Decisions & Conclusion (2:35 – 3:00)
- **Approximate Duration**: 25 seconds
- **Word Count**: 57 words
- **Processing Pause**: None

| Timestamp | Screen / Visual State | Exact Action / Mouse Movement | Verbatim Spoken Voiceover | Expected UI Result | Pause? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **2:35–2:48** | Scroll down to the `⏱️ Sequential Execution Trace` section. | Slowly scroll through trace items showing millisecond latencies, input parameters, and status badges. | *"Architecturally, this system enforces four core principles: controlled autonomy through sandboxed tools, dynamic parameter propagation between steps, bounded replanning capped at two recovery attempts, and independent SQL verification."* | Execution traces illustrate full observability and granular timing. | No |
| **2:48–3:00** | Scroll to top hero banner. Open sidebar to show SQLite ledger. | Move cursor smoothly to rest on the top header: `⚡ Autonomous AI Task Worker`. | *"In production, this architecture scales to PostgreSQL and distributed workflow engines like Temporal. Reliable AI employees require deterministic guardrails around probabilistic intelligence. Thank you!"* | Full dashboard visible, showing verified state and clean audit trail. | No |

---

## 📊 Script Teleprompter Summary

- **Total Spoken Words**: ~425 words
- **Average Speech Rate**: 136 words/minute
- **Built-in Execution / UI Wait Windows**: ~11 seconds total
- **Total Calculated Run Time**: ~2 minutes 58 seconds (safely under the 3:15 ceiling)
