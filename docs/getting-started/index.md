# Getting Started

Welcome to LIFX Emulator! This section will help you get up and running quickly.

## Learning Path

Follow these steps in order:

1. **[Installation](installation.md)** - Install the emulator (5 minutes)
2. **[Quick Start](quickstart.md)** - Create your first device (10 minutes)
3. **[CLI Usage](cli.md)** - Learn command-line options (reference)

## What You'll Learn

By the end of this section, you'll be able to:

- Install LIFX Emulator using uv or pip
- Start the emulator with default settings
- Create emulated devices using Python or CLI
- Understand basic device discovery
- Use verbose mode for debugging

## Prerequisites

- **Python 3.11+** (or let uv manage it for you)
- Basic understanding of Python or command-line tools
- (Optional) Familiarity with LIFX devices or protocol

## Quick Preview

Here's what you'll be able to do after completing this section:

```bash
# Install (recommended: using uv)
uv tool install lifx-emulator

# Or using pip
pip install lifx-emulator

# Run with one color light
lifx-emulator

# Create multiple devices
lifx-emulator --color 2 --multizone 1 --tile 1 --verbose
```

Or in Python:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
    await server.start()
    await asyncio.Event().wait()

asyncio.run(main())
```

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
- **[API Reference](../api/index.md)** - Complete API documentation

## Need Help?

- [Troubleshooting Guide](../reference/troubleshooting.md)
- [FAQ](../faq.md)
- [GitHub Issues](https://github.com/Djelibeybi/lifx-emulator/issues)
