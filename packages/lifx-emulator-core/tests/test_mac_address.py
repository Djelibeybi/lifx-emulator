"""Tests for the network MAC address an emulated device reports."""

import pytest
from lifx_emulator.factories import create_device

SERIAL = "d073d5010203"
DIRECT = bytes.fromhex("d073d5010203")
OFFSET = bytes.fromhex("d073d5010204")


@pytest.mark.parametrize(
    ("major", "minor", "expected"),
    [
        (2, 90, DIRECT),
        (3, 9, DIRECT),  # minor 9 is below 70, not above it
        (3, 50, DIRECT),
        (3, 69, DIRECT),
        (3, 70, OFFSET),
        (3, 90, OFFSET),
        (3, 255, OFFSET),
        (4, 0, DIRECT),
        (4, 90, DIRECT),
    ],
)
def test_mac_address_follows_firmware_offset_rule(major, minor, expected):
    state = create_device(27, serial=SERIAL, firmware_version=(major, minor)).state
    assert state.mac_address == expected


def test_offset_wraps_final_octet_without_carry():
    state = create_device(27, serial="d073d50102ff", firmware_version=(3, 70)).state
    assert state.mac_address == bytes.fromhex("d073d5010200")


def test_mac_address_tracks_firmware_changes():
    state = create_device(27, serial=SERIAL, firmware_version=(3, 50)).state
    assert state.mac_address == DIRECT

    state.version_minor = 70
    assert state.mac_address == OFFSET


def test_mac_address_is_read_only():
    state = create_device(27, serial=SERIAL).state
    with pytest.raises(AttributeError):
        state.mac_address = DIRECT
