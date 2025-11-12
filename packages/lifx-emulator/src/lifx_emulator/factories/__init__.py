"""Device factory for creating emulated LIFX devices.

This package provides a clean, testable API for creating LIFX devices using:
- Builder pattern for flexible device construction
- Separate services for serial generation, color config, firmware config
- Product registry integration for accurate device specifications
"""

from lifx_emulator.factories.builder import DeviceBuilder
from lifx_emulator.factories.default_config import DefaultColorConfig
from lifx_emulator.factories.factory import (
    create_color_light,
    create_color_temperature_light,
    create_device,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.factories.firmware_config import FirmwareConfig
from lifx_emulator.factories.serial_generator import SerialGenerator

__all__ = [
    # Builder and helpers
    "DeviceBuilder",
    "SerialGenerator",
    "DefaultColorConfig",
    "FirmwareConfig",
    # Factory functions
    "create_device",
    "create_color_light",
    "create_infrared_light",
    "create_hev_light",
    "create_multizone_light",
    "create_tile_device",
    "create_color_temperature_light",
]
