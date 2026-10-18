"""Lazy transition engine: durations and waveforms evaluated against a clock.

Every test drives a device through ``process_packet`` with an injected fake
clock and asserts on the packets that come back. Time is advanced by moving
the clock; nothing sleeps and no transition record is inspected.
"""

from __future__ import annotations

import math

import pytest
from lifx_emulator.devices import transitions
from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile
from lifx_emulator.factories import (
    DeviceBuilder,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.products.registry import get_product
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    LightWaveform,
    MultiZoneApplicationRequest,
    TileBufferRect,
)

SERIAL = "d073d5000777"
BLACK = LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)


def _send(device, packet, res_required: bool = True) -> list:
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=res_required,
    )
    return [pkt for _header, pkt in device.process_packet(header, packet)]


def _hsbk(hue=0, saturation=65535, brightness=0, kelvin=3500) -> LightHsbk:
    return LightHsbk(
        hue=hue, saturation=saturation, brightness=brightness, kelvin=kelvin
    )


def _set_color(device, color, duration_ms=0, res_required=True) -> list:
    return _send(
        device, Light.SetColor(color=color, duration=duration_ms), res_required
    )


def _get_color(device) -> LightHsbk:
    (state,) = _send(device, Light.GetColor())
    return state.color


def _get_power(device) -> int:
    (state,) = _send(device, Light.GetPower())
    return state.level


def _get_zones(device) -> list[LightHsbk]:
    (state,) = _send(device, MultiZone.ExtendedGetColorZones())
    return list(state.colors[: state.colors_count])


def _get_tile(device, tile_index=0) -> list[LightHsbk]:
    (state,) = _send(
        device,
        Tile.Get64(
            tile_index=tile_index,
            length=1,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        ),
    )
    return list(state.colors)


def _set_waveform(device, color, waveform, transient, period=1000, cycles=1.0, skew=0):
    return _send(
        device,
        Light.SetWaveform(
            transient=transient,
            color=color,
            period=period,
            cycles=cycles,
            skew_ratio=skew,
            waveform=waveform,
        ),
    )


@pytest.fixture
def clock(fake_clock):
    return fake_clock


@pytest.fixture
def light(clock):
    device = create_color_light(SERIAL, clock=clock)
    _set_color(device, _hsbk(brightness=0))
    return device


@pytest.fixture
def strip(clock):
    device = create_multizone_light(SERIAL, zone_count=16, clock=clock)
    _set_color(device, _hsbk(brightness=0))
    return device


@pytest.fixture
def tile(clock):
    device = create_tile_device(SERIAL, tile_count=1, clock=clock)
    _set_color(device, _hsbk(brightness=0))
    return device


class TestClockInjection:
    def test_uptime_follows_injected_clock(self, clock):
        device = create_color_light(SERIAL, clock=clock)
        clock.advance_ms(2500)
        assert device.get_uptime_ns() == 2_500_000_000

    def test_builder_accepts_clock(self, clock):
        product = get_product(91)
        assert product is not None
        device = DeviceBuilder(product).with_serial(SERIAL).with_clock(clock).build()
        clock.advance_ms(10)
        assert device.get_uptime_ns() == 10_000_000

    def test_static_device_reads_identically_before_and_after_settle(self, light):
        before = _get_color(light)
        light.settle()
        assert _get_color(light) == before


