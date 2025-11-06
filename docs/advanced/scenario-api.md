# Scenario Management REST API

The LIFX Emulator provides a comprehensive REST API for runtime management of testing scenarios via HTTP. This guide covers all endpoints and practical examples for managing scenarios.

## Quick Start

```bash
# Start emulator with API enabled
lifx-emulator --api

# Create a global scenario that drops all GetColor packets (100% drop rate)
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}'

# Verify the scenario was created
curl http://localhost:8080/api/scenarios/global
```

## Scope Levels

Scenarios operate at 5 scope levels with automatic precedence (highest to lowest):

1. **Device-specific** - Single device by serial number
2. **Device-type** - All devices of a type (color, multizone, extended_multizone, matrix, hev, infrared, basic)
3. **Location-specific** - All devices in a location
4. **Group-specific** - All devices in a group
5. **Global** - All devices as baseline

### Precedence Example

If you have:

- Global: `drop_packets: {101: 1.0}`
- Type (multizone): `response_delays: {502: 1.0}`
- Device (d073d5000001): `drop_packets: {102: 0.5}`

Then device d073d5000001 would:

- Drop packet 101 with 100% rate (from global)
- Drop packet 102 with 50% rate (from device-specific)
- Have 1.0s delay for packet type 502 (from type scenario)

## Configuration Properties

All scenarios can include the following optional properties:

### drop_packets

**Type:** Object mapping packet type to drop rate (0.0-1.0)

Silently drop (don't respond to) packets of specified types with given probability. 1.0 = always drop, 0.5 = drop 50%, 0.0 = never drop. Simulates packet loss.

```json
{"drop_packets": {"101": 1.0, "102": 0.5, "103": 0.3}}
```

### response_delays

**Type:** Object mapping packet type to delay in seconds

Add artificial delay before responding. Simulates latency.

```json
{"response_delays": {"101": 0.5, "116": 1.0}}
```

### malformed_packets

**Type:** Array of integers

Send truncated/corrupted response packets. Tests error handling.

```json
{"malformed_packets": [107, 506]}
```

### invalid_field_values

**Type:** Array of integers

Send response packets with all fields set to 0xFF (invalid). Tests validation.

```json
{"invalid_field_values": [107]}
```

### firmware_version

**Type:** Array [major, minor] or null

Override firmware version reported by device.

```json
{"firmware_version": [2, 60]}
```

### partial_responses

**Type:** Array of integers

Send incomplete multizone/tile data. Tests buffer handling.

```json
{"partial_responses": [506, 512]}
```

### send_unhandled

**Type:** Boolean

Send StateUnhandled (type 3) for unknown packet types.

```json
{"send_unhandled": true}
```

## REST Endpoints

### Global Scenarios

#### Get Global Scenario
```http
GET /api/scenarios/global
```

**Response (200):**
```json
{
  "scope": "global",
  "identifier": null,
  "scenario": {
    "drop_packets": [],
    "response_delays": {},
    "malformed_packets": [],
    "invalid_field_values": [],
    "firmware_version": null,
    "partial_responses": [],
    "send_unhandled": false
  }
}
```

**Example:**
```bash
curl http://localhost:8080/api/scenarios/global | jq
```

#### Set Global Scenario
```http
PUT /api/scenarios/global
Content-Type: application/json
```

**Request Body:**
```json
{
  "drop_packets": {"101": 1.0, "102": 0.6},
  "response_delays": {"101": 0.5, "116": 1.0},
  "malformed_packets": [],
  "invalid_field_values": [],
  "firmware_version": null,
  "partial_responses": [],
  "send_unhandled": false
}
```

**Response (200):** Returns the scenario that was set

**Example:**
```bash
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}, "response_delays": {"116": 0.5}}'
```

#### Clear Global Scenario
```http
DELETE /api/scenarios/global
```

**Response (204):** No content

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/scenarios/global
```

---

### Device-Specific Scenarios

#### Get Device Scenario
```http
GET /api/scenarios/devices/{serial}
```

**Path Parameters:**
- `serial`: Device serial (e.g., `d073d5000001`)

**Response (200):**
```json
{
  "scope": "device",
  "identifier": "d073d5000001",
  "scenario": {...}
}
```

**Response (404):** No scenario for this device

**Example:**
```bash
curl http://localhost:8080/api/scenarios/devices/d073d5000001 | jq
```

#### Set Device Scenario
```http
PUT /api/scenarios/devices/{serial}
Content-Type: application/json
```

**Path Parameters:**
- `serial`: Device serial

**Request Body:** Any scenario properties (partial update allowed)

**Response (200):** Returns the scenario that was set

**Response (404):** Device not found

**Example:**
```bash
# Set scenario for specific device (drop 100% of GetColor packets)
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}'
```

#### Clear Device Scenario
```http
DELETE /api/scenarios/devices/{serial}
```

**Response (204):** No content

**Response (404):** No scenario for this device

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/scenarios/devices/d073d5000001
```

