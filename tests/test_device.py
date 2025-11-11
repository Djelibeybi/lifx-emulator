"""Unit tests for EmulatedLifxDevice and device packet handlers."""

import time

from lifx_emulator.factories import create_color_light, create_infrared_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile
from lifx_emulator.protocol.protocol_types import (
    DeviceService,
    LightHsbk,
    LightWaveform,
)


class TestDeviceState:
    """Test DeviceState dataclass via factory functions."""

    def test_device_state_defaults(self):
        """Test default device state values via factory."""
        device = create_color_light("d073d5000001")
        state = device.state
        assert state.serial == "d073d5000001"
        assert state.power_level == 65535  # Factory defaults to on
        assert state.has_color is True
        assert state.has_infrared is False
        assert state.has_multizone is False
        assert state.has_matrix is False
        assert state.has_hev is False

    def test_device_state_custom_values(self):
        """Test creating device state with infrared capability."""
        device = create_infrared_light("d073d5000099")
        state = device.state
        assert state.serial == "d073d5000099"
        assert state.has_infrared is True
        assert state.infrared_brightness == 16384  # Factory default 25%

    def test_get_target_bytes(self):
        """Test MAC address conversion to target bytes."""
        device = create_color_light("d073d5000001")
        state = device.state
        target = state.get_target_bytes()
        assert len(target) == 8
        assert target == bytes.fromhex("d073d5000001") + b"\x00\x00"

    def test_color_default(self):
        """Test default color HSBK values."""
        device = create_color_light("d073d5000001")
        state = device.state
        # Factory sets a default color
        assert state.color is not None
        assert state.color.kelvin == 3500


class TestEmulatedLifxDevice:
    """Test EmulatedLifxDevice class."""

    def test_device_initialization(self, color_device):
        """Test device initializes correctly."""
        assert color_device.state.serial == "d073d5000001"
        assert color_device.state.has_color is True
        assert color_device.scenario_manager is not None

    def test_device_uptime_increases(self, color_device):
        """Test device uptime calculation."""
        uptime1 = color_device.get_uptime_ns()
        time.sleep(0.01)  # 10ms
        uptime2 = color_device.get_uptime_ns()
        assert uptime2 > uptime1
        # Should be at least 10 million nanoseconds (10ms)
        assert (uptime2 - uptime1) >= 10_000_000


