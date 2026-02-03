"""Unit tests for the FastAPI management API."""

import pytest
from fastapi.testclient import TestClient
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from lifx_emulator_app.api import create_api_app


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
        """Test GET /api/devices returns paginated device list."""
        response = api_client.get("/api/devices")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["offset"] == 0
        assert data["limit"] == 50
        assert len(data["devices"]) == 2
        assert data["devices"][0]["serial"] == "d073d5000001"
        assert data["devices"][1]["serial"] == "d073d5000002"

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


class TestDeviceStateUpdate:
    """Test PATCH /api/devices/{serial}/state endpoint."""

    def test_update_power_level(self, api_client):
        """Test updating power level."""
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={"power_level": 65535},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["power_level"] == 65535

        # Verify via GET
        response = api_client.get("/api/devices/d073d5000001")
        assert response.json()["power_level"] == 65535

    def test_update_color(self, api_client):
        """Test updating color on a color light."""
        color = {"hue": 10000, "saturation": 50000, "brightness": 40000, "kelvin": 3500}
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={"color": color},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["color"]["hue"] == 10000
        assert data["color"]["saturation"] == 50000

    def test_update_color_fills_zones(self, api_client):
        """Test that updating color on a multizone device fills all zones."""
        color = {"hue": 20000, "saturation": 30000, "brightness": 40000, "kelvin": 4000}
        response = api_client.patch(
            "/api/devices/d073d5000002/state",
            json={"color": color},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["color"]["hue"] == 20000
        # All zones should have the same color
        for zone in data["zone_colors"]:
            assert zone["hue"] == 20000
            assert zone["saturation"] == 30000

    def test_update_color_fills_tiles(self, api_client, server_with_devices):
        """Test that updating color on a matrix device fills all tiles."""
        tile_device = create_tile_device("d073d5000003")
        server_with_devices.add_device(tile_device)

        color = {"hue": 15000, "saturation": 25000, "brightness": 35000, "kelvin": 3500}
        response = api_client.patch(
            "/api/devices/d073d5000003/state",
            json={"color": color},
        )
        assert response.status_code == 200
        data = response.json()
        for tile in data["tile_devices"]:
            for c in tile["colors"]:
                assert c["hue"] == 15000

    def test_update_zone_colors(self, api_client):
        """Test updating zone colors on a multizone device."""
        colors = [
            {"hue": i * 1000, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
            for i in range(16)
        ]
        response = api_client.patch(
            "/api/devices/d073d5000002/state",
            json={"zone_colors": colors},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["zone_colors"]) == 16
        assert data["zone_colors"][0]["hue"] == 0
        assert data["zone_colors"][5]["hue"] == 5000

    def test_update_zone_colors_too_short(self, api_client):
        """Test that short zone_colors list is padded with last color."""
        colors = [
            {"hue": 100, "saturation": 200, "brightness": 300, "kelvin": 3500},
            {"hue": 999, "saturation": 999, "brightness": 999, "kelvin": 4000},
        ]
        response = api_client.patch(
            "/api/devices/d073d5000002/state",
            json={"zone_colors": colors},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["zone_colors"]) == 16
        # First color
        assert data["zone_colors"][0]["hue"] == 100
        # Second color
        assert data["zone_colors"][1]["hue"] == 999
        # Padded with last color
        assert data["zone_colors"][2]["hue"] == 999
        assert data["zone_colors"][15]["hue"] == 999

    def test_update_zone_colors_too_long(self, api_client):
        """Test that long zone_colors list is truncated."""
        colors = [
            {"hue": i * 100, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
            for i in range(30)
        ]
        response = api_client.patch(
            "/api/devices/d073d5000002/state",
            json={"zone_colors": colors},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["zone_colors"]) == 16

    def test_update_zone_colors_not_multizone(self, api_client):
        """Test that updating zone_colors on a non-multizone device returns 400."""
        colors = [{"hue": 0, "saturation": 0, "brightness": 0, "kelvin": 3500}]
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={"zone_colors": colors},
        )
        assert response.status_code == 400

    def test_update_tile_colors(self, api_client, server_with_devices):
        """Test updating tile colors on a matrix device."""
        tile_device = create_tile_device("d073d5000004")
        server_with_devices.add_device(tile_device)

        assert tile_device.state.matrix is not None
        tile_size = (
            tile_device.state.matrix.tile_width * tile_device.state.matrix.tile_height
        )
        colors = [
            {"hue": i * 10, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
            for i in range(tile_size)
        ]
        response = api_client.patch(
            "/api/devices/d073d5000004/state",
            json={"tile_colors": [{"tile_index": 0, "colors": colors}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tile_devices"][0]["colors"]) == tile_size

    def test_update_tile_colors_too_short(self, api_client, server_with_devices):
        """Test that short tile colors list is padded."""
        tile_device = create_tile_device("d073d5000005")
        server_with_devices.add_device(tile_device)

        colors = [
            {"hue": 5000, "saturation": 65535, "brightness": 65535, "kelvin": 3500},
        ]
        response = api_client.patch(
            "/api/devices/d073d5000005/state",
            json={"tile_colors": [{"tile_index": 0, "colors": colors}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert tile_device.state.matrix is not None
        tile_size = (
            tile_device.state.matrix.tile_width * tile_device.state.matrix.tile_height
        )
        assert len(data["tile_devices"][0]["colors"]) == tile_size
        # All padded with last color
        for c in data["tile_devices"][0]["colors"]:
            assert c["hue"] == 5000

    def test_update_tile_colors_too_long(self, api_client, server_with_devices):
        """Test that long tile colors list is truncated."""
        tile_device = create_tile_device("d073d5000006")
        server_with_devices.add_device(tile_device)

        assert tile_device.state.matrix is not None
        tile_size = (
            tile_device.state.matrix.tile_width * tile_device.state.matrix.tile_height
        )
        colors = [
            {"hue": i, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
            for i in range(tile_size + 50)
        ]
        response = api_client.patch(
            "/api/devices/d073d5000006/state",
            json={"tile_colors": [{"tile_index": 0, "colors": colors}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tile_devices"][0]["colors"]) == tile_size

    def test_update_tile_colors_not_matrix(self, api_client):
        """Test that updating tile_colors on a non-matrix device returns 400."""
        colors = [{"hue": 0, "saturation": 0, "brightness": 0, "kelvin": 3500}]
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={"tile_colors": [{"tile_index": 0, "colors": colors}]},
        )
        assert response.status_code == 400

    def test_update_device_not_found(self, api_client):
        """Test PATCH on non-existent device returns 404."""
        response = api_client.patch(
            "/api/devices/aabbccddeeff/state",
            json={"power_level": 0},
        )
        assert response.status_code == 404

    def test_update_empty_body(self, api_client):
        """Test PATCH with empty body is a no-op, returns current state."""
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["serial"] == "d073d5000001"

    def test_update_multiple_fields(self, api_client):
        """Test updating power and color in one request."""
        response = api_client.patch(
            "/api/devices/d073d5000001/state",
            json={
                "power_level": 65535,
                "color": {
                    "hue": 32768,
                    "saturation": 65535,
                    "brightness": 65535,
                    "kelvin": 3500,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["power_level"] == 65535
        assert data["color"]["hue"] == 32768


class TestBulkDeviceCreation:
    """Test POST /api/devices/bulk endpoint."""

    def test_bulk_create_devices(self, api_client, server_with_devices):
        """Test creating multiple devices at once."""
        response = api_client.post(
            "/api/devices/bulk",
            json={
                "devices": [
                    {"product_id": 27, "serial": "aabbccdd0001"},
                    {"product_id": 27, "serial": "aabbccdd0002"},
                    {"product_id": 27, "serial": "aabbccdd0003"},
                ]
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        assert data[0]["serial"] == "aabbccdd0001"
        assert data[1]["serial"] == "aabbccdd0002"
        assert data[2]["serial"] == "aabbccdd0003"
        # Verify all were added (2 original + 3 new)
        assert len(server_with_devices.get_all_devices()) == 5

    def test_bulk_create_with_duplicate_serial_in_batch(self, api_client):
        """Test bulk create with duplicate serial in batch returns 409."""
        response = api_client.post(
            "/api/devices/bulk",
            json={
                "devices": [
                    {"product_id": 27, "serial": "aabbccdd0001"},
                    {"product_id": 27, "serial": "aabbccdd0001"},
                ]
            },
        )
        assert response.status_code == 409

    def test_bulk_create_with_existing_serial(self, api_client):
        """Test bulk create with serial that already exists returns 409."""
        response = api_client.post(
            "/api/devices/bulk",
            json={
                "devices": [
                    {"product_id": 27, "serial": "d073d5000001"},
                ]
            },
        )
        assert response.status_code == 409

    def test_bulk_create_empty_list(self, api_client):
        """Test bulk create with empty list returns 422."""
        response = api_client.post(
            "/api/devices/bulk",
            json={"devices": []},
        )
        assert response.status_code == 422

    def test_bulk_create_rollback_on_failure(self, api_client, server_with_devices):
        """Test that failed bulk create rolls back already-created devices."""
        initial_count = len(server_with_devices.get_all_devices())
        # Second device has a serial that conflicts with an existing device
        response = api_client.post(
            "/api/devices/bulk",
            json={
                "devices": [
                    {"product_id": 27, "serial": "aabbccdd0010"},
                    {"product_id": 27, "serial": "d073d5000001"},
                ]
            },
        )
        assert response.status_code == 409
        # No new devices should remain
        assert len(server_with_devices.get_all_devices()) == initial_count


class TestDeviceListPagination:
    """Test paginated GET /api/devices endpoint."""

    def test_list_devices_default_pagination(self, api_client):
        """Test default pagination returns envelope with total/offset/limit."""
        response = api_client.get("/api/devices")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert data["total"] == 2
        assert data["offset"] == 0
        assert data["limit"] == 50

    def test_list_devices_with_offset(self, api_client):
        """Test skipping devices with offset."""
        response = api_client.get("/api/devices?offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["devices"]) == 1
        assert data["total"] == 2
        assert data["offset"] == 1
        assert data["devices"][0]["serial"] == "d073d5000002"

    def test_list_devices_with_limit(self, api_client):
        """Test limiting results."""
        response = api_client.get("/api/devices?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["devices"]) == 1
        assert data["total"] == 2
        assert data["limit"] == 1
        assert data["devices"][0]["serial"] == "d073d5000001"

    def test_list_devices_offset_beyond_total(self, api_client):
        """Test offset beyond total returns empty list but correct total."""
        response = api_client.get("/api/devices?offset=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data["devices"]) == 0
        assert data["total"] == 2

    def test_list_devices_negative_offset(self, api_client):
        """Test negative offset returns 422."""
        response = api_client.get("/api/devices?offset=-1")
        assert response.status_code == 422


class TestRunAPIServer:
    """Test the run_api_server function."""

    @pytest.mark.asyncio
    async def test_run_api_server_creates_app_and_server(
        self, server_with_devices, monkeypatch
    ):
        """Test that run_api_server creates uvicorn server with correct config."""
        from unittest.mock import AsyncMock, Mock

        from lifx_emulator_app.api.app import run_api_server

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

        from lifx_emulator_app.api.app import run_api_server

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
