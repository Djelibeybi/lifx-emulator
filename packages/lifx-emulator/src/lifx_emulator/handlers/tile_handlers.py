"""Tile packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import (
    DeviceStateHostFirmware,
    DeviceStateVersion,
    LightHsbk,
    TileAccelMeas,
    TileEffectParameter,
    TileEffectSettings,
    TileEffectType,
    TileStateDevice,
)

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)


class GetDeviceChainHandler(PacketHandler):
    """Handle TileGetDeviceChain (701) -> StateDeviceChain (702)."""

    PKT_TYPE = Tile.GetDeviceChain.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix:
            return []

        # Build tile device list (max 16 tiles in protocol)
        tile_devices = []
        for tile in device_state.tile_devices[:16]:
            accel_meas = TileAccelMeas(
                x=tile["accel_meas_x"], y=tile["accel_meas_y"], z=tile["accel_meas_z"]
            )
            device_version = DeviceStateVersion(
                vendor=tile["device_version_vendor"],
                product=tile["device_version_product"],
            )
            firmware = DeviceStateHostFirmware(
                build=tile["firmware_build"],
                version_minor=tile["firmware_version_minor"],
                version_major=tile["firmware_version_major"],
            )
            tile_device = TileStateDevice(
                accel_meas=accel_meas,
                user_x=tile["user_x"],
                user_y=tile["user_y"],
                width=tile["width"],
                height=tile["height"],
                device_version=device_version,
                firmware=firmware,
            )
            tile_devices.append(tile_device)

        # Pad to 16 tiles
        while len(tile_devices) < 16:
            dummy_accel = TileAccelMeas(x=0, y=0, z=0)
            dummy_version = DeviceStateVersion(vendor=0, product=0)
            dummy_firmware = DeviceStateHostFirmware(
                build=0, version_minor=0, version_major=0
            )
            dummy_tile = TileStateDevice(
                accel_meas=dummy_accel,
                user_x=0.0,
                user_y=0.0,
                width=0,
                height=0,
                device_version=dummy_version,
                firmware=dummy_firmware,
            )
            tile_devices.append(dummy_tile)

        return [
            Tile.StateDeviceChain(
                start_index=0,
                tile_devices=tile_devices,
                tile_devices_count=len(device_state.tile_devices),
            )
        ]


class SetUserPositionHandler(PacketHandler):
    """Handle TileSetUserPosition (703) - update tile position metadata."""

    PKT_TYPE = Tile.SetUserPosition.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Tile.SetUserPosition | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_matrix or not packet:
            return []

        logger.info(
            f"Tile user position set: tile_index={packet.tile_index}, "
            f"user_x={packet.user_x}, user_y={packet.user_y}"
        )

        # Update tile position if we have that tile
        if packet.tile_index < len(device_state.tile_devices):
            device_state.tile_devices[packet.tile_index]["user_x"] = packet.user_x
            device_state.tile_devices[packet.tile_index]["user_y"] = packet.user_y

        # No response packet defined for this in protocol
        return []


class Get64Handler(PacketHandler):
    """Handle TileGet64 (707) -> State64 (711)."""

    PKT_TYPE = Tile.Get64.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Tile.Get64 | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix or not packet:
            return []

        tile_index = packet.tile_index
        rect = packet.rect

        if tile_index >= len(device_state.tile_devices):
            return []

        tile = device_state.tile_devices[tile_index]
        tile_width = tile["width"]
        tile_height = tile["height"]

        # Calculate how many rows fit in 64 pixels
        rows_to_return = 64 // rect.width if rect.width > 0 else 1
        rows_to_return = min(rows_to_return, tile_height - rect.y)

        # Extract colors from the requested rectangle
        colors = []
        pixels_extracted = 0

        for row in range(rows_to_return):
            y = rect.y + row
            if y >= tile_height:
                break

            for col in range(rect.width):
                x = rect.x + col
                if x >= tile_width or pixels_extracted >= 64:
                    colors.append(
                        LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )
                    pixels_extracted += 1
                    continue

                # Calculate pixel index in flat color array
                pixel_idx = y * tile_width + x
                if pixel_idx < len(tile["colors"]):
                    colors.append(tile["colors"][pixel_idx])
                else:
                    colors.append(
                        LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )
                pixels_extracted += 1

        # Pad to exactly 64 colors
        while len(colors) < 64:
            colors.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        return [Tile.State64(tile_index=tile_index, rect=rect, colors=colors)]


class Set64Handler(PacketHandler):
    """Handle TileSet64 (715)."""

    PKT_TYPE = Tile.Set64.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Tile.Set64 | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix or not packet:
            return []

        tile_index = packet.tile_index

        if tile_index < len(device_state.tile_devices):
            # Update colors from packet
            for i, color in enumerate(packet.colors[:64]):
                if i < len(device_state.tile_devices[tile_index]["colors"]):
                    device_state.tile_devices[tile_index]["colors"][i] = color

            logger.info(
                f"Tile {tile_index} set 64 colors, duration={packet.duration}ms"
            )

        # Tiles never return a response to Set64 regardless of res_required
        # https://lan.developer.lifx.com/docs/changing-a-device#set64---packet-715
        return []


class CopyFrameBufferHandler(PacketHandler):
    """Handle TileCopyFrameBuffer (716) - copy frame buffer (no-op in emulator)."""

    PKT_TYPE = Tile.CopyFrameBuffer.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix:
            return []

        logger.debug("Tile copy frame buffer command received (no-op in emulator)")
        # In a real device, this would copy the frame buffer to display
        # In emulator, we don't need to do anything special
        return []


class GetEffectHandler(PacketHandler):
    """Handle TileGetEffect (718) -> StateTileEffect (720)."""

    PKT_TYPE = Tile.GetEffect.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix:
            return []

        # Build palette (up to 16 colors)
        palette = list(device_state.tile_effect_palette[:16])
        while len(palette) < 16:
            palette.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        # Create effect settings
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
            instanceid=0,
            type=TileEffectType(device_state.tile_effect_type),
            speed=device_state.tile_effect_speed * 1000,  # convert to milliseconds
            duration=0,  # infinite
            parameter=parameter,
            palette_count=min(len(device_state.tile_effect_palette), 16),
            palette=palette,
        )

        return [Tile.StateEffect(settings=settings)]


class SetEffectHandler(PacketHandler):
    """Handle TileSetEffect (719) -> StateTileEffect (720)."""

    PKT_TYPE = Tile.SetEffect.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Tile.SetEffect | None,
        res_required: bool,
    ) -> list[Any]:
        if not device_state.has_matrix:
            return []

        if packet:
            device_state.tile_effect_type = int(packet.settings.type)
            device_state.tile_effect_speed = (
                packet.settings.speed // 1000
            )  # convert to seconds
            device_state.tile_effect_palette = list(
                packet.settings.palette[: packet.settings.palette_count]
            )
            device_state.tile_effect_palette_count = packet.settings.palette_count

            logger.info(
                f"Tile effect set: type={packet.settings.type}, "
                f"speed={packet.settings.speed}ms, "
                f"palette_count={packet.settings.palette_count}"
            )

        if res_required:
            handler = GetEffectHandler()
            return handler.handle(device_state, None, res_required)
        return []


# List of all tile handlers for easy registration
ALL_TILE_HANDLERS = [
    GetDeviceChainHandler(),
    SetUserPositionHandler(),
    Get64Handler(),
    Set64Handler(),
    CopyFrameBufferHandler(),
    GetEffectHandler(),
    SetEffectHandler(),
]
