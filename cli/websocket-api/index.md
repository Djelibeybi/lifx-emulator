# WebSocket API

## Overview

The LIFX Emulator provides a WebSocket endpoint for real-time updates, eliminating the need for polling. Clients can subscribe to specific topics and receive push notifications when server state changes.

**Endpoint**: `ws://localhost:8080/ws`

**Benefits over REST polling**:

- Instant updates when devices change
- Lower latency for activity monitoring
- Reduced server load (no repeated polling)
- Efficient for dashboards and monitoring tools

## Quick Start

### Enable the API Server

```bash
# Start emulator with API server (enables WebSocket)
lifx-emulator --api

# Custom host and port
lifx-emulator --api --api-host 127.0.0.1 --api-port 9090
```

### Basic JavaScript Example

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  // Subscribe to topics
  ws.send(JSON.stringify({
    type: 'subscribe',
    topics: ['stats', 'devices', 'activity', 'scenarios']
  }));

  // Request full state sync
  ws.send(JSON.stringify({ type: 'sync' }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message.type, message.data);
};
```

### Python Example

```python
import asyncio
import json
import websockets

async def monitor_emulator():
    async with websockets.connect('ws://localhost:8080/ws') as ws:
        # Subscribe to all topics
        await ws.send(json.dumps({
            'type': 'subscribe',
            'topics': ['stats', 'devices', 'activity']
        }))

        # Request initial state
        await ws.send(json.dumps({'type': 'sync'}))

        # Listen for updates
        async for message in ws:
            data = json.loads(message)
            print(f"[{data['type']}] {data.get('data', data.get('message'))}")

