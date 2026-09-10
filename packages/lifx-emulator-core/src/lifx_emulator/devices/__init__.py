"""Device management module for LIFX emulator.

This module contains all device-related functionality including:
- Device core (EmulatedLifxDevice)
- Device manager (DeviceManager, IDeviceManager)
- Device states (DeviceState and related dataclasses)
- Device persistence (async file storage)
- State restoration and serialization
- Device state observers (ActivityObserver, ActivityLogger, PacketEvent, NullObserver)
"""

from lifx_emulator.devices.device import (
    EXTERNAL_STATE_UPDATE,
    STATE_CHANGING_PACKETS,
    EmulatedLifxDevice,
    StateChangeCallback,
    StateMutation,
)
from lifx_emulator.devices.manager import (
    DeviceAddedCallback,
    DeviceManager,
    DeviceRemovedCallback,
    IDeviceManager,
)
from lifx_emulator.devices.observers import (
    ActivityLogger,
    ActivityObserver,
    NullObserver,
    PacketEvent,
)
from lifx_emulator.devices.persistence import (
    DEFAULT_STORAGE_DIR,
    DevicePersistenceAsyncFile,
    DevicePersistenceError,
)
from lifx_emulator.devices.states import Connectivity, DeviceState

__all__ = [
    "EmulatedLifxDevice",
    "StateChangeCallback",
    "StateMutation",
    "STATE_CHANGING_PACKETS",
    "EXTERNAL_STATE_UPDATE",
    "DeviceManager",
    "DeviceAddedCallback",
    "DeviceRemovedCallback",
    "IDeviceManager",
    "Connectivity",
    "DeviceState",
    "DevicePersistenceAsyncFile",
    "DevicePersistenceError",
    "DEFAULT_STORAGE_DIR",
    "ActivityObserver",
    "ActivityLogger",
    "PacketEvent",
    "NullObserver",
]
