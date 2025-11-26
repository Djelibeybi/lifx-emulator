"""Extended tests for multizone packet handlers to improve coverage."""

from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import MultiZone
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneEffectParameter,
    MultiZoneEffectSettings,
    MultiZoneEffectType,
)


class TestGetColorZones:
    """Test MultiZoneGetColorZones handler."""

    def test_get_color_zones_all(self, multizone_device):
        """Test GetColorZones for all zones."""
        device = multizone_device

        packet = MultiZone.GetColorZones(start_index=0, end_index=15)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Should return multiple StateMultiZone packets (8 zones each)
        state_multizone_responses = [r for r in responses if r[0].pkt_type == 506]
        assert len(state_multizone_responses) == 2  # 16 zones = 2 packets

    def test_get_color_zones_subset(self, multizone_device):
        """Test GetColorZones for subset of zones."""
        device = multizone_device

        packet = MultiZone.GetColorZones(start_index=4, end_index=11)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_multizone_responses = [r for r in responses if r[0].pkt_type == 506]
        assert len(state_multizone_responses) == 1  # 8 zones = 1 packet

    def test_get_color_zones_padding(self, multizone_device):
        """Test GetColorZones pads to 8 colors per packet."""
        device = multizone_device

        packet = MultiZone.GetColorZones(start_index=0, end_index=3)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        resp_header, resp_packet = responses[-1]
        assert len(resp_packet.colors) == 8  # Always 8 colors

    def test_get_color_zones_on_non_multizone(self, color_device):
        """Test GetColorZones on non-multizone device."""
        device = color_device

        packet = MultiZone.GetColorZones(start_index=0, end_index=7)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Should not return StateMultiZone
        assert all(resp[0].pkt_type != 506 for resp in responses)

    def test_get_color_zones_single_zone(self, multizone_device):
        """Test GetColorZones for single zone."""
        device = multizone_device

        packet = MultiZone.GetColorZones(start_index=5, end_index=5)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_multizone_responses = [r for r in responses if r[0].pkt_type == 506]
        assert len(state_multizone_responses) == 1


