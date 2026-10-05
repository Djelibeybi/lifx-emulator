# Integration Testing Guide

This comprehensive guide covers how to integrate the LIFX Emulator into your testing workflow using pytest and pytest-asyncio.

## Overview

Integration testing with the emulator allows you to test your LIFX client code against real protocol implementations without needing physical devices. This guide covers pytest patterns, fixture design, CI/CD integration, and best practices.

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

## Quick Start

### Install Testing Dependencies

```bash
# Core testing tools
pip install pytest pytest-asyncio

# Optional: Parallel testing
pip install pytest-xdist

# Optional: Coverage reporting
pip install pytest-cov

# Optional: Timeout handling
pip install pytest-timeout
```

### Basic Test Setup

```python
# test_basic.py
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

@pytest.fixture
async def emulator():
    """Basic emulator fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.mark.asyncio
async def test_device_creation(emulator):
    """Test device is created correctly."""
    assert len(emulator.get_all_devices()) == 1
    assert emulator.get_all_devices()[0].state.serial == "d073d5000001"
```

Run tests:

```bash
pytest test_basic.py -v
```

## pytest Fixture Patterns

### Function-Scoped Fixtures (Default)

Fresh emulator for each test - safest but slowest:

```python
@pytest.fixture(scope="function")
async def fresh_emulator():
    """New emulator for each test."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.mark.asyncio
async def test_one(fresh_emulator):
    """Each test gets fresh emulator."""
    assert len(fresh_emulator.get_all_devices()) == 1

@pytest.mark.asyncio
async def test_two(fresh_emulator):
    """Separate fresh emulator."""
    assert len(fresh_emulator.get_all_devices()) == 1
```

**Use When:**
- Tests modify device state
- Perfect isolation is critical
- Tests are few or parallelized

### Module-Scoped Fixtures

Shared emulator across one test file - good balance:

A module- or session-scoped async fixture runs on an event loop of that scope, so the
tests that use it must run on the same loop. Declare the loop scope on both the fixture
and the tests, otherwise the server's sockets sit on a loop that isn't running while
the test executes and it never answers:

```python
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_emulator():
    """Shared across entire module."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
    ]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.mark.asyncio(loop_scope="module")
async def test_first_device(module_emulator):
    """Use shared emulator."""
    device = module_emulator.get_device("d073d5000001")
    assert device is not None

@pytest.mark.asyncio(loop_scope="module")
async def test_second_device(module_emulator):
    """Same emulator instance."""
    device = module_emulator.get_device("d073d5000002")
    assert device is not None
```

**Use When:**
- Tests don't modify shared state
- Want faster test execution
- Testing read-only operations

### Session-Scoped Fixtures

One emulator for entire test session - fastest:

```python
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def session_emulator():
    """Shared across all tests."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.mark.asyncio(loop_scope="session")
async def test_uses_session_emulator(session_emulator):
    assert session_emulator.get_device("d073d5000001") is not None
```

To run every test on the session loop without marking each one, set
`asyncio_default_test_loop_scope = session` in your pytest configuration.

**Use When:**
- Very large test suite
- All tests are read-only
- Speed is critical

**Warning:** Tests can affect each other

## Fixture Design Patterns

### Composable Fixtures

Build complex setups from simple fixtures:

```python
@pytest.fixture
async def basic_device():
    """Single device fixture."""
    return create_color_light("d073d5000001")

@pytest.fixture
async def server_with_device(basic_device):
    """Server using device fixture."""
    server = EmulatedLifxServer(
        [basic_device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.mark.asyncio
async def test_with_composed_fixtures(server_with_device):
    """Use composed fixtures."""
    assert len(server_with_device.get_all_devices()) == 1
```

### Parametrized Fixtures

Test against multiple configurations:

```python
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

@pytest.fixture(params=[
    ("color", lambda: create_color_light("d073d5000001")),
    ("multizone", lambda: create_multizone_light("d073d5800001", zone_count=16)),
    ("tile", lambda: create_tile_device("d073d5900001", tile_count=5)),
])
async def any_device(request):
    """Parametrized device fixture."""
    device_type, factory = request.param
    device = factory()
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server, device_type

@pytest.mark.asyncio
async def test_all_device_types(any_device):
    """Test runs 3 times (once per device type)."""
    server, device_type = any_device
    print(f"Testing with {device_type} device")
    assert len(server.get_all_devices()) == 1
```

### Conditional Fixtures

Skip tests based on conditions:

```python
import sys

@pytest.fixture
async def emulator_windows_only():
    """Only run on Windows."""
    if sys.platform != 'win32':
        pytest.skip("Windows-only test")

    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server
```

## conftest.py Organization

Centralize fixtures for reuse across test files:

