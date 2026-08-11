from lifx_emulator.products.specs import SpecsRegistry


def test_specs_yaml_loads_and_new_matrix_dims_correct():
    reg = SpecsRegistry()  # loads specs.yml on init
    assert reg.get_tile_dimensions(267) == (5, 10)  # Mirror US
    assert reg.get_tile_dimensions(268) == (5, 10)  # Mirror Intl
    assert reg.get_tile_dimensions(229) == (3, 2)  # new Path Intl
    assert reg.get_tile_dimensions(172) == (3, 1)  # new Spot
    assert reg.get_tile_dimensions(265) == (8, 8)  # Ceiling 13"
