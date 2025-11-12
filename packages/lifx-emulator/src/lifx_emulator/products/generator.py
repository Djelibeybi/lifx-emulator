"""Code generator for LIFX product registry.

Downloads the official products.json from the LIFX GitHub repository and
generates optimized Python code with pre-built product definitions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import yaml

from lifx_emulator.constants import PRODUCTS_URL


def _build_capabilities(features: dict[str, Any]) -> list[str]:
    """Build list of capability flags from product features.

    Args:
        features: Product features dictionary

    Returns:
        List of ProductCapability enum names
    """
    capabilities = []
    if features.get("color"):
        capabilities.append("ProductCapability.COLOR")
    if features.get("infrared"):
        capabilities.append("ProductCapability.INFRARED")
    if features.get("multizone"):
        capabilities.append("ProductCapability.MULTIZONE")
    if features.get("chain"):
        capabilities.append("ProductCapability.CHAIN")
    if features.get("matrix"):
        capabilities.append("ProductCapability.MATRIX")
    if features.get("relays"):
        capabilities.append("ProductCapability.RELAYS")
    if features.get("buttons"):
        capabilities.append("ProductCapability.BUTTONS")
    if features.get("hev"):
        capabilities.append("ProductCapability.HEV")
    return capabilities


def _check_extended_multizone(
    product: dict[str, Any], features: dict[str, Any]
) -> tuple[bool, int | None]:
    """Check if product supports extended multizone and get minimum firmware.

    Args:
        product: Product dictionary with upgrades
        features: Product features dictionary

    Returns:
        Tuple of (has_extended_multizone, min_firmware_version)
    """
    # First check if it's a native feature (no firmware requirement)
    if features.get("extended_multizone"):
        return True, None

    # Check if it's available as an upgrade (requires minimum firmware)
    for upgrade in product.get("upgrades", []):
        if upgrade.get("features", {}).get("extended_multizone"):
            # Parse firmware version (major.minor format)
            major = upgrade.get("major", 0)
            minor = upgrade.get("minor", 0)
            min_ext_mz_firmware = (major << 16) | minor
            return True, min_ext_mz_firmware

    return False, None


def _format_temperature_range(features: dict[str, Any]) -> str:
    """Format temperature range as Python code.

    Args:
        features: Product features dictionary

    Returns:
        Temperature range expression as string
    """
    if "temperature_range" not in features:
        return "None"

    temp_list = features["temperature_range"]
    if len(temp_list) >= 2:
        return f"TemperatureRange(min={temp_list[0]}, max={temp_list[1]})"

    return "None"


def _generate_product_code(
    pid: int,
    name: str,
    vendor_id: int,
    capabilities_expr: str,
    temp_range_expr: str,
    min_ext_mz_firmware: int | None,
) -> list[str]:
    """Generate Python code lines for a single ProductInfo instance.

    Args:
        pid: Product ID
        name: Product name
        vendor_id: Vendor ID
        capabilities_expr: Capabilities bitfield expression
        temp_range_expr: Temperature range expression
        min_ext_mz_firmware: Minimum firmware for extended multizone

    Returns:
        List of code lines
    """
    min_ext_mz_firmware_expr = (
        str(min_ext_mz_firmware) if min_ext_mz_firmware is not None else "None"
    )

    return [
        f"    {pid}: ProductInfo(",
        f"        pid={pid},",
        f"        name={repr(name)},",
        f"        vendor={vendor_id},",
        f"        capabilities={capabilities_expr},",
        f"        temperature_range={temp_range_expr},",
        f"        min_ext_mz_firmware={min_ext_mz_firmware_expr},",
        "    ),",
    ]


def download_products() -> dict[str, Any] | list[dict[str, Any]]:
    """Download and parse products.json from LIFX GitHub repository.

    Returns:
        Parsed products dictionary or list

    Raises:
        URLError: If download fails
        json.JSONDecodeError: If parsing fails
    """
    print(f"Downloading products.json from {PRODUCTS_URL}...")
    with urlopen(PRODUCTS_URL) as response:  # nosec
        products_data = response.read()

    print("Parsing products specification...")
    products = json.loads(products_data)
    return products


def generate_product_definitions(
    products_data: dict[str, Any] | list[dict[str, Any]],
) -> str:
    """Generate Python code for product definitions.

    Args:
        products_data: Parsed products.json data

    Returns:
        Python code string with ProductInfo instances
    """
    code_lines = []

    # Handle both array and object formats
    all_vendors = []
    if isinstance(products_data, list):
        all_vendors = products_data
    else:
        all_vendors = [products_data]

    # Generate product definitions
    code_lines.append("# Pre-generated product definitions")
    code_lines.append("PRODUCTS: dict[int, ProductInfo] = {")

    product_count = 0
    skipped_count = 0
    for vendor_data in all_vendors:
        vendor_id = vendor_data.get("vid", 1)
        defaults = vendor_data.get("defaults", {})
        default_features = defaults.get("features", {})

        # Process each product
        for product in vendor_data.get("products", []):
            pid = product["pid"]
            name = product["name"]
            features = {**default_features, **product.get("features", {})}

            # Skip switch products (devices with relays) - these are not lights
            if features.get("relays"):
                skipped_count += 1
                continue

            # Build capabilities
            capabilities = _build_capabilities(features)

            # Check for extended multizone
            has_ext_mz, min_ext_mz_firmware = _check_extended_multizone(
                product, features
            )
            if has_ext_mz:
                capabilities.append("ProductCapability.EXTENDED_MULTIZONE")

            # Build capabilities expression
            capabilities_expr = " | ".join(capabilities) if capabilities else "0"

            # Format temperature range
            temp_range_expr = _format_temperature_range(features)

            # Generate code for this product
            product_code = _generate_product_code(
                pid,
                name,
                vendor_id,
                capabilities_expr,
                temp_range_expr,
                min_ext_mz_firmware,
            )
            code_lines.extend(product_code)
            product_count += 1

    code_lines.append("}")
    code_lines.append("")

    print(f"Generated {product_count} product definitions")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} switch products (relays only)")
    return "\n".join(code_lines)


def generate_registry_file(products_data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Generate complete registry.py file.

    Args:
        products_data: Parsed products.json data

    Returns:
        Complete Python file content
    """
    header = '''"""LIFX product definitions and capability detection.

DO NOT EDIT THIS FILE MANUALLY.
Generated from https://github.com/LIFX/products/blob/master/products.json
by products/generator.py

This module provides pre-generated product information for efficient runtime lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property


class ProductCapability(IntEnum):
    """Product capability flags."""

    COLOR = 1
    INFRARED = 2
    MULTIZONE = 4
    CHAIN = 8
    MATRIX = 16
    RELAYS = 32
    BUTTONS = 64
    HEV = 128
    EXTENDED_MULTIZONE = 256


@dataclass
class TemperatureRange:
    """Color temperature range in Kelvin."""

    min: int
    max: int


@dataclass
class ProductInfo:
    """Information about a LIFX product.

    Attributes:
        pid: Product ID
        name: Product name
        vendor: Vendor ID (always 1 for LIFX)
        capabilities: Bitfield of ProductCapability flags
        temperature_range: Min/max color temperature in Kelvin
        min_ext_mz_firmware: Minimum firmware version for extended multizone
    """

    pid: int
    name: str
    vendor: int
    capabilities: int
    temperature_range: TemperatureRange | None
    min_ext_mz_firmware: int | None

    def has_capability(self, capability: ProductCapability) -> bool:
        """Check if product has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if product has the capability
        """
        return bool(self.capabilities & capability)

    @property
    def has_color(self) -> bool:
        """Check if product supports color."""
        return self.has_capability(ProductCapability.COLOR)

    @property
    def has_infrared(self) -> bool:
        """Check if product supports infrared."""
        return self.has_capability(ProductCapability.INFRARED)

    @property
    def has_multizone(self) -> bool:
        """Check if product supports multizone."""
        return self.has_capability(ProductCapability.MULTIZONE)

    @property
    def has_chain(self) -> bool:
        """Check if product supports chaining."""
        return self.has_capability(ProductCapability.CHAIN)

    @property
    def has_matrix(self) -> bool:
        """Check if product supports matrix (2D grid)."""
        return self.has_capability(ProductCapability.MATRIX)

    @property
    def has_relays(self) -> bool:
        """Check if product has relays."""
        return self.has_capability(ProductCapability.RELAYS)

    @property
    def has_buttons(self) -> bool:
        """Check if product has buttons."""
        return self.has_capability(ProductCapability.BUTTONS)

    @property
    def has_hev(self) -> bool:
        """Check if product supports HEV."""
        return self.has_capability(ProductCapability.HEV)

    @property
    def has_extended_multizone(self) -> bool:
        """Check if product supports extended multizone."""
        return self.has_capability(ProductCapability.EXTENDED_MULTIZONE)

    def supports_extended_multizone(self, firmware_version: int | None = None) -> bool:
        """Check if extended multizone is supported for given firmware version.

        Args:
            firmware_version: Firmware version to check (optional)

        Returns:
            True if extended multizone is supported
        """
        if not self.has_extended_multizone:
            return False
        if self.min_ext_mz_firmware is None:
            return True
        if firmware_version is None:
            return True
        return firmware_version >= self.min_ext_mz_firmware

    @cached_property
    def caps(self) -> str:
        """Format product capabilities as a human-readable string.

        Returns:
            Comma-separated capability string (e.g., "full color, infrared, multizone")
        """
        caps = []

        # Determine base light type
        if self.has_relays:
            # Devices with relays are switches, not lights
            caps.append("switch")
        elif self.has_color:
            caps.append("full color")
        else:
            # Check temperature range to determine white light type
            if self.temperature_range:
                if self.temperature_range.min != self.temperature_range.max:
                    caps.append("color temperature")
                else:
                    caps.append("brightness only")
            else:
                # No temperature range info, assume basic brightness
                caps.append("brightness only")

        # Add additional capabilities
        if self.has_infrared:
            caps.append("infrared")
        # Extended multizone is backwards compatible with multizone,
        # so only show multizone if extended multizone is not present
        if self.has_extended_multizone:
            caps.append("extended-multizone")
        elif self.has_multizone:
            caps.append("multizone")
        if self.has_matrix:
            caps.append("matrix")
        if self.has_hev:
            caps.append("HEV")
        if self.has_chain:
            caps.append("chain")
        if self.has_buttons and not self.has_relays:
            # Only show buttons if not already identified as switch
            caps.append("buttons")

        return ", ".join(caps) if caps else "unknown"


'''

    # Generate product definitions
    products_code = generate_product_definitions(products_data)

    # Generate helper functions
    helper_functions = '''

class ProductRegistry:
    """Registry of LIFX products and their capabilities."""

    def __init__(self) -> None:
        """Initialize product registry with pre-generated data."""
        self._products = PRODUCTS.copy()  # Copy to allow test overrides
        self._loaded = True  # Always loaded in generated registry

    def load_from_dict(self, data: dict | list) -> None:
        """Load products from parsed JSON data (for testing).

        Args:
            data: Parsed products.json dictionary or array
        """
        from typing import Any

        # Clear existing products
        self._products.clear()

        # Handle both array and object formats
        all_vendors = []
        if isinstance(data, list):
            all_vendors = data
        else:
            all_vendors = [data]

        # Process each vendor
        for vendor_data in all_vendors:
            vendor_id = vendor_data.get("vid", 1)
            defaults = vendor_data.get("defaults", {})
            default_features = defaults.get("features", {})

            # Parse each product
            for product in vendor_data.get("products", []):
                pid = product["pid"]
                name = product["name"]

                # Merge features with defaults
                prod_features = product.get("features", {})
                features: dict[str, Any] = {**default_features, **prod_features}

                # Skip switch products (devices with relays) - these are not lights
                if features.get("relays"):
                    continue

                # Build capabilities bitfield
                capabilities = 0
                if features.get("color"):
                    capabilities |= ProductCapability.COLOR
                if features.get("infrared"):
                    capabilities |= ProductCapability.INFRARED
                if features.get("multizone"):
                    capabilities |= ProductCapability.MULTIZONE
                if features.get("chain"):
                    capabilities |= ProductCapability.CHAIN
                if features.get("matrix"):
                    capabilities |= ProductCapability.MATRIX
                if features.get("relays"):
                    capabilities |= ProductCapability.RELAYS
                if features.get("buttons"):
                    capabilities |= ProductCapability.BUTTONS
                if features.get("hev"):
                    capabilities |= ProductCapability.HEV

                # Check for extended multizone capability
                min_ext_mz_firmware = None

                # First check if it's a native feature (no firmware requirement)
                if features.get("extended_multizone"):
                    capabilities |= ProductCapability.EXTENDED_MULTIZONE
                else:
                    # Check if it's available as an upgrade (requires minimum firmware)
                    for upgrade in product.get("upgrades", []):
                        if upgrade.get("features", {}).get("extended_multizone"):
                            capabilities |= ProductCapability.EXTENDED_MULTIZONE
                            # Parse firmware version (major.minor format)
                            major = upgrade.get("major", 0)
                            minor = upgrade.get("minor", 0)
                            min_ext_mz_firmware = (major << 16) | minor
                            break

                # Parse temperature range
                temp_range = None
                if "temperature_range" in features:
                    temp_list = features["temperature_range"]
                    if len(temp_list) >= 2:
                        temp_range = TemperatureRange(
                            min=temp_list[0], max=temp_list[1]
                        )

                product_info = ProductInfo(
                    pid=pid,
                    name=name,
                    vendor=vendor_id,
                    capabilities=capabilities,
                    temperature_range=temp_range,
                    min_ext_mz_firmware=min_ext_mz_firmware,
                )

                self._products[pid] = product_info

        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        """Check if registry has been loaded."""
        return self._loaded

    def get_product(self, pid: int) -> ProductInfo | None:
        """Get product info by product ID.

        Args:
            pid: Product ID

        Returns:
            ProductInfo if found, None otherwise
        """
        return self._products.get(pid)

    def get_device_class_name(
        self, pid: int, firmware_version: int | None = None
    ) -> str:
        """Get appropriate device class name for a product.

        Args:
            pid: Product ID
            firmware_version: Firmware version (optional)

        Returns:
            Device class name: "TileDevice", "MultiZoneLight", "HevLight",
            "InfraredLight", "Light", or "Device"
        """
        product = self.get_product(pid)
        if product is None:
            # Unknown product - default to Light if we don't know
            return "Light"

        # Matrix devices (Tiles, Candles) → TileDevice
        if product.has_matrix:
            return "TileDevice"

        # MultiZone devices (Strips, Beams) → MultiZoneLight
        if product.has_multizone:
            return "MultiZoneLight"

        # HEV lights → HevLight
        if product.has_hev:
            return "HevLight"

        # Infrared lights → InfraredLight
        if product.has_infrared:
            return "InfraredLight"

        # Color lights → Light
        if product.has_color:
            return "Light"

        # Devices with relays (switches/relays) → Device
        if product.has_relays:
            return "Device"

        # Devices with buttons but no color (switches) → Device
        if product.has_buttons:
            return "Device"

        # Everything else (basic lights, white-to-warm lights) → Light
        # These have no special capabilities but still support Light protocol
        return "Light"

    def __len__(self) -> int:
        """Get number of products in registry."""
        return len(self._products)

    def __contains__(self, pid: int) -> bool:
        """Check if product ID exists in registry."""
        return pid in self._products


# Global registry instance
_registry = ProductRegistry()


def get_registry() -> ProductRegistry:
    """Get the global product registry.

    Returns:
        Global ProductRegistry instance
    """
    return _registry


def get_product(pid: int) -> ProductInfo | None:
    """Get product info by product ID.

    Args:
        pid: Product ID

    Returns:
        ProductInfo if found, None otherwise
    """
    return _registry.get_product(pid)


def get_device_class_name(pid: int, firmware_version: int | None = None) -> str:
    """Get appropriate device class name for a product.

    Args:
        pid: Product ID
        firmware_version: Firmware version (optional)

    Returns:
        Device class name: "TileDevice", "MultiZoneLight", "Light", or "Device"
    """
    return _registry.get_device_class_name(pid, firmware_version)
'''

    return header + products_code + helper_functions


