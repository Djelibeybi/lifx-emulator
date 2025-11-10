# CLI Usage

Complete guide to the `lifx-emulator` command-line interface.

## Basic Usage

```bash
lifx-emulator [OPTIONS] [COMMAND]
```

## Commands

### `lifx-emulator` (default)

Start the emulator server with configurable devices.

**Example:**
```bash
lifx-emulator --color 2 --multizone 1 --verbose
```

### `lifx-emulator list-products`

List all available LIFX products from the registry.

**Example:**
```bash
lifx-emulator list-products
```

**With filter:**
```bash
# List only multizone products
lifx-emulator list-products --filter-type multizone

# List only matrix products (tiles)
lifx-emulator list-products --filter-type matrix
```

## Server Options

### `--bind <IP>`

IP address to bind to.

- **Default:** `127.0.0.1` (localhost only)
- **Example:** `--bind 0.0.0.0` (all IP addresses)

### `--port <PORT>`

UDP port to listen on.

- **Default:** `56700` (standard LIFX port)
- **Example:** `--port 56701`

### `--verbose`

Enable verbose logging showing all packet traffic.

- **Default:** `False`
- **Example:** `--verbose`

### `--persistent`

Enable persistent storage of device state across sessions. Device state (label, power, color, location, group, etc.) is saved to `~/.lifx-emulator/` and automatically restored on restart.

- **Default:** `False`
- **Example:** `--persistent`

### `--persistent-scenarios`

Enable persistent storage of scenario configurations across sessions. Scenarios are saved to `~/.lifx-emulator/scenarios.json`. Requires `--persistent` to be enabled.

- **Default:** `False`
- **Example:** `--persistent --persistent-scenarios`

## API Server Options

### `--api`

Enable HTTP API server for monitoring and device management. Provides a web dashboard and REST API for runtime control.

- **Default:** `False`
- **Example:** `--api`

### `--api-host <IP>`

IP address for the API server to bind to.

- **Default:** `127.0.0.1` (localhost only)
- **Example:** `--api-host 0.0.0.0`

### `--api-port <PORT>`

Port for the API server.

- **Default:** `8080`
- **Example:** `--api-port 9090`

### `--api-activity <BOOL>`

Enable activity logging in the API (last 100 packets). Disable to reduce traffic and save UI space.

- **Default:** `True`
- **Example:** `--api-activity=false`

## Product Selection

### `--product <product ID>`

Create devices by product ID from the registry. Can be specified multiple times.

**Example:**
```bash
# Create LIFX A19 (27) and LIFX Z (32)
lifx-emulator --product 27 --product 32

# Create multiple of same product
lifx-emulator --product 55 --product 55 --product 55
```

When using `--product`, the default `--color 1` is suppressed unless explicitly set.

## Device Type Options

### `--color <COUNT>`

Number of color lights to emulate (LIFX A19).

- **Default:** `1`
- **Product:** 27 (LIFX A19)
- **Example:** `--color 3`

### `--color-temperature <COUNT>`

Number of color temperature lights to emulate (LIFX Mini White to Warm).

- **Default:** `0`
- **Product:** 50 (LIFX Mini White to Warm)
- **Example:** `--color-temperature 2`

### `--infrared <COUNT>`

Number of infrared lights to emulate (LIFX A19 Night Vision).

- **Default:** `0`
- **Product:** 29 (LIFX A19 Night Vision)
- **Example:** `--infrared 1`

### `--HEV <COUNT>`

Number of HEV/Clean lights to emulate (LIFX Clean).

- **Default:** `0`
- **Product:** 90 (LIFX Clean)
- **Example:** `--HEV 2`

### `--multizone <COUNT>`

Number of multizone devices to emulate (strips/beams).

- **Default:** `0`
- **Product:** 32 (LIFX Z) or 38 (LIFX Beam with extended)
- **Example:** `--multizone 2`

### `--multizone-zones <COUNT>`

Number of zones per multizone device. If not specified, uses product defaults:

- LIFX Z: 16 zones
- LIFX Beam: 80 zones

- **Default:** `None` (uses product defaults)
- **Example:** `--multizone-zones 24`

### `--multizone-extended` / `--no-multizone-extended`

Enable or disable extended multizone support for multizone devices.

- **Default:** `True` (creates LIFX Beam with firmware 3.70)
- **Enabled:** `--multizone-extended` (default, firmware 3.70)
- **Disabled:** `--no-multizone-extended` (creates LIFX Z, firmware 2.60)
- **Example:** `--no-multizone-extended --multizone-zones 16`

### `--tile <COUNT>`

Number of tile devices to emulate (LIFX Tile).

- **Default:** `0`
- **Product:** 55 (LIFX Tile)
- **Example:** `--tile 1`

### `--tile-count <COUNT>`

Number of tiles per tile device. If not specified, uses product default (5 for LIFX Tile).

- **Default:** `None` (uses product defaults)
- **Example:** `--tile-count 10`

### `--tile-width <PIXELS>`

Width of each tile in pixels. If not specified, uses product default (typically 8).

- **Default:** `None` (uses product defaults)
- **Example:** `--tile-width 16`

### `--tile-height <PIXELS>`

Height of each tile in pixels. If not specified, uses product default (typically 8).

- **Default:** `None` (uses product defaults)
- **Example:** `--tile-height 8`

## serial Options

