"""Real-loopback proof for dual-family transport and Thread isolation."""

import asyncio
import socket

import pytest
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


def _ipv6_loopback_available() -> bool:
    """Return whether this host can bind a UDP socket to IPv6 loopback."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as probe:
            probe.bind(("::1", 0))
    except OSError:
        return False
    return True


requires_ipv6_loopback = pytest.mark.skipif(
    not _ipv6_loopback_available(),
    reason="host does not provide an IPv6 loopback interface",
)


class _ClientProtocol(asyncio.DatagramProtocol):
    """Queue replies and expose an awaitable client closure signal."""

    def __init__(self) -> None:
        self.received: asyncio.Queue[tuple[bytes, tuple]] = asyncio.Queue()
        self.closed = asyncio.Event()

    def datagram_received(self, data, addr) -> None:
        self.received.put_nowait((data, addr))

    def connection_lost(self, exc) -> None:
        self.closed.set()


def _get_label_request(
    device,
    *,
    sequence: int,
    target: bytes | None = None,
    tagged: bool = False,
) -> bytes:
    """Build one response-requesting GetLabel datagram."""
    return LifxHeader(
        size=LifxHeader.HEADER_SIZE,
        source=0xCAFE,
        target=device.state.get_target_bytes() if target is None else target,
        sequence=sequence,
        pkt_type=23,
        tagged=tagged,
        res_required=True,
    ).pack()


async def _open_client(family: socket.AddressFamily, host: str):
    """Open one real asyncio UDP client on the requested loopback family."""
    loop = asyncio.get_running_loop()
    protocol = _ClientProtocol()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=(host, 0),
        family=family,
    )
    return transport, protocol


async def _assert_silent(protocol: _ClientProtocol) -> None:
    """Assert that no UDP response arrives during a short local-only window."""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(protocol.received.get(), timeout=0.05)


@requires_ipv6_loopback
@pytest.mark.asyncio
async def test_wifi_replies_follow_repeated_interleaved_origin_family():
    """Interleaved WiFi traffic replies only through its receiving family."""
    wifi_device = create_color_light("d073d5000201")
    server = EmulatedLifxServer(
        [wifi_device], DeviceManager(DeviceRepository()), port=0
    )
    ipv4_transport = None
    ipv6_transport = None
    ipv4_protocol = None
    ipv6_protocol = None

    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        assert server.ipv6_endpoint is not None
        assert server.ipv4_endpoint[1] == server.ipv6_endpoint[1] != 0

        ipv4_transport, ipv4_protocol = await _open_client(socket.AF_INET, "127.0.0.1")
        ipv6_transport, ipv6_protocol = await _open_client(socket.AF_INET6, "::1")

        ipv4_sequences = {10, 12, 14}
        ipv6_sequences = {11, 13, 15}
        for ipv4_sequence, ipv6_sequence in zip(
            sorted(ipv4_sequences), sorted(ipv6_sequences), strict=True
        ):
            ipv4_transport.sendto(
                _get_label_request(wifi_device, sequence=ipv4_sequence),
                server.ipv4_endpoint,
            )
            ipv6_transport.sendto(
                _get_label_request(wifi_device, sequence=ipv6_sequence),
                server.ipv6_endpoint,
            )

        ipv4_replies = [
            await asyncio.wait_for(ipv4_protocol.received.get(), timeout=1.0)
            for _ in ipv4_sequences
        ]
        ipv6_replies = [
            await asyncio.wait_for(ipv6_protocol.received.get(), timeout=1.0)
            for _ in ipv6_sequences
        ]

        assert {
            LifxHeader.unpack(data).sequence for data, _ in ipv4_replies
        } == ipv4_sequences
        assert {
            LifxHeader.unpack(data).sequence for data, _ in ipv6_replies
        } == ipv6_sequences
        assert all("." in peer[0] for _, peer in ipv4_replies)
        assert all(":" in peer[0] for _, peer in ipv6_replies)
        assert ipv4_protocol.received.empty()
        assert ipv6_protocol.received.empty()
    finally:
        await server.stop()
        for transport in (ipv4_transport, ipv6_transport):
            if transport is not None:
                transport.close()
        for protocol in (ipv4_protocol, ipv6_protocol):
            if protocol is not None:
                await asyncio.wait_for(protocol.closed.wait(), timeout=1.0)

    assert server.ipv4_endpoint is None
    assert server.ipv6_endpoint is None


@requires_ipv6_loopback
@pytest.mark.asyncio
async def test_thread_exact_ipv6_unicast_is_sole_response_path():
    """Thread stays silent for IPv4, broadcast, tagged, zero and mismatch cases."""
    thread_device = create_color_light("d073d5000202", connectivity="thread")
    server = EmulatedLifxServer(
        [thread_device], DeviceManager(DeviceRepository()), port=0, track_activity=False
    )
    ipv4_transport = None
    ipv6_transport = None
    ipv4_protocol = None
    ipv6_protocol = None

    try:
        await server.start()
        ipv4_transport, ipv4_protocol = await _open_client(socket.AF_INET, "127.0.0.1")
        ipv6_transport, ipv6_protocol = await _open_client(socket.AF_INET6, "::1")
        baseline_received = server.packets_received

        rejected = (
            (ipv4_transport, ipv4_protocol, server.ipv4_endpoint, None, False),
            (ipv4_transport, ipv4_protocol, server.ipv4_endpoint, b"\x00" * 8, True),
            (ipv6_transport, ipv6_protocol, server.ipv6_endpoint, b"\x00" * 8, False),
            (ipv6_transport, ipv6_protocol, server.ipv6_endpoint, b"\x00" * 8, True),
            (
                ipv6_transport,
                ipv6_protocol,
                server.ipv6_endpoint,
                bytes.fromhex("d073d500ffff0000"),
                False,
            ),
            (
                ipv6_transport,
                ipv6_protocol,
                server.ipv6_endpoint,
                thread_device.state.get_target_bytes(),
                True,
            ),
        )
        for sequence, (transport, protocol, endpoint, target, tagged) in enumerate(
            rejected, start=20
        ):
            transport.sendto(
                _get_label_request(
                    thread_device,
                    sequence=sequence,
                    target=target,
                    tagged=tagged,
                ),
                endpoint,
            )
            await _assert_silent(protocol)

        assert server.packets_received == baseline_received
        assert server.get_recent_activity() == []

        ipv6_transport.sendto(
            _get_label_request(thread_device, sequence=99),
            server.ipv6_endpoint,
        )
        response, peer = await asyncio.wait_for(
            ipv6_protocol.received.get(), timeout=1.0
        )

        assert LifxHeader.unpack(response).pkt_type == Device.StateLabel.PKT_TYPE
        assert LifxHeader.unpack(response).sequence == 99
        assert ":" in peer[0]
        assert server.packets_received == baseline_received + 1
        assert ipv4_protocol.received.empty()
    finally:
        await server.stop()
        for transport in (ipv4_transport, ipv6_transport):
            if transport is not None:
                transport.close()
        for protocol in (ipv4_protocol, ipv6_protocol):
            if protocol is not None:
                await asyncio.wait_for(protocol.closed.wait(), timeout=1.0)

    assert server.ipv4_endpoint is None
    assert server.ipv6_endpoint is None


@requires_ipv6_loopback
@pytest.mark.asyncio
async def test_private_ipv6_socket_is_kernel_enforced_v6only():
    """White-box V6-only proof preserves D-04's private raw transport contract."""
    server = EmulatedLifxServer([], DeviceManager(DeviceRepository()), port=0)

    try:
        await server.start()
        ipv6_socket = server._ipv6_transport.get_extra_info("socket")

        assert ipv6_socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == 1
        assert not hasattr(server, "ipv6_transport")
    finally:
        await server.stop()

    assert server.ipv4_endpoint is None
    assert server.ipv6_endpoint is None
