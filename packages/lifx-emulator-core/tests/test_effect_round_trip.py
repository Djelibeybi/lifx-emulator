"""Tests that SetEffect settings survive a GetEffect round trip and a restart."""

import pytest
from lifx_emulator.devices.state_restorer import StateRestorer
from lifx_emulator.devices.state_serializer import (
    deserialize_device_state,
    serialize_device_state,
)
from lifx_emulator.factories import create_multizone_light, create_tile_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import MultiZone, Tile
from lifx_emulator.protocol.protocol_types import (
    LightHsbk,
    MultiZoneEffectParameter,
    MultiZoneEffectSettings,
    MultiZoneEffectType,
    TileEffectParameter,
    TileEffectSettings,
    TileEffectSkyType,
    TileEffectType,
)

# lifx-async Direction: MOVE effect parameter1 is REVERSED = 0, FORWARD = 1
DIRECTION_REVERSED = 0
DIRECTION_FORWARD = 1

# Effect durations are uint64 nanoseconds on the wire
TEN_SECONDS_NS = 10_000_000_000

ACKNOWLEDGEMENT = 45


class MockStorage:
    """Storage stub that returns a fixed saved state per serial."""

    def __init__(self, states: dict):
        self.states = states

    def load_device_state(self, serial: str):
        return self.states.get(serial)


def _send(device, packet, pkt_type: int, res_required: bool = False):
    """Send a packet to a device and return the reply payloads, wire-decoded."""
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=pkt_type,
        res_required=res_required,
    )
    responses = device.process_packet(header, packet)
    # Pack and unpack each reply so the assertions see what a client would
    return [
        type(reply).unpack(reply.pack())
        for reply_header, reply in responses
        if reply_header.pkt_type != ACKNOWLEDGEMENT
    ]


def _move_settings(
    direction: int, speed_ms: int, duration_ns: int = 0, instanceid: int = 1
) -> MultiZoneEffectSettings:
    return MultiZoneEffectSettings(
        instanceid=instanceid,
        type=MultiZoneEffectType.MOVE,
        speed=speed_ms,
        duration=duration_ns,
        parameter=MultiZoneEffectParameter(
            parameter0=0,
            parameter1=direction,
            parameter2=0,
            parameter3=0,
            parameter4=0,
            parameter5=0,
            parameter6=0,
            parameter7=0,
        ),
    )


def _get_multizone_effect(device) -> MultiZoneEffectSettings:
    (reply,) = _send(device, MultiZone.GetEffect(), 507, res_required=True)
    return reply.settings


def _get_tile_effect(device) -> TileEffectSettings:
    (reply,) = _send(device, Tile.GetEffect(), 718, res_required=True)
    return reply.settings


def _morph_settings(speed_ms: int, duration_ns: int) -> TileEffectSettings:
    palette = [
        LightHsbk(hue=i * 4096, saturation=65535, brightness=65535, kelvin=3500)
        for i in range(16)
    ]
    return TileEffectSettings(
        instanceid=42,
        type=TileEffectType.MORPH,
        speed=speed_ms,
        duration=duration_ns,
        parameter=TileEffectParameter(
            sky_type=TileEffectSkyType.SUNRISE,
            cloud_saturation_min=0,
            cloud_saturation_max=0,
        ),
        palette_count=3,
        palette=palette,
    )


class TestMultiZoneEffectRoundTrip:
    """SetEffect (508) followed by GetEffect (507) returns what was set."""

    def test_speed_keeps_milliseconds(self, multizone_device):
        _send(
            multizone_device, MultiZone.SetEffect(settings=_move_settings(1, 1250)), 508
        )

        assert _get_multizone_effect(multizone_device).speed == 1250

    @pytest.mark.parametrize("direction", [DIRECTION_FORWARD, DIRECTION_REVERSED])
    def test_move_direction(self, multizone_device, direction):
        settings = _move_settings(direction, 1250)
        _send(multizone_device, MultiZone.SetEffect(settings=settings), 508)

        assert _get_multizone_effect(multizone_device).parameter.parameter1 == direction

    def test_duration_instanceid_and_all_parameters(self, multizone_device):
        settings = _move_settings(DIRECTION_FORWARD, 1250, TEN_SECONDS_NS, 7)
        settings.parameter = MultiZoneEffectParameter(1, 2, 3, 4, 5, 6, 7, 8)
        _send(multizone_device, MultiZone.SetEffect(settings=settings), 508)

        result = _get_multizone_effect(multizone_device)

        assert result.type == MultiZoneEffectType.MOVE
        assert result.duration == TEN_SECONDS_NS
        assert result.instanceid == 7
        assert result.parameter == MultiZoneEffectParameter(1, 2, 3, 4, 5, 6, 7, 8)

    def test_set_effect_reply_echoes_settings(self, multizone_device):
        settings = _move_settings(DIRECTION_FORWARD, 1250, TEN_SECONDS_NS)

        (reply,) = _send(
            multizone_device, MultiZone.SetEffect(settings=settings), 508, True
        )

        assert reply.settings.speed == 1250
        assert reply.settings.duration == TEN_SECONDS_NS
        assert reply.settings.parameter.parameter1 == DIRECTION_FORWARD

    def test_default_effect_is_off(self, multizone_device):
        result = _get_multizone_effect(multizone_device)

        assert result.type == MultiZoneEffectType.OFF
        assert result.speed == 5000
        assert result.duration == 0
        assert result.parameter == MultiZoneEffectParameter(0, 0, 0, 0, 0, 0, 0, 0)


