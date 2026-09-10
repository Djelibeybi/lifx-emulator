"""Tests for WebSocket endpoint and manager."""

import asyncio
import gc
import inspect
import logging
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import lifx_emulator_app.api.app as api_app_module
import pytest
from fastapi.testclient import TestClient
from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.devices import DeviceManager, PacketEvent
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from lifx_emulator_app.api.app import create_api_app
from lifx_emulator_app.api.services import MessageType, Topic, WebSocketManager
from lifx_emulator_app.api.services.event_bridge import (
    WebSocketActivityObserver,
    WebSocketEventQueue,
    WebSocketStateChangeObserver,
    wire_device_events,
)


class RecordingTaskTracker:
    """Record bridge scheduling while closing captured coroutine objects."""

    def __init__(self) -> None:
        self.operations: list[str] = []

    def schedule(self, coroutine: Coroutine[Any, Any, Any], operation: str) -> None:
        self.operations.append(operation)
        coroutine.close()


@pytest.fixture
def server():
    """Create a minimal server for testing."""
    device_manager = DeviceManager(DeviceRepository())
    return EmulatedLifxServer([], device_manager, "127.0.0.1", 56700)


@pytest.fixture
def client(server):
    """Create a test client with WebSocket support."""
    app = create_api_app(server)
    return TestClient(app)


@pytest.fixture
def ws_manager(server):
    """Create a WebSocket manager for testing."""
    return WebSocketManager(server)


