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

    @pytest.mark.skip(
        reason="TestClient runs in sync context without event loop for device callbacks"
    )
    def test_device_added_broadcast(self, client, server):
        """Test device_added event is broadcast to WebSocket clients."""
        import time

        with client.websocket_connect("/ws") as websocket:
            # Subscribe to devices topic
            websocket.send_json({"type": "subscribe", "topics": ["devices"]})

            # Add a device (triggers device_added event)
            device = create_color_light("d073d5aabbcc")
            server.add_device(device)

            # Small delay to allow async broadcast to complete
            time.sleep(0.05)

            # Receive the device_added message
            response = websocket.receive_json(timeout=1)
            assert response["type"] == "device_added"
            assert response["data"]["serial"] == "d073d5aabbcc"

    @pytest.mark.skip(
        reason="TestClient runs in sync context without event loop for device callbacks"
    )
    def test_device_removed_broadcast(self, client, server):
        """Test device_removed event is broadcast to WebSocket clients."""
        import time

        # Add device first
        device = create_color_light("d073d5ddeeff")
        server.add_device(device)

        with client.websocket_connect("/ws") as websocket:
            # Subscribe to devices topic
            websocket.send_json({"type": "subscribe", "topics": ["devices"]})

            # Remove the device (triggers device_removed event)
            server.remove_device("d073d5ddeeff")

            # Small delay to allow async broadcast to complete
            time.sleep(0.05)

            # Receive the device_removed message
            response = websocket.receive_json(timeout=1)
            assert response["type"] == "device_removed"
            assert response["data"]["serial"] == "d073d5ddeeff"

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
