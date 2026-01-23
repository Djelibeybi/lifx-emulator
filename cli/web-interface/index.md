# Web Interface Guide

## Overview

The LIFX Emulator includes a built-in web interface for real-time monitoring and device management. The dashboard provides a browser-based alternative to the REST API, with live updates of server statistics, device status, and packet activity.

**Access**: Open `http://localhost:8080` in your web browser (after starting the emulator with `--api`)

## Getting Started

### Enable the Web Interface

```bash
# Start emulator with API (enables web interface)
lifx-emulator --api

# Custom host and port
lifx-emulator --api --api-host 127.0.0.1 --api-port 9090

# Then open in browser:
# http://localhost:8080
# or http://127.0.0.1:9090
```

## Interface Layout

The web interface is organized into three main sections:

### Server Statistics Card (Top Left)

Displays real-time emulator health metrics:

```text
Server Statistics
├─ Uptime: 123s
├─ Devices: 3
├─ Packets RX: 1250
├─ Packets TX: 2100
└─ Errors: 0
```

**Metrics:**

- **Uptime**: Time since server started (auto-updating)
- **Devices**: Number of currently emulated devices
- **Packets RX**: Total packets received from LIFX clients
- **Packets TX**: Total packets sent to LIFX clients
- **Errors**: Total packet processing errors

**Use Cases:**

- Verify API server is running
- Monitor packet flow during testing
- Check for errors during protocol testing

______________________________________________________________________

### Add Device Card (Top Right)

Creates new devices on the fly:

```text
Add Device
├─ Product ID: [dropdown menu]
└─ [Add Device button]
```

**Features:**

- Dropdown list of common products:
- 27 - LIFX A19 (color light)
- 29 - LIFX A19 Night Vision
- 32 - LIFX Z (multizone strip)
- 38 - LIFX Beam (extended multizone)
- 50 - LIFX Mini White to Warm
- 55 - LIFX Tile (matrix device)
- 90 - LIFX Clean (HEV)
- Serial numbers are auto-generated

**Use Cases:**

- Quick device creation for testing
- Create multiple device types without CLI
- Test with different device configurations

______________________________________________________________________

### Devices Section

Displays all emulated devices with detailed status:

```text
Devices (3)                    [Remove All]  [Clear Storage]

┌─ Device Card ─────────────────────────────────────────┐
│ d073d5000001                                    [Del]  │
│ Living Room Light                                      │
│                                                        │
│ [ON]  [P27]  [color]  [multizone×16]  [HEV]         │
│                                                        │
│ ▸ Show metadata  (click to expand)                    │
│ ▸ Show zones (16)  (click to expand)                 │
└────────────────────────────────────────────────────────┘
```

#### Device Card Components

**Header:**

- Device serial number (clickable, displays copy tooltip)
- Device label (e.g., "Living Room Light")
- Delete button (red, with confirmation)

**Status Badges:**

- Power status: `[ON]` (green) or `[OFF]` (gray)
- Product ID: `[P27]` (light blue)
- Capabilities: `[color]`, `[multizone×16]`, `[HEV]`, etc.
- Extended multizone: `[extended-mz×80]` (green)

**Expandable Metadata** (click "▸ Show metadata"):

```text
Firmware: 3.70
Vendor: 1
Product: 27
Capabilities: Color, Multizone (16 zones)
Group: (empty)
Location: (empty)
Uptime: 123s
WiFi Signal: -45.5 dBm
```

**Color/Zone Display:**

For color lights:

```text
▸ Show zones
  ■ Current color
```

For multizone devices:

```text
▸ Show zones (16)  (click to expand)
  [colored strips representing each zone]
```

For matrix/tile devices:

```text
▸ Show tiles (5)  (click to expand)
  ┌──────────┐
  │ T1       │  (8×8 zone grid)
  │ ████████ │
  │ ████████ │
  │ ████████ │
  │ ████████ │
  │ ████████ │
  │ ████████ │
  │ ████████ │
  │ ████████ │
  └──────────┘
  (repeats for each tile)
```

**Zone Display:**

- Each zone shown as a colored segment
- Colors represent current HSBK values
- Heights approximately proportional to brightness
- Saturation affects color intensity
- Hue determines the color

