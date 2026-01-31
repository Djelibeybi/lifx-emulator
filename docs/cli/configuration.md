# Configuration File

> Configure the emulator using a YAML file instead of command-line arguments

The LIFX Emulator supports YAML configuration files for persistent, reproducible setups. This is especially useful for complex configurations, team sharing, and CI/CD pipelines.

## Overview

Configuration files allow you to:

- Define complex device setups once and reuse them
- Share configurations across team members
- Version control your emulator settings
- Simplify CI/CD pipeline configuration
- Create named devices with specific product IDs

## Quick Start

Create a file named `lifx-emulator.yaml` in your current directory:

```yaml
# lifx-emulator.yaml
api: true
verbose: true
color: 2
multizone: 1
```

Then simply run:

```bash
lifx-emulator
```

The emulator automatically detects and loads the configuration file.

## Config File Resolution

The emulator looks for configuration in this order (first match wins):

1. **`--config` flag** - Explicit path to a config file
2. **`LIFX_EMULATOR_CONFIG` environment variable** - Path from environment
3. **Auto-detection** - `lifx-emulator.yaml` or `lifx-emulator.yml` in the current directory

### Examples

```bash
# Explicit config file
lifx-emulator --config /path/to/my-config.yaml

# Using environment variable
export LIFX_EMULATOR_CONFIG=/path/to/config.yaml
lifx-emulator

# Auto-detection (looks for lifx-emulator.yaml in current directory)
lifx-emulator
```

## CLI Override Behavior

CLI parameters always override config file values. This allows you to use a base configuration and override specific settings:

```bash
# Config file has port: 56700, but CLI overrides it
lifx-emulator --config base.yaml --port 56701
```

**Priority order:** CLI arguments > Config file > Defaults

## Configuration Options

### Server Options

```yaml
# IP address to bind to (default: 127.0.0.1)
bind: 127.0.0.1

# UDP port for LIFX protocol (default: 56700)
port: 56700

# Enable verbose packet logging (default: false)
verbose: false
```

### Storage & Persistence

```yaml
# Persist device state across restarts (default: false)
# State is saved to ~/.lifx-emulator/
persistent: false

# Persist scenario configurations (default: false)
# Requires persistent: true
persistent_scenarios: false
```

### HTTP API Server

```yaml
# Enable HTTP API server (default: false)
api: true

# API server bind address (default: 127.0.0.1)
api_host: 127.0.0.1

# API server port (default: 8080)
api_port: 8080

# Enable activity logging - last 100 packets (default: true)
api_activity: true
```

### Device Creation by Product ID

Create devices using specific product IDs from the LIFX registry:

```yaml
# List of product IDs to create
products:
  - 27   # LIFX A19
  - 38   # LIFX Beam
  - 55   # LIFX Tile
```

!!! tip "Finding Product IDs"
    Run `lifx-emulator list-products` to see all available products and their IDs.

When `products` is specified, the default `color: 1` is suppressed unless explicitly set.

### Device Creation by Type

Create devices by category:

```yaml
# Number of color lights - LIFX A19 (default: 1)
color: 1

# Number of color temperature lights - LIFX Mini White to Warm (default: 0)
color_temperature: 0

# Number of infrared lights - LIFX A19 Night Vision (default: 0)
infrared: 0

# Number of HEV/Clean lights - LIFX Clean (default: 0)
hev: 0

# Number of multizone devices - strips/beams (default: 0)
multizone: 0

# Number of tile devices - LIFX Tile (default: 0)
tile: 0

# Number of LIFX Switch devices - relay-based (default: 0)
switch: 0
```

### Multizone Options

```yaml
# Number of zones per multizone device
# Default: uses product defaults (16 for Z, 80 for Beam)
multizone_zones: 24

# Enable extended multizone support (default: true)
# true: Creates LIFX Beam with firmware 3.70
# false: Creates LIFX Z with firmware 2.60
multizone_extended: true
```

### Tile/Matrix Options

```yaml
# Number of tiles per tile device
# Default: uses product defaults (5 for LIFX Tile)
tile_count: 5

# Tile dimensions in zones
# Defaults: 8x8 for LIFX Tile, 5x6 for Candle
tile_width: 8
tile_height: 8
```

### Serial Number Options

```yaml
# Serial prefix - exactly 6 hex characters (default: d073d5)
serial_prefix: d073d5

# Starting serial suffix (default: 1)
# Serials are formatted as: <prefix><suffix as 6-digit hex>
serial_start: 1
```

## Per-Device Definitions

For fine-grained control, define individual devices with the `devices` list:

```yaml
devices:
  # Simple device with just product ID
  - product_id: 27

  # Device with custom label
  - product_id: 27
    label: "Living Room"

  # Multizone device with custom zone count
  - product_id: 38
    zone_count: 60
    label: "TV Backlight"

  # Tile device with custom tile count
  - product_id: 55
    tile_count: 3
    label: "Art Display"

  # Tile device with custom dimensions
  - product_id: 55
    tile_count: 1
    tile_width: 16
    tile_height: 8
    label: "Wide Panel"
```

