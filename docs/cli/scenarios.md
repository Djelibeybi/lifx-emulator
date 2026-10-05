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
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

manager = HierarchicalScenarioManager()

# Drop 30% of GetColor (101) packets
manager.set_device_scenario("d073d5000001", ScenarioConfig(drop_packets={101: 0.3}))

device = create_color_light("d073d5000001", scenario_manager=manager)

# The server assigns its own scenario manager to every device it manages,
# so pass it the same manager
server = EmulatedLifxServer(
    [device],
    DeviceManager(DeviceRepository()),
    "127.0.0.1",
    56700,
    scenario_manager=manager,
)
```

String packet-type keys (as used in JSON) are converted to integers, so `{101: 0.3}` and `{"101": 0.3}` are equivalent.

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

Scenario fields match packet types differently: `drop_packets` matches the **incoming request** type, while every other field matches the **outgoing response** type.

| Field | Matches | Example |
|-------|---------|---------|
| `drop_packets` | Incoming request type | `{101: 1.0}` drops every GetColor |
| `response_delays` | Outgoing response type | `{107: 0.5}` delays every StateColor |
| `malformed_packets` | Outgoing response type | `[107]` truncates StateColor |
| `invalid_field_values` | Outgoing response type | `[107]` fills StateColor with `0xFF` |
| `partial_responses` | Outgoing multi-packet response type | `[506]` sends only some StateMultiZone packets |

Packet type keys can be integers or numeric strings (`{"101": 1.0}`), which is the form JSON and the REST API use.

### Packet Dropping

Simulate packet loss by dropping incoming packets:

```python
from lifx_emulator.scenarios import ScenarioConfig

# Drop 100% of GetColor packets
config = ScenarioConfig(drop_packets={101: 1.0})

# Drop 30% probabilistically
config = ScenarioConfig(drop_packets={101: 0.3})

# Drop multiple packet types
config = ScenarioConfig(drop_packets={101: 1.0, 102: 0.5})
```

### Response Delays

Add latency to responses to simulate slow networks. Delays are keyed by the response packet type, so one delay covers every request that produces that response:

```python
# Add 500ms delay to every StateColor (reply to GetColor and SetColor)
config = ScenarioConfig(response_delays={107: 0.5})

# Multiple delays
config = ScenarioConfig(
    response_delays={
        107: 0.5,  # StateColor - 500ms
        118: 1.0,  # Light.StatePower (reply to Light.GetPower) - 1000ms
        22: 0.2,  # Device.StatePower (reply to Device.GetPower) - 200ms
    }
)
```

### Malformed Packets

Send corrupted/truncated packets to test error handling:

```python
# Send truncated StateColor packets
config = ScenarioConfig(malformed_packets=[107])

# Multiple packet types
config = ScenarioConfig(malformed_packets=[107, 118, 506])
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

### Firmware Version

`firmware_version` changes the version a device reports in `StateHostFirmware` (15), the reply to `GetHostFirmware` (14). Only the reported version changes: the device keeps its configured firmware and the features that go with it, so you can test a client's version-based feature detection. Because it is a scenario, you can change it at runtime and at any scope:

```python
from lifx_emulator.scenarios import ScenarioConfig

# Report firmware 2.60 in StateHostFirmware
config = ScenarioConfig(firmware_version=(2, 60))
```

To emulate a device that really runs a given firmware version, including the features it enables, set it when creating the device instead:

```python
from lifx_emulator import create_color_light

device = create_color_light("d073d5000001", firmware_version=(2, 60))
```

## Scenario Scope

### Global Scenarios

Apply to all devices:

```python
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

manager = HierarchicalScenarioManager()

manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))

# All devices now drop GetColor packets
```

Pass the manager to the server as `scenario_manager=` (and to each factory call, as shown above). On a running server, change `server.scenario_manager` and then call `server.invalidate_all_scenario_caches()`, because devices cache their merged scenario.

### Device-Specific Scenarios

Target individual devices by serial:

```python
# Only device d073d5000001 delays its StateColor replies
manager.set_device_scenario(
    "d073d5000001",
    ScenarioConfig(response_delays={107: 0.5}),
)
```

### Type-Specific Scenarios

Target all devices of a type:

```python
# All color devices drop GetColor packets
manager.set_type_scenario(
    "color",
    ScenarioConfig(drop_packets={101: 0.3}),
)

# All multizone devices delay StateMultiZone replies by 500ms
manager.set_type_scenario(
    "multizone",
    ScenarioConfig(response_delays={506: 0.5}),
)

# Supported types: color, multizone, extended_multizone, matrix, hev, infrared, basic
```