asyncio.run(monitor_emulator())
```

______________________________________________________________________

## Client Messages

Messages sent from client to server.

### Subscribe to Topics

Subscribe to one or more topics to receive updates.

```json
{
  "type": "subscribe",
  "topics": ["stats", "devices", "activity", "scenarios"]
}
```

**Available Topics:**

| Topic       | Description                             |
| ----------- | --------------------------------------- |
| `stats`     | Server statistics (pushed every second) |
| `devices`   | Device add/remove/update events         |
| `activity`  | Packet activity events (RX/TX)          |
| `scenarios` | Scenario configuration changes          |

**Notes:**

- Subscribe can be called multiple times to add more topics
- Unknown topics are silently ignored
- Subscriptions persist for the lifetime of the connection

______________________________________________________________________

### Request State Sync

Request a full state snapshot for all subscribed topics.

```json
{
  "type": "sync"
}
```

**Response:**

```json
{
  "type": "sync",
  "data": {
    "stats": { ... },
    "devices": [ ... ],
    "activity": [ ... ],
    "scenarios": { ... }
  }
}
```

Only topics you've subscribed to are included in the sync response.

**Use Cases:**

- Initialize dashboard state on page load
- Recover state after reconnection
- Refresh full state on demand

______________________________________________________________________

## Server Messages

Messages pushed from server to clients.

### Stats Update

Pushed every second to clients subscribed to `stats`.

```json
{
  "type": "stats",
  "data": {
    "uptime_seconds": 123.45,
    "start_time": 1699564800.0,
    "device_count": 3,
    "packets_received": 1250,
    "packets_sent": 2100,
    "packets_received_by_type": { "2": 50, "101": 200 },
    "packets_sent_by_type": { "3": 50, "107": 200 },
    "error_count": 2,
    "activity_enabled": true
  }
}
```

______________________________________________________________________

### Device Added

Pushed when a new device is created.

```json
{
  "type": "device_added",
  "data": {
    "serial": "d073d5000001",
    "label": "New Light",
    "product": 27,
    "vendor": 1,
    "power_level": 0,
    "has_color": true,
    "has_infrared": false,
    "has_multizone": false,
    "has_extended_multizone": false,
    "has_matrix": false,
    "has_hev": false,
    "zone_count": 0,
    "tile_count": 0,
    "color": {
      "hue": 0,
      "saturation": 0,
      "brightness": 65535,
      "kelvin": 3500
    }
  }
}
```

______________________________________________________________________

### Device Removed

Pushed when a device is deleted.

```json
{
  "type": "device_removed",
  "data": {
    "serial": "d073d5000001"
  }
}
```

______________________________________________________________________

### Device Updated

Pushed when a device's state changes (power, color, zones, etc.).

```json
{
  "type": "device_updated",
  "data": {
    "serial": "d073d5000001",
    "changes": {
      "power_level": 65535,
      "color": {
        "hue": 21845,
        "saturation": 65535,
        "brightness": 32768,
        "kelvin": 3500
      }
    }
  }
}
```

The `changes` object contains only the fields that changed.

______________________________________________________________________

### Activity Event

Pushed for each packet received or sent.

```json
{
  "type": "activity",
  "data": {
    "timestamp": 1699564923.456,
    "direction": "rx",
    "packet_type": 101,
    "packet_name": "GetColor",
    "device": "d073d5000001",
    "target": "00:00:00:00:00:00:00:00",
    "addr": "192.168.1.100:54321"
  }
}
```

**Fields:**

| Field         | Description                           |
| ------------- | ------------------------------------- |
| `timestamp`   | Unix timestamp of the packet          |
| `direction`   | `rx` (received) or `tx` (transmitted) |
| `packet_type` | Numeric LIFX packet type ID           |
| `packet_name` | Human-readable packet name            |
| `device`      | Target device serial (if applicable)  |
| `target`      | LIFX protocol target field            |
| `addr`        | Client IP address and port            |

______________________________________________________________________

### Scenario Changed

Pushed when a scenario configuration is modified.

```json
{
  "type": "scenario_changed",
  "data": {
    "scope": "device",
    "identifier": "d073d5000001",
    "config": {
      "drop_packets": { "101": 50 },
      "response_delays": { "101": { "min_ms": 100, "max_ms": 500 } }
    }
  }
}
```

**Scope Values:**

| Scope      | Identifier     | Description                                         |
| ---------- | -------------- | --------------------------------------------------- |
| `global`   | `null`         | Applies to all devices                              |
| `device`   | Serial number  | Applies to specific device                          |
| `type`     | Device type    | Applies to device type (e.g., "color", "multizone") |
| `location` | Location label | Applies to devices in location                      |
| `group`    | Group label    | Applies to devices in group                         |

When a scenario is deleted, `config` will be `null`.

______________________________________________________________________

### Error Message

Sent when an invalid message is received.

```json
{
  "type": "error",
  "message": "Unknown message type: invalid_type"
}
```

______________________________________________________________________

## Sync Response Format

When requesting a sync, the response includes data for all subscribed topics:

```json
{
  "type": "sync",
  "data": {
    "stats": {
      "uptime_seconds": 123.45,
      "device_count": 2,
      ...
    },
    "devices": [
      {
        "serial": "d073d5000001",
        "label": "Living Room",
        "product": 27,
        ...
      },
      {
        "serial": "d073d5000002",
        "label": "Bedroom Strip",
        "product": 32,
        "zone_count": 16,
        ...
      }
    ],
    "activity": [
      {
        "timestamp": 1699564923.456,
        "direction": "rx",
        "packet_type": 101,
        ...
      }
    ],
    "scenarios": {
      "global": null,
      "devices": {
        "d073d5000001": { "drop_packets": { "101": 50 } }
      },
      "types": {},
      "locations": {},
      "groups": {}
    }
  }
}
```

______________________________________________________________________

## Common Patterns

### Dashboard with Live Updates

```javascript
class EmulatorDashboard {
  constructor(wsUrl = 'ws://localhost:8080/ws') {
    this.ws = null;
    this.devices = new Map();
    this.stats = {};
    this.connect(wsUrl);
  }

  connect(wsUrl) {
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        topics: ['stats', 'devices']
      }));
      this.ws.send(JSON.stringify({ type: 'sync' }));
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };

    this.ws.onclose = () => {
      // Reconnect after 2 seconds
      setTimeout(() => this.connect(wsUrl), 2000);
    };
  }

  handleMessage(msg) {
    switch (msg.type) {
      case 'sync':
        if (msg.data.stats) this.stats = msg.data.stats;
        if (msg.data.devices) {
          msg.data.devices.forEach(d => this.devices.set(d.serial, d));
        }
        break;
      case 'stats':
        this.stats = msg.data;
        break;
      case 'device_added':
        this.devices.set(msg.data.serial, msg.data);
        break;
      case 'device_removed':
        this.devices.delete(msg.data.serial);
        break;
      case 'device_updated':
        const device = this.devices.get(msg.data.serial);
        if (device) Object.assign(device, msg.data.changes);
        break;
    }
    this.render();
  }

  render() {
    // Update your UI here
    console.log('Stats:', this.stats);
    console.log('Devices:', [...this.devices.values()]);
  }
}

