"""Persistence layer for scenario configurations.

This module provides JSON serialization and deserialization for scenarios,
allowing them to persist across emulator restarts.
"""

import json
import logging
from pathlib import Path
from typing import Any

from lifx_emulator.scenario_manager import HierarchicalScenarioManager, ScenarioConfig

logger = logging.getLogger(__name__)


class ScenarioPersistence:
    """Handles scenario persistence to disk.

    Scenarios are stored in JSON format at ~/.lifx-emulator/scenarios.json
    with separate sections for each scope level.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize scenario persistence.

        Args:
            storage_path: Directory to store scenarios.json
                         Defaults to ~/.lifx-emulator
        """
        if storage_path is None:
            storage_path = Path.home() / ".lifx-emulator"

        self.storage_path = Path(storage_path)
        self.scenario_file = self.storage_path / "scenarios.json"

    def load(self) -> HierarchicalScenarioManager:
        """Load scenarios from disk.

        Returns:
            HierarchicalScenarioManager with loaded scenarios.
            If file doesn't exist, returns empty manager.
        """
        manager = HierarchicalScenarioManager()

        if not self.scenario_file.exists():
            logger.debug("No scenario file found at %s", self.scenario_file)
            return manager

        try:
            with open(self.scenario_file) as f:
                data = json.load(f)

            # Load global scenario
            if "global" in data and data["global"]:
                manager.global_scenario = ScenarioConfig.from_dict(data["global"])
                logger.debug("Loaded global scenario")

            # Load device-specific scenarios
            for serial, config_data in data.get("devices", {}).items():
                manager.device_scenarios[serial] = ScenarioConfig.from_dict(config_data)
            if manager.device_scenarios:
                logger.debug(
                    "Loaded %s device scenario(s)", len(manager.device_scenarios)
                )

            # Load type-specific scenarios
            for device_type, config_data in data.get("types", {}).items():
                manager.type_scenarios[device_type] = ScenarioConfig.from_dict(
                    config_data
                )
            if manager.type_scenarios:
                logger.debug("Loaded %s type scenario(s)", len(manager.type_scenarios))

            # Load location-specific scenarios
            for location, config_data in data.get("locations", {}).items():
                manager.location_scenarios[location] = ScenarioConfig.from_dict(
                    config_data
                )
            if manager.location_scenarios:
                logger.debug(
                    "Loaded %s location scenario(s)", len(manager.location_scenarios)
                )

            # Load group-specific scenarios
            for group, config_data in data.get("groups", {}).items():
                manager.group_scenarios[group] = ScenarioConfig.from_dict(config_data)
            if manager.group_scenarios:
                logger.debug(
                    "Loaded %s group scenario(s)", len(manager.group_scenarios)
                )

            logger.info("Loaded scenarios from %s", self.scenario_file)
            return manager

        except json.JSONDecodeError as e:
            logger.error("Failed to parse scenario file %s: %s", self.scenario_file, e)
            return manager
        except Exception as e:
            logger.error("Failed to load scenarios from %s: %s", self.scenario_file, e)
            return manager

    def save(self, manager: HierarchicalScenarioManager) -> None:
        """Save scenarios to disk.

        Args:
            manager: HierarchicalScenarioManager to save
        """

        # Convert response_delays keys to strings for JSON serialization
        def _serialize_config(config: ScenarioConfig) -> dict[str, Any]:
            """Convert ScenarioConfig to JSON-serializable dict."""
            data = config.to_dict()
            # Convert int keys in response_delays to strings
            if data.get("response_delays"):
                data["response_delays"] = {
                    str(k): v for k, v in data["response_delays"].items()
                }
            return data

        data: dict[str, Any] = {
            "global": _serialize_config(manager.global_scenario),
            "devices": {
                serial: _serialize_config(config)
                for serial, config in manager.device_scenarios.items()
            },
            "types": {
                device_type: _serialize_config(config)
                for device_type, config in manager.type_scenarios.items()
            },
            "locations": {
                location: _serialize_config(config)
                for location, config in manager.location_scenarios.items()
            },
            "groups": {
                group: _serialize_config(config)
                for group, config in manager.group_scenarios.items()
            },
        }

        try:
            # Create directory if it doesn't exist
            self.storage_path.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.scenario_file.with_suffix(".json.tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            temp_file.replace(self.scenario_file)

            logger.info("Saved scenarios to %s", self.scenario_file)

        except Exception as e:
            logger.error("Failed to save scenarios to %s: %s", self.scenario_file, e)
            raise

    def delete(self) -> bool:
        """Delete the scenario file.

        Returns:
            True if file was deleted, False if it didn't exist
        """
        if self.scenario_file.exists():
            try:
                self.scenario_file.unlink()
                logger.info("Deleted scenario file %s", self.scenario_file)
                return True
            except Exception as e:
                logger.error("Failed to delete scenario file: %s", e)
                raise
        return False


def _deserialize_response_delays(data: dict[str, Any]) -> dict[int, float]:
    """Convert string keys back to integers for response_delays.

    JSON only supports string keys, so we convert them back to ints.

    Args:
        data: Dictionary with string keys

    Returns:
        Dictionary with integer keys
    """
    if not data:
        return {}
    return {int(k): v for k, v in data.items()}


# Monkey-patch ScenarioConfig.from_dict to handle string keys
_original_from_dict = ScenarioConfig.from_dict


@classmethod
def _from_dict_with_conversion(cls, data: dict[str, Any]) -> ScenarioConfig:
    """Create from dictionary with int key conversion."""
    # Convert response_delays string keys to ints
    if "response_delays" in data and data["response_delays"]:
        data = data.copy()
        data["response_delays"] = _deserialize_response_delays(data["response_delays"])
    return _original_from_dict(data)


ScenarioConfig.from_dict = _from_dict_with_conversion  # type: ignore
