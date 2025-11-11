"""Device repository interface and implementation.

Provides abstraction for device storage and retrieval operations,
following the Repository Pattern and Dependency Inversion Principle.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lifx_emulator.devices import EmulatedLifxDevice


@runtime_checkable
class IDeviceRepository(Protocol):
    """Interface for device repository operations.

    This protocol defines the contract for managing device storage and retrieval.
    Concrete implementations can use in-memory storage, databases, or other backends.
    """

    def add(self, device: EmulatedLifxDevice) -> bool:
        """Add a device to the repository.

        Args:
            device: Device to add

        Returns:
            True if device was added, False if device with same serial already exists
        """
        ...

    def remove(self, serial: str) -> bool:
        """Remove a device from the repository.

        Args:
            serial: Serial number of device to remove

        Returns:
            True if device was removed, False if not found
        """
        ...

    def get(self, serial: str) -> EmulatedLifxDevice | None:
        """Get a device by serial number.

        Args:
            serial: Serial number to look up

        Returns:
            Device if found, None otherwise
        """
        ...

    def get_all(self) -> list[EmulatedLifxDevice]:
        """Get all devices.

        Returns:
            List of all devices in the repository
        """
        ...

    def clear(self) -> int:
        """Remove all devices from the repository.

        Returns:
            Number of devices removed
        """
        ...

    def count(self) -> int:
        """Get the number of devices in the repository.

        Returns:
            Number of devices
        """
        ...


class DeviceRepository:
    """In-memory device repository implementation.

    Stores devices in a dictionary keyed by serial number.
    This is the default implementation used by EmulatedLifxServer.
    """

    def __init__(self) -> None:
        """Initialize empty device repository."""
        self._devices: dict[str, EmulatedLifxDevice] = {}

    def add(self, device: EmulatedLifxDevice) -> bool:
        """Add a device to the repository.

        Args:
            device: Device to add

        Returns:
            True if device was added, False if device with same serial already exists
        """
        serial = device.state.serial
        if serial in self._devices:
            return False
        self._devices[serial] = device
        return True

    def remove(self, serial: str) -> bool:
        """Remove a device from the repository.

        Args:
            serial: Serial number of device to remove

        Returns:
            True if device was removed, False if not found
        """
        if serial in self._devices:
            del self._devices[serial]
            return True
        return False

    def get(self, serial: str) -> EmulatedLifxDevice | None:
        """Get a device by serial number.

        Args:
            serial: Serial number to look up

        Returns:
            Device if found, None otherwise
        """
        return self._devices.get(serial)

    def get_all(self) -> list[EmulatedLifxDevice]:
        """Get all devices.

        Returns:
            List of all devices in the repository
        """
        return list(self._devices.values())

    def clear(self) -> int:
        """Remove all devices from the repository.

        Returns:
            Number of devices removed
        """
        count = len(self._devices)
        self._devices.clear()
        return count

    def count(self) -> int:
        """Get the number of devices in the repository.

        Returns:
            Number of devices
        """
        return len(self._devices)
