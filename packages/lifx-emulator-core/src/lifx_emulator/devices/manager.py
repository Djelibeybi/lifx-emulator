"""Device management for LIFX emulator.

This module provides the DeviceManager class which handles device lifecycle
operations, packet routing, and device lookup. It follows the separation of
concerns principle by extracting domain logic from the network layer.
"""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from lifx_emulator.devices.states import Connectivity
from lifx_emulator.scenarios import HierarchicalScenarioManager

if TYPE_CHECKING:
    from lifx_emulator.devices.device import EmulatedLifxDevice
    from lifx_emulator.protocol.header import LifxHeader
    from lifx_emulator.repositories import IDeviceRepository

logger = logging.getLogger(__name__)

# Type aliases for device lifecycle callbacks
DeviceAddedCallback = Callable[["EmulatedLifxDevice"], None]
DeviceRemovedCallback = Callable[[str], None]


@dataclass(frozen=True, eq=False)
class DeviceLifecycleListener:
    """Independent synchronous observers of committed membership changes."""

    on_added: DeviceAddedCallback | None = None
    on_removed: DeviceRemovedCallback | None = None


@runtime_checkable
class IDeviceLifecycleSource(Protocol):
    """Optional capability for non-displacing membership subscriptions."""

    def add_lifecycle_listener(self, listener: DeviceLifecycleListener) -> None:
        """Subscribe by object identity."""
        ...

    def remove_lifecycle_listener(self, listener: DeviceLifecycleListener) -> None:
        """Unsubscribe idempotently."""
        ...


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

    async def remove_device(self, serial: str, storage=None) -> bool:
        """Remove a device from the manager.

        Args:
            serial: Serial number of device to remove (12 hex chars)
            storage: Optional storage backend to delete persistent state

        Returns:
            True if removed, False if device not found
        """
        ...

    async def remove_all_devices(
        self, delete_storage: bool = False, storage=None
    ) -> int:
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

    def resolve_target_devices(
        self,
        header: LifxHeader,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[EmulatedLifxDevice]:
        """Resolve which devices should handle a packet based on the header.

        Args:
            header: Parsed LIFX header containing target information
            family: Address family on which the packet arrived

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

    Supports optional callbacks for device lifecycle events, allowing
    external systems (like WebSocket managers) to be notified of changes.
    """

    def __init__(
        self,
        device_repository: IDeviceRepository,
        on_device_added: DeviceAddedCallback | None = None,
        on_device_removed: DeviceRemovedCallback | None = None,
    ):
        """Initialize the device manager.

        Args:
            device_repository: Repository for device storage and retrieval
            on_device_added: Optional callback invoked when a device is added
            on_device_removed: Optional callback invoked when a device is removed
        """
        self._device_repository = device_repository
        self._serial_lock = threading.Lock()
        self._lifecycle_listeners: list[DeviceLifecycleListener] = []
        self.on_device_added = on_device_added
        self.on_device_removed = on_device_removed

    def add_lifecycle_listener(self, listener: DeviceLifecycleListener) -> None:
        """Register once by identity, retaining deterministic insertion order."""
        if not any(item is listener for item in self._lifecycle_listeners):
            self._lifecycle_listeners.append(listener)

    def remove_lifecycle_listener(self, listener: DeviceLifecycleListener) -> None:
        """Remove only the specified subscription, with idempotent cleanup."""
        self._lifecycle_listeners[:] = [
            item for item in self._lifecycle_listeners if item is not listener
        ]

    def _notify_added(self, device: EmulatedLifxDevice) -> None:
        listeners = tuple(self._lifecycle_listeners)
        callbacks = (self.on_device_added, *(item.on_added for item in listeners))
        for callback in callbacks:
            if callback is not None:
                try:
                    callback(device)
                except Exception:
                    logger.exception(
                        "Error in on_device_added callback for %s", device.state.serial
                    )

    def _notify_removed(self, serial: str) -> None:
        listeners = tuple(self._lifecycle_listeners)
        callbacks = (self.on_device_removed, *(item.on_removed for item in listeners))
        for callback in callbacks:
            if callback is not None:
                try:
                    callback(serial)
                except Exception:
                    logger.exception(
                        "Error in on_device_removed callback for %s", serial
                    )

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
            if isinstance(device.scenario_manager, HierarchicalScenarioManager):
                device.scenario_manager = scenario_manager
                device.invalidate_scenario_cache()

        with self._serial_lock:
            success = self._device_repository.add(device)
        if success:
            serial = device.state.serial
            device.activate_persistence()
            logger.info("Added device: %s (product=%s)", serial, device.state.product)
            self._notify_added(device)
        return success

    async def remove_device(self, serial: str, storage=None) -> bool:
        """Remove a device from the manager.

        Args:
            serial: Serial number of device to remove (12 hex chars)
            storage: Optional storage backend to delete persistent state

        Returns:
            True if removed, False if device not found
        """
        device = self._device_repository.get(serial)
        if device is None:
            return False

        try:
            await device.close()
            if storage:
                deleted = await storage.delete_device_state(serial)
                if not isinstance(deleted, bool):
                    raise TypeError(
                        "delete_device_state() must return bool, "
                        f"got {type(deleted).__name__}"
                    )
        except BaseException:
            if self._device_repository.get(serial) is device:
                device.reopen()
            raise

        success = self._device_repository.remove(serial)
        if not success:
            device.reopen()
            return False

        logger.info("Removed device: %s", serial)

        self._notify_removed(serial)

        return success

    async def remove_all_devices(
        self, delete_storage: bool = False, storage=None
    ) -> int:
        """Remove all devices from the manager.

        Args:
            delete_storage: If True, also delete persistent storage files
            storage: Storage backend to use for deletion

        Returns:
            Number of devices removed
        """
        devices = self._device_repository.get_all()
        serials = [device.state.serial for device in devices]
        closing_devices = []

        try:
            for device in devices:
                closing_devices.append(device)
                await device.close()

            if delete_storage and storage:
                deleted = await storage.delete_device_states(serials)
                if type(deleted) is not int:
                    raise TypeError(
                        "delete_device_states() must return int, "
                        f"got {type(deleted).__name__}"
                    )
                logger.info(
                    "Deleted %s device state(s) from persistent storage", deleted
                )
        except BaseException:
            for device in closing_devices:
                serial = device.state.serial
                if self._device_repository.get(serial) is device:
                    device.reopen()
            raise

        removed = [
            serial for serial in serials if self._device_repository.remove(serial)
        ]
        device_count = len(removed)
        logger.info("Removed all %s device(s)", device_count)
        for serial in removed:
            self._notify_removed(serial)

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

    def resolve_target_devices(
        self,
        header: LifxHeader,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[EmulatedLifxDevice]:
        """Resolve which devices should handle a packet based on the header.

        Args:
            header: Parsed LIFX header containing target information
            family: Address family on which the packet arrived

        Returns:
            List of devices that should process this packet
        """
        is_broadcast = header.tagged or header.target == b"\x00" * 8
        target_serial = None if is_broadcast else header.target[:6].hex()
        target_devices = []

        for device in self._device_repository.get_all():
            if device.state.connectivity is Connectivity.THREAD:
                rejection_reason = self._thread_rejection_reason(
                    device.state.serial,
                    header,
                    family,
                )
                if rejection_reason is not None:
                    logger.debug(
                        "Filtered Thread device %s: %s",
                        device.state.serial,
                        rejection_reason,
                    )
                    continue

                target_devices.append(device)
                continue

            if is_broadcast or device.state.serial == target_serial:
                target_devices.append(device)

        return target_devices

    @staticmethod
    def _thread_rejection_reason(
        serial: str,
        header: LifxHeader,
        family: socket.AddressFamily,
    ) -> str | None:
        """Return why a Thread device is ineligible, or ``None`` if eligible."""
        if family != socket.AF_INET6:
            family_name = "IPv4" if family == socket.AF_INET else str(family)
            return f"received over {family_name}; Thread requires IPv6"
        if header.tagged:
            return "tagged request is broadcast; Thread requires untagged unicast"
        if header.target == b"\x00" * 8:
            return "all-zero target is broadcast; Thread requires exact unicast"

        target_serial = header.target[:6].hex()
        if target_serial != serial:
            return f"target {target_serial} does not match Thread serial {serial}"
        return None

    def invalidate_all_scenario_caches(self) -> None:
        """Invalidate scenario cache for all devices.

        This should be called when scenario configuration changes to ensure
        devices reload their scenario settings from the scenario manager.
        """
        for device in self._device_repository.get_all():
            device.invalidate_scenario_cache()