### Device Definition Fields

| Field | Required | Description |
|-------|----------|-------------|
| `product_id` | Yes | LIFX product ID from registry |
| `label` | No | Device label (max 32 characters) |
| `zone_count` | No | Number of zones (multizone devices only) |
| `tile_count` | No | Number of tiles (matrix devices only) |
| `tile_width` | No | Tile width in zones (matrix devices only) |
| `tile_height` | No | Tile height in zones (matrix devices only) |

!!! note "Combining Device Types"
    You can use both `devices` list and device type counts (`color`, `multizone`, etc.) together. All specified devices will be created.

## Example Configurations

### Development Setup

```yaml
# development.yaml - Full observability for development
bind: 127.0.0.1
port: 56700
verbose: true

api: true
api_port: 8080
api_activity: true

color: 2
multizone: 1
tile: 1
```

### Testing Lab

```yaml
# testing-lab.yaml - Named devices for structured testing
bind: 127.0.0.1
port: 56700

api: true
persistent: true

# Disable default devices
color: 0

# Define specific test devices
devices:
  - product_id: 27
    label: "Test Bulb A"
  - product_id: 27
    label: "Test Bulb B"
  - product_id: 38
    zone_count: 80
    label: "Test Beam"
  - product_id: 55
    tile_count: 5
    label: "Test Tiles"
  - product_id: 90
    label: "Test HEV"
```

### CI/CD Pipeline

```yaml
# ci-config.yaml - Isolated configuration for CI
bind: 127.0.0.1
port: 56701  # Non-standard port to avoid conflicts

verbose: false
api: false
persistent: false

# Use unique serial prefix for test isolation
serial_prefix: "test00"

color: 1
multizone: 1
```

### Production-like Environment

```yaml
# production-like.yaml - Simulate a real home setup
bind: 0.0.0.0
port: 56700

api: true
api_host: 0.0.0.0
persistent: true
persistent_scenarios: true

color: 0

devices:
  # Living room
  - product_id: 27
    label: "Living Room Lamp"
  - product_id: 38
    zone_count: 40
    label: "TV Backlight"

  # Bedroom
  - product_id: 29
    label: "Bedroom Light"

  # Kitchen
  - product_id: 32
    zone_count: 16
    label: "Kitchen Strip"

  # Office
  - product_id: 55
    tile_count: 5
    label: "Office Tiles"
```

### Multizone Testing

```yaml
# multizone-test.yaml - Various multizone configurations
color: 0

devices:
  # Standard LIFX Z (non-extended)
  - product_id: 32
    zone_count: 16
    label: "Z Strip 16"

  # LIFX Beam (extended)
  - product_id: 38
    zone_count: 80
    label: "Beam 80"

  # Large zone count
  - product_id: 38
    zone_count: 160
    label: "Beam 160"
```

## Validation

The configuration file is validated on load. Invalid configurations will produce clear error messages:

```bash
$ lifx-emulator --config invalid.yaml
Error loading config file invalid.yaml: serial_prefix must be exactly 6 hex characters
```

### Common Validation Rules

- `serial_prefix` must be exactly 6 hexadecimal characters
- `product_id` in device definitions must be a valid LIFX product ID
- Unknown fields are rejected (typo protection)
- Type mismatches produce clear errors

## Environment Variable

Set `LIFX_EMULATOR_CONFIG` to automatically load a config file:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export LIFX_EMULATOR_CONFIG="$HOME/.config/lifx-emulator/default.yaml"

# Now just run without arguments
lifx-emulator
```

This is useful for:

- Personal default configurations
- Team-wide standard setups
- Container environments

## Best Practices

1. **Version control your configs** - Store configuration files in your project repository
2. **Use meaningful device labels** - Makes debugging and testing easier
3. **Separate configs by purpose** - Development, testing, CI/CD, etc.
4. **Use environment variable for defaults** - Set `LIFX_EMULATOR_CONFIG` for your preferred setup
5. **Override with CLI for one-off changes** - Don't modify config files for temporary adjustments
6. **Use `color: 0` with `devices`** - Prevents the default color light when using per-device definitions

## Troubleshooting

### Config File Not Loading

1. Check the file exists and is readable
2. Verify YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
3. Check for typos in field names (unknown fields are rejected)
4. Ensure the file is in the current directory for auto-detection

### Unexpected Device Count

Remember that device type counts (`color`, `multizone`, etc.) are **added to** the `devices` list, not replaced by it. To use only the `devices` list:

```yaml
color: 0  # Disable default color light
devices:
  - product_id: 27
    label: "My Only Light"
```

### Serial Conflicts

If you're running multiple emulator instances, use different serial prefixes:

```yaml
# Instance 1
serial_prefix: "aaa000"

# Instance 2
serial_prefix: "bbb000"
```

## Next Steps

- [CLI Reference](cli-reference.md) - Complete list of command-line options
- [Persistent Storage](storage.md) - Save device state across restarts
- [Device Management API](device-management-api.md) - Runtime device management
- [Scenarios Guide](scenarios.md) - Configure test scenarios