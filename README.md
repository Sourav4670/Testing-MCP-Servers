# Internet Speed Test – MCP Server

A **production-ready Model Context Protocol (MCP) server** that provides
real-time internet speed measurements through multiple tools:

- **Download Speed** – Measure download bandwidth using incremental file sizes
- **Upload Speed** – Measure upload bandwidth using incremental file sizes
- **Latency** – Measure round-trip time (ping latency)
- **Full Speed Test** – Run all measurements in one go

- **No external API dependencies** – uses public HTTP endpoints
- **No environment variables** – everything is configured via CLI flags
- **Three transport modes** – stdio, SSE, and Streamable HTTP
- **Deterministic responses** – predictable output for reliable integration

---

## Folder Structure

```
internet-speed-check/
├── Dockerfile
├── pyproject.toml               ← package metadata & dependencies
├── README.md
├── server.py                    ← MCP server + all 3 transport modes
└── tools/
  ├── __init__.py              ← package marker
  ├── toolhandler.py           ← abstract base class ToolHandler
  └── speed_test_tool.py       ← speed test tool handlers
```

## Installation

```bash
mkdir inetrnet-speed-test
 
cd inetrnet-speed-test

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

## Features & Architecture

### Tools

#### 1. `measure_download_speed`
Measures internet download speed using incremental file sizes.

**Parameters:**
- `size_limit` (string, default: `"128MB"`): Maximum file size to test up to
- `sustain_time` (integer, default: `8`): Target duration for each test (1-8 seconds)

**Returns:**
- Download speed in Mbps
- File size used for measurement
- Elapsed time
- Total data transferred
- Server information

#### 2. `measure_upload_speed`
Measures internet upload speed using incremental file sizes.

**Parameters:**
- `size_limit` (string, default: `"128MB"`): Maximum file size to test up to
- `sustain_time` (integer, default: `8`): Target duration for each test (1-8 seconds)

**Returns:**
- Upload speed in Mbps
- File size used for measurement
- Elapsed time
- Total data transferred
- HTTP status code

#### 3. `measure_latency`
Measures network latency by making multiple ping requests.

**Parameters:**
- `num_pings` (integer, default: `10`): Number of ping requests (1-50)

**Returns:**
- Average latency in milliseconds
- Minimum latency
- Maximum latency
- Number of successful pings

#### 4. `run_full_speed_test`
Runs a comprehensive speed test (download + upload + latency).

**Parameters:**
- `test_size` (string, default: `"64MB"`): Maximum file size to use

**Returns:**
- Combined results from all three measurements

---

## Transport Modes

### 1. **stdio** (default)
Used by Claude Desktop, Cursor, and most MCP host applications.

```bash
python server.py
```

### 2. **SSE** (legacy HTTP)
For browser-based clients and simple HTTP proxies.

```bash
python server.py --mode sse --host 0.0.0.0 --port 8080
```

Endpoints:
- `GET  /sse` – open an SSE stream
- `POST /messages/` – send MCP messages

### 3. **Streamable HTTP** (MCP v1 preferred)
Modern HTTP streaming with session support.

```bash
python server.py --mode streamable-http --host 0.0.0.0 --port 8080
```

Endpoint:
- `POST /mcp` – all MCP traffic (responses are chunked streams)

---

## Installation & Usage

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd internet-speed-check
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

### Running the Server

#### stdio mode (default):
```bash
python server.py
```

#### SSE mode:
```bash
python server.py --mode sse --port 8080
```

#### Streamable HTTP mode:
```bash
python server.py --mode streamable-http --port 8080
```

---

## Example Usage with Claude

In **Claude Settings > Model Preferences > MCP Servers**, add:

```json
{
  "mcpServers": {
    "internet-speed-check": {
      "command": "python",
      "args": [
        "C:\\path\\to\\server.py",
        "--mode",
        "stdio"
      ],
      "cwd": "C:\\path\\to\\internet-speed-check"
    }
  }
}
```

Then ask Claude:
- *"Run a full speed test on my connection"*
- *"What's my download speed?"*
- *"Measure my latency"*

---

## Architecture

The server uses a modular **tool handler** pattern:

```
┌────────────────────────────┐
│  server.py                 │  ← Main entry-point & transport modes
│  - Tool registry           │
│  - MCP callbacks           │
│  - CLI argument parsing    │
└────────────┬───────────────┘
             │
    ┌────────┴────────┬─────────────┬──────────────┐
    │                 │             │              │
┌───▼──────────┐ ┌───▼──────────┐ ┌▼──────────┐ ┌▼──────────┐
│ Download     │ │ Upload       │ │ Latency  │ │Full Test │
│ SpeedHandler │ │ SpeedHandler │ │ Handler  │ │ Handler  │
└──────┬───────┘ └──────┬───────┘ └──┬───────┘ └──┬───────┘
       │                │             │            │
       └────────────────┼─────────────┴────────────┘
                        │
                 ┌──────▼──────────┐
                 │ ToolHandler    │
                 │ (abstract base)│
                 └─────────────────┘
```

**Key Design Principles:**

1. **Modular** – Each tool is a separate handler class
2. **Extensible** – Easy to add new tools
3. **Production-ready** – Proper logging, error handling, and async support
4. **Multi-transport** – Works over stdio, SSE, or Streamable HTTP
5. **No external state** – Stateless design simplifies deployment

---

## Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest -v

# Run a specific test file
pytest tests/test_speed_test_tool.py -v
```

If no tests are present yet, `pytest` may report "collected 0 items".

---

## Manual Testing

```bash
# Run a quick download test
python -c "
import asyncio
from tools.speed_test_tool import MeasureDownloadSpeedToolHandler

async def test():
    handler = MeasureDownloadSpeedToolHandler()
    result = await handler.run_tool({'size_limit': '1MB'})
    print(result[0].text)

asyncio.run(test())
"
```

---

## Deployment

The server can be deployed in Docker or as a systemd service:

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENTRYPOINT ["python", "server.py"]
CMD ["--mode", "stdio"]
```

### systemd (for HTTP modes)
```ini
[Unit]
Description=Internet Speed Test MCP Server
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/internet-speed-check
ExecStart=/usr/bin/python /opt/internet-speed-check/server.py --mode sse --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Extending the Server

Adding a new tool takes three steps:

1. Create a new handler in `tools/my_new_tool.py` subclassing `ToolHandler`.
2. Import and register it in `server.py::register_all_tools()`.
3. (Recommended) Add tests under `tests/` folder.

No changes to the transport layer, protocol callbacks, or any other file.

---

## Performance Notes

- **Download tests**: Typically 8–60 seconds depending on connection speed
- **Upload tests**: Typically 8–120 seconds depending on connection speed
- **Latency tests**: 10 pings ≈ 1 second

For faster results, use smaller `size_limit` or `sustain_time` parameters.

---

## License

MIT – See LICENSE file for details
