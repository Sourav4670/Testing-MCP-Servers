"""
Abstract base class for all MCP tool handlers in the Travel Advisor server.

This module defines the ToolHandler contract that every tool must satisfy,
providing a uniform interface for registration, schema description, and
execution throughout the server.  Following the same pattern as
mcp_weather_server (mcp-gsuite style), adding a new tool is as simple as:

  1. Subclass ToolHandler.
  2. Implement get_tool_description() → Tool.
  3. Implement run_tool(args) → Sequence[TextContent | ...].
  4. Register the instance in server.py::register_all_tools().
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)


class ToolHandler(ABC):
    """
    Abstract base class for every MCP tool in this server.

    Each concrete subclass represents exactly one tool that is exposed to
    MCP clients.  All tools must be registered via
    ``server.add_tool_handler()`` before the server starts serving traffic.
    """

    def __init__(self, tool_name: str) -> None:
        """
        Initialise the handler with the unique name that MCP clients will use
        when invoking this tool.

        Args:
            tool_name: Unique identifier for the tool (e.g. "get_travel_advice").
        """
        self.name = tool_name

    # ------------------------------------------------------------------
    # Abstract interface – subclasses MUST implement both methods.
    # ------------------------------------------------------------------

    @abstractmethod
    def get_tool_description(self) -> Tool:
        """
        Return the MCP ``Tool`` object that describes this handler to clients.

        The ``Tool`` object carries the tool name, a human-readable
        description, and a JSON Schema (``inputSchema``) that MCP clients
        use for validation and to generate prompts.

        Returns:
            Tool: Fully-populated MCP Tool descriptor.
        """
        raise NotImplementedError

    @abstractmethod
    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the tool with the validated argument dictionary.

        This method is ``async`` so implementations can optionally perform
        I/O in the future without changing the interface.

        Args:
            args: Key/value pairs supplied by the MCP client.

        Returns:
            A non-empty sequence of MCP content items.  Typically a single
            ``TextContent`` carrying the human-readable response.

        Raises:
            RuntimeError: When required arguments are absent or execution
                fails in a way the caller should surface as an error.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers – available to all subclasses.
    # ------------------------------------------------------------------

    def validate_required_args(self, args: dict, required_fields: list[str]) -> None:
        """
        Assert that every field in *required_fields* is present in *args*.

        Args:
            args:             Dictionary of arguments provided by the client.
            required_fields:  Names of mandatory parameters.

        Raises:
            RuntimeError: Listing every missing field name.
        """
        missing = [f for f in required_fields if f not in args or args[f] is None]
        if missing:
            raise RuntimeError(
                f"Missing required argument(s): {', '.join(missing)}"
            )
