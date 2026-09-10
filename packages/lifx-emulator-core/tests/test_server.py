"""Unit tests for EmulatedLifxServer packet routing and UDP handling."""

import asyncio
import errno
import gc
import logging
import socket
import time
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from lifx_emulator.constants import HEADER_SIZE
from lifx_emulator.devices import ActivityLogger, PacketEvent
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light, create_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios.manager import (
    HierarchicalScenarioManager,
    ScenarioConfig,
)
from lifx_emulator.server import EmulatedLifxServer


def find_free_port():
    """Find a UDP port currently available on both loopback families."""
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ipv4_socket:
            ipv4_socket.bind(("127.0.0.1", 0))
            port = ipv4_socket.getsockname()[1]

        try:
            with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as ipv6_socket:
                ipv6_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                ipv6_socket.bind(("::1", port))
        except OSError:
            continue
        return port


class _FakeDatagramTransport:
    """Small transport double with an inspectable effective endpoint."""

    def __init__(self, sockname):
        self.sockname = sockname
        self.closed = False

    def close(self):
        self.closed = True

    def get_extra_info(self, name):
        return self.sockname if name == "sockname" else None

    def sendto(self, data, addr):
        pass


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
        assert server.ipv6_bind_address == "::1"

    def test_server_init_retains_keyword_only_ipv6_address(self, color_device):
        """A caller-selected IPv6 bind address remains independent of IPv4."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56700,
            ipv6_bind_address="2001:db8::42",
        )

        assert server.bind_address == "127.0.0.1"
        assert server.ipv6_bind_address == "2001:db8::42"

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
        """Test a short packet records one receive/error and no activity."""
        short_packet = b"\x00\x01\x02"  # Only 3 bytes
        addr = ("127.0.0.1", 56700)

        await server_with_devices.handle_packet(short_packet, addr)

        assert server_with_devices.packets_received == 1
        assert server_with_devices.error_count == 1
        assert server_with_devices.packets_received_by_type == {}
        assert server_with_devices.get_recent_activity() == []

    @pytest.mark.parametrize(
        "malformed_case",
        ["undersized", "oversized", "truncated-payload", "trailing-byte"],
    )
    @pytest.mark.asyncio
    async def test_declared_frame_size_must_match_datagram(
        self, color_device, malformed_case
    ):
        """Malformed declared sizes have no packet-level observable effects."""
        activity = ActivityLogger(max_events=10)
        server = EmulatedLifxServer(
            [color_device],
            DeviceManager(DeviceRepository()),
            activity_observer=activity,
        )
        transport = Mock()
        server.transport = transport

        if malformed_case == "truncated-payload":
            payload = Device.SetPower(level=0).pack()
            header = LifxHeader(
                size=HEADER_SIZE + len(payload),
                source=12345,
                target=color_device.state.get_target_bytes(),
                sequence=1,
                pkt_type=Device.SetPower.PKT_TYPE,
                ack_required=True,
            )
            datagram = header.pack() + payload[:-1]
        else:
            declared_size = {
                "undersized": 0,
                "oversized": HEADER_SIZE + 1,
                "trailing-byte": HEADER_SIZE,
            }[malformed_case]
            header = LifxHeader(
                size=declared_size,
                source=12345,
                target=color_device.state.get_target_bytes(),
                sequence=1,
                pkt_type=Device.GetLabel.PKT_TYPE,
                ack_required=True,
                res_required=True,
            )
            datagram = header.pack()
            if malformed_case == "trailing-byte":
                datagram += b"\x00"

        original_power = color_device.state.power_level
        with patch.object(
            color_device, "process_packet", wraps=color_device.process_packet
        ) as process_packet:
            await server.handle_packet(datagram, ("127.0.0.1", 56700))

        process_packet.assert_not_called()
        transport.sendto.assert_not_called()
        assert color_device.state.power_level == original_power
        assert server.packets_received == 1
        assert server.error_count == 1
        assert server.packets_received_by_type == {}
        assert activity.get_recent_activity() == []

    @pytest.mark.asyncio
    async def test_handle_packet_broadcast_tagged(self, color_device):
        """Test broadcast packets (tagged=True) route to all devices."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        # Create broadcast GetService packet
        header = LifxHeader(
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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

    async def test_uppercase_factory_serial_routes_by_canonical_target(self):
        """A normalised public-factory serial remains targetable over LIFX."""
        device = create_color_light("D073D50000AB")
        server = EmulatedLifxServer(
            [device],
            DeviceManager(DeviceRepository()),
            "127.0.0.1",
            56700,
        )
        header = LifxHeader(
            size=HEADER_SIZE,
            source=12345,
            target=bytes.fromhex("d073d50000ab0000"),
            sequence=1,
            pkt_type=23,
            tagged=False,
            res_required=True,
        )
        server.transport = Mock()

        await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        server.transport.sendto.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_packet_unknown_target(self, color_device):
        """Test packet to unknown device MAC is ignored."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)

        # Create packet for non-existent device
        header = LifxHeader(
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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

        start_time = time.time()
        await server.handle_packet(packet_data, addr)
        elapsed = time.time() - start_time

        # Should be very fast (< 100ms, generous for CI runners)
        assert elapsed < 0.1


class TestServerLifecycle:
    """Test server start/stop lifecycle."""

    async def test_constructor_duplicate_cannot_persist_rejected_state(self, tmp_path):
        """Only the admitted initial device can create the shared state file."""
        serial = "d073d50000fa"
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
        accepted = create_device(91, serial=serial, storage=storage)
        rejected = create_device(38, serial=serial, storage=storage)
        manager = DeviceManager(DeviceRepository())

        assert storage.pending == {}
        server = EmulatedLifxServer(
            [accepted, rejected],
            manager,
            storage=storage,
        )

        try:
            assert server.get_device(serial) is accepted
            assert not rejected._background_tasks.accepting
            await accepted.close()
        finally:
            await storage.shutdown()

        saved = storage.load_device_state(serial)
        assert saved is not None
        assert saved["product"] == accepted.state.product == 91

    @pytest.mark.asyncio
    async def test_server_start(self, color_device):
        """A stock server publishes one same-port dual-family endpoint pair."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, port=0)

        await server.start()

        assert server.transport is not None
        assert server.ipv4_endpoint is not None
        assert server.ipv6_endpoint is not None
        assert server.ipv4_endpoint[1] == server.ipv6_endpoint[1]
        assert server.ipv4_endpoint[1] != 0
        assert server.port == 0
        assert color_device.state.port == server.ipv4_endpoint[1]
        assert not hasattr(server, "ipv6_transport")

        # Cleanup
        await server.stop()

    @pytest.mark.asyncio
    async def test_start_uses_configured_ipv6_address_and_v6only(self, color_device):
        """The explicit AF_INET6 socket is V6-only before the configured bind."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            manager,
            port=0,
            ipv6_bind_address="2001:db8::42",
        )
        ipv4_transport = _FakeDatagramTransport(("127.0.0.1", 43123))
        ipv6_transport = _FakeDatagramTransport(("2001:db8::42", 43123, 0, 0))
        fake_socket = Mock()
        fake_loop = Mock()

        async def create_endpoint(protocol_factory, **kwargs):
            protocol = protocol_factory()
            transport = ipv6_transport if "sock" in kwargs else ipv4_transport
            protocol.connection_made(transport)
            return transport, protocol

        fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)

        with (
            patch(
                "lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop
            ),
            patch("lifx_emulator.server.socket.socket", return_value=fake_socket),
        ):
            await server.start()

        assert fake_socket.method_calls[:3] == [
            call.setblocking(False),
            call.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1),
            call.bind(("2001:db8::42", 43123)),
        ]
        assert server.ipv4_endpoint == ("127.0.0.1", 43123)
        assert server.ipv6_endpoint == ("2001:db8::42", 43123)

    @pytest.mark.asyncio
    async def test_ipv6_collision_retries_whole_port_zero_pair(self, color_device):
        """An IPv6 EADDRINUSE race discards IPv4 and chooses a fresh pair."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        first_ipv4 = _FakeDatagramTransport(("127.0.0.1", 43123))
        second_ipv4 = _FakeDatagramTransport(("127.0.0.1", 43124))
        ipv6_transport = _FakeDatagramTransport(("::1", 43124, 0, 0))
        fake_sockets = [Mock(), Mock()]
        fake_sockets[0].bind.side_effect = OSError(errno.EADDRINUSE, "collision")
        transports = iter([first_ipv4, second_ipv4, ipv6_transport])
        fake_loop = Mock()

        async def create_endpoint(protocol_factory, **kwargs):
            protocol = protocol_factory()
            transport = next(transports)
            protocol.connection_made(transport)
            return transport, protocol

        fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)

        with (
            patch(
                "lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop
            ),
            patch("lifx_emulator.server.socket.socket", side_effect=fake_sockets),
        ):
            await server.start()

        assert first_ipv4.closed
        assert fake_sockets[0].bind.call_args == call(("::1", 43123))
        assert fake_sockets[1].bind.call_args == call(("::1", 43124))
        assert server.ipv4_endpoint == ("127.0.0.1", 43124)
        assert server.ipv6_endpoint == ("::1", 43124)

    @pytest.mark.asyncio
    async def test_ipv6_collision_retry_is_bounded_to_five_pairs(self, color_device):
        """Five consecutive ephemeral IPv6 collisions preserve the last error."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        ipv4_transports = [
            _FakeDatagramTransport(("127.0.0.1", 43130 + index)) for index in range(5)
        ]
        failures = [
            OSError(errno.EADDRINUSE, f"collision {index}") for index in range(5)
        ]
        fake_sockets = [Mock() for _ in range(5)]
        for fake_socket, failure in zip(fake_sockets, failures, strict=True):
            fake_socket.bind.side_effect = failure
        transports = iter(ipv4_transports)
        fake_loop = Mock()

        async def create_endpoint(protocol_factory, **kwargs):
            protocol = protocol_factory()
            transport = next(transports)
            protocol.connection_made(transport)
            return transport, protocol

        fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)

        with (
            patch(
                "lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop
            ),
            patch("lifx_emulator.server.socket.socket", side_effect=fake_sockets),
        ):
            with pytest.raises(OSError) as caught:
                await server.start()

        assert caught.value is failures[-1]
        assert fake_loop.create_datagram_endpoint.await_count == 5
        assert all(transport.closed for transport in ipv4_transports)
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

    @pytest.mark.asyncio
    async def test_ipv6_unavailable_rolls_back_without_ipv4_fallback(
        self, color_device, caplog
    ):
        """An IPv6 bind failure preserves the error and leaves no public state."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=56700)
        ipv4_transport = _FakeDatagramTransport(("127.0.0.1", 56700))
        fake_socket = Mock()
        failure = OSError(errno.EAFNOSUPPORT, "IPv6 unavailable")
        fake_socket.bind.side_effect = failure
        fake_loop = Mock()

        async def create_endpoint(protocol_factory, **kwargs):
            protocol = protocol_factory()
            protocol.connection_made(ipv4_transport)
            return ipv4_transport, protocol

        fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)

        with (
            caplog.at_level(logging.ERROR),
            patch(
                "lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop
            ),
            patch("lifx_emulator.server.socket.socket", return_value=fake_socket),
        ):
            with pytest.raises(OSError) as caught:
                await server.start()

        assert caught.value is failure
        assert ipv4_transport.closed
        assert server.transport is None
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None
        assert "IPv6 bind failed for ::1" in caplog.text

    @pytest.mark.asyncio
    async def test_port_zero_updates_live_added_device_service_port(self, color_device):
        """Initial and live-added devices advertise the committed UDP port."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        added = create_color_light("d073d50000ff")

        await server.start()
        try:
            assert server.add_device(added)
            for device in (color_device, added):
                request = LifxHeader(
                    size=HEADER_SIZE,
                    source=1,
                    target=device.state.get_target_bytes(),
                    sequence=1,
                    pkt_type=2,
                    res_required=True,
                )
                reply_transport = Mock()
                await server.handle_packet(
                    request.pack(),
                    ("127.0.0.1", 56700),
                    transport=reply_transport,
                )
                response = reply_transport.sendto.call_args.args[0]
                state_service = Device.StateService.unpack(response[HEADER_SIZE:])

                assert state_service.port == server.ipv4_endpoint[1]
                assert state_service.port != 0
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_repeated_start_keeps_complete_endpoint_pair(self, color_device):
        """A second start is a no-op only after both endpoints are committed."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)

        await server.start()
        try:
            original_transport = server.transport
            original_ipv4_endpoint = server.ipv4_endpoint
            original_ipv6_endpoint = server.ipv6_endpoint

            await server.start()

            assert server.transport is original_transport
            assert server.ipv4_endpoint == original_ipv4_endpoint
            assert server.ipv6_endpoint == original_ipv6_endpoint
        finally:
            await server.stop()

    @pytest.mark.parametrize("failed_family", [socket.AF_INET, socket.AF_INET6])
    @pytest.mark.asyncio
    async def test_unexpected_endpoint_loss_rebinds_complete_pair(
        self, color_device, failed_family
    ):
        """Losing either family invalidates the pair and permits a clean restart."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)

        await server.start()
        old_ipv4_transport = server._ipv4_transport
        old_ipv6_transport = server._ipv6_transport
        old_protocol = (
            server._ipv4_protocol
            if failed_family == socket.AF_INET
            else server._ipv6_protocol
        )
        failed_transport = (
            old_ipv4_transport
            if failed_family == socket.AF_INET
            else old_ipv6_transport
        )

        failed_transport.close()
        await asyncio.wait_for(old_protocol.closed.wait(), timeout=1.0)

        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

        await server.start()
        try:
            assert server._ipv4_transport is not old_ipv4_transport
            assert server._ipv6_transport is not old_ipv6_transport
            assert server.ipv4_endpoint is not None
            assert server.ipv6_endpoint is not None
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_restart_uses_new_packet_generation_while_old_work_is_pending(
        self, color_device
    ):
        """Endpoint restart does not reopen a tracker owned by the lost pair."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        work_started = asyncio.Event()
        release_work = asyncio.Event()

        async def blocked_work():
            work_started.set()
            await release_work.wait()

        await server.start()
        old_tracker = server._background_tasks
        old_protocol = server._ipv4_protocol
        old_transport = server._ipv4_transport
        assert old_protocol is not None
        assert old_transport is not None
        old_tracker.schedule(blocked_work(), "old-generation-work")
        await work_started.wait()

        try:
            old_transport.close()
            await asyncio.wait_for(old_protocol.closed.wait(), timeout=1.0)

            await server.start()

            assert server._background_tasks is not old_tracker
            assert server._background_tasks.accepting
            assert old_tracker in server._retired_background_tasks
            assert old_tracker.pending_count == 1
            new_ipv4_protocol = server._ipv4_protocol
            new_ipv6_protocol = server._ipv6_protocol
            assert new_ipv4_protocol is not None
            assert new_ipv6_protocol is not None
            assert new_ipv4_protocol._background_tasks is server._background_tasks
            assert new_ipv6_protocol._background_tasks is server._background_tasks
        finally:
            release_work.set()
            await server.stop()

        assert old_tracker.pending_count == 0
        assert not server._retired_background_tasks

    @pytest.mark.asyncio
    async def test_concurrent_start_binds_one_endpoint_pair(self, color_device):
        """Concurrent starts serialise and leave exactly one pair for stop."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)

        with patch.object(
            asyncio.get_running_loop(),
            "create_datagram_endpoint",
            wraps=asyncio.get_running_loop().create_datagram_endpoint,
        ) as create_endpoint:
            await asyncio.gather(server.start(), server.start())

        try:
            assert create_endpoint.await_count == 2
            assert server.ipv4_endpoint is not None
            assert server.ipv6_endpoint is not None
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_start_commit_failure_rolls_back_pair_and_device_port(
        self, color_device
    ):
        """A commit-step failure closes provisional endpoints and restores state."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        ipv4_transport = _FakeDatagramTransport(("127.0.0.1", 43123))
        ipv6_transport = _FakeDatagramTransport(("::1", 43123, 0, 0))
        transports = iter([ipv4_transport, ipv6_transport])
        fake_socket = Mock()
        fake_loop = Mock()

        async def create_endpoint(protocol_factory, **kwargs):
            protocol = protocol_factory()
            transport = next(transports)
            protocol.connection_made(transport)
            return transport, protocol

        fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)
        original_port = color_device.state.port

        with (
            patch(
                "lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop
            ),
            patch("lifx_emulator.server.socket.socket", return_value=fake_socket),
            patch.object(
                server._background_tasks,
                "start_accepting",
                side_effect=RuntimeError("commit failed"),
            ),
            pytest.raises(RuntimeError, match="commit failed"),
        ):
            await server.start()

        assert ipv4_transport.closed
        assert ipv6_transport.closed
        assert color_device.state.port == original_port
        assert server.transport is None
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

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

    @pytest.mark.asyncio
    async def test_stop_drains_work_before_closing_endpoints(self, color_device):
        """Accepted work can finish while both reply transports remain usable."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        started = asyncio.Event()
        release = asyncio.Event()

        async def blocked_work():
            started.set()
            await release.wait()

        await server.start()
        ipv4_transport = server.transport
        ipv6_transport = server._ipv6_transport
        server._background_tasks.schedule(blocked_work(), "blocked-work")
        await started.wait()

        stop_task = asyncio.create_task(server.stop())
        await asyncio.sleep(0)

        try:
            assert not ipv4_transport.is_closing()
            assert not ipv6_transport.is_closing()
        finally:
            release.set()
            await stop_task
            await server._background_tasks.shutdown(timeout=0.1)

        assert server._background_tasks.pending_count == 0
        assert server.transport is None
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

    @pytest.mark.asyncio
    async def test_stop_cancels_overdue_work_and_retrieves_outcome(self, color_device):
        """Overdue tracked work is cancelled and fully removed before return."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def blocked_work():
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        await server.start()
        server._background_tasks.schedule(blocked_work(), "overdue-work")
        await started.wait()

        try:
            with patch("lifx_emulator.server._TRACKED_TASK_DRAIN_TIMEOUT", 0.01):
                await server.stop()

            assert cancelled.is_set()
            assert server._background_tasks.pending_count == 0
        finally:
            await server._background_tasks.shutdown(timeout=0.01)

    @pytest.mark.asyncio
    async def test_stop_drains_device_persistence_work(self):
        """Server shutdown waits for saves owned by remaining devices."""
        save_started = asyncio.Event()
        release_save = asyncio.Event()

        class BlockingStorage:
            async def save_device_state(self, state):
                save_started.set()
                await release_save.wait()

            def load_device_state(self, serial):
                return None

        storage = BlockingStorage()
        device = create_color_light("d073d50000aa", storage=storage)
        server = EmulatedLifxServer(
            [device], DeviceManager(DeviceRepository()), storage=storage
        )
        await save_started.wait()

        stop_task = asyncio.create_task(server.stop())
        await asyncio.sleep(0)

        assert not stop_task.done()
        assert device._background_tasks.pending_count == 1

        release_save.set()
        await stop_task
        assert device._background_tasks.pending_count == 0

    @pytest.mark.asyncio
    async def test_stop_bounds_missing_endpoint_closure_signal(
        self, color_device, caplog
    ):
        """A broken transport cannot leave shutdown waiting indefinitely."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager)
        ipv4_protocol = server.LifxProtocol(server, socket.AF_INET, accepting=False)
        ipv6_protocol = server.LifxProtocol(server, socket.AF_INET6, accepting=False)
        ipv4_transport = _FakeDatagramTransport(("127.0.0.1", 56700))
        ipv6_transport = _FakeDatagramTransport(("::1", 56700, 0, 0))
        server.transport = ipv4_transport
        server._ipv4_transport = ipv4_transport
        server._ipv6_transport = ipv6_transport
        server._ipv4_protocol = ipv4_protocol
        server._ipv6_protocol = ipv6_protocol
        server._ipv4_endpoint = ("127.0.0.1", 56700)
        server._ipv6_endpoint = ("::1", 56700)
        server._effective_port = 56700

        async def force_timeout(awaitable, *, timeout):
            awaitable.close()
            raise asyncio.TimeoutError

        with (
            caplog.at_level(logging.WARNING),
            patch(
                "lifx_emulator.server.asyncio.wait_for",
                AsyncMock(side_effect=force_timeout),
            ) as wait_for,
        ):
            await server.stop()

        assert wait_for.await_count == 2
        assert "Timed out waiting for IPv4 endpoint closure" in caplog.text
        assert "Timed out waiting for IPv6 endpoint closure" in caplog.text
        assert server.transport is None
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

    @pytest.mark.asyncio
    async def test_repeated_stop_is_safe(self, color_device):
        """Stopping an already stopped endpoint pair remains a no-op."""
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager, port=0)

        await server.start()
        await server.stop()
        await server.stop()

        assert server._background_tasks.pending_count == 0
        assert server.transport is None
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None

    @pytest.mark.asyncio
    async def test_legacy_subclass_stop_closes_historical_transport_once(self):
        """Inherited teardown tolerates subclasses that only set transport."""

        class LegacyServer(EmulatedLifxServer):
            def __init__(self, transport):
                self.transport = transport

        transport = Mock()
        server = LegacyServer(transport)

        await server.stop()

        transport.close.assert_called_once_with()
        assert server.transport is None


class TestProtocolClass:
    """Test LifxProtocol nested class."""

    def test_protocol_connection_made_owns_transport_without_mutating_server_alias(
        self, color_device
    ):
        """Protocol transport ownership must not overwrite the IPv4 alias."""
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", 56700)
        compatibility_transport = Mock()
        server.transport = compatibility_transport
        protocol = server.LifxProtocol(server)

        mock_transport = Mock()
        protocol.connection_made(mock_transport)

        assert protocol.transport == mock_transport
        assert server.transport is compatibility_transport
        assert protocol.family == socket.AF_INET

    @pytest.mark.asyncio
    async def test_protocol_datagram_received(self, color_device):
        """Test a directly constructed protocol retains a datagram through reply."""
        port = find_free_port()
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], device_manager, "127.0.0.1", port)
        protocol = server.LifxProtocol(server)

        original_handle_packet = server.handle_packet
        started = asyncio.Event()
        release = asyncio.Event()
        completed = asyncio.Event()
        handler_calls = 0

        captured_contexts = []

        async def blocked_handle_packet(data, context):
            nonlocal handler_calls
            handler_calls += 1
            captured_contexts.append(context)
            started.set()
            await release.wait()
            await original_handle_packet(data, context)
            completed.set()

        server.handle_packet = blocked_handle_packet
        protocol_transport = Mock()
        protocol.connection_made(protocol_transport)

        # Create valid packet
        header = LifxHeader(
            size=HEADER_SIZE,
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )
        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        protocol.datagram_received(packet_data, addr)
        await asyncio.wait_for(started.wait(), timeout=1.0)

        gc.collect()

        assert server._background_tasks.pending_count == 1

        release.set()
        await asyncio.wait_for(completed.wait(), timeout=1.0)
        await asyncio.sleep(0)

        assert handler_calls == 1
        protocol_transport.sendto.assert_called_once()
        assert captured_contexts[0].family == socket.AF_INET
        assert captured_contexts[0].peer == addr
        assert captured_contexts[0].transport is protocol_transport
        with pytest.raises(FrozenInstanceError):
            setattr(captured_contexts[0], "family", socket.AF_INET6)
        assert server._background_tasks.pending_count == 0

    @pytest.mark.asyncio
    async def test_protocol_drops_flood_before_pending_task_allocation(
        self, color_device
    ):
        """A blocked handler cannot grow retained packet work beyond its limit."""
        server = EmulatedLifxServer(
            [color_device],
            DeviceManager(DeviceRepository()),
            max_pending_packets=2,
        )
        protocol = server.LifxProtocol(server)
        protocol.connection_made(Mock())
        started = asyncio.Event()
        release = asyncio.Event()
        allocations = 0
        active = 0

        async def blocked_packet():
            nonlocal active
            active += 1
            if active == 2:
                started.set()
            await release.wait()

        def make_blocked_packet(data, context):
            nonlocal allocations
            allocations += 1
            return blocked_packet()

        server.handle_packet = make_blocked_packet
        datagram = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetLabel.PKT_TYPE,
        ).pack()

        for _ in range(10):
            protocol.datagram_received(datagram, ("127.0.0.1", 56700))
        await asyncio.wait_for(started.wait(), timeout=1.0)

        assert allocations == 2
        assert active == 2
        assert server._background_tasks.pending_count == 2
        assert server.packets_dropped_overload == 8
        assert server.get_stats()["packets_dropped_overload"] == 8

        release.set()
        await server._background_tasks.shutdown(timeout=1.0)
        assert server._background_tasks.pending_count == 0


class TestDatagramContextRouting:
    """Per-datagram endpoint identity controls resolution and every reply."""

    @pytest.mark.asyncio
    async def test_legacy_handler_prefers_explicit_transport(self, color_device):
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager)
        compatibility_transport = Mock()
        explicit_transport = Mock()
        server.transport = compatibility_transport
        peer = ("::1", 56700, 0, 0)
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )

        await server.handle_packet(
            header.pack(),
            peer,
            family=socket.AF_INET6,
            transport=explicit_transport,
        )

        explicit_transport.sendto.assert_called_once()
        assert explicit_transport.sendto.call_args.args[1] == peer
        compatibility_transport.sendto.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_helper_calls_capture_ipv4_alias(self, color_device):
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager)
        compatibility_transport = Mock()
        server.transport = compatibility_transport
        peer = ("127.0.0.1", 56700)
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            ack_required=True,
            res_required=True,
        )

        server._send_ack(color_device, header, peer)
        compatibility_transport.sendto.assert_called_once()
        assert compatibility_transport.sendto.call_args.args[1] == peer

        compatibility_transport.reset_mock()
        await server._process_device_packet(color_device, header, None, peer)
        assert compatibility_transport.sendto.call_count == 2
        assert all(
            call.args[1] == peer
            for call in compatibility_transport.sendto.call_args_list
        )

    @pytest.mark.asyncio
    async def test_interleaved_families_keep_resolution_and_reply_affinity(
        self, color_device
    ):
        manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([color_device], manager)
        compatibility_transport = Mock()
        ipv4_transport = Mock()
        ipv6_transport = Mock()
        server.transport = compatibility_transport
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )

        with patch.object(
            manager,
            "resolve_target_devices",
            wraps=manager.resolve_target_devices,
        ) as resolve:
            await asyncio.gather(
                server.handle_packet(
                    header.pack(),
                    ("127.0.0.1", 56700),
                    family=socket.AF_INET,
                    transport=ipv4_transport,
                ),
                server.handle_packet(
                    header.pack(),
                    ("::1", 56700, 0, 0),
                    family=socket.AF_INET6,
                    transport=ipv6_transport,
                ),
            )

        assert [call.args[1] for call in resolve.call_args_list] == [
            socket.AF_INET,
            socket.AF_INET6,
        ]
        ipv4_transport.sendto.assert_called_once()
        ipv6_transport.sendto.assert_called_once()
        assert ipv4_transport.sendto.call_args.args[1] == ("127.0.0.1", 56700)
        assert ipv6_transport.sendto.call_args.args[1] == ("::1", 56700, 0, 0)
        compatibility_transport.sendto.assert_not_called()

    @pytest.mark.asyncio
    async def test_ipv6_activity_and_logs_use_bracketed_explicit_family(
        self, color_device, caplog
    ):
        manager = DeviceManager(DeviceRepository())
        activity = ActivityLogger(max_events=10)
        server = EmulatedLifxServer([color_device], manager, activity_observer=activity)
        transport = Mock()
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )

        with caplog.at_level(logging.DEBUG):
            await server.handle_packet(
                header.pack(),
                ("::1", 56700, 0, 0),
                family=socket.AF_INET6,
                transport=transport,
            )

        assert all(
            event["addr"] == "[::1]:56700" for event in activity.get_recent_activity()
        )
        assert "[::1]:56700" in caplog.text

    @pytest.mark.asyncio
    async def test_rejected_thread_packets_have_no_observable_side_effects(self):
        thread_device = create_color_light("d073d5000201", connectivity="thread")
        manager = DeviceManager(DeviceRepository())
        activity = ActivityLogger(max_events=10)
        server = EmulatedLifxServer(
            [thread_device], manager, activity_observer=activity
        )
        transport = Mock()
        server.transport = transport
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=thread_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            ack_required=True,
            res_required=True,
        )

        with patch.object(
            thread_device,
            "process_packet",
            wraps=thread_device.process_packet,
        ) as process_packet:
            await server.handle_packet(header.pack(), ("127.0.0.1", 56700))
            await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        process_packet.assert_not_called()
        transport.sendto.assert_not_called()
        assert server.packets_received == 0
        assert server.packets_received_by_type == {}
        assert server.packets_sent == 0
        assert server.packets_sent_by_type == {}
        assert server.error_count == 0
        assert activity.get_recent_activity() == []


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
    async def test_handle_unparsable_header_counts_error_without_activity(
        self, color_device
    ):
        """Test complete but invalid header bytes record only receive and error."""
        activity_logger = ActivityLogger(max_events=10)
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56707,
            activity_observer=activity_logger,
        )

        with patch(
            "lifx_emulator.server.LifxHeader.unpack",
            side_effect=ValueError("unparsable header"),
        ):
            await server.handle_packet(b"\x00" * HEADER_SIZE, ("127.0.0.1", 56700))

        assert server.packets_received == 1
        assert server.error_count == 1
        assert server.packets_received_by_type == {}
        assert activity_logger.get_recent_activity() == []

    @pytest.mark.asyncio
    async def test_handle_unparsable_payload_preserves_error_count_and_activity(
        self, color_device
    ):
        """Test invalid payload records receive/type but no error or activity."""
        activity_logger = ActivityLogger(max_events=10)
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56707,
            activity_observer=activity_logger,
        )

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

        await server.handle_packet(packet_data, addr)

        assert server.packets_received == 1
        assert server.packets_received_by_type == {102: 1}
        assert server.error_count == 0
        assert activity_logger.get_recent_activity() == []

    @pytest.mark.parametrize(
        "serial",
        ["d073d5000010", "d073d5000100", "d073d5000000"],
    )
    @pytest.mark.asyncio
    async def test_unknown_target_preserves_all_twelve_hex_digits(self, serial, caplog):
        """Test unknown warning, normal log, and activity share an exact target."""
        activity_logger = ActivityLogger(max_events=10)
        device_manager = DeviceManager(DeviceRepository())
        device = create_color_light(serial)
        server = EmulatedLifxServer(
            [device],
            device_manager,
            "127.0.0.1",
            56707,
            activity_observer=activity_logger,
        )
        header = LifxHeader(
            size=HEADER_SIZE,
            source=12345,
            target=bytes.fromhex(serial) + b"\x00\x00",
            sequence=1,
            pkt_type=9999,
            tagged=False,
        )

        with caplog.at_level(logging.DEBUG):
            await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        unknown_messages = [
            record.getMessage()
            for record in caplog.records
            if "Unknown packet type 9999" in record.getMessage()
        ]
        normal_messages = [
            record.getMessage()
            for record in caplog.records
            if "RX Unknown(9999)" in record.getMessage()
        ]
        assert len(unknown_messages) == 1
        assert f"(target={serial}," in unknown_messages[0]
        assert len(normal_messages) == 1
        assert f"(target={serial}," in normal_messages[0]
        assert activity_logger.get_recent_activity()[0]["target"] == serial

    @pytest.mark.parametrize(
        ("tagged", "target"),
        [
            (True, bytes.fromhex("d073d5000010") + b"\x00\x00"),
            (False, b"\x00" * 8),
        ],
        ids=["tagged", "all-zero"],
    )
    @pytest.mark.asyncio
    async def test_unknown_target_broadcast_forms_match_all_surfaces(
        self, tagged, target, caplog
    ):
        """Test tagged and all-zero targets render as broadcast everywhere."""
        activity_logger = ActivityLogger(max_events=10)
        device_manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d5000010")
        server = EmulatedLifxServer(
            [device],
            device_manager,
            "127.0.0.1",
            56707,
            activity_observer=activity_logger,
        )
        header = LifxHeader(
            size=HEADER_SIZE,
            source=12345,
            target=target,
            sequence=1,
            pkt_type=9999,
            tagged=tagged,
        )

        with caplog.at_level(logging.DEBUG):
            await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        packet_messages = [
            record.getMessage()
            for record in caplog.records
            if "RX Unknown" in record.getMessage()
        ]
        assert len(packet_messages) == 2
        assert all("target=broadcast" in message for message in packet_messages)
        assert activity_logger.get_recent_activity()[0]["target"] == "broadcast"


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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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
            size=HEADER_SIZE,
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


class TestServerDropPackets:
    """Test drop_packets scenario suppresses all responses including acks."""

    @pytest.mark.asyncio
    async def test_drop_packets_suppresses_ack_for_set_packet(self, color_device):
        """Test drop_packets prevents early ack for SET packets (ack_required).

        This is the key regression test: prior to the fix, the server sent an
        ack before process_packet() could check drop_packets, so SET packets
        were never truly dropped.
        """
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(drop_packets={21: 1.0}),  # Drop SetPower
        )

        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )

        # Build a SetPower packet with ack_required=True
        set_power = Device.SetPower(level=65535)
        payload = set_power.pack()

        header = LifxHeader(
            size=HEADER_SIZE + len(payload),
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,  # SetPower
            ack_required=True,
        )

        packet_data = header.pack() + payload
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # No response at all — no ack, no state response
        server.transport.sendto.assert_not_called()

    @pytest.mark.asyncio
    async def test_drop_packets_suppresses_get_packet(self, color_device):
        """Test drop_packets suppresses GET packets (res_required)."""
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(drop_packets={20: 1.0}),  # Drop GetPower
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
            size=HEADER_SIZE,
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,  # GetPower
            res_required=True,
        )

        packet_data = header.pack()
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # No response — packet was dropped
        server.transport.sendto.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_dropped_set_packet_still_gets_ack(self, color_device):
        """Test SET packets still get acks when not in drop_packets."""
        # Drop GetPower (20) but NOT SetPower (21)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(drop_packets={20: 1.0}),
        )

        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [color_device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )

        set_power = Device.SetPower(level=65535)
        payload = set_power.pack()

        header = LifxHeader(
            size=HEADER_SIZE + len(payload),
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,  # SetPower
            ack_required=True,
        )

        packet_data = header.pack() + payload
        addr = ("127.0.0.1", 56700)

        server.transport = Mock()
        server.transport.sendto = Mock()

        await server.handle_packet(packet_data, addr)

        # Should get at least an ack (type 45)
        assert server.transport.sendto.call_count >= 1
        first_call_data = server.transport.sendto.call_args_list[0][0][0]
        first_resp_header = LifxHeader.unpack(first_call_data)
        assert first_resp_header.pkt_type == 45  # Acknowledgement

    @pytest.mark.asyncio
    async def test_probabilistic_drop_decision_is_packet_atomic(self, color_device):
        """One draw controls both acknowledgement and normal processing."""
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            color_device.state.serial,
            ScenarioConfig(drop_packets={23: 0.5}),
        )
        server = EmulatedLifxServer(
            [color_device],
            DeviceManager(DeviceRepository()),
            scenario_manager=scenario_manager,
        )
        transport = Mock()
        server.transport = transport
        header = LifxHeader(
            size=HEADER_SIZE,
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            ack_required=True,
            res_required=True,
        )

        with patch.object(
            scenario_manager,
            "should_respond",
            side_effect=[True, False],
        ) as should_respond:
            await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        should_respond.assert_called_once()
        assert transport.sendto.call_count == 2
        assert [
            LifxHeader.unpack(call.args[0]).pkt_type
            for call in transport.sendto.call_args_list
        ] == [Device.Acknowledgement.PKT_TYPE, Device.StateLabel.PKT_TYPE]


class TestServerStatsAndActivity:
    """Tests for server stats and activity tracking."""

    def test_get_stats_with_activity_enabled(self):
        """Test get_stats() includes activity_enabled when observer supports it."""
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

    def test_get_stats_uses_monotonic_uptime_and_wall_clock_start(self):
        """Elapsed uptime is monotonic while start_time remains an epoch value."""
        with (
            patch("lifx_emulator.server.time.time", return_value=1_700_000_000.0),
            patch(
                "lifx_emulator.server.time.monotonic",
                side_effect=[50.0, 55.5],
            ),
        ):
            server = EmulatedLifxServer([], DeviceManager(DeviceRepository()))
            stats = server.get_stats()

        assert stats["start_time"] == 1_700_000_000.0
        assert stats["uptime_seconds"] == 5.5

    @pytest.mark.asyncio
    async def test_no_transport_does_not_fabricate_sent_metrics_or_activity(
        self, color_device
    ):
        """Missing reply transport produces no successful-send accounting."""
        activity = ActivityLogger(max_events=10)
        server = EmulatedLifxServer(
            [color_device],
            DeviceManager(DeviceRepository()),
            activity_observer=activity,
        )
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetLabel.PKT_TYPE,
            ack_required=True,
            res_required=True,
        )

        await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        assert server.packets_sent == 0
        assert server.packets_sent_by_type == {}
        assert [
            event
            for event in activity.get_recent_activity()
            if event["direction"] == "tx"
        ] == []

    @pytest.mark.parametrize("ack_required", [False, True])
    @pytest.mark.asyncio
    async def test_throwing_transport_does_not_record_unsent_packet(
        self, color_device, ack_required
    ):
        """A send failure propagates to error accounting without a sent event."""
        activity = ActivityLogger(max_events=10)
        server = EmulatedLifxServer(
            [color_device],
            DeviceManager(DeviceRepository()),
            activity_observer=activity,
        )
        transport = Mock()
        transport.sendto.side_effect = OSError("send failed")
        header = LifxHeader(
            size=HEADER_SIZE,
            source=1,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetLabel.PKT_TYPE,
            ack_required=ack_required,
            res_required=True,
        )

        await server.handle_packet(
            header.pack(),
            ("127.0.0.1", 56700),
            transport=transport,
        )

        assert server.error_count == 1
        assert server.packets_sent == 0
        assert server.packets_sent_by_type == {}
        assert [
            event
            for event in activity.get_recent_activity()
            if event["direction"] == "tx"
        ] == []

    def test_get_recent_activity_with_logger(self):
        """Test get_recent_activity() returns events when observer supports it."""
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
