"""Repository interfaces and implementations for LIFX emulator.

This module defines repository abstractions following the Repository Pattern
and Dependency Inversion Principle. Repositories encapsulate data access logic
and provide a clean separation between domain logic and data persistence.
"""

from lifx_emulator.repositories.device_repository import (
    DeviceRepository,
    IDeviceRepository,
)
from lifx_emulator.repositories.storage_backend import (
    IDeviceStorageBackend,
    IScenarioStorageBackend,
)

__all__ = [
    "IDeviceRepository",
    "DeviceRepository",
    "IDeviceStorageBackend",
    "IScenarioStorageBackend",
]
