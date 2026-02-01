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
1. **`LIFX_EMULATOR_CONFIG` environment variable** - Path from environment
1. **Auto-detection** - `lifx-emulator.yaml` or `lifx-emulator.yml` in the current directory

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

### Storage & Persistence (Deprecated)

Deprecated

`persistent` and `persistent_scenarios` are deprecated and will be removed in a future release. Use [device definitions with state fields](#per-device-definitions) and the [scenarios section](#scenarios) instead. To migrate existing persistent storage, see [Migrating from Persistent Storage](#migrating-from-persistent-storage).

```yaml
# DEPRECATED: Use device definitions with state fields instead
# persistent: false

# DEPRECATED: Use the scenarios section instead
# persistent_scenarios: false
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

Finding Product IDs

Run `lifx-emulator list-products` to see all available products and their IDs.

No devices are created by default. Use `products`, `color`, or other device type fields to specify which devices to create.

### Device Creation by Type

Create devices by category:

```yaml
# Number of color lights - LIFX A19 (default: 0)
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

  # Device with full initial state
  - product_id: 27
    serial: d073d5000001
    label: "Living Room"
    power_level: 65535
    color:
      hue: 21845
      saturation: 65535
      brightness: 65535
      kelvin: 3500
    location: "Downstairs"
    group: "Lights"

  # Device using compact HSBK notation
  - product_id: 27
    label: "Kitchen"
    color: [0, 0, 32768, 4000]

  # Multizone device with per-zone colors
  - product_id: 38
    zone_count: 16
    label: "TV Backlight"
    zone_colors:
      - [0, 65535, 65535, 3500]
      - [21845, 65535, 65535, 3500]
      - [43690, 65535, 65535, 3500]

  # Infrared light with IR brightness
  - product_id: 29
    label: "Security Camera"
    infrared_brightness: 32768

  # HEV light with cycle configuration
  - product_id: 90
    label: "Bathroom"
    hev_cycle_duration: 7200
    hev_indication: true

  # Tile device with custom tile count
  - product_id: 55
    tile_count: 3
    label: "Art Display"
```

### Device Definition Fields

| Field                 | Required | Description                                                               |
| --------------------- | -------- | ------------------------------------------------------------------------- |
| `product_id`          | Yes      | LIFX product ID from registry                                             |
| `serial`              | No       | 12-character hex serial (e.g. `d073d5000001`). Auto-generated if not set. |
| `label`               | No       | Device label (max 32 characters)                                          |
| `power_level`         | No       | Initial power level (`0` = off, `65535` = on)                             |
| `color`               | No       | Initial HSBK color (dict or `[h, s, b, k]` list)                          |
| `location`            | No       | Location label (UUID auto-generated from label)                           |
| `group`               | No       | Group label (UUID auto-generated from label)                              |
| `zone_count`          | No       | Number of zones (multizone devices only)                                  |
| `zone_colors`         | No       | List of per-zone HSBK colors (multizone devices only)                     |
| `infrared_brightness` | No       | Initial IR brightness 0–65535 (infrared devices only)                     |
| `hev_cycle_duration`  | No       | HEV cycle duration in seconds (HEV devices only)                          |
| `hev_indication`      | No       | HEV indication enabled (HEV devices only)                                 |
| `tile_count`          | No       | Number of tiles (matrix devices only)                                     |
| `tile_width`          | No       | Tile width in zones (matrix devices only)                                 |
| `tile_height`         | No       | Tile height in zones (matrix devices only)                                |

#### HSBK Color Format

Colors can be specified as a dict or a compact list:

```yaml
# Verbose dict format
color:
  hue: 21845
  saturation: 65535
  brightness: 65535
  kelvin: 3500

# Compact list format [hue, saturation, brightness, kelvin]
color: [21845, 65535, 65535, 3500]
```

All values are uint16 (0–65535). Kelvin must be between 1500 and 9000.

The compact list format is especially useful for `zone_colors`:

```yaml
zone_colors:
  - [0, 65535, 65535, 3500]       # Red
  - [21845, 65535, 65535, 3500]   # Green
  - [43690, 65535, 65535, 3500]   # Blue
```

Combining Device Types

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
# testing-lab.yaml - Stateful devices with initial state in config
bind: 127.0.0.1
port: 56700
api: true

devices:
  - product_id: 27
    serial: d073d5000001
    label: "Test Bulb A"
    power_level: 65535
    color: [21845, 65535, 65535, 3500]
    location: "Lab"
    group: "Test Lights"
  - product_id: 27
    serial: d073d5000002
    label: "Test Bulb B"
    location: "Lab"
    group: "Test Lights"
  - product_id: 38
    serial: d073d5000003
    zone_count: 80
    label: "Test Beam"
  - product_id: 55
    serial: d073d5000004
    tile_count: 5
    label: "Test Tiles"
  - product_id: 90
    serial: d073d5000005
    label: "Test HEV"
    hev_cycle_duration: 7200
    hev_indication: true
```

### CI/CD Pipeline

```yaml
# ci-config.yaml - Isolated configuration for CI
bind: 127.0.0.1
port: 56701  # Non-standard port to avoid conflicts

verbose: false
api: false

# Use unique serial prefix for test isolation
serial_prefix: "cafe00"

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

devices:
  # Living room
  - product_id: 27
    label: "Living Room Lamp"
    power_level: 65535
    color: [0, 0, 65535, 3500]
    location: "Living Room"
    group: "Main Lights"
  - product_id: 38
    zone_count: 40
    label: "TV Backlight"
    location: "Living Room"
    group: "Entertainment"

  # Bedroom
  - product_id: 29
    label: "Bedroom Light"
    infrared_brightness: 16384
    location: "Bedroom"
    group: "Bedroom Lights"

  # Kitchen
  - product_id: 32
    zone_count: 16
    label: "Kitchen Strip"
    location: "Kitchen"
    group: "Kitchen Lights"

  # Office
  - product_id: 55
    tile_count: 5
    label: "Office Tiles"
    location: "Office"
    group: "Office"
```

### Multizone Testing

```yaml
# multizone-test.yaml - Various multizone configurations
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

## Scenarios

Configure test scenarios directly in the config file. Scenarios simulate protocol edge cases such as packet loss, delays, and malformed responses. They can be set at 5 scope levels with automatic precedence resolution (device > type > location > group > global).

```yaml
scenarios:
  # Global settings apply to all devices
  global:
    send_unhandled: true

  # Per-device scenarios (by serial)
  devices:
    d073d5000001:
      drop_packets:
        101: 0.5          # Drop 50% of GetColor responses
      response_delays:
        116: 0.2          # 200ms delay on GetPower responses

  # Per-type scenarios (color, multizone, matrix, hev, infrared)
  types:
    multizone:
      response_delays:
        506: 0.1          # 100ms delay on StateMultiZone

  # Per-location scenarios
  locations:
    Downstairs:
      drop_packets:
        101: 0.1          # 10% packet loss for downstairs devices

  # Per-group scenarios
  groups:
    Entertainment:
      malformed_packets:
        - 506             # Corrupt StateMultiZone for group
```

### Scenario Fields

| Field                  | Type                     | Description                             |
| ---------------------- | ------------------------ | --------------------------------------- |
| `drop_packets`         | `{packet_type: rate}`    | Drop rate 0.0–1.0 per packet type       |
| `response_delays`      | `{packet_type: seconds}` | Delay before responding                 |
| `malformed_packets`    | `[packet_type, ...]`     | Send truncated/corrupted responses      |
| `invalid_field_values` | `[packet_type, ...]`     | Send responses with all 0xFF bytes      |
| `firmware_version`     | `[major, minor]`         | Override firmware version               |
| `partial_responses`    | `[packet_type, ...]`     | Send incomplete multizone/tile data     |
| `send_unhandled`       | `bool`                   | Send StateUnhandled for unknown packets |

Replaces `--persistent-scenarios`

Config file scenarios replace the deprecated `--persistent-scenarios` flag. Use `lifx-emulator export-config` to migrate existing persistent scenarios.

## Migrating from Persistent Storage

If you have been using `--persistent` or `--persistent-scenarios`, you can migrate your saved state to a config file using the `export-config` command:

```bash
# Export saved device state and scenarios to a config file
lifx-emulator export-config --output my-config.yaml

# Export without scenarios
lifx-emulator export-config --no-scenarios --output devices-only.yaml

# Export from a custom storage directory
lifx-emulator export-config --storage-dir /path/to/storage --output config.yaml

# Print to stdout for inspection
lifx-emulator export-config
```

The exported config file includes all device state (serial, label, power, color, location, group, zone colors, infrared, HEV settings) and scenario configurations. You can then use this file instead of `--persistent`:

```bash
# Before (deprecated)
lifx-emulator --persistent

# After (recommended)
lifx-emulator --config my-config.yaml
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
1. **Use meaningful device labels** - Makes debugging and testing easier
1. **Separate configs by purpose** - Development, testing, CI/CD, etc.
1. **Use environment variable for defaults** - Set `LIFX_EMULATOR_CONFIG` for your preferred setup
1. **Override with CLI for one-off changes** - Don't modify config files for temporary adjustments
1. **Use the `devices` list for named devices** - Define individual devices with labels and specific configurations

## Troubleshooting

### Config File Not Loading

1. Check the file exists and is readable
1. Verify YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
1. Check for typos in field names (unknown fields are rejected)
1. Ensure the file is in the current directory for auto-detection

### Unexpected Device Count

Device type counts (`color`, `multizone`, etc.) are **added to** the `devices` list, not replaced by it. If you only want the devices in your `devices` list, don't set any type counts:

```yaml
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

- [CLI Reference](https://djelibeybi.github.io/lifx-emulator/cli/cli-reference/index.md) - Complete list of command-line options
- [Persistent Storage](https://djelibeybi.github.io/lifx-emulator/cli/storage/index.md) - Save device state across restarts
- [Device Management API](https://djelibeybi.github.io/lifx-emulator/cli/device-management-api/index.md) - Runtime device management
- [Scenarios Guide](https://djelibeybi.github.io/lifx-emulator/cli/scenarios/index.md) - Configure test scenarios
