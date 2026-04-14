"""Pytest configuration and shared fixtures."""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Provide an async HTTP client for testing."""
    import httpx
    async with httpx.AsyncClient() as client:
        yield client
