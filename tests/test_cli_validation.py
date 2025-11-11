"""Tests for CLI parameter validation."""

import re
import socket
import subprocess
import sys
from contextlib import contextmanager

import pytest

from lifx_emulator.api import create_api_app
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


def find_free_port():
    """Find an unused port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@contextmanager
def managed_subprocess(cmd, **kwargs):
    """Context manager for subprocess that ensures cleanup."""
    timeout = kwargs.pop("timeout", None)
    process = None
    try:
        process = subprocess.Popen(cmd, **kwargs)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            yield (stdout, stderr, process.returncode)
        except subprocess.TimeoutExpired:
            # Timeout occurred - terminate the process gracefully
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work
                process.kill()
                stdout, stderr = process.communicate()
            raise
    finally:
        # Ensure process is cleaned up
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


class TestCLIValidation:
    """Test CLI parameter validation (CLI-level validation errors)."""

    def test_persistent_scenarios_requires_persistent(self):
        """Test that --persistent-scenarios requires --persistent."""
        with managed_subprocess(
            ["uv", "run", "lifx-emulator", "--persistent-scenarios", "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        ) as (stdout, stderr, returncode):
            # Should exit with error code
            assert returncode != 0, f"Expected non-zero exit code, got {returncode}"

            # Should have error message in output (either stdout or stderr)
            output = stdout + stderr
            assert re.search(
                r"--persistent-scenarios requires.*--persistent", output, re.DOTALL
            )

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Subprocess termination unreliable on Windows"
    )
    def test_persistent_scenarios_with_persistent_works(self):
        """Test that --persistent-scenarios works when --persistent is set."""
        port = find_free_port()
        try:
            with managed_subprocess(
                [
                    "uv",
                    "run",
                    "lifx-emulator",
                    "--persistent",
                    "--persistent-scenarios",
                    "--verbose",
                    "--port",
                    str(port),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2,
            ) as (stdout, stderr, returncode):
                output = stdout + stderr
                assert (
                    "OSError" not in output and "Address already in use" not in output
                )
        except subprocess.TimeoutExpired:
            # Timeout expected: server started successfully but was cleaned up
            pass


class TestServerConfiguration:
    """Test server configuration via in-process API (much faster)."""

    @pytest.fixture
    def api_app(self):
        """Create API app with test server."""
        # Create default color device
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)
        return app, server

    @pytest.fixture
    def client(self, api_app):
        """Create test client."""
        from fastapi.testclient import TestClient

        app, _server = api_app
        with TestClient(app) as client:
            yield client

    def test_default_color_device(self, client):
        """Test default color device is created."""
        response = client.get("/api/devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["has_color"] is True

    def test_multiple_color_devices(self):
        """Test creating multiple color devices."""
        devices = [
            create_color_light("d073d5000001"),
            create_color_light("d073d5000002"),
        ]
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            devices, device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            device_list = response.json()
            assert len(device_list) == 2
            for device in device_list:
                assert device["has_color"] is True

    def test_multizone_device_with_zone_count(self):
        """Test multizone device with custom zone count."""
        device = create_multizone_light("d073d5000001", zone_count=24)
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert len(devices) == 1
            assert devices[0]["has_multizone"] is True
            assert devices[0]["zone_count"] == 24

    def test_custom_serial_prefix(self):
        """Test device with custom serial prefix."""
        device = create_color_light("cafe00000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["serial"] == "cafe00000001"
            assert devices[0]["serial"].startswith("cafe00")

    def test_multiple_device_types(self):
        """Test server with multiple device types."""
        devices = [
            create_color_light("d073d5000001"),
            create_multizone_light("d073d5000002", zone_count=16),
            create_tile_device("d073d5000003", tile_count=1),
        ]
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            devices, device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            device_list = response.json()
            assert len(device_list) == 3

            # Verify device types
            has_color = any(
                d["has_color"] and not d["has_multizone"] for d in device_list
            )
            has_multizone = any(d["has_multizone"] for d in device_list)
            has_matrix = any(d["has_matrix"] for d in device_list)

            assert has_color, "Should have color-only device"
            assert has_multizone, "Should have multizone device"
            assert has_matrix, "Should have matrix device"

    def test_tile_device_dimensions(self):
        """Test tile device with custom dimensions."""
        device = create_tile_device(
            "d073d5000001", tile_count=1, tile_width=16, tile_height=8
        )
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["has_matrix"] is True
            assert len(devices[0]["tile_devices"]) > 0
            assert any(t["width"] == 8 for t in devices[0]["tile_devices"])

    def test_infrared_device(self):
        """Test infrared device creation."""
        device = create_infrared_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["has_infrared"] is True

    def test_hev_device(self):
        """Test HEV device creation."""
        device = create_hev_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["has_hev"] is True

    def test_color_temperature_device(self):
        """Test color temperature device creation."""
        device = create_color_temperature_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["power_level"] >= 0

    def test_multizone_extended(self):
        """Test extended multizone device."""
        device = create_multizone_light(
            "d073d5000001", zone_count=82, extended_multizone=True
        )
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["has_multizone"] is True
            assert devices[0]["has_extended_multizone"] is True
            assert devices[0]["zone_count"] == 82

    def test_multizone_non_extended(self):
        """Test non-extended multizone device."""
        device = create_multizone_light(
            "d073d5000001", zone_count=16, extended_multizone=False
        )
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["has_multizone"] is True
            assert devices[0]["has_extended_multizone"] is False

    def test_verbose_flag(self):
        """Test verbose logging flag (just verify server starts)."""
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200

    def test_custom_bind_address(self):
        """Test custom bind address (verify config)."""
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        assert server.bind_address == "127.0.0.1"

    def test_api_flag_enabled(self):
        """Test API flag enables HTTP API."""
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            # API should be responding
            response = client.get("/api/devices")
            assert response.status_code == 200

    def test_product_id_creation(self):
        """Test device creation by product ID."""
        from lifx_emulator.factories import create_device

        # Product 27 is LIFX A19
        device = create_device(product_id=27)
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            devices = response.json()
            assert devices[0]["product"] == 27
            assert devices[0]["has_color"] is True

    def test_multiple_product_ids(self):
        """Test creating multiple devices by product ID."""
        from lifx_emulator.factories import create_device

        devices = [
            create_device(product_id=27),  # A19
            create_device(product_id=32),  # Z strip
            create_device(product_id=55),  # Tile
        ]
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            devices, device_manager, "127.0.0.1", find_free_port()
        )
        app = create_api_app(server)

        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.get("/api/devices")
            assert response.status_code == 200
            device_list = response.json()
            assert len(device_list) == 3
            products = {d["product"] for d in device_list}
            assert 27 in products
            assert 32 in products
            assert 55 in products
