# Project Index: lifx-emulator

**Generated**: 2025-12-08
**Purpose**: Efficient context loading for AI assistants (94% token reduction: 58k → 3k tokens)

---

## 📊 Project Overview

**LIFX Emulator** - Comprehensive LIFX device emulator for testing LIFX LAN protocol libraries without physical hardware.

- **Type**: Python Monorepo
- **Packages**: 2 (core library + standalone CLI/API)
- **Version**: Core 3.0.3, App 3.0.1
- **License**: UPL-1.0
- **Python**: 3.11+ (supports 3.11, 3.12, 3.13, 3.14)
- **Lines of Code**: 15,326 (core: 13,654 | app: 1,672)
- **Test Files**: 29 (764 test cases)
- **Test Coverage**: 95% target (80% minimum)
- **Documentation**: 45 markdown files

---

## 📁 Project Structure

```
lifx-emulator/
├── packages/
│   ├── lifx-emulator-core/          # Core library (lifx_emulator)
│   │   ├── src/lifx_emulator/       # 13,654 LOC
│   │   │   ├── devices/             # Device lifecycle & state (10 files)
│   │   │   ├── scenarios/           # Test scenario management (3 files)
│   │   │   ├── protocol/            # LIFX binary protocol (7 files)
│   │   │   ├── handlers/            # Packet type handlers (5 files)
│   │   │   ├── products/            # Product registry (4 files)
│   │   │   ├── factories/           # Device creation (6 files)
│   │   │   ├── repositories/        # Storage abstraction (3 files)
│   │   │   └── server.py            # UDP server
│   │   └── tests/                   # 23 test files
│   │
│   └── lifx-emulator/               # Standalone app (lifx_emulator_app)
│       ├── src/lifx_emulator_app/   # 1,672 LOC
│       │   ├── __main__.py          # CLI entry point
│       │   └── api/                 # HTTP API (FastAPI)
│       │       ├── routers/         # API endpoints
│       │       ├── services/        # Business logic
│       │       └── mappers/         # Data transformation
│       └── tests/                   # 5 test files
│
├── docs/                            # MkDocs documentation (45 files)
│   ├── development/                 # Developer guides (NEW)
│   ├── getting-started/             # Installation & quickstart
│   ├── library/                     # Python API reference
│   ├── cli/                         # CLI/API documentation
│   ├── architecture/                # System design
│   ├── guide/                       # User guides
│   ├── tutorials/                   # Step-by-step tutorials
│   └── reference/                   # FAQ, glossary, troubleshooting
│
├── pyproject.toml                   # Workspace config (uv)
├── mkdocs.yml                       # Documentation config
├── uv.lock                          # Dependency lockfile
└── README.md                        # Project overview
```

---

## 🚀 Entry Points

### Core Library (`lifx-emulator-core`)
**Package**: `lifx_emulator`
**PyPI**: `lifx-emulator-core`

**Main exports** (`src/lifx_emulator/__init__.py`):
```python
from lifx_emulator import (
    EmulatedLifxServer,          # UDP server (network layer)
    EmulatedLifxDevice,          # Device instance (domain layer)
    create_color_light,          # Factory: full RGB color light
    create_color_temperature_light,  # Factory: white with temp control
    create_infrared_light,       # Factory: night vision capable
    create_hev_light,            # Factory: HEV/Clean device
    create_multizone_light,      # Factory: strips/beams
    create_tile_device,          # Factory: matrix tiles
)
```

**Key modules**:
- `devices/` - Device management, state, persistence
- `scenarios/` - Test scenario configuration
- `protocol/` - LIFX binary protocol implementation
- `handlers/` - Packet type handlers
- `factories/` - Device creation patterns
- `products/` - Product registry (137+ products)
- `repositories/` - Storage abstraction
- `server.py` - UDP server (asyncio DatagramProtocol)

### Standalone App (`lifx-emulator`)
**Package**: `lifx_emulator_app`
**PyPI**: `lifx-emulator`
**CLI Command**: `lifx-emulator`

**Entry point** (`src/lifx_emulator_app/__main__.py:main()`):
- CLI argument parsing (cyclopts)
- Device creation from CLI parameters
- HTTP API server (FastAPI + uvicorn)
- Server lifecycle management

