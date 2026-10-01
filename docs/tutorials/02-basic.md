# Basic Examples

This page demonstrates basic usage patterns for the LIFX Emulator. These examples cover the most common use cases for getting started.

Every example creates its server with a `DeviceManager`, which `EmulatedLifxServer` requires as its second argument. Give each server its own `DeviceManager(DeviceRepository())`; don't share one between servers.

## Single Device Creation

The simplest way to start is with a single colour light:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create a single LIFX colour light (LIFX Color, product 91)
    device = create_color_light("d073d5000001")

    # Create and start the server
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(f"Emulator running with device {device.state.serial}")
        print(f"Label: {device.state.label}")
        print(f"Product: {device.state.product}")

        # Keep server running
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Emulator running with device d073d5000001
Label: LIFX Color 800lm 000001
Product: 91
```

## Using Context Manager (Recommended)

The context manager automatically handles server startup and shutdown:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    # Server starts automatically on entry, stops on exit
    async with server:
        print("Server is running")
        await asyncio.sleep(60)

    print("Server has stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
```

If you can't use `async with`, call `await server.start()` and `await server.stop()` yourself, with `stop()` in a `finally` block.

## Multiple Devices on Same Server

Run multiple devices simultaneously:

```python
import asyncio

from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_color_temperature_light,
    create_infrared_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create different device types
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_color_temperature_light("d073d5000003"),
        create_infrared_light("d073d5000004"),
    ]

    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(f"Running {len(devices)} devices:")
        for device in devices:
            print(
                f"  - {device.state.serial}: {device.state.label} "
                f"(product {device.state.product})"
            )

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Running 4 devices:
  - d073d5000001: LIFX Color 800lm 000001 (product 91)
  - d073d5000002: LIFX Color 800lm 000002 (product 91)
  - d073d5000003: LIFX Mini DD 000003 (product 50)
  - d073d5000004: LIFX+ (A19) 000004 (product 29)
```

## Query Device State

Access device state at any time:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        # Access current device state
        state = device.state

        print(f"Serial: {state.serial}")
        print(f"Label: {state.label}")
        print(f"Power: {state.power_level}")
        print(
            f"Colour: H={state.color.hue}, S={state.color.saturation}, "
            f"B={state.color.brightness}, K={state.color.kelvin}"
        )
        print("Capabilities:")
        print(f"  - Color: {state.has_color}")
        print(f"  - Infrared: {state.has_infrared}")
        print(f"  - Multizone: {state.has_multizone}")
        print(f"  - Matrix: {state.has_matrix}")

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Serial: d073d5000001
Label: LIFX Color 800lm 000001
Power: 65535
Colour: H=21845, S=65535, B=32768, K=3500
Capabilities:
  - Color: True
  - Infrared: False
  - Multizone: False
  - Matrix: False
