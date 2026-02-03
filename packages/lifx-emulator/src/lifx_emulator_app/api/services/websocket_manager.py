"""WebSocket connection manager for real-time updates.

Manages WebSocket client connections, topic subscriptions, and message broadcasting.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

logger = logging.getLogger(__name__)


class Topic(str, Enum):
    """Topics that clients can subscribe to."""

    STATS = "stats"
    DEVICES = "devices"
    ACTIVITY = "activity"
    SCENARIOS = "scenarios"


class MessageType(str, Enum):
    """WebSocket message types."""

    # Server → Client
    STATS = "stats"
    DEVICE_ADDED = "device_added"
    DEVICE_REMOVED = "device_removed"
    DEVICE_UPDATED = "device_updated"
    ACTIVITY = "activity"
    SCENARIO_CHANGED = "scenario_changed"
    SYNC = "sync"
    ERROR = "error"

    # Client → Server
    SUBSCRIBE = "subscribe"


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client."""

    websocket: WebSocket
    subscriptions: set[Topic] = field(default_factory=set)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting.

    Handles:
    - Client connection lifecycle (connect/disconnect)
    - Topic subscriptions
    - Broadcasting messages to subscribed clients
    - Full state sync on request
    """

    def __init__(self, server: EmulatedLifxServer) -> None:
        """Initialize the WebSocket manager.

        Args:
            server: The LIFX emulator server instance for state access
        """
        self._server = server
        self._clients: dict[WebSocket, ClientConnection] = {}
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        """Return the number of connected clients."""
        return len(self._clients)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket to accept
        """
        await websocket.accept()
        async with self._lock:
            self._clients[websocket] = ClientConnection(websocket=websocket)
        logger.info("WebSocket client connected (%d total)", self.client_count)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket client.

        Args:
            websocket: The WebSocket to remove
        """
        async with self._lock:
            self._clients.pop(websocket, None)
        logger.info("WebSocket client disconnected (%d remaining)", self.client_count)

    async def subscribe(self, websocket: WebSocket, topics: list[str]) -> None:
        """Subscribe a client to topics.

        Args:
            websocket: The client's WebSocket
            topics: List of topic names to subscribe to
        """
        async with self._lock:
            client = self._clients.get(websocket)
            if client:
                for topic_name in topics:
                    try:
                        topic = Topic(topic_name)
                        client.subscriptions.add(topic)
                    except ValueError:
                        logger.warning("Unknown topic: %s", topic_name)
                logger.debug(
                    "Client subscribed to: %s",
                    [t.value for t in client.subscriptions],
                )

    async def handle_message(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Handle an incoming message from a client.

        Args:
            websocket: The client's WebSocket
            data: The parsed JSON message
        """
        msg_type = data.get("type")

        if msg_type == MessageType.SUBSCRIBE.value:
            topics = data.get("topics", [])
            await self.subscribe(websocket, topics)

        elif msg_type == "sync":
            await self._send_full_sync(websocket)

        else:
            logger.warning("Unknown message type: %s", msg_type)
            await self._send_error(websocket, f"Unknown message type: {msg_type}")

    async def _send_full_sync(self, websocket: WebSocket) -> None:
        """Send full state sync to a client.

        Args:
            websocket: The client's WebSocket
        """
        from lifx_emulator_app.api.mappers.device_mapper import DeviceMapper

        client = self._clients.get(websocket)
        if not client:
            return

        sync_data: dict[str, Any] = {}

        if Topic.STATS in client.subscriptions:
            sync_data["stats"] = self._server.get_stats()

        if Topic.DEVICES in client.subscriptions:
            devices = self._server.get_all_devices()
            sync_data["devices"] = [
                DeviceMapper.to_device_info(d).model_dump() for d in devices
            ]

        if Topic.ACTIVITY in client.subscriptions:
            sync_data["activity"] = self._server.get_recent_activity()

        if Topic.SCENARIOS in client.subscriptions:
            sync_data["scenarios"] = self._get_all_scenarios()

        await self._send_to_client(
            websocket, {"type": MessageType.SYNC.value, "data": sync_data}
        )

    def _get_all_scenarios(self) -> dict[str, Any]:
        """Get all scenario configurations."""
        manager = self._server.scenario_manager
        return {
            "global": (
                manager.global_scenario.model_dump()
                if manager.global_scenario
                else None
            ),
            "devices": {
                serial: config.model_dump()
                for serial, config in manager.device_scenarios.items()
            },
            "types": {
                dtype: config.model_dump()
                for dtype, config in manager.type_scenarios.items()
            },
            "locations": {
                loc: config.model_dump()
                for loc, config in manager.location_scenarios.items()
            },
            "groups": {
                grp: config.model_dump()
                for grp, config in manager.group_scenarios.items()
            },
        }

    async def _send_error(self, websocket: WebSocket, message: str) -> None:
        """Send an error message to a client.

        Args:
            websocket: The client's WebSocket
            message: The error message
        """
        await self._send_to_client(
            websocket, {"type": MessageType.ERROR.value, "message": message}
        )

    async def _send_to_client(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> None:
        """Send a message to a specific client.

        Args:
            websocket: The client's WebSocket
            message: The message to send
        """
        try:
            await websocket.send_json(message)
        except Exception:
            logger.exception("Failed to send message to client")
            await self.disconnect(websocket)

    async def broadcast(
        self, topic: Topic, message_type: MessageType, data: dict[str, Any]
    ) -> None:
        """Broadcast a message to all clients subscribed to a topic.

        Args:
            topic: The topic to broadcast to
            message_type: The type of message
            data: The message data
        """
        message = {"type": message_type.value, "data": data}

        async with self._lock:
            clients_to_notify = [
                client.websocket
                for client in self._clients.values()
                if topic in client.subscriptions
            ]

        if not clients_to_notify:
            return

        # Send to all subscribed clients concurrently
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in clients_to_notify],
            return_exceptions=True,
        )

        # Handle any failed sends
        for ws, result in zip(clients_to_notify, results):
            if isinstance(result, Exception):
                logger.warning("Failed to send to client: %s", result)
                await self.disconnect(ws)

    async def broadcast_stats(self, stats: dict[str, Any]) -> None:
        """Broadcast stats update to subscribed clients.

        Args:
            stats: The server statistics
        """
        await self.broadcast(Topic.STATS, MessageType.STATS, stats)

    async def broadcast_device_added(self, device_info: dict[str, Any]) -> None:
        """Broadcast device added event.

        Args:
            device_info: The new device information
        """
        await self.broadcast(Topic.DEVICES, MessageType.DEVICE_ADDED, device_info)

    async def broadcast_device_removed(self, serial: str) -> None:
        """Broadcast device removed event.

        Args:
            serial: The serial of the removed device
        """
        await self.broadcast(
            Topic.DEVICES, MessageType.DEVICE_REMOVED, {"serial": serial}
        )

    async def broadcast_device_updated(
        self, serial: str, changes: dict[str, Any]
    ) -> None:
        """Broadcast device updated event.

        Args:
            serial: The serial of the updated device
            changes: The changed fields
        """
        await self.broadcast(
            Topic.DEVICES,
            MessageType.DEVICE_UPDATED,
            {"serial": serial, "changes": changes},
        )

    async def broadcast_activity(self, event: dict[str, Any]) -> None:
        """Broadcast activity event.

        Args:
            event: The activity event data
        """
        await self.broadcast(Topic.ACTIVITY, MessageType.ACTIVITY, event)

    async def broadcast_scenario_changed(
        self, scope: str, identifier: str | None, config: dict[str, Any] | None
    ) -> None:
        """Broadcast scenario changed event.

        Args:
            scope: The scenario scope (global, device, type, location, group)
            identifier: The scope identifier (serial, type name, etc.)
            config: The new scenario configuration (None if deleted)
        """
        await self.broadcast(
            Topic.SCENARIOS,
            MessageType.SCENARIO_CHANGED,
            {"scope": scope, "identifier": identifier, "config": config},
        )
