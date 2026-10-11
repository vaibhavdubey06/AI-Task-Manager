"""SQLite persistent storage for accounts payable, tasks, and execution traces."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import settings
from src.models import PayableRecord, TaskResult, ExecutionTraceItem, TaskStatus, InvoiceData, ActionPlan, VerificationEvidence


class DatabaseError(Exception):
    """Base exception for database failures."""
    pass


class DuplicatePayableError(DatabaseError):
    """Raised when attempting to insert a payable record that already exists."""
    pass


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    path = custom_path or settings.database_path
    if isinstance(path, str):
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables with strict schema and unique constraints."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Accounts Payable table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                amount REAL NOT NULL,
                due_date TEXT NOT NULL,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'PENDING_PAYMENT',
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(vendor_name, invoice_number)
            )
        """)

        # 2. Task lifecycle history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                user_query TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT,
                plan_json TEXT,
                extracted_invoice_json TEXT,
                verification_json TEXT,
                error_message TEXT,
                clarification_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Execution traces
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                parameters_json TEXT,
                result_json TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                execution_time_ms REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def insert_payable(record: PayableRecord, db_path: Optional[Path] = None) -> PayableRecord:
    """Insert a new payable record with duplicate prevention."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        v_low = record.vendor_name.lower().strip()
        # Check for duplicate
        cursor.execute("""
            SELECT id FROM payables 
            WHERE (LOWER(vendor_name) = ? OR LOWER(vendor_name) LIKE ? OR ? LIKE '%' || LOWER(vendor_name) || '%')
              AND invoice_number = ?
        """, (v_low, f"%{v_low}%", v_low, record.invoice_number))
        existing = cursor.fetchone()
        if existing:
            raise DuplicatePayableError(
                f"Duplicate payable detected: Invoice '{record.invoice_number}' for vendor '{record.vendor_name}' "
                f"already exists with ID {existing['id']}."
            )

        try:
            cursor.execute("""
                INSERT INTO payables (invoice_number, vendor_name, amount, due_date, currency, status, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.invoice_number,
                record.vendor_name,
                record.amount,
                record.due_date,
                record.currency,
                record.status,
                record.source_file
            ))
            conn.commit()
            record_id = cursor.lastrowid
            
            cursor.execute("SELECT created_at FROM payables WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            created_at = row["created_at"] if row else datetime.now(timezone.utc).isoformat()
            
            record.id = record_id
            record.created_at = created_at
            return record
        except sqlite3.IntegrityError as e:
            raise DuplicatePayableError(f"Database constraint violation: {e}")


def get_payable_by_vendor_and_invoice(
    vendor_name: str, invoice_number: str, db_path: Optional[Path] = None
) -> Optional[PayableRecord]:
    """Retrieve payable record by vendor and invoice number with fuzzy entity matching."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        v_low = vendor_name.lower().strip()
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, amount, due_date, currency, status, source_file, created_at
            FROM payables
            WHERE (LOWER(vendor_name) = ? OR LOWER(vendor_name) LIKE ? OR ? LIKE '%' || LOWER(vendor_name) || '%')
              AND invoice_number = ?
        """, (v_low, f"%{v_low}%", v_low, invoice_number))
        row = cursor.fetchone()
        if not row:
            return None
        return PayableRecord(
            id=row["id"],
            invoice_number=row["invoice_number"],
            vendor_name=row["vendor_name"],
            amount=row["amount"],
            due_date=row["due_date"],
            currency=row["currency"],
            status=row["status"],
            source_file=row["source_file"],
            created_at=row["created_at"]
        )


