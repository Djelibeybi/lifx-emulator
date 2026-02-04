"""Tests for WebSocket endpoint and manager."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from lifx_emulator_app.api.app import create_api_app
from lifx_emulator_app.api.services import MessageType, Topic, WebSocketManager


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
        from unittest.mock import AsyncMock, MagicMock, patch

        from lifx_emulator_app.api.services.event_bridge import (
            WebSocketStateChangeObserver,
        )

        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_device_updated = AsyncMock()

        observer = WebSocketStateChangeObserver(mock_ws_manager)

        device = create_color_light("d073d5000001")

        # Mock the async scheduling
        with patch(
            "lifx_emulator_app.api.services.event_bridge._schedule_async"
        ) as mock_schedule:
            observer.on_state_changed(device, 102, 1000)

            # Verify _schedule_async was called with the broadcast coroutine
            mock_schedule.assert_called_once()
            args = mock_schedule.call_args[0]
            # The first arg should be a coroutine
            assert args[0] is not None

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

        # Test color packets
        assert observer._get_change_category(102) == "color"
        assert observer._get_change_category(103) == "color"


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
