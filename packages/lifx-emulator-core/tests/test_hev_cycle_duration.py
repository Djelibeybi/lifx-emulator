"""Tests that a one-off HEV cycle keeps its length apart from the configured one."""

from lifx_emulator.devices.state_restorer import StateRestorer
from lifx_emulator.devices.state_serializer import (
    deserialize_device_state,
    serialize_device_state,
)
from lifx_emulator.factories import create_hev_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light

ACKNOWLEDGEMENT = 45
CONFIGURED_S = 7200


class MockStorage:
    """Storage stub that returns a fixed saved state per serial."""

    def __init__(self, states: dict):
        self.states = states

    def load_device_state(self, serial: str):
        return self.states.get(serial)


def _send(device, packet, res_required: bool = False):
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=packet.PKT_TYPE,
        res_required=res_required,
    )
    return [
        type(reply).unpack(reply.pack())
        for reply_header, reply in device.process_packet(header, packet)
        if reply_header.pkt_type != ACKNOWLEDGEMENT
    ]


def _cycle(device) -> Light.StateHevCycle:
    (reply,) = _send(device, Light.GetHevCycle(), res_required=True)
    return reply


def _configured_duration(device) -> int:
    (reply,) = _send(device, Light.GetHevCycleConfiguration(), res_required=True)
    return reply.duration_s


def test_one_off_cycle_does_not_change_the_configured_duration(hev_device):
    _send(hev_device, Light.SetHevCycle(enable=True, duration_s=600))

    assert _configured_duration(hev_device) == CONFIGURED_S
    assert _cycle(hev_device).duration_s == 600
    assert _cycle(hev_device).remaining_s == 600


def test_zero_duration_runs_for_the_configured_duration(hev_device):
    _send(hev_device, Light.SetHevCycleConfiguration(indication=True, duration_s=1800))

    _send(hev_device, Light.SetHevCycle(enable=True, duration_s=0))

    assert _cycle(hev_device).duration_s == 1800
    assert _cycle(hev_device).remaining_s == 1800


def test_idle_device_reports_the_configured_duration(hev_device):
    assert _cycle(hev_device).duration_s == CONFIGURED_S
    assert _cycle(hev_device).remaining_s == 0


def test_stopping_a_cycle_keeps_its_duration(hev_device):
    _send(hev_device, Light.SetHevCycle(enable=True, duration_s=600))

    _send(hev_device, Light.SetHevCycle(enable=False, duration_s=0))

    assert _cycle(hev_device).duration_s == 600
    assert _cycle(hev_device).remaining_s == 0
    assert _configured_duration(hev_device) == CONFIGURED_S


def test_current_cycle_duration_survives_a_restart():
    device = create_hev_light("d073d5000001")
    _send(device, Light.SetHevCycle(enable=True, duration_s=600))
    saved = deserialize_device_state(serialize_device_state(device.state))

    fresh = create_hev_light("d073d5000001")
    storage = MockStorage({fresh.state.serial: saved})
    restored = StateRestorer(storage).restore_if_available(fresh.state)

    assert restored.hev_cycle_current_duration_s == 600
    assert restored.hev_cycle_duration_s == CONFIGURED_S
