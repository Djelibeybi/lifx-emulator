"""Tests for the LIFX Mirror (product 267/268) and Ceiling matrix geometry.

The Mirror is driven as a single 4x13 matrix: 52 buffer positions holding 50
zones, with two positions unused. Zone numbering does not follow buffer order;
the firmware zone map (mirrored from lifx-async's ``MIRROR_ZONE_MAP``) gives the
zone at each buffer position. Zones 0-24 form the front ring and zones 25-49
the back (uplight) ring.
"""

import pytest
from lifx_emulator.factories import create_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import LightHsbk, TileBufferRect


def _get_device_chain(device) -> Tile.StateDeviceChain:
    """Drive GetDeviceChain (701) and return the StateDeviceChain (702) reply."""
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=701,
        res_required=True,
    )
    responses = device.process_packet(header, Tile.GetDeviceChain())
    resp_header, resp_packet = responses[-1]
    assert resp_header.pkt_type == 702
    assert isinstance(resp_packet, Tile.StateDeviceChain)
    return resp_packet


def test_mirror_reports_a_single_4x13_tile_on_the_wire():
    for pid in (267, 268):
        chain = _get_device_chain(create_device(pid))
        assert chain.tile_devices_count == 1
        assert (chain.tile_devices[0].width, chain.tile_devices[0].height) == (4, 13)


def _seed_zone_hues(device) -> list[int]:
    """Give every zone of tile 0 a distinct hue so reads can be traced back.

    Without distinguishable zone data a Get64 assertion cannot tell which
    zones a response actually carries -- the handler pads every reply to 64
    entries regardless.
    """
    colors = device.state.tile_devices[0]["colors"]
    hues = [i * 500 for i in range(len(colors))]
    device.state.tile_devices[0]["colors"] = [
        LightHsbk(hue=hue, saturation=65535, brightness=65535, kelvin=3500)
        for hue in hues
    ]
    return hues


def test_mirror_single_get64_covers_all_52_buffer_positions():
    device = create_device(267)
    hues = _seed_zone_hues(device)

    # Request the full tile width starting at the top row, exactly as
    # single_tile_device tests in test_tile_handlers_extended.py do.
    rect = TileBufferRect(x=0, y=0, width=device.state.tile_width, fb_index=0)
    packet = Tile.Get64(tile_index=0, length=1, rect=rect)

    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=707,
        res_required=True,
    )

    responses = device.process_packet(header, packet)

    state64_responses = [
        (resp_header, resp_packet)
        for resp_header, resp_packet in responses
        if resp_header.pkt_type == 711
    ]

    # A single Get64 must yield exactly one State64 response -- the 52-position
    # Mirror buffer fits within the 64-zone-per-response limit, so no
    # second Get64/State64 round trip is required to cover the full tile.
    assert len(state64_responses) == 1

    resp_header, resp_packet = state64_responses[0]
    assert isinstance(resp_packet, Tile.State64)
    assert resp_packet.tile_index == 0
    # State64.colors is always padded to exactly 64 entries by the handler,
    # so the padding alone proves nothing: assert the 52 Mirror buffer
    # positions (50 zones plus the two unused cells) are the seeded ones, in
    # order, and that the remaining 12 entries are padding, not device data.
    assert len(resp_packet.colors) == 64
    assert [c.hue for c in resp_packet.colors[: len(hues)]] == hues
    assert all(c.hue == 0 for c in resp_packet.colors[len(hues) :])


def _get64(device, *, y: int) -> Tile.State64:
    """Drive a single Get64 request for the full tile width at row offset y.

    Mirrors the Get64 driving pattern used throughout
    test_tile_handlers_extended.py (single_tile_device/large_matrix_device
    TestGet64 cases): build a TileBufferRect + Tile.Get64, wrap it in a
    LifxHeader with pkt_type=707, and pull the State64 (711) response.
    """
    rect = TileBufferRect(x=0, y=y, width=device.state.tile_width, fb_index=0)
    packet = Tile.Get64(tile_index=0, length=1, rect=rect)

    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=707,
        res_required=True,
    )

    responses = device.process_packet(header, packet)
    resp_header, resp_packet = responses[-1]
    assert resp_header.pkt_type == 711
    assert isinstance(resp_packet, Tile.State64)
    return resp_packet


def _set64(device, *, y: int, colors: list) -> None:
    """Drive a single Set64 request for the full tile width at row offset y.

    Mirrors the Set64 driving pattern used in
    test_tile_handlers_extended.py::TestSet64 (single_tile_device cases).
    """
    rect = TileBufferRect(x=0, y=y, width=device.state.tile_width, fb_index=0)
    packet = Tile.Set64(tile_index=0, length=1, rect=rect, duration=0, colors=colors)

    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=715,
        res_required=False,
    )

    device.process_packet(header, packet)


