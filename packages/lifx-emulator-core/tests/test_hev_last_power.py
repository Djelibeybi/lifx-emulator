"""Tests that StateHevCycle last_power reports the power state before the cycle."""

import asyncio
import socket

import pytest
from lifx_emulator.constants import HEADER_SIZE
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_hev_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer

SERIAL = "d073d5000042"
ACKNOWLEDGEMENT = 45


@pytest.fixture
def hev_server(integration_port):
    """A server with one HEV light, not yet started."""
    device = create_hev_light(SERIAL)
    device.state.port = integration_port
    return EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", integration_port
    )


@pytest.fixture
def client():
    """A non-blocking UDP client socket, so the server can reply in-loop."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    yield sock
    sock.close()


async def _request(sock: socket.socket, port: int, packet) -> bytes:
    """Send a packet with res_required set and return its reply payload."""
    payload = packet.pack()
    header = LifxHeader(
        size=HEADER_SIZE + len(payload),
        source=12345,
        target=bytes.fromhex(SERIAL) + b"\x00\x00",
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=True,
    )
    sock.sendto(header.pack() + payload, ("127.0.0.1", port))
    loop = asyncio.get_running_loop()
    while True:
        data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=2.0)
        if LifxHeader.unpack(data).pkt_type != ACKNOWLEDGEMENT:
            return data[HEADER_SIZE:]


async def _start_cycle_with_power(sock, port: int, level: int) -> Light.StateHevCycle:
    await _request(sock, port, Device.SetPower(level=level))
    await _request(sock, port, Light.SetHevCycle(enable=True, duration_s=600))
    reply = await _request(sock, port, Light.GetHevCycle())
    return Light.StateHevCycle.unpack(reply)


@pytest.mark.parametrize(
    ("level", "expected"),
    [(65535, True), (0, False)],
    ids=["on", "off"],
)
async def test_last_power_is_the_power_state_when_the_cycle_started(
    hev_server, client, integration_port, level, expected
):
    async with hev_server:
        cycle = await _start_cycle_with_power(client, integration_port, level)

    assert cycle.remaining_s == 600
    assert cycle.last_power is expected


async def test_last_power_follows_each_new_cycle(hev_server, client, integration_port):
    async with hev_server:
        await _start_cycle_with_power(client, integration_port, 65535)
        cycle = await _start_cycle_with_power(client, integration_port, 0)

    assert cycle.last_power is False


async def test_power_change_during_a_cycle_does_not_change_last_power(
    hev_server, client, integration_port
):
    async with hev_server:
        await _start_cycle_with_power(client, integration_port, 65535)
        await _request(client, integration_port, Device.SetPower(level=0))
        reply = await _request(client, integration_port, Light.GetHevCycle())

    assert Light.StateHevCycle.unpack(reply).last_power is True


async def test_stopping_a_cycle_keeps_last_power(hev_server, client, integration_port):
    async with hev_server:
        await _start_cycle_with_power(client, integration_port, 65535)
        await _request(
            client, integration_port, Light.SetHevCycle(enable=False, duration_s=0)
        )
        reply = await _request(client, integration_port, Light.GetHevCycle())

    cycle = Light.StateHevCycle.unpack(reply)
    assert cycle.remaining_s == 0
    assert cycle.last_power is True
