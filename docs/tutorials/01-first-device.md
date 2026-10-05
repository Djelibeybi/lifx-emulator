# Your First LIFX Device

**Difficulty:** 🟢 Beginner | **Time:** ⏱️ 5 minutes | **Prerequisites:** Python 3.10+, LIFX Emulator installed

This tutorial walks you through creating and running your first emulated LIFX device. By the end, you'll have a virtual LIFX light running on your machine that responds to LIFX protocol commands.

## What You'll Learn

- How to create a single emulated device
- How to start the emulator server
- How to verify the device is running
- How to test it with a LIFX client (optional)

## Step 1: Create Your First Device

=== "CLI (Quick Start)"

    The fastest way to get started is with the CLI:

    ```bash
    # Install (if not already installed)
    pip install lifx-emulator

    # Create a single color light with verbose output
    lifx-emulator --color 1 --verbose
    ```

    You should see output like:

    ```
    INFO     Starting LIFX Emulator on 127.0.0.1:56700
    INFO     Created 1 emulated device(s):
    INFO       • LIFX Color 800lm 000001 (d073d5000001) - color
    INFO     Server running with verbose packet logging... Press Ctrl+C to stop
    ```

    **That's it!** You now have a virtual LIFX device running.

=== "Python Library"

    Create a new Python file called `first_device.py`:

    ```python
    import asyncio
    from lifx_emulator import EmulatedLifxServer, create_color_light
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.devices import DeviceManager

    async def main():
        # Create a LIFX Color light
        device = create_color_light("d073d5000001")

        # Create repository and manager (required)
        device_manager = DeviceManager(DeviceRepository())

        # Create server on standard LIFX port (56700)
        server = EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", 56700
        )

        # Start the server
        async with server:
            print(f"Emulator running!")
            print(f"Device: {device.state.label}")
            print(f"Serial: {device.state.serial}")
            print(f"Listening on: 127.0.0.1:56700")
            print("\nPress Ctrl+C to stop")

            # Keep server running
            try:
                await asyncio.sleep(3600)  # Run for 1 hour
            except KeyboardInterrupt:
                print("\nShutting down...")

    if __name__ == "__main__":
        asyncio.run(main())
    ```

    Run your script:

    ```bash
    python first_device.py
    ```

    You should see output like:

    ```
    Emulator running!
    Device: LIFX Color 800lm 000001
    Serial: d073d5000001
    Listening on: 127.0.0.1:56700

    Press Ctrl+C to stop
    ```

**Congratulations!** You now have a virtual LIFX device running on your machine.

## Step 2: Understanding What's Happening

=== "CLI"

    The CLI command `lifx-emulator --color 1 --verbose` does the following:

    - `--color 1` - Creates 1 LIFX Color light (product ID 91)
    - `--verbose` - Enables detailed packet logging to see activity

    **CLI Options Explained:**

    | Option | Description |
    |--------|-------------|
    | `--color N` | Create N color lights |
    | `--verbose` | Show packet-level details |
    | `--port PORT` | Use custom UDP port (default: 56700) |
    | `--bind IP` | Bind to specific IP (default: 127.0.0.1) |
    | `--api` | Enable HTTP management API |

=== "Python Library"

    ### Creating the Device

    ```python
    device = create_color_light("d073d5000001")
    ```

    - `create_color_light()` - Creates a LIFX Color bulb (product ID 91)
    - `"d073d5000001"` - The device's unique serial. LIFX serials look like MAC addresses, and are often almost identical to the device's real MAC address, but they are not the MAC address

    ### Creating the Server

    ```python
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)
    ```

    - `DeviceManager` and `DeviceRepository` - Required for device lifecycle management
    - `[device]` - List of devices to emulate (we have one)
    - `"127.0.0.1"` - IP address to bind to (localhost)
    - `56700` - Standard LIFX UDP port

    ### Using the Context Manager

    ```python
    async with server:
        # Server is running here
        await asyncio.sleep(3600)
    ```

    The `async with` statement:

    1. Starts the server automatically
    2. Runs your code inside the block
    3. Stops the server cleanly when done

