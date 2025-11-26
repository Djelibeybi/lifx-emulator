"""Extended tests for tile packet handlers to improve coverage."""

from lifx_emulator.factories import create_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    TileBufferRect,
    TileEffectParameter,
    TileEffectSettings,
    TileEffectSkyType,
    TileEffectType,
)


class TestTileDeviceChain:
    """Test TileGetDeviceChain handler edge cases."""

    def test_get_device_chain_on_non_matrix_device(self, color_device):
        """Test GetDeviceChain returns None for non-matrix device."""
        device = color_device
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=701,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should only get acknowledgment, no StateDeviceChain
        assert all(resp[0].pkt_type != 702 for resp in responses)

    def test_get_device_chain_with_single_tile(self, single_tile_device):
        """Test GetDeviceChain with single tile device."""
        device = single_tile_device
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=701,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 702
        assert isinstance(resp_packet, Tile.StateDeviceChain)
        assert resp_packet.tile_devices_count == 1
        assert len(resp_packet.tile_devices) == 16  # Always padded to 16

    def test_get_device_chain_padding(self, multi_tile_device):
        """Test that device chain is always padded to 16 tiles."""
        device = multi_tile_device
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=701,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert len(resp_packet.tile_devices) == 16

        # Check that padding tiles have zero dimensions
        for i in range(3, 16):
            assert resp_packet.tile_devices[i].width == 0
            assert resp_packet.tile_devices[i].height == 0


class TestSetUserPosition:
    """Test TileSetUserPosition handler."""

    def test_set_user_position_updates_tile(self, multi_tile_device):
        """Test SetUserPosition updates tile position."""
        device = multi_tile_device

        packet = Tile.SetUserPosition(tile_index=1, user_x=10.5, user_y=20.5)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=703,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify position was updated
        assert device.state.tile_devices[1]["user_x"] == 10.5
        assert device.state.tile_devices[1]["user_y"] == 20.5

    def test_set_user_position_invalid_index(self, multi_tile_device):
        """Test SetUserPosition with invalid tile index is ignored."""
        device = multi_tile_device

        packet = Tile.SetUserPosition(tile_index=10, user_x=10.5, user_y=20.5)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=703,
            res_required=False,
        )

        # Should not raise error
        device.process_packet(header, packet)

    def test_set_user_position_on_non_matrix(self, color_device):
        """Test SetUserPosition on non-matrix device."""
        device = color_device
        packet = Tile.SetUserPosition(tile_index=0, user_x=1.0, user_y=2.0)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=703,
            res_required=False,
        )

        responses = device.process_packet(header, packet)
        # Should not crash, just ignore
        assert len([r for r in responses if r[0].pkt_type == 703]) == 0


class TestGet64:
    """Test TileGet64 handler edge cases."""

    def test_get_64_invalid_tile_index(self, multi_tile_device):
        """Test Get64 with invalid tile index returns None."""
        device = multi_tile_device
        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Get64(tile_index=10, length=1, rect=rect)

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=707,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Should only get acknowledgment, no State64
        assert all(resp[0].pkt_type != 711 for resp in responses)

    def test_get_64_large_tile_partial_rows(self, large_matrix_device):
        """Test Get64 for matrix devices >64 zones with partial row extraction."""
        device = large_matrix_device

        # Request first 4 rows (16 zones wide × 4 rows = 64 zones)
        rect = TileBufferRect(x=0, y=0, width=16, fb_index=0)
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
        assert len(resp_packet.colors) == 64

    def test_get_64_large_tile_second_half(self, large_matrix_device):
        """Test Get64 for second half of large matrix device using y offset."""
        device = large_matrix_device

        # Request rows 4-7 (second half of 16x8 tile)
        rect = TileBufferRect(x=0, y=4, width=16, fb_index=0)
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
        assert len(resp_packet.colors) == 64

    def test_get_64_with_offset_rectangle(self, single_tile_device):
        """Test Get64 with offset rectangle (not starting at 0,0)."""
        device = single_tile_device

        # Request 4x4 rectangle starting at (2, 2)
        rect = TileBufferRect(x=2, y=2, width=4, fb_index=0)
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
        assert len(resp_packet.colors) == 64  # Always padded to 64

    def test_get_64_boundary_exceeding(self, single_tile_device):
        """Test Get64 when rectangle exceeds tile boundaries."""
        device = single_tile_device

        # Request rectangle that goes beyond tile boundaries
        rect = TileBufferRect(x=6, y=6, width=8, fb_index=0)
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
        # Should pad with default colors where out of bounds
        assert len(resp_packet.colors) == 64

    def test_get_64_zero_width(self, single_tile_device):
        """Test Get64 with zero width rectangle."""
        device = single_tile_device

        rect = TileBufferRect(x=0, y=0, width=0, fb_index=0)
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
        assert len(resp_packet.colors) == 64


