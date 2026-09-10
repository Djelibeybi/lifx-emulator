"""Event bridge for connecting core library callbacks to WebSocket broadcasts.

This module provides functions to wire up synchronous device lifecycle callbacks
to asynchronous WebSocket broadcasts, bridging the gap between the core library
(which has no async dependencies) and the FastAPI application layer.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.devices import (
    EXTERNAL_STATE_UPDATE,
    ActivityLogger,
    DeviceManager,
    PacketEvent,
    StateChangeCallback,
)

from lifx_emulator_app.api.mappers.device_mapper import DeviceMapper

if TYPE_CHECKING:
    from lifx_emulator.devices import (
        ActivityObserver,
        EmulatedLifxDevice,
        IDeviceManager,
    )
    from lifx_emulator.server import EmulatedLifxServer

    from lifx_emulator_app.api.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

DEFAULT_EVENT_QUEUE_CAPACITY = 256
DEFAULT_EVENT_WORKERS = 4
BroadcastFactory = Callable[[], Coroutine[Any, Any, None]]


class WebSocketEventQueue:
    """Bound WebSocket bridge work with a fixed asynchronous worker pool."""

    drop_policy = "drop_newest"

    def __init__(
        self,
        *,
        max_pending: int = DEFAULT_EVENT_QUEUE_CAPACITY,
        worker_count: int = DEFAULT_EVENT_WORKERS,
        on_drop: Callable[[], None] | None = None,
    ) -> None:
        if max_pending <= 0:
            raise ValueError("max_pending must be positive")
        if worker_count <= 0:
            raise ValueError("worker_count must be positive")
        self._max_pending = max_pending
        self._worker_count = worker_count
        self._on_drop = on_drop
        self._queue: asyncio.Queue[tuple[BroadcastFactory, str]] | None = None
        self._workers: set[asyncio.Task[None]] = set()
        self._pending_count = 0
        self._accepting = True
        self.dropped_events = 0

    @property
    def pending_count(self) -> int:
        """Return queued plus actively broadcasting events."""
        return self._pending_count

    @property
    def has_capacity(self) -> bool:
        """Return whether another event can be accepted."""
        return self._pending_count < self._max_pending

    def start(self) -> None:
        """Start a fresh fixed worker generation."""
        if self._workers:
            return
        if self._pending_count:
            raise RuntimeError("Cannot restart WebSocket event workers while pending")
        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._accepting = True
        self._workers = {
            loop.create_task(
                self._worker(index), name=f"websocket-event-worker:{index}"
            )
            for index in range(self._worker_count)
        }

    def schedule_factory(self, factory: BroadcastFactory, operation: str) -> bool:
        """Reserve bounded capacity before constructing a broadcast coroutine."""
        if not self._accepting or not self.has_capacity:
            self._record_drop(operation)
            return False
        if not self._workers:
            try:
                self.start()
            except RuntimeError:
                self._record_drop(operation)
                return False

        if self._queue is None:
            raise RuntimeError("WebSocket event queue has not started")
        self._pending_count += 1
        self._queue.put_nowait((factory, operation))
        return True

    def schedule(self, coroutine: Coroutine[Any, Any, None], operation: str) -> bool:
        """Compatibility wrapper for direct callers with an existing coroutine."""
        accepted = self.schedule_factory(lambda: coroutine, operation)
        if not accepted:
            coroutine.close()
        return accepted

    def _record_drop(self, operation: str) -> None:
        self.dropped_events += 1
        if self._on_drop is not None:
            self._on_drop()
        log = logger.warning if self.dropped_events == 1 else logger.debug
        log(
            "Dropped newest WebSocket bridge event (operation=%s, pending=%s)",
            operation,
            self._pending_count,
        )

    async def _worker(self, index: int) -> None:
        if self._queue is None:
            raise RuntimeError("WebSocket event queue has not started")
        queue = self._queue
        while True:
            factory, operation = await queue.get()
            try:
                await factory()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "WebSocket bridge event failed (worker=%s, operation=%s)",
                    index,
                    operation,
                )
            finally:
                self._pending_count -= 1
                queue.task_done()

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Drain accepted events, then cancel workers and discard queued overflow."""
        self._accepting = False
        queue = self._queue
        if queue is None:
            return

        try:
            await asyncio.wait_for(queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            while True:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                self._pending_count -= 1
                queue.task_done()
        finally:
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            self._queue = None


def _schedule_bridge(scheduler: Any, factory: BroadcastFactory, operation: str) -> None:
    """Use lazy production scheduling while retaining tracker compatibility."""
    schedule_factory = getattr(scheduler, "schedule_factory", None)
    if schedule_factory is not None:
        schedule_factory(factory, operation)
        return
    scheduler.schedule(factory(), operation)


def _task_tracker_or_fallback(
    task_tracker: BackgroundTaskTracker | WebSocketEventQueue | None, owner: str
) -> BackgroundTaskTracker | WebSocketEventQueue:
    """Return an injected tracker or an accepting owner-local fallback."""
    if task_tracker is not None:
        return task_tracker

    logger.debug(
        "Creating owner-local background task tracker for %s without an external "
        "lifespan owner; normal task completion is its drain boundary",
        owner,
    )
    return BackgroundTaskTracker(owner)


def wire_device_events(
    device_manager: IDeviceManager,
    ws_manager: WebSocketManager,
    *,
    task_tracker: BackgroundTaskTracker | WebSocketEventQueue | None = None,
) -> None:
    """Wire device lifecycle callbacks to WebSocket broadcasts.

    This sets up the DeviceManager callbacks to broadcast events to
    connected WebSocket clients when devices are added or removed.

    Args:
        device_manager: The DeviceManager to wire callbacks to (must be
            a DeviceManager instance that supports callbacks)
        ws_manager: The WebSocketManager to broadcast events through
        task_tracker: Optional owner-provided tracker for broadcast tasks
    """
    # Only DeviceManager (not all IDeviceManager implementations) supports callbacks
    if not isinstance(device_manager, DeviceManager):
        logger.warning(
            "Device manager is not a DeviceManager instance, skipping event wiring"
        )
        return

    tracker = _task_tracker_or_fallback(task_tracker, "websocket-device-events")

    def on_device_added(device: EmulatedLifxDevice) -> None:
        """Callback invoked when a device is added."""
        device_info = DeviceMapper.to_device_info(device)
        _schedule_bridge(
            tracker,
            lambda: ws_manager.broadcast_device_added(device_info.model_dump()),
            f"device-added:{device.state.serial}",
        )
        logger.debug("Scheduled device_added broadcast for %s", device.state.serial)

    def on_device_removed(serial: str) -> None:
        """Callback invoked when a device is removed."""
        _schedule_bridge(
            tracker,
            lambda: ws_manager.broadcast_device_removed(serial),
            f"device-removed:{serial}",
        )
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
        *,
        task_tracker: BackgroundTaskTracker | WebSocketEventQueue | None = None,
    ) -> None:
        """Initialize the WebSocket activity observer.

        Args:
            ws_manager: The WebSocketManager to broadcast events through
            inner_observer: Optional inner observer to delegate to (for logging).
                If it has get_recent_activity(), that will be used.
            task_tracker: Optional owner-provided tracker for broadcast tasks
        """
        self._ws_manager = ws_manager
        self._task_tracker = _task_tracker_or_fallback(
            task_tracker, "websocket-activity-observer"
        )
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
        _schedule_bridge(
            self._task_tracker,
            lambda: self._ws_manager.broadcast_activity(
                {
                    "timestamp": event.timestamp,
                    "direction": "rx",
                    "packet_type": event.packet_type,
                    "packet_name": event.packet_name,
                    "target": event.target,
                    "addr": event.addr,
                }
            ),
            f"activity:rx:{event.packet_type}",
        )

    def on_packet_sent(self, event: PacketEvent) -> None:
        """Handle packet sent event.

        Args:
            event: The packet event with direction='tx'
        """
        # Delegate to inner observer for logging
        self._inner.on_packet_sent(event)

        # Broadcast to WebSocket clients
        _schedule_bridge(
            self._task_tracker,
            lambda: self._ws_manager.broadcast_activity(
                {
                    "timestamp": event.timestamp,
                    "direction": "tx",
                    "packet_type": event.packet_type,
                    "packet_name": event.packet_name,
                    "device": event.device,
                    "addr": event.addr,
                }
            ),
            f"activity:tx:{event.packet_type}",
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

    def __init__(
        self,
        ws_manager: WebSocketManager,
        *,
        task_tracker: BackgroundTaskTracker | WebSocketEventQueue | None = None,
    ) -> None:
        """Initialize the WebSocket state change observer.

        Args:
            ws_manager: The WebSocketManager to broadcast events through
            task_tracker: Optional owner-provided tracker for broadcast tasks
        """
        self._ws_manager = ws_manager
        self._task_tracker = _task_tracker_or_fallback(
            task_tracker, "websocket-state-change-observer"
        )

    def on_state_changed(
        self, device: EmulatedLifxDevice, pkt_type: int, duration_ms: int
    ) -> None:
        """Handle device state change event.

        Args:
            device: The device that changed
            pkt_type: The packet type that caused the change
            duration_ms: The transition duration in milliseconds
        """
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
        if pkt_type == EXTERNAL_STATE_UPDATE:
            changes = device_info.model_dump(mode="json")
            changes["category"] = category
            changes["duration_ms"] = duration_ms
        elif category == "zones" and device_info.zone_colors:
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
        elif category == "metadata":
            changes["label"] = device_info.label
            changes["group_label"] = device_info.group_label
            changes["location_label"] = device_info.location_label
        elif category in ("color", "power") and device_info.color:
            changes["color"] = device_info.color.model_dump()

        _schedule_bridge(
            self._task_tracker,
            lambda: self._ws_manager.broadcast_device_updated(
                device.state.serial, changes
            ),
            f"device-updated:{device.state.serial}:{pkt_type}",
        )

    def _get_change_category(self, pkt_type: int) -> str:
        """Determine the category of change based on packet type.

        Args:
            pkt_type: The packet type number

        Returns:
            Category string: "zones", "tiles", "power", "metadata", or "color"
        """
        if pkt_type in {501, 510}:  # SetColorZones, ExtendedSetColorZones
            return "zones"
        elif pkt_type in {715, 716}:  # Set64, CopyFrameBuffer
            return "tiles"
        elif pkt_type in {21, 117}:  # Device.SetPower, Light.SetPower
            return "power"
        elif pkt_type in {24, 49, 52}:  # SetLabel, SetLocation, SetGroup
            return "metadata"
        elif pkt_type == EXTERNAL_STATE_UPDATE:
            return "state"
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
