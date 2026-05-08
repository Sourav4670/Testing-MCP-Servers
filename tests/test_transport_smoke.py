"""Manual smoke test for SSE and streamable-http calculator transport."""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def call_streamable_http(base_url: str = "http://127.0.0.1:8090/mcp") -> str:
    async with streamablehttp_client(base_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("add_numbers", {"a": 7, "b": 8})
            text = result.content[0].text if result.content else ""
            assert "Result:" in text
            return text


async def main() -> None:
    stream_text = await call_streamable_http()
    print("Streamable HTTP test: PASS")
    print(stream_text)


if __name__ == "__main__":
    asyncio.run(main())
