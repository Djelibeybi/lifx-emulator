"""Unit tests for EmulatedLifxServer packet routing and UDP handling."""

import asyncio
import socket
from unittest.mock import AsyncMock, Mock

import pytest

from lifx_emulator.constants import HEADER_SIZE
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


def find_free_port():
    """Find an unused port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestServerInitialization:
    """Test EmulatedLifxServer initialization."""

    def test_server_init_with_devices(self, color_device, multizone_device):
        """Test server initializes with device list."""
        devices = [color_device, multizone_device]
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)

        assert server.bind_address == "127.0.0.1"
        assert server.port == 56700
        assert len(server.get_all_devices()) == 2
        assert server.get_device(color_device.state.serial) == color_device
        assert server.get_device(multizone_device.state.serial) == multizone_device

    def test_server_init_default_params(self, color_device):
        """Test server initialization with default parameters."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager)
        assert server.bind_address == "127.0.0.1"
        assert server.port == 56700

    def test_server_device_lookup_by_mac(self, color_device):
        """Test devices are indexed by serial string."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)
        serial = color_device.state.serial
        assert server.get_device(serial) == color_device


class TestPacketRouting:
    """Test server packet routing logic."""

    @pytest.mark.asyncio
    async def test_handle_packet_too_short(self, server_with_devices):
        """Test server ignores packets shorter than header size."""
        short_packet = b"\x00\x01\x02"  # Only 3 bytes
        addr = ("127.0.0.1", 56700)

        # Should not raise exception, just log warning
        await server_with_devices.handle_packet(short_packet, addr)

    @pytest.mark.asyncio
    async def test_handle_packet_broadcast_tagged(self, color_device):
        """Test broadcast packets (tagged=True) route to all devices."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        # Create broadcast GetService packet
        header = LifxHeader(
            source=12345,
            target=b"\x00" * 8,
            sequence=1,
            pkt_type=2,  # GetService
            tagged=True,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        # Mock transport
        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should send response (StateService)
        assert server.transport.sendto.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_packet_specific_target(self, color_device, multizone_device):
        """Test packet routes to specific device by MAC address."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device, multizone_device], device_manager, "127.0.0.1", 56700
        )

        # Create targeted GetLabel packet for color_device
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,  # GetLabel
            tagged=False,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        # Mock transport
        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should send StateLabel response
        assert server.transport.sendto.call_count >= 1
        sent_data, sent_addr = server.transport.sendto.call_args[0]
        assert sent_addr == addr

        # Parse response header
        resp_header = LifxHeader.unpack(sent_data)
        assert resp_header.pkt_type == 25  # StateLabel

    @pytest.mark.asyncio
    async def test_handle_packet_unknown_target(self, color_device):
        """Test packet to unknown device MAC is ignored."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        # Create packet for non-existent device
        header = LifxHeader(
            source=12345,
            target=b"\xff\xff\xff\xff\xff\xff\x00\x00",
            sequence=1,
            pkt_type=23,  # GetLabel
            tagged=False,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        # Mock transport
        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should not send any response
        server.transport.sendto.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_packet_null_target_broadcasts(
        self, color_device, multizone_device
    ):
        """Test null target (all zeros) broadcasts to all devices."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device, multizone_device], device_manager, "127.0.0.1", 56700
        )

        header = LifxHeader(
            source=12345,
            target=b"\x00" * 8,
            sequence=1,
            pkt_type=2,  # GetService
            tagged=False,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should send responses from both devices
        assert server.transport.sendto.call_count >= 2


class TestResponseDelays:
    """Test server response delay handling."""

    @pytest.mark.asyncio
    async def test_response_delay_applied(self, color_device):
        """Test server applies response delays from device scenarios."""
        from lifx_emulator.scenarios.manager import (
            HierarchicalScenarioManager,
            ScenarioConfig,
        )

        # Create device with delay scenario for StateColor response (packet type 107)
        # Note: delay is for the RESPONSE packet type, not the request type
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(response_delays={107: 0.1}),  # StateColor response
        )
        # Pass scenario_manager to server so it gets shared with all devices
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )

        # StateColor response (107) has 100ms delay configured
        from lifx_emulator.constants import HEADER_SIZE
        from lifx_emulator.protocol.packets import Light
        from lifx_emulator.protocol.protocol_types import LightHsbk

        color = LightHsbk(hue=10000, saturation=65535, brightness=50000, kelvin=3500)
        set_color_packet = Light.SetColor(color=color, duration=0)
        payload = set_color_packet.pack()

        header = LifxHeader(
            size=HEADER_SIZE + len(payload),
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,  # SetColor
            res_required=True,
        )

        packet_data = header.pack() + payload
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        import time

        start_time = time.time()
        await server.handle_packet(packet_data, addr)
        elapsed = time.time() - start_time

        # Should have delayed for approximately 100ms
        assert elapsed >= 0.09  # Allow small margin

    @pytest.mark.asyncio
    async def test_no_delay_by_default(self, color_device):
        """Test server sends responses immediately when no delay configured."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,  # GetLabel
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        import time

        start_time = time.time()
        await server.handle_packet(packet_data, addr)
        elapsed = time.time() - start_time

        # Should be very fast (< 10ms)
        assert elapsed < 0.01


class TestServerLifecycle:
    """Test server start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_server_start(self, color_device):
        """Test server starts and creates UDP endpoint."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)

        await server.start()

        assert server.transport is not None

        # Cleanup
        await server.stop()

    @pytest.mark.asyncio
    async def test_server_stop(self, color_device):
        """Test server stops and closes transport."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)

        await server.start()
        assert server.transport is not None

        await server.stop()

    @pytest.mark.asyncio
    async def test_server_stop_without_start(self, color_device):
        """Test stopping server that was never started doesn't raise exception."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)

        # Should not raise exception
        await server.stop()


class TestProtocolClass:
    """Test LifxProtocol nested class."""

    def test_protocol_connection_made(self, color_device):
        """Test LifxProtocol.connection_made sets up transport."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)
        protocol = server.LifxProtocol(server)

        mock_transport = Mock()
        protocol.connection_made(mock_transport)

        assert protocol.transport == mock_transport
        assert server.transport == mock_transport

    @pytest.mark.asyncio
    async def test_protocol_datagram_received(self, color_device):
        """Test LifxProtocol.datagram_received creates async task."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)
        protocol = server.LifxProtocol(server)

        # Mock handle_packet
        server.handle_packet = AsyncMock()

        # Create valid packet
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=2,
            res_required=True,
        )
        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        protocol.datagram_received(packet_data, addr)

        # Give async task time to start
        await asyncio.sleep(0.01)

        # Should have called handle_packet
        server.handle_packet.assert_called_once()


class TestErrorHandling:
    """Test server error handling."""

    @pytest.mark.asyncio
    async def test_handle_invalid_packet_type(self, color_device):
        """Test server handles invalid packet type gracefully."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56706)

        # Create packet with invalid type
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=9999,  # Invalid type
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        # Should not raise exception
        await server.handle_packet(packet_data, addr)

    @pytest.mark.asyncio
    async def test_handle_malformed_payload(self, color_device):
        """Test server handles malformed payload gracefully."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56707)

        # Create header for SetColor but with truncated payload
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,  # SetColor
            res_required=True,
            size=HEADER_SIZE + 5,  # Say we have 5 bytes but actual SetColor needs more
        )

        packet_data = header.pack() + b"\x00\x00\x00\x00\x00"
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        # Should log warning but not crash
        await server.handle_packet(packet_data, addr)


