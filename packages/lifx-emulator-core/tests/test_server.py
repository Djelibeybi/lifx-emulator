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

    def test_server_init_updates_device_port(self, color_device):
        """Test that device port is updated to match server port at init."""
        # Device defaults to port 56700, but server is on custom port
        custom_port = 12345
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device], device_manager, "127.0.0.1", custom_port
        )
        # Device port should be updated to match server port
        assert color_device.state.port == custom_port
        assert server.get_device(color_device.state.serial).state.port == custom_port

    def test_server_add_device_updates_port(self, color_device, multizone_device):
        """Test that device port is updated when added via add_device()."""
        custom_port = 54321
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device], device_manager, "127.0.0.1", custom_port
        )
        # multizone_device starts with default port
        assert multizone_device.state.port == 56700
        # Add device to server
        server.add_device(multizone_device)
        # Port should be updated to match server port
        assert multizone_device.state.port == custom_port


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

        # Should be very fast (< 100ms, generous for CI runners)
        assert elapsed < 0.1


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


class TestServerAckBehavior:
    """Test server sends acks immediately before device processing."""

    @pytest.mark.asyncio
    async def test_ack_sent_first_before_handler_response(self, color_device):
        """Test ack is the first sendto call when ack_required=True."""
        from lifx_emulator.constants import HEADER_SIZE
        from lifx_emulator.protocol.packets import Light
        from lifx_emulator.protocol.protocol_types import LightHsbk

        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        color = LightHsbk(hue=10000, saturation=65535, brightness=50000, kelvin=3500)
        set_color_packet = Light.SetColor(color=color, duration=0)
        payload = set_color_packet.pack()

        header = LifxHeader(
            size=HEADER_SIZE + len(payload),
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,  # SetColor
            ack_required=True,
            res_required=True,
        )

        packet_data = header.pack() + payload
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # First sendto call should be the ack (type 45)
        assert server.transport.sendto.call_count >= 2
        first_call_data = server.transport.sendto.call_args_list[0][0][0]
        first_resp_header = LifxHeader.unpack(first_call_data)
        assert first_resp_header.pkt_type == 45  # Acknowledgement

        # Second call should be the handler response (StateColor = 107)
        second_call_data = server.transport.sendto.call_args_list[1][0][0]
        second_resp_header = LifxHeader.unpack(second_call_data)
        assert second_resp_header.pkt_type == 107  # StateColor

    @pytest.mark.asyncio
    async def test_server_does_not_send_ack_when_scenario_affects_acks(
        self, color_device
    ):
        """Test server skips ack when scenario targets ack behavior."""
        from lifx_emulator.scenarios.manager import (
            HierarchicalScenarioManager,
            ScenarioConfig,
        )

        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(response_delays={45: 0.0}),  # Targets ack type
        )

        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,  # GetPower
            ack_required=True,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # All responses should come from device.process_packet()
        # The first should be the ack (device handles it when scenario targets acks)
        assert server.transport.sendto.call_count >= 2
        first_call_data = server.transport.sendto.call_args_list[0][0][0]
        first_resp_header = LifxHeader.unpack(first_call_data)
        assert first_resp_header.pkt_type == 45  # Ack from device

    @pytest.mark.asyncio
    async def test_no_ack_when_not_required(self, color_device):
        """Test no ack is sent when ack_required=False."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,  # GetLabel
            ack_required=False,
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should have exactly 1 response (StateLabel), no ack
        assert server.transport.sendto.call_count == 1
        sent_data = server.transport.sendto.call_args_list[0][0][0]
        resp_header = LifxHeader.unpack(sent_data)
        assert resp_header.pkt_type == 25  # StateLabel


class TestServerStatsAndActivity:
    """Tests for server stats and activity tracking."""

    def test_get_stats_with_activity_enabled(self):
        """Test get_stats() includes activity_enabled when observer supports it."""
        from lifx_emulator.devices import ActivityLogger

        device_manager = DeviceManager(DeviceRepository())
        activity_logger = ActivityLogger(max_events=100)
        server = EmulatedLifxServer(
            [], device_manager, "127.0.0.1", 56700, activity_observer=activity_logger
        )

        stats = server.get_stats()
        assert stats["activity_enabled"] is True
        assert "uptime_seconds" in stats
        assert "packets_received" in stats

    def test_get_stats_with_activity_disabled(self):
        """Test get_stats() shows activity disabled with NullObserver."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [], device_manager, "127.0.0.1", 56700, track_activity=False
        )

        stats = server.get_stats()
        assert stats["activity_enabled"] is False

    def test_get_recent_activity_with_logger(self):
        """Test get_recent_activity() returns events when observer supports it."""
        from lifx_emulator.devices import ActivityLogger, PacketEvent

        device_manager = DeviceManager(DeviceRepository())
        activity_logger = ActivityLogger(max_events=100)
        server = EmulatedLifxServer(
            [], device_manager, "127.0.0.1", 56700, activity_observer=activity_logger
        )

        # Add an event
        event = PacketEvent(
            timestamp="12:34:56",
            direction="rx",
            packet_type=2,
            packet_name="GetService",
            target=None,
            device=None,
            addr=("192.168.1.100", 56700),
        )
        activity_logger.on_packet_received(event)

        activity = server.get_recent_activity()
        assert len(activity) == 1
        assert activity[0]["packet_name"] == "GetService"

    def test_get_recent_activity_without_support(self):
        """Test get_recent_activity() returns empty list with no support."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [], device_manager, "127.0.0.1", 56700, track_activity=False
        )

        activity = server.get_recent_activity()
        assert activity == []

    def test_get_recent_activity_with_custom_observer(self):
        """Test get_recent_activity() with WebSocketActivityObserver."""
        from lifx_emulator.devices import ActivityLogger

        # This simulates the WebSocketActivityObserver pattern
        device_manager = DeviceManager(DeviceRepository())
        inner_logger = ActivityLogger(max_events=50)

        # Create a mock observer that wraps the inner logger
        class CustomObserver:
            def __init__(self, inner):
                self._inner = inner

            def get_recent_activity(self):
                return self._inner.get_recent_activity()

            def on_packet_received(self, event):
                self._inner.on_packet_received(event)

            def on_packet_sent(self, event):
                self._inner.on_packet_sent(event)

        custom_observer = CustomObserver(inner_logger)
        server = EmulatedLifxServer(
            [], device_manager, "127.0.0.1", 56700, activity_observer=custom_observer
        )

        stats = server.get_stats()
        assert stats["activity_enabled"] is True

        activity = server.get_recent_activity()
        assert activity == []
