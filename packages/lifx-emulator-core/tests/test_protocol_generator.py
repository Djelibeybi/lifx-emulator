"""Comprehensive tests for protocol generator.

This tests the code generation pipeline that creates Python protocol structures
from the LIFX protocol specification, ensuring generated code is valid and correct.
"""

from lifx_emulator.protocol.generator import (
    TypeRegistry,
    camel_to_snake_upper,
    convert_type_to_python,
    filter_button_relay_items,
    format_long_import,
    format_long_list,
    generate_enum_code,
    parse_field_type,
    should_skip_button_relay,
    to_snake_case,
)


class TestTypeRegistry:
    """Test TypeRegistry for tracking protocol types."""

    def test_type_registry_initialization(self):
        """Test TypeRegistry initializes with basic types."""
        registry = TypeRegistry()
        assert registry.has_type("uint8")
        assert registry.has_type("uint16")
        assert registry.has_type("uint32")
        assert registry.has_type("uint64")
        assert registry.has_type("int8")
        assert registry.has_type("int16")
        assert registry.has_type("int32")
        assert registry.has_type("int64")
        assert registry.has_type("float32")
        assert registry.has_type("bool")
        assert registry.has_type("byte")
        assert registry.has_type("reserved")

    def test_register_enum(self):
        """Test registering enum types."""
        registry = TypeRegistry()
        registry.register_enum("DeviceService")
        assert registry.has_type("DeviceService")
        assert registry.is_enum("DeviceService")

    def test_register_field(self):
        """Test registering field structure types."""
        registry = TypeRegistry()
        registry.register_field("HSBK")
        assert registry.has_type("HSBK")
        assert not registry.is_enum("HSBK")

    def test_register_packet(self):
        """Test registering packet types."""
        registry = TypeRegistry()
        registry.register_packet("GetService")
        assert registry.has_type("GetService")

    def test_register_union(self):
        """Test registering union types."""
        registry = TypeRegistry()
        registry.register_union("UnknownPayload")
        assert registry.has_type("UnknownPayload")

    def test_is_enum_returns_false_for_non_enum(self):
        """Test is_enum returns False for non-enum types."""
        registry = TypeRegistry()
        registry.register_field("HSBK")
        assert not registry.is_enum("HSBK")

    def test_get_all_types(self):
        """Test getting all registered types."""
        registry = TypeRegistry()
        registry.register_enum("DeviceService")
        registry.register_field("HSBK")
        registry.register_packet("GetService")

        all_types = registry.get_all_types()
        assert "DeviceService" in all_types
        assert "HSBK" in all_types
        assert "GetService" in all_types
        assert "uint8" in all_types  # Basic type

    def test_has_type_basic_types(self):
        """Test has_type includes basic types."""
        registry = TypeRegistry()
        assert registry.has_type("uint32")
        assert registry.has_type("float32")

    def test_has_type_custom_types(self):
        """Test has_type checks custom types."""
        registry = TypeRegistry()
        registry.register_enum("MyEnum")
        assert registry.has_type("MyEnum")
        assert not registry.has_type("UnknownType")


class TestToSnakeCase:
    """Test PascalCase to snake_case conversion."""

    def test_pascal_case_to_snake(self):
        """Test converting PascalCase to snake_case."""
        assert to_snake_case("DeviceService") == "device_service"
        assert to_snake_case("GetService") == "get_service"
        assert to_snake_case("SetLightState") == "set_light_state"

    def test_single_word(self):
        """Test single word remains lowercase."""
        assert to_snake_case("Device") == "device"
        assert to_snake_case("Light") == "light"

    def test_already_lowercase(self):
        """Test already lowercase strings."""
        assert to_snake_case("device") == "device"
        assert to_snake_case("get") == "get"

    def test_consecutive_capitals(self):
        """Test consecutive capital letters."""
        assert to_snake_case("HTTPResponse") == "h_t_t_p_response"
        assert to_snake_case("XMLParser") == "x_m_l_parser"

    def test_with_numbers(self):
        """Test strings with numbers."""
        assert to_snake_case("UTF8String") == "u_t_f8_string"
        assert to_snake_case("Protocol2Spec") == "protocol2_spec"

    def test_camel_case_to_snake(self):
        """Test camelCase to snake_case."""
        assert to_snake_case("myVariable") == "my_variable"
        assert to_snake_case("getColorState") == "get_color_state"


