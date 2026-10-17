"""Lazy evaluation of colour and power transitions and waveforms.

Nothing in this module ticks. A packet handler records what a device is
moving towards and when; ``settle()`` later evaluates every record against
the clock, commits the interpolated values into the ordinary colour and power
fields, and prunes whatever has finished. Handlers therefore keep reading
plain fields and never see the clock: a new transition starts at the instant
the state was last settled to (``TransitionState.settled_ns``).

Zones use a flat index: a colour light has zone 0, a multizone light has zone
0 to ``zone_count - 1`` and a matrix device has one zone per framebuffer-0
cell, tile by tile. Only framebuffer 0 ever transitions.

This module depends only on the device state and protocol types; it must not
import transport, API or UI code.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Protocol

from lifx_emulator.devices.states import (
    ActiveWaveform,
    ColorTransition,
    PowerEnvelope,
)
from lifx_emulator.protocol.protocol_types import LightHsbk, LightWaveform

if TYPE_CHECKING:
    from lifx_emulator.devices.states import DeviceState

NS_PER_MS = 1_000_000
_HUE_RANGE = 0x10000
_HALF_HUE_RANGE = _HUE_RANGE // 2
_UINT16_MAX = 0xFFFF
# skew_ratio is a signed int16 scaled onto 0..1 (-32768 -> 0, 32767 -> 1)
_SKEW_OFFSET = 0x8000
_SKEW_RANGE = 0xFFFF
# A SINE or TRIANGLE cycle ends where it began, and the LIFX waveform
# documentation says the light returns to its original colour for these two
# types whatever the transient flag says.
_RETURNS_TO_START = frozenset({int(LightWaveform.SINE), int(LightWaveform.TRIANGLE)})

ZoneWriter = Callable[[int, LightHsbk], None]

# The device-level colour of a multizone or matrix device, which SetColor
# fades alongside the zones so the top-level colour never reports the
# destination before the zones reach it. On a colour light zone 0 is the
# device colour already.
DEVICE_COLOR_ZONE = -1


class WaveformParameters(Protocol):
    """The waveform fields shared by SetWaveform and SetWaveformOptional."""

    transient: bool
    period: int
    cycles: float
    skew_ratio: int
    waveform: int


# --- Flat zone addressing -------------------------------------------------


def zone_count(state: DeviceState) -> int:
    """Number of flat zones that take part in transitions on this device."""
    if state.has_matrix and state.tile_devices:
        return sum(len(tile["colors"]) for tile in state.tile_devices)
    if state.has_multizone and state.zone_colors:
        return len(state.zone_colors)
    return 1


def matrix_zone_offset(state: DeviceState, tile_index: int) -> int:
    """Flat zone index of the first framebuffer-0 cell on a tile."""
    return sum(len(tile["colors"]) for tile in state.tile_devices[:tile_index])


def get_zone_color(state: DeviceState, index: int) -> LightHsbk:
    """Current colour of one flat zone (or the device colour for -1)."""
    if index == DEVICE_COLOR_ZONE:
        return state.color
    if state.has_matrix and state.tile_devices:
        for tile in state.tile_devices:
            if index < len(tile["colors"]):
                return tile["colors"][index]
            index -= len(tile["colors"])
        raise IndexError("Matrix zone index out of range")
    if state.has_multizone and state.zone_colors:
        return state.zone_colors[index]
    return state.color


def set_zone_color(state: DeviceState, index: int, color: LightHsbk) -> None:
    """Write one flat zone's colour (or the device colour for -1) to the fields."""
    if index == DEVICE_COLOR_ZONE:
        state.color = color
        return
    if state.has_matrix and state.tile_devices:
        for tile in state.tile_devices:
            if index < len(tile["colors"]):
                tile["colors"][index] = color
                return
            index -= len(tile["colors"])
        raise IndexError("Matrix zone index out of range")
    if state.has_multizone and state.zone_colors:
        state.zone_colors[index] = color
        return
    state.color = color


# --- Interpolation --------------------------------------------------------


def _clamp16(value: float) -> int:
    return max(0, min(_UINT16_MAX, round(value)))


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def interpolate_hue(start: int, end: int, progress: float) -> int:
    """Hue along the shortest path around the 16-bit colour wheel."""
    delta = ((end - start + _HALF_HUE_RANGE) % _HUE_RANGE) - _HALF_HUE_RANGE
    return round(start + delta * progress) % _HUE_RANGE


