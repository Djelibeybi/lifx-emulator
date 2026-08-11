"""Tests for button packet handlers."""

from lifx_emulator.devices.states import default_button, default_button_action
from lifx_emulator.factories import create_device
from lifx_emulator.handlers.button_handlers import (
    GetConfigHandler,
    GetHandler,
    SetConfigHandler,
    SetHandler,
)
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Button
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


def test_state_normalises_buttons_with_wrong_action_count():
    """A configured button with != 5 actions still yields a round-trippable State.

    Button.unpack always reads 5 actions per button while Button.pack emits
    len(self.actions); a button with the wrong action count would misalign the
    array. The handler must normalise each button to exactly 5 actions.
    """
    dev = create_device(219)
    # Populate with buttons whose action counts are deliberately wrong: one has
    # too few actions, one has too many.
    dev.state.buttons_state.buttons = [
        ButtonStruct(actions_count=1, actions=[default_button_action()]),
        ButtonStruct(
            actions_count=7,
            actions=[default_button_action() for _ in range(7)],
        ),
    ]

    state = GetHandler().handle(dev.state, Button.Get(), True)[0]

    assert isinstance(state, Button.State)
    assert len(state.buttons) == 8
    for button in state.buttons:
        assert len(button.actions) == 5

    packed = state.pack()
    unpacked = Button.State.unpack(packed)
    assert len(unpacked.buttons) == 8
    # Round trip consumes exactly what was packed.
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


def test_non_button_device_returns_state_unhandled_for_button_packets():
    """Button packets are capability-gated in device.py, not swallowed.

    Returning [] from the handler alone would leave a client waiting forever;
    real devices answer StateUnhandled for packet types they do not implement.
    """
    dev = create_device(22)  # plain bulb
    for pkt_type in (905, 906, 909, 910, 911):
        header = LifxHeader(
            source=1,
            target=dev.state.get_target_bytes(),
            sequence=1,
            pkt_type=pkt_type,
            res_required=True,
        )
        responses = dev.process_packet(header, None)
        assert [h.pkt_type for h, _ in responses] == [223]
        assert responses[0][1].unhandled_type == pkt_type


def test_button_device_seeds_its_physical_buttons():
    for product_id, expected in ((219, 4), (267, 4), (89, 2)):
        dev = create_device(product_id)
        assert len(dev.state.buttons_state.buttons) == expected
        state = GetHandler().handle(dev.state, Button.Get(), True)[0]
        assert state.count == expected
        assert state.buttons_count == expected


def test_set_applies_supplied_buttons_to_state():
    dev = create_device(219)
    action = ButtonAction(
        gesture=ButtonGesture.HOLD,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x01" * 16),
    )
    pkt = Button.Set(
        index=1,
        buttons_count=1,
        buttons=[ButtonStruct(actions_count=1, actions=[action])],
    )

    out = SetHandler().handle(dev.state, pkt, True)[0]

    # The written button lands at the requested index and survives a re-read.
    assert out.buttons[1].actions_count == 1
    assert out.buttons[1].actions[0].gesture == ButtonGesture.HOLD
    assert out.buttons[0].actions_count == 0  # untouched
    reread = GetHandler().handle(dev.state, Button.Get(), True)[0]
    assert reread.buttons[1].actions[0].target.data == b"\x01" * 16


def test_set_ignores_padding_beyond_buttons_count():
    dev = create_device(219)
    configured = ButtonAction(
        gesture=ButtonGesture.HOLD,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x07" * 16),
    )
    SetHandler().handle(
        dev.state,
        Button.Set(
            index=0,
            buttons_count=1,
            buttons=[ButtonStruct(actions_count=1, actions=[configured])],
        ),
        False,
    )

    # A later request that only writes button 1 must leave button 0 alone,
    # even though the wire array always carries 8 entries of padding.
    SetHandler().handle(
        dev.state,
        Button.Set(
            index=1,
            buttons_count=1,
            buttons=[ButtonStruct(actions_count=0, actions=[])],
        ),
        False,
    )

    state = GetHandler().handle(dev.state, Button.Get(), True)[0]
    assert state.buttons[0].actions[0].target.data == b"\x07" * 16


def test_state_counts_never_exceed_the_eight_entry_wire_array():
    dev = create_device(219)
    dev.state.buttons_state.buttons = [default_button() for _ in range(10)]

    state = GetHandler().handle(dev.state, Button.Get(), True)[0]

    # count/buttons_count must describe what is packed, or a client iterating
    # range(buttons_count) reads past the end of the decoded array.
    assert state.count == 8
    assert state.buttons_count == 8
    assert len(state.buttons) == 8


def test_normalisation_clamps_actions_count_to_the_actions_packed():
    dev = create_device(219)
    dev.state.buttons_state.buttons = [
        ButtonStruct(
            actions_count=7, actions=[default_button_action() for _ in range(7)]
        )
    ]

    state = GetHandler().handle(dev.state, Button.Get(), True)[0]

    assert state.buttons[0].actions_count == 5
    assert len(state.buttons[0].actions) == 5
    unpacked = Button.State.unpack(state.pack())
    assert unpacked.buttons[0].actions_count == 5


def test_button_set_unpacks_zero_padded_wire_array():
    """Unused button/action slots are zero-filled, and 0 is not a declared
    ButtonGesture -- decoding must tolerate it rather than raise.
    """
    configured = default_button()
    configured.actions_count = 1
    configured.actions[0] = ButtonAction(
        gesture=ButtonGesture.HOLD,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x00" * 16),
    )
    packet = Button.Set(
        index=0,
        buttons_count=1,
        buttons=[configured, *[default_button() for _ in range(7)]],
    )
    packed = packet.pack()

    # The padding buttons carry gesture/target_type 0 in every unused slot.
    unpacked = Button.Set.unpack(packed)
    assert unpacked.buttons_count == 1
    assert unpacked.buttons[0].actions[0].gesture == ButtonGesture.HOLD
    # A fully zero-filled payload must decode rather than raise.
    assert Button.Set.unpack(bytes(len(packed))).buttons_count == 0


def test_set_pads_missing_slots_when_writing_past_the_configured_buttons():
    """Writing button 5 on a 4-button device must pad the gap, not shift it."""
    dev = create_device(219)
    assert len(dev.state.buttons_state.buttons) == 4
    action = ButtonAction(
        gesture=ButtonGesture.HOLD,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x09" * 16),
    )

    state = SetHandler().handle(
        dev.state,
        Button.Set(
            index=5,
            buttons_count=1,
            buttons=[ButtonStruct(actions_count=1, actions=[action])],
        ),
        True,
    )[0]

    assert len(dev.state.buttons_state.buttons) == 6
    assert state.buttons[5].actions[0].target.data == b"\x09" * 16
    # The padded gap carries neutral buttons, not a copy of the written one.
    assert state.buttons[4].actions_count == 0


def test_set_without_payload_leaves_state_untouched():
    """A malformed request that yields no payload must not clear the buttons."""
    dev = create_device(219)
    before = list(dev.state.buttons_state.buttons)

    out = SetHandler().handle(dev.state, None, True)

    assert len(out) == 1 and isinstance(out[0], Button.State)
    assert dev.state.buttons_state.buttons == before
