# Persistent Storage Guide

> Save and restore device state across emulator sessions

!!! warning "Deprecated"
    `--persistent` and `--persistent-scenarios` are deprecated and will be removed in a future release. Use [config file device definitions](configuration.md#per-device-definitions) and [config file scenarios](configuration.md#scenarios) instead.

    **To migrate**, run `lifx-emulator export-config --output my-config.yaml` to convert your saved state into a config file. See [Migration to Config File](#migration-to-config-file) below.

The LIFX Emulator supports optional persistent storage that saves device state (colour, power, labels, zone colours, etc.) to disk and restores it when the emulator restarts.

## Overview

With persistent storage enabled, device state survives emulator restarts, making it useful for:

- Testing long-running applications with stateful devices
- Preserving test setup between development sessions
- Simulating real-world device behaviour where state persists

## Quick Start

Enable persistent storage from the CLI:

```bash
# Start emulator with persistent storage and devices
lifx-emulator --persistent --color 2

# On subsequent runs, saved devices are restored automatically
lifx-emulator --persistent
```

Or from Python:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DevicePersistenceAsyncFile, DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create storage handler (uses ~/.lifx-emulator by default)
    storage = DevicePersistenceAsyncFile()

    # Create device with storage; saved state for this serial is restored
    device = create_color_light("d073d5000001", storage=storage)

    # Direct state assignments are not saved automatically, so queue a save
    device.state.label = "My Light"
    device.state.color.hue = 21845  # 120 degrees
    await storage.save_device_state(device.state)

    # Start server; packets that change state (SetColor, SetLabel, ...) are
    # saved automatically from here on
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:
        await asyncio.sleep(60)

    # Drain the device's pending saves and flush everything to disk
    await device.close()
    await storage.shutdown()


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
from lifx_emulator.devices import DevicePersistenceAsyncFile

# Use custom directory
storage = DevicePersistenceAsyncFile("/var/lib/lifx-emulator")

# Now state files will be stored in /var/lib/lifx-emulator/
```

## What Gets Saved

The following device state is persisted:

- **Label** - Device name
- **Power Level** - On/off and brightness
- **Colour** - Hue, saturation, brightness, kelvin
- **Location** - Location ID and label
- **Group** - Group ID and label
- **Zone Colours** - Zone count, individual zone colours and effect (for multizone devices)
- **Tile Colours** - Tile count, per-tile colours, framebuffers and effect (for matrix devices)
- **Infrared Brightness** - IR brightness level (for IR capable devices)
- **HEV State** - HEV cycle duration, remaining time, indication and last result (for HEV capable devices)

## State File Format

Device state is stored as JSON. Fields for optional capabilities (zones, tiles, infrared, HEV) are only present for devices that have them:

```json
{
  "serial": "d073d5000001",
  "label": "Living Room Light",
  "product": 91,
  "power_level": 65535,
  "connectivity": "wifi",
  "color": {
    "hue": 21845,
    "saturation": 65535,
    "brightness": 32768,
    "kelvin": 3500
  },
  "location_id": "b70ff23357854504bbe3d8776ecd07ee",
  "location_label": "Living Room",
  "location_updated_at": 1790869329617617920,
  "group_id": "fe2c95b58b90418eb667c93b10b30195",
  "group_label": "Main Lights",
  "group_updated_at": 1790869329617624064,
  "has_color": true,
  "has_infrared": false,
  "has_multizone": false,
  "has_matrix": false,
  "has_hev": false
}
```

## Restoration on Startup

When a device is created with the same serial and storage as a previously saved device, its state is restored automatically. Saves are queued and written in the background, so flush them with `await storage.shutdown()` before the state is guaranteed to be on disk:

```python
import asyncio

from lifx_emulator import create_color_light
from lifx_emulator.devices import DevicePersistenceAsyncFile


async def main():
    # First session - create state and save it
    storage = DevicePersistenceAsyncFile()
    device1 = create_color_light("d073d5000001", storage=storage)
    device1.state.label = "Kitchen Light"
    device1.state.color.hue = 10923  # Orange
    await storage.save_device_state(device1.state)  # Queue async save
    await storage.shutdown()  # Flush pending writes to disk

    # Later session - state is restored
    storage = DevicePersistenceAsyncFile()
    device2 = create_color_light("d073d5000001", storage=storage)
    assert device2.state.label == "Kitchen Light"
    assert device2.state.color.hue == 10923


asyncio.run(main())
```

## Automatic Saving

Device state is saved automatically (and asynchronously) after any state-changing protocol packet, such as:

- `SetColor`, `SetWaveform` and `SetWaveformOptional`
- `SetPower` and `SetLightPower`
- `SetLabel`, `SetLocation` and `SetGroup`
- Zone and tile setters (`SetColorZones`, `ExtendedSetColorZones`, `Set64`, `CopyFrameBuffer`)

Assigning to `device.state` directly does **not** queue a save. Call `await storage.save_device_state(device.state)` after changing state in code.

```python
import asyncio

from lifx_emulator import create_color_light
from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device


async def main():
    storage = DevicePersistenceAsyncFile()
    device = create_color_light("d073d5000001", storage=storage)

    # A SetLabel packet changes state, so a save is queued automatically
    header = LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=Device.SetLabel.PKT_TYPE,
    )
    device.process_packet(header, Device.SetLabel(label="Kitchen Light"))

    # Drain the device's pending saves, then flush storage to disk
    await device.close()
    await storage.shutdown()
    print(storage.load_device_state("d073d5000001")["label"])  # Kitchen Light


asyncio.run(main())
```

The `DevicePersistenceAsyncFile` class provides high-performance non-blocking saves by:

- **Debouncing**: Coalescing rapid changes to the same device (default: 100ms)
- **Batch writes**: Grouping multiple devices in a single flush
- **Executor-based I/O**: Running I/O in a background thread
- **Adaptive flushing**: Flushing early if the queue size threshold is reached

## Advanced Usage

### Managing Multiple Devices

```python
from lifx_emulator import create_color_light, create_multizone_light
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()

# Create multiple devices - each maintains its own state file
devices = [
    create_color_light("d073d5000001", storage=storage),
    create_color_light("d073d5000002", storage=storage),
    create_multizone_light("d073d8000001", storage=storage),
]

# All state is independently persisted and restored
```

### Clearing Saved State

```python
import asyncio

from lifx_emulator.devices import DevicePersistenceAsyncFile


async def main():
    storage = DevicePersistenceAsyncFile()

    # List all saved devices
    print(storage.list_devices())

    # Delete saved state for one device (async; True if a file was removed)
    removed = await storage.delete_device_state("d073d5000001")

    # Delete all saved state (synchronous; returns the number deleted)
    count = storage.delete_all_device_states()


asyncio.run(main())
```

### Backup and Restore

```bash
# Backup device state
cp -r ~/.lifx-emulator ~/.lifx-emulator.backup

# Restore from backup
cp -r ~/.lifx-emulator.backup/* ~/.lifx-emulator/
```

## Scenarios with Persistent Storage

Device storage only saves device state; scenarios are not part of it. Configure scenarios with a `HierarchicalScenarioManager` and pass the same manager to both the factory and the server (the server assigns its own scenario manager to every device it manages):

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DevicePersistenceAsyncFile, DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    storage = DevicePersistenceAsyncFile()
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(response_delays={101: 0.5}),  # 500ms delay on GetColor
    )

    device = create_color_light(
        "d073d5000001", storage=storage, scenario_manager=manager
    )
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        await asyncio.sleep(60)

    # Device state persists across restarts; the scenario does not
    await device.close()
    await storage.shutdown()


asyncio.run(main())
```

To persist scenarios too, save the manager with `ScenarioPersistenceAsyncFile` (see below) or, preferably, define them in a [config file](configuration.md#scenarios).

## Persistent Scenarios

!!! warning "Deprecated"
    Use [config file scenarios](configuration.md#scenarios) instead.

In addition to device state, test scenarios can also be persisted:

```bash
# Enable both device state and scenario persistence (deprecated)
lifx-emulator --persistent --persistent-scenarios
```

This saves scenario configurations to `~/.lifx-emulator/scenarios.json`. Library users can do the same with `ScenarioPersistenceAsyncFile`:

```python
import asyncio

from lifx_emulator.scenarios import ScenarioConfig, ScenarioPersistenceAsyncFile


async def main():
    scenario_storage = ScenarioPersistenceAsyncFile()  # ~/.lifx-emulator

    # Load saved scenarios (an empty manager if none are saved)
    manager = await scenario_storage.load()
    manager.set_global_scenario(ScenarioConfig(drop_packets={101: 0.3}))

    # Write ~/.lifx-emulator/scenarios.json
    await scenario_storage.save(manager)


asyncio.run(main())
```

## API Reference

For complete API documentation, see:

- [Storage API Reference](../library/storage.md)
- [File format specification](../library/storage.md#file-format)

## Migration to Config File

The `export-config` command converts your persistent storage into a YAML config file that replaces `--persistent` and `--persistent-scenarios`:

```bash
# Export everything (device state + scenarios)
lifx-emulator export-config --output my-config.yaml

# Export without scenarios
lifx-emulator export-config --no-scenarios --output devices-only.yaml

# Export from a custom storage directory
lifx-emulator export-config --storage-dir /path/to/storage --output config.yaml

# Preview by printing to stdout
lifx-emulator export-config
```

After exporting, switch from `--persistent` to `--config`:

```bash
# Before (deprecated)
lifx-emulator --persistent --persistent-scenarios

# After (recommended)
lifx-emulator --config my-config.yaml
```

The config file approach offers several advantages over persistent storage:

- **Version control** — config files can be committed to git
- **Reproducibility** — start from a known state every time
- **Sharing** — config files are easy to share across teams
- **Transparency** — all state is visible in a single YAML file

See the [Configuration File Guide](configuration.md) for full details on config file options.

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

# Or use the clear-storage command
lifx-emulator clear-storage
```

Or from Python:

```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()
count = storage.delete_all_device_states()
print(f"Deleted {count} device states")
```

## Next Steps

Migrate to config files for a better experience:

- [Configuration File Guide](configuration.md) - Recommended replacement for persistent storage
- [Storage API Reference](../library/storage.md) - Detailed API documentation for library users
