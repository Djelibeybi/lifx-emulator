"""Tests for Thread device identity: connectivity, firmware precedence,
wifi_signal and the header thread_connection bit.

This module also holds the pre-Thread-phase byte fixtures for a WiFi color
light's four reply shapes (StateService, StateColor, Acknowledgement,
StateUnhandled), captured from an unmodified tree before any behaviour
change, so a later diff can prove WiFi wire output did not move.
"""

import pytest
from lifx_emulator import Connectivity
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_device,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_switch,
    create_tile_device,
)
from lifx_emulator.factories.builder import DeviceBuilder
from lifx_emulator.factories.firmware_config import FirmwareConfig
from lifx_emulator.products.registry import PRODUCTS, get_product
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile
from lifx_emulator.protocol.protocol_types import TileBufferRect
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator.server import EmulatedLifxServer


class _RecordingTransport:
    """Records (data, addr) tuples in place of a real asyncio transport.

    server.transport is a plain attribute initialised to None in
    EmulatedLifxServer.__init__, so this double is assigned directly and no
    socket is ever bound.
    """

    def __init__(self) -> None:
        self.sent: list[tuple[bytes, tuple[str, int]]] = []

    def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
        self.sent.append((data, addr))


# Captured from an unmodified tree at commit e610c08e8ea9eab6e2b37cb097b731542ff8d717,
# via create_color_light("d073d5000001") driven through GetService, GetColor,
# device._create_response_header(...) for Acknowledgement, and an unhandled
# Tile packet (701).
_STATE_SERVICE_HEADER = bytes.fromhex(
    "2900001401000000d073d500000100000000000000000001000000000000000003000000"
)
_STATE_SERVICE_PAYLOAD = bytes.fromhex("017cdd0000")

_STATE_COLOR_HEADER = bytes.fromhex(
    "5800001402000000d073d50000010000000000000000000200000000000000006b000000"
)
_STATE_COLOR_PAYLOAD = bytes.fromhex(
    "5555ffff0080ac0d0000ffff4c49465820436f6c6f7220383030"
    "6c6d203030303030310000000000000000000000000000000000"
)

_ACKNOWLEDGEMENT_HEADER = bytes.fromhex(
    "2400001403000000d073d50000010000000000000000000300000000000000002d000000"
)

_STATE_UNHANDLED_HEADER = bytes.fromhex(
    "2600001404000000d073d5000001000000000000000000040000000000000000df000000"
)
_STATE_UNHANDLED_PAYLOAD = bytes.fromhex("bd02")


class TestWifiWireOutputUnchanged:
    """A WiFi device's reply bytes are unchanged by the Thread-identity phase."""

    def test_state_service_bytes_unchanged(self):
        """StateService (discovery reply) packs identically to the pre-phase fixture."""
        device = create_color_light("d073d5000001")
        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Device.GetService.PKT_TYPE,
            res_required=True,
        )
        resp_header, resp_packet = device.process_packet(header, None)[0]

        assert resp_header.pack() == _STATE_SERVICE_HEADER
        assert resp_packet.pack() == _STATE_SERVICE_PAYLOAD
        assert resp_header.pack()[22] == 0x00

    def test_state_color_bytes_unchanged(self):
        """StateColor (a data reply) packs identically to the pre-phase fixture."""
        device = create_color_light("d073d5000001")
        header = LifxHeader(
            source=2,
            target=device.state.get_target_bytes(),
            sequence=2,
            pkt_type=Light.GetColor.PKT_TYPE,
            res_required=True,
        )
        resp_header, resp_packet = device.process_packet(header, None)[0]

        assert resp_header.pack() == _STATE_COLOR_HEADER
        assert resp_packet.pack() == _STATE_COLOR_PAYLOAD
        assert resp_header.pack()[22] == 0x00

    def test_acknowledgement_bytes_unchanged(self):
        """Acknowledgement (built via the same helper the server's fast path uses)
        packs identically to the pre-phase fixture. Its payload is empty."""
        device = create_color_light("d073d5000001")
        resp_header = device._create_response_header(
            3, 3, Device.Acknowledgement.PKT_TYPE, len(Device.Acknowledgement().pack())
        )

        assert resp_header.pack() == _ACKNOWLEDGEMENT_HEADER
        assert Device.Acknowledgement().pack() == b""
        assert resp_header.pack()[22] == 0x00

    def test_state_unhandled_bytes_unchanged(self):
        """StateUnhandled (capability-mismatch reply) packs identically to the
        pre-phase fixture."""
        device = create_color_light("d073d5000001")
        header = LifxHeader(
            source=4,
            target=device.state.get_target_bytes(),
            sequence=4,
            pkt_type=701,  # Tile.Get64 -- unhandled by a color light
            res_required=True,
        )
        resp_header, resp_packet = device.process_packet(header, None)[0]

        assert resp_header.pack() == _STATE_UNHANDLED_HEADER
        assert resp_packet.pack() == _STATE_UNHANDLED_PAYLOAD
        assert resp_header.pack()[22] == 0x00


