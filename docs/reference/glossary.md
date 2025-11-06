# Glossary

Terminology and concepts used in the LIFX Emulator documentation.

## General Terms

### LIFX
A brand of WiFi-enabled smart LED light bulbs and accessories that use the LIFX LAN Protocol for local network control.

### LIFX LAN Protocol
The binary UDP-based protocol used to communicate with LIFX devices over a local network. Documented at https://lan.developer.lifx.com

### Emulator
A software implementation that mimics the behavior of physical LIFX devices for testing purposes without requiring actual hardware.

### Device
A virtual or physical LIFX product (bulb, strip, tile, etc.) that responds to LIFX protocol commands.

### Server
The `EmulatedLifxServer` instance that listens for UDP packets and routes them to emulated devices.

## Device Types

### Color Light
A LIFX device with full RGB color control, including hue, saturation, brightness, and color temperature. Examples: LIFX A19, BR30, GU10.

### Color Temperature Light
A LIFX device that only supports variable white color (warm to cool) without RGB color capability. Also called "white-to-warm" lights. Examples: LIFX Mini White to Warm.

### Infrared Light
A color light with additional infrared capability for night vision. The infrared LED is separate from the visible light. Examples: LIFX A19 Night Vision.

### HEV Light
A color light with High Energy Visible (HEV) light capability for anti-bacterial sanitization. Example: LIFX Clean.

### Multizone Device
A LIFX device with multiple independently controllable zones arranged linearly (1D array). Examples: LIFX Z (strip), LIFX Beam, LIFX Neon.

### Extended Multizone
Multizone devices that support the extended multizone packets. These devices also support standard multizone packets for backward compatibility.

### Matrix Device
A LIFX device with zones arranged in a 2D matrix (width × height). Examples: LIFX Tile, LIFX Candle, LIFX Ceiling.

### Tile Device
Historical term for matrix devices. Originally referred to LIFX Tile, but now used more broadly for any matrix device.

### Chain
A set of tiles connected together on a single device. Most modern matrix devices have a single tile per chain. The original LIFX Tile supported up to 5 tiles per chain.

## Device Identification

### Serial
A 12-character hexadecimal string representing a unique device identifier. Examples: `d073d5000001`, `d073d8123456`.

### Serial Bytes
The 6-byte binary representation of a serial number. The LIFX protocol uses 6-byte MAC addresses as device identifiers.

### Target
An 8-byte field in the LIFX packet header consisting of:

- 6 bytes: Device MAC address (serial bytes)
- 2 bytes: Reserved (always 0x00 0x00)

When `target` is all zeros (`00:00:00:00:00:00:00:00`), the packet is a broadcast.

### MAC Address
Media Access Control address - a 6-byte unique identifier for network devices.

## Product Information

### Product ID
An integer identifying a specific LIFX product model. Examples:

- 27: LIFX A19
- 32: LIFX Z
- 55: LIFX Tile
- 90: LIFX Clean

### Specification
A device definition that matches a real-world product. The LIFX Emulator uses its specification library to emulate LIFX devices as accurately as possible. Specifications include product defaults like zone counts for multizone devices and tile dimensions for matrix devices.

### Vendor ID
An integer identifying the manufacturer. For LIFX devices, this is always `1`.

### Firmware Version
The software version running on a LIFX device, typically reported as major.minor (e.g., `3.70`).

## Packet Structure

### Packet
A complete LIFX protocol message consisting of a header (36 bytes) and payload (0-1024 bytes).

### Header
The first 36 bytes of every LIFX packet containing metadata:

- Protocol version
- Source (client identifier)
- Target (device serial)
- Flags (tagged, ack_required, res_required)
- Sequence number
- Packet type

### Payload
The data portion of a LIFX packet after the 36-byte header. Contains packet-specific fields.

### Packet Type
A 16-bit integer identifying the type of LIFX message. Examples:

- 2: GetService (discovery)
- 101: LightGetPower
- 102: LightSetColor
- 107: LightState (color)

## Protocol Flags

### Tagged
A header flag indicating whether a packet is broadcast or unicast:

- `tagged=True`: Broadcast packet (target is ignored)
- `tagged=False`: Unicast packet (target specifies device serial)

### Broadcast
A packet sent to all devices on the network. Indicated by `tagged=True` in the header.

### Unicast
A packet sent to a specific device. Indicated by `tagged=False` and a specific target serial in the header.

### Ack Required
A header flag (`ack_required`) indicating the sender wants an acknowledgment (packet type 45) when the packet is received.

### Res Required
A header flag (`res_required`) indicating the sender wants a state response packet (not just an acknowledgment). Devices will
send a state response back to all get packets, regardless of whether this flag is set or not. If this flag is set in the header
of a set packet, and the set packet changed the visible state of the device, the response will contain the state prior to the
change.

### Acknowledgment
A simple response packet (type 45) confirming receipt of a command. Sent when `ack_required=True` in the received packet's header.

### Response
A state packet containing requested information (e.g., LightState, StatePower). Sent in reply to the corresponding get packet.

## Zone and Tile Concepts

### Zone
A single independently controllable color segment on a multizone or matrix device.

### Zone Index
Zero-based position of a zone:

- Multizone: 0 to (zone_count - 1)
- Matrix: Varies by device (row-major order)

### Zone Count
Total number of zones on a multizone device. Examples:

- LIFX Z: 16 zones (2 meters, 8 zones per meter)
- LIFX Beam: 80 zones (10 zones per beam × 8 beams)

### Tile
One physical tile in a chain (matrix devices). Most modern devices have 1 tile per chain.

### Tile Count
Number of tiles in a chain. Default values:

- LIFX Tile: 5 tiles per chain
- LIFX Candle: 1 tile
- LIFX Ceiling: 1 tile

