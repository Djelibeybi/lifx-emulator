# Custom Test Scenarios

> Simulate real-world conditions and protocol edge cases

Test scenarios allow you to configure the emulator to simulate various real-world conditions like packet loss, network delays, malformed packets, and more. This is useful for testing how your application handles protocol errors and network unreliability.

## Overview

Scenarios are organized in a hierarchical structure with automatic precedence resolution:

1. **Device-specific** - Affects single device by serial
2. **Type-specific** - Affects all devices of a type (color, multizone, etc.)
3. **Location-based** - Affects all devices in a location
4. **Group-based** - Affects all devices in a group
5. **Global** - Affects all devices

This allows fine-grained control over which devices experience which conditions.

## Quick Start

Configure a simple scenario via Python API:

```python
from lifx_emulator import create_color_light
from lifx_emulator.scenarios.manager import ScenarioConfig

device = create_color_light("d073d5000001")

# Drop 30% of GetColor packets
device.scenarios = ScenarioConfig(
    drop_packets={"101": 0.3}
)
```

Or via REST API:

```bash
# Set global scenario - drop 100% of GetColor packets
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{
    "drop_packets": {"101": 1.0},
    "response_delays": {},
    "malformed_packets": [],
    "invalid_field_values": [],
    "firmware_version": null,
    "partial_responses": [],
    "send_unhandled": false
  }'
```

## Scenario Types

### Packet Dropping

Simulate packet loss by dropping incoming packets:

```python
from lifx_emulator.scenarios.manager import ScenarioConfig

# Drop 100% of GetColor packets
config = ScenarioConfig(drop_packets={"101": 1.0})

# Drop 30% probabilistically
config = ScenarioConfig(drop_packets={"101": 0.3})

# Drop multiple packet types
config = ScenarioConfig(drop_packets={"101": 1.0, "102": 0.5})
```

### Response Delays

Add latency to responses to simulate slow networks:

```python
# Add 500ms delay to all GetColor responses
config = ScenarioConfig(response_delays={"101": 0.5})

# Multiple delays
config = ScenarioConfig(response_delays={
    "101": 0.5,    # GetColor - 500ms
    "102": 0.2,    # SetColor - 200ms
    "116": 1.0,    # GetPower - 1000ms
})
```

### Malformed Packets

Send corrupted/truncated packets to test error handling:

```python
# Send truncated StateColor packets
config = ScenarioConfig(malformed_packets=[107])

# Multiple packet types
config = ScenarioConfig(malformed_packets=[107, 108, 110])
```

### Invalid Field Values

Send packets with invalid field values (all 0xFF bytes):

```python
# Send StateColor with all 0xFF values
config = ScenarioConfig(invalid_field_values=[107])
```

### Partial Responses

Send incomplete multizone/tile data:

```python
# Send only partial zone data
config = ScenarioConfig(partial_responses=[506])  # StateMultiZone
```

### Firmware Version Override

Simulate different firmware versions:

```python
# Simulate older firmware
config = ScenarioConfig(firmware_version=(2, 60))

# Simulate newer firmware
config = ScenarioConfig(firmware_version=(3, 90))
```

## Scenario Scope

### Global Scenarios

Apply to all devices:

```python
from lifx_emulator.scenarios.manager import HierarchicalScenarioManager

manager = HierarchicalScenarioManager()

manager.set_global_scenario(ScenarioConfig(
    drop_packets={"101": 1.0}
))

# All devices now drop GetColor packets
```

### Device-Specific Scenarios

Target individual devices by serial:

```python
# Only device d073d5000001 experiences delays
manager.set_device_scenario(
    "d073d5000001",
    ScenarioConfig(response_delays={"101": 0.5})
)
```

### Type-Specific Scenarios

Target all devices of a type:

```python
# All color devices drop GetColor packets
manager.set_type_scenario(
    "color",
    ScenarioConfig(drop_packets={"101": 0.3})
)

# All multizone devices get 500ms delay
manager.set_type_scenario(
    "multizone",
    ScenarioConfig(response_delays={"502": 0.5})
)

# Supported types: color, multizone, extended_multizone, matrix, hev, infrared, basic
```

### Location-Based Scenarios

Target all devices in a location:

```python
# All devices in "Kitchen" experience delays
manager.set_location_scenario(
    "Kitchen",
    ScenarioConfig(response_delays={"101": 0.2})
)
```

### Group-Based Scenarios

Target all devices in a group:

```python
# All devices in "Bedroom Lights" group
manager.set_group_scenario(
    "Bedroom Lights",
    ScenarioConfig(drop_packets={"101": 0.5})
)
```

## Scenario Precedence

When multiple scopes apply, precedence is:

