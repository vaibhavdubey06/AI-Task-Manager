"""Tests for permitted tools, schemas, and sandbox enforcement."""
import pytest
from src.tools.invoice_tools import SearchInvoicesTool, ReadInvoiceTool, ExtractInvoiceDataTool
from src.tools.payable_tools import CreatePayableTool, GetPayableTool
from src.tools.base import ToolExecutionError, RecoverableToolError, PermissionDeniedError
from src.tools.registry import create_default_registry


def test_search_invoices_finds_latest_acme(temp_env):
    tool = SearchInvoicesTool()
    result = tool.run(vendor_name="Acme Technologies", directory=str(temp_env["invoices_dir"]))
    assert result["count"] >= 2
    assert result["latest"] is not None
    # INV-2024-002 is dated 2024-10-01 which is newer than INV-2024-001 (2024-09-15)
    assert result["latest"]["invoice_number"] == "INV-2024-002"
    assert result["latest"]["is_latest"] is True


def test_read_invoice_content(temp_env):
    tool = ReadInvoiceTool()
    result = tool.run(filename="INV-2024-001_Acme_Technologies.json", directory=str(temp_env["invoices_dir"]))
    assert "INV-2024-001" in result["content"]
    assert result["format"] == "json"


def test_read_invoice_missing_file_fails(temp_env):
    tool = ReadInvoiceTool()
    with pytest.raises(ToolExecutionError) as exc_info:
        tool.run(filename="non_existent_file_9999.json", directory=str(temp_env["invoices_dir"]))
    assert "not found" in str(exc_info.value).lower()


def test_read_invoice_recoverable_failure():
    tool = ReadInvoiceTool()
    with pytest.raises(RecoverableToolError) as exc_info:
        tool.run(filename="any.json", simulate_recoverable_failure=True)
    assert "retryable" in str(exc_info.value).lower()


def test_extract_invoice_data_from_json():
    tool = ExtractInvoiceDataTool()
    json_content = """{
        "invoice_number": "INV-100",
        "vendor_name": "Test Vendor",
        "invoice_date": "2024-10-01",
        "due_date": "2024-10-31",
        "total_amount": 500.00
    }"""
    extracted = tool.run(raw_content=json_content, filename="test.json")
    assert extracted["invoice_number"] == "INV-100"
    assert extracted["total_amount"] == 500.00
    assert extracted["due_date"] == "2024-10-31"


def test_extract_invoice_data_malformed_json_fails():
    tool = ExtractInvoiceDataTool()
    corrupted_json = '{"invoice_number": "INV-404", missing_quote: true}'
    with pytest.raises(ToolExecutionError) as exc_info:
        tool.run(raw_content=corrupted_json, filename="corrupted.json")
    assert "malformed invoice json" in str(exc_info.value).lower()


def test_extract_invoice_ambiguous_vendor_flags_clarification():
    tool = ExtractInvoiceDataTool()
    ambiguous_text = "Parties: Joint venture billing between Alpha Logistics and Beta Partners LLC. No specific due date specified."
    with pytest.raises(ToolExecutionError) as exc_info:
        tool.run(raw_content=ambiguous_text, filename="INV-2024-005_Ambiguous_Vendor.txt")
    assert "clarification is required" in str(exc_info.value).lower()


def test_tool_registry_sandbox_blocks_unauthorized_tools():
    registry = create_default_registry()
    with pytest.raises(PermissionDeniedError) as exc_info:
        registry.get("execute_arbitrary_shell_command")
    assert "strictly forbidden" in str(exc_info.value).lower()

    with pytest.raises(PermissionDeniedError):
        registry.get("eval_python_code")
