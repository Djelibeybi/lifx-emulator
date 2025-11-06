# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LIFX Emulator for testing LIFX LAN protocol libraries. It implements the binary UDP protocol from https://lan.developer.lifx.com and emulates various LIFX device types including color lights, multizone strips, tiles, infrared, and HEV devices.

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_filename.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Run linter (Ruff)
ruff check .

# Run linter with auto-fix
ruff check --fix .

# Run type checker (Pyright)
pyright
```

### Running the Emulator
```bash
# Run as module with default configuration (1 color light)
python -m lifx_emulator

# Install and run as CLI
pip install -e .
lifx-emulator

# Common usage examples:
# List all available LIFX products from the registry
lifx-emulator list-products

# List only multizone products
lifx-emulator list-products --filter-type multizone

# Create devices by product ID (from registry)
lifx-emulator --product 27 --product 32 --product 55  # A19, Z strip, Tile

# Start on custom port with verbose packet logging
lifx-emulator --port 56700 --verbose

# Bind to specific IP address
lifx-emulator --bind 192.168.1.100 --port 56700

# Create multiple device types
lifx-emulator --color 2 --multizone 1 --tile 1 --verbose

# Create only specific device types
lifx-emulator --color 0 --infrared 3 --hev 2

# Mix product IDs with device types
lifx-emulator --product 27 --color 2 --multizone 1

# Custom device configuration
lifx-emulator --multizone 2 --multizone-zones 24 --tile 3 --tile-count 10

# Create non-extended multizone devices
lifx-emulator --multizone 2 --no-multizone-extended --multizone-zones 16

# Custom serial prefix (useful for testing)
lifx-emulator --serial-prefix cafe00 --color 5

# Enable HTTP API server for monitoring and management
lifx-emulator --api

# API server with custom host/port
lifx-emulator --api --api-host 127.0.0.1 --api-port 9090

# Disable activity logging to save UI space and reduce traffic
lifx-emulator --api --api-activity=false

# See all available options
lifx-emulator --help
```

**CLI Commands:**
- `list-products`: Show all LIFX products in the registry with capabilities
  - `--filter-type`: Filter by capability (color, multizone, matrix, hev, infrared)
  - Capability labels:
    - `full color`: RGB color control
    - `color temperature`: White with variable color temperature
    - `brightness only`: Fixed color temperature, brightness control only
    - `switch`: Relay-based switches (not lights)
    - `multizone`: Linear light strips
    - `extended-multizone`: Extended multizone (>16 zones)
    - `matrix`: 2D tile/candle arrangements
    - `infrared`: Night vision capability
    - `HEV`: Germicidal UV-C capability
    - `chain`: Supports device chaining
    - `buttons`: Has physical buttons

**CLI Parameters:**
- `--bind`: IP address to bind to (default: 127.0.0.1)
- `--port`: UDP port to listen on (default: 56700)
- `--verbose`: Enable verbose logging showing all packets sent/received
- `--persistent`: Enable persistent storage of device state across sessions
- `--product`: Create devices by product ID (can specify multiple times)
- `--color`: Number of color lights (default: 1)
- `--color-temperature`: Number of color temperature lights
- `--infrared`: Number of infrared lights
- `--hev`: Number of HEV/Clean lights
- `--multizone`: Number of multizone devices (strips/beams, default: 0)
- `--multizone-zones`: Zones per multizone device (uses product default if not specified)
- `--multizone-extended`: Enable extended multizone support (default: True, use --no-multizone-extended to disable)
- `--tile`: Number of tile devices
- `--tile-count`: Tiles per device (uses product default if not specified)
- `--tile-width`: Width of each tile in pixels (uses product default if not specified)
- `--tile-height`: Height of each tile in pixels (uses product default if not specified)
- `--serial-prefix`: serial prefix (6 hex chars, default: d073d5)
- `--serial-start`: Starting serial suffix (default: 1)
- `--api`: Enable HTTP API server for monitoring and management (default: False)
- `--api-host`: API server host to bind to (default: 127.0.0.1)
- `--api-port`: API server port (default: 8080)
- `--api-activity`: Enable activity logging in API (default: True, disable to reduce traffic and save UI space)

**Product Defaults:**
Device parameters like `--multizone-zones` and `--tile-count` automatically use product-specific defaults from the specs system when not specified:
- LIFX Beam: Extended multizone support enabled and 80 zones by default
- LIFX Tile: 5 tiles of 8x8 pixels by default
- LIFX Candle: 1 tile of 5x6 pixels by default
- LIFX Ceiling: 1 tile of 8x8 pixels by default
- These defaults can be overridden with command-line parameters

**Firmware Version:**
The emulator automatically sets firmware version for multizone
lights based on the `--multizone-extended` flag:
- `--multizone-extended` (default): firmware set to 3.70
- `--no-multizone-extended`: firmware set to 2.60

For all other devices, the emulator will use 3.70 unless
`firmware_major` and `firmware_minor` are provided in the
request made to the `create_device` API endpoint.

## HTTP Management API

The emulator includes an optional HTTP API server for runtime monitoring and device management. Enable it with the `--api` flag.

**Features:**
- Real-time monitoring dashboard with live packet activity
- View server statistics (uptime, packet counts, errors)
- List and inspect all emulated devices
- Add and remove devices at runtime (via REST API)
- View recent protocol activity (last 100 packets, optional with `--api-activity`)

**Usage:**
```bash
# Enable API server (default: http://127.0.0.1:8080)
lifx-emulator --api

