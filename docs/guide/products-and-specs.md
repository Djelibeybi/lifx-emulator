# LIFX Product Registry and Specifications

This directory contains the product registry and specification library for the LIFX emulator.

## Files

### `registry.py` (Auto-generated)

**DO NOT EDIT MANUALLY**

Generated from the official LIFX products.json catalog. Contains:

- Product IDs and names
- Vendor IDs
- Capabilities (color, multizone, matrix, infrared, HEV, etc.)
- Temperature ranges
- Extended multizone firmware versions

To regenerate:
```bash
python -m lifx_emulator.products.generator
```

### `specs.yml` (Manual configuration)

**EDIT THIS FILE**

Contains product-specific details not available in the upstream catalog:

- Default zone counts for multizone devices
- Min/max zone counts
- Default tile counts for matrix devices
- Min/max tile counts
- Tile dimensions (width x height in pixels)
- Product-specific notes

### `specs.py`
Python module for loading and accessing specification data.

### `generator.py`
Script to download and generate `registry.py` from the official LIFX products.json.

## Customizing Specifications

When the product generator creates specifications, you can edit them in `specs.yml` to customize defaults or add product-specific notes.

#### For Multizone Devices (Strips, Beams, Neon)
```yaml
products:
  <product_id>:
    default_zone_count: <number>    # Typical zone count
    min_zone_count: <number>        # Minimum zones supported
    max_zone_count: <number>        # Maximum zones supported
    notes: "<description>"
```

**Example - LIFX Z Strip:**
```yaml
products:
  32:
    default_zone_count: 16
    min_zone_count: 1
    max_zone_count: 16
    notes: "LIFX Z with extended multizone firmware support"
```

**Example - LIFX Beam:**
```yaml
products:
  38:
    default_zone_count: 80
    min_zone_count: 10
    max_zone_count: 82
    notes: "LIFX Beam, 8 individual beams, each with 10 zones and up to 2 corners"
```

#### For Matrix Devices (Tiles, Candles, Ceiling)
```yaml
products:
  <product_id>:
    default_tile_count: <number>    # Typical number of tiles in chain
    min_tile_count: <number>        # Minimum tiles supported
    max_tile_count: <number>        # Maximum tiles supported
    tile_width: <pixels>            # Width of each tile
    tile_height: <pixels>           # Height of each tile
    notes: "<description>"
```

**Example - LIFX Tile:**
```yaml
products:
  55:
    default_tile_count: 5
    min_tile_count: 1
    max_tile_count: 5
    tile_width: 8
    tile_height: 8
    notes: "LIFX Tile, 8x8 pixel matrix, chainable up to 5"
```

**Example - LIFX Candle:**
```yaml
products:
  57:
    default_tile_count: 1
    min_tile_count: 1
    max_tile_count: 1
    tile_width: 5
    tile_height: 6
    notes: "LIFX Candle, 5x6 pixel matrix, single unit"
```

**Example - LIFX Ceiling:**
```yaml
products:
  176:
    default_tile_count: 1
    min_tile_count: 1
    max_tile_count: 1
    tile_width: 22
    tile_height: 22
    notes: "LIFX Ceiling, 22x22 pixel matrix"
```

## How Specifications Are Used

### Multizone Devices

When creating a multizone device without specifying `zone_count`:

1. Check `specs.yml` for `default_zone_count`
2. If not found, use registry capability defaults:
   - Extended multizone: 82 zones
   - Standard multizone: 16 zones

```python
# Uses specification default (80 zones for Beam)
device = create_device(38)

# Override with custom count
device = create_device(38, zone_count=40)
```

### Matrix Devices

When creating a matrix device:

1. **Tile dimensions**: Always from `specs.yml` (required for accuracy)
2. **Tile count**: From `specs.yml` if not specified by user

```python
# Uses specification: 5 tiles of 8x8 pixels
device = create_device(55)

# Custom tile count, specification dimensions
device = create_device(55, tile_count=3)  # 3 tiles of 8x8 pixels

# Candle: 1 tile of 5x5 pixels (from specification)
device = create_device(57)

# Ceiling: 1 tile of 22x22 pixels (from specification)
device = create_device(176)
```


## Current Specification Coverage

All multizone and matrix devices currently available have specifications defined:

- **Multizone**: 19 products (Z, Beam, Neon, String, Outdoor Neon, Indoor Neon, Permanent Outdoor - with US and international variants)
- **Matrix**: 22 products (Tile, Candle, Ceiling, Round Spot, Round Path, Square Path, Tube, Luna - with US and international variants)
- **Total**: 41 products with specifications defined

See `specs.yml` for the complete list.

## Maintenance

### When to Update Specifications

1. **New LIFX products released**: The generator automatically creates a specification - edit `specs.yml` to customize defaults or add product-specific notes
2. **Product specifications change**: Update specification values in `specs.yml`
3. **Better information available**: Refine default values
4. **User reports incorrect defaults**: Verify and update in `specs.yml`

### Regenerating Registry

When LIFX releases new products or updates the catalog:
```bash
# Download latest products.json and regenerate registry.py
python -m lifx_emulator.products.generator

# Specifications are auto-generated; edit specs.yml to customize if needed
# Test with: lifx-emulator --product <new_pid>
```

## API Reference

### Python API

```python
from lifx_emulator.products.specs import (
    get_specs,
    get_default_zone_count,
    get_default_tile_count,
    get_tile_dimensions,
)

# Get all specification for a product
specification = get_specs(55)  # LIFX Tile
if specification:
    print(f"Default tiles: {specification.default_tile_count}")
    print(f"Tile size: {specification.tile_width}x{specification.tile_height}")

# Get specific values
zones = get_default_zone_count(32)  # 16 for LIFX Z
tiles = get_default_tile_count(55)  # 5 for LIFX Tile
width, height = get_tile_dimensions(176)  # (22, 22) for LIFX Ceiling
```

## Contributing

When you discover more accurate specification information:

1. Edit or refine the specification in `specs.yml`
2. Test with `python -m lifx_emulator --product <product ID>`
3. Include source/reference in the `notes` field
4. Submit your refinement either as pull request or open an issue.

For questions or help, check the main project README.
