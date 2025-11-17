"""Device management for LIFX emulator.

This module provides the DeviceManager class which handles device lifecycle
operations, packet routing, and device lookup. It follows the separation of
concerns principle by extracting domain logic from the network layer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lifx_emulator.devices.device import EmulatedLifxDevice
    from lifx_emulator.protocol.header import LifxHeader
    from lifx_emulator.repositories import IDeviceRepository
    from lifx_emulator.scenarios import HierarchicalScenarioManager

logger = logging.getLogger(__name__)


@runtime_checkable
class IDeviceManager(Protocol):
    """Interface for device management operations."""

    def add_device(
        self,
        device: EmulatedLifxDevice,
        scenario_manager: HierarchicalScenarioManager | None = None,
    ) -> bool:
        """Add a device to the manager.

        Args:
            device: The device to add
            scenario_manager: Optional scenario manager to share with the device

        Returns:
            True if added, False if device with same serial already exists
        """
        ...

    def remove_device(self, serial: str, storage=None) -> bool:
        """Remove a device from the manager.

        Args:
            serial: Serial number of device to remove (12 hex chars)
            storage: Optional storage backend to delete persistent state

        Returns:
            True if removed, False if device not found
        """
        ...

    def remove_all_devices(self, delete_storage: bool = False, storage=None) -> int:
        """Remove all devices from the manager.

        Args:
            delete_storage: If True, also delete persistent storage files
            storage: Storage backend to use for deletion

        Returns:
            Number of devices removed
        """
        ...

    def get_device(self, serial: str) -> EmulatedLifxDevice | None:
        """Get a device by serial number.

        Args:
            serial: Serial number (12 hex chars)

        Returns:
            Device if found, None otherwise
        """
        ...

    def get_all_devices(self) -> list[EmulatedLifxDevice]:
        """Get all devices.

        Returns:
            List of all devices
        """
        ...

    def count_devices(self) -> int:
        """Get the number of devices.

        Returns:
            Number of devices in the manager
        """
        ...

    def resolve_target_devices(self, header: LifxHeader) -> list[EmulatedLifxDevice]:
        """Resolve which devices should handle a packet based on the header.

        Args:
            header: Parsed LIFX header containing target information

        Returns:
            List of devices that should process this packet
        """
        ...

    def invalidate_all_scenario_caches(self) -> None:
        """Invalidate scenario cache for all devices.

        This should be called when scenario configuration changes to ensure
        devices reload their scenario settings from the scenario manager.
        """
        ...


class DeviceManager:
    """Manages device lifecycle, routing, and lookup operations.

    This class extracts device management logic from EmulatedLifxServer,
    providing a clean separation between domain logic and network I/O.
    It mirrors the architecture of HierarchicalScenarioManager.
    """

    def __init__(self, device_repository: IDeviceRepository):
        """Initialize the device manager.

        Args:
            device_repository: Repository for device storage and retrieval
        """
        self._device_repository = device_repository

    def add_device(
        self,
        device: EmulatedLifxDevice,
        scenario_manager: HierarchicalScenarioManager | None = None,
    ) -> bool:
        """Add a device to the manager.

        Args:
            device: The device to add
            scenario_manager: Optional scenario manager to share with the device

        Returns:
            True if added, False if device with same serial already exists
        """
        # If device is using HierarchicalScenarioManager, share the provided manager
        if scenario_manager is not None:
            from lifx_emulator.scenarios import HierarchicalScenarioManager

            if isinstance(device.scenario_manager, HierarchicalScenarioManager):
                device.scenario_manager = scenario_manager
                device.invalidate_scenario_cache()

        success = self._device_repository.add(device)
        if success:
            serial = device.state.serial
            logger.info("Added device: %s (product=%s)", serial, device.state.product)
        return success

    def remove_device(self, serial: str, storage=None) -> bool:
        """Remove a device from the manager.

        Args:
            serial: Serial number of device to remove (12 hex chars)
            storage: Optional storage backend to delete persistent state

        Returns:
            True if removed, False if device not found
        """
        success = self._device_repository.remove(serial)
        if success:
            logger.info("Removed device: %s", serial)

            # Delete persistent storage if enabled
            if storage:
                storage.delete_device_state(serial)

        return success

    def remove_all_devices(self, delete_storage: bool = False, storage=None) -> int:
        """Remove all devices from the manager.

        Args:
            delete_storage: If True, also delete persistent storage files
            storage: Storage backend to use for deletion

        Returns:
            Number of devices removed
        """
        # Clear all devices from repository
        device_count = self._device_repository.clear()
        logger.info("Removed all %s device(s)", device_count)

        # Delete persistent storage if requested
        if delete_storage and storage:
            deleted = storage.delete_all_device_states()
            logger.info("Deleted %s device state(s) from persistent storage", deleted)

        return device_count

    def get_device(self, serial: str) -> EmulatedLifxDevice | None:
        """Get a device by serial number.

        Args:
            serial: Serial number (12 hex chars)

        Returns:
            Device if found, None otherwise
        """
        return self._device_repository.get(serial)

    def get_all_devices(self) -> list[EmulatedLifxDevice]:
        """Get all devices.

        Returns:
            List of all devices
        """
        return self._device_repository.get_all()

    def count_devices(self) -> int:
        """Get the number of devices.

        Returns:
            Number of devices in the manager
        """
        return self._device_repository.count()

    def resolve_target_devices(self, header: LifxHeader) -> list[EmulatedLifxDevice]:
        """Resolve which devices should handle a packet based on the header.

        Args:
            header: Parsed LIFX header containing target information

        Returns:
            List of devices that should process this packet
        """
        target_devices = []

        if header.tagged or header.target == b"\x00" * 8:
            # Broadcast to all devices
            target_devices = self._device_repository.get_all()
        else:
            # Specific device - convert target bytes to serial string
            # Target is 8 bytes: 6-byte MAC + 2 null bytes
            target_serial = header.target[:6].hex()
            device = self._device_repository.get(target_serial)
            if device:
                target_devices = [device]

        return target_devices

    def invalidate_all_scenario_caches(self) -> None:
        """Invalidate scenario cache for all devices.

        This should be called when scenario configuration changes to ensure
        devices reload their scenario settings from the scenario manager.
        """
        for device in self._device_repository.get_all():
            device.invalidate_scenario_cache()