# Custom host and port
lifx-emulator --api --api-host 127.0.0.1 --api-port 9090

# Combined with other options
lifx-emulator --color 2 --multizone 1 --api --verbose
```

**Web Dashboard:**
- Open `http://localhost:8080` in your browser
- View real-time statistics and device status
- Monitor packet activity (TX/RX)
- Add/remove devices dynamically

**OpenAPI Documentation:**
- OpenAPI 3.1.0 schema: `http://localhost:8080/openapi.json`
- Swagger UI (interactive): `http://localhost:8080/docs`
- ReDoc (documentation): `http://localhost:8080/redoc`

**REST API Endpoints:**
- `GET /api/stats` - Server statistics (uptime, packet counts, errors)
- `GET /api/devices` - List all emulated devices
- `GET /api/devices/{serial}` - Get specific device info
- `POST /api/devices` - Create a new device (JSON: `{"product_id": 27}`)
- `DELETE /api/devices/{serial}` - Remove a device
- `GET /api/activity` - Recent packet activity (last 100 events)

**API Examples:**
```bash
# Get server stats
curl http://localhost:8080/api/stats

# List all devices
curl http://localhost:8080/api/devices

# Add a new LIFX A19 (product 27)
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 27}'

# Add a multizone strip with 16 zones
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 32, "zone_count": 16}'

# Remove a device by serial
curl -X DELETE http://localhost:8080/api/devices/d073d5000001
```

**API Module** (`src/lifx_emulator/api.py`):
- `create_api_app(server)`: Create FastAPI application with OpenAPI 3.1.0 schema
- `run_api_server(server, host, port)`: Run the API server
- Automatic OpenAPI schema generation with full Pydantic validation
- Interactive API documentation via Swagger UI and ReDoc

**OpenAPI Compliance:**
The API follows the OpenAPI 3.1.0 specification and provides:
- Full schema definition at `/openapi.json`
- Interactive Swagger UI at `/docs` for testing endpoints
- ReDoc documentation UI at `/redoc` for readable API docs
- Proper HTTP status codes and error responses
- Request/response models with Pydantic validation
- Organized endpoints with tags (monitoring, devices)
- Complete metadata (title, version, description, license, contact info)

## Persistent Storage

The emulator supports optional persistent storage of device state across sessions using the `--persistent` CLI flag.

**Features:**
- Device state persists between emulator restarts
- Saves: label, power level, color, location, group, infrared brightness, HEV state, zone colors, tile colors/positions
- Storage location: `~/.lifx-emulator/` (one JSON file per device serial)
- Only restored if serial and product ID match
- Automatic save on all state-changing operations

**Usage:**
```bash
# Enable persistence
lifx-emulator --persistent

# Device state now survives restarts
# Change a device's label, color, etc. - they'll be restored on next run
```

**Programmatic API:**
```python
import asyncio
from lifx_emulator.async_storage import AsyncDeviceStorage
from lifx_emulator.factories import create_color_light

async def main():
    # Create storage
    storage = AsyncDeviceStorage()  # Uses ~/.lifx-emulator by default
    # Or specify custom path:
    # storage = AsyncDeviceStorage("/path/to/storage")

    # Create device with persistence
    device = create_color_light(serial="d073d5123456", storage=storage)

    # State changes are automatically saved asynchronously
    device.state.label = "My Light"
    # No need to manually call save - it's automatic with debouncing (100ms default)

    # On next run with same serial, state will be restored
    device2 = create_color_light(serial="d073d5123456", storage=storage)
    # device2.state.label == "My Light"

asyncio.run(main())
```

