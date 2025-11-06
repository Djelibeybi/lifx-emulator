"""Unit tests for protocol serializer module."""

import struct

import pytest

from lifx_emulator.protocol.serializer import (
    FieldSerializer,
    get_type_size,
    pack_array,
    pack_bytes,
    pack_reserved,
    pack_string,
    pack_value,
    unpack_array,
    unpack_bytes,
    unpack_string,
    unpack_value,
)


class TestTypeSize:
    """Test get_type_size function."""

    def test_get_type_size_uint8(self):
        assert get_type_size("uint8") == 1

    def test_get_type_size_uint16(self):
        assert get_type_size("uint16") == 2

    def test_get_type_size_uint32(self):
        assert get_type_size("uint32") == 4

    def test_get_type_size_uint64(self):
        assert get_type_size("uint64") == 8

    def test_get_type_size_float32(self):
        assert get_type_size("float32") == 4

    def test_get_type_size_bool(self):
        assert get_type_size("bool") == 1

    def test_get_type_size_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown type"):
            get_type_size("invalid_type")


class TestPackValue:
    """Test pack_value function."""

    def test_pack_uint8(self):
        result = pack_value(255, "uint8")
        assert result == b"\xff"
        assert len(result) == 1

    def test_pack_uint16(self):
        result = pack_value(65535, "uint16")
        assert result == b"\xff\xff"
        assert len(result) == 2

    def test_pack_uint32(self):
        result = pack_value(4294967295, "uint32")
        assert result == b"\xff\xff\xff\xff"
        assert len(result) == 4

    def test_pack_uint64(self):
        result = pack_value(18446744073709551615, "uint64")
        assert len(result) == 8

    def test_pack_int16_negative(self):
        result = pack_value(-100, "int16")
        assert len(result) == 2
        # Verify it can be unpacked correctly
        unpacked = struct.unpack("<h", result)[0]
        assert unpacked == -100

    def test_pack_float32(self):
        result = pack_value(3.14159, "float32")
        assert len(result) == 4
        unpacked = struct.unpack("<f", result)[0]
        assert abs(unpacked - 3.14159) < 0.0001

    def test_pack_bool_true(self):
        result = pack_value(True, "bool")
        assert result == b"\x01"

    def test_pack_bool_false(self):
        result = pack_value(False, "bool")
        assert result == b"\x00"

    def test_pack_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown type"):
            pack_value(42, "unknown")

    def test_pack_value_overflow(self):
        # uint8 can only hold 0-255
        with pytest.raises(struct.error):
            pack_value(256, "uint8")


class TestUnpackValue:
    """Test unpack_value function."""

    def test_unpack_uint8(self):
        value, offset = unpack_value(b"\xff", "uint8")
        assert value == 255
        assert offset == 1

    def test_unpack_uint16(self):
        value, offset = unpack_value(b"\xff\xff", "uint16")
        assert value == 65535
        assert offset == 2

    def test_unpack_uint32(self):
        value, offset = unpack_value(b"\xff\xff\xff\xff", "uint32")
        assert value == 4294967295
        assert offset == 4

    def test_unpack_with_offset(self):
        data = b"\x00\x00\xff\xff"
        value, offset = unpack_value(data, "uint16", offset=2)
        assert value == 65535
        assert offset == 4

    def test_unpack_float32(self):
        packed = struct.pack("<f", 3.14159)
        value, offset = unpack_value(packed, "float32")
        assert abs(value - 3.14159) < 0.0001
        assert offset == 4

    def test_unpack_bool(self):
        value, offset = unpack_value(b"\x01", "bool")
        assert value is True
        assert offset == 1

    def test_unpack_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            unpack_value(b"\xff", "uint16")

    def test_unpack_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown type"):
            unpack_value(b"\xff\xff", "unknown")


class TestPackArray:
    """Test pack_array function."""

    def test_pack_uint8_array(self):
        values = [0, 127, 255]
        result = pack_array(values, "uint8", 3)
        assert result == b"\x00\x7f\xff"
        assert len(result) == 3

    def test_pack_uint16_array(self):
        values = [0, 32768, 65535]
        result = pack_array(values, "uint16", 3)
        assert len(result) == 6

    def test_pack_array_wrong_count(self):
        with pytest.raises(ValueError, match="Expected 3 values, got 2"):
            pack_array([1, 2], "uint8", 3)

    def test_pack_empty_array(self):
        result = pack_array([], "uint8", 0)
        assert result == b""

    def test_pack_large_array(self):
        values = list(range(100))
        result = pack_array(values, "uint8", 100)
        assert len(result) == 100


