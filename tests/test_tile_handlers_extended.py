"""Extended tests for tile packet handlers to improve coverage."""

from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    TileBufferRect,
    TileEffectParameter,
    TileEffectSettings,
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

        # Request first 4 rows (16 pixels wide × 4 rows = 64 pixels)
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
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
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
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
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
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
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
            parameter0=0,
            parameter1=0,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
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
