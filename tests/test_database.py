"""Tests for SQLite database operations and duplicate record prevention."""
import pytest
from src.database import (
    insert_payable,
    get_payable_by_vendor_and_invoice,
    get_payable_by_id,
    list_payables,
    save_task,
    get_task,
    DuplicatePayableError
)
from src.models import PayableRecord, TaskResult, TaskStatus, ExecutionTraceItem


def test_insert_and_retrieve_payable(temp_env):
    db_path = temp_env["db_path"]
    record = PayableRecord(
        invoice_number="INV-TEST-001",
        vendor_name="Acme Technologies",
        amount=1500.00,
        due_date="2024-11-15",
        currency="USD",
        source_file="test_invoice.json"
    )

    created = insert_payable(record, db_path=db_path)
    assert created.id is not None
    assert created.created_at is not None

    # Retrieve by ID
    by_id = get_payable_by_id(created.id, db_path=db_path)
    assert by_id is not None
    assert by_id.invoice_number == "INV-TEST-001"
    assert by_id.amount == 1500.00

    # Retrieve by vendor + invoice
    by_vendor = get_payable_by_vendor_and_invoice("Acme Technologies", "INV-TEST-001", db_path=db_path)
    assert by_vendor is not None
    assert by_vendor.id == created.id


def test_duplicate_payable_prevention(temp_env):
    db_path = temp_env["db_path"]
    record1 = PayableRecord(
        invoice_number="INV-DUP-999",
        vendor_name="Duplicate Vendor LLC",
        amount=400.00,
        due_date="2024-12-01"
    )
    insert_payable(record1, db_path=db_path)

    # Attempt duplicate insertion with same vendor and invoice number
    record2 = PayableRecord(
        invoice_number="INV-DUP-999",
        vendor_name="Duplicate Vendor LLC",
        amount=400.00,
        due_date="2024-12-01"
    )
    with pytest.raises(DuplicatePayableError) as exc_info:
        insert_payable(record2, db_path=db_path)

    assert "already exists" in str(exc_info.value).lower()


def test_save_and_retrieve_task_with_traces(temp_env):
    db_path = temp_env["db_path"]
    trace1 = ExecutionTraceItem(
        step_number=1,
        tool_name="search_invoices",
        parameters={"vendor_name": "Acme Technologies"},
        result={"count": 2},
        status="SUCCESS",
        timestamp="2024-10-11T12:00:00"
    )
    task = TaskResult(
        task_id="task-abc-123",
        user_query="Find Acme invoice",
        status=TaskStatus.SUCCESSFUL,
        summary="Processed successfully",
        traces=[trace1]
    )

    save_task(task, db_path=db_path)

    retrieved = get_task("task-abc-123", db_path=db_path)
    assert retrieved is not None
    assert retrieved.task_id == "task-abc-123"
    assert retrieved.status == TaskStatus.SUCCESSFUL
    assert len(retrieved.traces) == 1
    assert retrieved.traces[0].tool_name == "search_invoices"
