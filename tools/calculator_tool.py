"""calculator_tool.py - MCP tool handlers for calculator operations."""

from __future__ import annotations

from collections.abc import Sequence

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .toolhandler import ToolHandler


class AddNumbersToolHandler(ToolHandler):
    def __init__(self) -> None:
        super().__init__("add_numbers")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Add Numbers",
            description="Add two numbers and return the result.",
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "a": {"type": "number", "description": "First number."},
                    "b": {"type": "number", "description": "Second number."},
                },
                "required": ["a", "b"],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        self.validate_required_args(args, ["a", "b"])
        a = float(args["a"])
        b = float(args["b"])
        result = a + b
        return [TextContent(type="text", text=f"Result: {result}")]


class SubtractNumbersToolHandler(ToolHandler):
    def __init__(self) -> None:
        super().__init__("subtract_numbers")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Subtract Numbers",
            description="Subtract second number from first number.",
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "a": {"type": "number", "description": "First number."},
                    "b": {"type": "number", "description": "Second number."},
                },
                "required": ["a", "b"],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        self.validate_required_args(args, ["a", "b"])
        a = float(args["a"])
        b = float(args["b"])
        result = a - b
        return [TextContent(type="text", text=f"Result: {result}")]


class MultiplyNumbersToolHandler(ToolHandler):
    def __init__(self) -> None:
        super().__init__("multiply_numbers")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Multiply Numbers",
            description="Multiply two numbers and return the result.",
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "a": {"type": "number", "description": "First number."},
                    "b": {"type": "number", "description": "Second number."},
                },
                "required": ["a", "b"],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        self.validate_required_args(args, ["a", "b"])
        a = float(args["a"])
        b = float(args["b"])
        result = a * b
        return [TextContent(type="text", text=f"Result: {result}")]


class DivideNumbersToolHandler(ToolHandler):
    def __init__(self) -> None:
        super().__init__("divide_numbers")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Divide Numbers",
            description="Divide first number by second number.",
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "a": {"type": "number", "description": "Dividend."},
                    "b": {
                        "type": "number",
                        "description": "Divisor (must not be zero).",
                    },
                },
                "required": ["a", "b"],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        self.validate_required_args(args, ["a", "b"])
        a = float(args["a"])
        b = float(args["b"])
        if b == 0:
            raise RuntimeError("Division by zero is not allowed")
        result = a / b
        return [TextContent(type="text", text=f"Result: {result}")]
