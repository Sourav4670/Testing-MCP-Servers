"""
server.py - Real-Time Weather Advisor MCP Server
================================================

This file is the single entry-point for the MCP server. It supports
three transport modes selected via the ``--mode`` command-line flag:

1. ``stdio``
   Default mode used by Claude Desktop, Cursor, and most MCP hosts.
   Messages are exchanged over stdin/stdout.

2. ``sse``
   Exposes HTTP endpoints:
   - GET /sse
   - POST /messages/

3. ``streamable-http``
   Exposes HTTP endpoint:
   - POST /mcp
   Responses are delivered as chunked streams.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys
import traceback
from collections.abc import AsyncIterator, Sequence
from typing import Any, Dict

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from tools.toolhandler import ToolHandler
from tools.weather_tool import GetWeatherToolHandler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("weather-advisor")

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

app = Server("weather-advisor-mcp")

# ---------------------------------------------------------------------------
# Tool handler registry
# ---------------------------------------------------------------------------

_tool_handlers: Dict[str, ToolHandler] = {}


def add_tool_handler(handler: ToolHandler) -> None:
    """Register *handler* in the global tool registry."""
    _tool_handlers[handler.name] = handler
    logger.info("Registered tool: %s", handler.name)


def get_tool_handler(name: str) -> ToolHandler | None:
    """Return the handler for *name*, or ``None`` if not registered."""
    return _tool_handlers.get(name)


def register_all_tools() -> None:
    """
    Central catalogue of all tools this server exposes.

    To add a new tool:
      1. Create a new ToolHandler subclass in tools/.
      2. Import it here.
      3. Call ``add_tool_handler(MyNewToolHandler())``.
    """
    add_tool_handler(GetWeatherToolHandler())
    logger.info("Total tools registered: %d", len(_tool_handlers))


# ---------------------------------------------------------------------------
# MCP protocol callbacks
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Called by MCP clients to discover available tools."""
    tools = [h.get_tool_description() for h in _tool_handlers.values()]
    logger.info("list_tools -> %d tool(s) returned", len(tools))
    return tools


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Called by MCP clients to execute a tool by *name* with *arguments*."""
    if arguments is None:
        arguments = {}
    elif not isinstance(arguments, dict):
        try:
            arguments = dict(arguments)
        except Exception:
            logger.error("arguments is not dict-like: %s", type(arguments))
            raise RuntimeError("Tool arguments must be a dictionary")

    handler = get_tool_handler(name)
    if not handler:
        logger.error("Unknown tool requested: %s", name)
        raise ValueError(f"Unknown tool: '{name}'")

    logger.info("Executing tool '%s' with keys: %s", name, list(arguments.keys()))
    try:
        result = await handler.run_tool(arguments)
        logger.info("Tool '%s' completed successfully", name)
        return result
    except Exception as exc:
        logger.exception("Tool '%s' raised an exception: %s", name, exc)
        return [
            TextContent(
                type="text",
                text=f"Error executing tool '{name}': {exc}\n\n{traceback.format_exc()}",
            )
        ]


# ---------------------------------------------------------------------------
# Transport: SSE
# ---------------------------------------------------------------------------

def create_sse_starlette_app(mcp_server: Server) -> Starlette:
    """Build the Starlette ASGI application for SSE transport."""
    sse_transport = SseServerTransport("/messages/")

    class _SSEEndpoint:
        async def __call__(self, scope, receive, send) -> None:
            async with sse_transport.connect_sse(scope, receive, send) as (
                read_stream,
                write_stream,
            ):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )

    async def _health_endpoint(_request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    starlette_app = Starlette(
        debug=False,
        routes=[
            Route("/health", endpoint=_health_endpoint),
            Route("/sse", endpoint=_SSEEndpoint()),
            Mount("/messages/", app=sse_transport.handle_post_message),
        ],
    )

    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,
    )
    return starlette_app


# ---------------------------------------------------------------------------
# Transport: Streamable HTTP
# ---------------------------------------------------------------------------

def create_streamable_http_app(mcp_server: Server) -> Starlette:
    """Build the Starlette ASGI application for Streamable HTTP transport."""
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=False,
        stateless=False,
    )

    class _StreamableHTTPRoute:
        async def __call__(self, scope, receive, send) -> None:
            await session_manager.handle_request(scope, receive, send)

    async def _health_endpoint(_request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @contextlib.asynccontextmanager
    async def _lifespan(_starlette_app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    starlette_app = Starlette(
        debug=False,
        routes=[
            Route("/health", endpoint=_health_endpoint),
            Route("/mcp", endpoint=_StreamableHTTPRoute()),
        ],
        lifespan=_lifespan,
    )

    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )
    return starlette_app


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------

async def run_server(mode: str, host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start the server in the requested *mode*."""
    if mode == "stdio":
        logger.info("Starting in STDIO mode (stdin/stdout)")
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    elif mode == "sse":
        logger.info("Starting in SSE mode on http://%s:%d", host, port)
        starlette_app = create_sse_starlette_app(app)
        config = uvicorn.Config(app=starlette_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    elif mode == "streamable-http":
        logger.info("Starting in STREAMABLE-HTTP mode on http://%s:%d", host, port)
        starlette_app = create_streamable_http_app(app)
        config = uvicorn.Config(app=starlette_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    else:
        raise ValueError(f"Unknown server mode: '{mode}'")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Parse CLI arguments and start the server."""
    parser = argparse.ArgumentParser(
        prog="simple-weather-mcp",
        description="Real-Time Weather Advisor MCP Server",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "streamable-http", "streamable_http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host for HTTP modes (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port for HTTP modes (default: 8080)",
    )
    args = parser.parse_args()

    logger.info("Weather Advisor MCP Server starting up")
    logger.info("Python %s", sys.version)

    register_all_tools()
    logger.info("Tools available: %s", list(_tool_handlers.keys()))

    mode = "streamable-http" if args.mode == "streamable_http" else args.mode
    await run_server(mode=mode, host=args.host, port=args.port)


def cli_main() -> None:
    """Synchronous wrapper used by console scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()