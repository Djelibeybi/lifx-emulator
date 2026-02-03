# Device Management API

## Overview

The LIFX Emulator provides a comprehensive REST API for monitoring server status and managing emulated devices. The API is built with FastAPI and provides an OpenAPI 3.1.0 compliant specification.

**Base URL**: `http://localhost:8080/api`

**Interactive Documentation**:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI Schema: `http://localhost:8080/openapi.json`

## Quick Start

### Enable the API Server

```bash
# Start emulator with API server
lifx-emulator --api

# Custom host and port
lifx-emulator --api --api-host 127.0.0.1 --api-port 9090

# Disable activity logging to reduce traffic
lifx-emulator --api --api-activity=false
```

### Basic Examples

```bash
# Get server statistics
curl http://localhost:8080/api/stats

# List all devices (paginated)
curl http://localhost:8080/api/devices
curl 'http://localhost:8080/api/devices?offset=0&limit=10'

# Create a new color light (product 27)
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 27}'

# Create multiple devices at once
curl -X POST http://localhost:8080/api/devices/bulk \
  -H "Content-Type: application/json" \
  -d '{"devices": [{"product_id": 27}, {"product_id": 32, "zone_count": 16}]}'

# Get specific device info
curl http://localhost:8080/api/devices/d073d5000001

# Update device state (power on, set color)
curl -X PATCH http://localhost:8080/api/devices/d073d5000001/state \
  -H "Content-Type: application/json" \
  -d '{"power_level": 65535, "color": {"hue": 21845, "saturation": 65535, "brightness": 32768, "kelvin": 3500}}'

# Delete a device
curl -X DELETE http://localhost:8080/api/devices/d073d5000001

# Get recent activity
curl http://localhost:8080/api/activity
```

---

## Monitoring Endpoints

### Get Server Statistics

```http
GET /api/stats
```

Returns server uptime, packet counts, error counts, and device count.

**Response (200 OK):**
```json
{
  "uptime_seconds": 123.45,
  "start_time": 1699564800.0,
  "device_count": 3,
  "packets_received": 1250,
  "packets_sent": 2100,
  "packets_received_by_type": {
    "2": 50,
    "101": 200,
    "102": 300
  },
  "packets_sent_by_type": {
    "3": 50,
    "107": 200,
    "116": 300
  },
  "error_count": 2,
  "activity_enabled": true
}
```

**Use Cases:**
- Monitor emulator health and uptime
- Track packet statistics by type
- Verify API is running
- Check error rates

---

### Get Recent Activity

```http
GET /api/activity
```

Returns the last 100 packet events (TX/RX) with timestamps and packet details.

**Response (200 OK):**
```json
[
  {
    "timestamp": 1699564923.456,
    "direction": "rx",
    "packet_type": 101,
    "packet_name": "GetColor",
    "device": "d073d5000001",
    "target": "00:00:00:00:00:00:00:00",
    "addr": "192.168.1.100:54321"
  },
  {
    "timestamp": 1699564923.457,
    "direction": "tx",
    "packet_type": 107,
    "packet_name": "State",
    "device": "d073d5000001",
    "target": "192.168.1.100",
    "addr": "192.168.1.100:54321"
  }
]
```

**Activity Event Fields:**
- `timestamp`: Unix timestamp of the packet
- `direction`: "rx" (received) or "tx" (transmitted)
- `packet_type`: Numeric packet type ID
- `packet_name`: Human-readable packet name
- `device`: Target device serial (if applicable)
- `target`: LIFX protocol target field
- `addr`: Client IP and port

**Use Cases:**
- Debugging LIFX client communication
- Verifying packet flow
- Monitoring protocol interactions
- Testing packet handling

**Note:** Activity logging must be enabled with `--api-activity` flag (default: true). Disable it to reduce traffic if not needed.

---

## Device Management Endpoints

### List All Devices

```http
GET /api/devices?offset=0&limit=20
```

