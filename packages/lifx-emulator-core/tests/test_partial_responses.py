"""Tests for partial_responses, extended multizone >82 zones, and Get64 length."""

from unittest.mock import patch

from lifx_emulator.factories import create_multizone_light, create_tile_device
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import MultiZone, Tile
from lifx_emulator.protocol.protocol_types import TileBufferRect
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig

# --- Helpers ---


def _make_header(device, pkt_type, res_required=True):
    return LifxHeader(
        source=1,
        target=device.state.get_target_bytes(),
        sequence=1,
        pkt_type=pkt_type,
        res_required=res_required,
    )


def _responses_of_type(responses, pkt_type):
    return [r for r in responses if r[0].pkt_type == pkt_type]


# --- Extended multizone fix tests ---


class TestExtendedMultizoneMultiplePackets:
    """ExtendedGetColorZonesHandler should return multiple packets for >82 zones."""

    def test_120_zones_returns_two_packets(self):
        device = create_multizone_light(
            "d073d5100001", zone_count=120, extended_multizone=True
        )
        header = _make_header(device, 511)
        responses = device.process_packet(header, None)

        ext_responses = _responses_of_type(responses, 512)
        assert len(ext_responses) == 2

        _, pkt0 = ext_responses[0]
        assert pkt0.index == 0
        assert pkt0.colors_count == 82
        assert pkt0.count == 120

        _, pkt1 = ext_responses[1]
        assert pkt1.index == 82
        assert pkt1.colors_count == 38
        assert pkt1.count == 120

    def test_60_zones_returns_one_packet(self):
        device = create_multizone_light(
            "d073d5100002", zone_count=60, extended_multizone=True
        )
        header = _make_header(device, 511)
        responses = device.process_packet(header, None)

        ext_responses = _responses_of_type(responses, 512)
        assert len(ext_responses) == 1
        assert ext_responses[0][1].colors_count == 60

    def test_82_zones_returns_one_packet(self):
        device = create_multizone_light(
            "d073d5100003", zone_count=82, extended_multizone=True
        )
        header = _make_header(device, 511)
        responses = device.process_packet(header, None)

        ext_responses = _responses_of_type(responses, 512)
        assert len(ext_responses) == 1
        assert ext_responses[0][1].colors_count == 82


# --- Get64 length fix tests ---


class TestGet64Length:
    """Get64Handler should respect the length field."""

    def test_length_1(self):
        device = create_tile_device("d073d5200001", tile_count=5)
        packet = Tile.Get64(
            tile_index=0,
            length=1,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        )
        header = _make_header(device, 707)
        responses = device.process_packet(header, packet)

        tile_responses = _responses_of_type(responses, 711)
        assert len(tile_responses) == 1
        assert tile_responses[0][1].tile_index == 0

    def test_length_3(self):
        device = create_tile_device("d073d5200002", tile_count=5)
        packet = Tile.Get64(
            tile_index=0,
            length=3,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        )
        header = _make_header(device, 707)
        responses = device.process_packet(header, packet)

        tile_responses = _responses_of_type(responses, 711)
        assert len(tile_responses) == 3
        assert [r[1].tile_index for r in tile_responses] == [0, 1, 2]

    def test_length_5_full_chain(self):
        device = create_tile_device("d073d5200003", tile_count=5)
        packet = Tile.Get64(
            tile_index=0,
            length=5,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        )
        header = _make_header(device, 707)
        responses = device.process_packet(header, packet)

        tile_responses = _responses_of_type(responses, 711)
        assert len(tile_responses) == 5
        assert [r[1].tile_index for r in tile_responses] == [0, 1, 2, 3, 4]

    def test_length_exceeds_chain(self):
        device = create_tile_device("d073d5200004", tile_count=5)
        packet = Tile.Get64(
            tile_index=3,
            length=5,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        )
        header = _make_header(device, 707)
        responses = device.process_packet(header, packet)

        tile_responses = _responses_of_type(responses, 711)
        assert len(tile_responses) == 2
        assert [r[1].tile_index for r in tile_responses] == [3, 4]


# --- Partial response tests ---


