# Basic Examples

This page demonstrates basic usage patterns for the LIFX Emulator. These examples cover the most common use cases for getting started.

## Single Device Creation

The simplest way to start is with a single color light:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    # Create a single LIFX color light (A19)
    device = create_color_light("d073d5000001")

    # Create and start the server
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print(f"Emulator running with device {device.state.serial}")
        print(f"Label: {device.state.label}")
        print(f"Product: {device.state.product_id}")

        # Keep server running
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Emulator running with device d073d5000001
Label: LIFX Light
Product: 27
```

## Using Context Manager (Recommended)

The context manager automatically handles server startup and shutdown:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    # Server starts automatically on entry, stops on exit
    async with server:
        print("Server is running")
        await asyncio.sleep(60)

    print("Server has stopped cleanly")

if __name__ == "__main__":
    asyncio.run(main())
```

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

async def main():
    # Create different device types
    devices = [
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),
        create_color_temperature_light("d073d5000003"),
        create_infrared_light("d073d5000004"),
    ]

    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        print(f"Running {len(devices)} devices:")
        for device in devices:
            print(f"  - {device.state.serial}: {device.state.label} "
                  f"(product {device.state.product_id})")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Running 4 devices:
  - d073d5000001: LIFX Light (product 27)
  - d073d5000002: LIFX Light (product 27)
  - d073d5000003: LIFX Light (product 50)
  - d073d5000004: LIFX+ A19 (product 29)
```

## Query Device State

Access device state at any time:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        # Access current device state
        state = device.state

        print(f"Serial: {state.serial}")
        print(f"Label: {state.label}")
        print(f"Power: {state.power}")
        print(f"Color: H={state.color.hue}, S={state.color.saturation}, "
              f"B={state.color.brightness}, K={state.color.kelvin}")
        print(f"Capabilities:")
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
Label: LIFX Light
Power: 65535
Color: H=0, S=0, B=65535, K=3500
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

async def main():
    device = create_color_light("d073d5000001")

    # Bind to specific IP and port
    # Use "0.0.0.0" to listen on all interfaces
    server = EmulatedLifxServer(
        devices=[device],
        bind_address="127.0.0.1",
        port=56701  # Non-standard port
    )

    async with server:
        print(f"Server listening on 127.0.0.1:56701")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Setting Initial Device State

Customize device state before starting the server:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.protocol.protocol_types import LightHsbk

async def main():
    device = create_color_light("d073d5000001")

    # Configure device state before starting
    device.state.label = "Living Room Light"
    device.state.power = 65535  # On
    device.state.color = LightHsbk(
        hue=21845,      # 120° (green)
        saturation=65535,  # Fully saturated
        brightness=32768,  # 50% brightness
        kelvin=3500
    )

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print(f"Device ready with custom state:")
        print(f"  Label: {device.state.label}")
        print(f"  Power: {'On' if device.state.power else 'Off'}")
        print(f"  Color: Green at 50% brightness")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Creating Devices by Product ID

Use the universal factory to create any device type:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_device

async def main():
    # Create devices using product IDs from the registry
    devices = [
        create_device(27, serial="d073d5000001"),  # LIFX A19
        create_device(32, serial="d073d5000002"),  # LIFX Z (strip)
        create_device(55, serial="d073d5000003"),  # LIFX Tile
        create_device(90, serial="d073d5000004"),  # LIFX Clean (HEV)
    ]

    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

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

            print(f"  - Product {device.state.product_id}: {', '.join(capabilities)}")

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

Here's how to test your emulated device with a real LIFX LAN client library:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

# Example using lifxlan library (install with: pip install lifxlan)
from lifxlan import LifxLAN

async def run_emulator():
    """Run the emulator in the background."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Emulator running, press Ctrl+C to stop")
        await asyncio.sleep(3600)  # Run for 1 hour

def test_with_client():
    """Test the emulator using a LIFX client."""
    # Discover devices on the local network
    lifx = LifxLAN()
    devices = lifx.get_devices()

    print(f"Found {len(devices)} device(s)")

    for device in devices:
        print(f"\nDevice: {device.get_label()}")
        print(f"Power: {device.get_power()}")

        # Change color to red
        device.set_color([65535, 65535, 32768, 3500])  # Red, full brightness
        print("Changed color to red")

# Run the emulator (in production, use separate processes or async tasks)
if __name__ == "__main__":
    # In real usage, run emulator and client in separate processes/terminals
    asyncio.run(run_emulator())
```

## Simple pytest Example

Basic pytest integration:

```python
import pytest
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

@pytest.fixture
async def emulator():
    """Pytest fixture for emulator."""
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        yield server

@pytest.mark.asyncio
async def test_device_responds(emulator):
    """Test that device is accessible."""
    assert len(emulator.devices) == 1
    device = emulator.devices[0]
    assert device.state.serial == "d073d5000001"
    assert device.state.has_color is True
```

## Next Steps

- **[Integration Examples](03-integration.md)** - Comprehensive pytest patterns and test fixtures
- **[Advanced Examples](04-advanced-scenarios.md)** - Complex scenarios with multizone, tiles, and error injection
- **[API Reference: Device](../api/device.md)** - Full EmulatedLifxDevice API documentation
- **[API Reference: Server](../api/server.md)** - Full EmulatedLifxServer API documentation

## See Also

- [CLI Usage](../getting-started/cli.md) - Command-line interface for quick testing
- [Product Registry](../api/products.md) - Available product IDs and capabilities
- [Device Types Guide](../guide/device-types.md) - Understanding different LIFX device types