class TestConnectivityFactory:
    """create_device(): default, explicit connectivity, and coercion errors."""

    def test_default_is_wifi(self):
        """Omitting connectivity yields WiFi, matching pre-phase behaviour."""
        device = create_device(91, serial="d073d5000013")
        assert device.state.connectivity == Connectivity.WIFI
        assert device.state.connectivity == "wifi"

    def test_explicit_thread(self):
        """connectivity="thread" yields the Thread member and string equality."""
        device = create_device(91, serial="d073d5000014", connectivity="thread")
        assert device.state.connectivity == Connectivity.THREAD
        assert device.state.connectivity == "thread"

    @pytest.mark.parametrize("bad_value", ["Thread", "THREAD", "bluetooth"])
    def test_invalid_connectivity_raises(self, bad_value):
        """The match is exact and lowercase; anything else raises ValueError
        naming both accepted values."""
        with pytest.raises(ValueError) as excinfo:
            create_device(91, serial="d073d5000015", connectivity=bad_value)
        assert "wifi" in str(excinfo.value)
        assert "thread" in str(excinfo.value)


class TestConnectivityImmutability:
    """Reassigning connectivity or wifi_signal after construction raises."""

    def test_reassigning_connectivity_raises_even_for_same_value(self):
        """Freezing NetworkState means even a no-op reassignment raises."""
        device = create_device(91, serial="d073d5000016")
        with pytest.raises(ValueError, match="connectivity"):
            device.state.connectivity = Connectivity.WIFI

    def test_reassigning_connectivity_to_new_value_raises(self):
        device = create_device(91, serial="d073d5000017", connectivity="thread")
        with pytest.raises(ValueError, match="connectivity"):
            device.state.connectivity = Connectivity.WIFI

    def test_reassigning_wifi_signal_names_wifi_signal_not_connectivity(self):
        """Freezing NetworkState also freezes wifi_signal; the refusal message
        must name the attribute actually refused, not hard-code connectivity."""
        device = create_device(91, serial="d073d5000018")
        with pytest.raises(ValueError) as excinfo:
            device.state.wifi_signal = -50.0
        message = str(excinfo.value)
        assert "wifi_signal" in message
        assert "connectivity" not in message


def _reply_headers_for(device):
    """Drive a StateColor, an Acknowledgement, and a StateUnhandled reply and
    return their headers.

    process_packet() returns a list of (header, packet) two-tuples.
    """
    color_request = LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=Light.GetColor.PKT_TYPE,
        res_required=True,
    )
    color_header, _color_packet = device.process_packet(color_request, None)[0]

    ack_header = device._create_response_header(
        2, 2, Device.Acknowledgement.PKT_TYPE, len(Device.Acknowledgement().pack())
    )

    unhandled_request = LifxHeader(
        source=3,
        target=device.state.get_target_bytes(),
        sequence=3,
        pkt_type=701,  # Tile.Get64 -- unhandled by a color light
        res_required=True,
    )
    unhandled_header, _unhandled_packet = device.process_packet(
        unhandled_request, None
    )[0]

    return color_header, ack_header, unhandled_header


class TestThreadBitOnEveryReply:
    """A Thread device sets bit 3 on every reply shape; a WiFi device never does."""

    def test_thread_device_sets_bit_on_every_reply_shape(self):
        device = create_device(91, serial="d073d5000019", connectivity="thread")

        for header in _reply_headers_for(device):
            assert header.thread_connection is True
            assert header.pack()[22] & 0x08 == 0x08

    def test_wifi_device_never_sets_bit(self):
        device = create_device(91, serial="d073d5000020")

        for header in _reply_headers_for(device):
            assert header.thread_connection is False
            assert header.pack()[22] == 0x00


class TestDeviceBuilderConnectivity:
    """DeviceBuilder.with_connectivity() as its own public entry point (CONN-01)."""

    def _builder(self, pid: int = 91) -> DeviceBuilder:
        return DeviceBuilder(get_product(pid))

    def test_omitted_yields_wifi(self):
        device = self._builder().with_serial("d073d5000021").build()
        assert device.state.connectivity == Connectivity.WIFI

    def test_none_means_unspecified_yields_wifi(self):
        device = (
            self._builder().with_serial("d073d5000022").with_connectivity(None).build()
        )
        assert device.state.connectivity == Connectivity.WIFI

    def test_enum_member(self):
        device = (
            self._builder()
            .with_serial("d073d5000023")
            .with_connectivity(Connectivity.THREAD)
            .build()
        )
        assert device.state.connectivity == Connectivity.THREAD

    def test_valid_string(self):
        device = (
            self._builder()
            .with_serial("d073d5000024")
            .with_connectivity("thread")
            .build()
        )
        assert device.state.connectivity == Connectivity.THREAD

    def test_invalid_string_raises(self):
        builder = (
            self._builder().with_serial("d073d5000025").with_connectivity("Thread")
        )
        with pytest.raises(ValueError):
            builder.build()

    def test_returns_self_for_chaining(self):
        builder = self._builder()
        assert builder.with_connectivity("thread") is builder


