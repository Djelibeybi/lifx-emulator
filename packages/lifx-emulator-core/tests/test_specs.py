from pathlib import Path

import yaml
from lifx_emulator.constants import max_tile_count
from lifx_emulator.products.registry import get_product
from lifx_emulator.products.specs import (
    SpecsRegistry,
    get_specs,
    get_uplight_zone_count,
)

SPECS_YML = (
    Path(__file__).parents[1] / "src" / "lifx_emulator" / "products" / "specs.yml"
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


def test_specs_tile_limits_agree_with_the_chain_rule():
    """The emulator enforces "1 tile unless the product chains, then 1 to 5"
    from has_chain; specs.yml repeats the limit per product, so a hand edit
    there must not quietly disagree with the rule actually enforced."""
    pids = yaml.safe_load(SPECS_YML.read_text())["products"]
    checked = 0
    for pid in pids:
        specs = get_specs(int(pid))
        product = get_product(int(pid))
        if specs is None or specs.max_tile_count is None or product is None:
            continue
        assert specs.max_tile_count == max_tile_count(product.has_chain), pid
        assert specs.min_tile_count == 1, pid
        checked += 1
    assert checked > 0
