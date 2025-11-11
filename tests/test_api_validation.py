"""Tests for API input validation using Pydantic models."""

import pytest
from pydantic import ValidationError

from lifx_emulator.api.models import ColorHsbk, DeviceCreateRequest


class TestDeviceCreateRequestValidation:
    """Test DeviceCreateRequest validation."""

    def test_valid_product_id(self):
        """Test valid product ID."""
        request = DeviceCreateRequest(product_id=27)
        assert request.product_id == 27

    def test_product_id_too_low(self):
        """Test product ID of 0 is rejected."""
        with pytest.raises(ValidationError, match="greater than 0"):
            DeviceCreateRequest(product_id=0)

    def test_product_id_too_high(self):
        """Test product ID >= 10000 is rejected."""
        with pytest.raises(ValidationError, match="less than 10000"):
            DeviceCreateRequest(product_id=10000)

    def test_valid_serial(self):
        """Test valid serial number."""
        request = DeviceCreateRequest(product_id=27, serial="d073d5000001")
        assert request.serial == "d073d5000001"

    def test_serial_uppercase_normalized(self):
        """Test serial with uppercase is normalized to lowercase."""
        request = DeviceCreateRequest(product_id=27, serial="D073D5000001")
        assert request.serial == "d073d5000001"

    def test_serial_mixed_case_normalized(self):
        """Test serial with mixed case is normalized."""
        request = DeviceCreateRequest(product_id=27, serial="DeAdBeEf0123")
        assert request.serial == "deadbeef0123"

    def test_serial_too_short(self):
        """Test serial that's too short is rejected."""
        with pytest.raises(ValidationError, match="12 characters"):
            DeviceCreateRequest(product_id=27, serial="short")

    def test_serial_too_long(self):
        """Test serial that's too long is rejected."""
        with pytest.raises(ValidationError, match="12 characters"):
            DeviceCreateRequest(product_id=27, serial="d073d500000100")

    def test_serial_invalid_hex(self):
        """Test serial with non-hex characters is rejected."""
        with pytest.raises(ValidationError, match="hexadecimal"):
            DeviceCreateRequest(product_id=27, serial="xyz123456789")

    def test_serial_with_special_chars(self):
        """Test serial with special characters is rejected."""
        with pytest.raises(ValidationError, match="hexadecimal"):
            DeviceCreateRequest(product_id=27, serial="d073-5000001")

    def test_zone_count_valid(self):
        """Test valid zone count."""
        request = DeviceCreateRequest(product_id=32, zone_count=16)
        assert request.zone_count == 16

    def test_zone_count_zero(self):
        """Test zone count of 0 is accepted."""
        request = DeviceCreateRequest(product_id=27, zone_count=0)
        assert request.zone_count == 0

    def test_zone_count_negative(self):
        """Test negative zone count is rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            DeviceCreateRequest(product_id=32, zone_count=-1)

    def test_zone_count_too_high(self):
        """Test zone count > 1000 is rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 1000"):
            DeviceCreateRequest(product_id=32, zone_count=1001)

    def test_tile_count_valid(self):
        """Test valid tile count."""
        request = DeviceCreateRequest(product_id=55, tile_count=5)
        assert request.tile_count == 5

    def test_tile_count_too_high(self):
        """Test tile count > 100 is rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            DeviceCreateRequest(product_id=55, tile_count=101)

    def test_tile_dimensions_valid(self):
        """Test valid tile dimensions."""
        request = DeviceCreateRequest(product_id=55, tile_width=8, tile_height=8)
        assert request.tile_width == 8
        assert request.tile_height == 8

    def test_tile_width_too_small(self):
        """Test tile width of 0 is rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DeviceCreateRequest(product_id=55, tile_width=0, tile_height=8)

    def test_tile_dimensions_too_large(self):
        """Test tile dimensions > 256 are rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 256"):
            DeviceCreateRequest(product_id=55, tile_width=257, tile_height=8)

    def test_firmware_version_valid(self):
        """Test valid firmware version."""
        request = DeviceCreateRequest(
            product_id=27, firmware_major=3, firmware_minor=70
        )
        assert request.firmware_major == 3
        assert request.firmware_minor == 70

    def test_firmware_version_too_high(self):
        """Test firmware version > 255 is rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 255"):
            DeviceCreateRequest(product_id=27, firmware_major=256)


class TestColorHsbkValidation:
    """Test ColorHsbk validation."""

    def test_valid_color(self):
        """Test valid HSBK color."""
        color = ColorHsbk(hue=32768, saturation=65535, brightness=32768, kelvin=3500)
        assert color.hue == 32768
        assert color.saturation == 65535
        assert color.brightness == 32768
        assert color.kelvin == 3500

    def test_hue_min(self):
        """Test hue minimum value (0)."""
        color = ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=2500)
        assert color.hue == 0

    def test_hue_max(self):
        """Test hue maximum value (65535)."""
        color = ColorHsbk(hue=65535, saturation=0, brightness=0, kelvin=2500)
        assert color.hue == 65535

    def test_hue_too_low(self):
        """Test hue < 0 is rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ColorHsbk(hue=-1, saturation=0, brightness=0, kelvin=2500)

    def test_hue_too_high(self):
        """Test hue > 65535 is rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ColorHsbk(hue=65536, saturation=0, brightness=0, kelvin=2500)

    def test_saturation_bounds(self):
        """Test saturation bounds."""
        # Min
        color = ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=2500)
        assert color.saturation == 0

        # Max
        color = ColorHsbk(hue=0, saturation=65535, brightness=0, kelvin=2500)
        assert color.saturation == 65535

        # Too high
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ColorHsbk(hue=0, saturation=65536, brightness=0, kelvin=2500)

    def test_brightness_bounds(self):
        """Test brightness bounds."""
        # Min
        color = ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=2500)
        assert color.brightness == 0

        # Max
        color = ColorHsbk(hue=0, saturation=0, brightness=65535, kelvin=2500)
        assert color.brightness == 65535

        # Too high
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ColorHsbk(hue=0, saturation=0, brightness=65536, kelvin=2500)

    def test_kelvin_min(self):
        """Test kelvin minimum value (1500)."""
        color = ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=1500)
        assert color.kelvin == 1500

    def test_kelvin_max(self):
        """Test kelvin maximum value (9000)."""
        color = ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=9000)
        assert color.kelvin == 9000

    def test_kelvin_too_low(self):
        """Test kelvin < 1500 is rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 1500"):
            ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=1499)

    def test_kelvin_too_high(self):
        """Test kelvin > 9000 is rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 9000"):
            ColorHsbk(hue=0, saturation=0, brightness=0, kelvin=9001)
