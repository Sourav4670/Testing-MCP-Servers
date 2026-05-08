# Simple Calculator MCP Server

A production-ready Model Context Protocol (MCP) server that exposes calculator tools.

It supports all three transports:
- stdio
- SSE
- streamable-http

For container deployment, streamable-http is the default transport.

## Folder Structure

```text
simple-calculator-tool/
|-- Dockerfile
|-- LICENSE
|-- mcp.example.json
|-- pyproject.toml
|-- README.md
|-- server.py
|-- tests/
|   |-- __init__.py
|   `-- test_calculator_tool.py
`-- tools/
    |-- __init__.py
    |-- calculator_tool.py
    `-- toolhandler.py
```

## Tools

- add_numbers
- subtract_numbers
- multiply_numbers
- divide_numbers

All tools accept numeric arguments `a` and `b`.

## Local Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

## Run

### stdio (default for MCP desktop hosts)

```bash
python server.py --mode stdio
```

### SSE

```bash
python server.py --mode sse --host 0.0.0.0 --port 8000
```

Endpoints:
- GET /sse
- POST /messages/

### Streamable HTTP

```bash
python server.py --mode streamable-http --host 0.0.0.0 --port 8000
```

Endpoint:
- POST /mcp

Health endpoints:
- GET /health
- GET /healthz
- GET /

## Docker

```bash
# Build image
docker build -t simple-calculator-mcp .

# Run (streamable-http default)
docker run -p 8000:8000 simple-calculator-mcp
```

## Example MCP Config

See mcp.example.json and set `cwd` to your local absolute path.