class TestThreadFirmwarePrecedence:
    """FirmwareConfig.get_firmware_version(): Thread default, floor and the
    per-product terminal-firmware ceiling, extending the single existing
    precedence chain."""

    def test_thread_default_for_product_with_no_specs_default(self):
        config = FirmwareConfig()
        assert config.get_firmware_version(
            product_id=91, connectivity=Connectivity.THREAD
        ) == (4, 200)

    def test_thread_default_overrides_specs_default(self):
        """Product 176 (Ceiling) has a specs.yml default of (4, 10); the
        Thread branch must fire before the product-default branch."""
        config = FirmwareConfig()
        assert config.get_firmware_version(
            product_id=176, connectivity=Connectivity.THREAD
        ) == (4, 200)

    def test_thread_explicit_override_at_floor_accepted(self):
        config = FirmwareConfig()
        assert config.get_firmware_version(
            product_id=91, connectivity=Connectivity.THREAD, override=(4, 200)
        ) == (4, 200)

    def test_thread_explicit_override_above_floor_accepted(self):
        config = FirmwareConfig()
        assert config.get_firmware_version(
            product_id=91, connectivity=Connectivity.THREAD, override=(5, 0)
        ) == (5, 0)

    def test_thread_override_just_below_floor_raises(self):
        config = FirmwareConfig()
        with pytest.raises(ValueError) as excinfo:
            config.get_firmware_version(
                product_id=91, connectivity=Connectivity.THREAD, override=(4, 199)
            )
        assert "200" in str(excinfo.value)

    def test_thread_override_well_below_floor_raises(self):
        config = FirmwareConfig()
        with pytest.raises(ValueError) as excinfo:
            config.get_firmware_version(
                product_id=91, connectivity=Connectivity.THREAD, override=(3, 70)
            )
        assert "200" in str(excinfo.value)

    def test_tile_override_above_ceiling_raises(self):
        config = FirmwareConfig()
        with pytest.raises(ValueError) as excinfo:
            config.get_firmware_version(product_id=55, override=(3, 51))
        message = str(excinfo.value)
        assert "51" in message
        assert "50" in message

    def test_tile_override_at_ceiling_accepted(self):
        config = FirmwareConfig()
        assert config.get_firmware_version(product_id=55, override=(3, 50)) == (3, 50)

    def test_tile_on_thread_names_both_bounds(self):
        """Thread's default (4.200) sits above the Tile's terminal firmware
        ceiling (3.50); the arithmetic alone rejects it, with no product-ID
        comparison anywhere in the source."""
        config = FirmwareConfig()
        with pytest.raises(ValueError) as exc:
            config.get_firmware_version(product_id=55, connectivity=Connectivity.THREAD)
        assert "200" in str(exc.value)
        assert "50" in str(exc.value)

    def test_tile_on_thread_override_does_not_bypass_ceiling(self):
        """An explicit override does not exempt a device from its product's
        terminal firmware -- the ceiling check is not skipped."""
        config = FirmwareConfig()
        with pytest.raises(ValueError) as exc:
            config.get_firmware_version(
                product_id=55, connectivity=Connectivity.THREAD, override=(4, 200)
            )
        assert "50" in str(exc.value)

    def test_tile_on_thread_sub_floor_override_names_floor_not_ceiling(self):
        """The floor check runs first: a sub-floor Thread request must never
        be silently accepted just because it also fits under the ceiling."""
        config = FirmwareConfig()
        with pytest.raises(ValueError) as exc:
            config.get_firmware_version(
                product_id=55, connectivity=Connectivity.THREAD, override=(3, 40)
            )
        assert "200" in str(exc.value)

    def test_wifi_extended_multizone_unaffected(self):
        config = FirmwareConfig()
        assert config.get_firmware_version(extended_multizone=True) == (3, 70)
        assert config.get_firmware_version(extended_multizone=False) == (2, 60)