Returns a paginated list of all emulated devices with their current configuration.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | int | `0` | Number of devices to skip (must be >= 0) |
| `limit` | int | `50` | Maximum number of devices to return (1-1000) |

**Response (200 OK):**
```json
{
  "devices": [
    {
      "serial": "d073d5000001",
      "label": "Living Room Light",
      "product": 27,
      "vendor": 1,
      "power_level": 65535,
      "has_color": true,
      "has_infrared": false,
      "has_multizone": false,
      "has_extended_multizone": false,
      "has_matrix": false,
      "has_hev": false,
      "zone_count": 0,
      "tile_count": 0,
      "color": {
        "hue": 32768,
        "saturation": 65535,
        "brightness": 65535,
        "kelvin": 3500
      },
      "zone_colors": [],
      "tile_devices": [],
      "version_major": 3,
      "version_minor": 70,
      "build_timestamp": 0,
      "group_label": "",
      "location_label": "",
      "uptime_ns": 123000000000,
      "wifi_signal": -45.5
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

**Envelope Fields:**
- `devices`: Array of device objects for the current page
- `total`: Total number of devices across all pages
- `offset`: The offset used for this request
- `limit`: The limit used for this request

**Device Info Fields:**
- `serial`: Unique device identifier (12-char hex string)
- `label`: Human-readable device label
- `product`: LIFX product ID
- `vendor`: Vendor ID (always 1 for LIFX)
- `power_level`: 0 (off) or 65535 (on)
- `has_*`: Boolean capability flags
- `zone_count`: Number of multizone zones (if multizone)
- `tile_count`: Number of tiles (if matrix device)
- `color`: Current HSBK color (if color-capable)
- `zone_colors`: Array of colors per zone (if multizone)
- `tile_devices`: Tile configuration and colors (if matrix)
- `version_major/minor`: Firmware version
- `build_timestamp`: Build timestamp (usually 0)
- `group_label`: Group assignment
- `location_label`: Location assignment
- `uptime_ns`: Device uptime in nanoseconds
- `wifi_signal`: WiFi signal strength in dBm

---

### Get Device Information

```http
GET /api/devices/{serial}
```

Returns detailed information about a specific device by its serial number.

**Path Parameters:**
- `serial`: Device serial number (e.g., `d073d5000001`)

**Response (200 OK):**
Same as list devices, but for a single device.

**Error Response (404):**
```json
{
  "detail": "Device d073d5000001 not found"
}
```

**Example:**
```bash
curl http://localhost:8080/api/devices/d073d5000001
```

---

### Create Device

```http
POST /api/devices
```

Creates a new emulated device by product ID. The device will be added to the emulator immediately.

**Request Body:**
```json
{
  "product_id": 27,
  "serial": "d073d5000099",
  "zone_count": 16,
  "tile_count": 5,
  "tile_width": 8,
  "tile_height": 8,
  "firmware_major": 3,
  "firmware_minor": 70
}
```

**Request Fields:**
- `product_id` (required): LIFX product ID from registry
- `serial` (optional): Device serial (auto-generated if not provided)
- `zone_count` (optional): Number of zones for multizone devices
- `tile_count` (optional): Number of tiles for matrix devices
- `tile_width` (optional): Width of each tile in zones
- `tile_height` (optional): Height of each tile in zones
- `firmware_major` (optional): Firmware major version
- `firmware_minor` (optional): Firmware minor version

**Response (201 Created):**
Same as get device response.

**Error Responses:**
- `400 Bad Request`: Invalid parameters
  ```json
  {
    "detail": "Failed to create device: Invalid product ID 9999"
  }
  ```
- `409 Conflict`: Duplicate serial
  ```json
  {
    "detail": "Device with serial d073d5000001 already exists"
  }
  ```

**Examples:**

```bash
# Create color light with auto-generated serial
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 27}'

# Create multizone device with specific zone count
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 32,
    "zone_count": 16
  }'

# Create tile device with specific count
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 55,
    "tile_count": 3
  }'

