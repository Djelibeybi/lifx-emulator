# Architecture Patterns and Design Guidelines

## Core Architectural Principles

### 1. Layered Architecture
The emulator uses a strict layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────┐
│   Network Layer (UDP Protocol)     │  EmulatedLifxServer
├─────────────────────────────────────┤
│   Domain Layer (Business Logic)    │  DeviceManager, ScenarioManager
├─────────────────────────────────────┤
│   Repository Layer (Abstraction)   │  IDeviceRepository, IStorageBackend
├─────────────────────────────────────┤
│   Persistence Layer (File I/O)     │  DevicePersistenceAsyncFile
└─────────────────────────────────────┘
```

**Key Rules:**
- Network layer handles ONLY UDP transport
- Domain layer contains ALL business logic
- Repository layer provides storage abstraction
- Persistence layer handles actual file I/O

### 2. Dependency Injection
All major components use constructor injection for dependencies:

```python
# Server requires DeviceManager (injected)
server = EmulatedLifxServer(
    devices,
    device_manager,  # REQUIRED - injected dependency
    "127.0.0.1",
    56700
)

# DeviceManager requires IDeviceRepository (injected)
device_manager = DeviceManager(device_repository)

# Device can receive optional dependencies
device = EmulatedLifxDevice(
    device_state,
    storage=storage_backend,           # Optional
    handler_registry=custom_registry,  # Optional
    scenario_manager=scenario_mgr,     # Optional
)
```

**Benefits:**
- Easy testing with mock dependencies
- Loose coupling between layers
- Clear dependency graph
- Alternative implementations possible

### 3. Protocol Interfaces
The project uses Protocol classes (PEP 544) for structural subtyping:

```python
from typing import Protocol

class IDeviceRepository(Protocol):
    def add(self, device: EmulatedLifxDevice) -> None: ...
    def remove(self, serial: str) -> None: ...
    def get(self, serial: str) -> EmulatedLifxDevice | None: ...

class IDeviceStorageBackend(Protocol):
    async def save_device_state(self, state: DeviceState) -> None: ...
    def load_device_state(self, serial: str) -> dict[str, Any] | None: ...
```

**Benefits:**
- Duck typing with type safety
- No inheritance required
- Easy to create test doubles
- Clear contracts between layers

### 4. Handler Pattern (Strategy)
Packet handling uses the strategy pattern via handler registry:

```python
# Handlers are registered by packet type
registry = HandlerRegistry()
registry.register(101, handle_light_get_color)
registry.register(102, handle_light_set_color)

# Device dispatches to appropriate handler
handler = registry.get_handler(pkt_type)
responses = handler(device, packet, req_header, res_required)
```

**Benefits:**
- Separation of concerns (one handler per packet type)
- Easy to add new packet types
- Testable in isolation
- Custom registries for testing

## Key Design Patterns

### Factory Pattern
Device creation uses factory functions with product defaults:

```python
# Simple factories
device = create_color_light(serial="d073d5000001")
device = create_multizone_light(zone_count=16, extended_multizone=True)

# Universal factory with product ID
device = create_device(product_id=27)  # LIFX A19
device = create_device(product_id=32, zone_count=24)  # LIFX Z with 24 zones
```

### Repository Pattern
Device storage abstraction using repository pattern:

```python
class DeviceRepository(IDeviceRepository):
    def __init__(self):
        self._devices: dict[str, EmulatedLifxDevice] = {}

    def add(self, device: EmulatedLifxDevice) -> None:
        self._devices[device.state.serial] = device

    def get(self, serial: str) -> EmulatedLifxDevice | None:
        return self._devices.get(serial)
```

### Observer Pattern
Device state changes can be observed for persistence:

```python
# Device automatically saves state changes via storage backend
device.state.label = "Living Room"  # Triggers async save

# Storage backend uses debouncing to batch writes
storage = DevicePersistenceAsyncFile()  # 100ms debounce by default
```

### Hierarchical Configuration (Chain of Responsibility)
Scenarios use hierarchical resolution with precedence:

```python
# Scenario precedence: device-specific > type > location > group > global
scenario_mgr = HierarchicalScenarioManager()
scenario_mgr.set_global_scenario(ScenarioConfig(drop_packets={101: 0.5}))
scenario_mgr.set_device_scenario("d073d5000001", ScenarioConfig(drop_packets={101: 1.0}))

