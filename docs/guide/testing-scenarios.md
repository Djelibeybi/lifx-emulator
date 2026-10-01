# Testing Scenarios

The LIFX Emulator provides a powerful scenarios system that allows you to simulate various error conditions, network issues, and edge cases. This guide covers all available testing scenarios and how to use them effectively.

## Overview

Testing scenarios modify how emulated devices respond to protocol packets, allowing you to test your client's resilience and error handling.

=== "Python Library"

    Configure scenarios by passing a `ScenarioConfig` to the server's shared
    `HierarchicalScenarioManager` (`server.scenario_manager`). Scenarios can be
    set per device, device type, location, group or globally. When you change
    scenarios on a running server, call `server.invalidate_all_scenario_caches()`
    so devices pick up the new configuration:

    ```python
    from lifx_emulator import EmulatedLifxServer, create_color_light
    from lifx_emulator.devices import DeviceManager
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.scenarios import ScenarioConfig

    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Configure scenarios
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(
            drop_packets={101: 1.0},  # Drop GetColor requests
            response_delays={102: 0.5},  # Delay SetColor by 500ms
            malformed_packets=[107],  # Corrupt StateColor responses
        ),
    )
    server.invalidate_all_scenario_caches()
    ```

=== "REST API"

    Configure scenarios via the Scenario REST API (requires `--api` flag):

    ```bash
    # Start emulator with API
    lifx-emulator --color 1 --api

    # Configure scenario for a specific device
    curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
      -H "Content-Type: application/json" \
      -d '{
        "drop_packets": {"101": 1.0},
        "response_delays": {"102": 0.5},
        "malformed_packets": [107]
      }'

    # Configure scenario for all color devices
    curl -X PUT http://localhost:8080/api/scenarios/types/color \
      -H "Content-Type: application/json" \
      -d '{"drop_packets": {"101": 0.3}}'

    # Configure global scenario for all devices
    curl -X PUT http://localhost:8080/api/scenarios/global \
      -H "Content-Type: application/json" \
      -d '{"response_delays": {"101": 0.5}}'
    ```

## Available Scenarios

### 1. Packet Dropping (`drop_packets`)

Silently ignore specific packet types to simulate network packet loss or device unresponsiveness. Supports both deterministic dropping (always drop) and probabilistic dropping (drop X% of packets).

**Configuration:** Dictionary mapping packet type to drop rate (0.1-1.0)
- `1.0` = always drop (100%)
- `0.5` = drop 50% of packets
- `0.1` = drop 10% of packets

**Use Cases:**
- Test client retry logic
- Simulate network packet loss
- Test timeout handling
- Verify client doesn't hang on no response
- Test resilience to intermittent failures

**Example - Always Drop:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Always drop GetColor (101) and GetPower (20) requests
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(drop_packets={101: 1.0, 20: 1.0}),
    )

    async with server:
        print("Device will drop 100% of GetColor and GetPower packets")
        print("Clients should timeout and implement retry logic")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Example - Probabilistic Drop:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Drop packets probabilistically (simulating flaky network)
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(
            drop_packets={
                101: 0.3,   # Drop 30% of GetColor requests
                102: 0.2,   # Drop 20% of SetColor requests
                23: 0.4,    # Drop 40% of GetLabel requests
            }
        ),
    )

    async with server:
        print("Device will drop packets probabilistically")
        print("Simulating an unreliable network connection")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Common Packet Types to Drop:**
- `23` - GetLabel
- `101` - GetColor (Light.GetColor)
- `116` - GetLightPower (Light.GetPower)
- `502` - GetColorZones (MultiZone.GetColorZones)
- `707` - Get64 (Tile.Get64)

**Drop Rate Recommendations:**

- **Testing retry logic:** 1.0 (always drop)
- **Simulating flaky WiFi:** 0.1-0.3 (10-30% drop rate)
- **Simulating congestion:** 0.2-0.4 (20-40% drop rate)
- **Simulating very poor connection:** 0.5-0.8 (50-80% drop rate)

**Testing Checklist:**
- [ ] Client implements retry logic
- [ ] Client has appropriate timeouts
- [ ] Client doesn't hang indefinitely
- [ ] User gets feedback about timeout
- [ ] Exponential backoff is implemented (if applicable)
- [ ] Client recovers after transient failures (for probabilistic drops)

### 2. Response Delays (`response_delays`)

Add artificial delays to specific packet responses to simulate slow devices or network latency.

**Configuration:** Dictionary mapping packet type to delay in seconds

**Use Cases:**
- Test timeout configuration
- Simulate slow network conditions
- Test concurrent request handling
- Verify UI doesn't freeze during slow responses

