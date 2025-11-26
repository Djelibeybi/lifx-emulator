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
- **No RGB color** (saturation locked to 0)

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

### Creating Multizone Devices

=== "CLI"

    ```bash
    # Standard LIFX Z with default 16 zones
    lifx-emulator --multizone 1

    # Multiple multizone devices with custom zone count
    lifx-emulator --multizone 2 --multizone-zones 24

    # Extended multizone (LIFX Beam) with default 80 zones
    lifx-emulator --multizone 1 --multizone-extended

    # Non-extended multizone
    lifx-emulator --multizone 1 --no-multizone-extended

    # Create by specific product ID
    lifx-emulator --product 32  # LIFX Z
    lifx-emulator --product 38  # LIFX Beam
    ```

=== "Python Library"

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

### Creating Matrix Devices

=== "CLI"

    ```bash
    # Standard LIFX Tile (8x8) with default 5 tiles
    lifx-emulator --tile 1

    # Multiple tile devices with custom tile count
    lifx-emulator --tile 2 --tile-count 3

    # Custom tile dimensions
    lifx-emulator --tile 1 --tile-width 16 --tile-height 8

    # Create by specific product ID
    lifx-emulator --product 55   # LIFX Tile
    lifx-emulator --product 57   # LIFX Candle
    lifx-emulator --product 176  # LIFX Ceiling
    ```

=== "Python Library"

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

=== "REST API"

    ```bash
    # Standard tile
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 55, "tile_count": 5}'

    # Custom dimensions
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 55, "tile_count": 1, "tile_width": 16, "tile_height": 8}'
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
    print(f"Tile {i}: {tile.width}x{tile.height} zones")
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
    from lifx_emulator import create_switch

    # Create LIFX Switch (default product 70)
    switch = create_switch("d073d7000001")

    # Or specify a different switch product
    switch = create_switch("d073d7000002", product_id=89)
    ```

=== "REST API"

    ```bash
    curl -X POST http://localhost:8080/api/devices \
      -H "Content-Type: application/json" \
      -d '{"product_id": 70}'
    ```

### Switch Behavior

```python
switch = create_switch("d073d7000001")

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
- **Tile.* packets (701-720)**: Get64, Set64, GetTileEffect, etc.

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

**Note**: Button and relay control protocol packets are not currently implemented in the emulator.

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
    z_strip = create_device(32, serial="d073d8000001", zone_count=16)
    tiles = create_device(55, serial="d073d9000001", tile_count=5)
    candle = create_device(57, serial="d073d9000002")

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
