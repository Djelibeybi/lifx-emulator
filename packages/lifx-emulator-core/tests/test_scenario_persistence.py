"""Tests for scenario persistence."""

import json
import tempfile
from pathlib import Path

from lifx_emulator.scenarios.manager import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator.scenarios.persistence import ScenarioPersistenceAsyncFile


class TestScenarioPersistenceAsyncFile:
    """Test scenario persistence to disk."""

    async def test_persistence_initialization(self):
        """Test persistence initializes with correct paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))
            assert persistence.storage_path == Path(tmpdir)
            assert persistence.scenario_file == Path(tmpdir) / "scenarios.json"

    async def test_save_empty_manager(self):
        """Test saving empty scenario manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))
            manager = HierarchicalScenarioManager()

            await persistence.save(manager)

            assert persistence.scenario_file.exists()
            with open(persistence.scenario_file) as f:
                data = json.load(f)

            assert data["global"] == {
                "drop_packets": {},
                "response_delays": {},
                "malformed_packets": [],
                "invalid_field_values": [],
                "firmware_version": None,
                "partial_responses": [],
                "send_unhandled": False,
            }
            assert data["devices"] == {}
            assert data["types"] == {}
            assert data["locations"] == {}
            assert data["groups"] == {}

    async def test_save_and_load_global_scenario(self):
        """Test saving and loading global scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create and save
            manager1 = HierarchicalScenarioManager()
            manager1.set_global_scenario(
                ScenarioConfig(
                    drop_packets={101: 1.0, 102: 0.5},
                    response_delays={101: 0.5, 102: 1.0},
                    firmware_version=(3, 70),
                )
            )
            await persistence.save(manager1)

            # Load
            manager2 = await persistence.load()

            assert manager2.global_scenario.drop_packets == {101: 1.0, 102: 0.5}
            assert manager2.global_scenario.response_delays == {101: 0.5, 102: 1.0}
            assert manager2.global_scenario.firmware_version == (3, 70)

    async def test_save_and_load_device_scenarios(self):
        """Test saving and loading device-specific scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create and save
            manager1 = HierarchicalScenarioManager()
            manager1.set_device_scenario(
                "d073d5000001", ScenarioConfig(drop_packets={101: 1.0})
            )
            manager1.set_device_scenario(
                "d073d5000002", ScenarioConfig(malformed_packets=[103])
            )
            await persistence.save(manager1)

            # Load
            manager2 = await persistence.load()

            assert "d073d5000001" in manager2.device_scenarios
            assert manager2.device_scenarios["d073d5000001"].drop_packets == {101: 1.0}
            assert "d073d5000002" in manager2.device_scenarios
            assert manager2.device_scenarios["d073d5000002"].malformed_packets == [103]

    async def test_save_and_load_type_scenarios(self):
        """Test saving and loading type-specific scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create and save
            manager1 = HierarchicalScenarioManager()
            manager1.set_type_scenario(
                "multizone", ScenarioConfig(response_delays={502: 0.5})
            )
            manager1.set_type_scenario(
                "matrix", ScenarioConfig(drop_packets={701: 1.0})
            )
            await persistence.save(manager1)

            # Load
            manager2 = await persistence.load()

            assert "multizone" in manager2.type_scenarios
            assert manager2.type_scenarios["multizone"].response_delays == {502: 0.5}
            assert "matrix" in manager2.type_scenarios
            assert manager2.type_scenarios["matrix"].drop_packets == {701: 1.0}

    async def test_save_and_load_location_scenarios(self):
        """Test saving and loading location-specific scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create and save
            manager1 = HierarchicalScenarioManager()
            manager1.set_location_scenario(
                "Kitchen", ScenarioConfig(drop_packets={116: 1.0})
            )
            await persistence.save(manager1)

            # Load
            manager2 = await persistence.load()

            assert "Kitchen" in manager2.location_scenarios
            assert manager2.location_scenarios["Kitchen"].drop_packets == {116: 1.0}

    async def test_save_and_load_group_scenarios(self):
        """Test saving and loading group-specific scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create and save
            manager1 = HierarchicalScenarioManager()
            manager1.set_group_scenario("Bedroom", ScenarioConfig(send_unhandled=True))
            await persistence.save(manager1)

            # Load
            manager2 = await persistence.load()

            assert "Bedroom" in manager2.group_scenarios
            assert manager2.group_scenarios["Bedroom"].send_unhandled is True

    async def test_save_and_load_all_scopes(self):
        """Test saving and loading scenarios at all scopes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create complex scenario setup
            manager1 = HierarchicalScenarioManager()
            manager1.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
            manager1.set_device_scenario(
                "d073d5000001", ScenarioConfig(drop_packets={102: 0.5})
            )
            manager1.set_type_scenario(
                "multizone", ScenarioConfig(response_delays={502: 0.5})
            )
            manager1.set_location_scenario(
                "Kitchen", ScenarioConfig(malformed_packets=[103])
            )
            manager1.set_group_scenario(
                "Main", ScenarioConfig(invalid_field_values=[104])
            )
            await persistence.save(manager1)

            # Load and verify
            manager2 = await persistence.load()

            assert manager2.global_scenario.drop_packets == {101: 1.0}
            assert manager2.device_scenarios["d073d5000001"].drop_packets == {102: 0.5}
            assert manager2.type_scenarios["multizone"].response_delays == {502: 0.5}
            assert manager2.location_scenarios["Kitchen"].malformed_packets == [103]
            assert manager2.group_scenarios["Main"].invalid_field_values == [104]

    async def test_load_nonexistent_file(self):
        """Test loading when file doesn't exist returns empty manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))
            manager = await persistence.load()

            assert len(manager.device_scenarios) == 0
            assert len(manager.type_scenarios) == 0
            assert len(manager.location_scenarios) == 0
            assert len(manager.group_scenarios) == 0
            assert manager.global_scenario.drop_packets == {}

    async def test_load_invalid_json(self):
        """Test loading invalid JSON returns empty manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Write invalid JSON
            persistence.storage_path.mkdir(parents=True, exist_ok=True)
            with open(persistence.scenario_file, "w") as f:
                f.write("{ invalid json }")

            # Should return empty manager without crashing
            manager = await persistence.load()
            assert len(manager.device_scenarios) == 0

    async def test_delete_scenario_file(self):
        """Test deleting scenario file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create file
            manager = HierarchicalScenarioManager()
            manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))
            await persistence.save(manager)
            assert persistence.scenario_file.exists()

            # Delete
            assert await persistence.delete() is True
            assert not persistence.scenario_file.exists()

            # Delete again (idempotent)
            assert await persistence.delete() is False

    async def test_atomic_save(self):
        """Test that save is atomic (uses temp file + rename)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))
            manager = HierarchicalScenarioManager()
            manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))

            await persistence.save(manager)

            # Temp file should not exist after save
            temp_file = persistence.scenario_file.with_suffix(".json.tmp")
            assert not temp_file.exists()
            assert persistence.scenario_file.exists()

    async def test_response_delays_key_conversion(self):
        """Test that response_delays integer keys survive serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = ScenarioPersistenceAsyncFile(Path(tmpdir))

            # Create with integer keys
            manager1 = HierarchicalScenarioManager()
            manager1.set_global_scenario(
                ScenarioConfig(
                    response_delays={
                        101: 0.5,
                        102: 1.0,
                        999: 2.5,
                    }
                )
            )
            await persistence.save(manager1)

            # Verify JSON has string keys
            with open(persistence.scenario_file) as f:
                data = json.load(f)
            assert "101" in data["global"]["response_delays"]
            assert "102" in data["global"]["response_delays"]
            assert "999" in data["global"]["response_delays"]

            # Load and verify integer keys restored
            manager2 = await persistence.load()
            assert 101 in manager2.global_scenario.response_delays
            assert 102 in manager2.global_scenario.response_delays
            assert 999 in manager2.global_scenario.response_delays
            assert manager2.global_scenario.response_delays[101] == 0.5
            assert manager2.global_scenario.response_delays[102] == 1.0
            assert manager2.global_scenario.response_delays[999] == 2.5
