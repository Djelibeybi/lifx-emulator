# Installation

## Requirements

- Python 3.11 or higher
- pip or uv package manager

## Choose Your Package

| Package | Install Command | Use Case |
|---------|----------------|----------|
| `lifx-emulator` | `pip install lifx-emulator` | CLI tool with HTTP API |
| `lifx-emulator-core` | `pip install lifx-emulator-core` | Python library for embedding |

## Installation Methods

### lifx-emulator (CLI + HTTP API)

**Recommended: Using uv** (automatically manages Python environment):

```bash
uv tool install lifx-emulator
```

**Alternative: Using pip** (requires Python 3.11+ already installed):

```bash
pip install lifx-emulator
```

### lifx-emulator-core (Python Library)

**Using uv**:

```bash
uv add lifx-emulator-core
```

**Using pip**:

```bash
pip install lifx-emulator-core
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

### CLI Package

```bash
# Check CLI is available
lifx-emulator --help

# Run the emulator with a color light and verbose output
lifx-emulator --color 1 --verbose
```

You should see output like:

```text
INFO     Starting LIFX Emulator on 127.0.0.1:56700
INFO     Created 1 emulated device(s):
INFO       • LIFX Color 000001 (d073d5000001) - color
INFO     Server running with verbose packet logging... Press Ctrl+C to stop
```

### Library Package

```python
from lifx_emulator import create_color_light

device = create_color_light("d073d5000001")
print(f"Device: {device.state.label}")
print(f"Product: {device.state.product}")
print(f"Has color: {device.state.has_color}")
```

## Dependencies

### lifx-emulator (Standalone)

- **lifx-emulator-core**: Core emulation library
- **fastapi**: HTTP API framework
- **uvicorn**: ASGI server
- **cyclopts**: CLI framework
- **rich**: Terminal formatting

### lifx-emulator-core (Library)

- **pyyaml**: For product registry and configuration

### Development Dependencies

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

If you need to manage Python versions, we recommend using uv, which automatically handles Python version management:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# uv will automatically manage Python for you
uv tool install lifx-emulator  # For CLI tool
# or
uv add lifx-emulator-core  # As a dependency of your project
```

### Import Errors

If you see import errors, ensure the package is installed:

```bash
pip show lifx-emulator-core
```

If not found, reinstall:

```bash
pip install --force-reinstall lifx-emulator-core
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Create your first emulated device
- [CLI Usage](../cli/cli-reference.md) - Learn all CLI commands
- [Device Types](../guide/device-types.md) - Explore supported devices