class TestThreadOnTileRejectionRegistryWide:
    """MUST NOT reject any product ID other than 55 for connectivity="thread"
    (SPEC prohibition row 2, D-06 no-product-gating decision). Computed from
    the live registry, not a pinned count, so an upstream products.json sync
    cannot silently narrow or widen the claim without failing this test."""

    def test_only_product_55_is_rejected_registry_wide(self):
        rejected: set[int] = set()
        for pid in PRODUCTS:
            try:
                create_device(pid, connectivity="thread")
            except ValueError:
                rejected.add(pid)
        assert rejected == {55}

    def test_matrix_diagnostic_subset(self):
        """Secondary diagnostic: every matrix product except 55 accepts
        Thread. Kept alongside the registry-wide assertion so a failure
        immediately shows whether a regression is matrix-specific or
        registry-wide."""
        matrix_pids = {pid for pid, info in PRODUCTS.items() if info.has_matrix}
        assert matrix_pids, "expected at least one matrix product in the registry"

        rejected: set[int] = set()
        for pid in PRODUCTS:
            try:
                create_device(pid, connectivity="thread")
            except ValueError:
                rejected.add(pid)

        assert matrix_pids - rejected == matrix_pids - {55}


class TestThreadExtendedMultizoneInteraction:
    """Pinning test: a Thread device's firmware (4.200) always clears a
    multizone product's min_ext_mz_firmware threshold, so has_extended_multizone
    is derived True regardless of the extended_multizone argument. This is
    accepted semantics -- every Thread bulb ships extended-capable firmware --
    recorded here rather than left to be discovered later as a bug."""

    def test_extended_multizone_false_still_grants_extended_on_thread(self):
        thread_device = create_device(
            38,
            serial="d073d5000026",
            zone_count=8,
            extended_multizone=False,
            connectivity="thread",
        )
        assert thread_device.state.version_major == 4
        assert thread_device.state.version_minor == 200
        assert thread_device.state.has_extended_multizone is True

        wifi_device = create_device(
            38,
            serial="d073d5000027",
            zone_count=8,
            extended_multizone=False,
        )
        assert wifi_device.state.version_major == 2
        assert wifi_device.state.version_minor == 60
        assert wifi_device.state.has_extended_multizone is False


def _wrap_create_device_as_typed_factory():
    """Wrap create_device(91, ...) so it can sit alongside the seven typed
    factories in one parametrisation, as the plan's eighth entry point.

    Product 91 (LIFX Color) is a plain color light with no Thread-related
    ceiling, matching the "succeeds" typed factories.
    """

    def _factory(
        serial: str | None = None,
        connectivity: Connectivity | str | None = None,
        firmware_version: tuple[int, int] | None = None,
    ):
        return create_device(
            91,
            serial=serial,
            connectivity=connectivity,
            firmware_version=firmware_version,
        )

    return _factory


# (name, factory, succeeds) -- "succeeds" is False only for create_tile_device,
# whose hard-coded product 55 has a terminal firmware ceiling (3.50) below the
# Thread floor (4.200), so connectivity="thread" always raises ValueError.
_TYPED_FACTORY_ENTRY_POINTS = [
    ("create_color_light", create_color_light, True),
    ("create_infrared_light", create_infrared_light, True),
    ("create_hev_light", create_hev_light, True),
    ("create_color_temperature_light", create_color_temperature_light, True),
    ("create_multizone_light", create_multizone_light, True),
    ("create_tile_device", create_tile_device, False),
    ("create_switch", create_switch, True),
    ("create_device", _wrap_create_device_as_typed_factory(), True),
]


class TestTypedFactoryConnectivity:
    """Every public factory entry point accepts `connectivity` with
    identical semantics, except `create_tile_device`, which raises for
    `connectivity="thread"` because its hard-coded product 55's terminal
    firmware ceiling (3.50) sits below the Thread floor (4.200). SPEC AC 2
    was amended to say so explicitly (Round 1 consensus concern 3,
    `L101@c667eb9`, `L385@c667eb9`, `L480@c667eb9`).

    The "omitted or None" axis exercised here is the `connectivity`
    argument, which defaults to `None` on all eight entry points.
    `create_multizone_light`'s `extended_multizone: bool = True` is a
    different parameter with a non-`None` default and is deliberately not
    part of this parametrisation -- its Thread interaction is pinned once,
    in Plan 02 Task 2, through `create_device` directly (developer finding
    12, `L279@d626690`, `L462@d626690`).
    """

    @pytest.mark.parametrize(
        ("name", "factory", "succeeds"),
        _TYPED_FACTORY_ENTRY_POINTS,
        ids=[name for name, _, _ in _TYPED_FACTORY_ENTRY_POINTS],
    )
    def test_connectivity_forwarding_and_firmware(self, name, factory, succeeds):
        # Omitted and explicit None both yield WiFi, for every entry point.
        assert factory().state.connectivity == Connectivity.WIFI
        assert factory(connectivity=None).state.connectivity == Connectivity.WIFI

        # Wrong case and an unrelated radio name are rejected by every entry
        # point, regardless of whether "thread" itself succeeds for it.
        with pytest.raises(ValueError):
            factory(connectivity="Thread")
        with pytest.raises(ValueError):
            factory(connectivity="bluetooth")

        if not succeeds:
            with pytest.raises(ValueError):
                factory(connectivity="thread")
            return

        device = factory(connectivity="thread")
        assert device.state.connectivity == Connectivity.THREAD

        # No explicit firmware: the Thread default/floor (4.200) applies,
        # forwarded correctly through this entry point.
        assert device.state.version_major == 4
        assert device.state.version_minor == 200

        # An explicit valid Thread firmware wins over the Thread default --
        # pinned per entry point so a typed factory cannot preserve
        # connectivity while mishandling firmware_version (developer
        # finding 12, `L117@d626690`, `L123@d626690`).
        overridden = factory(connectivity="thread", firmware_version=(5, 0))
        assert overridden.state.version_major == 5
        assert overridden.state.version_minor == 0


