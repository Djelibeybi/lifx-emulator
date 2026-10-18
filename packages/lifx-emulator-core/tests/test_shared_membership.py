"""Tests for label-derived, shared location and group identifiers (#255)."""

import uuid

from lifx_emulator.devices import (
    LIFX_EMULATOR_NAMESPACE,
    derive_group_id,
    derive_location_id,
)
from lifx_emulator.devices.state_restorer import StateRestorer
from lifx_emulator.devices.states import GroupState, LocationState
from lifx_emulator.factories import (
    DeviceBuilder,
    create_color_light,
    create_device,
    create_multizone_light,
)
from lifx_emulator.products.registry import get_product
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device

EXPLICIT_LOCATION_ID = bytes(range(16))
EXPLICIT_GROUP_ID = bytes(range(16, 32))


def _query(device, pkt_type: int):
    """Send a Get packet to a device and return the last response payload."""
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=pkt_type,
        res_required=True,
    )
    responses = device.process_packet(header, None)
    return responses[-1][1]


def get_location(device) -> Device.StateLocation:
    packet = _query(device, Device.GetLocation.PKT_TYPE)
    assert isinstance(packet, Device.StateLocation)
    return packet


def get_group(device) -> Device.StateGroup:
    packet = _query(device, Device.GetGroup.PKT_TYPE)
    assert isinstance(packet, Device.StateGroup)
    return packet


class TestDerivedIdentifiers:
    """Identifier derivation is deterministic and label-based."""

    def test_derivation_is_uuid5_under_fixed_namespace(self):
        assert derive_location_id("Kitchen") == (
            uuid.uuid5(LIFX_EMULATOR_NAMESPACE, "Kitchen").bytes
        )
        assert derive_group_id("Downlights") == (
            uuid.uuid5(LIFX_EMULATOR_NAMESPACE, "Downlights").bytes
        )
        assert len(derive_location_id("x")) == 16

    def test_state_defaults_derive_from_default_labels(self):
        assert LocationState().location_id == derive_location_id("Test Location")
        assert GroupState().group_id == derive_group_id("Test Group")

    def test_state_derives_from_supplied_label(self):
        assert LocationState(location_label="Kitchen").location_id == (
            derive_location_id("Kitchen")
        )
        assert GroupState(group_label="Downlights").group_id == (
            derive_group_id("Downlights")
        )

    def test_state_keeps_explicit_identifier(self):
        loc = LocationState(location_id=EXPLICIT_LOCATION_ID, location_label="K")
        grp = GroupState(group_id=EXPLICIT_GROUP_ID, group_label="D")
        assert loc.location_id == EXPLICIT_LOCATION_ID
        assert grp.group_id == EXPLICIT_GROUP_ID


