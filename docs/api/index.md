# API Reference Overview

The LIFX Emulator provides a simple Python API for creating virtual LIFX devices in your tests.

## Core Components

### Server

The [`EmulatedLifxServer`](server.md) manages the UDP server and routes packets to devices.

```python
from lifx_emulator import EmulatedLifxServer

server = EmulatedLifxServer(devices, bind_address, port)
await server.start()
```

### Device

The [`EmulatedLifxDevice`](device.md) represents a single virtual LIFX device with stateful behavior.

```python
from lifx_emulator.device import EmulatedLifxDevice, DeviceState

state = DeviceState(serial="d073d5000001", label="Test Light")
device = EmulatedLifxDevice(state)
```

### Factory Functions

[Factory functions](factories.md) provide convenient device creation:

```python
from lifx_emulator import (
    create_color_light,
    create_color_temperature_light,
    create_infrared_light,
    create_hev_light,
    create_multizone_light,
    create_tile_device,
)
```

### Product Registry

The [product registry](products.md) contains official LIFX product definitions:

```python
from lifx_emulator.products.registry import get_product, get_registry

product = get_product(27)  # LIFX A19
registry = get_registry()  # Full registry
```

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