class TestWifiSignalDerivation:
    """wifi_signal is derived from the effective connectivity at build time."""

    def test_thread_wifi_signal_is_zero(self):
        device = create_color_light(serial="d073d5000028", connectivity="thread")
        assert device.state.wifi_signal == 0.0

    def test_wifi_wifi_signal_is_minus_45(self):
        device = create_color_light(serial="d073d5000029")
        assert device.state.wifi_signal == -45.0


def _send_and_get(device, request_cls, response_cls):
    """Send `request_cls` to `device` and return the matching `response_cls`."""
    header = LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=request_cls.PKT_TYPE,
        res_required=True,
    )
    responses = device.process_packet(header, None)
    for resp_header, resp_packet in responses:
        if resp_header.pkt_type == response_cls.PKT_TYPE:
            return resp_packet
    raise AssertionError(f"No {response_cls.__name__} in responses: {responses}")


class TestThreadIdentitySurface:
    """GetWifiInfo/GetHostFirmware/GetWifiFirmware and the ambient light
    sensor for a Thread device -- a Thread device must not be
    distinguishable from a WiFi device at the same firmware by its reply
    shape (Antigravity suggestion, `L388@c667eb9`)."""

    def test_thread_device_identity_surface(self):
        thread_device = create_color_light(serial="d073d5000030", connectivity="thread")
        wifi_device = create_color_light(
            serial="d073d5000031", firmware_version=(4, 200)
        )

        thread_wifi_info = _send_and_get(
            thread_device, Device.GetWifiInfo, Device.StateWifiInfo
        )
        assert thread_wifi_info.signal == 0.0

        wifi_wifi_info = _send_and_get(
            wifi_device, Device.GetWifiInfo, Device.StateWifiInfo
        )
        assert wifi_wifi_info.signal == -45.0

        thread_host_fw = _send_and_get(
            thread_device, Device.GetHostFirmware, Device.StateHostFirmware
        )
        thread_wifi_fw = _send_and_get(
            thread_device, Device.GetWifiFirmware, Device.StateWifiFirmware
        )
        assert (thread_host_fw.version_major, thread_host_fw.version_minor) == (
            4,
            200,
        )
        assert (thread_wifi_fw.version_major, thread_wifi_fw.version_minor) == (
            4,
            200,
        )

        # A WiFi device at the same firmware must reply with identical
        # version fields on both firmware packets -- a Thread device is not
        # distinguishable by its firmware reply shape.
        wifi_host_fw = _send_and_get(
            wifi_device, Device.GetHostFirmware, Device.StateHostFirmware
        )
        wifi_wifi_fw = _send_and_get(
            wifi_device, Device.GetWifiFirmware, Device.StateWifiFirmware
        )
        assert (wifi_host_fw.version_major, wifi_host_fw.version_minor) == (
            thread_host_fw.version_major,
            thread_host_fw.version_minor,
        )
        assert (wifi_wifi_fw.version_major, wifi_wifi_fw.version_minor) == (
            thread_wifi_fw.version_major,
            thread_wifi_fw.version_minor,
        )

        # The existing firmware-4 sensor rule, no Thread-specific branch.
        assert thread_device.state.ambient_light_lux == 100.0


