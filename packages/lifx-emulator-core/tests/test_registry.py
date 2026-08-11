"""Tests guarding the auto-generated product registry against upstream regressions."""

from lifx_emulator.products.registry import PRODUCTS


def test_mirror_and_new_products_present():
    for pid in (267, 268):
        info = PRODUCTS[pid]
        assert info.has_matrix
        assert info.has_buttons
        assert "Mirror" in info.name
    assert 265 in PRODUCTS and 266 in PRODUCTS  # Ceiling 13"
    assert 229 in PRODUCTS  # Path Intl