class TestPartialResponsesMultizone:
    """partial_responses should truncate multi-packet multizone responses."""

    def test_standard_multizone_partial(self):
        """120 zones = 15 StateMultiZone packets; partial should return 1..14."""
        device = create_multizone_light("d073d5300001", zone_count=120)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5300001", ScenarioConfig(partial_responses=[506])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        packet = MultiZone.GetColorZones(start_index=0, end_index=119)
        header = _make_header(device, 502)
        responses = device.process_packet(header, packet)

        mz_responses = _responses_of_type(responses, 506)
        assert 1 <= len(mz_responses) < 15

    def test_standard_multizone_no_partial(self):
        """Without partial_responses, all 15 packets should be returned."""
        device = create_multizone_light("d073d5300002", zone_count=120)
        packet = MultiZone.GetColorZones(start_index=0, end_index=119)
        header = _make_header(device, 502)
        responses = device.process_packet(header, packet)

        mz_responses = _responses_of_type(responses, 506)
        assert len(mz_responses) == 15

    def test_extended_multizone_partial(self):
        """120 zones = 2 ExtendedStateMultiZone; partial should return 1."""
        device = create_multizone_light(
            "d073d5300003", zone_count=120, extended_multizone=True
        )
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5300003", ScenarioConfig(partial_responses=[512])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        header = _make_header(device, 511)
        responses = device.process_packet(header, None)

        ext_responses = _responses_of_type(responses, 512)
        # 2 packets, partial -> exactly 1 (randint(1,1) = 1)
        assert len(ext_responses) == 1

    def test_extended_multizone_not_affected_by_standard_partial(self):
        """partial_responses=[506] should not affect ExtendedStateMultiZone (512)."""
        device = create_multizone_light(
            "d073d5300004", zone_count=120, extended_multizone=True
        )
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5300004", ScenarioConfig(partial_responses=[506])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        header = _make_header(device, 511)
        responses = device.process_packet(header, None)

        ext_responses = _responses_of_type(responses, 512)
        assert len(ext_responses) == 2


class TestPartialResponsesTile:
    """partial_responses should truncate multi-packet tile responses."""

    def test_tile_partial(self):
        """5 tiles = 5 State64 packets; partial should return 1..4."""
        device = create_tile_device("d073d5400001", tile_count=5)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5400001", ScenarioConfig(partial_responses=[711])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        packet = Tile.Get64(
            tile_index=0,
            length=5,
            rect=TileBufferRect(fb_index=0, x=0, y=0, width=8),
        )
        header = _make_header(device, 707)
        responses = device.process_packet(header, packet)

        tile_responses = _responses_of_type(responses, 711)
        assert 1 <= len(tile_responses) < 5


class TestPartialResponsesDeterministic:
    """Verify partial truncation with mocked randomness."""

    def test_deterministic_truncation(self):
        """With randint mocked to return 3, should get exactly 3 packets."""
        device = create_multizone_light("d073d5500001", zone_count=120)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5500001", ScenarioConfig(partial_responses=[506])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        packet = MultiZone.GetColorZones(start_index=0, end_index=119)
        header = _make_header(device, 502)

        with patch("lifx_emulator.devices.device.random.randint", return_value=3):
            responses = device.process_packet(header, packet)

        mz_responses = _responses_of_type(responses, 506)
        assert len(mz_responses) == 3

    def test_partial_coexists_with_other_scenarios(self):
        """partial_responses should work alongside response_delays."""
        device = create_multizone_light("d073d5500002", zone_count=120)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5500002",
            ScenarioConfig(
                partial_responses=[506],
                response_delays={506: 0.01},
            ),
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        packet = MultiZone.GetColorZones(start_index=0, end_index=119)
        header = _make_header(device, 502)

        with patch("lifx_emulator.devices.device.random.randint", return_value=5):
            responses = device.process_packet(header, packet)

        mz_responses = _responses_of_type(responses, 506)
        assert len(mz_responses) == 5

    def test_randomness_varies(self):
        """Without mocking, repeated runs should not all return the same count."""
        device = create_multizone_light("d073d5500003", zone_count=120)
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_device_scenario(
            "d073d5500003", ScenarioConfig(partial_responses=[506])
        )
        device.scenario_manager = scenario_manager
        device.invalidate_scenario_cache()

        packet = MultiZone.GetColorZones(start_index=0, end_index=119)
        header = _make_header(device, 502)

        counts = set()
        for _ in range(20):
            responses = device.process_packet(header, packet)
            mz_responses = _responses_of_type(responses, 506)
            counts.add(len(mz_responses))

        # With 14 possible values (1..14), 20 runs should produce >1 unique count
        assert len(counts) > 1