### `--serial-prefix <PREFIX>`

serial prefix (6 hex characters).

- **Default:** `d073d5`
- **Example:** `--serial-prefix cafe00`

serials are formatted as `<prefix><suffix>` where suffix is auto-incremented starting from `serial-start`.

### `--serial-start <NUMBER>`

Starting serial suffix.

- **Default:** `1`
- **Example:** `--serial-start 100`

## Complete Examples

### Default Configuration

```bash
# Single color light on port 56700
lifx-emulator
```

### Verbose Mode

```bash
# Show all packet traffic
lifx-emulator --verbose
```

### Custom Port

```bash
# Use port 56701
lifx-emulator --port 56701
```

### Multiple Device Types

```bash
# 2 color lights, 1 multizone, 1 tile
lifx-emulator --color 2 --multizone 1 --tile 1
```

### Extended Multizone

```bash
# LIFX Beam with 60 zones
lifx-emulator --multizone 1 --multizone-extended --multizone-zones 60
```

### Specific Products

```bash
# LIFX A19, LIFX Z, and LIFX Tile
lifx-emulator --product 27 --product 32 --product 55
```

### Mix Products and Types

```bash
# Specific product + additional generic devices
lifx-emulator --product 27 --color 2 --multizone 1
```

### Custom serials

```bash
# Custom prefix and starting number
lifx-emulator --serial-prefix cafe00 --serial-start 100 --color 3
# Creates: cafe00000064, cafe00000065, cafe00000066
```

### Only Specific Types

```bash
# No default devices, only infrared and HEV
lifx-emulator --color 0 --infrared 3 --HEV 2
```

### Discovery Testing

```bash
# Create many devices for load testing
lifx-emulator --color 10 --multizone 5 --tile 3
```

### Localhost Only

```bash
# Bind to localhost for security
lifx-emulator --bind 127.0.0.1 --verbose
```

### With HTTP API

```bash
# Enable web dashboard and REST API
lifx-emulator --api --color 2 --multizone 1

# Custom API port
lifx-emulator --api --api-port 9090

# API without activity logging (reduces traffic)
lifx-emulator --api --api-activity=false
```

### Persistent Storage

```bash
# Enable state persistence
lifx-emulator --persistent --color 2

# Enable both state and scenario persistence
lifx-emulator --persistent --persistent-scenarios --api
```

### Non-Extended Multizone

```bash
# Create LIFX Z (non-extended, 16 zones max)
lifx-emulator --multizone 2 --no-multizone-extended --multizone-zones 16
```

## List Products Command

### Basic List

```bash
lifx-emulator list-products
```

Output:
```
LIFX Product Registry (137 products)

 product ID │ Product Name                              │ Capabilities
─────┼───────────────────────────────────────────┼─────────────────────
  27 │ LIFX A19                                  │ full color
  29 │ LIFX A19 Night Vision                     │ full color, infrared
  32 │ LIFX Z                                    │ full color, multizone
  38 │ LIFX Beam                                 │ full color, extended-multizone
  55 │ LIFX Tile                                 │ full color, matrix
  90 │ LIFX Clean                                │ full color, HEV
 ...
```

### Filter by Type

```bash
# Only multizone products
lifx-emulator list-products --filter-type multizone

# Only matrix products
lifx-emulator list-products --filter-type matrix

# Only HEV products
lifx-emulator list-products --filter-type HEV

# Only infrared products
lifx-emulator list-products --filter-type infrared

# Only full color products
lifx-emulator list-products --filter-type color
```

## Tips

### Quick Testing

For quick testing, use verbose mode to see all traffic:

```bash
lifx-emulator --verbose
```

### Visual Monitoring

Use the HTTP API for visual monitoring during development:

```bash
lifx-emulator --api --verbose
# Open http://localhost:8080 in your browser
```

The web dashboard shows:
- Real-time server statistics
- List of all devices
- Recent packet activity (last 100 packets)
- REST API for runtime device management

### CI/CD Integration

Use specific ports and localhost binding in CI:

```bash
lifx-emulator --bind 127.0.0.1 --port 56701 &
EMULATOR_PID=$!
# Run your tests
kill $EMULATOR_PID
```

### Product Discovery

List products to find the right product ID for your tests:

```bash
lifx-emulator list-products --filter-type multizone
```

### State Preservation

Enable persistence to maintain device state across test runs:

```bash
lifx-emulator --persistent
# Device labels, colors, power states persist across restarts
```

### Realistic Configurations

Use product defaults for realistic device configurations:

```bash
# LIFX Beam with default 80 zones (extended by default)
lifx-emulator --multizone 1

# LIFX Tile with default 5 tiles
lifx-emulator --tile 1
```

### Development Mode

For development with full observability:

```bash
# Verbose logging, API dashboard, persistent state
lifx-emulator --verbose --api --persistent --color 2 --multizone 1
```

### Testing Mode

For testing network issues and edge cases:

```bash
# API enabled for runtime scenario configuration
lifx-emulator --api --color 3
# Then use the REST API to configure packet loss, delays, etc.
```

## Next Steps

- [Device Types Guide](../guide/device-types.md) - Learn about each device type
- [Testing Scenarios](../guide/testing-scenarios.md) - Configure error scenarios
- [API Reference](../api/index.md) - Python API documentation
- [Tutorials](../tutorials/index.md) - More usage examples