**Storage Module** (`src/lifx_emulator/async_storage.py`):
- `AsyncDeviceStorage`: High-performance async persistent storage with debouncing
- `async save_device_state(device_state)`: Queue state for async save (non-blocking)
- `load_device_state(serial)`: Load saved state from disk (synchronous)
- `delete_device_state(serial)`: Remove saved state (synchronous)
- `list_devices()`: List all devices with saved state (synchronous)
- `async shutdown()`: Gracefully flush pending saves before shutdown

## Scenario Management

The emulator supports comprehensive test scenario management for simulating protocol edge cases, packet loss, delays, and malformed responses. Scenarios can be configured at 5 different scope levels with automatic precedence resolution.

**Features:**
- Device-specific scenarios (affects single device by serial)
- Device-type scenarios (affects all devices of a type: color, multizone, matrix, hev, infrared, extended_multizone)
- Location-based scenarios (affects all devices in a location)
- Group-based scenarios (affects all devices in a group)
- Global scenarios (affects all devices)
- Scenario precedence resolution (device-specific > type > location > group > global)
- Runtime scenario updates via REST API
- Optional scenario persistence across restarts

**Scenario Configuration Types:**
- `drop_packets`: Dict mapping packet types to drop rates (0.0-1.0, where 1.0 = always drop, 0.5 = 50% probability)
- `response_delays`: Dictionary mapping packet types to delays in seconds
- `malformed_packets`: List of packet types to send truncated/corrupted
- `invalid_field_values`: List of packet types to send with all 0xFF bytes
- `firmware_version`: Override firmware version as tuple `(major, minor)`
- `partial_responses`: List of packet types to send incomplete multizone/tile data
- `send_unhandled`: Boolean to send StateUnhandled for unknown packet types

**REST API Endpoints:**

See the [Scenario REST API Documentation](docs/guide/scenario-api.md) for comprehensive REST API reference with detailed examples, shell scripts, and integration patterns.

Quick reference - Global scenarios:
```bash
# Get global scenario
curl http://localhost:8080/api/scenarios/global

# Set global scenario
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{
    "drop_packets": {"101": 1.0, "102": 0.6},
    "response_delays": {"101": 0.5, "116": 1.0},
    "malformed_packets": [],
    "invalid_field_values": [],
    "firmware_version": null,
    "partial_responses": [],
    "send_unhandled": false
  }'

# Clear global scenario
curl -X DELETE http://localhost:8080/api/scenarios/global
```

Device-specific scenarios:
```bash
# Get scenario for device by serial
curl http://localhost:8080/api/scenarios/devices/d073d5000001

# Set scenario for specific device (drop 100% of packet 101, 60% of packet 102)
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0, "102": 0.6}}'

# Clear device scenario
curl -X DELETE http://localhost:8080/api/scenarios/devices/d073d5000001
```

Type-specific scenarios:
```bash
# Set scenario for all multizone devices
curl -X PUT http://localhost:8080/api/scenarios/types/multizone \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"502": 1.0}}'

# Set scenario for all color devices (drop 60% of GetColor packets)
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 0.6}}'

# Supported types: color, multizone, extended_multizone, matrix, hev, infrared, basic
```

Location and group scenarios:
```bash
# Set scenario for all devices in "Kitchen" location
curl -X PUT http://localhost:8080/api/scenarios/locations/Kitchen \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"116": 0.5}}'

# Set scenario for all devices in "Bedroom Lights" group
curl -X PUT http://localhost:8080/api/scenarios/groups/"Bedroom Lights" \
  -H "Content-Type: application/json" \
  -d '{"malformed_packets": [506]}'
```

**Usage Examples:**

Simulate packet loss for testing retries:
```bash
# Always drop GetColor packets (100% drop rate) for all color devices
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}'

# Or drop 30% probabilistically (simulating flaky network)
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 0.3}}'
```

Simulate network latency:
```bash
# Add 500ms delay to all responses for one device
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"101": 0.5, "102": 0.5, "103": 0.5}}'
```

Test firmware version handling:
```bash
# Override firmware version for device
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"firmware_version": [2, 60]}'
```

Simulate malformed responses:
```bash
# Send corrupted StateColor packets to test error handling
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"malformed_packets": [107]}'
```

**Scenario Precedence Example:**