class TestSet64:
    """Test TileSet64 handler edge cases."""

    def test_set_64_updates_colors(self, single_tile_device):
        """Test Set64 updates tile colors."""
        device = single_tile_device

        # Create test colors
        test_colors = [
            LightHsbk(hue=i * 100, saturation=65535, brightness=65535, kelvin=3500)
            for i in range(64)
        ]

        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Set64(
            tile_index=0, length=1, rect=rect, duration=0, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify colors were updated
        for i in range(64):
            if i < len(device.state.tile_devices[0]["colors"]):
                assert device.state.tile_devices[0]["colors"][i].hue == i * 100

    def test_set_64_with_response(self, single_tile_device):
        """Test Set64 with res_required returns nothing."""
        device = single_tile_device

        # Create test colors
        test_colors = [
            LightHsbk(hue=i * 100, saturation=65535, brightness=65535, kelvin=3500)
            for i in range(64)
        ]

        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Set64(
            tile_index=0, length=1, rect=rect, duration=100, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Verify colors were updated
        for i in range(64):
            if i < len(device.state.tile_devices[0]["colors"]):
                assert device.state.tile_devices[0]["colors"][i].hue == i * 100

        # Should not return any response
        assert len(responses) == 0

    def test_set_64_invalid_tile_index(self, multi_tile_device):
        """Test Set64 with invalid tile index is ignored."""
        device = multi_tile_device

        test_colors = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(64)
        ]
        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Set64(
            tile_index=10, length=1, rect=rect, duration=0, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)

    def test_set_64_with_duration(self, single_tile_device):
        """Test Set64 with transition duration."""
        device = single_tile_device

        test_colors = [
            LightHsbk(hue=30000, saturation=65535, brightness=65535, kelvin=4000)
            for _ in range(64)
        ]
        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Set64(
            tile_index=0, length=1, rect=rect, duration=5000, colors=test_colors
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Colors should be updated (emulator applies immediately regardless of duration)
        assert device.state.tile_devices[0]["colors"][0].hue == 30000


class TestCopyFrameBuffer:
    """Test TileCopyFrameBuffer handler."""

    def test_copy_frame_buffer(self, single_tile_device):
        """Test CopyFrameBuffer is a no-op in emulator."""
        device = single_tile_device

        packet = Tile.CopyFrameBuffer(
            tile_index=0,
            length=1,
            src_fb_index=0,
            dst_fb_index=0,
            src_x=0,
            src_y=0,
            dst_x=0,
            dst_y=0,
            width=8,
            height=8,
            duration=0,
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=716,
            res_required=False,
        )

        # Should not crash
        responses = device.process_packet(header, packet)

        # Should not return any specific response
        frame_buffer_responses = [r for r in responses if r[0].pkt_type == 716]
        assert len(frame_buffer_responses) == 0

    def test_copy_frame_buffer_on_non_matrix(self, color_device):
        """Test CopyFrameBuffer on non-matrix device."""
        device = color_device
        packet = Tile.CopyFrameBuffer(
            tile_index=0,
            length=1,
            src_fb_index=0,
            dst_fb_index=0,
            src_x=0,
            src_y=0,
            dst_x=0,
            dst_y=0,
            width=8,
            height=8,
            duration=0,
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=716,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)


class TestTileEffects:
    """Test tile effect handlers."""

    def test_get_effect_default_state(self, single_tile_device):
        """Test GetEffect returns default effect state."""
        device = single_tile_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=718,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 720
        assert isinstance(resp_packet, Tile.StateEffect)
        assert isinstance(resp_packet.settings, TileEffectSettings)
        # Default should be OFF
        assert resp_packet.settings.type == TileEffectType.OFF

    def test_set_effect_updates_state(self, single_tile_device):
        """Test SetEffect updates tile effect state."""
        device = single_tile_device

        # Create effect settings
        palette = [
            LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500),
            LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500),
            LightHsbk(hue=43690, saturation=65535, brightness=65535, kelvin=3500),
        ]
        # Pad to 16 colors
        while len(palette) < 16:
            palette.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        )

        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.MORPH,
            speed=5000,  # 5 seconds in ms
            duration=0,  # infinite
            parameter=parameter,
            palette_count=3,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify effect was set
        assert device.state.tile_effect_type == int(TileEffectType.MORPH)
        assert device.state.tile_effect_speed == 5  # Converted to seconds
        assert device.state.tile_effect_palette_count == 3

    def test_set_effect_with_response(self, single_tile_device):
        """Test SetEffect with res_required returns StateEffect."""
        device = single_tile_device

        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        )

        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.FLAME,
            speed=3000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Should return StateEffect
        state_effect_responses = [r for r in responses if r[0].pkt_type == 720]
        assert len(state_effect_responses) > 0

        resp_header, resp_packet = state_effect_responses[0]
        assert resp_packet.settings.type == TileEffectType.FLAME

    def test_get_effect_on_non_matrix(self, color_device):
        """Test GetEffect on non-matrix device."""
        device = color_device
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=718,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should not return StateEffect
        assert all(resp[0].pkt_type != 720 for resp in responses)

    def test_set_effect_on_non_matrix(self, color_device):
        """Test SetEffect on non-matrix device."""
        device = color_device

        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.MORPH,
            speed=1000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)

    def test_effect_palette_count(self, single_tile_device):
        """Test that effect palette is stored correctly."""
        device = single_tile_device

        # Create palette with 10 colors
        palette = [
            LightHsbk(hue=i * 1000, saturation=65535, brightness=65535, kelvin=3500)
            for i in range(10)
        ]
        # Pad to 16 for the packet
        while len(palette) < 16:
            palette.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        )

        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.MORPH,
            speed=1000,
            duration=0,
            parameter=parameter,
            palette_count=10,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=True,
        )

        device.process_packet(header, packet)

        # Palette should be stored with only the specified count
        assert device.state.tile_effect_palette_count == 10

    def test_sky_effect_sunrise_preserved(self):
        """Test that SKY effect with SUNRISE (value=0) is properly preserved.

        Regression test: SUNRISE has value 0, which is falsy. The code must
        check for None explicitly, not use 'or' operator which treats 0 as falsy.
        """
        # Create a LIFX Ceiling device (supports SKY effect with firmware 4.4+)
        device = create_device(176, tile_count=1, firmware_version=(4, 4))

        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,  # Value = 0 (falsy!)
            cloud_saturation_min=100,
            cloud_saturation_max=200,
        )

        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.SKY,
            speed=5000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        # Set the effect
        set_packet = Tile.SetEffect(settings=settings)
        set_header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )
        device.process_packet(set_header, set_packet)

        # Verify state was stored correctly
        assert device.state.tile_effect_type == int(TileEffectType.SKY)
        assert device.state.tile_effect_sky_type == int(TileEffectSkyType.SUNRISE)
        assert device.state.tile_effect_cloud_sat_min == 100
        assert device.state.tile_effect_cloud_sat_max == 200

        # Get the effect - should return SUNRISE, not default to CLOUDS
        get_packet = Tile.GetEffect()
        get_header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=2,
            pkt_type=718,
            res_required=True,
        )
        responses = device.process_packet(get_header, get_packet)

        # Should return StateEffect
        state_effect_responses = [r for r in responses if r[0].pkt_type == 720]
        assert len(state_effect_responses) == 1

        resp_header, resp_packet = state_effect_responses[0]
        assert resp_packet.settings.type == TileEffectType.SKY
        assert (
            resp_packet.settings.parameter.sky_type == TileEffectSkyType.SUNRISE
        )  # Must be SUNRISE, not CLOUDS!
        assert resp_packet.settings.parameter.cloud_saturation_min == 100
        assert resp_packet.settings.parameter.cloud_saturation_max == 200