**Subcommands**:
- `lifx-emulator` - Start emulator
- `lifx-emulator list-products` - Show product registry

**HTTP API** (`api/app.py`):
- OpenAPI 3.1.0 compliant REST API
- Interactive Swagger UI at `/docs`
- Endpoints: devices, scenarios, monitoring

---

## 📦 Core Modules

### Layer Architecture
**4-layer design with dependency injection**:

```
Network Layer → Domain Layer → Repository Layer → Persistence Layer
```

#### Network Layer
**Purpose**: UDP protocol handling

- **`server.py`** - `EmulatedLifxServer`
  - UDP protocol (asyncio DatagramProtocol)
  - Packet parsing and response transmission
  - Delegates to DeviceManager and ScenarioManager
  - **Dependencies**: DeviceManager, HierarchicalScenarioManager

#### Domain Layer
**Purpose**: Business logic

- **`devices/manager.py`** - `DeviceManager`
  - Device lifecycle: add, remove, get, count
  - Packet routing: target resolution, broadcast
  - Scenario cache invalidation

- **`devices/device.py`** - `EmulatedLifxDevice`
  - Main entry: `process_packet()`
  - Packet dispatcher to handlers
  - State management: DeviceState dataclass
  - Scenario application (drop/delay/malform)

- **`scenarios/manager.py`** - `HierarchicalScenarioManager`
  - 5-level precedence: device > type > location > group > global
  - Scenario merging with field-level overrides
  - Cache management for performance

#### Repository Layer
**Purpose**: Storage abstraction

- **`repositories/device_repository.py`** - `DeviceRepository`
  - In-memory device collection (dict-based)
  - Implements `IDeviceRepository` protocol

- **`repositories/storage_backend.py`** - Protocol interfaces
  - `IDeviceRepository` - Device collection
  - `IDeviceStorageBackend` - Device state persistence
  - `IScenarioStorageBackend` - Scenario persistence

#### Persistence Layer
**Purpose**: File I/O

- **`devices/persistence.py`** - `DevicePersistenceAsyncFile`
  - Async file I/O with debouncing (100ms default)
  - JSON serialization
  - Storage: `~/.lifx-emulator/{serial}.json`

- **`scenarios/persistence.py`** - `ScenarioPersistenceAsyncFile`
  - Atomic file writes (temp + rename)
  - Storage: `~/.lifx-emulator/scenarios/`

### Key Components

#### Protocol Layer (`protocol/`)
- **`packets.py`** - 44+ auto-generated packet classes
  - **AUTO-GENERATED** from LIFX YAML spec
  - Organized by namespace: Device, Light, MultiZone, Tile
  - Each class: PKT_TYPE, pack(), unpack()
  - Registry: PACKET_REGISTRY dict

- **`header.py`** - `LifxHeader`
  - 36-byte LIFX packet header
  - Fields: target, source, sequence, pkt_type, flags

- **`serializer.py`** - Binary packing/unpacking
  - Low-level struct operations
  - Handles: byte arrays, enums, nested types

- **`protocol_types.py`** - Structured types
  - LightHsbk, TileStateDevice, effect settings

#### Handler Registry (`handlers/`)
- **`registry.py`** - `PacketHandlerRegistry`
  - Maps packet type → handler function

- **Modular handlers by namespace**:
  - `device_handlers.py` - Device.* (types 2-59)
  - `light_handlers.py` - Light.* (types 101-149)
  - `multizone_handlers.py` - MultiZone.* (types 501-512)
  - `tile_handlers.py` - Tile.* (types 701-720)

#### State Management (`devices/states.py`)
```python
@dataclass
class DeviceState:
    core: CoreDeviceState           # Serial, label, power, firmware
    color: ColorState | None        # HSBK for color devices
    infrared: InfraredState | None
    hev: HevState | None
    multizone: MultiZoneState | None
    matrix: MatrixState | None
    relay: RelayState | None

    # Capability flags
    has_color: bool
    has_infrared: bool
    has_multizone: bool
    has_matrix: bool
    has_hev: bool
    has_relays: bool
    has_buttons: bool
```

