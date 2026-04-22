# Real-Time Weather Advisor - MCP Server

A production-ready Model Context Protocol (MCP) server that provides
deterministic weather advisory through a single tool: `get_weather`.

- Uses Open-Meteo for weather and Nominatim for geocoding.
- Supports three transport modes: stdio, SSE, and Streamable HTTP.
- Uses a flat package layout (no `src/` directory).

## Folder Structure

```text
simple-weather-mcp/
|-- Dockerfile
|-- pyproject.toml               <- package metadata and dependencies
|-- README.md
|-- server.py                    <- MCP server + all 3 transport modes
|-- mcp.example.json             <- sample local MCP client config
|-- tests/
`-- tools/
    |-- __init__.py
    |-- toolhandler.py           <- abstract ToolHandler interface
    `-- weather_tool.py          <- GetWeatherToolHandler implementation
```

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

## Running the Server

### 1. stdio mode (default)

```bash
simple-weather-mcp
# or
python server.py --mode stdio
```

### 2. SSE mode

```bash
simple-weather-mcp --mode sse --host 0.0.0.0 --port 8080
```

Endpoints:
- `GET /sse`
- `POST /messages/`

### 3. Streamable HTTP mode

```bash
simple-weather-mcp --mode streamable-http --host 0.0.0.0 --port 8080
```

Endpoint:
- `POST /mcp`
- `GET /health` (health check)
- `GET /healthz` (health check)
- `GET /` (basic readiness check)

Environment variables supported (for container/Kubernetes deployments):
- `TRANSPORT_TYPE`: `SSE` or `STREAMABLE_HTTP`
- `APP_HOST`: bind host (default `0.0.0.0`)
- `APP_PORT`: bind port (default `8080`)

## Docker

```bash
# Build
docker build -t simple-weather-mcp .

# Run in streamable-http mode (default)
docker run -p 5051:5051 simple-weather-mcp

# Run in SSE mode
docker run -p 5051:5051 simple-weather-mcp --mode sse --host 0.0.0.0 --port 5051

# Run with environment-based startup (matches ARM deployment style)
docker run -e TRANSPORT_TYPE=STREAMABLE_HTTP -e APP_PORT=5052 -p 5052:5052 simple-weather-mcp
```

## Tool Reference: `get_weather`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `city_name` | string | yes | City name like `London`, `Tokyo`, or `New York` |

Returns weather details including temperature, wind speed, and day/night status.

## Architecture Diagram

```text
MCP Client (Claude/Cursor/VS Code)
    |
    | JSON-RPC 2.0
    v
Transport Layer (stdio | SSE | HTTP)   <- server.py
    |
    v
MCP Server callbacks (list_tools / call_tool)
    |
    v
ToolHandler Registry                   <- server.py _tool_handlers
    |
    v
GetWeatherToolHandler                  <- weather_tool.py
    |
    v
OpenMeteoTool (Nominatim + Open-Meteo)
```

## Extending the Server

1. Create a new handler in `tools/my_new_tool.py` subclassing `ToolHandler`.
2. Import and register it in `server.py::register_all_tools()`.
3. Add tests under `tests/`.