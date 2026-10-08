"""Tests that Set64 and CopyFrameBuffer apply to `length` tiles in the chain."""

import pytest
from lifx_emulator.factories import create_tile_device
from lifx_emulator.handlers.tile_handlers import CopyFrameBufferHandler, Set64Handler
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import LightHsbk, TileBufferRect

RED = LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500)


@pytest.fixture
def chain():
    """A chained matrix device with 5 tiles (8x8 each)."""
    return create_tile_device("d073d5000012", tile_count=5)


def _send(device, packet) -> None:
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=False,
    )
    device.process_packet(header, packet)


def _set64(device, tile_index, length, fb_index=0) -> None:
    _send(
        device,
        Tile.Set64(
            tile_index=tile_index,
            length=length,
            rect=TileBufferRect(fb_index=fb_index, x=0, y=0, width=8),
            duration=0,
            colors=[RED] * 64,
        ),
    )


def _copy(device, tile_index, length) -> None:
    _send(
        device,
        Tile.CopyFrameBuffer(
            tile_index=tile_index,
            length=length,
            src_fb_index=1,
            dst_fb_index=0,
            src_x=0,
            src_y=0,
            dst_x=0,
            dst_y=0,
            width=8,
            height=8,
            duration=0,
        ),
    )


def _painted(device) -> list[bool]:
    return [tile["colors"] == [RED] * 64 for tile in device.state.tile_devices]


class TestSet64Length:
    def test_writes_every_tile_in_length(self, chain):
        _set64(chain, tile_index=1, length=3)

        assert _painted(chain) == [False, True, True, True, False]

    @pytest.mark.parametrize("length", [0, 1])
    def test_zero_or_one_writes_a_single_tile(self, chain, length):
        _set64(chain, tile_index=2, length=length)

        assert _painted(chain) == [False, False, True, False, False]

    def test_length_past_the_end_of_the_chain_stops_at_the_last_tile(self, chain):
        _set64(chain, tile_index=3, length=16)

        assert _painted(chain) == [False, False, False, True, True]


class TestCopyFrameBufferLength:
    def test_copies_on_every_tile_in_length(self, chain):
        _set64(chain, tile_index=0, length=5, fb_index=1)

        _copy(chain, tile_index=0, length=4)

        assert _painted(chain) == [True, True, True, True, False]

    def test_zero_copies_on_a_single_tile(self, chain):
        _set64(chain, tile_index=0, length=5, fb_index=1)

        _copy(chain, tile_index=2, length=0)

        assert _painted(chain) == [False, False, True, False, False]


class TestEdgeCases:
    @pytest.mark.parametrize("handler", [Set64Handler(), CopyFrameBufferHandler()])
    def test_handlers_ignore_non_matrix_devices_and_missing_packets(
        self, handler, color_device, chain
    ):
        assert handler.handle(color_device.state, None, True) == []
        assert handler.handle(chain.state, None, True) == []
        assert _painted(chain) == [False] * 5

    def test_missing_framebuffer_storage_skips_the_tile(self, chain):
        chain.state.tile_framebuffers = []

        _set64(chain, tile_index=0, length=2, fb_index=1)
        _copy(chain, tile_index=0, length=2)

        assert _painted(chain) == [False] * 5

    def test_set64_rect_past_the_right_edge_writes_only_the_visible_part(self, chain):
        _send(
            chain,
            Tile.Set64(
                tile_index=0,
                length=1,
                rect=TileBufferRect(fb_index=0, x=4, y=0, width=8),
                duration=0,
                colors=[RED] * 64,
            ),
        )

        first_row = chain.state.tile_devices[0]["colors"][:8]
        assert [c == RED for c in first_row] == [False] * 4 + [True] * 4

    def test_copy_rect_past_the_tile_edges_copies_only_what_fits(self, chain):
        _set64(chain, tile_index=0, length=1, fb_index=1)

        _send(
            chain,
            Tile.CopyFrameBuffer(
                tile_index=0,
                length=1,
                src_fb_index=1,
                dst_fb_index=0,
                src_x=0,
                src_y=0,
                dst_x=6,
                dst_y=6,
                width=8,
                height=8,
                duration=0,
            ),
        )

        colors = chain.state.tile_devices[0]["colors"]
        painted = {i for i, c in enumerate(colors) if c == RED}
        assert painted == {6 * 8 + 6, 6 * 8 + 7, 7 * 8 + 6, 7 * 8 + 7}