class TestSetColorDuration:
    def test_midpoint_and_completion(self, light, clock):
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)

        clock.advance_ms(500)
        assert _get_color(light).brightness == pytest.approx(32768, abs=1)

        clock.advance_ms(500)
        assert _get_color(light).brightness == 65535

        clock.advance_ms(5000)
        assert _get_color(light).brightness == 65535

    def test_zero_duration_applies_instantly(self, light):
        _set_color(light, _hsbk(brightness=65535), duration_ms=0)
        assert _get_color(light).brightness == 65535

    def test_set_reply_reports_start_colour(self, light):
        (reply,) = _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        assert reply.color.brightness == 0

    def test_no_reply_when_not_required(self, light):
        assert _set_color(light, _hsbk(brightness=65535), 1000, False) == []

    def test_interruption_starts_from_interpolated_colour(self, light, clock):
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)

        (reply,) = _set_color(light, _hsbk(brightness=0), duration_ms=1000)
        assert reply.color.brightness == pytest.approx(32768, abs=1)

        clock.advance_ms(500)
        assert _get_color(light).brightness == pytest.approx(16384, abs=1)

    def test_hue_wraps_forward_through_zero(self, light, clock):
        _set_color(light, _hsbk(hue=65000))
        _set_color(light, _hsbk(hue=500), duration_ms=1000)
        clock.advance_ms(500)
        assert _get_color(light).hue == pytest.approx(65518, abs=1)

    def test_hue_wraps_backward_through_zero(self, light, clock):
        _set_color(light, _hsbk(hue=500))
        _set_color(light, _hsbk(hue=65000), duration_ms=1000)
        clock.advance_ms(500)
        assert _get_color(light).hue == pytest.approx(65518, abs=1)

    def test_all_components_interpolate_linearly(self, light, clock):
        _set_color(
            light, _hsbk(hue=1000, saturation=1000, brightness=1000, kelvin=2500)
        )
        _set_color(
            light,
            _hsbk(hue=3000, saturation=3000, brightness=3000, kelvin=4500),
            duration_ms=1000,
        )
        clock.advance_ms(250)
        colour = _get_color(light)
        assert (colour.hue, colour.saturation, colour.brightness, colour.kelvin) == (
            1500,
            1500,
            1500,
            3000,
        )

    def test_state_change_callback_keeps_duration(self, light):
        calls = []
        light.on_state_changed = lambda d, t, ms: calls.append((t, ms))
        _set_color(light, _hsbk(brightness=65535), duration_ms=1500)
        assert calls == [(Light.SetColor.PKT_TYPE, 1500)]


class TestPower:
    def test_light_set_power_fades(self, light, clock):
        (reply,) = _send(light, Light.SetPower(level=0, duration=1000))
        assert reply.level == 65535

        clock.advance_ms(500)
        assert _get_power(light) == pytest.approx(32768, abs=1)

        clock.advance_ms(500)
        assert _get_power(light) == 0

    def test_device_set_power_is_immediate(self, light, clock):
        _send(light, Light.SetPower(level=0, duration=1000))
        clock.advance_ms(500)

        (reply,) = _send(light, Device.SetPower(level=65535))
        assert reply.level == 65535
        clock.advance_ms(500)
        assert _get_power(light) == 65535

    def test_power_fade_does_not_disturb_colour_fade(self, light, clock):
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        _send(light, Light.SetPower(level=0, duration=2000))
        clock.advance_ms(500)
        assert _get_color(light).brightness == pytest.approx(32768, abs=1)
        assert _get_power(light) == pytest.approx(49151, abs=1)


