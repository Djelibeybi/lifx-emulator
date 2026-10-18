"""Integration suite that drives an emulated fleet with the lifx-async client.

Every other protocol test in this package speaks raw packets. This module
observes the emulator only through the public API of ``lifx-async``, the
emulator's primary consumer, and asserts on what a downstream user would see.

The suite is marked ``client`` and skipped when ``lifx-async`` is not
installed. Install it with ``uv sync --group third-party`` and run the suite
in isolation with ``uv run pytest -m client``.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from lifx_emulator.devices import DeviceManager, EmulatedLifxDevice
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_device,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_switch,
    create_tile_device,
)
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer

SKIP_REASON = "lifx-async is not installed (uv sync --group third-party)"
lifx = pytest.importorskip("lifx", reason=SKIP_REASON)
lifx_udp = pytest.importorskip("lifx.network.discovery.udp", reason=SKIP_REASON)
lifx_packets = pytest.importorskip("lifx.protocol.packets", reason=SKIP_REASON)

pytestmark = [pytest.mark.client, pytest.mark.asyncio(loop_scope="module")]

LOOPBACK = "127.0.0.1"
# Loopback answers instantly; the window only has to outlast the client's
# first re-broadcast so a dropped first datagram cannot fail the suite.
DISCOVERY_TIMEOUT = 2.0
# Each test process owns a distinct serial range so parallel runs on one host
# never answer each other's discovery sweeps.
SERIAL_PREFIX = f"d073d5{secrets.token_hex(2)}"

CANDLE_PRODUCT_ID = 57
CEILING_PRODUCT_ID = 176
LIGHT_GET_COLOR = 101


def fleet_serial(index: int) -> str:
    """Return a serial in this process's fleet range."""
    return f"{SERIAL_PREFIX}{index:02x}"


@dataclass
class Fleet:
    """An emulated fleet and the client's view of it.

    Attributes:
        server: The running emulated server.
        port: The effective UDP port the server is bound to.
        emulated: Emulated devices keyed by role name.
        discovered: Raw discovery records keyed by serial.
        clients: Typed lifx-async devices keyed by role name. The switch has
            no entry because lifx-async only models lights.
    """

    server: EmulatedLifxServer
    port: int
    emulated: dict[str, EmulatedLifxDevice]
    discovered: dict[str, Any]
    clients: dict[str, Any]

    def pairs(self) -> list[tuple[str, EmulatedLifxDevice, Any]]:
        """Return (role, emulated device, client device) for every light."""
        return [
            (role, self.emulated[role], client) for role, client in self.clients.items()
        ]


def build_fleet() -> dict[str, EmulatedLifxDevice]:
    """Create one device per product family using the public factories."""
    return {
        "color": create_color_light(fleet_serial(1)),
        "color_temperature": create_color_temperature_light(fleet_serial(2)),
        "infrared": create_infrared_light(fleet_serial(3)),
        "hev": create_hev_light(fleet_serial(4)),
        "legacy_multizone": create_multizone_light(
            fleet_serial(5), extended_multizone=False
        ),
        "extended_multizone": create_multizone_light(
            fleet_serial(6), extended_multizone=True
        ),
        "tile": create_tile_device(fleet_serial(7), tile_count=5),
        "candle": create_device(CANDLE_PRODUCT_ID, serial=fleet_serial(8)),
        "ceiling": create_device(CEILING_PRODUCT_ID, serial=fleet_serial(9)),
        "switch": create_switch(fleet_serial(10)),
    }


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def fleet() -> AsyncIterator[Fleet]:
    """Serve the fleet on loopback and discover it once with lifx-async."""
    emulated = build_fleet()
    server = EmulatedLifxServer(
        list(emulated.values()), DeviceManager(DeviceRepository()), LOOPBACK, 0
    )
    async with server:
        port = server.ipv4_endpoint[1]
        discovered: dict[str, Any] = {}
        sweep = lifx_udp.discover_devices(
            timeout=DISCOVERY_TIMEOUT, broadcast_address=LOOPBACK, port=port
        )
        async for record in sweep:
            discovered[record.serial] = record
        by_serial = {device.state.serial: role for role, device in emulated.items()}
        clients: dict[str, Any] = {}
        for serial, record in discovered.items():
            client = await record.create_device()
            if client is not None:
                clients[by_serial[serial]] = client
        try:
            yield Fleet(server, port, emulated, discovered, clients)
        finally:
            for client in clients.values():
                await client.close()


