# LIFX Emulator

**Test your LIFX LAN protocol libraries without physical devices.**

## What is LIFX Emulator?

LIFX Emulator is a Python library and CLI tool that creates virtual LIFX devices for testing. It implements the complete binary UDP protocol from [lan.developer.lifx.com](https://lan.developer.lifx.com), allowing you to:

- Test LIFX libraries without buying hardware
- Run automated tests in CI/CD pipelines
- Simulate error conditions and edge cases
- Develop protocol features safely

## Why Use an Emulator?

- **💰 Cost-effective**: No need to purchase multiple physical LIFX devices
- **⚡ Fast**: Instant device creation, no network delays
- **🎯 Reliable**: Consistent behavior for repeatable tests
- **🧪 Comprehensive**: Test scenarios impossible with real devices (packet loss, malformed data, etc.)
- **🔄 Flexible**: Create/destroy devices on demand

## Key Features

- **Complete Protocol Support**: All packet types from the LIFX LAN protocol
- **Multiple Device Types**: Color lights, infrared, HEV, multizone strips, and matrix tiles
- **Product Registry**: 137 official LIFX product definitions
- **Testing Scenarios**: Configurable packet loss, delays, malformed responses, and more
- **Easy Integration**: Simple Python API and CLI tool

## Quick Example

=== "Python API"

    ```python
    import asyncio
    from lifx_emulator import EmulatedLifxServer, create_color_light

    async def main():
        # Create a color light device
        device = create_color_light("d073d5000001")

        # Start server on port 56700
        server = EmulatedLifxServer([device], "127.0.0.1", 56700)
        await server.start()

        # Your test code here
        await asyncio.Event().wait()

    asyncio.run(main())
    ```

=== "CLI"

    ```bash
    # Start with default configuration (1 color light)
    lifx-emulator

    # Create multiple device types
    lifx-emulator --color 2 --multizone 1 --tile 1 --verbose

    # Use specific products from registry
    lifx-emulator --product 27 --product 32 --product 55
    ```

## Supported Device Types

| Device Type | Example Products | Capabilities |
|------------|------------------|--------------|
| Color Lights | LIFX A19, LIFX BR30 | Full RGB color control |
| Color Temperature | LIFX Mini White to Warm | Variable white temperature |
| Infrared | LIFX A19 Night Vision | IR brightness control |
| HEV | LIFX Clean | HEV cleaning cycle |
| Multizone | LIFX Z, LIFX Beam | Linear zones (up to 82) |
| Matrix | LIFX Tile, LIFX Candle | 2D pixel arrays |

## Use Cases

- **Library Testing**: Test your LIFX library without physical devices
- **CI/CD Integration**: Run automated tests in pipelines
- **Protocol Development**: Experiment with LIFX protocol features
- **Error Simulation**: Test error handling with configurable scenarios
- **Performance Testing**: Test concurrent device handling

## Installation

**Recommended:** Using [uv](https://astral.sh/uv) (automatically manages Python for you):

```bash
uv tool install lifx-emulator
```

**Alternative:** Using pip (requires Python 3.11+):

```bash
pip install lifx-emulator
```

## Getting Started

New to LIFX Emulator? Start here:

1. **[Installation](getting-started/installation.md)** - Install the package
2. **[Quick Start](getting-started/quickstart.md)** - Create your first device in 5 minutes
3. **[CLI Usage](getting-started/cli.md)** - Command-line reference

## Learn More

### 📖 User Guides

Understand how to use the emulator effectively:

- **[Overview](guide/index.md)** - High-level concepts and use cases
- **[Device Types](guide/device-types.md)** - All supported LIFX devices
- **[Web Interface](guide/web-interface.md)** - Visual monitoring and management
- **[Integration Testing](guide/integration-testing.md)** - Using in your test suites
- **[Testing Scenarios](guide/testing-scenarios.md)** - Simulate errors and edge cases
- **[Best Practices](guide/best-practices.md)** - Tips for effective testing

### 🎓 Tutorials

Step-by-step tutorials from beginner to advanced:

- **[First Device](tutorials/01-first-device.md)** - Your first emulated device
- **[Basic Usage](tutorials/02-basic.md)** - Multiple devices and basic testing
- **[Integration Testing](tutorials/03-integration.md)** - pytest integration
- **[Advanced Scenarios](tutorials/04-advanced-scenarios.md)** - Error injection and complex tests
- **[CI/CD Integration](tutorials/05-cicd.md)** - Automated testing pipelines

### 🏗️ Architecture

Understanding how it works:

- **[Architecture Overview](architecture/overview.md)** - High-level system design
- **[Packet Flow](architecture/packet-flow.md)** - How packets are processed
- **[Device State](architecture/device-state.md)** - State management
- **[Protocol Details](architecture/protocol.md)** - Binary protocol implementation

### 📚 API Reference

Detailed API documentation:

- **[Factories](api/factories.md)** - Creating devices
- **[Server](api/server.md)** - Server configuration
- **[Device](api/device.md)** - Device API
- **[Products](api/products.md)** - Product registry
- **[Protocol](api/protocol.md)** - Protocol packets
- **[Storage](api/storage.md)** - Persistent state

### 🚀 Advanced Features

Power-user features:

- **[Persistent Storage](advanced/storage.md)** - Save device state across restarts
- **[Device Management API](advanced/device-management-api.md)** - Runtime device management
- **[Scenarios](advanced/scenarios.md)** - Comprehensive testing scenarios
- **[Scenario API](advanced/scenario-api.md)** - Scenario REST API reference

### 📋 Reference

- **[Glossary](reference/glossary.md)** - Terms and definitions
- **[Troubleshooting](reference/troubleshooting.md)** - Common issues and solutions
- **[FAQ](faq.md)** - Frequently asked questions
- **[Changelog](changelog.md)** - Version history

## Project Links

- [GitHub Repository](https://github.com/Djelibeybi/lifx-emulator)
- [Issue Tracker](https://github.com/Djelibeybi/lifx-emulator/issues)
- [LIFX LAN Protocol Documentation](https://lan.developer.lifx.com)
