"""Tests for calculator tool handlers."""

import pytest

from tools.calculator_tool import (
    AddNumbersToolHandler,
    DivideNumbersToolHandler,
    MultiplyNumbersToolHandler,
    SubtractNumbersToolHandler,
)


@pytest.mark.asyncio
async def test_add_numbers_returns_result():
    handler = AddNumbersToolHandler()
    result = await handler.run_tool({"a": 10, "b": 5})
    assert result[0].text == "Result: 15.0"


@pytest.mark.asyncio
async def test_subtract_numbers_returns_result():
    handler = SubtractNumbersToolHandler()
    result = await handler.run_tool({"a": 10, "b": 5})
    assert result[0].text == "Result: 5.0"


@pytest.mark.asyncio
async def test_multiply_numbers_returns_result():
    handler = MultiplyNumbersToolHandler()
    result = await handler.run_tool({"a": 10, "b": 5})
    assert result[0].text == "Result: 50.0"


@pytest.mark.asyncio
async def test_divide_numbers_returns_result():
    handler = DivideNumbersToolHandler()
    result = await handler.run_tool({"a": 10, "b": 5})
    assert result[0].text == "Result: 2.0"


@pytest.mark.asyncio
async def test_divide_numbers_by_zero_raises_error():
    handler = DivideNumbersToolHandler()
    with pytest.raises(RuntimeError, match="Division by zero"):
        await handler.run_tool({"a": 10, "b": 0})


def test_tool_descriptions_are_present():
    handlers = [
        AddNumbersToolHandler(),
        SubtractNumbersToolHandler(),
        MultiplyNumbersToolHandler(),
        DivideNumbersToolHandler(),
    ]

    for handler in handlers:
        description = handler.get_tool_description()
        assert description.name == handler.name
        assert description.description
