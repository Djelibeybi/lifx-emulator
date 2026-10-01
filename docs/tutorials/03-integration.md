# Integration Testing Examples

This page demonstrates how to integrate the LIFX Emulator into your test suites using pytest, pytest-asyncio, and other testing frameworks.

The fixtures use `@pytest_asyncio.fixture`, which works in both pytest-asyncio's default `strict` mode and in `auto` mode. Every server is created with its own `DeviceManager(DeviceRepository())`, which `EmulatedLifxServer` requires as its second argument, and binds to port `0` so the operating system picks a free port. The server's `port` attribute stays `0`; the port actually bound is `server.ipv4_endpoint[1]` once the server has started.

## Basic pytest Fixture

The simplest pytest integration pattern:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def lifx_server():
    """Basic emulator fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_server_running(lifx_server):
    """Test that the server is running."""
    devices = lifx_server.get_all_devices()
    assert len(devices) == 1
    assert devices[0].state.serial == "d073d5000001"
```

## Function-Scoped Fixtures

Create a fresh emulator for each test (default scope):

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(scope="function")
async def lifx_emulator():
    """Function-scoped fixture - new emulator per test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_first(lifx_emulator):
    """First test gets a fresh emulator."""
    assert len(lifx_emulator.get_all_devices()) == 1


@pytest.mark.asyncio
async def test_second(lifx_emulator):
    """Second test gets a different fresh emulator."""
    assert len(lifx_emulator.get_all_devices()) == 1
```

## Module-Scoped Fixtures

Share one emulator across all tests in a module. A module-scoped async fixture must run in a module-scoped event loop, so set `loop_scope="module"` on the fixture and on every test that uses it:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def shared_emulator():
    """Module-scoped fixture - shared across all tests in module."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
    ]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio(loop_scope="module")
async def test_first_device(shared_emulator):
    """Test using shared emulator."""
    assert shared_emulator.get_device("d073d5000001") is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_second_device(shared_emulator):
    """Another test using the same emulator instance."""
    assert shared_emulator.get_device("d073d5000002") is not None
```

## Fixture with Custom Configuration

Create parameterised fixtures for different scenarios:

```python
import pytest
import pytest_asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def basic_device():
    """Single colour light fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest_asyncio.fixture
async def multizone_device():
    """Multizone strip fixture."""
    device = create_multizone_light("d073d8000001", zone_count=16)
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_color_light(basic_device):
    """Test with colour light."""
    assert basic_device.get_all_devices()[0].state.has_color


@pytest.mark.asyncio
async def test_multizone_light(multizone_device):
    """Test with multizone light."""
    device = multizone_device.get_all_devices()[0]
    assert device.state.has_multizone
    assert len(device.state.zone_colors) == 16
```

## Parametrized Tests

Test against multiple device types:

```python
import pytest
import pytest_asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(
    params=[
        ("color", create_color_light, "d073d5000001"),
        (
            "multizone",
            lambda s: create_multizone_light(s, zone_count=16),
            "d073d8000001",
        ),
        ("tile", lambda s: create_tile_device(s, tile_count=5), "d073d9000001"),
    ]
)
async def any_device(request):
    """Parametrised fixture for different device types."""
    device_type, factory, serial = request.param
    device = factory(serial)
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server, device_type


@pytest.mark.asyncio
async def test_all_devices_respond(any_device):
    """Test runs 3 times, once for each device type."""
    server, device_type = any_device
    print(f"Testing {device_type} device")
    assert len(server.get_all_devices()) == 1
```

## Port Management

Avoid port conflicts when running tests in parallel by binding to port `0`. The operating system assigns a free port when the server starts, so there is no window in which another process can take it:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def emulator_on_free_port():
    """Use dynamically allocated port."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        # server.port stays 0; the bound port is in ipv4_endpoint
        host, port = server.ipv4_endpoint
        yield server, port


@pytest.mark.asyncio
async def test_with_dynamic_port(emulator_on_free_port):
    """Test using dynamic port allocation."""
    server, port = emulator_on_free_port
    print(f"Emulator running on port {port}")
    assert port != 0
    assert server.get_all_devices()[0].state.port == port
```

## Test Isolation with Fresh Devices

Ensure each test has clean state:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def fresh_device():
    """Create a fresh device for each test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_modify_color(fresh_device):
    """Test that modifies device state."""
    device = fresh_device.get_all_devices()[0]

    # Modify state (hue 43690 is blue)
    device.state.color = LightHsbk(
        hue=43690, saturation=65535, brightness=32768, kelvin=3500
    )

    # Verify modification
    assert device.state.color.hue == 43690