class TestMultiZone:
    def test_zones_carry_independent_transitions(self, strip, clock):
        _send(
            strip,
            MultiZone.SetColorZones(
                start_index=0,
                end_index=3,
                color=_hsbk(brightness=65535),
                duration=1000,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )
        clock.advance_ms(500)
        _send(
            strip,
            MultiZone.SetColorZones(
                start_index=4,
                end_index=7,
                color=_hsbk(brightness=65535),
                duration=1000,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )
        clock.advance_ms(500)

        zones = _get_zones(strip)
        assert [z.brightness for z in zones[:4]] == [65535] * 4
        assert [z.brightness for z in zones[4:8]] == pytest.approx([32768] * 4, abs=1)
        assert [z.brightness for z in zones[8:]] == [0] * 8

    def test_no_apply_zones_fade_only_once_applied(self, strip, clock):
        _send(
            strip,
            MultiZone.SetColorZones(
                start_index=0,
                end_index=3,
                color=_hsbk(brightness=65535),
                duration=5000,
                apply=MultiZoneApplicationRequest.NO_APPLY,
            ),
        )
        clock.advance_ms(2500)
        assert [z.brightness for z in _get_zones(strip)[:4]] == [0] * 4

        _send(
            strip,
            MultiZone.SetColorZones(
                start_index=4,
                end_index=7,
                color=_hsbk(brightness=32768),
                duration=1000,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )
        clock.advance_ms(500)

        zones = _get_zones(strip)
        assert [z.brightness for z in zones[:4]] == pytest.approx([32768] * 4, abs=1)
        assert [z.brightness for z in zones[4:8]] == pytest.approx([16384] * 4, abs=1)

    def test_get_color_zones_mid_fade_is_interpolated(self, strip, clock):
        _send(
            strip,
            MultiZone.ExtendedSetColorZones(
                duration=1000,
                apply=MultiZoneApplicationRequest.APPLY,
                index=0,
                colors_count=16,
                colors=[_hsbk(brightness=65535)] * 16 + [BLACK] * 66,
            ),
        )
        clock.advance_ms(250)
        (state, *_rest) = _send(
            strip, MultiZone.GetColorZones(start_index=0, end_index=7)
        )
        assert [c.brightness for c in state.colors] == pytest.approx([16384] * 8, abs=1)

    def test_set_colour_zones_reply_reports_start_colours(self, strip):
        (reply,) = _send(
            strip,
            MultiZone.SetColorZones(
                start_index=0,
                end_index=7,
                color=_hsbk(brightness=65535),
                duration=1000,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )
        assert [c.brightness for c in reply.colors] == [0] * 8

    def test_set_colour_reply_reports_evaluated_zones(self, strip):
        (reply,) = _set_color(strip, _hsbk(brightness=65535), duration_ms=1000)
        assert reply.color.brightness == 0
        assert _get_color(strip).brightness == 0


class TestMatrix:
    def test_set_colour_reply_reports_evaluated_zones(self, tile):
        (reply,) = _set_color(tile, _hsbk(brightness=65535), duration_ms=1000)
        assert reply.color.brightness == 0
        assert _get_color(tile).brightness == 0

    def test_copy_into_hidden_framebuffer_then_back_ends_fade(self, tile, clock):
        _send(
            tile,
            Tile.CopyFrameBuffer(
                tile_index=0,
                length=1,
                src_fb_index=0,
                dst_fb_index=1,
                src_x=0,
                src_y=0,
                dst_x=0,
                dst_y=0,
                width=8,
                height=8,
                duration=0,
            ),
        )
        _set_color(tile, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)
        _send(
            tile,
            Tile.CopyFrameBuffer(
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
            ),
        )
        assert all(c.brightness == 0 for c in _get_tile(tile))
        clock.advance_ms(500)
        assert all(c.brightness == 0 for c in _get_tile(tile))

    def test_set64_fades_only_the_rectangle(self, tile, clock):
        target = _hsbk(brightness=65535)
        _send(
            tile,
            Tile.Set64(
                tile_index=0,
                length=1,
                rect=TileBufferRect(fb_index=0, x=0, y=0, width=2),
                duration=1000,
                colors=[target] * 4 + [BLACK] * 60,
            ),
        )
        clock.advance_ms(500)

        zones = _get_tile(tile)
        faded = {0, 1, 8, 9}
        for index, colour in enumerate(zones):
            expected = 32768 if index in faded else 0
            assert colour.brightness == pytest.approx(expected, abs=1), index

    def test_set64_to_other_framebuffer_is_immediate_and_hidden(self, tile, clock):
        target = _hsbk(brightness=65535)
        _send(
            tile,
            Tile.Set64(
                tile_index=0,
                length=1,
                rect=TileBufferRect(fb_index=1, x=0, y=0, width=8),
                duration=1000,
                colors=[target] * 64,
            ),
        )
        clock.advance_ms(500)
        assert all(c.brightness == 0 for c in _get_tile(tile))

        _send(
            tile,
            Tile.CopyFrameBuffer(
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
                duration=1000,
            ),
        )
        assert all(c.brightness == 65535 for c in _get_tile(tile))

    def test_copy_from_short_framebuffer_copies_what_it_has(self, tile):
        """A framebuffer shorter than the tile (hand-edited state) is not read past."""
        full = _hsbk(brightness=65535)
        framebuffer = tile.state.tile_framebuffers[0].get_framebuffer(1, 8, 8)
        framebuffer[:] = [full] * 8  # only the first row exists
        _send(
            tile,
            Tile.CopyFrameBuffer(
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
            ),
        )
        zones = _get_tile(tile)
        assert all(c.brightness == 65535 for c in zones[:8])
        assert all(c.brightness == 0 for c in zones[8:])

    def test_set_color_fades_every_tile_zone(self, tile, clock):
        _set_color(tile, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)
        assert all(c.brightness == pytest.approx(32768, abs=1) for c in _get_tile(tile))


# Expected progress (0..1) at quarter, half and full phase of one cycle.
_WAVEFORM_CURVES = {
    LightWaveform.SAW: (0.25, 0.5),
    LightWaveform.SINE: (0.5, 1.0),
    LightWaveform.HALF_SINE: (math.sin(math.pi / 8), math.sin(math.pi / 4)),
    LightWaveform.TRIANGLE: (0.5, 1.0),
    LightWaveform.PULSE: (1.0, 0.0),
}
# Where each type ends after its last cycle when the waveform is not transient.
# SINE and TRIANGLE return to the original colour regardless of the flag
# (https://lan.developer.lifx.com/docs/waveforms).
_NON_TRANSIENT_END = {
    LightWaveform.SAW: 1.0,
    LightWaveform.SINE: 0.0,
    LightWaveform.HALF_SINE: 1.0,
    LightWaveform.TRIANGLE: 0.0,
    LightWaveform.PULSE: 1.0,
}


class TestWaveforms:
    @pytest.mark.parametrize("waveform", list(_WAVEFORM_CURVES))
    def test_curve_at_quarter_half_and_full_phase(self, light, clock, waveform):
        quarter, half = _WAVEFORM_CURVES[waveform]
        _set_waveform(light, _hsbk(brightness=65535), waveform, transient=False)

        clock.advance_ms(250)
        assert _get_color(light).brightness == pytest.approx(65535 * quarter, abs=1)

        clock.advance_ms(250)
        assert _get_color(light).brightness == pytest.approx(65535 * half, abs=1)

        clock.advance_ms(500)
        end = _NON_TRANSIENT_END[waveform]
        assert _get_color(light).brightness == pytest.approx(65535 * end, abs=1)

    @pytest.mark.parametrize("waveform", list(_WAVEFORM_CURVES))
    def test_transient_restores_start_colour(self, light, clock, waveform):
        _set_waveform(light, _hsbk(brightness=65535), waveform, transient=True)
        clock.advance_ms(1000)
        assert _get_color(light).brightness == 0
        clock.advance_ms(1000)
        assert _get_color(light).brightness == 0

    def test_cycles_repeat_before_completion(self, light, clock):
        _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.SAW, False, cycles=2.0
        )
        clock.advance_ms(1250)
        assert _get_color(light).brightness == pytest.approx(16384, abs=1)
        clock.advance_ms(750)
        assert _get_color(light).brightness == 65535

    def test_set_reply_reports_start_colour(self, light):
        (reply,) = _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.SAW, False
        )
        assert reply.color.brightness == 0

    @pytest.mark.parametrize(
        ("skew", "on_at_ms", "off_at_ms"),
        [
            (0, 400, 600),  # duty 0.5
            (-16384, 700, 800),  # duty 0.75
            (16384, 200, 300),  # duty 0.25
        ],
    )
    def test_pulse_duty_from_skew_ratio(self, light, clock, skew, on_at_ms, off_at_ms):
        _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.PULSE, True, skew=skew
        )
        clock.advance_ms(on_at_ms)
        assert _get_color(light).brightness == 65535
        clock.advance_ms(off_at_ms - on_at_ms)
        assert _get_color(light).brightness == 0

    def test_waveform_on_multizone_keeps_per_zone_start(self, strip, clock):
        _send(
            strip,
            MultiZone.SetColorZones(
                start_index=0,
                end_index=7,
                color=_hsbk(brightness=20000),
                duration=0,
                apply=MultiZoneApplicationRequest.APPLY,
            ),
        )
        _set_waveform(strip, _hsbk(brightness=65535), LightWaveform.SAW, True)
        clock.advance_ms(500)
        zones = _get_zones(strip)
        assert zones[0].brightness == pytest.approx(42768, abs=1)
        assert zones[8].brightness == pytest.approx(32768, abs=1)
        clock.advance_ms(500)
        zones = _get_zones(strip)
        assert zones[0].brightness == 20000
        assert zones[8].brightness == 0

    def test_optional_changes_only_flagged_components(self, light, clock):
        _set_color(light, _hsbk(hue=1000, saturation=1000, brightness=0, kelvin=2500))
        _send(
            light,
            Light.SetWaveformOptional(
                transient=False,
                color=_hsbk(hue=9000, saturation=9000, brightness=65535, kelvin=6500),
                period=1000,
                cycles=1.0,
                skew_ratio=0,
                waveform=LightWaveform.SAW,
                set_hue=False,
                set_saturation=True,
                set_brightness=True,
                set_kelvin=False,
            ),
        )
        clock.advance_ms(500)
        colour = _get_color(light)
        assert colour.hue == 1000
        assert colour.kelvin == 2500
        assert colour.saturation == pytest.approx(5000, abs=1)
        assert colour.brightness == pytest.approx(32768, abs=1)

        clock.advance_ms(500)
        colour = _get_color(light)
        assert (colour.hue, colour.saturation, colour.brightness, colour.kelvin) == (
            1000,
            9000,
            65535,
            2500,
        )

    @pytest.mark.parametrize(
        ("period", "cycles", "waveform"),
        [
            (0, 1.0, LightWaveform.SAW),
            (1000, 0.0, LightWaveform.SAW),
            (1000, -1.0, LightWaveform.SAW),
            (1000, math.nan, LightWaveform.SAW),
            (1000, math.inf, LightWaveform.SAW),
            (1000, 1.0, 9),
        ],
    )
    def test_invalid_waveform_is_ignored_but_answered(
        self, light, clock, period, cycles, waveform
    ):
        (reply,) = _set_waveform(
            light,
            _hsbk(brightness=65535),
            waveform,
            transient=False,
            period=period,
            cycles=cycles,
        )
        assert reply.color.brightness == 0
        clock.advance_ms(500)
        assert _get_color(light).brightness == 0
        clock.advance_ms(60_000)
        assert _get_color(light).brightness == 0

    def test_set_colour_cancels_waveform_from_evaluated_colour(self, light, clock):
        _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.SINE, False, cycles=10.0
        )
        clock.advance_ms(250)

        (reply,) = _set_color(light, _hsbk(brightness=0), duration_ms=1000)
        assert reply.color.brightness == pytest.approx(32768, abs=1)

        clock.advance_ms(500)
        assert _get_color(light).brightness == pytest.approx(16384, abs=1)
        clock.advance_ms(500)
        assert _get_color(light).brightness == 0

    def test_instant_set_colour_cancels_waveform(self, light, clock):
        _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.SINE, False, cycles=10.0
        )
        clock.advance_ms(250)
        _set_color(light, _hsbk(brightness=10000))
        clock.advance_ms(250)
        assert _get_color(light).brightness == 10000

    def test_waveform_replaces_colour_fade(self, light, clock):
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)
        _set_waveform(light, _hsbk(brightness=0), LightWaveform.SAW, False)
        clock.advance_ms(500)
        assert _get_color(light).brightness == pytest.approx(16384, abs=1)
        clock.advance_ms(500)
        assert _get_color(light).brightness == 0

    def test_waveform_parameters_still_stored(self, light):
        _set_waveform(
            light, _hsbk(brightness=65535), LightWaveform.TRIANGLE, True, cycles=3.0
        )
        assert light.state.waveform_active is True
        assert light.state.waveform_type == int(LightWaveform.TRIANGLE)
        assert light.state.waveform_cycles == 3.0


