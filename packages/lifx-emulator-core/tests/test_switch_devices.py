"""Tests for LIFX Switch device emulation."""

from lifx_emulator.factories import create_device, create_switch
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Light


class TestSwitchFactory:
    """Test switch device factory functions."""

    def test_create_switch_default_product(self):
        """Test creating switch with default product ID (70)."""
        switch = create_switch("d073d7000001")

        assert switch.state.serial == "d073d7000001"
        assert switch.state.product == 70
        assert switch.state.has_relays is True
        assert switch.state.has_buttons is True
        assert switch.state.has_color is False
        assert switch.state.has_multizone is False
        assert switch.state.has_matrix is False

    def test_create_switch_custom_product(self):
        """Test creating switch with custom product ID."""
        switch = create_switch("d073d7000002", product_id=89)

        assert switch.state.serial == "d073d7000002"
        assert switch.state.product == 89
        assert switch.state.has_relays is True
        assert switch.state.has_buttons is True

    def test_create_switch_via_create_device(self):
        """Test creating switch via universal create_device factory."""
        switch = create_device(70, serial="d073d7000003")

        assert switch.state.serial == "d073d7000003"
        assert switch.state.product == 70
        assert switch.state.has_relays is True
        assert switch.state.has_buttons is True
        assert switch.state.has_color is False

    def test_all_switch_products(self):
        """Test creating all switch product IDs."""
        switch_pids = [70, 71, 89, 115, 116]

        for i, pid in enumerate(switch_pids):
            serial = f"d073d700{i + 1:04d}"  # e.g., d073d7000001, d073d7000002
            switch = create_device(pid, serial=serial)
            assert switch.state.has_relays is True
            assert switch.state.has_buttons is True
            assert switch.state.has_color is False
            assert switch.state.product == pid


class TestSwitchCapabilityFiltering:
    """Test capability-based packet filtering for switches."""

    def test_should_handle_device_packets(self):
        """Test switches handle Device.* packets (2-59)."""
        switch = create_switch("d073d7000001")

        # Device.* packets should be handled
        assert switch._should_handle_packet(23) is True  # GetLabel
        assert switch._should_handle_packet(32) is True  # GetVersion
        assert switch._should_handle_packet(45) is True  # Acknowledgement
        assert switch._should_handle_packet(58) is True  # EchoRequest

    def test_should_not_handle_light_packets(self):
        """Test switches reject Light.* packets (101-149)."""
        switch = create_switch("d073d7000001")

        # Light.* packets should be rejected
        assert switch._should_handle_packet(101) is False  # GetColor
        assert switch._should_handle_packet(102) is False  # SetColor
        assert switch._should_handle_packet(116) is False  # GetPower
        assert switch._should_handle_packet(117) is False  # SetPower
        assert switch._should_handle_packet(149) is False  # Last Light packet

    def test_should_not_handle_multizone_packets(self):
        """Test switches reject MultiZone.* packets (501-512)."""
        switch = create_switch("d073d7000001")

        # MultiZone.* packets should be rejected
        assert switch._should_handle_packet(501) is False  # SetColorZones
        assert switch._should_handle_packet(502) is False  # GetColorZones
        assert switch._should_handle_packet(510) is False  # SetExtendedColorZones
        assert switch._should_handle_packet(512) is False  # StateExtendedColorZones

    def test_should_not_handle_tile_packets(self):
        """Test switches reject Tile.* packets (701-720)."""
        switch = create_switch("d073d7000001")

        # Tile.* packets should be rejected
        assert switch._should_handle_packet(701) is False  # GetDeviceChain
        assert switch._should_handle_packet(707) is False  # GetTileState64
        assert switch._should_handle_packet(715) is False  # SetTileState64
        assert switch._should_handle_packet(720) is False  # Last Tile packet

    def test_color_light_handles_light_packets(self):
        """Test color lights (non-switches) handle Light.* packets."""
        from lifx_emulator.factories import create_color_light

        light = create_color_light("d073d5000001")

        # Color lights should handle Light.* packets
        assert light._should_handle_packet(101) is True  # GetColor
        assert light._should_handle_packet(102) is True  # SetColor
        assert light._should_handle_packet(116) is True  # GetPower


