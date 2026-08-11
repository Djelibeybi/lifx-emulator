"""Round-trip tests for newly-enabled Sensor and Button protocol packets."""

from lifx_emulator.protocol.packets import Button, Sensor
from lifx_emulator.protocol.protocol_types import (
    Button as ButtonStruct,
)
from lifx_emulator.protocol.protocol_types import (
    ButtonAction,
    ButtonBacklightHsbk,
    ButtonGesture,
    ButtonTarget,
    ButtonTargetType,
)


def _sample_action() -> ButtonAction:
    return ButtonAction(
        gesture=ButtonGesture.PRESS,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x00" * 16),
    )


def _sample_button() -> ButtonStruct:
    return ButtonStruct(
        actions_count=0,
        actions=[_sample_action() for _ in range(5)],
    )


def test_two_byte_enum_fields_pack_at_declared_width():
    """ButtonGesture/ButtonTargetType are size_bytes=2, so ButtonAction is 20 bytes.

    Regression guard for the generator hardcoding uint8 for every enum field:
    with the correct per-field widths a ButtonAction packs to 20 bytes (2 + 2 +
    16), the Button struct to 101, and Button.State's Buttons field to 808 (8 x
    101) for a total 811-byte payload.
    """
    action = _sample_action()
    assert len(action.pack()) == 20

    button = _sample_button()
    assert len(button.pack()) == 101

    # Round-trip the Button struct to prove pack/unpack agree at the new width.
    restored, offset = ButtonStruct.unpack(button.pack())
    assert offset == 101
    assert len(restored.actions) == 5

    state = Button.State(
        count=8,
        index=0,
        buttons_count=8,
        buttons=[_sample_button() for _ in range(8)],
    )
    payload = state.pack()
    assert len(payload) == 811
    # Buttons field is the payload minus count/index/buttons_count (3 x uint8).
    assert len(payload) - 3 == 808


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