---

### Type-Specific Scenarios

#### Get Type Scenario
```http
GET /api/scenarios/types/{device_type}
```

**Path Parameters:**
- `device_type`: One of `color`, `multizone`, `extended_multizone`, `matrix`, `hev`, `infrared`, `basic`

**Response (200):**
```json
{
  "scope": "type",
  "identifier": "multizone",
  "scenario": {...}
}
```

**Response (404):** No scenario for this type

**Example:**
```bash
curl http://localhost:8080/api/scenarios/types/multizone | jq
```

#### Set Type Scenario
```http
PUT /api/scenarios/types/{device_type}
Content-Type: application/json
```

**Path Parameters:**
- `device_type`: Device type

**Request Body:** Any scenario properties

**Response (200):** Returns the scenario

**Example:**
```bash
# All multizone devices will respond slowly to GetColorZones (502)
curl -X PUT http://localhost:8080/api/scenarios/types/multizone \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"502": 1.0}}'
```

#### Clear Type Scenario
```http
DELETE /api/scenarios/types/{device_type}
```

**Response (204):** No content

**Response (404):** No scenario for this type

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/scenarios/types/multizone
```

---

### Location-Specific Scenarios

#### Get Location Scenario
```http
GET /api/scenarios/locations/{location}
```

**Path Parameters:**
- `location`: Location label (e.g., `Kitchen`, `Living Room`)

**Response (200):**
```json
{
  "scope": "location",
  "identifier": "Kitchen",
  "scenario": {...}
}
```

**Response (404):** No scenario for this location

#### Set Location Scenario
```http
PUT /api/scenarios/locations/{location}
Content-Type: application/json
```

**Path Parameters:**
- `location`: Location label

**Request Body:** Any scenario properties

**Response (200):** Returns the scenario

**Example:**
```bash
# All devices in Kitchen will have poor connectivity
curl -X PUT http://localhost:8080/api/scenarios/locations/Kitchen \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"116": 0.5}, "drop_packets": {"101": 0.3}}'
```

#### Clear Location Scenario
```http
DELETE /api/scenarios/locations/{location}
```

**Response (204):** No content

**Response (404):** No scenario for this location

---

### Group-Specific Scenarios

#### Get Group Scenario
```http
GET /api/scenarios/groups/{group}
```

**Path Parameters:**
- `group`: Group label (e.g., `Bedroom Lights`)

**Response (200):**
```json
{
  "scope": "group",
  "identifier": "Bedroom Lights",
  "scenario": {...}
}
```

**Response (404):** No scenario for this group

#### Set Group Scenario
```http
PUT /api/scenarios/groups/{group}
Content-Type: application/json
```

**Path Parameters:**
- `group`: Group label

**Request Body:** Any scenario properties

**Response (200):** Returns the scenario

**Example:**
```bash
# All devices in "Bedroom Lights" group will send corrupted responses
curl -X PUT http://localhost:8080/api/scenarios/groups/"Bedroom Lights" \
  -H "Content-Type: application/json" \
  -d '{"malformed_packets": [107]}'
```

#### Clear Group Scenario
```http
DELETE /api/scenarios/groups/{group}
```

**Response (204):** No content

**Response (404):** No scenario for this group

---

## Practical Examples

### Example 1: Test Packet Loss Handling

Test client retry logic by dropping GetColor packets:

```bash
# Drop GetColor (type 101) for all color lights - 100% drop rate
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}'

# Your client should:
# 1. Send GetColor request
# 2. Timeout waiting for response
# 3. Retry (with backoff if implemented)
# 4. Eventually fail after max retries

# Verify scenario is set
curl http://localhost:8080/api/scenarios/types/color | jq '.scenario.drop_packets'
# Output: {"101": 1.0}

# Clean up
curl -X DELETE http://localhost:8080/api/scenarios/types/color
```

### Example 2: Simulate Network Latency

Add realistic network delays:

```bash
# Simulate 500ms latency to all color light responses
curl -X PUT http://localhost:8080/api/scenarios/types/color \
  -H "Content-Type: application/json" \
  -d '{
    "response_delays": {
      "45": 0.5,
      "101": 0.5,
      "102": 0.5,
      "107": 0.5,
      "116": 0.5,
      "117": 0.5
    }
  }'
```

### Example 3: Test Firmware Compatibility

Override firmware version to test backward compatibility:

```bash
# Set device to old firmware version
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"firmware_version": [2, 60]}'

