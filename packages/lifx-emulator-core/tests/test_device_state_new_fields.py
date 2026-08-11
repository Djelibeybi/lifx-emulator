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


def test_downlight_zone_count_requires_a_real_matrix():
    """has_matrix alone is not enough: without a MatrixState, tile_width and
    tile_height resolve through the 8x8 fallback defaults and would report a
    zone count belonging to no real device.
    """
    from lifx_emulator.factories.builder import DeviceBuilder
    from lifx_emulator.products.registry import get_product

    st = DeviceBuilder(get_product(267)).with_tile_count(0).build().state

    assert st.has_matrix is True
    assert st.matrix is None
    assert st.downlight_zone_count is None


def test_long_product_names_keep_the_serial_suffix_within_32_bytes():
    """Device.StateLabel packs 32 bytes; the serial suffix is what makes two
    devices of the same product distinguishable, so the name gives way first.
    """
    first = create_device(211, serial="d073d5000001")  # 34-character name
    second = create_device(211, serial="d073d50000ff")

    for dev in (first, second):
        assert len(dev.state.label.encode()) <= 32
    assert first.state.label.endswith("000001")
    assert second.state.label.endswith("0000ff")
    assert first.state.label != second.state.label