class TestMultiDeviceScenarios:
    """Test server with multiple devices."""

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_devices(
        self, color_device, infrared_device, tile_device
    ):
        """Test broadcast packet generates responses from all devices."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device, infrared_device, tile_device],
            device_manager,
            "127.0.0.1",
            56708,
        )

        header = LifxHeader(
            source=12345,
            target=b"\x00" * 8,
            sequence=1,
            pkt_type=2,  # GetService
            tagged=True,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should have 3 StateService responses (one from each device)
        assert server.transport.sendto.call_count == 3

    @pytest.mark.asyncio
    async def test_targeted_packet_to_one_device(self, color_device, infrared_device):
        """Test targeted packet only affects one device."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device, infrared_device], device_manager, "127.0.0.1", 56709
        )

        # Target only color_device
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,  # GetLabel
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should have exactly 1 StateLabel response
        assert server.transport.sendto.call_count == 1

        # Verify it's from color_device
        sent_data, _ = server.transport.sendto.call_args[0]
        resp_header = LifxHeader.unpack(sent_data)
        assert resp_header.target == color_device.state.get_target_bytes()


class TestSequenceHandling:
    """Test server preserves sequence numbers."""

    @pytest.mark.asyncio
    async def test_response_preserves_sequence(self, color_device):
        """Test response packet has same sequence number as request."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56710)

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=42,  # Specific sequence number
            pkt_type=23,  # GetLabel
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Check response has same sequence
        sent_data, _ = server.transport.sendto.call_args[0]
        resp_header = LifxHeader.unpack(sent_data)
        assert resp_header.sequence == 42

    @pytest.mark.asyncio
    async def test_response_preserves_source(self, color_device):
        """Test response packet has same source as request."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56711)

        header = LifxHeader(
            source=99999,  # Specific source
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,  # GetLabel
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Check response has same source
        sent_data, _ = server.transport.sendto.call_args[0]
        resp_header = LifxHeader.unpack(sent_data)
        assert resp_header.source == 99999