______________________________________________________________________

### Recent Activity Log (Bottom)

Displays the last 100 LIFX protocol packets in real-time:

```text
Recent Activity

12:34:56  RX  GetColor           d073d5000001  192.168.1.100:54321
12:34:56  TX  State              d073d5000001  192.168.1.100:54321
12:34:57  RX  GetPower           d073d5000002  192.168.1.101:54322
12:34:57  TX  StatePower         d073d5000002  192.168.1.101:54322
```

**Activity Event Fields:**

- **Time**: HH:MM:SS (local time)
- **Direction**:
- `RX` (blue) - Received from client
- `TX` (orange) - Transmitted to client
- **Packet Name**: Human-readable LIFX packet type (e.g., "GetColor", "SetColor")
- **Device**: Target device serial number
- **Address**: Client IP address and port

**Use Cases:**

- Debugging LIFX client communication
- Verifying packet flow
- Monitoring protocol interactions
- Identifying communication problems

**Note:** Activity log is only visible if activity logging is enabled (`--api-activity` flag, default: true). Disable to reduce server traffic.

______________________________________________________________________

## Common Tasks

### Add a New Device

1. Open the web interface: `http://localhost:8080`
1. Find the "Add Device" card (top right)
1. Select a product from the dropdown menu
1. Click "Add Device" button
1. New device appears in the Devices section with auto-generated serial

The device is immediately available to LIFX clients and is added to the emulator runtime (not persisted to disk unless `--persistent` flag is used).

______________________________________________________________________

### Check Device Status

1. Locate device in the Devices section
1. Check power badge (`[ON]` or `[OFF]`)
1. Check capability badges (color, multizone, matrix, HEV, etc.)
1. Click "▸ Show metadata" to view:
1. Firmware version
1. Product ID and vendor
1. Assigned group and location
1. Device uptime
1. WiFi signal strength

______________________________________________________________________

### View Multizone Colors

For multizone devices (strips, beams):

1. Locate device in Devices section
1. Click "▸ Show zones" to expand
1. Colored bar displays all zone colors
1. Each segment represents one zone
1. Color indicates current HSBK values
1. Click again to collapse

**Color Interpretation:**

- Hue (0-360°): Color wheel position
- Saturation (0-100%): Color intensity (white to saturated)
- Brightness (0-100%): Light intensity
- Kelvin (1500-9000K): Color temperature

______________________________________________________________________

### View Tile/Matrix Colors

For matrix devices (tiles, candles, ceiling):

1. Locate device in Devices section
1. Click "▸ Show tiles" to expand
1. Grid display shows zone colors
1. Each small square is one zone
1. Tiles labeled T1, T2, etc.
1. Click again to collapse

______________________________________________________________________

### Monitor Packet Activity

1. Scroll to "Recent Activity" section (bottom)
1. Watch for real-time packet updates
1. Filter mentally by:
1. **Direction**: RX (requests) vs TX (responses)
1. **Packet type**: GetColor, SetColor, StatePower, etc.
1. **Device**: Compare multiple devices
1. **Client address**: Identify different clients

**Common Packet Patterns:**

```text
RX GetService (broadcast)     <- Client discovering devices
TX StateService (response)    <- Device responds

RX GetColor                   <- Client querying color
TX State (color response)     <- Device responds

RX SetColor + params          <- Client setting new color
TX Acknowledgment             <- Device confirms

RX GetPower                   <- Client querying power
TX StatePower                 <- Device responds
```

______________________________________________________________________

### Remove a Device

**Remove Single Device:**

1. Locate device in Devices section
1. Click red "Del" button on device card
1. Confirm deletion in prompt
1. Device disappears from list
1. Device stops responding to LIFX protocol packets

**Remove All Devices:**

1. Click "Remove All" button (top right of Devices section)
1. Confirmation dialog shows: "Remove all X device(s)?"
1. Click OK to confirm
1. All devices removed from runtime (storage preserved)

______________________________________________________________________

### Clear Persistent Storage

If `--persistent` flag was used to enable state persistence:

1. Click "Clear Storage" button (top right of Devices section)
1. Confirmation dialog shows: "Clear all persistent device state?"
1. Click OK to confirm
1. All saved device state files deleted from disk
1. Currently running devices NOT affected
1. Next restart will start with no saved state