# Create device with specific serial
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 27,
    "serial": "d073d5cafe00"
  }'
```

---

### Update Device State

```http
PATCH /api/devices/{serial}/state
```

Updates the state of an existing device. All fields are optional — only the fields you include will be changed.

**Path Parameters:**
- `serial`: Device serial number (e.g., `d073d5000001`)

**Request Body:**
```json
{
  "power_level": 65535,
  "color": {
    "hue": 32768,
    "saturation": 65535,
    "brightness": 65535,
    "kelvin": 3500
  },
  "zone_colors": [
    {"hue": 0, "saturation": 65535, "brightness": 65535, "kelvin": 3500},
    {"hue": 10000, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
  ],
  "tile_colors": [
    {
      "tile_index": 0,
      "colors": [
        {"hue": 0, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
      ]
    }
  ]
}
```

**Request Fields (all optional):**
- `power_level`: Power level, 0 (off) or 65535 (on)
- `color`: HSBK color to set. On multizone devices, this fills all zones with the color. On matrix devices, this fills all tile pixels with the color.
- `zone_colors`: Array of HSBK colors replacing all zones on a multizone device. If the list is shorter than the zone count, the last color is repeated to fill the remaining zones. If longer, the list is truncated.
- `tile_colors`: Array of tile color updates for matrix devices. Each entry specifies a `tile_index` (0-4) and a `colors` array. Colors are padded or truncated to match the tile size.

**Response (200 OK):**
Full device info object (same format as Get Device).

**Error Responses:**
- `400 Bad Request`: Capability mismatch (e.g., setting `zone_colors` on a non-multizone device)
  ```json
  {
    "detail": "Device d073d5000001 does not support multizone"
  }
  ```
- `404 Not Found`: Device not found

**Examples:**

```bash
# Turn a device on
curl -X PATCH http://localhost:8080/api/devices/d073d5000001/state \
  -H "Content-Type: application/json" \
  -d '{"power_level": 65535}'

# Set color to red
curl -X PATCH http://localhost:8080/api/devices/d073d5000001/state \
  -H "Content-Type: application/json" \
  -d '{"color": {"hue": 0, "saturation": 65535, "brightness": 65535, "kelvin": 3500}}'

# Set power and color in one request
curl -X PATCH http://localhost:8080/api/devices/d073d5000001/state \
  -H "Content-Type: application/json" \
  -d '{
    "power_level": 65535,
    "color": {"hue": 21845, "saturation": 65535, "brightness": 32768, "kelvin": 3500}
  }'

# Set zone colors on a multizone device (short list is padded)
curl -X PATCH http://localhost:8080/api/devices/d073d5000002/state \
  -H "Content-Type: application/json" \
  -d '{
    "zone_colors": [
      {"hue": 0, "saturation": 65535, "brightness": 65535, "kelvin": 3500},
      {"hue": 21845, "saturation": 65535, "brightness": 65535, "kelvin": 3500}
    ]
  }'
```

---

### Create Multiple Devices (Bulk)

```http
POST /api/devices/bulk
```

Creates multiple emulated devices in a single request. If any device fails to create, all previously created devices in the batch are rolled back.

**Request Body:**
```json
{
  "devices": [
    {"product_id": 27},
    {"product_id": 32, "zone_count": 16},
    {"product_id": 55, "tile_count": 3, "serial": "d073d5cafe00"}
  ]
}
```

**Request Fields:**
- `devices` (required): Array of device creation requests (1-100 items). Each entry uses the same fields as [Create Device](#create-device).

**Response (201 Created):**
```json
[
  {"serial": "d073d5a00001", "product": 27, "...": "..."},
  {"serial": "d073d5a00002", "product": 32, "...": "..."},
  {"serial": "d073d5cafe00", "product": 55, "...": "..."}
]
```

Array of device info objects in the same order as the request.

**Error Responses:**
- `400 Bad Request`: Invalid parameters for any device in the batch
- `409 Conflict`: Duplicate serial within the batch, or a serial that already exists on the server. No devices are created.
  ```json
  {
    "detail": "Device with serial d073d5000001 already exists"
  }
  ```
- `422 Unprocessable Entity`: Empty device list or more than 100 devices

**Examples:**

```bash
# Create three devices at once
curl -X POST http://localhost:8080/api/devices/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {"product_id": 27},
      {"product_id": 27},
      {"product_id": 32, "zone_count": 16}
    ]
  }' | jq '.[].serial'