class TestTileEffectRoundTrip:
    """SetEffect (719) followed by GetEffect (718) returns what was set."""

    def test_speed_duration_and_instanceid(self, single_tile_device):
        settings = _morph_settings(1250, TEN_SECONDS_NS)
        _send(single_tile_device, Tile.SetEffect(settings=settings), 719)

        result = _get_tile_effect(single_tile_device)

        assert result.type == TileEffectType.MORPH
        assert result.speed == 1250
        assert result.duration == TEN_SECONDS_NS
        assert result.instanceid == 42
        assert result.palette_count == 3


class TestEffectPersistence:
    """Effect settings survive a save and restore."""

    def _restore(self, fresh_device, saved_state):
        storage = MockStorage({fresh_device.state.serial: saved_state})
        return StateRestorer(storage).restore_if_available(fresh_device.state)

    def test_multizone_effect_round_trips_through_storage(self):
        device = create_multizone_light("d073d5000001", zone_count=16)
        settings = _move_settings(DIRECTION_FORWARD, 1250, TEN_SECONDS_NS, 9)
        _send(device, MultiZone.SetEffect(settings=settings), 508)

        saved = deserialize_device_state(serialize_device_state(device.state))
        fresh = create_multizone_light("d073d5000001", zone_count=16)
        restored = self._restore(fresh, saved)

        assert restored.multizone_effect_type == int(MultiZoneEffectType.MOVE)
        assert restored.multizone_effect_speed_ms == 1250
        assert restored.multizone_effect_duration == TEN_SECONDS_NS
        assert restored.multizone_effect_instanceid == 9
        assert restored.multizone_effect_parameters[1] == DIRECTION_FORWARD

    def test_multizone_legacy_speed_in_seconds_is_upgraded(self):
        device = create_multizone_light("d073d5000001", zone_count=16)
        saved = {
            "product": device.state.product,
            "multizone_effect_type": int(MultiZoneEffectType.MOVE),
            "multizone_effect_speed": 3,
        }

        restored = self._restore(device, saved)

        assert restored.multizone_effect_speed_ms == 3000
        assert restored.multizone_effect_parameters == [0] * 8

    def test_multizone_malformed_parameters_are_ignored(self):
        device = create_multizone_light("d073d5000001", zone_count=16)
        saved = {
            "product": device.state.product,
            "multizone_effect_parameters": [1, 2, 3],
        }

        restored = self._restore(device, saved)

        assert restored.multizone_effect_parameters == [0] * 8

    def test_tile_effect_round_trips_through_storage(self):
        device = create_tile_device("d073d5000002", tile_count=1)
        _send(
            device, Tile.SetEffect(settings=_morph_settings(1250, TEN_SECONDS_NS)), 719
        )
        device.state.tile_effect_sky_type = int(TileEffectSkyType.SUNSET)
        device.state.tile_effect_cloud_sat_min = 60
        device.state.tile_effect_cloud_sat_max = 170

        saved = deserialize_device_state(serialize_device_state(device.state))
        fresh = create_tile_device("d073d5000002", tile_count=1)
        restored = self._restore(fresh, saved)

        assert restored.tile_effect_type == int(TileEffectType.MORPH)
        assert restored.tile_effect_speed_ms == 1250
        assert restored.tile_effect_duration == TEN_SECONDS_NS
        assert restored.tile_effect_instanceid == 42
        assert restored.tile_effect_sky_type == int(TileEffectSkyType.SUNSET)
        assert restored.tile_effect_cloud_sat_min == 60
        assert restored.tile_effect_cloud_sat_max == 170

    def test_tile_legacy_speed_in_seconds_is_upgraded(self):
        device = create_tile_device("d073d5000002", tile_count=1)
        saved = {"product": device.state.product, "tile_effect_speed": 4}

        restored = self._restore(device, saved)

        assert restored.tile_effect_speed_ms == 4000
