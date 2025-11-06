# LIFX Emulator

> A comprehensive LIFX device emulator for testing LIFX LAN protocol libraries

[![Codecov](https://codecov.io/gh/Djelibeybi/lifx-emulator/branch/main/graph/badge.svg)](https://codecov.io/gh/Djelibeybi/lifx-emulator)
[![CI](https://github.com/Djelibeybi/lifx-emulator/actions/workflows/ci.yml/badge.svg)](https://github.com/Djelibeybi/lifx-emulator/actions/workflows/ci.yml)
[![Docs](https://github.com/Djelibeybi/lifx-emulator/workflows/Documentation/badge.svg)](https://Djelibeybi.github.io/lifx-emulator/)

[![GitHub](https://img.shields.io/github/v/release/Djelibeybi/lifx-emulator)](https://github.com/Djelibeybi/lifx-emulator/releases)
[![PyPI](https://img.shields.io/pypi/v/lifx-emulator)](https://pypi.org/project/lifx-emulator/)
[![License](https://img.shields.io/badge/License-UPL--1.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](https://www.python.org)
## Overview

LIFX Emulator implements the complete binary UDP protocol from [lan.developer.lifx.com](https://lan.developer.lifx.com) by providing virtual LIFX devices for testing without physical hardware. The emulator includes a basic web interface and OpenAPI-compliant REST API for device and scenario management at runtime.

## Features

- **Complete Protocol Support**: 44+ packet types from the LIFX LAN protocol
- **Multiple Device Types**: Color lights, infrared, HEV, multizone strips, matrix tiles
- **REST API and Web Interface**:  Monitor and manage your virtual devices during testing
- **Testing Scenarios**: Built-in support for packet loss, delays, malformed responses
- **Easy Integration**: Simple Python API and comprehensive CLI


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


## License

[UPL-1.0](LICENSE)

## Links

- **Documentation**: https://djelibeybi.github.io/lifx-emulator
- **GitHub**: https://github.com/Djelibeybi/lifx-emulator
- **PyPI**: https://pypi.org/project/lifx-emulator/
- **LIFX Protocol**: https://lan.developer.lifx.com
