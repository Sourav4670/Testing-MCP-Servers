"""
travel_advisor – Real-Time Travel Advisor MCP Server package.

Public surface:
  main()       – synchronous entry point used by the ``project.scripts`` shim
  async_main() – the underlying coroutine for applications that manage their
                 own event loop.
"""

from .server import main as async_main
import asyncio


def main() -> None:
    """Synchronous entry point called by ``travel-advisor-mcp`` CLI command."""
    asyncio.run(async_main())


__all__ = ["main", "async_main"]
