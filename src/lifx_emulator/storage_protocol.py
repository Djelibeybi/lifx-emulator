"""Storage protocol definition for device state persistence.

This module defines the common interface that all storage implementations
must follow, enabling polymorphic use and easier testing.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageProtocol(Protocol):
    """Protocol defining the interface for device state storage.

    Both synchronous (DeviceStorage) and asynchronous (AsyncDeviceStorage)
    implementations must provide these methods.

    The protocol allows for polymorphic usage and dependency injection,
    improving testability and adherence to SOLID principles.
    """

    def load_device_state(self, serial: str) -> dict[str, Any] | None:
        """Load device state from persistent storage.

        This method is synchronous in both implementations because loading
        primarily happens at device initialization where blocking is acceptable.

        Args:
            serial: Device serial number

        Returns:
            Dictionary with device state, or None if not found
        """
        ...

    def delete_device_state(self, serial: str) -> None:
        """Delete device state from persistent storage.

        This method is synchronous because deletion is rare and blocking
        is acceptable for this operation.

        Args:
            serial: Device serial number
        """
        ...

    def delete_all_device_states(self) -> int:
        """Delete all device states from persistent storage.

        This method is synchronous because it's typically used for cleanup
        operations where blocking is acceptable.

        Returns:
            Number of devices deleted
        """
        ...

    def list_devices(self) -> list[str]:
        """List all devices with saved state.

        This method is synchronous because listing is typically used for
        administrative/query operations where blocking is acceptable.

        Returns:
            List of device serial numbers
        """
        ...


@runtime_checkable
class AsyncStorageProtocol(StorageProtocol, Protocol):
    """Extended protocol for asynchronous storage implementations.

    Adds async save method for high-performance non-blocking writes.
    """

    async def save_device_state(self, device_state: Any) -> None:
        """Queue device state for saving (non-blocking).

        Args:
            device_state: DeviceState instance to persist
        """
        ...


@runtime_checkable
class SyncStorageProtocol(StorageProtocol, Protocol):
    """Extended protocol for synchronous storage implementations.

    Adds synchronous save method for simple blocking writes.
    """

    def save_device_state(self, device_state: Any) -> None:
        """Save device state to persistent storage (blocking).

        Args:
            device_state: DeviceState instance to persist
        """
        ...
