"""Async persistent storage for scenario configurations.

This module provides async JSON serialization and deserialization for scenarios,
allowing them to persist across emulator restarts without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from lifx_emulator.scenarios.manager import HierarchicalScenarioManager, ScenarioConfig

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path.home() / ".lifx-emulator"


class ScenarioPersistenceAsyncFile:
    """Async persistent storage for scenario configurations.

    Non-blocking asynchronous I/O for scenario persistence.
    Scenarios are stored in JSON format at ~/.lifx-emulator/scenarios.json
    with separate sections for each scope level.

    Features:
    - Async I/O operations (no event loop blocking)
    - Executor-based I/O for file operations
    - Atomic writes (write to temp file, then rename)
    - Graceful error handling and recovery
    """

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize async scenario persistence.

        Args:
            storage_path: Directory to store scenarios.json
                         Defaults to ~/.lifx-emulator
        """
        if storage_path is None:
            storage_path = DEFAULT_STORAGE_DIR

        self.storage_path = Path(storage_path)
        self.scenario_file = self.storage_path / "scenarios.json"

        # Single-thread executor for serialized I/O operations
        self.executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="scenario-io"
        )

        logger.debug("Async scenario storage initialized at %s", self.storage_path)

    async def load(self) -> HierarchicalScenarioManager:
        """Load scenarios from disk (async).

        Returns:
            HierarchicalScenarioManager with loaded scenarios.
            If file doesn't exist, returns empty manager.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._sync_load)

    def _sync_load(self) -> HierarchicalScenarioManager:
        """Synchronous load operation (runs in executor).

        Returns:
            HierarchicalScenarioManager with loaded scenarios
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
                manager.global_scenario = ScenarioConfig.model_validate(data["global"])
                logger.debug("Loaded global scenario")

            # Load device-specific scenarios
            for serial, config_data in data.get("devices", {}).items():
                manager.device_scenarios[serial] = ScenarioConfig.model_validate(
                    config_data
                )
            if manager.device_scenarios:
                logger.debug(
                    "Loaded %s device scenario(s)", len(manager.device_scenarios)
                )

            # Load type-specific scenarios
            for device_type, config_data in data.get("types", {}).items():
                manager.type_scenarios[device_type] = ScenarioConfig.model_validate(
                    config_data
                )
            if manager.type_scenarios:
                logger.debug("Loaded %s type scenario(s)", len(manager.type_scenarios))

            # Load location-specific scenarios
            for location, config_data in data.get("locations", {}).items():
                manager.location_scenarios[location] = ScenarioConfig.model_validate(
                    config_data
                )
            if manager.location_scenarios:
                logger.debug(
                    "Loaded %s location scenario(s)", len(manager.location_scenarios)
                )

            # Load group-specific scenarios
            for group, config_data in data.get("groups", {}).items():
                manager.group_scenarios[group] = ScenarioConfig.model_validate(
                    config_data
                )
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

    async def save(self, manager: HierarchicalScenarioManager) -> None:
        """Save scenarios to disk (async).

        Args:
            manager: HierarchicalScenarioManager to save
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self._sync_save, manager)

    def _sync_save(self, manager: HierarchicalScenarioManager) -> None:
        """Synchronous save operation (runs in executor).

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

    async def delete(self) -> bool:
        """Delete the scenario file (async).

        Returns:
            True if file was deleted, False if it didn't exist
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._sync_delete)

    def _sync_delete(self) -> bool:
        """Synchronous delete operation (runs in executor).

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

    async def shutdown(self) -> None:
        """Gracefully shutdown executor.

        This should be called before the application exits.
        """
        logger.info("Shutting down async scenario storage...")

        # Shutdown executor (non-blocking to avoid hanging on Windows)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.executor.shutdown, True)

        logger.info("Async scenario storage shutdown complete")


# Note: Pydantic's field_validators in ScenarioConfig handle string-to-int
# key conversion automatically, so no additional deserialization logic is needed.
