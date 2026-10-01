# Testing Scenarios

The LIFX Emulator provides a powerful scenarios system that allows you to simulate various error conditions, network issues, and edge cases. This guide covers all available testing scenarios and how to use them effectively.

## Overview

Testing scenarios modify how emulated devices respond to protocol packets, allowing you to test your client's resilience and error handling.

=== "Python Library"

    Scenarios are `ScenarioConfig` objects registered on a `HierarchicalScenarioManager`. Pass the same manager to the factory **and** to the server as `scenario_manager=`: the server assigns its own scenario manager to every device it manages, so a scenario registered on any other manager is ignored.

    ```python
    from lifx_emulator import EmulatedLifxServer, create_color_light
    from lifx_emulator.devices import DeviceManager
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={101: 1.0},  # Drop GetColor requests
            response_delays={107: 0.5},  # Delay StateColor replies by 500ms
            malformed_packets=[25],  # Corrupt StateLabel responses
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )
    ```

    Scenarios can also be set for every device (`set_global_scenario(config)`), by device type (`set_type_scenario("multizone", config)`), by location label (`set_location_scenario(label, config)`) or by group label (`set_group_scenario(label, config)`). Device scenarios take precedence over type, location, group and global scenarios, in that order.

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
        "response_delays": {"107": 0.5},
        "malformed_packets": [25]
      }'

    # Configure scenario for all color devices
    curl -X PUT http://localhost:8080/api/scenarios/types/color \
      -H "Content-Type: application/json" \
      -d '{"drop_packets": {"101": 0.3}}'

    # Configure global scenario for all devices
    curl -X PUT http://localhost:8080/api/scenarios/global \
      -H "Content-Type: application/json" \
      -d '{"response_delays": {"107": 0.5}}'
    ```

### Which Packet Type Each Field Matches

Scenario fields do not all match the same packet. `drop_packets` matches the request a client sends; every other field matches the response the device sends back:

| Field | Matches | Example |
|-------|---------|---------|
| `drop_packets` | Incoming request type | `{101: 1.0}` drops every GetColor |
| `response_delays` | Outgoing response type | `{107: 0.5}` delays every StateColor |
| `malformed_packets` | Outgoing response type | `[107]` truncates StateColor |
| `invalid_field_values` | Outgoing response type | `[107]` fills StateColor with `0xFF` |
| `partial_responses` | Outgoing multi-packet response type | `[506]` sends only some StateMultiZone packets |

For example, `StateColor` (107) is the reply to both `GetColor` (101) and `SetColor` (102), so `response_delays={107: 0.5}` delays both. Use the [packet types reference](#common-packet-types-reference) below to find the response type for a request.

## Available Scenarios

### 1. Packet Dropping (`drop_packets`)

Silently ignore specific packet types to simulate network packet loss or device unresponsiveness. Supports both deterministic dropping (always drop) and probabilistic dropping (drop X% of packets).

**Configuration:** Dictionary mapping the incoming request packet type to a drop rate (0.0–1.0)
- `1.0` = always drop (100%)
- `0.5` = drop 50% of packets
- `0.1` = drop 10% of packets

A dropped request gets no reply at all, including no acknowledgement.

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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Always drop GetColor (101) and Light.GetPower (116) requests
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(drop_packets={101: 1.0, 116: 1.0})
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Drop packets probabilistically (simulating flaky network)
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={
                101: 0.3,  # Drop 30% of GetColor requests
                102: 0.2,  # Drop 20% of SetColor requests
                23: 0.4,  # Drop 40% of GetLabel requests
            }
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will drop packets probabilistically")
        print("Simulating an unreliable network connection")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Common Packet Types to Drop:**
- `20` - GetPower (Device.GetPower)
- `23` - GetLabel (Device.GetLabel)
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

**Configuration:** Dictionary mapping the outgoing **response** packet type to a delay in seconds. To slow down `GetColor` (101), delay its reply, `StateColor` (107). A delay only applies when the device actually sends that response, so a `SetColor` sent without `res_required` is not delayed by `{107: ...}`.

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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Add various delays, keyed by response packet type
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            response_delays={
                107: 0.5,  # StateColor (reply to GetColor/SetColor): 500ms
                25: 0.2,  # StateLabel (reply to GetLabel/SetLabel): 200ms
                118: 2.0,  # Light.StatePower (reply to Light.GetPower/SetPower): 2s
            }
        ),
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
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

**Configuration:** List of outgoing response packet types to corrupt

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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Corrupt StateColor (107) and StateLabel (25) responses
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(malformed_packets=[107, 25])
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send malformed StateColor and StateLabel packets")
        print("Your client should handle parsing errors gracefully")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Implementation Details:**
- The payload is truncated to 50% of its normal size
- The header still parses, but its `size` field no longer matches the length of the datagram

**Testing Checklist:**
- [ ] Client doesn't crash on malformed packets
- [ ] Parsing errors are caught and logged
- [ ] User sees error message (not crash)
- [ ] Client can recover after parsing error
- [ ] Invalid data is rejected, not used

### 4. Invalid Field Values (`invalid_field_values`)

Send packets with all fields set to invalid values (0xFF bytes).

**Configuration:** List of outgoing response packet types to send with invalid data

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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Send StateColor (107) with invalid field values
    manager.set_device_scenario(
        "d073d5000001", ScenarioConfig(invalid_field_values=[107])
    )

    device = create_color_light("d073d5000001", scenario_manager=manager)
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send StateColor with all 0xFF bytes")
        print("Hue, saturation, brightness, kelvin all invalid")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**What Gets Invalidated:**

Every byte of the payload is replaced with `0xFF`, while the payload length and header stay correct. As a result:

- Numeric fields become their maximum value (`0xFFFF`, `0xFFFFFFFF`, and so on)
- String fields contain `0xFF` bytes, which are not valid UTF-8
- Enum fields hold values that are not defined in the protocol

**Testing Checklist:**
- [ ] Client validates field ranges
- [ ] Out-of-range values are rejected
- [ ] Invalid enums are handled
- [ ] Client uses safe defaults on invalid data
- [ ] Errors are reported to user

### 5. Partial Responses (`partial_responses`)

Send only some of the packets in a multi-packet response, to test the client's handling of incomplete data.

**Configuration:** List of outgoing response packet types. This only affects responses that span several packets, such as the `StateMultiZone` (506) packets a strip sends in reply to `GetColorZones` (502), or `State64` (711) replies from a large matrix device. The device sends a random number of packets between one and one fewer than the full reply. Single-packet responses such as `StateColor` (107) are never affected.

**Use Cases:**
- Test buffer handling
- Verify client doesn't wait forever for missing packets
- Test partial data handling
- Simulate packets lost in transit

**Example:**

```python
import asyncio

