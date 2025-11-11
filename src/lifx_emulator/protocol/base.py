"""Base packet class for LIFX protocol.

Provides generic pack/unpack functionality for all packet types.

Performance optimizations:
- Pre-compiled regex patterns for field name conversion
- Cached field type parsing results
- Pre-computed field info for faster unpacking
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

# Performance optimization: Pre-compiled regex patterns
_CAMEL_TO_SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")
_ARRAY_TYPE_PATTERN = re.compile(r"\[(\d+)\](.+)")

# Performance optimization: Field type parsing cache
_FIELD_TYPE_CACHE: dict[str, tuple[str, int | None, bool]] = {}

# Performance optimization: Field name conversion cache (per-class)
_FIELD_NAME_CACHE: dict[type, dict[str, str]] = {}


@dataclass
class Packet:
    """Base class for all LIFX protocol packets.

    Each packet subclass defines:
    - PKT_TYPE: ClassVar[int] - The packet type number
    - _fields: ClassVar[list[dict]] - Field metadata from protocol.yml
    - Actual field attributes as dataclass fields
    """

    PKT_TYPE: ClassVar[int]
    _fields: ClassVar[list[dict[str, Any]]]
    _field_info: ClassVar[list[tuple[str, str, int]] | None] = None

    def pack(self) -> bytes:
        """Pack packet to bytes using field metadata.

        Returns:
            Packed bytes ready to send in a LIFX message payload
        """
        from lifx_emulator.protocol import serializer

        result = b""

        for field_item in self._fields:
            # Handle reserved fields (no name)
            if "name" not in field_item:
                size_bytes = field_item.get("size_bytes", 0)
                result += serializer.pack_reserved(size_bytes)
                continue

            # Get field value from instance
            field_name = self._protocol_to_python_name(field_item["name"])
            value = getattr(self, field_name)

            # Pack based on type
            field_type = field_item["type"]
            size_bytes = field_item.get("size_bytes", 0)
            result += self._pack_field_value(value, field_type, size_bytes)

        return result

    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> Packet:
        """Unpack packet from bytes using field metadata.

        Args:
            data: Bytes to unpack from
            offset: Offset in bytes to start unpacking

        Returns:
            Packet instance
        """
        packet, _ = cls._unpack_internal(data, offset)
        return packet

    @classmethod
    def _compute_field_info(cls) -> list[tuple[str, str, int]]:
        """Pre-compute parsed field metadata for faster unpacking.

        This optimization caches the parsing of field metadata to avoid
        repeated dictionary lookups and name conversions during unpacking.

        Returns:
            List of tuples: (field_name, field_type, size_bytes)
            Reserved fields have empty string as field_name
        """
        info: list[tuple[str, str, int]] = []

        for field_item in cls._fields:
            size_bytes = field_item.get("size_bytes", 0)

            # Handle reserved fields (no name)
            if "name" not in field_item:
                info.append(("", "", size_bytes))
                continue

            # Regular field
            field_name = cls._protocol_to_python_name(field_item["name"])
            field_type = field_item["type"]
            info.append((field_name, field_type, size_bytes))

        return info

    @classmethod
    def _unpack_internal(cls, data: bytes, offset: int) -> tuple[Packet, int]:
        """Internal method for unpacking packets with offset tracking.

        This method handles the recursion needed for nested structures.

        Args:
            data: Bytes to unpack from
            offset: Offset in bytes to start unpacking

        Returns:
            Tuple of (packet_instance, new_offset)
        """
        # Pre-compute field info on first use (lazy initialization)
        if cls._field_info is None:
            cls._field_info = cls._compute_field_info()

        current_offset = offset
        field_values: dict[str, Any] = {}

        for field_name, field_type, size_bytes in cls._field_info:
            # Handle reserved fields (empty name)
            if not field_name:
                current_offset += size_bytes
                continue

            # Unpack field value
            value, current_offset = cls._unpack_field_value(
                data, field_type, size_bytes, current_offset, field_name
            )
            field_values[field_name] = value

        return cls(**field_values), current_offset

    @classmethod
    def _protocol_to_python_name(cls, name: str) -> str:
        """Convert protocol name (PascalCase) to Python name (snake_case).

        Performance optimized with caching and pre-compiled regex.
        """
        # Check class-specific cache first
        if cls not in _FIELD_NAME_CACHE:
            _FIELD_NAME_CACHE[cls] = {}

        cache = _FIELD_NAME_CACHE[cls]

        if name not in cache:
            # Convert using pre-compiled pattern
            snake = _CAMEL_TO_SNAKE_PATTERN.sub("_", name)
            cache[name] = snake.lower()

        return cache[name]

    def _pack_field_value(self, value: Any, field_type: str, size_bytes: int) -> bytes:
        """Pack a single field value based on its type."""
        from lifx_emulator.protocol import serializer

        # Parse field type
        base_type, array_count, is_nested = self._parse_field_type(field_type)

        # Check if it's an enum (Button/Relay enums excluded)
        enum_types = {
            "DeviceService",
            "LightLastHevCycleResult",
            "LightWaveform",
            "MultiZoneApplicationRequest",
            "MultiZoneEffectType",
            "MultiZoneExtendedApplicationRequest",
        }
        is_enum = is_nested and base_type in enum_types

        # Handle different field types
        if array_count:
            if is_enum:
                # Array of enums
                result = b""
                for item in value:
                    result += serializer.pack_value(int(item), "uint8")
                return result
            elif is_nested:
                # Array of nested structures
                result = b""
                for item in value:
                    result += item.pack()
                return result
            elif base_type in ("uint8", "byte"):
                # Check if value is a string (Label fields)
                if isinstance(value, str):
                    return serializer.pack_string(value, size_bytes)
                # Regular byte array
                return serializer.pack_bytes(value, size_bytes)
            else:
                # Array of primitives
                return serializer.pack_array(value, base_type, array_count)
        elif is_enum:
            # Single enum
            return serializer.pack_value(int(value), "uint8")
        elif is_nested:
            # Nested structure
            return value.pack()
        else:
            # Primitive type
            return serializer.pack_value(value, base_type)

    @classmethod
    def _unpack_array_field(
        cls,
        data: bytes,
        base_type: str,
        array_count: int,
        size_bytes: int,
        offset: int,
        field_name: str,
        is_nested: bool,
        enum_types: dict,
    ) -> tuple[Any, int]:
        """Unpack an array field value."""
        from lifx_emulator.protocol import serializer

        is_enum = is_nested and base_type in enum_types

        if is_enum:
            result = []
            current_offset = offset
            enum_class = enum_types[base_type]
            for _ in range(array_count):
                item_raw, current_offset = serializer.unpack_value(
                    data, "uint8", current_offset
                )
                result.append(enum_class(item_raw))
            return result, current_offset
        elif is_nested:
            from lifx_emulator.protocol import protocol_types

            struct_class = getattr(protocol_types, base_type)
            result = []
            current_offset = offset
            for _ in range(array_count):
                if issubclass(struct_class, cls):
                    item, current_offset = struct_class._unpack_internal(
                        data, current_offset
                    )
                else:
                    item_result = struct_class.unpack(data, current_offset)
                    item, current_offset = item_result  # type: ignore[misc]
                result.append(item)
            return result, current_offset
        elif base_type in ("uint8", "byte"):
            if field_name.lower().endswith("label"):
                return serializer.unpack_string(data, size_bytes, offset)
            return serializer.unpack_bytes(data, size_bytes, offset)
        else:
            return serializer.unpack_array(data, base_type, array_count, offset)

    @classmethod
    def _unpack_single_field(
        cls,
        data: bytes,
        base_type: str,
        offset: int,
        is_nested: bool,
        enum_types: dict,
    ) -> tuple[Any, int]:
        """Unpack a non-array field value."""
        from lifx_emulator.protocol import serializer

        is_enum = is_nested and base_type in enum_types

        if is_enum:
            enum_class = enum_types[base_type]
            value_raw, new_offset = serializer.unpack_value(data, "uint8", offset)
            return enum_class(value_raw), new_offset
        elif is_nested:
            from lifx_emulator.protocol import protocol_types

            struct_class = getattr(protocol_types, base_type)
            if issubclass(struct_class, cls):
                return struct_class._unpack_internal(data, offset)
            else:
                return struct_class.unpack(data, offset)
        else:
            return serializer.unpack_value(data, base_type, offset)

    @classmethod
    def _unpack_field_value(
        cls,
        data: bytes,
        field_type: str,
        size_bytes: int,
        offset: int,
        field_name: str = "",
    ) -> tuple[Any, int]:
        """Unpack a single field value based on its type.

        Args:
            data: Bytes to unpack from
            field_type: Protocol field type string
            size_bytes: Size in bytes
            offset: Offset in bytes
            field_name: Optional field name for semantic type detection

        Returns:
            Tuple of (value, new_offset)
        """
        from lifx_emulator.protocol.protocol_types import (
            DeviceService,
            LightLastHevCycleResult,
            LightWaveform,
            MultiZoneApplicationRequest,
            MultiZoneEffectType,
            MultiZoneExtendedApplicationRequest,
        )

        base_type, array_count, is_nested = cls._parse_field_type(field_type)

        enum_types = {
            "DeviceService": DeviceService,
            "LightLastHevCycleResult": LightLastHevCycleResult,
            "LightWaveform": LightWaveform,
            "MultiZoneApplicationRequest": MultiZoneApplicationRequest,
            "MultiZoneEffectType": MultiZoneEffectType,
            "MultiZoneExtendedApplicationRequest": MultiZoneExtendedApplicationRequest,
        }

        if array_count:
            return cls._unpack_array_field(
                data,
                base_type,
                array_count,
                size_bytes,
                offset,
                field_name,
                is_nested,
                enum_types,
            )
        else:
            return cls._unpack_single_field(
                data, base_type, offset, is_nested, enum_types
            )

    @staticmethod
    def _parse_field_type(field_type: str) -> tuple[str, int | None, bool]:
        """Parse a field type string with caching.

        Performance optimized with global cache and pre-compiled regex.

        Args:
            field_type: Field type (e.g., 'uint16', '[32]uint8', '<HSBK>')

        Returns:
            Tuple of (base_type, array_count, is_nested)
        """
        # Check cache first
        if field_type in _FIELD_TYPE_CACHE:
            return _FIELD_TYPE_CACHE[field_type]

        # Parse type
        # Check for array: [N]type
        array_match = _ARRAY_TYPE_PATTERN.match(field_type)
        if array_match:
            count = int(array_match.group(1))
            inner_type = array_match.group(2)
            # Check if inner type is nested
            if inner_type.startswith("<") and inner_type.endswith(">"):
                result = (inner_type[1:-1], count, True)
            else:
                result = (inner_type, count, False)
        # Check for nested structure: <Type>
        elif field_type.startswith("<") and field_type.endswith(">"):
            result = (field_type[1:-1], None, True)
        else:
            # Simple type
            result = (field_type, None, False)

        # Cache the result
        _FIELD_TYPE_CACHE[field_type] = result
        return result
