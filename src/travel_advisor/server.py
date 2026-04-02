"""
server.py – Real-Time Travel Advisor MCP Server
================================================

This file is the single entry-point for the MCP server.  It supports
three transport modes selected via the ``--mode`` command-line flag:

┌──────────────────┬────────────────────────────────────────────────────┐
│ Mode             │ How it works                                       │
├──────────────────┼────────────────────────────────────────────────────┤
│ stdio            │ The server reads JSON-RPC messages from stdin and   │
│                  │ writes responses to stdout.  This is the default    │
│                  │ mode used by Claude Desktop, Cursor, and most MCP   │
│                  │ host applications.  No network port is needed.      │
├──────────────────┼────────────────────────────────────────────────────┤
│ sse              │ The server exposes two HTTP endpoints:              │
│                  │   GET  /sse       – client opens a persistent SSE   │
│                  │                     stream to receive MCP events    │
│                  │   POST /messages/ – client sends MCP messages here  │
│                  │ Good for browser-based clients and simple HTTP      │
│                  │ reverse proxies.                                    │
├──────────────────┼────────────────────────────────────────────────────┤
│ streamable-http  │ The server exposes a single endpoint:              │
│                  │   POST /mcp       – all MCP traffic flows here      │
│                  │ Responses are streamed via HTTP chunked encoding.   │
│                  │ This is the newer MCP v1 preferred HTTP mechanism.  │
│                  │ Maintains per-session state via the                 │
│                  │ StreamableHTTPSessionManager.                       │
└──────────────────┴────────────────────────────────────────────────────┘

Usage
-----
  # stdio (default, for Claude Desktop / Cursor)
  python -m travel_advisor

  # SSE (legacy HTTP streaming)
  python -m travel_advisor --mode sse --host 0.0.0.0 --port 8080

  # Streamable HTTP (MCP v1 preferred HTTP)
  python -m travel_advisor --mode streamable-http --host 0.0.0.0 --port 8080

No environment variables required.  All configuration is via CLI args.
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
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .tools.toolhandler import ToolHandler
from .tools.travel_tool import GetTravelAdviceToolHandler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("travel-advisor")

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

# ``Server`` is the core MCP server object from the Python SDK.
# We give it a human-readable name that clients will display.
app = Server("travel-advisor-mcp")

# ---------------------------------------------------------------------------
# Tool handler registry
# ---------------------------------------------------------------------------

# All registered tool handlers are stored in this global dict keyed by
# their unique tool name.  The registry is populated once at startup by
# ``register_all_tools()`` and is read-only thereafter.
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
    add_tool_handler(GetTravelAdviceToolHandler())
    logger.info("Total tools registered: %d", len(_tool_handlers))


# ---------------------------------------------------------------------------
# MCP protocol callbacks
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    Called by MCP clients to discover available tools.

    Returns the ``Tool`` schema for every registered handler so the client
    knows each tool's name, description, and required input parameters.
    """
    tools = [h.get_tool_description() for h in _tool_handlers.values()]
    logger.info("list_tools → %d tool(s) returned", len(tools))
    return tools


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """
    Called by MCP clients to execute a tool by *name* with *arguments*.

    Normalise arguments to a plain dict (some transports pass other
    mapping-like objects), look up the handler, and delegate execution.
    """
    # Normalise arguments to a plain dict
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
#
# How SSE mode works
# ------------------
# 1. The MCP client opens a persistent GET connection to ``/sse``.
#    The server sends MCP events (JSON-encoded) as server-sent event frames
#    over this long-lived HTTP connection.
# 2. To *send* a message to the server the client POSTs JSON-RPC payloads
#    to ``/messages/``.  The ``SseServerTransport`` routes those payloads
#    internally to the same MCP server session as the SSE stream.
# 3. Starlette wraps both endpoints.  CORS middleware is added so
#    browser-based clients can connect.
# ---------------------------------------------------------------------------

