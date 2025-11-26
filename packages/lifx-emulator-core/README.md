# lifx-emulator-core

Core Python library for emulating LIFX devices using the LAN protocol.

This package provides the embeddable library for creating virtual LIFX devices in your own projects. It implements the binary UDP protocol from the [LIFX LAN Protocol](https://lan.developer.lifx.com) specification.

## Installation

```bash
pip install lifx-emulator-core
```

## Quick Start

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository

async def main():
    # Create devices
    devices = [
        create_color_light(serial="d073d5000001"),
        create_color_light(serial="d073d5000002"),
    ]

    # Create repository and manager
    repository = DeviceRepository()
    manager = DeviceManager(repository)

    # Start the emulator server
    server = EmulatedLifxServer(
        devices=devices,
        device_manager=manager,
        bind_address="127.0.0.1",
        port=56700,
    )

    await server.start()
    print("LIFX Emulator running on 127.0.0.1:56700")

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    finally:
        await server.stop()

asyncio.run(main())
```

## Features

- Emulate color lights, multizone strips, tiles, infrared, HEV, and switch devices
- Full LIFX LAN protocol implementation
- Persistent device state storage
- Testing scenarios for simulating edge cases
- Product registry with 137+ official LIFX products

## Documentation

Full documentation is available at: **https://djelibeybi.github.io/lifx-emulator**

- [Installation Guide](https://djelibeybi.github.io/lifx-emulator/getting-started/installation/)
- [Quick Start](https://djelibeybi.github.io/lifx-emulator/getting-started/quickstart/)
- [API Reference](https://djelibeybi.github.io/lifx-emulator/library/)
- [Architecture](https://djelibeybi.github.io/lifx-emulator/architecture/)

## Related Packages

- **[lifx-emulator](https://pypi.org/project/lifx-emulator/)**: Standalone CLI tool and HTTP management API built on this library

## License

[UPL-1.0](https://opensource.org/licenses/UPL)
