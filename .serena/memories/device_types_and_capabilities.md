# Device Types and Capabilities

## Overview
The emulator supports multiple LIFX device types based on capability flags in `DeviceState`.

## Capability Flags
```python
class DeviceState:
    has_color: bool           # RGB color control
    has_infrared: bool        # Night vision capability
    has_multizone: bool       # Linear multizone strips/beams
    has_extended_multizone: bool  # Extended multizone packet support
    has_matrix: bool          # 2D matrix (tiles/candles)
    has_hev: bool            # Germicidal UV-C capability
    has_relays: bool         # Relay switches (LIFX Switch)
    has_buttons: bool        # Physical buttons (LIFX Switch)
```

## Device Types

### 1. Color Light (Basic)
**Factory**: `create_color_light()`
**Product ID**: 27 (LIFX A19)
**Capabilities**: `has_color=True`
**Features**:
- Full RGB color control (hue, saturation, brightness)
- Variable color temperature (kelvin)
- Power on/off
**Protocol Support**: Device.*, Light.*

### 2. Color Temperature Light
**Factory**: `create_color_temperature_light()`
**Product ID**: 50 (LIFX Mini White to Warm)
**Capabilities**: No special flags
**Features**:
- Brightness control only
- Variable color temperature (2500K-9000K)
- No RGB color support
**Protocol Support**: Device.*, Light.* (limited)

### 3. Infrared Light
**Factory**: `create_infrared_light()`
**Product ID**: 29 (LIFX+ A19)
**Capabilities**: `has_color=True`, `has_infrared=True`
**Features**:
- All features of color light
- Infrared brightness control for night vision
**Protocol Support**: Device.*, Light.* (including SetInfrared)

### 4. HEV/Clean Light
**Factory**: `create_hev_light()`
**Product ID**: 90 (LIFX Clean)
**Capabilities**: `has_color=True`, `has_hev=True`
**Features**:
- All features of color light
- HEV cycle control (germicidal UV-C)
- HEV last result tracking
**Protocol Support**: Device.*, Light.*, HEV.*

### 5. Multizone Device (Strip/Beam)
**Factory**: `create_multizone_light(zone_count, extended_multizone)`
**Product IDs**:
- 32 (LIFX Z, non-extended)
- 38 (LIFX Beam, extended)
**Capabilities**: `has_color=True`, `has_multizone=True`, `has_extended_multizone=True/False`
**Features**:
- Per-zone color control
- 8-82 zones typical (no hard limit)
- Extended multizone for >82 zones or firmware ≥2.77
**Protocol Support**: Device.*, Light.*, MultiZone.*

**Zone Handling**:
- Standard: Returns multiple `StateMultiZone` packets (8 zones each)
- Extended: Returns one or more `ExtendedStateMultiZone` packets (82 zones each)
- Minimum zones: 8
- Maximum zones: No limit (defaults from product specs)

**Firmware Versions**:
- Extended multizone: 3.70
- Non-extended: 2.60

### 6. Matrix Device (Tiles/Candles)
**Factory**: `create_tile_device(tile_count)`
**Product IDs**:
- 55 (LIFX Tile, 5 tiles of 8x8 zones)
- 57 (LIFX Candle, 1 tile of 5x6 zones)
**Capabilities**: `has_color=True`, `has_matrix=True`
**Features**:
- 2D zone arrangement
- Up to 5 tiles per chain (most have 1)
- Per-zone color control
- 8 framebuffers (0-7) for advanced rendering
**Protocol Support**: Device.*, Light.*, Tile.*

**Tile Specifications**:
- Each tile: width×height zones (8×8 or 16×8)
- All tiles on chain must be identical size
- Default tile count/dimensions from product specs

**Framebuffer Support**:
- Framebuffer 0: Visible buffer (in `tile_devices[i]["colors"]`)
- Framebuffers 1-7: Non-visible buffers (in `MatrixState.tile_framebuffers`)
- `Set64`: Respects `rect.fb_index` parameter
- `Get64`: Always returns framebuffer 0 (visible)
- `CopyFrameBuffer`: Copies rectangular zones between framebuffers

### 7. Switch Device
**Factory**: `create_switch(product_id=70)`
**Product ID**: 70 (LIFX Switch)
**Capabilities**: `has_relays=True`, `has_buttons=True`
**Features**:
- Relay control (no lighting)
- Button events (requires cloud/Matter infrastructure - not implemented)
**Protocol Support**: Device.* ONLY
**Filtering**: Returns `StateUnhandled` (223) for Light.*, MultiZone.*, Tile.* packets

