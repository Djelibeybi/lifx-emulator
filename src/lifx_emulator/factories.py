"""Factory functions for creating emulated LIFX devices."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from lifx_emulator.device import DeviceState, EmulatedLifxDevice
from lifx_emulator.device_states import (
    CoreDeviceState,
    GroupState,
    HevState,
    InfraredState,
    LocationState,
    MatrixState,
    MultiZoneState,
    NetworkState,
    WaveformState,
)
from lifx_emulator.products.registry import ProductInfo, get_product
from lifx_emulator.products.specs import (
    get_default_tile_count,
    get_default_zone_count,
    get_tile_dimensions,
)
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.state_restorer import StateRestorer

if TYPE_CHECKING:
    from lifx_emulator.async_storage import AsyncDeviceStorage
    from lifx_emulator.scenario_manager import HierarchicalScenarioManager


def create_color_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
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
    storage: AsyncDeviceStorage | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice:
    """Create a device for any LIFX product using the product registry.

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
    product_info: ProductInfo | None = get_product(product_id)
    if product_info is None:
        raise ValueError(f"Unknown product ID: {product_id}")

    # Generate serial if not provided
    if not serial:
        # Use different prefixes for product types for easier identification
        if product_info.has_matrix:
            prefix = "d073d9"  # Tiles
        elif product_info.has_multizone:
            prefix = "d073d8"  # Strips/Beams
        elif product_info.has_hev:
            prefix = "d073d7"  # HEV
        elif product_info.has_infrared:
            prefix = "d073d6"  # Infrared
        else:
            prefix = "d073d5"  # Regular lights
        serial = f"{prefix}{random.randint(100000, 999999):06x}"  # nosec

    # Determine zone count for multizone devices
    if product_info.has_multizone and zone_count is None:
        # Try to get default from specs first
        zone_count = get_default_zone_count(product_id) or 16

    # Determine tile configuration for matrix devices
    if product_info.has_matrix:
        # Get tile dimensions from specs (always use specs for dimensions)
        tile_dims = get_tile_dimensions(product_id)
        if tile_dims:
            tile_width, tile_height = tile_dims
        else:
            # Fallback to standard 8x8 tiles
            if tile_width is None:
                tile_width = 8
            if tile_height is None:
                tile_height = 8

        # Get default tile count from specs
        if tile_count is None:
            specs_tile_count = get_default_tile_count(product_id)
            if specs_tile_count is not None:
                tile_count = specs_tile_count
            else:
                tile_count = 5  # Generic default

    # Create default color based on product type
    if (
        not product_info.has_color
        and product_info.temperature_range is not None
        and product_info.temperature_range.min == product_info.temperature_range.max
    ):
        # Brightness only light
        default_color = LightHsbk(hue=0, saturation=0, brightness=32768, kelvin=2700)
    elif (
        not product_info.has_color
        and product_info.temperature_range is not None
        and product_info.temperature_range.min != product_info.temperature_range.max
    ):
        # Color temperature adjustable light
        default_color = LightHsbk(hue=0, saturation=0, brightness=32768, kelvin=3500)
    else:
        # Color devices - use a unique hue per device type
        hue_map = {
            "matrix": 43690,  # Cyan
            "multizone": 0,  # Red
            "hev": 32768,  # Green
            "infrared": 0,  # Red
            "color": 21845,  # Orange
        }
        if product_info.has_matrix:
            hue = hue_map["matrix"]
        elif product_info.has_multizone:
            hue = hue_map["multizone"]
        elif product_info.has_hev:
            hue = hue_map["hev"]
        elif product_info.has_infrared:
            hue = hue_map["infrared"]
        else:
            hue = hue_map["color"]
        default_color = LightHsbk(
            hue=hue, saturation=65535, brightness=32768, kelvin=3500
        )

    # Get a simplified label from product name
    label = f"{product_info.name} {serial[-6:]}"

    # Determine firmware version: use extended_multizone to set default,
    # then override with explicit firmware_version if provided
    # None defaults to True (3.70), only explicit False gives 2.60
    if extended_multizone is False:
        version_major = 2
        version_minor = 60
    else:
        version_major = 3
        version_minor = 70

    # Override with explicit firmware_version if provided
    if firmware_version is not None:
        version_major, version_minor = firmware_version

    core = CoreDeviceState(
        serial=serial,
        label=label,
        power_level=65535,  # Default to on
        color=default_color,
        vendor=product_info.vendor,
        product=product_info.pid,
        version_major=version_major,
        version_minor=version_minor,
        build_timestamp=int(time.time()),
        mac_address=bytes.fromhex(serial[:12]),
    )

    # Create network, location, group, and waveform state
    network = NetworkState()
    location = LocationState()
    group = GroupState()
    waveform = WaveformState()

    # Create capability-specific state objects
    infrared_state = (
        InfraredState(infrared_brightness=16384) if product_info.has_infrared else None
    )
    hev_state = HevState() if product_info.has_hev else None

    multizone_state = None
    if product_info.has_multizone and zone_count:
        multizone_state = MultiZoneState(
            zone_count=zone_count,
            zone_colors=[],  # Will be initialized by EmulatedLifxDevice
        )

    matrix_state = None
    if product_info.has_matrix and tile_count:
        matrix_state = MatrixState(
            tile_count=tile_count,
            tile_devices=[],  # Will be initialized by EmulatedLifxDevice
            tile_width=tile_width or 8,
            tile_height=tile_height or 8,
        )

    # Determine if device supports extended multizone
    firmware_version_int = (version_major << 16) | version_minor
    has_extended_multizone = product_info.supports_extended_multizone(
        firmware_version_int
    )

    # Create composed device state
    state = DeviceState(
        core=core,
        network=network,
        location=location,
        group=group,
        waveform=waveform,
        infrared=infrared_state,
        hev=hev_state,
        multizone=multizone_state,
        matrix=matrix_state,
        has_color=product_info.has_color,
        has_infrared=product_info.has_infrared,
        has_multizone=product_info.has_multizone,
        has_extended_multizone=has_extended_multizone,
        has_matrix=product_info.has_matrix,
        has_hev=product_info.has_hev,
    )

    # Restore saved state if persistence is enabled
    if storage:
        restorer = StateRestorer(storage)
        restorer.restore_if_available(state)

    return EmulatedLifxDevice(
        state,
        storage=storage,
        scenario_manager=scenario_manager,
    )
