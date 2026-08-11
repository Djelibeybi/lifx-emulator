"""Tests for sensor packet handlers."""

from lifx_emulator.factories import create_device
from lifx_emulator.handlers.sensor_handlers import GetAmbientLightHandler
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
