# Your First LIFX Device

**Difficulty:** 🟢 Beginner | **Time:** ⏱️ 5 minutes | **Prerequisites:** Python 3.11+, LIFX Emulator installed

This tutorial walks you through creating and running your first emulated LIFX device. By the end, you'll have a virtual LIFX light running on your machine that responds to LIFX protocol commands.

## What You'll Learn

- How to create a single emulated device
- How to start the emulator server
- How to verify the device is running
- How to test it with a LIFX client (optional)

## Step 1: Create Your First Device

Create a new Python file called `first_device.py`:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    # Create a LIFX A19 color light
    device = create_color_light("d073d5000001")

    # Create server on standard LIFX port (56700)
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    # Start the server
    async with server:
        print(f"✓ Emulator running!")
        print(f"✓ Device: {device.state.label}")
        print(f"✓ Serial: {device.state.serial}")
        print(f"✓ Listening on: 127.0.0.1:56700")
        print("\nPress Ctrl+C to stop")

        # Keep server running
        try:
            await asyncio.sleep(3600)  # Run for 1 hour
        except KeyboardInterrupt:
            print("\n✓ Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 2: Run the Emulator

Run your script:

```bash
python first_device.py
```

You should see output like:

```
✓ Emulator running!
✓ Device: LIFX Light
✓ Serial: d073d5000001
✓ Listening on: 127.0.0.1:56700

Press Ctrl+C to stop
```

**Congratulations!** You now have a virtual LIFX device running on your machine.

## Step 3: Understanding What's Happening

Let's break down what each part does:

### Creating the Device

```python
device = create_color_light("d073d5000001")
```

- `create_color_light()` - Creates a LIFX A19 bulb (product ID 27)
- `"d073d5000001"` - The device's unique serial number (MAC address)

### Creating the Server

```python
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
```

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

## Step 4: Customizing Your Device (Optional)

You can customize the device before starting the server:

```python
from lifx_emulator.protocol.protocol_types import LightHsbk

# Create device
device = create_color_light("d073d5000001")

# Customize it
device.state.label = "My First Light"
device.state.power = 65535  # On (max power)
device.state.color = LightHsbk(
    hue=21845,      # Green (120 degrees)
    saturation=65535,  # Fully saturated
    brightness=32768,  # 50% brightness
    kelvin=3500
)

# Now start the server...
```

## Step 5: Testing with a LIFX Client (Optional)

If you have a LIFX client library installed, you can test your emulated device.

### Using the lifx-async library

Install the library:

```bash
pip install lifx-async
```

In a **separate terminal**, create `test_client.py`:

```python
import asyncio
from lifx import discover
from lifx.color import HSBK

async def main():
    # Discover devices
    async with discover() as group:
        print(f"Found {len(group.devices)} device(s)")

        if group.devices:
            device = group.devices[0]
            print(f"Device: {device.label}")
            print(f"Power: {device.power}")

            # Change color to red
            print("Setting color to red...")
            await device.set_color(HSBK.from_rgb(255, 0, 0))
            print("Done!")

asyncio.run(main())
```

Run it while your emulator is running:

```bash
python test_client.py
```

You should see:

```
Found 1 device(s)
Device: LIFX Light
Power: 65535
Setting color to red...
Done!
```

## Troubleshooting

### Port Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:** Change the port number:

```python
server = EmulatedLifxServer([device], "127.0.0.1", 56701)  # Different port
```

### Device Not Discovered

**Problem:** Client can't find the device

**Solutions:**
1. Make sure the emulator is running
2. Check that both emulator and client are on the same network interface
3. Try binding to `"0.0.0.0"` instead of `"127.0.0.1"`:

```python
server = EmulatedLifxServer([device], "0.0.0.0", 56700)
```

### Python Version Error

**Error:** `SyntaxError` or import errors

**Solution:** Ensure you're using Python 3.11 or newer:

```bash
python --version  # Should show 3.11 or higher
```

## What You've Learned

✓ How to create an emulated LIFX device
✓ How to start the emulator server
✓ How to use the context manager pattern
✓ How to customize device properties
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
  server = EmulatedLifxServer(devices, "127.0.0.1", 56700)
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

- [CLI Usage](../getting-started/cli.md) - Quick command-line testing
- [Device Types](../guide/device-types.md) - Understanding different LIFX devices
- [API Reference: Device](../api/device.md) - Complete device API documentation
