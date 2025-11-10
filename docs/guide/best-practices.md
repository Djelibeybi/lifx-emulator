# Best Practices

This guide covers best practices for using the LIFX Emulator effectively in your development and testing workflows.

## When to Use the Emulator

### ✅ Use the Emulator When:

**1. Developing LIFX Client Libraries**
- Testing protocol implementation
- Verifying packet handling
- Testing discovery mechanisms
- Validating state management

**2. Integration Testing**
- Testing application logic with LIFX devices
- Verifying end-to-end workflows
- Testing error handling
- CI/CD pipeline integration

**3. Protocol Exploration**
- Learning the LIFX LAN protocol
- Experimenting with different device types
- Understanding packet structures
- Testing edge cases

**4. Performance Testing**
- Load testing with many devices
- Concurrent request handling
- Network latency simulation
- Resource usage profiling

### ❌ Don't Use the Emulator When:

**1. Unit Testing Business Logic**
- Use mocks for faster, isolated tests
- Emulator adds unnecessary overhead
- Business logic should not depend on protocol details

```python
# Good: Unit test with mock
from unittest.mock import Mock

def test_color_converter():
    mock_device = Mock()
    mock_device.get_color.return_value = (21845, 65535, 32768, 3500)

    # Test your color conversion logic
    rgb = convert_hsbk_to_rgb(mock_device.get_color())
    assert rgb == (0, 255, 128)

# Bad: Unit test with emulator (too slow)
async def test_color_converter_slow():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:
        # Just testing conversion logic doesn't need a full emulator
        ...
```

**2. Testing Third-Party Hardware**
- Emulator can't reproduce hardware-specific bugs
- Real devices needed for hardware validation
- Firmware behavior may differ

**3. Testing WiFi/Network Stack**
- Emulator doesn't simulate WiFi issues
- Network stack testing needs real network conditions
- Use network simulation tools instead

## Decision Tree: Mock vs Emulator vs Real Device

```
Are you testing protocol implementation?
├─ Yes → Use Emulator
└─ No
    ├─ Is this a unit test of business logic?
    │   └─ Yes → Use Mock
    └─ No
        ├─ Do you need to test hardware-specific behavior?
        │   └─ Yes → Use Real Device
        └─ No
            ├─ Is this an integration/E2E test?
            │   └─ Yes → Use Emulator
            └─ No → Use Mock
```

## Serial Number Strategies

### Consistent Naming Conventions

Use meaningful serial number patterns for easier debugging:

```python
# Good: Meaningful patterns
DEVICES = {
    'living_room': "d073d5001001",  # 1001 = living room
    'bedroom':     "d073d5001002",  # 1002 = bedroom
    'kitchen':     "d073d5001003",  # 1003 = kitchen
}

# Also good: By device type
DEVICES = {
    'color_1':     "d073d5100001",  # 1xxxxx = color lights
    'color_2':     "d073d5100002",
    'strip_1':     "d073d5200001",  # 2xxxxx = multizone
    'tile_1':      "d073d5300001",  # 3xxxxx = tiles
}
```

### Avoid Conflicts

Ensure serial numbers are unique across your test suite:

```python
# Bad: Reusing serials in different tests
# test_colors.py
device = create_color_light("d073d5000001")

# test_power.py
device = create_color_light("d073d5000001")  # Same serial!

# Good: Unique serials
# test_colors.py
device = create_color_light("d073d5010001")  # 01xxxx = color tests

# test_power.py
device = create_color_light("d073d5020001")  # 02xxxx = power tests
```

### Use Fixtures for Serial Generation

```python
import pytest

@pytest.fixture
def unique_serial():
    """Generate unique serial numbers."""
    counter = 0
    def _get_serial(prefix="d073d5"):
        nonlocal counter
        counter += 1
        return f"{prefix}{counter:06d}"
    return _get_serial

@pytest.mark.asyncio
async def test_with_unique_serial(unique_serial):
    device1 = create_color_light(unique_serial())  # d073d5000001
    device2 = create_color_light(unique_serial())  # d073d5000002
    # Guaranteed unique
```

## Port Management

### Dynamic Port Allocation

Always use dynamic ports to avoid conflicts:

```python
import socket

def get_free_port():
    """Get an available port from the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

@pytest.fixture
async def emulator():
    """Emulator with dynamic port."""
    port = get_free_port()
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server, port
```

### Port Ranges for Parallel Tests

When using pytest-xdist:

```python
@pytest.fixture
async def emulator(worker_id):
    """Port allocation for parallel workers."""
    if worker_id == 'master':
        port = 56700
    else:
        # gw0 -> 56701, gw1 -> 56702, etc.
        worker_num = int(worker_id.replace('gw', ''))
        port = 56700 + worker_num + 1

    device = create_color_light(f"d073d500{worker_num:04d}")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server
```