def _load_existing_specs(specs_path: Path) -> dict[int, dict[str, Any]]:
    """Load existing specs from YAML file.

    Args:
        specs_path: Path to specs.yml file

    Returns:
        Dictionary of product specs keyed by PID
    """
    if not specs_path.exists():
        return {}

    with open(specs_path) as f:
        specs_data = yaml.safe_load(f)
        if specs_data and "products" in specs_data:
            return specs_data["products"]

    return {}


def _discover_new_products(
    products_data: dict[str, Any] | list[dict[str, Any]],
    existing_specs: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find new multizone or matrix products that need specs templates.

    Args:
        products_data: Parsed products.json data
        existing_specs: Existing product specs

    Returns:
        List of new product dictionaries with metadata
    """
    all_vendors = []
    if isinstance(products_data, list):
        all_vendors = products_data
    else:
        all_vendors = [products_data]

    new_products = []
    for vendor_data in all_vendors:
        defaults = vendor_data.get("defaults", {})
        default_features = defaults.get("features", {})

        for product in vendor_data.get("products", []):
            pid = product["pid"]
            features = {**default_features, **product.get("features", {})}

            # Skip switch products (devices with relays) - these are not lights
            if features.get("relays"):
                continue

            # Check if this product needs specs template
            if pid not in existing_specs:
                is_multizone = features.get("multizone", False)
                is_matrix = features.get("matrix", False)

                if is_multizone or is_matrix:
                    new_product = {
                        "pid": pid,
                        "name": product["name"],
                        "multizone": is_multizone,
                        "matrix": is_matrix,
                        "extended_multizone": False,
                    }

                    # Check for extended multizone in upgrades
                    for upgrade in product.get("upgrades", []):
                        if upgrade.get("features", {}).get("extended_multizone"):
                            new_product["extended_multizone"] = True
                            break

                    new_products.append(new_product)

    return new_products


def _add_product_templates(
    new_products: list[dict[str, Any]], existing_specs: dict[int, dict[str, Any]]
) -> None:
    """Add templates for new products to existing specs.

    Args:
        new_products: List of new product dictionaries
        existing_specs: Existing product specs (modified in place)
    """
    for product in new_products:
        product_name = product["name"].replace('"', '\\"')

        if product["multizone"]:
            existing_specs[product["pid"]] = {
                "default_zone_count": 16,
                "min_zone_count": 1,
                "max_zone_count": 16,
                "notes": product_name,
            }
        elif product["matrix"]:
            existing_specs[product["pid"]] = {
                "default_tile_count": 1,
                "min_tile_count": 1,
                "max_tile_count": 1,
                "tile_width": 8,
                "tile_height": 8,
                "notes": product_name,
            }


def _categorize_products(
    existing_specs: dict[int, dict[str, Any]],
) -> tuple[list[int], list[int]]:
    """Categorize products into multizone and matrix.

    Args:
        existing_specs: Product specs dictionary

    Returns:
        Tuple of (sorted_multizone_pids, sorted_matrix_pids)
    """
    multizone_pids = []
    matrix_pids = []

    for pid, specs in existing_specs.items():
        if "tile_width" in specs or "tile_height" in specs:
            matrix_pids.append(pid)
        elif "default_zone_count" in specs:
            multizone_pids.append(pid)

    multizone_pids.sort()
    matrix_pids.sort()

    return multizone_pids, matrix_pids


def _generate_yaml_header() -> list[str]:
    """Generate YAML file header with documentation.

    Returns:
        List of header lines
    """
    return [
        "# LIFX Product Specs and Defaults",
        "# =================================",
        "#",
        "# This file contains product-specific details that are not available in the",
        "# upstream LIFX products.json catalog, such as default zone counts, tile",
        "# configurations, and other device-specific defaults.",
        "#",
        "# These values are used by the emulator to create realistic device",
        "# configurations when specific parameters are not provided by the user.",
        "#",
        "# Format:",
        "# -------",
        "# products:",
        "#   <product_id>:",
        "#     # For multizone devices",
        "#     default_zone_count: <number>      # Default zones (e.g., 16)",
        "#     min_zone_count: <number>          # Minimum zones supported",
        "#     max_zone_count: <number>          # Maximum zones supported",
        "#",
        "#     # For matrix devices (tiles, candles, etc.)",
        "#     default_tile_count: <number>      # Default number of tiles in chain",
        "#     min_tile_count: <number>          # Minimum tiles supported",
        "#     max_tile_count: <number>          # Maximum tiles supported",
        "#     tile_width: <number>              # Width of each tile in pixels",
        "#     tile_height: <number>             # Height of each tile in pixels",
        "#",
        "#     # Other device-specific defaults",
        '#     notes: "<string>"                 # Notes about product',
        "",
        "products:",
    ]


def _generate_multizone_section(
    multizone_pids: list[int], existing_specs: dict[int, dict[str, Any]]
) -> list[str]:
    """Generate YAML lines for multizone products section.

    Args:
        multizone_pids: Sorted list of multizone product IDs
        existing_specs: Product specs dictionary

    Returns:
        List of YAML lines
    """
    if not multizone_pids:
        return []

    lines = [
        "  # ========================================",
        "  # Multizone Products (Linear Strips)",
        "  # ========================================",
        "",
    ]

    for pid in multizone_pids:
        specs = existing_specs[pid]
        name = specs.get("notes", f"Product {pid}").split(" - ")[0]

        lines.append(f"  {pid}:  # {name}")
        lines.append(f"    default_zone_count: {specs['default_zone_count']}")
        lines.append(f"    min_zone_count: {specs['min_zone_count']}")
        lines.append(f"    max_zone_count: {specs['max_zone_count']}")

        notes = specs.get("notes", "")
        if notes:
            notes_escaped = notes.replace('"', '\\"')
            lines.append(f'    notes: "{notes_escaped}"')
        lines.append("")

    return lines


def _generate_matrix_section(
    matrix_pids: list[int], existing_specs: dict[int, dict[str, Any]]
) -> list[str]:
    """Generate YAML lines for matrix products section.

    Args:
        matrix_pids: Sorted list of matrix product IDs
        existing_specs: Product specs dictionary

    Returns:
        List of YAML lines
    """
    if not matrix_pids:
        return []

    lines = [
        "  # ========================================",
        "  # Matrix Products (Tiles, Candles, etc.)",
        "  # ========================================",
        "",
    ]

    for pid in matrix_pids:
        specs = existing_specs[pid]
        name = specs.get("notes", f"Product {pid}").split(" - ")[0]

        lines.append(f"  {pid}:  # {name}")
        lines.append(f"    default_tile_count: {specs['default_tile_count']}")
        lines.append(f"    min_tile_count: {specs['min_tile_count']}")
        lines.append(f"    max_tile_count: {specs['max_tile_count']}")
        lines.append(f"    tile_width: {specs['tile_width']}")
        lines.append(f"    tile_height: {specs['tile_height']}")

        notes = specs.get("notes", "")
        if notes:
            notes_escaped = notes.replace('"', '\\"')
            lines.append(f'    notes: "{notes_escaped}"')
        lines.append("")

    return lines


def update_specs_file(
    products_data: dict[str, Any] | list[dict[str, Any]], specs_path: Path
) -> None:
    """Update specs.yml with templates for new products and sort all entries by PID.

    Args:
        products_data: Parsed products.json data
        specs_path: Path to specs.yml file
    """
    # Load existing specs
    existing_specs = _load_existing_specs(specs_path)

    # Find new products that need specs
    new_products = _discover_new_products(products_data, existing_specs)

    # Print status
    if not new_products:
        print("No new multizone or matrix products found - specs.yml is up to date")
        if existing_specs:
            print("Sorting existing specs entries by product ID...")
        else:
            return
    else:
        print(f"\nFound {len(new_products)} new products that need specs:")
        for product in new_products:
            print(f"  PID {product['pid']:>3}: {product['name']}")

    # Add templates for new products
    _add_product_templates(new_products, existing_specs)

    # Categorize products and sort
    multizone_pids, matrix_pids = _categorize_products(existing_specs)

    # Build YAML content
    lines = _generate_yaml_header()
    lines.extend(_generate_multizone_section(multizone_pids, existing_specs))
    lines.extend(_generate_matrix_section(matrix_pids, existing_specs))

    # Write the new file
    with open(specs_path, "w") as f:
        f.write("\n".join(lines))

    # Print completion message
    if new_products:
        print(
            f"\n✓ Added {len(new_products)} new product templates "
            f"and sorted all entries by PID"
        )
        print(
            "  Please review and update the placeholder values "
            "with actual product specifications"
        )
    else:
        print(f"\n✓ Sorted all {len(existing_specs)} specs entries by product ID")


def main() -> None:
    """Main generator entry point."""
    try:
        # Download and parse products from GitHub
        products_data = download_products()
    except Exception as e:
        print(f"Error: Failed to download products.json: {e}", file=sys.stderr)
        sys.exit(1)

    # Count products for summary
    if isinstance(products_data, list):
        all_products = []
        for vendor in products_data:
            all_products.extend(vendor.get("products", []))
    else:
        all_products = products_data.get("products", [])

    print(f"Found {len(all_products)} products")

    # Generate registry.py
    print("\nGenerating registry.py...")
    registry_code = generate_registry_file(products_data)

    # Determine output path
    registry_path = Path(__file__).parent / "registry.py"

    with open(registry_path, "w") as f:
        f.write(registry_code)

    print(f"✓ Generated {registry_path}")

    # Update specs.yml with templates for new products
    print("\nChecking for new products that need specs...")
    specs_path = Path(__file__).parent / "specs.yml"

    try:
        update_specs_file(products_data, specs_path)
    except Exception as e:
        print(f"Warning: Failed to update specs.yml: {e}", file=sys.stderr)
        print("You can manually add specs for new products")

    print("\n✓ Generation complete!")


if __name__ == "__main__":
    main()