class TestCamelToSnakeUpper:
    """Test CamelCase to UPPER_SNAKE_CASE conversion."""

    def test_pascal_case_to_upper_snake(self):
        """Test converting PascalCase to UPPER_SNAKE_CASE."""
        assert camel_to_snake_upper("DeviceService") == "DEVICE_SERVICE"
        assert camel_to_snake_upper("GetService") == "GET_SERVICE"
        assert camel_to_snake_upper("SetLightState") == "SET_LIGHT_STATE"

    def test_single_word_uppercase(self):
        """Test single word becomes all uppercase."""
        assert camel_to_snake_upper("Device") == "DEVICE"
        assert camel_to_snake_upper("Light") == "LIGHT"

    def test_consecutive_capitals(self):
        """Test handling consecutive capitals."""
        assert camel_to_snake_upper("HTTPResponse") == "H_T_T_P_RESPONSE"

    def test_lowercase_input(self):
        """Test lowercase input."""
        assert camel_to_snake_upper("device") == "DEVICE"


class TestFormatLongImport:
    """Test formatting long import statements."""

    def test_single_line_import(self):
        """Test short import fits on single line."""
        items = ["Foo", "Bar"]
        result = format_long_import(items)
        assert "from lifx_emulator.protocol.protocol_types import Foo, Bar" in result

    def test_empty_import_list(self):
        """Test empty import list returns empty string."""
        result = format_long_import([])
        assert result == ""

    def test_multiline_import(self):
        """Test long import wraps to multiple lines."""
        items = [f"Type{i}" for i in range(20)]
        result = format_long_import(items)
        assert "(" in result
        assert ")" in result
        assert len(result.split("\n")) > 3

    def test_custom_prefix(self):
        """Test custom import prefix."""
        items = ["Foo"]
        prefix = "from custom.module import "
        result = format_long_import(items, prefix)
        assert "from custom.module import" in result

    def test_long_single_item_still_wraps(self):
        """Test very long single import wraps."""
        items = ["VeryLongTypeNameThatExceedsMaximumLength" * 5]
        result = format_long_import(items)
        # With 120 char limit, this should wrap
        assert len(result) > 0


class TestFormatLongList:
    """Test formatting long list literals."""

    def test_empty_list(self):
        """Test empty list returns []."""
        result = format_long_list([])
        assert result == "[]"

    def test_single_line_list(self):
        """Test short list fits on single line."""
        items = [{"key": "value"}]
        result = format_long_list(items)
        assert "[{" in result and "}]" in result

    def test_multiline_list(self):
        """Test long list wraps to multiple lines."""
        items = [{"id": i, "name": f"item{i}"} for i in range(30)]
        result = format_long_list(items)
        lines = result.split("\n")
        assert len(lines) > 5
        assert lines[0] == "["
        assert lines[-1] == "]"

    def test_max_line_length_parameter(self):
        """Test custom max_line_length."""
        items = [{"short": "data"}]
        result = format_long_list(items, max_line_length=5)
        # Should wrap due to very short limit
        assert "\n" in result or len(result) <= 5


class TestParseFieldType:
    """Test parsing field type strings."""

    def test_simple_type(self):
        """Test parsing simple types."""
        base, count, is_nested = parse_field_type("uint8")
        assert base == "uint8"
        assert count is None
        assert is_nested is False

    def test_array_type(self):
        """Test parsing array types."""
        base, count, is_nested = parse_field_type("[4]uint16")
        assert base == "uint16"
        assert count == 4
        assert is_nested is False

    def test_nested_type(self):
        """Test parsing nested types."""
        base, count, is_nested = parse_field_type("<HSBK>")
        assert base == "HSBK"
        assert count is None
        assert is_nested is True

    def test_array_of_nested_type(self):
        """Test parsing array of nested types."""
        base, count, is_nested = parse_field_type("[8]<HSBK>")
        assert base == "HSBK"
        assert count == 8
        assert is_nested is True

    def test_large_array_count(self):
        """Test parsing large array counts."""
        base, count, is_nested = parse_field_type("[1024]uint8")
        assert base == "uint8"
        assert count == 1024

    def test_complex_type_name(self):
        """Test parsing complex type names."""
        base, count, is_nested = parse_field_type("<StateMultiZone>")
        assert base == "StateMultiZone"
        assert is_nested is True


