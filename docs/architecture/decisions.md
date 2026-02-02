# Architectural Decision Records

> Key architectural decisions and design patterns in the lifx-emulator project

## Overview

This document captures the reasoning behind major architectural decisions in the lifx-emulator codebase. Understanding these decisions helps developers maintain consistency and make informed changes.

## ADR-001: Monorepo with Separate Packages

**Status**: Adopted

**Context**: The emulator needs to serve two distinct audiences:
1. End users wanting a ready-to-run CLI tool
2. Library developers wanting to embed emulation in their test suites

**Decision**: Use a monorepo with two separate packages:
- `lifx-emulator` (standalone CLI + HTTP API)
- `lifx-emulator-core` (embeddable library)

**Consequences**:
- ✅ Clear separation of concerns
- ✅ Users don't install unnecessary dependencies (FastAPI, uvicorn for library users)
- ✅ Single codebase for maintenance
- ✅ Shared development tools (pytest, ruff, pyright)
- ⚠️ Requires careful dependency management
- ⚠️ Independent versioning (semantic-release with conventional-monorepo)

**Implementation**: `pyproject.toml` - uv workspace configuration

---

## ADR-002: Layered Architecture with Dependency Injection

**Status**: Adopted

**Context**: The emulator needs to be testable, flexible, and maintainable with clear separation between network I/O, business logic, and persistence.

**Decision**: Implement a 4-layer architecture with dependency injection:

```
Network Layer → Domain Layer → Repository Layer → Persistence Layer
    ↓               ↓              ↓                    ↓
EmulatedLifxServer  DeviceManager  DeviceRepository    AsyncFile
                    ScenarioMgr    Interfaces          Storage
```

**Consequences**:
- ✅ Single Responsibility Principle - each layer has one clear purpose
- ✅ Testability - easy to inject mocks for unit testing
- ✅ Flexibility - can swap storage backends without changing domain logic
- ✅ Dependency Inversion - layers depend on Protocol interfaces, not implementations
- ⚠️ More complex initialization (requires explicit dependency wiring)
- ⚠️ Developers must understand layer boundaries

**Example** (`server.py`):
```python
# Constructor requires dependencies
EmulatedLifxServer(
    devices,
    device_manager,  # REQUIRED - injected dependency
    bind_address,
    port
)
```

**Reference**: `docs/architecture/overview.md` - Repository Pattern section

---

## ADR-003: Protocol Interfaces for Testability

**Status**: Adopted

**Context**: Need to enable unit testing with mocks while maintaining type safety.

**Decision**: Define Protocol interfaces for all dependency boundaries:
- `IDeviceManager` - Device lifecycle operations
- `IDeviceRepository` - In-memory device collection
- `IDeviceStorageBackend` - Device state persistence
- `IScenarioStorageBackend` - Scenario persistence

**Consequences**:
- ✅ Type-safe duck typing with Protocol classes
- ✅ Easy to create test doubles (no inheritance required)
- ✅ Clear contracts at layer boundaries
- ✅ Pyright validation of implementations
- ⚠️ Must keep Protocol in sync with implementations

**Implementation**: `repositories/storage_backend.py`

---

## ADR-004: Auto-Generated Protocol Code

**Status**: Adopted

**Context**: The LIFX LAN protocol has 44+ packet types with complex binary structures. Manual implementation is error-prone and hard to maintain.

**Decision**: Auto-generate `protocol/packets.py` from LIFX YAML specification.

**Consequences**:
- ✅ Guaranteed correctness with upstream protocol
- ✅ Easy to update when LIFX adds new packet types
- ✅ Eliminates manual struct packing errors
- ⚠️ Must regenerate when protocol changes
- ⚠️ Generated code is verbose and not human-editable
- ⚠️ Requires generator.py maintenance

**DO NOT EDIT**: `protocol/packets.py`

**Regenerate with**:
```bash
python -m lifx_emulator.protocol.generator
```

**Reference**: `protocol/generator.py`

---

## ADR-005: Auto-Generated Product Registry

**Status**: Adopted

