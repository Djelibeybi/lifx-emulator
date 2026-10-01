# Best Practices

This guide covers best practices for using the LIFX Emulator effectively in your development and testing workflows.

Every example creates its server with a `DeviceManager`, which `EmulatedLifxServer` requires as its second argument. Give each server its own `DeviceManager(DeviceRepository())`; never share one between servers. Snippets that omit their imports assume these:

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
```

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

    # Test your colour conversion logic
    rgb = convert_hsbk_to_rgb(mock_device.get_color())
    assert rgb == (0, 255, 128)

# Bad: Unit test with emulator (too slow)
async def test_color_converter_slow():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:
        # Just testing conversion logic doesn't need a full emulator
        ...
```

**2. Testing Third-Party Hardware**
- Emulator can't reproduce hardware-specific bugs
- Real devices needed for hardware validation
- Firmware behaviour may differ

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
        ├─ Do you need to test hardware-specific behaviour?
        │   └─ Yes → Use Real Device
        └─ No
            ├─ Is this an integration/E2E test?
            │   └─ Yes → Use Emulator
            └─ No → Use Mock
```

## Serial Strategies

### Consistent Naming Conventions

Use meaningful serial patterns for easier debugging:

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

Ensure serials are unique across your test suite:

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
    """Generate unique serials."""
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

Always use dynamic ports to avoid conflicts. Bind to port 0 and let the operating
system choose a free UDP port when the server starts. `server.port` keeps the value you
passed (0); read the bound port from `server.ipv4_endpoint`:

```python
@pytest.fixture
async def emulator():
    """Emulator with dynamic port."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        host, port = server.ipv4_endpoint
        yield server, port
```

Avoid helpers that bind a throwaway socket to find a free port and then close it: the
port can be taken again before the emulator binds it, and a free TCP port says nothing
about the UDP port the emulator needs.

### Ports for Parallel Tests

Port 0 also makes fixtures safe under pytest-xdist: every worker's server gets its own
port, so there is no need to derive port numbers from `worker_id`.

### Environment Variable Override

```python
import os

@pytest.fixture
async def emulator():
    """Allow port override via environment."""
    port = int(os.getenv("LIFX_EMULATOR_PORT", "0"))

    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", port
    )

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
    # Each server needs its own DeviceManager
    server1 = EmulatedLifxServer(
        [device1], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    server2 = EmulatedLifxServer(
        [device2], DeviceManager(DeviceRepository()), "127.0.0.1", 56701
    )

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
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

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
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        try:
            yield server
        finally:
            # Additional cleanup if needed. This runs while the server is
            # still up; the context manager stops it afterwards.
            print("Cleaning up...")
```

### Cleanup Even on Exceptions

pytest does not raise a test's exception inside the fixture, so an `except` block around
`yield` never runs. You don't need one: the code after `yield`, including the exit of
`async with server:`, runs whether the test passed or failed.

```python
@pytest.fixture
async def robust_emulator():
    """Emulator that cleans up even on test failure."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server
    # Server is stopped here, even if the test failed
```

To act on a failure, see [Capture State on Failure](#capture-state-on-failure).

### Background Task Management

```python
import asyncio

@pytest.fixture
async def emulator_with_task():
    """Emulator with background task."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

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

Choose appropriate fixture scopes for performance. A module- or session-scoped async
fixture runs on an event loop of that scope, so tests that use it must declare the same
`loop_scope`; otherwise the server's sockets sit on a loop that isn't running while the
test executes, and it never answers:

```python
import pytest
import pytest_asyncio

# Fastest: Session scope (one emulator for all tests)
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def shared_emulator():
    """Shared across entire test session."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server
    # Pros: Very fast, minimal overhead
    # Cons: Tests may affect each other

# Balanced: Module scope (one per test file)
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_emulator():
    """Shared across one test file."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server
    # Pros: Good isolation, reasonable speed
    # Cons: Some test coupling within module

# Safest: Function scope (one per test)
@pytest.fixture(scope="function")
async def fresh_emulator():
    """Fresh emulator for each test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server
    # Pros: Perfect isolation
    # Cons: Slowest (startup overhead per test)

@pytest.mark.asyncio(loop_scope="module")
async def test_uses_module_emulator(module_emulator):
    assert module_emulator.get_device("d073d5000001") is not None
