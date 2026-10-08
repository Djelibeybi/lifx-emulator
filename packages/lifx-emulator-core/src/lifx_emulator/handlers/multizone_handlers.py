"""MultiZone packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lifx_emulator.devices.states import MULTIZONE_EFFECT_PARAMETER_COUNT
from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import MultiZone
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneApplicationRequest,
    MultiZoneEffectParameter,
    MultiZoneEffectSettings,
    MultiZoneEffectType,
)

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)


def _update_zones(
    device_state: DeviceState, updates: dict[int, LightHsbk], apply: int
) -> None:
    """Stage and/or show zone colours as a (Extended)SetColorZones asks.

    NO_APPLY only stages the colours. APPLY stages them and then shows every
    staged colour. APPLY_ONLY ignores the request's colours and shows what an
    earlier NO_APPLY request staged.

    Args:
        device_state: Multizone device state to update
        updates: Zone colours carried by the request, keyed by zone index
        apply: The request's MultiZoneApplicationRequest value
    """
    pending = device_state.multizone_pending_zone_colors
    if apply != MultiZoneApplicationRequest.APPLY_ONLY:
        zone_total = min(device_state.zone_count, len(device_state.zone_colors))
        pending.update({i: c for i, c in updates.items() if 0 <= i < zone_total})
    if apply == MultiZoneApplicationRequest.NO_APPLY:
        return
    for index, color in pending.items():
        device_state.zone_colors[index] = color
    pending.clear()


class GetColorZonesHandler(PacketHandler):
    """Handle MultiZoneGetColorZones (502) -> StateMultiZone (506) packets."""

    PKT_TYPE = MultiZone.GetColorZones.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: MultiZone.GetColorZones | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        start_index = packet.start_index if packet else 0
        end_index = packet.end_index if packet else 0

        # Return multiple StateMultiZone packets, each containing up to 8 zones
        responses = []

        # Send packets of up to 8 zones each (StateMultiZone format)
        index = start_index
        while index <= end_index and index < device_state.zone_count:
            # Collect up to 8 zones for this packet
            colors = []
            for i in range(8):
                zone_index = index + i
                if zone_index < device_state.zone_count and zone_index <= end_index:
                    zone_color = (
                        device_state.zone_colors[zone_index]
                        if zone_index < len(device_state.zone_colors)
                        else LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )
                    colors.append(zone_color)
                else:
                    # Pad remaining slots with black
                    colors.append(
                        LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )

            # Pad to exactly 8 colors
            while len(colors) < 8:
                colors.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

            packet_obj = MultiZone.StateMultiZone(
                count=device_state.zone_count, index=index, colors=colors
            )
            responses.append(packet_obj)

            index += 8

        return responses


class SetColorZonesHandler(PacketHandler):
    """Handle MultiZoneSetColorZones (501)."""

    PKT_TYPE = MultiZone.SetColorZones.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: MultiZone.SetColorZones | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        if packet:
            start_index = packet.start_index
            end_index = packet.end_index
            updates = dict.fromkeys(range(start_index, end_index + 1), packet.color)
            _update_zones(device_state, updates, packet.apply)

            logger.info(
                "MultiZone set zones %s-%s to color, apply=%s, duration=%sms",
                start_index,
                end_index,
                packet.apply,
                packet.duration,
            )

        if res_required and packet:
            # Create a GetColorZones packet to reuse the get handler
            get_packet = MultiZone.GetColorZones(
                start_index=packet.start_index, end_index=packet.end_index
            )
            # Reuse GetColorZonesHandler
            handler = GetColorZonesHandler()
            return handler.handle(device_state, get_packet, res_required)
        return []


class ExtendedGetColorZonesHandler(PacketHandler):
    """Handle MultiZoneExtendedGetColorZones (511) -> ExtendedStateMultiZone (512)."""

    PKT_TYPE = MultiZone.ExtendedGetColorZones.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        responses = []
        index = 0
        while index < device_state.zone_count:
            end = min(index + 82, device_state.zone_count)
            colors_count = end - index
            colors = list(device_state.zone_colors[index:end])
            # Pad to 82 colors
            while len(colors) < 82:
                colors.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))
            responses.append(
                MultiZone.ExtendedStateMultiZone(
                    count=device_state.zone_count,
                    index=index,
                    colors_count=colors_count,
                    colors=colors,
                )
            )
            index += 82

        return responses


class ExtendedSetColorZonesHandler(PacketHandler):
    """Handle MultiZoneExtendedSetColorZones (510)."""

    PKT_TYPE = MultiZone.ExtendedSetColorZones.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: MultiZone.ExtendedSetColorZones | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        if packet:
            updates = {
                packet.index + i: color
                for i, color in enumerate(packet.colors[: packet.colors_count])
            }
            _update_zones(device_state, updates, packet.apply)

            logger.info(
                "MultiZone extended set %s zones from index %s, apply=%s, "
                "duration=%sms",
                packet.colors_count,
                packet.index,
                packet.apply,
                packet.duration,
            )

        if res_required:
            handler = ExtendedGetColorZonesHandler()
            return handler.handle(device_state, None, res_required)
        return []


class GetEffectHandler(PacketHandler):
    """Handle MultiZoneGetEffect (507) -> StateEffect (509)."""

    PKT_TYPE = MultiZone.GetEffect.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        # Echo exactly what SetEffect stored: a real strip reports back the
        # speed, duration and parameters it was given (for MOVE, parameter1
        # is the direction, so zeroing it would flip FORWARD to REVERSED).
        values = list(device_state.multizone_effect_parameters)
        values += [0] * (MULTIZONE_EFFECT_PARAMETER_COUNT - len(values))
        parameter = MultiZoneEffectParameter(*values[:MULTIZONE_EFFECT_PARAMETER_COUNT])
        settings = MultiZoneEffectSettings(
            instanceid=device_state.multizone_effect_instanceid,
            type=MultiZoneEffectType(device_state.multizone_effect_type),
            speed=device_state.multizone_effect_speed_ms,
            duration=device_state.multizone_effect_duration,
            parameter=parameter,
        )

        return [MultiZone.StateEffect(settings=settings)]


class SetEffectHandler(PacketHandler):
    """Handle MultiZoneSetEffect (508) -> StateEffect (509)."""

    PKT_TYPE = MultiZone.SetEffect.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: MultiZone.SetEffect | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_multizone:
            return []

        if packet:
            settings = packet.settings
            parameter = settings.parameter
            device_state.multizone_effect_type = int(settings.type)
            device_state.multizone_effect_instanceid = settings.instanceid
            device_state.multizone_effect_speed_ms = settings.speed
            device_state.multizone_effect_duration = settings.duration
            device_state.multizone_effect_parameters = [
                parameter.parameter0,
                parameter.parameter1,
                parameter.parameter2,
                parameter.parameter3,
                parameter.parameter4,
                parameter.parameter5,
                parameter.parameter6,
                parameter.parameter7,
            ]

            logger.info(
                "MultiZone effect set: type=%s, speed=%sms, duration=%sns",
                settings.type,
                settings.speed,
                settings.duration,
            )

        if res_required:
            handler = GetEffectHandler()
            return handler.handle(device_state, None, res_required)
        return []


# List of all multizone handlers for easy registration
ALL_MULTIZONE_HANDLERS = [
    GetColorZonesHandler(),
    SetColorZonesHandler(),
    ExtendedGetColorZonesHandler(),
    ExtendedSetColorZonesHandler(),
    GetEffectHandler(),
    SetEffectHandler(),
]