# Create devices with specific serials
curl -X POST http://localhost:8080/api/devices/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {"product_id": 27, "serial": "aabbccdd0001"},
      {"product_id": 27, "serial": "aabbccdd0002"}
    ]
  }'
```

---

### Delete Device

```http
DELETE /api/devices/{serial}
```

Removes an emulated device from the server. The device will stop responding to LIFX protocol packets.

**Path Parameters:**
- `serial`: Device serial number

**Response (204 No Content):**
No response body.

**Error Response (404):**
```json
{
  "detail": "Device d073d5000001 not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/devices/d073d5000001
```

---

### Delete All Devices

```http
DELETE /api/devices
```

Removes all emulated devices from the server. All devices will stop responding to LIFX protocol packets.

**Response (200 OK):**
```json
{
  "deleted": 5,
  "message": "Removed 5 device(s) from server"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/devices
```

**Note:** This only removes devices from memory.

---

## Code Examples

### Python

```python
import requests
import json

BASE_URL = "http://localhost:8080/api"

# Get server statistics
stats = requests.get(f"{BASE_URL}/stats").json()
print(f"Uptime: {stats['uptime_seconds']:.1f}s")
print(f"Devices: {stats['device_count']}")
print(f"Packets RX: {stats['packets_received']}")
print(f"Packets TX: {stats['packets_sent']}")

# List all devices (paginated)
data = requests.get(f"{BASE_URL}/devices").json()
print(f"Total devices: {data['total']}")
for device in data["devices"]:
    print(f"\nDevice: {device['label']} ({device['serial']})")
    print(f"  Product: {device['product']}")
    print(f"  Power: {'ON' if device['power_level'] > 0 else 'OFF'}")
    if device['has_color']:
        color = device['color']
        print(f"  Color: H={color['hue']} S={color['saturation']} B={color['brightness']} K={color['kelvin']}")

# Create a new device
response = requests.post(
    f"{BASE_URL}/devices",
    json={"product_id": 27, "zone_count": 16}
)
if response.status_code == 201:
    device = response.json()
    print(f"Created device: {device['serial']}")

# Get recent activity
activity = requests.get(f"{BASE_URL}/activity").json()
for event in activity[-5:]:  # Last 5 events
    direction = "RX" if event['direction'] == "rx" else "TX"
    print(f"{direction} {event['packet_name']} from {event['addr']}")

# Delete a device
serial = data["devices"][0]['serial']
requests.delete(f"{BASE_URL}/devices/{serial}")
print(f"Deleted device: {serial}")
```

### JavaScript/Node.js

```javascript
const BASE_URL = "http://localhost:8080/api";

// Get server statistics
async function getStats() {
    const response = await fetch(`${BASE_URL}/stats`);
    const stats = await response.json();
    console.log(`Uptime: ${stats.uptime_seconds.toFixed(1)}s`);
    console.log(`Devices: ${stats.device_count}`);
    console.log(`Packets RX: ${stats.packets_received}`);
    console.log(`Packets TX: ${stats.packets_sent}`);
}

// List all devices (paginated)
async function listDevices() {
    const response = await fetch(`${BASE_URL}/devices`);
    const data = await response.json();
    console.log(`Total devices: ${data.total}`);

    for (const device of data.devices) {
        console.log(`\nDevice: ${device.label} (${device.serial})`);
        console.log(`  Product: ${device.product}`);
        console.log(`  Power: ${device.power_level > 0 ? "ON" : "OFF"}`);
        if (device.has_color) {
            const c = device.color;
            console.log(`  Color: H=${c.hue} S=${c.saturation} B=${c.brightness} K=${c.kelvin}`);
        }
    }
}

// Create a new device
async function createDevice(productId) {
    const response = await fetch(`${BASE_URL}/devices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId })
    });

    if (response.status === 201) {
        const device = await response.json();
        console.log(`Created device: ${device.serial}`);
        return device;
    } else {
        const error = await response.json();
        console.error(`Failed: ${error.detail}`);
    }
}

// Delete a device
async function deleteDevice(serial) {
    const response = await fetch(`${BASE_URL}/devices/${serial}`, {
        method: "DELETE"
    });

    if (response.status === 204) {
        console.log(`Deleted device: ${serial}`);
    } else {
        const error = await response.json();
        console.error(`Failed: ${error.detail}`);
    }
}

// Get recent activity
async function getActivity() {
    const response = await fetch(`${BASE_URL}/activity`);
    const activities = await response.json();

    console.log("Recent activity:");
    for (const event of activities.slice(-5)) {
        const dir = event.direction === "rx" ? "RX" : "TX";
        console.log(`  ${dir} ${event.packet_name} from ${event.addr}`);
    }
}

// Run examples
getStats();
listDevices();
createDevice(27);
getActivity();
```

### cURL

```bash
# Get stats (pretty-print with jq)
curl http://localhost:8080/api/stats | jq

# List devices
curl http://localhost:8080/api/devices | jq '.devices[] | {serial, label, product}'

# List devices with pagination
curl 'http://localhost:8080/api/devices?offset=0&limit=10' | jq '.devices[] | .serial'

# Create color light
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 27}' | jq '.serial'

# Create multizone device with 16 zones
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -d '{"product_id": 32, "zone_count": 16}' | jq

# Get specific device
curl http://localhost:8080/api/devices/d073d5000001 | jq '{serial, label, power_level}'

# Get recent activity
curl http://localhost:8080/api/activity | jq '.[-5:] | .[] | {direction, packet_name, addr}'

# Delete device
curl -X DELETE http://localhost:8080/api/devices/d073d5000001 -v

# Delete all devices
curl -X DELETE http://localhost:8080/api/devices | jq
```

---

## Common Patterns

### Monitor Emulator Status

```python
import requests
import time

while True:
    try:
        stats = requests.get("http://localhost:8080/api/stats", timeout=2).json()
        print(f"Status: {stats['device_count']} devices, "
              f"{stats['packets_received']} RX, "
              f"{stats['packets_sent']} TX, "
              f"uptime {stats['uptime_seconds']:.0f}s")
    except:
        print("API unavailable")

    time.sleep(5)
```

### Maintain Minimum Device Count

```python
def ensure_min_devices(min_count, product_id):
    data = requests.get(f"{BASE_URL}/devices").json()
    current = data["total"]

    if current < min_count:
        needed = min_count - current
        requests.post(f"{BASE_URL}/devices/bulk",
                     json={"devices": [{"product_id": product_id}] * needed})
        print(f"Created {needed} device(s)")
```

### Log Activity to File

```python
import json
from datetime import datetime

while True:
    activity = requests.get(f"{BASE_URL}/activity").json()

    for event in activity:
        log_entry = {
            "timestamp": datetime.fromtimestamp(event['timestamp']).isoformat(),
            "direction": event['direction'],
            "packet": event['packet_name'],
            "device": event['device'],
            "addr": event['addr']
        }

        with open("emulator_activity.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
```

---

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `200 OK`: Successful GET/DELETE request with response body
- `201 Created`: Successful POST request (device creation)
- `204 No Content`: Successful DELETE request (no body)
- `400 Bad Request`: Invalid parameters or request body
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate serial)
- `503 Service Unavailable`: Feature not enabled (e.g., storage)

---

## See Also

- [Web Interface Guide](web-interface.md) - Browser-based monitoring dashboard
- [Scenario Management API](./scenario-api.md) - Test scenario configuration
