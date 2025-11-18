# Factory Functions

Factory functions provide the easiest way to create emulated LIFX devices with sensible defaults.

## Overview

All factory functions return an `EmulatedLifxDevice` instance configured for a specific product type. They automatically load product-specific defaults (like zone counts and tile dimensions) from the product registry.

Device factory for creating emulated LIFX devices.

This package provides a clean, testable API for creating LIFX devices using:

- Builder pattern for flexible device construction
- Separate services for serial generation, color config, firmware config
- Product registry integration for accurate device specifications

| FUNCTION                         | DESCRIPTION                                                      |
| -------------------------------- | ---------------------------------------------------------------- |
| `create_color_light`             | Create a regular color light (LIFX Color)                        |
| `create_color_temperature_light` | Create a color temperature light (LIFX Mini White to Warm).      |
| `create_infrared_light`          | Create an infrared-enabled light (LIFX A19 Night Vision)         |
| `create_hev_light`               | Create an HEV-enabled light (LIFX Clean)                         |
| `create_multizone_light`         | Create a multizone light (LIFX Beam)                             |
| `create_tile_device`             | Create a tile device (LIFX Tile)                                 |
| `create_device`                  | Create a device for any LIFX product using the product registry. |

## Functions

### create_color_light

```python
create_color_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create a regular color light (LIFX Color)

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
```

### create_color_temperature_light

```python
create_color_temperature_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create a color temperature light (LIFX Mini White to Warm).

Variable color temperature, no RGB.

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
```

### create_infrared_light

```python
create_infrared_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create an infrared-enabled light (LIFX A19 Night Vision)

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
```

### create_hev_light

```python
create_hev_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create an HEV-enabled light (LIFX Clean)

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
```

### create_multizone_light

```python
create_multizone_light(
    serial: str | None = None,
    zone_count: int | None = None,
    extended_multizone: bool = True,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create a multizone light (LIFX Beam)

| PARAMETER            | DESCRIPTION                                                                          |
| -------------------- | ------------------------------------------------------------------------------------ |
| `serial`             | Optional serial **TYPE:** \`str                                                      |
| `zone_count`         | Optional zone count (uses product default if not specified) **TYPE:** \`int          |
| `extended_multizone` | enables support for extended multizone requests **TYPE:** `bool` **DEFAULT:** `True` |
| `firmware_version`   | Optional firmware version tuple (major, minor) **TYPE:** \`tuple[int, int]           |
| `storage`            | Optional storage for persistence **TYPE:** \`DevicePersistenceAsyncFile              |
| `scenario_manager`   | Optional scenario manager **TYPE:** \`HierarchicalScenarioManager                    |

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
```

### create_tile_device

```python
create_tile_device(
    serial: str | None = None,
    tile_count: int | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
) -> EmulatedLifxDevice
```

Create a tile device (LIFX Tile)

| PARAMETER          | DESCRIPTION                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `serial`           | Optional serial **TYPE:** \`str                                            |
| `tile_count`       | Optional tile count (uses product default) **TYPE:** \`int                 |
| `tile_width`       | Optional tile width in zones (uses product default) **TYPE:** \`int        |
| `tile_height`      | Optional tile height in zones (uses product default) **TYPE:** \`int       |
| `firmware_version` | Optional firmware version tuple (major, minor) **TYPE:** \`tuple[int, int] |
| `storage`          | Optional storage for persistence **TYPE:** \`DevicePersistenceAsyncFile    |
| `scenario_manager` | Optional scenario manager **TYPE:** \`HierarchicalScenarioManager          |

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
        tile_width: Optional tile width in zones (uses product default)
        tile_height: Optional tile height in zones (uses product default)
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
```

### create_device

```python
create_device(
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
) -> EmulatedLifxDevice
```

Create a device for any LIFX product using the product registry.

This function uses the DeviceBuilder pattern to construct devices with clean separation of concerns and testable components.

