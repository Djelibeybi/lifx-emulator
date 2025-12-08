# Code Navigation Guide

> Developer-focused guide to navigating the lifx-emulator codebase

## Quick Stats

- **Core Library**: 13,654 lines of Python across 41 files
- **Standalone App**: 1,672 lines of Python across modules
- **Test Coverage**: 95% (764 test cases)
- **Documentation**: 41 markdown files

## Package Structure

```
lifx-emulator/
├── packages/
│   ├── lifx-emulator-core/          # Library package (13.6k LOC)
│   │   └── src/lifx_emulator/
│   │       ├── devices/             # Device lifecycle and state (10 files)
│   │       ├── scenarios/           # Test scenario management (3 files)
│   │       ├── protocol/            # LIFX binary protocol (7 files)
│   │       ├── handlers/            # Packet type handlers (5 files)
│   │       ├── products/            # Product registry (4 files)
│   │       ├── factories/           # Device creation (6 files)
│   │       ├── repositories/        # Storage abstraction (3 files)
│   │       └── server.py            # UDP server
│   │
│   └── lifx-emulator/               # Standalone package (1.6k LOC)
│       └── src/lifx_emulator_app/
│           ├── __main__.py          # CLI entry point
│           └── api/                 # HTTP API module
│               ├── app.py           # FastAPI application
│               ├── models.py        # Pydantic models
│               ├── routers/         # API endpoints
│               └── services/        # Business logic
│
├── docs/                            # MkDocs documentation (41 files)
└── pyproject.toml                   # Workspace config
```

## Core Library (`lifx-emulator-core`)

### Entry Points

**Main exports** (`packages/lifx-emulator-core/src/lifx_emulator/__init__.py:1`)
```python
from lifx_emulator import (
    EmulatedLifxServer,      # UDP server
    EmulatedLifxDevice,      # Device instance
    create_color_light,      # Factory functions
    create_multizone_light,
    create_tile_device,
)
```

### Layer Architecture

#### 1. Network Layer
**Purpose**: UDP protocol handling

- `server.py:1` - `EmulatedLifxServer`
  - Responsibilities: Network I/O, packet routing
  - Dependencies: `DeviceManager`, `HierarchicalScenarioManager`
  - Protocol: asyncio DatagramProtocol

#### 2. Domain Layer
**Purpose**: Business logic and device management

**Device Management** (`devices/`)
- `devices/manager.py:1` - `DeviceManager`
  - Device lifecycle: add, remove, get, count
  - Packet routing: target resolution, broadcast handling
  - Scenario cache invalidation

- `devices/device.py:1` - `EmulatedLifxDevice`
  - Main entry: `process_packet()` (line ~100)
  - Packet dispatcher: `_handle_packet_type()` (line ~200)
  - State storage: `DeviceState` dataclass

**Scenario Management** (`scenarios/`)
- `scenarios/manager.py:1` - `HierarchicalScenarioManager`
  - 5-level precedence: device > type > location > group > global
  - Scenario merging and caching
  - Configuration: `ScenarioConfig` dataclass

**Protocol Layer** (`protocol/`)
- `protocol/packets.py:1` - Auto-generated packet classes
  - 44+ packet types organized by namespace (Device, Light, MultiZone, Tile)
  - Each class: `PKT_TYPE`, `pack()`, `unpack()`
  - Registry: `PACKET_REGISTRY` dict

- `protocol/header.py:1` - `LifxHeader`
  - 36-byte LIFX packet header
  - Key fields: target, source, sequence, pkt_type, flags

**Handler Registry** (`handlers/`)
- `handlers/registry.py:1` - `PacketHandlerRegistry`
  - Maps packet types → handler functions
  - Modular handlers by namespace:
    - `device_handlers.py:1` - Device.* packets (types 2-59)
    - `light_handlers.py:1` - Light.* packets (types 101-149)
    - `multizone_handlers.py:1` - MultiZone.* packets (types 501-512)
    - `tile_handlers.py:1` - Tile.* packets (types 701-720)

#### 3. Repository Layer
**Purpose**: Storage abstraction

**Interfaces** (`repositories/`)
- `repositories/storage_backend.py:1`
  - `IDeviceRepository` - In-memory device collection
  - `IDeviceStorageBackend` - Device state persistence
  - `IScenarioStorageBackend` - Scenario persistence

**Implementations**
- `repositories/device_repository.py:1` - In-memory dict storage
- `devices/persistence.py:1` - Async file persistence with debouncing
- `scenarios/persistence.py:1` - Atomic scenario file writes

#### 4. State Management
**Purpose**: Device state representation

**State Dataclasses** (`devices/states.py:1`)
```python
@dataclass
class DeviceState:
    """Complete device state"""
    core: CoreDeviceState        # Serial, power, label, firmware
    color: ColorState | None      # HSBK color for color devices
    infrared: InfraredState | None
    hev: HevState | None
    multizone: MultiZoneState | None
    matrix: MatrixState | None
    relay: RelayState | None
```

