"""FastAPI application factory for LIFX emulator management API.

This module creates the main FastAPI application by assembling routers for:
- Monitoring (server stats, activity)
- Devices (CRUD operations)
- Scenarios (test scenario management)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator.api.routers.devices import create_devices_router
from lifx_emulator.api.routers.monitoring import create_monitoring_router
from lifx_emulator.api.routers.scenarios import create_scenarios_router

logger = logging.getLogger(__name__)

# Template directory for web UI
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_api_app(server: EmulatedLifxServer) -> FastAPI:
    """Create FastAPI application for emulator management.

    This factory function assembles the complete API by:
    1. Creating the FastAPI app with metadata
    2. Including routers for monitoring, devices, and scenarios
    3. Serving the embedded web UI at the root endpoint

    Args:
        server: The LIFX emulator server instance

    Returns:
        Configured FastAPI application

    Example:
        >>> from lifx_emulator.server import EmulatedLifxServer
        >>> server = EmulatedLifxServer(bind="127.0.0.1", port=56700)
        >>> app = create_api_app(server)
        >>> # Run with: uvicorn app:app --host 127.0.0.1 --port 8080
    """
    app = FastAPI(
        title="LIFX Emulator API",
        description="""
Runtime management and monitoring API for LIFX device emulator.

This API provides read-only monitoring of the emulator state and device management
capabilities (add/remove devices). Device state changes must be performed via the
LIFX LAN protocol.

## Features
- Real-time server statistics and packet monitoring
- Device inspection and management
- Test scenario management for protocol testing
- Recent activity tracking
- OpenAPI 3.1.0 compliant schema

## Architecture
The API is organized into three main routers:
- **Monitoring**: Server stats and activity logs
- **Devices**: Device CRUD operations
- **Scenarios**: Test scenario configuration
        """,
        version="1.0.0",
        contact={
            "name": "LIFX Emulator",
            "url": "https://github.com/Djelibeybi/lifx-emulator",
        },
        license_info={
            "name": "UPL-1.0",
            "url": "https://opensource.org/licenses/UPL",
        },
        openapi_tags=[
            {
                "name": "monitoring",
                "description": "Server statistics and activity monitoring",
            },
            {
                "name": "devices",
                "description": "Device management and inspection",
            },
            {
                "name": "scenarios",
                "description": "Test scenario management",
            },
        ],
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root(request: Request):
        """Serve embedded web UI dashboard."""
        return templates.TemplateResponse(request, "dashboard.html")

    # Include routers with server dependency injection
    monitoring_router = create_monitoring_router(server)
    devices_router = create_devices_router(server)
    scenarios_router = create_scenarios_router(server)

    app.include_router(monitoring_router)
    app.include_router(devices_router)
    app.include_router(scenarios_router)

    logger.info(
        "API application created with 3 routers (monitoring, devices, scenarios)"
    )

    return app


async def run_api_server(
    server: EmulatedLifxServer, host: str = "127.0.0.1", port: int = 8080
):
    """Run the FastAPI server with uvicorn.

    Args:
        server: The LIFX emulator server instance
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8080)

    Example:
        >>> import asyncio
        >>> from lifx_emulator.server import EmulatedLifxServer
        >>> server = EmulatedLifxServer(bind="127.0.0.1", port=56700)
        >>> asyncio.run(run_api_server(server, host="0.0.0.0", port=8080))
    """
    import uvicorn

    app = create_api_app(server)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    api_server = uvicorn.Server(config)

    logger.info("Starting API server on http://%s:%s", host, port)
    logger.info("OpenAPI docs available at http://%s:%s/docs", host, port)
    logger.info("ReDoc docs available at http://%s:%s/redoc", host, port)

    await api_server.serve()
