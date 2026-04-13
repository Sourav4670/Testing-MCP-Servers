import asyncio
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


TEST_ARGS: dict[str, Any] = {
    "origin": "London",
    "destination": "Paris",
    "travel_date": "2026-06-15",
}


async def call_sse(base_url: str = "http://127.0.0.1:8081/sse") -> str:
    async with sse_client(base_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_travel_advice", TEST_ARGS)
            text = result.content[0].text if result.content else ""
            assert "Weather" in text
            assert "Travel Safety" in text
            return text


async def call_streamable_http(base_url: str = "http://127.0.0.1:8082/mcp") -> str:
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_travel_advice", TEST_ARGS)
            text = result.content[0].text if result.content else ""
            assert "Weather" in text
            assert "Travel Safety" in text
            return text


async def main() -> None:
    sse_text = await call_sse()
    print("SSE test: PASS")
    print(sse_text[:220].replace("\n", " ") + "...")

    stream_text = await call_streamable_http()
    print("Streamable HTTP test: PASS")
    print(stream_text[:220].replace("\n", " ") + "...")


if __name__ == "__main__":
    asyncio.run(main())
