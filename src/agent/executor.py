"""Autonomous Task Executor with dynamic parameter resolution, retries, replanning, and verification."""
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.config import settings
from src.models import (
    TaskStatus,
    TaskResult,
    ActionPlan,
    ActionStep,
    ExecutionTraceItem,
    InvoiceData,
    PayableRecord,
    StepResult,
    ReplanAction,
    ReplanDecision,
    VerificationEvidence
)
from src.tools.base import ToolExecutionError, RecoverableToolError, PermissionDeniedError
from src.tools.registry import ToolRegistry, default_registry
from src.agent.planner import ActionPlanner
from src.agent.resolver import resolve_parameters
from src.agent.verifier import OutcomeVerifier
from src.database import save_task, get_task, init_db

# Maximum number of dynamic recovery replanning attempts per task execution
MAX_REPLANNING_ATTEMPTS = 2


class AutonomousExecutor:
    """Executes action plans with generic parameter resolution, retries, and dynamic replanning."""

    def __init__(
        self,
        planner: Optional[ActionPlanner] = None,
        verifier: Optional[OutcomeVerifier] = None,
        registry: Optional[ToolRegistry] = None,
        max_retries: Optional[int] = None,
        db_path: Optional[Path] = None,
        invoices_dir: Optional[Path] = None,
        auto_approve: Optional[bool] = None
    ):
        self.registry = registry or default_registry
        self.planner = planner or ActionPlanner(registry=self.registry)
        self.verifier = verifier or OutcomeVerifier(db_path=db_path)
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.db_path = db_path
        self.invoices_dir = invoices_dir
        self.auto_approve = auto_approve if auto_approve is not None else settings.auto_approve

        # Ensure database tables exist
        init_db(self.db_path)

    def run_task(
        self,
        user_goal: str,
        task_id: Optional[str] = None,
        plan: Optional[ActionPlan] = None,
        approved: bool = False,
        clarification_response: Optional[str] = None
    ) -> TaskResult:
        """Run an autonomous task lifecycle or resume an approved/clarified task."""
        # 1. Check if resuming an existing task
        existing_result: Optional[TaskResult] = None
        if task_id:
            existing_result = get_task(task_id, db_path=self.db_path)

        start_step_idx = 0
        if existing_result and existing_result.status in (TaskStatus.APPROVAL_REQUIRED, TaskStatus.CLARIFICATION_REQUIRED):
            task_result = existing_result

            # Resuming from User Clarification
            if clarification_response and clarification_response.strip():
                task_result.status = TaskStatus.IN_PROGRESS
                task_result.clarification_prompt = None
                task_result.error_message = None

                # Find the step that was pending or failed and ask planner to substitute it with user clarification
                failed_step = task_result.plan.steps[-1]
                for tr in reversed(task_result.traces):
                    if tr.status in ("FAILED", "CLARIFICATION_REQUIRED"):
                        match = next((s for s in task_result.plan.steps if s.step_number == tr.step_number), None)
                        if match:
                            failed_step = match
                        break

                decision = self.planner.replan(
                    user_goal=task_result.user_query,
                    plan=task_result.plan,
                    failed_step=failed_step,
                    error_context="User clarification received",
                    traces=task_result.traces,
                    attempt=1,
                    clarification_response=clarification_response
                )

                if decision.action == ReplanAction.SUBSTITUTE_STEP:
                    if decision.new_steps:
                        task_result.plan.steps = decision.new_steps
                        task_result.traces = []
                        task_result.step_results = {}
                        start_step_idx = 0
                    elif decision.adjusted_step:
                        step_idx = next((idx for idx, s in enumerate(task_result.plan.steps) if s.step_number == failed_step.step_number), None)
                        if step_idx is not None:
                            task_result.plan.steps[step_idx] = decision.adjusted_step

            # Resuming from Human Approval
            elif approved:
                task_result.status = TaskStatus.IN_PROGRESS
                task_result.error_message = None
        else:
            new_id = task_id or str(uuid.uuid4())[:8]
            task_result = TaskResult(
                task_id=new_id,
                user_query=user_goal,
                status=TaskStatus.IN_PROGRESS,
                traces=[]
            )
            if plan:
                task_result.plan = plan
            else:
                try:
                    task_result.plan = self.planner.plan_task(user_goal)
                except Exception as e:
                    task_result.status = TaskStatus.FAILED
                    task_result.error_message = f"Planning failed: {str(e)}"
                    task_result.summary = f"Task aborted during planning: {str(e)}"
                    save_task(task_result, db_path=self.db_path)
                    return task_result

            if task_result.plan:
                task_result.execution_mode = task_result.plan.execution_mode
                task_result.model_name = task_result.plan.model_name
                task_result.fallback_reason = task_result.plan.fallback_reason

        save_task(task_result, db_path=self.db_path)

        # 2. Reconstruct StepResult storage from prior traces if resuming
        if not task_result.step_results and task_result.traces:
            for tr in task_result.traces:
                if tr.status == "SUCCESS" and tr.result is not None:
                    sr = StepResult(
                        step_number=tr.step_number,
                        tool_name=tr.tool_name,
                        status=tr.status,
                        result=tr.result,
                        error=tr.error,
                        timestamp=tr.timestamp
                    )
                    task_result.step_results[str(tr.step_number)] = sr
                    task_result.step_results[f"step_{tr.step_number}"] = sr
                    task_result.step_results[tr.tool_name] = sr

        # Find starting step (if resuming from approval)
        start_step_idx = 0
        if existing_result:
            completed_steps = {t.step_number for t in existing_result.traces if t.status == "SUCCESS"}
            for i, step in enumerate(task_result.plan.steps):
                if step.step_number not in completed_steps:
                    start_step_idx = i
                    break

        # 3. Sequential Step Execution Loop with Generic Resolution and Replanning
        i = start_step_idx
        while i < len(task_result.plan.steps):
            step = task_result.plan.steps[i]

            # Resolve parameters generically using dynamic StepResult references
            bound_params = self._bind_parameters(step, task_result.step_results)

            # Check for Human Approval requirement
            if step.consequential and not self.auto_approve and not approved:
                task_result.status = TaskStatus.APPROVAL_REQUIRED
                approval_trace = ExecutionTraceItem(
                    step_number=step.step_number,
                    tool_name=step.tool_name,
                    parameters=bound_params,
                    status="WAITING_APPROVAL",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                task_result.traces.append(approval_trace)
                task_result.summary = (
                    f"Action paused for human approval: Step {step.step_number} is about to execute "
                    f"consequential action '{step.tool_name}'. Awaiting user confirmation."
                )
                save_task(task_result, db_path=self.db_path)
                return task_result

            # If user just approved this step, reset approved flag for any subsequent consequential steps
            if approved and step.consequential:
                approved = False

            # Execute step with retries and recovery replanning
            step_success = self._execute_step_with_retries(step, bound_params, task_result, clarification_response)
            if not step_success:
                # Task paused for clarification, aborted by replanner, or failed
                save_task(task_result, db_path=self.db_path)
                return task_result

            i += 1

        # 4. Independent Outcome Verification
        # Check if an invoice was extracted during execution
        if not task_result.extracted_invoice:
            for sr in task_result.step_results.values():
                if isinstance(sr.result, dict) and "invoice_number" in sr.result and "total_amount" in sr.result:
                    try:
                        task_result.extracted_invoice = InvoiceData(**sr.result)
                        break
                    except Exception:
                        pass

        if task_result.extracted_invoice:
            # Check if payable was recorded
            payable_id = None
            if "create_payable_record" in task_result.step_results:
                pay_res = task_result.step_results["create_payable_record"].result
                if isinstance(pay_res, dict):
                    payable_id = pay_res.get("payable_id")

            verification = self.verifier.verify_payable_outcome(
                invoice=task_result.extracted_invoice,
                payable_id=payable_id
            )
            task_result.verification = verification

            if verification.verified:
                task_result.status = TaskStatus.SUCCESSFUL
                task_result.summary = (
                    f"Task completed successfully and independently verified. "
                    f"Extracted invoice '{task_result.extracted_invoice.invoice_number}' from "
                    f"{task_result.extracted_invoice.vendor_name} for ${task_result.extracted_invoice.total_amount:.2f} "
                    f"(Due: {task_result.extracted_invoice.due_date}). "
                    f"Recorded in payable system under ID #{verification.payable_id}."
                )
            else:
                task_result.status = TaskStatus.FAILED
                task_result.error_message = verification.message
                task_result.summary = f"Task completed actions but FAILED independent verification: {verification.message}"
        else:
            # Generic task completion (non-payable task)
            task_result.status = TaskStatus.SUCCESSFUL
            task_result.summary = f"Task completed all {len(task_result.plan.steps)} steps successfully."

        save_task(task_result, db_path=self.db_path)
        return task_result

    def _bind_parameters(self, step: ActionStep, step_results: Dict[str, StepResult]) -> Dict[str, Any]:
        """Bind dynamic parameters from upstream step outputs using generic path references.

        Fully decoupled from any specific tool or invoice workflow.
        """
        # 1. Generic reference resolution ($steps.<selector>.result.<path>)
        params = resolve_parameters(step.parameters, step_results)

        # 2. Ambient environment configuration injections
        if self.invoices_dir and step.tool_name in ("search_invoices", "read_invoice"):
            if not params.get("directory"):
                params["directory"] = str(self.invoices_dir)

        if self.db_path and step.tool_name in ("create_payable_record", "get_payable_record", "list_payables"):
            if not params.get("db_path"):
                params["db_path"] = str(self.db_path)

        return params

    def _execute_step_with_retries(
        self,
        step: ActionStep,
        params: Dict[str, Any],
        task_result: TaskResult,
        clarification_response: Optional[str] = None
    ) -> bool:
        """Execute a single step with retry policy and dynamic replanning on failure."""
        retry_count = 0
        tool = self.registry.get(step.tool_name)

        while retry_count <= self.max_retries:
            start_time = time.time()
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = tool.run(**params)
                elapsed_ms = (time.time() - start_time) * 1000

                # Detect empty result failure conditions (e.g. search_invoices finding 0 matches)
                if step.tool_name == "search_invoices" and isinstance(result, dict) and result.get("count") == 0:
                    empty_err = f"No invoices found matching query: {params.get('vendor_name') or params.get('query')}"
                    return self._handle_step_failure(
                        step=step,
                        params=params,
                        error_str=empty_err,
                        elapsed_ms=elapsed_ms,
                        retry_count=retry_count,
                        task_result=task_result,
                        clarification_response=clarification_response
                    )

                # Record successful trace
                trace = ExecutionTraceItem(
                    step_number=step.step_number,
                    tool_name=step.tool_name,
                    parameters=params,
                    result=result,
                    error=None,
                    retry_count=retry_count,
                    execution_time_ms=round(elapsed_ms, 2),
                    status="SUCCESS",
                    timestamp=timestamp
                )
                task_result.traces.append(trace)

                # Store generic StepResult for subsequent step reference
                step_res = StepResult(
                    step_number=step.step_number,
                    tool_name=step.tool_name,
                    status="SUCCESS",
                    result=result,
                    error=None,
                    timestamp=timestamp
                )
                task_result.step_results[str(step.step_number)] = step_res
                task_result.step_results[f"step_{step.step_number}"] = step_res
                task_result.step_results[step.tool_name] = step_res

                # Opportunistic extraction check for UI metrics
                if isinstance(result, dict) and "invoice_number" in result and "total_amount" in result:
                    try:
                        task_result.extracted_invoice = InvoiceData(**result)
                    except Exception:
                        pass

                return True

            except RecoverableToolError as rte:
                elapsed_ms = (time.time() - start_time) * 1000
                if retry_count < self.max_retries:
                    retry_count += 1
                    trace = ExecutionTraceItem(
                        step_number=step.step_number,
                        tool_name=step.tool_name,
                        parameters=params,
                        result=None,
                        error=f"Recoverable error: {str(rte)} (Retrying {retry_count}/{self.max_retries})",
                        retry_count=retry_count,
                        execution_time_ms=round(elapsed_ms, 2),
                        status="RETRIED",
                        timestamp=timestamp
                    )
                    task_result.traces.append(trace)
                    time.sleep(0.05 * retry_count)
                    continue
                else:
                    # Max retries exceeded; pass to dynamic replanning
                    return self._handle_step_failure(
                        step=step,
                        params=params,
                        error_str=f"Max retries exceeded for tool '{step.tool_name}': {str(rte)}",
                        elapsed_ms=elapsed_ms,
                        retry_count=retry_count,
                        task_result=task_result,
                        clarification_response=clarification_response
                    )

            except ToolExecutionError as tee:
                elapsed_ms = (time.time() - start_time) * 1000
                return self._handle_step_failure(
                    step=step,
                    params=params,
                    error_str=str(tee),
                    elapsed_ms=elapsed_ms,
                    retry_count=retry_count,
                    task_result=task_result,
                    clarification_response=clarification_response
                )

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                return self._handle_step_failure(
                    step=step,
                    params=params,
                    error_str=f"Unexpected error: {str(e)}",
                    elapsed_ms=elapsed_ms,
                    retry_count=retry_count,
                    task_result=task_result,
                    clarification_response=clarification_response
                )

        return False

    def _handle_step_failure(
        self,
        step: ActionStep,
        params: Dict[str, Any],
        error_str: str,
        elapsed_ms: float,
        retry_count: int,
        task_result: TaskResult,
        clarification_response: Optional[str] = None
    ) -> bool:
        """Handle failure via dynamic recovery replanning (up to MAX_REPLANNING_ATTEMPTS)."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Log failure trace
        trace = ExecutionTraceItem(
            step_number=step.step_number,
            tool_name=step.tool_name,
            parameters=params,
            result=None,
            error=error_str,
            retry_count=retry_count,
            execution_time_ms=round(elapsed_ms, 2),
            status="FAILED",
            timestamp=timestamp
        )
        task_result.traces.append(trace)

        # Check if replanning can be attempted
        if task_result.replanning_count < MAX_REPLANNING_ATTEMPTS:
            task_result.replanning_count += 1

            decision: ReplanDecision = self.planner.replan(
                user_goal=task_result.user_query,
                plan=task_result.plan,
                failed_step=step,
                error_context=error_str,
                traces=task_result.traces,
                attempt=task_result.replanning_count,
                clarification_response=clarification_response
            )

            if decision.used_llm:
                task_result.llm_replanning_used = True

            # Option A: Ask User Clarification
            if decision.action == ReplanAction.ASK_CLARIFICATION:
                task_result.status = TaskStatus.CLARIFICATION_REQUIRED
                task_result.clarification_prompt = decision.clarification_prompt or error_str
                task_result.summary = f"Task paused: {task_result.clarification_prompt}"
                return False

            # Option B: Substitute with Adjusted Tool Step
            elif decision.action == ReplanAction.SUBSTITUTE_STEP and decision.adjusted_step:
                # Log replan intervention trace
                replan_trace = ExecutionTraceItem(
                    step_number=step.step_number,
                    tool_name="planner_recovery",
                    parameters={
                        "action": "SUBSTITUTE_STEP",
                        "reasoning": decision.reasoning,
                        "used_llm": decision.used_llm,
                        "model": decision.model_name
                    },
                    status="RETRIED",
                    result={"substituted_tool": decision.adjusted_step.tool_name},
                    error=None,
                    retry_count=task_result.replanning_count,
                    execution_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                task_result.traces.append(replan_trace)

                # Bind new parameters and execute substituted step
                adj_step = decision.adjusted_step
                new_params = self._bind_parameters(adj_step, task_result.step_results)
                return self._execute_step_with_retries(adj_step, new_params, task_result, clarification_response)

            # Option C: Replan suggests Retry
            elif decision.action == ReplanAction.RETRY and decision.adjusted_step:
                new_params = self._bind_parameters(decision.adjusted_step, task_result.step_results)
                return self._execute_step_with_retries(decision.adjusted_step, new_params, task_result, clarification_response)

            # Option D: Terminate
            else:
                task_result.status = TaskStatus.FAILED
                task_result.error_message = decision.error_message or error_str
                task_result.summary = f"Task failed at step {step.step_number} ({step.tool_name}): {task_result.error_message}"
                return False

        # Max replanning limit reached
        task_result.status = TaskStatus.FAILED
        task_result.error_message = f"Max replanning limit reached ({MAX_REPLANNING_ATTEMPTS}): {error_str}"
        task_result.summary = f"Task failed after recovery attempts: {error_str}"
        return False
