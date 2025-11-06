# Protocol API Reference

> LIFX LAN Protocol implementation - packet types, headers, and serialization

The protocol module provides a complete implementation of the LIFX LAN binary protocol, including packet definitions, header parsing, type serialization, and packet registry management.

---

## Table of Contents

### Core Components

- [LifxHeader](#lifxheader) - Packet header structure
- [Packet Types](#packet-types) - Protocol packet definitions
- [Protocol Types](#protocol-types) - Structured data types (HSBK, TileState, etc.)
- [Packet Registry](#packet-registry) - Mapping packet type numbers to classes

### Concepts

- [Binary Format Overview](#binary-format-overview)
- [Serialization and Deserialization](#serialization-and-deserialization)
- [Working with Packets](#working-with-packets)
- [Type Conversion](#type-conversion)

---

## LifxHeader

The LIFX protocol header is a 36-byte structure that precedes every packet payload.

### Structure

```python
@dataclass
class LifxHeader:
    # Frame
    size: int = 0                # Total packet size (header + payload)
    origin: int = 0              # Message origin (always 0)
    tagged: bool = False         # Broadcast flag (True = all devices)
    addressable: bool = True     # Addressable flag (always True)
    protocol: int = 1024         # Protocol number (always 1024)
    source: int = 0              # Unique client identifier

    # Frame Address
    target: bytes = b'\x00' * 8  # 6-byte serial + 2 null bytes
    ack_required: bool = False   # Request acknowledgment
    res_required: bool = False   # Request response
    sequence: int = 0            # Message sequence number (0-255)

    # Protocol Header
    pkt_type: int = 0            # Packet type number (e.g., 2, 101, 116)
```

### Key Fields

#### `tagged` (bool)

- **`True`**: Broadcast packet - sent to all devices on network
- **`False`**: Unicast packet - sent to specific device (requires valid `target`)

#### `target` (bytes)

- 8-byte field: 6-byte device serial + 2 null bytes
- Example: `b'\xd0\x73\xd5\x00\x00\x01\x00\x00'` for serial `d073d5000001`
- All zeros (`b'\x00' * 8`) when `tagged=True`

#### `ack_required` (bool)

- **`True`**: Device must send acknowledgment (packet type 45)
- **`False`**: No acknowledgment needed

#### `res_required` (bool)

- **`True`**: Device must send response packet (e.g., `State` for `Get`)
- **`False`**: No response packet expected

#### `source` (int)

- 32-bit client identifier
- Used to match responses to requests
- Should be unique per client instance

#### `sequence` (int)

- 8-bit sequence number (0-255, wraps around)
- Used to match responses to specific requests
- Client should increment for each request

#### `pkt_type` (int)

- Identifies the packet payload type
- Common types: 2 (`GetService`), 101 (`Get`), 102 (`SetColor`), 107 (`State`), etc.

### Methods

#### `pack() -> bytes`

Serialize header to 36-byte binary format.

**Returns:** `bytes` - 36-byte header

**Example:**
```python
from lifx_emulator.protocol.header import LifxHeader

header = LifxHeader(
    size=36,
    source=12345,
    target=bytes.fromhex("d073d5000001") + b'\x00\x00',
    res_required=True,
    sequence=1,
    pkt_type=101,  # Light.Get
)
raw_header = header.pack()
# Returns: 36 bytes
```

#### `unpack(data: bytes) -> LifxHeader`

Parse 36 bytes into a LifxHeader object.

**Parameters:**
- **`data`** (`bytes`) - 36-byte header data

**Returns:** `LifxHeader` - Parsed header object

**Example:**
```python
raw_header = sock.recv(36)
header = LifxHeader.unpack(raw_header)
print(f"Packet type: {header.pkt_type}")
print(f"Source: {header.source}")
print(f"Target: {header.target.hex()}")
```

---

## Packet Types

The protocol module provides classes for all LIFX protocol packets, organized into namespaces:

### Packet Organization

```python
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile, Relay, Hev

# Device discovery and information
Device.GetService             # Type 2
Device.StateService           # Type 3
Device.GetHostInfo            # Type 12
Device.StateHostInfo          # Type 13
Device.GetVersion             # Type 32
Device.StateVersion           # Type 33
Device.GetLocation            # Type 48
Device.StateLocation          # Type 50
Device.GetGroup               # Type 51
Device.StateGroup             # Type 53
Device.Acknowledgement        # Type 45
Device.EchoRequest            # Type 58
Device.EchoResponse           # Type 59

# Light control (all color-capable devices)
Light.Get                     # Type 101
Light.SetColor                # Type 102
Light.SetWaveform             # Type 103
Light.State                   # Type 107
Light.GetPower                # Type 116
Light.SetPower                # Type 117
Light.StatePower              # Type 118
Light.GetInfrared             # Type 120 (infrared devices only)
Light.SetInfrared             # Type 122
Light.StateInfrared           # Type 121

# Multizone control (strips/beams)
MultiZone.SetColorZones       # Type 501
MultiZone.GetColorZones       # Type 502
MultiZone.StateZone           # Type 503
MultiZone.StateMultiZone      # Type 506
MultiZone.SetMultiZoneEffect  # Type 508
MultiZone.GetMultiZoneEffect  # Type 509
MultiZone.StateMultiZoneEffect # Type 510

# Extended multizone (>16 zones)
MultiZone.SetExtendedColorZones       # Type 510
MultiZone.GetExtendedColorZones       # Type 511
MultiZone.StateExtendedColorZones     # Type 512

# Tile/Matrix control (2D arrangements)
Tile.GetDeviceChain           # Type 701
Tile.StateDeviceChain         # Type 702
Tile.Get64                    # Type 707
Tile.State64                  # Type 711
Tile.Set64                    # Type 715
Tile.SetUserPosition          # Type 703
Tile.GetTileEffect            # Type 718
Tile.SetTileEffect            # Type 719
Tile.StateTileEffect          # Type 720

# HEV (germicidal light)
Hev.GetCycle                  # Type 142
Hev.SetCycle                  # Type 143
Hev.StateCycle                # Type 144
Hev.GetConfiguration          # Type 145
Hev.StateConfiguration        # Type 146
```

### Packet Class Structure

Each packet class has:

- **`PKT_TYPE`**: Class constant with packet type number
- **`pack()`**: Serialize to binary format
- **`unpack(data)`**: Parse from binary format

### Example: Light.SetColor

```python
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.protocol_types import LightHsbk

# Create SetColor packet
packet = Light.SetColor(
    reserved=0,
    color=LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500),
    duration_ms=1000,
)

# Serialize to bytes
raw_payload = packet.pack()

# Parse from bytes
received_packet = Light.SetColor.unpack(raw_payload)
print(f"Color: H={received_packet.color.hue} S={received_packet.color.saturation}")
print(f"Duration: {received_packet.duration_ms}ms")
```

### Example: MultiZone.GetColorZones

```python
from lifx_emulator.protocol.packets import MultiZone

# Request zones 0-7
packet = MultiZone.GetColorZones(
    start_index=0,
    end_index=7,
)

raw_payload = packet.pack()
```

### Example: Tile.Get64

```python
from lifx_emulator.protocol.packets import Tile

# Request 8x8 rectangle starting at (0,0) from tile 0
packet = Tile.Get64(
    tile_index=0,
    length=1,      # Not used for Get64
    rect_x=0,
    rect_y=0,
    rect_width=8,
)

raw_payload = packet.pack()
```

---

## Protocol Types

Protocol types are structured data types used within packets.

### LightHsbk

HSBK color representation (Hue, Saturation, Brightness, Kelvin).

```python
@dataclass
class LightHsbk:
    hue: int          # 0-65535 (0° to 360°)
    saturation: int   # 0-65535 (0% to 100%)
    brightness: int   # 0-65535 (0% to 100%)
    kelvin: int       # 1500-9000 (color temperature)
```

**Color Conversion:**
- **Hue**: `degrees * 65535 / 360`
- **Saturation**: `percent * 65535 / 100`
- **Brightness**: `percent * 65535 / 100`
- **Kelvin**: Absolute value (e.g., 3500 for warm white)

**Examples:**
```python
from lifx_emulator.protocol.protocol_types import LightHsbk

# Red at 50% brightness
red = LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500)

# Green at full brightness
green = LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500)

# Blue at 75% brightness
blue = LightHsbk(hue=43690, saturation=65535, brightness=49152, kelvin=3500)

# Warm white (no color)
warm_white = LightHsbk(hue=0, saturation=0, brightness=65535, kelvin=2700)

# Cool white (no color)
cool_white = LightHsbk(hue=0, saturation=0, brightness=65535, kelvin=6500)
```

### TileStateDevice

Tile position and metadata in a matrix chain.

```python
@dataclass
class TileStateDevice:
    accel_meas_x: int
    accel_meas_y: int
    accel_meas_z: int
    user_x: float         # User-configured X position
    user_y: float         # User-configured Y position
    width: int            # Tile width in pixels (e.g., 8)
    height: int           # Tile height in pixels (e.g., 8)
    device_version_vendor: int
    device_version_product: int
    device_version_version: int
    firmware_build: int
    firmware_version_minor: int
    firmware_version_major: int
```

### Enums

The protocol defines several enums for packet fields:

```python
from lifx_emulator.protocol.protocol_types import (
    DeviceService,
    LightWaveform,
    LightLastHevCycleResult,
    MultiZoneEffectType,
    MultiZoneApplicationRequest,
    TileEffectType,
)

# Service types
DeviceService.UDP                          # 1

# Waveform types for Light.SetWaveform
LightWaveform.SAW                          # 0
LightWaveform.SINE                         # 1
LightWaveform.HALF_SINE                    # 2
LightWaveform.TRIANGLE                     # 3
LightWaveform.PULSE                        # 4

# Multizone effects
MultiZoneEffectType.OFF                    # 0
MultiZoneEffectType.MOVE                   # 1

# Tile effects
TileEffectType.OFF                         # 0
TileEffectType.MORPH                       # 2
TileEffectType.FLAME                       # 3
```

---

## Packet Registry

The `PACKET_REGISTRY` maps packet type numbers to packet classes.

### Usage

```python
from lifx_emulator.protocol.packets import PACKET_REGISTRY, get_packet_class

# Get packet class by type number
packet_class = PACKET_REGISTRY[102]  # Light.SetColor
print(packet_class.PKT_TYPE)  # 102

# Or use the helper function
packet_class = get_packet_class(102)

# Parse unknown packet type
raw_payload = receive_payload()
packet_class = get_packet_class(header.pkt_type)
if packet_class:
    packet = packet_class.unpack(raw_payload)
else:
    print(f"Unknown packet type: {header.pkt_type}")
```

### Complete Packet Type List

| Type | Packet | Description |
|------|--------|-------------|
| 2 | `Device.GetService` | Device discovery request |
| 3 | `Device.StateService` | Device discovery response |
| 12 | `Device.GetHostInfo` | Get host MCU info |
| 13 | `Device.StateHostInfo` | Host MCU info response |
| 14 | `Device.GetHostFirmware` | Get host firmware |
| 15 | `Device.StateHostFirmware` | Host firmware response |
| 16 | `Device.GetWifiInfo` | Get WiFi info |
| 17 | `Device.StateWifiInfo` | WiFi info response |
| 18 | `Device.GetWifiFirmware` | Get WiFi firmware |
| 19 | `Device.StateWifiFirmware` | WiFi firmware response |
| 20 | `Device.GetPower` | Get device power |
| 21 | `Device.SetPower` | Set device power |
| 22 | `Device.StatePower` | Device power response |
| 23 | `Device.GetLabel` | Get device label |
| 24 | `Device.SetLabel` | Set device label |
| 25 | `Device.StateLabel` | Device label response |
| 32 | `Device.GetVersion` | Get firmware version |
| 33 | `Device.StateVersion` | Firmware version response |
| 34 | `Device.GetInfo` | Get device info |
| 35 | `Device.StateInfo` | Device info response |
| 45 | `Device.Acknowledgement` | Acknowledgment response |
| 48 | `Device.GetLocation` | Get location |
| 50 | `Device.StateLocation` | Location response |
| 51 | `Device.GetGroup` | Get group |
| 53 | `Device.StateGroup` | Group response |
| 58 | `Device.EchoRequest` | Echo request |
| 59 | `Device.EchoResponse` | Echo response |
| 101 | `Light.Get` | Get light state |
| 102 | `Light.SetColor` | Set color |
| 103 | `Light.SetWaveform` | Set waveform effect |
| 107 | `Light.State` | Light state response |
| 116 | `Light.GetPower` | Get light power |
| 117 | `Light.SetPower` | Set light power |
| 118 | `Light.StatePower` | Light power response |
| 120 | `Light.GetInfrared` | Get IR brightness |
| 121 | `Light.StateInfrared` | IR brightness response |
| 122 | `Light.SetInfrared` | Set IR brightness |
| 142 | `Hev.GetCycle` | Get HEV cycle |
| 143 | `Hev.SetCycle` | Set HEV cycle |
| 144 | `Hev.StateCycle` | HEV cycle response |
| 501 | `MultiZone.SetColorZones` | Set zone colors |
| 502 | `MultiZone.GetColorZones` | Get zone colors |
| 503 | `MultiZone.StateZone` | Single zone response |
| 506 | `MultiZone.StateMultiZone` | Multiple zones response |
| 508 | `MultiZone.SetMultiZoneEffect` | Set zone effect |
| 509 | `MultiZone.GetMultiZoneEffect` | Get zone effect |
| 510 | `MultiZone.StateMultiZoneEffect` | Zone effect response |
| 511 | `MultiZone.GetExtendedColorZones` | Get extended zones |
| 512 | `MultiZone.StateExtendedColorZones` | Extended zones response |
| 513 | `MultiZone.SetExtendedColorZones` | Set extended zones |
| 701 | `Tile.GetDeviceChain` | Get tile chain info |
| 702 | `Tile.StateDeviceChain` | Tile chain response |
| 703 | `Tile.SetUserPosition` | Set tile position |
| 707 | `Tile.Get64` | Get tile colors (64 zones) |
| 711 | `Tile.State64` | Tile colors response |
| 715 | `Tile.Set64` | Set tile colors |
| 718 | `Tile.GetTileEffect` | Get tile effect |
| 719 | `Tile.SetTileEffect` | Set tile effect |
| 720 | `Tile.StateTileEffect` | Tile effect response |

---

## Binary Format Overview

### Packet Structure

Every LIFX packet consists of:

1. **Header** (36 bytes) - See [LifxHeader](#lifxheader)
2. **Payload** (variable length) - Packet-specific data

```
┌─────────────────────────────────────┐
│         Header (36 bytes)           │
│  - Frame (8 bytes)                  │
│  - Frame Address (16 bytes)         │
│  - Protocol Header (12 bytes)       │
├─────────────────────────────────────┤
│         Payload (variable)          │
│  - Packet-specific fields           │
└─────────────────────────────────────┘
```

### Header Binary Layout

```
Bytes 0-1:   Size (uint16, little-endian)
Bytes 2-3:   Protocol/Origin/Tagged/Addressable (bitfield)
Bytes 4-7:   Source (uint32, little-endian)
Bytes 8-15:  Target (6-byte MAC + 2 reserved bytes)
Bytes 16-21: Reserved
Byte  22:    Ack/Res flags + reserved bits
Byte  23:    Sequence (uint8)
Bytes 24-31: Reserved
Bytes 32-33: Packet type (uint16, little-endian)
Bytes 34-35: Reserved
```

### Payload Encoding

Payload fields are serialized using little-endian byte order:

- **Integers**: `uint8`, `uint16`, `uint32`, `uint64`
- **Floats**: `float32` (IEEE 754)
- **Booleans**: `uint8` (0=False, 1=True)
- **Strings**: UTF-8 encoded, null-padded to fixed length
- **Bytes**: Raw byte arrays
- **Nested types**: Recursively serialized structures
- **Arrays**: Consecutive serialized elements

---

## Serialization and Deserialization

### Packing (Python → Binary)

```python
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.protocol_types import LightHsbk

# Create header
header = LifxHeader(
    size=0,  # Will be calculated
    source=12345,
    target=bytes.fromhex("d073d5000001") + b'\x00\x00',
    res_required=True,
    sequence=1,
    pkt_type=102,  # SetColor
)

# Create packet
packet = Light.SetColor(
    reserved=0,
    color=LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500),
    duration_ms=1000,
)

# Pack to binary
payload = packet.pack()
header.size = 36 + len(payload)
header_bytes = header.pack()

# Send over UDP
full_packet = header_bytes + payload
sock.sendto(full_packet, (device_ip, 56700))
```

### Unpacking (Binary → Python)

```python
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import get_packet_class

# Receive packet
data, addr = sock.recvfrom(1024)

# Parse header
header = LifxHeader.unpack(data[:36])
print(f"Received packet type: {header.pkt_type}")

# Parse payload
packet_class = get_packet_class(header.pkt_type)
if packet_class:
    payload_data = data[36:]
    packet = packet_class.unpack(payload_data)
    print(f"Packet: {packet}")
else:
    print(f"Unknown packet type: {header.pkt_type}")
```

---

## Working with Packets

### Complete Request/Response Example

```python
import socket
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.protocol_types import LightHsbk

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.0)

# Build GetService request (discovery)
header = LifxHeader(
    size=36,
    tagged=True,  # Broadcast
    source=12345,
    res_required=True,
    sequence=1,
    pkt_type=2,  # GetService
)

# Send discovery
sock.sendto(header.pack(), ('<broadcast>', 56700))

# Receive StateService response
data, addr = sock.recvfrom(1024)
resp_header = LifxHeader.unpack(data[:36])
print(f"Device found at {addr}: serial={resp_header.target[:6].hex()}")

# Get light state
header = LifxHeader(
    size=36,
    source=12345,
    target=resp_header.target,
    res_required=True,
    sequence=2,
    pkt_type=101,  # Light.Get
)
sock.sendto(header.pack(), addr)

# Receive Light.State response
data, addr = sock.recvfrom(1024)
resp_header = LifxHeader.unpack(data[:36])
state = Light.State.unpack(data[36:])
print(f"Color: H={state.color.hue} S={state.color.saturation} B={state.color.brightness}")
print(f"Power: {state.power}")
print(f"Label: {state.label}")

sock.close()
```

### Handling Acknowledgments

```python
# Request acknowledgment
header = LifxHeader(
    size=36 + len(payload),
    source=12345,
    target=device_target,
    ack_required=True,  # Request ack
    res_required=False,  # Don't need state response
    sequence=3,
    pkt_type=117,  # SetPower
)

sock.sendto(header.pack() + payload, addr)

# Wait for acknowledgment (type 45)
data, addr = sock.recvfrom(1024)
ack_header = LifxHeader.unpack(data[:36])
if ack_header.pkt_type == 45:
    print("Command acknowledged")
```

---

## Type Conversion

### HSBK to RGB

```python
import colorsys

def hsbk_to_rgb(hsbk: LightHsbk) -> tuple[int, int, int]:
    """Convert HSBK to RGB (0-255 range)."""
    h = hsbk.hue / 65535.0  # 0-1
    s = hsbk.saturation / 65535.0  # 0-1
    v = hsbk.brightness / 65535.0  # 0-1

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)
```

### RGB to HSBK

```python
import colorsys

def rgb_to_hsbk(r: int, g: int, b: int, kelvin: int = 3500) -> LightHsbk:
    """Convert RGB (0-255) to HSBK."""
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    return LightHsbk(
        hue=int(h * 65535),
        saturation=int(s * 65535),
        brightness=int(v * 65535),
        kelvin=kelvin,
    )
```

### Percentage Conversions

```python
def percent_to_uint16(percent: float) -> int:
    """Convert percentage (0-100) to uint16 (0-65535)."""
    return int(percent * 65535 / 100)

def uint16_to_percent(value: int) -> float:
    """Convert uint16 (0-65535) to percentage (0-100)."""
    return value * 100 / 65535
```

---

## References

**Source Files:**
- `src/lifx_emulator/protocol/header.py` - Header implementation
- `src/lifx_emulator/protocol/packets.py` - Packet definitions (auto-generated)
- `src/lifx_emulator/protocol/protocol_types.py` - Type definitions (auto-generated)
- `src/lifx_emulator/protocol/serializer.py` - Serialization utilities
- `src/lifx_emulator/protocol/generator.py` - Code generator from YAML spec

**Related Documentation:**
- [Device API](device.md) - Device state and packet processing
- [Server API](server.md) - UDP server implementation
- [LIFX LAN Protocol Specification](https://lan.developer.lifx.com/) - Official protocol docs
- [Architecture Overview](../architecture/overview.md) - System architecture

**Protocol Specification:**
- Auto-generated from [LIFX public-protocol](https://github.com/LIFX/public-protocol)
- Generator: `src/lifx_emulator/protocol/generator.py`
- Source: `protocol.yml` from LIFX/public-protocol repository
