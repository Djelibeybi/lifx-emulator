"""Product specs and defaults for LIFX devices.

This module provides access to product-specific details that are not available
in the upstream LIFX products.json catalog, such as default zone counts and
tile configurations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ProductSpecs:
    """Product-specific specs and defaults.

    Attributes:
        product_id: Product ID this applies to
        default_zone_count: Default number of zones for multizone devices
        min_zone_count: Minimum zones supported
        max_zone_count: Maximum zones supported
        default_tile_count: Default number of tiles in chain
        min_tile_count: Minimum tiles supported
        max_tile_count: Maximum tiles supported
        tile_width: Width of each tile in pixels
        tile_height: Height of each tile in pixels
        notes: Human-readable notes about this product
    """

    product_id: int
    default_zone_count: int | None = None
    min_zone_count: int | None = None
    max_zone_count: int | None = None
    default_tile_count: int | None = None
    min_tile_count: int | None = None
    max_tile_count: int | None = None
    tile_width: int | None = None
    tile_height: int | None = None
    notes: str | None = None

    @property
    def has_multizone_specs(self) -> bool:
        """Check if this product has multizone-specific specs."""
        return self.default_zone_count is not None

    @property
    def has_matrix_specs(self) -> bool:
        """Check if this product has matrix-specific specs."""
        return self.tile_width is not None or self.tile_height is not None


class SpecsRegistry:
    """Registry of product specs loaded from specs.yml."""

    def __init__(self) -> None:
        """Initialize empty specs registry."""
        self._specs: dict[int, ProductSpecs] = {}
        self._loaded = False

    def load_from_file(self, specs_path: Path | None = None) -> None:
        """Load specs from YAML file.

        Args:
            specs_path: Path to specs.yml file. If None, uses default location.
        """
        if specs_path is None:
            specs_path = Path(__file__).parent / "specs.yml"

        if not specs_path.exists():
            # No specs file, that's okay - we'll use registry defaults only
            self._loaded = True
            return

        with open(specs_path) as f:
            data = yaml.safe_load(f)

        if not data or "products" not in data:
            self._loaded = True
            return

        # Parse product specs
        for pid, specs_data in data["products"].items():
            self._specs[int(pid)] = ProductSpecs(
                product_id=int(pid),
                default_zone_count=specs_data.get("default_zone_count"),
                min_zone_count=specs_data.get("min_zone_count"),
                max_zone_count=specs_data.get("max_zone_count"),
                default_tile_count=specs_data.get("default_tile_count"),
                min_tile_count=specs_data.get("min_tile_count"),
                max_tile_count=specs_data.get("max_tile_count"),
                tile_width=specs_data.get("tile_width"),
                tile_height=specs_data.get("tile_height"),
                notes=specs_data.get("notes"),
            )

        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        """Check if specs have been loaded."""
        return self._loaded

    def get_specs(self, product_id: int) -> ProductSpecs | None:
        """Get specs for a specific product.

        Args:
            product_id: Product ID to look up

        Returns:
            ProductSpecs if found, None otherwise
        """
        if not self._loaded:
            self.load_from_file()

        return self._specs.get(product_id)

    def has_specs(self, product_id: int) -> bool:
        """Check if a product has specs defined.

        Args:
            product_id: Product ID to check

        Returns:
            True if specs exist for this product
        """
        if not self._loaded:
            self.load_from_file()

        return product_id in self._specs

    def get_default_zone_count(self, product_id: int) -> int | None:
        """Get default zone count for a multizone product.

        Args:
            product_id: Product ID

        Returns:
            Default zone count if defined, None otherwise
        """
        specs = self.get_specs(product_id)
        return specs.default_zone_count if specs else None

    def get_default_tile_count(self, product_id: int) -> int | None:
        """Get default tile count for a matrix product.

        Args:
            product_id: Product ID

        Returns:
            Default tile count if defined, None otherwise
        """
        specs = self.get_specs(product_id)
        return specs.default_tile_count if specs else None

    def get_tile_dimensions(self, product_id: int) -> tuple[int, int] | None:
        """Get tile dimensions for a matrix product.

        Args:
            product_id: Product ID

        Returns:
            Tuple of (width, height) if defined, None otherwise
        """
        specs = self.get_specs(product_id)
        if specs and specs.tile_width and specs.tile_height:
            return (specs.tile_width, specs.tile_height)
        return None

    def __len__(self) -> int:
        """Get number of products with specs."""
        if not self._loaded:
            self.load_from_file()
        return len(self._specs)

    def __contains__(self, product_id: int) -> bool:
        """Check if product has specs."""
        return self.has_specs(product_id)


# Global specs registry instance
_specs_registry = SpecsRegistry()


def get_specs_registry() -> SpecsRegistry:
    """Get the global specs registry.

    Returns:
        Global SpecsRegistry instance
    """
    return _specs_registry


def get_specs(product_id: int) -> ProductSpecs | None:
    """Get specs for a specific product.

    Args:
        product_id: Product ID to look up

    Returns:
        ProductSpecs if found, None otherwise
    """
    return _specs_registry.get_specs(product_id)


def get_default_zone_count(product_id: int) -> int | None:
    """Get default zone count for a multizone product.

    Args:
        product_id: Product ID

    Returns:
        Default zone count if defined, None otherwise
    """
    return _specs_registry.get_default_zone_count(product_id)


def get_default_tile_count(product_id: int) -> int | None:
    """Get default tile count for a matrix product.

    Args:
        product_id: Product ID

    Returns:
        Default tile count if defined, None otherwise
    """
    return _specs_registry.get_default_tile_count(product_id)


def get_tile_dimensions(product_id: int) -> tuple[int, int] | None:
    """Get tile dimensions for a matrix product.

    Args:
        product_id: Product ID

    Returns:
        Tuple of (width, height) if defined, None otherwise
    """
    return _specs_registry.get_tile_dimensions(product_id)
