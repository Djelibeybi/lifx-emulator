"""Tests for ambient-light, button and uplight state wiring (upstream sync)."""

from lifx_emulator.factories import create_device


def test_mirror_state_has_buttons_sensor_uplight():
    dev = create_device(267)  # Mirror
    st = dev.state
    assert st.has_buttons
    assert st.ambient_light_lux == 100.0  # seeded (buttons + matrix)
    assert st.uplight_zone_count == 25
    assert st.has_uplight is True
    assert st.downlight_zone_count == 25  # 50 total - 25


def test_plain_bulb_reports_zero_lux():
    dev = create_device(22)  # LIFX Color 1000 A19-class bulb, no sensor
    st = dev.state
    assert st.ambient_light_lux == 0.0
    assert st.uplight_zone_count is None
    assert st.has_uplight is False
    assert st.downlight_zone_count is None  # no uplight -> no downlight split
