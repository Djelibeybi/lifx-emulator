"""Tests for sensor packet handlers."""

from lifx_emulator.factories import create_device, create_switch
from lifx_emulator.handlers.sensor_handlers import GetAmbientLightHandler
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Sensor


def test_ambient_light_returns_state_for_sensor_device():
    """Mirror (267) with ambient light sensor returns StateAmbientLight."""
    dev = create_device(267)  # Mirror — seeded 100.0 lux
    out = GetAmbientLightHandler().handle(dev.state, Sensor.GetAmbientLight(), True)
    assert len(out) == 1 and isinstance(out[0], Sensor.StateAmbientLight)
    assert out[0].lux == 100.0


def test_ambient_light_returns_zero_never_unhandled_for_sensorless():
    """Plain bulb (22) without sensor returns StateAmbientLight with lux 0.0."""
    dev = create_device(22)  # plain bulb, lux 0.0
    out = GetAmbientLightHandler().handle(dev.state, Sensor.GetAmbientLight(), True)
    assert len(out) == 1 and out[0].lux == 0.0


def test_switch_answers_ambient_light_not_unhandled():
    """Switches must answer SensorGetAmbientLight, not swallow it as StateUnhandled.

    Switches route Light/MultiZone/Tile packets to StateUnhandled (223), but the
    Sensor namespace (401/402) must still reach the registered handler.
    """
    switch = create_switch("d073d7000099")

    header = LifxHeader(
        source=12345,
        target=switch.state.get_target_bytes(),
        sequence=9,
        tagged=False,
        pkt_type=Sensor.GetAmbientLight.PKT_TYPE,  # 401
        size=36,
        ack_required=False,
        res_required=True,
    )

    responses = switch.process_packet(header, Sensor.GetAmbientLight())

    assert len(responses) == 1
    resp_header, resp_packet = responses[0]
    assert resp_packet.PKT_TYPE == Sensor.StateAmbientLight.PKT_TYPE
    assert resp_packet.lux == switch.state.ambient_light_lux