```

### Parallel Test Execution

```bash
# Run tests in parallel with pytest-xdist
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 workers
```

```python
# Ensure tests are parallel-safe: port 0 gives every worker its own port
@pytest.fixture
async def parallel_safe_emulator():
    """Each server binds an OS-assigned port."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server
```

### Minimize Device Count

Create only the devices you need:

```python
# Bad: Creating unnecessary devices
devices = [create_color_light(f"d073d500{i:04d}") for i in range(100)]
server = EmulatedLifxServer(
    devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
)
# Only testing with 1 device!

# Good: Create what you need
device = create_color_light("d073d5000001")
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
)
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
        server = EmulatedLifxServer(
            [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
        )
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
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

@pytest.fixture
async def basic_emulator():
    """Reusable basic emulator fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:
        yield server

@pytest.fixture
async def multi_device_emulator():
    """Reusable multi-device fixture."""
    devices = [
        create_color_light(f"d073d500{i:04d}")
        for i in range(1, 4)
    ]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:
        yield server
```

### Parametrized Device Tests

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

@pytest.fixture(params=[
    ("color", create_color_light),
    ("multizone", lambda s: create_multizone_light(s, zone_count=16)),
    ("tile", lambda s: create_tile_device(s, tile_count=5)),
])
async def any_device_type(request):
    """Test against all device types."""
    device_type, factory = request.param
    device = factory("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

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

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(f"Server listening on {server.ipv4_endpoint}")
        print(f"Devices: {[d.state.serial for d in server.get_all_devices()]}")

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

A fixture never sees the test's exception, so it can't catch it. Record each test
phase's report on the test item with a hook in `conftest.py`, then check it in the
fixture's teardown:

```python
# tests/conftest.py
import pytest


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, f"rep_{report.when}", report)
    return report


@pytest.fixture
async def emulator_with_state_capture(request):
    """Capture state on test failure."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

        report = getattr(request.node, "rep_call", None)
        if report is not None and report.failed:
            # Capture state before the server stops
            print("\nDevice state at failure:")
            print(f"  Serial: {device.state.serial}")
            print(f"  Label: {device.state.label}")
            print(f"  Power: {device.state.power_level}")
            print(f"  Color: {device.state.color}")
```

Output printed during teardown appears in the test's "Captured stdout teardown" section.

## Common Pitfalls

### ❌ Pitfall 1: Forgetting await

```python
# Bad: Forgot await
async def test_bad():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    server.start()  # Returns coroutine, not called!

# Good: Using await
async def test_good():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )
    async with server:  # Properly awaits start/stop
        ...
```

### ❌ Pitfall 2: Port Conflicts

```python
# Bad: Hard-coded port (conflicts in parallel tests)
port = 56700

# Good: Port 0, so the OS assigns a free port at bind time
@pytest.fixture
async def emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server  # Bound port: server.ipv4_endpoint[1]
```

### ❌ Pitfall 3: Shared Mutable State

```python
# Bad: Shared device across tests
GLOBAL_DEVICE = create_color_light("d073d5000001")

def test_1():
    GLOBAL_DEVICE.state.power_level = 0  # Modifies global state!

def test_2():
    assert GLOBAL_DEVICE.state.power_level == 65535  # Fails!

# Good: Fresh device per test
@pytest.fixture
async def device():
    return create_color_light("d073d5000001")
```

### ❌ Pitfall 4: Not Cleaning Up

```python
# Bad: Manual cleanup can be missed
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
)
await server.start()
# If error occurs here, server never stops!
await run_test()
await server.stop()

# Good: Context manager guarantees cleanup
async with server:
    await run_test()
# Always stops, even on error
```

### ❌ Pitfall 5: Mismatched Event Loop Scopes

```python
import pytest
import pytest_asyncio

# Bad: module-scoped fixture used by function-scoped tests. The server runs on
# the module's event loop, which isn't running while each test runs on its own
# loop, so the emulator never answers.
@pytest.fixture(scope="module")
async def shared_emulator():
    ...

# Good: fixture and tests share the module's event loop
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def shared_emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server

@pytest.mark.asyncio(loop_scope="module")
async def test_uses_shared_emulator(shared_emulator):
    ...
```

## Checklist for New Tests

Before writing a new test, ask:

- [ ] Do I need the full emulator, or would a mock suffice?
- [ ] What fixture scope is appropriate (function/module/session)?
- [ ] Am I using dynamic port allocation?
- [ ] Are my serials unique and meaningful?
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
- [API Reference: Server](../library/server.md)
- [API Reference: Device](../library/device.md)
