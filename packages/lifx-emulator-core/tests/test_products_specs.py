"""Unit tests for the products.specs module."""

import tempfile
from pathlib import Path

from lifx_emulator.factories.firmware_config import FirmwareConfig
from lifx_emulator.products.specs import (
    ProductSpecs,
    SpecsRegistry,
    get_default_tile_count,
    get_default_zone_count,
    get_specs,
    get_specs_registry,
    get_tile_dimensions,
)


class TestProductSpecs:
    """Test ProductSpecs dataclass."""

    def test_has_multizone_specs_true(self):
        """Test has_multizone_specs returns True when default_zone_count is set."""
        specs = ProductSpecs(product_id=32, default_zone_count=16)
        assert specs.has_multizone_specs is True

    def test_has_multizone_specs_false(self):
        """Test has_multizone_specs returns False when default_zone_count is None."""
        specs = ProductSpecs(product_id=27)
        assert specs.has_multizone_specs is False

    def test_has_matrix_specs_with_width(self):
        """Test has_matrix_specs returns True when tile_width is set."""
        specs = ProductSpecs(product_id=55, tile_width=8)
        assert specs.has_matrix_specs is True

    def test_has_matrix_specs_with_height(self):
        """Test has_matrix_specs returns True when tile_height is set."""
        specs = ProductSpecs(product_id=55, tile_height=8)
        assert specs.has_matrix_specs is True

    def test_has_matrix_specs_false(self):
        """Test has_matrix_specs returns False when both width and height are None."""
        specs = ProductSpecs(product_id=27)
        assert specs.has_matrix_specs is False

    def test_has_firmware_specs_true(self):
        """Test has_firmware_specs returns True when both major and minor are set."""
        specs = ProductSpecs(
            product_id=27, default_firmware_major=3, default_firmware_minor=70
        )
        assert specs.has_firmware_specs is True

    def test_has_firmware_specs_false_no_major(self):
        """Test has_firmware_specs returns False when major is None."""
        specs = ProductSpecs(product_id=27, default_firmware_minor=70)
        assert specs.has_firmware_specs is False

    def test_has_firmware_specs_false_no_minor(self):
        """Test has_firmware_specs returns False when minor is None."""
        specs = ProductSpecs(product_id=27, default_firmware_major=3)
        assert specs.has_firmware_specs is False

    def test_has_firmware_specs_false_both_none(self):
        """Test has_firmware_specs returns False when both are None."""
        specs = ProductSpecs(product_id=27)
        assert specs.has_firmware_specs is False


class TestSpecsRegistry:
    """Test SpecsRegistry class."""

    def test_load_from_file_nonexistent(self):
        """Test load_from_file with non-existent file sets loaded flag."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.yml"
            registry.load_from_file(nonexistent)
            assert registry.is_loaded is True
            assert len(registry) == 0

    def test_load_from_file_empty(self):
        """Test load_from_file with empty file."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.yml"
            empty_file.write_text("")
            registry.load_from_file(empty_file)
            assert registry.is_loaded is True
            assert len(registry) == 0

    def test_load_from_file_no_products_key(self):
        """Test load_from_file with file missing 'products' key."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("other_key: value\n")
            registry.load_from_file(specs_file)
            assert registry.is_loaded is True
            assert len(registry) == 0

    def test_load_from_file_with_products(self):
        """Test load_from_file loads products correctly."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("""
products:
  32:
    default_zone_count: 16
    min_zone_count: 8
    max_zone_count: 82
    notes: "LIFX Z Strip"
  55:
    default_tile_count: 5
    tile_width: 8
    tile_height: 8
    notes: "LIFX Tile"
""")
            registry.load_from_file(specs_file)
            assert registry.is_loaded is True
            assert len(registry) == 2
            assert 32 in registry
            assert 55 in registry

    def test_get_specs_lazy_load(self):
        """Test get_specs triggers lazy loading."""
        registry = SpecsRegistry()
        # Should trigger load_from_file on first access
        registry.get_specs(32)
        assert registry.is_loaded is True

    def test_has_specs_lazy_load(self):
        """Test has_specs triggers lazy loading."""
        registry = SpecsRegistry()
        # Should trigger load_from_file on first access
        registry.has_specs(32)
        assert registry.is_loaded is True

    def test_get_default_zone_count_found(self):
        """Test get_default_zone_count returns value when found."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("""
products:
  32:
    default_zone_count: 16
""")
            registry.load_from_file(specs_file)
            assert registry.get_default_zone_count(32) == 16

    def test_get_default_zone_count_not_found(self):
        """Test get_default_zone_count returns None when not found."""
        registry = SpecsRegistry()
        registry.load_from_file(Path("nonexistent.yml"))
        assert registry.get_default_zone_count(999) is None

    def test_get_default_tile_count_found(self):
        """Test get_default_tile_count returns value when found."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("""
products:
  55:
    default_tile_count: 5
""")
            registry.load_from_file(specs_file)
            assert registry.get_default_tile_count(55) == 5

    def test_get_default_tile_count_not_found(self):
        """Test get_default_tile_count returns None when not found."""
        registry = SpecsRegistry()
        registry.load_from_file(Path("nonexistent.yml"))
        assert registry.get_default_tile_count(999) is None

    def test_get_tile_dimensions_found(self):
        """Test get_tile_dimensions returns tuple when both dimensions set."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("""
