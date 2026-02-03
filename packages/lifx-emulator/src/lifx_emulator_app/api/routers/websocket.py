"""WebSocket endpoint for real-time updates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from lifx_emulator_app.api.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


def create_websocket_router(ws_manager: WebSocketManager) -> APIRouter:
    """Create WebSocket router with manager dependency.

    Args:
        ws_manager: The WebSocket manager instance

    Returns:
        Configured APIRouter for WebSocket endpoint
    """
    router = APIRouter(tags=["websocket"])

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates.

        Clients connect and send messages to subscribe to topics:

        ```json
        {"type": "subscribe", "topics": ["stats", "devices", "activity", "scenarios"]}
        ```

        Available topics:
        - stats: Server statistics (pushed every second)
        - devices: Device add/remove/update events
        - activity: Packet activity events
        - scenarios: Scenario configuration changes

        To request a full state sync:

        ```json
        {"type": "sync"}
        ```

        Server pushes messages in the format:

        ```json
        {"type": "<message_type>", "data": {...}}
        ```

        Where message_type is one of: stats, device_added, device_removed,
        device_updated, activity, scenario_changed.
        """
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_message(websocket, data)
        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected normally")
        except Exception:
            logger.exception("WebSocket error")
        finally:
            await ws_manager.disconnect(websocket)

    return router
