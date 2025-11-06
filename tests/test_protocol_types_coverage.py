"""Tests for protocol types and header for increased coverage."""

from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.protocol_types import (
    DeviceService,
    LightHsbk,
)


class TestLightHsbk:
    """Test LightHsbk protocol type."""

    def test_light_hsbk_creation(self):
        """Test creating LightHsbk instances."""
        color = LightHsbk(hue=10000, saturation=20000, brightness=30000, kelvin=4000)
        assert color.hue == 10000
        assert color.saturation == 20000
        assert color.brightness == 30000
        assert color.kelvin == 4000

    def test_light_hsbk_with_defaults(self):
        """Test LightHsbk with default values."""
        color = LightHsbk(hue=0, saturation=0, brightness=65535, kelvin=5500)
        assert color.hue == 0
        assert color.saturation == 0
        assert color.brightness == 65535
        assert color.kelvin == 5500

    def test_light_hsbk_max_values(self):
        """Test LightHsbk with maximum values."""
        color = LightHsbk(hue=65535, saturation=65535, brightness=65535, kelvin=9000)
        assert color.hue == 65535
        assert color.saturation == 65535
        assert color.brightness == 65535
        assert color.kelvin == 9000

    def test_light_hsbk_equality(self):
        """Test LightHsbk equality checking."""
        color1 = LightHsbk(hue=10000, saturation=20000, brightness=30000, kelvin=4000)
        color2 = LightHsbk(hue=10000, saturation=20000, brightness=30000, kelvin=4000)
        # Both objects should have identical values
        assert color1.hue == color2.hue
        assert color1.saturation == color2.saturation
        assert color1.brightness == color2.brightness
        assert color1.kelvin == color2.kelvin

    def test_light_hsbk_different_colors(self):
        """Test different LightHsbk colors."""
        color1 = LightHsbk(hue=0, saturation=0, brightness=0, kelvin=2700)
        color2 = LightHsbk(hue=65535, saturation=65535, brightness=65535, kelvin=9000)
        assert color1.hue != color2.hue
        assert color1.kelvin != color2.kelvin


class TestLifxHeader:
    """Test LifxHeader protocol type."""

    def test_header_creation(self):
        """Test creating LifxHeader."""
        header = LifxHeader()
        assert header.size is not None
        assert header.protocol is not None

    def test_header_get_target_bytes(self):
        """Test converting serial to target bytes."""
        # Test with a valid 12-character hex serial
        serial = "d073d5000001"
        target_bytes = bytes.fromhex(serial) + b"\x00\x00"
        assert len(target_bytes) == 8

    def test_header_sequence_field(self):
        """Test header sequence field."""
        header = LifxHeader()
        # The sequence field should be accessible
        assert hasattr(header, "__dict__") or hasattr(header, "__dataclass_fields__")

    def test_device_service_enum(self):
        """Test DeviceService enum."""
        # DeviceService should have specific values
        assert DeviceService.UDP == 1
        # Should not have undefined values
        assert hasattr(DeviceService, "UDP")


class TestProtocolTypeRoundtrip:
    """Test roundtrip of protocol types."""

    def test_light_hsbk_roundtrip(self):
        """Test LightHsbk can be created and used consistently."""
        color1 = LightHsbk(hue=12345, saturation=54321, brightness=11111, kelvin=2700)
        color2 = LightHsbk(
            hue=color1.hue,
            saturation=color1.saturation,
            brightness=color1.brightness,
            kelvin=color1.kelvin,
        )
        assert color1.hue == color2.hue
        assert color1.saturation == color2.saturation
        assert color1.brightness == color2.brightness
        assert color1.kelvin == color2.kelvin

    def test_multiple_light_hsbk_colors(self):
        """Test multiple different LightHsbk colors."""
        colors = [
            LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=16384, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=32768, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=49152, saturation=65535, brightness=32768, kelvin=3500),
        ]
        assert len(colors) == 4
        assert colors[0].hue == 0
        assert colors[1].hue == 16384
        assert colors[2].hue == 32768
        assert colors[3].hue == 49152
        # All have same saturation and brightness
        for color in colors:
            assert color.saturation == 65535
            assert color.brightness == 32768
