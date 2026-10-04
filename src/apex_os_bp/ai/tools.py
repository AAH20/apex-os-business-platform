"""Tool Integration Module.

Provides a registry for tools, tool execution with validation,
and support for both sync and async tool handlers.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class ToolError(Exception):
    """Raised when a tool execution fails."""

    def __init__(self, message: str, tool_name: str = "") -> None:
        super().__init__(message)
        self.tool_name = tool_name


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    """A callable tool with metadata and validation."""

    name: str
    description: str
    handler: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    is_async: bool = False
    timeout: float = 30.0
    tool_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if inspect.iscoroutinefunction(self.handler):
            self.is_async = True

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given parameters."""
        start = time.time()
        try:
            if self.is_async:
                output = await asyncio.wait_for(
                    self.handler(**kwargs), timeout=self.timeout
                )
            else:
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.handler(**kwargs)),
                    timeout=self.timeout,
                )
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=output,
                duration=time.time() - start,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Tool '{self.name}' timed out after {self.timeout}s",
                duration=time.time() - start,
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                duration=time.time() - start,
            )

    def validate_parameters(self, **kwargs: Any) -> list[str]:
        """Validate parameters against the tool's schema. Returns list of errors."""
        errors: list[str] = []
        required = self.parameters.get("required", [])
        for param in required:
            if param not in kwargs:
                errors.append(f"Missing required parameter: '{param}'")

        properties = self.parameters.get("properties", {})
        for key, value in kwargs.items():
            if key in properties:
                expected_type = properties[key].get("type")
                type_map = {
                    "string": str,
                    "integer": int,
                    "number": (int, float),
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                if expected_type and expected_type in type_map:
                    if not isinstance(value, type_map[expected_type]):
                        errors.append(
                            f"Parameter '{key}' expected type '{expected_type}', "
                            f"got '{type(value).__name__}'"
                        )
        return errors


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_by_tag(self, tag: str) -> list[Tool]:
        """List tools filtered by tag."""
        return [t for t in self._tools.values() if tag in t.tags]

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by name with the given parameters."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' not found in registry",
            )

        validation_errors = tool.validate_parameters(**kwargs)
        if validation_errors:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Validation failed: {'; '.join(validation_errors)}",
            )

        return await tool.execute(**kwargs)

    async def execute_many(
        self, calls: list[tuple[str, dict[str, Any]]]
    ) -> list[ToolResult]:
        """Execute multiple tools in parallel.

        Each call is a tuple of (tool_name, kwargs).
        """
        coros = [self.execute(name, **kwargs) for name, kwargs in calls]
        return await asyncio.gather(*coros)

    def search(self, query: str) -> list[Tool]:
        """Search tools by name or description."""
        query_lower = query.lower()
        return [
            t
            for t in self._tools.values()
            if query_lower in t.name.lower() or query_lower in t.description.lower()
        ]

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()

    @property
    def count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)
