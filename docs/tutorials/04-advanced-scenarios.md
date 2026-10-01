# Advanced Examples

This page demonstrates advanced usage patterns including multizone devices, tiles, error injection, and complex testing scenarios.

Every example creates its server with a `DeviceManager`, which `EmulatedLifxServer` requires as its second argument:

```python
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

device = create_color_light("d073d5000001")
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
)
```

## Multizone Light (Standard)

Multizone devices like the LIFX Z have a strip of individually addressable zones:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create a LIFX Z strip (product ID 32) with 16 zones
    device = create_device(32, serial="d073d8000001", zone_count=16)

    # Set a different colour for each zone
    for i in range(16):
        # Create a rainbow effect
        hue = int((65535 / 16) * i)
        device.state.zone_colors[i] = LightHsbk(
            hue=hue,
            saturation=65535,
            brightness=32768,
            kelvin=3500,
        )

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(f"Multizone device running with {len(device.state.zone_colors)} zones")
        print("Rainbow pattern configured")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Extended Multizone (Beam)

Extended multizone devices like the LIFX Beam return up to 82 zones in each `ExtendedStateMultiZone` (512) packet instead of 8 per `StateMultiZone` (506) packet:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_multizone_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create a LIFX Beam with 80 zones and extended multizone support
    device = create_multizone_light(
        serial="d073d8000001",
        zone_count=80,
        extended_multizone=True,
    )

    # Extended multizone devices are backwards compatible:
    # they respond to both standard and extended multizone packets

    print("Extended multizone capabilities:")
    print(f"  Zones: {len(device.state.zone_colors)}")
    print(f"  Extended: {device.state.has_extended_multizone}")
    print(f"  Product ID: {device.state.product}")

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Tile Matrix Device

Tile devices have a 2D matrix of zones on each tile, with tiles arranged in a chain:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_tile_device
from lifx_emulator.devices import DeviceManager
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create a LIFX Tile with 5 tiles in the chain
    device = create_tile_device("d073d9000001", tile_count=5)

    # Each LIFX Tile is 8x8 zones (64 zones)
    print("Tile device configuration:")
    print(f"  Tiles: {len(device.state.tile_devices)}")
    for i, tile in enumerate(device.state.tile_devices):
        zones = len(tile["colors"])
        print(f"  Tile {i}: {tile['width']}x{tile['height']} = {zones} zones")

    # Set the first tile to red
    red = LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500)
    first_tile = device.state.tile_devices[0]
    for i in range(len(first_tile["colors"])):
        first_tile["colors"][i] = red

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print("Tile device running")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Error Injection

Error scenarios are `ScenarioConfig` objects registered with a `HierarchicalScenarioManager`. Pass the same manager to the factory **and** to the server as `scenario_manager=`: the server assigns its own scenario manager to every device it manages, so a scenario registered on any other manager is ignored.

Scenario fields match packet types differently:

| Field | Matches | Example |
|-------|---------|---------|
| `drop_packets` | Incoming request type | `{101: 1.0}` drops every GetColor |
| `response_delays` | Outgoing response type | `{107: 0.5}` delays every StateColor |
| `malformed_packets` | Outgoing response type | `[107]` truncates StateColor |
| `invalid_field_values` | Outgoing response type | `[107]` fills StateColor with `0xFF` |
| `partial_responses` | Outgoing multi-packet response type | `[506]` sends only some StateMultiZone packets |

### Packet Dropping

Test client retry logic by dropping specific packets:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Drop every GetColor request (packet type 101); 0.3 would drop 30%
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(drop_packets={101: 1.0})
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will silently drop GetColor packets")
        print("Clients should time out and retry")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

### Response Delays

Simulate a slow network or slow device processing. Delays are keyed by the response packet type:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            response_delays={
                107: 0.5,  # StateColor (reply to GetColor/SetColor): 500ms
                22: 1.0,  # StatePower (reply to GetPower/SetPower): 1 second
                25: 0.1,  # StateLabel (reply to GetLabel/SetLabel): 100ms
            }
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device configured with response delays:")
        print("  StateColor: 500ms")
        print("  StatePower: 1000ms")
        print("  StateLabel: 100ms")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

### Malformed Packets