class TestZoneAddressing:
    def test_matrix_index_out_of_range_raises(self, tile):
        with pytest.raises(IndexError):
            transitions.get_zone_color(tile.state, 10_000)
        with pytest.raises(IndexError):
            transitions.set_zone_color(tile.state, 10_000, BLACK)


class TestPersistence:
    async def test_saved_state_holds_power_and_waveform_end_values(
        self, tmp_path, clock
    ):
        storage = DevicePersistenceAsyncFile(str(tmp_path))
        light = create_color_light(SERIAL, storage=storage, clock=clock)
        _set_color(light, _hsbk(brightness=0))
        _send(light, Light.SetPower(level=0, duration=1000))
        _set_waveform(light, _hsbk(brightness=65535), LightWaveform.SAW, False)
        clock.advance_ms(500)
        light.settle()

        await storage.save_device_state(light.state)
        await storage.shutdown()

        saved = storage.load_device_state(SERIAL)
        assert saved is not None
        assert saved["power_level"] == 0
        assert saved["color"].brightness == 65535

    async def test_saved_state_holds_target_mid_fade(self, tmp_path, clock):
        storage = DevicePersistenceAsyncFile(str(tmp_path))
        light = create_color_light(SERIAL, storage=storage, clock=clock)
        _set_color(light, _hsbk(brightness=0))
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)
        light.settle()

        await storage.save_device_state(light.state)
        await storage.shutdown()

        saved = storage.load_device_state(SERIAL)
        assert saved is not None
        assert saved["color"].brightness == 65535
        assert "transition" not in saved

    async def test_restored_device_has_no_active_transition(self, tmp_path, clock):
        storage = DevicePersistenceAsyncFile(str(tmp_path))
        light = create_color_light(SERIAL, storage=storage, clock=clock)
        _set_color(light, _hsbk(brightness=0))
        _set_color(light, _hsbk(brightness=65535), duration_ms=1000)
        clock.advance_ms(500)
        await storage.save_device_state(light.state)
        await storage.shutdown()

        restored = create_color_light(SERIAL, storage=storage, clock=clock)
        assert _get_color(restored).brightness == 65535
        clock.advance_ms(250)
        assert _get_color(restored).brightness == 65535