### Environment Variable Override

```python
import os

@pytest.fixture
async def emulator():
    """Allow port override via environment."""
    port = int(os.getenv('LIFX_EMULATOR_PORT', get_free_port()))

    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server
```

## Async Context Manager Patterns

### Always Use Context Managers

```python
# Good: Context manager ensures cleanup
async with server:
    # Server automatically starts
    await do_tests()
# Server automatically stops

# Bad: Manual start/stop
await server.start()
try:
    await do_tests()
finally:
    await server.stop()  # Easy to forget!
```

### Nested Context Managers

```python
# Multiple servers
async with server1:
    async with server2:
        # Both running
        await test_multi_server()
# Both stopped

# Or use asynccontextmanager for custom fixtures
from contextlib import asynccontextmanager

@asynccontextmanager
async def multi_server_setup():
    server1 = EmulatedLifxServer([device1], "127.0.0.1", 56700)
    server2 = EmulatedLifxServer([device2], "127.0.0.1", 56701)

    async with server1, server2:
        yield server1, server2
```

### Timeout Protection

```python
import asyncio

@pytest.mark.asyncio
@pytest.mark.timeout(30)  # Fail if test takes >30s
async def test_with_timeout():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        # Test times out if it hangs
        await asyncio.wait_for(run_test(), timeout=25)
```

## Resource Cleanup

### Explicit Cleanup in Fixtures

```python
@pytest.fixture
async def emulator():
    """Fixture with explicit cleanup."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        try:
            yield server
        finally:
            # Additional cleanup if needed
            print("Cleaning up...")
            # Context manager already stopped server
```

### Cleanup Even on Exceptions

```python
import pytest

@pytest.fixture
async def robust_emulator():
    """Emulator that cleans up even on test failure."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        try:
            yield server
        except Exception as e:
            # Log error but still clean up
            print(f"Test failed: {e}")
            raise  # Re-raise after logging
```

### Background Task Management

```python
import asyncio

@pytest.fixture
async def emulator_with_task():
    """Emulator with background task."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        # Start background task
        task = asyncio.create_task(monitor_server(server))

        try:
            yield server
        finally:
            # Cancel background task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
```

## Performance Considerations

### Fixture Scoping

Choose appropriate fixture scopes for performance:

```python
# Fastest: Session scope (one emulator for all tests)
@pytest.fixture(scope="session")
async def shared_emulator():
    """Shared across entire test session."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:
        yield server
    # Pros: Very fast, minimal overhead
    # Cons: Tests may affect each other

# Balanced: Module scope (one per test file)
@pytest.fixture(scope="module")
async def module_emulator():
    """Shared across one test file."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:
        yield server
    # Pros: Good isolation, reasonable speed
    # Cons: Some test coupling within module

# Safest: Function scope (one per test)
@pytest.fixture(scope="function")
async def fresh_emulator():
    """Fresh emulator for each test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:
        yield server
    # Pros: Perfect isolation
    # Cons: Slowest (startup overhead per test)
```

### Parallel Test Execution

```bash
# Run tests in parallel with pytest-xdist
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 workers
```

```python
# Ensure tests are parallel-safe
@pytest.fixture
async def parallel_safe_emulator(worker_id):
    """Each worker gets unique port and serial."""
    if worker_id == 'master':
        port = 56700
        serial = "d073d5000001"
    else:
        worker_num = int(worker_id.replace('gw', ''))
        port = 56700 + worker_num + 1
        serial = f"d073d500{worker_num:04d}"

    device = create_color_light(serial)
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server
```

### Minimize Device Count

Create only the devices you need:

```python
# Bad: Creating unnecessary devices
devices = [create_color_light(f"d073d500{i:04d}") for i in range(100)]
server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
# Only testing with 1 device!

# Good: Create what you need
device = create_color_light("d073d5000001")
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
```

## Test Organization Patterns

### Group Related Tests

```python
# tests/test_colors.py
class TestColorOperations:
    """Group color-related tests."""

    @pytest.fixture
    async def color_device(self):
        device = create_color_light("d073d5010001")
        server = EmulatedLifxServer([device], "127.0.0.1", 56700)
        async with server:
            yield server

    async def test_set_color(self, color_device):
        ...

    async def test_get_color(self, color_device):
        ...

# tests/test_power.py
class TestPowerOperations:
    """Group power-related tests."""
    ...
```

### Shared Fixtures in conftest.py

