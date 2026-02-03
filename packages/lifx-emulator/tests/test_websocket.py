"""Tests for WebSocket endpoint and manager."""

import pytest
from fastapi.testclient import TestClient
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from lifx_emulator_app.api.app import create_api_app
from lifx_emulator_app.api.services.websocket_manager import (
    MessageType,
    Topic,
    WebSocketManager,
)


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
