# Integration Testing Examples

This page demonstrates how to integrate the LIFX Emulator into your test suites using pytest, pytest-asyncio, and other testing frameworks.

## Basic pytest Fixture

The simplest pytest integration pattern:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def lifx_server():
    """Basic emulator fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_server_running(lifx_server):
    """Test that the server is running."""
    assert len(lifx_server.devices) == 1
    assert lifx_server.devices[0].state.serial == "d073d5000001"
```

## Function-Scoped Fixtures

Create a fresh emulator for each test (default scope):

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture(scope="function")
async def lifx_emulator():
    """Function-scoped fixture - new emulator per test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_first(lifx_emulator):
    """First test gets a fresh emulator."""
    assert len(lifx_emulator.devices) == 1

@pytest.mark.asyncio
async def test_second(lifx_emulator):
    """Second test gets a different fresh emulator."""
    assert len(lifx_emulator.devices) == 1
```

## Module-Scoped Fixtures

Share one emulator across all tests in a module:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture(scope="module")
async def shared_emulator():
    """Module-scoped fixture - shared across all tests in module."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
    ]
    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_first_device(shared_emulator):
    """Test using shared emulator."""
    assert shared_emulator.devices[0].state.serial == "d073d5000001"

@pytest.mark.asyncio
async def test_second_device(shared_emulator):
    """Another test using the same emulator instance."""
    assert shared_emulator.devices[1].state.serial == "d073d5000002"
```

## Fixture with Custom Configuration

Create parameterized fixtures for different scenarios:

```python
import pytest
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)

@pytest.fixture
async def basic_device():
    """Single color light fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.fixture
async def multizone_device():
    """Multizone strip fixture."""
    device = create_multizone_light("d073d8000001", zone_count=16)
    server = EmulatedLifxServer([device], "127.0.0.1", 56701)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_color_light(basic_device):
    """Test with color light."""
    assert basic_device.devices[0].state.has_color

@pytest.mark.asyncio
async def test_multizone_light(multizone_device):
    """Test with multizone light."""
    assert multizone_device.devices[0].state.has_multizone
    assert len(multizone_device.devices[0].state.zone_colors) == 16
```

## Parametrized Tests

Test against multiple device types:

```python
import pytest
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)

@pytest.fixture(params=[
    ("color", create_color_light, "d073d5000001"),
    ("multizone", lambda s: create_multizone_light(s, zone_count=16), "d073d8000001"),
    ("tile", lambda s: create_tile_device(s, tile_count=5), "d073d9000001"),
])
async def any_device(request):
    """Parametrized fixture for different device types."""
    device_type, factory, serial = request.param
    device = factory(serial)
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server, device_type

@pytest.mark.asyncio
async def test_all_devices_respond(any_device):
    """Test runs 3 times, once for each device type."""
    server, device_type = any_device
    print(f"Testing {device_type} device")
    assert len(server.devices) == 1
```

## Port Management

Avoid port conflicts when running tests in parallel:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

def get_free_port():
    """Find an available port."""
    import socket
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@pytest.fixture
async def emulator_on_free_port():
    """Use dynamically allocated port."""
    device = create_color_light("d073d5000001")
    port = get_free_port()
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server, port

@pytest.mark.asyncio
async def test_with_dynamic_port(emulator_on_free_port):
    """Test using dynamic port allocation."""
    server, port = emulator_on_free_port
    print(f"Emulator running on port {port}")
    assert len(server.devices) == 1
```

## Test Isolation with Fresh Devices

Ensure each test has clean state:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.protocol.protocol_types import LightHsbk

@pytest.fixture
async def fresh_device():
    """Create a fresh device for each test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_modify_color(fresh_device):
    """Test that modifies device state."""
    device = fresh_device.devices[0]

    # Modify state
    device.state.color = LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500)

    # Verify modification
    assert device.state.color.hue == 21845

@pytest.mark.asyncio
async def test_default_color(fresh_device):
    """Test gets fresh device with default state."""
    device = fresh_device.devices[0]

    # Fresh device should have default color (not modified by previous test)
    assert device.state.color.hue == 0  # Default
```

## Cleanup and Resource Management

Ensure proper cleanup even when tests fail:

```python
import pytest
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def emulator_with_cleanup():
    """Fixture with explicit cleanup."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

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
    assert len(emulator_with_cleanup.devices) == 1
```

## Testing with Real LIFX Clients

Integration test with an actual LIFX client library:

```python
import pytest
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

# This example uses lifxlan library: pip install lifxlan
from lifxlan import LifxLAN

@pytest.fixture
async def emulator_for_client():
    """Emulator configured for client testing."""
    device = create_color_light("d073d5000001")
    device.state.label = "Test Light"
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        # Give server time to start
        await asyncio.sleep(0.1)
        yield server

@pytest.mark.asyncio
async def test_client_discovery(emulator_for_client):
    """Test client can discover emulated device."""
    # Run client code in separate thread/task
    lifx = LifxLAN()

    # Small timeout for local network
    devices = lifx.get_devices()

    assert len(devices) == 1
    assert devices[0].get_label() == "Test Light"

@pytest.mark.asyncio
async def test_client_set_color(emulator_for_client):
    """Test client can control emulated device."""
    lifx = LifxLAN()
    devices = lifx.get_devices()
    device = devices[0]

    # Change color to red
    device.set_color([65535, 65535, 32768, 3500])

    # Verify state change in emulator
    emu_device = emulator_for_client.devices[0]
    assert emu_device.state.color.hue == 65535  # Red
```

## Parallel Test Execution

Configure for pytest-xdist parallel execution:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def isolated_emulator(worker_id):
    """Isolated emulator for parallel testing."""
    # Use worker_id to get unique port per worker
    if worker_id == 'master':
        port = 56700
    else:
        # Extract worker number and add to base port
        worker_num = int(worker_id.replace('gw', ''))
        port = 56700 + worker_num

    device = create_color_light(f"d073d500000{port % 100}")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_parallel_safe(isolated_emulator):
    """Test that can run in parallel with others."""
    assert len(isolated_emulator.devices) == 1
```

Run with: `pytest -n auto` (requires pytest-xdist)

## conftest.py Organization

Organize fixtures in conftest.py for reuse:

```python
# conftest.py
import pytest
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def single_color_light():
    """Reusable single color light fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.fixture
async def multiple_devices():
    """Reusable multi-device fixture."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_multizone_light("d073d8000001", zone_count=16),
    ]
    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        yield server
```

## Testing Error Scenarios

Test your client's error handling:

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def unreliable_device():
    """Device configured to drop packets."""
    device = create_color_light("d073d5000001")
    device.scenarios = {
        'drop_packets': [101],  # Drop GetColor
        'response_delays': {102: 1.0},  # Delay SetColor
    }
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

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
    # Your client should timeout appropriately
    # This test verifies timeout behavior
    pass
```

## Mock vs Emulator Decision

When to use emulator vs mocks:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from lifx_emulator import EmulatedLifxServer, create_color_light

# Use emulator for integration tests
@pytest.fixture
async def integration_emulator():
    """Full emulator for integration testing."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_integration_with_emulator(integration_emulator):
    """Integration test using real emulated device."""
    # Test full protocol interaction
    assert len(integration_emulator.devices) == 1

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
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture(scope="session")
async def dockerized_emulator():
    """
    In CI/CD, you can run emulator in a separate container.
    This fixture connects to it.
    """
    # In actual usage, emulator runs in separate container
    # This is a simplified example for local testing
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "0.0.0.0", 56700)

    async with server:
        await asyncio.sleep(0.1)  # Allow server to start
        yield server

@pytest.mark.asyncio
async def test_with_docker(dockerized_emulator):
    """Test against dockerized emulator."""
    # Connect to emulator (in real case, from different container)
    assert len(dockerized_emulator.devices) == 1
```

**Dockerfile example:**
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

EXPOSE 56700/udp

CMD ["lifx-emulator", "--color", "3", "--multizone", "2"]
```

## Background Server Pattern

Run emulator as background task during tests:

```python
import pytest
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def background_emulator():
    """Emulator running as background task."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    # Start server manually
    await server.start()

    # Start server task in background
    task = asyncio.create_task(server.run())

    try:
        # Wait for server to be ready
        await asyncio.sleep(0.1)
        yield server
    finally:
        # Stop server
        await server.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_with_background_server(background_emulator):
    """Test with server running in background."""
    assert len(background_emulator.devices) == 1
```

## Complete Test Suite Example

A comprehensive test module:

```python
# test_lifx_client.py
import pytest
import asyncio
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.protocol.protocol_types import LightHsbk

@pytest.fixture(scope="module")
async def test_devices():
    """Module-level fixture with multiple devices."""
    devices = [
        create_color_light("d073d5000001"),
        create_multizone_light("d073d8000001", zone_count=16),
    ]

    devices[0].state.label = "Color Light"
    devices[1].state.label = "Strip Light"

    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        await asyncio.sleep(0.1)
        yield server

@pytest.mark.asyncio
async def test_device_count(test_devices):
    """Verify device count."""
    assert len(test_devices.devices) == 2

@pytest.mark.asyncio
async def test_color_light_capabilities(test_devices):
    """Verify color light capabilities."""
    device = test_devices.devices[0]
    assert device.state.has_color
    assert not device.state.has_multizone

@pytest.mark.asyncio
async def test_multizone_capabilities(test_devices):
    """Verify multizone capabilities."""
    device = test_devices.devices[1]
    assert device.state.has_multizone
    assert len(device.state.zone_colors) == 16

@pytest.mark.asyncio
async def test_state_modification(test_devices):
    """Test state can be modified."""
    device = test_devices.devices[0]

    # Modify color
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
- [API Reference: Device](../api/device.md) - Device API documentation
- [API Reference: Server](../api/server.md) - Server API documentation