# Merged scenario for device (device-specific overrides global)
merged = scenario_mgr.get_scenario_for_device(
    serial="d073d5000001",
    device_type="color"
)
```

## Performance Optimizations

### 1. Pre-allocated Response Headers
```python
# Device pre-allocates response header template (10-15% performance gain)
self._response_header_template = LifxHeader(
    source=0,
    target=self.state.get_target_bytes(),
    sequence=0,
    tagged=False,
    pkt_type=0,
    size=0,
)
```

### 2. Scenario Caching
```python
# Device caches merged scenario to avoid repeated lookups
self._cached_scenario: ScenarioConfig | None = None

def _get_scenario(self) -> ScenarioConfig:
    if self._cached_scenario is None:
        self._cached_scenario = self.scenario_manager.get_scenario_for_device(...)
    return self._cached_scenario
```

### 3. Async Storage with Debouncing
```python
# Storage backend batches writes to reduce I/O
storage = DevicePersistenceAsyncFile(debounce_interval=0.1)  # 100ms
device.state.label = "Room 1"  # Queued
device.state.power = 65535       # Queued
# Both changes written together after 100ms
```

### 4. List Comprehensions
```python
# Use list comprehensions for performance
self.state.zone_colors = [
    LightHsbk(
        hue=int((i / self.state.zone_count) * 65535),
        saturation=65535,
        brightness=32768,
        kelvin=3500,
    )
    for i in range(self.state.zone_count)
]
```

## Anti-Patterns to Avoid

### ❌ Direct File I/O in Domain Layer
```python
# BAD - domain logic should not do file I/O
class DeviceManager:
    def add_device(self, device):
        with open("devices.json", "w") as f:  # ❌ Wrong layer
            json.dump(devices, f)
```

### ✅ Use Repository Pattern
```python
# GOOD - delegate to repository/storage layer
class DeviceManager:
    def add_device(self, device):
        self.repository.add(device)  # ✅ Correct
```

### ❌ Business Logic in Network Layer
```python
# BAD - server should not contain business logic
class EmulatedLifxServer:
    def handle_packet(self, data, addr):
        # Complex device lookup logic here  # ❌ Wrong layer
        # Scenario application here          # ❌ Wrong layer
```

### ✅ Delegate to Domain Layer
```python
# GOOD - server delegates to domain layer
class EmulatedLifxServer:
    def handle_packet(self, data, addr):
        targets = self.device_manager.get_targets(header)  # ✅ Correct
```

### ❌ Circular Dependencies
```python
# BAD - circular import
from lifx_emulator.devices.device import EmulatedLifxDevice  # ❌ Circular
```

### ✅ Use TYPE_CHECKING Guard
```python
# GOOD - import only for type checking
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile  # ✅
```

## Testing Patterns

### Unit Tests
- Test individual components in isolation
- Use mock dependencies via dependency injection
- Test edge cases and error conditions
- Aim for 95% coverage

### Integration Tests
- Test components working together
- Use real (not mock) dependencies
- Test actual UDP protocol interactions
- Validate end-to-end scenarios

### Example Test Structure
```python
import pytest
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light

@pytest.mark.asyncio
async def test_light_set_color():
    """Test setting color on a device."""
    state = DeviceState(serial="d073d5000001", ...)
    device = EmulatedLifxDevice(state)

    header = LifxHeader(...)
    packet = Light.SetColor(...)

    responses = device.process_packet(header, packet)

    assert len(responses) > 0
    assert device.state.color.hue == packet.color.hue
```

## Documentation Standards

### Module Documentation
```python
"""Device state and emulated device implementation.

This module contains the core EmulatedLifxDevice class and related state
management components.
"""
```

### Class Documentation
```python
class EmulatedLifxDevice:
    """Emulated LIFX device with configurable scenarios and state management.

    Represents a single virtual LIFX device that responds to LIFX LAN protocol
    packets. Supports all device types (color, multizone, matrix, etc.) through
    capability flags in DeviceState.
    """
```

### Function Documentation (when needed)
```python
def process_packet(
    self, req_header: LifxHeader, packet: Any
) -> list[tuple[LifxHeader, Any]]:
    """Process incoming packet and return list of response packets.

    Args:
        req_header: Request packet header
        packet: Unpacked packet payload

    Returns:
        List of (header, packet) tuples to send back to client
    """
```
