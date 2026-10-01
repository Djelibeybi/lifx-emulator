# EmulatedLifxServer

The `EmulatedLifxServer` class manages the UDP server and routes packets to emulated devices.

## Overview

The server:

- Listens on a UDP socket for LIFX protocol packets
- Parses packet headers to determine routing
- Forwards packets to appropriate devices
- Sends response packets back to clients
- Supports both targeted and broadcast packets

## API Reference

::: lifx_emulator.server.EmulatedLifxServer
    options:
      show_root_heading: true
      show_source: true
      members:
        - start
        - stop


## Usage

### Basic Server

```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

# Create devices
devices = [create_color_light("d073d5000001")]

# Set up repository and manager (required)
device_repository = DeviceRepository()
device_manager = DeviceManager(device_repository)

# Create server
server = EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)

# Start server
await server.start()

# ... do work ...

# Stop server
await server.stop()
```

### Context Manager

The recommended way to use the server:

```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

devices = [create_color_light("d073d5000001")]
device_manager = DeviceManager(DeviceRepository())

async with EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700) as server:
    # Server automatically starts
    # Your test code here
    pass
# Server automatically stops
```

### Multiple Devices

```python
from lifx_emulator import EmulatedLifxServer
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

async with EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700) as server:
    # All devices are discoverable and controllable
    pass
```

## Parameters

### `devices`
List of `EmulatedLifxDevice` instances to emulate.

**Type:** `list[EmulatedLifxDevice]`

### `device_manager`
The device manager handling device lifecycle and packet routing.

**Type:** `DeviceManager`

**Required:** Yes

**Notes:**
- The server delegates all device management operations to this manager
- Must be created with a `DeviceRepository` instance
- This is a **required** parameter in v2.0.0+

**Example:**
```python
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

device_repository = DeviceRepository()
device_manager = DeviceManager(device_repository)
```

### `bind_address`
IP address to bind the UDP server to.

**Type:** `str`

**Examples:**
- `"0.0.0.0"` - Listen on all interfaces
- `"127.0.0.1"` - Localhost only
- `"192.168.1.100"` - Specific interface

### `port`
UDP port to listen on.

**Type:** `int`

**Default:** 56700 (standard LIFX port)

### `track_activity`
Enable packet activity tracking for the HTTP API dashboard.

**Type:** `bool`

**Default:** `True`

**Notes:**
- When enabled, the server tracks recent packet activity for the API dashboard
- Disable to reduce memory usage in production or CI environments
- Activity tracking is independent of packet logging (controlled by `--verbose` CLI flag)

**Example:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

# Disable activity tracking
device_manager = DeviceManager(DeviceRepository())
server = EmulatedLifxServer(
    devices,
    device_manager,
    "127.0.0.1",
    56700,
    track_activity=False
)
```

### `storage`
Optional persistent storage backend for device state.

**Type:** `DevicePersistenceAsyncFile | None`

**Default:** `None`

**Notes:**
- Devices save their own state through the storage passed to their factory; pass the same instance here
- The server uses it to delete persisted state when devices are removed (`remove_device()`, `remove_all_devices(delete_storage=True)`)
- Allows device state to persist across emulator restarts
- See [Persistent Storage Guide](../cli/storage.md) for details

**Example:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager, DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository

storage = DevicePersistenceAsyncFile()
device = create_color_light("d073d5000001", storage=storage)

device_manager = DeviceManager(DeviceRepository())

# Create server with storage support
server = EmulatedLifxServer(
    [device],
    device_manager,
    "127.0.0.1",
    56700,
    storage=storage
)
```

### `activity_observer`
Optional observer for packet activity events.

**Type:** `ActivityObserver | None`

**Default:** `None`

**Notes:**
- Implement `ActivityObserver` protocol to receive packet events
- Useful for custom activity tracking or metrics collection
- Receives events for all packets sent and received

### `scenario_manager`
Optional scenario manager for test scenario configuration.

**Type:** `HierarchicalScenarioManager | None`

**Default:** `None`

**Notes:**
- Shared by all devices; if omitted, the server creates an empty one (available as `server.scenario_manager`)
- When provided, enables runtime scenario management via REST API
- Supports device-specific, type-specific, location-based, group-based, and global scenarios
- Scenarios control packet dropping, delays, malformed responses, etc.
- See [Testing Scenarios Guide](../cli/scenarios.md) for detailed examples

**Example:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.scenarios import HierarchicalScenarioManager
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

manager = HierarchicalScenarioManager()
device_manager = DeviceManager(DeviceRepository())

server = EmulatedLifxServer(
    devices,
    device_manager,
    "127.0.0.1",
    56700,
    scenario_manager=manager
)

# Now scenario management API is available
```

### `persist_scenarios`
Enable persistent storage of scenario configurations.

**Type:** `bool`

**Default:** `False`

**Notes:**
- When enabled, scenario changes made through the API are saved via `scenario_storage` (`ScenarioPersistenceAsyncFile` writes `~/.lifx-emulator/scenarios.json`)
- Requires both `scenario_storage` and `scenario_manager`; the constructor raises `ValueError` if either is missing
- Load `scenario_manager` from `scenario_storage` before creating the server so saved scenarios are restored

**Example:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioPersistenceAsyncFile

# Enable both state and scenario persistence
scenario_storage = ScenarioPersistenceAsyncFile()
manager = await scenario_storage.load()

device_manager = DeviceManager(DeviceRepository())
server = EmulatedLifxServer(
    devices,
    device_manager,
    "127.0.0.1",
    56700,
    storage=storage,
    scenario_manager=manager,
    persist_scenarios=True,
    scenario_storage=scenario_storage,
)
```

