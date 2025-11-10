# Advanced Examples

This page demonstrates advanced usage patterns including multizone devices, tiles, error injection, and complex testing scenarios.

## Multizone Light (Standard)

Standard multizone devices like LIFX Z support up to 16 zones:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_multizone_light
from lifx_emulator.protocol.protocol_types import LightHsbk

async def main():
    # Create a LIFX Z strip with 16 zones
    device = create_multizone_light("d073d8000001", zone_count=16)

    # Set different colors for each zone
    for i in range(16):
        # Create a rainbow effect
        hue = int((65535 / 16) * i)
        device.state.zone_colors[i] = LightHsbk(
            hue=hue,
            saturation=65535,
            brightness=32768,
            kelvin=3500
        )

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print(f"Multizone device running with {len(device.state.zone_colors)} zones")
        print("Rainbow pattern configured")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Extended Multizone (Beam)

Extended multizone devices like LIFX Beam support up to 82 zones:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_multizone_light
from lifx_emulator.protocol.protocol_types import LightHsbk

async def main():
    # Create a LIFX Beam with extended multizone support
    device = create_multizone_light(
        serial="d073d8000001",
        zone_count=80,
        extended_multizone=True
    )

    # Extended multizone devices are backwards compatible
    # They respond to both standard and extended multizone packets

    print(f"Extended multizone capabilities:")
    print(f"  Zones: {len(device.state.zone_colors)}")
    print(f"  Extended: {device.state.extended_multizone}")
    print(f"  Product ID: {device.state.product_id}")

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Tile Matrix Device

Tile devices have a 2D matrix of zones arranged in a chain:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_tile_device
from lifx_emulator.protocol.protocol_types import LightHsbk

async def main():
    # Create a LIFX Tile with 5 tiles in the chain
    device = create_tile_device("d073d9000001", tile_count=5)

    # Each tile is 8x8 pixels (64 zones)
    print(f"Tile device configuration:")
    print(f"  Tiles: {len(device.state.tile_devices)}")
    for i, tile in enumerate(device.state.tile_devices):
        print(f"  Tile {i}: {tile.width}x{tile.height} = {len(tile.colors)} zones")

    # Set first tile to red
    red = LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500)
    for i in range(64):
        device.state.tile_devices[0].colors[i] = red

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Tile device running")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection: Packet Dropping