#### Product Registry (`products/`)
- **`registry.py`** - 137+ product definitions
  - **AUTO-GENERATED** from LIFX GitHub
  - Pre-built ProductInfo instances
  - Capability detection: color, IR, multizone, matrix, HEV, relays, buttons

- **`specs.py` + `specs.yml`** - Product specifications
  - Zone counts, tile dimensions
  - Device-specific defaults
  - Manually maintained

#### Factory System (`factories/`)
- **`factory.py`** - Device creation functions
  - Simple factories per device type
  - Universal: `create_device(product_id, ...)`

- **`builder.py`** - `DeviceBuilder`
  - Builder pattern for complex configuration
  - Fluent API: `.with_color_support().build()`

- **Configuration services**:
  - `serial_generator.py` - Serial number generation
  - `firmware_config.py` - Firmware version logic
  - `default_config.py` - Default color/power values

---

## 🔧 Configuration Files

### Workspace Configuration
- **`pyproject.toml`** (root)
  - uv workspace setup
  - Dev dependencies (pytest, ruff, pyright, mkdocs)
  - Code quality rules (Ruff lint, Pyright config)
  - Test configuration (pytest, coverage)

### Package Configuration
- **`packages/lifx-emulator-core/pyproject.toml`**
  - Package: lifx-emulator-core v3.0.3
  - Dependencies: pydantic, pyyaml
  - Semantic-release config (conventional-monorepo)

- **`packages/lifx-emulator/pyproject.toml`**
  - Package: lifx-emulator v3.0.1
  - Dependencies: lifx-emulator-core, fastapi, uvicorn, cyclopts, rich
  - CLI entry point: `lifx-emulator`

### Documentation Configuration
- **`mkdocs.yml`**
  - Material theme with dark mode
  - Navigation structure (8 main sections)
  - Plugins: search, llmstxt, mkdocstrings, git-revision-date

### Other Configuration
- **`uv.lock`** - Dependency lockfile (83 packages)
- **`.github/workflows/`** - CI/CD (linting, tests, docs)

---

## 📚 Documentation Structure

