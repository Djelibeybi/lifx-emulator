# Factory Functions

Factory functions provide the easiest way to create emulated LIFX devices with sensible defaults.

## Overview

All factory functions return an `EmulatedLifxDevice` instance configured for a specific product type. They automatically load product-specific defaults (like zone counts and tile dimensions) from the product registry.

::: lifx_emulator.factories
    options:
      members:
        - create_color_light
        - create_color_temperature_light
        - create_infrared_light
        - create_hev_light
        - create_multizone_light
        - create_tile_device
        - create_device
      show_root_heading: false
      heading_level: 2

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

See [Product Registry](products.md) for all product definitions and defaults.

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

- [Server API](server.md) - Running the emulator server
- [Device API](device.md) - Device and state details
- [Product Registry](products.md) - All available products
- [Basic Tutorial](../tutorials/02-basic.md) - Complete usage examples
