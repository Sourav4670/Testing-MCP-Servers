from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys
import traceback
from collections.abc import AsyncIterator, Sequence
from typing import Any

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route

from tools.weather_tool import OpenMetoTool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("weather-tool")

# Core MCP app
app = Server("weather-tool-mcp")
weather_tool = OpenMetoTool()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="weather_tool",
            description="Retrieve weather information for a given city using the Open-Meteo API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "The name of the city for which to retrieve weather data.",
                    }
                },
                "required": ["city_name"],
            },
        )
    ]


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Execute a tool."""
    if name != "weather_tool":
        raise ValueError(f"Unknown tool: {name}")

    if arguments is None:
        arguments = {}
    elif not isinstance(arguments, dict):
        try:
            arguments = dict(arguments)
        except Exception:
            raise RuntimeError("Tool arguments must be a dictionary")

    try:
        city_name = arguments.get("city_name")
        if not city_name:
            raise ValueError("city_name is required")
        
        result = weather_tool.weather_tool(city_name)
        return [TextContent(type="text", text=result)]
    except Exception as exc:
        logger.exception("Error running weather_tool: %s", exc)
        return [
            TextContent(
                type="text",
                text=f"Error executing weather_tool: {exc}\n\n{traceback.format_exc()}",
            )
        ]


def create_sse_starlette_app(mcp_server: Server) -> Starlette:
    """Create Starlette app for SSE transport."""
    sse_transport = SseServerTransport("/messages/")

    class _SSEEndpoint:
        async def __call__(self, scope, receive, send) -> None:
            async with sse_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )

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


def create_streamable_http_app(mcp_server: Server) -> Starlette:
    """Create Starlette app for Streamable HTTP transport."""
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=False,
        stateless=False,
    )

    class _MCPRoute:
        async def __call__(self, scope, receive, send) -> None:
            await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def _lifespan(_: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    starlette_app = Starlette(
        debug=False,
        routes=[Route("/mcp", endpoint=_MCPRoute())],
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


async def run_server(mode: str, host: str, port: int) -> None:
    """Run the server with specified transport mode."""
    if mode == "stdio":
        logger.info("Running in STDIO mode")
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
        return

    if mode == "sse":
        logger.info("Running in SSE mode at http://%s:%d/sse", host, port)
        starlette_app = create_sse_starlette_app(app)
        config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
        await uvicorn.Server(config).serve()
        return

    if mode == "streamable_http":
        logger.info("Running in Streamable HTTP mode at http://%s:%d/mcp", host, port)
        starlette_app = create_streamable_http_app(app)
        config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
        await uvicorn.Server(config).serve()
        return

    raise ValueError(f"Unsupported mode: {mode}")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Weather Tool MCP server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "streamable_http"],
        default="stdio",
        help="Transport mode for the MCP server",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (for sse and streamable_http modes)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (for sse and streamable_http modes)",
    )

    args = parser.parse_args()
    await run_server(args.mode, args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())