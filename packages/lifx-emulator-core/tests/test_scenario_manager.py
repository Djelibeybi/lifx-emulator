"""Tests for hierarchical scenario manager."""

from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.scenarios.manager import (
    HierarchicalScenarioManager,
    ScenarioConfig,
    get_device_type,
)


class TestScenarioConfig:
    """Test ScenarioConfig dataclass."""

    def test_scenario_config_defaults(self):
        """Test default values for ScenarioConfig."""
        config = ScenarioConfig()
        assert config.drop_packets == {}
        assert config.response_delays == {}
        assert config.malformed_packets == []
        assert config.invalid_field_values == []
        assert config.firmware_version is None
        assert config.partial_responses == []
        assert config.send_unhandled is False

    def test_scenario_config_to_dict(self):
        """Test conversion to dictionary."""
        config = ScenarioConfig(
            drop_packets={101: 1.0, 102: 0.6},
            response_delays={101: 0.5},
            firmware_version=(3, 70),
        )
        result = config.to_dict()
        assert result["drop_packets"] == {"101": 1.0, "102": 0.6}
        assert result["response_delays"] == {"101": 0.5}
        assert result["firmware_version"] == (3, 70)

    def test_scenario_config_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "drop_packets": {"101": 1.0, "102": 0.6},
            "response_delays": {"101": 0.5},
            "malformed_packets": [103],
            "firmware_version": [3, 70],
            "send_unhandled": True,
        }
        config = ScenarioConfig.from_dict(data)
        assert config.drop_packets == {101: 1.0, 102: 0.6}
        assert config.response_delays == {101: 0.5}
        assert config.malformed_packets == [103]
        assert config.firmware_version == (3, 70)
        assert config.send_unhandled is True

    def test_scenario_config_from_dict_with_defaults(self):
        """Test creation from dictionary with missing fields."""
        data = {"drop_packets": {"101": 1.0}}
        config = ScenarioConfig.from_dict(data)
        assert config.drop_packets == {101: 1.0}
        assert config.response_delays == {}
        assert config.malformed_packets == []


class TestGetDeviceType:
    """Test device type detection."""

    def test_get_device_type_color(self):
        """Test detection of color device."""
        device = create_color_light(serial="d073d5000001")
        assert get_device_type(device) == "color"

    def test_get_device_type_multizone(self):
        """Test detection of multizone device."""
        device = create_multizone_light(serial="d073d5000001", extended_multizone=False)
        assert get_device_type(device) == "multizone"

    def test_get_device_type_extended_multizone(self):
        """Test detection of extended multizone device."""
        device = create_multizone_light(serial="d073d5000001", extended_multizone=True)
        assert get_device_type(device) == "extended_multizone"

    def test_get_device_type_matrix(self):
        """Test detection of matrix device."""
        device = create_tile_device(serial="d073d5000001")
        assert get_device_type(device) == "matrix"


class TestHierarchicalScenarioManager:
    """Test HierarchicalScenarioManager class."""

    def test_manager_initialization(self):
        """Test manager starts with empty scenarios."""
        manager = HierarchicalScenarioManager()
        assert len(manager.device_scenarios) == 0
        assert len(manager.type_scenarios) == 0
        assert len(manager.location_scenarios) == 0
        assert len(manager.group_scenarios) == 0
        assert manager.global_scenario.drop_packets == {}

    def test_set_device_scenario(self):
        """Test setting device-specific scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(drop_packets={101: 1.0, 102: 0.6})
        manager.set_device_scenario("d073d5000001", config)
        assert "d073d5000001" in manager.device_scenarios
        assert manager.device_scenarios["d073d5000001"].drop_packets == {
            101: 1.0,
            102: 0.6,
        }

    def test_set_type_scenario(self):
        """Test setting type-specific scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(response_delays={101: 0.5})
        manager.set_type_scenario("multizone", config)
        assert "multizone" in manager.type_scenarios
        assert manager.type_scenarios["multizone"].response_delays == {101: 0.5}

    def test_set_location_scenario(self):
        """Test setting location-specific scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(malformed_packets=[103])
        manager.set_location_scenario("Kitchen", config)
        assert "Kitchen" in manager.location_scenarios
        assert manager.location_scenarios["Kitchen"].malformed_packets == [103]

    def test_set_group_scenario(self):
        """Test setting group-specific scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(invalid_field_values=[104])
        manager.set_group_scenario("Bedroom", config)
        assert "Bedroom" in manager.group_scenarios
        assert manager.group_scenarios["Bedroom"].invalid_field_values == [104]

    def test_set_global_scenario(self):
        """Test setting global scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(firmware_version=(3, 70))
        manager.set_global_scenario(config)
        assert manager.global_scenario.firmware_version == (3, 70)

    def test_delete_device_scenario(self):
        """Test deleting device-specific scenario."""
        manager = HierarchicalScenarioManager()
        config = ScenarioConfig(drop_packets={101: 1.0})
        manager.set_device_scenario("d073d5000001", config)
        assert manager.delete_device_scenario("d073d5000001") is True
        assert "d073d5000001" not in manager.device_scenarios
        assert manager.delete_device_scenario("d073d5000001") is False

    def test_clear_global_scenario(self):
        """Test clearing global scenario."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
        manager.clear_global_scenario()
        assert manager.global_scenario.drop_packets == {}