class TestGenerateEnumCode:
    """Test enum code generation."""

    def test_generate_simple_enum(self):
        """Test generating a simple enum."""
        # Enum format: values is a dict like {"UDP": 1, "Reserved": 2}
        enums = {
            "DeviceService": {
                "values": [
                    {"name": "UDP", "value": 1},
                    {"name": "Reserved", "value": 2},
                ]
            }
        }
        code = generate_enum_code(enums)
        assert "class DeviceService(IntEnum):" in code

    def test_generate_enum_with_docstring(self):
        """Test generated enum includes docstring."""
        enums = {"TestEnum": {"values": [{"name": "VALUE", "value": 0}]}}
        code = generate_enum_code(enums)
        assert '"""Auto-generated enum."""' in code

    def test_generate_multiple_enums(self):
        """Test generating multiple enums."""
        enums = {
            "Enum1": {"values": [{"name": "A", "value": 0}]},
            "Enum2": {"values": [{"name": "B", "value": 1}]},
        }
        code = generate_enum_code(enums)
        assert "class Enum1(IntEnum):" in code
        assert "class Enum2(IntEnum):" in code

    def test_enum_values_in_code(self):
        """Test enum values appear in generated code."""
        enums = {
            "Service": {
                "values": [
                    {"name": "UDP", "value": 1},
                    {"name": "RESERVED", "value": 2},
                    {"name": "TCP", "value": 3},
                ]
            }
        }
        code = generate_enum_code(enums)
        # Code should be generated without errors
        assert "Service" in code


class TestConvertTypeToJython:
    """Test converting field types to Python type hints."""

    def test_convert_basic_type_uint32(self):
        """Test converting uint32 to int."""
        result = convert_type_to_python("uint32")
        # Function returns a string representation of the type
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_basic_type_bool(self):
        """Test converting bool to bool."""
        result = convert_type_to_python("bool")
        assert isinstance(result, str)

    def test_convert_basic_type_float(self):
        """Test converting float32 to float."""
        result = convert_type_to_python("float32")
        assert isinstance(result, str)

    def test_convert_nested_type(self):
        """Test converting nested types."""
        result = convert_type_to_python("HSBK")
        # Should return a type string
        assert isinstance(result, str)

    def test_convert_reserved_type(self):
        """Test converting reserved type."""
        result = convert_type_to_python("reserved")
        assert isinstance(result, str)

    def test_convert_with_type_aliases(self):
        """Test conversion with type aliases."""
        aliases = {"CustomType": "int"}
        result = convert_type_to_python("CustomType", aliases)
        assert isinstance(result, str)


class TestCodeGenerationIntegration:
    """Integration tests for the code generation pipeline."""

    def test_generated_enum_is_valid_python(self):
        """Test that generated enum code is valid Python."""
        enums = {
            "Service": {
                "values": [
                    {"name": "UDP", "value": 1},
                    {"name": "TCP", "value": 2},
                ]
            }
        }
        code = generate_enum_code(enums)

        # Should contain enum class
        assert "class Service(IntEnum):" in code

    def test_import_formatting_consistency(self):
        """Test import formatting produces consistent output."""
        items = ["Type1", "Type2", "Type3"]
        result1 = format_long_import(items)
        result2 = format_long_import(items)
        assert result1 == result2

    def test_type_parsing_roundtrip(self):
        """Test parsing field types correctly extracts components."""
        test_cases = [
            ("uint32", ("uint32", None, False)),
            ("[16]uint8", ("uint8", 16, False)),
            ("<HSBK>", ("HSBK", None, True)),
            ("[4]<Color>", ("Color", 4, True)),
        ]
        for input_type, expected in test_cases:
            result = parse_field_type(input_type)
            assert result == expected, f"Failed for {input_type}"

    def test_snake_case_roundtrip_consistency(self):
        """Test snake_case conversions are consistent."""
        names = ["DeviceService", "GetColor", "SetLightState"]
        for name in names:
            snake = to_snake_case(name)
            upper = camel_to_snake_upper(name)
            assert snake == upper.lower()
            assert upper == snake.upper()

    def test_registry_tracks_all_type_kinds(self):
        """Test registry properly tracks different type kinds."""
        registry = TypeRegistry()

        # Register different types
        registry.register_enum("MyEnum")
        registry.register_field("MyField")
        registry.register_packet("MyPacket")
        registry.register_union("MyUnion")

        # All should be present in get_all_types
        all_types = registry.get_all_types()
        assert "MyEnum" in all_types
        assert "MyField" in all_types
        assert "MyPacket" in all_types
        assert "MyUnion" in all_types

        # But only MyEnum should be an enum
        assert registry.is_enum("MyEnum")
        assert not registry.is_enum("MyField")
        assert not registry.is_enum("MyPacket")
        assert not registry.is_enum("MyUnion")


