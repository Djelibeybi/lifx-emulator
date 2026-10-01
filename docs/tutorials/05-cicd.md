# CI/CD Integration

**Difficulty:** 🔴 Advanced | **Time:** ⏱️ 30 minutes | **Prerequisites:** [Integration Testing Tutorial](03-integration.md)

This tutorial shows how to integrate the LIFX Emulator into your CI/CD pipelines using GitHub Actions, GitLab CI, and Docker.

## What You'll Learn

- Running the emulator in GitHub Actions
- GitLab CI configuration
- Docker containerization
- Port conflict management in CI
- Background process handling
- Test parallelization in CI

## GitHub Actions Integration

### Basic Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v7

    - name: Set up Python
      uses: actions/setup-python@v7
      with:
        python-version: '3.13'

    - name: Install uv
      uses: astral-sh/setup-uv@v10

    - name: Install dependencies
      run: uv sync

    - name: Run tests with emulator
      run: uv run pytest tests/ -v

```

### With Explicit Emulator Installation

If the emulator is a separate dependency:

```yaml
    - name: Install LIFX Emulator
      run: |
        pip install lifx-emulator

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --tb=short
```

### Matrix Testing Across Python Versions

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13', '3.14']

    steps:
    - uses: actions/checkout@v7

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v7
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-asyncio

    - name: Run tests
      run: pytest tests/ -v
```

### Parallel Test Execution

Using pytest-xdist for faster tests:

```yaml
    - name: Install test dependencies
      run: |
        pip install pytest pytest-asyncio pytest-xdist

    - name: Run tests in parallel
      run: |
        # -n auto: Use all available CPU cores
        pytest tests/ -v -n auto
```

**Note:** Ensure your tests use dynamic port allocation to avoid conflicts. Bind to port `0` so the operating system picks a free UDP port, then read the real port from `server.ipv4_endpoint` once the server has started (`server.port` stays `0`):

```python
import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest.fixture
async def emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        port = server.ipv4_endpoint[1]  # The port the OS assigned
        yield server, port
```

## GitLab CI Integration

### Basic Configuration

Create `.gitlab-ci.yml`:

```yaml
image: python:3.13

stages:
  - test

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

before_script:
  - pip install uv
  - uv sync

test:
  stage: test
  script:
    - uv run pytest tests/ -v --junitxml=report.xml
  artifacts:
    when: always
    reports:
      junit: report.xml
```

### With Coverage Reporting

```yaml
test:
  stage: test
  script:
    - uv run --with pytest-cov pytest tests/ -v --cov=src --cov-report=xml --cov-report=term
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Multiple Python Versions

```yaml
.test_template:
  stage: test
  script:
    - pip install -e .
    - pytest tests/ -v

test:python3.13:
  extends: .test_template
  image: python:3.13

test:python3.14:
  extends: .test_template
  image: python:3.14
```

## Docker Integration

### Dockerfile for Testing

Create a `Dockerfile.test`:

```dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir uv && \
    uv sync

# Run tests by default
CMD ["uv", "run", "pytest", "tests/", "-v"]
```

### Docker Compose for Multi-Container Testing

Create `docker-compose.test.yml` (this assumes `lifx-emulator` is one of your project's dependencies, so `uv sync` installs it):

```yaml
services:
  emulator:
    build:
      context: .
      dockerfile: Dockerfile.test
    # Bind to 0.0.0.0 so the tests container can reach the emulator
    command: uv run lifx-emulator --color 3 --multizone 2 --bind 0.0.0.0
    ports:
      - "56700:56700/udp"
    networks:
      - test-network

  tests:
    build:
      context: .
      dockerfile: Dockerfile.test
    command: uv run pytest tests/integration/ -v
    depends_on:
      - emulator
    networks:
      - test-network
    environment:
      - LIFX_EMULATOR_HOST=emulator
      - LIFX_EMULATOR_PORT=56700

networks:
  test-network:
    driver: bridge
```

Run with:

```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Standalone Emulator Container

Build and run the emulator in a container:

