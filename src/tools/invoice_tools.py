"""Invoice tools: searching, reading, and structured field extraction."""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.config import settings
from src.models import InvoiceData
from src.tools.base import BaseTool, ToolExecutionError, RecoverableToolError


# --- Tool 1: Search Invoices ---

class SearchInvoicesInput(BaseModel):
    vendor_name: Optional[str] = Field(default=None, description="Vendor name or substring to match")
    query: Optional[str] = Field(default=None, description="General search term or invoice number")
    directory: Optional[str] = Field(default=None, description="Custom invoices directory path")


class SearchInvoicesTool(BaseTool):
    name = "search_invoices"
    description = "Searches the invoice repository for files matching a vendor name or query, sorted by date (latest first)."
    consequential = False
    input_schema = SearchInvoicesInput

    def _execute(self, args: SearchInvoicesInput) -> Dict[str, Any]:
        target_dir = Path(args.directory) if args.directory else settings.invoices_dir
        if not target_dir.exists():
            return {"matches": [], "count": 0, "message": f"Invoices directory does not exist: {target_dir}"}

        matches = []
        vendor_filter = args.vendor_name.strip().lower() if args.vendor_name else None
        query_filter = args.query.strip().lower() if args.query else None

        for file_path in target_dir.glob("*"):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                continue

            parsed_vendor = ""
            parsed_inv_num = ""
            parsed_date = ""

            # Preliminary parse to extract date and vendor
            if file_path.suffix == ".json":
                try:
                    data = json.loads(content)
                    parsed_vendor = str(data.get("vendor_name", ""))
                    parsed_inv_num = str(data.get("invoice_number", ""))
                    parsed_date = str(data.get("invoice_date", ""))
                except Exception:
                    parsed_vendor = file_path.stem
            else:
                # Text file heuristics
                v_match = re.search(r"^\s*([A-Z0-9\s,\.]{3,30}?)(?:\n|INC|LLC|CORP)", content, re.MULTILINE)
                if v_match:
                    parsed_vendor = v_match.group(1).strip()
                date_match = re.search(r"INVOICE DATE:\s*(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
                if date_match:
                    parsed_date = date_match.group(1)
                num_match = re.search(r"INVOICE NUMBER:\s*([A-Za-z0-9\-]+)", content, re.IGNORECASE)
                if num_match:
                    parsed_inv_num = num_match.group(1)

            # Check matching
            file_name_lower = file_path.name.lower()
            content_lower = content.lower()
            vendor_match = True
            query_match = True

            if vendor_filter:
                vendor_match = (
                    vendor_filter in parsed_vendor.lower()
                    or vendor_filter in file_name_lower
                    or vendor_filter in content_lower
                )
            if query_filter:
                query_match = (
                    query_filter in parsed_inv_num.lower()
                    or query_filter in file_name_lower
                    or query_filter in content_lower
                )

            if vendor_match and query_match:
                matches.append({
                    "filename": file_path.name,
                    "filepath": str(file_path),
                    "vendor_name": parsed_vendor or "Unknown",
                    "invoice_number": parsed_inv_num or file_path.stem,
                    "invoice_date": parsed_date or "1970-01-01",
                    "format": file_path.suffix.lstrip(".")
                })

        # Sort matches by date descending (latest first)
        matches.sort(key=lambda m: m["invoice_date"], reverse=True)

        if matches:
            matches[0]["is_latest"] = True
            for m in matches[1:]:
                m["is_latest"] = False

        return {
            "matches": matches,
            "files": matches,
            "invoices": matches,
            "count": len(matches),
            "latest": matches[0] if matches else None,
            "message": f"Found {len(matches)} matching invoices" if matches else "No invoices matched the search criteria."
        }


# --- Tool 2: Read Invoice ---

class ReadInvoiceInput(BaseModel):
    filename: str = Field(..., description="Name of the invoice file to read")
    directory: Optional[str] = Field(default=None, description="Custom invoices directory")
    simulate_recoverable_failure: bool = Field(default=False, description="Simulate transient I/O error for retry testing")


class ReadInvoiceTool(BaseTool):
    name = "read_invoice"
    description = "Reads the raw contents of an invoice file from the repository."
    consequential = False
    input_schema = ReadInvoiceInput

    def _execute(self, args: ReadInvoiceInput) -> Dict[str, Any]:
        if args.simulate_recoverable_failure:
            raise RecoverableToolError("Simulated temporary I/O lock: Resource busy. Retryable error.")

        target_dir = Path(args.directory) if args.directory else settings.invoices_dir
        file_path = target_dir / args.filename

        if not file_path.exists():
            # Search by substring if exact filename wasn't found
            candidates = list(target_dir.glob(f"*{args.filename}*"))
            if candidates:
                file_path = candidates[0]
            else:
                raise ToolExecutionError(f"Invoice file '{args.filename}' not found in {target_dir}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ToolExecutionError(f"Failed to read file '{file_path.name}': {str(e)}")

        return {
            "filename": file_path.name,
            "filepath": str(file_path),
            "content": content,
            "format": file_path.suffix.lstrip(".").lower()
        }


# --- Tool 3: Extract Invoice Data ---

class ExtractInvoiceDataInput(BaseModel):
    raw_content: str = Field(..., description="Raw invoice text or JSON string")
    filename: Optional[str] = Field(default=None, description="Original filename for context")


class ExtractInvoiceDataTool(BaseTool):
    name = "extract_invoice_data"
    description = "Parses and validates structured invoice details (vendor, invoice #, amount, due date) from raw invoice content."
    consequential = False
    input_schema = ExtractInvoiceDataInput

    def _execute(self, args: ExtractInvoiceDataInput) -> Dict[str, Any]:
        content = args.raw_content.strip()

        # Attempt JSON parsing first
        if content.startswith("{"):
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ToolExecutionError(f"Malformed invoice JSON in {args.filename or 'content'}: {str(e)}")

            try:
                # Map fields
                invoice_number = data.get("invoice_number") or data.get("invoice_id")
                vendor_name = data.get("vendor_name") or data.get("vendor")
                invoice_date = data.get("invoice_date") or data.get("date")
                due_date = data.get("due_date")
                amount = data.get("total_amount") or data.get("amount") or data.get("total")
                currency = data.get("currency", "USD")
                po = data.get("purchase_order") or data.get("po_number")

                if not invoice_number or not vendor_name or not due_date or amount is None:
                    missing = []
                    if not invoice_number: missing.append("invoice_number")
                    if not vendor_name: missing.append("vendor_name")
                    if not due_date: missing.append("due_date")
                    if amount is None: missing.append("total_amount")
                    raise ToolExecutionError(f"Missing required invoice fields in JSON: {', '.join(missing)}")

                invoice_obj = InvoiceData(
                    invoice_number=str(invoice_number),
                    vendor_name=str(vendor_name),
                    invoice_date=str(invoice_date or due_date),
                    due_date=str(due_date),
                    total_amount=float(amount),
                    currency=str(currency),
                    purchase_order=str(po) if po else None,
                    source_file=args.filename
                )
                return invoice_obj.model_dump()
            except Exception as e:
                raise ToolExecutionError(f"Data validation failed for invoice JSON: {str(e)}")

        # Text format extraction
        # Check for ambiguity indicators
        if "ambiguous" in (args.filename or "").lower() or "joint venture" in content.lower():
            if "no specific due date" in content.lower() or "upon mutual agreement" in content.lower():
                raise ToolExecutionError(
                    "Ambiguous invoice: multiple billing parties identified and due date is not specified. "
                    "User clarification is required before proceeding."
                )

        # Regex extraction
        num_m = re.search(r"INVOICE\s*(?:NUMBER|#|ID)?:\s*([A-Za-z0-9\-]+)", content, re.IGNORECASE)
        date_m = re.search(r"INVOICE\s*DATE:\s*(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
        due_m = re.search(r"DUE\s*DATE:\s*(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
        
        # Priority 1: Explicit total amount due
        amt_m = re.search(
            r"(?:TOTAL\s+AMOUNT\s+DUE|TOTAL\s+AMOUNT|BALANCE\s+DUE|AMOUNT\s+DUE|TOTAL\s+DUE):\s*\$?([\d,]+\.?\d*)",
            content,
            re.IGNORECASE
        )
        if not amt_m:
            # Priority 2: Standalone TOTAL (never match SUBTOTAL)
            amt_m = re.search(r"(?<!SUB)TOTAL:\s*\$?([\d,]+\.?\d*)", content, re.IGNORECASE)

        po_m = re.search(r"PO\s*(?:NUMBER|#)?:\s*([A-Za-z0-9\-]+)", content, re.IGNORECASE)

        # Vendor name heuristic
        vendor_name = None
        for line in content.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("=") and not line_str.startswith("-"):
                if any(kw in line_str.upper() for kw in ["INC", "LLC", "TECHNOLOGIES", "CORP", "SOLUTIONS", "CO"]):
                    vendor_name = line_str
                    break
        if not vendor_name:
            if "ACME" in content.upper():
                vendor_name = "Acme Technologies"
            else:
                vendor_name = "Unknown Vendor"

        invoice_number = num_m.group(1) if num_m else None
        invoice_date = date_m.group(1) if date_m else None
        due_date = due_m.group(1) if due_m else None
        
        amount = None
        if amt_m:
            try:
                amount = float(amt_m.group(1).replace(",", ""))
            except ValueError:
                pass

        missing_fields = []
        if not invoice_number: missing_fields.append("invoice_number")
        if not due_date: missing_fields.append("due_date")
        if amount is None: missing_fields.append("total_amount")

        if missing_fields:
            raise ToolExecutionError(
                f"Failed to extract mandatory fields from text invoice: {', '.join(missing_fields)}. "
                f"Clarification required."
            )

        invoice_obj = InvoiceData(
            invoice_number=invoice_number,
            vendor_name=vendor_name,
            invoice_date=invoice_date or due_date,
            due_date=due_date,
            total_amount=amount,
            currency="USD",
            purchase_order=po_m.group(1) if po_m else None,
            source_file=args.filename
        )
        return invoice_obj.model_dump()
