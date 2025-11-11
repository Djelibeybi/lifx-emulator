"""Device management business logic service.

Separates API handlers from server operations, providing a clean service layer
for device CRUD operations. Applies Single Responsibility Principle by keeping
business logic separate from HTTP concerns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator.api.mappers import DeviceMapper
from lifx_emulator.api.models import DeviceCreateRequest, DeviceInfo
from lifx_emulator.factories import create_device

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
