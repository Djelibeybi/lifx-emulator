# API Reference

Complete Python API documentation for the LIFX Emulator.

## Overview

The LIFX Emulator API is designed for simplicity and ease of use. Most users only need the factory functions and server class.

## Reading This Guide

This reference is organized from most common to advanced usage:

1. **[Factory Functions](factories.md)** ⭐ Start here - Creating devices (most common)
2. **[Server](server.md)** - Server setup and configuration
3. **[Device](device.md)** - Device API and state management
4. **[Products](products.md)** - Product registry and specs
5. **[Protocol](protocol.md)** - Low-level protocol types (advanced)
6. **[Storage](storage.md)** - Persistent state (advanced)

## Quick Start

### Installation

**Recommended:** Using [uv](https://astral.sh/uv):

```bash
uv add lifx-emulator
```

**Alternative:** Using pip:

```bash
pip install lifx-emulator
```

### Basic Usage

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    # Create a device
    device = create_color_light("d073d5000001")

    # Start server
    async with EmulatedLifxServer([device], "127.0.0.1", 56700) as server:
        # Server is running, test your LIFX library here
        await asyncio.Event().wait()

asyncio.run(main())
```

## Core Components

### 1. Factory Functions (Most Common)

Use these to create devices easily:

```python
from lifx_emulator import (
    create_color_light,           # RGB color lights
    create_color_temperature_light, # White temperature lights
    create_infrared_light,         # IR-capable lights
    create_hev_light,             # HEV cleaning lights
    create_multizone_light,       # Linear strips
    create_tile_device,           # Matrix tiles
)
```

👉 **[Full Factory Documentation](factories.md)**

### 2. Server

The server manages UDP communication and device routing:

```python
from lifx_emulator import EmulatedLifxServer

# Create server
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

# Use as context manager (recommended)
async with server:
    # Server running
    pass

# Or manual lifecycle
await server.start()
await server.stop()
```

👉 **[Full Server Documentation](server.md)**

### 3. Device (Advanced)

For custom device creation:

```python
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState

state = DeviceState(serial="d073d5000001", label="Custom Device")
device = EmulatedLifxDevice(state)
```

👉 **[Full Device Documentation](device.md)**

### 4. Product Registry

Access official LIFX product definitions:

```python
from lifx_emulator.products.registry import get_product, get_registry

product = get_product(27)  # LIFX A19
all_products = get_registry()
```

👉 **[Full Product Documentation](products.md)**

## Quick Reference

### Creating Devices

| Function | Product | Description |
|----------|---------|-------------|
| `create_color_light()` | LIFX A19 (27) | Standard RGB color light |
| `create_color_temperature_light()` | LIFX Mini White to Warm (50) | Variable color temperature |
| `create_infrared_light()` | LIFX A19 Night Vision (29) | IR capable light |
| `create_hev_light()` | LIFX Clean (90) | HEV cleaning light |
| `create_multizone_light()` | LIFX Z (32) or Beam (38) | Linear multizone strip |
| `create_tile_device()` | LIFX Tile (55) | Tile matrix (configurable dimensions) |

### Server Context Manager

The server can be used as an async context manager:

```python
async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # Server is running
    # Your test code here
    pass
# Server automatically stops
```

### Server Lifecycle

Manual server lifecycle management:

```python
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
await server.start()  # Start listening
# ... do work ...
await server.stop()   # Stop server
```

## Module Structure

```
lifx_emulator/
├── __init__.py           # Public exports
├── server.py             # EmulatedLifxServer
├── device.py             # EmulatedLifxDevice, DeviceState
├── factories.py          # create_* factory functions
├── constants.py          # Protocol constants
├── protocol/
│   ├── header.py         # LifxHeader
│   ├── packets.py        # Packet definitions
│   ├── protocol_types.py # LightHsbk, etc.
│   └── serializer.py     # Binary serialization
└── products/
    ├── registry.py       # Product registry
    ├── specs.py          # Product defaults
    └── generator.py      # Registry generator
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
)
```

## Common Patterns

### Basic Test Setup

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def test_basic():
    device = create_color_light("d073d5000001")

    async with EmulatedLifxServer([device], "127.0.0.1", 56700) as server:
        # Your test code using your LIFX library
        pass
```

### Multiple Device Types

```python
from lifx_emulator import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)

devices = [
    create_color_light("d073d5000001"),
    create_multizone_light("d073d8000001", zone_count=16),
    create_tile_device("d073d9000001", tile_count=5),
]

async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # Test with multiple device types
    pass
```

### Custom serials

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

- [Server API](server.md) - EmulatedLifxServer documentation
- [Device API](device.md) - EmulatedLifxDevice and DeviceState
- [Factory Functions](factories.md) - All create_* functions
- [Protocol Types](protocol.md) - LightHsbk and other types
- [Product Registry](products.md) - Product database
