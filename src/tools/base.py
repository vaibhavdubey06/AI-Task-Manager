"""Base tool class and exception definitions."""
from abc import ABC, abstractmethod
from typing import Type, Dict, Any, Optional
from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Base exception for all tool operations."""
    pass


class ToolExecutionError(ToolError):
    """Fatal or non-recoverable error during tool execution."""
    pass


class RecoverableToolError(ToolError):
    """Transient or recoverable error that may succeed upon retry."""
    pass


class PermissionDeniedError(ToolError):
    """Raised when an unauthorized or unregistered tool is invoked."""
    pass


class BaseTool(ABC):
    """Abstract base class for all permitted tools with strict Pydantic schema validation."""
    name: str
    description: str
    consequential: bool = False  # If True, requires human approval before execution
    input_schema: Type[BaseModel]

    def run(self, **kwargs) -> Any:
        """Validate input arguments against Pydantic schema and execute."""
        try:
            validated_args = self.input_schema(**kwargs)
        except ValidationError as e:
            raise ToolExecutionError(f"Schema validation failed for tool '{self.name}': {e.errors()}")

        return self._execute(validated_args)

    @abstractmethod
    def _execute(self, args: BaseModel) -> Any:
        """Subclass implementation of tool logic."""
        pass