class TestWebSocketEndpoint:
    """Tests for /ws endpoint."""

    def test_websocket_connect(self, client):
        """Test WebSocket connection."""
        with client.websocket_connect("/ws") as websocket:
            # Connection should succeed
            assert websocket is not None

    def test_websocket_subscribe(self, client):
        """Test subscribing to topics."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(
                {"type": "subscribe", "topics": ["stats", "devices", "activity"]}
            )
            # Should not error - subscription is silent

    def test_websocket_sync_empty(self, client):
        """Test sync returns empty state when no subscriptions."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            assert response["data"] == {}

    def test_websocket_sync_with_stats(self, client):
        """Test sync returns stats when subscribed."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "subscribe", "topics": ["stats"]})
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            assert "stats" in response["data"]
            assert "uptime_seconds" in response["data"]["stats"]

    def test_websocket_sync_with_devices(self, client, server):
        """Test sync returns devices when subscribed."""
        # Add a device
        device = create_color_light()
        server.add_device(device)

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "subscribe", "topics": ["devices"]})
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            assert "devices" in response["data"]
            assert len(response["data"]["devices"]) == 1
            assert response["data"]["devices"][0]["serial"] == device.state.serial

    def test_websocket_sync_with_scenarios(self, client):
        """Test sync returns scenarios when subscribed."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "subscribe", "topics": ["scenarios"]})
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            assert "scenarios" in response["data"]
            assert "global" in response["data"]["scenarios"]
            assert "devices" in response["data"]["scenarios"]

    def test_websocket_sync_with_activity(self, client):
        """Test sync returns activity when subscribed."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "subscribe", "topics": ["activity"]})
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            assert "activity" in response["data"]
            # Activity should be a list (empty or with events)
            assert isinstance(response["data"]["activity"], list)

    def test_websocket_unknown_message_type(self, client):
        """Test unknown message type returns error."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "unknown_type"})
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "unknown_type" in response["message"].lower()

    def test_websocket_subscribe_unknown_topic(self, client):
        """Test subscribing to unknown topic is handled gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Should not raise, unknown topics are ignored
            websocket.send_json(
                {"type": "subscribe", "topics": ["stats", "unknown_topic"]}
            )
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            # Should still work for valid topic
            assert response["type"] == "sync"
            assert "stats" in response["data"]


class TestWebSocketManager:
    """Tests for WebSocketManager class."""

    def test_client_count_starts_at_zero(self, ws_manager):
        """Test client count is zero initially."""
        assert ws_manager.client_count == 0

    def test_topic_enum_values(self):
        """Test Topic enum has expected values."""
        assert Topic.STATS.value == "stats"
        assert Topic.DEVICES.value == "devices"
        assert Topic.ACTIVITY.value == "activity"
        assert Topic.SCENARIOS.value == "scenarios"

    def test_message_type_enum_values(self):
        """Test MessageType enum has expected values."""
        assert MessageType.STATS.value == "stats"
        assert MessageType.DEVICE_ADDED.value == "device_added"
        assert MessageType.DEVICE_REMOVED.value == "device_removed"
        assert MessageType.DEVICE_UPDATED.value == "device_updated"
        assert MessageType.ACTIVITY.value == "activity"
        assert MessageType.SCENARIO_CHANGED.value == "scenario_changed"
        assert MessageType.SUBSCRIBE.value == "subscribe"
        assert MessageType.SYNC.value == "sync"
        assert MessageType.ERROR.value == "error"


class TestWebSocketManagerInApp:
    """Tests for WebSocketManager integration with FastAPI app."""

    def test_ws_manager_in_app_state(self, client):
        """Test WebSocketManager is accessible via app.state."""
        assert hasattr(client.app.state, "ws_manager")
        assert isinstance(client.app.state.ws_manager, WebSocketManager)

    def test_ws_manager_has_server_reference(self, client, server):
        """Test WebSocketManager has reference to server."""
        ws_manager = client.app.state.ws_manager
        assert ws_manager._server is server


class TestEventBridgeLifespan:
    """Tests for application ownership of WebSocket bridge tasks."""

    def test_create_api_app_exposes_open_background_task_tracker(self, server):
        """Test app construction immediately exposes an accepting bridge owner."""
        app = create_api_app(server)

        assert hasattr(app.state, "background_task_tracker")
        assert isinstance(app.state.background_task_tracker, WebSocketEventQueue)
        assert app.state.background_task_tracker.pending_count == 0

    def test_create_api_app_injects_one_tracker_into_all_adapters(self, server):
        """Test the factory passes one exact tracker to every bridge adapter."""
        with (
            patch.object(api_app_module, "wire_device_events") as wire_events,
            patch.object(
                api_app_module, "WebSocketStateChangeObserver"
            ) as state_observer_type,
            patch.object(
                api_app_module, "wire_device_state_events"
            ) as wire_state_events,
            patch.object(
                api_app_module, "WebSocketActivityObserver"
            ) as activity_observer_type,
        ):
            app = api_app_module.create_api_app(server)

        tracker = app.state.background_task_tracker
        assert wire_events.call_args.kwargs["task_tracker"] is tracker
        assert state_observer_type.call_args.kwargs["task_tracker"] is tracker
        assert activity_observer_type.call_args.kwargs["task_tracker"] is tracker
        wire_state_events.assert_called_once_with(
            server._device_manager, state_observer_type.return_value
        )

    @pytest.mark.asyncio
    async def test_non_lifespan_test_client_keeps_bridge_admission_open(self, server):
        """Test constructing TestClient without entering it still accepts work."""
        app = create_api_app(server)
        test_client = TestClient(app)
        tracker = app.state.background_task_tracker
        started = asyncio.Event()
        release = asyncio.Event()
        completed: list[str] = []

        async def broadcast_device_added(payload: dict[str, Any]) -> None:
            started.set()
            await release.wait()
            completed.append(payload["serial"])

        app.state.ws_manager.broadcast_device_added = broadcast_device_added
        try:
            assert server.add_device(create_color_light("d073d5112233"))
            await started.wait()
            assert tracker.pending_count == 1
            release.set()
            await tracker.shutdown()
        finally:
            test_client.close()

        assert completed == ["d073d5112233"]
        assert tracker.pending_count == 0

    @pytest.mark.asyncio
    async def test_lifespan_drains_normally_and_reopens_for_second_cycle(self, server):
        """Test normal and repeated lifespan cycles finish with no bridge work."""
        app = create_api_app(server)
        tracker = app.state.background_task_tracker

        for cycle in range(2):
            completed = asyncio.Event()

            async def finish_broadcast() -> None:
                completed.set()

            async with app.router.lifespan_context(app):
                assert (
                    tracker.schedule(finish_broadcast(), f"lifespan-cycle:{cycle}")
                    is not None
                )
                await completed.wait()

            assert tracker.pending_count == 0

    def test_context_managed_test_client_reenters_drained_lifespan(self, server):
        """Test the repository's context-managed client runs repeatable lifespan."""
        app = create_api_app(server)
        tracker = app.state.background_task_tracker

        for _ in range(2):
            with TestClient(app) as test_client:
                assert test_client.get("/api/stats").status_code == 200
            assert tracker.pending_count == 0

        with pytest.raises(RuntimeError, match="client body failed"):
            with TestClient(app):
                raise RuntimeError("client body failed")
        assert tracker.pending_count == 0

    @pytest.mark.asyncio
    async def test_exceptional_lifespan_stops_stats_then_cancels_bridge_work(
        self, server, monkeypatch
    ):
        """Test exceptional teardown stops its producer before bounded drain."""
        order: list[str] = []
        broadcaster = MagicMock()
        broadcaster.start.side_effect = lambda: order.append("start")

        async def stop_broadcaster() -> None:
            order.append("stop")

        broadcaster.stop.side_effect = stop_broadcaster
        with patch.object(api_app_module, "StatsBroadcaster", return_value=broadcaster):
            app = api_app_module.create_api_app(server)

        tracker = app.state.background_task_tracker
        original_shutdown = tracker.shutdown
        cancelled = asyncio.Event()
        started = asyncio.Event()

        async def bounded_shutdown(timeout: float = 5.0) -> None:
            order.append("drain")
            assert timeout == 5.0
            await original_shutdown(timeout=0)

        monkeypatch.setattr(tracker, "shutdown", bounded_shutdown)

        async def blocked_broadcast() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        with pytest.raises(RuntimeError, match="lifespan body failed"):
            async with app.router.lifespan_context(app):
                assert (
                    tracker.schedule(blocked_broadcast(), "test:blocked-broadcast")
                    is not None
                )
                await started.wait()
                raise RuntimeError("lifespan body failed")

        assert order == ["start", "stop", "drain"]
        assert cancelled.is_set()
        assert tracker.pending_count == 0

    async def test_activity_flood_is_bounded_and_reports_drops(self, server):
        """A blocked broadcast cannot create unbounded bridge work."""
        broadcast_started = asyncio.Event()
        release_broadcast = asyncio.Event()

        async def blocked_broadcast(_event: dict[str, Any]) -> None:
            broadcast_started.set()
            await release_broadcast.wait()

        ws_manager = MagicMock()
        ws_manager.broadcast_activity = blocked_broadcast
        queue = WebSocketEventQueue(
            max_pending=8,
            worker_count=1,
            on_drop=lambda: setattr(
                server,
                "websocket_events_dropped",
                server.websocket_events_dropped + 1,
            ),
        )
        observer = WebSocketActivityObserver(ws_manager, task_tracker=queue)
        event = PacketEvent(
            timestamp=1704067200.0,
            direction="rx",
            packet_type=2,
            packet_name="GetService",
            target="d073d5000001",
            addr="192.168.1.100:56700",
        )

        for _ in range(5_000):
            observer.on_packet_received(event)
        await broadcast_started.wait()

        assert queue.pending_count <= 8
        assert not queue.has_capacity
        assert queue.dropped_events == 4_992
        assert queue.drop_policy == "drop_newest"
        assert server.get_stats()["websocket_events_dropped"] == 4_992

        await queue.shutdown(timeout=0)
        assert queue.pending_count == 0