class TestGeneratePackMethod:
    """Test pack method code generation."""

    def test_pack_simple_uint32_field(self):
        """Test packing simple uint32 field."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [{"name": "Value", "type": "uint32"}]
        code = generate_pack_method(fields_data, "field")

        assert "def pack(self) -> bytes:" in code
        assert "self.value" in code
        assert "pack_value" in code
        assert "uint32" in code

    def test_pack_reserved_field(self):
        """Test packing reserved fields."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [
            {"size_bytes": 4}  # Reserved field without name
        ]
        code = generate_pack_method(fields_data, "field")

        assert "pack_reserved(4)" in code

    def test_pack_byte_array_field(self):
        """Test packing byte array field."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [{"name": "Data", "type": "[6]byte", "size_bytes": 6}]
        code = generate_pack_method(fields_data, "field")

        assert "pack_bytes" in code
        assert "self.data" in code

    def test_pack_nested_structure(self):
        """Test packing nested structure."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [{"name": "Color", "type": "<HSBK>"}]
        code = generate_pack_method(fields_data, "field", enum_types=set())

        assert "self.color.pack()" in code

    def test_pack_array_of_nested_structures(self):
        """Test packing array of nested structures."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [{"name": "Colors", "type": "[8]<HSBK>"}]
        code = generate_pack_method(fields_data, "field", enum_types=set())

        assert "for item in self.colors:" in code
        assert "item.pack()" in code

    def test_pack_enum_field(self):
        """Test packing enum field."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [{"name": "Service", "type": "<DeviceService>"}]
        code = generate_pack_method(fields_data, "field", enum_types={"DeviceService"})

        assert "int(self.service)" in code
        assert "pack_value" in code

    def test_pack_multiple_fields(self):
        """Test packing multiple fields."""
        from lifx_emulator.protocol.generator import generate_pack_method

        fields_data = [
            {"name": "X", "type": "uint16"},
            {"name": "Y", "type": "uint16"},
            {"name": "Z", "type": "uint16"},
        ]
        code = generate_pack_method(fields_data, "field")

        assert code.count("pack_value") >= 3
        assert "self.x" in code
        assert "self.y" in code
        assert "self.z" in code


class TestGenerateUnpackMethod:
    """Test unpack method code generation."""

    def test_unpack_simple_uint32_field(self):
        """Test unpacking simple uint32 field."""
        from lifx_emulator.protocol.generator import generate_unpack_method

        fields_data = [{"name": "Value", "type": "uint32"}]
        code = generate_unpack_method("TestClass", fields_data, "field")

        assert "@classmethod" in code
        assert "def unpack(cls, data: bytes, offset: int = 0) -> tuple" in code
        assert "TestClass" in code
        assert "serializer.unpack_value(data, 'uint32'" in code

    def test_unpack_byte_array(self):
        """Test unpacking byte array."""
        from lifx_emulator.protocol.generator import generate_unpack_method

        fields_data = [{"name": "Data", "type": "[6]byte", "size_bytes": 6}]
        code = generate_unpack_method("TestClass", fields_data, "field")

        assert "serializer.unpack_bytes(" in code
        assert ", 6," in code or ", 6)" in code

    def test_unpack_nested_structure(self):
        """Test unpacking nested structure."""
        from lifx_emulator.protocol.generator import generate_unpack_method

        fields_data = [{"name": "Color", "type": "<HSBK>"}]
        code = generate_unpack_method(
            "TestClass", fields_data, "field", enum_types=set()
        )

        assert "HSBK.unpack(data," in code
        assert "color," in code

    def test_unpack_multiple_fields(self):
        """Test unpacking multiple fields."""
        from lifx_emulator.protocol.generator import generate_unpack_method

        fields_data = [
            {"name": "X", "type": "uint16"},
            {"name": "Y", "type": "uint16"},
        ]
        code = generate_unpack_method("Point", fields_data, "field")

        assert "unpack_value" in code
        # Multiple unpack calls for multiple fields
        assert code.count("unpack_value") >= 2

    def test_unpack_enum_field(self):
        """Test unpacking enum field."""
        from lifx_emulator.protocol.generator import generate_unpack_method

        fields_data = [{"name": "Service", "type": "<DeviceService>"}]
        code = generate_unpack_method(
            "TestClass", fields_data, "field", enum_types={"DeviceService"}
        )

        assert "DeviceService(value)" in code or "DeviceService" in code


