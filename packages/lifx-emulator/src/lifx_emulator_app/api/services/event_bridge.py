"""Event bridge for connecting core library callbacks to WebSocket broadcasts.

This module provides functions to wire up synchronous device lifecycle callbacks
to asynchronous WebSocket broadcasts, bridging the gap between the core library
(which has no async dependencies) and the FastAPI application layer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from lifx_emulator.devices import PacketEvent, StateChangeCallback

if TYPE_CHECKING:
    from lifx_emulator.devices import (
        ActivityLogger,
        ActivityObserver,
        EmulatedLifxDevice,
        IDeviceManager,
    )
    from lifx_emulator.server import EmulatedLifxServer

    from lifx_emulator_app.api.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


def _schedule_async(coro) -> None:
    """Schedule an async coroutine from a sync context.

    Args:
        coro: The coroutine to schedule
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        logger.warning("No running event loop to schedule async task")


def wire_device_events(
    device_manager: IDeviceManager, ws_manager: WebSocketManager
) -> None:
    """Wire device lifecycle callbacks to WebSocket broadcasts.

    This sets up the DeviceManager callbacks to broadcast events to
    connected WebSocket clients when devices are added or removed.

    Args:
        device_manager: The DeviceManager to wire callbacks to (must be
            a DeviceManager instance that supports callbacks)
        ws_manager: The WebSocketManager to broadcast events through
    """
    from lifx_emulator.devices import DeviceManager

    from lifx_emulator_app.api.mappers.device_mapper import DeviceMapper

    # Only DeviceManager (not all IDeviceManager implementations) supports callbacks
    if not isinstance(device_manager, DeviceManager):
        logger.warning(
            "Device manager is not a DeviceManager instance, skipping event wiring"
        )
        return

    def on_device_added(device: EmulatedLifxDevice) -> None:
        """Callback invoked when a device is added."""
        device_info = DeviceMapper.to_device_info(device)
        _schedule_async(ws_manager.broadcast_device_added(device_info.model_dump()))
        logger.debug("Scheduled device_added broadcast for %s", device.state.serial)

    def on_device_removed(serial: str) -> None:
        """Callback invoked when a device is removed."""
        _schedule_async(ws_manager.broadcast_device_removed(serial))
        logger.debug("Scheduled device_removed broadcast for %s", serial)

    device_manager.on_device_added = on_device_added
    device_manager.on_device_removed = on_device_removed

    logger.info("Device event callbacks wired to WebSocket manager")


class WebSocketActivityObserver:
    """ActivityObserver implementation that broadcasts events via WebSocket.

    This observer bridges the synchronous ActivityObserver protocol to
    asynchronous WebSocket broadcasts, allowing real-time activity updates
    to connected clients.

    Also wraps an optional inner observer (typically ActivityLogger) to
    maintain the activity log while adding WebSocket broadcasting.
    """

    def __init__(
        self,
        ws_manager: WebSocketManager,
        inner_observer: ActivityObserver | None = None,
    ) -> None:
        """Initialize the WebSocket activity observer.

        Args:
            ws_manager: The WebSocketManager to broadcast events through
            inner_observer: Optional inner observer to delegate to (for logging).
                If it has get_recent_activity(), that will be used.
        """
        from lifx_emulator.devices import ActivityLogger

        self._ws_manager = ws_manager
        # Use provided observer or create a new ActivityLogger
        self._inner: ActivityLogger | ActivityObserver = (
            inner_observer
            if inner_observer is not None
            else ActivityLogger(max_events=100)
        )

    def on_packet_received(self, event: PacketEvent) -> None:
        """Handle packet received event.

        Args:
            event: The packet event with direction='rx'
        """
        # Delegate to inner observer for logging
        self._inner.on_packet_received(event)

        # Broadcast to WebSocket clients
        _schedule_async(
            self._ws_manager.broadcast_activity(
                {
                    "timestamp": event.timestamp,
                    "direction": "rx",
                    "packet_type": event.packet_type,
                    "packet_name": event.packet_name,
                    "target": event.target,
                    "addr": event.addr,
                }
            )
        )

    def on_packet_sent(self, event: PacketEvent) -> None:
        """Handle packet sent event.

        Args:
            event: The packet event with direction='tx'
        """
        # Delegate to inner observer for logging
        self._inner.on_packet_sent(event)

        # Broadcast to WebSocket clients
        _schedule_async(
            self._ws_manager.broadcast_activity(
                {
                    "timestamp": event.timestamp,
                    "direction": "tx",
                    "packet_type": event.packet_type,
                    "packet_name": event.packet_name,
                    "device": event.device,
                    "addr": event.addr,
                }
            )
        )

    def get_recent_activity(self) -> list[dict]:
        """Get recent activity from the inner logger.

        Returns:
            List of recent activity events, or empty list if inner observer
            doesn't support activity tracking
        """
        get_activity = getattr(self._inner, "get_recent_activity", None)
        if get_activity is not None:
            return get_activity()
        return []