If you have:
- Global: drop packets {101: 1.0}
- Type (multizone): response_delays {502: 1.0}
- Device (d073d5000001): drop packets {102: 0.5}

Then device `d073d5000001` of type `multizone` would:
- Drop packet 101 with 100% rate (from global)
- Drop packet 102 with 50% rate (from device-specific)
- Have 1.0s delay for packet type 502 (from type scenario)

**Persistence:**
```bash
# Enable scenario persistence (saved to ~/.lifx-emulator/scenarios.json)
lifx-emulator --api --persistent --persistent-scenarios
```

**Programmatic API:**
```python
from lifx_emulator.scenario_manager import HierarchicalScenarioManager, ScenarioConfig

# Create manager
manager = HierarchicalScenarioManager()

# Set global scenario - drop 100% of packet 101, 60% of packet 102
manager.set_global_scenario(ScenarioConfig(
    drop_packets={101: 1.0, 102: 0.6},  # dict with drop rates (0.0-1.0)
    response_delays={116: 0.5}
))

# Set device-specific scenario - drop 100% of packet 103 for one device
manager.set_device_scenario(
    "d073d5000001",
    ScenarioConfig(drop_packets={103: 1.0})  # dict format
)

# Set type-specific scenario
manager.set_type_scenario(
    "multizone",
    ScenarioConfig(response_delays={502: 1.0})
)

# Resolve scenario for a device (accounts for all scopes)
merged = manager.get_scenario_for_device(
    serial="d073d5000001",
    device_type="multizone",
    location="Kitchen",
    group="Strips"
)

# Use scenario methods to check behavior
should_respond = manager.should_respond(101, merged)  # False (dropped)
delay = manager.get_response_delay(502, merged)  # 1.0s
```

**Scenario Manager** (`src/lifx_emulator/scenario_manager.py`):
- `ScenarioConfig`: Dataclass representing a scenario configuration
- `HierarchicalScenarioManager`: Manages scenarios across 5 scope levels
- `get_device_type()`: Classify device by capability for type-based scoping
- Methods: `set_*_scenario()`, `delete_*_scenario()`, `get_scenario_for_device()`, `should_respond()`, etc.

**Persistence Module** (`src/lifx_emulator/scenario_persistence.py`):
- `ScenarioPersistence`: Handles JSON serialization of scenario configurations
- Automatic save after API updates
- Atomic file operations (temp file + rename) for consistency
- Error recovery on corrupted scenario files

## Architecture

### Core Components

**EmulatedLifxServer** (`src/lifx_emulator/server.py`):
- UDP server using asyncio DatagramProtocol
- Routes incoming packets to appropriate devices based on target serial (encoded in header target field)
- Handles broadcast packets (tagged=True or target=00000000) by forwarding to all devices
- Supports configurable response delays per packet type for testing

**EmulatedLifxDevice** (`src/lifx_emulator/device.py`):
- Represents a single virtual LIFX device with stateful behavior
- `process_packet()`: Main entry point that handles packet type routing and acknowledgments
- `_handle_packet_type()`: Dispatcher that routes to specific handlers (e.g., `_handle_light_set_color()`)
- Supports testing scenarios: packet dropping, malformed responses, invalid field values, partial responses

**DeviceState** (`src/lifx_emulator/device.py`):
- Dataclass holding all device state (color, power, zones, tiles, firmware version, etc.)
- Capability flags: `has_color`, `has_infrared`, `has_multizone`, `has_matrix`, `has_hev`
- Initialized differently per device type via factory functions

### Protocol Layer

**Protocol packets** (`src/lifx_emulator/protocol/packets.py`):
- Auto-generated from LIFX protocol YAML spec
- Organized into nested classes: `Device.*`, `Light.*`, `MultiZone.*`, `Tile.*`
- Each packet class has `PKT_TYPE` constant and `pack()`/`unpack()` methods
- Uses `PACKET_REGISTRY` dict to map packet type numbers to classes

**Protocol types** (`src/lifx_emulator/protocol/protocol_types.py`):
- Defines structured types like `LightHsbk`, `TileStateDevice`, effect settings
- Uses enums for constants (e.g., `DeviceService`, `LightWaveform`)

**Header** (`src/lifx_emulator/protocol/header.py`):
- `LifxHeader` class handles the 36-byte LIFX packet header
- Important fields: `target` (6-byte serial + 2 null bytes), `source`, `sequence`, `pkt_type`, `tagged`, `ack_required`, `res_required`

