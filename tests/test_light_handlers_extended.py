"""Extended tests for light packet handlers to improve coverage."""

from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.protocol_types import LightHsbk, LightWaveform


class TestGetAndSetColor:
    """Test LightGet and LightSetColor handlers."""

    def test_get_color(self, color_device):
        """Test LightGet returns current color state."""
        device = color_device
        device.state.label = "Test Light"

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=101,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 107  # StateColor
        assert isinstance(resp_packet, Light.StateColor)
        assert resp_packet.power == device.state.power_level

    def test_set_color_updates_state(self, color_device):
        """Test SetColor updates device color."""
        device = color_device

        new_color = LightHsbk(
            hue=30000, saturation=65535, brightness=32768, kelvin=4000
        )
        packet = Light.SetColor(color=new_color, duration=1000)

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.color.hue == 30000
        assert device.state.color.saturation == 65535
        assert device.state.color.brightness == 32768
        assert device.state.color.kelvin == 4000

    def test_set_color_with_response(self, color_device):
        """Test SetColor with res_required returns StateColor."""
        device = color_device

        new_color = LightHsbk(
            hue=10000, saturation=30000, brightness=40000, kelvin=3500
        )
        packet = Light.SetColor(color=new_color, duration=0)

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=102,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_color_responses = [r for r in responses if r[0].pkt_type == 107]
        assert len(state_color_responses) > 0


class TestGetAndSetPower:
    """Test LightGetPower and LightSetPower handlers."""

    def test_get_power(self, color_device):
        """Test LightGetPower returns current power level."""
        device = color_device
        device.state.power_level = 65535

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=116,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 118  # StatePower
        assert isinstance(resp_packet, Light.StatePower)
        assert resp_packet.level == 65535

    def test_set_power_on(self, color_device):
        """Test SetPower turns light on."""
        device = color_device
        device.state.power_level = 0

        packet = Light.SetPower(level=65535, duration=500)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=117,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.power_level == 65535

    def test_set_power_off(self, color_device):
        """Test SetPower turns light off."""
        device = color_device
        device.state.power_level = 65535

        packet = Light.SetPower(level=0, duration=0)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=117,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.power_level == 0

    def test_set_power_with_duration(self, color_device):
        """Test SetPower with transition duration."""
        device = color_device

        packet = Light.SetPower(level=32768, duration=2000)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=117,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        # Verify power was set
        assert device.state.power_level == 32768

        # Verify response was sent
        state_power_responses = [r for r in responses if r[0].pkt_type == 118]
        assert len(state_power_responses) > 0


