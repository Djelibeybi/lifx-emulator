# Matrix Framebuffer Support

Matrix devices with more than 64 zones require multiple Set64 packets to update all zones. Framebuffers enable atomic updates by allowing you to prepare all zones off-screen before displaying them.

## Overview

Matrix devices support **8 framebuffers (0-7)**:

- **Framebuffer 0**: The visible buffer displayed on the device
- **Framebuffers 1-7**: Non-visible buffers for preparing content

## Why Framebuffers Matter

For large tiles (>64 zones), such as the LIFX Ceiling 13"x26" with 128 zones (16×8):

**Without framebuffers:**
```
Set64(fb=0, zones 0-63)   → Visible immediately (partial update)
Set64(fb=0, zones 64-127) → Visible immediately (flicker as zones update)
```

**With framebuffers:**
```
Set64(fb=1, zones 0-63)      → Prepared off-screen
Set64(fb=1, zones 64-127)    → Prepared off-screen
CopyFrameBuffer(fb=1 → fb=0) → All 128 zones appear atomically
```

## Framebuffer Operations

### Set64 - Update Zones

The `rect.fb_index` field specifies which framebuffer to update:

```python
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import TileBufferRect, LightHsbk

# Update visible framebuffer (immediate display)
rect = TileBufferRect(fb_index=0, x=0, y=0, width=8)
packet = Tile.Set64(
    tile_index=0,
    rect=rect,
    duration=0,
    colors=[...64 colors...]
)

# Update non-visible framebuffer 1 (off-screen)
rect = TileBufferRect(fb_index=1, x=0, y=0, width=8)
packet = Tile.Set64(
    tile_index=0,
    rect=rect,
    duration=0,
    colors=[...64 colors...]
)
```

### Get64 - Read Zones

Get64 **always returns framebuffer 0** (the visible buffer), regardless of the `fb_index` in the request:

```python
# Request can specify any fb_index
rect = TileBufferRect(fb_index=1, x=0, y=0, width=8)
packet = Tile.Get64(tile_index=0, rect=rect)

# Response will contain framebuffer 0 content
# Response rect.fb_index is always 0
```

### CopyFrameBuffer - Atomic Display

Copy zones between framebuffers to make prepared content visible:

```python
# Copy entire framebuffer 1 to framebuffer 0 (make visible)
packet = Tile.CopyFrameBuffer(
    tile_index=0,
    src_fb_index=1,
    dst_fb_index=0,
    src_x=0,
    src_y=0,
    dst_x=0,
    dst_y=0,
    width=16,
    height=8,
    duration=0
)
```

## Complete Example: Updating a 16×8 Tile

```python
from lifx_emulator import create_tile_device
from lifx_emulator.protocol.packets import Tile
from lifx_emulator.protocol.protocol_types import TileBufferRect, LightHsbk

# Create 16×8 tile (128 zones)
device = create_tile_device(
    serial="d073dc000001",
    tile_count=1,
    tile_width=16,
    tile_height=8
)

# Prepare colors for all 128 zones
red = LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500)
green = LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500)

# Step 1: Update first 64 zones in framebuffer 1 (rows 0-3)
rect1 = TileBufferRect(fb_index=1, x=0, y=0, width=16)
set1 = Tile.Set64(
    tile_index=0,
    rect=rect1,
    duration=0,
    colors=[red] * 64
)
device.process_packet(header, set1)

# Step 2: Update next 64 zones in framebuffer 1 (rows 4-7)
rect2 = TileBufferRect(fb_index=1, x=0, y=4, width=16)
set2 = Tile.Set64(
    tile_index=0,
    rect=rect2,
    duration=0,
    colors=[green] * 64
)
device.process_packet(header, set2)

# Step 3: Atomically display all 128 zones
copy = Tile.CopyFrameBuffer(
    tile_index=0,
    src_fb_index=1,
    dst_fb_index=0,
    src_x=0,
    src_y=0,
    dst_x=0,
    dst_y=0,
    width=16,
    height=8,
    duration=0
)
device.process_packet(header, copy)

# All 128 zones now visible without flicker
```

## Implementation Details

### Storage

- **Framebuffer 0**: Stored in `tile_devices[i]["colors"]` (protocol-defined)
- **Framebuffers 1-7**: Stored in `MatrixState.tile_framebuffers` (internal)

### Lazy Initialization

Non-visible framebuffers are created on first access:

```python
# First Set64 to framebuffer 2 creates it automatically
# Initialized with black (hue=0, saturation=0, brightness=0)
```

### Persistence

Non-visible framebuffers are saved with device state when persistence is enabled:

```bash
lifx-emulator --persistent --tile 1
```

## Best Practices

### For Tiles ≤64 Zones
Update framebuffer 0 directly (no need for off-screen preparation):

```python
rect = TileBufferRect(fb_index=0, x=0, y=0, width=8)
```

### For Tiles >64 Zones
Always use a non-visible framebuffer:

1. Prepare all zones in framebuffer 1-7
2. Use CopyFrameBuffer to make visible
3. Prevents flicker during multi-packet updates

### Partial Updates
Use CopyFrameBuffer with specific rectangles:

```python
# Copy only top-left 4×4 area
copy = Tile.CopyFrameBuffer(
    src_fb_index=1,
    dst_fb_index=0,
    src_x=0,
    src_y=0,
    dst_x=0,
    dst_y=0,
    width=4,
    height=4,
    duration=0
)
```

## Related Documentation

- [Device Types](device-types.md#matrix-devices) - Matrix device capabilities
- [Protocol](../architecture/protocol.md) - LIFX LAN protocol details