```dockerfile
# Dockerfile
FROM python:3.13-slim

RUN pip install --no-cache-dir lifx-emulator

# Expose UDP port
EXPOSE 56700/udp

# Run emulator with specific devices
CMD ["lifx-emulator", "--color", "3", "--multizone", "2", "--bind", "0.0.0.0"]
```

Build and run:

```bash
docker build -t lifx-emulator .
docker run -p 56700:56700/udp lifx-emulator
```

## Background Process Management

### GitHub Actions Background Service

Run emulator as a background service:

```yaml
    - name: Start LIFX Emulator
      run: |
        lifx-emulator --color 2 &
        echo $! > emulator.pid
        sleep 2  # Wait for startup

    - name: Run tests
      run: |
        pytest tests/integration/ -v

    - name: Stop LIFX Emulator
      if: always()
      run: |
        if [ -f emulator.pid ]; then
          kill $(cat emulator.pid) || true
        fi
```

### Using pytest Fixtures

Better approach - let pytest manage the process:

```python
# conftest.py
import signal
import subprocess
import time

import pytest


@pytest.fixture(scope="session")
def emulator_process():
    """Start emulator as subprocess for entire test session."""
    # Start emulator. Discard its output: a pipe that is never read can
    # fill up and block the emulator, especially with --verbose.
    proc = subprocess.Popen(
        ["lifx-emulator", "--color", "3"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for startup
    time.sleep(2)

    yield proc

    # Cleanup
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)
```

No CI configuration changes needed - tests manage the emulator themselves!

## Port Conflict Handling

### Strategy 1: Dynamic Port Allocation

Bind to port `0` and let the operating system assign a free UDP port. `server.port` keeps the value you passed (`0`), so read the assigned port from `server.ipv4_endpoint` after the server starts:

```python
import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest.fixture
async def emulator_with_dynamic_port():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server, server.ipv4_endpoint[1]
```

This avoids the race in "find a free port, close it, then bind it" helpers, where another process can take the port in between.

### Strategy 2: Port Ranges per Worker

When using pytest-xdist:

```python
import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest.fixture
async def emulator(worker_id):
    """Each worker gets a unique port and serial."""
    if worker_id == "master":
        # Not running under xdist
        worker_num = 0
    else:
        # Extract worker number (gw0, gw1, etc.)
        worker_num = int(worker_id.replace("gw", "")) + 1

    port = 56700 + worker_num
    device = create_color_light(f"d073d500{worker_num:04d}")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", port
    )

    async with server:
        yield server
```

### Strategy 3: Environment Variables

```python
import os

import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest.fixture
async def emulator():
    # Allow port override via env var
    port = int(os.getenv("LIFX_EMULATOR_PORT", "56700"))

    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", port
    )

    async with server:
        yield server
```

In CI:

```yaml
    - name: Run tests on custom port
      env:
        LIFX_EMULATOR_PORT: 56800
      run: pytest tests/ -v
```

## Complete GitHub Actions Example

Here's a production-ready workflow:

```yaml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.13', '3.14']

    steps:
    - uses: actions/checkout@v7

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v7
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv (with dependency caching)
      uses: astral-sh/setup-uv@v10
      with:
        enable-cache: true

    # Assumes pytest, pytest-asyncio, pytest-cov and pytest-xdist are in
    # your project's dev dependency group (uv add --dev ...)
    - name: Install dependencies
      run: uv sync

    # One line, because the default shell on Windows runners is PowerShell,
    # which does not understand backslash line continuations
    - name: Run tests with coverage
      run: uv run pytest tests/ -v -n auto --cov=src --cov-report=xml --cov-report=term-missing

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v7
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.13'
      with:
        files: ./coverage.xml
        token: ${{ secrets.CODECOV_TOKEN }}
        fail_ci_if_error: true
```

## Complete GitLab CI Example

