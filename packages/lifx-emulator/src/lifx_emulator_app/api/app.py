"""FastAPI application factory for LIFX emulator management API.

This module creates the main FastAPI application by assembling routers for:
- Monitoring (server stats, activity)
- Devices (CRUD operations)
- Scenarios (test scenario management)
- WebSocket (real-time updates)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator_app.api.routers.devices import create_devices_router
from lifx_emulator_app.api.routers.monitoring import create_monitoring_router
from lifx_emulator_app.api.routers.products import create_products_router
from lifx_emulator_app.api.routers.scenarios import create_scenarios_router
from lifx_emulator_app.api.routers.websocket import create_websocket_router
from lifx_emulator_app.api.services.event_bridge import (
    StatsBroadcaster,
    WebSocketActivityObserver,
    WebSocketStateChangeObserver,
    wire_device_events,
    wire_device_state_events,
)
from lifx_emulator_app.api.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

# Asset directory for web UI (Svelte build output)
STATIC_DIR = Path(__file__).parent / "static"


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
    # Create WebSocket manager early so we can reference it in lifespan
    ws_manager = WebSocketManager(server)
    stats_broadcaster = StatsBroadcaster(server, ws_manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application lifecycle - start/stop background tasks."""
        # Startup: start the stats broadcaster
        stats_broadcaster.start()
        yield
        # Shutdown: stop the stats broadcaster
        await stats_broadcaster.stop()

    app = FastAPI(
        lifespan=lifespan,
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
The API is organized into four main routers:
- **Monitoring**: Server stats and activity logs
- **Devices**: Device CRUD operations
- **Scenarios**: Test scenario configuration
- **Products**: LIFX product registry
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
            {
                "name": "products",
                "description": "LIFX product registry",
            },
            {
                "name": "websocket",
                "description": """Real-time updates via WebSocket.

## Connection

Connect to `ws://<host>:<port>/ws` to receive real-time updates.

## Client Messages

### Subscribe to Topics

```json
{"type": "subscribe", "topics": ["stats", "devices", "activity", "scenarios"]}
```

**Available topics:**
- `stats` - Server statistics (pushed every second)
- `devices` - Device add/remove/update events
- `activity` - Packet activity events (requires `--activity` flag)
- `scenarios` - Scenario configuration changes

### Request Full State Sync

```json
{"type": "sync"}
```

Returns current state for all subscribed topics.

## Server Messages

All server messages follow this format:

```json
{"type": "<message_type>", "data": {...}}
```

### Message Types

| Type | Description |
|------|-------------|
| `sync` | Full state response containing `stats`, `devices`, `activity`, `scenarios` |
| `stats` | Server statistics update |
| `device_added` | New device created |
| `device_removed` | Device deleted (data: `{"serial": "..."}`) |
| `device_updated` | Device state changed (data: `{serial, changes}`) |
| `activity` | Packet activity event |
| `scenario_changed` | Scenario configuration changed |
| `error` | Error message (data: `{"message": "..."}`) |

## Example Session

```
-> {"type": "subscribe", "topics": ["devices", "stats"]}
-> {"type": "sync"}
<- {"type": "sync", "data": {"stats": {...}, "devices": [...]}}
<- {"type": "stats", "data": {"uptime_seconds": 123, ...}}
<- {"type": "device_added", "data": {"serial": "d073d5000001", ...}}
```
""",
            },
        ],
    )

    @app.get("/", include_in_schema=False)
    async def root():
        """Serve embedded Svelte dashboard."""
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    # Mount Svelte app assets at /_app (SvelteKit default)
    app.mount("/_app", StaticFiles(directory=str(STATIC_DIR / "_app")), name="app")

    # Mount static files for backward compatibility
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Store WebSocket manager in app state for access by event handlers
    app.state.ws_manager = ws_manager

    # Wire device lifecycle events to WebSocket broadcasts
    wire_device_events(server._device_manager, ws_manager)

    # Wire device state change events to WebSocket broadcasts
    state_observer = WebSocketStateChangeObserver(ws_manager)
    wire_device_state_events(server._device_manager, state_observer)

    # Wrap the activity observer with WebSocket broadcasting
    # This preserves activity logging while adding real-time WebSocket updates
    server.activity_observer = WebSocketActivityObserver(
        ws_manager, server.activity_observer
    )

    # Include routers with server dependency injection
    monitoring_router = create_monitoring_router(server)
    devices_router = create_devices_router(server)
    scenarios_router = create_scenarios_router(server, ws_manager)
    products_router = create_products_router()
    websocket_router = create_websocket_router(ws_manager)

    app.include_router(monitoring_router)
    app.include_router(devices_router)
    app.include_router(scenarios_router)
    app.include_router(products_router)
    app.include_router(websocket_router)

    logger.info("API application created with 5 routers")

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
