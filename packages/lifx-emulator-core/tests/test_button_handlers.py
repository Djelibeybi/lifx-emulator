"""Tests for button packet handlers."""

from lifx_emulator.factories import create_device
from lifx_emulator.handlers.button_handlers import (
    GetConfigHandler,
    GetHandler,
    SetConfigHandler,
    SetHandler,
)
from lifx_emulator.protocol.packets import Button
from lifx_emulator.protocol.protocol_types import ButtonBacklightHsbk


def test_get_config_returns_state_config_for_button_device():
    dev = create_device(219)  # Luna — has buttons
    out = GetConfigHandler().handle(dev.state, Button.GetConfig(), True)
    assert len(out) == 1 and isinstance(out[0], Button.StateConfig)


def test_set_config_updates_state_and_echoes():
    dev = create_device(219)
    pkt = Button.SetConfig(
        haptic_duration_ms=80,
        backlight_on_color=ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=65535, kelvin=3500
        ),
        backlight_off_color=ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=0, kelvin=3500
        ),
    )
    out = SetConfigHandler().handle(dev.state, pkt, True)
    assert dev.state.buttons_state.haptic_duration_ms == 80
    assert isinstance(out[0], Button.StateConfig) and out[0].haptic_duration_ms == 80


def test_non_button_device_returns_empty():
    dev = create_device(22)  # plain bulb
    assert GetConfigHandler().handle(dev.state, Button.GetConfig(), True) == []
    assert SetConfigHandler().handle(dev.state, Button.GetConfig(), True) == []
    assert GetHandler().handle(dev.state, Button.Get(), True) == []
    assert (
        SetHandler().handle(
            dev.state, Button.Set(index=0, buttons_count=0, buttons=[]), True
        )
        == []
    )


def test_get_returns_state_with_padded_eight_button_array():
    dev = create_device(219)
    out = GetHandler().handle(dev.state, Button.Get(), True)
    assert len(out) == 1
    state = out[0]
    assert isinstance(state, Button.State)
    assert len(state.buttons) == 8
    for button in state.buttons:
        assert len(button.actions) == 5


def test_button_state_round_trips_through_pack_unpack():
    dev = create_device(219)
    state = GetHandler().handle(dev.state, Button.Get(), True)[0]

    packed = state.pack()
    unpacked = Button.State.unpack(packed)

    assert len(unpacked.buttons) == 8
    assert unpacked.count == state.count
    assert unpacked.buttons_count == state.buttons_count
    # Round trip must consume exactly the bytes that were packed.
    assert unpacked.pack() == packed


def test_set_returns_state_without_error():
    dev = create_device(219)
    pkt = Button.Set(index=0, buttons_count=0, buttons=[])
    out = SetHandler().handle(dev.state, pkt, True)
    assert len(out) == 1 and isinstance(out[0], Button.State)


def test_set_suppresses_response_when_res_required_false():
    dev = create_device(219)
    pkt = Button.Set(index=0, buttons_count=0, buttons=[])
    out = SetHandler().handle(dev.state, pkt, False)
    assert out == []


def test_set_config_suppresses_response_but_still_persists_when_res_required_false():
    dev = create_device(219)
    pkt = Button.SetConfig(
        haptic_duration_ms=80,
        backlight_on_color=ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=65535, kelvin=3500
        ),
        backlight_off_color=ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=0, kelvin=3500
        ),
    )
    out = SetConfigHandler().handle(dev.state, pkt, False)
    assert out == []
    # Mutation happens regardless of whether a response was requested.
    assert dev.state.buttons_state.haptic_duration_ms == 80
    assert dev.state.buttons_state.backlight_on.brightness == 65535
