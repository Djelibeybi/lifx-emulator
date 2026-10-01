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
    name: str                             # Product name (e.g., "LIFX (A19)")
    vendor: int                           # Vendor ID (always 1 for LIFX)
    capabilities: int                     # Bitfield of capabilities
    temperature_range: TemperatureRange | None  # Min/max Kelvin
    min_ext_mz_firmware: int | None       # Min firmware for extended multizone
```

### Fields

#### `pid` (int)
Product ID number. Common examples:

- `27`: LIFX (A19)
- `32`: LIFX Z (multizone strip)
- `38`: LIFX Beam (extended multizone)
- `55`: LIFX Tile
- `90`: LIFX Clean A19 1100lm (HEV)

#### `name` (str)
Human-readable product name (e.g., "LIFX (A19)", "LIFX Z", "LIFX Tile").

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
Minimum firmware version required for extended multizone support, encoded as `(major << 16) | minor`.

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
- **`has_extended_multizone`** → `bool` - Extended multizone protocol support

**Example:**
```python
from lifx_emulator.products import get_product

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
from lifx_emulator.products import get_product

product = get_product(38)  # LIFX Beam
if product.supports_extended_multizone():
    print("Supports extended multizone messages")
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
    EXTENDED_MULTIZONE = 256  # Extended multizone protocol
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

The `PRODUCTS` dictionary (in `lifx_emulator.products.registry`) and helper functions provide access to the product database.

### `get_product(pid: int) -> ProductInfo | None`

Retrieve product information by product ID.

**Parameters:**
- **`pid`** (`int`) - Product ID

**Returns:** `ProductInfo | None` - Product information or `None` if not found

**Example:**
```python
from lifx_emulator.products import get_product

product = get_product(27)  # LIFX (A19)
if product and product.temperature_range:
    print(f"Product: {product.name}")
    print(f"Capabilities: {product.capabilities}")
    print(f"Temperature range: {product.temperature_range.min}-{product.temperature_range.max}K")
```

### `get_registry() -> ProductRegistry`

Get the global product registry. `ProductRegistry` supports `get_product(pid)`, `len()` and `in`; to iterate over every product, use the `PRODUCTS` dictionary.

**Returns:** `ProductRegistry` - The global registry instance

**Example:**
```python
from lifx_emulator.products import get_registry
from lifx_emulator.products.registry import PRODUCTS

registry = get_registry()
print(f"Total products: {len(registry)}")
print(f"Has LIFX Z: {32 in registry}")

for pid, product in PRODUCTS.items():
    if product.has_multizone:
        print(f"{pid}: {product.name}")
```

### `get_device_class_name(pid: int, firmware_version: int | None = None) -> str`

Get the device class name based on a product's capabilities.

**Parameters:**
- **`pid`** (`int`) - Product ID to classify
- **`firmware_version`** (`int | None`) - Firmware version (optional)

**Returns:** `str` - Device class name (`"TileDevice"`, `"MultiZoneLight"`, `"HevLight"`, `"InfraredLight"`, `"Light"` or `"Device"`)

**Example:**
```python
from lifx_emulator.products import get_device_class_name

class_name = get_device_class_name(32)
print(f"Device class: {class_name}")  # "MultiZoneLight"
```

---

## ProductSpecs

Device-specific specifications (zone counts, tile dimensions, etc.) are stored in the specs system.

### `get_specs(product_id: int) -> ProductSpecs | None`

Get detailed specifications for a product (from `lifx_emulator.products.specs`, loaded from `specs.yml`).

**Parameters:**
- **`product_id`** (`int`) - Product ID

**Returns:** `ProductSpecs | None` - Specifications dataclass or `None` if the product has no specs

**Spec Fields** (all optional, `None` when not set):
- `default_zone_count`, `min_zone_count`, `max_zone_count`: Zone counts (multizone devices)
- `default_tile_count`, `min_tile_count`, `max_tile_count`: Tile counts (matrix devices)
- `tile_width`, `tile_height`: Tile dimensions in zones (matrix devices)
- `default_firmware_major`, `default_firmware_minor`: Default firmware version
- `max_firmware_major`, `max_firmware_minor`: Terminal firmware version for discontinued products
- `uplight_zone_count`, `zone_map`, `button_count`, `notes`

Extended multizone support comes from the product registry (`ProductInfo.has_extended_multizone`), not from specs.

**Example:**
```python
from lifx_emulator.products.specs import get_specs

# LIFX Z
specs = get_specs(32)
print(f"Zones: {specs.default_zone_count}")  # 16

# LIFX Beam
specs = get_specs(38)
print(f"Zones: {specs.default_zone_count}")  # 80

# LIFX Tile
specs = get_specs(55)
print(f"Tiles: {specs.default_tile_count}")  # 5
print(f"Dimensions: {specs.tile_width}x{specs.tile_height}")  # 8x8
```

---

## Capability Matrix

Complete capability matrix for major LIFX products:

| Product ID | Name | Color | Infrared | Multizone | Extended MZ | Matrix | HEV | Temp Range (K) |
|------------|------|-------|----------|-----------|-------------|--------|-----|----------------|
| 1 | Original | ✓ | | | | | | 2500-9000 |
| 27 | LIFX (A19) | ✓ | | | | | | 2500-9000 |
| 29 | LIFX+ (A19) | ✓ | ✓ | | | | | 2500-9000 |
| 30 | LIFX+ (BR30) | ✓ | ✓ | | | | | 2500-9000 |
| 32 | LIFX Z | ✓ | | ✓ | ✓ | | | 2500-9000 |
| 36 | LIFX DL | ✓ | | | | | | 2500-9000 |
| 38 | LIFX Beam | ✓ | | ✓ | ✓ | | | 2500-9000 |
| 44 | LIFX (BR30) | ✓ | | | | | | 2500-9000 |
| 50 | LIFX Mini DD | | | | | | | 2500-9000 |
| 52 | LIFX GU10 | ✓ | | | | | | 1500-9000 |
| 55 | LIFX Tile | ✓ | | | | ✓ | | 2500-9000 |
| 57 | LIFX Candle C | ✓ | | | | ✓ | | 1500-9000 |
| 90 | LIFX Clean A19 1100lm | ✓ | | | | | ✓ | 1500-9000 |
| 141 | LIFX Neon | ✓ | | ✓ | ✓ | | | 1500-9000 |
| 176 | LIFX Ceiling | ✓ | | | | ✓ | | 1500-9000 |

