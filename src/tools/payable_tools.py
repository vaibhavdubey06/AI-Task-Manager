"""Payable tools for interacting with the company accounts payable database."""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.models import PayableRecord
from src.database import (
    insert_payable,
    get_payable_by_vendor_and_invoice,
    list_payables,
    DuplicatePayableError,
)
from src.tools.base import BaseTool, ToolExecutionError


from pathlib import Path

class CreatePayableInput(BaseModel):
    invoice_number: str = Field(..., description="Invoice identifier (e.g. INV-2024-002)")
    vendor_name: str = Field(..., description="Full legal name of the vendor")
    amount: float = Field(..., gt=0, description="Total amount payable")
    due_date: str = Field(..., description="Payment due date (YYYY-MM-DD)")
    currency: str = Field(default="USD", description="Currency code")
    source_file: Optional[str] = Field(default=None, description="Source invoice file path or name")
    db_path: Optional[str] = Field(default=None, description="Custom database path")


class CreatePayableTool(BaseTool):
    name = "create_payable_record"
    description = (
        "Enters an invoice into the company accounts payable database. "
        "CONSEQUENTIAL ACTION: Financial state change requiring user approval. "
        "Strictly enforces duplicate prevention."
    )
    consequential = True
    input_schema = CreatePayableInput

    def _execute(self, args: CreatePayableInput) -> Dict[str, Any]:
        record = PayableRecord(
            invoice_number=args.invoice_number,
            vendor_name=args.vendor_name,
            amount=args.amount,
            due_date=args.due_date,
            currency=args.currency,
            source_file=args.source_file,
            status="PENDING_PAYMENT"
        )
        try:
            target_db = Path(args.db_path) if args.db_path else None
            created = insert_payable(record, db_path=target_db)
            return {
                "success": True,
                "payable_id": created.id,
                "invoice_number": created.invoice_number,
                "vendor_name": created.vendor_name,
                "amount": created.amount,
                "due_date": created.due_date,
                "currency": created.currency,
                "status": created.status,
                "created_at": created.created_at,
                "message": f"Successfully created payable record ID #{created.id} for {created.vendor_name}"
            }
        except DuplicatePayableError as e:
            raise ToolExecutionError(str(e))
        except Exception as e:
            raise ToolExecutionError(f"Database insertion failed: {str(e)}")


class GetPayableInput(BaseModel):
    vendor_name: str = Field(..., description="Vendor name")
    invoice_number: str = Field(..., description="Invoice number")
    db_path: Optional[str] = Field(default=None, description="Custom database path")


class GetPayableTool(BaseTool):
    name = "get_payable_record"
    description = "Queries the company database to check if a payable record already exists for a vendor and invoice."
    consequential = False
    input_schema = GetPayableInput

    def _execute(self, args: GetPayableInput) -> Dict[str, Any]:
        target_db = Path(args.db_path) if args.db_path else None
        record = get_payable_by_vendor_and_invoice(args.vendor_name, args.invoice_number, db_path=target_db)
        if not record:
            return {
                "exists": False,
                "payable": None,
                "message": f"No payable record found for vendor '{args.vendor_name}' and invoice '{args.invoice_number}'"
            }
        return {
            "exists": True,
            "payable": record.model_dump(),
            "message": f"Found existing payable record ID #{record.id}"
        }


class ListPayablesInput(BaseModel):
    limit: int = Field(default=20, ge=1, le=100, description="Max records to retrieve")
    db_path: Optional[str] = Field(default=None, description="Custom database path")


class ListPayablesTool(BaseTool):
    name = "list_payables"
    description = "Lists recent accounts payable entries from the database."
    consequential = False
    input_schema = ListPayablesInput

    def _execute(self, args: ListPayablesInput) -> Dict[str, Any]:
        target_db = Path(args.db_path) if args.db_path else None
        records = list_payables(limit=args.limit, db_path=target_db)
        return {
            "count": len(records),
            "payables": [r.model_dump() for r in records]
        }
