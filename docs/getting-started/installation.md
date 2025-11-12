# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Installation Methods

We support both `uv` (recommended) and `pip` for installation.

The LIFX emulator is split into two packages:

1. **`lifx-emulator`** - Core library with minimal dependencies (just `pyyaml`)
2. **`lifx-emulator-cli`** - CLI tool and HTTP API server (includes core + `cyclopts`, `fastapi`, `rich`, `uvicorn`)

### As a CLI Tool

**Recommended: Using uv** (automatically manages Python environment):

```bash
uv tool install lifx-emulator-cli
```

**Alternative: Using pip** (requires Python 3.11+ already installed):

```bash
pip install lifx-emulator-cli
```

This installs the `lifx-emulator` command with full CLI and API server features.

### As a Library in Your Project

**For minimal dependencies** (core library only):

Using uv:
```bash
uv add lifx-emulator
```

Using pip:
```bash
pip install lifx-emulator
```

**For full features** (core + CLI/API):

Using uv:
```bash
uv add lifx-emulator-cli
```

Using pip:
```bash
pip install lifx-emulator-cli
```

Then in your code:

```python
from lifx_emulator import (
    create_color_light,
    EmulatedLifxServer,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

# Create devices
device = create_color_light("d073d5000001")

# Create repository and manager
repo = DeviceRepository()
manager = DeviceManager(repo)

# Create server
server = EmulatedLifxServer([device], manager, "127.0.0.1", 56700)
```

!!! note "Choosing the right package"
    - **Use `lifx-emulator`** when you only need programmatic access and want minimal dependencies
    - **Use `lifx-emulator-cli`** when you need the command-line tool or HTTP API server

### Development Installation

For development or to get the latest features:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install all workspace packages and dev dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

The repository uses a **uv workspace** with two packages:
- `packages/lifx-emulator/` - Core library
- `packages/lifx-emulator-cli/` - CLI tool

Running `uv sync` installs both packages in development mode along with all dev dependencies.

## Verify Installation

Test that the installation worked:

```bash
# Check CLI is available
lifx-emulator --help

# Run the emulator with verbose output
lifx-emulator --verbose
```

You should see output like:

```
INFO - Starting LIFX Emulator on 127.0.0.1:56700
INFO - Created 1 emulated device(s):
INFO -   • A19 d073d5000001 (d073d5000001) - full color
INFO - Server running with verbose packet logging... Press Ctrl+C to stop
```

## Python API Verification

Test the Python API:

```python
from lifx_emulator import create_color_light

device = create_color_light("d073d5000001")
print(f"Device: {device.state.label}")
print(f"Product: {device.state.product}")
print(f"Has color: {device.state.has_color}")
```

## Dependencies

### Core Library (`lifx-emulator`)

Minimal dependencies for the core library:

- **pyyaml**: For product registry and configuration
- **asyncio**: For asynchronous networking (built-in to Python)

### CLI Package (`lifx-emulator-cli`)

Additional dependencies for the CLI and API:

- **cyclopts**: Command-line argument parsing
- **fastapi**: HTTP API server framework
- **rich**: Terminal output formatting
- **uvicorn**: ASGI server for FastAPI

### Development Dependencies

For development, additional dependencies are installed:

- **pytest**, **pytest-asyncio**: Testing framework
- **ruff**: Fast Python linter and formatter
- **pyright**: Type checker
- **hatchling**: Build backend
- **mkdocs**, **mkdocs-material**: Documentation

## Troubleshooting

### Port Already in Use

If you see an error about port 56700 being in use:

```bash
# Use a different port
lifx-emulator --port 56701
```

### Python Version

Ensure you're using Python 3.11+:

```bash
python --version
```

If you need to manage Python versions, we recommend using uv, which automatically handles Python version management for tools and projects:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# uv will automatically manage Python for you
uv tool install lifx-emulator-cli  # For CLI tool
# or
uv add lifx-emulator  # Core library as a dependency
uv add lifx-emulator-cli  # CLI + core as a dependency
```

### Import Errors

If you see import errors, ensure the package is installed:

```bash
# Check core library
pip show lifx-emulator

# Check CLI package
pip show lifx-emulator-cli
```

If not found, reinstall:

```bash
# Core library only
pip install --force-reinstall lifx-emulator

# CLI + core
pip install --force-reinstall lifx-emulator-cli
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Create your first emulated device
- [CLI Usage](cli.md) - Learn all CLI commands
- [Device Types](../guide/device-types.md) - Explore supported devices
