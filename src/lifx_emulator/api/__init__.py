"""FastAPI-based management API for LIFX emulator.

This package provides a comprehensive REST API for managing the LIFX emulator:
- Monitoring server statistics and activity
- Creating, listing, and deleting devices
- Managing test scenarios for protocol testing

The API is built with FastAPI and organized into routers for clean separation
of concerns.
"""

# Import from new refactored structure
from lifx_emulator.api.app import create_api_app, run_api_server

# Note: HTML_UI remains in the old lifx_emulator/api.py file temporarily
# TODO: Phase 1.1d - extract HTML template to separate file

__all__ = ["create_api_app", "run_api_server"]
