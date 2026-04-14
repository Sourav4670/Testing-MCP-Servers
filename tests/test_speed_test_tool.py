"""Tests for the speed test tools."""

import pytest
from tools.speed_test_tool import (
    MeasureDownloadSpeedToolHandler,
    MeasureUploadSpeedToolHandler,
    MeasureLatencyToolHandler,
    RunFullSpeedTestToolHandler,
)


class TestMeasureDownloadSpeedToolHandler:
    """Test cases for download speed measurement."""

    @pytest.mark.asyncio
    async def test_download_speed_handler_exists(self):
        """Verify the download speed handler can be instantiated."""
        handler = MeasureDownloadSpeedToolHandler()
        assert handler is not None
        assert handler.name == "measure_download_speed"

    @pytest.mark.asyncio
    async def test_download_speed_handler_description(self):
        """Verify the download speed handler has a proper description."""
        handler = MeasureDownloadSpeedToolHandler()
        desc = handler.get_tool_description()
        assert desc.name == "measure_download_speed"
        assert desc.description is not None
        assert len(desc.description) > 0


class TestMeasureUploadSpeedToolHandler:
    """Test cases for upload speed measurement."""

    @pytest.mark.asyncio
    async def test_upload_speed_handler_exists(self):
        """Verify the upload speed handler can be instantiated."""
        handler = MeasureUploadSpeedToolHandler()
        assert handler is not None
        assert handler.name == "measure_upload_speed"

    @pytest.mark.asyncio
    async def test_upload_speed_handler_description(self):
        """Verify the upload speed handler has a proper description."""
        handler = MeasureUploadSpeedToolHandler()
        desc = handler.get_tool_description()
        assert desc.name == "measure_upload_speed"
        assert desc.description is not None
        assert len(desc.description) > 0


class TestMeasureLatencyToolHandler:
    """Test cases for latency measurement."""

    @pytest.mark.asyncio
    async def test_latency_handler_exists(self):
        """Verify the latency handler can be instantiated."""
        handler = MeasureLatencyToolHandler()
        assert handler is not None
        assert handler.name == "measure_latency"

    @pytest.mark.asyncio
    async def test_latency_handler_description(self):
        """Verify the latency handler has a proper description."""
        handler = MeasureLatencyToolHandler()
        desc = handler.get_tool_description()
        assert desc.name == "measure_latency"
        assert desc.description is not None
        assert len(desc.description) > 0


class TestRunFullSpeedTestToolHandler:
    """Test cases for full speed test."""

    @pytest.mark.asyncio
    async def test_full_speed_test_handler_exists(self):
        """Verify the full speed test handler can be instantiated."""
        handler = RunFullSpeedTestToolHandler()
        assert handler is not None
        assert handler.name == "run_full_speed_test"

    @pytest.mark.asyncio
    async def test_full_speed_test_handler_description(self):
        """Verify the full speed test handler has a proper description."""
        handler = RunFullSpeedTestToolHandler()
        desc = handler.get_tool_description()
        assert desc.name == "run_full_speed_test"
        assert desc.description is not None
        assert len(desc.description) > 0
