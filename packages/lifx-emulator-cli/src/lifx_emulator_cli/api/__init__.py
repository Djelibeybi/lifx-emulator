"""FastAPI-based management API for LIFX emulator.

This package provides a comprehensive REST API for managing the LIFX emulator:
- Monitoring server statistics and activity
- Creating, listing, and deleting devices
- Managing test scenarios for protocol testing

The API is built with FastAPI and organized into routers for clean separation
of concerns.
"""

# Import from local API module
from lifx_emulator_cli.api.app import create_api_app, run_api_server

__all__ = ["create_api_app", "run_api_server"]
