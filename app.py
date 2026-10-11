"""Autonomous AI Task Worker - Streamlit Dashboard

CentrAlign AI Engineering Challenge Submission
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import pandas as pd

from src.config import settings
from src.models import TaskStatus, TaskResult
from src.agent.executor import AutonomousExecutor
from src.database import (
    init_db,
    list_payables,
    list_recent_tasks,
    get_task,
    get_connection,
    reset_demo_environment,
)
from src.tools.registry import default_registry

# Streamlit Page Config
st.set_page_config(
    page_title="Autonomous AI Task Worker | CentrAlign AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Header Gradient Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }
    
    .hero-title {
        color: #f8fafc;
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 6px;
        letter-spacing: -0.02em;
    }
    
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 0px;
    }
    
    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-success {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    .badge-failed {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .badge-approval {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-clarification {
        background-color: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    
    .badge-progress {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Trace Timeline item */
    .trace-card {
        border-left: 3px solid #6366f1;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 0 10px 10px 0;
        padding: 12px 18px;
        margin-bottom: 10px;
    }
    
    .trace-card.success { border-left-color: #22c55e; }
    .trace-card.failed { border-left-color: #ef4444; }
    .trace-card.retried { border-left-color: #f59e0b; }
    .trace-card.approval { border-left-color: #eab308; }
</style>
""", unsafe_allow_html=True)

# Initialize Database
init_db()

# Session State Initialization
if "current_task" not in st.session_state:
    st.session_state.current_task = None
if "task_input" not in st.session_state:
    st.session_state.task_input = (
        "Find the latest invoice from Acme Technologies, extract the amount and due date, "
        "enter it into the company payable system, and confirm completion."
    )