class TestSkyEffectRestrictions:
    """Test that SKY effect is only supported on Ceiling devices with firmware 4.4+."""

    def test_sky_effect_on_non_ceiling_tile_device(self):
        """Test SKY effect on non-Ceiling tile device (should be ignored)."""
        # Create a LIFX Tile (product 55, not a Ceiling) with firmware 4.4
        device = create_device(55, tile_count=1, firmware_version=(4, 4))

        # Create SKY effect packet
        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=1000,
            cloud_saturation_max=5000,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.SKY,
            speed=3000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Process the packet
        device.process_packet(header, packet)

        # Effect should NOT be set (still default OFF)
        assert device.state.tile_effect_type == int(TileEffectType.OFF)

    def test_sky_effect_on_ceiling_with_old_firmware(self):
        """Test SKY effect on Ceiling device with firmware < 4.4 (should be ignored)."""
        # Create a LIFX Ceiling US (product 176) with firmware 4.3
        device = create_device(176, tile_count=1, firmware_version=(4, 3))

        # Create SKY effect packet
        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.CLOUDS,
            cloud_saturation_min=2000,
            cloud_saturation_max=8000,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.SKY,
            speed=5000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Process the packet
        device.process_packet(header, packet)

        # Effect should NOT be set (still default OFF)
        assert device.state.tile_effect_type == int(TileEffectType.OFF)

    def test_sky_effect_on_ceiling_with_valid_firmware(self):
        """Test SKY effect on Ceiling device with firmware >= 4.4 (should work)."""
        # Create a LIFX Ceiling US (product 176) with firmware 4.4
        device = create_device(176, tile_count=1, firmware_version=(4, 4))

        # Create SKY effect packet
        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=1500,
            cloud_saturation_max=6000,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.SKY,
            speed=4000,
            duration=0,
            parameter=parameter,
            palette_count=2,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Process the packet
        device.process_packet(header, packet)

        # Effect SHOULD be set
        assert device.state.tile_effect_type == int(TileEffectType.SKY)
        assert device.state.tile_effect_speed == 4  # Converted to seconds
        assert device.state.tile_effect_sky_type == int(TileEffectSkyType.SUNRISE)
        assert device.state.tile_effect_cloud_sat_min == 1500
        assert device.state.tile_effect_cloud_sat_max == 6000

    def test_sky_effect_on_ceiling_with_newer_firmware(self):
        """Test SKY effect on Ceiling device with firmware > 4.4 (should work)."""
        # Create a LIFX Ceiling Intl (product 177) with firmware 5.0
        device = create_device(177, tile_count=1, firmware_version=(5, 0))

        # Create SKY effect packet
        palette = [
            LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500) for _ in range(16)
        ]
        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.CLOUDS,
            cloud_saturation_min=3000,
            cloud_saturation_max=7000,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.SKY,
            speed=2000,
            duration=0,
            parameter=parameter,
            palette_count=1,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Process the packet
        device.process_packet(header, packet)

        # Effect SHOULD be set
        assert device.state.tile_effect_type == int(TileEffectType.SKY)
        assert device.state.tile_effect_speed == 2
        assert device.state.tile_effect_sky_type == int(TileEffectSkyType.CLOUDS)

    def test_other_effects_on_non_ceiling_still_work(self):
        """Test non-SKY effects still work on non-Ceiling devices."""
        # Create a LIFX Tile (product 55) with firmware 4.4
        device = create_device(55, tile_count=1, firmware_version=(4, 4))

        # Create MORPH effect packet (not SKY)
        palette = [
            LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500),
            LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500),
        ]
        # Pad to 16
        while len(palette) < 16:
            palette.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        )
        settings = TileEffectSettings(
            instanceid=1,
            type=TileEffectType.MORPH,
            speed=3000,
            duration=0,
            parameter=parameter,
            palette_count=2,
            palette=palette,
        )

        packet = Tile.SetEffect(settings=settings)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=719,
            res_required=False,
        )

        # Process the packet
        device.process_packet(header, packet)

        # Effect SHOULD be set (MORPH is allowed on all matrix devices)
        assert device.state.tile_effect_type == int(TileEffectType.MORPH)
        assert device.state.tile_effect_speed == 3

    def test_sky_effect_on_all_ceiling_products(self):
        """Test SKY effect on all 4 Ceiling product IDs."""
        ceiling_product_ids = [176, 177, 201, 202]

        for product_id in ceiling_product_ids:
            # Create Ceiling device with firmware 4.4
            device = create_device(product_id, tile_count=1, firmware_version=(4, 4))

            # Create SKY effect packet
            palette = [
                LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                for _ in range(16)
            ]
            parameter = TileEffectParameter(
                sky_type=TileEffectSkyType.SUNRISE,
                cloud_saturation_min=1000,
                cloud_saturation_max=5000,
            )
            settings = TileEffectSettings(
                instanceid=1,
                type=TileEffectType.SKY,
                speed=3000,
                duration=0,
                parameter=parameter,
                palette_count=1,
                palette=palette,
            )

            packet = Tile.SetEffect(settings=settings)
            header = LifxHeader(
                source=12345,
                target=device.state.get_target_bytes(),
                sequence=1,
                pkt_type=719,
                res_required=False,
            )

            # Process the packet
            device.process_packet(header, packet)

            # Effect SHOULD be set for all Ceiling products
            assert device.state.tile_effect_type == int(TileEffectType.SKY), (
                f"Product {product_id} should support SKY effect"
            )


