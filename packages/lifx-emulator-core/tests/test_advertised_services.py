"""Tests for multi-service StateService discovery replies.

Real LIFX hardware replies to a single GetService with one StateService per
service it advertises -- including reserved/embedded services whose identifiers
are not defined as DeviceService enum members (values like 5 seen in the wild).
These tests exercise the emulator's opt-in multi-service behaviour.
"""

from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device


def _get_service(device):
    """Send a GetService to a device and return its StateService responses."""
    header = LifxHeader(
        source=12345,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=Device.GetService.PKT_TYPE,
        res_required=True,
    )
    responses = device.process_packet(header, None)
    state_type = Device.StateService.PKT_TYPE
    return [pkt for hdr, pkt in responses if hdr.pkt_type == state_type]


class TestDefaultBehaviour:
    """Backward compatibility: unconfigured devices reply with one UDP service."""

    def test_default_single_udp_reply(self):
        device = create_color_light("d073d5000001")

        replies = _get_service(device)

        assert len(replies) == 1
        assert replies[0].service == 1  # UDP
        assert replies[0].port == 56700


class TestMultiService:
    """Opt-in multi-service advertisement."""

    def test_multiple_services_emitted_in_order(self):
        # Non-UDP service deliberately before the UDP service to exercise
        # client dedup / port-selection ordering.
        device = create_color_light(
            "d073d5000001", advertised_services=[(5, 0), (1, 56700)]
        )

        replies = _get_service(device)

        assert len(replies) == 2
        assert (replies[0].service, replies[0].port) == (5, 0)
        assert (replies[1].service, replies[1].port) == (1, 56700)

    def test_raw_service_byte_on_wire(self):
        """service=5 must be packed as the literal byte 0x05, not remapped."""
        device = create_color_light(
            "d073d5000001", advertised_services=[(5, 0), (1, 56700)]
        )

        replies = _get_service(device)

        # StateService wire format: service uint8 + port uint32 little-endian.
        assert replies[0].pack() == b"\x05\x00\x00\x00\x00"
        assert replies[1].pack()[0:1] == b"\x01"

    def test_service_id_outside_enum_is_not_rejected(self):
        """An arbitrary uint8 not in DeviceService (e.g. 8) is emitted verbatim."""
        device = create_color_light("d073d5000001", advertised_services=[(8, 0)])

        replies = _get_service(device)

        assert len(replies) == 1
        assert replies[0].service == 8
        assert replies[0].pack() == b"\x08\x00\x00\x00\x00"

    def test_emitted_bytes_decode_without_crashing(self):
        """The emulator's own decoder tolerates the unknown service it emits.

        Symmetry: if we emit service=8 on the wire, StateService.unpack() must
        not raise -- it preserves the unknown value as a raw int rather than
        rejecting it (forward-compatibility, mirroring what clients must do).
        """
        device = create_color_light("d073d5000001", advertised_services=[(8, 0)])

        wire = _get_service(device)[0].pack()
        decoded = Device.StateService.unpack(wire)

        assert decoded.service == 8
        assert decoded.port == 0


class TestFactory:
    """Factory wiring for advertised_services."""

    def test_factory_sets_advertised_services(self):
        device = create_color_light(
            "d073d5000001", advertised_services=[(1, 56700), (5, 0)]
        )

        assert device.state.advertised_services == [(1, 56700), (5, 0)]

    def test_unconfigured_advertised_services_is_none(self):
        device = create_color_light("d073d5000001")

        assert device.state.advertised_services is None