```python
# tests/conftest.py
import pytest

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

@pytest.fixture
async def single_device():
    """Reusable single device fixture."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.fixture
async def multi_device():
    """Reusable multi-device fixture."""
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_multizone_light("d073d5800001", zone_count=16),
    ]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server

@pytest.fixture
async def unreliable_device():
    """Device configured for error testing."""
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={101: 1.0},  # Never answer GetColor (101)
            response_delays={22: 0.5},  # Delay StatePower (22) replies by 500ms
        ),
    )
    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        yield server
```

Pass the same `HierarchicalScenarioManager` to the factory and to the server as
`scenario_manager=`: the server gives every device it manages its own scenario manager,
so a scenario registered anywhere else is ignored. `drop_packets` matches the incoming
request type, but `response_delays`, `malformed_packets`, `invalid_field_values` and
`partial_responses` match the outgoing response type, which is why the delay above is
keyed by `StatePower` (22), the reply to `GetPower` (20) and `SetPower` (21). See
[Testing Scenarios](testing-scenarios.md) for more.

Now all test files can use these fixtures:

```python
# tests/test_colors.py
import pytest

@pytest.mark.asyncio
async def test_color_device(single_device):
    """Uses fixture from conftest.py"""
    device = single_device.get_device("d073d5000001")
    assert device.state.has_color
```

## Test Isolation Techniques

### State Reset Between Tests

```python
@pytest.fixture
async def emulator_with_reset():
    """Emulator that resets state between tests."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    # Store initial state
    initial_color = device.state.color
    initial_power = device.state.power_level

    async with server:
        yield server

        # Reset state after test
        device.state.color = initial_color
        device.state.power_level = initial_power
```

### Separate Device Instances

```python
@pytest.fixture
def device_factory():
    """Factory for creating fresh devices."""
    def _create(serial=None):
        if serial is None:
            import uuid
            serial = f"d073d5{uuid.uuid4().hex[:6]}"
        return create_color_light(serial)
    return _create

@pytest.mark.asyncio
async def test_with_factory(device_factory):
    """Each call creates fresh device."""
    device1 = device_factory()
    device2 = device_factory()
    assert device1.state.serial != device2.state.serial
```

### Port Isolation

Bind to port 0 and let the operating system choose a free port. `server.port` keeps the
value you passed (0); read the bound port from `server.ipv4_endpoint` once the server
has started:

```python
@pytest.fixture
async def isolated_emulator():
    """Emulator on a unique, OS-assigned port."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        host, port = server.ipv4_endpoint
        yield server, port
```

## Parallel Test Execution

### Basic Parallel Testing

Install pytest-xdist:

```bash
pip install pytest-xdist
```

Run tests in parallel:

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4

# Parallel within modules only
pytest -n auto --dist loadfile
```

### Worker-Safe Fixtures

Each pytest-xdist worker is a separate process, so two workers binding the same fixed
port clash. Bind to port 0 so every server gets its own OS-assigned port, and use
`worker_id` only if you also want serials that differ between workers:

```python
@pytest.fixture
async def worker_safe_emulator(worker_id):
    """Safe for parallel execution."""
    if worker_id == "master":
        # Running without pytest-xdist
        serial = "d073d5000001"
    else:
        # Running with pytest-xdist (gw0, gw1, etc.)
        worker_num = int(worker_id.replace("gw", ""))
        serial = f"d073d5{worker_num + 1:06d}"

    device = create_color_light(serial)
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server  # Bound port: server.ipv4_endpoint[1]
```

### Parallel Test Best Practices

```python
# Mark tests as safe for parallel execution
@pytest.mark.parallel
@pytest.mark.asyncio
async def test_parallel_safe(worker_safe_emulator):
    """Can run in parallel with other tests."""
    assert len(worker_safe_emulator.get_all_devices()) == 1

# Mark tests that must run serially
@pytest.mark.serial
@pytest.mark.asyncio
async def test_must_run_alone():
    """Cannot run in parallel."""
    # Tests that modify global state, use hardcoded ports, etc.
    ...
```

Configure in pytest.ini:

```ini
[pytest]
markers =
    parallel: Tests safe for parallel execution
    serial: Tests that must run alone
```

## CI/CD Integration

### GitHub Actions

Basic workflow:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13', '3.14']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install pytest pytest-asyncio pytest-xdist
        pip install -e .

    - name: Run tests
      run: |
        pytest tests/ -v -n auto
```

### GitLab CI

```yaml
# .gitlab-ci.yml
test:
  image: python:3.13
  script:
    - pip install pytest pytest-asyncio
    - pip install -e .
    - pytest tests/ -v --junitxml=report.xml
  artifacts:
    when: always
    reports:
      junit: report.xml
```

### Docker-Based Testing