class TestUnpackArray:
    """Test unpack_array function."""

    def test_unpack_uint8_array(self):
        data = b"\x00\x7f\xff"
        values, offset = unpack_array(data, "uint8", 3)
        assert values == [0, 127, 255]
        assert offset == 3

    def test_unpack_uint16_array(self):
        data = b"\x00\x00\x00\x80\xff\xff"
        values, offset = unpack_array(data, "uint16", 3)
        assert values == [0, 32768, 65535]
        assert offset == 6

    def test_unpack_array_with_offset(self):
        data = b"\xff\xff\x00\x7f\xff"
        values, offset = unpack_array(data, "uint8", 3, offset=2)
        assert values == [0, 127, 255]
        assert offset == 5

    def test_unpack_array_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            unpack_array(b"\xff", "uint16", 2)

    def test_unpack_empty_array(self):
        values, offset = unpack_array(b"", "uint8", 0)
        assert values == []
        assert offset == 0


class TestPackString:
    """Test pack_string function."""

    def test_pack_string_basic(self):
        result = pack_string("Hello", 10)
        assert result == b"Hello\x00\x00\x00\x00\x00"
        assert len(result) == 10

    def test_pack_string_exact_length(self):
        result = pack_string("Hello", 5)
        assert result == b"Hello"
        assert len(result) == 5

    def test_pack_string_truncation(self):
        result = pack_string("Hello World", 5)
        assert len(result) == 5
        # Should truncate to "Hello"
        assert result.rstrip(b"\x00").decode("utf-8") == "Hello"

    def test_pack_string_unicode(self):
        result = pack_string("Héllo", 10)
        assert len(result) == 10
        # é takes 2 bytes in UTF-8
        assert b"H\xc3\xa9llo" in result

    def test_pack_string_unicode_truncation_safe(self):
        # Test safe truncation at UTF-8 boundary
        # "Héllo" = H(1) + é(2) + l(1) + l(1) + o(1) = 6 bytes
        result = pack_string("Héllo", 4)
        assert len(result) == 4
        # Should truncate to "Hél" (4 bytes), "Hé" (3 bytes), or "H" (1 byte)
        # without breaking UTF-8
        decoded = result.rstrip(b"\x00").decode("utf-8")
        assert decoded in ["H", "Hé", "Hél"]  # Safe truncation

    def test_pack_empty_string(self):
        result = pack_string("", 5)
        assert result == b"\x00\x00\x00\x00\x00"


class TestUnpackString:
    """Test unpack_string function."""

    def test_unpack_string_basic(self):
        data = b"Hello\x00\x00\x00\x00\x00"
        value, offset = unpack_string(data, 10)
        assert value == "Hello"
        assert offset == 10

    def test_unpack_string_no_null(self):
        data = b"Hello"
        value, offset = unpack_string(data, 5)
        assert value == "Hello"
        assert offset == 5

    def test_unpack_string_with_offset(self):
        data = b"\xff\xff\xffHello\x00\x00\x00"
        value, offset = unpack_string(data, 8, offset=3)
        assert value == "Hello"
        assert offset == 11

    def test_unpack_string_unicode(self):
        data = b"H\xc3\xa9llo\x00\x00\x00\x00"
        value, offset = unpack_string(data, 10)
        assert value == "Héllo"

    def test_unpack_string_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            unpack_string(b"Hi", 10)

    def test_unpack_string_invalid_utf8(self):
        # Invalid UTF-8 should be replaced with replacement character
        data = b"\xff\xff\x00\x00\x00"
        value, offset = unpack_string(data, 5)
        assert offset == 5
        # Should handle gracefully with errors='replace'


class TestPackReserved:
    """Test pack_reserved function."""

    def test_pack_reserved_basic(self):
        result = pack_reserved(5)
        assert result == b"\x00\x00\x00\x00\x00"

    def test_pack_reserved_zero(self):
        result = pack_reserved(0)
        assert result == b""

    def test_pack_reserved_large(self):
        result = pack_reserved(100)
        assert len(result) == 100
        assert result == b"\x00" * 100


class TestPackBytes:
    """Test pack_bytes function."""

    def test_pack_bytes_basic(self):
        result = pack_bytes(b"Hello", 10)
        assert result == b"Hello\x00\x00\x00\x00\x00"
        assert len(result) == 10

    def test_pack_bytes_exact_length(self):
        result = pack_bytes(b"Hello", 5)
        assert result == b"Hello"

    def test_pack_bytes_truncation(self):
        result = pack_bytes(b"Hello World", 5)
        assert result == b"Hello"
        assert len(result) == 5

    def test_pack_bytes_empty(self):
        result = pack_bytes(b"", 5)
        assert result == b"\x00\x00\x00\x00\x00"


