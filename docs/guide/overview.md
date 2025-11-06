# User Guide Overview

Welcome to the LIFX Emulator User Guide. This guide covers all aspects of using the emulator for testing.

## What You'll Learn

- [Device Types](device-types.md) - Understanding all supported device types
- [Testing Scenarios](testing-scenarios.md) - Configuring error scenarios and edge cases
- [Integration Testing](integration-testing.md) - Using the emulator in your test suites
- [Best Practices](best-practices.md) - Tips for effective testing

## Getting Started

If you haven't already, check out the [Quick Start Guide](../getting-started/quickstart.md) to get the emulator running.

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
