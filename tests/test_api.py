"""Unit tests for the FastAPI management API."""

import pytest
from fastapi.testclient import TestClient

from lifx_emulator.api import create_api_app
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light, create_multizone_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


@pytest.fixture
def server_with_devices():
    """Create a server with some test devices."""
    devices = [
        create_color_light("d073d5000001"),
        create_multizone_light("d073d5000002", zone_count=16),
    ]
    device_manager = DeviceManager(DeviceRepository())
    return EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)


@pytest.fixture
def api_client(server_with_devices):
    """Create a test client for the API."""
    app = create_api_app(server_with_devices)
    return TestClient(app)


class TestAPIEndpoints:
    """Test API endpoint functionality."""

    def test_get_stats(self, api_client, server_with_devices):
        """Test GET /api/stats returns server statistics."""
        response = api_client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()

        assert "uptime_seconds" in data
        assert "device_count" in data
        assert data["device_count"] == 2
        assert "packets_received" in data
        assert "packets_sent" in data
        assert "error_count" in data

    def test_list_devices(self, api_client):
        """Test GET /api/devices returns all devices."""
        response = api_client.get("/api/devices")
        assert response.status_code == 200
        devices = response.json()

        assert len(devices) == 2
        assert devices[0]["serial"] == "d073d5000001"
        assert devices[1]["serial"] == "d073d5000002"

    def test_get_device(self, api_client):
        """Test GET /api/devices/{serial} returns specific device."""
        response = api_client.get("/api/devices/d073d5000001")
        assert response.status_code == 200
        device = response.json()

        assert device["serial"] == "d073d5000001"
        assert "label" in device
        assert "product" in device
        assert "has_color" in device

    def test_get_device_not_found(self, api_client):
        """Test GET /api/devices/{serial} returns 404 for non-existent device."""
        response = api_client.get("/api/devices/nonexistent")
        assert response.status_code == 404

    def test_create_device(self, api_client, server_with_devices):
        """Test POST /api/devices creates a new device."""
        response = api_client.post("/api/devices", json={"product_id": 27})
        assert response.status_code == 201
        device = response.json()

        assert "serial" in device
        assert device["product"] == 27
        # Verify device was added to server
        assert len(server_with_devices.get_all_devices()) == 3

    def test_create_device_with_invalid_product(self, api_client):
        """Test POST /api/devices with invalid product ID fails validation."""
        response = api_client.post("/api/devices", json={"product_id": 99999})
        # 422 is the correct status for Pydantic validation errors
        assert response.status_code == 422

    def test_create_device_duplicate_serial(self, api_client, server_with_devices):
        """Test POST /api/devices with duplicate serial fails."""
        # Create a device with a specific serial
        device = create_color_light("d073d5000099")
        server_with_devices.add_device(device)

        # Try to create another device with the same serial
        response = api_client.post(
            "/api/devices",
            json={"product_id": 27, "serial": "d073d5000099"},
        )
        assert response.status_code == 409

    def test_delete_device(self, api_client, server_with_devices):
        """Test DELETE /api/devices/{serial} removes a device."""
        response = api_client.delete("/api/devices/d073d5000001")
        assert response.status_code == 204
        # Verify device was removed
        assert len(server_with_devices.get_all_devices()) == 1

    def test_delete_device_not_found(self, api_client):
        """Test DELETE /api/devices/{serial} returns 404 for non-existent device."""
        response = api_client.delete("/api/devices/nonexistent")
        assert response.status_code == 404

    def test_get_activity(self, api_client):
        """Test GET /api/activity returns recent activity."""
        response = api_client.get("/api/activity")
        assert response.status_code == 200
        activity = response.json()
        assert isinstance(activity, list)


class TestWebUI:
    """Test web UI endpoint."""

    def test_root_returns_html(self, api_client):
        """Test GET / returns HTML web UI."""
        response = api_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"LIFX Emulator Monitor" in response.content