## Step 3: Customising Your Device (Optional)

You can customise the device before starting the server:

```python
from lifx_emulator import create_color_light
from lifx_emulator.protocol.protocol_types import LightHsbk

# Create device
device = create_color_light("d073d5000001")

# Customize it
device.state.label = "My First Light"
device.state.power_level = 65535  # On (max power)
device.state.color = LightHsbk(
    hue=21845,      # Green (120 degrees)
    saturation=65535,  # Fully saturated
    brightness=32768,  # 50% brightness
    kelvin=3500
)

# Now start the server...
```

## Step 4: Testing with a LIFX Client (Optional)

If you have a LIFX client library installed, you can test your emulated device.

### Using the lifx-async library

Install the library:

```bash
pip install lifx-async
```

If you're working in a clone of the emulator repository, sync its `third-party` dependency group instead:

```bash
uv sync --group third-party
```

In a **separate terminal**, create `test_client.py`. It follows the [lifx-async best practices](https://djelibeybi.github.io/lifx-async/api/#best-practices): connect with a context manager, use a `Colors` preset, and handle `LifxError`:

```python
import asyncio

from lifx import Colors, Device, LifxError


async def main() -> None:
    try:
        # Connect directly to the emulated device. Broadcast discovery would
        # also find, and could change, any real LIFX devices on your network.
        async with await Device.connect("127.0.0.1", serial="d073d5000001") as light:
            label: str = await light.get_label()
            power: int = await light.get_power()
            print(f"Device: {label}")
            print(f"Power: {power}")

            print("Setting colour to red...")
            await light.set_color(Colors.RED)
            print("Done!")
    except LifxError as e:
        print(f"LIFX error: {e}")


asyncio.run(main())
```

Run it while your emulator is running:

```bash
python test_client.py
```

You should see:

```
Device: LIFX Color 800lm 000001
Power: 65535
Setting colour to red...
Done!
```

If you customised the label in Step 4, you'll see that label instead.

## Troubleshooting

### Port Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:** Change the port number:

```python
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56701
)  # Different port
```

### Device Not Discovered

**Problem:** Client can't find the device

**Solutions:**
1. Make sure the emulator is running
2. Check that both emulator and client are on the same network interface
3. Try binding to `"0.0.0.0"` instead of `"127.0.0.1"`:

```python
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "0.0.0.0", 56700
)
```

### Python Version Error

**Error:** `SyntaxError` or import errors

**Solution:** Ensure you're using Python 3.10 or newer:

```bash
python --version  # Should show 3.10 or higher
```

## What You've Learned

✓ How to create an emulated LIFX device
✓ How to start the emulator server
✓ How to use the context manager pattern
✓ How to customise device properties
✓ How to test with a LIFX client

## Next Steps

Now that you have a basic device running, you can:

1. **[Basic Usage Tutorial](02-basic.md)** - Learn more patterns (multiple devices, state queries, etc.)
2. **[Integration Testing](03-integration.md)** - Use the emulator in your pytest test suite
3. **[Advanced Scenarios](04-advanced-scenarios.md)** - Explore multizone devices, tiles, and error injection

### Quick Wins

Try these modifications to your `first_device.py`:

- **Multiple devices:** Add more devices to the list:
  ```python
  devices = [
      create_color_light("d073d5000001"),
      create_color_light("d073d5000002"),
      create_color_light("d073d5000003"),
  ]
  server = EmulatedLifxServer(
      devices, DeviceManager(DeviceRepository()), "127.0.0.1", 56700
  )
  ```

- **Different device type:** Try a multizone strip:
  ```python
  from lifx_emulator import create_multizone_light
  device = create_multizone_light("d073d8000001", zone_count=16)
  ```

- **Custom labels:** Give each device a unique name:
  ```python
  device.state.label = "Living Room"
  ```

## See Also

- [CLI Usage](../cli/cli-reference.md) - Quick command-line testing
- [Device Types](../guide/device-types.md) - Understanding different LIFX devices
- [API Reference: Device](../library/device.md) - Complete device API documentation
