"""Production responder contract, including actual legacy-unicast datagrams."""

import asyncio
import inspect
import secrets
import socket
import struct

import pytest
from lifx_emulator import mdns
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer

# Each test process owns a distinct serial range: concurrent runs on one host
# would otherwise probe for the same mDNS names and see each other's records.
WIRE_PREFIX = f"d073d5{secrets.token_hex(2)}"
# zeroconf ignores a datagram identical to one it received within the last
# second, so concurrent runs sending the same fixed query ID would silence each
# other. Offset every query ID by a per-process base to keep payloads distinct.
_QUERY_ID_BASE = secrets.randbelow(0x10000)


def wire_serial(index):
    """Return a serial in this process's wire-test range."""
    return f"{WIRE_PREFIX}{index:02x}"


def foreign_serial():
    """Return a LIFX serial outside this process's wire-test range."""
    while True:
        serial = f"d073d5{secrets.token_hex(3)}"
        if not serial.startswith(WIRE_PREFIX):
            return serial


def wire_query_id(query_id):
    """Return the DNS message ID that raw_query sends for a test's query ID."""
    return (_QUERY_ID_BASE + query_id) & 0xFFFF


def owned_records(records, port=None):
    """Keep only records advertised by the server under test.

    Every responder on the host answers a legacy-unicast query from port 5353,
    so the source address cannot attribute a reply. A record is ours when it
    names, or points at, a serial in this process's range, or when it is an
    SRV record targeting the server's own UDP port when one is given.
    """

    def owned(record):
        names = [record[0], record[4]] if record[1] == 12 else [record[0]]
        if any(name.startswith(WIRE_PREFIX) for name in names):
            return True
        return record[1] == 33 and record[4][2] == port

    return [record for record in records if owned(record)]


def heard_records(replies):
    """Flatten every record in a list of raw query replies."""
    return [record for packet, _ in replies for record in parse_records(packet)[1]]


def test_disabled_default():
    """Existing callers must explicitly opt into owning mDNS sockets."""
    parameters = inspect.signature(EmulatedLifxServer).parameters
    assert "mdns_enabled" in parameters
    assert parameters["mdns_enabled"].default is False


async def test_tracer_legacy_unicast(foreign_responder):
    """An actual ephemeral query returns complete records at the committed port."""
    device = create_color_light(serial=wire_serial(0x10), firmware_version=(4, 200))
    server = make_server([device])
    try:
        await server.start()
        for query_id in (123, 456):
            replies = await raw_query(query_id)
            port = server.ipv4_endpoint[1]
            records = []
            for packet, peer in replies:
                header, parsed = parse_records(packet)
                owned = owned_records(parsed, port)
                if owned:
                    assert peer[1] == 5353
                    assert header[0] == wire_query_id(query_id)
                assert all(0 < record[3] <= 10 for record in owned)
                assert all(record[2] & 0x8000 == 0 for record in owned)
                records.extend(owned)
            assert_service(records, device.state.serial, port)
    finally:
        await server.stop()
    assert server._mdns is None


def make_server(devices, **kwargs):
    return EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), port=0, mdns_enabled=True, **kwargs
    )


def dns_name(name):
    return (
        b"".join(
            bytes([len(label)]) + label.encode()
            for label in name.rstrip(".").split(".")
        )
        + b"\x00"
    )


class _QueryReceiver(asyncio.DatagramProtocol):
    """Capture datagrams through the transport API supported by Python 3.10."""

    def __init__(self):
        self.results = []
        self.errors = []
        self.closed = asyncio.get_running_loop().create_future()

    def datagram_received(self, data, addr):
        self.results.append((data, addr))

    def error_received(self, exc):
        self.errors.append(exc)

    def connection_lost(self, exc):
        if exc is not None:
            self.errors.append(exc)
        self.closed.set_result(None)


async def raw_query(
    query_id, name="_lifx._udp.local.", qtype=12, duration=0.4, interface="127.0.0.1"
):
    packet = (
        struct.pack("!6H", wire_query_id(query_id), 0, 1, 0, 0, 0)
        + dns_name(name)
        + struct.pack("!2H", qtype, 1)
    )
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setblocking(False)
        sock.bind((interface, 0))
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface)
        )
        transport, receiver = await loop.create_datagram_endpoint(
            _QueryReceiver, sock=sock
        )
    except BaseException:
        sock.close()
        raise
    try:
        transport.sendto(packet, ("224.0.0.251", 5353))
        await asyncio.sleep(duration)
    finally:
        transport.close()
        await asyncio.shield(receiver.closed)
    assert not receiver.errors
    return receiver.results