@pytest.mark.asyncio
async def test_default_color(fresh_device):
    """Test gets fresh device with default state."""
    device = fresh_device.get_all_devices()[0]

    # Fresh device has the factory default colour, not the previous test's blue
    assert device.state.color == create_color_light("d073d5000001").state.color
```

## Cleanup and Resource Management

Ensure proper cleanup even when tests fail:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def emulator_with_cleanup():
    """Fixture with explicit cleanup."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    # Start server
    async with server:
        try:
            yield server
        finally:
            # Cleanup always runs, even if test fails
            print("Cleaning up emulator resources")
            # Server stops automatically when exiting context manager


@pytest.mark.asyncio
async def test_that_might_fail(emulator_with_cleanup):
    """Test with guaranteed cleanup."""
    # Even if this test raises an exception, cleanup runs
    assert len(emulator_with_cleanup.get_all_devices()) == 1
```

## Testing with Real LIFX Clients

Integration test with an actual LIFX client library. `lifxlan` is synchronous, so run its calls in a worker thread with `asyncio.to_thread()`; calling it directly would block the event loop and the emulator could never reply. The test addresses the light directly by MAC address and IP instead of relying on broadcast discovery, which doesn't reach a server bound to `127.0.0.1`:

```python
import asyncio

import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

# This example uses lifxlan library: pip install lifxlan
from lifxlan import Light


@pytest_asyncio.fixture
async def emulator_for_client():
    """Emulator configured for client testing."""
    device = create_color_light("d073d5000001")
    device.state.label = "Test Light"
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


def make_light(server):
    """Create a lifxlan Light pointing at the emulated device."""
    host, port = server.ipv4_endpoint
    return Light("d0:73:d5:00:00:01", host, port=port)


@pytest.mark.asyncio
async def test_client_get_label(emulator_for_client):
    """Test client can talk to the emulated device."""
    light = make_light(emulator_for_client)

    label = await asyncio.to_thread(light.get_label)

    assert label == "Test Light"


@pytest.mark.asyncio
async def test_client_set_color(emulator_for_client):
    """Test client can control emulated device."""
    light = make_light(emulator_for_client)

    # Change colour to red; rapid=False waits for the acknowledgement
    await asyncio.to_thread(light.set_color, [65535, 65535, 32768, 3500], 0, False)

    # Verify state change in emulator
    emu_device = emulator_for_client.get_device("d073d5000001")
    assert emu_device.state.color.hue == 65535  # Red
```

## Parallel Test Execution

With every fixture binding to port `0`, tests are already safe to run in parallel with pytest-xdist: each worker gets its own free port and no per-worker port arithmetic is needed:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def isolated_emulator():
    """Isolated emulator for parallel testing."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_parallel_safe(isolated_emulator):
    """Test that can run in parallel with others."""
    assert len(isolated_emulator.get_all_devices()) == 1
```

Run with: `pytest -n auto` (requires pytest-xdist)

## conftest.py Organization

Organise fixtures in conftest.py for reuse. pytest-asyncio manages the event loop itself, so don't define an `event_loop` fixture:

```python
# conftest.py
import pytest_asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def single_color_light():
    """Reusable single colour light fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest_asyncio.fixture
async def multiple_devices():
    """Reusable multi-device fixture."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_multizone_light("d073d8000001", zone_count=16),
    ]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server
```

## Testing Error Scenarios

Test your client's error handling. Scenarios are `ScenarioConfig` objects registered on a `HierarchicalScenarioManager`; pass the same manager to the factory **and** to the server as `scenario_manager=`, because the server assigns its own scenario manager to every device it manages, so a scenario registered on any other manager is ignored. `drop_packets` matches the incoming request type, while `response_delays` matches the outgoing response type:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


@pytest_asyncio.fixture
async def unreliable_device():
    """Device configured to drop and delay packets."""
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={101: 1.0},  # Drop every GetColor request
            response_delays={22: 1.0},  # Delay StatePower replies by 1 second
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        0,
        scenario_manager=manager,
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_client_retry_logic(unreliable_device):
    """Test that client handles dropped packets."""
    # Your client should implement retry logic
    # This test verifies it works correctly
    pass


@pytest.mark.asyncio
async def test_client_timeout_handling(unreliable_device):
    """Test that client handles slow responses."""
    # Your client should time out appropriately
    # This test verifies timeout behaviour
    pass
```

To change scenarios while the server is running, update `server.scenario_manager` and then call `server.invalidate_all_scenario_caches()`, because each device caches its merged scenario. See [Advanced Examples](04-advanced-scenarios.md) for the full list of scenario fields.

## Mock vs Emulator Decision

When to use emulator vs mocks:

```python
from unittest.mock import Mock

import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


# Use emulator for integration tests
@pytest_asyncio.fixture
async def integration_emulator():
    """Full emulator for integration testing."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_integration_with_emulator(integration_emulator):
    """Integration test using real emulated device."""
    # Test full protocol interaction
    assert len(integration_emulator.get_all_devices()) == 1