class TestDevicePacketHandlers:
    """Test device packet handling methods."""

    def test_get_service_handler(self, color_device):
        """Test DeviceGetService (2) -> DeviceStateService (3)."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=2,
            res_required=True,
        )
        responses = color_device.process_packet(header, None)

        # Should return StateService response
        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 3
        assert isinstance(resp_packet, Device.StateService)
        assert resp_packet.service == DeviceService.UDP
        assert resp_packet.port == color_device.state.port

    def test_get_label_handler(self, color_device):
        """Test DeviceGetLabel (23) -> DeviceStateLabel (25)."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )
        responses = color_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 25
        assert isinstance(resp_packet, Device.StateLabel)
        assert resp_packet.label == color_device.state.label

    def test_set_label_handler(self, color_device):
        """Test DeviceSetLabel (24) updates device label."""
        new_label = "New Label"
        packet = Device.SetLabel(label=new_label)
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=24,
            res_required=True,
        )

        responses = color_device.process_packet(header, packet)

        assert color_device.state.label == "New Label"
        # Should return StateLabel if res_required
        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 25

    def test_get_power_handler(self, color_device):
        """Test DeviceGetPower (20) -> DeviceStatePower (22)."""
        color_device.state.power_level = 65535
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 22
        assert isinstance(resp_packet, Device.StatePower)
        assert resp_packet.level == 65535

    def test_set_power_handler(self, color_device):
        """Test DeviceSetPower (21) updates power level."""
        packet = Device.SetPower(level=32768)
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,
            res_required=True,
        )

        responses = color_device.process_packet(header, packet)

        assert color_device.state.power_level == 32768
        assert len(responses) >= 1

    def test_get_version_handler(self, color_device):
        """Test DeviceGetVersion (32) -> DeviceStateVersion (33)."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=32,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 33
        assert isinstance(resp_packet, Device.StateVersion)
        assert resp_packet.vendor == color_device.state.vendor
        assert resp_packet.product == color_device.state.product


class TestLightPacketHandlers:
    """Test light-specific packet handlers."""

    def test_light_get_handler(self, color_device):
        """Test LightGet (101) -> LightState (107)."""
        color_device.state.color = LightHsbk(
            hue=21845, saturation=65535, brightness=32768, kelvin=3500
        )
        color_device.state.power_level = 65535

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=101,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 107
        assert isinstance(resp_packet, Light.StateColor)
        assert resp_packet.color.hue == 21845
        assert resp_packet.power == 65535

    def test_light_set_color_handler(self, color_device):
        """Test LightSetColor (102) updates device color."""
        new_color = LightHsbk(
            hue=10000, saturation=50000, brightness=40000, kelvin=4000
        )
        packet = Light.SetColor(color=new_color, duration=1000)

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,
            res_required=True,
        )

        _responses = color_device.process_packet(header, packet)

        assert color_device.state.color.hue == 10000
        assert color_device.state.color.saturation == 50000
        assert color_device.state.color.brightness == 40000
        assert color_device.state.color.kelvin == 4000

    def test_light_set_waveform_handler(self, color_device):
        """Test LightSetWaveform (103) stores waveform state."""
        waveform_color = LightHsbk(
            hue=30000, saturation=65535, brightness=65535, kelvin=3500
        )
        packet = Light.SetWaveform(
            transient=True,
            color=waveform_color,
            period=1000,
            cycles=5.0,
            skew_ratio=0,
            waveform=LightWaveform.SAW,
        )

        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=False,
        )

        color_device.process_packet(header, packet)

        assert color_device.state.waveform_active is True
        assert color_device.state.waveform_transient is True
        assert color_device.state.waveform_period_ms == 1000
        assert color_device.state.waveform_cycles == 5.0


class TestInfraredHandlers:
    """Test infrared-specific packet handlers."""

    def test_get_infrared_handler(self, infrared_device):
        """Test LightGetInfrared (120) -> LightStateInfrared (121)."""
        infrared_device.state.infrared_brightness = 32768

        header = LifxHeader(
            source=12345,
            target=infrared_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=120,
            res_required=True,
        )

        responses = infrared_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 121
        assert isinstance(resp_packet, Light.StateInfrared)
        assert resp_packet.brightness == 32768

    def test_set_infrared_handler(self, infrared_device):
        """Test LightSetInfrared (122) updates infrared brightness."""
        packet = Light.SetInfrared(brightness=50000)

        header = LifxHeader(
            source=12345,
            target=infrared_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=122,
            res_required=True,
        )

        infrared_device.process_packet(header, packet)

        assert infrared_device.state.infrared_brightness == 50000

    def test_infrared_not_supported_on_color_device(self, color_device):
        """Test infrared commands return None for non-IR devices."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=120,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        # Should only have ACK if ack_required, no infrared response
        for _, packet in responses:
            assert not isinstance(packet, Light.StateInfrared)


class TestHEVHandlers:
    """Test HEV-specific packet handlers."""

    def test_get_hev_cycle_handler(self, hev_device):
        """Test LightGetHevCycle (142) -> LightStateHevCycle (144)."""
        hev_device.state.hev_cycle_duration_s = 7200
        hev_device.state.hev_cycle_remaining_s = 3600

        header = LifxHeader(
            source=12345,
            target=hev_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=142,
            res_required=True,
        )

        responses = hev_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 144
        assert isinstance(resp_packet, Light.StateHevCycle)
        assert resp_packet.duration_s == 7200
        assert resp_packet.remaining_s == 3600

    def test_set_hev_cycle_enable(self, hev_device):
        """Test LightSetHevCycle (143) enables HEV cycle."""
        packet = Light.SetHevCycle(enable=True, duration_s=3600)

        header = LifxHeader(
            source=12345,
            target=hev_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=False,
        )

        hev_device.process_packet(header, packet)

        assert hev_device.state.hev_cycle_duration_s == 3600
        assert (
            hev_device.state.hev_cycle_remaining_s == 3600
        )  # Set to duration when enabled

    def test_set_hev_cycle_disable(self, hev_device):
        """Test LightSetHevCycle disables HEV cycle."""
        packet = Light.SetHevCycle(enable=False, duration_s=3600)

        header = LifxHeader(
            source=12345,
            target=hev_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=False,
        )

        hev_device.process_packet(header, packet)

        assert hev_device.state.hev_cycle_remaining_s == 0  # Disabled