# Get the device to verify firmware version is changed
curl http://localhost:8080/api/devices/d073d5000001 | jq '.version_major, .version_minor'
# Output: 2, 60
```

### Example 4: Simulate Problematic Device

Combine multiple scenarios to simulate a problematic device:

```bash
# Device sometimes drops responses, is slow, and sends bad data
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{
    "drop_packets": {"101": 1.0},
    "response_delays": {"102": 1.0, "116": 0.8},
    "malformed_packets": [107],
    "firmware_version": [2, 50]
  }'
```

### Example 5: Location-Based Testing

Test a group of devices with poor connectivity:

```bash
# All devices in Kitchen location have latency
curl -X PUT http://localhost:8080/api/scenarios/locations/Kitchen \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"116": 0.5}}'

# Override with specific device being worse
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5kitchen01 \
  -H "Content-Type: application/json" \
  -d '{"response_delays": {"116": 2.0}, "drop_packets": {"102": 0.5}}'

# Device d073d5kitchen01 will have 2.0s delay for 116 (device override wins)
# Other Kitchen devices will have 0.5s delay for 116 (location scenario)
```

### Example 6: Test Invalid Data Handling

Send packets with invalid field values:

```bash
# Device will send StateColor with all 0xFF bytes
curl -X PUT http://localhost:8080/api/scenarios/devices/d073d5000001 \
  -H "Content-Type: application/json" \
  -d '{"invalid_field_values": [107]}'

# Your client should:
# - Detect invalid values (hue=65535, saturation=65535, etc.)
# - Reject or sanitize the values
# - Not crash or use invalid values
```

### Example 7: Clear All Scenarios

```bash
# List all devices to find serial numbers
curl http://localhost:8080/api/devices | jq '.[] | .serial'

# Clear scenarios for specific devices
curl -X DELETE http://localhost:8080/api/scenarios/devices/d073d5000001
curl -X DELETE http://localhost:8080/api/scenarios/devices/d073d5000002

# Clear all type scenarios
for type in color multizone extended_multizone matrix hev infrared basic; do
  curl -X DELETE http://localhost:8080/api/scenarios/types/$type 2>/dev/null
done

# Clear global
curl -X DELETE http://localhost:8080/api/scenarios/global
```

## Shell Script Helpers

### Get All Scenarios

```bash
#!/bin/bash

echo "=== Global Scenario ==="
curl -s http://localhost:8080/api/scenarios/global | jq '.scenario'

echo -e "\n=== Device-Specific Scenarios ==="
curl -s http://localhost:8080/api/devices | jq -r '.[] | .serial' | while read serial; do
  echo -n "$serial: "
  curl -s http://localhost:8080/api/scenarios/devices/$serial 2>/dev/null | jq '.scenario.drop_packets // "none"'
done

echo -e "\n=== Type Scenarios ==="
for type in color multizone extended_multizone matrix hev infrared basic; do
  echo -n "$type: "
  curl -s http://localhost:8080/api/scenarios/types/$type 2>/dev/null | jq '.scenario.drop_packets // "none"'
done
```

### Test Scenario Workflow

```bash
#!/bin/bash

echo "1. Setting global scenario..."
curl -X PUT http://localhost:8080/api/scenarios/global \
  -H "Content-Type: application/json" \
  -d '{"drop_packets": {"101": 1.0}}' > /dev/null

echo "2. Verifying global scenario..."
curl -s http://localhost:8080/api/scenarios/global | jq '.scenario'

echo "3. Running test suite..."
pytest tests/

echo "4. Clearing scenario..."
curl -X DELETE http://localhost:8080/api/scenarios/global > /dev/null

echo "5. Verifying cleared..."
curl -s http://localhost:8080/api/scenarios/global | jq '.scenario'
```

## Python Client Examples

### Using requests Library

```python
import requests
import json

BASE_URL = "http://localhost:8080/api"

def get_global_scenario():
    """Get the global scenario configuration."""
    response = requests.get(f"{BASE_URL}/scenarios/global")
    return response.json()

def set_device_scenario(serial, scenario):
    """Set scenario for a specific device."""
    response = requests.put(
        f"{BASE_URL}/scenarios/devices/{serial}",
        json=scenario
    )
    return response.json()

def clear_device_scenario(serial):
    """Clear scenario for a device."""
    response = requests.delete(f"{BASE_URL}/scenarios/devices/{serial}")
    return response.status_code

# Usage
scenario = {
    "drop_packets": {"101": 1.0},
    "response_delays": {"102": 0.5}
}

result = set_device_scenario("d073d5000001", scenario)
print(f"Scenario set: {result}")

status = clear_device_scenario("d073d5000001")
print(f"Cleared: {status == 204}")
```

### Using httpx Library (Async)

```python
import httpx
import asyncio