```

## Custom Port and Bind Address

Configure the server's network settings:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    device = create_color_light("d073d5000001")

    # Bind to specific IP and port
    # Use "0.0.0.0" to listen on all interfaces
    server = EmulatedLifxServer(
        devices=[device],
        device_manager=DeviceManager(DeviceRepository()),
        bind_address="127.0.0.1",
        port=56701,  # Non-standard port
    )

    async with server:
        print("Server listening on 127.0.0.1:56701")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

Pass `port=0` to let the operating system choose a free port. `server.port` stays `0`; read the port that was actually bound from `server.ipv4_endpoint[1]` (or `device.state.port`) once the server has started.

## Setting Initial Device State

Customise device state before starting the server:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


async def main():
    device = create_color_light("d073d5000001")

    # Configure device state before starting
    device.state.label = "Living Room Light"
    device.state.power_level = 65535  # On
    device.state.color = LightHsbk(
        hue=21845,  # 120° (green)
        saturation=65535,  # Fully saturated
        brightness=32768,  # 50% brightness
        kelvin=3500,
    )

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print("Device ready with custom state:")
        print(f"  Label: {device.state.label}")
        print(f"  Power: {'On' if device.state.power_level else 'Off'}")
        print("  Colour: Green at 50% brightness")

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Creating Devices by Product ID

Use the universal factory to create any device type:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create devices using product IDs from the registry
    devices = [
        create_device(27, serial="d073d5000001"),  # LIFX A19
        create_device(32, serial="d073d5000002"),  # LIFX Z (strip)
        create_device(55, serial="d073d5000003"),  # LIFX Tile
        create_device(90, serial="d073d5000004"),  # LIFX Clean (HEV)
    ]

    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print("Devices created by product ID:")
        for device in devices:
            capabilities = []
            if device.state.has_color:
                capabilities.append("color")
            if device.state.has_multizone:
                capabilities.append("multizone")
            if device.state.has_matrix:
                capabilities.append("matrix")
            if device.state.has_hev:
                capabilities.append("hev")

            print(f"  - Product {device.state.product}: {', '.join(capabilities)}")

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Devices created by product ID:
  - Product 27: color
  - Product 32: color, multizone
  - Product 55: color, matrix
  - Product 90: color, hev
```

## Testing with a LIFX Client

Here's how to test your emulated device with a real LIFX LAN client library, [`lifx-async`](https://pypi.org/project/lifx-async/). Install it with `pip install lifx-async`, or, in a clone of the emulator repository, with `uv sync --group third-party`.

The example runs the emulator and the client in the same event loop and follows the [lifx-async best practices](https://djelibeybi.github.io/lifx-async/api/#best-practices). The client connects directly to the emulated device by IP and serial number rather than using broadcast discovery, which would also find, and could change, any real LIFX devices on your network:

```python
import asyncio

from lifx import Colors, Device, LifxError

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def control_light(host: str, port: int) -> None:
    """Control the emulated device with lifx-async."""
    # Connect directly to the emulated device by IP and serial number.
    # Broadcast discovery would also find, and could change, any real LIFX
    # devices on your network.
    async with await Device.connect(host, serial="d073d5000001", port=port) as light:
        label: str = await light.get_label()
        power: int = await light.get_power()
        print(f"Device: {label}")
        print(f"Power: {power}")

        await light.set_color(Colors.RED)
        print("Changed colour to red")


async def main() -> None:
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        endpoint = server.ipv4_endpoint
        assert endpoint is not None  # Set once the server has started
        host, port = endpoint
        try:
            await control_light(host, port)
        except LifxError as e:
            print(f"LIFX error: {e}")
        print(f"Emulator colour: {device.state.color}")


if __name__ == "__main__":
    asyncio.run(main())
```

You should see:

```
Device: LIFX Color 800lm 000001
Power: 65535
Changed colour to red
Emulator colour: LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500)
```

## Simple pytest Example

Basic pytest integration (requires [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)):

```python
import pytest
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture
async def emulator():
    """Pytest fixture for emulator."""
    device = create_color_light("d073d5000001")
    # Port 0 lets the OS pick a free port
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )

    async with server:
        yield server


@pytest.mark.asyncio
async def test_device_responds(emulator):
    """Test that device is accessible."""
    devices = emulator.get_all_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.state.serial == "d073d5000001"
    assert device.state.has_color is True
```

## Next Steps

- **[Integration Examples](03-integration.md)** - Comprehensive pytest patterns and test fixtures
- **[Advanced Examples](04-advanced-scenarios.md)** - Complex scenarios with multizone, tiles, and error injection
- **[API Reference: Device](../library/device.md)** - Full EmulatedLifxDevice API documentation
- **[API Reference: Server](../library/server.md)** - Full EmulatedLifxServer API documentation

## See Also

- [CLI Usage](../cli/cli-reference.md) - Command-line interface for quick testing
- [Product Registry](../library/products.md) - Available product IDs and capabilities
- [Device Types Guide](../guide/device-types.md) - Understanding different LIFX device types