def read_name(packet, offset):
    labels = []
    end = None
    seen = set()
    while packet[offset]:
        assert offset not in seen
        seen.add(offset)
        length = packet[offset]
        if length & 0xC0 == 0xC0:
            if end is None:
                end = offset + 2
            offset = ((length & 0x3F) << 8) | packet[offset + 1]
        else:
            offset += 1
            labels.append(packet[offset : offset + length].decode())
            offset += length
    return ".".join(labels) + ".", end or offset + 1


def parse_records(packet):
    header = struct.unpack_from("!6H", packet)
    offset = 12
    for _ in range(header[2]):
        _, offset = read_name(packet, offset)
        offset += 4
    records = []
    for _ in range(sum(header[3:])):
        name, offset = read_name(packet, offset)
        kind, cls, ttl, size = struct.unpack_from("!HHIH", packet, offset)
        offset += 10
        data = packet[offset : offset + size]
        value = data
        if kind == 12:
            value = read_name(packet, offset)[0]
        elif kind == 33:
            value = (
                *struct.unpack_from("!3H", packet, offset),
                read_name(packet, offset + 6)[0],
            )
        records.append((name, kind, cls, ttl, value))
        offset += size
    return header, records


def assert_service(records, serial, port):
    instance = f"{serial}._lifx._udp.local."
    host = f"{serial}.local."
    assert any(
        r[0] == "_lifx._udp.local." and r[1] == 12 and r[4] == instance for r in records
    )
    assert any(
        r[0] == instance and r[1] == 33 and r[4] == (0, 0, port, host) for r in records
    )
    txt = next(r[4] for r in records if r[0] == instance and r[1] == 16)
    fields = {}
    offset = 0
    while offset < len(txt):
        size = txt[offset]
        key, value = txt[offset + 1 : offset + 1 + size].split(b"=", 1)
        fields[key] = value
        offset += size + 1
    assert fields == {b"id": serial.encode(), b"p": b"91", b"fw": b"4.200", b"tm": b"1"}
    assert any(
        r[0] == host and r[1] == 1 and r[4] == socket.inet_aton("127.0.0.1")
        for r in records
    )


@pytest.mark.parametrize("operation", ["register", "unregister"])
@pytest.mark.parametrize("stage", ["outer", "inner"])
async def test_cleanup_operation_failure(monkeypatch, operation, stage):
    """Either public operation stage can fail; close still runs exactly once."""
    owner = FakeOwner()
    owner.failure = (operation, stage)
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kwargs: owner)
    server = make_server([create_color_light(connectivity="thread")])
    try:
        if operation == "register":
            with pytest.raises(RuntimeError, match=f"{operation}-{stage}"):
                await server.start()
        else:
            await server.start()
            with pytest.raises(RuntimeError, match=f"{operation}-{stage}"):
                await server.stop()
    finally:
        await server.stop()
    assert owner.closes == 1
    assert server.ipv4_endpoint is None


@pytest.mark.parametrize("operation", ["register", "unregister"])
async def test_cleanup_waits_for_second_stage(monkeypatch, operation):
    owner = FakeOwner()
    owner.held = operation
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kwargs: owner)
    server = make_server([create_color_light()])
    if operation == "unregister":
        await server.start()
    task = asyncio.create_task(
        server.start() if operation == "register" else server.stop()
    )
    await asyncio.wait_for(owner.entered.wait(), 1)
    assert not task.done()
    assert owner.closes == 0
    owner.release.set()
    await task
    await server.stop()
    assert owner.closes == 1


class FakeOwner:
    def __init__(self):
        self.failure = None
        self.held = None
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.closes = 0

    async def operation(self, name):
        if self.failure == (name, "outer"):
            raise RuntimeError(f"{name}-outer")

        async def finish():
            if self.held == name:
                self.entered.set()
                await self.release.wait()
            if self.failure == (name, "inner"):
                raise RuntimeError(f"{name}-inner")

        return finish()

    async def async_register_service(self, info, **kwargs):
        return await self.operation("register")

    async def async_unregister_service(self, info):
        return await self.operation("unregister")

    async def async_close(self):
        self.closes += 1


@pytest.mark.parametrize("count", [0, 1, 3])
async def test_default_record_sets(count, foreign_responder):
    devices = [
        create_color_light(serial=wire_serial(i), firmware_version=(4, 200))
        for i in range(count)
    ]
    server = make_server(devices)
    try:
        await server.start()
        port = server.ipv4_endpoint[1]
        for query_id in (812, 913):
            records = owned_records(heard_records(await raw_query(query_id)), port)
            if not count:
                assert records == []
            for device in devices:
                assert_service(records, device.state.serial, port)
        if devices:
            host = f"{devices[0].state.serial}.local."
            records = heard_records(await raw_query(31, host, 1))
            assert any(r[0] == host and r[1] == 1 for r in records)
            records = heard_records(await raw_query(32, host, 28))
            assert not any(r[0] == host and r[1] == 28 for r in records)
    finally:
        await server.stop()