### Tile Width
Number of zones horizontally on a single tile. Examples:

- LIFX Tile: 8 (8×8 grid)
- LIFX Candle: 5 (5×6 grid)
- LIFX Ceiling 26"×13": 16 (16×8 grid)

### Tile Height
Number of zones vertically on a single tile. Examples:

- LIFX Tile: 8 (8×8 grid)
- LIFX Candle: 6 (5×6 grid)
- LIFX Ceiling 26"×13": 8 (16×8 grid)

### Get64 / Set64
Protocol packets (types 707 and 715) for retrieving or setting up to 64 zones on a matrix device at once. Uses a rectangle specification (x, y, width) to select zones.

### Device Chain
Protocol packet (type 701/702) that describes the tile configuration: number of tiles, dimensions, and positions.

## Color and Light

### HSBK
HSBK is an acronym that refers to Hue, Saturation, Brightness, and Kelvin: the color representation used by LIFX.

#### Hue
The color on the color wheel, represented as 0-65535 (maps to 0° to 360°).

#### Saturation
The intensity of color, from 0 (white/gray) to 65535 (fully saturated color).

#### Brightness
The light intensity, from 0 (off) to 65535 (maximum brightness).

#### Kelvin
Color temperature measured in Kelvin. The LIFX smart phone app uses the following
names for particular Kelvin values:

- 1500K: Candlelight
- 2000K: Sunset
- 2200K: Amber
- 2500K: Ultra Warm
- 2700K: Incandescent
- 3000K: Warm
- 3200K: Neutral Warm
- 3500K: Neutral
- 4000K: Cool
- 4500K: Cool Daylight
- 5000K: Soft Daylight
- 5600K: Daylight
- 6000K: Noon Daylight
- 6500K: Bright Daylight
- 7000K: Cloudy Daylight
- 7500K: Blue Daylight
- 8000K: Blue Overcast
- 9000K: Blue Ice


### Power Level
Device power state:

- 0: Off
- 65535: On

## Testing Concepts

### Test Scenario
Configuration that modifies emulator behavior for testing error conditions. Examples: packet dropping, response delays, malformed packets.

### Mock
A test double that simulates the behavior of real code. Different from an emulator - mocks are simpler and less accurate.

### Integration Test
A test that verifies multiple components working together. The emulator is ideal for integration tests of LIFX client libraries.

### Unit Test
A test of a single component in isolation. The emulator is typically overkill for unit tests - use mocks instead.

## Packet Testing

### Drop Packets
A test scenario where the emulator silently ignores specific packet types, simulating network packet loss or device unresponsiveness.

### Response Delays
A test scenario where the emulator waits a specified time before responding to packets, simulating slow devices or network latency.

### Malformed Packets
A test scenario where the emulator returns corrupted or truncated response packets to test client error handling.

### Invalid Field Values
A test scenario where the emulator returns packets with all bytes set to 0xFF, testing client validation logic.

### Partial Responses
A test scenario where the emulator returns incomplete state data (e.g., only half the zones), testing client robustness.

## Network Concepts

### UDP
User Datagram Protocol - a connectionless network protocol. LIFX uses UDP for fast, low-latency communication.

### Port
A network endpoint identifier. The default LIFX port is 56700 (UDP).

### Bind Address
The IP address a server listens on:

- `127.0.0.1`: Localhost only (not discoverable on network)
- `0.0.0.0`: All network interfaces (discoverable on network)
- Specific IP: Single interface only

### Discovery
The process of finding LIFX devices on the network by sending GetService (type 2) broadcast packets.

## Storage and Persistence

### Persistent Storage
The emulator's optional feature to save device state to disk across restarts using JSON files.

### Storage Directory
The directory where persistent state is saved. Default: `~/.lifx-emulator/`

### Device State
All the current settings of a device: color, power, label, location, group, zones, tiles, etc.

### State File
A JSON file storing the persistent state of a single device, named by serial (e.g., `d073d5000001.json`).

## HTTP API

### API Server
The optional HTTP server (`--api`) for monitoring and managing the emulator at runtime.

### OpenAPI
A standard specification for describing REST APIs. The emulator API provides an OpenAPI 3.1.0 schema.

### Swagger UI
An interactive web interface for testing REST APIs, available at `/docs` when the API server is running.

### ReDoc
A documentation-focused web interface for REST APIs, available at `/redoc` when the API server is running.

### Activity Log
A record of recent packet transmissions (TX) and receptions (RX) shown in the API dashboard.

## Capabilities

### has_color
A boolean indicating whether a device supports RGB color (not just white).

### has_multizone
A boolean indicating whether a device has multiple independently controllable zones in a linear arrangement.

### has_matrix
A boolean indicating whether a device has zones arranged in a 2D matrix.

### has_infrared
A boolean indicating whether a device has infrared LED capability.

### has_hev
A boolean indicating whether a device has HEV (germicidal UV-C) capability.

## Factory Functions

### create_color_light()
Factory function that creates a full RGB color light (LIFX A19, product ID 27).

### create_multizone_light()
Factory function that creates a multizone device (LIFX Z or Beam depending on `extended_multizone` parameter).

### create_tile_device()
Factory function that creates a matrix device (LIFX Tile by default, product ID 55).

### create_device()
Universal factory function that creates any device by product ID from the registry.

## See Also

- [FAQ](../faq.md) - Common questions and answers
- [Troubleshooting](troubleshooting.md) - Solutions to common problems
- [Device Types](../guide/device-types.md) - Detailed device type documentation
- [Protocol Types](../api/protocol.md) - Protocol data structures
- [LIFX LAN Protocol](https://lan.developer.lifx.com) - Official protocol specification
