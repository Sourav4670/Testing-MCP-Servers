# Real-Time Travel Advisor – MCP Server

A **production-ready Model Context Protocol (MCP) server** that provides
deterministic, real-time-style travel advisory through a single tool:
`get_travel_advice`.

- **No external APIs** – all knowledge is embedded in `travel_data.py`
- **No environment variables** – everything is configured via CLI flags
- **Three transport modes** – stdio, SSE, and Streamable HTTP
- **Deterministic responses** – same input always produces the same output

---

## Folder Structure

```
travel-advisor-mcp/
├── Dockerfile
├── pytest.ini
├── pyproject.toml               ← package metadata & dependencies
├── README.md
├── src/
│   └── travel_advisor/
│       ├── __init__.py          ← sync entry-point (main())
│       ├── __main__.py          ← python -m travel_advisor
│       ├── server.py            ← MCP server + all 3 transport modes
│       └── tools/
│           ├── __init__.py      ← re-exports for convenient import
│           ├── toolhandler.py   ← abstract base class ToolHandler
│           ├── travel_data.py   ← static knowledge base (cities, routes, seasons)
│           └── travel_tool.py   ← GetTravelAdviceToolHandler implementation
└── tests/
    └── test_travel_advisor.py   ← deterministic unit + integration tests
```

---

## Installation

```bash
cd travel-advisor-mcp

# Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install the package (editable mode for development)
pip install -e .
```

---

## Running the Server

### 1. stdio mode (default — for Claude Desktop, Cursor, VS Code MCP)

stdio mode communicates over standard input / output.  No network port is
opened.  This is the mode used by all local MCP host applications.

```bash
# 1. stdio mode (Claude Desktop / Cursor / VS Code)
python -m travel_advisor
# or equivalently:
python -m travel_advisor --mode stdio

# 2. SSE mode  
python -m travel_advisor --mode sse --port 5000
# endpoints: GET /sse  |  POST /messages/

# 3. Streamable HTTP mode (MCP v1 preferred)
python -m travel_advisor --mode streamable-http --port 5000
# endpoint: POST /mcp  (chunked streaming responses)
```

**How it works inside the code (`server.py`):**

```
stdin ──► SseServerTransport / stdio_server ──► MCP Server
                                                    │
                                                  list_tools
                                                  call_tool
                                                    │
stdout ◄─── JSON-RPC responses ◄────────────────────┘
```

The `mcp.server.stdio.stdio_server()` context manager connects the process's
`sys.stdin` / `sys.stdout` to the MCP read/write streams.

**Claude Desktop config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "travel-advisor": {
      "command": "python",
      "args": ["-m", "travel_advisor"],
      "cwd": "C:/path/to/travel-advisor-mcp"
    }
  }
}
```

---

### 2. SSE mode (legacy HTTP streaming)

SSE mode exposes **two** HTTP endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sse` | GET | Client opens a persistent Server-Sent Events stream |
| `/messages/` | POST | Client sends MCP JSON-RPC messages |

```bash
python -m travel_advisor --mode sse --host 0.0.0.0 --port 8080
```

**How it works inside the code (`server.py`):**

```
Client                      Starlette (SSE transport)          MCP Server
  │── GET /sse ──────────────► SSEEndpoint.__call__()
  │                              connect_sse() ─────────────►  app.run()
  │◄══════ SSE frames ══════════ write_stream ◄──────────────  responses
  │
  │── POST /messages/ body ──► handle_post_message()
  │                              read_stream ──────────────►   call_tool / list_tools
```

**Example MCP client call (Python `httpx-sse`):**

```python
import httpx
from httpx_sse import connect_sse

with httpx.Client() as client:
    with connect_sse(client, "GET", "http://localhost:8080/sse") as event_source:
        # Send initialize
        client.post("http://localhost:8080/messages/", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "clientInfo": {"name": "test", "version": "1.0"},
                       "capabilities": {}}
        })
        # Read events
        for event in event_source.iter_sse():
            print(event.data)
```

**Using `mcp` Python SDK:**

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def call_tool():
    async with sse_client("http://localhost:8080/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_travel_advice", {
                "origin": "London",
                "destination": "Paris",
                "travel_date": "2026-06-15",
            })
            print(result.content[0].text)