| PARAMETER            | DESCRIPTION                                                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `product_id`         | Product ID from the LIFX product registry **TYPE:** `int`                                                                                        |
| `serial`             | Optional serial (auto-generated if not provided) **TYPE:** \`str                                                                                 |
| `zone_count`         | Number of zones for multizone devices (auto-determined) **TYPE:** \`int                                                                          |
| `extended_multizone` | Enable extended multizone requests **TYPE:** \`bool                                                                                              |
| `tile_count`         | Number of tiles for matrix devices (default: 5) **TYPE:** \`int                                                                                  |
| `tile_width`         | Width of each tile in zones (default: 8) **TYPE:** \`int                                                                                         |
| `tile_height`        | Height of each tile in zones (default: 8) **TYPE:** \`int                                                                                        |
| `firmware_version`   | Optional firmware version tuple (major, minor). If not specified, uses 3.70 for extended_multizone or 2.60 otherwise **TYPE:** \`tuple[int, int] |
| `storage`            | Optional storage for persistence **TYPE:** \`DevicePersistenceAsyncFile                                                                          |
| `scenario_manager`   | Optional scenario manager for testing **TYPE:** \`HierarchicalScenarioManager                                                                    |

| RETURNS              | DESCRIPTION                                             |
| -------------------- | ------------------------------------------------------- |
| `EmulatedLifxDevice` | EmulatedLifxDevice configured for the specified product |

| RAISES       | DESCRIPTION                            |
| ------------ | -------------------------------------- |
| `ValueError` | If product_id is not found in registry |

Examples:

```pycon
>>> # Create LIFX A19 (PID 27)
>>> device = create_device(27)
>>> # Create LIFX Z strip (PID 32) with 24 zones
>>> strip = create_device(32, zone_count=24)
>>> # Create LIFX Tile (PID 55) with 10 tiles
>>> tiles = create_device(55, tile_count=10)
```

Source code in `src/lifx_emulator/factories/factory.py`

```python
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
        tile_width: Width of each tile in zones (default: 8)
        tile_height: Height of each tile in zones (default: 8)
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
```

## Usage Examples

### Color Light

Create a standard RGB color light (LIFX A19):

```python
from lifx_emulator import create_color_light

# Auto-generated serial
device = create_color_light()

# Custom serial
device = create_color_light("d073d5000001")

# Access state
print(f"Label: {device.state.label}")
print(f"Product: {device.state.product}")  # 27 (LIFX A19)
print(f"Has color: {device.state.has_color}")  # True
```

### Color Temperature Light

Create a white light with variable color temperature:

```python
from lifx_emulator import create_color_temperature_light

device = create_color_temperature_light("d073d5000001")

print(f"Has color: {device.state.has_color}")  # False
print(f"Product: {device.state.product}")  # 50 (LIFX Mini White to Warm)
```

### Infrared Light

Create a light with infrared capability:

```python
from lifx_emulator import create_infrared_light

device = create_infrared_light("d073d5000002")

print(f"Has infrared: {device.state.has_infrared}")  # True
print(f"Product: {device.state.product}")  # 29 (LIFX A19 Night Vision)
print(f"IR brightness: {device.state.infrared_brightness}")  # 16384 (25%)
```

### HEV Light

Create a light with HEV cleaning capability:

```python
from lifx_emulator import create_hev_light

device = create_hev_light("d073d5000003")

print(f"Has HEV: {device.state.has_hev}")  # True
print(f"Product: {device.state.product}")  # 90 (LIFX Clean)
print(f"HEV cycle duration: {device.state.hev_cycle_duration_s}")  # 7200 (2 hours)
```

### Multizone Light

Create a linear multizone device (strip or beam):

```python
from lifx_emulator import create_multizone_light

# Standard LIFX Z with default 16 zones
strip = create_multizone_light("d073d8000001")

# Custom zone count
strip_custom = create_multizone_light("d073d8000002", zone_count=24)

# Extended multizone (LIFX Beam) with default 80 zones
beam = create_multizone_light("d073d8000003", extended_multizone=True)

# Custom extended multizone
beam_custom = create_multizone_light(
    "d073d8000004",
    zone_count=60,
    extended_multizone=True
)

print(f"Strip zones: {strip.state.zone_count}")  # 16
print(f"Beam zones: {beam.state.zone_count}")   # 80
print(f"Strip product: {strip.state.product}")  # 32 (LIFX Z)
print(f"Beam product: {beam.state.product}")    # 38 (LIFX Beam)
```

### Tile Device

Create a matrix tile device:

```python
from lifx_emulator import create_tile_device

# Default configuration (5 tiles of 8x8)
tiles = create_tile_device("d073d9000001")

# Custom tile count
tiles_custom = create_tile_device("d073d9000002", tile_count=10)

# Custom tile dimensions (e.g., 16x8 with >64 zones per tile)
large_tile = create_tile_device(
    "d073d9000003",
    tile_count=1,
    tile_width=16,
    tile_height=8
)

print(f"Tile count: {tiles.state.tile_count}")      # 5
print(f"Tile width: {tiles.state.tile_width}")      # 8
print(f"Tile height: {tiles.state.tile_height}")    # 8
print(f"Product: {tiles.state.product}")            # 55 (LIFX Tile)

# Tiles with >64 zones require multiple Get64 requests (16x8 = 128 zones)
print(f"Large tile zones: {large_tile.state.tile_width * large_tile.state.tile_height}")  # 128
```

### Generic Device Creation

Create any device by product ID:

```python
from lifx_emulator.factories import create_device

# LIFX A19 (product ID 27)
a19 = create_device(27, serial="d073d5000001")

# LIFX Z (product ID 32) with custom zones
z_strip = create_device(32, serial="d073d8000001", zone_count=24)