# Use mocks for unit tests
def test_unit_with_mock():
    """Unit test using mock."""
    # Mock is faster and more isolated for unit tests
    mock_device = Mock()
    mock_device.state.serial = "d073d5000001"
    mock_device.state.has_color = True

    # Test your code that uses the device
    assert mock_device.state.has_color
```

**When to use Emulator:**
- Integration tests with real protocol
- Testing client library implementations
- End-to-end workflow testing
- Protocol compliance testing

**When to use Mocks:**
- Unit tests for business logic
- Fast test suites
- Testing error conditions that are hard to trigger
- Isolating code under test

## Testing with Docker

Run emulator in Docker for CI/CD:

```python
# test_docker.py
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def dockerized_emulator():
    """
    In CI/CD, you can run emulator in a separate container.
    This fixture connects to it.
    """
    # In actual usage, emulator runs in separate container
    # This is a simplified example for local testing
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "0.0.0.0", 56700
    )

    async with server:
        yield server


@pytest.mark.asyncio(loop_scope="session")
async def test_with_docker(dockerized_emulator):
    """Test against dockerized emulator."""
    # Connect to emulator (in real case, from different container)
    assert len(dockerized_emulator.get_all_devices()) == 1
```

**Dockerfile example:**
```dockerfile
FROM python:3.13-slim

RUN pip install lifx-emulator

EXPOSE 56700/udp

# Bind to all interfaces so traffic from outside the container reaches it
CMD ["lifx-emulator", "--bind", "0.0.0.0", "--color", "3", "--multizone", "2"]
```

## Starting and Stopping Manually

If a fixture can't use `async with`, start and stop the server explicitly. `start()` returns once the server is bound and listening, so no extra sleep is needed:

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def background_emulator():
    """Emulator started and stopped explicitly."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_with_background_server(background_emulator):
    """Test with server running in background."""
    assert len(background_emulator.get_all_devices()) == 1
```

## Complete Test Suite Example

A comprehensive test module:

```python
# test_lifx_client.py
import pytest
import pytest_asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def test_devices():
    """Module-level fixture with multiple devices."""
    devices = [
        create_color_light("d073d5000001"),
        create_multizone_light("d073d8000001", zone_count=16),
    ]

    devices[0].state.label = "Color Light"
    devices[1].state.label = "Strip Light"

    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio(loop_scope="module")
async def test_device_count(test_devices):
    """Verify device count."""
    assert len(test_devices.get_all_devices()) == 2


@pytest.mark.asyncio(loop_scope="module")
async def test_color_light_capabilities(test_devices):
    """Verify colour light capabilities."""
    device = test_devices.get_device("d073d5000001")
    assert device.state.has_color
    assert not device.state.has_multizone


@pytest.mark.asyncio(loop_scope="module")
async def test_multizone_capabilities(test_devices):
    """Verify multizone capabilities."""
    device = test_devices.get_device("d073d8000001")
    assert device.state.has_multizone
    assert len(device.state.zone_colors) == 16


@pytest.mark.asyncio(loop_scope="module")
async def test_state_modification(test_devices):
    """Test state can be modified."""
    device = test_devices.get_device("d073d5000001")

    # Modify colour
    new_color = LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500)
    device.state.color = new_color

    # Verify
    assert device.state.color.hue == 21845
```

## Next Steps

- **[Basic Examples](02-basic.md)** - Review basic usage patterns
- **[Advanced Examples](04-advanced-scenarios.md)** - Complex scenarios and error injection
- **[Best Practices Guide](../guide/best-practices.md)** - Testing best practices
- **[pytest Documentation](https://docs.pytest.org/)** - Official pytest docs

## See Also

- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/) - Async test support
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/) - Parallel test execution
- [API Reference: Device](../library/device.md) - Device API documentation
- [API Reference: Server](../library/server.md) - Server API documentation
