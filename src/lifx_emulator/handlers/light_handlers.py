"""Light packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
    """Handle LightSetColor (102) -> LightState (107)."""

    PKT_TYPE = Light.SetColor.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetColor | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.color = packet.color
            c = packet.color

            # For backwards compatibility: propagate color to all zones
            # Multizone devices: update all zone colors
            if device_state.has_multizone and device_state.zone_colors:
                for i in range(len(device_state.zone_colors)):
                    device_state.zone_colors[i] = packet.color
                logger.info(
                    f"Color set to HSBK({c.hue}, {c.saturation}, "
                    f"{c.brightness}, {c.kelvin}) across all "
                    f"{len(device_state.zone_colors)} zones, "
                    f"duration={packet.duration}ms"
                )
            # Matrix devices: update all tile zones
            elif device_state.has_matrix and device_state.tile_devices:
                total_zones = 0
                for tile in device_state.tile_devices:
                    for i in range(len(tile["colors"])):
                        tile["colors"][i] = packet.color
                    total_zones += len(tile["colors"])
                logger.info(
                    f"Color set to HSBK({c.hue}, {c.saturation}, "
                    f"{c.brightness}, {c.kelvin}) across all {total_zones} zones, "
                    f"duration={packet.duration}ms"
                )
            else:
                # Simple color device
                logger.info(
                    f"Color set to HSBK({c.hue}, {c.saturation}, "
                    f"{c.brightness}, {c.kelvin}), duration={packet.duration}ms"
                )

        if res_required:
            return [
                Light.StateColor(
                    color=device_state.color,
                    power=device_state.power_level,
                    label=device_state.label,
                )
            ]
        return []


class GetPowerHandler(PacketHandler):
    """Handle LightGetPower (116) -> LightStatePower (118)."""

    PKT_TYPE = Light.GetPower.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Light.StatePower(level=device_state.power_level)]


class SetPowerHandler(PacketHandler):
    """Handle LightSetPower (117) -> LightStatePower (118)."""

    PKT_TYPE = Light.SetPower.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetPower | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.power_level = packet.level
            logger.info(
                f"Light power set to {packet.level}, duration={packet.duration}ms"
            )

        if res_required:
            return [Light.StatePower(level=device_state.power_level)]
        return []


class SetWaveformHandler(PacketHandler):
    """Handle LightSetWaveform (103) -> LightState (107)."""

    PKT_TYPE = Light.SetWaveform.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetWaveform | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            # Store waveform state
            device_state.waveform_active = True
            device_state.waveform_transient = packet.transient
            device_state.waveform_color = packet.color
            device_state.waveform_period_ms = packet.period
            device_state.waveform_cycles = packet.cycles
            device_state.waveform_skew_ratio = packet.skew_ratio
            device_state.waveform_type = int(packet.waveform)

            # If not transient, update the color state
            if not packet.transient:
                device_state.color = packet.color

                # For backwards compatibility: propagate color to all zones
                # Multizone devices: update all zone colors
                if device_state.has_multizone and device_state.zone_colors:
                    for i in range(len(device_state.zone_colors)):
                        device_state.zone_colors[i] = packet.color
                # Matrix devices: update all tile zones
                elif device_state.has_matrix and device_state.tile_devices:
                    for tile in device_state.tile_devices:
                        for i in range(len(tile["colors"])):
                            tile["colors"][i] = packet.color

            logger.info(
                f"Waveform set: type={packet.waveform}, "
                f"transient={packet.transient}, period={packet.period}ms, "
                f"cycles={packet.cycles}, skew={packet.skew_ratio}"
            )

        if res_required:
            # Use GetColorHandler to get proper averaged color if needed
            handler = GetColorHandler()
            return handler.handle(device_state, None, res_required)
        return []


class SetWaveformOptionalHandler(PacketHandler):
    """Handle LightSetWaveformOptional (119) -> LightState (107)."""

    PKT_TYPE = Light.SetWaveformOptional.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Light.SetWaveformOptional | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            # Store waveform state
            device_state.waveform_active = True
            device_state.waveform_transient = packet.transient
            device_state.waveform_period_ms = packet.period
            device_state.waveform_cycles = packet.cycles
            device_state.waveform_skew_ratio = packet.skew_ratio
            device_state.waveform_type = int(packet.waveform)

            # Apply color components selectively based on flags
            if not packet.transient:
                if packet.set_hue:
                    device_state.color.hue = packet.color.hue
                if packet.set_saturation:
                    device_state.color.saturation = packet.color.saturation
                if packet.set_brightness:
                    device_state.color.brightness = packet.color.brightness
                if packet.set_kelvin:
                    device_state.color.kelvin = packet.color.kelvin

                # Backwards compatibility propagates color changes to zones
                # Multizone devices: update all zone colors
                if device_state.has_multizone and device_state.zone_colors:
                    for zone_color in device_state.zone_colors:
                        if packet.set_hue:
                            zone_color.hue = packet.color.hue
                        if packet.set_saturation:
                            zone_color.saturation = packet.color.saturation
                        if packet.set_brightness:
                            zone_color.brightness = packet.color.brightness
                        if packet.set_kelvin:
                            zone_color.kelvin = packet.color.kelvin
                # Matrix devices: update all tile zones
                elif device_state.has_matrix and device_state.tile_devices:
                    for tile in device_state.tile_devices:
                        for zone_color in tile["colors"]:
                            if packet.set_hue:
                                zone_color.hue = packet.color.hue
                            if packet.set_saturation:
                                zone_color.saturation = packet.color.saturation
                            if packet.set_brightness:
                                zone_color.brightness = packet.color.brightness
                            if packet.set_kelvin:
                                zone_color.kelvin = packet.color.kelvin

            # Store the waveform color (all components)
            device_state.waveform_color = packet.color

            logger.info(
                f"Waveform optional set: type={packet.waveform}, "
                f"transient={packet.transient}, period={packet.period}ms, "
                f"cycles={packet.cycles}, components=[H:{packet.set_hue},"
                f"S:{packet.set_saturation},B:{packet.set_brightness},"
                f"K:{packet.set_kelvin}]"
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
        return [
            Light.StateHevCycle(
                duration_s=device_state.hev_cycle_duration_s,
                remaining_s=device_state.hev_cycle_remaining_s,
                last_power=device_state.hev_cycle_last_power,
            )
        ]


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
            device_state.hev_cycle_duration_s = packet.duration_s
            if packet.enable:
                device_state.hev_cycle_remaining_s = packet.duration_s
            else:
                device_state.hev_cycle_remaining_s = 0
            logger.info(
                f"HEV cycle set: enable={packet.enable}, duration={packet.duration_s}s"
            )

        if res_required:
            return [
                Light.StateHevCycle(
                    duration_s=device_state.hev_cycle_duration_s,
                    remaining_s=device_state.hev_cycle_remaining_s,
                    last_power=device_state.hev_cycle_last_power,
                )
            ]
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
                f"HEV config set: indication={packet.indication}, "
                f"duration={packet.duration_s}s"
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
