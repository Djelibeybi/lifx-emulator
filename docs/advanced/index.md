# Advanced Features

Power-user features for sophisticated testing scenarios.

## Overview

This section covers advanced emulator features for complex testing needs. These features are optional but powerful for:

- Maintaining device state across test runs
- Runtime device management
- Comprehensive error simulation
- Complex multi-scenario testing

## Prerequisites

Before exploring advanced features, you should:

- Be comfortable with basic emulator usage
- Have completed at least the first 2-3 tutorials
- Understand your testing requirements
- Be familiar with REST APIs (for API features)

## Learning Path

Read these guides in order from simple to complex:

1. **[Persistent Storage](storage.md)** - Save device state across restarts
2. **[Device Management API](device-management-api.md)** - Add/remove devices at runtime
3. **[Scenarios](scenarios.md)** - Comprehensive error simulation concepts
4. **[Scenario API](scenario-api.md)** - REST API for managing test scenarios

## Quick Concepts

### Persistent Storage

Save device state (colors, labels, power) across emulator restarts:

```bash
lifx-emulator --persistent
```

Device states are saved to `~/.lifx-emulator/` and automatically restored.

👉 **[Storage Guide](storage.md)**

### Device Management API

Enable the HTTP API to manage devices at runtime:

```bash
lifx-emulator --api
```

Access the web dashboard at `http://localhost:8080` or use the REST API to add/remove devices dynamically.

👉 **[Device Management Guide](device-management-api.md)**

### Testing Scenarios

Configure error conditions for comprehensive testing:

- Packet loss (test retries)
- Response delays (test timeouts)
- Malformed data (test error handling)
- Firmware version overrides

👉 **[Scenarios Guide](scenarios.md)**

### Scenario API

Manage scenarios via REST API with hierarchical scoping:

```bash
# Drop 100% of GetColor packets for all color devices
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}'
```

Supports device-specific, type-based, location-based, group-based, and global scenarios.

👉 **[Scenario API Reference](scenario-api.md)**

## Feature Comparison

| Feature | Basic | Advanced |
|---------|-------|----------|
| Create devices | ✅ | ✅ |
| Device discovery | ✅ | ✅ |
| Control devices | ✅ | ✅ |
| State persistence | ❌ | ✅ |
| Runtime management | ❌ | ✅ |
| Error simulation | Basic | Comprehensive |
| Web UI | ❌ | ✅ |
| REST API | ❌ | ✅ |

## When to Use Advanced Features

### Use Persistent Storage When:

- Running long test suites where state matters
- Testing state restoration after failures
- Developing iteratively and want to preserve state
- Simulating real-world device persistence

### Use Device Management API When:

- Tests need dynamic device creation/removal
- Running multi-stage test scenarios
- Need visual monitoring during development
- Integrating with external test orchestration

### Use Scenarios When:

- Testing retry logic and error handling
- Simulating network issues (packet loss, delays)
- Testing edge cases (malformed data, timeouts)
- Validating firmware version compatibility
- Testing client resilience

## Combined Example

Use multiple advanced features together:

```bash
# Start with persistence, API, and scenarios
lifx-emulator --persistent --api --color 2

# Configure global scenario for packet loss
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 0.3}}'  # 30% packet loss

# Add device at runtime
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 32, "zone_count": 16}'

# Run your tests...
# State persists across restarts
```

## Next Steps

Choose a topic based on your needs, or read through all guides in order for comprehensive understanding.
