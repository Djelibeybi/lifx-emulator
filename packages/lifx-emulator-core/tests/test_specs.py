from lifx_emulator.products.specs import SpecsRegistry, get_uplight_zone_count


def test_specs_yaml_loads_and_new_matrix_dims_correct():
    reg = SpecsRegistry()  # loads specs.yml on init
    assert reg.get_tile_dimensions(267) == (5, 10)  # Mirror US
    assert reg.get_tile_dimensions(268) == (5, 10)  # Mirror Intl
    assert reg.get_tile_dimensions(229) == (3, 2)  # new Path Intl
    assert reg.get_tile_dimensions(172) == (3, 1)  # new Spot
    assert reg.get_tile_dimensions(265) == (8, 8)  # Ceiling 13"


def test_uplight_zone_count():
    assert get_uplight_zone_count(176) == 1  # Ceiling 8x8
    assert get_uplight_zone_count(201) == 1  # Ceiling 16x8
    assert get_uplight_zone_count(265) == 1  # Ceiling 13"
    assert get_uplight_zone_count(267) == 25  # Mirror rear
    assert get_uplight_zone_count(55) is None  # plain Tile — no uplight
