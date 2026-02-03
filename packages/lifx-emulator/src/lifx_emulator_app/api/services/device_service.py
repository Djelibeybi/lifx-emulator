"""Device management business logic service.

Separates API handlers from server operations, providing a clean service layer
for device CRUD operations. Applies Single Responsibility Principle by keeping
business logic separate from HTTP concerns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.devices import EmulatedLifxDevice
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator.factories import create_device
from lifx_emulator.protocol.protocol_types import LightHsbk

from lifx_emulator_app.api.mappers import DeviceMapper
from lifx_emulator_app.api.models import (
    ColorHsbk,
    DeviceCreateRequest,
    DeviceInfo,
    DeviceStateUpdate,
    TileColorUpdate,
)

logger = logging.getLogger(__name__)


class DeviceNotFoundError(Exception):
    """Raised when a device with the specified serial is not found."""

    def __init__(self, serial: str):
        super().__init__(f"Device {serial} not found")
        self.serial = serial


class DeviceAlreadyExistsError(Exception):
    """Raised when attempting to create a device with a serial that already exists."""

    def __init__(self, serial: str):
        super().__init__(f"Device with serial {serial} already exists")
        self.serial = serial


class DeviceCreationError(Exception):
    """Raised when device creation fails."""

    pass


class DeviceStateUpdateError(Exception):
    """Raised when a device state update fails due to capability mismatch."""

    pass


class DeviceService:
    """Service for managing emulated LIFX devices.

    Provides business logic for device operations:
    - Listing all devices
    - Getting individual device info
    - Creating new devices
    - Deleting devices
    - Clearing all devices

    **Benefits**:
    - Separates business logic from HTTP/API concerns
    - Testable without FastAPI dependencies
    - Consistent error handling
    - Single source of truth for device operations
    """

    def __init__(self, server: EmulatedLifxServer):
        """Initialize the device service.

        Args:
            server: The LIFX emulator server instance to manage devices for
        """
        self.server = server

    def list_all_devices(self) -> list[DeviceInfo]:
        """Get information about all emulated devices.

        Returns:
            List of DeviceInfo objects for all devices

        Example:
            >>> service = DeviceService(server)
            >>> devices = service.list_all_devices()
            >>> len(devices)
            3
        """
        devices = self.server.get_all_devices()
        return DeviceMapper.to_device_info_list(devices)

    def get_device_info(self, serial: str) -> DeviceInfo:
        """Get information about a specific device.

        Args:
            serial: The device serial number (12-character hex string)

        Returns:
            DeviceInfo object for the device

        Raises:
            DeviceNotFoundError: If no device with the given serial exists

        Example:
            >>> service = DeviceService(server)
            >>> info = service.get_device_info("d073d5000001")
            >>> info.label
            'LIFX Bulb'
        """
        device = self.server.get_device(serial)
        if not device:
            raise DeviceNotFoundError(serial)

        return DeviceMapper.to_device_info(device)

    def create_device(self, request: DeviceCreateRequest) -> DeviceInfo:
        """Create a new emulated device.

        Args:
            request: Device creation request with product_id and optional parameters

        Returns:
            DeviceInfo object for the newly created device

        Raises:
            DeviceCreationError: If device creation fails
            DeviceAlreadyExistsError: If a device with the serial already exists

        Example:
            >>> service = DeviceService(server)
            >>> request = DeviceCreateRequest(product_id=27, serial="d073d5000001")
            >>> info = service.create_device(request)
            >>> info.product
            27
        """
        # Build firmware version tuple if provided
        firmware_version = None
        if request.firmware_major is not None and request.firmware_minor is not None:
            firmware_version = (request.firmware_major, request.firmware_minor)

        # Create the device using the factory
        try:
            device = create_device(
                product_id=request.product_id,
                serial=request.serial,
                zone_count=request.zone_count,
                tile_count=request.tile_count,
                tile_width=request.tile_width,
                tile_height=request.tile_height,
                firmware_version=firmware_version,
                storage=self.server.storage,
                scenario_manager=self.server.scenario_manager,
            )
        except Exception as e:
            logger.error("Failed to create device: %s", e, exc_info=True)
            raise DeviceCreationError(f"Failed to create device: {e}") from e

        # Add device to server
        if not self.server.add_device(device):
            raise DeviceAlreadyExistsError(device.state.serial)

        logger.info(
            "Created device: serial=%s product=%s",
            device.state.serial,
            device.state.product,
        )

        return DeviceMapper.to_device_info(device)

    def delete_device(self, serial: str) -> None:
        """Delete an emulated device.

        Args:
            serial: The device serial number to delete

        Raises:
            DeviceNotFoundError: If no device with the given serial exists

        Example:
            >>> service = DeviceService(server)
            >>> service.delete_device("d073d5000001")
        """
        if not self.server.remove_device(serial):
            raise DeviceNotFoundError(serial)

        logger.info("Deleted device: serial=%s", serial)

    def clear_all_devices(self, delete_storage: bool = False) -> int:
        """Remove all emulated devices from the server.

        Args:
            delete_storage: If True, also delete persistent storage for devices

        Returns:
            The number of devices removed

        Example:
            >>> service = DeviceService(server)
            >>> count = service.clear_all_devices()
            >>> count
            5
        """
        count = self.server.remove_all_devices(delete_storage=delete_storage)
        logger.info("Cleared %d devices (delete_storage=%s)", count, delete_storage)
        return count

    def update_device_state(self, serial: str, update: DeviceStateUpdate) -> DeviceInfo:
        """Update the state of an existing device.

        Args:
            serial: The device serial number
            update: The state update to apply

        Returns:
            Updated DeviceInfo

        Raises:
            DeviceNotFoundError: If no device with the given serial exists
            DeviceStateUpdateError: If update is invalid for the device's capabilities
        """
        device = self.server.get_device(serial)
        if not device:
            raise DeviceNotFoundError(serial)

        if update.power_level is not None:
            device.state.power_level = update.power_level

        if update.color is not None:
            self._apply_color(device, update.color)

        if update.zone_colors is not None:
            self._apply_zone_colors(device, serial, update.zone_colors)

        if update.tile_colors is not None:
            self._apply_tile_colors(device, serial, update.tile_colors)

        return DeviceMapper.to_device_info(device)

    @staticmethod
    def _to_hsbk(c: ColorHsbk) -> LightHsbk:
        return LightHsbk(
            hue=c.hue,
            saturation=c.saturation,
            brightness=c.brightness,
            kelvin=c.kelvin,
        )

    @staticmethod
    def _fill_hsbk(hsbk: LightHsbk, count: int) -> list[LightHsbk]:
        return [
            LightHsbk(
                hue=hsbk.hue,
                saturation=hsbk.saturation,
                brightness=hsbk.brightness,
                kelvin=hsbk.kelvin,
            )
            for _ in range(count)
        ]

    @staticmethod
    def _pad_and_truncate(colors: list[LightHsbk], target: int) -> list[LightHsbk]:
        if len(colors) < target and len(colors) > 0:
            last = colors[-1]
            colors.extend(
                LightHsbk(
                    hue=last.hue,
                    saturation=last.saturation,
                    brightness=last.brightness,
                    kelvin=last.kelvin,
                )
                for _ in range(target - len(colors))
            )
        return colors[:target]

    def _apply_color(self, device: EmulatedLifxDevice, color: ColorHsbk) -> None:
        hsbk = self._to_hsbk(color)
        device.state.color = hsbk

        if device.state.has_multizone and device.state.multizone is not None:
            zone_count = device.state.multizone.zone_count
            device.state.multizone.zone_colors = self._fill_hsbk(hsbk, zone_count)

        if device.state.has_matrix and device.state.matrix is not None:
            for tile in device.state.matrix.tile_devices:
                width = tile.get("width", 8)
                height = tile.get("height", 8)
                tile["colors"] = self._fill_hsbk(hsbk, width * height)

    def _apply_zone_colors(
        self,
        device: EmulatedLifxDevice,
        serial: str,
        zone_colors: list[ColorHsbk],
    ) -> None:
        if not device.state.has_multizone or device.state.multizone is None:
            raise DeviceStateUpdateError(f"Device {serial} does not support multizone")
        zone_count = device.state.multizone.zone_count
        colors = [self._to_hsbk(c) for c in zone_colors]
        device.state.multizone.zone_colors = self._pad_and_truncate(colors, zone_count)

    def _apply_tile_colors(
        self,
        device: EmulatedLifxDevice,
        serial: str,
        tile_colors: list[TileColorUpdate],
    ) -> None:
        if not device.state.has_matrix or device.state.matrix is None:
            raise DeviceStateUpdateError(f"Device {serial} does not support matrix")
        for tile_update in tile_colors:
            idx = tile_update.tile_index
            if idx >= len(device.state.matrix.tile_devices):
                raise DeviceStateUpdateError(
                    f"Tile index {idx} out of range "
                    f"(device has {len(device.state.matrix.tile_devices)} tiles)"
                )
            tile = device.state.matrix.tile_devices[idx]
            width = tile.get("width", 8)
            height = tile.get("height", 8)
            colors = [self._to_hsbk(c) for c in tile_update.colors]
            tile["colors"] = self._pad_and_truncate(colors, width * height)

    def create_devices_bulk(
        self, requests: list[DeviceCreateRequest]
    ) -> list[DeviceInfo]:
        """Create multiple devices at once.

        Args:
            requests: List of device creation requests

        Returns:
            List of DeviceInfo objects for the newly created devices

        Raises:
            DeviceAlreadyExistsError: If any serial conflicts with existing or batch
            DeviceCreationError: If any device creation fails
        """
        # Validate no duplicate serials within the batch
        serials_in_batch: list[str] = []
        for req in requests:
            if req.serial is not None:
                if req.serial in serials_in_batch:
                    raise DeviceAlreadyExistsError(req.serial)
                # Check against existing devices
                if self.server.get_device(req.serial):
                    raise DeviceAlreadyExistsError(req.serial)
                serials_in_batch.append(req.serial)

        created: list[DeviceInfo] = []
        created_serials: list[str] = []
        try:
            for req in requests:
                info = self.create_device(req)
                created.append(info)
                created_serials.append(info.serial)
        except Exception:
            # Roll back: remove already-added devices
            for serial in created_serials:
                self.server.remove_device(serial)
            raise

        return created

    def list_devices_paginated(
        self, offset: int, limit: int
    ) -> tuple[list[DeviceInfo], int]:
        """Get a paginated list of devices.

        Args:
            offset: Number of devices to skip
            limit: Maximum number of devices to return

        Returns:
            Tuple of (device info list, total device count)
        """
        devices = self.server.get_all_devices()
        total = len(devices)
        sliced = devices[offset : offset + limit]
        return DeviceMapper.to_device_info_list(sliced), total