class StatsBroadcaster:
    """Background task that broadcasts server stats periodically.

    Broadcasts stats to WebSocket clients at a configurable interval
    (default 1 second).
    """

    def __init__(
        self,
        server: EmulatedLifxServer,
        ws_manager: WebSocketManager,
        interval: float = 1.0,
    ) -> None:
        """Initialize the stats broadcaster.

        Args:
            server: The LIFX emulator server to get stats from
            ws_manager: The WebSocketManager to broadcast through
            interval: Broadcast interval in seconds (default 1.0)
        """
        self._server = server
        self._ws_manager = ws_manager
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def _broadcast_loop(self) -> None:
        """Background loop that broadcasts stats at regular intervals."""
        while self._running:
            try:
                stats = self._server.get_stats()
                await self._ws_manager.broadcast_stats(stats)
            except Exception:
                logger.exception("Error broadcasting stats")

            await asyncio.sleep(self._interval)

    def start(self) -> None:
        """Start the stats broadcast background task."""
        if self._task is not None:
            return

        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info("Stats broadcaster started (interval=%.1fs)", self._interval)

    async def stop(self) -> None:
        """Stop the stats broadcast background task."""
        if self._task is None:
            return

        self._running = False
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Stats broadcaster stopped")


class WebSocketStateChangeObserver:
    """Broadcasts device state changes to WebSocket clients.

    This observer receives state change callbacks from devices when
    state-changing packets (SetColor, SetColorZones, Set64, etc.)
    are processed, and broadcasts the changes to WebSocket clients
    including the transition duration from the packet.
    """

    def __init__(self, ws_manager: WebSocketManager) -> None:
        """Initialize the WebSocket state change observer.

        Args:
            ws_manager: The WebSocketManager to broadcast events through
        """
        self._ws_manager = ws_manager

    def on_state_changed(
        self, device: EmulatedLifxDevice, pkt_type: int, duration_ms: int
    ) -> None:
        """Handle device state change event.

        Args:
            device: The device that changed
            pkt_type: The packet type that caused the change
            duration_ms: The transition duration in milliseconds
        """
        from lifx_emulator_app.api.mappers.device_mapper import DeviceMapper

        logger.debug(
            "State change callback: device=%s, pkt_type=%d, duration_ms=%d",
            device.state.serial,
            pkt_type,
            duration_ms,
        )

        # Get full device state
        device_info = DeviceMapper.to_device_info(device)

        # Determine change category based on packet type
        category = self._get_change_category(pkt_type)

        changes: dict = {
            "category": category,
            "duration_ms": duration_ms,
            "power_level": device_info.power_level,
        }

        # Include relevant data based on category
        if category == "zones" and device_info.zone_colors:
            changes["zone_colors"] = [c.model_dump() for c in device_info.zone_colors]
        elif category == "tiles" and device_info.tile_devices:
            # Convert tile_devices: each tile dict has 'colors' containing
            # LightHsbk dataclass objects that need to be serialized
            changes["tile_devices"] = [
                {
                    "width": tile.get("width", 0),
                    "height": tile.get("height", 0),
                    "colors": [
                        {
                            "hue": c.hue,
                            "saturation": c.saturation,
                            "brightness": c.brightness,
                            "kelvin": c.kelvin,
                        }
                        for c in tile.get("colors", [])
                    ],
                }
                for tile in device_info.tile_devices
            ]
        elif category in ("color", "power") and device_info.color:
            changes["color"] = device_info.color.model_dump()

        _schedule_async(
            self._ws_manager.broadcast_device_updated(device.state.serial, changes)
        )

    def _get_change_category(self, pkt_type: int) -> str:
        """Determine the category of change based on packet type.

        Args:
            pkt_type: The packet type number

        Returns:
            Category string: "zones", "tiles", "power", or "color"
        """
        if pkt_type in {501, 510}:  # SetColorZones, ExtendedSetColorZones
            return "zones"
        elif pkt_type in {715, 716}:  # Set64, CopyFrameBuffer
            return "tiles"
        elif pkt_type in {21, 117}:  # Device.SetPower, Light.SetPower
            return "power"
        return "color"

    def get_callback(self) -> StateChangeCallback:
        """Get the callback function for wiring to devices.

        Returns:
            The on_state_changed method bound to this instance
        """
        return self.on_state_changed


def wire_device_state_events(
    device_manager: IDeviceManager,
    state_observer: WebSocketStateChangeObserver,
) -> None:
    """Wire state change callbacks to all devices.

    Sets up the on_state_changed callback on all existing devices
    and hooks into device_added to wire new devices.

    Args:
        device_manager: The DeviceManager to wire callbacks to
        state_observer: The WebSocketStateChangeObserver to broadcast through
    """
    from lifx_emulator.devices import DeviceManager

    # Only DeviceManager supports callbacks
    if not isinstance(device_manager, DeviceManager):
        logger.warning(
            "Device manager is not a DeviceManager instance, "
            "skipping state event wiring"
        )
        return

    callback = state_observer.get_callback()

    # Wire existing devices
    existing_devices = list(device_manager.get_all_devices())
    for device in existing_devices:
        device.on_state_changed = callback
        logger.debug("Wired state callback for device %s", device.state.serial)

    logger.info("Wired state callbacks for %d existing devices", len(existing_devices))

    # Hook into device_added to wire new devices
    original_callback = device_manager.on_device_added

    def on_device_added_wrapper(device: EmulatedLifxDevice) -> None:
        """Wrapper to wire state callback before calling original handler."""
        device.on_state_changed = callback
        if original_callback:
            original_callback(device)

    device_manager.on_device_added = on_device_added_wrapper

    logger.info("Device state change callbacks wired to WebSocket manager")