class TestOpenAPISchema:
    """Test OpenAPI schema endpoints."""

    def test_openapi_schema_available(self, api_client):
        """Test GET /openapi.json returns OpenAPI schema."""
        response = api_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        # Verify OpenAPI structure
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "LIFX Emulator API"
        assert schema["info"]["version"] == "1.0.0"

        # Verify tags are present
        tags = [tag["name"] for tag in schema["info"].get("tags", [])]
        assert "monitoring" in tags or "monitoring" in [
            tag["name"] for tag in schema.get("tags", [])
        ]
        assert "devices" in tags or "devices" in [
            tag["name"] for tag in schema.get("tags", [])
        ]

    def test_swagger_ui_available(self, api_client):
        """Test GET /docs returns Swagger UI."""
        response = api_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_available(self, api_client):
        """Test GET /redoc returns ReDoc documentation."""
        response = api_client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestGlobalScenarios:
    """Test global scenario management endpoints."""

    def test_get_global_scenario(self, api_client):
        """Test GET /api/scenarios/global returns global scenario."""
        response = api_client.get("/api/scenarios/global")
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "global"
        assert data["identifier"] is None
        assert "scenario" in data
        assert isinstance(data["scenario"]["drop_packets"], dict)
        assert isinstance(data["scenario"]["response_delays"], dict)

    def test_set_global_scenario(self, api_client):
        """Test PUT /api/scenarios/global sets global scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0, "102": 0.6},
            "response_delays": {"101": 0.5},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "global"
        assert data["scenario"]["drop_packets"] == {"101": 1.0, "102": 0.6}
        assert data["scenario"]["response_delays"] == {"101": 0.5}

    def test_set_global_scenario_with_firmware_version(self, api_client):
        """Test setting global scenario with firmware version override."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": [2, 60],
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"]["firmware_version"] == [2, 60]

    def test_clear_global_scenario(self, api_client):
        """Test DELETE /api/scenarios/global clears global scenario."""
        # First set a scenario
        scenario_config = {
            "drop_packets": {"101": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/global", json=scenario_config)

        # Then clear it
        response = api_client.delete("/api/scenarios/global")
        assert response.status_code == 204


class TestDeviceScenarios:
    """Test device-specific scenario management endpoints."""

    def test_get_device_scenario_not_set(self, api_client):
        """Test GET /api/scenarios/devices/{serial} returns 404 when not set."""
        response = api_client.get("/api/scenarios/devices/d073d5000001")
        assert response.status_code == 404

    def test_set_device_scenario(self, api_client):
        """Test PUT /api/scenarios/devices/{serial} sets device scenario."""
        scenario_config = {
            "drop_packets": {"103": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put(
            "/api/scenarios/devices/d073d5000001", json=scenario_config
        )
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "device"
        assert data["identifier"] == "d073d5000001"
        assert data["scenario"]["drop_packets"] == {"103": 1.0}

    def test_get_device_scenario(self, api_client):
        """Test GET /api/scenarios/devices/{serial} retrieves device scenario."""
        scenario_config = {
            "drop_packets": {"104": 1.0},
            "response_delays": {"116": 0.25},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/devices/d073d5000001", json=scenario_config)

        response = api_client.get("/api/scenarios/devices/d073d5000001")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"]["drop_packets"] == {"104": 1.0}
        assert data["scenario"]["response_delays"] == {"116": 0.25}

    def test_set_device_scenario_nonexistent_device(self, api_client):
        """Test PUT /api/scenarios/devices/{serial} with non-existent device."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put(
            "/api/scenarios/devices/nonexistent", json=scenario_config
        )
        assert response.status_code == 404

    def test_clear_device_scenario(self, api_client):
        """Test DELETE /api/scenarios/devices/{serial} clears device scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/devices/d073d5000001", json=scenario_config)

        response = api_client.delete("/api/scenarios/devices/d073d5000001")
        assert response.status_code == 204

        # Verify it's cleared
        response = api_client.get("/api/scenarios/devices/d073d5000001")
        assert response.status_code == 404

    def test_clear_device_scenario_not_set(self, api_client):
        """Test DELETE /api/scenarios/devices/{serial} when not set."""
        response = api_client.delete("/api/scenarios/devices/d073d5000001")
        assert response.status_code == 404


class TestTypeScenarios:
    """Test device-type-specific scenario management endpoints."""

    def test_get_type_scenario_not_set(self, api_client):
        """Test GET /api/scenarios/types/{type} returns 404 when not set."""
        response = api_client.get("/api/scenarios/types/color")
        assert response.status_code == 404

    def test_set_type_scenario(self, api_client):
        """Test PUT /api/scenarios/types/{type} sets type scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0, "102": 0.6},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/types/color", json=scenario_config)
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "type"
        assert data["identifier"] == "color"
        assert data["scenario"]["drop_packets"] == {"101": 1.0, "102": 0.6}

    def test_get_type_scenario(self, api_client):
        """Test GET /api/scenarios/types/{type} retrieves type scenario."""
        scenario_config = {
            "drop_packets": {"105": 1.0},
            "response_delays": {"502": 1.0},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/types/multizone", json=scenario_config)

        response = api_client.get("/api/scenarios/types/multizone")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"]["drop_packets"] == {"105": 1.0}
        assert data["scenario"]["response_delays"] == {"502": 1.0}

    def test_clear_type_scenario(self, api_client):
        """Test DELETE /api/scenarios/types/{type} clears type scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/types/matrix", json=scenario_config)

        response = api_client.delete("/api/scenarios/types/matrix")
        assert response.status_code == 204

        # Verify it's cleared
        response = api_client.get("/api/scenarios/types/matrix")
        assert response.status_code == 404

    def test_clear_type_scenario_not_set(self, api_client):
        """Test DELETE /api/scenarios/types/{type} when not set."""
        response = api_client.delete("/api/scenarios/types/color")
        assert response.status_code == 404

    def test_set_type_scenario_multiple_types(self, api_client):
        """Test setting scenarios for multiple device types."""
        scenario_config = {
            "drop_packets": {"501": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }

        types = ["color", "multizone", "matrix", "infrared", "hev"]
        for device_type in types:
            response = api_client.put(
                f"/api/scenarios/types/{device_type}", json=scenario_config
            )
            assert response.status_code == 200


class TestLocationScenarios:
    """Test location-specific scenario management endpoints."""

    def test_get_location_scenario_not_set(self, api_client):
        """Test GET /api/scenarios/locations/{location} returns 404 when not set."""
        response = api_client.get("/api/scenarios/locations/Kitchen")
        assert response.status_code == 404

    def test_set_location_scenario(self, api_client):
        """Test PUT /api/scenarios/locations/{location} sets location scenario."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {"116": 0.5},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put(
            "/api/scenarios/locations/Kitchen", json=scenario_config
        )
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "location"
        assert data["identifier"] == "Kitchen"
        assert data["scenario"]["response_delays"] == {"116": 0.5}

    def test_get_location_scenario(self, api_client):
        """Test GET /api/scenarios/locations/{location} retrieves location scenario."""
        scenario_config = {
            "drop_packets": {"506": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/locations/Bedroom", json=scenario_config)

        response = api_client.get("/api/scenarios/locations/Bedroom")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"]["drop_packets"] == {"506": 1.0}

    def test_clear_location_scenario(self, api_client):
        """Test DELETE /api/scenarios/locations/{location} clears location scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/locations/Living Room", json=scenario_config)

        response = api_client.delete("/api/scenarios/locations/Living Room")
        assert response.status_code == 204

        # Verify it's cleared
        response = api_client.get("/api/scenarios/locations/Living Room")
        assert response.status_code == 404

    def test_clear_location_scenario_not_set(self, api_client):
        """Test DELETE /api/scenarios/locations/{location} when not set."""
        response = api_client.delete("/api/scenarios/locations/Basement")
        assert response.status_code == 404


class TestGroupScenarios:
    """Test group-specific scenario management endpoints."""

    def test_get_group_scenario_not_set(self, api_client):
        """Test GET /api/scenarios/groups/{group} returns 404 when not set."""
        response = api_client.get("/api/scenarios/groups/Bedroom Lights")
        assert response.status_code == 404

    def test_set_group_scenario(self, api_client):
        """Test PUT /api/scenarios/groups/{group} sets group scenario."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {"101": 0.75},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put(
            "/api/scenarios/groups/Bedroom Lights", json=scenario_config
        )
        assert response.status_code == 200
        data = response.json()

        assert data["scope"] == "group"
        assert data["identifier"] == "Bedroom Lights"
        assert data["scenario"]["response_delays"] == {"101": 0.75}

    def test_get_group_scenario(self, api_client):
        """Test GET /api/scenarios/groups/{group} retrieves group scenario."""
        scenario_config = {
            "drop_packets": {"512": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/groups/Living Room Lights", json=scenario_config)

        response = api_client.get("/api/scenarios/groups/Living Room Lights")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"]["drop_packets"] == {"512": 1.0}

    def test_clear_group_scenario(self, api_client):
        """Test DELETE /api/scenarios/groups/{group} clears group scenario."""
        scenario_config = {
            "drop_packets": {"101": 1.0},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        api_client.put("/api/scenarios/groups/Kitchen Lights", json=scenario_config)

        response = api_client.delete("/api/scenarios/groups/Kitchen Lights")
        assert response.status_code == 204

        # Verify it's cleared
        response = api_client.get("/api/scenarios/groups/Kitchen Lights")
        assert response.status_code == 404

    def test_clear_group_scenario_not_set(self, api_client):
        """Test DELETE /api/scenarios/groups/{group} when not set."""
        response = api_client.delete("/api/scenarios/groups/Office Lights")
        assert response.status_code == 404


class TestScenarioConfiguration:
    """Test various scenario configuration options."""

    def test_scenario_with_all_options(self, api_client):
        """Test scenario with all configuration options set."""
        scenario_config = {
            "drop_packets": {"101": 1.0, "102": 0.8, "103": 0.6},
            "response_delays": {"101": 0.5, "102": 1.0},
            "malformed_packets": [104, 105],
            "invalid_field_values": [106],
            "firmware_version": [3, 70],
            "partial_responses": [507],
            "send_unhandled": True,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200
        data = response.json()

        assert data["scenario"]["drop_packets"] == {"101": 1.0, "102": 0.8, "103": 0.6}
        assert data["scenario"]["response_delays"] == {"101": 0.5, "102": 1.0}
        assert data["scenario"]["malformed_packets"] == [104, 105]
        assert data["scenario"]["invalid_field_values"] == [106]
        assert data["scenario"]["firmware_version"] == [3, 70]
        assert data["scenario"]["partial_responses"] == [507]
        assert data["scenario"]["send_unhandled"] is True

    def test_scenario_with_empty_config(self, api_client):
        """Test scenario with empty/default configuration."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200
        data = response.json()

        assert data["scenario"]["drop_packets"] == {}
        assert data["scenario"]["response_delays"] == {}
        assert data["scenario"]["firmware_version"] is None
        assert data["scenario"]["send_unhandled"] is False

    def test_scenario_response_delays_numeric_keys(self, api_client):
        """Test that response delays support numeric packet type keys."""
        scenario_config = {
            "drop_packets": {},
            "response_delays": {"101": 0.1, "102": 0.2, "116": 0.5},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put(
            "/api/scenarios/devices/d073d5000002", json=scenario_config
        )
        assert response.status_code == 200
        data = response.json()

        # Response delays should include all three delays (as strings due to JSON)
        assert len(data["scenario"]["response_delays"]) == 3
        assert data["scenario"]["response_delays"]["101"] == 0.1
        assert data["scenario"]["response_delays"]["102"] == 0.2
        assert data["scenario"]["response_delays"]["116"] == 0.5

    def test_scenario_drop_packets_string_keys_converted(
        self, api_client, server_with_devices
    ):
        """Test that string keys in drop_packets are converted to integers.

        Regression test for bug where JSON string keys like {"101": 1.0}
        were not being converted to integers, causing packet dropping to fail
        because the comparison was int vs string.
        """
        from lifx_emulator.protocol.header import LifxHeader

        # Set scenario with string keys (as JSON will provide)
        scenario_config = {
            "drop_packets": {"101": 1.0},  # String key
            "response_delays": {},
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200

        # Verify the device's scenario manager has integer keys
        device = server_with_devices.get_device("d073d5000001")
        resolved_scenario = device._get_resolved_scenario()

        # Keys should be integers, not strings
        assert 101 in resolved_scenario.drop_packets
        assert "101" not in resolved_scenario.drop_packets
        assert resolved_scenario.drop_packets[101] == 1.0

        # Verify packet dropping actually works
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=101,  # GetColor - should be dropped
            res_required=True,
        )
        responses = device.process_packet(header, None)
        assert len(responses) == 0  # Packet should be dropped

    def test_scenario_response_delays_string_keys_converted(
        self, api_client, server_with_devices
    ):
        """Test that string keys in response_delays are converted to integers.

        Ensures Pydantic validation correctly converts JSON string keys like
        {"101": 0.5} to integer keys for proper packet type matching.
        """
        # Set scenario with string keys (as JSON will provide)
        scenario_config = {
            "drop_packets": {},
            "response_delays": {"101": 0.5, "116": 1.0},  # String keys
            "malformed_packets": [],
            "invalid_field_values": [],
            "firmware_version": None,
            "partial_responses": [],
            "send_unhandled": False,
        }
        response = api_client.put("/api/scenarios/global", json=scenario_config)
        assert response.status_code == 200

        # Verify the response contains the expected data
        data = response.json()
        assert data["scenario"]["response_delays"] == {"101": 0.5, "116": 1.0}

        # Verify the device's scenario manager has integer keys
        device = server_with_devices.get_device("d073d5000001")
        resolved_scenario = device._get_resolved_scenario()

        # Keys should be integers, not strings
        assert 101 in resolved_scenario.response_delays
        assert "101" not in resolved_scenario.response_delays
        assert resolved_scenario.response_delays[101] == 0.5

        assert 116 in resolved_scenario.response_delays
        assert "116" not in resolved_scenario.response_delays
        assert resolved_scenario.response_delays[116] == 1.0


class TestRunAPIServer:
    """Test the run_api_server function."""

    @pytest.mark.asyncio
    async def test_run_api_server_creates_app_and_server(
        self, server_with_devices, monkeypatch
    ):
        """Test that run_api_server creates uvicorn server with correct config."""
        from unittest.mock import AsyncMock, Mock

        from lifx_emulator.api.app import run_api_server

        # Mock uvicorn components
        mock_server_instance = Mock()
        mock_server_instance.serve = AsyncMock()
        mock_server_class = Mock(return_value=mock_server_instance)
        mock_config_class = Mock()

        # Track what was passed to uvicorn.Server and uvicorn.Config
        captured_config = None

        def capture_config(*args, **kwargs):
            nonlocal captured_config
            captured_config = kwargs if kwargs else args[0] if args else None
            return Mock()

        mock_config_class.side_effect = capture_config

        # Monkeypatch uvicorn
        import uvicorn

        monkeypatch.setattr(uvicorn, "Server", mock_server_class)
        monkeypatch.setattr(uvicorn, "Config", mock_config_class)

        # Call the function
        await run_api_server(server_with_devices, host="0.0.0.0", port=9090)

        # Verify Config was called
        assert mock_config_class.called

        # Verify Server was called
        assert mock_server_class.called

        # Verify serve was called
        assert mock_server_instance.serve.called

    @pytest.mark.asyncio
    async def test_run_api_server_default_host_and_port(
        self, server_with_devices, monkeypatch
    ):
        """Test that run_api_server uses default host and port."""
        from unittest.mock import AsyncMock, Mock

        from lifx_emulator.api.app import run_api_server

        # Mock uvicorn components
        mock_server_instance = Mock()
        mock_server_instance.serve = AsyncMock()
        mock_server_class = Mock(return_value=mock_server_instance)

        # Capture the Config call
        config_args = []

        def capture_config(*args, **kwargs):
            config_args.append((args, kwargs))
            return Mock()

        mock_config_class = Mock(side_effect=capture_config)

        # Monkeypatch uvicorn
        import uvicorn

        monkeypatch.setattr(uvicorn, "Server", mock_server_class)
        monkeypatch.setattr(uvicorn, "Config", mock_config_class)

        # Call with default host/port
        await run_api_server(server_with_devices)

        # Verify Config was called
        assert mock_config_class.called

        # Verify Server and serve were called
        assert mock_server_class.called
        assert mock_server_instance.serve.called