______________________________________________________________________

## Features and Capabilities

### Real-Time Updates

- Dashboard auto-refreshes every 2 seconds
- Server statistics updated in real-time
- Device list and status refreshed
- Activity log scrolls with new packets
- No manual refresh button needed

### Persistent UI State

The interface remembers your preferences:

- Zone/tile display states (expanded/collapsed) per device
- Metadata display states (expanded/collapsed) per device
- Preferences stored in browser localStorage
- Persists across page reloads
- Per-device basis (no global toggle)

### Color Display

Colors are displayed accurately:

- HSBK to RGB conversion for display
- Hue: Color wheel position
- Saturation: Intensity/purity
- Brightness: Light level
- Kelvin: Color temperature (white point)

### Responsive Design

- Adapts to different screen sizes
- Device cards responsive grid layout
- Touch-friendly on tablets
- Dark theme optimized for monitoring

______________________________________________________________________

## Performance Considerations

### Activity Logging Impact

Activity logging has performance implications:

```bash
# Disable activity logging (reduces traffic)
lifx-emulator --api --api-activity=false

# Activity endpoint returns 503 Service Unavailable when disabled
curl http://localhost:8080/api/activity
# Response: 503 Service Unavailable
```

### Optimal Configuration for Monitoring

```bash
# Balance between visibility and performance
lifx-emulator --api \
  --api-host 127.0.0.1 \  # Limit to localhost if not needed on network
  --api-port 8080
```

### Browser Performance

For emulators with many devices (50+):

- Activity log auto-update may slow down browser
- Consider disabling activity logging (`--api-activity=false`)
- Refresh page if UI becomes sluggish
- Use REST API directly for automated monitoring

______________________________________________________________________

## Troubleshooting

### Web Interface Not Loading

```bash
# Check if API server is running
curl http://localhost:8080/api/stats

# Check if port is correct
# Default: http://localhost:8080
# Custom: http://localhost:9090  (if --api-port 9090)
```

### Activity Log Not Updating

- Ensure `--api-activity` is not disabled (default: enabled)
- Check browser developer console for errors
- Try refreshing page

### Devices Not Appearing

```bash
# Verify devices exist via API
curl http://localhost:8080/api/devices | jq

# Check emulator logs for creation errors
# Device should appear in response
```

### Zones Not Displaying

For multizone devices:

- Click "▸ Show zones" to expand display
- Ensure device has `has_multizone: true`
- Check that zone_count > 0 and zone_colors array is populated

For tile/matrix devices:

- Click "▸ Show tiles" to expand display
- Ensure device has `has_matrix: true`
- Check that tile_count > 0 and colors are populated

______________________________________________________________________

## Browser Compatibility

**Tested and Supported:**

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required:**

- JavaScript enabled
- LocalStorage for UI state persistence
- CSS Grid support

______________________________________________________________________

## Security Considerations

The web interface provides no authentication or authorization:

- Intended for local development/testing only
- No user login required
- All operations available to anyone with network access
- Consider firewall rules if on shared network
- Use `--api-host 127.0.0.1` for localhost-only access

______________________________________________________________________

## Advanced Features

### Serial Number Details

Each device has a unique 12-character hexadecimal serial:

- Default prefix: `d073d5`
- Default range: `d073d5000001` - `d073d5999999`
- Can be customized with `--serial-prefix` and `--serial-start` CLI flags

### Product IDs

Common products:

- 27: LIFX A19 (color light)
- 29: LIFX A19 Night Vision (infrared)
- 32: LIFX Z (multizone strip)
- 38: LIFX Beam (extended multizone)
- 50: LIFX Mini White to Warm (color temperature)
- 55: LIFX Tile (matrix/tile device)
- 90: LIFX Clean (HEV)

See `lifx-emulator list-products` for complete list.

______________________________________________________________________

## Related Documentation

- [Device Management API](https://djelibeybi.github.io/lifx-emulator/cli/device-management-api/index.md) - Programmatic API access
- [Scenario Management API](https://djelibeybi.github.io/lifx-emulator/cli/scenario-api/index.md) - Test scenario configuration
