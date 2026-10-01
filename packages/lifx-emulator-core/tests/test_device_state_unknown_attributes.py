"""Tests that DeviceState rejects writes to attributes it does not know about."""

import pytest
from lifx_emulator.factories import create_color_light, create_device


def test_unknown_attribute_assignment_raises():
    """A typo such as ``power`` for ``power_level`` must not silently create a
    stray attribute while the device's real state stays unchanged.
    """
    state = create_color_light().state
    state.power_level = 0

    with pytest.raises(AttributeError, match="power"):
        state.power = 65535

    assert "power" not in vars(state)
    assert state.power_level == 0


def test_unknown_attribute_error_suggests_close_match():
    state = create_color_light().state

    with pytest.raises(AttributeError, match="did you mean 'power_level'"):
        state.power = 65535

    with pytest.raises(AttributeError, match="did you mean 'product'"):
        state.product_id = 27


def test_unknown_attribute_error_without_close_match():
    state = create_color_light().state

    with pytest.raises(AttributeError) as excinfo:
        state.xyzzy = 1

    assert "did you mean" not in str(excinfo.value)


def test_routed_dataclass_and_private_attributes_remain_writable():
    state = create_device(32).state  # LIFX Z, multizone

    state.power_level = 65535
    state.zone_count = 16
    state.has_color = False
    state.ambient_light_lux = 12.5
    state._scratch = "private"

    assert state.core.power_level == 65535
    assert state.multizone.zone_count == 16
    assert state.has_color is False
    assert state.ambient_light_lux == 12.5
    assert state._scratch == "private"


def test_routed_write_to_absent_optional_state_is_still_ignored():
    state = create_color_light().state  # no multizone sub-state

    state.zone_count = 16

    assert state.zone_count == 0
