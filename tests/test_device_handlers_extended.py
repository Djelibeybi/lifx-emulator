"""Extended tests for device packet handlers to improve coverage."""

from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device


class TestGetService:
    """Test GetService handler."""

    def test_get_service_returns_udp(self, color_device):
        """Test GetService returns UDP service."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=2,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        # Should return StateService
        state_service_responses = [r for r in responses if r[0].pkt_type == 3]
        assert len(state_service_responses) > 0

        resp_header, resp_packet = state_service_responses[0]
        assert isinstance(resp_packet, Device.StateService)
        assert resp_packet.service == 1  # UDP
        assert resp_packet.port == 56700

    def test_get_service_always_responds(self, color_device):
        """Test GetService always responds (ignores res_required)."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=2,
            res_required=False,
        )

        responses = device.process_packet(header, None)

        # GetService always responds regardless of res_required
        state_service_responses = [r for r in responses if r[0].pkt_type == 3]
        assert len(state_service_responses) > 0


class TestPowerHandlers:
    """Test GetPower and SetPower handlers."""

    def test_get_power_on(self, color_device):
        """Test GetPower when device is on."""
        device = color_device
        device.state.power_level = 65535

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 22  # StatePower
        assert isinstance(resp_packet, Device.StatePower)
        assert resp_packet.level == 65535

    def test_get_power_off(self, color_device):
        """Test GetPower when device is off."""
        device = color_device
        device.state.power_level = 0

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=20,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_packet.level == 0

    def test_set_power_on(self, color_device):
        """Test SetPower turning device on."""
        device = color_device
        device.state.power_level = 0

        packet = Device.SetPower(level=65535)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.power_level == 65535

    def test_set_power_off(self, color_device):
        """Test SetPower turning device off."""
        device = color_device
        device.state.power_level = 65535

        packet = Device.SetPower(level=0)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.power_level == 0

    def test_set_power_with_response(self, color_device):
        """Test SetPower with res_required returns StatePower."""
        device = color_device

        packet = Device.SetPower(level=32768)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=21,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_power_responses = [r for r in responses if r[0].pkt_type == 22]
        assert len(state_power_responses) > 0


class TestLabelHandlers:
    """Test GetLabel and SetLabel handlers."""

    def test_get_label_default(self, color_device):
        """Test GetLabel returns default label."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=23,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 25  # StateLabel
        assert isinstance(resp_packet, Device.StateLabel)
        # Default label is auto-generated from product name and serial suffix
        assert resp_packet.label == "LIFX Color 000001"

    def test_set_label_ascii(self, color_device):
        """Test SetLabel with ASCII string."""
        device = color_device

        # SetLabel expects a string
        packet = Device.SetLabel(label="Living Room")
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=24,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.label == "Living Room"

    def test_set_label_unicode(self, color_device):
        """Test SetLabel with Unicode characters."""
        device = color_device

        packet = Device.SetLabel(label="Café Light ☀")
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=24,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.label == "Café Light ☀"

    def test_set_label_empty(self, color_device):
        """Test SetLabel with empty string."""
        device = color_device
        device.state.label = "Original"

        packet = Device.SetLabel(label="")
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=24,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.label == ""

    def test_set_label_with_response(self, color_device):
        """Test SetLabel with res_required returns StateLabel."""
        device = color_device

        packet = Device.SetLabel(label="Test Label")
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=24,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_label_responses = [r for r in responses if r[0].pkt_type == 25]
        assert len(state_label_responses) > 0


class TestVersionAndInfo:
    """Test GetVersion and GetInfo handlers."""

    def test_get_version(self, color_device):
        """Test GetVersion returns vendor and product info."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=32,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 33  # StateVersion
        assert isinstance(resp_packet, Device.StateVersion)
        assert resp_packet.vendor == 1  # LIFX
        assert resp_packet.product == 91  # LIFX Color

    def test_get_info(self, color_device):
        """Test GetInfo returns uptime and time."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=34,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 35  # StateInfo
        assert isinstance(resp_packet, Device.StateInfo)
        assert resp_packet.uptime >= 0
        assert resp_packet.time > 0
        assert resp_packet.downtime == 0

    def test_get_info_always_responds(self, color_device):
        """Test GetInfo always responds (ignores res_required)."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=34,
            res_required=False,
        )

        responses = device.process_packet(header, None)

        # GetInfo always responds regardless of res_required
        state_info_responses = [r for r in responses if r[0].pkt_type == 35]
        assert len(state_info_responses) > 0


