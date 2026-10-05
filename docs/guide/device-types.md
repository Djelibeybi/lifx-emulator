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

### Creating Color Lights

=== "CLI"

    ```bash
    # Create a single color light
    lifx-emulator --color 1

    # Create multiple color lights
    lifx-emulator --color 3

    # Create by specific product ID
    lifx-emulator --product 27  # LIFX A19
    lifx-emulator --product 43  # LIFX BR30
    ```

=== "Python Library"

    ```python
    from lifx_emulator import create_color_light

    device = create_color_light("d073d5000001")
    ```

=== "REST API"

    ```bash
    # With API server enabled (lifx-emulator --api)
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 27}'
    ```

### Example Usage

=== "CLI"

    ```bash
    # Start emulator with verbose output to see state
    lifx-emulator --color 1 --verbose
    ```

=== "Python Library"

    ```python
    # Create and start server
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)
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
- **No RGB colour** (reported as `has_color=False`)

### Creating Color Temperature Lights

=== "CLI"

    ```bash
    # Create color temperature lights
    lifx-emulator --color-temperature 1

    # Create by specific product ID
    lifx-emulator --product 50  # LIFX Mini White to Warm
    ```

=== "Python Library"

    ```python
    from lifx_emulator import create_color_temperature_light

    device = create_color_temperature_light("d073d5000007")
    ```

=== "REST API"

    ```bash
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 50}'
    ```

### Behavior

These devices:

- Always report `has_color=False`
- Still accept `SetColor`: the emulator stores the colour as sent and does not
  force saturation to 0, so clients must avoid sending saturated colours
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

### Creating Infrared Lights

=== "CLI"

    ```bash
    # Create infrared lights
    lifx-emulator --infrared 1

    # Create by specific product ID
    lifx-emulator --product 29  # LIFX A19 Night Vision
    ```

=== "Python Library"

    ```python
    from lifx_emulator import create_infrared_light

    device = create_infrared_light("d073d5000002")
    ```

=== "REST API"

    ```bash
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 29}'
    ```

### Infrared Control

```python
device = create_infrared_light("d073d5000002")

# Check infrared support
print(f"Has IR: {device.state.has_infrared}")  # True

# Default IR brightness (set to 25%)
print(f"IR brightness: {device.state.infrared_brightness}")  # 16384

# After receiving a Light.SetInfrared command
# device.state.infrared_brightness will be updated
```

### Packet Types

- `Light.GetInfrared` (120)
- `Light.StateInfrared` (121)
- `Light.SetInfrared` (122)

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

### Creating HEV Lights

=== "CLI"

    ```bash
    # Create HEV lights
    lifx-emulator --hev 1

    # Create by specific product ID
    lifx-emulator --product 90  # LIFX Clean
    ```

=== "Python Library"

    ```python
    from lifx_emulator import create_hev_light

    device = create_hev_light("d073d5000003")
    ```

=== "REST API"

    ```bash
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 90}'
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

- `Light.GetHevCycle` (142)
- `Light.SetHevCycle` (143)
- `Light.StateHevCycle` (144)
- `Light.GetHevCycleConfiguration` (145)
- `Light.SetHevCycleConfiguration` (146)
- `Light.StateHevCycleConfiguration` (147)
- `Light.GetLastHevCycleResult` (148)
- `Light.StateLastHevCycleResult` (149)

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

### Creating Multizone Devices

=== "CLI"

    ```bash
    # Extended multizone (LIFX Beam, product 38) with default 80 zones
    lifx-emulator --multizone 1

    # Multiple multizone devices with custom zone count
    lifx-emulator --multizone 2 --multizone-zones 24

    # Non-extended multizone
    lifx-emulator --multizone 1 --no-multizone-extended

    # Create by specific product ID
    lifx-emulator --product 32  # LIFX Z
    lifx-emulator --product 38  # LIFX Beam
    ```

=== "Python Library"

    ```python
    from lifx_emulator import create_multizone_light
    from lifx_emulator.factories import create_device

    # Standard LIFX Z (product 32) with default 16 zones
    strip = create_device(32, serial="d073d5800001")

    # create_multizone_light() creates a LIFX Beam (product 38):
    # extended multizone with default 80 zones
    beam = create_multizone_light("d073d5800002")

    # Custom zone count
    beam = create_multizone_light("d073d5800003", zone_count=24)

    # Non-extended multizone
    beam = create_multizone_light("d073d5800004", extended_multizone=False)
    ```

=== "REST API"

    ```bash
    # Standard multizone
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 32, "zone_count": 16}'

    # Extended multizone with custom zones
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 38, "zone_count": 80}'
    ```

### Zone Management