**Context**: LIFX has 137+ products with varying capabilities, temperature ranges, and firmware requirements. Manual maintenance is infeasible.

**Decision**: Auto-generate `products/registry.py` from official LIFX products.json on GitHub.

**Consequences**:
- ✅ Always up-to-date with official LIFX products
- ✅ Accurate capability detection (extended multizone, IR, HEV, etc.)
- ✅ Firmware requirement tracking
- ⚠️ Must regenerate when new products are released
- ⚠️ Requires manual specs.yml updates for new multizone/matrix products

**DO NOT EDIT**: `products/registry.py`

**Regenerate with**:
```bash
python -m lifx_emulator.products.generator
```

**Reference**: `products/generator.py`

---

## ADR-006: Async File Persistence with Debouncing

**Status**: Adopted

**Context**: Device state changes frequently (color, power, zones). Synchronous I/O on every change would block the event loop and cause performance issues.

**Decision**: Implement async file persistence with debouncing:
- Queue state changes in memory
- Debounce writes (100ms default)
- Async file I/O (aiofiles)
- Graceful shutdown flushes pending writes

**Consequences**:
- ✅ Non-blocking I/O - doesn't slow down packet processing
- ✅ Reduced disk writes - batches rapid changes
- ✅ Automatic - no manual save() calls required
- ⚠️ State changes have eventual consistency (100ms delay)
- ⚠️ Must call shutdown() for clean exit

**Implementation**: `devices/persistence.py` - `DevicePersistenceAsyncFile`

**Usage**:
```python
storage = DevicePersistenceAsyncFile()
device = create_color_light("d073d5000001", storage=storage)

# State changes auto-save asynchronously
device.state.label = "My Light"

# Graceful shutdown
await storage.shutdown()
```

**Reference**: `docs/library/storage.md`

---

## ADR-007: Handler Registry Pattern

**Status**: Adopted

**Context**: The emulator must handle 44+ different packet types with varying complexity. A single giant switch statement would violate Single Responsibility Principle.

**Decision**: Use a handler registry pattern:
- Separate handler modules by packet namespace (Device, Light, MultiZone, Tile)
- Registry maps packet type → handler function
- Handlers are pure functions (state in, responses out)

**Consequences**:
- ✅ Separation of Concerns - each handler is independent
- ✅ Easy to add new packet types
- ✅ Testable - handlers are pure functions
- ✅ Organized by protocol namespace
- ⚠️ Must register new handlers in registry

**Implementation**:
```
handlers/
├── registry.py           # PacketHandlerRegistry
├── device_handlers.py    # Device.* packets (types 2-59)
├── light_handlers.py     # Light.* packets (types 101-149)
├── multizone_handlers.py # MultiZone.* packets (types 501-512)
└── tile_handlers.py      # Tile.* packets (types 701-720)
```

**Reference**: `docs/architecture/packet-flow.md`

---

## ADR-008: Dataclass-Based State Management

**Status**: Adopted

**Context**: Device state is complex and varies by device type. Need type-safe, validated state representation.

**Decision**: Use nested dataclasses with capability flags:

```python
@dataclass
class DeviceState:
    core: CoreDeviceState           # Always present
    color: ColorState | None        # Only for color devices
    infrared: InfraredState | None
    hev: HevState | None
    multizone: MultiZoneState | None
    matrix: MatrixState | None
    relay: RelayState | None

    # Capability flags
    has_color: bool
    has_infrared: bool
    # ... etc
```

**Consequences**:
- ✅ Type-safe with Pyright validation
- ✅ Clear capability detection (has_color, has_multizone, etc.)
- ✅ Easy to serialize/deserialize
- ✅ Immutable-by-default with frozen=True option
- ⚠️ Must update serialization when adding fields
- ⚠️ Capability flags must stay in sync with state fields

**Implementation**: `devices/states.py`

**Reference**: `docs/architecture/device-state.md`

---

## ADR-009: Hierarchical Scenario Management

**Status**: Adopted

**Context**: Testing scenarios need to apply at different scopes (specific device, all multizone devices, entire server). Need a consistent resolution strategy.