def test_ceiling_16x8_zone_count_and_uplight():
    st = create_device(201).state  # Ceiling 13x26" US, 16x8 = 128 zones
    assert st.tile_width == 16
    assert st.tile_height == 8
    assert st.tile_width * st.tile_height == 128
    assert st.uplight_zone_count == 1


def test_ceiling_16x8_single_get64_is_clamped_to_64_zones():
    """A single Get64 for a 128-zone Ceiling can only ever return 64 zones.

    rows_to_return = 64 // rect.width = 64 // 16 = 4 rows, clamped further by
    (tile_height - rect.y). Even though the rect nominally spans the full
    16-wide tile, one request only ever covers half the 8 rows (4 of 8) --
    proving a second request is mandatory to read the remaining rows.
    """
    device = create_device(201)

    resp_packet = _get64(device, y=0)
    assert resp_packet.rect.y == 0
    assert resp_packet.rect.width == 16
    assert len(resp_packet.colors) == 64  # always padded to 64, never 128


def test_ceiling_16x8_requires_two_get64_requests_for_full_coverage():
    """Prove two disjoint Get64 requests (rows 0-3, rows 4-7) are needed to
    read all 128 zones of a Ceiling 16x8 tile, and that together they cover
    the whole tile with no overlap and no gap.
    """
    device = create_device(201)
    tile_width = device.state.tile_width
    tile_height = device.state.tile_height
    assert tile_width * tile_height == 128

    rows_per_request = 64 // tile_width
    assert rows_per_request == 4
    assert rows_per_request < tile_height  # confirms a single request can't cover it

    # Distinct per-zone hues: the handler echoes rect.x/y/width from the
    # request and always pads colors to 64, so only the zone data can show
    # which rows each response really carries.
    hues = _seed_zone_hues(device)

    first = _get64(device, y=0)
    second = _get64(device, y=rows_per_request)

    zones_per_request = rows_per_request * tile_width
    assert [c.hue for c in first.colors] == hues[:zones_per_request]
    assert [c.hue for c in second.colors] == hues[zones_per_request:]

    # Disjoint (no zone appears in both) and complete (every zone appears).
    assert set(hues[:zones_per_request]).isdisjoint(hues[zones_per_request:])
    assert len(first.colors) + len(second.colors) == tile_width * tile_height


def test_ceiling_16x8_set64_round_trip_across_split_requests():
    """Write distinct colors to each half of the tile via two Set64 requests,
    then read them back via the matching two Get64 requests, proving the
    framebuffer persists correctly across the split.
    """
    device = create_device(201)
    tile_width = device.state.tile_width
    rows_per_request = 64 // tile_width

    first_half_colors = [
        LightHsbk(hue=i * 100, saturation=65535, brightness=65535, kelvin=3500)
        for i in range(64)
    ]
    second_half_colors = [
        LightHsbk(
            hue=(i * 100) + 50000, saturation=65535, brightness=65535, kelvin=4000
        )
        for i in range(64)
    ]

    _set64(device, y=0, colors=first_half_colors)
    _set64(device, y=rows_per_request, colors=second_half_colors)

    first = _get64(device, y=0)
    second = _get64(device, y=rows_per_request)

    assert [c.hue for c in first.colors] == [c.hue for c in first_half_colors]
    assert [c.hue for c in second.colors] == [c.hue for c in second_half_colors]


# Zone at each 4x13 buffer position, row by row, from the LIFX firmware team's
# zone map (identical to lifx-async's MIRROR_ZONE_MAP); -1 marks unused cells.
FIRMWARE_MIRROR_ZONE_MAP = (
    *(9, -1, 40, -1),
    *(8, 10, 41, 39),
    *(7, 11, 42, 38),
    *(6, 12, 43, 37),
    *(5, 13, 44, 36),
    *(4, 14, 45, 35),
    *(3, 15, 46, 34),
    *(2, 16, 47, 33),
    *(1, 17, 48, 32),
    *(0, 18, 49, 31),
    *(24, 19, 25, 30),
    *(23, 20, 26, 29),
    *(22, 21, 27, 28),
)


def test_mirror_carries_the_firmware_zone_map():
    for pid in (267, 268):
        assert create_device(pid).state.zone_map == FIRMWARE_MIRROR_ZONE_MAP


def test_mirror_front_and_back_rings_have_25_zones_each():
    st = create_device(267).state
    assert st.downlight_zone_count == 25
    assert st.uplight_zone_count == 25


def test_products_without_a_zone_map_number_zones_in_buffer_order():
    assert create_device(201).state.zone_map is None  # Ceiling 16x8


class _SavedStateStorage:
    """Storage boundary stub that hands back one previously saved state."""

    def __init__(self, saved_state: dict) -> None:
        self._saved_state = saved_state

    def load_device_state(self, serial: str) -> dict | None:
        return self._saved_state