**Capability Detection**
- `has_color`, `has_infrared`, `has_multizone`, `has_matrix`, `has_hev`
- `has_relays`, `has_buttons` (for LIFX Switch devices)

### Factory System

**Factory Functions** (`factories/factory.py:1`)
```python
# Simple factories
create_color_light(serial, storage) -> EmulatedLifxDevice
create_multizone_light(serial, zone_count, extended_multizone, storage)
create_tile_device(serial, tile_count, storage)
create_switch(serial, product_id, storage)

# Universal factory
create_device(product_id, serial, zone_count, tile_count, storage)
```

**Builder Pattern** (`factories/builder.py:1`)
```python
builder = (
    DeviceBuilder()
    .with_serial("d073d5000001")
    .with_product(27)  # LIFX A19
    .with_color_support()
    .with_infrared_support()
    .build()
)
```

**Configuration Services**
- `factories/serial_generator.py:1` - Serial number generation
- `factories/firmware_config.py:1` - Firmware version logic
- `factories/default_config.py:1` - Default color/power values

### Product Registry

**Registry** (`products/registry.py:1`)
- **Auto-generated** from LIFX GitHub (DO NOT EDIT)
- 137+ product definitions with capabilities
- Pre-built `ProductInfo` instances

**Specs** (`products/specs.py:1` + `specs.yml`)
- Product-specific configuration
- Zone counts, tile dimensions, defaults
- Manually maintained for accuracy

**Generator** (`products/generator.py:1`)
```bash
python -m lifx_emulator.products.generator
# Downloads latest products.json
# Regenerates registry.py
# Updates specs.yml templates
```

### Protocol Components

**Serializer** (`protocol/serializer.py:1`)
- Low-level binary packing/unpacking
- Handles: byte arrays, enums, nested types, arrays

**Types** (`protocol/protocol_types.py:1`)
- `LightHsbk` - Color representation
- `TileStateDevice` - Tile configuration
- Effect settings, enums, constants

**Generator** (`protocol/generator.py:1`)
```bash
python -m lifx_emulator.protocol.generator
# Regenerates packets.py from LIFX YAML spec
```

## Standalone App (`lifx-emulator`)

### CLI Entry Point

**Main** (`packages/lifx-emulator/src/lifx_emulator_app/__main__.py:1`)
- Command-line argument parsing (cyclopts)
- Device creation from CLI parameters
- Server startup and lifecycle management
- Subcommands: `list-products`

### HTTP API Module

**FastAPI App** (`api/app.py:1`)
```python
def create_api_app(server: EmulatedLifxServer) -> FastAPI:
    """Creates OpenAPI 3.1.0 compliant FastAPI application"""

def run_api_server(server, host, port):
    """Run uvicorn ASGI server"""
```

**Routers** (`api/routers/`)
- `monitoring.py` - `/api/stats`, `/api/activity`
- `devices.py` - `/api/devices`, `/api/devices/{serial}`
- `scenarios.py` - `/api/scenarios/*` (5 scope levels)

**Models** (`api/models.py:1`)
- Pydantic request/response validation
- OpenAPI schema generation
- Type-safe API contracts

**Services** (`api/services/`)
- Business logic layer
- Separates API concerns from domain logic

## Key File Locations

### Configuration
- `pyproject.toml:1` - Workspace configuration
- `packages/lifx-emulator-core/pyproject.toml:1` - Library package config
- `packages/lifx-emulator/pyproject.toml:1` - App package config

### Testing
- `packages/lifx-emulator-core/tests/` - Library tests
- `packages/lifx-emulator/tests/` - App/API tests
- Test count: 764 total

### Documentation
- `docs/` - MkDocs documentation (41 files)
- `CLAUDE.md:1` - AI assistant guidance
- `README.md:1` - Project overview

### Auto-Generated (DO NOT EDIT)
- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py:1`
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py:1`

## Common Code Paths

### Creating a Device
```
CLI Args
  ↓
__main__.py:main()
  ↓
factories/factory.py:create_*()
  ↓
factories/builder.py:DeviceBuilder
  ↓
devices/device.py:EmulatedLifxDevice()
```

### Processing a Packet
```
UDP Socket
  ↓
server.py:EmulatedLifxServer.handle_packet()
  ↓
devices/manager.py:DeviceManager.route_packet()
  ↓
devices/device.py:EmulatedLifxDevice.process_packet()
  ↓
handlers/registry.py:PacketHandlerRegistry.get_handler()
  ↓
handlers/*_handlers.py:handle_*()
  ↓
Response packets sent via UDP
```

### Scenario Application
```
Scenario Config
  ↓
scenarios/manager.py:HierarchicalScenarioManager.set_*_scenario()
  ↓
Cache invalidation
  ↓
devices/device.py:EmulatedLifxDevice.invalidate_scenario_cache()
  ↓
Next packet: get_scenario_for_device()
  ↓
Merged scenario applied (drop/delay/malform)
```

