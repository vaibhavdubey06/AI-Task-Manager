"""Tests for dynamic failure replanning, clarification resumption, and database reset."""
import pytest
from src.agent.executor import AutonomousExecutor, MAX_REPLANNING_ATTEMPTS
from src.agent.planner import ActionPlanner
from src.models import TaskStatus, ActionPlan, ActionStep, ReplanAction
from src.database import reset_demo_environment, list_payables, list_recent_tasks, insert_payable, PayableRecord
from src.tools.invoice_tools import ReadInvoiceTool
from src.tools.base import ToolExecutionError


def test_dynamic_replanning_recovery_on_vendor_search(temp_env):
    """Proves replanner recovers when initial vendor search returns empty results."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    # Goal with specific suffix that produces 0 direct matches
    query = "Find the latest invoice from Acme Technologies Corp, extract amount and due date, enter into payable system."
    res = executor.run_task(user_goal=query)

    # Replanner relaxed 'Acme Technologies Corp' to 'Acme Technologies' and completed!
    assert res.status == TaskStatus.SUCCESSFUL
    assert res.replanning_count >= 1
    # Check that a planner_recovery trace exists
    recovery_traces = [t for t in res.traces if t.tool_name == "planner_recovery"]
    assert len(recovery_traces) >= 1
    assert recovery_traces[0].parameters.get("action") == "SUBSTITUTE_STEP"


def test_replanning_max_attempts_enforcement(temp_env, monkeypatch):
    """Proves replanning terminates after MAX_REPLANNING_ATTEMPTS without infinite looping."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    # Force a permanent tool execution failure
    def always_fail(self, args):
        raise ToolExecutionError("Persistent unrecoverable tool fault")

    monkeypatch.setattr(ReadInvoiceTool, "_execute", always_fail)

    query = "Find the latest invoice from Acme Technologies, extract amount and enter into payable system."
    res = executor.run_task(user_goal=query)

    assert res.status == TaskStatus.FAILED
    assert res.replanning_count <= MAX_REPLANNING_ATTEMPTS


def test_interactive_clarification_resumption(temp_env):
    """Proves that a task halting with CLARIFICATION_REQUIRED can be resumed

    by passing clarification_response, completing the lifecycle.
    """
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    # Target the ambiguous vendor invoice
    query = "Find the latest invoice from Alpha Logistics, extract amount and enter into payable system."

    # Stage 1: Initial run encounters ambiguity
    r1 = executor.run_task(user_goal=query)
    assert r1.status == TaskStatus.CLARIFICATION_REQUIRED
    assert r1.clarification_prompt is not None

    # Stage 2: User provides clarification via interactive input
    r2 = executor.run_task(
        user_goal=query,
        task_id=r1.task_id,
        clarification_response="Process Acme Technologies"
    )

    # Replanner substituted the target entity with user guidance and completed
    assert r2.status == TaskStatus.SUCCESSFUL
    assert r2.extracted_invoice is not None
    assert r2.extracted_invoice.vendor_name == "ACME TECHNOLOGIES INC."


def test_reset_demo_environment(temp_env):
    """Proves reset_demo_environment clears all tables for repeatable evaluation."""
    db_path = temp_env["db_path"]

    # Seed data
    p = PayableRecord(
        invoice_number="INV-SEED-01",
        vendor_name="Seed Vendor",
        amount=100.0,
        due_date="2024-12-01"
    )
    insert_payable(p, db_path=db_path)
    assert len(list_payables(db_path=db_path)) == 1

    # Reset
    reset_demo_environment(db_path=db_path)

    # Verify tables are empty
    assert len(list_payables(db_path=db_path)) == 0
    assert len(list_recent_tasks(db_path=db_path)) == 0