def get_payable_by_id(payable_id: int, db_path: Optional[Path] = None) -> Optional[PayableRecord]:
    """Retrieve payable record by primary key."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, amount, due_date, currency, status, source_file, created_at
            FROM payables WHERE id = ?
        """, (payable_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return PayableRecord(
            id=row["id"],
            invoice_number=row["invoice_number"],
            vendor_name=row["vendor_name"],
            amount=row["amount"],
            due_date=row["due_date"],
            currency=row["currency"],
            status=row["status"],
            source_file=row["source_file"],
            created_at=row["created_at"]
        )


def list_payables(limit: int = 50, db_path: Optional[Path] = None) -> List[PayableRecord]:
    """List most recent payable entries."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, amount, due_date, currency, status, source_file, created_at
            FROM payables ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [
            PayableRecord(
                id=r["id"],
                invoice_number=r["invoice_number"],
                vendor_name=r["vendor_name"],
                amount=r["amount"],
                due_date=r["due_date"],
                currency=r["currency"],
                status=r["status"],
                source_file=r["source_file"],
                created_at=r["created_at"]
            )
            for r in rows
        ]


def save_task(task_result: TaskResult, db_path: Optional[Path] = None) -> None:
    """Save or update task execution result."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        plan_json = task_result.plan.model_dump_json() if task_result.plan else None
        extracted_invoice_json = task_result.extracted_invoice.model_dump_json() if task_result.extracted_invoice else None
        verification_json = task_result.verification.model_dump_json() if task_result.verification else None

        cursor.execute("""
            INSERT INTO tasks (
                task_id, user_query, status, summary, plan_json,
                extracted_invoice_json, verification_json, error_message, clarification_prompt, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(task_id) DO UPDATE SET
                status = excluded.status,
                summary = excluded.summary,
                plan_json = excluded.plan_json,
                extracted_invoice_json = excluded.extracted_invoice_json,
                verification_json = excluded.verification_json,
                error_message = excluded.error_message,
                clarification_prompt = excluded.clarification_prompt,
                updated_at = CURRENT_TIMESTAMP
        """, (
            task_result.task_id,
            task_result.user_query,
            task_result.status.value,
            task_result.summary,
            plan_json,
            extracted_invoice_json,
            verification_json,
            task_result.error_message,
            task_result.clarification_prompt
        ))

        # Save traces
        cursor.execute("DELETE FROM execution_traces WHERE task_id = ?", (task_result.task_id,))
        for trace in task_result.traces:
            cursor.execute("""
                INSERT INTO execution_traces (
                    task_id, step_number, tool_name, parameters_json, result_json,
                    error, retry_count, execution_time_ms, status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_result.task_id,
                trace.step_number,
                trace.tool_name,
                json.dumps(trace.parameters),
                json.dumps(trace.result) if trace.result is not None else None,
                trace.error,
                trace.retry_count,
                trace.execution_time_ms,
                trace.status,
                trace.timestamp
            ))
        conn.commit()


def get_task(task_id: str, db_path: Optional[Path] = None) -> Optional[TaskResult]:
    """Retrieve full task record with execution traces."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        plan = ActionPlan.model_validate_json(row["plan_json"]) if row["plan_json"] else None
        extracted = InvoiceData.model_validate_json(row["extracted_invoice_json"]) if row["extracted_invoice_json"] else None
        verification = VerificationEvidence.model_validate_json(row["verification_json"]) if row["verification_json"] else None

        cursor.execute("SELECT * FROM execution_traces WHERE task_id = ? ORDER BY step_number ASC, id ASC", (task_id,))
        trace_rows = cursor.fetchall()
        traces = [
            ExecutionTraceItem(
                step_number=tr["step_number"],
                tool_name=tr["tool_name"],
                parameters=json.loads(tr["parameters_json"]) if tr["parameters_json"] else {},
                result=json.loads(tr["result_json"]) if tr["result_json"] else None,
                error=tr["error"],
                retry_count=tr["retry_count"],
                execution_time_ms=tr["execution_time_ms"],
                status=tr["status"],
                timestamp=tr["timestamp"]
            )
            for tr in trace_rows
        ]

        step_results = {}
        for tr in traces:
            if tr.status == "SUCCESS" and tr.result is not None:
                from src.models import StepResult
                sr = StepResult(
                    step_number=tr.step_number,
                    tool_name=tr.tool_name,
                    status=tr.status,
                    result=tr.result,
                    error=tr.error,
                    timestamp=tr.timestamp
                )
                step_results[str(tr.step_number)] = sr
                step_results[f"step_{tr.step_number}"] = sr
                step_results[tr.tool_name] = sr

        execution_mode = plan.execution_mode if plan else "DETERMINISTIC_FALLBACK"
        model_name = plan.model_name if plan else None
        fallback_reason = plan.fallback_reason if plan else None
        llm_replanning_used = any(
            t.tool_name == "planner_recovery" and t.parameters.get("used_llm") is True
            for t in traces
        )

        return TaskResult(
            task_id=row["task_id"],
            user_query=row["user_query"],
            status=TaskStatus(row["status"]),
            plan=plan,
            execution_mode=execution_mode,
            model_name=model_name,
            llm_replanning_used=llm_replanning_used,
            fallback_reason=fallback_reason,
            extracted_invoice=extracted,
            verification=verification,
            traces=traces,
            step_results=step_results,
            summary=row["summary"] or "",
            error_message=row["error_message"],
            clarification_prompt=row["clarification_prompt"]
        )


def reset_demo_environment(db_path: Optional[Path] = None) -> None:
    """Clear tasks, execution traces, and payables from SQLite to reset demo state."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM execution_traces")
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM payables")
        conn.commit()


def list_recent_tasks(limit: int = 20, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List recent tasks overview."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT task_id, user_query, status, summary, created_at, updated_at
            FROM tasks ORDER BY updated_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
