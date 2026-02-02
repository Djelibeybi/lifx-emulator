# Protocol Layer

How the LIFX LAN protocol is implemented: header structure, packet serialization, and code generation.

## Overview

The LIFX LAN protocol is a binary UDP protocol documented at [lan.developer.lifx.com](https://lan.developer.lifx.com). Every message consists of a 36-byte header followed by a variable-length payload. All multi-byte values use little-endian byte order.

The emulator's protocol layer handles:

- Parsing and constructing the 36-byte header
- Serializing and deserializing packet payloads
- Mapping packet type numbers to typed Python classes

## Header Structure

The `LifxHeader` dataclass represents the 36-byte header, which has three sections:

### Frame (8 bytes)

| Field                                    | Size    | Description                                                      |
| ---------------------------------------- | ------- | ---------------------------------------------------------------- |
| `size`                                   | 16 bits | Total message size (header + payload)                            |
| origin / tagged / addressable / protocol | 16 bits | Bitfield: origin (2), tagged (1), addressable (1), protocol (12) |
| `source`                                 | 32 bits | Unique client identifier                                         |

The `protocol` field is always 1024. The `addressable` bit is always 1. The `tagged` bit indicates broadcast (`True`) vs unicast (`False`).

### Frame Address (16 bytes)

| Field      | Size    | Description                                                |
| ---------- | ------- | ---------------------------------------------------------- |
| `target`   | 64 bits | 6-byte MAC address + 2 null bytes                          |
| reserved   | 48 bits | Reserved (zeros)                                           |
| flags      | 8 bits  | Bitfield: res_required (1), ack_required (1), reserved (6) |
| `sequence` | 8 bits  | Sequence number for request/response matching              |

The `target` field encodes the device serial: a 12-character hex string like `"d073d5000001"` becomes 6 bytes `d0 73 d5 00 00 01` followed by 2 null bytes.

### Protocol Header (12 bytes)

| Field      | Size    | Description            |
| ---------- | ------- | ---------------------- |
| reserved   | 64 bits | Reserved (zeros)       |
| `pkt_type` | 16 bits | Packet type identifier |
| reserved   | 16 bits | Reserved (zeros)       |

The header is packed and unpacked using a pre-compiled `struct.Struct("<HHI Q6sBB QHH")` for performance.

## Packet Classes

Packet payloads are represented as typed dataclasses organized by protocol namespace:

- **`Device`** — Discovery, identity, power, label, location, group (types 2-59)
- **`Light`** — Color, waveform, infrared, HEV (types 101-149)
- **`MultiZone`** — Zone colors, extended zones, effects (types 501-512)
- **`Tile`** — Matrix colors, framebuffers, effects (types 701-720)

Each packet class has:

- `PKT_TYPE` — Class variable with the packet type number
- `pack()` — Serialize fields to bytes
- `unpack(data)` — Class method to deserialize bytes to a packet instance

```python
from lifx_emulator.protocol.packets import Light

# Unpack a SetColor payload
packet = Light.SetColor.unpack(payload_bytes)
print(packet.color.hue)  # Access typed fields

# Pack a State response
response = Light.State(color=device_state.color, power=device_state.power_level, ...)
response_bytes = response.pack()
```

## Binary Serialization

The `serializer.py` module handles struct-based binary packing with:

- **Type mapping** — Python types to struct format codes (`uint16` → `"H"`, `uint32` → `"I"`, etc.)
- **Little-endian** — All values packed as `<` (little-endian) per the LIFX specification
- **Pre-compiled structs** — A cache of `struct.Struct` objects avoids repeated compilation
- **Composite types** — `LightHsbk` (8 bytes: 4 × uint16), `TileStateDevice` (55 bytes), and other protocol structures

## Protocol Types

`protocol_types.py` defines the data structures used within packets:

- **`LightHsbk`** — Color representation (hue, saturation, brightness, kelvin), each uint16
- **`TileStateDevice`** — Tile metadata (position, dimensions, firmware version)
- **`TileBufferRect`** — Rectangle specification for Get64/Set64 (framebuffer index, x, y, width)
- **Enums** — `DeviceService`, `LightWaveform`, `MultiZoneEffectType`, `MultiZoneApplicationRequest`, etc.

## Code Generation

Two modules are auto-generated from the [LIFX public protocol](https://github.com/LIFX/public-protocol) specification and must not be edited manually:

| Generated File         | Generator                                    | Source            |
| ---------------------- | -------------------------------------------- | ----------------- |
| `protocol/packets.py`  | `python -m lifx_emulator.protocol.generator` | `protocol.yml`    |
| `products/registry.py` | `python -m lifx_emulator.products.generator` | LIFX product data |

The generators produce:

- **`packets.py`** — All packet classes with nested `Device.*`, `Light.*`, `MultiZone.*`, `Tile.*` namespaces, field definitions, `pack()`/`unpack()` methods, and `PKT_TYPE` constants
- **`protocol_types.py`** — Dataclasses and enums for composite protocol structures (also auto-generated)
- **`registry.py`** — Product definitions (137+ products with capability flags)

## Packet Type Resolution

`get_packet_class(pkt_type)` maps a numeric packet type to its class:

```python
get_packet_class(2)   # → Device.GetService
get_packet_class(101) # → Light.Get (GetColor)
get_packet_class(502) # → MultiZone.GetColorZones
get_packet_class(707) # → Tile.Get64
```

Unknown packet types return `None`, and the device either ignores the packet or returns `StateUnhandled` (type 223) depending on configuration.

## See Also

- [Architecture Overview](https://djelibeybi.github.io/lifx-emulator/architecture/overview/index.md) — How the protocol layer fits in
- [Packet Flow](https://djelibeybi.github.io/lifx-emulator/architecture/packet-flow/index.md) — End-to-end packet processing
- [Device State](https://djelibeybi.github.io/lifx-emulator/architecture/device-state/index.md) — State structures that handlers read and write
- [LIFX LAN Protocol](https://lan.developer.lifx.com) — Official protocol specification
