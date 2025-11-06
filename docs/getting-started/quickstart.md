# Quick Start

Get started with LIFX Emulator in just a few minutes.

## Start the Emulator

The simplest way to start the emulator is with the default configuration:

```bash
lifx-emulator
```

This creates a single color light device listening on port 56700.

## Using Verbose Mode

To see all packet traffic (helpful for debugging):

```bash
lifx-emulator --verbose
```

You'll see output like:

```
INFO - Starting LIFX Emulator on 127.0.0.1:56700
INFO - Created 1 emulated device(s):
INFO -   • A19 d073d5 (d073d5000001) - full color
INFO - Server running with verbose packet logging... Press Ctrl+C to stop
DEBUG - Received 36 bytes from ('192.168.1.100', 54321)
DEBUG - Header: GetService (type=2) target=000000000000 source=12345678
DEBUG - Sending StateService to ('192.168.1.100', 54321)
```

## Create Multiple Devices

Create different device types:

```bash
# Create 2 color lights, 1 multizone strip, and 1 tile
lifx-emulator --color 2 --multizone 1 --tile 1
```

## Use Specific Products

Create devices by product ID from the LIFX registry:

```bash
# Create LIFX A19 (27), LIFX Z (32), and LIFX Tile (55)
lifx-emulator --product 27 --product 32 --product 55
```

See all available products:

```bash
lifx-emulator list-products
```

## Python API

Use the emulator in your Python tests:

=== "Basic Example"

    ```python
    import asyncio
    from lifx_emulator import EmulatedLifxServer, create_color_light

    async def main():
        # Create a color light
        device = create_color_light("d073d5000001")

        # Start server
        server = EmulatedLifxServer([device], "127.0.0.1", 56700)
        await server.start()

        print(f"Server running with device: {device.state.label}")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            await server.stop()

    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "Multiple Devices"

    ```python
    import asyncio
    from lifx_emulator import (
        EmulatedLifxServer,
        create_color_light,
        create_multizone_light,
        create_tile_device,
    )

    async def main():
        # Create different device types
        devices = [
            create_color_light("d073d5000001"),
            create_multizone_light("d073d8000001", zone_count=16),
            create_tile_device("d073d9000001", tile_count=5),
        ]

        # Start server
        server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
        await server.start()

        print(f"Server running with {len(devices)} devices")

        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            await server.stop()

    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "Test Integration"

    ```python
    import asyncio
    import pytest
    from lifx_emulator import EmulatedLifxServer, create_color_light
    from your_lifx_library import LifxClient

    @pytest.mark.asyncio
    async def test_discover_devices():
        # Create emulated devices
        device = create_color_light("d073d5000001")
        server = EmulatedLifxServer([device], "127.0.0.1", 56700)

        async with server:
            # Use your LIFX library
            client = LifxClient()
            await client.discover(port=56700)

            # Verify discovery
            assert len(client.devices) == 1
            assert client.devices[0].serial == "d073d5000001"

    @pytest.mark.asyncio
    async def test_set_color():
        device = create_color_light("d073d5000001")
        server = EmulatedLifxServer([device], "127.0.0.1", 56700)

        async with server:
            client = LifxClient()
            await client.discover(port=56700)

            # Set color
            await client.devices[0].set_color(hue=120, saturation=1.0, brightness=0.5)

            # Verify state changed
            assert device.state.color.hue == 21845  # 120 degrees in LIFX format
            assert device.state.color.saturation == 65535
            assert device.state.color.brightness == 32768
    ```

## Device Discovery

The emulator responds to discovery broadcasts on port 56700 (or your chosen port). Your LIFX library should be able to discover emulated devices just like real ones.

Example with a typical discovery flow:

1. Your library broadcasts `GetService` (packet type 2)
2. Emulator responds with `StateService` listing UDP service on port 56700
3. Your library sends `GetVersion` to get product info
4. Emulator responds with vendor=1, product=27 (or configured product)
5. Your library can now send commands to control the device

## Next Steps

- [CLI Usage Guide](cli.md) - Learn all CLI options
- [Device Types](../guide/device-types.md) - Explore supported devices
- [Testing Scenarios](../guide/testing-scenarios.md) - Configure error scenarios
- [API Reference](../api/index.md) - Complete API documentation
- [Tutorials](../tutorials/index.md) - More code examples
