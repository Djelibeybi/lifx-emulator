"""Pytest configuration for LIFX Emulator App tests."""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"
