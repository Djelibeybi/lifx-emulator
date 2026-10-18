"""Tests that legacy single-zone requests are answered with StateZone (503).

Real firmware replies to GetColorZones or SetColorZones covering exactly one
zone with a single StateZone packet. Ranges of two or more zones keep the
StateMultiZone (506) chunking of eight zones per packet.
"""

import pytest
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import MultiZone
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneApplicationRequest,
)

GREEN = LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500)
BLACK = LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)


def _send(device, packet) -> list:
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=True,
    )
    return device.process_packet(header, packet)


def _get_zones(device, start, end) -> list:
    return _send(device, MultiZone.GetColorZones(start_index=start, end_index=end))


class TestGetColorZonesReplyShape:
    def test_single_zone_returns_one_state_zone(self, multizone_device):
        multizone_device.state.zone_colors[5] = GREEN

        responses = _get_zones(multizone_device, 5, 5)

        assert len(responses) == 1
        header, packet = responses[0]
        assert header.pkt_type == MultiZone.StateZone.PKT_TYPE
        assert isinstance(packet, MultiZone.StateZone)
        assert packet.count == 16
        assert packet.index == 5
        assert packet.color == GREEN

    def test_two_zones_return_one_state_multizone(self, multizone_device):
        responses = _get_zones(multizone_device, 3, 4)

        assert [h.pkt_type for h, _ in responses] == [MultiZone.StateMultiZone.PKT_TYPE]
        assert responses[0][1].index == 3

    def test_nine_zones_return_two_state_multizone(self, multizone_device):
        responses = _get_zones(multizone_device, 0, 8)

        assert [h.pkt_type for h, _ in responses] == [
            MultiZone.StateMultiZone.PKT_TYPE
        ] * 2
        assert [p.index for _, p in responses] == [0, 8]

    def test_single_zone_out_of_range_returns_nothing(self, multizone_device):
        assert _get_zones(multizone_device, 16, 16) == []
        assert _get_zones(multizone_device, 200, 200) == []

    def test_last_zone_returns_state_zone(self, multizone_device):
        responses = _get_zones(multizone_device, 15, 15)

        assert len(responses) == 1
        assert isinstance(responses[0][1], MultiZone.StateZone)
        assert responses[0][1].index == 15


class TestSetColorZonesReplyShape:
    @pytest.mark.parametrize(
        "apply",
        [MultiZoneApplicationRequest.NO_APPLY, MultiZoneApplicationRequest.APPLY],
    )
    def test_single_zone_set_returns_state_zone(self, multizone_device, apply):
        responses = _send(
            multizone_device,
            MultiZone.SetColorZones(
                start_index=7, end_index=7, color=GREEN, duration=0, apply=apply
            ),
        )

        assert len(responses) == 1
        header, packet = responses[0]
        assert header.pkt_type == MultiZone.StateZone.PKT_TYPE
        assert isinstance(packet, MultiZone.StateZone)
        assert packet.count == 16
        assert packet.index == 7
        shown = apply == MultiZoneApplicationRequest.APPLY
        assert (packet.color == GREEN) is shown
        assert (multizone_device.state.zone_colors[7] == GREEN) is shown

    def test_multi_zone_set_still_returns_state_multizone(self, multizone_device):
        responses = _send(
            multizone_device,
            MultiZone.SetColorZones(
                start_index=0,
                end_index=7,
                color=GREEN,
                duration=0,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )

        assert [h.pkt_type for h, _ in responses] == [MultiZone.StateMultiZone.PKT_TYPE]


class TestExtendedDeviceLegacySingleZone:
    def test_get_single_zone_returns_state_zone(self, extended_multizone_device):
        extended_multizone_device.state.zone_colors[40] = GREEN

        responses = _get_zones(extended_multizone_device, 40, 40)

        assert len(responses) == 1
        packet = responses[0][1]
        assert isinstance(packet, MultiZone.StateZone)
        assert packet.count == 82
        assert packet.index == 40
        assert packet.color == GREEN

    def test_set_single_zone_returns_state_zone(self, extended_multizone_device):
        responses = _send(
            extended_multizone_device,
            MultiZone.SetColorZones(
                start_index=81,
                end_index=81,
                color=GREEN,
                duration=0,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )

        assert len(responses) == 1
        packet = responses[0][1]
        assert isinstance(packet, MultiZone.StateZone)
        assert packet.index == 81
        assert packet.color == GREEN

    def test_single_zone_out_of_range_returns_nothing(self, extended_multizone_device):
        assert _get_zones(extended_multizone_device, 82, 82) == []


class TestMissingZoneColours:
    """A zone within zone_count but without a stored colour reads as black."""

    def test_single_zone_without_stored_colour_is_black(self, multizone_device):
        del multizone_device.state.zone_colors[12:]

        responses = _get_zones(multizone_device, 14, 14)

        assert len(responses) == 1
        packet = responses[0][1]
        assert isinstance(packet, MultiZone.StateZone)
        assert packet.count == 16
        assert packet.index == 14
        assert packet.color == BLACK

    def test_range_without_stored_colours_is_padded_black(self, multizone_device):
        multizone_device.state.zone_colors[11] = GREEN
        del multizone_device.state.zone_colors[12:]

        responses = _get_zones(multizone_device, 8, 15)

        assert len(responses) == 1
        packet = responses[0][1]
        assert isinstance(packet, MultiZone.StateMultiZone)
        assert packet.colors[3] == GREEN
        assert packet.colors[4:] == [BLACK] * 4
