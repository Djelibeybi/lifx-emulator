"""LIFX Emulator

A comprehensive LIFX emulator for testing LIFX LAN protocol libraries.
Implements the binary UDP protocol documented at https://lan.developer.lifx.com
"""

from importlib.metadata import version as get_version

from lifx_emulator.devices import EmulatedLifxDevice
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.server import EmulatedLifxServer

__version__ = get_version("lifx_emulator")

__all__ = [
    "EmulatedLifxServer",
    "EmulatedLifxDevice",
    "create_color_light",
    "create_color_temperature_light",
    "create_hev_light",
    "create_infrared_light",
    "create_multizone_light",
    "create_tile_device",
]