**Serializer** (`src/lifx_emulator/protocol/serializer.py`):
- Low-level binary packing/unpacking using struct
- Handles byte arrays, enums, nested protocol types, arrays of protocol types

### Device Factories

**Factory functions** (`src/lifx_emulator/factories.py`):
- `create_color_light()`: Full color RGB light - LIFX A19 (product=27)
- `create_color_temperature_light()`: Color temperature light - LIFX Mini White to Warm (product=50)
- `create_infrared_light()`: Night vision capable (product=29)
- `create_hev_light()`: LIFX Clean with HEV (product=90)
- `create_multizone_light(zone_count=None, extended_multizone=False)`: Multizone strip/beam
  - `extended_multizone=False`: LIFX Z strip (product=32, up to 16 zones)
  - `extended_multizone=True`: LIFX Beam (product=38, up to 82 zones)
  - Extended multizone devices are backwards compatible with non-extended packets
  - Zone count uses product defaults from specs if not specified
- `create_tile_device(tile_count=None)`: Tile chain (product=55)
  - Tile count and dimensions use product defaults from specs if not specified
- `create_device(product_id, zone_count=None, tile_count=None)`: Universal factory
  - Creates any device by product ID from the registry
  - Automatically uses product defaults from specs system

**Product Defaults System:**
All factory functions now use the specs system to load product-specific defaults:
- Zone counts for multizone devices (e.g., 16 for Z, 80 for Beam)
- Tile counts for matrix devices (e.g., 5 for Tiles)
- Tile dimensions (e.g., 8x8 for Tiles, 5x6 for Candles)
- Users can override these defaults by passing explicit parameters

## Key Implementation Details

### MultiZone Handling
- Standard multizone: Returns multiple `StateMultiZone` packets (type 506), each containing up to 8 zones
- Extended multizone: Returns one or more `ExtendedStateMultiZone` packet (type 512) with with up to 82 zones
- Zone colors stored in `DeviceState.zone_colors` list indexed by zone number

### Tile Handling
- Matrix devices support up to 5 tiles in a chain, but most only have 1.
- Each tile has width×height zones (8×8 or 16×8). All tiles on a chain should be identical in size.
- `Get64`/`Set64` packets transfer up to 64 zones at a time using a rectangle specification
- Tiles with more than 64 zones (16×8) require multiple Get64 requests with different y coordinates
- Tile state stored in `DeviceState.tile_devices` list, each with `colors` array

### Testing Scenarios
Configure via ScenarioConfig in HierarchicalScenarioManager:
- `drop_packets`: Dict mapping packet type to drop rate (0.0-1.0, where 1.0 = always drop)
- `response_delays`: Dict mapping packet type to delay in seconds
- `malformed_packets`: List of packet types to truncate/corrupt
- `invalid_field_values`: List of packet types to send with all 0xFF bytes
- `partial_responses`: List of packet types to send incomplete multizone/tile data
- `firmware_version`: Tuple of (major, minor) to override firmware version
- `send_unhandled`: Boolean to send StateUnhandled for unknown packet types

### Packet Flow
1. UDP packet arrives at `EmulatedLifxServer.handle_packet()`
2. Header unpacked via `LifxHeader.unpack()`
3. Payload unpacked to packet object using `get_packet_class()` and `.unpack()`
4. Target devices determined (broadcast or specific serial from target field)
5. For each device: `device.process_packet()` returns list of (header, packet) responses
6. Acknowledgment (type 45) sent if `ack_required=True`
7. Response packets packed and sent back to client via UDP

## Important Patterns

- **Acknowledgments are automatic**: `process_packet()` handles ack_required flag before calling packet-specific handlers
- **Handlers return packets, not (header, packet) tuples**: The `process_packet()` method constructs response headers
- **Handlers can return lists**: For multizone/tile responses that need multiple packets
- **res_required flag**: Handler functions receive this to decide whether to return state packet
- **serial format**: 12-character hex string (e.g., "d073d5000001") converted to 6-byte MAC + 2 null bytes

## Python Version and Dependencies

- Requires Python 3.13+
- Uses modern Python features: dataclasses, type hints, pattern matching (if present)
- Key dependencies: `pyyaml` for config, asyncio for networking
- Dev dependencies: `pytest`, `pytest-asyncio`, `ruff`, `pyright`, `hatchling`
- Never use the term or phrase "wide tile device". Use "large matrix device" or "chained matrix device" instead