def client_hsbk(color: Any) -> Any:
    """Convert an emulator LightHsbk into the client's HSBK for comparison."""
    return lifx.HSBK.from_protocol(color)


async def test_discovery_finds_every_device(fleet: Fleet) -> None:
    """Story 1: a broadcast on loopback finds every emulated device."""
    expected = {device.state.serial for device in fleet.emulated.values()}
    assert set(fleet.discovered) == expected
    for record in fleet.discovered.values():
        assert record.ip == LOOPBACK
        assert record.port == fleet.port
    assert fleet.port != 56700, "the fleet must use an ephemeral port"


async def test_each_product_family_is_classified(fleet: Fleet) -> None:
    """Story 2: the client picks the right device class for every family."""
    expected = {
        "color": lifx.Light,
        "color_temperature": lifx.Light,
        "infrared": lifx.InfraredLight,
        "hev": lifx.HevLight,
        "legacy_multizone": lifx.MultiZoneLight,
        "extended_multizone": lifx.MultiZoneLight,
        "tile": lifx.MatrixLight,
        "candle": lifx.MatrixLight,
        "ceiling": lifx.CeilingLight,
    }
    assert set(fleet.clients) == set(expected)
    for role, device, client in fleet.pairs():
        assert type(client) is expected[role], role
        capabilities = client.capabilities
        assert capabilities is not None, role
        assert capabilities.has_color == device.state.has_color, role
        assert capabilities.has_infrared == device.state.has_infrared, role
        assert capabilities.has_hev == device.state.has_hev, role
        assert capabilities.has_multizone == device.state.has_multizone, role
        assert capabilities.has_matrix == device.state.has_matrix, role
    # lifx-async models lights only, so the switch is discovered but untyped.
    assert "switch" not in fleet.clients


async def test_identity_matches_device_state(fleet: Fleet) -> None:
    """Story 3: label, product, firmware, location and group read back."""
    for role, device, client in fleet.pairs():
        state = device.state
        assert await client.get_label() == state.label, role
        version = await client.get_version()
        assert (version.vendor, version.product) == (state.vendor, state.product), role
        firmware = await client.get_host_firmware()
        assert firmware.version_major == state.version_major, role
        assert firmware.version_minor == state.version_minor, role
        assert firmware.build == state.build_timestamp, role
        location = await client.get_location()
        assert location.uuid == state.location_id.hex(), role
        assert location.label == state.location_label, role
        assert location.updated_at == state.location_updated_at, role
        group = await client.get_group()
        assert group.uuid == state.group_id.hex(), role
        assert group.label == state.group_label, role
        assert group.updated_at == state.group_updated_at, role


async def test_set_colour_power_and_label_round_trip(fleet: Fleet) -> None:
    """Story 4: colour, power and label written by the client read back."""
    device = fleet.emulated["color"]
    client = fleet.clients["color"]
    target = lifx.HSBK(hue=210.0, saturation=0.75, brightness=0.5, kelvin=4000)

    await client.set_color(target)
    color, power, label = await client.get_color()
    assert color == target
    assert color == client_hsbk(device.state.color)

    await client.set_power(False)
    assert await client.get_power() == 0
    assert device.state.power_level == 0
    assert power != 0, "the light was on before the client switched it off"
    await client.set_power(True)
    assert await client.get_power() == 65535
    assert device.state.power_level == 65535

    await client.set_label("Client Label")
    assert await client.get_label() == "Client Label"
    assert device.state.label == "Client Label"
    assert label != "Client Label", "the label was changed by the client"