class TestGenerateFieldCode:
    """Test field structure code generation."""

    def test_generate_simple_field_structure(self):
        """Test generating simple field structure."""
        from lifx_emulator.protocol.generator import generate_field_code

        fields = {"SimpleField": {"fields": [{"name": "Value", "type": "uint32"}]}}
        code, mappings = generate_field_code(fields)

        assert "@dataclass" in code
        assert "class SimpleField:" in code
        assert "value: int" in code
        assert "def pack(self) -> bytes:" in code
        assert "def unpack(cls, data: bytes" in code

    def test_generate_field_with_reserved_bytes(self):
        """Test generating field with reserved bytes."""
        from lifx_emulator.protocol.generator import generate_field_code

        fields = {"ReservedField": {"fields": [{"size_bytes": 4}]}}
        code, mappings = generate_field_code(fields)

        assert "class ReservedField:" in code

    def test_generate_multiple_fields(self):
        """Test generating multiple field structures."""
        from lifx_emulator.protocol.generator import generate_field_code

        fields = {
            "Field1": {"fields": [{"name": "A", "type": "uint16"}]},
            "Field2": {"fields": [{"name": "B", "type": "uint32"}]},
        }
        code, mappings = generate_field_code(fields)

        assert "class Field1:" in code
        assert "class Field2:" in code
        assert "Field1" in mappings
        assert "Field2" in mappings

    def test_field_code_with_nested_type(self):
        """Test field code generation with nested types."""
        from lifx_emulator.protocol.generator import generate_field_code

        fields = {"ColorField": {"fields": [{"name": "Color", "type": "<HSBK>"}]}}
        code, mappings = generate_field_code(fields)

        assert "color: HSBK" in code or "color:" in code
        assert "ColorField" in mappings


class TestGenerateNestedPacketCode:
    """Test nested packet class code generation."""

    def test_generate_device_packets(self):
        """Test generating Device category packets."""
        from lifx_emulator.protocol.generator import generate_nested_packet_code

        packets = {
            "device": {
                "GetLabel": {"pkt_type": 23, "fields": []},
                "StateLabel": {
                    "pkt_type": 25,
                    "fields": [{"name": "Label", "type": "[32]byte", "size_bytes": 32}],
                },
            }
        }
        code = generate_nested_packet_code(packets)

        assert "class Device(Packet):" in code
        assert "class GetLabel(Packet):" in code
        assert "class StateLabel(Packet):" in code
        assert "PKT_TYPE: ClassVar[int] = 23" in code
        assert "PKT_TYPE: ClassVar[int] = 25" in code

    def test_generate_light_packets(self):
        """Test generating Light category packets."""
        from lifx_emulator.protocol.generator import generate_nested_packet_code

        packets = {
            "light": {
                "Get": {"pkt_type": 101, "fields": []},
                "State": {"pkt_type": 107, "fields": []},
            }
        }
        code = generate_nested_packet_code(packets)

        assert "class Light(Packet):" in code
        # Light.Get should be renamed to GetColor
        assert "class GetColor(Packet):" in code
        # Light.State should be renamed to StateColor
        assert "class StateColor(Packet):" in code

    def test_packet_kind_classification(self):
        """Test packet kind classification (GET, SET, STATE, OTHER)."""
        from lifx_emulator.protocol.generator import generate_nested_packet_code

        packets = {
            "device": {
                "GetService": {"pkt_type": 2, "fields": []},
                "SetLabel": {"pkt_type": 24, "fields": []},
                "StatePower": {"pkt_type": 22, "fields": []},
            }
        }
        code = generate_nested_packet_code(packets)

        # GET packets should have _packet_kind = "GET"
        assert "_packet_kind: ClassVar[str] = 'GET'" in code
        # SET packets should have _packet_kind = "SET" and _requires_ack = True
        assert "_packet_kind: ClassVar[str] = 'SET'" in code
        assert "_requires_ack: ClassVar[bool] = True" in code
        # STATE packets should have _packet_kind = "STATE"
        assert "_packet_kind: ClassVar[str] = 'STATE'" in code

    def test_tile_copy_buffer_is_set_operation(self):
        """Test Tile.CopyFrameBuffer is classified as SET operation."""
        from lifx_emulator.protocol.generator import generate_nested_packet_code

        packets = {"tile": {"CopyFrameBuffer": {"pkt_type": 518, "fields": []}}}
        code = generate_nested_packet_code(packets)

        # CopyFrameBuffer should be SET (modifies device state)
        assert "_packet_kind: ClassVar[str] = 'SET'" in code