```python
strip = create_device(32, serial="d073d5800001", zone_count=16)

# Check configuration
print(f"Has multizone: {strip.state.has_multizone}")  # True
print(f"Zone count: {strip.state.zone_count}")  # 16
print(f"Product: {strip.state.product}")  # 32 (LIFX Z)

# Access zone colors
for i, color in enumerate(strip.state.zone_colors):
    print(f"Zone {i}: {color}")
```

### Multizone Packet Types

**Standard (all multizone devices):**
- `SetColorZones` (501)
- `GetColorZones` (502)
- `StateZone` (503)
- `StateMultiZone` (506)

**Extended (extended multizone only):**
- `ExtendedSetColorZones` (510)
- `ExtendedGetColorZones` (511)
- `ExtendedStateMultiZone` (512)

**Effects:**
- `GetEffect` (507)
- `SetEffect` (508)
- `StateEffect` (509)

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
- **LIFX Mirror** (product ID 267, 268) - 4x13 with front and back rings (see below)

### LIFX Mirror Zone Map

The Mirror is driven as a single 4x13 matrix: 52 buffer positions holding 50
zones, with two positions unused. Its zone numbers do not follow buffer order.
Zones 0-24 form the front ring (facing the room) and zones 25-49 form the back
ring (washing the wall). The emulator carries the firmware zone map, which gives
the zone at each buffer position:

| Row | Col 0 (front left) | Col 1 (front right) | Col 2 (back left) | Col 3 (back right) |
| --- | --- | --- | --- | --- |
| 0 | 9 | unused | 40 | unused |
| 1-9 | 8 down to 0 | 10 up to 18 | 41 up to 49 | 39 down to 31 |
| 10 | 24 | 19 | 25 | 30 |
| 11 | 23 | 20 | 26 | 29 |
| 12 | 22 | 21 | 27 | 28 |

The two unused positions behave like any other buffer position: they store and
report whatever `Set64` writes. The map is exposed as `DeviceState.zone_map`
(`-1` marks an unused position) and as `zone_map` in the HTTP API's device
info, and the dashboard draws the Mirror as its two rings instead of a grid.

### Capabilities

- 2D matrix of individually controlled full color zones
- Multiple tiles in a chain (original Tile only)
- Tile positioning in 2D space (original Tile only)
- Matrix effects (Morph, Flame, Sky)
- Power on/off

### Creating Matrix Devices

=== "CLI"

    ```bash
    # Standard LIFX Tile (8x8) with default 5 tiles
    lifx-emulator --tile 1

    # Multiple tile devices with custom tile count
    lifx-emulator --tile 2 --tile-count 3

    # Create by specific product ID
    lifx-emulator --product 55   # LIFX Tile
    lifx-emulator --product 57   # LIFX Candle
    lifx-emulator --product 176  # LIFX Ceiling
    lifx-emulator --product 201  # LIFX Ceiling 13x26" (one 16x8 tile, >64 zones)
    ```

!!! note "Tile size is fixed per product"
    The LIFX Tile is always 8x8 with 1 to 5 tiles on its chain; every other
    matrix product is a single tile of its own size. The `--tile-width` /
    `--tile-height` options and `tile_width` / `tile_height` arguments are
    deprecated and ignored. To get a different tile size, choose the product
    that has it.

=== "Python Library"

    ```python
    from lifx_emulator import create_tile_device
    from lifx_emulator.factories import create_device

    # Standard LIFX Tile (8x8) with default 5 tiles
    tiles = create_tile_device("d073d5900001")

    # Custom tile count (1 to 5)
    tiles = create_tile_device("d073d5900002", tile_count=3)

    # Large matrix device: LIFX Ceiling 13x26", one 16x8 tile (>64 zones)
    large_matrix = create_device(201, serial="d073d5c00001")
    ```

=== "REST API"

    ```bash
    # Standard tile
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 55, "tile_count": 5}'

    # Large matrix device (LIFX Ceiling 13x26", one 16x8 tile)
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 201}'
    ```

### Matrix Configuration

```python
tiles = create_tile_device("d073d5900001", tile_count=5)

# Check configuration
print(f"Has matrix: {tiles.state.has_matrix}")  # True
print(f"Tile count: {tiles.state.tile_count}")  # 5
print(f"Tile width: {tiles.state.tile_width}")  # 8
print(f"Tile height: {tiles.state.tile_height}")  # 8

# Access tile devices (each one is a dict)
for i, tile in enumerate(tiles.state.tile_devices):
    print(f"Tile {i}: {tile['width']}x{tile['height']} zones")
```

### Matrix Packet Types

- `GetDeviceChain` (701)
- `StateDeviceChain` (702)
- `SetUserPosition` (703)
- `Get64` (707)
- `State64` (711)
- `Set64` (715)
- `CopyFrameBuffer` (716)
- `GetEffect` (718)
- `SetEffect` (719)
- `StateEffect` (720)

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

