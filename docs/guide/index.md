# User Guide Overview

Welcome to the LIFX Emulator User Guide. This guide helps you understand the emulator's features and use them effectively.

## Prerequisites

Before reading this guide, you should have:

- Completed the [Getting Started](../getting-started/index.md) section
- Successfully run the emulator at least once
- Basic understanding of LIFX devices (optional but helpful)

## Learning Path

Read these guides in order for the best learning experience:

1. **[Overview](#what-is-lifx-emulator)** (below) - High-level concepts
2. **[Device Types](device-types.md)** - What devices you can emulate
3. **[Products and Specs](products-and-specs.md)** - Product registry system
4. **[Web Interface](web-interface.md)** - Visual monitoring and management
5. **[Integration Testing](integration-testing.md)** - Using in test suites
6. **[Testing Scenarios](testing-scenarios.md)** - Simulating errors and edge cases
7. **[Best Practices](best-practices.md)** - Tips for effective testing

## What is LIFX Emulator?

LIFX Emulator creates virtual LIFX devices that behave like real hardware. It implements the complete LIFX LAN protocol, allowing you to:

### Test Without Hardware

No need to purchase physical devices. Create as many virtual devices as you need for testing.

### Simulate Real-World Conditions

- Normal operations (power, color, brightness)
- Network issues (packet loss, delays)
- Edge cases (malformed packets, invalid data)
- Error conditions (timeouts, unhandled packets)

### Integrate with CI/CD

Run automated tests in continuous integration pipelines without physical device dependencies.

## Common Use Cases

### Testing Your LIFX Library

The emulator allows you to test your LIFX library without physical devices:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light

async def test_my_library():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)

    async with server:
        # Test your library here
        pass
```

### CI/CD Integration

Run tests in continuous integration pipelines:

```bash
# Start emulator in background
lifx-emulator --bind 127.0.0.1 --port 56701 &
EMULATOR_PID=$!

# Run tests
pytest tests/

# Clean up
kill $EMULATOR_PID
```

### Protocol Development

Experiment with LIFX protocol features:

```bash
# Start with verbose logging to see all packets
lifx-emulator --verbose
```

## Next Steps

Choose a topic from the list above to dive deeper into specific features.
