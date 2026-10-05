"""Tests for the firmware_version scenario override."""

from unittest.mock import Mock

import pytest
from lifx_emulator.constants import LIFX_HEADER_SIZE
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator.server import EmulatedLifxServer
from pydantic import ValidationError

SERIAL = "d073d5000001"


def _host_firmware(device):
    header = LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=Device.GetHostFirmware.PKT_TYPE,
        res_required=True,
    )
    responses = device.process_packet(header, Device.GetHostFirmware())
    states = [
        packet
        for resp_header, packet in responses
        if resp_header.pkt_type == Device.StateHostFirmware.PKT_TYPE
    ]
    assert len(states) == 1
    return states[0]


def _device_with_scenario(config: ScenarioConfig):
    manager = HierarchicalScenarioManager()
    manager.set_device_scenario(SERIAL, config)
    device = create_color_light(
        SERIAL, firmware_version=(3, 70), scenario_manager=manager
    )
    return device, manager


class TestFirmwareVersionScenario:
    """StateHostFirmware reports the scenario's firmware version."""

    def test_reports_real_version_without_override(self):
        device, _ = _device_with_scenario(ScenarioConfig())

        state = _host_firmware(device)

        assert (state.version_major, state.version_minor) == (3, 70)

    def test_override_replaces_reported_version(self):
        device, _ = _device_with_scenario(ScenarioConfig(firmware_version=(2, 60)))

        state = _host_firmware(device)

        assert (state.version_major, state.version_minor) == (2, 60)

    def test_override_keeps_build_timestamp(self):
        device, _ = _device_with_scenario(ScenarioConfig(firmware_version=(2, 60)))

        state = _host_firmware(device)

        assert state.build == device.state.build_timestamp

    def test_override_does_not_change_device_state(self):
        device, _ = _device_with_scenario(ScenarioConfig(firmware_version=(2, 60)))

        _host_firmware(device)

        assert (device.state.version_major, device.state.version_minor) == (3, 70)

    def test_override_applies_at_global_scope(self):
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(firmware_version=(2, 77)))
        device = create_color_light(SERIAL, scenario_manager=manager)

        state = _host_firmware(device)

        assert (state.version_major, state.version_minor) == (2, 77)

    def test_runtime_change_takes_effect_after_cache_invalidation(self):
        device, manager = _device_with_scenario(ScenarioConfig())
        assert _host_firmware(device).version_major == 3

        manager.set_device_scenario(SERIAL, ScenarioConfig(firmware_version=(2, 60)))
        device.invalidate_scenario_cache()

        state = _host_firmware(device)
        assert (state.version_major, state.version_minor) == (2, 60)

    def test_override_does_not_affect_other_replies(self):
        device, _ = _device_with_scenario(ScenarioConfig(firmware_version=(2, 60)))
        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetLabel.PKT_TYPE,
            res_required=True,
        )

        responses = device.process_packet(header, Device.GetLabel())

        assert [h.pkt_type for h, _ in responses] == [Device.StateLabel.PKT_TYPE]
        assert responses[0][1].label == device.state.label


class TestFirmwareVersionValidation:
    """Both components must fit the uint16 fields of StateHostFirmware."""

    @pytest.mark.parametrize("version", [(0, 0), (65535, 65535)])
    def test_accepts_uint16_boundaries(self, version):
        device, _ = _device_with_scenario(ScenarioConfig(firmware_version=version))

        state = _host_firmware(device)

        assert (state.version_major, state.version_minor) == version

    @pytest.mark.parametrize("version", [(-1, 60), (2, -1), (65536, 60), (2, 65536)])
    def test_rejects_out_of_range_components(self, version):
        with pytest.raises(ValidationError):
            ScenarioConfig(firmware_version=version)

    def test_rejects_out_of_range_from_dict(self):
        with pytest.raises(ValidationError):
            ScenarioConfig.from_dict({"firmware_version": [65536, 60]})


class TestFirmwareVersionScenarioOnTheWire:
    """The override reaches the client through EmulatedLifxServer."""

    async def test_server_sends_overridden_version(self):
        manager = HierarchicalScenarioManager()
        manager.set_device_scenario(SERIAL, ScenarioConfig(firmware_version=(2, 60)))
        device = create_color_light(
            SERIAL, firmware_version=(3, 70), scenario_manager=manager
        )
        server = EmulatedLifxServer(
            [device],
            DeviceManager(DeviceRepository()),
            "127.0.0.1",
            56700,
            scenario_manager=manager,
        )
        server.transport = Mock()
        header = LifxHeader(
            size=LIFX_HEADER_SIZE,
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetHostFirmware.PKT_TYPE,
            res_required=True,
        )

        await server.handle_packet(header.pack(), ("127.0.0.1", 56700))

        sent = [call.args[0] for call in server.transport.sendto.call_args_list]
        replies = [
            data
            for data in sent
            if LifxHeader.unpack(data).pkt_type == Device.StateHostFirmware.PKT_TYPE
        ]
        assert len(replies) == 1
        state = Device.StateHostFirmware.unpack(replies[0][LIFX_HEADER_SIZE:])
        assert (state.version_major, state.version_minor) == (2, 60)
