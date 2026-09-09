"""Tests for the LifxHeader wire-format module.

These tests lock in the pre-Thread-phase byte output of LifxHeader.pack()
and LifxHeader.unpack() before any change to protocol/header.py. The fixture
below is a plain round-trip header (no device involved) captured from an
unmodified tree, so a later diff can prove the wire bytes did not move.
"""

import pytest
from lifx_emulator.protocol.header import LifxHeader

# Captured from an unmodified tree at commit e610c08e8ea9eab6e2b37cb097b731542ff8d717,
# via: LifxHeader(source=99, target=bytes.fromhex("d073d5000001") + b"\x00\x00",
#                 sequence=7, pkt_type=999, res_required=True, ack_required=True,
#                 tagged=True).pack()
_HEADER_FIXTURE_BEFORE = bytes.fromhex(
    "0000003463000000d073d5000001000000000000000003070000000000000000e7030000"
)


class TestHeaderByteFixture:
    """Pre-change byte fixture: plain LifxHeader pack/unpack round trip."""

    def _build_fixture_header(self) -> LifxHeader:
        """Build the header that produced _HEADER_FIXTURE_BEFORE."""
        return LifxHeader(
            source=99,
            target=bytes.fromhex("d073d5000001") + b"\x00\x00",
            sequence=7,
            pkt_type=999,
            res_required=True,
            ack_required=True,
            tagged=True,
        )

    def test_pack_matches_pre_phase_fixture(self):
        """Reconstructing the fixture header packs to the identical bytes."""
        header = self._build_fixture_header()
        assert header.pack() == _HEADER_FIXTURE_BEFORE

    def test_unpack_matches_pre_phase_fixture(self):
        """Unpacking the fixture bytes reconstructs the identical header."""
        header = self._build_fixture_header()
        assert LifxHeader.unpack(_HEADER_FIXTURE_BEFORE) == header

    def test_reserved_bits_of_byte_22_are_clear(self):
        """Byte 22 (addr_flags) carries only res_required/ack_required today.

        This fixture is built with BOTH res_required=True and ack_required=True,
        so byte 22 is 0x03 (bits 0-1 set), not 0x00. The masked assertion is the
        load-bearing one: it stays correct once thread_connection (bit 3) is
        added, since the Thread-set counterpart becomes 0x0B and the mask
        becomes & 0xF4 == 0.
        """
        assert _HEADER_FIXTURE_BEFORE[22] & 0xFC == 0
        assert _HEADER_FIXTURE_BEFORE[22] == 0x03

    def test_unpack_short_data_raises(self):
        """Data shorter than the 36-byte header raises ValueError."""
        with pytest.raises(ValueError, match="36 bytes"):
            LifxHeader.unpack(b"\x00" * 35)


def _build_header(thread_connection: bool) -> LifxHeader:
    """Build a header identical except for thread_connection."""
    return LifxHeader(
        source=99,
        target=bytes.fromhex("d073d5000001") + b"\x00\x00",
        sequence=7,
        pkt_type=999,
        res_required=True,
        ack_required=True,
        tagged=True,
        thread_connection=thread_connection,
    )


class TestThreadConnectionBit:
    """LifxHeader.thread_connection: frame-address byte 22, bit 3."""

    def test_default_is_false(self):
        """Every existing LifxHeader(...) call site is unaffected by the new field."""
        header = LifxHeader(source=1, target=b"\x00" * 8, sequence=1, pkt_type=1)
        assert header.thread_connection is False

    def test_set_bit_differs_only_in_byte_22(self):
        """Setting thread_connection changes exactly byte 22, by exactly 0x08."""
        clear = _build_header(thread_connection=False).pack()
        setb = _build_header(thread_connection=True).pack()

        diff = [i for i in range(36) if clear[i] != setb[i]]

        assert diff == [22]
        assert setb[22] == clear[22] | 0x08

    def test_reserved_bits_stay_zero_when_bit_set(self):
        """Bits 2 and 4-7 of byte 22 remain zero when thread_connection is set."""
        packed = _build_header(thread_connection=True).pack()
        assert packed[22] & 0xF4 == 0

    def test_unpack_round_trips_both_values(self):
        """unpack() recovers thread_connection True and False."""
        for value in (True, False):
            header = _build_header(thread_connection=value)
            assert LifxHeader.unpack(header.pack()).thread_connection is value

    def test_repr_shows_thread_state(self):
        """repr() surfaces the bit so a failing byte assertion shows it directly."""
        header = _build_header(thread_connection=True)
        assert "thread=True" in repr(header)
