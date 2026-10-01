from lifx_emulator.constants import max_tile_count
from lifx_emulator.products.registry import get_registry
from lifx_emulator.products.specs import (
    SpecsRegistry,
    get_specs,
    get_uplight_zone_count,
    get_zone_map,
)


def test_specs_yaml_loads_and_new_matrix_dims_correct():
    reg = SpecsRegistry()  # loads specs.yml on init
    assert reg.get_tile_dimensions(267) == (4, 13)  # Mirror US
    assert reg.get_tile_dimensions(268) == (4, 13)  # Mirror Intl
    assert reg.get_tile_dimensions(229) == (3, 2)  # new Path Intl
    assert reg.get_tile_dimensions(172) == (3, 1)  # new Spot
    assert reg.get_tile_dimensions(265) == (8, 8)  # Ceiling 13"


def test_uplight_zone_count():
    assert get_uplight_zone_count(176) == 1  # Ceiling 8x8
    assert get_uplight_zone_count(201) == 1  # Ceiling 16x8
    assert get_uplight_zone_count(265) == 1  # Ceiling 13"
    assert get_uplight_zone_count(267) == 25  # Mirror rear
    assert get_uplight_zone_count(55) is None  # plain Tile — no uplight


def _matrix_products():
    """Every matrix product in the registry, keyed by product ID.

    The registry is generated and exposes no iterator, so this reads its
    product table the way the CLI's list-products command does.
    """
    products = get_registry()._products.values()
    return {p.pid: p for p in products if p.has_matrix}


def test_specs_tile_limits_agree_with_the_chain_rule():
    """The emulator enforces "1 tile unless the product chains, then 1 to 5"
    from has_chain; specs.yml repeats the limit per product, so a hand edit
    there must not quietly disagree with the rule actually enforced."""
    for pid, product in _matrix_products().items():
        specs = get_specs(pid)
        assert specs is not None, pid
        assert specs.max_tile_count == max_tile_count(product.has_chain), pid
        assert specs.min_tile_count == 1, pid


def test_only_single_tile_products_carry_a_zone_map():
    """Restore keeps a non-chain product at its own size, which is what lets
    the builder apply a zone map unconditionally; a chain could be restored
    at another size and read its zones from the wrong positions."""
    for pid, product in _matrix_products().items():
        if get_zone_map(pid) is not None:
            assert not product.has_chain, pid
