"""End-to-end workflow scenarios and edge case tests."""
import pytest
from src.agent.executor import AutonomousExecutor
from src.agent.planner import ActionPlanner
from src.agent.verifier import OutcomeVerifier
from src.models import TaskStatus, InvoiceData
from src.database import get_payable_by_vendor_and_invoice, insert_payable, PayableRecord
from src.tools.invoice_tools import ReadInvoiceTool
from src.tools.base import RecoverableToolError


def test_core_workflow_acme_latest_invoice_with_human_approval(temp_env):
    """Core challenge test: Find latest invoice from Acme Technologies, extract details,
    request approval for payable entry, execute on approval, and verify outcome.
    """
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(
        db_path=db_path,
        invoices_dir=inv_dir,
        auto_approve=False  # Requires human approval for consequential action!
    )

    query = "Find the latest invoice from Acme Technologies, extract the amount and due date, enter it into the company payable system, and confirm completion."

    # Stage A: Run task initially -> should pause for human approval at step 4
    initial_res = executor.run_task(user_goal=query)
    assert initial_res.status == TaskStatus.APPROVAL_REQUIRED
    assert initial_res.extracted_invoice is not None
    # Latest invoice is INV-2024-002 with date 2024-10-01, amount 2750.50, due date 2024-10-31
    assert initial_res.extracted_invoice.invoice_number == "INV-2024-002"
    assert initial_res.extracted_invoice.total_amount == 2750.50
    assert initial_res.extracted_invoice.due_date == "2024-10-31"

    # Verify a WAITING_APPROVAL trace item exists
    waiting_traces = [t for t in initial_res.traces if t.status == "WAITING_APPROVAL"]
    assert len(waiting_traces) == 1
    assert waiting_traces[0].tool_name == "create_payable_record"

    # Stage B: Human user approves the action -> task resumes and completes
    final_res = executor.run_task(user_goal=query, task_id=initial_res.task_id, approved=True)
    assert final_res.status == TaskStatus.SUCCESSFUL
    assert final_res.verification is not None
    assert final_res.verification.verified is True
    assert final_res.verification.amount_matched is True
    assert final_res.verification.due_date_matched is True
    assert final_res.verification.vendor_matched is True

    # Independently check SQLite record
    record = get_payable_by_vendor_and_invoice("Acme Technologies", "INV-2024-002", db_path=db_path)
    assert record is not None
    assert record.amount == 2750.50
    assert record.due_date == "2024-10-31"


def test_duplicate_execution_prevention(temp_env):
    """Ensures running the task again for an already entered invoice halts with duplicate error."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    query = "Find the latest invoice from Acme Technologies, extract amount and due date, enter into payable system."

    # First run succeeds
    first_res = executor.run_task(user_goal=query)
    assert first_res.status == TaskStatus.SUCCESSFUL

    # Second run attempts to insert duplicate invoice INV-2024-002
    second_res = executor.run_task(user_goal=query)
    assert second_res.status == TaskStatus.FAILED
    assert "duplicate payable detected" in second_res.error_message.lower() or "already exists" in second_res.error_message.lower()


def test_missing_invoice_handling(temp_env):
    """Ensures searching for a non-existent vendor fails gracefully without crashing."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    query = "Find the latest invoice from NonExistent Corp, extract amount and enter into payable system."
    res = executor.run_task(user_goal=query)

    assert res.status == TaskStatus.FAILED
    assert "no invoices found" in res.error_message.lower()
    assert res.extracted_invoice is None


def test_malformed_invoice_handling(temp_env):
    """Ensures corrupted invoice syntax is detected and reported honestly."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, auto_approve=True)

    query = "Find the latest invoice from Broken Data Corp, extract amount and enter into payable system."
    res = executor.run_task(user_goal=query)

    assert res.status == TaskStatus.FAILED
    assert "malformed invoice json" in res.error_message.lower()


def test_recoverable_tool_failure_and_retry_limit(temp_env, monkeypatch):
    """Tests that transient failures trigger retries and enforce max retry limit."""
    db_path = temp_env["db_path"]
    inv_dir = temp_env["invoices_dir"]
    executor = AutonomousExecutor(db_path=db_path, invoices_dir=inv_dir, max_retries=2, auto_approve=True)

    call_count = 0

    def flaky_read(self, args):
        nonlocal call_count
        call_count += 1
        raise RecoverableToolError("Transient simulated disk lock")

    monkeypatch.setattr(ReadInvoiceTool, "_execute", flaky_read)

    query = "Find the latest invoice from Acme Technologies, extract amount and enter into payable system."
    res = executor.run_task(user_goal=query)

    assert res.status == TaskStatus.FAILED
    assert "max retries exceeded" in res.error_message.lower()
    # 1 initial attempt + 2 retries = 3 attempts total
    assert call_count == 3


def test_independent_verifier_detects_data_tampering(temp_env):
    """Verifies that if database record has tampered data, the verifier catches it."""
    db_path = temp_env["db_path"]
    verifier = OutcomeVerifier(db_path=db_path)

    # Insert a record with wrong amount
    tampered_record = PayableRecord(
        invoice_number="INV-2024-002",
        vendor_name="Acme Technologies",
        amount=9999.99,  # Wrong amount! Real is 2750.50
        due_date="2024-10-31"
    )
    insert_payable(tampered_record, db_path=db_path)

    invoice = InvoiceData(
        invoice_number="INV-2024-002",
        vendor_name="Acme Technologies",
        invoice_date="2024-10-01",
        due_date="2024-10-31",
        total_amount=2750.50
    )

    evidence = verifier.verify_payable_outcome(invoice=invoice, payable_id=tampered_record.id)
    assert evidence.verified is False
    assert evidence.amount_matched is False
    assert "mismatch" in evidence.message.lower()
