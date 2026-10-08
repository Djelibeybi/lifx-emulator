"""Tests that (Extended)SetColorZones honour the apply field.

NO_APPLY stages colours without showing them, APPLY shows everything staged
plus the request's own colours, and APPLY_ONLY shows what was staged while
ignoring the request's colours.
"""

import pytest
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import MultiZone
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneApplicationRequest,
)

RED = LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500)
BLUE = LightHsbk(hue=43690, saturation=65535, brightness=65535, kelvin=3500)
BLACK = LightHsbk(hue=0, saturation=0, brightness=0, kelvin=0)


def _send(device, packet) -> None:
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=False,
    )
    device.process_packet(header, packet)


def _set_zones(device, start, end, color, apply) -> None:
    _send(
        device,
        MultiZone.SetColorZones(
            start_index=start, end_index=end, color=color, duration=0, apply=apply
        ),
    )


def _extended_set(device, index, colors, apply) -> None:
    padded = colors + [BLACK] * (82 - len(colors))
    _send(
        device,
        MultiZone.ExtendedSetColorZones(
            duration=0,
            apply=apply,
            index=index,
            colors_count=len(colors),
            colors=padded,
        ),
    )


class TestSetColorZonesApply:
    def test_no_apply_does_not_change_visible_zones(self, multizone_device):
        before = list(multizone_device.state.zone_colors)

        _set_zones(multizone_device, 0, 7, RED, MultiZoneApplicationRequest.NO_APPLY)

        assert multizone_device.state.zone_colors == before

    def test_apply_only_shows_staged_colours_and_ignores_its_own(
        self, multizone_device
    ):
        _set_zones(multizone_device, 0, 7, RED, MultiZoneApplicationRequest.NO_APPLY)

        _set_zones(
            multizone_device, 0, 15, BLACK, MultiZoneApplicationRequest.APPLY_ONLY
        )

        zones = multizone_device.state.zone_colors
        assert zones[:8] == [RED] * 8
        assert BLACK not in zones[8:]

    def test_apply_shows_staged_and_own_colours_together(self, multizone_device):
        _set_zones(multizone_device, 0, 7, RED, MultiZoneApplicationRequest.NO_APPLY)

        _set_zones(multizone_device, 8, 15, BLUE, MultiZoneApplicationRequest.APPLY)

        assert multizone_device.state.zone_colors == [RED] * 8 + [BLUE] * 8

    def test_commit_clears_the_staged_colours(self, multizone_device):
        _set_zones(multizone_device, 0, 7, RED, MultiZoneApplicationRequest.NO_APPLY)
        _set_zones(multizone_device, 0, 0, RED, MultiZoneApplicationRequest.APPLY_ONLY)
        _set_zones(multizone_device, 0, 15, BLUE, MultiZoneApplicationRequest.APPLY)

        _set_zones(multizone_device, 0, 0, RED, MultiZoneApplicationRequest.APPLY_ONLY)

        assert multizone_device.state.zone_colors == [BLUE] * 16

    def test_zones_beyond_the_strip_are_not_staged(self, multizone_device):
        _set_zones(multizone_device, 14, 255, RED, MultiZoneApplicationRequest.NO_APPLY)

        assert sorted(multizone_device.state.multizone_pending_zone_colors) == [
            14,
            15,
        ]


class TestExtendedSetColorZonesApply:
    def test_no_apply_then_apply_only(self, extended_multizone_device):
        device = extended_multizone_device
        before = list(device.state.zone_colors)

        _extended_set(device, 0, [RED] * 10, MultiZoneApplicationRequest.NO_APPLY)
        assert device.state.zone_colors == before

        _extended_set(device, 0, [BLACK] * 82, MultiZoneApplicationRequest.APPLY_ONLY)
        assert device.state.zone_colors[:10] == [RED] * 10
        assert device.state.zone_colors[10:] == before[10:]

    @pytest.mark.parametrize(
        "first",
        [MultiZoneApplicationRequest.NO_APPLY, MultiZoneApplicationRequest.APPLY],
    )
    def test_staged_and_own_colours_apply_together(
        self, extended_multizone_device, first
    ):
        device = extended_multizone_device

        _extended_set(device, 0, [RED] * 10, first)
        _extended_set(device, 10, [BLUE] * 10, MultiZoneApplicationRequest.APPLY)

        assert device.state.zone_colors[:20] == [RED] * 10 + [BLUE] * 10
