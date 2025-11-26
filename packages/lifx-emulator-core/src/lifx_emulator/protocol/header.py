"""LIFX protocol header implementation.

The LIFX header is 36 bytes total, consisting of:
- Frame (8 bytes)
- Frame Address (16 bytes)
- Protocol Header (12 bytes)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import ClassVar

from lifx_emulator.constants import LIFX_PROTOCOL_VERSION

# Pre-compiled struct for entire 36-byte header (performance optimization)
_HEADER_STRUCT = struct.Struct("<HHI Q6sBB QHH")


@dataclass
class LifxHeader:
    """LIFX protocol header (36 bytes).

    Attributes:
        size: Total packet size in bytes (header + payload)
        protocol: Protocol number (must be 1024)
        source: Unique client identifier
        target: Device serial (8 bytes)
        tagged: True for broadcast discovery, False for targeted messages
        ack_required: Request acknowledgement from device
        res_required: Request response from device
        sequence: Sequence number for matching requests/responses
        pkt_type: Packet type identifier
    """

    HEADER_SIZE: ClassVar[int] = 36
    PROTOCOL_NUMBER: ClassVar[int] = 1024
    ORIGIN: ClassVar[int] = 0  # Always 0
    ADDRESSABLE: ClassVar[int] = 1  # Always 1

    size: int = 0
    protocol: int = LIFX_PROTOCOL_VERSION
    source: int = 0
    target: bytes = b"\x00" * 8  # Stored as 8 bytes internally
    tagged: bool = False
    ack_required: bool = False
    res_required: bool = False
    sequence: int = 0
    pkt_type: int = 0

    def __post_init__(self) -> None:
        """Validate header fields and auto-pad serial if needed."""
        # Ensure target is 8 bytes
        if len(self.target) < 8:
            self.target = self.target + b"\x00" * (8 - len(self.target))
        elif len(self.target) > 8:
            self.target = self.target[:8]

        # Validate protocol
        if self.protocol != self.PROTOCOL_NUMBER:
            raise ValueError(
                f"Invalid protocol number: {self.protocol}"
                f"(expected {self.PROTOCOL_NUMBER})"
            )

    def pack(self) -> bytes:
        """Pack header into 36 bytes using optimized single struct call.

        Returns:
            Packed header bytes
        """
        # Calculate flag fields
        frame_flags = (
            (self.protocol & 0xFFF)
            | (self.ADDRESSABLE << 12)
            | ((1 if self.tagged else 0) << 13)
            | ((self.ORIGIN & 0x3) << 14)
        )
        target_int = int.from_bytes(self.target[:8], byteorder="little")
        addr_flags = (1 if self.res_required else 0) | (
            (1 if self.ack_required else 0) << 1
        )

        # Pack entire header in single struct call (15-20% faster than 3 separate calls)
        return _HEADER_STRUCT.pack(
            self.size,  # H - Frame: size
            frame_flags,  # H - Frame: flags (protocol, tagged, addressable, origin)
            self.source,  # I - Frame: source
            target_int,  # Q - Frame Address: target (8 bytes as uint64)
            b"\x00" * 6,  # 6s - Frame Address: reserved (6 bytes)
            addr_flags,  # B - Frame Address: flags (ack_required, res_required)
            self.sequence,  # B - Frame Address: sequence
            0,  # Q - Protocol Header: reserved (8 bytes)
            self.pkt_type,  # H - Protocol Header: packet type
            0,  # H - Protocol Header: reserved (2 bytes)
        )

    @classmethod
    def unpack(cls, data: bytes) -> LifxHeader:
        """Unpack header from bytes.

        Args:
            data: Header bytes (at least 36 bytes)

        Returns:
            LifxHeader instance

        Raises:
            ValueError: If data is too short or invalid
        """
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Header data must be at least {cls.HEADER_SIZE} bytes")

        # Unpack Frame (8 bytes)
        size, protocol_field, source = struct.unpack("<HHI", data[0:8])

        # Extract protocol field components
        origin = (protocol_field >> 14) & 0b11
        tagged = bool((protocol_field >> 13) & 0b1)
        addressable = bool((protocol_field >> 12) & 0b1)
        protocol = protocol_field & 0xFFF

        # Validate origin and addressable
        if origin != cls.ORIGIN:
            raise ValueError(f"Invalid origin: {origin}")
        if not addressable:
            raise ValueError("Addressable bit must be set")

        # Unpack Frame Address (16 bytes)
        target_int, _reserved, flags, sequence = struct.unpack("<Q6sBB", data[8:24])
        target = target_int.to_bytes(8, byteorder="little")

        res_required = bool(flags & 0b1)
        ack_required = bool((flags >> 1) & 0b1)

        # Unpack Protocol Header (12 bytes)
        _reserved1, pkt_type, _reserved2 = struct.unpack("<QHH", data[24:36])

        return cls(
            size=size,
            protocol=protocol,
            source=source,
            target=target,
            tagged=tagged,
            ack_required=ack_required,
            res_required=res_required,
            sequence=sequence,
            pkt_type=pkt_type,
        )

    def __repr__(self) -> str:
        """String representation of header."""
        return (
            f"LifxHeader(size={self.size}, protocol={self.protocol}, "
            f"source={self.source}, target={self.target.hex()}, "
            f"tagged={self.tagged}, ack={self.ack_required}, "
            f"res={self.res_required}, seq={self.sequence}, pkt_type={self.pkt_type})"
        )
