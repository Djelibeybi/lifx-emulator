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

Create a standard full-colour light (LIFX Color 800lm):

```python
from lifx_emulator import create_color_light

# Auto-generated serial
device = create_color_light()

# Custom serial
device = create_color_light("d073d5000001")

# Access state
print(f"Label: {device.state.label}")
print(f"Product: {device.state.product}")  # 91 (LIFX Color 800lm)
print(f"Has color: {device.state.has_color}")  # True
```

### Color Temperature Light

Create a white light with variable color temperature:

```python
from lifx_emulator import create_color_temperature_light

device = create_color_temperature_light("d073d5000001")

print(f"Has color: {device.state.has_color}")  # False
print(f"Product: {device.state.product}")  # 50 (LIFX Mini DD)
```

### Infrared Light

Create a light with infrared capability:

```python
from lifx_emulator import create_infrared_light

device = create_infrared_light("d073d5000002")

print(f"Has infrared: {device.state.has_infrared}")  # True
print(f"Product: {device.state.product}")  # 29 (LIFX+ A19)
print(f"IR brightness: {device.state.infrared_brightness}")  # 16384 (25%)
```

### HEV Light

Create a light with HEV cleaning capability:

```python
from lifx_emulator import create_hev_light

device = create_hev_light("d073d5000003")

print(f"Has HEV: {device.state.has_hev}")  # True
print(f"Product: {device.state.product}")  # 90 (LIFX Clean A19 1100lm)
print(f"HEV cycle duration: {device.state.hev_cycle_duration_s}")  # 7200 (2 hours)
```

### Multizone Light

Create a linear multizone device. `create_multizone_light()` always creates a LIFX Beam; use `create_device()` with a product ID for other strips such as the LIFX Z:

```python
from lifx_emulator import create_multizone_light
from lifx_emulator.factories import create_device

# LIFX Beam with the default 80 zones and extended multizone support
beam = create_multizone_light("d073d8000001")

# Custom zone count
beam_custom = create_multizone_light("d073d8000002", zone_count=60)

# Standard multizone only (no extended multizone packets, firmware 2.60)
beam_standard = create_multizone_light("d073d8000003", extended_multizone=False)

# LIFX Z (product ID 32) with the default 16 zones
strip = create_device(32, serial="d073d8000004")

print(f"Beam zones: {beam.state.zone_count}")   # 80
print(f"Strip zones: {strip.state.zone_count}")  # 16
print(f"Beam product: {beam.state.product}")    # 38 (LIFX Beam)
print(f"Strip product: {strip.state.product}")  # 32 (LIFX Z)
```

### Tile Device

Create a matrix tile device:

```python
from lifx_emulator import create_tile_device

# Default configuration (5 tiles of 8x8)
tiles = create_tile_device("d073d9000001")

# Custom tile count (1 to 5 tiles on the chain)
tiles_custom = create_tile_device("d073d9000002", tile_count=3)

print(f"Tile count: {tiles.state.tile_count}")      # 5
print(f"Tile width: {tiles.state.tile_width}")      # 8
print(f"Tile height: {tiles.state.tile_height}")    # 8
print(f"Product: {tiles.state.product}")            # 55 (LIFX Tile)
```

!!! warning "Deprecated: `tile_width` and `tile_height`"
    Every matrix product has a fixed tile size from its specs: the LIFX Tile
    is always 8x8. The `tile_width`/`tile_height` arguments of
    `create_tile_device()` and `create_device()`, and
    `DeviceBuilder.with_tile_dimensions()`, are accepted but ignored and
    raise a `DeprecationWarning`. They will be removed in the next major
    release. For a tile with more than 64 zones, create the product that has
    one:

    ```python
    from lifx_emulator.factories import create_device

    # LIFX Ceiling 13x26": one 16x8 tile, so reading it takes two Get64 requests
    large_matrix = create_device(201, serial="d073d9000003")
    print(large_matrix.state.tile_width * large_matrix.state.tile_height)  # 128
    ```

### Generic Device Creation

