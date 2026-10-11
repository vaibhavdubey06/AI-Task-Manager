"""Structured action planner with Pydantic validation and strict tool verification."""
import json
import logging
import re
from typing import Optional, Dict, Any, List
from pydantic import ValidationError

from src.models import ActionPlan, ActionStep, ReplanAction, ReplanDecision, ExecutionTraceItem
from src.tools.registry import ToolRegistry, default_registry
from src.llm_client import LLMClient, LLMUnavailableError

logger = logging.getLogger(__name__)


class PlanValidationError(Exception):
    """Raised when an action plan fails structure or safety verification."""
    pass


class ActionPlanner:
    """Generates and validates structured plans for task goals."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        registry: Optional[ToolRegistry] = None
    ):
        self.llm_client = llm_client or LLMClient()
        self.registry = registry or default_registry

    def plan_task(self, user_goal: str) -> ActionPlan:
        """Create a validated ActionPlan using LLM if available, or deterministic planner."""
        if not user_goal or not user_goal.strip():
            raise PlanValidationError("Task description cannot be empty.")

        if self.llm_client.is_available():
            try:
                plan = self._plan_with_llm(user_goal)
                plan.execution_mode = "LLM_PLANNING"
                plan.model_name = self.llm_client.model
                plan.fallback_reason = None
                return plan
            except Exception as e:
                logger.warning(f"LLM planning failed ({e}), falling back to deterministic planner")
                return self._plan_deterministic(user_goal, fallback_reason=f"LLM API failure: {str(e)}")
        else:
            reason = "OPENAI_API_KEY / GROQ_API_KEY unavailable or unconfigured"
            return self._plan_deterministic(user_goal, fallback_reason=reason)

    def _plan_with_llm(self, user_goal: str) -> ActionPlan:
        """Prompt OpenAI-compatible API to generate a structured JSON plan."""
        tools_info = self.registry.list_tools()
        system_prompt = f"""You are an autonomous AI Task Planning Agent.
Given a user's objective, generate a structured, sequential action plan using ONLY the permitted tools.

PERMITTED TOOLS AND SCHEMAS:
{json.dumps(tools_info, indent=2)}

STRICT SAFETY RULES:
1. You MUST NEVER use or output arbitrary Python code, bash scripts, or unapproved tools.
2. For database insertions or financial operations ('create_payable_record'), mark 'consequential': true.
3. Every step must have: step_number (int starting at 1), tool_name (must exist in permitted tools), parameters (object), reasoning (string), consequential (boolean).
4. DATA FLOW REFERENCES: To pass output from an earlier step into a subsequent step, use dynamic path references:
   "$steps.<tool_name_or_number>.result.<field_path>"
   Example: {{"filename": "$steps.search_invoices.result.latest.filename"}}
   Example: {{"amount": "$steps.extract_invoice_data.result.total_amount"}}