class TestWaveforms:
    """Test waveform handlers."""

    def test_set_waveform_saw(self, color_device):
        """Test SetWaveform with SAW waveform."""
        device = color_device

        waveform_color = LightHsbk(
            hue=20000, saturation=65535, brightness=65535, kelvin=3500
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
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.waveform_active is True
        assert device.state.waveform_type == int(LightWaveform.SAW)
        assert device.state.waveform_transient is True
        assert device.state.waveform_cycles == 5.0

    def test_set_waveform_sine(self, color_device):
        """Test SetWaveform with SINE waveform."""
        device = color_device

        waveform_color = LightHsbk(
            hue=10000, saturation=50000, brightness=40000, kelvin=4000
        )
        packet = Light.SetWaveform(
            transient=False,
            color=waveform_color,
            period=2000,
            cycles=10.0,
            skew_ratio=0,
            waveform=LightWaveform.SINE,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.waveform_type == int(LightWaveform.SINE)
        assert device.state.waveform_transient is False
        # Non-transient should update color
        assert device.state.color == waveform_color

    def test_set_waveform_triangle(self, color_device):
        """Test SetWaveform with TRIANGLE waveform."""
        device = color_device

        waveform_color = LightHsbk(
            hue=40000, saturation=65535, brightness=50000, kelvin=2700
        )
        packet = Light.SetWaveform(
            transient=True,
            color=waveform_color,
            period=500,
            cycles=20.0,
            skew_ratio=0,
            waveform=LightWaveform.TRIANGLE,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.waveform_type == int(LightWaveform.TRIANGLE)

    def test_set_waveform_pulse(self, color_device):
        """Test SetWaveform with PULSE waveform."""
        device = color_device

        waveform_color = LightHsbk(hue=0, saturation=0, brightness=65535, kelvin=6500)
        packet = Light.SetWaveform(
            transient=True,
            color=waveform_color,
            period=100,
            cycles=50.0,
            skew_ratio=32768,  # 50% duty cycle
            waveform=LightWaveform.PULSE,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.waveform_type == int(LightWaveform.PULSE)
        assert device.state.waveform_skew_ratio == 32768

    def test_set_waveform_with_response(self, color_device):
        """Test SetWaveform with res_required returns StateColor."""
        device = color_device

        waveform_color = LightHsbk(
            hue=30000, saturation=65535, brightness=65535, kelvin=3500
        )
        packet = Light.SetWaveform(
            transient=True,
            color=waveform_color,
            period=1000,
            cycles=1.0,
            skew_ratio=0,
            waveform=LightWaveform.SAW,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=103,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_color_responses = [r for r in responses if r[0].pkt_type == 107]
        assert len(state_color_responses) > 0


class TestWaveformOptional:
    """Test SetWaveformOptional handler."""

    def test_set_waveform_optional_all_components(self, color_device):
        """Test SetWaveformOptional with all color components enabled."""
        device = color_device

        waveform_color = LightHsbk(
            hue=25000, saturation=50000, brightness=40000, kelvin=4500
        )
        packet = Light.SetWaveformOptional(
            transient=False,
            color=waveform_color,
            period=1000,
            cycles=3.0,
            skew_ratio=0,
            waveform=LightWaveform.SINE,
            set_hue=True,
            set_saturation=True,
            set_brightness=True,
            set_kelvin=True,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=119,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.color.hue == 25000
        assert device.state.color.saturation == 50000
        assert device.state.color.brightness == 40000
        assert device.state.color.kelvin == 4500

    def test_set_waveform_optional_hue_only(self, color_device):
        """Test SetWaveformOptional updating only hue."""
        device = color_device
        original_saturation = device.state.color.saturation
        original_brightness = device.state.color.brightness

        waveform_color = LightHsbk(
            hue=50000, saturation=30000, brightness=20000, kelvin=3000
        )
        packet = Light.SetWaveformOptional(
            transient=False,
            color=waveform_color,
            period=1000,
            cycles=1.0,
            skew_ratio=0,
            waveform=LightWaveform.TRIANGLE,
            set_hue=True,
            set_saturation=False,
            set_brightness=False,
            set_kelvin=False,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=119,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Only hue should be updated
        assert device.state.color.hue == 50000
        assert device.state.color.saturation == original_saturation
        assert device.state.color.brightness == original_brightness

    def test_set_waveform_optional_saturation_brightness(self, color_device):
        """Test SetWaveformOptional updating saturation and brightness."""
        device = color_device
        original_hue = device.state.color.hue
        original_kelvin = device.state.color.kelvin

        waveform_color = LightHsbk(
            hue=10000, saturation=40000, brightness=50000, kelvin=2500
        )
        packet = Light.SetWaveformOptional(
            transient=False,
            color=waveform_color,
            period=500,
            cycles=2.0,
            skew_ratio=16384,
            waveform=LightWaveform.PULSE,
            set_hue=False,
            set_saturation=True,
            set_brightness=True,
            set_kelvin=False,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=119,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.color.hue == original_hue
        assert device.state.color.saturation == 40000
        assert device.state.color.brightness == 50000
        assert device.state.color.kelvin == original_kelvin

    def test_set_waveform_optional_transient(self, color_device):
        """Test SetWaveformOptional with transient=True doesn't update color."""
        device = color_device
        original_color = device.state.color

        waveform_color = LightHsbk(
            hue=60000, saturation=60000, brightness=60000, kelvin=6000
        )
        packet = Light.SetWaveformOptional(
            transient=True,
            color=waveform_color,
            period=1000,
            cycles=5.0,
            skew_ratio=0,
            waveform=LightWaveform.SAW,
            set_hue=True,
            set_saturation=True,
            set_brightness=True,
            set_kelvin=True,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=119,
            res_required=False,
        )

        device.process_packet(header, packet)

        # Color should not change when transient
        assert device.state.color == original_color
        # But waveform color should be stored
        assert device.state.waveform_color == waveform_color

    def test_set_waveform_optional_with_response(self, color_device):
        """Test SetWaveformOptional with res_required returns StateColor."""
        device = color_device

        waveform_color = LightHsbk(
            hue=15000, saturation=45000, brightness=55000, kelvin=3500
        )
        packet = Light.SetWaveformOptional(
            transient=False,
            color=waveform_color,
            period=1000,
            cycles=1.0,
            skew_ratio=0,
            waveform=LightWaveform.SINE,
            set_hue=True,
            set_saturation=True,
            set_brightness=True,
            set_kelvin=True,
        )

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=119,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_color_responses = [r for r in responses if r[0].pkt_type == 107]
        assert len(state_color_responses) > 0


class TestInfrared:
    """Test infrared handlers."""

    def test_get_infrared(self, infrared_device):
        """Test GetInfrared returns infrared brightness."""
        device = infrared_device
        device.state.infrared_brightness = 32768

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=120,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 121  # StateInfrared
        assert isinstance(resp_packet, Light.StateInfrared)
        assert resp_packet.brightness == 32768

    def test_set_infrared(self, infrared_device):
        """Test SetInfrared updates infrared brightness."""
        device = infrared_device

        packet = Light.SetInfrared(brightness=50000)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=122,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.infrared_brightness == 50000

    def test_set_infrared_with_response(self, infrared_device):
        """Test SetInfrared with res_required returns StateInfrared."""
        device = infrared_device

        packet = Light.SetInfrared(brightness=40000)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=122,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_infrared_responses = [r for r in responses if r[0].pkt_type == 121]
        assert len(state_infrared_responses) > 0

    def test_get_infrared_on_non_ir_device(self, color_device):
        """Test GetInfrared on non-IR device returns None."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=120,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should not return StateInfrared
        assert all(resp[0].pkt_type != 121 for resp in responses)

    def test_set_infrared_on_non_ir_device(self, color_device):
        """Test SetInfrared on non-IR device is ignored."""
        device = color_device

        packet = Light.SetInfrared(brightness=30000)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=122,
            res_required=False,
        )

        # Should not crash
        device.process_packet(header, packet)


class TestHEV:
    """Test HEV (High Energy Visible) handlers."""

    def test_get_hev_cycle(self, hev_device):
        """Test GetHevCycle returns current cycle state."""
        device = hev_device
        device.state.hev_cycle_duration_s = 7200
        device.state.hev_cycle_remaining_s = 3600

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=142,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 144  # StateHevCycle
        assert isinstance(resp_packet, Light.StateHevCycle)
        assert resp_packet.duration_s == 7200
        assert resp_packet.remaining_s == 3600

    def test_set_hev_cycle_enable(self, hev_device):
        """Test SetHevCycle enables HEV cycle."""
        device = hev_device

        packet = Light.SetHevCycle(enable=True, duration_s=3600)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.hev_cycle_duration_s == 3600
        assert (
            device.state.hev_cycle_remaining_s == 3600
        )  # Set to duration when enabled

    def test_set_hev_cycle_disable(self, hev_device):
        """Test SetHevCycle disables HEV cycle."""
        device = hev_device
        device.state.hev_cycle_remaining_s = 1800

        packet = Light.SetHevCycle(enable=False, duration_s=3600)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.hev_cycle_duration_s == 3600
        assert device.state.hev_cycle_remaining_s == 0  # Reset to 0 when disabled

    def test_set_hev_cycle_with_response(self, hev_device):
        """Test SetHevCycle with res_required returns StateHevCycle."""
        device = hev_device

        packet = Light.SetHevCycle(enable=True, duration_s=1800)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_hev_responses = [r for r in responses if r[0].pkt_type == 144]
        assert len(state_hev_responses) > 0

    def test_get_hev_cycle_on_non_hev_device(self, color_device):
        """Test GetHevCycle on non-HEV device returns None."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=142,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        assert all(resp[0].pkt_type != 144 for resp in responses)

    def test_set_hev_cycle_on_non_hev_device(self, color_device):
        """Test SetHevCycle on non-HEV device is ignored."""
        device = color_device

        packet = Light.SetHevCycle(enable=True, duration_s=3600)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=143,
            res_required=False,
        )

        device.process_packet(header, packet)

    def test_get_hev_cycle_configuration(self, hev_device):
        """Test GetHevCycleConfiguration returns config."""
        device = hev_device
        device.state.hev_indication = True
        device.state.hev_cycle_duration_s = 7200

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=145,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 147  # StateHevCycleConfiguration
        assert isinstance(resp_packet, Light.StateHevCycleConfiguration)
        assert resp_packet.indication is True
        assert resp_packet.duration_s == 7200

    def test_set_hev_cycle_configuration(self, hev_device):
        """Test SetHevCycleConfiguration updates config."""
        device = hev_device

        packet = Light.SetHevCycleConfiguration(indication=False, duration_s=5400)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=146,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.hev_indication is False
        assert device.state.hev_cycle_duration_s == 5400

    def test_set_hev_cycle_configuration_with_response(self, hev_device):
        """Test SetHevCycleConfiguration with res_required."""
        device = hev_device

        packet = Light.SetHevCycleConfiguration(indication=True, duration_s=10800)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=146,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_config_responses = [r for r in responses if r[0].pkt_type == 147]
        assert len(state_config_responses) > 0

    def test_get_last_hev_cycle_result(self, hev_device):
        """Test GetLastHevCycleResult returns last result."""
        device = hev_device
        device.state.hev_last_result = 1

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=148,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 149  # StateLastHevCycleResult
        assert isinstance(resp_packet, Light.StateLastHevCycleResult)

    def test_get_last_hev_cycle_result_on_non_hev(self, color_device):
        """Test GetLastHevCycleResult on non-HEV device."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=148,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        assert all(resp[0].pkt_type != 149 for resp in responses)
