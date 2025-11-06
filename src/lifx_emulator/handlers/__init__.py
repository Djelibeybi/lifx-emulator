"""Packet handler infrastructure using Strategy pattern.

This module provides the base classes and registry for handling LIFX protocol packets.
Each packet type has a dedicated handler class that implements the business logic.
"""

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.handlers.device_handlers import ALL_DEVICE_HANDLERS
from lifx_emulator.handlers.light_handlers import ALL_LIGHT_HANDLERS
from lifx_emulator.handlers.multizone_handlers import ALL_MULTIZONE_HANDLERS
from lifx_emulator.handlers.registry import HandlerRegistry
from lifx_emulator.handlers.tile_handlers import ALL_TILE_HANDLERS

__all__ = [
    "PacketHandler",
    "HandlerRegistry",
    "ALL_DEVICE_HANDLERS",
    "ALL_LIGHT_HANDLERS",
    "ALL_MULTIZONE_HANDLERS",
    "ALL_TILE_HANDLERS",
    "create_default_registry",
]


def create_default_registry() -> HandlerRegistry:
    """Create a handler registry with all default handlers registered.

    Returns:
        HandlerRegistry with all built-in handlers
    """
    registry = HandlerRegistry()

    # Register all handler categories
    registry.register_all(ALL_DEVICE_HANDLERS)
    registry.register_all(ALL_LIGHT_HANDLERS)
    registry.register_all(ALL_MULTIZONE_HANDLERS)
    registry.register_all(ALL_TILE_HANDLERS)

    return registry
