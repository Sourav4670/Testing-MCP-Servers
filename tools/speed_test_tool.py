"""
speed_test_tool.py – MCP Tool Handlers for Internet Speed Tests

This module contains the tool handlers for measuring download speed,
upload speed, latency, and jitter. All measurements use incremental
testing methodology inspired by SpeedOf.Me.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence

import httpx

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .toolhandler import ToolHandler

logger = logging.getLogger("internet-speed-test")

# Default URLs for testing
GITHUB_USERNAME = "inventer-dev"
GITHUB_REPO = "speed-test-files"
GITHUB_BRANCH = "main"

GITHUB_MEDIA_URL = (
    f"https://media.githubusercontent.com/media/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}"
)

DEFAULT_DOWNLOAD_URLS = {
    "128KB": f"{GITHUB_MEDIA_URL}/128KB.bin",
    "256KB": f"{GITHUB_MEDIA_URL}/256KB.bin",
    "512KB": f"{GITHUB_MEDIA_URL}/512KB.bin",
    "1MB": f"{GITHUB_MEDIA_URL}/1MB.bin",
    "2MB": f"{GITHUB_MEDIA_URL}/2MB.bin",
    "4MB": f"{GITHUB_MEDIA_URL}/4MB.bin",
    "8MB": f"{GITHUB_MEDIA_URL}/8MB.bin",
    "16MB": f"{GITHUB_MEDIA_URL}/16MB.bin",
    "32MB": f"{GITHUB_MEDIA_URL}/32MB.bin",
    "64MB": f"{GITHUB_MEDIA_URL}/64MB.bin",
    "128MB": f"{GITHUB_MEDIA_URL}/128MB.bin",
}

UPLOAD_ENDPOINTS = [
    {
        "url": "https://httpi.dev/",
        "name": "Cloudflare Workers (Global)",
        "provider": "Cloudflare",
        "priority": 1,
    },
    {
        "url": "https://httpbin.org/",
        "name": "HTTPBin (AWS)",
        "provider": "AWS",
        "priority": 2,
    },
]

DEFAULT_UPLOAD_URL = UPLOAD_ENDPOINTS[0]["url"] + "post"
DEFAULT_LATENCY_URL = UPLOAD_ENDPOINTS[0]["url"] + "get"

UPLOAD_SIZES = {
    "128KB": 128 * 1024,
    "256KB": 256 * 1024,
    "512KB": 512 * 1024,
    "1MB": 1 * 1024 * 1024,
    "2MB": 2 * 1024 * 1024,
    "4MB": 4 * 1024 * 1024,
    "8MB": 8 * 1024 * 1024,
    "16MB": 16 * 1024 * 1024,
    "32MB": 32 * 1024 * 1024,
    "64MB": 64 * 1024 * 1024,
    "128MB": 128 * 1024 * 1024,
}

DEFAULT_TEST_DURATION = 8.0
MIN_TEST_DURATION = 1.0
MAX_TEST_DURATION = 8.0

SIZE_PROGRESSION = [
    "128KB",
    "256KB",
    "512KB",
    "1MB",
    "2MB",
    "4MB",
    "8MB",
    "16MB",
    "32MB",
    "64MB",
    "128MB",
]


def extract_server_info(headers: dict) -> dict:
    """Extract server information from response headers."""
    server_info = {}
    if "server" in headers:
        server_info["server"] = headers.get("server")
    if "cf-ray" in headers:
        server_info["cloudflare_ray"] = headers.get("cf-ray")
        server_info["provider"] = "Cloudflare"
    return server_info


class MeasureDownloadSpeedToolHandler(ToolHandler):
    """
    Handles the ``measure_download_speed`` MCP tool.

    Uses incremental file sizes to find the optimal test size that takes
    at least 8 seconds to download.
    """

    def __init__(self) -> None:
        super().__init__("measure_download_speed")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Measure Download Speed",
            description=(
                "Measure internet download speed using incremental file sizes. "
                "Starts with small files and progressively increases size until "
                "the test sustains for the specified duration (1-8 seconds)."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "MeasureDownloadSpeedInput",
                "additionalProperties": False,
                "properties": {
                    "size_limit": {
                        "type": "string",
                        "title": "Maximum File Size",
                        "default": "128MB",
                        "enum": SIZE_PROGRESSION,
                        "description": "Maximum file size to test up to",
                    },
                    "sustain_time": {
                        "type": "integer",
                        "title": "Sustain Time (seconds)",
                        "default": 8,
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Target duration for each download test (1-8 seconds)",
                    },
                },
                "required": [],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute download speed test."""
        size_limit = args.get("size_limit", "128MB")
        sustain_time = max(
            MIN_TEST_DURATION,
            min(MAX_TEST_DURATION, float(args.get("sustain_time", DEFAULT_TEST_DURATION))),
        )

        logger.info(
            "Starting download speed test: size_limit=%s, sustain_time=%s",
            size_limit,
            sustain_time,
        )

        results = []
        final_result = None

        max_index = (
            SIZE_PROGRESSION.index(size_limit)
            if size_limit in SIZE_PROGRESSION
            else len(SIZE_PROGRESSION) - 1
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            for size_key in SIZE_PROGRESSION[: max_index + 1]:
                url = DEFAULT_DOWNLOAD_URLS[size_key]
                start = time.time()
                total_size = 0
                current_result = None

                try:
                    async with client.stream("GET", url) as response:
                        server_info = extract_server_info(dict(response.headers))

                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            if chunk:
                                total_size += len(chunk)
                                elapsed_time = time.time() - start

                                speed_mbps = ((total_size * 8) / (1024 * 1024)) / elapsed_time
                                current_result = {
                                    "download_speed": round(speed_mbps, 2),
                                    "elapsed_time": round(elapsed_time, 2),
                                    "data_size": total_size,
                                    "size": size_key,
                                    "url": url,
                                    "server_info": server_info,
                                }

                                if elapsed_time >= sustain_time:
                                    break

                    if current_result is None:
                        elapsed_time = time.time() - start
                        current_result = {
                            "download_speed": 0,
                            "elapsed_time": round(elapsed_time, 2),
                            "data_size": total_size,
                            "size": size_key,
                            "url": url,
                            "server_info": server_info if total_size > 0 else None,
                        }

                    results.append(current_result)
                    final_result = current_result

                    if current_result["elapsed_time"] >= sustain_time:
                        break

                except Exception as e:
                    logger.error("Error during download test for %s: %s", size_key, e)
                    continue

        if final_result:
            response_text = (
                f"**Download Speed Test Results**\n\n"
                f"- **Speed**: {final_result['download_speed']} Mbps\n"
                f"- **File Size**: {final_result['size']}\n"
                f"- **Elapsed Time**: {final_result['elapsed_time']}s\n"
                f"- **Data Transferred**: {final_result['data_size'] / (1024 * 1024):.2f} MB\n"
            )
            if final_result.get("server_info"):
                response_text += f"- **Server**: {json.dumps(final_result['server_info'])}\n"

            return [TextContent(type="text", text=response_text)]
        else:
            return [
                TextContent(
                    type="text",
                    text="Download speed test failed. Unable to reach test servers.",
                )
            ]


class MeasureUploadSpeedToolHandler(ToolHandler):
    """
    Handles the ``measure_upload_speed`` MCP tool.

    Uses incremental file sizes to find the optimal test size that takes
    at least 8 seconds to upload.
    """

    def __init__(self) -> None:
        super().__init__("measure_upload_speed")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Measure Upload Speed",
            description=(
                "Measure internet upload speed using incremental file sizes. "
                "Starts with small files and progressively increases size until "
                "the test sustains for the specified duration (1-8 seconds)."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "MeasureUploadSpeedInput",
                "additionalProperties": False,
                "properties": {
                    "size_limit": {
                        "type": "string",
                        "title": "Maximum File Size",
                        "default": "128MB",
                        "enum": SIZE_PROGRESSION,
                        "description": "Maximum file size to test up to",
                    },
                    "sustain_time": {
                        "type": "integer",
                        "title": "Sustain Time (seconds)",
                        "default": 8,
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Target duration for each upload test (1-8 seconds)",
                    },
                },
                "required": [],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute upload speed test."""
        size_limit = args.get("size_limit", "128MB")
        sustain_time = max(
            MIN_TEST_DURATION,
            min(MAX_TEST_DURATION, float(args.get("sustain_time", DEFAULT_TEST_DURATION))),
        )

        logger.info(
            "Starting upload speed test: size_limit=%s, sustain_time=%s",
            size_limit,
            sustain_time,
        )

        results = []
        final_result = None

        max_index = (
            SIZE_PROGRESSION.index(size_limit)
            if size_limit in SIZE_PROGRESSION
            else len(SIZE_PROGRESSION) - 1
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            for size_key in SIZE_PROGRESSION[: max_index + 1]:
                upload_size = UPLOAD_SIZES[size_key]
                data = b"x" * upload_size

                start = time.time()
                current_result = None

                try:
                    response = await client.post(DEFAULT_UPLOAD_URL, content=data)
                    elapsed_time = time.time() - start

                    speed_mbps = ((upload_size * 8) / (1024 * 1024)) / elapsed_time
                    current_result = {
                        "upload_speed": round(speed_mbps, 2),
                        "elapsed_time": round(elapsed_time, 2),
                        "data_size": upload_size,
                        "size": size_key,
                        "url": DEFAULT_UPLOAD_URL,
                        "status_code": response.status_code,
                    }

                    results.append(current_result)
                    final_result = current_result

                    if elapsed_time >= sustain_time:
                        break

                except Exception as e:
                    logger.error("Error during upload test for %s: %s", size_key, e)
                    continue

        if final_result:
            response_text = (
                f"**Upload Speed Test Results**\n\n"
                f"- **Speed**: {final_result['upload_speed']} Mbps\n"
                f"- **File Size**: {final_result['size']}\n"
                f"- **Elapsed Time**: {final_result['elapsed_time']}s\n"
                f"- **Data Transferred**: {final_result['data_size'] / (1024 * 1024):.2f} MB\n"
                f"- **Status Code**: {final_result['status_code']}\n"
            )

            return [TextContent(type="text", text=response_text)]
        else:
            return [
                TextContent(
                    type="text",
                    text="Upload speed test failed. Unable to reach upload endpoint.",
                )
            ]


class MeasureLatencyToolHandler(ToolHandler):
    """
    Handles the ``measure_latency`` MCP tool.

    Measures round-trip time (latency) by making multiple small HTTP requests
    and calculating average, min, and max latency.
    """

    def __init__(self) -> None:
        super().__init__("measure_latency")

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Measure Latency",
            description=(
                "Measure network latency (round-trip time) by making multiple "
                "small HTTP requests to a test server."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "MeasureLatencyInput",
                "additionalProperties": False,
                "properties": {
                    "num_pings": {
                        "type": "integer",
                        "title": "Number of Pings",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Number of ping requests to send (1-50)",
                    },
                },
                "required": [],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute latency measurement."""
        num_pings = min(50, max(1, int(args.get("num_pings", 10))))

        logger.info("Starting latency measurement: num_pings=%s", num_pings)

        latencies = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for _ in range(num_pings):
                try:
                    start = time.time()
                    await client.get(DEFAULT_LATENCY_URL)
                    elapsed_ms = (time.time() - start) * 1000
                    latencies.append(elapsed_ms)
                except Exception as e:
                    logger.error("Ping failed: %s", e)
                    continue

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            response_text = (
                f"**Latency Measurement Results**\n\n"
                f"- **Average Latency**: {avg_latency:.2f} ms\n"
                f"- **Min Latency**: {min_latency:.2f} ms\n"
                f"- **Max Latency**: {max_latency:.2f} ms\n"
                f"- **Successful Pings**: {len(latencies)}/{num_pings}\n"
            )

            return [TextContent(type="text", text=response_text)]
        else:
            return [
                TextContent(
                    type="text",
                    text="Latency measurement failed. Unable to reach test server.",
                )
            ]


class RunFullSpeedTestToolHandler(ToolHandler):
    """
    Handles the ``run_full_speed_test`` MCP tool.

    Runs a complete speed test including download speed, upload speed,
    and latency measurements.
    """

    def __init__(self) -> None:
        super().__init__("run_full_speed_test")
        self.download_handler = MeasureDownloadSpeedToolHandler()
        self.upload_handler = MeasureUploadSpeedToolHandler()
        self.latency_handler = MeasureLatencyToolHandler()

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Run Full Speed Test",
            description=(
                "Run a comprehensive internet speed test including download speed, "
                "upload speed, and latency measurements."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "RunFullSpeedTestInput",
                "additionalProperties": False,
                "properties": {
                    "test_size": {
                        "type": "string",
                        "title": "Test Size",
                        "default": "64MB",
                        "enum": SIZE_PROGRESSION,
                        "description": "Maximum file size to test up to",
                    },
                },
                "required": [],
            },
        )

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute full speed test."""
        test_size = args.get("test_size", "64MB")

        logger.info("Starting full speed test with test_size=%s", test_size)

        results = []

        # Download speed
        download_result = await self.download_handler.run_tool(
            {"size_limit": test_size, "sustain_time": 8}
        )
        if download_result:
            results.append(download_result[0].text)

        # Upload speed
        upload_result = await self.upload_handler.run_tool(
            {"size_limit": test_size, "sustain_time": 8}
        )
        if upload_result:
            results.append(upload_result[0].text)

        # Latency
        latency_result = await self.latency_handler.run_tool({"num_pings": 10})
        if latency_result:
            results.append(latency_result[0].text)

        combined_text = "\n\n".join(results)

        return [TextContent(type="text", text=combined_text)]