def test_mirror_restored_with_old_5x10_geometry_drops_the_zone_map():
    """State saved before the Mirror moved to 4x13 restores a 5x10 matrix the
    52-entry zone map cannot describe, so the map must not be applied to it.
    """
    from lifx_emulator.factories.builder import DeviceBuilder
    from lifx_emulator.products.registry import get_product

    black = {"hue": 0, "saturation": 0, "brightness": 0, "kelvin": 3500}
    saved = {
        "serial": "d073d5000267",
        "product": 267,
        "tile_count": 1,
        "tile_width": 5,
        "tile_height": 10,
        "tile_devices": [{"width": 5, "height": 10, "colors": [black] * 50}],
    }
    builder = DeviceBuilder(get_product(267)).with_serial("d073d5000267")
    st = builder.with_storage(_SavedStateStorage(saved)).build().state

    assert (st.tile_width, st.tile_height) == (5, 10)
    assert st.zone_map is None


def test_mirror_unused_buffer_positions_echo_what_set64_writes():
    """The two unused cells hold no light, but the emulator does not invent
    firmware behaviour for them: they store and report writes like any cell.
    """
    device = create_device(267)
    colors = [
        LightHsbk(hue=i * 1000, saturation=65535, brightness=65535, kelvin=3500)
        for i in range(52)
    ]

    _set64(device, y=0, colors=colors)
    reply = _get64(device, y=0)

    unused = [i for i, zone in enumerate(FIRMWARE_MIRROR_ZONE_MAP) if zone == -1]
    assert unused == [1, 3]
    assert [reply.colors[i].hue for i in unused] == [1000, 3000]


@pytest.mark.parametrize("tile_count", [0, 2, 3])
def test_a_non_chain_matrix_device_has_exactly_one_tile(tile_count):
    """has_matrix without has_chain (the Mirror and every matrix product
    except the original LIFX Tile) means a single tile, never a chain.
    """
    with pytest.raises(ValueError, match="exactly 1 tile"):
        create_device(267, tile_count=tile_count)


@pytest.mark.parametrize("tile_count", [0, 6])
def test_a_chain_device_has_one_to_five_tiles(tile_count):
    with pytest.raises(ValueError, match="1 to 5 tiles"):
        create_device(55, tile_count=tile_count)  # LIFX Tile


@pytest.mark.parametrize("tile_count", [1, 5])
def test_the_lifx_tile_chains_one_to_five_tiles(tile_count):
    assert create_device(55, tile_count=tile_count).state.tile_count == tile_count


@pytest.mark.parametrize("saved_count", [0, 3])
def test_restoring_a_saved_multi_tile_mirror_keeps_one_tile(saved_count):
    """Saved state can carry a tile count no Mirror can have (written by an
    older build, or edited by hand); restore must not bring it back.
    """
    from lifx_emulator.factories.builder import DeviceBuilder
    from lifx_emulator.products.registry import get_product

    black = {"hue": 0, "saturation": 0, "brightness": 0, "kelvin": 3500}
    tile = {"width": 4, "height": 13, "colors": [black] * 52}
    saved = {
        "serial": "d073d5000267",
        "product": 267,
        "tile_count": saved_count,
        "tile_width": 4,
        "tile_height": 13,
        "tile_devices": [dict(tile) for _ in range(saved_count)],
    }
    builder = DeviceBuilder(get_product(267)).with_serial("d073d5000267")
    st = builder.with_storage(_SavedStateStorage(saved)).build().state

    assert st.tile_count == 1
    assert len(st.tile_devices) == 1
    assert st.zone_map == FIRMWARE_MIRROR_ZONE_MAP


def test_restoring_mirror_tile_colours_saved_without_a_tile_count():
    from lifx_emulator.factories.builder import DeviceBuilder
    from lifx_emulator.products.registry import get_product

    red = {"hue": 0, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
    saved = {
        "serial": "d073d5000267",
        "product": 267,
        "tile_devices": [{"width": 4, "height": 13, "colors": [red] * 52}],
    }
    builder = DeviceBuilder(get_product(267)).with_serial("d073d5000267")
    st = builder.with_storage(_SavedStateStorage(saved)).build().state

    assert st.tile_devices[0]["colors"][0]["saturation"] == 65535


def test_a_transposed_mirror_restore_drops_the_zone_map():
    """13x4 holds 52 positions too, but the map is laid out 4 wide: applied
    to a 13-wide buffer every zone would read the wrong position.
    """
    from lifx_emulator.factories.builder import DeviceBuilder
    from lifx_emulator.products.registry import get_product

    black = {"hue": 0, "saturation": 0, "brightness": 0, "kelvin": 3500}
    saved = {
        "serial": "d073d5000267",
        "product": 267,
        "tile_count": 1,
        "tile_width": 13,
        "tile_height": 4,
        "tile_devices": [{"width": 13, "height": 4, "colors": [black] * 52}],
    }
    builder = DeviceBuilder(get_product(267)).with_serial("d073d5000267")
    st = builder.with_storage(_SavedStateStorage(saved)).build().state

    assert (st.tile_width, st.tile_height) == (13, 4)
    assert st.zone_map is None
