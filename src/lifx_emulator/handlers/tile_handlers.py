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
    TileBufferRect,
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

        # Get64 always returns framebuffer 0 (the visible buffer)
        # regardless of which fb_index is in the request
        tile_colors = tile["colors"]

        # Calculate how many rows fit in 64 zones
        rows_to_return = 64 // rect.width if rect.width > 0 else 1
        rows_to_return = min(rows_to_return, tile_height - rect.y)

        # Extract colors from the requested rectangle
        colors = []
        zones_extracted = 0

        for row in range(rows_to_return):
            y = rect.y + row
            if y >= tile_height:
                break

            for col in range(rect.width):
                x = rect.x + col
                if x >= tile_width or zones_extracted >= 64:
                    colors.append(
                        LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )
                    zones_extracted += 1
                    continue

                # Calculate zone index in flat color array
                zone_idx = y * tile_width + x
                if zone_idx < len(tile_colors):
                    colors.append(tile_colors[zone_idx])
                else:
                    colors.append(
                        LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                    )
                zones_extracted += 1

        # Pad to exactly 64 colors
        while len(colors) < 64:
            colors.append(LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500))

        # Return with fb_index forced to 0 (visible buffer)
        return_rect = TileBufferRect(
            fb_index=0,  # Always return FB0
            x=rect.x,
            y=rect.y,
            width=rect.width,
        )
        return [Tile.State64(tile_index=tile_index, rect=return_rect, colors=colors)]