class TestFirmwareHandlers:
    """Test GetHostFirmware and GetWifiFirmware handlers."""

    def test_get_host_firmware(self, color_device):
        """Test GetHostFirmware returns firmware version."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=14,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 15  # StateHostFirmware
        assert isinstance(resp_packet, Device.StateHostFirmware)
        assert resp_packet.version_major == 3
        assert resp_packet.version_minor == 70

    def test_get_host_firmware_custom_version(self, color_device):
        """Test GetHostFirmware with custom firmware version."""
        device = color_device
        device.state.version_major = 2
        device.state.version_minor = 80

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=14,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_packet.version_major == 2
        assert resp_packet.version_minor == 80

    def test_get_wifi_firmware(self, color_device):
        """Test GetWifiFirmware returns WiFi firmware version."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=18,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 19  # StateWifiFirmware
        assert isinstance(resp_packet, Device.StateWifiFirmware)
        # WiFi firmware uses device firmware version (default 3.70)
        assert resp_packet.version_major == 3
        assert resp_packet.version_minor == 70


class TestWifiInfo:
    """Test GetWifiInfo handler."""

    def test_get_wifi_info(self, color_device):
        """Test GetWifiInfo returns signal strength."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=16,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 17  # StateWifiInfo
        assert isinstance(resp_packet, Device.StateWifiInfo)
        # Signal is negative in dBm (default -45.0)
        assert resp_packet.signal == -45.0

    def test_get_wifi_info_always_responds(self, color_device):
        """Test GetWifiInfo always responds (ignores res_required)."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=16,
            res_required=False,
        )

        responses = device.process_packet(header, None)

        # GetWifiInfo always responds regardless of res_required
        state_wifi_info_responses = [r for r in responses if r[0].pkt_type == 17]
        assert len(state_wifi_info_responses) > 0