### State Persistence
```
State Change
  ↓
devices/device.py:EmulatedLifxDevice.state (modified)
  ↓
Observer pattern: notify state change
  ↓
devices/persistence.py:DevicePersistenceAsyncFile.save_device_state()
  ↓
Debounced async write (100ms default)
  ↓
JSON file: ~/.lifx-emulator/{serial}.json
```

## Development Workflow

### Quick Commands
```bash
# Code quality
ruff check --fix .                # Lint and auto-fix
pyright                          # Type checking
pytest -v                        # Run all tests

# Run emulator
python -m lifx_emulator_app      # CLI mode
lifx-emulator --api              # With HTTP API

# Regenerate code
python -m lifx_emulator.products.generator   # Update registry
python -m lifx_emulator.protocol.generator   # Update packets
```

### Testing Specific Components
```bash
# Test specific module
pytest packages/lifx-emulator-core/tests/test_device.py -v

# Test with coverage
pytest --cov=lifx_emulator --cov-report=html

# Run specific test
pytest packages/lifx-emulator-core/tests/test_device.py::test_process_packet -v
```

## Module Dependencies

### Core Library Dependencies
```
lifx_emulator/
├── server.py → devices.manager, scenarios.manager
├── devices/
│   ├── device.py → states, handlers.registry, scenarios.models
│   ├── manager.py → repositories.device_repository
│   ├── persistence.py → repositories.storage_backend
│   └── states.py → (no internal deps)
├── scenarios/
│   ├── manager.py → models, persistence
│   └── models.py → (pydantic only)
├── protocol/
│   ├── packets.py → header, serializer, protocol_types
│   └── header.py → (struct only)
├── handlers/
│   └── *_handlers.py → protocol.packets, devices.states
├── products/
│   └── registry.py → specs
└── factories/
    └── factory.py → builder, devices.device, products.registry
```

### External Dependencies
- **pydantic**: State validation, API models
- **pyyaml**: Product specs loading
- **fastapi**: HTTP API (app only)
- **uvicorn**: ASGI server (app only)
- **cyclopts**: CLI parsing (app only)
- **rich**: Terminal UI (app only)

## Cross-Reference Index

### By Feature

**Device Creation**
- Entry: `factories/__init__.py:1`
- Functions: `factories/factory.py:1`
- Builder: `factories/builder.py:1`
- Docs: `docs/library/factories.md:1`

**Packet Processing**
- Entry: `devices/device.py:100` (process_packet)
- Handlers: `handlers/registry.py:1`
- Protocol: `protocol/packets.py:1`
- Docs: `docs/architecture/packet-flow.md:1`

**State Management**
- States: `devices/states.py:1`
- Persistence: `devices/persistence.py:1`
- Serialization: `devices/state_serializer.py:1`
- Docs: `docs/architecture/device-state.md:1`, `docs/library/storage.md:1`

**Scenario Management**
- Manager: `scenarios/manager.py:1`
- Models: `scenarios/models.py:1`
- API: `api/routers/scenarios.py:1`
- Docs: `docs/guide/testing-scenarios.md:1`, `docs/cli/scenario-api.md:1`

**HTTP API**
- App: `api/app.py:1`
- Routers: `api/routers/`
- Models: `api/models.py:1`
- Docs: `docs/cli/web-interface.md:1`, `docs/cli/device-management-api.md:1`

### By Layer

**Network Layer**
- `server.py:1` - UDP server
- Docs: `docs/library/server.md:1`

**Domain Layer**
- `devices/manager.py:1` - Device management
- `scenarios/manager.py:1` - Scenario management
- Docs: `docs/architecture/overview.md:1`

**Repository Layer**
- `repositories/device_repository.py:1` - In-memory storage
- `repositories/storage_backend.py:1` - Interfaces
- Docs: `docs/architecture/overview.md:1` (Repository Pattern section)

**Persistence Layer**
- `devices/persistence.py:1` - Device state files
- `scenarios/persistence.py:1` - Scenario files
- Docs: `docs/library/storage.md:1`, `docs/cli/storage.md:1`

## Next Steps

- **New to the codebase?** Start with `docs/getting-started/quickstart.md:1`
- **Adding features?** Review `docs/architecture/overview.md:1`
- **Writing tests?** Check `docs/guide/integration-testing.md:1`
- **Using the API?** See `docs/cli/device-management-api.md:1`
- **Understanding protocol?** Read `docs/architecture/protocol.md:1`

## Related Documentation

- [Architecture Overview](../architecture/overview.md) - System design
- [Device Types](../guide/device-types.md) - Supported devices
- [Testing Scenarios](../guide/testing-scenarios.md) - Error simulation
- [CLI Reference](../cli/cli-reference.md) - Command-line options
- [Library Reference](../library/index.md) - Python API