**Decision**: Implement 5-level hierarchical scenario system with precedence:

1. **Device-specific** (serial)
2. **Device-type** (color, multizone, matrix, hev, infrared, extended_multizone)
3. **Location-based** (all devices in location)
4. **Group-based** (all devices in group)
5. **Global** (all devices)

Higher precedence wins, with field-level merging.

**Consequences**:
- ✅ Flexible test scenario targeting
- ✅ Clear precedence rules (no ambiguity)
- ✅ Field-level merging allows partial overrides
- ✅ Cache invalidation for performance
- ⚠️ Complex scenario resolution logic
- ⚠️ Developers must understand precedence rules

**Example**:
```python
manager = HierarchicalScenarioManager()

# Global: drop 50% of packets
manager.set_global_scenario(ScenarioConfig(drop_packets={101: 0.5}))

# Type: all multizone devices delay responses
manager.set_type_scenario("multizone", ScenarioConfig(response_delays={506: 0.2}))

# Device: specific device drops 100% (overrides global)
manager.set_device_scenario("d073d5000001", ScenarioConfig(drop_packets={101: 1.0}))
```

**Implementation**: `scenarios/manager.py`

**Reference**: `docs/guide/testing-scenarios.md`, `docs/cli/scenario-api.md`

---

## ADR-010: Factory Pattern for Device Creation

**Status**: Adopted

**Context**: Creating devices requires complex configuration (product specs, firmware versions, zone counts, default colors). Direct instantiation is error-prone.

**Decision**: Provide factory functions and builder pattern:

**Simple factories** (`factories/factory.py`):
```python
create_color_light(serial, storage)
create_multizone_light(serial, zone_count, extended_multizone, storage)
create_tile_device(serial, tile_count, storage)
create_device(product_id, serial, zone_count, tile_count, storage)
```

**Builder pattern** (`factories/builder.py`):
```python
device = (
    DeviceBuilder()
    .with_serial("d073d5000001")
    .with_product(27)
    .with_color_support()
    .build()
)
```

**Consequences**:
- ✅ Encapsulates complex initialization logic
- ✅ Product defaults automatically applied
- ✅ Firmware version logic centralized
- ✅ Easy to test (no direct EmulatedLifxDevice construction)
- ⚠️ Must update factories when adding device types

**Reference**: `docs/library/factories.md`

---

## ADR-011: Observer Pattern for State Changes

**Status**: Adopted

**Context**: Multiple components need to react to device state changes (persistence, activity logging, metrics). Direct coupling would violate Open/Closed Principle.

**Decision**: Implement observer pattern for device state changes:

```python
class ActivityObserver(Protocol):
    def on_packet_sent(self, event: PacketEvent): ...
    def on_packet_received(self, event: PacketEvent): ...
    def on_state_changed(self, device: EmulatedLifxDevice): ...
```

**Consequences**:
- ✅ Decoupled components
- ✅ Easy to add new observers (plugins, metrics, etc.)
- ✅ Type-safe with Protocol
- ⚠️ Must carefully manage observer lifecycle
- ⚠️ Performance impact with many observers

**Implementations**:
- `ActivityLogger` - Logs packet activity
- `NullObserver` - No-op for testing
- Custom observers can be added

**Reference**: `devices/observers.py`

---

## ADR-012: OpenAPI 3.1.0 Compliance for HTTP API

**Status**: Adopted

**Context**: The HTTP API needs to be discoverable, testable, and well-documented. Manual API documentation gets out of sync.

**Decision**: Use FastAPI with Pydantic for automatic OpenAPI 3.1.0 schema generation:
- Pydantic models for request/response validation
- Automatic schema generation
- Interactive Swagger UI at `/docs`
- ReDoc documentation at `/redoc`

**Consequences**:
- ✅ Self-documenting API
- ✅ Type-safe request/response handling
- ✅ Interactive testing via Swagger UI
- ✅ Schema always in sync with code
- ⚠️ Must use Pydantic models (no plain dicts)
- ⚠️ OpenAPI limitations for complex scenarios

