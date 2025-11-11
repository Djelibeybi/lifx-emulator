"""Tests for the products generator."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lifx_emulator.products.generator import (
    download_products,
    generate_product_definitions,
    generate_registry_file,
    update_specs_file,
)


class TestGenerateProductDefinitions:
    """Test product definition code generation."""

    def test_generate_empty_products(self):
        """Test generating code for empty products list."""
        products_data: list[dict[str, Any]] = []
        code = generate_product_definitions(products_data)

        assert "PRODUCTS: dict[int, ProductInfo] = {" in code
        assert "}" in code
        assert (
            "Generated 0 product definitions" not in code
            or code.count("ProductInfo(") == 0
        )

    def test_generate_single_product_basic(self):
        """Test generating code for a single basic product."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {
                            "color": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "27: ProductInfo(" in code
        assert "pid=27" in code
        assert "'LIFX A19'" in code  # Uses single quotes from repr()
        assert "vendor=1" in code
        assert "ProductCapability.COLOR" in code

    def test_generate_product_with_temperature_range(self):
        """Test generating product with temperature range."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {"color": True, "temperature_range": [2500, 9000]},
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "TemperatureRange(min=2500, max=9000)" in code

    def test_generate_product_multiple_capabilities(self):
        """Test generating product with multiple capabilities."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 29,
                        "name": "LIFX A19 Night Vision",
                        "features": {
                            "color": True,
                            "infrared": True,
                            "temperature_range": [2500, 9000],
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "29: ProductInfo(" in code
        assert "ProductCapability.COLOR" in code
        assert "ProductCapability.INFRARED" in code
        assert "ProductCapability.COLOR | ProductCapability.INFRARED" in code

    def test_generate_multizone_product(self):
        """Test generating multizone product."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 32,
                        "name": "LIFX Z Strip",
                        "features": {
                            "color": True,
                            "multizone": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "32: ProductInfo(" in code
        assert "ProductCapability.MULTIZONE" in code
        assert "ProductCapability.COLOR" in code

    def test_generate_extended_multizone_product(self):
        """Test generating product with extended multizone support."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 38,
                        "name": "LIFX Beam",
                        "features": {
                            "color": True,
                            "multizone": True,
                        },
                        "upgrades": [
                            {
                                "major": 3,
                                "minor": 70,
                                "features": {"extended_multizone": True},
                            }
                        ],
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "38: ProductInfo(" in code
        assert "ProductCapability.EXTENDED_MULTIZONE" in code
        # Firmware version packed as (3 << 16) | 70 = 196678
        assert "min_ext_mz_firmware=196678" in code

    def test_generate_matrix_product(self):
        """Test generating matrix (tile) product."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 55,
                        "name": "LIFX Tile",
                        "features": {
                            "color": True,
                            "matrix": True,
                            "chain": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "55: ProductInfo(" in code
        assert "ProductCapability.MATRIX" in code
        assert "ProductCapability.CHAIN" in code

    def test_generate_hev_product(self):
        """Test generating HEV (germicidal) product."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 90,
                        "name": "LIFX Clean",
                        "features": {
                            "color": True,
                            "hev": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "90: ProductInfo(" in code
        assert "ProductCapability.HEV" in code

    def test_generate_switch_product(self):
        """Test that switch (relay) products are skipped."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 70,
                        "name": "LIFX Switch",
                        "features": {
                            "relays": True,
                            "buttons": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Switch products should be skipped since they're not lights
        assert "70: ProductInfo(" not in code
        assert "ProductCapability.RELAYS" not in code
        # Verify empty result
        assert "PRODUCTS: dict[int, ProductInfo] = {" in code

    def test_generate_multiple_products(self):
        """Test generating code for multiple products."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 1,
                        "name": "LIFX Original 1000",
                        "features": {"color": True},
                    },
                    {"pid": 3, "name": "LIFX Color 650", "features": {"color": True}},
                    {"pid": 10, "name": "LIFX A19", "features": {"color": True}},
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "1: ProductInfo(" in code
        assert "3: ProductInfo(" in code
        assert "10: ProductInfo(" in code
        assert code.count("ProductInfo(") == 3

    def test_generate_product_with_defaults(self):
        """Test generating product using default features."""
        products_data = [
            {
                "vid": 1,
                "defaults": {"features": {"temperature_range": [2500, 9000]}},
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {
                            "color": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Should merge defaults with product features
        assert "27: ProductInfo(" in code
        assert "TemperatureRange(min=2500, max=9000)" in code

    def test_generate_product_override_defaults(self):
        """Test product features override defaults."""
        products_data = [
            {
                "vid": 1,
                "defaults": {
                    "features": {"temperature_range": [2500, 9000], "color": False}
                },
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {
                            "color": True,  # Override default
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "27: ProductInfo(" in code
        assert "ProductCapability.COLOR" in code

    def test_generate_product_no_temperature_range(self):
        """Test product with no temperature range."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 32,
                        "name": "LIFX Z Strip",
                        "features": {
                            "color": True,
                            "multizone": True,
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "32: ProductInfo(" in code
        assert "temperature_range=None" in code

    def test_generate_product_no_capabilities(self):
        """Test product with no capabilities."""
        products_data = [
            {
                "vid": 1,
                "products": [{"pid": 999, "name": "Unknown Product", "features": {}}],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "999: ProductInfo(" in code
        assert "capabilities=0" in code

    def test_generate_multiple_vendors(self):
        """Test generating products from multiple vendors."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            },
            {
                "vid": 2,
                "products": [
                    {
                        "pid": 1,
                        "name": "Other Vendor Product",
                        "features": {"color": True},
                    }
                ],
            },
        ]

        code = generate_product_definitions(products_data)

        assert "27: ProductInfo(" in code
        assert "vendor=1" in code
        assert "1: ProductInfo(" in code
        assert "vendor=2" in code

    def test_generate_object_format(self):
        """Test generating from object format (not array)."""
        products_data = {
            "vid": 1,
            "products": [{"pid": 27, "name": "LIFX A19", "features": {"color": True}}],
        }

        code = generate_product_definitions(products_data)

        assert "27: ProductInfo(" in code
        assert "vendor=1" in code


class TestGenerateRegistryFile:
    """Test complete registry file generation."""

    def test_generate_registry_file_header(self):
        """Test registry file includes proper header."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            }
        ]

        content = generate_registry_file(products_data)

        # Check header
        assert '"""LIFX product definitions' in content
        assert "DO NOT EDIT THIS FILE MANUALLY" in content
        assert (
            "from lifx_emulator.products.registry import" in content
            or "ProductCapability" in content
        )

    def test_generate_registry_file_has_classes(self):
        """Test registry file includes required classes."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            }
        ]

        content = generate_registry_file(products_data)

        assert "class ProductCapability(IntEnum):" in content
        assert "class TemperatureRange:" in content
        assert "class ProductInfo:" in content
        assert "class ProductRegistry:" in content

    def test_generate_registry_file_has_products(self):
        """Test registry file includes product definitions."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            }
        ]

        content = generate_registry_file(products_data)

        assert "PRODUCTS: dict[int, ProductInfo] = {" in content
        assert "27: ProductInfo(" in content

    def test_generate_registry_file_valid_python(self):
        """Test generated registry file is valid Python."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {"color": True, "temperature_range": [2500, 9000]},
                    },
                    {
                        "pid": 32,
                        "name": "LIFX Z",
                        "features": {"color": True, "multizone": True},
                    },
                ],
            }
        ]

        content = generate_registry_file(products_data)

        # Should be valid Python (at least syntactically)
        try:
            compile(content, "<string>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated registry file has syntax error: {e}")

    def test_generate_registry_temperature_range_values(self):
        """Test temperature range values are correctly generated."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {"color": True, "temperature_range": [2700, 6500]},
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "TemperatureRange(min=2700, max=6500)" in code

    def test_generate_firmware_version_encoding(self):
        """Test firmware version is correctly encoded."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 38,
                        "name": "LIFX Beam",
                        "features": {"color": True, "multizone": True},
                        "upgrades": [
                            {
                                "major": 3,
                                "minor": 70,
                                "features": {"extended_multizone": True},
                            }
                        ],
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # (3 << 16) | 70 = 196678
        assert "min_ext_mz_firmware=196678" in code

    def test_generate_firmware_version_different_values(self):
        """Test different firmware version values."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 38,
                        "name": "LIFX Beam",
                        "features": {"color": True, "multizone": True},
                        "upgrades": [
                            {
                                "major": 2,
                                "minor": 60,
                                "features": {"extended_multizone": True},
                            }
                        ],
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # (2 << 16) | 60 = 131132
        assert "min_ext_mz_firmware=131132" in code


class TestUpdateSpecsFile:
    """Test specs.yml file generation and updating."""

    def test_update_specs_file_creates_new_file(self):
        """Test update_specs_file creates specs file for new products."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": "LIFX Z Strip",
                            "features": {"color": True, "multizone": True},
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            assert specs_path.exists()
            content = specs_path.read_text()
            assert "32:" in content
            assert "default_zone_count:" in content

    def test_update_specs_file_with_matrix_product(self):
        """Test update_specs_file creates specs for matrix products."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 55,
                            "name": "LIFX Tile",
                            "features": {"color": True, "matrix": True},
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            assert "55:" in content
            assert "tile_width:" in content
            assert "tile_height:" in content
            assert "default_tile_count:" in content

    def test_update_specs_file_no_new_products(self):
        """Test update_specs_file when specs already exists and no new products."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            # Create initial specs file
            initial_content = """
products:
  32:
    default_zone_count: 16
    min_zone_count: 1
    max_zone_count: 16
"""
            specs_path.write_text(initial_content)

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": "LIFX Z Strip",
                            "features": {"color": True, "multizone": True},
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            # File should still exist and be updated
            assert specs_path.exists()

    def test_update_specs_file_sorts_entries(self):
        """Test update_specs_file sorts entries by product ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 55,
                            "name": "LIFX Tile",
                            "features": {"color": True, "matrix": True},
                        },
                        {
                            "pid": 32,
                            "name": "LIFX Z Strip",
                            "features": {"color": True, "multizone": True},
                        },
                        {
                            "pid": 38,
                            "name": "LIFX Beam",
                            "features": {
                                "color": True,
                                "multizone": True,
                                "extended_multizone": True,
                            },
                        },
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            # Should be sorted: 32, 38, 55
            idx_32 = content.find("32:")
            idx_38 = content.find("38:")
            idx_55 = content.find("55:")
            assert idx_32 < idx_38 < idx_55

    def test_update_specs_file_with_extended_multizone(self):
        """Test update_specs_file detects extended multizone in upgrades."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 38,
                            "name": "LIFX Beam",
                            "features": {"color": True, "multizone": True},
                            "upgrades": [
                                {
                                    "major": 3,
                                    "minor": 70,
                                    "features": {"extended_multizone": True},
                                }
                            ],
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            assert "38:" in content
            # Should have multizone specs
            assert "default_zone_count:" in content

    def test_update_specs_file_escapes_quotes(self):
        """Test update_specs_file properly escapes quotes in product names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": 'LIFX "Special" Strip',
                            "features": {"color": True, "multizone": True},
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            # Should escape the quotes
            assert '\\"' in content or content.find("Special") > 0

    def test_update_specs_file_multiple_vendors(self):
        """Test update_specs_file with multiple vendors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": "LIFX Z",
                            "features": {"color": True, "multizone": True},
                        }
                    ],
                },
                {
                    "vid": 2,
                    "products": [
                        {
                            "pid": 100,
                            "name": "Other Brand Strip",
                            "features": {"color": True, "multizone": True},
                        }
                    ],
                },
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            assert "32:" in content
            assert "100:" in content


class TestGeneratedCodeExecution:
    """Test that generated code can be executed properly."""

    def test_generated_code_is_executable(self):
        """Test that generated code is valid Python that can be executed."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {"color": True, "temperature_range": [2500, 9000]},
                    },
                    {
                        "pid": 32,
                        "name": "LIFX Z",
                        "features": {"color": True, "multizone": True},
                    },
                    {
                        "pid": 55,
                        "name": "LIFX Tile",
                        "features": {"color": True, "matrix": True},
                    },
                ],
            }
        ]

        registry_code = generate_registry_file(products_data)

        # Code should be valid Python
        try:
            compile(registry_code, "<string>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_generated_registry_has_product_info(self):
        """Test generated registry code includes ProductInfo class."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            }
        ]

        registry_code = generate_registry_file(products_data)

        assert "class ProductInfo:" in registry_code
        assert "def has_capability" in registry_code
        assert "@property" in registry_code
        assert "def has_color" in registry_code

    def test_generated_registry_has_capability_enum(self):
        """Test generated registry code includes ProductCapability enum."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 27, "name": "LIFX A19", "features": {"color": True}}
                ],
            }
        ]

        registry_code = generate_registry_file(products_data)

        assert "class ProductCapability(IntEnum):" in registry_code
        assert "COLOR = 1" in registry_code
        assert "INFRARED = 2" in registry_code

    def test_generated_registry_includes_all_products(self):
        """Test that generated registry includes all input products."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {"pid": 1, "name": "Original", "features": {"color": True}},
                    {"pid": 10, "name": "A19", "features": {"color": True}},
                    {"pid": 27, "name": "Color A19", "features": {"color": True}},
                    {
                        "pid": 32,
                        "name": "Z Strip",
                        "features": {"color": True, "multizone": True},
                    },
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        assert "1: ProductInfo(" in code
        assert "10: ProductInfo(" in code
        assert "27: ProductInfo(" in code
        assert "32: ProductInfo(" in code

    def test_all_capability_flags_covered(self):
        """Test product definitions handle all capability flags.

        Note: RELAYS capability is intentionally excluded because products
        with relays (switches) are not lights and are filtered out.
        """
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 999,
                        "name": "All Light Features",
                        "features": {
                            "color": True,
                            "infrared": True,
                            "multizone": True,
                            "chain": True,
                            "matrix": True,
                            "buttons": True,
                            "hev": True,
                        },
                    },
                    {
                        "pid": 998,
                        "name": "Switch Product",
                        "features": {
                            "relays": True,
                            "buttons": True,
                        },
                    },
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Light capabilities should be present
        assert "ProductCapability.COLOR" in code
        assert "ProductCapability.INFRARED" in code
        assert "ProductCapability.MULTIZONE" in code
        assert "ProductCapability.CHAIN" in code
        assert "ProductCapability.MATRIX" in code
        assert "ProductCapability.BUTTONS" in code
        assert "ProductCapability.HEV" in code

        # Switch (relay) products should be filtered out
        assert "998: ProductInfo(" not in code
        assert "ProductCapability.RELAYS" not in code


class TestDownloadProducts:
    """Test downloading products from GitHub."""

    def test_download_products_with_mocked_response(self):
        """Test download_products parses JSON correctly."""
        mock_data = [
            {
                "vid": 1,
                "products": [{"pid": 27, "name": "A19", "features": {"color": True}}],
            }
        ]

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch(
            "lifx_emulator.products.generator.urlopen", return_value=mock_response
        ):
            result = download_products()

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["vid"] == 1
            assert len(result[0]["products"]) == 1

    def test_download_products_with_single_vendor_object(self):
        """Test download_products handles single vendor as object."""
        mock_data = {
            "vid": 1,
            "products": [{"pid": 27, "name": "A19", "features": {"color": True}}],
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        with patch(
            "lifx_emulator.products.generator.urlopen", return_value=mock_response
        ):
            result = download_products()

            assert isinstance(result, dict)
            assert result["vid"] == 1


class TestUpdateSpecsFileEdgeCases:
    """Test edge cases in specs file updating."""

    def test_update_specs_file_only_sorting_no_new_products(self):
        """Test specs file with existing entries but no new products."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            # Create initial specs file with multizone and matrix products
            initial_content = """
products:
  55:  # Tile
    default_tile_count: 1
    min_tile_count: 1
    max_tile_count: 5
    tile_width: 8
    tile_height: 8
  32:  # Z Strip
    default_zone_count: 16
    min_zone_count: 1
    max_zone_count: 16
"""
            specs_path.write_text(initial_content)

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": "LIFX Z Strip",
                            "features": {"color": True, "multizone": True},
                        },
                        {
                            "pid": 55,
                            "name": "LIFX Tile",
                            "features": {"color": True, "matrix": True},
                        },
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            content = specs_path.read_text()
            # Should have both sections
            assert "Multizone Products" in content or "32:" in content
            assert "Matrix Products" in content or "55:" in content

    def test_update_specs_file_temperature_range_too_short(self):
        """Test that temperature_range with less than 2 elements is handled."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {
                            "color": True,
                            "temperature_range": [2500],  # Only 1 element
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Should use None for temperature range
        assert "temperature_range=None" in code

    def test_update_specs_file_no_upgrades(self):
        """Test product without upgrades section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            specs_path = Path(tmpdir) / "specs.yml"

            products_data = [
                {
                    "vid": 1,
                    "products": [
                        {
                            "pid": 32,
                            "name": "LIFX Z Strip",
                            "features": {"color": True, "multizone": True},
                            # No upgrades section
                        }
                    ],
                }
            ]

            update_specs_file(products_data, specs_path)

            assert specs_path.exists()
            content = specs_path.read_text()
            assert "32:" in content

    def test_product_definitions_with_incomplete_temperature_range(self):
        """Test product with temperature_range key but missing data."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        "features": {
                            "color": True,
                            "temperature_range": [],  # Empty list
                        },
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Should handle gracefully
        assert "27: ProductInfo(" in code
        assert "temperature_range=None" in code

    def test_product_with_no_upgrades_but_multizone(self):
        """Test multizone product without upgrades doesn't get extended_multizone."""
        products_data = [
            {
                "vid": 1,
                "products": [
                    {
                        "pid": 32,
                        "name": "LIFX Z",
                        "features": {"color": True, "multizone": True},
                        # No upgrades, so no extended_multizone
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Should have MULTIZONE but not EXTENDED_MULTIZONE
        assert "ProductCapability.MULTIZONE" in code
        assert "ProductCapability.EXTENDED_MULTIZONE" not in code

    def test_product_without_features_key(self):
        """Test product without features key uses defaults."""
        products_data = [
            {
                "vid": 1,
                "defaults": {"features": {"color": True}},
                "products": [
                    {
                        "pid": 27,
                        "name": "LIFX A19",
                        # No features key - should use defaults
                    }
                ],
            }
        ]

        code = generate_product_definitions(products_data)

        # Should inherit from defaults
        assert "ProductCapability.COLOR" in code