1. **Device-specific** (highest priority)
2. **Type-specific**
3. **Location-based**
4. **Group-based**
5. **Global** (lowest priority)

Example:

```python
manager = HierarchicalScenarioManager()

# Global: drop 100% of GetColor
manager.set_global_scenario(
    ScenarioConfig(drop_packets={"101": 1.0})
)

# Type: multizone devices get 500ms delay
manager.set_type_scenario(
    "multizone",
    ScenarioConfig(response_delays={"502": 0.5})
)

# Device: d073d5000001 drops 50% of SetColor
manager.set_device_scenario(
    "d073d5000001",
    ScenarioConfig(drop_packets={"102": 0.5})
)

# Result for d073d5000001:
# - Drop 100% of GetColor (from global)
# - Drop 50% of SetColor (from device, overrides global)
# - 500ms delay for packet 502 (from type if multizone)
```

## REST API Examples

Full REST API documentation is in the [Scenario Management API guide](scenario-api.md).

### Get Current Scenario

```bash
# Get global scenario
curl http://localhost:8080/api/scenarios/global

# Get scenario for specific device
curl http://localhost:8080/api/scenarios/devices/d073d5000001

# Get scenario for device type
curl http://localhost:8080/api/scenarios/types/multizone
```

### Update Scenarios

```bash
# Set global scenario
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{
    "drop_packets": {"101": 0.3},
    "response_delays": {"101": 0.2},
    "malformed_packets": [],
    "invalid_field_values": [],
    "firmware_version": null,
    "partial_responses": [],
    "send_unhandled": false
  }'

# Set device-specific scenario
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{
    "drop_packets": {"101": 1.0},
    "response_delays": {},
    "malformed_packets": [],
    "invalid_field_values": [],
    "firmware_version": [2, 60],
    "partial_responses": [],
    "send_unhandled": false
  }'
```

### Clear Scenarios

```bash
# Clear global scenario
curl -X DELETE http://localhost:8080/api/scenarios/global

# Clear device scenario
curl -X DELETE http://localhost:8080/api/scenarios/devices/d073d5000001

# Clear type scenario
curl -X DELETE http://localhost:8080/api/scenarios/types/multizone
```

## Practical Testing Patterns

### Testing Retry Logic

```python
# Simulate flaky network - drop 30% of packets
config = ScenarioConfig(drop_packets={"101": 0.3})

# Your client should retry and eventually succeed
```

### Testing Timeout Handling

```python
# Add 2 second delay to simulate slow device
config = ScenarioConfig(response_delays={"101": 2.0})

# Test that client timeout is > 2 seconds
```

### Testing Error Recovery

```python
# Send malformed responses
config = ScenarioConfig(malformed_packets=[107])

# Test that client handles parse errors gracefully
```

### Testing Firmware Compatibility

```python
# Simulate older firmware
config = ScenarioConfig(firmware_version=(2, 60))

# Test client behavior with older firmware

# Simulate newer firmware
config = ScenarioConfig(firmware_version=(3, 90))

# Test client with newer features
```

### Testing Concurrent Operations

```python
# Create multiple devices with different scenarios
devices = [
    create_color_light("d073d5000001"),  # No delays
    create_color_light("d073d5000002"),  # 500ms delay
    create_color_light("d073d5000003"),  # Drop packets
]

manager.set_device_scenario(
    "d073d5000002",
    ScenarioConfig(response_delays={"101": 0.5})
)

manager.set_device_scenario(
    "d073d5000003",
    ScenarioConfig(drop_packets={"101": 0.5})
)

# Test client behavior with heterogeneous device conditions
```

## Persistent Scenarios

Save scenarios across emulator restarts:

```bash
lifx-emulator --api --persistent --persistent-scenarios
```

Scenarios are saved to `~/.lifx-emulator/scenarios.json`.

## API Reference

For complete API documentation, see:

- [Scenario Management API Guide](scenario-api.md) - REST API endpoints
- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Configuration details
- [Scenario Manager API](../api/server.md) - Python API

## Common Packet Types

| Type | ID | Description |
|------|-----|-------------|
| GetColor | 101 | Request device color |
| SetColor | 102 | Set device color |
| GetPower | 116 | Request power state |
| SetPower | 117 | Set power state |
| StateColor | 107 | Color state response |
| StatePower | 118 | Power state response |
| StateMultiZone | 506 | Multizone state |
| ExtendedStateMultiZone | 512 | Extended multizone state |
| Get64 | 514 | Get tile 64 |
| Set64 | 715 | Set tile 64 |

See [Protocol Documentation](../architecture/protocol.md) for complete list.

## Next Steps

- [Scenario Management API](scenario-api.md) - REST API reference
- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Configuration details
- [Integration Testing](../guide/integration-testing.md) - Testing patterns