Test client error handling with truncated responses:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Truncate StateColor (107) payloads
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(malformed_packets=[107])
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send malformed StateColor packets")
        print("Test your client's error handling!")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

### Invalid Field Values

Send responses with every payload byte set to `0xFF`:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(invalid_field_values=[107])
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send StateColor with invalid field values")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

### Partial Responses

Send only some packets of a multi-packet response, to test how clients handle missing data. This applies to responses that span several packets, such as the `StateMultiZone` (506) packets a strip sends in reply to `GetColorZones`:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d8000001", ScenarioConfig(partial_responses=[506])
    )

    # LIFX Z with 16 zones: a full reply is two StateMultiZone packets
    device = create_device(
        32, serial="d073d8000001", zone_count=16, scenario_manager=manager
    )
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send partial StateMultiZone responses")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

### Combined Error Scenarios

Test multiple error conditions simultaneously:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={101: 1.0},  # Drop GetColor
            response_delays={
                22: 0.5,  # Delay StatePower
                25: 0.2,  # Delay StateLabel
            },
            malformed_packets=[107],  # Corrupt StateColor
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device configured with multiple error scenarios:")
        print("  - Dropping GetColor packets")
        print("  - Delaying StatePower and StateLabel")
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
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Create a diverse fleet of devices
    devices = [
        # Standard lights
        create_color_light("d073d5000001", scenario_manager=manager),
        create_color_light("d073d5000002", scenario_manager=manager),
        # Multizone devices: a LIFX Z and a LIFX Beam
        create_device(
            32, serial="d073d8000001", zone_count=16, scenario_manager=manager
        ),
        create_multizone_light(
            "d073d8000002", zone_count=80, scenario_manager=manager
        ),
        # Matrix device
        create_tile_device("d073d9000001", tile_count=5, scenario_manager=manager),
    ]

    # Configure different scenarios for different devices
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(response_delays={107: 0.1})
    )
    manager.set_device_scenario(
        "d073d5000002", ScenarioConfig(drop_packets={101: 1.0})
    )

    # Customise device labels
    devices[0].state.label = "Living Room"
    devices[1].state.label = "Bedroom"
    devices[2].state.label = "Kitchen Strip"
    devices[3].state.label = "Hallway Beam"
    devices[4].state.label = "Office Tiles"

    server = EmulatedLifxServer(
        devices,
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print(f"Running {len(devices)} devices:")
        for device in devices:
            capabilities = []
            if device.state.has_multizone:
                capabilities.append(
                    f"multizone ({len(device.state.zone_colors)} zones)"
                )
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

Enable state persistence across emulator restarts. State-changing protocol packets (`SetColor`, `SetLabel`, and so on) queue a save automatically; changes made directly to `device.state` need an explicit `save_device_state()`:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager, DevicePersistenceAsyncFile
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Create async storage (uses ~/.lifx-emulator by default)
    storage = DevicePersistenceAsyncFile()

    # Create device with storage enabled; saved state is restored here
    device = create_color_light("d073d5000001", storage=storage)

    # Modify device state directly
    device.state.label = "Persistent Light"
    device.state.color = LightHsbk(
        hue=21845,  # Green
        saturation=65535,
        brightness=32768,
        kelvin=3500,
    )

    # Direct assignments are not saved automatically, so queue a save
    await storage.save_device_state(device.state)

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print("Device state will persist across restarts")
        print(f"Storage location: {storage.storage_dir}")
        await asyncio.sleep(60)

    # Drain the device's pending saves, then flush everything to disk
    await device.close()
    await storage.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

## Custom Firmware Version

Emulate specific firmware versions by setting the version when creating the device. It is reported in `StateHostFirmware` (15) and decides which features the device advertises:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    # Simulate an older firmware release
    device = create_color_light("d073d5000001", firmware_version=(2, 80))

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(
            "Device reporting firmware version "
            f"{device.state.version_major}.{device.state.version_minor}"
        )
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Concurrent Client Testing

Test the emulator with multiple concurrent clients. Each client below opens its own UDP socket, sends a `GetService` (2) request and waits for the `StateService` (3) reply:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.constants import LIFX_HEADER_SIZE
from lifx_emulator.devices import DeviceManager
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device
from lifx_emulator.repositories import DeviceRepository


class ClientProtocol(asyncio.DatagramProtocol):
    """Resolve a future with the first datagram received."""

    def __init__(self, reply: asyncio.Future):
        self.reply = reply

    def datagram_received(self, data, addr):
        if not self.reply.done():
            self.reply.set_result(data)


async def simulate_client(client_id, port):
    """Send a GetService request and wait for the StateService reply."""
    await asyncio.sleep(client_id * 0.1)  # Stagger start times

    loop = asyncio.get_running_loop()
    reply = loop.create_future()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: ClientProtocol(reply), remote_addr=("127.0.0.1", port)
    )
    try:
        payload = Device.GetService().pack()
        header = LifxHeader(
            size=LIFX_HEADER_SIZE + len(payload),
            source=1000 + client_id,
            target=b"\x00" * 8,
            tagged=True,
            res_required=True,
            sequence=client_id,
            pkt_type=Device.GetService.PKT_TYPE,
        )
        transport.sendto(header.pack() + payload)

        data = await asyncio.wait_for(reply, timeout=2.0)
        response = LifxHeader.unpack(data)
        serial = response.target[:6].hex()
        print(f"Client {client_id}: StateService ({response.pkt_type}) from {serial}")
    finally:
        transport.close()