def interpolate_color(start: LightHsbk, end: LightHsbk, progress: float) -> LightHsbk:
    """Colour ``progress`` of the way from ``start`` to ``end``.

    Hue takes the shortest circular path; saturation, brightness and kelvin
    are linear. Maths is done in floating point and rounded once here.
    """
    return LightHsbk(
        hue=interpolate_hue(start.hue, end.hue, progress),
        saturation=_clamp16(_lerp(start.saturation, end.saturation, progress)),
        brightness=_clamp16(_lerp(start.brightness, end.brightness, progress)),
        kelvin=_clamp16(_lerp(start.kelvin, end.kelvin, progress)),
    )


def _progress(start_ns: int, end_ns: int, now_ns: int) -> float:
    """Fraction of a linear transition elapsed at ``now_ns``, clamped to 0..1."""
    if now_ns >= end_ns:
        return 1.0
    if now_ns <= start_ns or end_ns <= start_ns:
        return 0.0
    return (now_ns - start_ns) / (end_ns - start_ns)


# --- Waveforms ------------------------------------------------------------


def pulse_duty_cycle(skew_ratio: int) -> float:
    """Fraction of each PULSE cycle spent on the target colour.

    The LIFX documentation defines the duty cycle as ``1 - skew_ratio`` with
    ``skew_ratio`` scaled from the signed 16-bit range onto 0..1, so 0 gives a
    50% duty cycle, -32768 holds the target colour for the whole cycle and
    32767 never shows it.
    """
    scaled = (skew_ratio + _SKEW_OFFSET) / _SKEW_RANGE
    return min(1.0, max(0.0, 1.0 - scaled))


def waveform_progress(waveform_type: int, phase: float, skew_ratio: int) -> float:
    """How far (0..1) a waveform is towards its target at ``phase`` (0..1).

    SAW rises linearly, SINE is a raised cosine, HALF_SINE is a quarter sine
    that rises smoothly, TRIANGLE rises then falls linearly, and PULSE holds
    the target for the duty-cycle fraction of the period then drops back.
    """
    if waveform_type == LightWaveform.SINE:
        return (1.0 - math.cos(2.0 * math.pi * phase)) / 2.0
    if waveform_type == LightWaveform.HALF_SINE:
        return math.sin(phase * math.pi / 2.0)
    if waveform_type == LightWaveform.TRIANGLE:
        return 2.0 * phase if phase < 0.5 else 2.0 * (1.0 - phase)
    if waveform_type == LightWaveform.PULSE:
        return 1.0 if phase < pulse_duty_cycle(skew_ratio) else 0.0
    return phase  # SAW


def waveform_end_colors(waveform: ActiveWaveform) -> list[LightHsbk]:
    """Per-zone colours a waveform leaves behind once it completes."""
    if waveform.transient or waveform.waveform_type in _RETURNS_TO_START:
        return list(waveform.start_colors)
    return list(waveform.target_colors)


def evaluate_waveform(
    waveform: ActiveWaveform, now_ns: int
) -> tuple[list[LightHsbk], bool]:
    """Per-zone colours of a waveform at ``now_ns`` and whether it has ended."""
    elapsed_ns = max(0, now_ns - waveform.start_ns)
    phase = elapsed_ns / waveform.period_ns
    if phase >= waveform.cycles:
        return waveform_end_colors(waveform), True
    fraction = phase - math.floor(phase)
    progress = waveform_progress(waveform.waveform_type, fraction, waveform.skew_ratio)
    colors = [
        interpolate_color(start, target, progress)
        for start, target in zip(waveform.start_colors, waveform.target_colors)
    ]
    return colors, False


def _waveform_is_valid(params: WaveformParameters) -> bool:
    """Reject the parameters real firmware cannot run."""
    if params.period <= 0:
        return False
    cycles = float(params.cycles)
    if not math.isfinite(cycles) or cycles <= 0:
        return False
    return int(params.waveform) in {int(member) for member in LightWaveform}


# --- Recording transitions (called by packet handlers) ----------------------


