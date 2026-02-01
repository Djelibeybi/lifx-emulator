# LIFX Emulator

**Test your LIFX LAN protocol libraries without physical devices.**

## Overview

LIFX Emulator is a Python project for testing LIFX LAN protocol client libraries. It implements the complete binary UDP protocol from [lan.developer.lifx.com](https://lan.developer.lifx.com).

## Packages

This project provides two packages for different use cases:

| Package | PyPI Name | Import Name | Description |
|---------|-----------|-------------|-------------|
| **Standalone** | `lifx-emulator` | `lifx_emulator_app` | CLI tool + HTTP management API |
| **Core Library** | `lifx-emulator-core` | `lifx_emulator` | Embeddable Python library |

### Which Package Do I Need?

**Install `lifx-emulator` if you want:**

- A ready-to-run CLI tool
- HTTP REST API for device management
- Web dashboard for monitoring
- Quick testing without writing code

```bash
pip install lifx-emulator
lifx-emulator --color 1 --api --verbose
```

**Install `lifx-emulator-core` if you want:**

- To embed emulation in your own Python application
- Programmatic control for pytest or other test frameworks
- To build custom tooling around LIFX emulation

```bash
pip install lifx-emulator-core
```

```python
from lifx_emulator import create_color_light, EmulatedLifxServer
```

## Quick Start

=== "CLI (lifx-emulator)"

    ```bash
    # Install
    pip install lifx-emulator

    # Start with a config file (auto-detected in current directory)
    lifx-emulator

    # Create devices via CLI flags
    lifx-emulator --color 2 --multizone 1 --api --verbose
    ```

=== "Python Library (lifx-emulator-core)"

    ```python
    import asyncio
    from lifx_emulator import EmulatedLifxServer
    from lifx_emulator.factories import create_color_light
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.devices import DeviceManager

    async def main():
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())

        async with EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", 56700
        ) as server:
            print(f"Emulating: {device.state.label}")
            await asyncio.Event().wait()

    asyncio.run(main())
    ```

## Key Features

- **Complete Protocol Support**: All packet types from the LIFX LAN protocol
- **Multiple Device Types**: Color lights, infrared, HEV, multizone strips, and matrix tiles
- **Product Registry**: 137+ official LIFX product definitions
- **Testing Scenarios**: Configurable packet loss, delays, malformed responses
- **HTTP Management API**: OpenAPI 3.1.0 compliant REST API (standalone package)
- **Web Dashboard**: Real-time monitoring interface (standalone package)
- **Persistent Storage**: Save device state across sessions

## Documentation

### Getting Started

- **[Installation](getting-started/installation.md)** - Install either package
- **[Quick Start](getting-started/quickstart.md)** - First steps with CLI or Python API

### lifx-emulator (Standalone CLI)

- **[Overview](cli/index.md)** - CLI tool and HTTP management server
- **[CLI Reference](cli/cli-reference.md)** - All CLI commands and options
- **[Web Interface](cli/web-interface.md)** - Browser-based monitoring dashboard
- **[Device Management API](cli/device-management-api.md)** - REST API for devices
- **[Scenario API](cli/scenario-api.md)** - REST API for test scenarios
- **[Persistent Storage](cli/storage.md)** - Save state across restarts
- **[Scenarios Guide](cli/scenarios.md)** - Comprehensive scenario configuration

### lifx-emulator-core (Python Library)

- **[Python Library Reference](library/index.md)** - Complete library documentation
- **[Factory Functions](library/factories.md)** - Device creation functions
- **[Server](library/server.md)** - EmulatedLifxServer configuration
- **[Device](library/device.md)** - EmulatedLifxDevice and DeviceState
- **[Protocol Types](library/protocol.md)** - LightHsbk and other types
- **[Storage](library/storage.md)** - Persistent state management
- **[Product Registry](library/products.md)** - Product database
- **[Architecture](architecture/index.md)** - System design and internals

### Guides (Shared)

- **[Device Types](guide/device-types.md)** - Supported LIFX devices
- **[Products & Specs](guide/products-and-specs.md)** - Product registry usage
- **[Testing Scenarios](guide/testing-scenarios.md)** - Error simulation
- **[Framebuffers](guide/framebuffers.md)** - Matrix device framebuffer support
- **[Integration Testing](guide/integration-testing.md)** - Using in test suites
- **[Best Practices](guide/best-practices.md)** - Tips for effective testing

### Tutorials

- **[First Device](tutorials/01-first-device.md)** - Your first emulated device
- **[Basic Usage](tutorials/02-basic.md)** - Multiple devices and basic testing
- **[Integration Testing](tutorials/03-integration.md)** - pytest integration
- **[Advanced Scenarios](tutorials/04-advanced-scenarios.md)** - Error injection
- **[CI/CD Integration](tutorials/05-cicd.md)** - Automated testing pipelines

### Reference

- **[FAQ](faq.md)** - Frequently asked questions
- **[Troubleshooting](reference/troubleshooting.md)** - Common issues and solutions
- **[Glossary](reference/glossary.md)** - Terms and definitions
- **[Changelog](changelogs/index.md)** - Version history

## Supported Device Types

| Device Type | Example Products | Capabilities |
|------------|------------------|--------------|
| Color Lights | LIFX A19, LIFX BR30 | Full RGB color control |
| Color Temperature | LIFX Mini White to Warm | Variable white temperature |
| Infrared | LIFX A19 Night Vision | IR brightness control |
| HEV | LIFX Clean | HEV cleaning cycle |
| Multizone | LIFX Z, LIFX Beam | Linear zones (up to 82+) |
| Matrix | LIFX Tile, LIFX Candle | 2D zone arrays |
| Switch | LIFX Switch | Relay-based switches |

## Use Cases

- **Library Testing**: Test your LIFX library without physical devices
- **CI/CD Integration**: Run automated tests in pipelines
- **Protocol Development**: Experiment with LIFX protocol features
- **Error Simulation**: Test error handling with configurable scenarios
- **Performance Testing**: Test concurrent device handling

## Requirements

- Python 3.11 or higher

## Project Links

- [GitHub Repository](https://github.com/Djelibeybi/lifx-emulator)
- [PyPI: lifx-emulator](https://pypi.org/project/lifx-emulator/)
- [PyPI: lifx-emulator-core](https://pypi.org/project/lifx-emulator-core/)
- [LIFX LAN Protocol Documentation](https://lan.developer.lifx.com)
