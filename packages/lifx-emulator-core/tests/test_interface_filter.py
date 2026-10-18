"""Wildcard bind with interface peer filtering for LAN discovery."""

import socket
from ipaddress import IPv4Network
from unittest.mock import Mock, patch

import pytest
from lifx_emulator.constants import HEADER_SIZE
from lifx_emulator.devices import ActivityLogger
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.interfaces import (
    InterfaceSelection,
    is_direct_bind_address,
    select_interface,
)
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer

# TEST-NET-1 (RFC 5737) is never assigned to a local interface.
_UNASSIGNED_ADDRESS = "192.0.2.1"


def _get_service_datagram() -> bytes:
    header = LifxHeader(
        size=HEADER_SIZE,
        source=12345,
        target=b"\x00" * 8,
        sequence=1,
        pkt_type=2,  # GetService
        tagged=True,
        res_required=True,
    )
    return header.pack()


def _make_server(bind_address: str) -> EmulatedLifxServer:
    activity = ActivityLogger(max_events=10)
    server = EmulatedLifxServer(
        [create_color_light("d073d5000001")],
        DeviceManager(DeviceRepository()),
        bind_address,
        56700,
        activity_observer=activity,
    )
    server.transport = Mock()
    server.transport.sendto = Mock()
    return server


@pytest.fixture
def lan_selection() -> InterfaceSelection:
    return InterfaceSelection(
        address="192.0.2.10",
        name="test0",
        prefixes=(IPv4Network("192.0.2.0/24"), IPv4Network("198.51.100.0/24")),
    )


class TestInterfaceSelection:
    def test_accepts_peer_inside_any_prefix(self, lan_selection):
        assert lan_selection.accepts("192.0.2.77")
        assert lan_selection.accepts("198.51.100.1")

    def test_rejects_peer_outside_every_prefix(self, lan_selection):
        assert not lan_selection.accepts("203.0.113.5")
        assert not lan_selection.accepts("10.0.0.1")

    def test_rejects_unparseable_peer(self, lan_selection):
        assert not lan_selection.accepts("not-an-address")

    @pytest.mark.parametrize("address", ["127.0.0.1", "127.5.5.5", "0.0.0.0"])
    def test_loopback_and_wildcard_bind_directly(self, address):
        assert is_direct_bind_address(address)

    def test_lan_address_does_not_bind_directly(self):
        assert not is_direct_bind_address("192.0.2.10")


class TestSelectInterface:
    def test_loopback_address_resolves_to_loopback_interface(self):
        selection = select_interface("127.0.0.1")

        assert selection.address == "127.0.0.1"
        assert selection.name
        assert selection.accepts("127.0.0.1")
        assert any(
            IPv4Network("127.0.0.1/32").subnet_of(prefix)
            for prefix in selection.prefixes
        )

    def test_unknown_address_raises_naming_it(self):
        with pytest.raises(ValueError, match=_UNASSIGNED_ADDRESS):
            select_interface(_UNASSIGNED_ADDRESS)

    def test_invalid_address_raises(self):
        with pytest.raises(ValueError, match="not-an-address"):
            select_interface("not-an-address")


class TestPeerFiltering:
    async def test_in_subnet_peer_is_processed_and_counted(self, lan_selection):
        server = _make_server("192.0.2.10")
        server.peer_filter = lan_selection

        await server.handle_packet(_get_service_datagram(), ("192.0.2.77", 56700))

        assert server.packets_received == 1
        assert server.packets_filtered == 0
        assert server.packets_received_by_type == {2: 1}
        assert len(server.get_recent_activity()) >= 1
        assert server.transport.sendto.call_count >= 1

    async def test_out_of_subnet_peer_is_filtered_without_activity(self, lan_selection):
        server = _make_server("192.0.2.10")
        server.peer_filter = lan_selection

        await server.handle_packet(_get_service_datagram(), ("203.0.113.5", 56700))

        assert server.packets_received == 0
        assert server.packets_filtered == 1
        assert server.packets_received_by_type == {}
        assert server.error_count == 0
        assert server.get_recent_activity() == []
        server.transport.sendto.assert_not_called()

    async def test_filter_runs_before_header_validation(self, lan_selection):
        server = _make_server("192.0.2.10")
        server.peer_filter = lan_selection

        await server.handle_packet(b"\x00\x01", ("203.0.113.5", 56700))

        assert server.packets_received == 0
        assert server.error_count == 0
        assert server.packets_filtered == 1

    async def test_ipv6_peers_are_never_filtered(self, lan_selection):
        server = _make_server("192.0.2.10")
        server.peer_filter = lan_selection

        await server.handle_packet(
            _get_service_datagram(),
            ("2001:db8::1", 56700, 0, 0),
            family=socket.AF_INET6,
        )

        assert server.packets_filtered == 0

    async def test_loopback_bound_server_does_not_filter(self):
        server = _make_server("127.0.0.1")

        assert server.peer_filter is None
        await server.handle_packet(_get_service_datagram(), ("203.0.113.5", 56700))

        assert server.packets_received == 1
        assert server.packets_filtered == 0

    async def test_wildcard_bound_server_does_not_filter(self):
        server = _make_server("0.0.0.0")

        assert server.peer_filter is None
        await server.handle_packet(_get_service_datagram(), ("203.0.113.5", 56700))

        assert server.packets_received == 1
        assert server.packets_filtered == 0

    def test_stats_expose_filtered_counter(self):
        server = _make_server("127.0.0.1")
        server.packets_filtered = 3

        assert server.get_stats()["packets_filtered"] == 3


class TestWildcardBindAtStart:
    async def test_lan_address_binds_wildcard_and_enables_filter(self, lan_selection):
        server = EmulatedLifxServer(
            [], DeviceManager(DeviceRepository()), lan_selection.address, port=0
        )
        with patch(
            "lifx_emulator.server.select_interface", return_value=lan_selection
        ) as select:
            await server.start()
            try:
                select.assert_called_once_with(lan_selection.address)
                assert server.ipv4_endpoint is not None
                assert server.ipv4_endpoint[0] == "0.0.0.0"
                assert server.peer_filter is lan_selection
                assert server.bind_address == lan_selection.address
            finally:
                await server.stop()

        assert server.peer_filter is None

    async def test_loopback_address_binds_directly(self):
        server = EmulatedLifxServer(
            [], DeviceManager(DeviceRepository()), "127.0.0.1", port=0
        )
        with patch("lifx_emulator.server.select_interface") as select:
            await server.start()
            try:
                select.assert_not_called()
                assert server.ipv4_endpoint is not None
                assert server.ipv4_endpoint[0] == "127.0.0.1"
                assert server.peer_filter is None
            finally:
                await server.stop()

    async def test_unknown_address_fails_start_with_clear_error(self):
        server = EmulatedLifxServer(
            [], DeviceManager(DeviceRepository()), _UNASSIGNED_ADDRESS, port=0
        )

        with pytest.raises(ValueError, match=_UNASSIGNED_ADDRESS):
            await server.start()

        assert server.ipv4_endpoint is None
        assert server.transport is None
        assert server.peer_filter is None