```yaml
image: python:3.13

stages:
  - test
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - .venv/

before_script:
  - pip install uv
  - uv sync

test:unit:
  stage: test
  script:
    - uv run pytest tests/unit/ -v --junitxml=report.xml
  artifacts:
    when: always
    reports:
      junit: report.xml

test:integration:
  stage: test
  script:
    - uv run --with pytest-xdist pytest tests/integration/ -v -n auto --junitxml=integration-report.xml
  artifacts:
    when: always
    reports:
      junit: integration-report.xml

test:coverage:
  stage: test
  script:
    - uv run --with pytest-cov pytest tests/ -v --cov=src --cov-report=xml --cov-report=html
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    paths:
      - htmlcov/
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## Testing the CI Configuration Locally

### GitHub Actions with act

Install [act](https://github.com/nektos/act):

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

Run workflows locally:

```bash
# Run all jobs
act

# Run specific job
act -j test

# Run on specific event
act pull_request
```

### GitLab CI with gitlab-runner

Install GitLab Runner:

```bash
# macOS
brew install gitlab-runner

# Linux
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner
```

Test locally:

```bash
gitlab-runner exec docker test
```

## Best Practices

### 1. Use Fixture Scopes Appropriately

```python
import pytest
import pytest_asyncio


# Session scope - shared across all tests (fastest)
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def shared_emulator():
    ...


# Module scope - shared within a test file
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_emulator():
    ...


# Function scope - fresh per test (slowest, most isolated)
@pytest.fixture(scope="function")
async def fresh_emulator():
    ...
```

With pytest-asyncio, a shared emulator must run on an event loop that lives as long as the fixture, and the tests that use it must run on that same loop. Otherwise the server sits on a loop that is idle while your test runs, and every request times out with no reply. Give the fixture a matching `loop_scope` as above and mark the tests that use it:

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_discovery(shared_emulator):
    ...
```

Alternatively, set `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope` to `"session"` in your pytest configuration.

### 2. Cache Dependencies

Always cache pip/uv dependencies in CI to speed up builds:

```yaml
# GitHub Actions: setup-uv caches the uv cache directory for you
- uses: astral-sh/setup-uv@v10
  with:
    enable-cache: true

# Or, with pip
- uses: actions/cache@v6
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
```

### 3. Use Timeouts

Prevent hanging tests (the `timeout` marker needs the `pytest-timeout` plugin):

```python
import pytest


@pytest.mark.timeout(30)  # Fail after 30 seconds
async def test_with_timeout(emulator):
    ...
```

In GitHub Actions:

```yaml
jobs:
  test:
    timeout-minutes: 10  # Fail entire job after 10 minutes
```

### 4. Collect Logs on Failure

```yaml
    - name: Upload logs on failure
      if: failure()
      uses: actions/upload-artifact@v7
      with:
        name: test-logs
        path: |
          *.log
          test-results/
```

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Common causes:**
- Port conflicts in CI environment
- Timing issues (CI is slower)
- Different Python versions
- Missing dependencies

**Solutions:**
- Use dynamic port allocation
- Add startup delays: `await asyncio.sleep(0.5)`
- Pin Python version in CI config
- Install all dependencies explicitly

### Timeout Issues in CI

**Problem:** Tests timeout in CI but work locally

**Solutions:**
- Increase test timeouts
- Use faster fixture scopes
- Enable parallel testing with pytest-xdist
- Check for deadlocks in async code

### Windows-Specific Issues

**Problem:** Tests fail on Windows runners

**Solutions:**

- Don't change the event loop policy. The default Proactor event loop on Windows supports the UDP sockets the emulator uses, and `asyncio.set_event_loop_policy()` is deprecated from Python 3.14.
- Use `shell: bash` (or keep commands on one line) in workflow steps, because the default shell on Windows runners is PowerShell.
- Bind to `127.0.0.1` so Windows Defender Firewall doesn't prompt for network access.

## Next Steps

- **[Integration Testing](03-integration.md)** - Review pytest patterns
- **[Advanced Examples](04-advanced-scenarios.md)** - Learn error injection for CI tests
- **[Best Practices](../guide/best-practices.md)** - Testing best practices

## See Also

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [GitLab CI Documentation](https://docs.gitlab.com/ee/ci/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
