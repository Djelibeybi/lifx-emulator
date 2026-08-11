"""Sensor packet handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Sensor

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState


class GetAmbientLightHandler(PacketHandler):
    """Handle SensorGetAmbientLight (401) -> SensorStateAmbientLight (402).

    Always responds — devices without a sensor report lux 0.0.
    """

    PKT_TYPE = Sensor.GetAmbientLight.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Sensor.StateAmbientLight(lux=device_state.ambient_light_lux)]


ALL_SENSOR_HANDLERS: list[PacketHandler] = [GetAmbientLightHandler()]
