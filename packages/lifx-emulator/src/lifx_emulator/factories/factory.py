"""Factory functions for creating emulated LIFX devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lifx_emulator.devices import EmulatedLifxDevice
from lifx_emulator.factories.builder import DeviceBuilder
from lifx_emulator.products.registry import get_product

if TYPE_CHECKING:
    from lifx_emulator.devices import DevicePersistenceAsyncFile
    from lifx_emulator.scenarios import HierarchicalScenarioManager


def create_color_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a regular color light (LIFX Color)"""
    return create_device(
        91,
        serial=serial,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )  # LIFX Color


def create_infrared_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create an infrared-enabled light (LIFX A19 Night Vision)"""
    return create_device(
        29,
        serial=serial,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )  # LIFX A19 Night Vision


def create_hev_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create an HEV-enabled light (LIFX Clean)"""
    return create_device(
        90,
        serial=serial,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )  # LIFX Clean


def create_multizone_light(
    serial: str | None = None,
    zone_count: int | None = None,
    extended_multizone: bool = True,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a multizone light (LIFX Beam)

    Args:
        serial: Optional serial
        zone_count: Optional zone count (uses product default if not specified)
        extended_multizone: enables support for extended multizone requests
        firmware_version: Optional firmware version tuple (major, minor)
        storage: Optional storage for persistence
        scenario_manager: Optional scenario manager
    """
    return create_device(
        38,
        serial=serial,
        zone_count=zone_count,
        extended_multizone=extended_multizone,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )


def create_tile_device(
    serial: str | None = None,
    tile_count: int | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a tile device (LIFX Tile)

    Args:
        serial: Optional serial
        tile_count: Optional tile count (uses product default)
        tile_width: Optional tile width in pixels (uses product default)
        tile_height: Optional tile height in pixels (uses product default)
        firmware_version: Optional firmware version tuple (major, minor)
        storage: Optional storage for persistence
        scenario_manager: Optional scenario manager
    """
    return create_device(
        55,
        serial=serial,
        tile_count=tile_count,
        tile_width=tile_width,
        tile_height=tile_height,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )  # LIFX Tile


def create_color_temperature_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a color temperature light (LIFX Mini White to Warm).

    Variable color temperature, no RGB.
    """
    return create_device(
        50,
        serial=serial,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
    )  # LIFX Mini White to Warm


def create_device(
    product_id: int,
    serial: str | None = None,
    zone_count: int | None = None,
    extended_multizone: bool | None = None,
    tile_count: int | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a device for any LIFX product using the product registry.

    This function uses the DeviceBuilder pattern to construct devices with
    clean separation of concerns and testable components.

    Args:
        product_id: Product ID from the LIFX product registry
        serial: Optional serial (auto-generated if not provided)
        zone_count: Number of zones for multizone devices (auto-determined)
        extended_multizone: Enable extended multizone requests
        tile_count: Number of tiles for matrix devices (default: 5)
        tile_width: Width of each tile in pixels (default: 8)
        tile_height: Height of each tile in pixels (default: 8)
        firmware_version: Optional firmware version tuple (major, minor).
                         If not specified, uses 3.70 for extended_multizone
                         or 2.60 otherwise
        storage: Optional storage for persistence
        scenario_manager: Optional scenario manager for testing

    Returns:
        EmulatedLifxDevice configured for the specified product

    Raises:
        ValueError: If product_id is not found in registry

    Examples:
        >>> # Create LIFX A19 (PID 27)
        >>> device = create_device(27)
        >>> # Create LIFX Z strip (PID 32) with 24 zones
        >>> strip = create_device(32, zone_count=24)
        >>> # Create LIFX Tile (PID 55) with 10 tiles
        >>> tiles = create_device(55, tile_count=10)
    """
    # Get product info from registry
    product_info = get_product(product_id)
    if product_info is None:
        raise ValueError(f"Unknown product ID: {product_id}")

    # Build device using builder pattern
    builder = DeviceBuilder(product_info)

    if serial is not None:
        builder.with_serial(serial)

    if zone_count is not None:
        builder.with_zone_count(zone_count)

    if extended_multizone is not None:
        builder.with_extended_multizone(extended_multizone)

    if tile_count is not None:
        builder.with_tile_count(tile_count)

    if tile_width is not None and tile_height is not None:
        builder.with_tile_dimensions(tile_width, tile_height)

    if firmware_version is not None:
        builder.with_firmware_version(*firmware_version)

    if storage is not None:
        builder.with_storage(storage)

    if scenario_manager is not None:
        builder.with_scenario_manager(scenario_manager)

    return builder.build()
