"""Button packet handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lifx_emulator.devices.states import (
    ACTIONS_PER_BUTTON,
    BUTTONS_ARRAY_LENGTH,
    default_button,
    default_button_action,
)
from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Button
from lifx_emulator.protocol.protocol_types import Button as ButtonStruct

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState
    from lifx_emulator.devices.states import ButtonsState


def _normalised_button(button: ButtonStruct) -> ButtonStruct:
    """Return a button whose action list is exactly 5 entries (wire shape).

    ``Button.pack`` emits ``len(self.actions)`` while ``Button.unpack`` always
    reads exactly 5, so any button with a different action count would misalign
    a round trip. Truncate extras / pad with the default action to match.
    """
    actions = list(button.actions)[:ACTIONS_PER_BUTTON]
    actions_count = min(button.actions_count, len(actions), ACTIONS_PER_BUTTON)
    while len(actions) < ACTIONS_PER_BUTTON:
        actions.append(default_button_action())
    return ButtonStruct(actions_count=actions_count, actions=actions)


def _padded_buttons(buttons_state: ButtonsState) -> list[ButtonStruct]:
    """Pad/truncate configured buttons to the fixed 8-entry wire array.

    Each retained button is normalised to exactly 5 actions so the whole array
    round-trips through pack()/unpack() without misalignment.
    """
    buttons = [
        _normalised_button(b)
        for b in list(buttons_state.buttons)[:BUTTONS_ARRAY_LENGTH]
    ]
    while len(buttons) < BUTTONS_ARRAY_LENGTH:
        buttons.append(default_button())
    return buttons


def _state_config(state: DeviceState) -> Button.StateConfig:
    bs = state.buttons_state
    return Button.StateConfig(
        haptic_duration_ms=bs.haptic_duration_ms,
        backlight_on_color=bs.backlight_on,
        backlight_off_color=bs.backlight_off,
    )


def _state(state: DeviceState) -> Button.State:
    bs = state.buttons_state
    # Only the first 8 configured buttons fit the fixed wire array, so the
    # advertised counts must describe what is actually packed -- a client that
    # iterates range(buttons_count) over the decoded array must not run off it.
    wire_count = min(len(bs.buttons), BUTTONS_ARRAY_LENGTH)
    return Button.State(
        count=wire_count,
        index=0,
        buttons_count=wire_count,
        buttons=_padded_buttons(bs),
    )


class GetConfigHandler(PacketHandler):
    """ButtonGetConfig (909) -> ButtonStateConfig (911)."""

    PKT_TYPE = Button.GetConfig.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_buttons:
            return []
        return [_state_config(device_state)]


class SetConfigHandler(PacketHandler):
    """ButtonSetConfig (910) -> ButtonStateConfig (911)."""

    PKT_TYPE = Button.SetConfig.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_buttons or packet is None:
            return []
        bs = device_state.buttons_state
        bs.haptic_duration_ms = packet.haptic_duration_ms
        bs.backlight_on = packet.backlight_on_color
        bs.backlight_off = packet.backlight_off_color
        if res_required:
            return [_state_config(device_state)]
        return []


class GetHandler(PacketHandler):
    """ButtonGet (905) -> ButtonState (907)."""

    PKT_TYPE = Button.Get.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_buttons:
            return []
        return [_state(device_state)]


def _apply_set(buttons_state: ButtonsState, packet: Button.Set) -> None:
    """Write the buttons carried by a ButtonSet into device state.

    ``index`` is the first button the request writes and ``buttons_count`` is
    how many of the fixed 8-entry wire array are meaningful; entries beyond
    that are zero padding and must not overwrite existing configuration.
    """
    index = max(0, min(packet.index, BUTTONS_ARRAY_LENGTH))
    supplied = list(packet.buttons)[: max(0, packet.buttons_count)]
    end = min(index + len(supplied), BUTTONS_ARRAY_LENGTH)
    supplied = supplied[: end - index]

    buttons = list(buttons_state.buttons)[:BUTTONS_ARRAY_LENGTH]
    while len(buttons) < end:
        buttons.append(default_button())
    for offset, button in enumerate(supplied):
        buttons[index + offset] = _normalised_button(button)
    buttons_state.buttons = buttons


class SetHandler(PacketHandler):
    """ButtonSet (906) -> ButtonState (907)."""

    PKT_TYPE = Button.Set.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_buttons:
            return []
        if packet is not None:
            _apply_set(device_state.buttons_state, packet)
        if res_required:
            return [_state(device_state)]
        return []


ALL_BUTTON_HANDLERS: list[PacketHandler] = [
    GetHandler(),
    SetHandler(),
    GetConfigHandler(),
    SetConfigHandler(),
]
