"""Domain models and Pydantic schemas for structured data validation."""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"


class InvoiceData(BaseModel):
    """Structured, validated invoice data extracted from raw source files."""
    invoice_number: str = Field(..., description="Unique invoice identifier")
    vendor_name: str = Field(..., description="Name of billing vendor")
    invoice_date: str = Field(..., description="Date invoice was issued (YYYY-MM-DD)")
    due_date: str = Field(..., description="Payment due date (YYYY-MM-DD)")
    total_amount: float = Field(..., gt=0, description="Total amount due, strictly positive")
    currency: str = Field(default="USD", description="Currency symbol or 3-letter code")
    purchase_order: Optional[str] = Field(default=None, description="PO Reference number")
    source_file: Optional[str] = Field(default=None, description="Filename or relative path")
    notes: Optional[str] = Field(default=None, description="Additional context or line item summary")

    @field_validator("invoice_number", "vendor_name", "due_date")
    @classmethod
    def not_empty_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class PayableRecord(BaseModel):
    """Payable system entry stored in SQLite."""
    id: Optional[int] = None
    invoice_number: str
    vendor_name: str
    amount: float
    due_date: str
    currency: str = "USD"
    status: str = "PENDING_PAYMENT"
    source_file: Optional[str] = None
    created_at: Optional[str] = None


class ActionStep(BaseModel):
    """Single step in an execution plan."""
    step_number: int = Field(..., ge=1, description="Sequential step index")
    tool_name: str = Field(..., description="Permitted tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to tool")
    reasoning: str = Field(..., description="Explicit rationale for calling this tool")
    consequential: bool = Field(default=False, description="Whether human approval is required before execution")


class ActionPlan(BaseModel):
    """Structured, validated plan before autonomous execution."""
    goal: str = Field(..., description="User's parsed high-level goal")
    steps: List[ActionStep] = Field(..., min_length=1, description="List of validated action steps")
    estimated_risk: str = Field(default="LOW", description="Risk assessment: LOW, MEDIUM, or HIGH")


class ExecutionTraceItem(BaseModel):
    """Granular trace item for every tool action attempt."""
    step_number: int
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    execution_time_ms: float = 0.0
    status: str = "PENDING"  # PENDING, EXECUTING, SUCCESS, FAILED, RETRIED, WAITING_APPROVAL
    timestamp: str


class VerificationEvidence(BaseModel):
    """Independent verification proof comparing database state to source invoice."""
    verified: bool = False
    invoice_found: bool = False
    payable_id: Optional[int] = None
    amount_matched: bool = False
    due_date_matched: bool = False
    vendor_matched: bool = False
    evidence_details: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class StepResult(BaseModel):
    """Structured container for intermediate step outputs accessible by subsequent steps."""
    step_number: int
    tool_name: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str


class ReplanAction(str, Enum):
    RETRY = "RETRY"
    SUBSTITUTE_STEP = "SUBSTITUTE_STEP"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    TERMINATE = "TERMINATE"


class ReplanDecision(BaseModel):
    """Structured decision output from the planner during failure recovery."""
    action: ReplanAction
    reasoning: str
    adjusted_step: Optional[ActionStep] = None
    new_steps: Optional[List[ActionStep]] = None
    clarification_prompt: Optional[str] = None
    error_message: Optional[str] = None


class TaskResult(BaseModel):
    """Complete lifecycle state of an autonomous task."""
    task_id: str
    user_query: str
    status: TaskStatus = TaskStatus.PENDING
    plan: Optional[ActionPlan] = None
    extracted_invoice: Optional[InvoiceData] = None
    payable_record: Optional[PayableRecord] = None
    verification: Optional[VerificationEvidence] = None
    traces: List[ExecutionTraceItem] = Field(default_factory=list)
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    replanning_count: int = 0
    summary: str = ""
    error_message: Optional[str] = None
    clarification_prompt: Optional[str] = None