# LIFX Tile (product ID 55) with custom configuration
tiles = create_device(
    55,
    serial="d073d9000001",
    tile_count=10,
    tile_width=8,
    tile_height=8
)

# LIFX Candle (product ID 57) - loads 5x6 dimensions from product defaults
candle = create_device(57, serial="d073d9000002")
print(f"Candle size: {candle.state.tile_width}x{candle.state.tile_height}")  # 5x6
```

## Serial Format

Serials must be 12 hex characters (6 bytes):

```python
# Valid formats
device = create_color_light("d073d5000001")  # Serial with LIFX prefix ("d073d5")
device = create_color_light("cafe00abcdef")  # Serial with custom prefix
device = create_color_light()                # Auto-generate serial

# Invalid (will raise error)
device = create_color_light("123")           # Too short
device = create_color_light("xyz")           # Not hex
```

Auto-generated serials use prefixes based on device type:

- `d073d5` - Regular lights
- `d073d6` - Infrared lights
- `d073d7` - HEV lights
- `d073d8` - Multizone strips/beams
- `d073d9` - Matrix tiles

## Product Defaults

When parameters like `zone_count` or `tile_count` are not specified, the factory functions automatically load defaults from the product registry's specs system:

```python
# Uses product default (16 zones for LIFX Z)
strip = create_multizone_light("d073d8000001")

# Uses product default (80 zones for LIFX Beam)
beam = create_multizone_light("d073d8000002", extended_multizone=True)

# Uses product default (5 tiles for LIFX Tile)
tiles = create_tile_device("d073d9000001")

# Uses product default (5x6 for LIFX Candle)
candle = create_device(57, serial="d073d9000002")
```

See [Product Registry](../products/) for all product definitions and defaults.

## Device State Access

After creation, access device state:

```python
device = create_color_light("d073d5000001")

# Device identity
print(device.state.serial)          # "d073d5000001"
print(device.state.label)           # "A19 d073d5"
print(device.state.vendor)          # 1 (LIFX)
print(device.state.product)         # 27 (LIFX A19)

# Device capabilities
print(device.state.has_color)       # True
print(device.state.has_infrared)    # False
print(device.state.has_multizone)   # False
print(device.state.has_matrix)      # False
print(device.state.has_hev)         # False

# Light state
print(device.state.power_level)     # 65535 (on)
print(device.state.color)           # LightHsbk(...)
print(device.state.port)            # 56700 (default)

# Firmware version
print(device.state.version_major)   # 2
print(device.state.version_minor)   # 80
```

## Multiple Devices

Create multiple devices for testing:

```python
from lifx_emulator import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
    EmulatedLifxServer,
)

# Create a diverse set of devices
devices = [
    create_color_light("d073d5000001"),
    create_color_light("d073d5000002"),
    create_multizone_light("d073d8000001", zone_count=16),
    create_multizone_light("d073d8000002", zone_count=82, extended_multizone=True),
    create_tile_device("d073d9000001", tile_count=5),
]

# Start server with all devices
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
await server.start()
```

## Advanced Options

### Persistent Storage

Devices can automatically persist state across restarts:

```python
from lifx_emulator import create_color_light
from lifx_emulator.async_storage import AsyncDeviceStorage

# Create storage (uses ~/.lifx-emulator by default)
storage = AsyncDeviceStorage()

# Create device with storage enabled
device = create_color_light("d073d5000001", storage=storage)

# State changes are automatically saved asynchronously
device.state.label = "My Light"

# On next run, state is automatically restored from disk
```

### Test Scenarios

Inject test scenarios (packet loss, delays, etc.) for error testing:

```python
from lifx_emulator import create_color_light
from lifx_emulator.scenarios.manager import HierarchicalScenarioManager, ScenarioConfig

# Create scenario manager
manager = HierarchicalScenarioManager()

# Create device with scenario support
device = create_color_light("d073d5000001", scenario_manager=manager)

# Configure scenarios for testing error handling
manager.set_device_scenario(
    device.state.serial,
    ScenarioConfig(
        drop_packets={101: 0.3},  # Drop 30% of GetColor packets
        response_delays={102: 0.5},  # Add 500ms delay to SetColor
    )
)
```

### Custom Firmware Versions

Override firmware version for compatibility testing:

```python
from lifx_emulator import create_color_light

# Simulate older firmware
old_device = create_color_light(
    "d073d5000001",
    firmware_version=(2, 60)
)

# Simulate newer firmware
new_device = create_color_light(
    "d073d5000002",
    firmware_version=(3, 90)
)
```

## Next Steps

- [Server API](../server/) - Running the emulator server
- [Device API](../device/) - Device and state details
- [Product Registry](../products/) - All available products
- [Basic Tutorial](../../tutorials/02-basic/) - Complete usage examples