class TestThreadBitOnEveryReplyShapeMultizone:
    """One Thread multizone device proves bit 3 on every reply shape the
    SPEC enumerates -- StateColor, the fast-path Acknowledgement, the
    scenario-path Acknowledgement, StateUnhandled, and every packet of a
    multi-packet StateMultiZone list -- in a single test body, so a partial
    fix cannot pass any subset. Matrix's State64 is covered separately
    (TestMatrixThreadBit) because no registry product is both multizone
    and matrix."""

    def test_thread_multizone_device_sets_bit_on_all_reply_shapes(self):
        device = create_multizone_light(
            "d073d5000039", zone_count=16, connectivity="thread"
        )

        # StateColor: a data reply.
        color_request = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Light.GetColor.PKT_TYPE,
            res_required=True,
        )
        color_header, _color_packet = device.process_packet(color_request, None)[0]
        assert color_header.thread_connection is True
        assert color_header.pack()[22] & 0x08 == 0x08

        # StateUnhandled: a Tile-namespace packet fails
        # _should_handle_packet's has_matrix check on a multizone device.
        unhandled_request = LifxHeader(
            source=2,
            target=device.state.get_target_bytes(),
            sequence=2,
            pkt_type=701,  # Tile.Get64 -- unhandled by a multizone device
            res_required=True,
        )
        unhandled_header, _unhandled_packet = device.process_packet(
            unhandled_request, None
        )[0]
        assert unhandled_header.thread_connection is True
        assert unhandled_header.pack()[22] & 0x08 == 0x08

        # Every packet of a multi-packet StateMultiZone list: 16 zones
        # spans two 8-zone StateMultiZone packets.
        multizone_request = LifxHeader(
            source=3,
            target=device.state.get_target_bytes(),
            sequence=3,
            pkt_type=MultiZone.GetColorZones.PKT_TYPE,
            res_required=True,
        )
        multizone_packet = MultiZone.GetColorZones(start_index=0, end_index=15)
        multizone_responses = device.process_packet(multizone_request, multizone_packet)
        assert len(multizone_responses) == 2
        for resp_header, _resp_packet in multizone_responses:
            assert resp_header.thread_connection is True
            assert resp_header.pack()[22] & 0x08 == 0x08

        # Fast-path Acknowledgement, obtained from the REAL server path
        # (not device._create_response_header "the way the server does").
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer([device], device_manager, "127.0.0.1", 56700)
        recorder = _RecordingTransport()
        server.transport = recorder

        ack_request = LifxHeader(
            source=4,
            target=device.state.get_target_bytes(),
            sequence=4,
            pkt_type=Light.GetColor.PKT_TYPE,
            ack_required=True,
            res_required=False,
        )
        server._send_ack(device, ack_request, ("::1", 56700))
        assert len(recorder.sent) == 1
        ack_data, _addr = recorder.sent[0]
        ack_header = LifxHeader.unpack(ack_data[:36])
        assert ack_header.thread_connection is True
        assert ack_data[22] & 0x08 == 0x08

        # Scenario-path Acknowledgement, built inside process_packet() when
        # a scenario targets ack behaviour. response_delays={45: 0.01}
        # flips affects_acks (packet type 45 in response_delays); asserted
        # explicitly so a silently-False flag can't hide behind the
        # fast-path ack instead.
        scenario = ScenarioConfig(response_delays={45: 0.01})
        assert scenario.affects_acks
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(device.state.serial, scenario)
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        scenario_ack_request = LifxHeader(
            source=5,
            target=device.state.get_target_bytes(),
            sequence=5,
            pkt_type=Light.GetColor.PKT_TYPE,
            ack_required=True,
            res_required=True,
        )
        scenario_responses = device.process_packet(scenario_ack_request, None)
        scenario_ack_header = next(
            resp_header
            for resp_header, _resp_packet in scenario_responses
            if resp_header.pkt_type == Device.Acknowledgement.PKT_TYPE
        )
        assert scenario_ack_header.thread_connection is True
        assert scenario_ack_header.pack()[22] & 0x08 == 0x08


class TestSendAckRealServerWifiAndThread:
    """The fast-path acknowledgement, driven through the real
    EmulatedLifxServer._send_ack(), carries bit 3 for a Thread device and
    not for a WiFi device."""

    def test_send_ack_thread_and_wifi_bytes(self):
        thread_device = create_color_light("d073d5000047", connectivity="thread")
        wifi_device = create_color_light("d073d5000048")

        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [thread_device, wifi_device], device_manager, "127.0.0.1", 56700
        )
        recorder = _RecordingTransport()
        server.transport = recorder

        for device, expected_byte in (
            (thread_device, 0x08),
            (wifi_device, 0x00),
        ):
            request_header = LifxHeader(
                source=1,
                target=device.state.get_target_bytes(),
                sequence=1,
                pkt_type=Light.GetColor.PKT_TYPE,
                ack_required=True,
                res_required=False,
            )
            server._send_ack(device, request_header, ("::1", 56700))

        assert len(recorder.sent) == 2
        assert recorder.sent[0][0][22] & 0x08 == 0x08  # Thread ack, sent first
        assert recorder.sent[1][0][22] == 0x00  # WiFi ack, sent second