products:
  55:
    tile_width: 8
    tile_height: 8
""")
            registry.load_from_file(specs_file)
            assert registry.get_tile_dimensions(55) == (8, 8)

    def test_get_tile_dimensions_missing_height(self):
        """Test get_tile_dimensions returns None when height is missing."""
        registry = SpecsRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_file = Path(tmpdir) / "specs.yml"
            specs_file.write_text("""
products:
  55:
    tile_width: 8
""")
            registry.load_from_file(specs_file)
            assert registry.get_tile_dimensions(55) is None

    def test_get_tile_dimensions_not_found(self):
        """Test get_tile_dimensions returns None when product not found."""
        registry = SpecsRegistry()
        registry.load_from_file(Path("nonexistent.yml"))
        assert registry.get_tile_dimensions(999) is None

    def test_get_default_firmware_version_found(self):
        """Test get_default_firmware_version when both fields are set."""
        registry = SpecsRegistry()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                """
products:
  27:
    default_firmware_major: 3
    default_firmware_minor: 70
"""
            )
            temp_path = Path(f.name)

        try:
            registry.load_from_file(temp_path)
            result = registry.get_default_firmware_version(27)
            assert result == (3, 70)
        finally:
            temp_path.unlink()

    def test_get_default_firmware_version_missing_minor(self):
        """Test get_default_firmware_version returns None when minor is missing."""
        registry = SpecsRegistry()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                """
products:
  27:
    default_firmware_major: 3
"""
            )
            temp_path = Path(f.name)

        try:
            registry.load_from_file(temp_path)
            result = registry.get_default_firmware_version(27)
            assert result is None
        finally:
            temp_path.unlink()

    def test_get_default_firmware_version_not_found(self):
        """Test get_default_firmware_version returns None for non-existent product."""
        registry = SpecsRegistry()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("products:\n  27:\n    notes: Test\n")
            temp_path = Path(f.name)

        try:
            registry.load_from_file(temp_path)
            result = registry.get_default_firmware_version(999)
            assert result is None
        finally:
            temp_path.unlink()

    def test_len_triggers_lazy_load(self):
        """Test __len__ triggers lazy loading."""
        registry = SpecsRegistry()
        len(registry)
        assert registry.is_loaded is True


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_get_specs_registry(self):
        """Test get_specs_registry returns the global registry."""
        registry = get_specs_registry()
        assert isinstance(registry, SpecsRegistry)

    def test_get_specs(self):
        """Test get_specs uses global registry."""
        # This will use the actual specs.yml file from the project
        # Just verify it returns None or ProductSpecs
        result = get_specs(32)
        assert result is None or isinstance(result, ProductSpecs)

    def test_get_default_zone_count(self):
        """Test get_default_zone_count module function."""
        result = get_default_zone_count(32)
        assert result is None or isinstance(result, int)

    def test_get_default_tile_count(self):
        """Test get_default_tile_count module function."""
        result = get_default_tile_count(55)
        assert result is None or isinstance(result, int)

    def test_get_tile_dimensions(self):
        """Test get_tile_dimensions module function."""
        result = get_tile_dimensions(55)
        assert result is None or isinstance(result, tuple)

    def test_get_default_firmware_version(self):
        """Test get_default_firmware_version module function."""
        from lifx_emulator.products.specs import get_default_firmware_version

        result = get_default_firmware_version(27)
        assert result is None or isinstance(result, tuple)


class TestFirmwareConfigWithProductSpecs:
    """Test FirmwareConfig with product-specific defaults."""

    def test_firmware_version_with_product_specs(self):
        """Test firmware version uses specs when product_id provided."""
        from lifx_emulator.products.specs import get_specs_registry

        # Create temp specs file with firmware version
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml_content = """
products:
  27:
    default_firmware_major: 4
    default_firmware_minor: 50
"""
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            # Load specs into global registry
            registry = get_specs_registry()
            registry.load_from_file(temp_path)

            # Test with product_id - should use specs from global registry
            config = FirmwareConfig()
            version = config.get_firmware_version(product_id=27)
            assert version == (4, 50), f"Expected (4, 50) from specs, got {version}"

        finally:
            temp_path.unlink()

    def test_firmware_version_precedence_override_wins(self):
        """Test explicit override takes precedence over specs."""
        config = FirmwareConfig()
        version = config.get_firmware_version(
            product_id=27, extended_multizone=True, override=(5, 0)
        )
        assert version == (5, 0)

    def test_firmware_version_precedence_no_specs(self):
        """Test fallback to extended_multizone when no specs."""
        config = FirmwareConfig()

        # No product_id, extended=True -> 3.70
        version = config.get_firmware_version(extended_multizone=True)
        assert version == (3, 70)

        # No product_id, extended=False -> 2.60
        version = config.get_firmware_version(extended_multizone=False)
        assert version == (2, 60)

    def test_firmware_version_product_not_in_specs(self):
        """Test fallback to extended_multizone when product not in specs."""
        config = FirmwareConfig()
        # Product 999 won't have specs, should fall back
        version = config.get_firmware_version(product_id=999, extended_multizone=True)
        assert version == (3, 70)
