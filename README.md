# LIFX Emulator

> A comprehensive LIFX device emulator for testing LIFX LAN protocol libraries

[![License](https://img.shields.io/badge/License-UPL--1.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)

## Overview

LIFX Emulator implements the complete binary UDP protocol from [lan.developer.lifx.com](https://lan.developer.lifx.com), providing virtual LIFX devices for testing without physical hardware.

## Features

- **Complete Protocol Support**: 44+ packet types from the LIFX LAN protocol
- **Multiple Device Types**: Color lights, infrared, HEV, multizone strips, matrix tiles
- **Product Registry**: 40+ official LIFX product definitions with accurate defaults
- **Testing Scenarios**: Built-in support for packet loss, delays, malformed responses
- **Easy Integration**: Simple Python API and comprehensive CLI
- **Zero Dependencies**: Pure Python with only PyYAML for configuration

## Quick Start

### Installation

```bash
pip install lifx-emulator
```

### CLI Usage

```bash
# Start with default configuration (1 color light)
lifx-emulator

# Create multiple device types with verbose logging
lifx-emulator --color 2 --multizone 1 --tile 1 --verbose

# Use specific products from registry
lifx-emulator --product 27 --product 32 --product 55

# List all available products
lifx-emulator list-products
```

### Python API

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    # Create emulated device
    device = create_color_light("d073d5000001")

    # Start server
    async with EmulatedLifxServer([device], "127.0.0.1", 56700) as server:
        print(f"Server running with device: {device.state.label}")
        await asyncio.Event().wait()

asyncio.run(main())
```

### Integration Testing

```python
import pytest
from lifx_emulator import EmulatedLifxServer, create_color_light
from your_lifx_library import LifxClient

@pytest.mark.asyncio
async def test_discover_devices():
    # Create emulated device
    device = create_color_light("d073d5000001")

    # Start emulator
    async with EmulatedLifxServer([device], "127.0.0.1", 56700):
        # Test your library
        client = LifxClient()
        await client.discover(port=56700)

        assert len(client.devices) == 1
        assert client.devices[0].mac == "d073d5000001"
```

## Supported Device Types

| Device Type | Factory Function | Example Product |
|------------|------------------|-----------------|
| Color Lights | `create_color_light()` | LIFX A19 |
| Color Temperature | `create_color_temperature_light()` | LIFX Mini White to Warm |
| Infrared | `create_infrared_light()` | LIFX A19 Night Vision |
| HEV | `create_hev_light()` | LIFX Clean |
| Multizone | `create_multizone_light()` | LIFX Z, LIFX Beam |
| Matrix Tiles | `create_tile_device()` | LIFX Tile |

[See all 40+ supported products →](https://lifx-emulator.readthedocs.io/en/latest/guide/device-types/)

## Documentation

- **[Installation Guide](https://lifx-emulator.readthedocs.io/en/latest/getting-started/installation/)** - Get started
- **[Quick Start](https://lifx-emulator.readthedocs.io/en/latest/getting-started/quickstart/)** - Your first emulated device
- **[CLI Reference](https://lifx-emulator.readthedocs.io/en/latest/getting-started/cli/)** - All CLI options
- **[Device Types](https://lifx-emulator.readthedocs.io/en/latest/guide/device-types/)** - Supported devices
- **[API Reference](https://lifx-emulator.readthedocs.io/en/latest/api/)** - Complete API docs
- **[Architecture](https://lifx-emulator.readthedocs.io/en/latest/architecture/overview/)** - How it works

## CLI Examples

### Basic Usage

```bash
# Single color light on default port 56700
lifx-emulator

# Multiple devices with verbose logging
lifx-emulator --color 2 --multizone 1 --tile 1 --verbose
```

### Advanced Usage

```bash
# Extended multizone (LIFX Beam) with custom zone count
lifx-emulator --multizone 1 --multizone-extended --multizone-zones 60

# Specific products by ID
lifx-emulator --product 27 --product 32 --product 55

# Custom port and localhost only
lifx-emulator --bind 127.0.0.1 --port 56701

# Filter products list
lifx-emulator list-products --filter-type multizone
```

## Python API Examples

### Multiple Device Types

```python
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)

devices = [
    create_color_light("d073d5000001"),
    create_multizone_light("d073d8000001", zone_count=16),
    create_tile_device("d073d9000001", tile_count=5),
]

async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # All devices are discoverable and controllable
    print(f"Emulating {len(devices)} devices")
    await asyncio.Event().wait()
```

### Testing Scenarios

```python
# Configure error scenarios for testing
device = create_color_light("d073d5000001")
device.scenarios = {
    'drop_packets': [101],           # Drop LightGet packets
    'response_delays': {102: 0.5},   # Delay SetColor by 500ms
    'malformed_packets': [107],      # Truncate StateLight
}

async with EmulatedLifxServer([device], "127.0.0.1", 56700) as server:
    # Test your library's error handling
    pass
```

## Use Cases

- **Library Testing**: Test your LIFX library without physical devices
- **CI/CD Integration**: Run automated tests in pipelines
- **Protocol Development**: Experiment with LIFX protocol features
- **Error Simulation**: Test error handling with configurable scenarios
- **Performance Testing**: Test concurrent device handling

## Requirements

- Python 3.13+
- PyYAML (automatically installed)

## Performance

The emulator includes comprehensive performance optimization with **51% average throughput improvement**:

- Complete benchmarking and profiling suite
- Detailed optimization analysis and recommendations
- Before/after performance comparison

**Key Results:**
- **Packet Processing**: +51% (35K → 53K pkt/s)
- **Serialization**: +77% (27K → 48K pkt/s)
- **Latency**: -35% to -44% reduction

See the [Performance Documentation](docs/performance/index.md) for details.

### Run Performance Benchmarks

```bash
uv run python tools/performance/benchmark.py
uv run python tools/performance/profiler.py
```

## Development

```bash
# Clone repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Build docs
uv run mkdocs serve
```

### Documentation Tools

The emulator includes automated tools for documentation generation, validation, and quality checking:

#### 1. API Reference Generator (`generate_api_reference.py`)

Auto-generates API reference documentation from Python source code with docstrings, type hints, and inheritance diagrams.

```bash
# Generate API reference for a module
python tools/docs/generate_api_reference.py src/lifx_emulator/device.py > docs/api/device.md

# With output file
python tools/docs/generate_api_reference.py src/lifx_emulator/storage.py --output docs/api/storage.md
```

#### 2. Diagram Generator (`generate_diagrams.py`)

Auto-generates architecture diagrams from code analysis (component, packet flow, state machine, handler flow).

```bash
# Generate all diagrams
python tools/docs/generate_diagrams.py --type all --output docs/architecture/diagrams/

# Generate specific diagram type
python tools/docs/generate_diagrams.py --type component
python tools/docs/generate_diagrams.py --type packet-flow
```

#### 3. Example Validator (`validate_examples.py`)

Validates that code examples in documentation actually work by extracting and compiling Python code blocks.

```bash
# Validate all examples in docs/
python tools/docs/validate_examples.py docs/

# Validate with verbose output
python tools/docs/validate_examples.py docs/tutorials/ --verbose
```

#### 4. Coverage Reporter (`coverage_report.py`)

Tracks documentation coverage across the codebase and enforces minimum coverage thresholds.

```bash
# Generate coverage report
python tools/docs/coverage_report.py

# Require minimum coverage
python tools/docs/coverage_report.py --min-coverage 80

# Generate HTML report
python tools/docs/coverage_report.py --html --output coverage.html
```

#### 5. Terminology Checker (`check_terminology.py`)

Validates consistent terminology usage across documentation against defined glossary.

```bash
# Check terminology
python tools/docs/check_terminology.py docs/

# Auto-fix violations
python tools/docs/check_terminology.py docs/ --fix
```

#### Documentation Workflow

When writing documentation:

1. **Write content** with code examples
2. **Run validation locally:**
   ```bash
   # Check terminology
   python tools/docs/check_terminology.py docs/ --fix

   # Validate examples
   python tools/docs/validate_examples.py docs/ --verbose

   # Check coverage
   python tools/docs/coverage_report.py
   ```

3. **Auto-generate API reference:**
   ```bash
   python tools/docs/generate_api_reference.py src/lifx_emulator/device.py --output docs/api/device.md
   ```

4. **Generate diagrams:**
   ```bash
   python tools/docs/generate_diagrams.py --type all --output docs/architecture/diagrams/
   ```

5. **Commit changes** - CI will validate everything

The `.github/workflows/docs.yml` workflow runs all validation tools on pull requests and pushes to main.

See [Documentation Tools](docs/development/documentation-tools.md) for detailed documentation tool usage and troubleshooting.

## Product Registry

The emulator includes an auto-generated registry of all official LIFX products with accurate defaults:

```python
from lifx_emulator.products.registry import get_product, get_registry

# Get specific product
product = get_product(27)  # LIFX A19
print(f"{product.name}: {product.pid}")
print(f"Capabilities: color={product.has_color}, multizone={product.has_multizone}")

# List all products
registry = get_registry()
for pid, product in registry.products.items():
    print(f"PID {pid}: {product.name}")
```

## Testing Scenarios

Configure devices to simulate real-world issues:

```python
device.scenarios = {
    # Packet dropping (simulate packet loss)
    'drop_packets': [101, 102],

    # Response delays (simulate latency)
    'response_delays': {102: 0.5, 107: 1.0},

    # Malformed packets (test error handling)
    'malformed_packets': [107],

    # Invalid field values (test validation)
    'invalid_field_values': {22: True},

    # Partial responses (test timeout handling)
    'partial_responses': [506],
}
```

## Architecture

```
┌─────────────────┐
│  LIFX Client    │
│    Library      │
└────────┬────────┘
         │ UDP Packets
         ▼
┌─────────────────┐
│ EmulatedLifx    │
│     Server      │
└────────┬────────┘
         │ Route by MAC
         ▼
┌─────────────────┐     ┌──────────────┐
│ EmulatedLifx    │────▶│ DeviceState  │
│     Device      │     │  (Stateful)  │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│  Protocol Layer │
│  (44+ packets)  │
└─────────────────┘
```

[Learn more about the architecture →](https://lifx-emulator.readthedocs.io/en/latest/architecture/overview/)

## Contributing

Contributions are welcome! Please see our [Contributing Guide](https://lifx-emulator.readthedocs.io/en/latest/development/contributing/) for details.

## License

[UPL-1.0](LICENSE)

## Links

- **Documentation**: https://lifx-emulator.readthedocs.io
- **GitHub**: https://github.com/Djelibeybi/lifx-emulator
- **PyPI**: https://pypi.org/project/lifx-emulator/
- **LIFX Protocol**: https://lan.developer.lifx.com
