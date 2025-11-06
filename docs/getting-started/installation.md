# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Installation Methods

We support both `uv` (recommended) and `pip` for installation.

### As a CLI Tool

**Recommended: Using uv** (automatically manages Python environment):

```bash
uv tool install lifx-emulator
```

**Alternative: Using pip** (requires Python 3.11+ already installed):

```bash
pip install lifx-emulator
```

### As a Library in Your Project

**Recommended: Using uv**:

```bash
uv add lifx-emulator
```

**Alternative: Using pip** (requires Python 3.11+ already installed):

```bash
pip install lifx-emulator
```

Then in your code:

```python
from lifx_emulator import create_color_light, EmulatedLifxServer
```

### Development Installation

For development or to get the latest features:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

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

The emulator has minimal dependencies:

- **pyyaml**: For product registry and configuration
- **asyncio**: For asynchronous networking (built-in)

### Development Dependencies

For development, additional dependencies are installed:

- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **ruff**: Fast Python linter
- **pyright**: Type checker
- **hatchling**: Build backend

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
uv tool install lifx-emulator  # For CLI tool
# or
uv add lifx-emulator  # As a dependency of your project
```

### Import Errors

If you see import errors, ensure the package is installed:

```bash
pip show lifx-emulator
```

If not found, reinstall:

```bash
pip install --force-reinstall lifx-emulator
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Create your first emulated device
- [CLI Usage](cli.md) - Learn all CLI commands
- [Device Types](../guide/device-types.md) - Explore supported devices