### Framebuffers (v2.3+)

Matrix devices support **8 framebuffers (0-7)** to enable atomic updates of tiles with more than 64 zones:

- **Framebuffer 0**: Visible buffer (displayed on device)
- **Framebuffers 1-7**: Non-visible buffers for preparing content off-screen

For large tiles (>64 zones), prepare all zones in a non-visible framebuffer, then use `CopyFrameBuffer` to atomically display them without flicker.

See [Framebuffer Guide](framebuffers.md) for complete documentation and examples.


## Switch Devices

LIFX Switch devices are relay-based switches with no lighting capabilities. They respond with `StateUnhandled` (packet 223) to all lighting-related protocol requests.

### Example Products

- **LIFX Switch** (product IDs 70, 71, 89, 115, 116) - 2 relay switches

### Capabilities

- **Relays**: Physical relay switches for controlling external loads
- **Buttons**: Physical buttons for manual control
- **No lighting**: No color, brightness, or zone control
- Basic device operations (GetVersion, GetLabel, EchoRequest, etc.)

### Creating Switch Devices

=== "CLI"

    ```bash
    # Create LIFX Switch devices
    lifx-emulator --switch 1

    # Create by specific product ID
    lifx-emulator --product 70  # LIFX Switch
    lifx-emulator --product 89  # LIFX Switch variant
    ```

=== "Python Library"

    ```python
    from lifx_emulator.factories import create_switch

    # Create LIFX Switch (default product 70)
    switch = create_switch("d073d5700001")

    # Or specify a different switch product
    switch = create_switch("d073d5700002", product_id=89)
    ```

=== "REST API"

    ```bash
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 70}'
    ```

### Switch Behavior

```python
switch = create_switch("d073d5700001")

# Check capabilities
print(f"Has relays: {switch.state.has_relays}")  # True
print(f"Has buttons: {switch.state.has_buttons}")  # True
print(f"Has color: {switch.state.has_color}")  # False
print(f"Has multizone: {switch.state.has_multizone}")  # False
```

### Packet Handling

**Supported (Device.* packets 2-59):**
- `GetVersion` (32) → `StateVersion` (33)
- `GetLabel` (23) → `StateLabel` (25)
- `SetLabel` (24)
- `EchoRequest` (58) → `EchoResponse` (59)
- All other Device.* packets

**Rejected with StateUnhandled (223):**
- **Light.* packets (101-149)**: GetColor, SetColor, GetPower, SetPower, etc.
- **MultiZone.* packets (501-512)**: GetColorZones, SetColorZones, etc.
- **Tile.* packets (701-720)**: Get64, Set64, GetEffect, etc.

### StateUnhandled Response

When a switch receives an unsupported packet type, it responds with:

```python
# Client sends Light.GetColor (101) to switch
# Switch responds with:
# - StateUnhandled (223) with unhandled_type=101
# - Acknowledgement (45) if ack_required=True
```

The `StateUnhandled` packet includes the rejected packet type in the `unhandled_type` field, allowing clients to detect and handle unsupported operations gracefully.

### Limitations

**Note**: Button packets (`Button.Get`, `Button.Set`, `Button.GetConfig`, `Button.SetConfig`, 905-911) are handled, but relay control protocol packets are not currently implemented in the emulator.

The switch emulation is primarily for testing client libraries' handling of:
- Device capability detection
- StateUnhandled response handling
- Graceful degradation when lighting features are unavailable


## Using Generic create_device()

All factory functions use `create_device()` internally. You can use it directly:

=== "CLI"

    ```bash
    # Create any device by product ID
    lifx-emulator --product 27   # LIFX A19
    lifx-emulator --product 32   # LIFX Z
    lifx-emulator --product 55   # LIFX Tile
    lifx-emulator --product 57   # LIFX Candle

    # Mix multiple products
    lifx-emulator --product 27 --product 32 --product 55
    ```

=== "Python Library"

    ```python
    from lifx_emulator.factories import create_device

    # Create by product ID
    a19 = create_device(27, serial="d073d5000001")
    z_strip = create_device(32, serial="d073d5800001", zone_count=16)
    tiles = create_device(55, serial="d073d5900001", tile_count=5)
    candle = create_device(57, serial="d073d5900002")

    # Product defaults are automatically loaded
    print(f"Candle size: {candle.state.tile_width}x{candle.state.tile_height}")  # 5x6
    ```

=== "REST API"

    ```bash
    # Create any device by product ID
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 57}'  # LIFX Candle
    ```

## Next Steps

- [Testing Scenarios](testing-scenarios.md) - Configure error scenarios
- [Integration Testing](integration-testing.md) - Use in tests
- [Factory Functions API](../library/factories.md) - Detailed API docs
- [Product Registry](../library/products.md) - All products