from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Send only some of the StateMultiZone (506) packets
    manager.set_device_scenario(
        "d073d5800001", ScenarioConfig(partial_responses=[506])
    )

    # LIFX Z with 16 zones: a full reply is two StateMultiZone packets
    device = create_device(
        32, serial="d073d5800001", zone_count=16, scenario_manager=manager
    )
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Device will send partial StateMultiZone responses")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

**Testing Checklist:**
- [ ] Client detects incomplete multi-packet responses
- [ ] Client doesn't wait indefinitely for missing packets
- [ ] Partial data is rejected or re-requested
- [ ] Client doesn't crash on missing zones
- [ ] Error is logged appropriately

### 6. Custom Firmware Version (`firmware_version`)

Override the reported firmware version to test version compatibility.

!!! warning "Use the factory, not the scenario field"

    `ScenarioConfig` accepts a `firmware_version` field, but the emulator does not currently apply it: devices keep reporting their own firmware version. To emulate a specific firmware version, pass `firmware_version=(major, minor)` to the factory when you create the device.

**Configuration:** Tuple of (major, minor) version numbers, passed to the factory

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


async def main():
    # Pretend to be an older firmware version
    device = create_color_light("d073d5000001", firmware_version=(2, 50))

    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        major = device.state.version_major
        minor = device.state.version_minor
        print(f"Device reports firmware version: {major}.{minor}")
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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Realistic "problem device" scenario
    manager.set_device_scenario(
        "d073d5000001",
        ScenarioConfig(
            drop_packets={101: 0.4},  # Drops 40% of GetColor requests
            response_delays={
                107: 0.8,  # StateColor: colour changes are slow
                25: 0.3,  # StateLabel: label queries are slow
            },
            malformed_packets=[25],  # StateLabel corrupted
        ),
    )

    # Older firmware is set on the device itself
    device = create_color_light(
        "d073d5000001", firmware_version=(2, 77), scenario_manager=manager
    )
    server = EmulatedLifxServer(
        [device],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
    )

    async with server:
        print("Simulating a problematic device:")
        print("  - Drops 40% of GetColor requests")
        print("  - Slow to respond to colour and label requests")
        print("  - Sends corrupted labels")
        print("  - Reports older firmware")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Real-World Test Scenarios