# --- Top Hero Banner ---
st.markdown("""
<div class="hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="hero-title">⚡ Autonomous AI Task Worker</div>
            <div class="hero-subtitle">CentrAlign AI Engineering Challenge • Verified Autonomous Execution Loop</div>
        </div>
        <div style="text-align: right;">
            <span class="badge badge-success">Production Ready</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Sidebar: System Status & Persistence ---
with st.sidebar:
    st.markdown("### ⚙️ System Architecture")
    
    # LLM Status Indicator
    llm_active = settings.is_llm_configured()
    if llm_active:
        st.success(f"🟢 LLM Client: Connected ({settings.openai_model})")
    else:
        st.info("🟡 LLM Client: Offline / Deterministic Fallback Mode\n*(Honest reporting: OPENAI_API_KEY not set)*")
    
    auto_approve_toggle = st.toggle(
        "Auto-Approve Consequential Actions",
        value=settings.auto_approve,
        help="When disabled, financial transactions (inserting into accounts payable) pause for human confirmation."
    )
    
    st.divider()
    
    # Permitted Tools Sandbox
    st.markdown("### 🛡️ Permitted Tool Registry")
    st.caption("Arbitrary shell and Python execution are strictly blocked.")
    tools = default_registry.list_tools()
    for t in tools:
        is_consequential = "⚠️ Consequential" if t["consequential"] else "✅ Safe"
        with st.expander(f"`{t['name']}` ({is_consequential})"):
            st.write(t["description"])
    
    st.divider()
    
    # Accounts Payable SQLite Live View
    st.markdown("### 🗄️ SQLite Accounts Payable")
    payables = list_payables(limit=10)
    if payables:
        df_payables = pd.DataFrame([
            {
                "ID": p.id,
                "Vendor": p.vendor_name,
                "Invoice #": p.invoice_number,
                "Amount ($)": f"{p.amount:,.2f}",
                "Due Date": p.due_date,
                "Status": p.status
            }
            for p in payables
        ])
        st.dataframe(df_payables, use_container_width=True, hide_index=True)
    else:
        st.caption("No payable records in SQLite database yet.")
        
    st.divider()
    
    # Task History
    st.markdown("### 📜 Task Execution History")
    recent_tasks = list_recent_tasks(limit=10)
    if recent_tasks:
        for rt in recent_tasks:
            t_col1, t_col2 = st.columns([3, 1])
            with t_col1:
                st.caption(f"**ID:** `{rt['task_id']}` | {rt['created_at'][:19]}")
                st.write(f"*{rt['user_query'][:45]}...*")
            with t_col2:
                status = rt["status"]
                badge_class = (
                    "badge-success" if status == "SUCCESSFUL"
                    else "badge-failed" if status == "FAILED"
                    else "badge-approval" if status == "APPROVAL_REQUIRED"
                    else "badge-progress"
                )
                st.markdown(f'<span class="badge {badge_class}">{status[:7]}</span>', unsafe_allow_html=True)
                if st.button("Load", key=f"load_{rt['task_id']}"):
                    loaded = get_task(rt["task_id"])
                    if loaded:
                        st.session_state.current_task = loaded
                        st.rerun()
            st.markdown("---")
    else:
        st.caption("No recorded previous tasks.")

    st.divider()
    st.markdown("### 🧹 Demo Controls")
    if st.button("🔄 Reset Demo Environment", use_container_width=True, help="Clear all database tables (tasks, traces, payables) for a fresh demo run."):
        reset_demo_environment()
        st.session_state.current_task = None
        st.sidebar.success("Database wiped clean!")
        st.rerun()

# --- Main Workspace ---

# Preset Task Buttons
st.markdown("#### 🎯 Quick Test Presets")
preset_cols = st.columns(5)

with preset_cols[0]:
    if st.button("📌 Acme Tech (Latest)", use_container_width=True):
        st.session_state.task_input = (
            "Find the latest invoice from Acme Technologies, extract the amount and due date, "
            "enter it into the company payable system, and confirm completion."
        )
        st.rerun()

with preset_cols[1]:
    if st.button("🏢 Apex Global", use_container_width=True):
        st.session_state.task_input = (
            "Find the latest invoice from Apex Global Solutions, extract the amount and due date, "
            "enter it into the company payable system, and confirm completion."
        )
        st.rerun()

with preset_cols[2]:
    if st.button("⚠️ Missing Vendor", use_container_width=True):
        st.session_state.task_input = (
            "Find the latest invoice from NonExistent Corp, extract amount and enter into payable system."
        )
        st.rerun()

with preset_cols[3]:
    if st.button("⚡ Corrupted Invoice", use_container_width=True):
        st.session_state.task_input = (
            "Find the latest invoice from Broken Data Corp, extract amount and enter into payable system."
        )
        st.rerun()

with preset_cols[4]:
    if st.button("❓ Ambiguous Vendor", use_container_width=True):
        st.session_state.task_input = (
            "Find the latest invoice from Alpha Logistics, extract amount and enter into payable system."
        )
        st.rerun()

# Task Input Form
with st.container():
    user_query = st.text_area(
        "Natural Language Task Description:",
        value=st.session_state.task_input,
        height=90,
        placeholder="Enter your instruction here..."
    )
    
    col_run, col_clear = st.columns([4, 1])
    with col_run:
        run_clicked = st.button("🚀 Execute Autonomous Worker", type="primary", use_container_width=True)
    with col_clear:
        if st.button("🔄 Reset View", use_container_width=True):
            st.session_state.current_task = None
            st.rerun()

# Instantiate Executor
executor = AutonomousExecutor(auto_approve=auto_approve_toggle)

# Execute on Run Button Click
if run_clicked and user_query:
    with st.spinner("Autonomous Agent planning and executing steps..."):
        result = executor.run_task(user_goal=user_query)
        st.session_state.current_task = result
        st.rerun()

# --- Display Active Task State ---
current_task: TaskResult = st.session_state.current_task

if current_task:
    st.divider()
    
    # Task Status Banner
    status_val = current_task.status.value
    badge_map = {
        "SUCCESSFUL": ("badge-success", "✅ Task Completed & Verified"),
        "FAILED": ("badge-failed", "❌ Task Failed"),
        "APPROVAL_REQUIRED": ("badge-approval", "⚠️ Human Approval Required"),
        "CLARIFICATION_REQUIRED": ("badge-clarification", "❓ Clarification Required"),
        "IN_PROGRESS": ("badge-progress", "⏳ Execution In Progress"),
    }
    badge_class, status_label = badge_map.get(status_val, ("badge-progress", status_val))
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h3 style="margin: 0;">Task ID: <code>{current_task.task_id}</code></h3>
            <p style="color: #94a3b8; margin: 4px 0 0 0;">Objective: <em>"{current_task.user_query}"</em></p>
        </div>
        <div>
            <span class="badge {badge_class}" style="font-size: 1.05rem; padding: 6px 16px;">{status_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Human Approval Alert if needed ---
    if current_task.status == TaskStatus.APPROVAL_REQUIRED:
        st.warning("### ⚠️ Human-in-the-Loop Approval Required")
        st.write(current_task.summary)
        
        if current_task.extracted_invoice:
            inv = current_task.extracted_invoice
            st.markdown(f"""
            **Transaction Details Pending Approval:**
            - **Vendor:** {inv.vendor_name}
            - **Invoice Number:** `{inv.invoice_number}`
            - **Amount Due:** **${inv.total_amount:,.2f} {inv.currency}**
            - **Due Date:** `{inv.due_date}`
            - **Source Document:** `{inv.source_file or 'N/A'}`
            """)
        
        appr_col1, appr_col2 = st.columns([1, 1])
        with appr_col1:
            if st.button("✅ Approve & Commit to Accounts Payable", type="primary", use_container_width=True):
                with st.spinner("Resuming task with human approval..."):
                    resumed = executor.run_task(
                        user_goal=current_task.user_query,
                        task_id=current_task.task_id,
                        approved=True
                    )
                    st.session_state.current_task = resumed
                    st.rerun()
        with appr_col2:
            if st.button("❌ Reject & Abort Operation", use_container_width=True):
                current_task.status = TaskStatus.FAILED
                current_task.error_message = "Operation was rejected by user."
                current_task.summary = "Task aborted: User rejected the consequential database insertion."
                st.session_state.current_task = current_task
                st.rerun()

    # --- Interactive Clarification Dialog if needed ---
    elif current_task.status == TaskStatus.CLARIFICATION_REQUIRED:
        st.warning("### ❓ User Clarification Required")
        st.markdown(f"**Reason:** {current_task.clarification_prompt or current_task.summary}")
        st.info("The agent encountered ambiguity or missing information in the source document. Please provide guidance below to unblock and resume the task.")

        clarif_input = st.text_input(
            "Your Clarification / Guidance:",
            key="interactive_clarification_input",
            placeholder="e.g. Process Acme Technologies, or Due date is 2024-11-15"
        )

        c_col1, c_col2 = st.columns([1, 1])
        with c_col1:
            if st.button("🚀 Submit Clarification & Resume Task", type="primary", use_container_width=True):
                if clarif_input.strip():
                    with st.spinner("Resuming task with user clarification..."):
                        resumed = executor.run_task(
                            user_goal=current_task.user_query,
                            task_id=current_task.task_id,
                            clarification_response=clarif_input.strip()
                        )
                        st.session_state.current_task = resumed
                        st.rerun()
                else:
                    st.error("Please enter clarification instructions before resuming.")
        with c_col2:
            if st.button("❌ Abort Task", use_container_width=True):
                current_task.status = TaskStatus.FAILED
                current_task.error_message = "Task aborted by user during clarification."
                current_task.summary = "Task aborted: User cancelled during clarification."
                st.session_state.current_task = current_task
                st.rerun()

    # --- Summary & Final Outcome ---
    if current_task.summary:
        if current_task.status == TaskStatus.SUCCESSFUL:
            st.success(f"**Outcome Summary:** {current_task.summary}")
        elif current_task.status == TaskStatus.FAILED:
            st.error(f"**Failure Summary:** {current_task.summary}")
            if current_task.error_message:
                st.caption(f"Error Details: `{current_task.error_message}`")

    # --- Section: Extracted Invoice & Verification Evidence Side-by-Side ---
    col_inv, col_ver = st.columns([1, 1])
    
    with col_inv:
        st.markdown("### 📄 Extracted Invoice Details")
        if current_task.extracted_invoice:
            inv = current_task.extracted_invoice
            m1, m2 = st.columns(2)
            m1.metric("Vendor", inv.vendor_name)
            m2.metric("Invoice #", inv.invoice_number)
            
            m3, m4 = st.columns(2)
            m3.metric("Total Amount", f"${inv.total_amount:,.2f} {inv.currency}")
            m4.metric("Due Date", inv.due_date)
            
            with st.expander("Show Full Extracted Record (JSON)"):
                st.json(inv.model_dump())
        else:
            st.info("No invoice details extracted yet.")
            
    with col_ver:
        st.markdown("### 🔍 Independent Verification Evidence")
        if current_task.verification:
            ver = current_task.verification
            if ver.verified:
                st.success(f"**VERIFIED AGAINST SQLITE:** {ver.message}")
            else:
                st.error(f"**VERIFICATION MISMATCH:** {ver.message}")
                
            # Evidence Matrix
            checks = ver.evidence_details.get("checks", {})
            if checks:
                check_cols = st.columns(len(checks))
                for idx, (k, v) in enumerate(checks.items()):
                    with check_cols[idx]:
                        status_emoji = "✅" if v == "MATCH" else "❌"
                        st.metric(k.replace("_", " ").title(), f"{status_emoji} {v}")
                        
            with st.expander("View Full Verification Evidence"):
                st.json(ver.evidence_details)
        else:
            st.info("Independent verification has not yet run.")

    # --- Section: Validated Action Plan ---
    st.markdown("### 📋 Validated Action Plan")
    if current_task.plan and current_task.plan.steps:
        plan_steps = current_task.plan.steps
        plan_data = []
        for s in plan_steps:
            plan_data.append({
                "Step": s.step_number,
                "Tool": s.tool_name,
                "Reasoning": s.reasoning,
                "Consequential": "⚠️ Yes (Approval Required)" if s.consequential else "No (Autonomous Safe)"
            })
        st.table(pd.DataFrame(plan_data))
    else:
        st.info("No action plan available.")

    # --- Section: Execution Trace Timeline ---
    st.markdown("### ⏱️ Sequential Execution Trace")
    if current_task.traces:
        for trace in current_task.traces:
            t_status = trace.status.lower()
            status_badge = (
                f'<span class="badge badge-success">SUCCESS</span>' if trace.status == "SUCCESS"
                else f'<span class="badge badge-failed">FAILED</span>' if trace.status == "FAILED"
                else f'<span class="badge badge-approval">RETRIED ({trace.retry_count})</span>' if trace.status == "RETRIED"
                else f'<span class="badge badge-approval">WAITING APPROVAL</span>' if trace.status == "WAITING_APPROVAL"
                else f'<span class="badge badge-progress">{trace.status}</span>'
            )
            
            trace_html = f"""
            <div class="trace-card {t_status}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>Step {trace.step_number}: <code>{trace.tool_name}</code></strong>
                        <span style="color: #64748b; font-size: 0.85rem; margin-left: 12px;">{trace.execution_time_ms} ms</span>
                    </div>
                    <div>
                        {status_badge}
                    </div>
                </div>
            </div>
            """
            st.markdown(trace_html, unsafe_allow_html=True)
            
            # Trace Details Expander
            with st.expander(f"Trace Details: Step {trace.step_number} ({trace.tool_name})"):
                t_col_p, t_col_r = st.columns(2)
                with t_col_p:
                    st.caption("Parameters Input:")
                    st.json(trace.parameters)
                with t_col_r:
                    if trace.result:
                        st.caption("Result Output:")
                        st.json(trace.result)
                    elif trace.error:
                        st.caption("Error / Warning:")
                        st.error(trace.error)
    else:
        st.info("No execution trace items logged.")

st.markdown("---")
st.caption("CentrAlign AI Engineering Challenge • Autonomous AI Task Worker MVP • SQLite Persistent Storage • Validated Pydantic Schemas")
