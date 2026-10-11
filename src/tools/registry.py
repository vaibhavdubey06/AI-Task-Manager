"""Explicit permitted tool registry ensuring strict sandbox boundaries.

No arbitrary shell execution, eval(), exec(), or unapproved tools are permitted.
"""
from typing import Dict, List, Any, Optional
from src.tools.base import BaseTool, PermissionDeniedError
from src.tools.invoice_tools import SearchInvoicesTool, ReadInvoiceTool, ExtractInvoiceDataTool
from src.tools.payable_tools import CreatePayableTool, GetPayableTool, ListPayablesTool


class ToolRegistry:
    """Registry maintaining explicitly permitted tools with validated schemas."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a permitted tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve tool by name, enforcing strict permissions."""
        if name not in self._tools:
            allowed = ", ".join(self._tools.keys())
            raise PermissionDeniedError(
                f"Unauthorized tool requested: '{name}'. "
                f"Arbitrary code and unapproved tools are strictly forbidden. "
                f"Permitted tools are: [{allowed}]"
            )
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """List metadata and schemas for all permitted tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "consequential": tool.consequential,
                "parameters": tool.input_schema.model_json_schema()
            }
            for tool in self._tools.values()
        ]


def create_default_registry() -> ToolRegistry:
    """Instantiate and populate default permitted tool registry."""
    registry = ToolRegistry()
    registry.register(SearchInvoicesTool())
    registry.register(ReadInvoiceTool())
    registry.register(ExtractInvoiceDataTool())
    registry.register(CreatePayableTool())
    registry.register(GetPayableTool())
    registry.register(ListPayablesTool())
    return registry


# Singleton default registry
default_registry = create_default_registry()
