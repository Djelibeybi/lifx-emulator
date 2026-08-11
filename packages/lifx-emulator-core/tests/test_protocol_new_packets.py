"""Round-trip tests for newly-enabled Sensor and Button protocol packets."""

from lifx_emulator.protocol.packets import Button, Sensor
from lifx_emulator.protocol.protocol_types import ButtonBacklightHsbk


def test_sensor_ambient_light_roundtrip():
    s = Sensor.StateAmbientLight(lux=123.5)
    assert Sensor.StateAmbientLight.unpack(s.pack()).lux == 123.5
    assert Sensor.GetAmbientLight.PKT_TYPE == 401
    assert Sensor.StateAmbientLight.PKT_TYPE == 402


def test_button_config_roundtrip():
    on_color = ButtonBacklightHsbk(hue=0, saturation=0, brightness=65535, kelvin=3500)
    off_color = ButtonBacklightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
    cfg = Button.StateConfig(
        haptic_duration_ms=65,
        backlight_on_color=on_color,
        backlight_off_color=off_color,
    )
    rt = Button.StateConfig.unpack(cfg.pack())
    assert rt.haptic_duration_ms == 65
    assert Button.State.PKT_TYPE == 907
    assert Button.StateConfig.PKT_TYPE == 911
