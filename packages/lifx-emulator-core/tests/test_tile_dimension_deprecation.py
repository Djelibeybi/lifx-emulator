"""Tests for the deprecated tile_width/tile_height library options.

Every matrix product has a fixed tile size from specs.yml, so the options are
still accepted but ignored, and each use raises a DeprecationWarning.
"""

import warnings

import pytest
from lifx_emulator.factories import create_device, create_tile_device
from lifx_emulator.factories.builder import DeviceBuilder
from lifx_emulator.products.registry import get_product


def _tile_size(device) -> tuple[int, int]:
    return (device.state.tile_width, device.state.tile_height)


@pytest.mark.parametrize(
    ("kwargs"),
    [
        {"tile_width": 16, "tile_height": 8},
        {"tile_width": 16},
        {"tile_height": 16},
    ],
)
def test_create_device_warns_and_ignores_tile_dimensions(kwargs):
    with pytest.warns(DeprecationWarning, match="tile_width and tile_height"):
        device = create_device(55, **kwargs)
    assert _tile_size(device) == (8, 8)


def test_create_tile_device_warns_and_ignores_tile_dimensions():
    with pytest.warns(DeprecationWarning, match="tile_width and tile_height"):
        device = create_tile_device(tile_count=1, tile_width=16, tile_height=8)
    assert _tile_size(device) == (8, 8)


def test_create_tile_device_warning_points_at_the_caller():
    with pytest.warns(DeprecationWarning) as record:
        create_tile_device(tile_width=16, tile_height=8)
    assert len(record) == 1
    assert record[0].filename == __file__


def test_create_device_warning_points_at_the_caller():
    with pytest.warns(DeprecationWarning) as record:
        create_device(201, tile_width=8, tile_height=8)
    assert len(record) == 1
    assert record[0].filename == __file__


def test_builder_with_tile_dimensions_warns_and_is_ignored():
    builder = DeviceBuilder(get_product(201))
    with pytest.warns(DeprecationWarning, match="with_tile_dimensions"):
        returned = builder.with_tile_dimensions(8, 8)
    assert returned is builder
    assert _tile_size(builder.build()) == (16, 8)


def test_no_warning_without_tile_dimensions():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        create_device(55)
        create_tile_device(tile_count=2)
