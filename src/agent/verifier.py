"""Independent outcome verification comparing SQLite database state against source invoice."""
from pathlib import Path
from typing import Optional, Dict, Any
from src.models import InvoiceData, VerificationEvidence, PayableRecord
from src.database import get_payable_by_id, get_payable_by_vendor_and_invoice


class OutcomeVerifier:
    """Verifies that the payable system record matches the source invoice data."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def verify_payable_outcome(
        self,
        invoice: InvoiceData,
        payable_id: Optional[int] = None
    ) -> VerificationEvidence:
        """Independently query SQLite database and cross-check all financial attributes."""
        # 1. Fetch actual DB record
        record: Optional[PayableRecord] = None
        if payable_id is not None:
            record = get_payable_by_id(payable_id, db_path=self.db_path)

        if not record:
            record = get_payable_by_vendor_and_invoice(
                invoice.vendor_name, invoice.invoice_number, db_path=self.db_path
            )

        if not record:
            return VerificationEvidence(
                verified=False,
                invoice_found=False,
                payable_id=None,
                amount_matched=False,
                due_date_matched=False,
                vendor_matched=False,
                evidence_details={"reason": "No matching payable record found in SQLite database"},
                message=f"Verification failed: Payable record for '{invoice.vendor_name}' ({invoice.invoice_number}) was not found in the database."
            )

        # 2. Check each attribute independently
        amount_diff = abs(float(record.amount) - float(invoice.total_amount))
        amount_matched = amount_diff < 0.005

        due_date_matched = record.due_date.strip() == invoice.due_date.strip()

        # Vendor name normalization check
        norm_rec_vendor = record.vendor_name.lower().strip()
        norm_inv_vendor = invoice.vendor_name.lower().strip()
        vendor_matched = (norm_rec_vendor == norm_inv_vendor) or (norm_inv_vendor in norm_rec_vendor) or (norm_rec_vendor in norm_inv_vendor)

        num_matched = record.invoice_number.strip() == invoice.invoice_number.strip()

        all_matched = amount_matched and due_date_matched and vendor_matched and num_matched

        evidence = {
            "database_payable_id": record.id,
            "database_invoice_number": record.invoice_number,
            "source_invoice_number": invoice.invoice_number,
            "database_vendor": record.vendor_name,
            "source_vendor": invoice.vendor_name,
            "database_amount": record.amount,
            "source_amount": invoice.total_amount,
            "amount_difference": round(amount_diff, 4),
            "database_due_date": record.due_date,
            "source_due_date": invoice.due_date,
            "database_status": record.status,
            "database_created_at": record.created_at,
            "checks": {
                "invoice_number": "MATCH" if num_matched else "MISMATCH",
                "vendor_name": "MATCH" if vendor_matched else "MISMATCH",
                "amount": "MATCH" if amount_matched else "MISMATCH",
                "due_date": "MATCH" if due_date_matched else "MISMATCH"
            }
        }

        if all_matched:
            msg = (
                f"Independent verification PASSED: Database record #{record.id} matches source invoice "
                f"({invoice.invoice_number}) exactly: Amount ${record.amount:.2f}, Due Date {record.due_date}, Vendor '{record.vendor_name}'."
            )
        else:
            mismatches = []
            if not num_matched: mismatches.append(f"Invoice Number ('{record.invoice_number}' vs '{invoice.invoice_number}')")
            if not vendor_matched: mismatches.append(f"Vendor ('{record.vendor_name}' vs '{invoice.vendor_name}')")
            if not amount_matched: mismatches.append(f"Amount (${record.amount:.2f} vs ${invoice.total_amount:.2f})")
            if not due_date_matched: mismatches.append(f"Due Date ({record.due_date} vs {invoice.due_date})")
            msg = f"Independent verification FAILED: Mismatches detected in {', '.join(mismatches)}."

        return VerificationEvidence(
            verified=all_matched,
            invoice_found=True,
            payable_id=record.id,
            amount_matched=amount_matched,
            due_date_matched=due_date_matched,
            vendor_matched=vendor_matched,
            evidence_details=evidence,
            message=msg
        )
