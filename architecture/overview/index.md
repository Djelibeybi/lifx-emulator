# Architecture Overview

The LIFX Emulator is built with a layered architecture that mirrors real LIFX devices.

## High-Level Architecture

```
graph TB
    Client[LIFX Client Library]
    Server[EmulatedLifxServer]
    Device1[EmulatedLifxDevice]
    Device2[EmulatedLifxDevice]
    Device3[EmulatedLifxDevice]
    Protocol[Protocol Layer]
    State[DeviceState]

    Client -->|UDP Packets| Server
    Server -->|Route by Serial| Device1
    Server -->|Route by Serial| Device2
    Server -->|Route by Serial| Device3
    Device1 -->|Parse/Pack| Protocol
    Device2 -->|Parse/Pack| Protocol
    Device3 -->|Parse/Pack| Protocol
    Device1 -->|Read/Write| State
    Device2 -->|Read/Write| State
    Device3 -->|Read/Write| State
```

## Core Components

### 1. Server Layer (`EmulatedLifxServer`)

The server layer handles:

- UDP socket management
- Packet reception and sending
- Device routing by serial (encoded in target field)
- Broadcast packet distribution

**Key Responsibilities:**

- Listen on configured IP and port
- Parse packet headers to determine routing
- Forward packets to appropriate devices
- Send responses back to clients

### 2. Device Layer (`EmulatedLifxDevice`)

Each device instance represents a virtual LIFX device:

- Maintains device state
- Processes incoming packets
- Generates response packets
- Handles device-specific logic

**Key Responsibilities:**

- Process packet type routing
- Update state based on commands
- Generate appropriate responses
- Implement device capabilities

### 3. Protocol Layer

The protocol layer implements LIFX LAN protocol:

- Binary packet serialization/deserialization
- Header parsing and generation
- Packet type definitions
- Type conversions

**Components:**

- `LifxHeader` - 36-byte header structure
- Packet classes - 44+ packet type definitions
- `Serializer` - Binary packing/unpacking
- Protocol types - `LightHsbk`, `TileStateDevice`, etc.

### 4. State Layer (`DeviceState`)

Device state is stored in a dataclass:

- Device identity (serial, label, product)
- Capability flags (color, infrared, multizone, etc.)
- Light state (power, color, zones, tiles)
- Firmware version
- Network configuration

## Packet Flow

```
sequenceDiagram
    participant Client
    participant Server
    participant Device
    participant Protocol
    participant State

    Client->>Server: UDP Packet
    Server->>Protocol: Parse Header
    Protocol-->>Server: LifxHeader
    Server->>Device: Route by target serial
    Device->>Protocol: Unpack Payload
    Protocol-->>Device: Packet Object
    Device->>State: Update State
    Device->>Protocol: Generate Response
    Protocol-->>Device: Packed Response
    Device-->>Server: Response Packet(s)
    Server->>Client: UDP Response
```

### Detailed Flow

1. **Reception**
1. Client sends UDP packet to server
1. Server receives bytes on socket
1. **Header Parsing**
1. Extract 36-byte header
1. Parse: target (serial + padding), packet type, flags
1. Determine if broadcast or targeted
1. **Device Routing**
1. If broadcast (tagged=True or target=000000000000): forward to all devices
1. If targeted: find device by serial (encoded in target field)
1. If not found: ignore packet
1. **Packet Processing**
1. Device unpacks payload using packet class
1. Determines packet type (e.g., LightSetColor)
1. Routes to specific handler method
1. **State Update**
1. Handler reads current state
1. Applies command logic
1. Updates state fields
1. **Response Generation**
1. If `res_required=True`: generate state response
1. If `ack_required=True`: generate acknowledgment
1. Create response header with sequence number
1. **Response Sending**
1. Pack response packets to bytes
1. Send back to client via UDP

## Layer Details

### Server Layer

```python
class EmulatedLifxServer:
    """UDP server that routes packets to devices."""

    def __init__(self, devices, bind_address, port):
        self._devices = {d.state.serial: d for d in devices}
        self._bind_address = bind_address
        self._port = port

    async def start(self):
        """Start UDP server."""
        pass

    def handle_packet(self, data, addr):
        """Route incoming packet to device(s)."""
        # Parse header
        # Find target device(s)
        # Process and send responses
        pass
```

### Device Layer

```python
class EmulatedLifxDevice:
    """Virtual LIFX device with stateful behavior."""

    def __init__(self, state: DeviceState):
        self.state = state
        self.scenarios = {}  # Testing scenarios

    def process_packet(self, header, packet):
        """Process incoming packet and generate responses."""
        # Handle acknowledgments
        # Route to packet-specific handler
        # Generate response packets
        pass

    def _handle_light_set_color(self, packet):
        """Handle LightSetColor command."""
        # Update self.state.color
        # Return response if needed
        pass
```

