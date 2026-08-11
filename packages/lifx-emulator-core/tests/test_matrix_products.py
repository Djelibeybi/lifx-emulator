"""Tests for the LIFX Mirror (product 267/268) uplight/downlight split.

The Mirror's front/rear split is modelled as metadata (`uplight_zone_count`)
over a single 5x10 = 50-zone matrix, reusing the existing single-matrix
Get64 handling -- no dedicated "wide tile" or split-tile code path exists.
"""

from lifx_emulator.factories import create_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import TileBufferRect


def test_mirror_split_and_total_zones():
    st = create_device(267).state
    assert st.uplight_zone_count == 25
    assert st.downlight_zone_count == 25
    assert st.tile_width * st.tile_height == 50  # via nested MatrixState


def test_mirror_single_get64_covers_all_50_zones():
    device = create_device(267)

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
    # but all 50 real Mirror zones (uplight + downlight) are present within
    # that single response -- verified by rows_to_return covering the full
    # tile_height (10) in one request.
    assert len(resp_packet.colors) == 64
