# LIFX Emulator

> A comprehensive LIFX device emulator for testing LIFX LAN protocol libraries

[![Codecov](https://codecov.io/gh/Djelibeybi/lifx-emulator/branch/main/graph/badge.svg)](https://codecov.io/gh/Djelibeybi/lifx-emulator)
[![CI](https://github.com/Djelibeybi/lifx-emulator/actions/workflows/ci.yml/badge.svg)](https://github.com/Djelibeybi/lifx-emulator/actions/workflows/ci.yml)
[![Docs](https://github.com/Djelibeybi/lifx-emulator/workflows/Documentation/badge.svg)](https://Djelibeybi.github.io/lifx-emulator/)
[![License](https://img.shields.io/badge/License-UPL--1.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](https://www.python.org)

## Overview

LIFX Emulator implements the complete binary UDP protocol from [lan.developer.lifx.com](https://lan.developer.lifx.com) by providing virtual LIFX devices for testing without physical hardware. The emulator includes a basic web interface and OpenAPI-compliant REST API for device and scenario management at runtime.

## Packages

This monorepo contains two packages:

| Package | PyPI | Description |
|---------|------|-------------|
| **lifx-emulator** | [![PyPI](https://img.shields.io/pypi/v/lifx-emulator)](https://pypi.org/project/lifx-emulator/) | Standalone CLI + HTTP management API |
| **lifx-emulator-core** | [![PyPI](https://img.shields.io/pypi/v/lifx-emulator-core)](https://pypi.org/project/lifx-emulator-core/) | Core library for embedding in your projects |

## Installation

### For most users: Standalone emulator

```bash
uv tool install lifx-emulator
```

This installs the `lifx-emulator` command globally, making it immediately available without needing to activate a virtual environment.

### For developers: Embeddable library

```bash
uv add --dev lifx-emulator-core
```

Use this if you're building a LIFX library or application and want to add the emulator as a development dependency for your test suite.

## Quick Start

### Using the CLI

```bash
# Start with a config file (auto-detected in current directory)
lifx-emulator

# Create specific device types via CLI flags
lifx-emulator --color 2 --multizone 1 --tile 1

# Enable the HTTP management API
lifx-emulator --color 1 --api

# List available LIFX products
lifx-emulator list-products
```

### Using the library

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, DeviceManager, DeviceRepository
from lifx_emulator.factories import create_color_light

async def main():
    # Create devices
    devices = [create_color_light(serial="d073d5000001")]

    # Set up the server
    repository = DeviceRepository()
    manager = DeviceManager(repository)
    server = EmulatedLifxServer(devices, manager, "127.0.0.1", 56700)

    # Run the emulator
    await server.start()
    try:
        await asyncio.sleep(3600)  # Run for an hour
    finally:
        await server.stop()

asyncio.run(main())
```

## Features

- **Complete Protocol Support**: 44+ packet types from the LIFX LAN protocol
- **Multiple Device Types**: Color lights, infrared, HEV, multizone strips, matrix tiles, switches
- **REST API and Web Interface**: Monitor and manage your virtual devices during testing
- **Testing Scenarios**: Built-in support for packet loss, delays, malformed responses
- **Persistent Storage**: Optional device state persistence across restarts
- **Product Registry**: 137+ real LIFX products with accurate specifications

## Documentation

- **[Installation Guide](https://djelibeybi.github.io/lifx-emulator/getting-started/installation/)** - Get started
- **[Quick Start](https://djelibeybi.github.io/lifx-emulator/getting-started/quickstart/)** - Your first emulated device
- **[User Guide](https://djelibeybi.github.io/lifx-emulator/guide/overview/)** - Product specifications and testing scenarios
- **[Advanced Topics](https://djelibeybi.github.io/lifx-emulator/advanced/device-management-api/)** - REST API and persistent storage
- **[CLI Reference](https://djelibeybi.github.io/lifx-emulator/getting-started/cli/)** - All CLI options
- **[Device Types](https://djelibeybi.github.io/lifx-emulator/guide/device-types/)** - Supported devices
- **[API Reference](https://djelibeybi.github.io/lifx-emulator/api/)** - Complete API docs
- **[Architecture](https://djelibeybi.github.io/lifx-emulator/architecture/overview/)** - How it works

## Use Cases

- **Library Testing**: Test your LIFX library without physical devices
- **CI/CD Integration**: Run automated tests in pipelines
- **Protocol Development**: Experiment with LIFX protocol features
- **Error Simulation**: Test error handling with configurable scenarios
- **Performance Testing**: Test concurrent device handling

## Development

```bash
# Clone repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install dependencies
uv sync

# Run tests for both packages
uv run pytest

# Run linter
uv run ruff check .

# Build docs
uv run mkdocs serve
```

## License

[UPL-1.0](LICENSE)

## Links

- **Documentation**: https://djelibeybi.github.io/lifx-emulator
- **GitHub**: https://github.com/Djelibeybi/lifx-emulator
- **PyPI (standalone)**: https://pypi.org/project/lifx-emulator/
- **PyPI (library)**: https://pypi.org/project/lifx-emulator-core/
- **LIFX Protocol**: https://lan.developer.lifx.com