class TestUnpackBytes:
    """Test unpack_bytes function."""

    def test_unpack_bytes_basic(self):
        data = b"Hello\x00\x00\x00\x00\x00"
        value, offset = unpack_bytes(data, 10)
        assert value == b"Hello\x00\x00\x00\x00\x00"
        assert offset == 10

    def test_unpack_bytes_with_offset(self):
        data = b"\xff\xff\xffHello"
        value, offset = unpack_bytes(data, 5, offset=3)
        assert value == b"Hello"
        assert offset == 8

    def test_unpack_bytes_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            unpack_bytes(b"Hi", 10)


class TestFieldSerializer:
    """Test FieldSerializer class."""

    @pytest.fixture
    def serializer(self):
        """Create a serializer with test field definitions."""
        field_defs = {
            "HSBK": {
                "hue": "uint16",
                "saturation": "uint16",
                "brightness": "uint16",
                "kelvin": "uint16",
            },
            "Point": {"x": "float32", "y": "float32"},
        }
        return FieldSerializer(field_defs)

    def test_pack_field_hsbk(self, serializer):
        data = {"hue": 21845, "saturation": 65535, "brightness": 32768, "kelvin": 3500}
        result = serializer.pack_field(data, "HSBK")
        assert len(result) == 8  # 4 uint16s

    def test_pack_field_point(self, serializer):
        data = {"x": 1.5, "y": 2.5}
        result = serializer.pack_field(data, "Point")
        assert len(result) == 8  # 2 float32s

    def test_pack_field_unknown(self, serializer):
        with pytest.raises(ValueError, match="Unknown field"):
            serializer.pack_field({}, "Unknown")

    def test_pack_field_missing_attribute(self, serializer):
        data = {"hue": 21845}
        with pytest.raises(ValueError, match="Missing attribute"):
            serializer.pack_field(data, "HSBK")

    def test_unpack_field_hsbk(self, serializer):
        # Pack then unpack
        original = {
            "hue": 21845,
            "saturation": 65535,
            "brightness": 32768,
            "kelvin": 3500,
        }
        packed = serializer.pack_field(original, "HSBK")
        unpacked, offset = serializer.unpack_field(packed, "HSBK")
        assert unpacked == original
        assert offset == 8

    def test_unpack_field_with_offset(self, serializer):
        data = b"\xff\xff" + serializer.pack_field(
            {"hue": 100, "saturation": 200, "brightness": 300, "kelvin": 3500}, "HSBK"
        )
        unpacked, offset = serializer.unpack_field(data, "HSBK", offset=2)
        assert unpacked["hue"] == 100
        assert offset == 10

    def test_get_field_size_hsbk(self, serializer):
        size = serializer.get_field_size("HSBK")
        assert size == 8  # 4 * 2 bytes

    def test_get_field_size_point(self, serializer):
        size = serializer.get_field_size("Point")
        assert size == 8  # 2 * 4 bytes

    def test_get_field_size_unknown(self, serializer):
        with pytest.raises(ValueError, match="Unknown field"):
            serializer.get_field_size("Unknown")


class TestRoundTrip:
    """Test round-trip serialization (pack then unpack)."""

    @pytest.mark.parametrize(
        "value,type_name",
        [
            (0, "uint8"),
            (255, "uint8"),
            (0, "uint16"),
            (65535, "uint16"),
            (0, "uint32"),
            (4294967295, "uint32"),
            (-32768, "int16"),
            (32767, "int16"),
            (3.14159, "float32"),
            (True, "bool"),
            (False, "bool"),
        ],
    )
    def test_pack_unpack_roundtrip(self, value, type_name):
        """Test that pack followed by unpack returns original value."""
        packed = pack_value(value, type_name)
        unpacked, _ = unpack_value(packed, type_name)

        if type_name == "float32":
            assert abs(unpacked - value) < 0.0001
        else:
            assert unpacked == value

    def test_array_roundtrip(self):
        """Test array pack/unpack roundtrip."""
        original = [0, 100, 200, 255]
        packed = pack_array(original, "uint8", 4)
        unpacked, _ = unpack_array(packed, "uint8", 4)
        assert unpacked == original

    def test_string_roundtrip(self):
        """Test string pack/unpack roundtrip."""
        original = "Test String"
        packed = pack_string(original, 20)
        unpacked, _ = unpack_string(packed, 20)
        assert unpacked == original

    def test_bytes_roundtrip(self):
        """Test bytes pack/unpack roundtrip."""
        original = b"Binary\x00\xff\x01"
        packed = pack_bytes(original, 20)
        unpacked, _ = unpack_bytes(packed, 20)
        # Note: pack_bytes pads, so we need to check prefix
        assert unpacked.startswith(original)
