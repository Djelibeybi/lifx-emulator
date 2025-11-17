"""MultiZone packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import MultiZone
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneEffectParameter,
    MultiZoneEffectSettings,
    MultiZoneEffectType,
)

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)


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

            # Update zone colors
            for i in range(start_index, min(end_index + 1, device_state.zone_count)):
                if i < len(device_state.zone_colors):
                    device_state.zone_colors[i] = packet.color

            logger.info(
                f"MultiZone set zones {start_index}-{end_index} to color, "
                f"duration={packet.duration}ms"
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

        colors_count = min(82, len(device_state.zone_colors))
        colors = []
        for i in range(colors_count):
            colors.append(device_state.zone_colors[i])
        # Pad to 82 colors
        while len(colors) < 82:
            colors.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        return [
            MultiZone.ExtendedStateMultiZone(
                count=device_state.zone_count,
                index=0,
                colors_count=colors_count,
                colors=colors,
            )
        ]


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
            # Update zone colors from packet
            for i, color in enumerate(packet.colors[: packet.colors_count]):
                zone_index = packet.index + i
                if zone_index < len(device_state.zone_colors):
                    device_state.zone_colors[zone_index] = color

            logger.info(
                f"MultiZone extended set {packet.colors_count} zones "
                f"from index {packet.index}, duration={packet.duration}ms"
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

        # Create effect settings
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
            instanceid=0,
            type=MultiZoneEffectType(device_state.multizone_effect_type),
            speed=device_state.multizone_effect_speed * 1000,  # convert to milliseconds
            duration=0,  # infinite
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
            device_state.multizone_effect_type = int(packet.settings.type)
            device_state.multizone_effect_speed = (
                packet.settings.speed // 1000
            )  # convert to seconds

            logger.info(
                f"MultiZone effect set: type={packet.settings.type}, "
                f"speed={packet.settings.speed}ms"
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