class Set64Handler(PacketHandler):
    """Handle TileSet64 (715)."""

    PKT_TYPE = Tile.Set64.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Tile.Set64 | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_matrix or not packet:
            return []

        tile_index = packet.tile_index
        fb_index = packet.rect.fb_index

        if tile_index >= len(device_state.tile_devices):
            return []

        tile = device_state.tile_devices[tile_index]
        tile_width = tile["width"]
        tile_height = tile["height"]
        rect = packet.rect

        # Determine which framebuffer to update
        if fb_index == 0:
            # Update visible framebuffer (stored in tile_devices)
            target_colors = tile["colors"]
        else:
            # Update non-visible framebuffer (stored in tile_framebuffers)
            if tile_index < len(device_state.tile_framebuffers):
                fb_storage = device_state.tile_framebuffers[tile_index]
                target_colors = fb_storage.get_framebuffer(
                    fb_index, tile_width, tile_height
                )
            else:
                logger.warning(f"Tile {tile_index} framebuffer storage not initialized")
                return []

        # Update colors in the specified rectangle
        # Calculate how many rows fit in 64 zones
        rows_to_write = 64 // rect.width if rect.width > 0 else 1
        rows_to_write = min(rows_to_write, tile_height - rect.y)

        zones_written = 0
        for row in range(rows_to_write):
            y = rect.y + row
            if y >= tile_height:
                break

            for col in range(rect.width):
                x = rect.x + col
                if x >= tile_width or zones_written >= 64:
                    zones_written += 1
                    continue

                # Calculate zone index in flat color array
                zone_idx = y * tile_width + x
                if zone_idx < len(target_colors) and zones_written < len(packet.colors):
                    target_colors[zone_idx] = packet.colors[zones_written]
                zones_written += 1

        logger.info(
            f"Tile {tile_index} FB{fb_index} set {zones_written} colors at "
            f"({rect.x},{rect.y}), duration={packet.duration}ms"
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
        if not device_state.has_matrix or not packet:
            return []

        tile_index = packet.tile_index
        if tile_index >= len(device_state.tile_devices):
            return []

        tile = device_state.tile_devices[tile_index]
        tile_width = tile["width"]
        tile_height = tile["height"]

        src_fb_index = packet.src_fb_index
        dst_fb_index = packet.dst_fb_index

        # Get source framebuffer
        if src_fb_index == 0:
            src_colors = tile["colors"]
        else:
            if tile_index < len(device_state.tile_framebuffers):
                fb_storage = device_state.tile_framebuffers[tile_index]
                src_colors = fb_storage.get_framebuffer(
                    src_fb_index, tile_width, tile_height
                )
            else:
                logger.warning(f"Tile {tile_index} framebuffer storage not initialized")
                return []

        # Get destination framebuffer
        if dst_fb_index == 0:
            dst_colors = tile["colors"]
        else:
            if tile_index < len(device_state.tile_framebuffers):
                fb_storage = device_state.tile_framebuffers[tile_index]
                dst_colors = fb_storage.get_framebuffer(
                    dst_fb_index, tile_width, tile_height
                )
            else:
                logger.warning(f"Tile {tile_index} framebuffer storage not initialized")
                return []

        # Copy the specified rectangle from source to destination
        src_x = packet.src_x
        src_y = packet.src_y
        dst_x = packet.dst_x
        dst_y = packet.dst_y
        width = packet.width
        height = packet.height

        zones_copied = 0
        for row in range(height):
            src_row = src_y + row
            dst_row = dst_y + row

            if src_row >= tile_height or dst_row >= tile_height:
                break

            for col in range(width):
                src_col = src_x + col
                dst_col = dst_x + col

                if src_col >= tile_width or dst_col >= tile_width:
                    continue

                src_idx = src_row * tile_width + src_col
                dst_idx = dst_row * tile_width + dst_col

                if src_idx < len(src_colors) and dst_idx < len(dst_colors):
                    dst_colors[dst_idx] = src_colors[src_idx]
                    zones_copied += 1

        logger.info(
            f"Tile {tile_index} copied {zones_copied} zones from "
            f"FB{src_fb_index}({src_x},{src_y}) to "
            f"FB{dst_fb_index}({dst_x},{dst_y}), "
            f"size={width}x{height}, duration={packet.duration}ms"
        )

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

        # Create effect settings with Sky parameters
        from lifx_emulator.protocol.protocol_types import TileEffectSkyType

        # Use defaults for SKY effect when values are None, otherwise use stored values
        # NOTE: Must check for None explicitly, not use 'or', because SUNRISE=0 is falsy
        effect_type = TileEffectType(device_state.tile_effect_type)
        if effect_type == TileEffectType.SKY:
            sky_type = (
                device_state.tile_effect_sky_type
                if device_state.tile_effect_sky_type is not None
                else TileEffectSkyType.CLOUDS
            )
            cloud_sat_min = (
                device_state.tile_effect_cloud_sat_min
                if device_state.tile_effect_cloud_sat_min is not None
                else 50
            )
            cloud_sat_max = (
                device_state.tile_effect_cloud_sat_max
                if device_state.tile_effect_cloud_sat_max is not None
                else 180
            )
        else:
            sky_type = device_state.tile_effect_sky_type
            cloud_sat_min = device_state.tile_effect_cloud_sat_min
            cloud_sat_max = device_state.tile_effect_cloud_sat_max

        parameter = TileEffectParameter(
            sky_type=TileEffectSkyType(sky_type),
            cloud_saturation_min=cloud_sat_min,
            cloud_saturation_max=cloud_sat_max,
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
            # Sky effect is only supported on LIFX Ceiling devices (176, 177, 201, 202)
            # running firmware 4.4 or higher
            if packet.settings.type == TileEffectType.SKY:
                ceiling_product_ids = {176, 177, 201, 202}
                is_ceiling = device_state.product in ceiling_product_ids

                # Check firmware version >= 4.4
                firmware_supported = device_state.version_major > 4 or (
                    device_state.version_major == 4 and device_state.version_minor >= 4
                )

                if not (is_ceiling and firmware_supported):
                    logger.debug(
                        f"Ignoring SKY effect request: "
                        f"product={device_state.product}, "
                        f"firmware={device_state.version_major}."
                        f"{device_state.version_minor} "
                        f"(requires Ceiling product and firmware >= 4.4)"
                    )
                    return []

            device_state.tile_effect_type = int(packet.settings.type)
            device_state.tile_effect_speed = (
                packet.settings.speed // 1000
            )  # convert to seconds
            device_state.tile_effect_palette = list(
                packet.settings.palette[: packet.settings.palette_count]
            )
            device_state.tile_effect_palette_count = packet.settings.palette_count

            # Save Sky effect parameters
            device_state.tile_effect_sky_type = int(packet.settings.parameter.sky_type)
            device_state.tile_effect_cloud_sat_min = (
                packet.settings.parameter.cloud_saturation_min
            )
            device_state.tile_effect_cloud_sat_max = (
                packet.settings.parameter.cloud_saturation_max
            )

            logger.info(
                f"Tile effect set: type={packet.settings.type}, "
                f"speed={packet.settings.speed}ms, "
                f"palette_count={packet.settings.palette_count}, "
                f"sky_type={packet.settings.parameter.sky_type}, "
                f"cloud_sat=[{packet.settings.parameter.cloud_saturation_min}, "
                f"{packet.settings.parameter.cloud_saturation_max}]"
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
