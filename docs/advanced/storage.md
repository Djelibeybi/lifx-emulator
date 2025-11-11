# Persistent Storage Guide

> Save and restore device state across emulator sessions

The LIFX Emulator supports optional persistent storage that automatically saves device state (color, power, labels, zone colors, etc.) to disk and restores it when the emulator restarts.

## Overview

With persistent storage enabled, device state survives emulator restarts, making it useful for:

- Testing long-running applications with stateful devices
- Preserving test setup between development sessions
- Simulating real-world device behavior where state persists

## Quick Start

Enable persistent storage from the CLI:

```bash
# Start emulator with persistent storage
lifx-emulator --persistent

# State will be saved and restored across restarts
```

Or from Python:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.async_storage import AsyncDeviceStorage

async def main():
    # Create storage handler
    storage = AsyncDeviceStorage()

    # Create device with storage
    device = create_color_light("d073d5000001", storage=storage)

    # State changes are automatically saved
    device.state.label = "My Light"
    device.state.color.hue = 21845  # 120 degrees

    # Start server
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    await server.start()

    # Device state will be restored on next run with same serial

asyncio.run(main())
```

## Storage Location

By default, device state is stored in `~/.lifx-emulator/`:

```bash
~/.lifx-emulator/
├── d073d5000001.json  # State for first device
├── d073d5000002.json  # State for second device
└── d073d8000001.json  # State for multizone device
```

### Custom Storage Directory

```python
from lifx_emulator.async_storage import AsyncDeviceStorage

# Use custom directory
storage = AsyncDeviceStorage("/var/lib/lifx-emulator")

# Now state files will be stored in /var/lib/lifx-emulator/
```

## What Gets Saved

The following device state is persisted:

- **Label** - Device name
- **Power Level** - On/off and brightness
- **Color** - Hue, saturation, brightness, kelvin (for color lights)
- **Location** - Device location
- **Group** - Device group
- **Zone Colors** - Individual zone colors (for multizone devices)
- **Tile Colors** - Individual tile colors (for matrix devices)
- **Infrared Brightness** - IR brightness level (for IR capable devices)
- **HEV State** - HEV cycle state (for HEV capable devices)

## State File Format

Device state is stored as JSON:

```json
{
  "serial": "d073d5000001",
  "product_id": 27,
  "label": "Living Room Light",
  "power_level": 65535,
  "color": {
    "hue": 21845,
    "saturation": 65535,
    "brightness": 32768,
    "kelvin": 4000
  },
  "location": "Living Room",
  "group": "Main Lights",
  "zone_colors": [],
  "tile_devices": [],
  "infrared_brightness": 0,
  "hev_state": null
}
```

## Restoration on Startup

When a device is created with the same serial as a previously saved device, its state is automatically restored:

```python
from lifx_emulator.async_storage import AsyncDeviceStorage
from lifx_emulator import create_color_light

storage = AsyncDeviceStorage()

# First session - state is created
device1 = create_color_light("d073d5000001", storage=storage)
device1.state.label = "Kitchen Light"
device1.state.color.hue = 10923  # Orange

# State changes are automatically queued for saving
# (saved asynchronously with debouncing)

# Later session - state is restored
device2 = create_color_light("d073d5000001", storage=storage)
assert device2.state.label == "Kitchen Light"
assert device2.state.color.hue == 10923
```

## Automatic Saving

Device state is automatically saved (asynchronously) after certain operations:

```python
device = create_color_light("d073d5000001", storage=storage)

# These automatically trigger async saves with debouncing:
# - Color changes (via protocol packets)
# - Power state changes
# - Label changes
# - Group/Location changes

# AsyncDeviceStorage queues saves and flushes with debouncing
# to minimize I/O overhead (default: 100ms debounce)
```

The `AsyncDeviceStorage` class provides high-performance non-blocking saves by:

- **Debouncing**: Coalescing rapid changes to the same device
- **Batch writes**: Grouping multiple devices in single flush
- **Executor-based I/O**: Running I/O in background thread
- **Adaptive flushing**: Flushing early if queue size threshold is reached

## Advanced Usage

### Managing Multiple Devices

```python
from lifx_emulator.async_storage import AsyncDeviceStorage
from lifx_emulator import create_color_light, create_multizone_light

storage = AsyncDeviceStorage()

# Create multiple devices - each maintains its own state file
devices = [
    create_color_light("d073d5000001", storage=storage),
    create_color_light("d073d5000002", storage=storage),
    create_multizone_light("d073d8000001", storage=storage),
]

# All state is independently persisted and restored asynchronously
```

### Clearing Saved State

```python
storage = AsyncDeviceStorage()

# Delete saved state for one device (synchronous)
storage.delete_device_state("d073d5000001")

# Delete all saved state
storage.delete_all_device_states()

# List all saved devices
devices = storage.list_devices()
```

### Backup and Restore

```bash
# Backup device state
cp -r ~/.lifx-emulator ~/.lifx-emulator.backup

# Restore from backup
cp -r ~/.lifx-emulator.backup/* ~/.lifx-emulator/
```

## Scenarios with Persistent Storage

Combine persistent storage with test scenarios:

```python
from lifx_emulator import create_color_light
from lifx_emulator.async_storage import AsyncDeviceStorage
from lifx_emulator.scenarios.manager import ScenarioConfig

storage = AsyncDeviceStorage()
device = create_color_light("d073d5000001", storage=storage)

# Configure scenario
device.scenarios = ScenarioConfig(
    response_delays={101: 0.5}  # 500ms delay on GetColor
)

# State + scenario config both persist across restarts
```

## Persistent Scenarios

In addition to device state, test scenarios can also be persisted:

```bash
# Enable both device state and scenario persistence
lifx-emulator --persistent --persistent-scenarios
```

This saves scenario configurations to `~/.lifx-emulator/scenarios.json`.

## API Reference

For complete API documentation, see:

- [Storage API Reference](../api/storage.md)
- [AsyncDeviceStorage class reference](../api/storage.md#asyncdevicestorage)
- [File format specification](../api/storage.md#file-format)

## Troubleshooting

### Saved State Not Loading

1. Check that the serial matches exactly (case-sensitive hex)
2. Verify the file exists: `ls ~/.lifx-emulator/`
3. Check file permissions: `ls -la ~/.lifx-emulator/`
4. Check for JSON syntax errors: `cat ~/.lifx-emulator/{serial}.json | python -m json.tool`

### Storage Directory Issues

```bash
# Ensure storage directory exists with proper permissions
mkdir -p ~/.lifx-emulator
chmod 700 ~/.lifx-emulator

# Check for disk space
df -h ~/.lifx-emulator
```

### Clearing All State

```bash
# Remove all saved state
rm -rf ~/.lifx-emulator/

# Or use the API
from lifx_emulator.async_storage import AsyncDeviceStorage
storage = AsyncDeviceStorage()
for serial in storage.list_devices():
    storage.delete_device_state(serial)
```

## Best Practices

1. **Use storage for integration tests** - Persist state across test sessions
2. **Back up important state** - Use `cp -r ~/.lifx-emulator ~/.lifx-emulator.backup`
3. **Clean up after tests** - Delete device state when tests complete
4. **Use meaningful serials** - Make it easy to identify saved devices
5. **Version your state** - Keep track of state changes in git if needed

## Next Steps

- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Combine with error scenarios
- [Storage API Reference](../api/storage.md) - Detailed API documentation
- [Advanced Testing Guide](../guide/integration-testing.md) - Integration patterns