class TestScenarioPrecedence:
    """Test scenario precedence and merging."""

    def test_device_overrides_global(self):
        """Test device-specific scenario has highest priority."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
        manager.set_device_scenario(
            "d073d5000001", ScenarioConfig(drop_packets={102: 0.6})
        )

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="color",
            location="",
            group="",
        )

        # Both should be present (merged)
        assert 101 in merged.drop_packets
        assert 102 in merged.drop_packets

    def test_type_overrides_global(self):
        """Test type-specific overrides global."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(response_delays={101: 1.0}))
        manager.set_type_scenario(
            "multizone", ScenarioConfig(response_delays={101: 0.5})
        )

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="multizone",
            location="",
            group="",
        )

        # Later value overrides (type > global)
        assert merged.response_delays[101] == 0.5

    def test_full_precedence_chain(self):
        """Test complete precedence: device > type > location > group > global."""
        manager = HierarchicalScenarioManager()

        # Set scenarios at all levels
        manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
        manager.set_group_scenario("MyGroup", ScenarioConfig(drop_packets={102: 0.8}))
        manager.set_location_scenario(
            "Kitchen", ScenarioConfig(drop_packets={103: 0.6})
        )
        manager.set_type_scenario("multizone", ScenarioConfig(drop_packets={104: 0.4}))
        manager.set_device_scenario(
            "d073d5000001", ScenarioConfig(drop_packets={105: 0.2})
        )

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="multizone",
            location="Kitchen",
            group="MyGroup",
        )

        # All should be present (merged)
        assert set(merged.drop_packets.keys()) == {101, 102, 103, 104, 105}

    def test_delay_override_precedence(self):
        """Test delays are overridden by more specific scopes."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(
            ScenarioConfig(response_delays={101: 1.0, 102: 2.0})
        )
        manager.set_type_scenario(
            "multizone", ScenarioConfig(response_delays={101: 0.5})
        )

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="multizone",
            location="",
            group="",
        )

        # Packet 101 overridden, 102 inherited
        assert merged.response_delays[101] == 0.5
        assert merged.response_delays[102] == 2.0

    def test_firmware_version_override(self):
        """Test firmware version uses most specific value."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(firmware_version=(2, 80)))
        manager.set_device_scenario(
            "d073d5000001", ScenarioConfig(firmware_version=(3, 70))
        )

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="color",
            location="",
            group="",
        )

        # Device-specific wins
        assert merged.firmware_version == (3, 70)

    def test_send_unhandled_or_logic(self):
        """Test send_unhandled uses OR logic (any True = True)."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(send_unhandled=False))
        manager.set_device_scenario("d073d5000001", ScenarioConfig(send_unhandled=True))

        merged = manager.get_scenario_for_device(
            serial="d073d5000001",
            device_type="color",
            location="",
            group="",
        )

        # True wins
        assert merged.send_unhandled is True


class TestScenarioManagerMethods:
    """Test scenario manager helper methods."""

    def test_should_respond_always_drop(self):
        """Test packet drop checking with 100% drop rate."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(drop_packets={101: 1.0, 102: 1.0})

        # With drop_rate=1.0, should always return False (drop)
        for _ in range(10):
            assert manager.should_respond(101, scenario) is False
            assert manager.should_respond(102, scenario) is False
        assert manager.should_respond(103, scenario) is True

    def test_should_respond_probabilistic(self):
        """Test probabilistic packet dropping."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(drop_packets={101: 0.5})

        # With drop_rate=0.5, approximately 50% should be dropped
        responses = [manager.should_respond(101, scenario) for _ in range(100)]
        dropped = responses.count(False)

        # Should be roughly 50%, allowing 30-70% range for randomness
        assert 30 <= dropped <= 70

    def test_should_respond_never_drop(self):
        """Test with very low drop rate."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(drop_packets={101: 0.1})

        # With drop_rate=0.1, approximately 10% should be dropped
        responses = [manager.should_respond(101, scenario) for _ in range(100)]
        dropped = responses.count(False)

        # Should be roughly 10%, allowing 0-20% range for randomness
        assert 0 <= dropped <= 20

    def test_get_response_delay(self):
        """Test response delay retrieval."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(response_delays={101: 0.5, 102: 1.0})

        assert manager.get_response_delay(101, scenario) == 0.5
        assert manager.get_response_delay(102, scenario) == 1.0
        assert manager.get_response_delay(103, scenario) == 0.0

    def test_should_send_malformed(self):
        """Test malformed packet checking."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(malformed_packets=[103])

        assert manager.should_send_malformed(103, scenario) is True
        assert manager.should_send_malformed(104, scenario) is False

    def test_should_send_invalid_fields(self):
        """Test invalid field checking."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(invalid_field_values=[104])

        assert manager.should_send_invalid_fields(104, scenario) is True
        assert manager.should_send_invalid_fields(105, scenario) is False

    def test_get_firmware_version_override(self):
        """Test firmware version retrieval."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(firmware_version=(3, 70))

        assert manager.get_firmware_version_override(scenario) == (3, 70)

    def test_should_send_partial_response(self):
        """Test partial response checking."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(partial_responses=[505, 506])

        assert manager.should_send_partial_response(505, scenario) is True
        assert manager.should_send_partial_response(506, scenario) is True
        assert manager.should_send_partial_response(507, scenario) is False

    def test_should_send_unhandled(self):
        """Test unhandled packet checking."""
        manager = HierarchicalScenarioManager()
        scenario = ScenarioConfig(send_unhandled=True)

        assert manager.should_send_unhandled(scenario) is True

        scenario.send_unhandled = False
        assert manager.should_send_unhandled(scenario) is False


class TestDeviceIntegration:
    """Test integration with EmulatedLifxDevice."""

    def test_device_uses_hierarchical_manager(self):
        """Test device can use HierarchicalScenarioManager."""
        manager = HierarchicalScenarioManager()
        manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))

        device = create_color_light(serial="d073d5000001", scenario_manager=manager)

        # Device should resolve scenario correctly
        scenario = device._get_resolved_scenario()
        assert 101 in scenario.drop_packets

    def test_device_scenario_caching(self):
        """Test device caches resolved scenario."""
        manager = HierarchicalScenarioManager()
        device = create_color_light(serial="d073d5000001", scenario_manager=manager)

        # First call resolves and caches
        scenario1 = device._get_resolved_scenario()
        # Second call returns cached value
        scenario2 = device._get_resolved_scenario()

        assert scenario1 is scenario2  # Same object

    def test_device_invalidate_cache(self):
        """Test cache invalidation."""
        manager = HierarchicalScenarioManager()
        device = create_color_light(serial="d073d5000001", scenario_manager=manager)

        # Get and cache scenario
        scenario1 = device._get_resolved_scenario()

        # Update scenario
        manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
        device.invalidate_scenario_cache()

        # Get new scenario
        scenario2 = device._get_resolved_scenario()

        assert scenario1 is not scenario2
        assert 101 in scenario2.drop_packets

    def test_device_with_location_and_group(self):
        """Test scenario resolution uses device location and group."""
        manager = HierarchicalScenarioManager()
        manager.set_location_scenario(
            "Kitchen", ScenarioConfig(drop_packets={101: 1.0})
        )
        manager.set_group_scenario("Main", ScenarioConfig(drop_packets={102: 0.8}))

        device = create_color_light(serial="d073d5000001", scenario_manager=manager)
        device.state.location_label = "Kitchen"
        device.state.group_label = "Main"

        scenario = device._get_resolved_scenario()

        assert 101 in scenario.drop_packets
        assert 102 in scenario.drop_packets