**Endpoints**:
- `/openapi.json` - OpenAPI 3.1.0 schema
- `/docs` - Swagger UI
- `/redoc` - ReDoc

**Implementation**: `api/app.py`, `api/models.py`

**Reference**: `docs/cli/device-management-api.md`

---

## ADR-013: Capability-Based Packet Filtering

**Status**: Adopted

**Context**: LIFX Switch devices have relays and buttons but no lighting control. Need to correctly reject unsupported packet types.

**Decision**: Use capability flags to filter packets before processing:
- Devices set capability flags: `has_color`, `has_multizone`, `has_matrix`, `has_relays`, `has_buttons`
- Switch devices (`has_relays=True`, `has_buttons=True`) return `StateUnhandled` for Light/MultiZone/Tile packets
- Device.* packets are handled normally

**Consequences**:
- ✅ Accurate device behavior (switches don't handle light packets)
- ✅ Clear capability detection
- ✅ Easy to add new device types with different capabilities
- ⚠️ Must update filtering logic when adding capabilities

**Example** (`devices/device.py`):
```python
# Switches reject lighting packets
if not self.state.has_color and pkt_type in LIGHT_PACKET_TYPES:
    return StateUnhandled(unhandled_type=pkt_type)
```

**Reference**: `docs/guide/device-types.md`

---

## ADR-014: Lazy Initialization for Tile Framebuffers

**Status**: Adopted

**Context**: Matrix devices support 8 framebuffers (0-7), but most only use framebuffer 0. Pre-allocating all framebuffers wastes memory.

**Decision**: Implement lazy initialization with `get_framebuffer(fb_index, width, height)`:
- Framebuffer 0 stored in `tile_devices[i]["colors"]` (protocol-defined)
- Framebuffers 1-7 lazily initialized on first access
- Internal dataclass `TileFramebuffers` manages non-visible buffers

**Consequences**:
- ✅ Memory efficient (only allocate what's used)
- ✅ Supports advanced rendering workflows
- ✅ Backwards compatible (framebuffer 0 always available)
- ⚠️ More complex state management
- ⚠️ Must handle CopyFrameBuffer with lazy init

**Implementation**: `devices/states.py` - `MatrixState` class

**Reference**: `docs/guide/framebuffers.md`

---

## ADR-015: Atomic File Writes for Scenario Persistence

**Status**: Adopted

**Context**: Scenario files must be consistent even if the process crashes during write. Partial writes would corrupt the scenario configuration.

**Decision**: Use atomic file writes:
1. Write to temporary file
2. fsync() to flush to disk
3. Atomic rename to final path

**Consequences**:
- ✅ Crash-safe writes
- ✅ No partial/corrupted files
- ✅ POSIX guarantees on rename atomicity
- ⚠️ Requires temp file cleanup on errors
- ⚠️ Slightly slower than direct writes

**Implementation**: `scenarios/persistence.py` - `ScenarioPersistenceAsyncFile`

---

## Summary of Key Patterns

### Design Patterns Used
- **Repository Pattern** - Storage abstraction
- **Factory Pattern** - Device creation
- **Builder Pattern** - Flexible configuration
- **Observer Pattern** - State change notifications
- **Handler Registry** - Packet type routing
- **Dependency Injection** - Testable architecture
- **Protocol Interfaces** - Type-safe contracts

### Architectural Principles
- **Single Responsibility** - Each layer/class has one purpose
- **Dependency Inversion** - Depend on interfaces, not implementations
- **Open/Closed** - Open for extension, closed for modification
- **Separation of Concerns** - Network, domain, persistence are independent
- **DRY** - Auto-generation for protocol and products

### Performance Optimizations
- Async I/O with debouncing (persistence)
- Scenario caching (invalidation on config change)
- Lazy initialization (tile framebuffers)
- Pre-built product registry (no runtime parsing)

## Related Documentation

- [Architecture Overview](overview.md)
- [Code Navigation Guide](../development/code-navigation.md)
- [Library Reference](../library/index.md)
- [Best Practices](../guide/best-practices.md)
