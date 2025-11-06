# LIFX Emulator

A comprehensive LIFX device emulator for testing LIFX LAN protocol libraries.

## Overview

LIFX Emulator implements the complete binary UDP protocol documented at [lan.developer.lifx.com](https://lan.developer.lifx.com), providing virtual LIFX devices for testing without physical hardware.

## Key Features

- **Complete Protocol Support**: Handles all packet types from the LIFX LAN protocol
- **Multiple Device Types**: Emulate color lights, infrared, HEV, multizone strips, and matrix tiles
- **Product Registry**: Built from official LIFX products.json with 40+ product definitions
- **Testing Scenarios**: Built-in support for packet loss, delays, malformed responses, and more
- **Easy Integration**: Simple Python API and CLI for both standalone and embedded use

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

## Next Steps

- [Installation Guide](getting-started/installation.md) - Get started with installation
- [Quick Start](getting-started/quickstart.md) - Create your first emulated device
- [CLI Usage](getting-started/cli.md) - Learn CLI commands and options
- [Device Types](guide/device-types.md) - Explore all supported devices
- [API Reference](api/server.md) - Detailed API documentation

## Project Links

- [GitHub Repository](https://github.com/Djelibeybi/lifx-emulator)
- [Issue Tracker](https://github.com/Djelibeybi/lifx-emulator/issues)
- [LIFX LAN Protocol Documentation](https://lan.developer.lifx.com)
