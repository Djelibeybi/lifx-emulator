# Products API Reference

> LIFX product registry and capability detection

The products module provides auto-generated product definitions from the official LIFX product registry, including product IDs, capabilities, temperature ranges, and device specifications. This enables accurate emulation of specific LIFX device types.

---

## Table of Contents

### Core Components

- [ProductInfo](#productinfo) - Product metadata and capabilities
- [ProductCapability](#productcapability) - Capability flags enum
- [Product Registry](#product-registry) - Accessing product database
- [ProductSpecs](#productspecs) - Device-specific specifications

### Concepts

- [Capability Matrix](#capability-matrix) - Complete product capabilities
- [Product Filtering](#product-filtering) - Query products by capability
- [Using Products](#using-products) - Creating devices from products

---

## ProductInfo

Dataclass containing complete information about a LIFX product.

```python
@dataclass
class ProductInfo:
    pid: int                              # Product ID
    name: str                             # Product name (e.g., "LIFX A19")
    vendor: int                           # Vendor ID (always 1 for LIFX)
    capabilities: int                     # Bitfield of capabilities
    temperature_range: TemperatureRange | None  # Min/max Kelvin
    min_ext_mz_firmware: int | None       # Min firmware for extended multizone
```

### Fields

#### `pid` (int)
Product ID number. Common examples:

- `27`: LIFX A19
- `32`: LIFX Z (multizone strip)
- `38`: LIFX Beam (extended multizone)
- `55`: LIFX Tile
- `90`: LIFX Clean (HEV)

#### `name` (str)
Human-readable product name (e.g., "LIFX A19", "LIFX Z", "LIFX Tile").

#### `vendor` (int)
Vendor ID. Always `1` for LIFX products.

#### `capabilities` (int)
Bitfield of `ProductCapability` flags. Use `has_capability()` or property methods to check.

#### `temperature_range` (TemperatureRange | None)
Supported color temperature range in Kelvin.

- `min`: Minimum Kelvin (e.g., 2500 for warm white)
- `max`: Maximum Kelvin (e.g., 9000 for cool white)
- `None` for non-color-temperature devices (relays, switches)

#### `min_ext_mz_firmware` (int | None)
Minimum firmware version required for extended multizone support (>16 zones).

- `None` if not applicable or always supported

### Methods

#### `has_capability(capability: ProductCapability) -> bool`

Check if product has a specific capability.

**Parameters:**
- **`capability`** (`ProductCapability`) - Capability to check

**Returns:** `bool` - `True` if product has the capability

**Example:**
```python
from lifx_emulator.products import get_product, ProductCapability

product = get_product(32)  # LIFX Z
if product.has_capability(ProductCapability.MULTIZONE):
    print(f"{product.name} supports multizone")
```

#### Property Methods

Convenience properties for common capability checks:

- **`has_color`** → `bool` - Full RGB color support
- **`has_infrared`** → `bool` - Infrared (night vision) support
- **`has_multizone`** → `bool` - Multizone (linear strips) support
- **`has_chain`** → `bool` - Device chaining support
- **`has_matrix`** → `bool` - 2D matrix/tile support
- **`has_relays`** → `bool` - Relay switches
- **`has_buttons`** → `bool` - Physical buttons
- **`has_hev`** → `bool` - HEV (germicidal light) support
- **`has_extended_multizone`** → `bool` - Extended multizone (>16 zones)

**Example:**
```python
product = get_product(55)  # LIFX Tile
print(f"Color: {product.has_color}")         # True
print(f"Matrix: {product.has_matrix}")       # True
print(f"Multizone: {product.has_multizone}") # False
```

#### `supports_extended_multizone(firmware_version: int | None = None) -> bool`

Check if extended multizone is supported for a given firmware version.

**Parameters:**
- **`firmware_version`** (`int | None`) - Firmware version to check (optional)

**Returns:** `bool` - `True` if extended multizone is supported

**Example:**
```python
product = get_product(38)  # LIFX Beam
if product.supports_extended_multizone():
    print("Supports 80 zones!")
```

---

## ProductCapability

Enum of capability flags used in product definitions.

```python
class ProductCapability(IntEnum):
    COLOR = 1               # Full RGB color
    INFRARED = 2            # Night vision IR
    MULTIZONE = 4           # Linear zones (strips)
    CHAIN = 8               # Device chaining
    MATRIX = 16             # 2D tile grid
    RELAYS = 32             # Relay switches
    BUTTONS = 64            # Physical buttons
    HEV = 128               # Germicidal light
    EXTENDED_MULTIZONE = 256  # >16 zones
```

### Usage

```python
from lifx_emulator.products import ProductCapability

# Check multiple capabilities
capabilities = ProductCapability.COLOR | ProductCapability.INFRARED
has_color = bool(capabilities & ProductCapability.COLOR)        # True
has_multizone = bool(capabilities & ProductCapability.MULTIZONE) # False
```

---

## Product Registry

The `PRODUCTS` dictionary and helper functions provide access to the product database.

### `get_product(pid: int) -> ProductInfo | None`

Retrieve product information by product ID.

**Parameters:**
- **`pid`** (`int`) - Product ID

**Returns:** `ProductInfo | None` - Product information or `None` if not found

**Example:**
```python
from lifx_emulator.products import get_product

product = get_product(27)  # LIFX A19
if product:
    print(f"Product: {product.name}")
    print(f"Capabilities: {product.capabilities}")
    print(f"Temperature range: {product.temperature_range.min}-{product.temperature_range.max}K")
```

### `get_registry() -> dict[int, ProductInfo]`

Get the complete product registry.

**Returns:** `dict[int, ProductInfo]` - Mapping of product ID to ProductInfo

**Example:**
```python
from lifx_emulator.products import get_registry

registry = get_registry()
print(f"Total products: {len(registry)}")

for pid, product in registry.items():
    if product.has_multizone:
        print(f"{pid}: {product.name}")
```

### `get_device_class_name(product: ProductInfo) -> str`

Get the device class name based on capabilities.

**Parameters:**
- **`product`** (`ProductInfo`) - Product to classify

**Returns:** `str` - Device class name ("color", "multizone", "matrix", "hev", etc.)

**Example:**
```python
from lifx_emulator.products import get_product, get_device_class_name

product = get_product(32)
class_name = get_device_class_name(product)
print(f"Device class: {class_name}")  # "multizone"
```

---

## ProductSpecs

Device-specific specifications (zone counts, tile dimensions, etc.) are stored in the specs system.

### `get_product_specs(product_id: int) -> dict | None`

Get detailed specifications for a product.

**Parameters:**
- **`product_id`** (`int`) - Product ID

**Returns:** `dict | None` - Specifications dictionary or `None`

**Spec Fields:**
- `zone_count`: Number of zones (multizone devices)
- `extended_multizone`: Extended multizone support flag
- `tile_count`: Default number of tiles (matrix devices)
- `tile_width`: Tile width in pixels (matrix devices)
- `tile_height`: Tile height in pixels (matrix devices)

**Example:**
```python
from lifx_emulator.specs import get_product_specs

# LIFX Z (standard multizone)
specs = get_product_specs(32)
print(f"Zones: {specs['zone_count']}")  # 16

# LIFX Beam (extended multizone)
specs = get_product_specs(38)
print(f"Zones: {specs['zone_count']}")           # 80
print(f"Extended: {specs['extended_multizone']}") # True

# LIFX Tile
specs = get_product_specs(55)
print(f"Tiles: {specs['tile_count']}")     # 5
print(f"Dimensions: {specs['tile_width']}x{specs['tile_height']}")  # 8x8
```

---

## Capability Matrix

Complete capability matrix for major LIFX products:

| Product ID | Name | Color | Infrared | Multizone | Extended MZ | Matrix | HEV | Temp Range (K) |
|------------|------|-------|----------|-----------|-------------|--------|-----|----------------|
| 1 | LIFX Original 1000 | ✓ | | | | | | 2500-9000 |
| 27 | LIFX A19 | ✓ | | | | | | 2500-9000 |
| 29 | LIFX A19 Night Vision | ✓ | ✓ | | | | | 2500-9000 |
| 32 | LIFX Z | ✓ | | ✓ | | | | 2500-9000 |
| 36 | LIFX Downlight | ✓ | | | | | | 2500-9000 |
| 38 | LIFX Beam | ✓ | | ✓ | ✓ | | | 2500-9000 |
| 43 | LIFX BR30 | ✓ | | | | | | 2500-9000 |
| 44 | LIFX BR30 Night Vision | ✓ | ✓ | | | | | 2500-9000 |
| 50 | LIFX Mini White to Warm | | | | | | | 2700-6500 |
| 55 | LIFX Tile | ✓ | | | | ✓ | | 2500-9000 |
| 57 | LIFX Candle | ✓ | | | | ✓ | | 2500-9000 |
| 66 | LIFX GU10 | ✓ | | | | | | 2500-9000 |
| 90 | LIFX Clean | ✓ | | | | | ✓ | 2500-9000 |
| 141 | LIFX Neon | ✓ | | ✓ | | | | 2500-9000 |
| 176 | LIFX Ceiling | ✓ | | | | ✓ | | 2500-9000 |

**Legend:**
- **Color**: Full RGB color control
- **Infrared**: Night vision capability
- **Multizone**: Linear zone control (up to 16 zones)
- **Extended MZ**: Extended multizone (>16 zones)
- **Matrix**: 2D tile/matrix control
- **HEV**: Germicidal UV-C light
- **Temp Range**: Color temperature range in Kelvin

---

## Product Filtering

Filter products by capabilities using the registry:

### Filter by Single Capability

```python
from lifx_emulator.products import get_registry, ProductCapability

registry = get_registry()

# Find all multizone products
multizone_products = [
    product for product in registry.values()
    if product.has_multizone
]

for product in multizone_products:
    print(f"{product.pid}: {product.name}")
# Output: 32: LIFX Z, 38: LIFX Beam, 141: LIFX Neon, etc.
```

### Filter by Multiple Capabilities

```python
# Find all color + infrared products
color_ir_products = [
    product for product in registry.values()
    if product.has_color and product.has_infrared
]

for product in color_ir_products:
    print(f"{product.pid}: {product.name}")
# Output: 29: LIFX A19 Night Vision, 44: LIFX BR30 Night Vision
```

### Filter by Temperature Range

```python
# Find products that support warm white (< 3000K)
warm_white_products = [
    product for product in registry.values()
    if product.temperature_range and product.temperature_range.min < 3000
]

for product in warm_white_products:
    print(f"{product.pid}: {product.name} ({product.temperature_range.min}K)")
```

### Filter Extended Multizone

```python
# Find extended multizone products (>16 zones)
extended_mz_products = [
    product for product in registry.values()
    if product.has_extended_multizone
]

for product in extended_mz_products:
    print(f"{product.pid}: {product.name}")
# Output: 38: LIFX Beam, etc.
```

### Custom Filter Function

```python
def filter_products(
    color: bool = False,
    multizone: bool = False,
    matrix: bool = False,
    hev: bool = False,
) -> list[ProductInfo]:
    """Filter products by capabilities."""
    registry = get_registry()
    results = []

    for product in registry.values():
        if color and not product.has_color:
            continue
        if multizone and not product.has_multizone:
            continue
        if matrix and not product.has_matrix:
            continue
        if hev and not product.has_hev:
            continue
        results.append(product)

    return results

# Usage
matrix_products = filter_products(matrix=True)
color_multizone = filter_products(color=True, multizone=True)
```

---

## Using Products

### Creating Devices from Product IDs

```python
from lifx_emulator.factories import create_device
from lifx_emulator.products import get_product

# Create device by product ID
device = create_device(product_id=27)  # LIFX A19

# Get product info
product = get_product(27)
print(f"Created: {product.name}")
print(f"Color: {device.state.has_color}")
print(f"Multizone: {device.state.has_multizone}")
```

### Using Product Specs for Configuration

```python
from lifx_emulator.factories import create_device
from lifx_emulator.specs import get_product_specs

# Create LIFX Z with product defaults
device = create_device(product_id=32)

# Specs are automatically applied
specs = get_product_specs(32)
assert device.state.zone_count == specs['zone_count']  # 16 zones

# Override defaults
device = create_device(product_id=32, zone_count=8)  # Custom: 8 zones
```

### Listing Available Products

Command-line tool to list all products:

```bash
# List all products
lifx-emulator list-products

# Filter by capability
lifx-emulator list-products --filter-type multizone
lifx-emulator list-products --filter-type matrix
lifx-emulator list-products --filter-type hev
```

**Example Output:**
```
LIFX Product Registry
┌──────┬────────────────────────────────────────────┬──────────────────────────┐
│ ID   │ Product Name                               │ Capabilities             │
├──────┼────────────────────────────────────────────┼──────────────────────────┤
│ 27   │ LIFX A19                                   │ full color               │
│ 29   │ LIFX A19 Night Vision                      │ full color, infrared     │
│ 32   │ LIFX Z                                     │ full color, multizone    │
│ 38   │ LIFX Beam                                  │ full color, extended-mz  │
│ 55   │ LIFX Tile                                  │ full color, matrix       │
│ 90   │ LIFX Clean                                 │ full color, HEV          │
└──────┴────────────────────────────────────────────┴──────────────────────────┘
```

### Programmatic Product Listing

```python
from lifx_emulator.products import get_registry

def list_products(filter_capability: str | None = None):
    """List all products with optional capability filter."""
    registry = get_registry()

    for pid, product in sorted(registry.items()):
        # Apply filter
        if filter_capability == "multizone" and not product.has_multizone:
            continue
        if filter_capability == "matrix" and not product.has_matrix:
            continue
        if filter_capability == "hev" and not product.has_hev:
            continue

        # Print product info
        capabilities = []
        if product.has_color:
            capabilities.append("color")
        if product.has_infrared:
            capabilities.append("infrared")
        if product.has_multizone:
            capabilities.append("multizone")
        if product.has_extended_multizone:
            capabilities.append("extended-mz")
        if product.has_matrix:
            capabilities.append("matrix")
        if product.has_hev:
            capabilities.append("HEV")

        print(f"{pid:3d}  {product.name:40s}  {', '.join(capabilities)}")

# Usage
list_products()
list_products(filter_capability="matrix")
```

---

## Product Data Source

The product registry is auto-generated from the official LIFX product database:

- **Source:** [LIFX/products on GitHub](https://github.com/LIFX/products)
- **Generator:** `src/lifx_emulator/products/generator.py`
- **Registry:** `src/lifx_emulator/products/registry.py` (auto-generated)
- **Specs:** `src/lifx_emulator/specs/` (manually curated device specifications)

### Updating Products

To update the product registry with the latest LIFX products:

```bash
# Run the generator (fetches latest from GitHub)
python -m lifx_emulator.products.generator

# Verify changes
git diff src/lifx_emulator/products/registry.py
```

---

## References

**Source Files:**
- `src/lifx_emulator/products/registry.py` - Product registry (auto-generated)
- `src/lifx_emulator/products/generator.py` - Registry generator
- `src/lifx_emulator/specs/` - Product specifications

**Related Documentation:**
- [Factories API](factories.md) - Device creation from product IDs
- [Device API](device.md) - Device capabilities and state
- [Device Types Guide](../guide/device-types.md) - Supported device types
- [CLI Reference](../getting-started/cli.md) - Command-line product usage

**External Resources:**
- [LIFX Products GitHub](https://github.com/LIFX/products) - Official product database
- [LIFX Developer Docs](https://lan.developer.lifx.com/) - Protocol specification