5. Return ONLY a valid JSON object matching the following schema:
{{
  "goal": "{user_goal}",
  "estimated_risk": "LOW" or "MEDIUM" or "HIGH",
  "steps": [
    {{
      "step_number": 1,
      "tool_name": "permitted_tool_name",
      "parameters": {{}},
      "reasoning": "explicit explanation",
      "consequential": false
    }}
  ]
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a structured execution plan for: '{user_goal}'"}
        ]

        response_text = self.llm_client.chat_completion(
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        try:
            plan = ActionPlan.model_validate_json(response_text)
            plan.execution_mode = "LLM_PLANNING"
            plan.model_name = self.llm_client.model
            plan.fallback_reason = None
        except ValidationError as ve:
            raise PlanValidationError(f"LLM plan failed Pydantic schema validation: {ve.errors()}")

        self.validate_plan_safety(plan)
        return plan

    def _plan_deterministic(self, user_goal: str, fallback_reason: Optional[str] = None) -> ActionPlan:
        """Deterministic plan generator with dynamic parameter references."""
        # Extract potential vendor name
        vendor_match = re.search(r"(?:from|for|vendor)\s+([A-Za-z0-9\s]+?)(?:,|$|\.|\band\b)", user_goal, re.IGNORECASE)
        vendor_name = vendor_match.group(1).strip() if vendor_match else "Acme Technologies"

        # Clean trailing noise
        for term in ["extract", "enter", "invoice", "the"]:
            if vendor_name.lower().endswith(term):
                vendor_name = vendor_name[:-len(term)].strip()

        if not vendor_name:
            vendor_name = "Acme Technologies"

        steps = [
            ActionStep(
                step_number=1,
                tool_name="search_invoices",
                parameters={"vendor_name": vendor_name},
                reasoning=f"Search the repository for all invoices from '{vendor_name}' and identify the latest one.",
                consequential=False
            ),
            ActionStep(
                step_number=2,
                tool_name="read_invoice",
                parameters={"filename": "$steps.search_invoices.result.latest.filename"},
                reasoning="Read the content of the identified latest invoice file.",
                consequential=False
            ),
            ActionStep(
                step_number=3,
                tool_name="extract_invoice_data",
                parameters={
                    "raw_content": "$steps.read_invoice.result.content",
                    "filename": "$steps.read_invoice.result.filename"
                },
                reasoning="Extract structured fields (vendor, invoice number, due date, amount).",
                consequential=False
            ),
            ActionStep(
                step_number=4,
                tool_name="create_payable_record",
                parameters={
                    "invoice_number": "$steps.extract_invoice_data.result.invoice_number",
                    "vendor_name": "$steps.extract_invoice_data.result.vendor_name",
                    "amount": "$steps.extract_invoice_data.result.total_amount",
                    "due_date": "$steps.extract_invoice_data.result.due_date",
                    "currency": "$steps.extract_invoice_data.result.currency",
                    "source_file": "$steps.extract_invoice_data.result.source_file"
                },
                reasoning="Record the payable in the company accounts payable database.",
                consequential=True
            )
        ]

        plan = ActionPlan(
            goal=user_goal,
            estimated_risk="MEDIUM",
            steps=steps,
            execution_mode="DETERMINISTIC_FALLBACK",
            model_name="N/A (Deterministic)",
            fallback_reason=fallback_reason
        )
        self.validate_plan_safety(plan)
        return plan

    def replan(
        self,
        user_goal: str,
        plan: ActionPlan,
        failed_step: ActionStep,
        error_context: str,
        traces: List[ExecutionTraceItem],
        attempt: int,
        clarification_response: Optional[str] = None
    ) -> ReplanDecision:
        """Lightweight failure recovery loop deciding whether to retry, substitute, clarify, or terminate."""
        # 1. User clarification response provided
        if clarification_response and clarification_response.strip():
            clarif_text = clarification_response.strip()
            # If user specified a vendor name
            vendor_candidate = clarif_text
            for prefix in ["process", "vendor is", "use", "select", "pay", "for"]:
                if clarif_text.lower().startswith(prefix):
                    vendor_candidate = clarif_text[len(prefix):].strip()
                    break

            cleaned_vendor = vendor_candidate or "Acme Technologies"
            # Regenerate end-to-end plan steps for the clarified entity
            new_plan = self._plan_deterministic(f"Process {cleaned_vendor}")
            return ReplanDecision(
                action=ReplanAction.SUBSTITUTE_STEP,
                reasoning=f"Applying user clarification: {clarif_text}. Initiating steps for {cleaned_vendor}.",
                new_steps=new_plan.steps
            )

        # 2. Check for ambiguity / missing clarification
        err_lower = error_context.lower()
        if "ambiguous" in err_lower or "clarification" in err_lower or "joint venture" in err_lower:
            return ReplanDecision(
                action=ReplanAction.ASK_CLARIFICATION,
                reasoning="Ambiguity in invoice source requires human input.",
                clarification_prompt=f"Ambiguity detected in step {failed_step.step_number}: {error_context}. Please specify which vendor or due date to apply."
            )

        # 3. If LLM is available, consult LLM for intelligent replan decision
        if self.llm_client.is_available():
            try:
                system_prompt = f"""You are an autonomous AI Task Recovery Agent.
An action step in the current plan failed. Analyze the goal, plan, failed step, and error, then decide the next action.

OPTIONS:
- RETRY: retry step with modified parameters
- SUBSTITUTE_STEP: provide an alternate tool call from permitted tools
- ASK_CLARIFICATION: request user guidance
- TERMINATE: abort if unrecoverable

PERMITTED TOOLS:
{json.dumps(self.registry.list_tools(), indent=2)}

Return a valid JSON object matching:
{{
  "action": "RETRY" | "SUBSTITUTE_STEP" | "ASK_CLARIFICATION" | "TERMINATE",
  "reasoning": "...",
  "adjusted_step": {{"step_number": int, "tool_name": "...", "parameters": {{}}, "reasoning": "...", "consequential": bool}} or null,
  "clarification_prompt": "..." or null,
  "error_message": "..." or null
}}"""
                user_msg = f"""Goal: {user_goal}
Failed Step: {failed_step.model_dump_json()}
Error Context: {error_context}
Attempt: {attempt} of 2"""

                response = self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                decision = ReplanDecision.model_validate_json(response)
                decision.used_llm = True
                decision.model_name = self.llm_client.model
                return decision
            except Exception as e:
                logger.warning(f"LLM replan call failed ({e}), falling back to deterministic replan logic")

        # 4. Deterministic replan heuristics
        if "no invoices found" in err_lower:
            # Check if vendor had suffix like 'Corp' or 'LLC' that can be relaxed
            curr_vendor = str(failed_step.parameters.get("vendor_name", ""))
            if any(s in curr_vendor.lower() for s in ["corp", "inc", "llc", "technologies"]):
                cleaned = re.sub(r"\b(corp|inc|llc|technologies)\b", "", curr_vendor, flags=re.IGNORECASE).strip()
                if cleaned and cleaned != curr_vendor and attempt <= 1:
                    adj_step = ActionStep(
                        step_number=failed_step.step_number,
                        tool_name="search_invoices",
                        parameters={"vendor_name": cleaned},
                        reasoning=f"Broadening search query to '{cleaned}' after initial search returned 0 results.",
                        consequential=False
                    )
                    return ReplanDecision(
                        action=ReplanAction.SUBSTITUTE_STEP,
                        reasoning=f"Relaxing vendor filter from '{curr_vendor}' to '{cleaned}'.",
                        adjusted_step=adj_step
                    )

            return ReplanDecision(
                action=ReplanAction.TERMINATE,
                reasoning=f"No matching invoices found for '{curr_vendor}'.",
                error_message=f"No invoices found matching '{curr_vendor}'."
            )

        if "duplicate" in err_lower:
            return ReplanDecision(
                action=ReplanAction.TERMINATE,
                reasoning="Duplicate payable record already exists in database.",
                error_message=error_context
            )

        if "malformed" in err_lower or "syntax" in err_lower:
            return ReplanDecision(
                action=ReplanAction.TERMINATE,
                reasoning="Invoice source document is corrupted and cannot be parsed.",
                error_message=error_context
            )

        return ReplanDecision(
            action=ReplanAction.TERMINATE,
            reasoning=f"Unrecoverable error in step {failed_step.step_number}: {error_context}",
            error_message=error_context
        )

    def validate_plan_safety(self, plan: ActionPlan) -> None:
        """Validate that all tools exist in registry and adhere to permission policies."""
        if not plan.steps:
            raise PlanValidationError("Action plan contains no steps.")

        for step in plan.steps:
            if not self.registry.has_tool(step.tool_name):
                raise PlanValidationError(
                    f"Plan contains unauthorized tool '{step.tool_name}'. "
                    f"Arbitrary code execution and unregistered tools are prohibited."
                )

            tool = self.registry.get(step.tool_name)
            # Enforce that consequential tools must be flagged consequential
            if tool.consequential and not step.consequential:
                step.consequential = True