class TestFramebufferHandling:
    """Test framebuffer handling for Set64, Get64, and CopyFrameBuffer."""

    def test_set64_to_framebuffer_0(self, tile_device):
        """Test Set64 updates framebuffer 0 (visible buffer)."""
        device = tile_device

        # Create a Set64 packet targeting framebuffer 0
        red_color = LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500)
        colors = [red_color] * 64

        rect = TileBufferRect(fb_index=0, x=0, y=0, width=8)
        packet = Tile.Set64(
            tile_index=0,
            length=1,
            rect=rect,
            duration=0,
            colors=colors,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify framebuffer 0 (visible buffer) was updated
        tile_colors = device.state.tile_devices[0]["colors"]
        assert tile_colors[0].hue == 0
        assert tile_colors[0].saturation == 65535
        assert tile_colors[0].brightness == 65535

    def test_set64_to_framebuffer_1(self, tile_device):
        """Test Set64 updates framebuffer 1 (non-visible buffer)."""
        device = tile_device

        # Create a Set64 packet targeting framebuffer 1
        blue_color = LightHsbk(
            hue=43690, saturation=65535, brightness=65535, kelvin=3500
        )
        colors = [blue_color] * 64

        rect = TileBufferRect(fb_index=1, x=0, y=0, width=8)
        packet = Tile.Set64(
            tile_index=0,
            length=1,
            rect=rect,
            duration=0,
            colors=colors,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=715,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify framebuffer 1 was updated (not visible in tile_devices)
        fb_storage = device.state.tile_framebuffers[0]
        fb1_colors = fb_storage.get_framebuffer(1, 8, 8)
        assert fb1_colors[0].hue == 43690
        assert fb1_colors[0].saturation == 65535

        # Verify framebuffer 0 was NOT changed
        tile_colors = device.state.tile_devices[0]["colors"]
        assert tile_colors[0].hue == 0  # Default color

    def test_get64_always_returns_framebuffer_0(self, tile_device):
        """Test Get64 always returns framebuffer 0 regardless of request."""
        device = tile_device

        # Set different colors in FB0 and FB1
        green_color = LightHsbk(
            hue=21845, saturation=65535, brightness=65535, kelvin=3500
        )
        device.state.tile_devices[0]["colors"][0] = green_color

        blue_color = LightHsbk(
            hue=43690, saturation=65535, brightness=65535, kelvin=3500
        )
        fb_storage = device.state.tile_framebuffers[0]
        fb1_colors = fb_storage.get_framebuffer(1, 8, 8)
        fb1_colors[0] = blue_color

        # Request with fb_index=1 (should still return FB0)
        rect = TileBufferRect(fb_index=1, x=0, y=0, width=8)
        packet = Tile.Get64(tile_index=0, length=1, rect=rect)

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=707,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Find State64 response
        state64_response = None
        for resp_header, resp_packet in responses:
            if resp_header.pkt_type == 711:
                state64_response = resp_packet
                break

        assert state64_response is not None
        # Should return FB0 colors (green), not FB1 (blue)
        assert state64_response.colors[0].hue == 21845  # Green
        # Response should explicitly say fb_index=0
        assert state64_response.rect.fb_index == 0

    def test_copy_framebuffer_1_to_0(self, tile_device):
        """Test CopyFrameBuffer copies from FB1 to FB0 (making it visible)."""
        device = tile_device

        # Set up FB1 with distinct colors
        yellow_color = LightHsbk(
            hue=10922, saturation=65535, brightness=65535, kelvin=3500
        )
        fb_storage = device.state.tile_framebuffers[0]
        fb1_colors = fb_storage.get_framebuffer(1, 8, 8)
        for i in range(64):
            fb1_colors[i] = yellow_color

        # Verify FB0 starts with default colors
        assert device.state.tile_devices[0]["colors"][0].hue == 0

        # Copy entire tile from FB1 to FB0
        packet = Tile.CopyFrameBuffer(
            tile_index=0,
            length=1,
            src_fb_index=1,
            dst_fb_index=0,
            src_x=0,
            src_y=0,
            dst_x=0,
            dst_y=0,
            width=8,
            height=8,
            duration=0,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=716,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify FB0 now has the yellow colors from FB1
        tile_colors = device.state.tile_devices[0]["colors"]
        assert tile_colors[0].hue == 10922  # Yellow
        assert tile_colors[63].hue == 10922

    def test_copy_framebuffer_partial_rectangle(self, tile_device):
        """Test CopyFrameBuffer with partial rectangle copy."""
        device = tile_device

        # Set up FB2 with magenta in top-left 4x4 area
        magenta_color = LightHsbk(
            hue=54613, saturation=65535, brightness=65535, kelvin=3500
        )
        fb_storage = device.state.tile_framebuffers[0]
        fb2_colors = fb_storage.get_framebuffer(2, 8, 8)
        for y in range(4):
            for x in range(4):
                fb2_colors[y * 8 + x] = magenta_color

        # Copy 4x4 rectangle from FB2 to FB0
        packet = Tile.CopyFrameBuffer(
            tile_index=0,
            length=1,
            src_fb_index=2,
            dst_fb_index=0,
            src_x=0,
            src_y=0,
            dst_x=0,
            dst_y=0,
            width=4,
            height=4,
            duration=0,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=716,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify top-left 4x4 is magenta
        tile_colors = device.state.tile_devices[0]["colors"]
        assert tile_colors[0].hue == 54613  # Top-left
        assert tile_colors[3].hue == 54613  # Top-right of 4x4
        # Verify rest is still default
        assert tile_colors[4].hue == 0  # Outside copied area

    def test_copy_framebuffer_with_offset(self, tile_device):
        """Test CopyFrameBuffer with source and destination offsets."""
        device = tile_device

        # Set up FB3 bottom-right corner
        cyan_color = LightHsbk(
            hue=32768, saturation=65535, brightness=65535, kelvin=3500
        )
        fb_storage = device.state.tile_framebuffers[0]
        fb3_colors = fb_storage.get_framebuffer(3, 8, 8)
        # Set bottom-right 2x2
        for y in range(6, 8):
            for x in range(6, 8):
                fb3_colors[y * 8 + x] = cyan_color

        # Copy from bottom-right of FB3 to top-left of FB0
        packet = Tile.CopyFrameBuffer(
            tile_index=0,
            length=1,
            src_fb_index=3,
            dst_fb_index=0,
            src_x=6,
            src_y=6,
            dst_x=0,
            dst_y=0,
            width=2,
            height=2,
            duration=0,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=716,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Verify top-left 2x2 of FB0 now has cyan
        tile_colors = device.state.tile_devices[0]["colors"]
        assert tile_colors[0].hue == 32768  # (0,0)
        assert tile_colors[1].hue == 32768  # (1,0)
        assert tile_colors[8].hue == 32768  # (0,1)
        assert tile_colors[9].hue == 32768  # (1,1)
        # Verify zone outside is still default
        assert tile_colors[2].hue == 0

    def test_multiple_framebuffers_independent(self, tile_device):
        """Test that multiple framebuffers maintain independent state."""
        device = tile_device

        # Set different colors in FB0, FB1, FB2, FB3
        colors_by_fb = {
            0: LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500),  # Red
            1: LightHsbk(
                hue=21845, saturation=65535, brightness=65535, kelvin=3500
            ),  # Green
            2: LightHsbk(
                hue=43690, saturation=65535, brightness=65535, kelvin=3500
            ),  # Blue
            3: LightHsbk(
                hue=10922, saturation=65535, brightness=65535, kelvin=3500
            ),  # Yellow
        }

        fb_storage = device.state.tile_framebuffers[0]

        # Set FB0 (visible)
        device.state.tile_devices[0]["colors"][0] = colors_by_fb[0]

        # Set FB1, FB2, FB3
        for fb_idx in [1, 2, 3]:
            fb_colors = fb_storage.get_framebuffer(fb_idx, 8, 8)
            fb_colors[0] = colors_by_fb[fb_idx]

        # Verify each framebuffer has its own color
        assert device.state.tile_devices[0]["colors"][0].hue == 0  # FB0: Red
        assert fb_storage.get_framebuffer(1, 8, 8)[0].hue == 21845  # FB1: Green
        assert fb_storage.get_framebuffer(2, 8, 8)[0].hue == 43690  # FB2: Blue
        assert fb_storage.get_framebuffer(3, 8, 8)[0].hue == 10922  # FB3: Yellow