BASE_URL = "http://localhost:8080/api"

async def test_scenario():
    """Test scenario management async."""
    async with httpx.AsyncClient() as client:
        # Get all devices
        devices = await client.get(f"{BASE_URL}/devices")

        for device in devices.json():
            serial = device["serial"]

            # Set scenario for device
            scenario = {"drop_packets": {"101": 1.0}}
            await client.put(
                f"{BASE_URL}/scenarios/devices/{serial}",
                json=scenario
            )

            # Verify it was set
            resp = await client.get(f"{BASE_URL}/scenarios/devices/{serial}")
            print(f"{serial}: {resp.json()['scenario']}")

            # Clear it
            await client.delete(f"{BASE_URL}/scenarios/devices/{serial}")

asyncio.run(test_scenario())
```

## Integration with Tests

### pytest Integration

```python
import pytest
import requests

API_URL = "http://localhost:8080/api"

@pytest.fixture(autouse=True)
def clear_scenarios():
    """Clear all scenarios before and after each test."""
    # Clear before
    requests.delete(f"{API_URL}/scenarios/global")
    yield
    # Clear after
    requests.delete(f"{API_URL}/scenarios/global")

def test_with_packet_loss():
    """Test client handles packet loss."""
    # Set scenario
    requests.put(
        f"{API_URL}/scenarios/types/color",
        json={"drop_packets": {"101": 1.0}}
    )

    # Run test that exercises retry logic
    client = YourLIFXClient()
    result = client.get_color("d073d5000001")

    # Should either retry successfully or timeout gracefully
    assert result is not None or client.last_error is not None

def test_with_latency():
    """Test client handles slow responses."""
    requests.put(
        f"{API_URL}/scenarios/types/color",
        json={"response_delays": {"101": 0.5}}
    )

    client = YourLIFXClient()
    import time
    start = time.time()
    result = client.get_color("d073d5000001")
    elapsed = time.time() - start

    assert elapsed >= 0.5
    assert result is not None
```

### GitHub Actions Integration

```yaml
name: Test with Scenarios

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Start emulator
        run: |
          python -m lifx_emulator --api --color 2 --multizone 1 &
          sleep 2

      - name: Run tests (normal conditions)
        run: pytest tests/ -v

      - name: Configure packet loss scenario
        run: |
          curl -X PUT http://localhost:8080/api/scenarios/types/color \
            -H "Content-Type: application/json" \
            -d '{"drop_packets": {"101": 1.0}}'

      - name: Run tests (with packet loss)
        run: pytest tests/ -v -k "retry"

      - name: Configure latency scenario
        run: |
          curl -X PUT http://localhost:8080/api/scenarios/types/color \
            -H "Content-Type: application/json" \
            -d '{"response_delays": {"101": 0.5}}'

      - name: Run performance tests
        run: pytest tests/ -v -k "performance"
```

## Common Packet Types

| Type | Name | Description |
|------|------|-------------|
| 45 | Acknowledgement | Sent when ack_required is set |
| 101 | GetColor | Request current color state |
| 102 | SetColor | Set device color |
| 103 | GetWaveform | Get waveform effect |
| 104 | SetWaveform | Set waveform effect |
| 107 | StateColor | Response with current color |
| 116 | GetLightPower | Request power state |
| 117 | SetLightPower | Set power state |
| 502 | GetColorZones | Request multizone colors |
| 503 | SetColorZones | Set multizone colors |
| 506 | StateMultiZone | Response with zone colors |
| 512 | ExtendedStateMultiZone | Response with extended zones |
| 701 | GetDeviceChain | Get tile chain info |
| 707 | Get64 | Get tile pixel data |
| 715 | Set64 | Set tile pixel data |

## Tips and Best Practices

1. **Test One Thing at a Time**: Set a single scenario property first, verify it works, then add more
2. **Use Realistic Values**: Network delays should be 0.1-2.0 seconds, not 10+ seconds
3. **Clean Up After Tests**: Always delete scenarios between test runs to avoid cross-contamination
4. **Monitor Activity**: Use the `/api/activity` endpoint to see actual packets being sent
5. **Start with Device-Level**: Test individual devices before testing by type/location/group
6. **Document Scenarios**: Add comments explaining why each scenario is configured in your tests
7. **Test Recovery**: Verify clients properly recover after scenario conditions clear

## See Also

- [Testing Scenarios Guide](../guide/testing-scenarios.md) - Programmatic scenario configuration
- [Integration Testing](../guide/integration-testing.md) - Using scenarios in test suites
- [Best Practices](../guide/best-practices.md) - Testing strategies
- [API Reference](../api/index.md) - Full API documentation