async def test_multizone_zones_round_trip(fleet: Fleet) -> None:
    """Story 5: zones read and write on legacy and extended strips."""
    legacy = fleet.emulated["legacy_multizone"]
    legacy_client = fleet.clients["legacy_multizone"]
    assert await legacy_client.get_zone_count() == legacy.state.zone_count
    green = lifx.HSBK(hue=120.0, saturation=1.0, brightness=0.6, kelvin=3500)
    await legacy_client.set_color_zones(0, 3, green)
    zones = await legacy_client.get_color_zones(0, 7)
    assert len(zones) == 8
    assert zones[:4] == [green] * 4
    assert zones == [client_hsbk(c) for c in legacy.state.zone_colors[:8]]

    extended = fleet.emulated["extended_multizone"]
    extended_client = fleet.clients["extended_multizone"]
    assert await extended_client.get_zone_count() == extended.state.zone_count
    gradient = [
        lifx.HSBK(hue=float(index * 36), saturation=1.0, brightness=0.4, kelvin=3500)
        for index in range(10)
    ]
    await extended_client.set_extended_color_zones(0, gradient)
    zones = await extended_client.get_extended_color_zones(0, 9)
    assert zones == gradient
    assert zones == [client_hsbk(c) for c in extended.state.zone_colors[:10]]
    everything = await extended_client.get_all_color_zones()
    assert len(everything) == extended.state.zone_count


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason=(
        "lifx-async up to 7.11.3 parses every GetColorZones reply as "
        "StateMultiZone (506); real firmware and the emulator answer a "
        "single-zone request with StateZone (503), which has no colors field"
    ),
)
async def test_single_zone_legacy_request_reads_back(fleet: Fleet) -> None:
    """Story 5, single zone: a one-zone legacy request is answered StateZone.

    Strict so that the lifx-async release that fixes the parser fails this
    test and prompts removal of the xfail marker.
    """
    legacy = fleet.emulated["legacy_multizone"]
    legacy_client = fleet.clients["legacy_multizone"]
    zones = await legacy_client.get_color_zones(2, 2)
    assert zones == [client_hsbk(legacy.state.zone_colors[2])]


async def test_matrix_chain_and_block_round_trip(fleet: Fleet) -> None:
    """Story 6: the device chain and a 64-zone block read and write."""
    device = fleet.emulated["tile"]
    client = fleet.clients["tile"]
    chain = await client.get_device_chain()
    assert len(chain) == device.state.tile_count == 5
    for info, tile in zip(chain, device.state.tile_devices, strict=True):
        assert (info.width, info.height) == (tile["width"], tile["height"])
        assert (info.user_x, info.user_y) == (tile["user_x"], tile["user_y"])

    width, height = device.state.tile_width, device.state.tile_height
    block = [
        lifx.HSBK(hue=float(index * 5), saturation=1.0, brightness=0.8, kelvin=3500)
        for index in range(width * height)
    ]
    await client.set64(
        tile_index=2, length=1, x=0, y=0, width=width, duration=0, colors=block
    )
    assert await client.get64(tile_index=2) == block
    stored = device.state.tile_devices[2]["colors"]
    assert [client_hsbk(c) for c in stored] == block


async def test_switch_returns_unhandled_for_light_packet(fleet: Fleet) -> None:
    """Story 7: a light packet sent to the switch is answered StateUnhandled."""
    serial = fleet.emulated["switch"].state.serial
    assert serial in fleet.discovered
    probe = lifx.Device(serial=serial, ip=LOOPBACK, port=fleet.port)
    try:
        response = await probe.connection.request(lifx_packets.Light.GetColor())
    finally:
        await probe.connection.close()
    assert isinstance(response, lifx_packets.Device.StateUnhandled)
    assert response.unhandled_type == LIGHT_GET_COLOR

    light = lifx.Light(serial=serial, ip=LOOPBACK, port=fleet.port)
    try:
        with pytest.raises(lifx.LifxUnsupportedCommandError):
            await light.get_color()
    finally:
        await light.close()