## Product Registry
The emulator includes a registry of 137+ real LIFX products with accurate specifications.

### Registry Usage
```python
from lifx_emulator.products.registry import get_product

product = get_product(27)  # LIFX A19
print(product.name)                    # "LIFX A19"
print(product.has_color)               # True
print(product.has_extended_multizone)  # False
print(product.min_kelvin)              # 2500
print(product.max_kelvin)              # 9000
```

### Registry Generation
**DO NOT EDIT** `products/registry.py` manually!

```bash
# Regenerate from official LIFX products.json
python -m lifx_emulator.products.generator
```

This downloads the latest products.json from https://github.com/LIFX/products and regenerates the registry.

### Product Specs
**File**: `products/specs.yml`

Contains product-specific defaults not in products.json:
- Default zone counts for multizone devices
- Default tile counts and dimensions
- Custom configurations per product

**Example**:
```yaml
32:  # LIFX Z
  zone_count: 16
  extended_multizone: false

38:  # LIFX Beam
  zone_count: 80
  extended_multizone: true

55:  # LIFX Tile
  tile_count: 5
  tile_width: 8
  tile_height: 8
```

## Capability-Based Packet Filtering

### Switch Devices
Switches automatically reject lighting-related packets:
- Light.* packets (101-149): `StateUnhandled`
- MultiZone.* packets (501-512): `StateUnhandled`
- Tile.* packets (701-720): `StateUnhandled`
- Device.* packets (2-59): Normal handling

**Response Format**:
```python
# StateUnhandled packet (223)
{
    "unhandled_type": 101  # Original packet type that was rejected
}
```

**Acknowledgments**:
- Still sent if `ack_required=True` flag is set
- Sent BEFORE StateUnhandled response

## Extended Multizone Support

### Native Support
Products with `extended_multizone: true` in features:
- LIFX Z US (PID 117)
- LIFX Beam US (PID 119)
- LIFX Neon
- LIFX Permanent Outdoor

```python
product = get_product(117)
product.has_extended_multizone      # True
product.min_ext_mz_firmware         # None (native support)
product.supports_extended_multizone()  # True
```

### Firmware Upgrade
Products with extended_multizone in upgrades section:
- LIFX Z (PID 32, requires firmware 2.77+)
- LIFX Beam (PID 38, requires firmware 2.77+)

```python
product = get_product(32)
product.has_extended_multizone      # True
product.min_ext_mz_firmware         # 131149 (firmware 2.77)
product.supports_extended_multizone(131149)  # True (meets requirement)
product.supports_extended_multizone(131148)  # False (below requirement)
```

## Device Creation Examples

### By Device Type
```python
from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
    create_switch,
)

# Color light
device = create_color_light(serial="d073d5000001")

# Multizone with 24 zones, extended support
device = create_multizone_light(
    serial="d073d5000002",
    zone_count=24,
    extended_multizone=True
)

# Tile with 5 tiles (uses product defaults for dimensions)
device = create_tile_device(
    serial="d073d5000003",
    tile_count=5
)

# Switch
device = create_switch(serial="d073d5000004", product_id=70)
```

### By Product ID
```python
from lifx_emulator.factories import create_device

# LIFX A19 (auto-detects capabilities from registry)
device = create_device(product_id=27, serial="d073d5000001")

# LIFX Z with custom zone count (overrides default of 16)
device = create_device(
    product_id=32,
    serial="d073d5000002",
    zone_count=24
)

# LIFX Tile (uses default: 5 tiles of 8x8)
device = create_device(product_id=55, serial="d073d5000003")

# LIFX Beam (uses default: 80 zones, extended=True)
device = create_device(product_id=38, serial="d073d5000004")
```

## Testing Considerations

### Capability Testing
Always test based on capability flags, not product IDs:

```python
# ✅ GOOD - test capabilities
if device.state.has_multizone:
    test_multizone_operations(device)

# ❌ BAD - test product ID
if device.state.product_id == 32:
    test_multizone_operations(device)
```

### Edge Cases to Test
1. **Multizone**: Devices with >82 zones (requires multiple ExtendedStateMultiZone packets)
2. **Matrix**: Tiles with >64 zones (16×8, requires multiple Get64 requests)
3. **Switch**: Verify StateUnhandled for all lighting packets
4. **Framebuffers**: Copy operations between different framebuffers
5. **Extended Multizone**: Backwards compatibility with standard multizone packets