class TestScenarioMutationReachesTransport:
    """Regression gate for the server.py bytes-aware repair (developer
    decision): a malformed or invalid-field scenario reply must reach the
    transport with bit 3 set, not raise AttributeError before anything is
    sent. Reverting the server.py change makes both cases fail with
    AttributeError."""

    @pytest.mark.parametrize("connectivity", ["wifi", "thread"])
    @pytest.mark.parametrize(
        "scenario_field", ["malformed_packets", "invalid_field_values"]
    )
    async def test_empty_scenario_ack_reaches_transport(
        self, connectivity, scenario_field
    ):
        """Mutating an empty acknowledgement still sends its header and radio bit."""
        device = create_color_light("d073d5000057", connectivity=connectivity)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            device.state.serial,
            ScenarioConfig(**{scenario_field: [Device.Acknowledgement.PKT_TYPE]}),
        )
        server = EmulatedLifxServer(
            [device],
            DeviceManager(DeviceRepository()),
            scenario_manager=scenario_manager,
        )
        recorder = _RecordingTransport()
        server.transport = recorder
        header = LifxHeader(
            source=123,
            target=device.state.get_target_bytes(),
            sequence=7,
            pkt_type=Device.SetPower.PKT_TYPE,
            ack_required=True,
        )
        address = ("127.0.0.1", 56701)

        await server._process_device_packet(
            device, header, Device.SetPower(level=0), address
        )

        assert len(recorder.sent) == 1
        data, destination = recorder.sent[0]
        assert destination == address
        assert len(data) == LifxHeader.HEADER_SIZE
        response = LifxHeader.unpack(data)
        assert response.pkt_type == Device.Acknowledgement.PKT_TYPE
        assert response.source == header.source
        assert response.sequence == header.sequence
        assert response.thread_connection is (connectivity == "thread")
        expected_size = 46 if scenario_field == "malformed_packets" else 36
        assert response.size == expected_size
        assert server.packets_sent == 1
        assert device.state.power_level == 0

    async def test_malformed_scenario_reaches_transport_with_bit_set(self):
        device = create_color_light("d073d5000049", connectivity="thread")
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            device.state.serial,
            ScenarioConfig(malformed_packets=[Light.StateColor.PKT_TYPE]),
        )
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )
        recorder = _RecordingTransport()
        server.transport = recorder

        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Light.GetColor.PKT_TYPE,
            res_required=True,
        )
        await server._process_device_packet(device, header, None, ("::1", 56700))

        assert len(recorder.sent) == 1
        data, _addr = recorder.sent[0]
        assert data[22] & 0x08 == 0x08

    async def test_invalid_field_scenario_reaches_transport_with_bit_set(self):
        device = create_color_light("d073d5000050", connectivity="thread")
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            device.state.serial,
            ScenarioConfig(invalid_field_values=[Light.StateColor.PKT_TYPE]),
        )
        device_manager = DeviceManager(DeviceRepository())
        server = EmulatedLifxServer(
            [device],
            device_manager,
            "127.0.0.1",
            56700,
            scenario_manager=scenario_manager,
        )
        recorder = _RecordingTransport()
        server.transport = recorder

        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Light.GetColor.PKT_TYPE,
            res_required=True,
        )
        await server._process_device_packet(device, header, None, ("::1", 56700))

        assert len(recorder.sent) == 1
        data, _addr = recorder.sent[0]
        assert data[22] & 0x08 == 0x08


class TestScenarioMutationPreservesThreadBitDeviceLevel:
    """partial_responses and malformed_packets mutate or drop payloads,
    never the header, so bit 3 must be unaffected on the packets that
    survive."""

    def test_partial_responses_preserve_thread_bit(self):
        device = create_multizone_light(
            "d073d5000051", zone_count=16, connectivity="thread"
        )
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            device.state.serial,
            ScenarioConfig(partial_responses=[MultiZone.StateMultiZone.PKT_TYPE]),
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=MultiZone.GetColorZones.PKT_TYPE,
            res_required=True,
        )
        packet = MultiZone.GetColorZones(start_index=0, end_index=15)
        responses = device.process_packet(header, packet)

        # 16 zones -> 2 full packets; random.randint(1, 1) truncates to 1.
        assert len(responses) == 1
        for resp_header, _resp_packet in responses:
            assert resp_header.thread_connection is True
            assert resp_header.pack()[22] & 0x08 == 0x08

    def test_malformed_packets_preserve_thread_bit_device_level(self):
        """The malformed reply's second tuple element is bytes, not a
        packet object -- that is what the server.py repair accommodates."""
        device = create_color_light("d073d5000052", connectivity="thread")
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            device.state.serial,
            ScenarioConfig(malformed_packets=[Light.StateColor.PKT_TYPE]),
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Light.GetColor.PKT_TYPE,
            res_required=True,
        )
        responses = device.process_packet(header, None)
        resp_header, resp_payload = responses[0]
        assert isinstance(resp_payload, bytes)
        assert resp_header.thread_connection is True
        assert resp_header.pack()[22] & 0x08 == 0x08


