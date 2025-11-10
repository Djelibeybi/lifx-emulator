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
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        pip install uv
        uv sync

    - name: Run tests with emulator
      run: |
        pytest tests/ -v

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
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
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

**Note:** Ensure your tests use dynamic port allocation to avoid conflicts:

```python
def get_free_port():
    """Find an available port."""
    import socket
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@pytest.fixture
async def emulator():
    port = get_free_port()
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", port)
    async with server:
        yield server
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
    - pytest tests/ -v --junitxml=report.xml
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
    - pip install pytest-cov
    - pytest tests/ -v --cov=src --cov-report=xml --cov-report=term
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
CMD ["pytest", "tests/", "-v"]
```

### Docker Compose for Multi-Container Testing

Create `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  emulator:
    build:
      context: .
      dockerfile: Dockerfile.test
    command: python -m lifx_emulator --color 3 --multizone 2
    ports:
      - "56700:56700/udp"
    networks:
      - test-network

  tests:
    build:
      context: .
      dockerfile: Dockerfile.test
    command: pytest tests/integration/ -v
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
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Standalone Emulator Container

Build and run emulator in a container:

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

# Expose UDP port
EXPOSE 56700/udp

# Run emulator with default configuration
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
import pytest
import subprocess
import time
import signal

@pytest.fixture(scope="session")
def emulator_process():
    """Start emulator as subprocess for entire test session."""
    # Start emulator
    proc = subprocess.Popen(
        ["lifx-emulator", "--color", "3"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
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

```python
import socket

def get_free_port():
    """Get a free port from the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

@pytest.fixture
async def emulator_with_dynamic_port():
    port = get_free_port()
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server, port
```

### Strategy 2: Port Ranges per Worker

When using pytest-xdist:

```python
@pytest.fixture
async def emulator(worker_id):
    """Each worker gets unique port."""
    if worker_id == 'master':
        port = 56700
    else:
        # Extract worker number (gw0, gw1, etc.)
        worker_num = int(worker_id.replace('gw', ''))
        port = 56700 + worker_num + 1

    device = create_color_light(f"d073d500{worker_num:04d}")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

    async with server:
        yield server
```

### Strategy 3: Environment Variables

```python
import os

@pytest.fixture
async def emulator():
    # Allow port override via env var
    port = int(os.getenv('LIFX_EMULATOR_PORT', '56700'))

    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", port)

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
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        pip install uv
        uv sync
        pip install pytest pytest-asyncio pytest-cov pytest-xdist

    - name: Run tests with coverage
      run: |
        pytest tests/ -v -n auto \
          --cov=src \
          --cov-report=xml \
          --cov-report=term-missing

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.13'
      with:
        file: ./coverage.xml
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
    - pytest tests/unit/ -v --junitxml=report.xml
  artifacts:
    when: always
    reports:
      junit: report.xml

test:integration:
  stage: test
  script:
    - pytest tests/integration/ -v -n auto --junitxml=integration-report.xml
  artifacts:
    when: always
    reports:
      junit: integration-report.xml

test:coverage:
  stage: test
  script:
    - pip install pytest-cov
    - pytest tests/ -v --cov=src --cov-report=xml --cov-report=html
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
# Session scope - shared across all tests (fastest)
@pytest.fixture(scope="session")
async def shared_emulator():
    ...

# Module scope - shared within a test file
@pytest.fixture(scope="module")
async def module_emulator():
    ...

# Function scope - fresh per test (slowest, most isolated)
@pytest.fixture(scope="function")
async def fresh_emulator():
    ...
```

### 2. Cache Dependencies

Always cache pip/uv dependencies in CI to speed up builds:

```yaml
# GitHub Actions

- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
```

### 3. Use Timeouts

Prevent hanging tests:

```python
@pytest.mark.asyncio
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
      uses: actions/upload-artifact@v3
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

**Solution:** Ensure proper async event loop handling:

```python
# conftest.py
import sys
import pytest

if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

## Next Steps

- **[Integration Testing](03-integration.md)** - Review pytest patterns
- **[Advanced Examples](04-advanced-scenarios.md)** - Learn error injection for CI tests
- **[Best Practices](../guide/best-practices.md)** - Testing best practices

## See Also

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [GitLab CI Documentation](https://docs.gitlab.com/ee/ci/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
