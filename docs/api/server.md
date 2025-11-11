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
from lifx_emulator import EmulatedLifxServer, create_color_light

# Create devices
devices = [create_color_light("d073d5000001")]

# Create server
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

# Start server
await server.start()

# ... do work ...

# Stop server
await server.stop()
```

### Context Manager

The recommended way to use the server:

```python
async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # Server automatically starts
    # Your test code here
    pass
# Server automatically stops
```

### Multiple Devices

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
    # All devices are discoverable and controllable
    pass
```

## Parameters

### `devices`
List of `EmulatedLifxDevice` instances to emulate.

**Type:** `list[EmulatedLifxDevice]`

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
# Disable activity tracking
server = EmulatedLifxServer(
    devices,
    "127.0.0.1",
    56700,
    track_activity=False
)
```

### `storage`
Optional persistent storage for device state.

**Type:** `AsyncDeviceStorage | None`

**Default:** `None`

**Notes:**
- When provided, device state changes are automatically saved asynchronously
- Allows device state to persist across emulator restarts
- Must be used with devices created with the same storage instance
- See [Persistent Storage Guide](../advanced/storage.md) for details

**Example:**
```python
from lifx_emulator.async_storage import AsyncDeviceStorage

storage = AsyncDeviceStorage()
device = create_color_light("d073d5000001", storage=storage)

# Create server with storage support
server = EmulatedLifxServer(
    [device],
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
- When provided, enables runtime scenario management via REST API
- Supports device-specific, type-specific, location-based, group-based, and global scenarios
- Scenarios control packet dropping, delays, malformed responses, etc.
- See [Testing Scenarios Guide](../advanced/scenarios.md) for detailed examples

**Example:**
```python
from lifx_emulator.scenarios.manager import HierarchicalScenarioManager

manager = HierarchicalScenarioManager()
server = EmulatedLifxServer(
    devices,
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
- When enabled, scenario configurations are saved to `~/.lifx-emulator/scenarios.json`
- Scenarios are restored from disk on startup
- Requires `scenario_manager` to be provided
- Ignored if `scenario_manager` is `None`

**Example:**
```python
# Enable both state and scenario persistence
server = EmulatedLifxServer(
    devices,
    "127.0.0.1",
    56700,
    storage=storage,
    scenario_manager=manager,
    persist_scenarios=True
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
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
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
async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # Server is automatically started
    # Perform your tests
    pass
# Server is automatically stopped
```

### Utility Methods

#### `get_uptime_ns()`
Get the server uptime in nanoseconds since startup.

**Returns:** `int` - Nanoseconds elapsed since server started

**Notes:**
- Returns 0 if server hasn't started yet
- Useful for performance testing and benchmarking
- Uses monotonic clock for accurate timing

**Example:**
```python
async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    await asyncio.sleep(1)
    uptime_ns = server.get_uptime_ns()
    uptime_ms = uptime_ns / 1_000_000
    print(f"Server uptime: {uptime_ms:.2f}ms")
```

#### `invalidate_scenario_cache()`
Clear the internal scenario precedence cache.

**Notes:**
- Normally called automatically after scenario updates via API
- Only needed if modifying scenario manager state outside of API
- Safe to call - no side effects
- Non-blocking operation

**Example:**
```python
manager = HierarchicalScenarioManager()
server = EmulatedLifxServer(devices, "127.0.0.1", 56700, scenario_manager=manager)

async with server:
    # Update scenarios externally
    manager.set_global_scenario(ScenarioConfig(...))
    # Invalidate cache to apply changes immediately
    server.invalidate_scenario_cache()
```

## Packet Routing

### Broadcast Packets

Packets with `tagged=True` or `target=000000000000` are forwarded to all devices:

```python
# GetService broadcasts are answered by all devices
# Client discovers all emulated devices
```

### Targeted Packets

Packets with a specific target serial are routed to that device:

```python
# LightSetColor for d073d5000001 goes only to that device
# Other devices don't see the packet
```

### Unknown Targets

Packets for unknown serial addresses are silently dropped:

```python
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

```python
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
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def lifx_server():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

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
@pytest.fixture(scope="module")
async def lifx_server():
    devices = [create_color_light(f"d073d500000{i}") for i in range(5)]
    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        yield server
```

## Next Steps

- [Device API](device.md) - EmulatedLifxDevice documentation
- [Factory Functions](factories.md) - Device creation
- [Integration Testing Tutorial](../tutorials/03-integration.md) - Integration test examples
