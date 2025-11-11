"""Mapper for converting EmulatedLifxDevice to DeviceInfo API model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.devices import EmulatedLifxDevice

from lifx_emulator.api.models import ColorHsbk, DeviceInfo


class DeviceMapper:
    """Maps domain device models to API response models.

    This mapper eliminates duplication across multiple API endpoints by
    providing a single, consistent way to convert device state to API responses.

    **Eliminates**: 150+ lines of duplicated code across list_devices(),
    get_device(), and create_device() endpoints.
    """

    @staticmethod
    def to_device_info(device: EmulatedLifxDevice) -> DeviceInfo:
        """Convert an EmulatedLifxDevice to a DeviceInfo API model.

        Args:
            device: The emulated LIFX device to convert

        Returns:
            DeviceInfo model ready for API response

        Example:
            >>> device = create_color_light(serial="d073d5000001")
            >>> info = DeviceMapper.to_device_info(device)
            >>> info.serial
            'd073d5000001'
        """
        return DeviceInfo(
            # Core identification
            serial=device.state.serial,
            label=device.state.label,
            product=device.state.product,
            vendor=device.state.vendor,
            # Power state
            power_level=device.state.power_level,
            # Capability flags
            has_color=device.state.has_color,
            has_infrared=device.state.has_infrared,
            has_multizone=device.state.has_multizone,
            has_extended_multizone=device.state.has_extended_multizone,
            has_matrix=device.state.has_matrix,
            has_hev=device.state.has_hev,
            # Zone/tile counts
            zone_count=device.state.multizone.zone_count
            if device.state.multizone is not None
            else 0,
            tile_count=device.state.matrix.tile_count
            if device.state.matrix is not None
            else 0,
            # Color state (if applicable)
            color=ColorHsbk(
                hue=device.state.color.hue,
                saturation=device.state.color.saturation,
                brightness=device.state.color.brightness,
                kelvin=device.state.color.kelvin,
            )
            if device.state.has_color
            else None,
            # Multizone colors (if applicable)
            zone_colors=[
                ColorHsbk(
                    hue=c.hue,
                    saturation=c.saturation,
                    brightness=c.brightness,
                    kelvin=c.kelvin,
                )
                for c in device.state.multizone.zone_colors
            ]
            if device.state.multizone is not None
            else [],
            # Matrix/tile devices (if applicable)
            tile_devices=device.state.matrix.tile_devices
            if device.state.matrix is not None
            else [],
            # Firmware/version metadata
            version_major=device.state.version_major,
            version_minor=device.state.version_minor,
            build_timestamp=device.state.build_timestamp,
            # Location/group metadata
            group_label=device.state.group.group_label,
            location_label=device.state.location.location_label,
            # Runtime metadata
            uptime_ns=device.state.uptime_ns,
            wifi_signal=device.state.wifi_signal,
        )

    @staticmethod
    def to_device_info_list(devices: list[EmulatedLifxDevice]) -> list[DeviceInfo]:
        """Convert a list of EmulatedLifxDevice to DeviceInfo API models.

        Args:
            devices: List of emulated LIFX devices to convert

        Returns:
            List of DeviceInfo models ready for API response

        Example:
            >>> devices = [create_color_light(), create_multizone_light()]
            >>> info_list = DeviceMapper.to_device_info_list(devices)
            >>> len(info_list)
            2
        """
        return [DeviceMapper.to_device_info(device) for device in devices]
