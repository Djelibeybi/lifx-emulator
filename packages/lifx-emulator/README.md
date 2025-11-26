# lifx-emulator

Standalone LIFX device emulator with CLI and HTTP management API.

This package provides a ready-to-run emulator for testing LIFX LAN protocol libraries. It includes a command-line interface and an optional HTTP API for runtime device management.

## Installation

```bash
pip install lifx-emulator
```

## Quick Start

```bash
# Start with default configuration (1 color light)
lifx-emulator

# Create multiple device types
lifx-emulator --color 2 --multizone 1 --tile 1

# Enable HTTP management API
lifx-emulator --api

# List available LIFX products
lifx-emulator list-products

# Create devices by product ID
lifx-emulator --product 27 --product 38 --product 55
```

## Features

- Command-line interface for quick emulator setup
- HTTP management API with web dashboard
- Real-time device monitoring and management
- Support for all LIFX device types (color, multizone, tile, infrared, HEV, switch)
- Persistent device state across restarts
- Testing scenarios for protocol edge cases

## HTTP Management API

Enable with `--api` to get:

- **Web Dashboard**: `http://localhost:8080` - Real-time monitoring UI
- **REST API**: Device management, statistics, and scenario control
- **OpenAPI Docs**: `http://localhost:8080/docs` - Interactive API documentation

```bash
# Start with API server
lifx-emulator --color 2 --api --api-port 9090

# Add a device via API
curl -X POST http://localhost:9090/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 27}'
```

## Documentation

Full documentation is available at: **https://djelibeybi.github.io/lifx-emulator**

- [Installation Guide](https://djelibeybi.github.io/lifx-emulator/getting-started/installation/)
- [CLI Reference](https://djelibeybi.github.io/lifx-emulator/cli/cli-reference/)
- [Web Interface](https://djelibeybi.github.io/lifx-emulator/cli/web-interface/)
- [REST API](https://djelibeybi.github.io/lifx-emulator/cli/device-management-api/)

## Related Packages

- **[lifx-emulator-core](https://pypi.org/project/lifx-emulator-core/)**: Core library for embedding the emulator in your own projects

## License

[UPL-1.0](https://opensource.org/licenses/UPL)