## Methods

### Lifecycle Methods

#### `async start()`
Start the UDP server and begin accepting connections.

**Notes:**
- Call this method before sending any packets to the emulator
- Binds to the configured address and port
- Logs server startup information
- Required if not using context manager

**Example:**
```python
device_manager = DeviceManager(DeviceRepository())
server = EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)
await server.start()
try:
    # Use server
    pass
finally:
    await server.stop()
```

#### `async stop()`
Stop the UDP server and clean up resources.

**Notes:**
- Gracefully closes the UDP endpoint
- Cleans up internal state
- Safe to call multiple times
- Automatically called by context manager

### Context Manager Protocol

The server implements the async context manager protocol for clean resource management:

#### `async __aenter__()`
Enter async context manager - automatically calls `start()`.

#### `async __aexit__()`
Exit async context manager - automatically calls `stop()`.

**Recommended Usage:**
```python
device_manager = DeviceManager(DeviceRepository())
async with EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700) as server:
    # Server is automatically started
    # Perform your tests
    pass
# Server is automatically stopped
```

### Utility Methods

#### `get_stats()`
Get server statistics.

**Returns:** `dict[str, Any]` - Includes `uptime_seconds`, `start_time`, `device_count`, `packets_received`, `packets_sent`, `packets_received_by_type`, `packets_sent_by_type`, `error_count`, `packets_dropped_overload`, `websocket_events_dropped` and `activity_enabled`

**Notes:**
- `uptime_seconds` is measured with a monotonic clock from server construction
- Useful for performance testing and benchmarking

**Example:**
```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

device_manager = DeviceManager(DeviceRepository())
async with EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700) as server:
    await asyncio.sleep(1)
    stats = server.get_stats()
    print(f"Server uptime: {stats['uptime_seconds']:.2f}s")
    print(f"Packets received: {stats['packets_received']}")
```

#### `invalidate_all_scenario_caches()`
Clear every device's cached resolved scenario.

**Notes:**
- Normally called automatically after scenario updates via API
- Only needed if modifying scenario manager state outside of API
- Safe to call - no side effects
- Non-blocking operation

**Example:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

manager = HierarchicalScenarioManager()
device_manager = DeviceManager(DeviceRepository())
server = EmulatedLifxServer(
    devices, device_manager, "127.0.0.1", 56700, scenario_manager=manager
)

async with server:
    # Update scenarios externally
    manager.set_global_scenario(ScenarioConfig(drop_packets={101: 0.5}))
    # Invalidate cache to apply changes immediately
    server.invalidate_all_scenario_caches()
```

## Packet Routing

### Broadcast Packets

Packets with `tagged=True` or `target=000000000000` are forwarded to all devices:

```text
# GetService broadcasts are answered by all devices
# Client discovers all emulated devices
```

### Targeted Packets

Packets with a specific target serial are routed to that device:

```text
# Light.SetColor for d073d5000001 goes only to that device
# Other devices don't see the packet
```

### Unknown Targets

Packets for unknown serial addresses are silently dropped:

```text
# Packet for d073d5999999 (not in server) is ignored
# No error or response generated
```

## Response Handling

The server handles responses automatically:

1. Device processes packet and returns response(s)
2. Server packs response packets to bytes
3. Server sends responses back to source address
4. Multiple responses (e.g., multizone StateMultiZone) are sent sequentially

## Concurrency

The server uses asyncio for concurrent operation:

```text
# Multiple clients can send packets concurrently
# Each device processes packets independently
# Responses are sent asynchronously
```

## Error Handling

The server handles errors gracefully:

- Invalid packets are logged and dropped
- Device exceptions are caught and logged
- Server continues running despite errors
- Malformed headers don't crash the server

## Lifecycle

### Startup

1. Create UDP endpoint
2. Bind to address and port
3. Start receiving packets
4. Log server start

### Runtime

1. Receive packet bytes
2. Parse header
3. Route to device(s)
4. Get responses
5. Send responses

### Shutdown

1. Stop accepting packets
2. Close UDP endpoint
3. Clean up resources
4. Log server stop

## Testing Integration

### pytest-asyncio

```python
import pytest
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.devices import DeviceManager

@pytest.fixture
def device_manager():
    return DeviceManager(DeviceRepository())

@pytest.fixture
async def lifx_server(device_manager):
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_discovery(lifx_server):
    # Test code using the server
    pass
```

### Module-Scoped Fixture

For faster tests, use module scope:

```python
import pytest

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository

@pytest.fixture(scope="module")
def device_manager():
    return DeviceManager(DeviceRepository())

@pytest.fixture(scope="module")
async def lifx_server(device_manager):
    devices = [create_color_light(f"d073d500000{i}") for i in range(5)]
    server = EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)

    async with server:
        yield server
```

## Next Steps

- [Device API](device.md) - EmulatedLifxDevice documentation
- [Factory Functions](factories.md) - Device creation
- [Integration Testing Tutorial](../tutorials/03-integration.md) - Integration test examples
