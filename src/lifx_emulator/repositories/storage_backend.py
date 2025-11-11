"""Storage backend interfaces for device and scenario persistence.

Provides abstraction for persistent storage operations,
following the Repository Pattern and Dependency Inversion Principle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lifx_emulator.scenarios import HierarchicalScenarioManager


@runtime_checkable
class IDeviceStorageBackend(Protocol):
    """Interface for device state persistence operations.

    This protocol defines the contract for loading and saving device state.
    Concrete implementations can use async file I/O, databases,
    or other storage backends.
    """

    async def save_device_state(self, device_state: Any) -> None:
        """Save device state to persistent storage (async).

        Args:
            device_state: DeviceState instance to persist
        """
        raise NotImplementedError

    def load_device_state(self, serial: str) -> dict | None:
        """Load device state from persistent storage (sync).

        Args:
            serial: Device serial number (12-character hex string)

        Returns:
            Dictionary with device state data, or None if not found
        """
        raise NotImplementedError

    def delete_device_state(self, serial: str) -> bool:
        """Delete device state from persistent storage.

        Args:
            serial: Device serial number

        Returns:
            True if state was deleted, False if not found
        """
        raise NotImplementedError

    def list_devices(self) -> list[str]:
        """List all device serials with saved state.

        Returns:
            List of serial numbers
        """
        raise NotImplementedError

    def delete_all_device_states(self) -> int:
        """Delete all device states from persistent storage.

        Returns:
            Number of device states deleted
        """
        raise NotImplementedError

    async def shutdown(self) -> None:
        """Gracefully shutdown storage backend, flushing pending writes."""
        raise NotImplementedError


@runtime_checkable
class IScenarioStorageBackend(Protocol):
    """Interface for scenario configuration persistence operations.

    This protocol defines the contract for loading and saving scenario configurations.
    Concrete implementations can use async file I/O, databases,
    or other storage backends.
    """

    async def load(self) -> HierarchicalScenarioManager:
        """Load scenario configuration from persistent storage (async).

        Returns:
            Scenario manager with loaded configuration, or default manager
            if no saved data
        """
        raise NotImplementedError

    async def save(self, manager: HierarchicalScenarioManager) -> None:
        """Save scenario configuration to persistent storage (async).

        Args:
            manager: Scenario manager whose configuration should be saved
        """
        raise NotImplementedError

    async def delete(self) -> bool:
        """Delete scenario configuration from persistent storage (async).

        Returns:
            True if configuration was deleted, False if it didn't exist
        """
        raise NotImplementedError