def create_sse_starlette_app(mcp_server: Server) -> Starlette:
    """
    Build the Starlette ASGI application for SSE transport.

    Endpoints
    ---------
    GET  /sse       – open an SSE stream (one per client session)
    POST /messages/ – receive client → server MCP messages
    """
    sse_transport = SseServerTransport("/messages/")

    class _SSEEndpoint:
        """ASGI callable that hands each incoming SSE connection to the MCP server."""

        async def __call__(self, scope, receive, send) -> None:
            logger.info("SSE: new client connection")
            # ``connect_sse`` upgrades the HTTP connection to a bi-directional
            # MCP stream.  read_stream carries client messages; write_stream
            # carries server responses sent as SSE frames.
            async with sse_transport.connect_sse(scope, receive, send) as (
                read_stream,
                write_stream,
            ):
                logger.info("SSE: session established – running MCP server")
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )
                logger.info("SSE: session closed")

    starlette_app = Starlette(
        debug=False,
        routes=[
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
#
# How Streamable HTTP mode works
# ------------------------------
# 1. All MCP traffic flows through a single ``POST /mcp`` endpoint.
# 2. ``StreamableHTTPSessionManager`` manages per-session state, assigns
#    session IDs (returned in the ``mcp-session-id`` response header), and
#    handles concurrent requests from the same session.
# 3. Responses are sent as HTTP chunked-transfer-encoding streams so the
#    client receives partial results incrementally without waiting for the
#    full response payload.
# 4. The session manager lifecycle (start / stop) is managed by Starlette's
#    ``lifespan`` context manager so sessions are cleanly terminated when
#    the server shuts down.
# ---------------------------------------------------------------------------

def create_streamable_http_app(mcp_server: Server) -> Starlette:
    """
    Build the Starlette ASGI application for Streamable HTTP transport.

    Endpoint
    --------
    POST /mcp  – all MCP JSON-RPC traffic; responses are chunked streams
    """
    # ``stateless=False`` means the session manager tracks per-session state.
    # ``json_response=False`` means responses are sent as SSE-like streams,
    # not a single JSON blob, enabling true streaming.
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,   # No resumability (simplest config)
        json_response=False,
        stateless=False,
    )

    class _StreamableHTTPRoute:
        """ASGI callable that forwards each request to the session manager."""

        async def __call__(self, scope, receive, send) -> None:
            await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def _lifespan(starlette_app: Starlette) -> AsyncIterator[None]:
        """
        Manage the StreamableHTTPSessionManager lifecycle.

        ``session_manager.run()`` starts background housekeeping tasks;
        they are stopped cleanly when the ``async with`` block exits.
        """
        async with session_manager.run():
            logger.info("Streamable HTTP: session manager started")
            try:
                yield
            finally:
                logger.info("Streamable HTTP: session manager shutting down")

    starlette_app = Starlette(
        debug=False,
        routes=[
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
        # Expose session + protocol version headers so clients can track state
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )
    return starlette_app


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------

async def run_server(mode: str, host: str = "0.0.0.0", port: int = 8080) -> None:
    """
    Start the server in the requested *mode*.

    Parameters
    ----------
    mode : "stdio" | "sse" | "streamable-http"
    host : bind address for HTTP modes
    port : TCP port for HTTP modes
    """
    if mode == "stdio":
        # ----------------------------------------------------------------
        # stdio mode
        # ----------------------------------------------------------------
        # The mcp ``stdio_server`` context manager connects stdin/stdout
        # to the MCP read/write streams.  The server blocks here until
        # the parent process closes stdin (e.g. Claude Desktop exits).
        # ----------------------------------------------------------------
        logger.info("Starting in STDIO mode (reading stdin / writing stdout)")
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    elif mode == "sse":
        # ----------------------------------------------------------------
        # SSE mode
        # ----------------------------------------------------------------
        logger.info("Starting in SSE mode on http://%s:%d", host, port)
        logger.info("  ↳ SSE endpoint  : GET  http://%s:%d/sse", host, port)
        logger.info("  ↳ Message inbox : POST http://%s:%d/messages/", host, port)

        starlette_app = create_sse_starlette_app(app)
        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    elif mode == "streamable-http":
        # ----------------------------------------------------------------
        # Streamable HTTP mode
        # ----------------------------------------------------------------
        logger.info("Starting in STREAMABLE-HTTP mode on http://%s:%d", host, port)
        logger.info("  ↳ MCP endpoint : POST http://%s:%d/mcp", host, port)

        starlette_app = create_streamable_http_app(app)
        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    else:
        raise ValueError(f"Unknown server mode: '{mode}'")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def main() -> None:
    """
    Parse CLI arguments and start the server.

    No environment variables are read.  All configuration is explicit.
    """
    parser = argparse.ArgumentParser(
        prog="travel-advisor-mcp",
        description="Real-Time Travel Advisor MCP Server",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "streamable-http"],
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

    logger.info("Travel Advisor MCP Server starting up")
    logger.info("Python %s", sys.version)

    # Register all tools before the server begins accepting connections
    register_all_tools()
    logger.info("Tools available: %s", list(_tool_handlers.keys()))

    await run_server(mode=args.mode, host=args.host, port=args.port)