### Location-Based Scenarios

Target all devices in a location:

```python
# All devices in "Kitchen" delay StateColor replies
manager.set_location_scenario(
    "Kitchen",
    ScenarioConfig(response_delays={107: 0.2}),
)
```

### Group-Based Scenarios

Target all devices in a group:

```python
# All devices in "Bedroom Lights" group
manager.set_group_scenario(
    "Bedroom Lights",
    ScenarioConfig(drop_packets={101: 0.5}),
)
```

## Scenario Precedence

When multiple scopes apply, they are merged from the most general to the most specific. Dictionary fields (`drop_packets`, `response_delays`) are combined, with the more specific scope winning for the same packet type; list fields are combined as a union. Precedence is:

1. **Device-specific** (highest priority)
2. **Type-specific**
3. **Location-based**
4. **Group-based**
5. **Global** (lowest priority)

Example:

```python
manager = HierarchicalScenarioManager()

# Global: drop 100% of GetColor
manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))

# Type: multizone devices delay StateMultiZone by 500ms
manager.set_type_scenario(
    "multizone",
    ScenarioConfig(response_delays={506: 0.5}),
)

# Device: d073d5000001 drops 50% of SetColor
manager.set_device_scenario(
    "d073d5000001",
    ScenarioConfig(drop_packets={102: 0.5}),
)

# Result for d073d5000001:
# - Drop 100% of GetColor (from global)
# - Drop 50% of SetColor (added by the device scope)
# - 500ms delay for StateMultiZone (from type, if it is a multizone device)
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
    "response_delays": {"107": 0.2},
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
    "firmware_version": null,
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
# Simulate flaky network - drop 30% of GetColor packets
config = ScenarioConfig(drop_packets={101: 0.3})

# Your client should retry and eventually succeed
```

### Testing Timeout Handling

```python
# Add 2 second delay to StateColor replies to simulate a slow device
config = ScenarioConfig(response_delays={107: 2.0})

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
# Devices that really run older and newer firmware
older = create_color_light("d073d5000001", firmware_version=(2, 60))
newer = create_color_light("d073d5000002", firmware_version=(3, 90))

# Or make one device report a different version at runtime
manager.set_device_scenario(
    "d073d5000002", ScenarioConfig(firmware_version=(2, 60))
)

# Test client behaviour with older and newer firmware
```

### Testing Concurrent Operations

```python
# Create multiple devices with different scenarios
devices = [
    create_color_light("d073d5000001"),  # No delays
    create_color_light("d073d5000002"),  # 500ms StateColor delay
    create_color_light("d073d5000003"),  # Drop packets
]

manager.set_device_scenario(
    "d073d5000002",
    ScenarioConfig(response_delays={107: 0.5}),
)

manager.set_device_scenario(
    "d073d5000003",
    ScenarioConfig(drop_packets={101: 0.5}),
)

# Test client behavior with heterogeneous device conditions
```

## Persistent Scenarios

!!! warning "Deprecated"
    `--persistent-scenarios` is deprecated. Use [config file scenarios](configuration.md#scenarios) instead. Run `lifx-emulator export-config` to migrate existing scenarios.

Save scenarios across emulator restarts:

```bash
# Deprecated — use config file scenarios instead
lifx-emulator --api --persistent --persistent-scenarios
```

Scenarios are saved to `~/.lifx-emulator/scenarios.json`.

## API Reference

For complete API documentation, see:

- [Scenario Management API Guide](scenario-api.md) - REST API endpoints
- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Configuration details
- [Scenario Manager API](../library/server.md) - Python API

## Common Packet Types

| Type | ID | Description |
|------|-----|-------------|
| GetColor | 101 | Request device color |
| SetColor | 102 | Set device color |
| GetPower | 116 | Request power state (Light) |
| SetPower | 117 | Set power state (Light) |
| StateColor | 107 | Color state response |
| StatePower | 118 | Power state response (Light) |
| GetColorZones | 502 | Request multizone colours |
| StateZone | 503 | Single zone state |
| StateMultiZone | 506 | Multizone state |
| ExtendedStateMultiZone | 512 | Extended multizone state |
| Get64 | 707 | Request tile zones |
| State64 | 711 | Tile zone state |
| Set64 | 715 | Set tile zones |

See [Protocol Documentation](../architecture/protocol.md) for complete list.

## Next Steps

- [Scenario Management API](scenario-api.md) - REST API reference
- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Configuration details
- [Integration Testing](../guide/integration-testing.md) - Testing patterns
