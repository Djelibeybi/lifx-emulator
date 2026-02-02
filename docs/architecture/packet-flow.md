# Packet Flow

How UDP packets are received, routed, processed, and responded to.

## Overview

Every interaction with the emulator follows the same path:

1. UDP packet arrives at `EmulatedLifxServer`
2. Header is parsed to determine target device(s)
3. Payload is unpacked into a typed packet object
4. Device processes the packet through its handler registry
5. Scenarios are applied (drops, delays, malformed responses)
6. Response packets are packed and sent back via UDP

## Step-by-Step Flow

### 1. Reception

The server listens on a UDP socket via `asyncio.DatagramProtocol`. When bytes arrive:

```python
# EmulatedLifxServer.handle_packet(data, addr)
header = LifxHeader.unpack(data[:36])
```

The 36-byte header is parsed first. If the header is malformed or too short, the packet is silently dropped (matching real LIFX device behavior).

### 2. Payload Unpacking

The `pkt_type` field from the header determines which packet class to use:

```python
packet_class = get_packet_class(header.pkt_type)
packet = packet_class.unpack(data[36:])
```

Packet classes are organized by protocol namespace:

- `Device.*` — types 2-59 (discovery, identity, power)
- `Light.*` — types 101-149 (color, waveform, infrared, HEV)
- `MultiZone.*` — types 501-512 (zone colors, effects)
- `Tile.*` — types 701-720 (matrix colors, effects, framebuffers)

### 3. Device Routing

The header's `target` field (6-byte MAC + 2 null bytes) determines which device(s) receive the packet:

- **Broadcast** (`tagged=True` or target is all zeros): packet forwarded to every device
- **Unicast** (`tagged=False` with specific target): routed to the device matching the serial encoded in the target field
- **Unknown target**: packet silently dropped

### 4. Packet Processing

Each device processes the packet through `EmulatedLifxDevice.process_packet()`:

```
process_packet(header, packet)
├── Look up handler in HandlerRegistry by pkt_type
├── If no handler found → return empty (or StateUnhandled for switches)
├── Apply scenario: check for packet drops
├── Call handler.handle(device_state, packet, res_required)
├── Handler reads/updates state and returns response packet(s)
├── Apply scenario: response delays, malformed packets, partial responses
├── Construct response headers
└── Return list of (header, packet) tuples
```

### 5. Handler Dispatch

The `HandlerRegistry` maps packet type numbers to handler instances using the Strategy pattern:

```python
handler = registry.get_handler(pkt_type)  # e.g., 101 → GetColorHandler
response = handler.handle(device_state, packet, res_required)
```

Handlers are split across four modules matching the protocol namespaces:

| Module | Packet Types | Examples |
|--------|-------------|----------|
| `device_handlers.py` | 2-59 | GetService, GetVersion, SetLabel |
| `light_handlers.py` | 101-149 | GetColor, SetColor, GetInfrared |
| `multizone_handlers.py` | 501-512 | GetColorZones, SetExtendedColorZones |
| `tile_handlers.py` | 701-720 | Get64, Set64, CopyFrameBuffer |

### 6. Response Construction

Handlers return packet objects (not headers). The device wraps each response in a header:

- `source` and `sequence` are copied from the request header
- `target` is set to the device's own serial
- `pkt_type` is set to the response packet's type
- `size` is calculated from header + payload length

If `ack_required=True` in the request header, an Acknowledgment packet (type 45) is automatically appended to the response list.

### 7. Multi-Packet Responses

Some handlers return multiple packets:

- **Multizone** (`GetColorZones`): one `StateMultiZone` (type 506) per 8 zones
- **Extended multizone** (`GetExtendedColorZones`): one or more `ExtendedStateMultiZone` (type 512) per 82 zones
- **Tile** (`Get64`): one `StateTileState64` per tile in the chain, with up to 64 zones per packet

Handlers return these as lists, and `process_packet()` constructs a separate header for each.

### 8. Sending

The server packs each (header, packet) tuple to bytes and sends via UDP back to the client's address and port.

## Scenario Interception Points

Scenarios modify the flow at several points during `process_packet()`:

| Scenario | When Applied | Effect |
|----------|-------------|--------|
| `drop_packets` | Before handler dispatch | Packet silently dropped (no response) |
| `response_delays` | After handler returns | `asyncio.sleep()` before sending |
| `malformed_packets` | After handler returns | Response payload truncated/corrupted |
| `invalid_field_values` | After handler returns | All response bytes set to 0xFF |
| `partial_responses` | After handler returns | Multi-packet response list randomly truncated |
| `send_unhandled` | When no handler found | Forces `StateUnhandled` (type 223) response |
| `firmware_version` | During state reads | Overrides reported firmware version |

## Switch Device Behavior

Switch devices (`has_relays=True`) handle Device namespace packets (types 2-59) normally but return `StateUnhandled` (type 223) for Light, MultiZone, and Tile packets. This matches physical LIFX Switch behavior.

## See Also

- [Architecture Overview](overview.md) — High-level component diagram
- [Protocol Layer](protocol.md) — Header and packet structure details
- [Device State](device-state.md) — How state is read and updated by handlers