class TestSwitchStateUnhandled:
    """Test StateUnhandled response behavior for switches."""

    def test_switch_returns_state_unhandled_for_get_color(self):
        """Test switch returns StateUnhandled for Light.GetColor."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=1,
            tagged=False,
            pkt_type=101,  # Light.GetColor
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Should get StateUnhandled response
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 223  # StateUnhandled
        assert resp_packet.unhandled_type == 101  # GetColor was rejected

    def test_switch_returns_state_unhandled_for_set_color(self):
        """Test switch returns StateUnhandled for Light.SetColor."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=2,
            tagged=False,
            pkt_type=102,  # Light.SetColor
            size=36,
            ack_required=False,
            res_required=False,
        )

        packet = Light.SetColor(
            color={
                "hue": 0,
                "saturation": 65535,
                "brightness": 32768,
                "kelvin": 3500,
            },
            duration=0,
        )

        responses = switch.process_packet(header, packet)

        # Should get StateUnhandled response
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 223  # StateUnhandled
        assert resp_packet.unhandled_type == 102  # SetColor was rejected

    def test_switch_returns_state_unhandled_without_ack(self):
        """Test switch returns only StateUnhandled when no scenario targets acks.

        The server sends acks before calling process_packet, so the device
        should not include one in its response list by default.
        """
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=3,
            tagged=False,
            pkt_type=101,  # Light.GetColor
            size=36,
            ack_required=True,  # Request acknowledgement
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Should get only StateUnhandled (server handles ack)
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 223  # StateUnhandled
        assert resp_packet.unhandled_type == 101

    def test_switch_handles_device_packets_normally(self):
        """Test switch handles Device.* packets without StateUnhandled."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=4,
            tagged=False,
            pkt_type=32,  # Device.GetVersion
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Should get StateVersion response (not StateUnhandled)
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 33  # StateVersion (not 223)

    def test_switch_returns_state_unhandled_for_multizone(self):
        """Test switch returns StateUnhandled for MultiZone packets."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=5,
            tagged=False,
            pkt_type=502,  # MultiZone.GetColorZones
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Should get StateUnhandled response
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 223  # StateUnhandled
        assert resp_packet.unhandled_type == 502

    def test_switch_returns_state_unhandled_for_tile(self):
        """Test switch returns StateUnhandled for Tile packets."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=6,
            tagged=False,
            pkt_type=707,  # Tile.GetTileState64
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Should get StateUnhandled response
        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 223  # StateUnhandled
        assert resp_packet.unhandled_type == 707


class TestSwitchEdgeCases:
    """Test edge cases and boundary conditions for switch devices."""

    def test_switch_with_persistence(self):
        """Test switch device works with persistence enabled."""
        from lifx_emulator.devices import DevicePersistenceAsyncFile

        storage = DevicePersistenceAsyncFile()
        switch = create_switch("d073d7000001", storage=storage)

        assert switch.storage is storage
        assert switch.state.has_relays is True

    def test_switch_with_scenario_manager(self):
        """Test switch device works with scenario manager."""
        from lifx_emulator.scenarios import HierarchicalScenarioManager

        manager = HierarchicalScenarioManager()
        switch = create_switch("d073d7000001", scenario_manager=manager)

        assert switch.scenario_manager is manager
        assert switch.state.has_relays is True

    def test_switch_label_operations(self):
        """Test switch supports label get/set operations."""
        switch = create_switch("d073d7000001")

        # GetLabel
        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=7,
            tagged=False,
            pkt_type=23,  # GetLabel
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        assert len(responses) == 1
        resp_header, resp_packet = responses[0]
        assert resp_packet.PKT_TYPE == 25  # StateLabel

    def test_response_tuple_format(self):
        """Test switch responses use correct 2-tuple format."""
        switch = create_switch("d073d7000001")

        header = LifxHeader(
            source=12345,
            target=switch.state.get_target_bytes(),
            sequence=8,
            tagged=False,
            pkt_type=101,  # Light.GetColor
            size=36,
            ack_required=False,
            res_required=True,
        )

        responses = switch.process_packet(header, None)

        # Verify all responses are 2-tuples (header, packet)
        for response in responses:
            assert len(response) == 2
            assert isinstance(response[0], LifxHeader)
            # Second element should be a packet object (has PKT_TYPE)
            assert hasattr(response[1], "PKT_TYPE")
