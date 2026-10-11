"""Tests for generic dynamic parameter resolution."""
import pytest
from src.agent.resolver import resolve_parameters, traverse_path, resolve_single_reference
from src.agent.executor import AutonomousExecutor
from src.models import StepResult, ActionPlan, ActionStep, TaskStatus, PayableRecord
from src.database import insert_payable


def test_traverse_path():
    data = {
        "matches": [
            {"filename": "INV-001.json", "meta": {"vendor": "Acme"}},
            {"filename": "INV-002.txt", "meta": {"vendor": "Apex"}}
        ],
        "count": 2,
        "amount": 1250.75
    }
    assert traverse_path(data, "count") == 2
    assert traverse_path(data, "amount") == 1250.75
    assert traverse_path(data, "matches[0].filename") == "INV-001.json"
    assert traverse_path(data, "matches[1].meta.vendor") == "Apex"
    assert traverse_path(data, "matches[5].filename") is None
    assert traverse_path(data, "non_existent.field") is None


def test_resolve_parameters_typing():
    step_results = {
        "step_1": StepResult(
            step_number=1,
            tool_name="search_invoices",
            status="SUCCESS",
            result={"matches": [{"filename": "invoice_oct.json"}], "count": 1},
            timestamp="2026-10-11T12:00:00"
        ),
        "extract": StepResult(
            step_number=2,
            tool_name="extract_invoice_data",
            status="SUCCESS",
            result={"invoice_number": "INV-999", "amount": 450.50, "items": ["Item A", "Item B"]},
            timestamp="2026-10-11T12:00:01"
        )
    }

    raw_params = {
        "filename": "$steps.step_1.result.matches[0].filename",
        "inv_id": "$steps.extract.result.invoice_number",
        "total": "$steps.extract.result.amount",
        "all_items": "$steps.extract.result.items",
        "static_str": "constant_value"
    }

    resolved = resolve_parameters(raw_params, step_results)
    assert resolved["filename"] == "invoice_oct.json"
    assert resolved["inv_id"] == "INV-999"
    assert resolved["total"] == 450.50
    assert isinstance(resolved["total"], float)
    assert resolved["all_items"] == ["Item A", "Item B"]
    assert resolved["static_str"] == "constant_value"


def test_different_parameter_flow_without_modifying_executor(temp_env):
    """Proves that a completely novel workflow with non-invoice parameter piping

    executes through AutonomousExecutor using generic parameter resolution.
    """
    db_path = temp_env["db_path"]

    # 1. Seed a payable record in the database
    seed_record = PayableRecord(
        invoice_number="INV-CUSTOM-777",
        vendor_name="Generic Cloud Corp",
        amount=888.00,
        due_date="2024-12-15"
    )
    insert_payable(seed_record, db_path=db_path)

    # 2. Define a plan with an entirely different parameter flow:
    # Step 1: list_payables
    # Step 2: get_payable_record where parameters are extracted from Step 1's list output!
    custom_plan = ActionPlan(
        goal="Audit existing payables and retrieve specific record details",
        estimated_risk="LOW",
        steps=[
            ActionStep(
                step_number=1,
                tool_name="list_payables",
                parameters={"limit": 5},
                reasoning="List recent payables from database.",
                consequential=False
            ),
            ActionStep(
                step_number=2,
                tool_name="get_payable_record",
                parameters={
                    "vendor_name": "$steps.list_payables.result.payables[0].vendor_name",
                    "invoice_number": "$steps.list_payables.result.payables[0].invoice_number"
                },
                reasoning="Fetch specific record using data dynamically resolved from Step 1.",
                consequential=False
            )
        ]
    )

    executor = AutonomousExecutor(db_path=db_path, auto_approve=True)

    # Execute custom plan directly through executor
    res = executor.run_task(
        user_goal="Audit existing payables and retrieve specific record details",
        plan=custom_plan
    )

    assert res.status == TaskStatus.SUCCESSFUL
    assert len(res.traces) == 2
    # Verify Step 2 received the dynamically resolved arguments from Step 1
    step_2_trace = res.traces[1]
    assert step_2_trace.tool_name == "get_payable_record"
    assert step_2_trace.parameters["vendor_name"] == "Generic Cloud Corp"
    assert step_2_trace.parameters["invoice_number"] == "INV-CUSTOM-777"
    assert step_2_trace.result["exists"] is True
    assert step_2_trace.result["payable"]["amount"] == 888.00