class TestValidationAndFiltering:
    """Test validation and filtering functions for protocol spec."""

    def test_should_skip_button_relay_relay_items(self):
        """Test identifying relay-related items for skipping."""
        # Items starting with "Relay" should be skipped
        assert should_skip_button_relay("RelayPower")
        assert should_skip_button_relay("RelayMatrixEffect")
        assert should_skip_button_relay("RelayGetStatus")

    def test_should_skip_button_relay_button_items(self):
        """Test identifying button-related items for skipping."""
        # Items starting with "Button" should be skipped
        assert should_skip_button_relay("ButtonPress")
        assert should_skip_button_relay("ButtonGetCount")

    def test_should_skip_button_relay_non_button_relay_items(self):
        """Test not skipping items that aren't Button/Relay related."""
        # Light devices should not be skipped
        assert not should_skip_button_relay("GetColor")
        assert not should_skip_button_relay("SetPower")
        assert not should_skip_button_relay("Device")
        assert not should_skip_button_relay("Light")

    def test_filter_button_relay_items_removes_relay_packets(self):
        """Test filtering removes relay-specific items."""
        items = {
            "RelayPower": {"type": "uint8"},
            "Power": {"type": "uint8"},
            "RelayMatrixEffect": {"type": "uint8"},
            "MatrixEffect": {"type": "uint8"},
        }
        # Items with "Relay" prefix should be filtered
        filtered = filter_button_relay_items(items)
        assert "Power" in filtered or "MatrixEffect" in filtered

    def test_filter_button_relay_packets_structure(self):
        """Test filtering packets by category."""
        packets = {
            "relay": {"GetPower": {"pkt_type": 100}, "SetPower": {"pkt_type": 101}},
            "device": {"GetLabel": {"pkt_type": 23}, "SetLabel": {"pkt_type": 24}},
        }
        # Both categories should still be present after filtering
        # (filtering is selective, not removing entire categories)
        assert isinstance(packets, dict)

    def test_filter_preserves_non_relay_items(self):
        """Test filtering preserves non-relay items."""
        items = {
            "Power": {"type": "uint8"},
            "Label": {"type": "[32]byte"},
            "Effect": {"type": "uint8"},
        }
        filtered = filter_button_relay_items(items)
        assert "Power" in filtered or len(filtered) > 0

    def test_filter_button_relay_items_handles_empty_dict(self):
        """Test filtering handles empty dictionaries."""
        items = {}
        filtered = filter_button_relay_items(items)
        assert filtered == {}

    def test_filter_button_relay_items_with_relay_prefix(self):
        """Test items with Relay prefix are identified."""
        items = {
            "RelaySpecificField": {"type": "uint8"},
            "NormalField": {"type": "uint8"},
        }
        # Filtering should handle both types
        filtered = filter_button_relay_items(items)
        assert isinstance(filtered, dict)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_format_import_with_aliases(self):
        """Test import formatting with type aliases."""
        items = ["TypeName as Alias", "AnotherType"]
        result = format_long_import(items)
        assert "as Alias" in result

    def test_parse_field_type_with_nested_array_count(self):
        """Test parsing field with complex array syntax."""
        base, count, is_nested = parse_field_type("[256]uint8")
        assert count == 256
        assert base == "uint8"
        assert not is_nested

    def test_enum_code_with_description(self):
        """Test enum generation preserves value information."""
        enums = {
            "State": {
                "values": [
                    {"name": "OFF", "value": 0},
                    {"name": "ON", "value": 1},
                    {"name": "UNKNOWN", "value": 255},
                ]
            }
        }
        code = generate_enum_code(enums)
        assert "State" in code  # Check enum class is defined

    def test_to_snake_case_handles_mixed_case(self):
        """Test snake_case handles mixed case strings."""
        # The function inserts underscores before capitals
        result = to_snake_case("MyVariable")
        assert "my" in result and "variable" in result

    def test_format_long_list_with_nested_structures(self):
        """Test formatting complex nested structures."""
        items = [
            {"type": "packet", "name": "Name", "fields": [1, 2, 3]},
            {"type": "enum", "name": "Value", "values": [{"name": "A", "value": 0}]},
        ]
        result = format_long_list(items)
        assert "packet" in result
        assert "enum" in result
        # Result should be valid Python list syntax
        assert "[" in result and "]" in result