Each of these is a `ScenarioConfig` that you register with `manager.set_device_scenario(serial, config)` (or any other scope), as in the examples above.

### Scenario 1: Flaky WiFi Connection

Simulate a device on an unreliable network:

```python
from lifx_emulator.scenarios import ScenarioConfig

flaky_wifi = ScenarioConfig(
    drop_packets={
        101: 0.3,  # Drop 30% of GetColor requests
        23: 0.3,  # Drop 30% of GetLabel requests
        116: 0.2,  # Drop 20% of Light.GetPower requests
    },
    response_delays={
        107: 1.5,  # Very slow StateColor replies
        118: 2.0,  # Very slow Light.StatePower replies
    },
)
```

**What to Test:**
- Does your client retry appropriately?
- Are users informed about connectivity issues?
- Does the UI remain responsive?
- Does the client recover after transient failures?

### Scenario 2: Firmware Bugs

Simulate a device with firmware issues. Create the device with `firmware_version=(2, 50)` to also report old firmware with known bugs:

```python
from lifx_emulator.scenarios import ScenarioConfig

firmware_bugs = ScenarioConfig(
    malformed_packets=[107],  # Corrupted StateColor
    invalid_field_values=[25],  # Invalid StateLabel data
)
```

**What to Test:**
- Does your client validate responses?
- Are parsing errors handled gracefully?
- Is the user informed about potential device issues?

### Scenario 3: Overloaded Device

Simulate a busy device with limited resources:

```python
from lifx_emulator.scenarios import ScenarioConfig

overloaded = ScenarioConfig(
    response_delays={
        107: 1.0,  # StateColor
        25: 0.4,  # StateLabel
        22: 0.6,  # Device.StatePower
        118: 1.2,  # Light.StatePower
    },
)
```

**What to Test:**
- Can your client handle slow devices?
- Do multiple concurrent requests work?
- Is there a loading indicator for slow operations?

### Scenario 4: Edge Case Testing

Test unusual but valid conditions. Create the device with `firmware_version=(0, 1)` to report very old firmware:

```python
from lifx_emulator.scenarios import ScenarioConfig

edge_case = ScenarioConfig(
    response_delays={107: 5.0},  # Extremely slow (but valid) StateColor
)
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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig


async def main():
    manager = HierarchicalScenarioManager()

    # Device 1: Perfect device (no scenarios)
    device1 = create_color_light("d073d5000001", scenario_manager=manager)
    device1.state.label = "Perfect Light"

    # Device 2: Slow device
    device2 = create_color_light("d073d5000002", scenario_manager=manager)
    device2.state.label = "Slow Light"
    manager.set_device_scenario(
        "d073d5000002",
        ScenarioConfig(response_delays={107: 1.0, 118: 1.5}),  # StateColor, StatePower
    )

    # Device 3: Unreliable device (drops some packets)
    device3 = create_multizone_light(
        "d073d5800001", zone_count=16, scenario_manager=manager
    )
    device3.state.label = "Flaky Strip"
    manager.set_device_scenario(
        "d073d5800001",
        ScenarioConfig(
            drop_packets={502: 0.4},  # Drop 40% of GetColorZones
            response_delays={506: 0.8},  # Slow StateMultiZone replies
        ),
    )

    server = EmulatedLifxServer(
        [device1, device2, device3],
        DeviceManager(DeviceRepository()),
        "127.0.0.1",
        56700,
        scenario_manager=manager,
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

## Changing Scenarios at Runtime

Devices cache their merged scenario. To change scenarios while the server is running, update `server.scenario_manager` and then call `server.invalidate_all_scenario_caches()`:

```python
import asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioConfig


async def main():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
    )

    async with server:
        # Start dropping GetColor (101) requests
        server.scenario_manager.set_device_scenario(
            "d073d5000001", ScenarioConfig(drop_packets={101: 1.0})
        )
        server.invalidate_all_scenario_caches()
        await asyncio.sleep(30)

        # Back to normal behaviour
        server.scenario_manager.delete_device_scenario("d073d5000001")
        server.invalidate_all_scenario_caches()
        await asyncio.sleep(30)


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

Make sure you're using the correct packet type numbers, and remember that every field except `drop_packets` is keyed by the response type:

```python
from lifx_emulator.protocol.packets import Device, Light

# Common packet types
print(f"GetColor: {Light.GetColor.PKT_TYPE}")  # 101
print(f"SetColor: {Light.SetColor.PKT_TYPE}")  # 102
print(f"StateColor: {Light.StateColor.PKT_TYPE}")  # 107
print(f"GetPower: {Light.GetPower.PKT_TYPE}")  # 116
print(f"StateLabel: {Device.StateLabel.PKT_TYPE}")  # 25
```

### Test Scenarios Independently

Test one scenario at a time to isolate issues:

```python
from lifx_emulator.scenarios import ScenarioConfig

# Test drop_packets alone (always drop GetColor)
drops_only = ScenarioConfig(drop_packets={101: 1.0})

# Then test response_delays alone (delay StateColor)
delays_only = ScenarioConfig(response_delays={107: 0.5})

# Then combine them
combined = ScenarioConfig(
    drop_packets={101: 0.5},  # Drop 50% probabilistically
    response_delays={107: 0.5},
)
```

Register each with `manager.set_device_scenario(serial, config)` in turn. On a running server, call `server.invalidate_all_scenario_caches()` after each change.

## Common Packet Types Reference

| Request | Name | Response | Description |
|---------|------|----------|-------------|
| 2 | GetService | 3 StateService | Device discovery |
| 14 | GetHostFirmware | 15 StateHostFirmware | Get host firmware version |
| 16 | GetWifiInfo | 17 StateWifiInfo | Get WiFi info |
| 18 | GetWifiFirmware | 19 StateWifiFirmware | Get WiFi firmware |
| 20 | GetPower | 22 StatePower | Get device power |
| 21 | SetPower | 22 StatePower | Set device power |
| 23 | GetLabel | 25 StateLabel | Get device label |
| 24 | SetLabel | 25 StateLabel | Set device label |
| 32 | GetVersion | 33 StateVersion | Get product and vendor |
| 48 | GetLocation | 50 StateLocation | Get location |
| 49 | SetLocation | 50 StateLocation | Set location |
| 51 | GetGroup | 53 StateGroup | Get group |
| 52 | SetGroup | 53 StateGroup | Set group |
| 101 | GetColor | 107 StateColor | Get light colour |
| 102 | SetColor | 107 StateColor | Set light colour |
| 116 | Light.GetPower | 118 Light.StatePower | Get light power |
| 117 | Light.SetPower | 118 Light.StatePower | Set light power |
| 501 | SetColorZones | — | Set multizone colours (no state reply) |
| 502 | GetColorZones | 506 StateMultiZone | Get multizone colours (one packet per 8 zones) |
| 507 | GetMultiZoneEffect | 509 StateMultiZoneEffect | Get multizone effect |
| 508 | SetMultiZoneEffect | — | Set multizone effect (no state reply) |
| 511 | ExtendedGetColorZones | 512 ExtendedStateMultiZone | Get extended multizone colours |
| 701 | GetDeviceChain | 702 StateDeviceChain | Get tile chain |
| 707 | Get64 | 711 State64 | Get tile 64 zones |
| 715 | Set64 | — | Set tile 64 zones (no state reply) |

## Best Practices

### 1. Start Simple

Begin with one scenario type, verify it works, then add more:

```python
from lifx_emulator.scenarios import ScenarioConfig

# Step 1: Test drops (always drop)
step1 = ScenarioConfig(drop_packets={101: 1.0})

# Step 2: Test probabilistic drops
step2 = ScenarioConfig(drop_packets={101: 0.5})

# Step 3: Add delays
step3 = ScenarioConfig(
    drop_packets={101: 0.5},
    response_delays={107: 0.5},
)

# Step 4: Add more complexity
step4 = ScenarioConfig(
    drop_packets={101: 0.5},
    response_delays={107: 0.5},
    malformed_packets=[25],
)
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
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

SCENARIOS = {
    "flaky_network": ScenarioConfig(
        drop_packets={101: 0.3, 23: 0.3},  # 30% drop rate
        response_delays={107: 1.0},
    ),
    "firmware_bug": ScenarioConfig(
        malformed_packets=[107],
    ),
    "slow_device": ScenarioConfig(
        response_delays={
            107: 1.0,  # StateColor
            25: 0.3,  # StateLabel
        },
    ),
    "intermittent_failures": ScenarioConfig(
        drop_packets={101: 0.5, 116: 0.4},  # 50% and 40% drop rates
    ),
}

# Use in tests
manager = HierarchicalScenarioManager()
manager.set_device_scenario("d073d5000001", SCENARIOS["flaky_network"])
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