```python
# tests/conftest.py
import pytest
from lifx_emulator import create_color_light, EmulatedLifxServer

@pytest.fixture
async def basic_emulator():
    """Reusable basic emulator fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:
        yield server

@pytest.fixture
async def multi_device_emulator():
    """Reusable multi-device fixture."""
    devices = [
        create_color_light(f"d073d500{i:04d}")
        for i in range(1, 4)
    ]
    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
    async with server:
        yield server
```

### Parametrized Device Tests

```python
import pytest
from lifx_emulator import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)

@pytest.fixture(params=[
    ("color", create_color_light),
    ("multizone", lambda s: create_multizone_light(s, zone_count=16)),
    ("tile", lambda s: create_tile_device(s, tile_count=5)),
])
async def any_device_type(request):
    """Test against all device types."""
    device_type, factory = request.param
    device = factory("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server, device_type

async def test_basic_operations(any_device_type):
    """Test runs 3 times (once per device type)."""
    server, device_type = any_device_type
    print(f"Testing {device_type}")
    # Test common operations...
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging

# At top of test file or conftest.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or for specific module
logging.getLogger('lifx_emulator').setLevel(logging.DEBUG)
```

### Add Print Debugging

```python
async def test_with_debugging():
    device = create_color_light("d073d5000001")

    # Check initial state
    print(f"Initial state: {device.state}")

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print(f"Server started on port {server.port}")
        print(f"Devices: {[d.state.serial for d in server.devices]}")

        # Your test here
        ...

        print(f"Final state: {device.state}")
```

### Use pytest -v and -s Flags

```bash
# Verbose output + show print statements
pytest tests/ -v -s

# Even more verbose
pytest tests/ -vv -s

# Show locals on failure
pytest tests/ -l
```

### Capture State on Failure

```python
@pytest.fixture
async def emulator_with_state_capture():
    """Capture state on test failure."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        try:
            yield server
        except Exception:
            # Capture state before cleanup
            print(f"\nDevice state at failure:")
            print(f"  Serial: {device.state.serial}")
            print(f"  Label: {device.state.label}")
            print(f"  Power: {device.state.power}")
            print(f"  Color: {device.state.color}")
            raise
```

## Common Pitfalls

### ❌ Pitfall 1: Forgetting await

```python
# Bad: Forgot await
async def test_bad():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    server.start()  # Returns coroutine, not called!

# Good: Using await
async def test_good():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    async with server:  # Properly awaits start/stop
        ...
```

### ❌ Pitfall 2: Port Conflicts

```python
# Bad: Hard-coded port (conflicts in parallel tests)
port = 56700

# Good: Dynamic port
port = get_free_port()

# Better: Let fixture handle it
@pytest.fixture
async def emulator():
    port = get_free_port()
    ...
```

### ❌ Pitfall 3: Shared Mutable State

```python
# Bad: Shared device across tests
GLOBAL_DEVICE = create_color_light("d073d5000001")

def test_1():
    GLOBAL_DEVICE.state.power = 0  # Modifies global state!

def test_2():
    assert GLOBAL_DEVICE.state.power == 65535  # Fails!

# Good: Fresh device per test
@pytest.fixture
async def device():
    return create_color_light("d073d5000001")
```

### ❌ Pitfall 4: Not Cleaning Up

```python
# Bad: Manual cleanup can be missed
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
await server.start()
# If error occurs here, server never stops!
await run_test()
await server.stop()

# Good: Context manager guarantees cleanup
async with server:
    await run_test()
# Always stops, even on error
```

### ❌ Pitfall 5: Ignoring Async Event Loop

```python
# Bad: Wrong event loop policy on Windows
# May cause issues with asyncio on Windows

# Good: Set policy in conftest.py
import sys
import pytest

if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )
```

## Checklist for New Tests

Before writing a new test, ask:

- [ ] Do I need the full emulator, or would a mock suffice?
- [ ] What fixture scope is appropriate (function/module/session)?
- [ ] Am I using dynamic port allocation?
- [ ] Are my serial numbers unique and meaningful?
- [ ] Am I using context managers for cleanup?
- [ ] Have I added appropriate timeouts?
- [ ] Can this test run in parallel with others?
- [ ] Did I test the test? (Run it locally first)

## Next Steps

- **[Testing Scenarios](testing-scenarios.md)** - Error injection patterns
- **[Integration Testing](integration-testing.md)** - pytest integration
- **[Advanced Examples](../tutorials/04-advanced-scenarios.md)** - Complex scenarios
- **[CI/CD Integration](../tutorials/05-cicd.md)** - Running in CI

## See Also

- [pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [API Reference: Server](../api/server.md)
- [API Reference: Device](../api/device.md)
