# Storage API Reference

> Persistent storage for device state across emulator restarts

The storage module provides asynchronous persistent storage of device state using JSON files on disk. When enabled, device state (color, power, label, zones, tiles, etc.) is automatically saved and restored across emulator sessions with high-performance non-blocking I/O.

!!! note "CLI users"
    The CLI flags `--persistent` and `--persistent-scenarios` are deprecated. Use [config file device definitions](../cli/configuration.md#per-device-definitions) and [config file scenarios](../cli/configuration.md#scenarios) instead. The storage API documented here is unaffected and remains available for library users.

---

## Table of Contents

### Core Components

- [DevicePersistenceAsyncFile](#devicepersistenceasyncfile) - Async storage handler class
- [File Format](#file-format) - JSON state file specification
- [State Serialization](#state-serialization) - Converting state to/from JSON

### Concepts

- [Storage Location](#storage-location) - Where files are stored
- [Device Lifecycle](#device-lifecycle) - State save/load during device lifecycle
- [Backup and Restore](#backup-and-restore) - Managing saved states
- [CLI Integration](#cli-integration) - Using persistent storage from CLI

---

## DevicePersistenceAsyncFile

Main class for handling asynchronous persistent device state storage with smart debouncing and batch writes.

### Constructor

#### `DevicePersistenceAsyncFile(storage_dir: Path | str = DEFAULT_STORAGE_DIR, debounce_ms: int = 100, batch_size_threshold: int = 50)`

Initialize an async storage handler for device state persistence.

**Parameters:**
- **`storage_dir`** (`Path | str`) - Directory to store state files (default: `~/.lifx-emulator`)
- **`debounce_ms`** (`int`) - Milliseconds to wait before flushing pending saves (default: 100ms)
- **`batch_size_threshold`** (`int`) - Flush early if queue exceeds this size (default: 50)

**Example:**
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

# Use default location (~/.lifx-emulator)
storage = DevicePersistenceAsyncFile()

# Use custom location with custom debounce settings
storage = DevicePersistenceAsyncFile(
    "/var/lib/lifx-emulator",
    debounce_ms=200,
    batch_size_threshold=100
)
```

### Methods

#### `async save_device_state(device_state: DeviceState) -> None`

Queue device state for saving (non-blocking async).

Queues the device state for saving. The write is performed asynchronously with debouncing to minimize I/O overhead.

**Parameters:**
- **`device_state`** (`DeviceState`) - Device state to persist

**Returns:** `None` (task runs in background)

**Example:**
```python
import asyncio

from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light


async def main():
    storage = DevicePersistenceAsyncFile()
    device = create_color_light("d073d5000001")
    device.state.label = "Living Room"
    device.state.power_level = 65535

    # Queue state for async save (non-blocking)
    await storage.save_device_state(device.state)

    # Flush pending writes before the event loop exits
    await storage.shutdown()

    # File is now at: ~/.lifx-emulator/d073d5000001.json


asyncio.run(main())
```

#### `load_device_state(serial: str) -> dict[str, Any] | None`

Load device state from disk (synchronous).

Reads the JSON file for the specified serial and returns the deserialized state dictionary. Returns `None` if the file doesn't exist or cannot be loaded.

**Parameters:**
- **`serial`** (`str`) - Device serial to load

**Returns:** `dict[str, Any] | None` - State dictionary or `None` if not found

**Example:**
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()
state_dict = storage.load_device_state("d073d5000001")

if state_dict:
    print(f"Label: {state_dict['label']}")
    print(f"Power: {state_dict['power_level']}")
else:
    print("No saved state found")
```

#### `async delete_device_state(serial: str) -> bool`

Delete saved state for a device.

Discards any queued write for the serial and removes its JSON file from disk.

**Parameters:**
- **`serial`** (`str`) - Device serial to delete

**Returns:** `bool` - `True` if a state file was removed

**Example:**
```python
import asyncio

from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()
asyncio.run(storage.delete_device_state("d073d5000001"))
# Removes: ~/.lifx-emulator/d073d5000001.json
```

#### `list_devices() -> list[str]`

List all devices with saved state (synchronous).

Returns a list of device serials that have saved state files in the storage directory.

**Returns:** `list[str]` - List of device serials

**Example:**
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()
devices = storage.list_devices()
print(f"Found {len(devices)} saved devices:")
for serial in devices:
    print(f"  - {serial}")
```

#### `delete_all_device_states() -> int`

Delete all saved device states (synchronous).

Removes all `.json` files from the storage directory.

**Returns:** `int` - Number of devices deleted

**Example:**
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()
count = storage.delete_all_device_states()
print(f"Deleted {count} device states")
```

---

## File Format

Device state is saved as JSON files with the naming convention `{serial}.json`.

### JSON Structure

```json
{
  "serial": "d073d5000001",
  "product": 27,
  "label": "Living Room Light",
  "power_level": 65535,
  "color": {
    "hue": 21845,
    "saturation": 65535,
    "brightness": 32768,
    "kelvin": 3500
  },
  "location_id": "01234567-89ab-cdef-0123-456789abcdef",
  "location_label": "Home",
  "group_id": "fedcba98-7654-3210-fedc-ba9876543210",
  "group_label": "Living Room",
  "infrared_brightness": 0,
  "hev_cycle_duration_s": 7200,
  "hev_cycle_remaining_s": 0,
  "zone_count": 0,
  "zone_colors": [],
  "tile_count": 0,
  "tile_devices": []
}
```

### Multizone Device Example

```json
{
  "serial": "d073d5000002",
  "product": 32,
  "label": "Kitchen Strip",
  "power_level": 65535,
  "color": {
    "hue": 0,
    "saturation": 0,
    "brightness": 65535,
    "kelvin": 3500
  },
  "zone_count": 16,
  "zone_colors": [
    {"hue": 0, "saturation": 65535, "brightness": 32768, "kelvin": 3500},
    {"hue": 21845, "saturation": 65535, "brightness": 32768, "kelvin": 3500},
    ...
  ]
}
```

### Matrix Device Example

```json
{
  "serial": "d073d5000003",
  "product": 55,
  "label": "Wall Art",
  "power_level": 65535,
  "tile_count": 5,
  "tile_width": 8,
  "tile_height": 8,
  "tile_devices": [
    {
      "user_x": 0.0,
      "user_y": 0.0,
      "width": 8,
      "height": 8,
      "colors": [...]
    },
    ...
  ]
}
```

---

## State Serialization

The `state_serializer` module handles conversion between DeviceState objects and JSON-compatible dictionaries.

### `serialize_device_state(device_state: DeviceState) -> dict`

Convert DeviceState to JSON-compatible dictionary.

**Parameters:**
- **`device_state`** (`DeviceState`) - State to serialize

**Returns:** `dict` - JSON-compatible dictionary

**Example:**
```python
from lifx_emulator.devices.state_serializer import serialize_device_state
from lifx_emulator.factories import create_color_light

device = create_color_light("d073d5000001")
device.state.label = "Test Light"
state_dict = serialize_device_state(device.state)
# state_dict is JSON-compatible dict
```

### `deserialize_device_state(state_dict: dict) -> dict`

Convert JSON dictionary back to DeviceState-compatible format.

**Parameters:**
- **`state_dict`** (`dict`) - Serialized state dictionary

**Returns:** `dict` - Deserialized state dictionary

**Example:**
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()

# load_device_state() calls deserialize_device_state() for you
loaded_dict = storage.load_device_state("d073d5000001")
if loaded_dict:
    print(f"Label: {loaded_dict['label']}")
```

---

## Storage Location

### Default Location

By default, device state files are stored in:

- **Linux/macOS**: `~/.lifx-emulator/`
- **Windows**: `C:\Users\{username}\.lifx-emulator\`

### Custom Location

You can specify a custom storage directory:

```python
from pathlib import Path
from lifx_emulator.devices import DevicePersistenceAsyncFile

# Project-specific storage
storage = DevicePersistenceAsyncFile("./lifx_state")

# System-wide storage (requires permissions)
storage = DevicePersistenceAsyncFile("/var/lib/lifx-emulator")

# Temporary storage (for testing)
import tempfile
storage = DevicePersistenceAsyncFile(tempfile.mkdtemp())
```

---

## Device Lifecycle

### State Restoration on Device Creation

When creating a device with storage enabled, existing state is automatically restored:

```python
import asyncio

from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light


async def main():
    storage = DevicePersistenceAsyncFile()

    # First run: Create device and save state
    device = create_color_light(serial="d073d5000001", storage=storage)
    device.state.label = "Living Room"
    device.state.power_level = 65535
    await storage.save_device_state(device.state)  # Queue async save
    await storage.shutdown()  # Flush pending writes

    # Later run: State is automatically restored
    storage = DevicePersistenceAsyncFile()
    device = create_color_light(serial="d073d5000001", storage=storage)
    print(device.state.label)  # Living Room
    print(device.state.power_level)  # 65535


asyncio.run(main())
```

### Automatic State Saving

Device state is automatically saved when:

- Device properties are updated via protocol packets (SetColor, SetPower, SetLabel, etc.)
- Device is properly shut down (via context manager or explicit save)

**Example with automatic saving:**
```python
import asyncio

from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device


async def main():
    storage = DevicePersistenceAsyncFile()
    device = create_color_light("d073d5000001", storage=storage)

    # Simulate a SetLabel packet
    packet = Device.SetLabel(label="Kitchen Light")
    header = LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=Device.SetLabel.PKT_TYPE,
    )
    device.process_packet(header, packet)

    # State is automatically queued for saving after processing.
    # Drain the device's pending saves, then flush storage to disk.
    await device.close()
    await storage.shutdown()
    print(storage.load_device_state("d073d5000001")["label"])  # Kitchen Light


asyncio.run(main())
```

### Manual State Management

For fine-grained control, use manual save/load:

```python
import asyncio

# Manual async save
await storage.save_device_state(device.state)

# Manual load (during initialization)
state_dict = storage.load_device_state(serial)
if state_dict:
    # Apply loaded state to device
    device.state.label = state_dict['label']
    device.state.power_level = state_dict['power_level']
    # ... etc
```

---

## Backup and Restore

### Creating Backups

```python
import shutil
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()

# Backup entire storage directory
shutil.copytree(storage.storage_dir, "/backup/lifx-emulator-backup")

# Backup single device
device_path = storage.storage_dir / "d073d5000001.json"
shutil.copy(device_path, "/backup/d073d5000001.json.bak")
```

### Restoring from Backup

```python
import shutil

# Restore entire storage directory
shutil.copytree("/backup/lifx-emulator-backup", "~/.lifx-emulator", dirs_exist_ok=True)

# Restore single device
shutil.copy("/backup/d073d5000001.json.bak", "~/.lifx-emulator/d073d5000001.json")
```

### Exporting Device State

```python
import json
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()

# Export all device states to a single file. Read the raw JSON files:
# load_device_state() returns deserialised objects that aren't JSON-serialisable.
all_states = {}
for serial in storage.list_devices():
    with open(storage.storage_dir / f"{serial}.json") as f:
        all_states[serial] = json.load(f)

with open("lifx-export.json", "w") as f:
    json.dump(all_states, f, indent=2)
```

### Importing Device State

Saved state files are plain JSON, so importing is a matter of writing each state back to the storage directory. The next time a device with that serial is created with the same storage, its state is restored.

The serials come from an untrusted file, so validate every one and check that each destination stays inside the storage directory (resolving symlinks) before writing anything:

```python
import json
import os
import re

from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_device

SERIAL_RE = re.compile(r"[0-9a-fA-F]{12}")

storage = DevicePersistenceAsyncFile()
root = os.path.realpath(storage.storage_dir)

# Import from exported file
with open("lifx-export.json") as f:
    all_states = json.load(f)

# Validate every serial and destination before writing any files
destinations = {}
for serial in all_states:
    if not SERIAL_RE.fullmatch(serial):
        raise ValueError(f"Invalid device serial: {serial!r}")
    path = os.path.realpath(os.path.join(root, f"{serial}.json"))
    if not path.startswith(root + os.sep):
        raise ValueError(f"State path for {serial} escapes the storage directory")
    destinations[serial] = path

for serial, state_dict in all_states.items():
    with open(destinations[serial], "w") as f:
        json.dump(state_dict, f, indent=2)

print(f"Imported {len(all_states)} devices")

# Recreate a device; its saved state is restored automatically
serial, state_dict = next(iter(all_states.items()))
device = create_device(state_dict["product"], serial=serial, storage=storage)
print(device.state.label)
```

---

## CLI Integration

!!! warning "Deprecated"
    The `--persistent` CLI flag is deprecated. Use [config file device definitions](../cli/configuration.md#per-device-definitions) instead. Run `lifx-emulator export-config` to migrate.

### Enabling Persistent Storage from CLI

Use the `--persistent` flag to enable state persistence:

```bash
# Enable persistence with default location (~/.lifx-emulator)
lifx-emulator --persistent

# Create devices and modify state
# State changes are automatically saved

# Stop and restart emulator - state is restored
lifx-emulator --persistent
```

### Viewing Saved Devices

```bash
# List saved devices
ls ~/.lifx-emulator/

# View device state
cat ~/.lifx-emulator/d073d5000001.json

# Pretty print
python -m json.tool ~/.lifx-emulator/d073d5000001.json
```

### Clearing Persistent Storage

```bash
# Remove all saved states
rm -rf ~/.lifx-emulator/

# Remove specific device
rm ~/.lifx-emulator/d073d5000001.json
```

### Programmatic CLI Access

```python
from lifx_emulator.devices import DevicePersistenceAsyncFile

storage = DevicePersistenceAsyncFile()

# List devices
print("Saved devices:")
for serial in storage.list_devices():
    state = storage.load_device_state(serial)
    if state:
        print(f"  {serial}: {state.get('label', 'Unnamed')}")

# Clear all
count = storage.delete_all_device_states()
print(f"Cleared {count} device states")
```

---

## Best Practices

### 1. Always Use Same Serial Numbers

For state persistence to work, devices must use consistent serial numbers:

```python
# Good: Fixed serial
device = create_color_light(serial="d073d5000001", storage=storage)

# Bad: Random serial (state won't persist)
import uuid
device = create_color_light(serial=uuid.uuid4().hex[:12], storage=storage)
```

### 2. Handle Storage Errors Gracefully

Storage operations may fail due to permissions, disk space, etc:

```python
from lifx_emulator.devices import DevicePersistenceError

try:
    await storage.commit_device_state(device.state)  # Save and flush to disk now
except DevicePersistenceError as e:
    logger.error("Failed to save state: %s", e)
    # Continue without persistence
```

### 3. Validate Restored State

Always validate restored state before using it:

```python
state_dict = storage.load_device_state(serial)
if state_dict:
    # Validate product ID matches
    if state_dict.get('product') != expected_product:
        logger.warning("Product ID mismatch, ignoring saved state")
        state_dict = None
```

### 4. Use Context Managers for Cleanup

Ensure state is saved on cleanup:

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_device(serial, storage):
    device = create_color_light(serial=serial, storage=storage)
    try:
        yield device
    finally:
        # Ensure state is saved on exit
        await storage.save_device_state(device.state)

async def main():
    async with managed_device("d073d5000001", storage) as device:
        # Use device
        device.state.power_level = 65535
    # State automatically saved on exit

asyncio.run(main())
```

### 5. Regular Backups

For production use, create regular backups:

```bash
#!/bin/bash
# Backup script
BACKUP_DIR="/backup/lifx-emulator/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp -r ~/.lifx-emulator/* "$BACKUP_DIR/"
echo "Backed up to $BACKUP_DIR"
```

---

## Troubleshooting

### State Not Persisting

**Problem:** Changes aren't saved between restarts

**Solutions:**
1. Verify `--persistent` flag is used
2. Check storage directory exists and is writable
3. Ensure consistent serial numbers
4. Check logs for save errors

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Will show "Saved state for device..." messages
```

### Permission Errors

**Problem:** Cannot write to storage directory

**Solutions:**
1. Check directory permissions: `ls -la ~/.lifx-emulator`
2. Use custom directory with proper permissions
3. Run with appropriate user permissions

### Corrupted State Files

**Problem:** Invalid JSON or deserialization errors

**Solutions:**
```python
# Validate and repair
import json
from pathlib import Path

storage_dir = Path.home() / ".lifx-emulator"
for file_path in storage_dir.glob("*.json"):
    try:
        with open(file_path) as f:
            json.load(f)
        print(f"✓ {file_path.name}")
    except json.JSONDecodeError:
        print(f"✗ {file_path.name} - CORRUPTED")
        # Delete or repair
        file_path.unlink()
```

---

## References

**Source Files:**
- `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py` - Async storage implementation (`DevicePersistenceAsyncFile`)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py` - State serialisation
- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py` - Restoring saved state into new devices

**Related Documentation:**
- [Device API](device.md) - Device state structure
- [CLI Reference](../cli/cli-reference.md) - CLI flags reference
- [Configuration File Guide](../cli/configuration.md) - Recommended replacement for `--persistent`

**See Also:**
- Persistent storage is optional and disabled by default
- Storage uses standard JSON format for easy inspection and editing
- State files can be manually edited (stop emulator first)
- Storage directory can be version controlled for test fixtures
