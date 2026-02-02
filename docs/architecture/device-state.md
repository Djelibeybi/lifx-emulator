# Device State

How device state is structured, accessed, and updated.

## Overview

Each emulated device holds a `DeviceState` object that represents its complete state: identity, capabilities, light settings, zone colors, tile data, and more. The state is composed from focused sub-state dataclasses following the Single Responsibility Principle.

## Composed State Architecture

`DeviceState` is not a monolithic dataclass. It delegates to specialized sub-state objects:

```
DeviceState
├── core: CoreDeviceState          (serial, label, power, color, firmware)
├── network: NetworkState          (WiFi signal strength)
├── location: LocationState        (location ID, label, timestamp)
├── group: GroupState              (group ID, label, timestamp)
├── waveform: WaveformState        (waveform effect parameters)
├── infrared: InfraredState | None (IR brightness — color lights with IR only)
├── hev: HevState | None           (HEV cycle state — LIFX Clean only)
├── multizone: MultiZoneState | None (zone count, zone colors, effects)
└── matrix: MatrixState | None     (tile count, dimensions, tile data, framebuffers)
```

The first five sub-states are always present. The last four are `None` when the device lacks the corresponding capability.

## Capability Flags

Boolean flags indicate what a device supports:

| Flag | Meaning | Enables |
|------|---------|---------|
| `has_color` | Full RGB color | Hue/saturation control |
| `has_infrared` | IR LED | `InfraredState` sub-state |
| `has_multizone` | Linear zones | `MultiZoneState` sub-state |
| `has_extended_multizone` | Extended multizone protocol | 82-zone packets |
| `has_matrix` | 2D zone grid | `MatrixState` sub-state |
| `has_hev` | Germicidal UV-C | `HevState` sub-state |
| `has_relays` | Physical relays | Switch behavior |
| `has_buttons` | Physical buttons | Button protocol (not yet implemented) |

These flags are set by factory functions based on the product specification and cannot change at runtime.

## Attribute Delegation

Rather than defining hundreds of property getter/setter methods, `DeviceState` uses `__getattr__` and `__setattr__` with a routing map to delegate attribute access to the correct sub-state:

```python
state.label          # → state.core.label
state.wifi_signal    # → state.network.wifi_signal
state.zone_count     # → state.multizone.zone_count (or 0 if multizone is None)
state.tile_width     # → state.matrix.tile_width (or 8 if matrix is None)
```

The `_ATTRIBUTE_ROUTES` dictionary maps attribute names to their sub-state. Some attributes use tuple routing for name translation:

```python
"multizone_effect_type": ("multizone", "effect_type")
# state.multizone_effect_type → state.multizone.effect_type
```

When an optional sub-state is `None`, reads return a default value from `_OPTIONAL_DEFAULTS` and writes are silently ignored.

## Sub-State Details

### CoreDeviceState

The essential identity and light state every device has:

- `serial` — 12-character hex string (e.g., `"d073d5000001"`)
- `label` — Device name (up to 32 bytes)
- `power_level` — 0 (off) or 65535 (on)
- `color` — `LightHsbk` (hue, saturation, brightness, kelvin)
- `vendor`, `product` — Product identification
- `version_major`, `version_minor` — Firmware version
- `build_timestamp` — Firmware build time (seconds since epoch)
- `mac_address`, `port` — Network identity

### MultiZoneState

For devices with independently controllable linear zones (strips, beams):

- `zone_count` — Number of zones (product-dependent; e.g., LIFX Z: 8–16, Beam: 10–82, Neon: 24–48)
- `zone_colors` — List of `LightHsbk`, one per zone
- `effect_type`, `effect_speed` — Multizone effect state

Zone count ranges are defined per product in `specs.yml`. Zone colors are initialized to a rainbow pattern by `EmulatedLifxDevice.__init__()` if not provided.

### MatrixState

For devices with a 2D zone grid (tiles, candles, ceilings):

- `tile_count` — Number of tiles in the chain (product-dependent; LIFX Tile: 1–5, most other matrix devices: 1 only)
- `tile_width`, `tile_height` — Dimensions of each tile (product-dependent; e.g., Tile: 8x8, Candle: 5x6, Ceiling: 8x8)
- `tile_devices` — List of tile metadata dicts (position, colors, dimensions)
- `tile_framebuffers` — List of `TileFramebuffers` for non-visible buffers

Tile count ranges and dimensions are defined per product in `specs.yml`. Each tile's visible colors are in `tile_devices[i]["colors"]`. Non-visible framebuffers are stored separately in `TileFramebuffers` and lazily initialized on first access.

### HevState

For LIFX Clean devices with germicidal UV-C:

- `hev_cycle_duration_s` — Cycle duration (default: 7200s / 2 hours)
- `hev_cycle_remaining_s` — Time remaining in active cycle
- `hev_cycle_last_power` — Whether HEV was on when last cycle ended
- `hev_indication` — Whether HEV indicator light is enabled
- `hev_last_result` — Result code of last HEV cycle

## State Updates

Handlers update state by writing directly to `DeviceState` attributes:

```python
# In a handler's handle() method:
device_state.color = packet.color
device_state.power_level = 65535
```

These writes are routed through `__setattr__` to the correct sub-state object. The device's `process_packet()` method calls the handler and then optionally triggers a persistence save if storage is configured.

## See Also

- [Architecture Overview](overview.md) — Component relationships
- [Packet Flow](packet-flow.md) — How handlers interact with state
- [Protocol Layer](protocol.md) — Packet structures that carry state
