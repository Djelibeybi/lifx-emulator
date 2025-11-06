"""Edge case tests for device handling."""

from lifx_emulator.factories import (
    create_color_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk


class TestDeviceEdgeCases:
    """Test edge cases in device handling."""

    def test_device_firmware_version(self):
        """Test creating device with firmware version."""
        device = create_multizone_light(
            "d073d5000001",
            zone_count=8,
            extended_multizone=False,
        )
        # Non-extended multizone should have firmware 2.60
        assert device.state.version_major == 2
        assert device.state.version_minor == 60

    def test_device_with_extended_multizone_firmware(self):
        """Test creating device with extended multizone firmware."""
        device = create_multizone_light(
            "d073d5000002",
            zone_count=80,
            extended_multizone=True,
        )
        # Extended multizone should have firmware 3.70
        assert device.state.version_major == 3
        assert device.state.version_minor == 70

    def test_device_basic_attributes(self):
        """Test device has expected attributes."""
        device = create_color_light("d073d5000001")
        # Check device has basic attributes
        assert hasattr(device.state, "serial")
        assert hasattr(device.state, "label")
        assert hasattr(device.state, "power_level")
        assert hasattr(device.state, "product")

    def test_color_light_capabilities(self):
        """Test color light device capabilities."""
        device = create_color_light("d073d5000001")
        assert device.state.has_color is True
        assert device.state.has_infrared is False
        assert device.state.has_multizone is False
        assert device.state.has_matrix is False
        assert device.state.has_hev is False

    def test_infrared_light_capabilities(self):
        """Test infrared light device capabilities."""
        device = create_infrared_light("d073d5000001")
        assert device.state.has_color is True
        assert device.state.has_infrared is True
        assert device.state.has_multizone is False

    def test_hev_light_capabilities(self):
        """Test HEV light device capabilities."""
        device = create_hev_light("d073d5000001")
        assert device.state.has_color is True
        assert device.state.has_hev is True
        assert device.state.has_infrared is False
        assert device.state.has_multizone is False

    def test_multizone_light_capabilities(self):
        """Test multizone light device capabilities."""
        device = create_multizone_light("d073d5000001", zone_count=16)
        # Multizone lights may have color
        assert device.state.has_multizone is True
        assert device.state.has_matrix is False
        assert device.state.zone_count == 16

    def test_extended_multizone_light_capabilities(self):
        """Test extended multizone light capabilities."""
        device = create_multizone_light(
            "d073d5000001", zone_count=80, extended_multizone=True
        )
        assert device.state.has_multizone is True
        assert device.state.zone_count == 80

    def test_tile_device_capabilities(self):
        """Test tile device capabilities."""
        device = create_tile_device("d073d5000001", tile_count=2)
        assert device.state.has_matrix is True
        assert device.state.has_multizone is False
        assert device.state.tile_count == 2

    def test_device_state_label_persistence(self):
        """Test device label can be set and retrieved."""
        device = create_color_light("d073d5000001")
        original_label = device.state.label

        # Set a new label
        new_label = "My Test Light"
        device.state.label = new_label

        # Verify it's set
        assert device.state.label == new_label
        assert device.state.label != original_label

    def test_device_location_and_group(self):
        """Test device location and group metadata."""
        device = create_color_light("d073d5000001")

        # Set location
        device.state.location_label = "Living Room"
        device.state.location_id = "abc123"

        # Set group
        device.state.group_label = "Downstairs"
        device.state.group_id = "xyz789"

        assert device.state.location_label == "Living Room"
        assert device.state.group_label == "Downstairs"

    def test_device_power_state(self):
        """Test device power state."""
        device = create_color_light("d073d5000001")

        # Check default power level
        assert isinstance(device.state.power_level, int)
        assert 0 <= device.state.power_level <= 65535

        # Set power level
        device.state.power_level = 0  # Off
        assert device.state.power_level == 0

        device.state.power_level = 65535  # On
        assert device.state.power_level == 65535

    def test_color_device_color_state(self):
        """Test color device color state."""
        device = create_color_light("d073d5000001")

        # Check default color
        assert device.state.color is not None
        assert isinstance(device.state.color, LightHsbk)

        # Set color
        new_color = LightHsbk(
            hue=10000, saturation=50000, brightness=40000, kelvin=4000
        )
        device.state.color = new_color
        assert device.state.color.hue == 10000

    def test_infrared_device_brightness(self):
        """Test infrared device brightness."""
        device = create_infrared_light("d073d5000001")

        # Check default infrared brightness
        assert device.state.infrared_brightness is not None
        assert 0 <= device.state.infrared_brightness <= 65535

        # Set infrared brightness
        device.state.infrared_brightness = 32768
        assert device.state.infrared_brightness == 32768

    def test_hev_device_state(self):
        """Test HEV device state fields."""
        device = create_hev_light("d073d5000001")

        # Check HEV fields
        assert hasattr(device.state, "hev_cycle_duration_s")
        assert hasattr(device.state, "hev_cycle_remaining_s")
        assert hasattr(device.state, "hev_cycle_last_power")
        assert hasattr(device.state, "hev_indication")
        assert hasattr(device.state, "hev_last_result")

    def test_multizone_device_zone_colors(self):
        """Test multizone device zone colors."""
        device = create_multizone_light("d073d5000001", zone_count=4)

        # Check zone count
        assert len(device.state.zone_colors) == 4

        # Set zone color
        new_color = LightHsbk(
            hue=10000, saturation=50000, brightness=40000, kelvin=4000
        )
        device.state.zone_colors[0] = new_color
        assert device.state.zone_colors[0].hue == 10000

    def test_tile_device_tile_colors(self):
        """Test tile device tile structure."""
        device = create_tile_device(
            "d073d5000001", tile_count=2, tile_width=8, tile_height=8
        )

        # Check tile count
        assert len(device.state.tile_devices) == 2

        # Check tile dimensions
        for tile in device.state.tile_devices:
            assert tile["width"] == 8
            assert tile["height"] == 8

    def test_device_serial_formats(self):
        """Test various serial number formats."""
        serials = [
            "d073d5000001",
            "d073d5abcdef",
            "000000000001",
            "ffffffffffffffff"[:12],  # Truncate to 12 chars
        ]

        for serial in serials:
            device = create_color_light(serial)
            assert device.state.serial == serial

    def test_device_version_fields(self):
        """Test device version fields."""
        device = create_color_light("d073d5000001")
        # Check version fields exist
        assert hasattr(device.state, "version_major")
        assert hasattr(device.state, "version_minor")
        assert device.state.version_major > 0
        assert device.state.version_minor >= 0

    def test_device_hardware_version(self):
        """Test device hardware version."""
        device = create_color_light("d073d5000001")
        # Check product fields
        assert hasattr(device.state, "product")
        assert device.state.product > 0  # Should have a product ID
        assert device.state.vendor == 1  # LIFX vendor ID