Create any device by product ID:

```python
from lifx_emulator.factories import create_device

# LIFX A19 (product ID 27)
a19 = create_device(27, serial="d073d5000001")

# LIFX Z (product ID 32) with custom zones
z_strip = create_device(32, serial="d073d8000001", zone_count=24)

# LIFX Tile (product ID 55) with 3 tiles on its chain
tiles = create_device(55, serial="d073d9000001", tile_count=3)

# LIFX Candle (product ID 57) - loads 5x6 dimensions from product defaults
candle = create_device(57, serial="d073d9000002")
print(f"Candle size: {candle.state.tile_width}x{candle.state.tile_height}")  # 5x6
```

## Serial Format

Serials must be 12 hex characters (6 bytes):

```python
from lifx_emulator import create_color_light

# Valid formats
device = create_color_light("d073d5000001")  # Serial with LIFX prefix ("d073d5")
device = create_color_light("cafe00abcdef")  # Serial with custom prefix
device = create_color_light()                # Auto-generate serial

# Invalid (raises ValueError)
for bad_serial in ("123", "xyz"):  # Too short / not hex
    try:
        create_color_light(bad_serial)
    except ValueError as e:
        print(e)  # Serial must be exactly 12 ASCII hexadecimal characters
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
from lifx_emulator import create_multizone_light, create_tile_device
from lifx_emulator.factories import create_device

# Uses product default (16 zones for LIFX Z)
strip = create_device(32, serial="d073d8000001")

# Uses product default (80 zones for LIFX Beam)
beam = create_multizone_light("d073d8000002")

# Uses product default (5 tiles for LIFX Tile)
tiles = create_tile_device("d073d9000001")

# Uses product default (5x6 for LIFX Candle)
candle = create_device(57, serial="d073d9000002")
```

See [Product Registry](products.md) for all product definitions and defaults.

## Device State Access

After creation, access device state:

```python
from lifx_emulator import create_color_light

device = create_color_light("d073d5000001")

# Device identity
print(device.state.serial)          # "d073d5000001"
print(device.state.label)           # "LIFX Color 800lm 000001"
print(device.state.vendor)          # 1 (LIFX)
print(device.state.product)         # 91 (LIFX Color 800lm)

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
print(device.state.version_major)   # 3
print(device.state.version_minor)   # 70
```

## Multiple Devices

Create multiple devices for testing:

```python
import asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create a diverse set of devices
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_device(32, serial="d073d8000001", zone_count=16),  # LIFX Z
        create_multizone_light("d073d8000002", zone_count=82),  # LIFX Beam
        create_tile_device("d073d9000001", tile_count=5),
    ]

    # Start server with all devices
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:
        await asyncio.sleep(60)


asyncio.run(main())
```

## Advanced Options

### Persistent Storage

Devices can persist state across restarts. State-changing protocol packets (`SetColor`, `SetLabel`, ...) queue a save automatically; direct assignments to `device.state` need an explicit `save_device_state()`:

```python
import asyncio

from lifx_emulator import create_color_light
from lifx_emulator.devices import DevicePersistenceAsyncFile


async def main():
    # Create storage (uses ~/.lifx-emulator by default)
    storage = DevicePersistenceAsyncFile()

    # Create device with storage enabled; saved state is restored here
    device = create_color_light("d073d5000001", storage=storage)

    # Direct assignments are not saved automatically, so queue a save
    device.state.label = "My Light"
    await storage.save_device_state(device.state)

    # Flush pending writes before the event loop exits
    await storage.shutdown()

    # On next run, state is automatically restored from disk


asyncio.run(main())
```

See [Storage API](storage.md) for details.

### Test Scenarios

Inject test scenarios (packet loss, delays, etc.) for error testing:

```python
from lifx_emulator import create_color_light
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

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

When the device runs inside an `EmulatedLifxServer`, pass the same manager to the server as `scenario_manager=manager`: the server assigns its own scenario manager to every device it manages, so scenarios registered only on the factory's manager would be ignored.

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