class TestSetColorZones:
    """Test MultiZoneSetColorZones handler."""

    def test_set_color_zones_range(self, multizone_device):
        """Test SetColorZones updates zone range."""
        device = multizone_device

        test_color = LightHsbk(
            hue=30000, saturation=65535, brightness=50000, kelvin=4000
        )
        packet = MultiZone.SetColorZones(
            start_index=2, end_index=5, color=test_color, duration=0, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify zones 2-5 were updated
        for i in range(2, 6):
            assert device.state.zone_colors[i].hue == 30000

    def test_set_color_zones_all(self, multizone_device):
        """Test SetColorZones updates all zones."""
        device = multizone_device

        test_color = LightHsbk(
            hue=45000, saturation=32768, brightness=65535, kelvin=3500
        )
        packet = MultiZone.SetColorZones(
            start_index=0, end_index=15, color=test_color, duration=1000, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=False,
        )

        device.process_packet(header, packet)

        # All zones should be updated
        for i in range(16):
            assert device.state.zone_colors[i].hue == 45000

    def test_set_color_zones_with_response(self, multizone_device):
        """Test SetColorZones with res_required returns StateMultiZone."""
        device = multizone_device

        test_color = LightHsbk(
            hue=10000, saturation=40000, brightness=30000, kelvin=2700
        )
        packet = MultiZone.SetColorZones(
            start_index=0, end_index=7, color=test_color, duration=500, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_multizone_responses = [r for r in responses if r[0].pkt_type == 506]
        assert len(state_multizone_responses) > 0

    def test_set_color_zones_on_non_multizone(self, color_device):
        """Test SetColorZones on non-multizone device."""
        device = color_device

        test_color = LightHsbk(
            hue=20000, saturation=50000, brightness=40000, kelvin=3500
        )
        packet = MultiZone.SetColorZones(
            start_index=0, end_index=7, color=test_color, duration=0, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)

    def test_set_color_zones_boundary(self, multizone_device):
        """Test SetColorZones at zone boundaries."""
        device = multizone_device

        test_color = LightHsbk(
            hue=60000, saturation=65535, brightness=65535, kelvin=6500
        )
        # Set zones beyond actual count (should be clamped)
        packet = MultiZone.SetColorZones(
            start_index=14, end_index=20, color=test_color, duration=0, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Only zones 14 and 15 should be updated
        assert device.state.zone_colors[14].hue == 60000
        assert device.state.zone_colors[15].hue == 60000


class TestExtendedColorZones:
    """Test extended multizone handlers."""

    def test_extended_get_color_zones(self, extended_multizone_device):
        """Test ExtendedGetColorZones returns all zones."""
        device = extended_multizone_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=511,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 512  # ExtendedStateMultiZone
        assert isinstance(resp_packet, MultiZone.ExtendedStateMultiZone)
        assert resp_packet.count == 82
        assert len(resp_packet.colors) == 82  # Always padded to 82

    def test_extended_get_color_zones_small_strip(self, multizone_device):
        """Test ExtendedGetColorZones on standard multizone (16 zones)."""
        device = multizone_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=511,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 512
        assert resp_packet.count == 16
        assert resp_packet.colors_count == 16
        assert len(resp_packet.colors) == 82  # Padded

    def test_extended_set_color_zones(self, extended_multizone_device):
        """Test ExtendedSetColorZones updates zones."""
        device = extended_multizone_device

        # Create test colors
        test_colors = [
            LightHsbk(hue=i * 800, saturation=65535, brightness=50000, kelvin=3500)
            for i in range(10)
        ]
        # Pad to 82
        while len(test_colors) < 82:
            test_colors.append(
                LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
            )

        packet = MultiZone.ExtendedSetColorZones(
            duration=0, apply=0, index=5, colors_count=10, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=510,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify zones 5-14 were updated
        for i in range(10):
            assert device.state.zone_colors[5 + i].hue == i * 800

    def test_extended_set_color_zones_with_response(self, extended_multizone_device):
        """Test ExtendedSetColorZones with res_required."""
        device = extended_multizone_device

        test_colors = [
            LightHsbk(hue=20000, saturation=30000, brightness=40000, kelvin=4000)
            for _ in range(82)
        ]
        packet = MultiZone.ExtendedSetColorZones(
            duration=1000, apply=0, index=0, colors_count=20, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=510,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Should return ExtendedStateMultiZone
        extended_state_responses = [r for r in responses if r[0].pkt_type == 512]
        assert len(extended_state_responses) > 0

    def test_extended_get_on_non_multizone(self, color_device):
        """Test ExtendedGetColorZones on non-multizone device."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=511,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should not return ExtendedStateMultiZone
        assert all(resp[0].pkt_type != 512 for resp in responses)

    def test_extended_set_on_non_multizone(self, color_device):
        """Test ExtendedSetColorZones on non-multizone device."""
        device = color_device

        test_colors = [
            LightHsbk(hue=10000, saturation=50000, brightness=60000, kelvin=3500)
            for _ in range(82)
        ]
        packet = MultiZone.ExtendedSetColorZones(
            duration=0, apply=0, index=0, colors_count=10, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=510,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)


class TestMultiZoneEffects:
    """Test multizone effect handlers."""

    def test_get_effect_default(self, multizone_device):
        """Test GetEffect returns default effect state."""
        device = multizone_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=507,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 509  # StateEffect
        assert isinstance(resp_packet, MultiZone.StateEffect)
        assert resp_packet.settings.type == MultiZoneEffectType.OFF

    def test_set_effect_move(self, multizone_device):
        """Test SetEffect with MOVE effect."""
        device = multizone_device

        parameter = MultiZoneEffectParameter(
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
        )

        settings = MultiZoneEffectSettings(
            instanceid=1,
            type=MultiZoneEffectType.MOVE,
            speed=5000,
            duration=0,
            parameter=parameter,
        )

        packet = MultiZone.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=508,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.multizone_effect_type == int(MultiZoneEffectType.MOVE)
        assert device.state.multizone_effect_speed == 5  # Converted to seconds

    def test_set_effect_off(self, multizone_device):
        """Test SetEffect turning effect off."""
        device = multizone_device
        device.state.multizone_effect_type = int(MultiZoneEffectType.MOVE)

        parameter = MultiZoneEffectParameter(
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
        )

        settings = MultiZoneEffectSettings(
            instanceid=1,
            type=MultiZoneEffectType.OFF,
            speed=0,
            duration=0,
            parameter=parameter,
        )

        packet = MultiZone.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=508,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.multizone_effect_type == int(MultiZoneEffectType.OFF)

    def test_set_effect_with_response(self, multizone_device):
        """Test SetEffect with res_required returns StateEffect."""
        device = multizone_device

        parameter = MultiZoneEffectParameter(
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
        )

        settings = MultiZoneEffectSettings(
            instanceid=1,
            type=MultiZoneEffectType.MOVE,
            speed=3000,
            duration=0,
            parameter=parameter,
        )

        packet = MultiZone.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=508,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_effect_responses = [r for r in responses if r[0].pkt_type == 509]
        assert len(state_effect_responses) > 0

    def test_get_effect_on_non_multizone(self, color_device):
        """Test GetEffect on non-multizone device."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=507,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should not return StateEffect
        assert all(resp[0].pkt_type != 509 for resp in responses)

    def test_set_effect_on_non_multizone(self, color_device):
        """Test SetEffect on non-multizone device."""
        device = color_device

        parameter = MultiZoneEffectParameter(
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
        )

        settings = MultiZoneEffectSettings(
            instanceid=1,
            type=MultiZoneEffectType.MOVE,
            speed=1000,
            duration=0,
            parameter=parameter,
        )

        packet = MultiZone.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=508,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)