class TestWebSocketDeviceEvents:
    """Tests for device event broadcasting via WebSocket."""

    def test_device_event_not_received_without_subscription(self, client, server):
        """Test device events are not received without devices subscription."""
        with client.websocket_connect("/ws") as websocket:
            # Don't subscribe to devices topic

            # Add a device
            device = create_color_light("d073d5112233")
            server.add_device(device)

            # Send sync to verify connection works
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"
            # Should not have received device_added (no subscription)


class TestEventBridge:
    """Tests for the event bridge module."""

    def test_event_bridge_entry_points_have_optional_keyword_only_tracker(self):
        """Test every importable bridge entry point preserves its old signature."""
        for entry_point in (
            wire_device_events,
            WebSocketActivityObserver,
            WebSocketStateChangeObserver,
        ):
            parameter = inspect.signature(entry_point).parameters.get("task_tracker")
            assert parameter is not None
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
            assert parameter.default is None

    def test_omitted_trackers_are_accepting_owner_local_fallbacks(self, caplog):
        """Test direct adapters retain distinct trackers with a lifecycle diagnostic."""
        device_manager = DeviceManager(DeviceRepository())
        mock_ws_manager = MagicMock()

        with caplog.at_level(logging.DEBUG):
            wire_device_events(device_manager, mock_ws_manager)
            activity_observer = WebSocketActivityObserver(mock_ws_manager)
            state_observer = WebSocketStateChangeObserver(mock_ws_manager)

        assert activity_observer._task_tracker is not state_observer._task_tracker
        diagnostics = [
            record
            for record in caplog.records
            if "normal task completion is its drain boundary" in record.getMessage()
        ]
        assert len(diagnostics) == 3

    async def test_wire_device_events_uses_exact_labels_and_payloads(self):
        """Test device lifecycle callbacks retain labels and broadcast arguments."""
        device_manager = DeviceManager(DeviceRepository())
        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_added = AsyncMock()
        mock_ws_manager.broadcast_device_removed = AsyncMock()
        tracker = RecordingTaskTracker()
        wire_device_events(device_manager, mock_ws_manager, task_tracker=tracker)

        device = create_color_light("d073d5112233")
        assert device_manager.add_device(device)
        assert await device_manager.remove_device(device.state.serial)

        assert tracker.operations == [
            "device-added:d073d5112233",
            "device-removed:d073d5112233",
        ]
        added_payload = mock_ws_manager.broadcast_device_added.call_args.args[0]
        assert added_payload["serial"] == "d073d5112233"
        mock_ws_manager.broadcast_device_removed.assert_called_once_with("d073d5112233")

    def test_wire_device_events_with_non_device_manager(self):
        """Test wire_device_events handles non-DeviceManager instances."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import wire_device_events

        # Create a mock that's not a DeviceManager
        mock_manager = MagicMock()
        mock_ws_manager = MagicMock()

        # Should not raise, just log warning
        wire_device_events(mock_manager, mock_ws_manager)

    def test_websocket_activity_observer_init_with_inner(self):
        """Test WebSocketActivityObserver initializes with inner observer."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()
        mock_inner = MagicMock()

        observer = WebSocketActivityObserver(mock_ws_manager, mock_inner)
        assert observer._inner is mock_inner

    def test_websocket_activity_observer_init_without_inner(self):
        """Test WebSocketActivityObserver creates ActivityLogger when no inner."""
        from unittest.mock import MagicMock

        from lifx_emulator.devices import ActivityLogger
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()

        observer = WebSocketActivityObserver(mock_ws_manager)
        assert isinstance(observer._inner, ActivityLogger)

    def test_websocket_activity_observer_get_recent_activity(self):
        """Test WebSocketActivityObserver.get_recent_activity delegates to inner."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()
        mock_inner = MagicMock()
        mock_inner.get_recent_activity = MagicMock(return_value=[{"event": "test"}])

        observer = WebSocketActivityObserver(mock_ws_manager, mock_inner)
        activity = observer.get_recent_activity()

        assert activity == [{"event": "test"}]
        mock_inner.get_recent_activity.assert_called_once()

    def test_websocket_activity_observer_get_recent_activity_no_method(self):
        """Test get_recent_activity returns empty list when inner lacks method."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()
        mock_inner = MagicMock(spec=[])  # No get_recent_activity method

        observer = WebSocketActivityObserver(mock_ws_manager, mock_inner)
        activity = observer.get_recent_activity()

        assert activity == []

    def test_websocket_activity_observer_on_packet_received(self):
        """Test on_packet_received broadcasts activity."""
        from lifx_emulator.devices import PacketEvent
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_activity = AsyncMock()
        mock_inner = MagicMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketActivityObserver(
            mock_ws_manager, mock_inner, task_tracker=tracker
        )

        event = PacketEvent(
            timestamp=1704067200.0,
            direction="rx",
            packet_type=2,
            packet_name="GetService",
            target="d073d5000001",
            addr="192.168.1.100:56700",
        )

        observer.on_packet_received(event)

        mock_inner.on_packet_received.assert_called_once_with(event)
        assert tracker.operations == ["activity:rx:2"]
        mock_ws_manager.broadcast_activity.assert_called_once_with(
            {
                "timestamp": 1704067200.0,
                "direction": "rx",
                "packet_type": 2,
                "packet_name": "GetService",
                "target": "d073d5000001",
                "addr": "192.168.1.100:56700",
            }
        )

    def test_websocket_activity_observer_on_packet_sent(self):
        """Test on_packet_sent broadcasts activity."""
        from lifx_emulator.devices import PacketEvent
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketActivityObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_activity = AsyncMock()
        mock_inner = MagicMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketActivityObserver(
            mock_ws_manager, mock_inner, task_tracker=tracker
        )

        event = PacketEvent(
            timestamp=1704067200.0,
            direction="tx",
            packet_type=3,
            packet_name="StateService",
            device="d073d5000001",
            addr="192.168.1.100:56700",
        )

        observer.on_packet_sent(event)

        mock_inner.on_packet_sent.assert_called_once_with(event)
        assert tracker.operations == ["activity:tx:3"]
        mock_ws_manager.broadcast_activity.assert_called_once_with(
            {
                "timestamp": 1704067200.0,
                "direction": "tx",
                "packet_type": 3,
                "packet_name": "StateService",
                "device": "d073d5000001",
                "addr": "192.168.1.100:56700",
            }
        )

    def test_wire_device_state_events_with_non_device_manager(self):
        """Test wire_device_state_events handles non-DeviceManager instances."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
            wire_device_state_events,
        )

        # Create a mock that's not a DeviceManager
        mock_manager = MagicMock()
        mock_ws_manager = MagicMock()
        state_observer = WebSocketStateChangeObserver(mock_ws_manager)

        # Should not raise, just log warning
        wire_device_state_events(mock_manager, state_observer)

    def test_wire_device_state_events_wires_existing_devices(self):
        """Test wire_device_state_events wires callback to existing devices."""
        from unittest.mock import MagicMock

        from lifx_emulator.devices import DeviceManager
        from lifx_emulator.repositories import DeviceRepository
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
            wire_device_state_events,
        )

        # Create manager with a device
        device_manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d5000001")
        device_manager.add_device(device)

        mock_ws_manager = MagicMock()
        state_observer = WebSocketStateChangeObserver(mock_ws_manager)

        # Wire state events
        wire_device_state_events(device_manager, state_observer)

        # Verify device has callback wired
        assert device.on_state_changed is not None
        assert device.on_state_changed == state_observer.on_state_changed

    def test_wire_device_state_events_wires_new_devices(self):
        """Test wire_device_state_events wires callback to newly added devices."""
        from unittest.mock import MagicMock

        from lifx_emulator.devices import DeviceManager
        from lifx_emulator.repositories import DeviceRepository
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
            wire_device_events,
            wire_device_state_events,
        )

        # Create empty manager
        device_manager = DeviceManager(DeviceRepository())

        mock_ws_manager = MagicMock()
        state_observer = WebSocketStateChangeObserver(mock_ws_manager)

        # Wire both events (lifecycle and state)
        wire_device_events(device_manager, mock_ws_manager)
        wire_device_state_events(device_manager, state_observer)

        # Add a new device
        device = create_color_light("d073d5000002")
        device_manager.add_device(device)

        # Verify device has callback wired
        assert device.on_state_changed is not None
        assert device.on_state_changed == state_observer.on_state_changed

    def test_state_change_observer_invokes_broadcast(self, server):
        """Test WebSocketStateChangeObserver broadcasts device updates."""
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_updated = AsyncMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketStateChangeObserver(mock_ws_manager, task_tracker=tracker)

        device = create_color_light("d073d5000001")

        observer.on_state_changed(device, 102, 1000)

        assert tracker.operations == ["device-updated:d073d5000001:102"]
        serial, changes = mock_ws_manager.broadcast_device_updated.call_args.args
        assert serial == "d073d5000001"
        assert changes["category"] == "color"
        assert changes["duration_ms"] == 1000

    @pytest.mark.asyncio
    async def test_device_added_bridge_survives_forced_collection(self):
        """Test the real tracker strongly retains a blocked device broadcast."""
        started = asyncio.Event()
        release = asyncio.Event()
        completed: list[str] = []

        async def broadcast_device_added(payload: dict[str, Any]) -> None:
            started.set()
            await release.wait()
            completed.append(payload["serial"])

        device_manager = DeviceManager(DeviceRepository())
        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_added = broadcast_device_added
        tracker = BackgroundTaskTracker("test-websocket-event-bridge")
        wire_device_events(device_manager, mock_ws_manager, task_tracker=tracker)

        assert device_manager.add_device(create_color_light("d073d5112233"))
        await started.wait()
        gc.collect()
        assert tracker.pending_count == 1

        release.set()
        await tracker.shutdown()
        assert completed == ["d073d5112233"]
        assert tracker.pending_count == 0

    @pytest.mark.asyncio
    async def test_activity_delegate_precedes_schedule_and_failure_is_logged_once(
        self, caplog
    ):
        """Test ordering and one observed failure for an activity broadcast."""
        delegated = False
        failed = asyncio.Event()

        class InnerObserver:
            def on_packet_received(self, event: PacketEvent) -> None:
                nonlocal delegated
                delegated = True

            def on_packet_sent(self, event: PacketEvent) -> None:
                pass

        async def failing_broadcast(payload: dict[str, Any]) -> None:
            assert delegated
            failed.set()
            raise RuntimeError("bridge broadcast failed")

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_activity = failing_broadcast
        tracker = BackgroundTaskTracker("test-websocket-event-bridge")
        observer = WebSocketActivityObserver(
            mock_ws_manager, InnerObserver(), task_tracker=tracker
        )
        event = PacketEvent(
            timestamp=1704067200.0,
            direction="rx",
            packet_type=2,
            packet_name="GetService",
            target="d073d5000001",
            addr="192.168.1.100:56700",
        )

        with caplog.at_level(logging.ERROR):
            observer.on_packet_received(event)
            await failed.wait()
            await tracker.shutdown()

        failures = [
            record
            for record in caplog.records
            if "activity:rx:2" in record.getMessage()
            and "Background task failed" in record.getMessage()
        ]
        assert len(failures) == 1

    def test_state_change_observer_category_detection(self):
        """Test WebSocketStateChangeObserver correctly categorizes packet types."""
        from unittest.mock import MagicMock

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        observer = WebSocketStateChangeObserver(mock_ws_manager)

        # Test zone packets
        assert observer._get_change_category(501) == "zones"
        assert observer._get_change_category(510) == "zones"

        # Test tile packets
        assert observer._get_change_category(715) == "tiles"
        assert observer._get_change_category(716) == "tiles"

        # Test power packets
        assert observer._get_change_category(21) == "power"
        assert observer._get_change_category(117) == "power"

        # Test metadata packets
        assert observer._get_change_category(24) == "metadata"
        assert observer._get_change_category(49) == "metadata"
        assert observer._get_change_category(52) == "metadata"

        # Test color packets
        assert observer._get_change_category(102) == "color"
        assert observer._get_change_category(103) == "color"

    def test_state_change_observer_with_zone_device(self):
        """Test WebSocketStateChangeObserver broadcasts zone changes."""
        from lifx_emulator.factories import create_multizone_light
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_updated = AsyncMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketStateChangeObserver(mock_ws_manager, task_tracker=tracker)

        # Create a multizone device
        device = create_multizone_light("d073d5000001", zone_count=16)

        # Trigger zone change (SetColorZones packet type 501)
        observer.on_state_changed(device, 501, 500)
        assert tracker.operations == ["device-updated:d073d5000001:501"]

    def test_state_change_observer_with_tile_device(self):
        """Test WebSocketStateChangeObserver broadcasts tile changes."""
        from lifx_emulator.factories import create_tile_device
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_updated = AsyncMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketStateChangeObserver(mock_ws_manager, task_tracker=tracker)

        # Create a tile device
        device = create_tile_device("d073d5000001")

        # Trigger tile change (Set64 packet type 715)
        observer.on_state_changed(device, 715, 500)
        assert tracker.operations == ["device-updated:d073d5000001:715"]

    def test_state_change_observer_with_metadata_change(self):
        """Test WebSocketStateChangeObserver broadcasts metadata changes."""
        from lifx_emulator.factories import create_color_light
        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_updated = AsyncMock()

        tracker = RecordingTaskTracker()
        observer = WebSocketStateChangeObserver(mock_ws_manager, task_tracker=tracker)

        device = create_color_light("d073d5000001")
        device.state.label = "New Label"

        # Trigger metadata change (SetLabel packet type 24)
        observer.on_state_changed(device, 24, 0)

        # AsyncMock records the call when invoked, before the coroutine
        # is awaited, so we can assert on the arguments directly.
        mock_ws_manager.broadcast_device_updated.assert_called_once()
        serial, changes = mock_ws_manager.broadcast_device_updated.call_args[0]
        assert serial == "d073d5000001"
        assert changes["category"] == "metadata"
        assert changes["label"] == "New Label"
        assert "group_label" in changes
        assert "location_label" in changes
        assert tracker.operations == ["device-updated:d073d5000001:24"]


class TestStatsBroadcaster:
    """Tests for the StatsBroadcaster class."""

    @pytest.mark.asyncio
    async def test_stats_broadcaster_start_stop(self, server, ws_manager):
        """Test StatsBroadcaster can be started and stopped."""
        from lifx_emulator_app.api.services.event_bridge import StatsBroadcaster

        broadcaster = StatsBroadcaster(server, ws_manager, interval=0.1)

        try:
            # Start the broadcaster
            broadcaster.start()
            assert broadcaster._task is not None
            assert broadcaster._running is True

            # Let it run briefly
            await asyncio.sleep(0.15)
        finally:
            # Stop the broadcaster
            await broadcaster.stop()

        assert broadcaster._task is None
        assert broadcaster._running is False

    @pytest.mark.asyncio
    async def test_stats_broadcaster_start_idempotent(self, server, ws_manager):
        """Test calling start() multiple times is idempotent."""
        from lifx_emulator_app.api.services.event_bridge import StatsBroadcaster

        broadcaster = StatsBroadcaster(server, ws_manager, interval=0.1)

        try:
            broadcaster.start()
            task1 = broadcaster._task

            # Starting again should not create a new task
            broadcaster.start()
            task2 = broadcaster._task

            assert task1 is task2
        finally:
            await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_stats_broadcaster_stop_idempotent(self, server, ws_manager):
        """Test calling stop() when not running is safe."""
        from lifx_emulator_app.api.services.event_bridge import StatsBroadcaster

        broadcaster = StatsBroadcaster(server, ws_manager, interval=0.1)

        # Stop without starting should not raise
        await broadcaster.stop()
        assert broadcaster._task is None

    @pytest.mark.asyncio
    async def test_stats_broadcaster_handles_broadcast_exception(self):
        """Test StatsBroadcaster handles exceptions in broadcast loop."""
        from unittest.mock import AsyncMock, MagicMock

        from lifx_emulator_app.api.services.event_bridge import StatsBroadcaster

        mock_server = MagicMock()
        mock_server.get_stats = MagicMock(side_effect=RuntimeError("Stats error"))

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_stats = AsyncMock()

        broadcaster = StatsBroadcaster(mock_server, mock_ws_manager, interval=0.05)

        try:
            broadcaster.start()
            # Let it try to broadcast (and fail) at least once
            await asyncio.sleep(0.1)
            # Should still be running despite error
            assert broadcaster._running is True
        finally:
            await broadcaster.stop()


class TestWebSocketManagerBroadcasting:
    """Async unit tests for WebSocketManager broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_methods_coverage(self, ws_manager):
        """Test all broadcast methods for coverage."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mock WebSocket and register with all subscriptions
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await ws_manager.connect(mock_ws)
        await ws_manager.subscribe(mock_ws, ["devices", "activity", "scenarios"])

        # Test broadcast_device_added
        await ws_manager.broadcast_device_added({"serial": "test"})
        assert mock_ws.send_json.call_count == 1

        # Test broadcast_device_removed
        await ws_manager.broadcast_device_removed("test")
        assert mock_ws.send_json.call_count == 2

        # Test broadcast_device_updated
        await ws_manager.broadcast_device_updated("test", {"power": 65535})
        assert mock_ws.send_json.call_count == 3

        # Test broadcast_activity
        await ws_manager.broadcast_activity({"event": "test"})
        assert mock_ws.send_json.call_count == 4

        # Test broadcast_scenario_changed
        await ws_manager.broadcast_scenario_changed("global", None, {"test": True})
        assert mock_ws.send_json.call_count == 5

    @pytest.mark.asyncio
    async def test_broadcast_error_handling(self, ws_manager):
        """Test broadcast handles client send failures."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mock that fails on send
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=RuntimeError("Send failed"))

        await ws_manager.connect(mock_ws)
        await ws_manager.subscribe(mock_ws, ["stats"])

        initial_count = ws_manager.client_count
        assert initial_count == 1

        # Broadcast should handle error and disconnect client
        await ws_manager.broadcast_stats({"uptime": 100})

        # Client should be disconnected after error
        assert ws_manager.client_count == 0

    @pytest.mark.asyncio
    async def test_send_to_client_error_handling(self, ws_manager):
        """Test _send_to_client method handles exceptions."""
        from unittest.mock import AsyncMock, MagicMock

        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=RuntimeError("Network error"))

        await ws_manager.connect(mock_ws)
        assert ws_manager.client_count == 1

        # _send_to_client should catch exception and disconnect
        await ws_manager._send_to_client(mock_ws, {"type": "test", "data": {}})

        assert ws_manager.client_count == 0

    @pytest.mark.asyncio
    async def test_sync_with_nonexistent_client(self, ws_manager):
        """Test _send_full_sync handles nonexistent client gracefully."""
        from unittest.mock import MagicMock

        # Create a mock websocket that was never connected
        mock_ws = MagicMock()

        # Should return early without error
        await ws_manager._send_full_sync(mock_ws)


class TestWebSocketExceptionHandling:
    """Tests for WebSocket exception handling in router."""

    def test_websocket_error_logging(self, client, caplog):
        """Test WebSocket logs errors when invalid data is received."""
        import logging

        with caplog.at_level(logging.ERROR):
            # Note: TestClient has limitations with async WebSocket error scenarios
            # We verify the exception handling exists by checking logs
            with client.websocket_connect("/ws") as websocket:
                # Normal operation works
                websocket.send_json({"type": "subscribe", "topics": ["stats"]})

                # Invalid message type triggers error response
                websocket.send_json({"type": "invalid_type"})
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "invalid_type" in response["message"].lower()

    def test_websocket_handles_client_disconnect(self, client):
        """Test WebSocket handles client disconnects gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Subscribe normally first to verify connection works
            websocket.send_json({"type": "subscribe", "topics": ["stats"]})
            websocket.send_json({"type": "sync"})
            response = websocket.receive_json()
            assert response["type"] == "sync"

            # Close the connection from client side
            websocket.close()

        # Connection should close cleanly without server errors
        # (verified by context manager exiting without exception)