class TestMatrixThreadBit:
    """State64 bit 3 on a large matrix device (a single oversized tile) and
    a chained matrix device (multiple tiles, one request many replies).
    Get64Handler emits exactly one State64 per requested tile index,
    sliced to at most 64 zones by the request rect -- zone count alone
    never produces extra packets, so these are two distinct tests rather
    than one "spans more than 64 zones" test."""

    def test_large_matrix_device_two_get64_requests(self):
        """LIFX Ceiling 13x26" (PID 201): a single 16x8 tile with
        max_tile_count: 1. Reading its 128 zones takes two Get64
        requests -- not tile_count=2, not length=2, which would describe a
        chained matrix device, which the Ceiling is not."""
        device = create_device(201, serial="d073d5000053", connectivity="thread")

        rect_first_half = TileBufferRect(fb_index=0, x=0, y=0, width=16)
        header1 = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Tile.Get64.PKT_TYPE,
            res_required=True,
        )
        packet1 = Tile.Get64(tile_index=0, length=1, rect=rect_first_half)
        responses1 = device.process_packet(header1, packet1)
        assert len(responses1) == 1
        resp_header1, resp_packet1 = responses1[0]
        assert len(resp_packet1.colors) == 64
        assert resp_header1.thread_connection is True
        assert resp_header1.pack()[22] & 0x08 == 0x08

        rect_second_half = TileBufferRect(fb_index=0, x=0, y=4, width=16)
        header2 = LifxHeader(
            source=2,
            target=device.state.get_target_bytes(),
            sequence=2,
            pkt_type=Tile.Get64.PKT_TYPE,
            res_required=True,
        )
        packet2 = Tile.Get64(tile_index=0, length=1, rect=rect_second_half)
        responses2 = device.process_packet(header2, packet2)
        assert len(responses2) == 1
        resp_header2, resp_packet2 = responses2[0]
        assert len(resp_packet2.colors) == 64
        assert resp_header2.thread_connection is True
        assert resp_header2.pack()[22] & 0x08 == 0x08

    def test_chained_matrix_device_single_get64_request(self):
        """Synthetic chained matrix device: product 185 (LIFX Candle Color
        US, max_tile_count: 1) built with an explicit tile_count=2 to
        exercise the one-request-many-replies branch of Get64Handler.
        Product 55 (Tile) is the only product whose specs.yml declares
        max_tile_count > 1, and 55 cannot be Thread (its terminal firmware
        ceiling sits below the Thread floor), so no real Thread product
        ships as a chain -- the builder does not enforce max_tile_count,
        and this test exists to exercise the handler branch, not to claim
        product fidelity."""
        device = create_device(
            185, serial="d073d5000054", tile_count=2, connectivity="thread"
        )
        rect = TileBufferRect(fb_index=0, x=0, y=0, width=5)
        header = LifxHeader(
            source=1,
            target=device.state.get_target_bytes(),
            sequence=1,
            pkt_type=Tile.Get64.PKT_TYPE,
            res_required=True,
        )
        packet = Tile.Get64(tile_index=0, length=2, rect=rect)
        responses = device.process_packet(header, packet)
        assert len(responses) == 2
        for resp_header, _resp_packet in responses:
            assert resp_header.thread_connection is True
            assert resp_header.pack()[22] & 0x08 == 0x08


class TestMixedFleetThreadAndWifi:
    """Mixed fleets retain identity bits while broadcasts select WiFi only."""

    def test_mixed_fleet_each_device_answers_with_its_own_bit(self):
        wifi_device = create_color_light("d073d5000055")
        thread_device = create_color_light("d073d5000056", connectivity="thread")

        repository = DeviceRepository()
        device_manager = DeviceManager(repository)
        device_manager.add_device(wifi_device)
        device_manager.add_device(thread_device)

        for device, expected_byte in (
            (wifi_device, 0x00),
            (thread_device, 0x08),
        ):
            request = LifxHeader(
                source=1,
                target=device.state.get_target_bytes(),
                sequence=1,
                pkt_type=Light.GetColor.PKT_TYPE,
                res_required=True,
            )
            resp_header, _resp_packet = device.process_packet(request, None)[0]
            assert resp_header.pack()[22] == expected_byte

        broadcast_header = LifxHeader(
            source=2,
            target=b"\x00" * 8,
            sequence=2,
            pkt_type=Device.GetService.PKT_TYPE,
            tagged=True,
            res_required=True,
        )
        targets = device_manager.resolve_target_devices(broadcast_header)
        assert targets == [wifi_device]

        answers_by_serial = {}
        for target_device in targets:
            resp_header, _resp_packet = target_device.process_packet(
                broadcast_header, None
            )[0]
            answers_by_serial[target_device.state.serial] = resp_header.pack()[22]

        assert answers_by_serial[wifi_device.state.serial] == 0x00
        assert thread_device.state.serial not in answers_by_serial
