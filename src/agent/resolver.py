"""Generic dynamic parameter resolver for step-to-step data propagation.

Enables tools to consume outputs of prior steps using path references,
e.g. '$steps.search_invoices.result.matches[0].filename' or '$step_1.result.latest.filename'.
Eliminates any need for hardcoded workflow-specific parameter binding.
"""
import re
from typing import Any, Dict, List, Optional
from src.models import StepResult


class ParameterResolutionError(Exception):
    """Raised when a dynamic parameter reference cannot be resolved."""
    pass


def traverse_path(root_obj: Any, path: str) -> Any:
    """Traverse dot and bracket path notations on dictionaries, lists, and objects.

    Examples:
        'matches[0].filename'
        'latest.vendor_name'
        'result.invoice_number'
    """
    if not path:
        return root_obj

    # Split by dots while keeping bracket indices: e.g. "matches[0].filename" -> ["matches", "[0]", "filename"]
    raw_tokens = re.findall(r'[^.\[\]]+|\[\d+\]', path)
    current = root_obj

    for token in raw_tokens:
        if current is None:
            return None

        if token.startswith('[') and token.endswith(']'):
            index = int(token[1:-1])
            if isinstance(current, (list, tuple)) and 0 <= index < len(current):
                current = current[index]
            else:
                return None
        elif token.isdigit() and isinstance(current, (list, tuple)):
            index = int(token)
            if 0 <= index < len(current):
                current = current[index]
            else:
                return None
        else:
            if isinstance(current, dict):
                current = current.get(token)
            elif hasattr(current, token):
                current = getattr(current, token)
            else:
                return None

    return current


def resolve_single_reference(ref_expr: str, step_results: Dict[str, StepResult]) -> Any:
    """Resolve a single reference string like '$steps.search_invoices.result.matches[0].filename'."""
    # Pattern matching:
    # 1. $steps.<selector>.<path>
    # 2. $step_<selector>.<path>
    match = re.match(r'^\$(?:steps\.([a-zA-Z0-9_-]+)|step_([a-zA-Z0-9_-]+))(?:\.(.+))?$', ref_expr.strip())
    if not match:
        return ref_expr

    selector = match.group(1) or match.group(2)
    path = match.group(3) or ""

    # Look up StepResult
    step_res: Optional[StepResult] = None
    candidates = [
        selector,
        f"step_{selector}",
        selector.lstrip("step_"),
    ]
    for cand in candidates:
        if cand in step_results:
            step_res = step_results[cand]
            break

    if not step_res:
        # Step hasn't executed or doesn't exist
        return None

    # Base target is step_res.result if available
    base_target = step_res.result if step_res.result is not None else step_res

    if not path or path == "result":
        return base_target

    if path.startswith("result."):
        path = path[len("result."):]

    resolved = traverse_path(base_target, path)
    if resolved is not None:
        return resolved

    # Fallback heuristics for common step results if LLM guessed slightly alternate key (e.g. files vs matches)
    if isinstance(base_target, dict):
        if "filename" in path:
            latest = base_target.get("latest") or (base_target.get("matches", [{}])[0] if base_target.get("matches") else None)
            if latest and isinstance(latest, dict) and "filename" in latest:
                return latest["filename"]

    return None


def resolve_value(val: Any, step_results: Dict[str, StepResult]) -> Any:
    """Recursively resolve dynamic parameter references within a value (string, dict, list)."""
    if isinstance(val, str):
        trimmed = val.strip()
        # If the entire string is a reference: return resolved object with original type
        if (trimmed.startswith("$steps.") or trimmed.startswith("$step_")) and " " not in trimmed:
            resolved = resolve_single_reference(trimmed, step_results)
            return resolved if resolved is not None else val

        # If it contains embedded references like "${steps.X.Y}": interpolate
        pattern = r'\$\{(?:steps\.([a-zA-Z0-9_-]+)|step_([a-zA-Z0-9_-]+))(?:\.([^}]+))?\}'
        if re.search(pattern, val):
            def replacer(m):
                full_expr = m.group(0).replace("{", "").replace("}", "")
                r = resolve_single_reference(full_expr, step_results)
                return str(r) if r is not None else m.group(0)
            return re.sub(pattern, replacer, val)

        return val

    elif isinstance(val, dict):
        return {k: resolve_value(v, step_results) for k, v in val.items()}

    elif isinstance(val, list):
        return [resolve_value(item, step_results) for item in val]

    return val


def resolve_parameters(params: Dict[str, Any], step_results: Dict[str, StepResult]) -> Dict[str, Any]:
    """Resolve all dynamic references in a step's parameter dictionary."""
    return resolve_value(params, step_results)
