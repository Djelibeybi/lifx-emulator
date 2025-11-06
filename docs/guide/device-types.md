# Device Types

Complete guide to all supported LIFX device types and their capabilities.

## Overview

The LIFX Emulator supports all major LIFX device types, each with specific capabilities and features.

## Color Lights

Full RGB color lights with complete color control.

### Example Products

- **LIFX A19** (product ID 27) - Standard color bulb
- **LIFX BR30** (product ID 43) - BR30 flood light
- **LIFX Downlight** (product ID 36) - Recessed downlight
- **LIFX GU10** (product ID 66) - GU10 spot light
- **And many more...**

### Capabilities

- Full RGBW color (360° hue, 0-100% saturation)
- Brightness control (0-100%)
- Color temperature (1500K-9000K)
- Power on/off

### Factory Function

```python
from lifx_emulator import create_color_light

device = create_color_light("d073d5000001")
```

### Example Usage

```python
# Create and start server
device = create_color_light("d073d5000001")
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
await server.start()

# Check state
print(f"Has color: {device.state.has_color}")  # True
print(f"Color: {device.state.color}")
```

## Color Temperature Lights

White lights with variable color temperature (warm to cool white).

### Example Products

- **LIFX Mini White to Warm** (product ID 50)
- **LIFX Downlight White to Warm** (product ID 48)

### Capabilities

- Color temperature adjustment (1500K-9000K)
- Brightness control (0-100%)
- Power on/off
- **No RGB color** (saturation locked to 0)

### Factory Function

```python
from lifx_emulator import create_color_temperature_light

device = create_color_temperature_light("d073d5000007")
```

### Behavior

These devices:

- Always report `has_color=False`
- Reject color commands (SetColor with saturation > 0)
- Accept color temperature changes via kelvin value
- Only vary brightness and temperature

## Infrared Lights

Color lights with additional infrared capability for night vision.

### Example Products

- **LIFX A19 Night Vision** (product ID 29)
- **LIFX BR30 Night Vision** (product ID 44)

### Capabilities

- Full RGBW color
- Brightness control
- Color temperature
- **Infrared brightness** (0-100%)
- Power on/off

### Factory Function

```python
from lifx_emulator import create_infrared_light

device = create_infrared_light("d073d5000002")
```

### Infrared Control

```python
device = create_infrared_light("d073d5000002")

# Check infrared support
print(f"Has IR: {device.state.has_infrared}")  # True

# Default IR brightness (set to 25%)
print(f"IR brightness: {device.state.infrared_brightness}")  # 16384

# After receiving LightSetInfrared command
# device.state.infrared_brightness will be updated
```

### Packet Types

- `LightGetInfrared` (120)
- `LightStateInfrared` (121)
- `LightSetInfrared` (122)

## HEV Lights

Lights with HEV (High Energy Visible) anti-bacterial cleaning capability.

### Example Products

- **LIFX Clean** (product ID 90)

### Capabilities

- Full RGBW color
- Brightness control
- Color temperature
- **HEV cleaning cycle** (anti-bacterial sanitization)
- Cycle duration configuration
- Cycle progress tracking
- Power on/off

### Factory Function

```python
from lifx_emulator import create_hev_light

device = create_hev_light("d073d5000003")
```

### HEV State

```python
device = create_hev_light("d073d5000003")

# HEV defaults
print(f"Has HEV: {device.state.has_hev}")  # True
print(f"Cycle duration: {device.state.hev_cycle_duration_s}")  # 7200 (2 hours)
print(f"Remaining: {device.state.hev_cycle_remaining_s}")  # 0 (not running)
print(f"Indication: {device.state.hev_indication}")  # True
```

### HEV Packet Types

- `HevGet` (143)
- `HevStateResult` (144)
- `HevGetResult` (145)
- `HevStateResult` (146)
- `HevSetConfig` (147)
- `HevGetConfig` (148)
- `HevStateConfig` (149)

## Multizone Devices

Linear light strips with independently controllable zones.

### Example Products

- **LIFX Z** (product ID 32) - Default 16 zones (8 zones/strip)
- **LIFX Beam** (product ID 38) - Default 80 zones (10 zones/beam)
- **LIFX Neon** (product ID 141) - Default 24 zones (24 zones/segment)
- **LIFX String** (product ID 143) - Default 36 zones (36 zones/string)
- **LIFX Permanent Outdoor** (product ID 213) - Default 30 zones (15 zones/segment)

### Capabilities

- Full RGBW color per zone
- Per-zone brightness and color
- Multizone effect (MOVE)
- Power on/off

### Factory Function

```python
from lifx_emulator import create_multizone_light

# Standard LIFX Z with default 16 zones
strip = create_multizone_light("d073d8000001")

# Custom zone count
strip = create_multizone_light("d073d8000002", zone_count=24)

# Extended multizone (LIFX Beam) with default 80 zones
beam = create_multizone_light("d073d8000003", extended_multizone=True)

# Extended with custom zone count
beam = create_multizone_light("d073d8000004", zone_count=60, extended_multizone=True)
```