```dockerfile
# Dockerfile.test
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install pytest pytest-asyncio && \
    pip install -e .

CMD ["pytest", "tests/", "-v"]
```

Run tests in Docker:

```bash
docker build -f Dockerfile.test -t lifx-tests .
docker run lifx-tests
```

## Handling Test Dependencies

### Sequential Test Execution

When tests must run in order:

```python
import pytest

@pytest.mark.asyncio
@pytest.mark.order(1)
async def test_first():
    """Runs first."""
    ...

@pytest.mark.asyncio
@pytest.mark.order(2)
async def test_second():
    """Runs second."""
    ...
```

Requires pytest-order:

```bash
pip install pytest-order
```

### Test Data Dependencies

Share data between tests:

```python
import pytest

@pytest.fixture(scope="module")
def test_data():
    """Shared test data."""
    return {"device_serial": "d073d5000001"}

@pytest.mark.asyncio
async def test_create(test_data):
    """Use shared data."""
    device = create_color_light(test_data["device_serial"])
    assert device is not None

@pytest.mark.asyncio
async def test_query(test_data):
    """Use same data."""
    # Can use test_data["device_serial"]
    ...
```

### Cleanup Dependencies

Ensure cleanup happens in correct order:

```python
@pytest.fixture
async def database():
    """Mock database."""
    db = setup_database()
    yield db
    teardown_database(db)

@pytest.fixture
async def emulator_with_db(database):
    """Emulator using database."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        yield server
    # database fixture will clean up after this
```

## Advanced Testing Patterns

### Testing Error Handling

`query_color()` and `query_device()` below stand in for your own client calls.

```python
import asyncio

import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test client handles timeouts."""
    # Drop every GetColor (101) packet sent to this device
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(drop_packets={101: 1.0})
    )
    device = create_color_light("d073d5000001", scenario_manager=manager)

    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        # Your client should time out gracefully
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(query_color(device), timeout=1.0)
```

### Testing Concurrent Operations

```python
import asyncio


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test multiple concurrent operations."""
    devices = [create_color_light(f"d073d500{i:04d}") for i in range(5)]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        # Send requests to all devices concurrently
        tasks = [
            query_device(device.state.serial)
            for device in devices
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
```

### Testing State Transitions

```python
@pytest.mark.asyncio
async def test_state_transitions():
    """Test device state changes."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        # Initial state
        assert device.state.power_level == 65535  # On

        # Transition to off
        device.state.power_level = 0
        assert device.state.power_level == 0

        # Back to on
        device.state.power_level = 65535
        assert device.state.power_level == 65535
```

## pytest Configuration

### pytest.ini

```ini
[pytest]
# Test discovery
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Output
addopts =
    -v
    --strict-markers
    --tb=short
    --color=yes

# Markers
markers =
    slow: Slow tests (deselect with '-m "not slow"')
    integration: Integration tests
    unit: Unit tests
    parallel: Safe for parallel execution
```

Coverage settings don't belong in `pytest.ini`; put them in `.coveragerc` (or
`setup.cfg`, `tox.ini` or `pyproject.toml`):

```ini
# .coveragerc
[run]
source = src
omit = */tests/*

[report]
precision = 2
show_missing = True
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

## Test Organization Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_colors.py
│   ├── test_power.py
│   └── test_labels.py
├── integration/             # Integration tests
│   ├── conftest.py         # Integration-specific fixtures
│   ├── test_discovery.py
│   ├── test_multidevice.py
│   └── test_scenarios.py
├── performance/             # Performance tests
│   ├── test_load.py
│   └── test_concurrent.py
└── fixtures/                # Shared test data
    ├── device_configs.py
    └── scenarios.py
```

## Debugging Failed Tests

### Capture Output

```python
import pytest

from lifx_emulator import create_color_light

@pytest.mark.asyncio
async def test_with_capture(capfd):
    """Capture stdout/stderr."""
    device = create_color_light("d073d5000001")
    print(f"Device created: {device.state.serial}")

    # Test code...

    # Check captured output
    captured = capfd.readouterr()
    assert "d073d5000001" in captured.out
```

### Use pytest --pdb

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Drop into debugger at start of test
pytest --trace
```

### Add Logging

```python
import logging
import pytest

@pytest.fixture(autouse=True)
def configure_logging():
    """Auto-configure logging for all tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

## Next Steps

- **[Best Practices](best-practices.md)** - Testing best practices
- **[Testing Scenarios](testing-scenarios.md)** - Error injection
- **[CI/CD Tutorial](../tutorials/05-cicd.md)** - Detailed CI/CD setup
- **[Integration Examples](../tutorials/03-integration.md)** - More examples

## See Also

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [API Reference: Server](../library/server.md)
- [API Reference: Device](../library/device.md)
