"""Light packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lifx_emulator.devices import transitions
from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.protocol_types import LightHsbk, LightLastHevCycleResult

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)


def _compute_average_color(colors: list[LightHsbk]) -> LightHsbk:
    """Compute average HSBK color from a list of LightHsbk colors.

    Uses circular mean for hue to correctly handle hue wraparound
    (e.g., average of 10° and 350° is 0°, not 180°).

    Args:
        colors: List of LightHsbk colors to average

    Returns:
        LightHsbk with averaged values using circular mean for hue
    """
    import math

    if not colors:
        return LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)

    # Convert uint16 values to proper ranges and calculate circular mean
    hue_x_total = 0.0
    hue_y_total = 0.0
    saturation_total = 0.0
    brightness_total = 0.0
    kelvin_total = 0

    for color in colors:
        # Convert uint16 hue (0-65535) to degrees (0-360)
        hue_deg = round(float(color.hue) * 360 / 0x10000, 2)

        # Convert uint16 sat/bright (0-65535) to float (0-1)
        sat_float = round(float(color.saturation) / 0xFFFF, 4)
        bright_float = round(float(color.brightness) / 0xFFFF, 4)

        # Circular mean calculation for hue using sin/cos
        hue_x_total += math.sin(hue_deg * 2.0 * math.pi / 360)
        hue_y_total += math.cos(hue_deg * 2.0 * math.pi / 360)

        # Regular sums for other components
        saturation_total += sat_float
        brightness_total += bright_float
        kelvin_total += color.kelvin

    # Calculate circular mean for hue
    hue = math.atan2(hue_x_total, hue_y_total) / (2.0 * math.pi)
    if hue < 0.0:
        hue += 1.0
    hue *= 360
    hue = round(hue, 4)

    # Calculate arithmetic means for other components
    saturation = round(saturation_total / len(colors), 4)
    brightness = round(brightness_total / len(colors), 4)
    kelvin = round(kelvin_total / len(colors))

    # Convert back to uint16 values
    uint16_hue = int(round(0x10000 * hue) / 360) % 0x10000
    uint16_saturation = int(round(0xFFFF * saturation))
    uint16_brightness = int(round(0xFFFF * brightness))

    return LightHsbk(
        hue=uint16_hue,
        saturation=uint16_saturation,
        brightness=uint16_brightness,
        kelvin=kelvin,
    )


def _state_hev_cycle(device_state: DeviceState) -> Light.StateHevCycle:
    """Build a StateHevCycle reporting the current or most recent cycle."""
    duration_s = device_state.hev_cycle_current_duration_s
    if duration_s is None:
        duration_s = device_state.hev_cycle_duration_s
    return Light.StateHevCycle(
        duration_s=duration_s,
        remaining_s=device_state.hev_cycle_remaining_s,
        last_power=device_state.hev_cycle_last_power,
    )


class GetColorHandler(PacketHandler):
    """Handle LightGet (101) -> LightState (107)."""

    PKT_TYPE = Light.GetColor.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        # For multizone/matrix devices, compute average color from all zones
        # This provides backwards compatibility with clients that don't use
        # zone-specific or tile-specific packets
        color_to_return = device_state.color

        if device_state.has_multizone and device_state.zone_colors:
            # Return average of all zone colors
            color_to_return = _compute_average_color(device_state.zone_colors)
        elif device_state.has_matrix and device_state.tile_devices:
            # Collect all zone colors from all tiles
            all_zones = []
            for tile in device_state.tile_devices:
                all_zones.extend(tile["colors"])
            color_to_return = _compute_average_color(all_zones)

        return [
            Light.StateColor(
                color=color_to_return,
                power=device_state.power_level,
                label=device_state.label,
            )
        ]


class SetColorHandler(PacketHandler):
    """Handle LightSetColor (102) -> LightState (107).

    With a duration of 0 the colour applies at once. Otherwise every zone,
    and on multizone and matrix devices the device-level colour as well,
    records a fade from its current colour to the new one, evaluated lazily
    on each later read. The reply is built like LightState: the colour at the
    time of the reply (the start of the fade), averaged over the zones on a
    multizone or matrix device. Either way an active waveform is cancelled at
    the colour it had reached.
    """

    PKT_TYPE = Light.SetColor.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetColor | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            c = packet.color
            zone_total = transitions.zone_count(device_state)
            targets = dict.fromkeys(range(zone_total), c)
            # Fade the device-level colour of a multizone or matrix device in
            # step with its zones (a colour light's zone 0 is that colour)
            if device_state.has_multizone or device_state.has_matrix:
                targets[transitions.DEVICE_COLOR_ZONE] = c
            transitions.apply_zone_colors(device_state, targets, packet.duration)
            logger.info(
                "Color set to HSBK(%s, %s, %s, %s) across %s zone(s), duration=%sms",
                c.hue,
                c.saturation,
                c.brightness,
                c.kelvin,
                zone_total,
                packet.duration,
            )

        if res_required:
            # Report evaluated state: averaged over the zones where there are any
            return GetColorHandler().handle(device_state, None, res_required)
        return []


class GetPowerHandler(PacketHandler):
    """Handle LightGetPower (116) -> LightStatePower (118)."""

    PKT_TYPE = Light.GetPower.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Light.StatePower(level=device_state.power_level)]


class SetPowerHandler(PacketHandler):
    """Handle LightSetPower (117) -> LightStatePower (118).

    A non-zero duration records a power envelope from the current level to
    the new one. The LIFX documentation only says the level "will transition"
    over the duration and does not state what LightStatePower reports in the
    meantime, so this emulator reports the interpolated level, as it does for
    colour, and the reply to the Set carries the level at the time of the
    reply (the start of the ramp).
    """

    PKT_TYPE = Light.SetPower.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetPower | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            transitions.apply_power(device_state, packet.level, packet.duration)
            logger.info(
                "Light power set to %s, duration=%sms", packet.level, packet.duration
            )

        if res_required:
            return [Light.StatePower(level=device_state.power_level)]
        return []


def _store_waveform_fields(
    device_state: DeviceState,
    packet: Light.SetWaveform | Light.SetWaveformOptional,
) -> None:
    """Keep the raw waveform parameters so they round-trip through state."""
    device_state.waveform_active = True
    device_state.waveform_transient = packet.transient
    device_state.waveform_color = packet.color
    device_state.waveform_period_ms = packet.period
    device_state.waveform_cycles = packet.cycles
    device_state.waveform_skew_ratio = packet.skew_ratio
    device_state.waveform_type = int(packet.waveform)


class SetWaveformHandler(PacketHandler):
    """Handle LightSetWaveform (103) -> LightState (107).

    The waveform runs lazily from every zone's current colour towards the
    packet's colour for ``cycles`` periods. On completion a transient
    waveform restores each zone's start colour; a non-transient SAW,
    HALF_SINE or PULSE leaves the target colour. SINE and TRIANGLE always end
    on the start colour, whatever ``transient`` says, because that is what
    the LIFX waveform documentation specifies for those two types (and the
    mathematical end of a full cycle). A period of 0, a cycle count that is
    not positive and finite, or an unknown type is ignored: nothing changes
    but LightState is still returned when requested.
    """

    PKT_TYPE = Light.SetWaveform.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetWaveform | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            _store_waveform_fields(device_state, packet)
            color = packet.color
            started = transitions.begin_waveform(device_state, packet, lambda _: color)
            logger.info(
                "Waveform %s: type=%s, transient=%s, period=%sms, cycles=%s, skew=%s",
                "set" if started else "rejected",
                packet.waveform,
                packet.transient,
                packet.period,
                packet.cycles,
                packet.skew_ratio,
            )

        if res_required:
            # Use GetColorHandler to get proper averaged color if needed
            handler = GetColorHandler()
            return handler.handle(device_state, None, res_required)
        return []


class SetWaveformOptionalHandler(PacketHandler):
    """Handle LightSetWaveformOptional (119) -> LightState (107).

    As SetWaveform, except that each zone's target is its own start colour
    with only the components whose ``set_*`` flag is true replaced by the
    packet's colour. End-state rules (transient, and SINE/TRIANGLE always
    returning to the start colour) are those of SetWaveformHandler.
    """

    PKT_TYPE = Light.SetWaveformOptional.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetWaveformOptional | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            _store_waveform_fields(device_state, packet)
            color = packet.color

            def target_for(start: LightHsbk) -> LightHsbk:
                return LightHsbk(
                    hue=color.hue if packet.set_hue else start.hue,
                    saturation=(
                        color.saturation if packet.set_saturation else start.saturation
                    ),
                    brightness=(
                        color.brightness if packet.set_brightness else start.brightness
                    ),
                    kelvin=color.kelvin if packet.set_kelvin else start.kelvin,
                )

            started = transitions.begin_waveform(device_state, packet, target_for)
            logger.info(
                "Waveform optional %s: type=%s, transient=%s, period=%sms, "
                "cycles=%s, components=[H:%s,S:%s,B:%s,K:%s]",
                "set" if started else "rejected",
                packet.waveform,
                packet.transient,
                packet.period,
                packet.cycles,
                packet.set_hue,
                packet.set_saturation,
                packet.set_brightness,
                packet.set_kelvin,
            )

        if res_required:
            # Use GetColorHandler to get proper averaged color if needed
            handler = GetColorHandler()
            return handler.handle(device_state, None, res_required)
        return []


class GetInfraredHandler(PacketHandler):
    """Handle LightGetInfrared (120) -> LightStateInfrared (121)."""

    PKT_TYPE = Light.GetInfrared.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_infrared:
            return []
        return [Light.StateInfrared(brightness=device_state.infrared_brightness)]


class SetInfraredHandler(PacketHandler):
    """Handle LightSetInfrared (122) -> LightStateInfrared (121)."""

    PKT_TYPE = Light.SetInfrared.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetInfrared | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_infrared:
            return []
        if packet:
            device_state.infrared_brightness = packet.brightness
            logger.info("Infrared brightness set to %s", packet.brightness)

        if res_required:
            return [Light.StateInfrared(brightness=device_state.infrared_brightness)]
        return []


class GetHevCycleHandler(PacketHandler):
    """Handle LightGetHevCycle (142) -> LightStateHevCycle (144)."""

    PKT_TYPE = Light.GetHevCycle.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_hev:
            return []
        return [_state_hev_cycle(device_state)]


class SetHevCycleHandler(PacketHandler):
    """Handle LightSetHevCycle (143) -> LightStateHevCycle (144)."""

    PKT_TYPE = Light.SetHevCycle.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetHevCycle | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_hev:
            return []
        if packet:
            if packet.enable:
                # A one-off cycle length: it must not change the configured
                # default, and 0 means "use the configured default"
                duration_s = packet.duration_s or device_state.hev_cycle_duration_s
                device_state.hev_cycle_current_duration_s = duration_s
                device_state.hev_cycle_remaining_s = duration_s
                # StateHevCycle last_power is the power state from before the
                # cycle started, which the light returns to when it completes
                device_state.hev_cycle_last_power = device_state.power_level > 0
            else:
                device_state.hev_cycle_remaining_s = 0
            logger.info(
                "HEV cycle set: enable=%s, duration=%ss",
                packet.enable,
                packet.duration_s,
            )

        if res_required:
            return [_state_hev_cycle(device_state)]
        return []


class GetHevCycleConfigurationHandler(PacketHandler):
    """Handle LightGetHevCycleConfiguration (145).

    Returns LightStateHevCycleConfiguration (147).
    """

    PKT_TYPE = Light.GetHevCycleConfiguration.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_hev:
            return []
        return [
            Light.StateHevCycleConfiguration(
                indication=device_state.hev_indication,
                duration_s=device_state.hev_cycle_duration_s,
            )
        ]


class SetHevCycleConfigurationHandler(PacketHandler):
    """Handle LightSetHevCycleConfiguration (146).

    Returns LightStateHevCycleConfiguration (147).
    """

    PKT_TYPE = Light.SetHevCycleConfiguration.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetHevCycleConfiguration | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_hev:
            return []
        if packet:
            device_state.hev_indication = packet.indication
            device_state.hev_cycle_duration_s = packet.duration_s
            logger.info(
                "HEV config set: indication=%s, duration=%ss",
                packet.indication,
                packet.duration_s,
            )

        if res_required:
            return [
                Light.StateHevCycleConfiguration(
                    indication=device_state.hev_indication,
                    duration_s=device_state.hev_cycle_duration_s,
                )
            ]
        return []


class GetLastHevCycleResultHandler(PacketHandler):
    """Handle LightGetLastHevCycleResult (148) -> LightStateLastHevCycleResult (149)."""

    PKT_TYPE = Light.GetLastHevCycleResult.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_hev:
            return []
        return [
            Light.StateLastHevCycleResult(
                result=LightLastHevCycleResult(device_state.hev_last_result)
            )
        ]


# List of all light handlers for easy registration
ALL_LIGHT_HANDLERS = [
    GetColorHandler(),
    SetColorHandler(),
    GetPowerHandler(),
    SetPowerHandler(),
    SetWaveformHandler(),
    SetWaveformOptionalHandler(),
    GetInfraredHandler(),
    SetInfraredHandler(),
    GetHevCycleHandler(),
    SetHevCycleHandler(),
    GetHevCycleConfigurationHandler(),
    SetHevCycleConfigurationHandler(),
    GetLastHevCycleResultHandler(),
]
