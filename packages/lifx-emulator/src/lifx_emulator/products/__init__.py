"""LIFX product registry module.

This module provides product information and capability detection for LIFX devices.

The product registry is auto-generated from the official LIFX
products.json specification.
To update: run `uv run python -m lifx_emulator.products.generator`
"""

from .registry import (
    ProductCapability,
    ProductInfo,
    ProductRegistry,
    TemperatureRange,
    get_device_class_name,
    get_product,
    get_registry,
)

__all__ = [
    "ProductCapability",
    "ProductInfo",
    "ProductRegistry",
    "TemperatureRange",
    "get_device_class_name",
    "get_product",
    "get_registry",
]