### Zone Management

```python
strip = create_multizone_light("d073d8000001", zone_count=16)

# Check configuration
print(f"Has multizone: {device.state.has_multizone}")  # True
print(f"Zone count: {device.state.zone_count}")  # 16
print(f"Product: {device.state.product}")  # 32 (LIFX Z)

# Access zone colors
for i, color in enumerate(device.state.zone_colors):
    print(f"Zone {i}: {color}")
```

### Multizone Packet Types

**Standard (all multizone devices):**
- `SetColorZones` (501)
- `GetColorZones` (502)
- `StateZone` (503)
- `StateMultiZone` (506)

**Extended (extended multizone only):**
- `SetExtendedColorZones` (510)
- `GetExtendedColorZones` (511)
- `StateExtendedColorZones` (512)

**Effects:**
- `SetMultiZoneEffect` (509)
- `GetMultiZoneEffect` (507)
- `StateMultiZoneEffect` (508)

## Matrix Devices

Devices with a 2D matrix of individually controlled zones.

### Example Products

- **LIFX Tile** (product ID 55) - 8x8 tile with up to 5 tiles per chain (discontinued)
- **LIFX Candle** (product ID 57, 68, 137, 138, 185, 186, 215, 216) - 6x5 tile
- **LIFX Ceiling** (product ID 176) - 8x8 with uplight/downlight zones
- **LIFX Ceiling 13x26"** (product ID 201, 202) - 16x8 with uplight/downlight zones
- **LIFX Tube** (product ID 177, 217, 218) - 5x11
- **LIFX Luna** (product ID 219, 220) - 7x5
- **LIFX Round Spot** (product ID 171, 221) - 3x1
- **LIFX Round/Square Path** (product ID 173, 174, 222) - 3x2

### Capabilities

- 2D matrix of individually controlled full color zones
- Multiple tiles in a chain (original Tile only)
- Tile positioning in 2D space (original Tile only)
- Matrix effects (Morph, Flame, Sky)
- Power on/off

### Factory Functions

```python
from lifx_emulator import create_tile_device

# Standard LIFX Tile (8x8) with default 5 tiles
tiles = create_tile_device("d073d9000001")

# Custom tile count
tiles = create_tile_device("d073d9000002", tile_count=10)

# Custom tile dimensions (e.g., 16x8 with >64 zones)
large_tile = create_tile_device("d073dc000001", tile_count=1, tile_width=16, tile_height=8)

# Any custom size
custom = create_tile_device("d073dc000002", tile_count=3, tile_width=12, tile_height=12)
```

### Matrix Configuration

```python
tiles = create_tile_device("d073d9000001", tile_count=5)

# Check configuration
print(f"Has matrix: {device.state.has_matrix}")  # True
print(f"Tile count: {device.state.tile_count}")  # 5
print(f"Tile width: {device.state.tile_width}")  # 8
print(f"Tile height: {device.state.tile_height}")  # 8

# Access tile devices
for i, tile in enumerate(device.state.tile_devices):
    print(f"Tile {i}: {tile.width}x{tile.height} pixels")
```

### Matrix Packet Types

- `GetDeviceChain` (701)
- `StateDeviceChain` (702)
- `SetUserPosition` (703)
- `GetTileState64` (707)
- `StateTileState64` (711)
- `SetTileState64` (715)
- `GetTileEffect` (718)
- `StateTileEffect` (719)

### Zone Access

Matrix devices usually have up to 64 zones per tile with a single
tile per chain.

Exceptions include the LIFX Tile that supports up to 5 tiles
per chain and the new LIFX Ceiling 26"x13" which has 128 zones on a
single tile.

```python
# Get64 requests specify a rectangle of zones
# x, y, width specify which zones to retrieve
# State64 responses contain up to 64 zones

# Large tiles (16x8) require multiple Get64 requests
# split either by row or column.
```


## Using Generic create_device()

All factory functions use `create_device()` internally. You can use it directly:

```python
from lifx_emulator.factories import create_device

# Create by product ID
a19 = create_device(27, serial="d073d5000001")
z_strip = create_device(32, serial="d073d8000001", zone_count=16)
tiles = create_device(55, serial="d073d9000001", tile_count=5)
candle = create_device(57, serial="d073d9000002")

# Product defaults are automatically loaded
print(f"Candle size: {candle.state.tile_width}x{candle.state.tile_height}")  # 5x6
```

## Next Steps

- [Testing Scenarios](testing-scenarios.md) - Configure error scenarios
- [Integration Testing](integration-testing.md) - Use in tests
- [Factory Functions API](../api/factories.md) - Detailed API docs
- [Product Registry](../api/products.md) - All products
