"""Tests for the LIFX Mirror (product 267/268) uplight/downlight split.

The Mirror's front/rear split is modelled as metadata (`uplight_zone_count`)
over a single 5x10 = 50-zone matrix, reusing the existing single-matrix
Get64 handling -- no dedicated "wide tile" or split-tile code path exists.
"""

from lifx_emulator.factories import create_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import LightHsbk, TileBufferRect


def test_mirror_split_and_total_zones():
    st = create_device(267).state
    assert st.uplight_zone_count == 25
    assert st.downlight_zone_count == 25
    assert st.tile_width * st.tile_height == 50  # via nested MatrixState


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


def test_mirror_single_get64_covers_all_50_zones():
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

    # A single Get64 must yield exactly one State64 response -- the 50-zone
    # Mirror matrix fits within the 64-zone-per-response limit, so no
    # second Get64/State64 round trip is required to cover the full tile.
    assert len(state64_responses) == 1

    resp_header, resp_packet = state64_responses[0]
    assert isinstance(resp_packet, Tile.State64)
    assert resp_packet.tile_index == 0
    # State64.colors is always padded to exactly 64 entries by the handler,
    # so the padding alone proves nothing: assert the 50 real Mirror zones
    # (uplight + downlight) are the seeded ones, in order, and that the
    # remaining 14 entries are padding rather than device data.
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