class TestFactoryMembership:
    """Devices built through the factories share identifiers by label."""

    def test_defaults_share_location_and_group(self):
        a = create_color_light("d073d5000001")
        b = create_multizone_light("d073d5000002")
        assert get_location(a).location == get_location(b).location
        assert get_group(a).group == get_group(b).group
        assert get_location(a).label == "Test Location"
        assert get_group(a).label == "Test Group"

    def test_same_label_shares_identifier(self):
        a = create_color_light(
            "d073d5000001", location_label="Kitchen", group_label="Downlights"
        )
        b = create_device(
            27,
            serial="d073d5000002",
            location_label="Kitchen",
            group_label="Downlights",
        )
        assert get_location(a).location == get_location(b).location
        assert get_location(a).label == "Kitchen"
        assert get_group(a).group == get_group(b).group
        assert get_group(a).label == "Downlights"

    def test_different_labels_differ(self):
        a = create_color_light(
            "d073d5000001", location_label="Kitchen", group_label="Downlights"
        )
        b = create_color_light(
            "d073d5000002", location_label="Bedroom", group_label="Lamps"
        )
        assert get_location(a).location != get_location(b).location
        assert get_group(a).group != get_group(b).group

    def test_explicit_identifier_wins_over_label(self):
        a = create_color_light(
            "d073d5000001",
            location_label="Kitchen",
            location_id=EXPLICIT_LOCATION_ID,
            group_label="Downlights",
            group_id=EXPLICIT_GROUP_ID,
        )
        b = create_color_light(
            "d073d5000002", location_label="Kitchen", group_label="Downlights"
        )
        assert get_location(a).location == EXPLICIT_LOCATION_ID
        assert get_location(a).label == "Kitchen"
        assert get_group(a).group == EXPLICIT_GROUP_ID
        assert get_location(a).location != get_location(b).location
        assert get_group(a).group != get_group(b).group

    def test_builder_accepts_location_and_group(self):
        product = get_product(27)
        assert product is not None
        device = (
            DeviceBuilder(product)
            .with_location("Kitchen")
            .with_group("Downlights", EXPLICIT_GROUP_ID)
            .build()
        )
        assert device.state.location_id == derive_location_id("Kitchen")
        assert device.state.location_label == "Kitchen"
        assert device.state.group_id == EXPLICIT_GROUP_ID
        assert device.state.group_label == "Downlights"

    def test_set_group_changes_only_the_target_device(self):
        a = create_color_light("d073d5000001")
        b = create_color_light("d073d5000002")
        before = get_group(b)

        header = LifxHeader(
            source=12345,
            target=a.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.SetGroup.PKT_TYPE,
            res_required=False,
        )
        a.process_packet(
            header,
            Device.SetGroup(group=EXPLICIT_GROUP_ID, label="Moved", updated_at=5),
        )

        assert get_group(a).group == EXPLICIT_GROUP_ID
        assert get_group(a).label == "Moved"
        # SetGroup uses the identifier in the packet and never re-derives
        assert get_group(a).group != derive_group_id("Moved")
        assert get_group(b).group == before.group
        assert get_group(b).label == before.label


class MockStorage:
    """Storage stub returning a fixed saved state."""

    def __init__(self, states: dict[str, dict]):
        self._states = states

    def load_device_state(self, serial: str) -> dict | None:
        return self._states.get(serial)


class TestRestore:
    """Restored devices keep their saved identifiers."""

    def test_restore_keeps_saved_identifier(self):
        device = create_color_light("d073d5000001")
        saved_state = {
            "product": device.state.product,
            "group_id": EXPLICIT_GROUP_ID,
            "group_label": "Test Group",
        }
        restorer = StateRestorer(MockStorage({"d073d5000001": saved_state}))
        result = restorer.restore_if_available(device.state)
        # Same label as the default, but the saved identifier wins
        assert result.group_label == "Test Group"
        assert result.group_id == EXPLICIT_GROUP_ID
        assert result.group_id != derive_group_id("Test Group")


class TestExplicitMembershipWinsOverRestore:
    """Explicit factory options take precedence over restored membership."""

    SAVED = {
        "product": 91,  # LIFX Color, as built by create_color_light
        "location_id": bytes(range(16)),
        "location_label": "Old Location",
        "group_id": bytes(range(16, 32)),
        "group_label": "Old Group",
    }

    def _storage(self):
        return MockStorage({"d073d5000001": dict(self.SAVED)})

    def test_omitted_options_keep_restored_membership(self):
        device = create_color_light("d073d5000001", storage=self._storage())
        assert get_location(device).label == "Old Location"
        assert get_location(device).location == bytes(range(16))
        assert get_group(device).label == "Old Group"
        assert get_group(device).group == bytes(range(16, 32))

    def test_explicit_labels_replace_restored_labels_and_identifiers(self):
        device = create_color_light(
            "d073d5000001",
            storage=self._storage(),
            location_label="Kitchen",
            group_label="Downlights",
        )
        assert get_location(device).label == "Kitchen"
        assert get_location(device).location == derive_location_id("Kitchen")
        assert get_group(device).label == "Downlights"
        assert get_group(device).group == derive_group_id("Downlights")

    def test_explicit_identifier_replaces_restored_identifier_only(self):
        device = create_color_light(
            "d073d5000001", storage=self._storage(), group_id=EXPLICIT_GROUP_ID
        )
        assert get_group(device).label == "Old Group"
        assert get_group(device).group == EXPLICIT_GROUP_ID
        # Location was not configured, so the saved location is kept
        assert get_location(device).label == "Old Location"
        assert get_location(device).location == bytes(range(16))