**Legend:**
- **Color**: Full RGB color control
- **Infrared**: Night vision capability
- **Multizone**: Linear zone control
- **Extended MZ**: Extended multizone protocol support (independent of zone count)
- **Matrix**: 2D tile/matrix control
- **HEV**: Germicidal UV-C light
- **Temp Range**: Color temperature range in Kelvin

---

## Product Filtering

Filter products by capabilities using the registry:

### Filter by Single Capability

```python
from lifx_emulator.products.registry import PRODUCTS

# Find all multizone products
multizone_products = [
    product for product in PRODUCTS.values()
    if product.has_multizone
]

for product in multizone_products:
    print(f"{product.pid}: {product.name}")
# Output: 32: LIFX Z, 38: LIFX Beam, 141: LIFX Neon, etc.
```

### Filter by Multiple Capabilities

```python
from lifx_emulator.products.registry import PRODUCTS

# Find all color + infrared products
color_ir_products = [
    product for product in PRODUCTS.values()
    if product.has_color and product.has_infrared
]

for product in color_ir_products:
    print(f"{product.pid}: {product.name}")
# Output: 25: LIFX+ (A19), 26: LIFX+ (BR30), 29: LIFX+ (A19), etc.
```

### Filter by Temperature Range

```python
from lifx_emulator.products.registry import PRODUCTS

# Find products that support warm white (< 3000K)
warm_white_products = [
    product for product in PRODUCTS.values()
    if product.temperature_range and product.temperature_range.min < 3000
]

for product in warm_white_products:
    print(f"{product.pid}: {product.name} ({product.temperature_range.min}K)")
```

### Filter Extended Multizone

```python
from lifx_emulator.products.registry import PRODUCTS

# Find extended multizone products
extended_mz_products = [
    product for product in PRODUCTS.values()
    if product.has_extended_multizone
]

for product in extended_mz_products:
    print(f"{product.pid}: {product.name}")
# Output: 32: LIFX Z, 38: LIFX Beam, etc.
```

### Custom Filter Function

```python
from lifx_emulator.products import ProductInfo
from lifx_emulator.products.registry import PRODUCTS


def filter_products(
    color: bool = False,
    multizone: bool = False,
    matrix: bool = False,
    hev: bool = False,
) -> list[ProductInfo]:
    """Filter products by capabilities."""
    results = []

    for product in PRODUCTS.values():
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
device = create_device(product_id=27)  # LIFX (A19)

# Get product info
product = get_product(27)
print(f"Created: {product.name}")
print(f"Color: {device.state.has_color}")
print(f"Multizone: {device.state.has_multizone}")
```

### Using Product Specs for Configuration

```python
from lifx_emulator.factories import create_device
from lifx_emulator.products.specs import get_specs

# Create LIFX Z with product defaults
device = create_device(product_id=32)

# Specs are automatically applied
specs = get_specs(32)
assert device.state.zone_count == specs.default_zone_count  # 16 zones

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

**Example Output** (excerpt):
```text
LIFX Product Registry (173 products)

 PID │ Product Name                             │ Capabilities
─────┼──────────────────────────────────────────┼─────────────────────────────────────────
  27 │ LIFX (A19)                               │ color
  29 │ LIFX+ (A19)                              │ color, infrared
  32 │ LIFX Z                                   │ color, extended-multizone
  38 │ LIFX Beam                                │ color, extended-multizone
  55 │ LIFX Tile                                │ color, matrix, chain
  90 │ LIFX Clean A19 1100lm                    │ color, HEV
```

### Programmatic Product Listing

```python
from lifx_emulator.products.registry import PRODUCTS

def list_products(filter_capability: str | None = None):
    """List all products with optional capability filter."""
    for pid, product in sorted(PRODUCTS.items()):
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
- **Generator:** `packages/lifx-emulator-core/src/lifx_emulator/products/generator.py`
- **Registry:** `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` (auto-generated)
- **Specs:** `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml` (manually curated device specifications, loaded by `products/specs.py`)

### Updating Products

To update the product registry with the latest LIFX products:

```bash
# Run the generator (fetches latest from GitHub)
python -m lifx_emulator.products.generator

# Verify changes
git diff packages/lifx-emulator-core/src/lifx_emulator/products/registry.py
```

---

## References

**Source Files:**
- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` - Product registry (auto-generated)
- `packages/lifx-emulator-core/src/lifx_emulator/products/generator.py` - Registry generator
- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.py`, `specs.yml` - Product specifications

**Related Documentation:**
- [Factories API](factories.md) - Device creation from product IDs
- [Device API](device.md) - Device capabilities and state
- [Device Types Guide](../guide/device-types.md) - Supported device types
- [CLI Reference](../cli/cli-reference.md) - Command-line product usage

**External Resources:**
- [LIFX Products GitHub](https://github.com/LIFX/products) - Official product database
- [LIFX Developer Docs](https://lan.developer.lifx.com/) - Protocol specification