class TestLocationHandlers:
    """Test GetLocation and SetLocation handlers."""

    def test_get_location_default(self, color_device):
        """Test GetLocation returns default location."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=48,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 50  # StateLocation
        assert isinstance(resp_packet, Device.StateLocation)
        # Default location label is "Test Location"
        assert resp_packet.label == "Test Location"

    def test_set_location(self, color_device):
        """Test SetLocation updates location."""
        device = color_device

        location_guid = (
            b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        )
        packet = Device.SetLocation(
            location=location_guid, label="Home", updated_at=1234567890000000000
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=49,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.location_id == location_guid
        assert device.state.location_label == "Home"
        assert device.state.location_updated_at == 1234567890000000000

    def test_set_location_with_response(self, color_device):
        """Test SetLocation with res_required returns StateLocation."""
        device = color_device

        location_guid = b"\xff" * 16
        packet = Device.SetLocation(
            location=location_guid, label="Office", updated_at=9876543210000000000
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=49,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_location_responses = [r for r in responses if r[0].pkt_type == 50]
        assert len(state_location_responses) > 0

        resp_header, resp_packet = state_location_responses[0]
        assert resp_packet.location == location_guid
        assert resp_packet.label == "Office"

    def test_set_location_empty_label(self, color_device):
        """Test SetLocation with empty label."""
        device = color_device

        location_guid = b"\x00" * 16
        packet = Device.SetLocation(location=location_guid, label="", updated_at=0)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=49,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.location_label == ""


class TestGroupHandlers:
    """Test GetGroup and SetGroup handlers."""

    def test_get_group_default(self, color_device):
        """Test GetGroup returns default group."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=51,
            res_required=True,
        )

        responses = device.process_packet(header, None)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 53  # StateGroup
        assert isinstance(resp_packet, Device.StateGroup)
        # Default group label is "Test Group"
        assert resp_packet.label == "Test Group"

    def test_set_group(self, color_device):
        """Test SetGroup updates group."""
        device = color_device

        group_guid = b"\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99"
        packet = Device.SetGroup(
            group=group_guid, label="Living Room", updated_at=5555555555000000000
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=52,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.group_id == group_guid
        assert device.state.group_label == "Living Room"
        assert device.state.group_updated_at == 5555555555000000000

    def test_set_group_with_response(self, color_device):
        """Test SetGroup with res_required returns StateGroup."""
        device = color_device

        group_guid = b"\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00"
        packet = Device.SetGroup(
            group=group_guid, label="Bedroom", updated_at=7777777777000000000
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=52,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        state_group_responses = [r for r in responses if r[0].pkt_type == 53]
        assert len(state_group_responses) > 0

        resp_header, resp_packet = state_group_responses[0]
        assert resp_packet.group == group_guid
        assert resp_packet.label == "Bedroom"

    def test_set_group_unicode_label(self, color_device):
        """Test SetGroup with Unicode label."""
        device = color_device

        group_guid = b"\x00" * 16
        packet = Device.SetGroup(
            group=group_guid,
            label="Salle à manger 🍽",  # codespell:ignore
            updated_at=0,
        )
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=52,
            res_required=False,
        )

        device.process_packet(header, packet)

        assert device.state.group_label == "Salle à manger 🍽"  # codespell:ignore


class TestEchoRequest:
    """Test EchoRequest handler."""

    def test_echo_request_empty_payload(self, color_device):
        """Test EchoRequest with empty payload."""
        device = color_device

        # EchoRequest payload is always 64 bytes (padded with nulls)
        test_payload = b"".ljust(64, b"\x00")
        packet = Device.EchoRequest(payload=test_payload)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=58,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        resp_header, resp_packet = responses[-1]
        assert resp_header.pkt_type == 59  # EchoResponse
        assert isinstance(resp_packet, Device.EchoResponse)
        assert resp_packet.payload == test_payload

    def test_echo_request_with_data(self, color_device):
        """Test EchoRequest echoes back data."""
        device = color_device

        # Payload is padded to 64 bytes
        test_payload = b"Hello LIFX!".ljust(64, b"\x00")
        packet = Device.EchoRequest(payload=test_payload)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=58,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        resp_header, resp_packet = responses[-1]
        assert resp_packet.payload == test_payload

    def test_echo_request_max_payload(self, color_device):
        """Test EchoRequest with maximum 64-byte payload."""
        device = color_device

        test_payload = b"A" * 64
        packet = Device.EchoRequest(payload=test_payload)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=58,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        resp_header, resp_packet = responses[-1]
        assert resp_packet.payload == test_payload
        assert len(resp_packet.payload) == 64

    def test_echo_request_binary_data(self, color_device):
        """Test EchoRequest with binary data."""
        device = color_device

        # Pad to 64 bytes
        test_payload = bytes(range(32)).ljust(64, b"\x00")
        packet = Device.EchoRequest(payload=test_payload)
        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=58,
            res_required=True,
        )

        responses = device.process_packet(header, packet)

        resp_header, resp_packet = responses[-1]
        assert resp_packet.payload == test_payload


class TestRebootHandler:
    """Test SetReboot handler."""

    def test_set_reboot_no_op(self, color_device):
        """Test SetReboot is a no-op in emulator."""
        device = color_device
        original_power = device.state.power_level
        original_label = device.state.label

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=38,
            res_required=False,
        )

        # Should not crash or change state
        device.process_packet(header, None)

        assert device.state.power_level == original_power
        assert device.state.label == original_label

    def test_set_reboot_with_response_required(self, color_device):
        """Test SetReboot with res_required."""
        device = color_device

        header = LifxHeader(
            source=12345,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=38,
            res_required=True,
        )

        # Should handle gracefully even with res_required
        responses = device.process_packet(header, None)

        # No state packet expected, only ack if ack_required was set
        # (but we only set res_required here)
        assert isinstance(responses, list)