Test client retry logic by dropping specific packets:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Configure device to drop GetColor requests (packet type 101)
    device.scenarios = {
        'drop_packets': [101]  # Drop all GetColor requests
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device will silently drop GetColor packets")
        print("Clients should timeout and retry")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection: Response Delays

Simulate slow network or device processing:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Add delays to specific packet types
    device.scenarios = {
        'response_delays': {
            101: 0.5,  # GetColor: 500ms delay
            102: 1.0,  # SetColor: 1 second delay
            20: 0.1,   # GetLabel: 100ms delay
        }
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device configured with response delays:")
        print("  GetColor: 500ms")
        print("  SetColor: 1000ms")
        print("  GetLabel: 100ms")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection: Malformed Packets

Test client error handling with corrupted responses:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Send truncated/corrupted responses
    device.scenarios = {
        'malformed_packets': [107]  # Corrupt StateColor responses
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device will send malformed StateColor packets")
        print("Test your client's error handling!")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection: Invalid Field Values

Send responses with invalid data:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Send packets with all fields set to 0xFF
    device.scenarios = {
        'invalid_field_values': [107]  # Invalid StateColor data
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device will send StateColor with invalid field values")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection: Partial Responses

Send incomplete data to test client parsing:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Send truncated packet payloads
    device.scenarios = {
        'partial_responses': [107]  # Truncate StateColor
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device will send partial StateColor responses")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Combined Error Scenarios

Test multiple error conditions simultaneously:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Combine multiple error scenarios
    device.scenarios = {
        'drop_packets': [101],  # Drop GetColor
        'response_delays': {
            102: 0.5,  # Delay SetColor
            20: 0.2,   # Delay GetLabel
        },
        'malformed_packets': [107],  # Corrupt StateColor
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device configured with multiple error scenarios:")
        print("  - Dropping GetColor packets")
        print("  - Delaying SetColor and GetLabel")
        print("  - Corrupting StateColor responses")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Multi-Device Orchestration

Coordinate multiple devices with different configurations:

```python
import asyncio
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
    create_tile_device,
)

async def main():
    # Create a diverse fleet of devices
    devices = [
        # Standard lights
        create_color_light("d073d5000001"),
        create_color_light("d073d5000002"),

        # Multizone devices
        create_multizone_light("d073d8000001", zone_count=16),
        create_multizone_light("d073d8000002", zone_count=80, extended_multizone=True),

        # Matrix device
        create_tile_device("d073d9000001", tile_count=5),
    ]

    # Configure different scenarios for different devices
    devices[0].scenarios = {'response_delays': {102: 0.1}}
    devices[1].scenarios = {'drop_packets': [101]}

    # Customize device labels
    devices[0].state.label = "Living Room"
    devices[1].state.label = "Bedroom"
    devices[2].state.label = "Kitchen Strip"
    devices[3].state.label = "Hallway Beam"
    devices[4].state.label = "Office Tiles"

    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        print(f"Running {len(devices)} devices:")
        for device in devices:
            capabilities = []
            if device.state.has_multizone:
                capabilities.append(f"multizone ({len(device.state.zone_colors)} zones)")
            if device.state.has_matrix:
                capabilities.append(f"matrix ({len(device.state.tile_devices)} tiles)")
            if device.state.has_color:
                capabilities.append("color")

            print(f"  {device.state.label}: {', '.join(capabilities)}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Running 5 devices:
  Living Room: color
  Bedroom: color
  Kitchen Strip: multizone (16 zones), color
  Hallway Beam: multizone (80 zones), color
  Office Tiles: matrix (5 tiles), color
```

## Persistent Storage

Enable state persistence across emulator restarts:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.async_storage import AsyncDeviceStorage
from lifx_emulator.protocol.protocol_types import LightHsbk

async def main():
    # Create async storage manager (uses ~/.lifx-emulator by default)
    storage = AsyncDeviceStorage()

    # Create device with storage enabled
    device = create_color_light("d073d5000001", storage=storage)

    # Modify device state
    device.state.label = "Persistent Light"
    device.state.color = LightHsbk(
        hue=21845,  # Green
        saturation=65535,
        brightness=32768,
        kelvin=3500
    )

    # State changes are automatically queued for async save with debouncing
    await storage.save_device_state(device.state)

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Device state will persist across restarts")
        print(f"Storage location: {storage.storage_dir}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Custom Firmware Version

Emulate specific firmware versions:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")

    # Override firmware version
    device.scenarios = {
        'firmware_version': (3, 70)  # Version 3.70
    }

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print(f"Device reporting firmware version: {device.scenarios['firmware_version']}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Concurrent Client Testing

Test emulator with multiple concurrent clients:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def simulate_client(client_id, port):
    """Simulate a client sending packets."""
    await asyncio.sleep(client_id * 0.1)  # Stagger start times

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # Send some test packets here
    # (This is a simplified example - actual implementation would
    # construct proper LIFX protocol packets)

    print(f"Client {client_id} connected")
    await asyncio.sleep(5)

    writer.close()
    await writer.wait_closed()
    print(f"Client {client_id} disconnected")

async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("Server running, simulating concurrent clients...")

        # Launch multiple concurrent clients
        clients = [simulate_client(i, 56700) for i in range(10)]
        await asyncio.gather(*clients)

        print("All clients finished")

if __name__ == "__main__":
    asyncio.run(main())
```

## HEV (Clean) Light

Emulate LIFX Clean devices with HEV capability:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_hev_light

async def main():
    device = create_hev_light("d073d5000001")

    # Configure HEV state
    device.state.hev_cycle_config_duration = 7200  # 2 hours
    device.state.hev_cycle_config_indication = True
    device.state.last_hev_cycle_result = 0  # Success

    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        print("HEV light capabilities:")
        print(f"  Has HEV: {device.state.has_hev}")
        print(f"  Cycle duration: {device.state.hev_cycle_config_duration}s")
        print(f"  Indication: {device.state.hev_cycle_config_indication}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Creating Devices from Product IDs

Use any product from the registry:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_device
from lifx_emulator.products import get_product_by_id

async def main():
    # List some interesting products
    product_ids = [27, 32, 38, 55, 57, 90]

    devices = []
    for i, pid in enumerate(product_ids):
        serial = f"d073d500000{i+1}"
        device = create_device(pid, serial=serial)

        # Get product info
        product = get_product_by_id(pid)
        print(f"Created: {product.name} (product {pid})")
        print(f"  Capabilities: {', '.join(product.capabilities)}")

        devices.append(device)

    server = EmulatedLifxServer(devices, "127.0.0.1", 56700)

    async with server:
        print(f"\nRunning {len(devices)} different product types")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Runtime Device Management with HTTP API

Add and remove devices dynamically using the HTTP API:

```python
import asyncio
import aiohttp
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.api import run_api_server

async def main():
    # Start with one device
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    # Run both emulator and API server
    async with server:
        # Start API server in background
        api_task = asyncio.create_task(
            run_api_server(server, host="127.0.0.1", port=8080)
        )

        # Wait for API to start
        await asyncio.sleep(1)

        # Use API to add a new device
        async with aiohttp.ClientSession() as session:
            # Add a LIFX Z strip
            async with session.post(
                "http://127.0.0.1:8080/api/devices",
                json={"product_id": 32, "zone_count": 16}
            ) as resp:
                result = await resp.json()
                print(f"Added device: {result}")

            # List all devices
            async with session.get("http://127.0.0.1:8080/api/devices") as resp:
                devices = await resp.json()
                print(f"\nTotal devices: {len(devices)}")

        await asyncio.sleep(60)

        api_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- **[Integration Examples](03-integration.md)** - Comprehensive pytest patterns and test fixtures
- **[Basic Examples](02-basic.md)** - Review basic usage patterns
- **[Testing Scenarios Guide](../guide/testing-scenarios.md)** - Detailed testing scenarios documentation
- **[API Reference: Device](../api/device.md)** - Full device API reference

## See Also

- [Product Registry](../api/products.md) - All available product IDs and capabilities
- [Storage API](../api/storage.md) - Persistent storage documentation
- [Scenario Management API Guide](../advanced/scenario-api.md) - Runtime device management and scenario testing
- [Device Types](../guide/device-types.md) - Understanding LIFX device capabilities