def apply_zone_colors(
    state: DeviceState, targets: Mapping[int, LightHsbk], duration_ms: int
) -> None:
    """Show target colours now, or record a fade to them over ``duration_ms``.

    Any colour change cancels an active waveform; its zones keep the colours
    they were last settled to. A fade starts from the zone's current colour
    and replaces any fade already running on that zone.
    """
    transition = state.transition
    transition.waveform = None
    if duration_ms <= 0:
        for index, color in targets.items():
            transition.zones.pop(index, None)
            set_zone_color(state, index, color)
        return
    start_ns = transition.settled_ns
    end_ns = start_ns + duration_ms * NS_PER_MS
    for index, color in targets.items():
        transition.zones[index] = ColorTransition(
            from_color=get_zone_color(state, index),
            to_color=color,
            start_ns=start_ns,
            end_ns=end_ns,
        )


def apply_power(state: DeviceState, level: int, duration_ms: int) -> None:
    """Set the power level now, or record a ramp to it over ``duration_ms``."""
    transition = state.transition
    if duration_ms <= 0:
        transition.power = None
        state.power_level = level
        return
    start_ns = transition.settled_ns
    transition.power = PowerEnvelope(
        from_level=state.power_level,
        to_level=level,
        start_ns=start_ns,
        end_ns=start_ns + duration_ms * NS_PER_MS,
    )


def begin_waveform(
    state: DeviceState,
    params: WaveformParameters,
    target_for: Callable[[LightHsbk], LightHsbk],
) -> bool:
    """Start a waveform from every zone's current colour.

    ``target_for`` maps a zone's start colour to its target, which lets
    SetWaveformOptional replace only the flagged components. Any colour fade
    in flight is replaced.

    Returns:
        False if the parameters are invalid (period 0, cycles not positive and
        finite, or an unknown type); the state is then left untouched.
    """
    if not _waveform_is_valid(params):
        return False
    start_colors = [get_zone_color(state, i) for i in range(zone_count(state))]
    transition = state.transition
    transition.zones.clear()
    transition.waveform = ActiveWaveform(
        start_colors=start_colors,
        target_colors=[target_for(color) for color in start_colors],
        start_ns=transition.settled_ns,
        period_ns=params.period * NS_PER_MS,
        cycles=float(params.cycles),
        skew_ratio=params.skew_ratio,
        waveform_type=int(params.waveform),
        transient=params.transient,
    )
    return True


# --- Settling (called by the device before any read) ------------------------


def _settle_zones(state: DeviceState, now_ns: int) -> None:
    finished: list[int] = []
    for index, fade in state.transition.zones.items():
        progress = _progress(fade.start_ns, fade.end_ns, now_ns)
        set_zone_color(
            state, index, interpolate_color(fade.from_color, fade.to_color, progress)
        )
        if progress >= 1.0:
            finished.append(index)
    for index in finished:
        del state.transition.zones[index]


def _settle_power(state: DeviceState, now_ns: int) -> None:
    envelope = state.transition.power
    if envelope is None:
        return
    progress = _progress(envelope.start_ns, envelope.end_ns, now_ns)
    state.power_level = _clamp16(
        _lerp(envelope.from_level, envelope.to_level, progress)
    )
    if progress >= 1.0:
        state.transition.power = None


def _settle_waveform(state: DeviceState, now_ns: int) -> None:
    waveform = state.transition.waveform
    if waveform is None:
        return
    colors, finished = evaluate_waveform(waveform, now_ns)
    for index, color in enumerate(colors):
        set_zone_color(state, index, color)
    if finished:
        state.transition.waveform = None


def settle(state: DeviceState, now_ns: int) -> None:
    """Commit every in-flight value as of ``now_ns`` and prune what finished.

    A device with nothing in flight pays only for recording the instant, so
    static devices keep their current cost.
    """
    transition = state.transition
    transition.settled_ns = now_ns
    if not transition.is_active:
        return
    _settle_zones(state, now_ns)
    _settle_power(state, now_ns)
    _settle_waveform(state, now_ns)


def project_to_end(state: DeviceState) -> DeviceState:
    """A copy of ``state`` with every in-flight change at its end value.

    Persistence uses this so a saved file holds where a fade or waveform will
    land, never a half-finished transition. The state itself is returned
    untouched when nothing is in flight.
    """
    if not state.transition.is_active:
        return state
    projected = copy.deepcopy(state)
    transition = projected.transition
    for index, fade in transition.zones.items():
        set_zone_color(projected, index, fade.to_color)
    if transition.power is not None:
        projected.power_level = transition.power.to_level
    if transition.waveform is not None:
        for index, color in enumerate(waveform_end_colors(transition.waveform)):
            set_zone_color(projected, index, color)
    transition.cancel_colors()
    transition.cancel_power()
    return projected
