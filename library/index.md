# Python Library Reference

Complete Python library documentation for the LIFX Emulator core library (`lifx-emulator-core`).

## Overview

The LIFX Emulator library is designed for simplicity and ease of use. Most users only need the factory functions, server class, and required manager/repository components.

## Reading This Guide

This reference is organized from most common to advanced usage:

1. **[Factory Functions](factories/)** - Creating devices (most common)
1. **[Server](server/)** - Server setup and configuration
1. **[Device](device/)** - Device API and state management
1. **[Products](products/)** - Product registry and specs
1. **[Protocol](protocol/)** - Low-level protocol types (advanced)
1. **[Storage](storage/)** - Persistent state (advanced)

## Quick Start

### Installation

**Recommended:** Using [uv](https://astral.sh/uv):

```bash
uv add lifx-emulator-core
```

**Alternative:** Using pip:

```bash
pip install lifx-emulator-core
```

### Basic Usage

```python
import asyncio
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

async def main():
    # Create a device
    device = create_color_light("d073d5000001")

    # Set up repository and manager (required)
    device_repository = DeviceRepository()
    device_manager = DeviceManager(device_repository)

    # Start server
    async with EmulatedLifxServer(
        [device], device_manager, "127.0.0.1", 56700
    ) as server:
        # Server is running, test your LIFX library here
        await asyncio.Event().wait()

asyncio.run(main())
```

## Core Components

### 1. Factory Functions (Most Common)

Use these to create devices easily:

```python
from lifx_emulator.factories import (
    create_color_light,             # RGB color lights
    create_color_temperature_light, # White temperature lights
    create_infrared_light,          # IR-capable lights
    create_hev_light,               # HEV cleaning lights
    create_multizone_light,         # Linear strips
    create_tile_device,             # Matrix tiles
    create_switch,                  # Relay switches
    create_device,                  # Universal factory
)
```

👉 **[Full Factory Documentation](factories/)**

### 2. Server

The server manages UDP communication and device routing:

```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

# Create repository and manager (required)
device_repository = DeviceRepository()
device_manager = DeviceManager(device_repository)

# Create server
server = EmulatedLifxServer(
    devices, device_manager, "127.0.0.1", 56700
)

# Use as context manager (recommended)
async with server:
    # Server running
    pass

# Or manual lifecycle
await server.start()
await server.stop()
```

👉 **[Full Server Documentation](server/)**

### 3. Device (Advanced)

For custom device creation:

```python
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState

state = DeviceState(serial="d073d5000001", label="Custom Device")
device = EmulatedLifxDevice(state)
```

👉 **[Full Device Documentation](device/)**

### 4. Product Registry

Access official LIFX product definitions:

```python
from lifx_emulator.products.registry import get_product, get_registry

product = get_product(27)  # LIFX A19
all_products = get_registry()
```

👉 **[Full Product Documentation](products/)**

## Quick Reference

### Creating Devices

| Function                           | Product                      | Description                |
| ---------------------------------- | ---------------------------- | -------------------------- |
| `create_color_light()`             | LIFX A19 (27)                | Standard RGB color light   |
| `create_color_temperature_light()` | LIFX Mini White to Warm (50) | Variable color temperature |
| `create_infrared_light()`          | LIFX A19 Night Vision (29)   | IR capable light           |
| `create_hev_light()`               | LIFX Clean (90)              | HEV cleaning light         |
| `create_multizone_light()`         | LIFX Z (32) or Beam (38)     | Linear multizone strip     |
| `create_tile_device()`             | LIFX Tile (55)               | Tile matrix                |
| `create_switch()`                  | LIFX Switch (70)             | Relay-based switch         |
| `create_device()`                  | Any product ID               | Universal factory          |

### Server Context Manager

The server can be used as an async context manager:

```python
device_manager = DeviceManager(DeviceRepository())

async with EmulatedLifxServer(
    devices, device_manager, "127.0.0.1", 56700
) as server:
    # Server is running
    # Your test code here
    pass
# Server automatically stops
```

### Server Lifecycle

Manual server lifecycle management:

```python
device_manager = DeviceManager(DeviceRepository())
server = EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)

await server.start()  # Start listening
# ... do work ...
await server.stop()   # Stop server
```

## Module Structure

```text
lifx_emulator/
├── __init__.py           # Public exports
├── server.py             # EmulatedLifxServer
├── devices/
│   ├── device.py         # EmulatedLifxDevice
│   ├── states.py         # DeviceState
│   ├── manager.py        # DeviceManager
│   └── persistence.py    # DevicePersistenceAsyncFile
├── repositories/
│   ├── device_repository.py  # DeviceRepository
│   └── storage_backend.py    # Storage interfaces
├── factories/
│   └── factory.py        # create_* factory functions
├── scenarios/
│   ├── manager.py        # HierarchicalScenarioManager
│   └── models.py         # ScenarioConfig
├── protocol/
│   ├── header.py         # LifxHeader
│   ├── packets.py        # Packet definitions
│   ├── protocol_types.py # LightHsbk, etc.
│   └── serializer.py     # Binary serialization
└── products/
    ├── registry.py       # Product registry (137+ products)
    └── specs.py          # Product defaults
```

## Public Exports

The following are exported from `lifx_emulator`:

```python
from lifx_emulator import (
    # Server
    EmulatedLifxServer,

    # Device (for advanced usage)
    EmulatedLifxDevice,

    # Factory functions (recommended)
    create_color_light,
    create_color_temperature_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
    create_switch,
    create_device,
)
```

## Common Patterns

### Basic Test Setup

```python
import asyncio
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

async def test_basic():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())

    async with EmulatedLifxServer(
        [device], device_manager, "127.0.0.1", 56700
    ) as server:
        # Your test code using your LIFX library
        pass
```

### Multiple Device Types

```python
from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

devices = [
    create_color_light("d073d5000001"),
    create_multizone_light("d073d8000001", zone_count=16),
    create_tile_device("d073d9000001", tile_count=5),
]

device_manager = DeviceManager(DeviceRepository())

async with EmulatedLifxServer(
    devices, device_manager, "127.0.0.1", 56700
) as server:
    # Test with multiple device types
    pass
```

### Custom Serials

```python
devices = [
    create_color_light("cafe00000001"),
    create_color_light("cafe00000002"),
    create_color_light("cafe00000003"),
]
```

### Accessing Device State

```python
device = create_color_light("d073d5000001")

# Check initial state
print(f"Label: {device.state.label}")
print(f"Power: {device.state.power_level}")
print(f"Color: {device.state.color}")

# After commands are sent to the device
print(f"New color: {device.state.color}")
```

## Next Steps

- [Server API](server/) - EmulatedLifxServer documentation
- [Device API](device/) - EmulatedLifxDevice and DeviceState
- [Factory Functions](factories/) - All create\_\* functions
- [Protocol Types](protocol/) - LightHsbk and other types
- [Product Registry](products/) - Product database