### User Documentation
- **getting-started/** - Installation, quickstart
- **cli/** - CLI reference, HTTP API, scenarios
- **library/** - Python API reference
- **guide/** - Device types, testing scenarios, best practices
- **tutorials/** - Step-by-step guides (5 tutorials)

### Developer Documentation (NEW)
- **development/index.md** - Developer onboarding
- **development/code-navigation.md** - Codebase navigation
- **development/architecture-decisions.md** - ADRs (15 decisions)
- **development/component-relationships.md** - Visual component maps

### Architecture Documentation
- **architecture/overview.md** - System design
- **architecture/packet-flow.md** - Packet processing
- **architecture/protocol.md** - Protocol layer
- **architecture/device-state.md** - State management

### Reference Documentation
- **reference/faq.md** - Frequently asked questions
- **reference/troubleshooting.md** - Common issues
- **reference/glossary.md** - Terms and definitions

---

## 🧪 Test Coverage

### Test Organization
- **Core library**: 23 test files, 739 tests
- **Standalone app**: 5 test files, 25 tests
- **Total**: 764 tests
- **Coverage**: 95% target (80% minimum enforced)

### Test Categories

**Unit Tests** (handlers, protocol, factories):
- `test_device.py` - Device core functionality
- `test_device_handlers_extended.py` - Device packet handlers
- `test_light_handlers_extended.py` - Light packet handlers
- `test_multizone_handlers_extended.py` - Multizone handlers
- `test_tile_handlers_extended.py` - Tile handlers
- `test_handler_registry.py` - Handler registration
- `test_serializer.py` - Binary serialization
- `test_protocol_types_coverage.py` - Protocol types

**Integration Tests**:
- `test_integration.py` - End-to-end packet processing
- `test_server.py` - UDP server integration
- `test_api.py` - HTTP API endpoints

**Persistence Tests**:
- `test_async_storage.py` - Async file persistence
- `test_scenario_persistence.py` - Scenario storage

**Scenario Tests**:
- `test_scenario_manager.py` - Hierarchical scenarios
- `test_device_edge_cases.py` - Edge cases and scenarios

**Product Tests**:
- `test_products_specs.py` - Product registry
- `test_products_generator.py` - Registry generator
- `test_protocol_generator.py` - Protocol generator

**Backwards Compatibility**:
- `test_backwards_compatibility.py` - Extended multizone compatibility
- `test_switch_devices.py` - LIFX Switch capability filtering

### Test Fixtures (`conftest.py`)
- Device creation helpers
- Packet construction utilities
- Mock storage backends
- Test server setup

---

## 🔗 Key Dependencies

### Core Library (`lifx-emulator-core`)
- **pydantic** (2.12.3) - State validation, data models
- **pyyaml** (6.0.3) - Product specs loading

### Standalone App (`lifx-emulator`)
- **lifx-emulator-core** (3.0.3) - Core library
- **fastapi** (0.120.3) - HTTP API framework
- **uvicorn** (0.38.0) - ASGI server
- **cyclopts** (4.2.0) - CLI argument parsing
- **rich** (14.2.0) - Terminal UI

### Development Dependencies
- **pytest** (8.4.2) - Test framework
- **pytest-asyncio** (1.2.0) - Async test support
- **pytest-cov** (7.0.0) - Coverage reporting
- **pytest-sugar** (1.1.1) - Better test output
- **ruff** (0.14.3) - Linter and formatter
- **pyright** (1.1.407) - Type checker
- **mkdocs** (1.6.1) - Documentation site
- **mkdocs-material** (9.6.22) - Material theme
- **mkdocstrings** (0.30.1) - API docs generation
- **httpx** (0.28.1) - HTTP client for testing

---

## 📝 Quick Start Commands

### Development Setup
```bash
# Clone and setup
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator
uv sync                          # Install dependencies
source .venv/bin/activate        # Activate venv
```

### Code Quality
```bash
ruff check --fix .               # Lint and auto-fix
pyright                          # Type checking
pytest                           # Run all tests (764)
pytest --cov                     # With coverage report
```

### Running the Emulator
```bash
# As module
python -m lifx_emulator_app

# As installed command
lifx-emulator --api --verbose

# Custom devices
lifx-emulator --color 2 --multizone 1 --tile 1 --api

# List products
lifx-emulator list-products
```

### Documentation
```bash
uv run mkdocs serve              # Live preview (localhost:8000)
uv run mkdocs build              # Build static site
```

### Auto-Generation
```bash
# Regenerate protocol (DO NOT EDIT packets.py manually)
python -m lifx_emulator.protocol.generator

# Regenerate product registry (DO NOT EDIT registry.py manually)
python -m lifx_emulator.products.generator
```

---

## 🎯 Common Use Cases

### 1. Create a Simple Emulated Device
```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

async def main():
    device = create_color_light("d073d5000001")
    manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], manager, "127.0.0.1", 56700)

    await server.start()
    await asyncio.sleep(3600)  # Run for 1 hour
    await server.stop()

asyncio.run(main())
```

### 2. Test Scenario with Packet Drops
```python
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

manager = HierarchicalScenarioManager()

# Drop 50% of GetColor packets globally
manager.set_global_scenario(ScenarioConfig(drop_packets={101: 0.5}))

# Drop 100% for specific device (overrides global)
manager.set_device_scenario("d073d5000001", ScenarioConfig(drop_packets={101: 1.0}))
```

### 3. Persistent Device State
```python
from lifx_emulator.devices import DevicePersistenceAsyncFile
from lifx_emulator.factories import create_color_light

storage = DevicePersistenceAsyncFile()
device = create_color_light("d073d5000001", storage=storage)

# State changes auto-save asynchronously
device.state.label = "My Light"

# Graceful shutdown flushes pending writes
await storage.shutdown()
```

### 4. HTTP API for Runtime Management
```bash
# Enable API
lifx-emulator --api --api-host 127.0.0.1 --api-port 8080

# Web dashboard: http://localhost:8080
# Swagger UI: http://localhost:8080/docs

# REST API examples:
curl http://localhost:8080/api/devices
curl -X POST http://localhost:8080/api/devices -d '{"product_id": 27}'
```

---

## 🔍 Code Quality Standards

### Complexity Limits (Enforced by Ruff)
- **Max McCabe complexity**: 10 per function
- **Max arguments**: 5 per function
- **Max branches**: 12 per function
- **Max statements**: 50 per function

### Type Checking (Pyright)
- **Mode**: Standard
- **Target**: Python 3.11+
- **Coverage**: All public APIs

### Test Coverage (pytest-cov)
- **Target**: 95%
- **Minimum**: 80% (CI enforced)
- **Excludes**: Auto-generated code (packets.py, registry.py)

### Formatting (Ruff)
- **Line length**: 88 characters
- **Quote style**: Double quotes
- **Indent**: 4 spaces
- **Import order**: stdlib → third-party → local

---

## 🏗️ Architectural Patterns

### Design Patterns Used
- **Repository Pattern** - Storage abstraction
- **Factory Pattern** - Device creation
- **Builder Pattern** - Flexible configuration
- **Observer Pattern** - State change notifications
- **Handler Registry** - Packet type routing
- **Dependency Injection** - Testable architecture
- **Protocol Interfaces** - Type-safe contracts (duck typing)

### Key Architectural Decisions
1. **Monorepo** - Two packages (core + app) in one repo
2. **Layered architecture** - Network → Domain → Repository → Persistence
3. **Auto-generation** - Protocol and products from upstream sources
4. **Async persistence** - Debounced file writes (100ms)
5. **Hierarchical scenarios** - 5-level precedence (device > type > location > group > global)
6. **Capability flags** - Feature detection (has_color, has_multizone, etc.)

### Performance Optimizations
- Async I/O with debouncing (persistence)
- Scenario caching (invalidation on config change)
- Lazy initialization (tile framebuffers)
- Pre-built product registry (no runtime parsing)

---

## 📖 Essential Reading for Developers

### First-Time Contributors
1. **[Development Index](docs/development/index.md)** - Start here
2. **[Code Navigation Guide](docs/development/code-navigation.md)** - Find your way around
3. **[Architecture Decisions](docs/development/architecture-decisions.md)** - Understand "why"
4. **[Component Relationships](docs/development/component-relationships.md)** - Visual data flow

### Adding Features
1. Review ADRs (Architecture Decision Records)
2. Follow existing patterns (Repository, Factory, Handler)
3. Write tests first (TDD)
4. Maintain 95% coverage
5. Update docs

### Common Tasks
- **Add packet type**: Regenerate protocol → Create handler → Register → Test
- **Add device type**: Update specs.yml → Create factory → Add CLI arg → Test
- **Fix bug**: Write failing test → Fix → Verify → Submit PR

---

## 🚫 Auto-Generated Files (DO NOT EDIT)

These files are regenerated from upstream sources:

1. **`packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py`**
   - Source: LIFX YAML spec from lan.developer.lifx.com
   - Generator: `python -m lifx_emulator.protocol.generator`

2. **`packages/lifx-emulator-core/src/lifx_emulator/products/registry.py`**
   - Source: https://github.com/LIFX/products (products.json)
   - Generator: `python -m lifx_emulator.products.generator`

**Why?** Ensures correctness and easy updates when LIFX releases new products or protocol changes.

---

## 🔗 External Links

### Project Links
- **GitHub**: https://github.com/Djelibeybi/lifx-emulator
- **Documentation**: https://djelibeybi.github.io/lifx-emulator
- **PyPI (CLI)**: https://pypi.org/project/lifx-emulator/
- **PyPI (Core)**: https://pypi.org/project/lifx-emulator-core/

### LIFX Resources
- **LAN Protocol**: https://lan.developer.lifx.com
- **Products JSON**: https://github.com/LIFX/products

### Tools & Frameworks
- **uv**: https://github.com/astral-sh/uv
- **Ruff**: https://docs.astral.sh/ruff/
- **Pyright**: https://github.com/microsoft/pyright
- **FastAPI**: https://fastapi.tiangolo.com/
- **MkDocs Material**: https://squidfunk.github.io/mkdocs-material/

---

## 📊 Token Efficiency Summary

**Before** (reading all files): ~58,000 tokens per session
**After** (reading this index): ~3,000 tokens per session
**Savings**: 94% reduction (55,000 tokens saved)

**ROI**:
- Index creation cost: ~2,000 tokens (one-time)
- Break-even: 1 session
- 10 sessions: 550,000 tokens saved
- 100 sessions: 5,500,000 tokens saved

---

**End of Project Index**