### Protocol Layer

```python
class LifxHeader:
    """36-byte LIFX packet header."""

    def __init__(self, ...):
        self.target = target        # 6-byte serial + 2 null bytes
        self.source = source        # 4-byte identifier
        self.sequence = sequence    # 1-byte sequence number
        self.pkt_type = pkt_type    # Packet type number
        self.tagged = tagged        # tagged
        # ... more fields

    def pack(self) -> bytes:
        """Pack header to 36 bytes."""
        pass

    @classmethod
    def unpack(cls, data: bytes):
        """Parse 36 bytes to header."""
        pass
```

### State Layer

```python
@dataclass
class DeviceState:
    """Device state storage."""

    # Identity
    serial: str
    label: str
    vendor: int
    product: int

    # Capabilities
    has_color: bool
    has_infrared: bool
    has_multizone: bool
    has_matrix: bool
    has_hev: bool

    # Light state
    power_level: int
    color: LightHsbk
    zone_colors: list[LightHsbk]
    tile_devices: list[TileState]

    # ... more fields
```

## Capability Flags

Devices advertise capabilities through boolean flags:

| Flag                     | Capability     | Example Products       |
| ------------------------ | -------------- | ---------------------- |
| `has_color`              | Full RGB color | LIFX A19, LIFX Beam    |
| `has_infrared`           | IR brightness  | LIFX A19 Night Vision  |
| `has_multizone`          | Linear zones   | LIFX Z, LIFX Beam      |
| `has_extended_multizone` | >16 zones      | LIFX Beam              |
| `has_matrix`             | 2D zone grid   | LIFX Tile, LIFX Candle |
| `has_hev`                | HEV cleaning   | LIFX Clean             |

## Packet Types

The emulator implements 44+ packet types across multiple domains:

### Device Domain (1-45)

- GetService (2) / StateService (3)
- GetVersion (32) / StateVersion (33)
- GetLabel (23) / StateLabel (25)
- SetLabel (24)
- GetPower (20) / StatePower (22)
- SetPower (21)

### Light Domain (100-122)

- LightGet (101) / LightState (107)
- LightSetColor (102)
- LightSetWaveform (103)
- LightGetInfrared (120) / LightStateInfrared (121)
- LightSetInfrared (122)

### MultiZone Domain (500-512)

- GetColorZones (502) / StateZone (503)
- StateMultiZone (506)
- SetColorZones (501)
- GetMultiZoneEffect (507) / StateMultiZoneEffect (508)
- SetMultiZoneEffect (509)
- SetExtendedColorZones (510)
- GetExtendedColorZones (511) / StateExtendedColorZones (512)

### Tile Domain (700-719)

- GetDeviceChain (701) / StateDeviceChain (702)
- SetUserPosition (703)
- GetTileState64 (707) / StateTileState64 (711)
- SetTileState64 (715)
- GetTileEffect (718) / StateTileEffect (719)

See [Protocol Layer](../protocol/) for complete packet documentation.

## Design Patterns

### Factory Pattern

Factory functions encapsulate device creation:

```python
def create_color_light(serial=None):
    """Create LIFX A19 with sensible defaults."""
    return create_device(27, serial=serial)
```

### Strategy Pattern

Packet handlers implement strategy pattern:

```python
def process_packet(self, header, packet):
    handler_map = {
        LightSetColor: self._handle_light_set_color,
        LightSetPower: self._handle_light_set_power,
        # ... more handlers
    }
    handler = handler_map.get(type(packet))
    if handler:
        return handler(packet)
```

### State Pattern

Device state changes based on received commands:

```python
def _handle_light_set_color(self, packet):
    self.state.color = packet.color
    self.state.power_level = packet.color.brightness
```

## Concurrency Model

The emulator uses Python's asyncio:

- **Single-threaded**: All operations run in the event loop
- **Non-blocking**: Uses async/await for I/O
- **Datagram protocol**: UDP doesn't maintain connections
- **Stateful devices**: Each device maintains independent state

```python
async with EmulatedLifxServer(devices, "127.0.0.1", 56700) as server:
    # Server runs in background tasks
    # Your test code runs concurrently
    await asyncio.sleep(1)
```

## Testing Architecture

The emulator supports advanced testing scenarios:

```python
device.scenarios = {
    'drop_packets': {101: 1.0},      # Drop all LightGet packets
    'response_delays': {102: 0.5},   # Delay SetColor by 500ms
    'malformed_packets': [107],      # Truncate StateLight
    'invalid_field_values': [22],    # Send invalid StatePower
    'partial_responses': [506],      # Incomplete multizone response
}
```

## Next Steps

- [Packet Flow](../packet-flow/) - Detailed packet processing
- [Protocol Layer](../protocol/) - Protocol implementation details
- [Device State](../device-state/) - State management
- [Server API](../../library/server/) - Server documentation
