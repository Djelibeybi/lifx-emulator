"""Button packet handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Button
from lifx_emulator.protocol.protocol_types import Button as ButtonStruct
from lifx_emulator.protocol.protocol_types import (
    ButtonAction,
    ButtonGesture,
    ButtonTarget,
    ButtonTargetType,
)

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState
    from lifx_emulator.devices.states import ButtonsState

# Button.State/Set pack a fixed [8]<Button> array on the wire, and each Button
# struct always unpacks exactly 5 ButtonAction entries (see
# protocol_types.Button.unpack). Any padding struct we synthesise must match
# that shape exactly, or a round trip through pack()/unpack() misaligns every
# subsequent button in the array.
_BUTTONS_ARRAY_LENGTH = 8
_ACTIONS_PER_BUTTON = 5


def _default_button_action() -> ButtonAction:
    """A neutral, valid ButtonAction used to fill unused action slots."""
    return ButtonAction(
        gesture=ButtonGesture.PRESS,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x00" * 16),
    )


def _default_button() -> ButtonStruct:
    """A neutral Button struct with exactly 5 action slots (wire-format shape)."""
    return ButtonStruct(
        actions_count=0,
        actions=[_default_button_action() for _ in range(_ACTIONS_PER_BUTTON)],
    )


def _padded_buttons(buttons_state: ButtonsState) -> list[ButtonStruct]:
    """Pad/truncate configured buttons to the fixed 8-entry wire array."""
    buttons = list(buttons_state.buttons)[:_BUTTONS_ARRAY_LENGTH]
    while len(buttons) < _BUTTONS_ARRAY_LENGTH:
        buttons.append(_default_button())
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
    configured_count = len(bs.buttons)
    return Button.State(
        count=configured_count,
        index=0,
        buttons_count=configured_count,
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


class SetHandler(PacketHandler):
    """ButtonSet (906) -> ButtonState (907)."""

    PKT_TYPE = Button.Set.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        if not device_state.has_buttons:
            return []
        if res_required:
            return [_state(device_state)]
        return []


ALL_BUTTON_HANDLERS: list[PacketHandler] = [
    GetHandler(),
    SetHandler(),
    GetConfigHandler(),
    SetConfigHandler(),
]
