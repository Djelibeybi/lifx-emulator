# Codebase Structure

## Repository Layout
```
lifx-emulator/
├── pyproject.toml                    # Workspace config (uv workspace)
├── uv.lock                          # Dependency lock file
├── packages/
│   ├── lifx-emulator-core/          # Library package
│   └── lifx-emulator/               # Standalone package
├── docs/                            # MkDocs documentation
├── .github/                         # GitHub Actions CI/CD
├── .serena/                         # Serena MCP memories
└── README.md
```

## Library Package (lifx-emulator-core)

### Location
`packages/lifx-emulator-core/`

### Structure
```
packages/lifx-emulator-core/
├── pyproject.toml                   # Package metadata and dependencies
├── README.md
├── src/lifx_emulator/               # Main source code
│   ├── __init__.py                  # Public API exports
│   ├── server.py                    # EmulatedLifxServer (UDP network layer)
│   ├── constants.py                 # Global constants
│   ├── devices/                     # Device module
│   │   ├── device.py                # EmulatedLifxDevice class
│   │   ├── manager.py               # DeviceManager (domain logic)
│   │   ├── states.py                # DeviceState dataclasses
│   │   ├── persistence.py           # DevicePersistenceAsyncFile (storage)
│   │   ├── state_restorer.py        # State restoration from storage
│   │   ├── state_serializer.py      # State serialization
│   │   └── observers.py             # Device state observation patterns
│   ├── scenarios/                   # Scenario module
│   │   ├── manager.py               # HierarchicalScenarioManager
│   │   ├── models.py                # ScenarioConfig dataclass
│   │   └── persistence.py           # Scenario persistence
│   ├── repositories/                # Repository module
│   │   ├── device_repository.py     # In-memory device storage
│   │   └── storage_backend.py       # Storage protocol interfaces
│   ├── handlers/                    # Packet handler module
│   │   ├── registry.py              # Handler registry
│   │   ├── base.py                  # Base handler class
│   │   ├── device_handlers.py       # Device.* packet handlers
│   │   ├── light_handlers.py        # Light.* packet handlers
│   │   ├── multizone_handlers.py    # MultiZone.* packet handlers
│   │   └── tile_handlers.py         # Tile.* packet handlers
│   ├── protocol/                    # Protocol module
│   │   ├── packets.py               # Auto-generated packet classes
│   │   ├── header.py                # LifxHeader (36-byte header)
│   │   ├── serializer.py            # Binary packing/unpacking
│   │   ├── protocol_types.py        # Protocol types (LightHsbk, etc.)
│   │   ├── const.py                 # Protocol constants
│   │   ├── base.py                  # Base packet class
│   │   └── generator.py             # Packet code generator
│   ├── products/                    # Product registry module
│   │   ├── registry.py              # Auto-generated product registry
│   │   ├── specs.py                 # Product specs loader
│   │   ├── specs.yml                # Product-specific configuration
│   │   └── generator.py             # Registry generator
│   └── factories/                   # Factory module
│       ├── factory.py               # Device factory functions
│       ├── builder.py               # DeviceBuilder class
│       ├── default_config.py        # Default device configurations
│       ├── firmware_config.py       # Firmware version configuration
│       └── serial_generator.py      # Serial number generation
└── tests/                           # Library tests
    ├── conftest.py                  # Pytest fixtures
    ├── test_device.py               # Device tests
    ├── test_server.py               # Server tests
    ├── test_scenario_manager.py     # Scenario tests
    └── [20+ other test files]
```

### Auto-Generated Files (Do Not Edit Manually)
1. `src/lifx_emulator/products/registry.py` - Regenerate with `python -m lifx_emulator.products.generator`
2. `src/lifx_emulator/protocol/packets.py` - Regenerate with `python -m lifx_emulator.protocol.generator`

## Standalone Package (lifx-emulator)

### Location
`packages/lifx-emulator/`

### Structure
```
packages/lifx-emulator/
├── pyproject.toml                   # Package metadata and dependencies
├── README.md
├── src/lifx_emulator_app/           # Main source code
│   ├── __init__.py                  # Public API exports
│   ├── __main__.py                  # CLI entry point
│   └── api/                         # HTTP API module
│       ├── app.py                   # FastAPI application
│       ├── models.py                # Pydantic request/response models
│       ├── routers/                 # API endpoint handlers
│       │   ├── monitoring.py        # Monitoring endpoints
│       │   ├── devices.py           # Device management endpoints
│       │   └── scenarios.py         # Scenario management endpoints
│       └── services/                # Business logic layer
│           ├── device_service.py    # Device operations
│           └── scenario_service.py  # Scenario operations
└── tests/                           # Standalone package tests
    ├── conftest.py                  # Pytest fixtures
    ├── test_cli.py                  # CLI tests
    └── test_api.py                  # API tests
```

## Documentation

### Location
`docs/`

### Structure
```
docs/
├── index.md                         # Landing page
├── getting-started/
│   ├── installation.md
│   └── quickstart.md
├── guide/
│   ├── overview.md
│   ├── device-types.md
│   └── scenario-api.md
└── advanced/
    ├── device-management-api.md
    └── persistent-storage.md
```

## Configuration Files

### Root Level
- `pyproject.toml` - Workspace config, Ruff, Pyright, Pytest, Coverage settings
- `uv.lock` - Locked dependencies for reproducible builds
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `mkdocs.yml` - Documentation site configuration
- `.gitignore` - Git ignore patterns
- `renovate.json` - Dependency update automation

### Package Level
- `packages/lifx-emulator-core/pyproject.toml` - Core library metadata
- `packages/lifx-emulator/pyproject.toml` - Standalone package metadata

## Import Patterns

### Library Imports (from lifx-emulator-core)
```python
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState, DeviceManager
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.factories import create_color_light, create_device
from lifx_emulator.server import EmulatedLifxServer
```

### App Imports (from lifx-emulator)
```python
from lifx_emulator_app.api import create_api_app, run_api_server
```

## Key Architectural Patterns

### Layered Architecture
1. **Network Layer**: `EmulatedLifxServer` (UDP protocol)
2. **Domain Layer**: `DeviceManager`, `HierarchicalScenarioManager` (business logic)
3. **Repository Layer**: `IDeviceRepository`, `IDeviceStorageBackend` (storage abstraction)
4. **Persistence Layer**: `DevicePersistenceAsyncFile`, `ScenarioPersistenceAsyncFile` (file I/O)

### Dependency Injection
All major components use dependency injection for testability:
- `EmulatedLifxServer` receives `DeviceManager`
- `DeviceManager` receives `IDeviceRepository`
- `EmulatedLifxDevice` receives `DevicePersistenceAsyncFile`, `HandlerRegistry`, `HierarchicalScenarioManager`

### Protocol Interfaces
- `IDeviceRepository` - Device collection storage
- `IDeviceStorageBackend` - Device state persistence
- `IScenarioStorageBackend` - Scenario persistence
- Enables easy mocking and alternative implementations
