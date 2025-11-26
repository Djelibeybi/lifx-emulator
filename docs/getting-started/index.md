# Getting Started

Welcome to LIFX Emulator! This section will help you get up and running quickly.

## Choose Your Package

LIFX Emulator is available as two packages:

| Package | Best For |
|---------|----------|
| `lifx-emulator` | CLI tool, web dashboard, quick testing |
| `lifx-emulator-core` | Embedding in Python applications, pytest |

## Learning Path

### CLI Users (lifx-emulator)

1. **[Installation](installation.md)** - Install the CLI tool
2. **[Quick Start](quickstart.md)** - Start emulating devices
3. **[CLI Reference](../cli/cli-reference.md)** - All command-line options

### Library Users (lifx-emulator-core)

1. **[Installation](installation.md)** - Install the library
2. **[Quick Start](quickstart.md)** - Programmatic usage
3. **[API Reference](../library/index.md)** - Python API documentation

## Quick Preview

=== "CLI (lifx-emulator)"

    ```bash
    # Install
    pip install lifx-emulator

    # Run with one color light
    lifx-emulator

    # Create multiple devices with web dashboard
    lifx-emulator --color 2 --multizone 1 --tile 1 --api --verbose
    ```

=== "Python API (lifx-emulator-core)"

    ```python
    import asyncio
    from lifx_emulator import EmulatedLifxServer
    from lifx_emulator.factories import create_color_light
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.devices import DeviceManager

    async def main():
        device = create_color_light("d073d5000001")
        device_manager = DeviceManager(DeviceRepository())

        async with EmulatedLifxServer(
            [device], device_manager, "127.0.0.1", 56700
        ) as server:
            print(f"Emulating: {device.state.label}")
            await asyncio.Event().wait()

    asyncio.run(main())
    ```

## Prerequisites

- **Python 3.11+** (or let uv manage it for you)
- Basic understanding of Python or command-line tools
- (Optional) Familiarity with LIFX devices or protocol

## Why uv?

We recommend [uv](https://astral.sh/uv) because it:

- Automatically manages Python versions for you
- Is significantly faster than pip
- Handles virtual environments seamlessly
- Works consistently across platforms

## Next Steps

Once you've completed the getting started guide, explore:

- **[User Guides](../guide/index.md)** - Deeper understanding of features
- **[Tutorials](../tutorials/index.md)** - Hands-on learning with examples
- **[API Reference](../library/index.md)** - Complete API documentation

## Need Help?

- [Troubleshooting Guide](../reference/troubleshooting.md)
- [FAQ](../faq.md)
- [GitHub Issues](https://github.com/Djelibeybi/lifx-emulator/issues)
