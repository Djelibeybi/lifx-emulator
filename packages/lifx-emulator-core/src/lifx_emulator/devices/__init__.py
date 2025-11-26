"""Device management module for LIFX emulator.

This module contains all device-related functionality including:
- Device core (EmulatedLifxDevice)
- Device manager (DeviceManager, IDeviceManager)
- Device states (DeviceState and related dataclasses)
- Device persistence (async file storage)
- State restoration and serialization
- Device state observers (ActivityObserver, ActivityLogger, PacketEvent, NullObserver)
"""

from lifx_emulator.devices.device import EmulatedLifxDevice
from lifx_emulator.devices.manager import DeviceManager, IDeviceManager
from lifx_emulator.devices.observers import (
    ActivityLogger,
    ActivityObserver,
    NullObserver,
    PacketEvent,
)
from lifx_emulator.devices.persistence import (
    DEFAULT_STORAGE_DIR,
    DevicePersistenceAsyncFile,
)
from lifx_emulator.devices.states import DeviceState

__all__ = [
    "EmulatedLifxDevice",
    "DeviceManager",
    "IDeviceManager",
    "DeviceState",
    "DevicePersistenceAsyncFile",
    "DEFAULT_STORAGE_DIR",
    "ActivityObserver",
    "ActivityLogger",
    "PacketEvent",
    "NullObserver",
]