async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

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
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


async def main():
    device = create_hev_light("d073d5000001")

    # Configure HEV state
    device.state.hev_cycle_duration_s = 7200  # 2 hours
    device.state.hev_indication = True
    device.state.hev_last_result = 0  # Success

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print("HEV light capabilities:")
        print(f"  Has HEV: {device.state.has_hev}")
        print(f"  Cycle duration: {device.state.hev_cycle_duration_s}s")
        print(f"  Indication: {device.state.hev_indication}")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Creating Devices from Product IDs

Use any product from the registry:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.products import get_product
from lifx_emulator.repositories import DeviceRepository


async def main():
    # List some interesting products
    product_ids = [27, 32, 38, 55, 57, 90]

    devices = []
    for i, pid in enumerate(product_ids):
        serial = f"d073d500000{i + 1}"
        device = create_device(pid, serial=serial)

        # Get product info
        product = get_product(pid)
        print(f"Created: {product.name} (product {pid})")
        print(f"  Capabilities: {product.caps}")

        devices.append(device)

    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        print(f"\nRunning {len(devices)} different product types")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Runtime Device Management with HTTP API

Add and remove devices dynamically using the HTTP API. `run_api_server()` is part of the standalone `lifx-emulator` package (`lifx_emulator_app`); this example uses the standard library's `urllib` as the HTTP client:

```python
import asyncio
import contextlib
import json
import urllib.request

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator_app.api import run_api_server

API_URL = "http://127.0.0.1:8080/api/devices"


def http_json(url, body=None):
    """Send a GET (or a POST when body is given) and decode the JSON reply."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:  # nosec
        return json.load(response)


async def main():
    # Start with one device
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    # Run both emulator and API server
    async with server:
        # Start API server in background
        api_task = asyncio.create_task(
            run_api_server(server, host="127.0.0.1", port=8080)
        )

        # Wait for API to start
        await asyncio.sleep(1)

        # Use API to add a LIFX Z strip (urllib blocks, so run it in a thread)
        added = await asyncio.to_thread(
            http_json, API_URL, {"product_id": 32, "zone_count": 16}
        )
        print(f"Added device: {added['serial']} ({added['label']})")

        # List all devices
        listing = await asyncio.to_thread(http_json, API_URL)
        print(f"\nTotal devices: {listing['total']}")

        await asyncio.sleep(60)

        # Stop the API server
        api_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await api_task


if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- **[Integration Examples](03-integration.md)** - Comprehensive pytest patterns and test fixtures
- **[Basic Examples](02-basic.md)** - Review basic usage patterns
- **[Testing Scenarios Guide](../guide/testing-scenarios.md)** - Detailed testing scenarios documentation
- **[API Reference: Device](../library/device.md)** - Full device API reference

## See Also

- [Product Registry](../library/products.md) - All available product IDs and capabilities
- [Storage API](../library/storage.md) - Persistent storage documentation
- [Scenario Management API Guide](../cli/scenario-api.md) - Runtime device management and scenario testing
- [Device Types](../guide/device-types.md) - Understanding LIFX device capabilities