asyncio.run(call_tool())
```

---

### 3. Streamable HTTP mode (MCP v1 preferred HTTP transport)

Streamable HTTP exposes a **single** endpoint:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | All MCP traffic; responses delivered as HTTP chunked streams |

```bash
python -m travel_advisor --mode streamable-http --host 0.0.0.0 --port 8080
```

**How it works inside the code (`server.py`):**

```
Client                 Starlette (/mcp)           SessionManager          MCP Server
  │── POST /mcp ──────► StreamableHTTPRoute
  │   (initialize)       handle_request() ──────► create/find session
  │◄── mcp-session-id ◄── response headers
  │
  │── POST /mcp ──────► StreamableHTTPRoute
  │   (call_tool)         handle_request() ──────► session.run_tool()
  │◄══ chunked stream ◄═══════════════════════════ streaming response
```

`StreamableHTTPSessionManager` maintains per-client session state tracked by
the `mcp-session-id` header.  Responses are HTTP chunked-transfer-encoded so
the client receives content incrementally.

**Using `mcp` Python SDK (streamable-http):**

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def call_tool():
    async with streamablehttp_client("http://localhost:8080/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_travel_advice", {
                "origin": "Tokyo",
                "destination": "Singapore",
                "travel_date": "2026-09-10",
            })
            print(result.content[0].text)

asyncio.run(call_tool())
```

**Raw HTTP example (curl):**

```bash
# Step 1 – initialize and get session ID
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "clientInfo":{"name":"curl-client","version":"1.0"},
      "capabilities":{}
    }
  }'

# Step 2 – call the tool (replace SESSION_ID with value from mcp-session-id header)
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: SESSION_ID" \
  -d '{
    "jsonrpc":"2.0","id":2,"method":"tools/call",
    "params":{
      "name":"get_travel_advice",
      "arguments":{
        "origin":"Dubai",
        "destination":"Bangkok",
        "travel_date":"2026-12-01"
      }
    }
  }'
```

---

## Docker

```bash
# Build
docker build -t travel-advisor-mcp .

# Run in streamable-http mode (default)
docker run -p 8080:8080 travel-advisor-mcp

# Run in SSE mode
docker run -p 8080:8080 travel-advisor-mcp --mode sse --host 0.0.0.0 --port 8080
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

All tests are **deterministic** and require no network access.

---

## Tool Reference: `get_travel_advice`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `origin` | string | ✅ | Departure city (e.g. `"London"`) |
| `destination` | string | ✅ | Arrival city (e.g. `"Paris"`) |
| `travel_date` | string | ✅ | ISO date, month-year, or natural language |

**Date formats accepted:**

| Format | Example |
|--------|---------|
| ISO 8601 | `"2026-06-15"` |
| Month Year | `"June 2026"`, `"Dec 2026"` |
| Season | `"next summer"`, `"winter 2027"` |
| Year only | `"2026"` → Jan 1 2026 |

**Response sections:**

1. 🌤️ **Weather Expectations** – season, climate type, expected conditions, packing list
2. 🛡️ **Travel Safety** – safety rating, practical tips, documents needed
3. 🚆 **Recommended Transport Mode** – best option for the specific route, local transport tips
4. 📊 **Peak / Off-Peak Timing** – crowd and price assessment for the travel month
5. 🏛️ **Popular Attractions** – top 5 curated attractions at the destination

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                  MCP Client (Claude, Cursor, etc.)        │
└─────────────────────┬────────────────────────────────────┘
                      │  JSON-RPC 2.0
          ┌───────────▼────────────┐
          │   Transport Layer      │
          │  stdio | SSE | HTTP    │   ← server.py
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │   MCP Server (app)     │   ← mcp.server.Server
          │  list_tools()          │
          │  call_tool()           │
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │  ToolHandler Registry  │   ← server.py _tool_handlers
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │GetTravelAdviceToolHandler│ ← travel_tool.py
          └───────────┬────────────┘
                      │
          ┌───────────▼────────────┐
          │   travel_data.py       │   ← pure static knowledge base
          │  CITY_DATA             │
          │  ATTRACTIONS           │
          │  ROUTE_DATA            │
          │  MONTH_PROFILES        │
          └────────────────────────┘
```

---

## Extending the Server

Adding a new tool takes three steps:

1. **Create a new handler** in `src/travel_advisor/tools/my_new_tool.py`
   subclassing `ToolHandler`.
2. **Import and register** it in `server.py::register_all_tools()`.
3. **Add tests** in `tests/test_travel_advisor.py`.

No changes to the transport layer, protocol callbacks, or any other file.
