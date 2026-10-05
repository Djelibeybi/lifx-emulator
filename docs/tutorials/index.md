# Tutorials Overview

Step-by-step tutorials to master the LIFX Emulator, organized from beginner to advanced.

## Learning Path

Follow these tutorials in order for the best learning experience:

1. **🟢 Beginner** - [First Device](01-first-device.md) - Your first emulated LIFX device (⏱️ 10-15 minutes)
2. **🟢 Beginner** - [Basic Usage](02-basic.md) - Multiple devices and basic operations (⏱️ 15-30 minutes)
3. **🟡 Intermediate** - [Integration Testing](03-integration.md) - Using the emulator in test suites (⏱️ 30-45 minutes)
4. **🔴 Advanced** - [Advanced Scenarios](04-advanced-scenarios.md) - Error injection and complex testing (⏱️ 45-60 minutes)
5. **🔴 Advanced** - [CI/CD Integration](05-cicd.md) - Automated testing pipelines (⏱️ 30-45 minutes)

## Tutorial Categories

### Getting Started

Learn the basics:

- Creating a single device
- Starting the server
- Using the context manager
- Basic server configuration

### Multiple Devices

Work with multiple devices:

- Creating different device types
- Managing device collections
- Testing multi-device scenarios

### Testing Integration

Integrate with test frameworks:

- pytest fixtures
- pytest-asyncio usage
- Module-scoped fixtures
- Test isolation strategies

### Error Scenarios

Test error handling:

- Packet dropping
- Response delays
- Malformed packets
- Invalid field values
- Partial responses

## Complete Example

Here's a complete example showing multiple features. The async fixtures assume pytest-asyncio's `asyncio_mode = "auto"` (see [Integration Testing](../guide/integration-testing.md)):

```python
import pytest

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


@pytest.fixture
def scenario_manager():
    """Configure error scenarios shared by the devices and the server."""
    manager = HierarchicalScenarioManager()

    # Delay StateColor (107) replies from one device by 100ms. Response
    # delays are keyed by the response packet type, not the request.
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(response_delays={107: 0.1})
    )
    return manager


@pytest.fixture
def lifx_devices(scenario_manager):
    """Create a diverse set of emulated devices."""
    return [
        create_color_light("d073d5000001", scenario_manager=scenario_manager),
        create_color_light("d073d5000002", scenario_manager=scenario_manager),
        create_multizone_light(
            "d073d8000001", zone_count=16, scenario_manager=scenario_manager
        ),
        create_multizone_light(
            "d073d8000002",
            zone_count=82,
            extended_multizone=True,
            scenario_manager=scenario_manager,
        ),
        create_tile_device(
            "d073d9000001", tile_count=5, scenario_manager=scenario_manager
        ),
    ]


@pytest.fixture
async def lifx_server(lifx_devices, scenario_manager):
    """Start emulator server with devices."""
    # The server assigns its scenario manager to every device it manages,
    # so pass it the same manager the scenarios were registered on.
    server = EmulatedLifxServer(
        lifx_devices,
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=scenario_manager,
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_discovery(lifx_server):
    """Test device discovery."""
    # Your test code here
    assert len(lifx_server.get_all_devices()) == 5


@pytest.mark.asyncio
async def test_color_control(lifx_server):
    """Test color control commands."""
    # Your test code here
    pass
```

## Next Steps

Browse the specific tutorial pages for detailed code samples and explanations. Each tutorial builds on the concepts from the previous one.