class TestMultiZoneHandlers:
    """Test multizone-specific packet handlers."""

    def test_get_color_zones_returns_multiple_packets(self, multizone_device):
        """Test MultiZoneGetColorZones returns multiple StateMultiZone packets."""
        packet = MultiZone.GetColorZones(start_index=0, end_index=15)

        header = LifxHeader(
            source=12345,
            target=multizone_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=502,
            res_required=True,
        )

        responses = multizone_device.process_packet(header, packet)

        # 16 zones should return 2 packets (8 zones each)
        state_multizone_responses = [r for r in responses if r[0].pkt_type == 506]
        assert len(state_multizone_responses) == 2

        # Check first packet
        _, first_packet = state_multizone_responses[0]
        assert isinstance(first_packet, MultiZone.StateMultiZone)
        assert first_packet.count == 16
        assert first_packet.index == 0
        assert len(first_packet.colors) == 8

    def test_set_color_zones_updates_zones(self, multizone_device):
        """Test MultiZoneSetColorZones updates zone colors."""
        new_color = LightHsbk(
            hue=10000, saturation=65535, brightness=50000, kelvin=3500
        )
        packet = MultiZone.SetColorZones(
            start_index=5, end_index=10, color=new_color, duration=0, apply=0
        )

        header = LifxHeader(
            source=12345,
            target=multizone_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=501,
            res_required=False,
        )

        multizone_device.process_packet(header, packet)

        # Zones 5-10 should be updated
        for i in range(5, 11):
            assert multizone_device.state.zone_colors[i].hue == 10000
            assert multizone_device.state.zone_colors[i].saturation == 65535

    def test_extended_multizone_get(self, extended_multizone_device):
        """Test ExtendedGetColorZones for 82-zone device."""
        header = LifxHeader(
            source=12345,
            target=extended_multizone_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=511,
            res_required=True,
        )

        responses = extended_multizone_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 512
        assert isinstance(resp_packet, MultiZone.ExtendedStateMultiZone)
        assert resp_packet.count == 82
        assert len(resp_packet.colors) == 82


class TestTileHandlers:
    """Test tile-specific packet handlers."""

    def test_get_device_chain(self, tile_device):
        """Test TileGetDeviceChain (701) -> StateDeviceChain (702)."""
        header = LifxHeader(
            source=12345,
            target=tile_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=701,
            res_required=True,
        )

        responses = tile_device.process_packet(header, None)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 702
        assert isinstance(resp_packet, Tile.StateDeviceChain)
        assert resp_packet.tile_devices_count == 5
        assert len(resp_packet.tile_devices) == 16  # Padded to 16

    def test_get_64_pixels(self, tile_device):
        """Test TileGet64 (707) returns State64 (711)."""
        from lifx_emulator.protocol.protocol_types import TileBufferRect

        rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
        packet = Tile.Get64(tile_index=0, length=1, rect=rect)

        header = LifxHeader(
            source=12345,
            target=tile_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=707,
            res_required=True,
        )

        responses = tile_device.process_packet(header, packet)

        assert len(responses) >= 1
        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 711
        assert isinstance(resp_packet, Tile.State64)
        assert resp_packet.tile_index == 0
        assert len(resp_packet.colors) == 64


class TestAcknowledgment:
    """Test acknowledgment packet generation."""

    def test_ack_required_generates_acknowledgment(self, color_device):
        """Test ack_required flag generates Acknowledgement packet."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,  # GetPower
            ack_required=True,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        # Should have at least 2 responses: ACK + StatePower
        assert len(responses) >= 2

        # First response should be ACK
        ack_header, ack_packet = responses[0]
        assert ack_header.pkt_type == 45
        assert isinstance(ack_packet, Device.Acknowledgement)

    def test_no_ack_when_not_required(self, color_device):
        """Test no ACK when ack_required is False."""
        header = LifxHeader(
            source=12345,
            target=color_device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,  # GetPower
            ack_required=False,
            res_required=True,
        )

        responses = color_device.process_packet(header, None)

        # Should only have StatePower, no ACK
        assert all(h.pkt_type != 45 for h, _ in responses)