**Example:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Add various delays
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(
            response_delays={
                101: 0.5,   # GetColor: 500ms delay
                102: 1.0,   # SetColor: 1 second delay
                23: 0.2,    # GetLabel: 200ms delay
                117: 2.0,   # SetPower: 2 second delay (very slow)
            }
        ),
    )

    async with server:
        print("Device configured with response delays")
        print("Test your client's async handling and timeouts")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Realistic Delay Values:**
- **Fast local network:** 0.01 - 0.05 seconds (10-50ms)
- **Normal local network:** 0.05 - 0.2 seconds (50-200ms)
- **Slow/congested network:** 0.5 - 2.0 seconds
- **Very slow/problematic:** 2.0+ seconds

**Testing Checklist:**
- [ ] UI remains responsive during slow operations
- [ ] Progress indicators show during slow requests
- [ ] Timeout values are appropriate for expected delays
- [ ] Multiple slow requests don't block each other
- [ ] Cancel operations work correctly

### 3. Malformed Packets (`malformed_packets`)

Send truncated or corrupted packet responses to test client parsing robustness.

**Configuration:** List of packet types to corrupt

**Use Cases:**
- Test packet parsing error handling
- Verify client doesn't crash on bad data
- Test protocol implementation resilience
- Ensure graceful degradation

**Example:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Corrupt StateColor and StateLabel responses
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(malformed_packets=[107, 25])  # StateColor, StateLabel,
    )

    async with server:
        print("Device will send malformed StateColor and StateLabel packets")
        print("Your client should handle parsing errors gracefully")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Implementation Details:**
- Packets are truncated to 50% of their normal size
- Binary data may be corrupted or incomplete
- Header is still valid (so packet is delivered)

**Testing Checklist:**
- [ ] Client doesn't crash on malformed packets
- [ ] Parsing errors are caught and logged
- [ ] User sees error message (not crash)
- [ ] Client can recover after parsing error
- [ ] Invalid data is rejected, not used

### 4. Invalid Field Values (`invalid_field_values`)

Send packets with all fields set to invalid values (0xFF bytes).

**Configuration:** List of packet types to send with invalid data

**Use Cases:**
- Test field validation
- Verify bounds checking
- Test handling of out-of-range values
- Ensure client validates data

**Example:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Send StateColor with invalid field values
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(invalid_field_values=[107])  # StateColor,
    )

    async with server:
        print("Device will send StateColor with all 0xFF bytes")
        print("Hue, saturation, brightness, kelvin all invalid")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**What Gets Invalidated:**
- All numeric fields set to 0xFFFF or 0xFFFFFFFF
- Strings filled with invalid characters
- Enums set to undefined values

**Testing Checklist:**
- [ ] Client validates field ranges
- [ ] Out-of-range values are rejected
- [ ] Invalid enums are handled
- [ ] Client uses safe defaults on invalid data
- [ ] Errors are reported to user

### 5. Partial Responses (`partial_responses`)

Send incomplete packet payloads to test client's handling of truncated data.

**Configuration:** List of response packet types to truncate. This only affects
replies made up of several packets (such as `StateMultiZone` (506) or `State64`
(711)): the device sends a random subset of them instead of the full set.

**Use Cases:**
- Test handling of missing response packets
- Verify client doesn't wait forever for the rest of a reply
- Test partial data handling
- Simulate network truncation

**Example:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_multizone_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_multizone_light("d073d8000001", zone_count=16)
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Send only some of the StateMultiZone packets for each GetColorZones
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(partial_responses=[506]),  # StateMultiZone
    )

    async with server:
        print("Device will send incomplete StateMultiZone responses")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Testing Checklist:**
- [ ] Client detects truncated packets
- [ ] No buffer overruns occur
- [ ] Partial data is rejected
- [ ] Client doesn't crash on short reads
- [ ] Error is logged appropriately

### 6. Custom Firmware Version (`firmware_version`)

Override the reported firmware version to test version compatibility.

**Configuration:** Tuple of (major, minor) version numbers

**Use Cases:**
- Test version detection
- Verify feature compatibility checks
- Test upgrade/downgrade scenarios
- Ensure graceful handling of unknown versions

**Example:**

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Pretend to be an older firmware version
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(firmware_version=(2, 50))  # Version 2.50 (old),
    )

    async with server:
        print(f"Device reports firmware version: 2.50")
        print("Test your client's version compatibility logic")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Common Versions to Test:**
- `(2, 0)` - Very old firmware
- `(3, 50)` - Mid-range firmware
- `(3, 70)` - Current typical version
- `(99, 99)` - Future/unknown version

## Combining Multiple Scenarios

You can combine multiple scenarios to create complex test conditions:

```python
import asyncio
from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    device = create_color_light("d073d5000001")
    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)

    # Realistic "problem device" scenario
    server.scenario_manager.set_device_scenario(
        device.state.serial,
        ScenarioConfig(
            drop_packets={101: 0.4},  # Drops 40% of GetColor requests
            response_delays={
                102: 0.8,  # Color changes are slow
                23: 0.3,   # Label queries are slow
            },
            malformed_packets=[25],  # StateLabel corrupted
            firmware_version=(2, 77),  # Older firmware
        ),
    )

    async with server:
        print("Simulating a problematic device:")
        print("  - Drops 40% of GetColor requests")
        print("  - Slow to respond to commands")
        print("  - Occasionally sends corrupted labels")
        print("  - Reports older firmware")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Real-World Test Scenarios

### Scenario 1: Flaky WiFi Connection

Simulate a device on an unreliable network:

```python
flaky_wifi = ScenarioConfig(
    drop_packets={
        101: 0.3,  # Drop 30% of GetColor requests
        23: 0.3,   # Drop 30% of GetLabel requests
        116: 0.2,  # Drop 20% of GetPower requests
    },
    response_delays={
        102: 1.5,  # Very slow commands
        117: 2.0,  # Very slow power changes
    },
)
server.scenario_manager.set_device_scenario(device.state.serial, flaky_wifi)
```

**What to Test:**
- Does your client retry appropriately?
- Are users informed about connectivity issues?
- Does the UI remain responsive?
- Does the client recover after transient failures?

### Scenario 2: Firmware Bugs

Simulate a device with firmware issues:

```python
firmware_bugs = ScenarioConfig(
    malformed_packets=[107],  # Corrupted color state
    invalid_field_values=[25],  # Invalid label data
    firmware_version=(2, 50),  # Old firmware with known bugs
)
server.scenario_manager.set_device_scenario(device.state.serial, firmware_bugs)
```

**What to Test:**
- Does your client validate responses?
- Are parsing errors handled gracefully?
- Is the user informed about potential device issues?

### Scenario 3: Overloaded Device

Simulate a busy device with limited resources:

```python
overloaded = ScenarioConfig(
    response_delays={
        101: 0.5,
        102: 1.0,
        23: 0.4,
        117: 1.2,
        116: 0.6,
    },
)
server.scenario_manager.set_device_scenario(device.state.serial, overloaded)
```

**What to Test:**
- Can your client handle slow devices?
- Do multiple concurrent requests work?
- Is there a loading indicator for slow operations?

### Scenario 4: Edge Case Testing

Test unusual but valid conditions:

```python
edge_cases = ScenarioConfig(
    firmware_version=(0, 1),  # Very old firmware
    response_delays={102: 5.0},  # Extremely slow (but valid)
)
server.scenario_manager.set_device_scenario(device.state.serial, edge_cases)
```

**What to Test:**
- Minimum firmware version support
- Maximum timeout handling
- Version compatibility warnings

## Per-Device Scenarios

Apply different scenarios to different devices in a multi-device setup:

```python
import asyncio
from lifx_emulator import (
    EmulatedLifxServer,
    create_color_light,
    create_multizone_light,
)
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig

async def main():
    # Device 1: Perfect device (no scenarios)
    device1 = create_color_light("d073d5000001")
    device1.state.label = "Perfect Light"

    # Device 2: Slow device
    device2 = create_color_light("d073d5000002")
    device2.state.label = "Slow Light"

    # Device 3: Unreliable device (drops some packets)
    device3 = create_multizone_light("d073d8000001", zone_count=16)
    device3.state.label = "Flaky Strip"

    device_manager = DeviceManager(DeviceRepository())
    server = EmulatedLifxServer(
        [device1, device2, device3], device_manager, "127.0.0.1", 56700
    )

    server.scenario_manager.set_device_scenario(
        device2.state.serial,
        ScenarioConfig(response_delays={102: 1.0, 117: 1.5}),
    )
    server.scenario_manager.set_device_scenario(
        device3.state.serial,
        ScenarioConfig(
            drop_packets={502: 0.4},  # Drop 40% of GetColorZones
            response_delays={501: 0.8},  # Slow SetColorZones
        ),
    )

    async with server:
        print("Testing with mixed device reliability:")
        print(f"  {device1.state.label}: Normal")
        print(f"  {device2.state.label}: Slow")
        print(f"  {device3.state.label}: Unreliable (drops 40% of color zone queries)")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Debugging Scenario Issues

### Enable Verbose Logging

When scenarios aren't behaving as expected:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Your test code here
```

### Verify Packet Types

Make sure you're using the correct packet type numbers:

```python
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile

# Common packet types
print(f"GetColor: {Light.GetColor.PKT_TYPE}")  # 101
print(f"SetColor: {Light.SetColor.PKT_TYPE}")  # 102
print(f"StateColor: {Light.StateColor.PKT_TYPE}")  # 107
print(f"GetPower: {Light.GetPower.PKT_TYPE}")  # 116
```

### Test Scenarios Independently

Test one scenario at a time to isolate issues:

```python
scenarios = server.scenario_manager
serial = device.state.serial

# Test drop_packets alone (always drop)
scenarios.set_device_scenario(serial, ScenarioConfig(drop_packets={101: 1.0}))

# Then test response_delays alone
scenarios.set_device_scenario(serial, ScenarioConfig(response_delays={102: 0.5}))

# Then combine them
scenarios.set_device_scenario(
    serial,
    ScenarioConfig(
        drop_packets={101: 0.5},  # Drop 50% probabilistically
        response_delays={102: 0.5},
    ),
)

# Make running devices pick up each change
server.invalidate_all_scenario_caches()
```

## Common Packet Types Reference

| Type | Name | Description |
|------|------|-------------|
| 2 | GetService | Device discovery |
| 14 | GetHostFirmware | Get host firmware version |
| 16 | GetWifiInfo | Get WiFi info |
| 18 | GetWifiFirmware | Get WiFi firmware |
| 20 | GetPower | Get device power |
| 21 | SetPower | Set device power |
| 23 | GetLabel | Get device label |
| 24 | SetLabel | Set device label |
| 32 | GetVersion | Get product and vendor |
| 48 | GetLocation | Get location |
| 49 | SetLocation | Set location |
| 51 | GetGroup | Get group |
| 52 | SetGroup | Set group |
| 101 | GetColor | Get light colour |
| 102 | SetColor | Set light colour |
| 116 | GetLightPower (Light.GetPower) | Get light power |
| 117 | SetLightPower (Light.SetPower) | Set light power |
| 501 | SetColorZones | Set multizone colours |
| 502 | GetColorZones | Get multizone colours |
| 507 | GetMultiZoneEffect (MultiZone.GetEffect) | Get multizone effect |
| 508 | SetMultiZoneEffect (MultiZone.SetEffect) | Set multizone effect |
| 701 | GetDeviceChain | Get tile chain |
| 707 | Get64 | Get tile 64 zones |
| 715 | Set64 | Set tile 64 zones |

## Best Practices

### 1. Start Simple

Begin with one scenario type, verify it works, then add more:

```python
# Step 1: Test drops (always drop)
step1 = ScenarioConfig(drop_packets={101: 1.0})

# Step 2: Test probabilistic drops
step2 = ScenarioConfig(drop_packets={101: 0.5})

# Step 3: Add delays
step3 = ScenarioConfig(
    drop_packets={101: 0.5},
    response_delays={102: 0.5},
)

# Step 4: Add more complexity
step4 = ScenarioConfig(
    drop_packets={101: 0.5},
    response_delays={102: 0.5},
    malformed_packets=[107],
)

# Apply one step at a time
server.scenario_manager.set_device_scenario(device.state.serial, step1)
server.invalidate_all_scenario_caches()
```

### 2. Use Realistic Values

Choose delay values that represent real-world conditions:

- Don't use 10-second delays (unrealistic)
- Do use 0.5-2 second delays (realistic for slow networks)

### 3. Test Error Recovery

Scenarios should test your recovery logic, not just error detection:

- After a drop, can the client retry successfully?
- After a timeout, can the client reconnect?
- After invalid data, can the client request fresh data?

### 4. Document Test Cases

Create named scenario configurations for common tests:

```python
SCENARIOS = {
    'flaky_network': ScenarioConfig(
        drop_packets={101: 0.3, 23: 0.3},  # 30% drop rate
        response_delays={102: 1.0},
    ),
    'firmware_bug': ScenarioConfig(
        malformed_packets=[107],
        firmware_version=(2, 50),
    ),
    'slow_device': ScenarioConfig(
        response_delays={
            101: 0.5,
            102: 1.0,
            23: 0.3,
        },
    ),
    'intermittent_failures': ScenarioConfig(
        drop_packets={101: 0.5, 116: 0.4},  # 50% and 40% drop rates
    ),
}

# Use in tests
server.scenario_manager.set_device_scenario(
    device.state.serial, SCENARIOS['flaky_network']
)
```

## Next Steps

- **[Advanced Examples](../tutorials/04-advanced-scenarios.md)** - See scenarios in action
- **[Integration Testing](integration-testing.md)** - Use scenarios in test suites
- **[Best Practices](best-practices.md)** - Testing strategies
- **[API Reference: Device](../library/device.md)** - Full device API documentation

## See Also

- [Protocol Types Reference](../library/protocol.md) - All packet types and numbers
- [Device API](../library/device.md) - EmulatedLifxDevice documentation
- [FAQ](../faq.md) - Common issues and solutions