const dashboard = new EmulatorDashboard();
```

______________________________________________________________________

### Activity Monitor with Filtering

```javascript
class ActivityMonitor {
  constructor(wsUrl = 'ws://localhost:8080/ws') {
    this.activities = [];
    this.maxActivities = 100;
    this.filters = { direction: null, packetType: null };

    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'subscribe',
        topics: ['activity']
      }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'activity') {
        this.addActivity(msg.data);
      }
    };
  }

  addActivity(activity) {
    this.activities.unshift(activity);
    if (this.activities.length > this.maxActivities) {
      this.activities.pop();
    }
    this.render();
  }

  getFiltered() {
    return this.activities.filter(a => {
      if (this.filters.direction && a.direction !== this.filters.direction) {
        return false;
      }
      if (this.filters.packetType && a.packet_type !== this.filters.packetType) {
        return false;
      }
      return true;
    });
  }

  render() {
    const filtered = this.getFiltered();
    console.table(filtered.slice(0, 10));
  }
}

const monitor = new ActivityMonitor();
```

______________________________________________________________________

### Python Async Monitor

```python
import asyncio
import json
from datetime import datetime
import websockets

class EmulatorMonitor:
    def __init__(self, url: str = 'ws://localhost:8080/ws'):
        self.url = url
        self.devices: dict = {}
        self.stats: dict = {}

    async def connect(self):
        async with websockets.connect(self.url) as ws:
            # Subscribe to updates
            await ws.send(json.dumps({
                'type': 'subscribe',
                'topics': ['stats', 'devices', 'activity']
            }))

            # Get initial state
            await ws.send(json.dumps({'type': 'sync'}))

            # Process messages
            async for message in ws:
                await self.handle_message(json.loads(message))

    async def handle_message(self, msg: dict):
        msg_type = msg.get('type')
        data = msg.get('data', {})

        if msg_type == 'sync':
            self.stats = data.get('stats', {})
            for device in data.get('devices', []):
                self.devices[device['serial']] = device
            print(f"Synced: {len(self.devices)} devices")

        elif msg_type == 'stats':
            self.stats = data
            print(f"Stats: {data['device_count']} devices, "
                  f"{data['packets_received']} RX, {data['packets_sent']} TX")

        elif msg_type == 'device_added':
            self.devices[data['serial']] = data
            print(f"Device added: {data['serial']} ({data['label']})")

        elif msg_type == 'device_removed':
            self.devices.pop(data['serial'], None)
            print(f"Device removed: {data['serial']}")

        elif msg_type == 'device_updated':
            if data['serial'] in self.devices:
                self.devices[data['serial']].update(data['changes'])
            print(f"Device updated: {data['serial']} - {list(data['changes'].keys())}")

        elif msg_type == 'activity':
            ts = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S.%f')[:-3]
            print(f"[{ts}] {data['direction'].upper()} {data['packet_name']} "
                  f"({data['packet_type']}) -> {data.get('device', 'broadcast')}")

if __name__ == '__main__':
    monitor = EmulatorMonitor()
    asyncio.run(monitor.connect())
```

______________________________________________________________________

## Connection Management

### Reconnection Strategy

WebSocket connections may drop due to network issues. Implement automatic reconnection:

```javascript
function createReconnectingWebSocket(url, options = {}) {
  const {
    reconnectDelay = 2000,
    maxReconnectDelay = 30000,
    onMessage,
    onConnect
  } = options;

  let ws = null;
  let delay = reconnectDelay;

  function connect() {
    ws = new WebSocket(url);

    ws.onopen = () => {
      delay = reconnectDelay; // Reset delay on successful connect
      if (onConnect) onConnect(ws);
    };

    ws.onmessage = (event) => {
      if (onMessage) onMessage(JSON.parse(event.data));
    };

    ws.onclose = () => {
      // Exponential backoff
      setTimeout(connect, delay);
      delay = Math.min(delay * 1.5, maxReconnectDelay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  connect();

  return {
    send: (data) => ws?.send(JSON.stringify(data)),
    close: () => ws?.close()
  };
}

// Usage
const ws = createReconnectingWebSocket('ws://localhost:8080/ws', {
  onConnect: (ws) => {
    ws.send(JSON.stringify({ type: 'subscribe', topics: ['stats', 'devices'] }));
    ws.send(JSON.stringify({ type: 'sync' }));
  },
  onMessage: (msg) => {
    console.log('Received:', msg);
  }
});
```

______________________________________________________________________

## See Also

- [Device Management API](https://djelibeybi.github.io/lifx-emulator/cli/device-management-api/index.md) - REST API for device CRUD operations
- [Scenario API](https://djelibeybi.github.io/lifx-emulator/cli/scenario-api/index.md) - REST API for scenario configuration
- [Web Interface Guide](https://djelibeybi.github.io/lifx-emulator/cli/web-interface/index.md) - Browser-based dashboard
- [Testing Scenarios](https://djelibeybi.github.io/lifx-emulator/guide/testing-scenarios/index.md) - Using scenarios for protocol testing
