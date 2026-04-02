# Simple Weather Tool

A Model Context Protocol (MCP) server providing weather information using the Open-Meteo API.

## Overview
This project implements a Model Context Protocol (MCP) server that provides current weather information for any city worldwide. It uses the Open-Meteo API for weather data and OpenStreetMap's Nominatim service for geocoding city names to coordinates.

## Features

- **Weather Information**: Current weather data via Open-Meteo API
- **Geocoding**: City name to coordinates conversion using Nominatim
- **SSL Bypass**: Handles SSL verification issues for reliable API access
- **Comprehensive Data**: Temperature, wind speed, and day/night information

## Architecture

```
├── tools/                  # MCP tool implementations
│   ├── __init__.py
│   └── weather_tool.py     # Weather information tool implementation
├── mcp_server.py           # MCP server implementation
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
├── env.example             # Example environment configuration
├── Dockerfile              # Docker configuration
└── README.md               # Project documentation
```

## Prerequisites

- Python 3.11.9 or higher
- UV package manager (recommended) or pip
- Internet connection for API access

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simple-weather-tool
```

2. Install dependencies using UV:
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

## Usage

Start the MCP server with different transport modes:

### STDIO Mode (Default - Local)
For local integration with Claude Desktop:
```bash
python mcp_server.py --mode stdio
```

### SSE Mode (Server-Sent Events)
For HTTP-based streaming transport:
```bash
python mcp_server.py --mode sse
```
Server will run at `http://0.0.0.0:8080/sse`

### Streamable HTTP Mode
For chunked HTTP streaming with session management:
```bash
python mcp_server.py --mode streamable_http
```
Server will run at `http://0.0.0.0:8080/mcp`

### Custom Host and Port
For SSE or streamable_http modes, customize host and port:
```bash
python mcp_server.py --mode sse --host localhost --port 9000
python mcp_server.py --mode streamable_http --host 127.0.0.1 --port 5000
```

### Command-Line Arguments
```
--mode {stdio,sse,streamable_http}  Transport mode for the MCP server (default: stdio)
--host HOST                          Host to bind to (default: 0.0.0.0)
--port PORT                          Port to bind to (default: 8080)
```

## Available Tools

### Weather Tool
- `weather_tool(city_name)` - Retrieves current weather information for a specified city
  - **Parameters**: 
    - `city_name` (str): The name of the city for which to retrieve weather data
  - **Returns**: String containing current weather information including:
    - Current temperature in Celsius
    - Wind speed in m/s
    - Day/night status
  - **Example**: `weather_tool("New York")` returns "Current temperature in New York is 15°C, with wind speed of 3.2 m/s and it is day time."

## API Integration

### Geocoding Service
- **Provider**: OpenStreetMap Nominatim
- **Purpose**: Convert city names to latitude/longitude coordinates
- **Endpoint**: `https://nominatim.openstreetmap.org/search`

### Weather Service
- **Provider**: Open-Meteo API
- **Purpose**: Retrieve current weather data
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Features**: No API key required, free usage

## Docker

Build and run the Docker container:
```bash
docker build -t simple-weather-tool .

# SSE mode
docker run -p 8080:8080 simple-weather-tool python mcp_server.py --mode sse

# Streamable HTTP mode
docker run -p 8080:8080 simple-weather-tool python mcp_server.py --mode streamable_http
```

## Architecture

This MCP server uses:
- **MCP Server**: Model Context Protocol server implementation
- **Starlette**: Modern web framework for HTTP transports
- **Uvicorn**: ASGI web server for HTTP transport modes

### Transport Modes

| Mode | Use Case | Endpoint |
|------|----------|----------|
| `stdio` | Local integration (Claude Desktop) | stdin/stdout |
| `sse` | HTTP-based streaming | `http://0.0.0.0:8080/sse` |
| `streamable_http` | Chunked HTTP with sessions | `http://0.0.0.0:8080/mcp` |

## Dependencies

- **mcp**: Model Context Protocol server implementation
- **Starlette**: Web application framework
- **Uvicorn**: ASGI web server
- **Requests**: HTTP library for API requests
- **urllib3**: HTTP client with SSL handling

## Configuration

The server runs with the following default configuration:
- **Host**: 0.0.0.0
- **Port**: 8080
- **Transport**: SSE (Server-Sent Events)
- **Name**: "Utility Tools"

## Error Handling

The weather tool includes comprehensive error handling for:
- Invalid city names
- Network connectivity issues
- API service unavailability
- Geocoding failures
- Missing weather data

## Example Usage

```python
# Get weather for major cities
weather_tool("London")        # London, UK weather
weather_tool("Tokyo")         # Tokyo, Japan weather
weather_tool("New York")      # New York, USA weather
weather_tool("Sydney")        # Sydney, Australia weather
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request