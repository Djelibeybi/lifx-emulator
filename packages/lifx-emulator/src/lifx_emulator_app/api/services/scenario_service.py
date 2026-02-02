"""Scenario management business logic service.

Separates API handlers from server operations, providing a clean service layer
for scenario CRUD operations across all scope levels (global, device, type,
location, group).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from lifx_emulator.scenarios import ScenarioConfig
    from lifx_emulator.server import EmulatedLifxServer

logger = logging.getLogger(__name__)

Scope = Literal["device", "type", "location", "group"]

_SCOPE_METHODS: dict[Scope, tuple[str, str, str]] = {
    "device": ("get_device_scenario", "set_device_scenario", "delete_device_scenario"),
    "type": ("get_type_scenario", "set_type_scenario", "delete_type_scenario"),
    "location": (
        "get_location_scenario",
        "set_location_scenario",
        "delete_location_scenario",
    ),
    "group": ("get_group_scenario", "set_group_scenario", "delete_group_scenario"),
}


class ScenarioNotFoundError(Exception):
    """Raised when a scenario is not set for the given scope and identifier."""

    def __init__(self, scope: str, identifier: str):
        super().__init__(f"No scenario set for {scope} {identifier}")
        self.scope = scope
        self.identifier = identifier


class InvalidDeviceSerialError(Exception):
    """Raised when a device serial is not a valid 12-character hex string."""

    def __init__(self, serial: str):
        super().__init__(f"Invalid device serial format: {serial}.")
        self.serial = serial


class ScenarioService:
    """Service for managing scenario configurations across all scope levels.

    Wraps the HierarchicalScenarioManager and handles cache invalidation
    and persistence after each mutation.
    """

    def __init__(self, server: EmulatedLifxServer):
        self.server = server

    async def _persist(self) -> None:
        """Invalidate device scenario caches and persist to storage."""
        self.server.invalidate_all_scenario_caches()
        if self.server.scenario_persistence:
            await self.server.scenario_persistence.save(self.server.scenario_manager)

    def get_global_scenario(self) -> ScenarioConfig:
        """Return the global scenario configuration."""
        return self.server.scenario_manager.get_global_scenario()

    async def set_global_scenario(self, config: ScenarioConfig) -> None:
        """Set the global scenario and persist."""
        self.server.scenario_manager.set_global_scenario(config)
        await self._persist()
        logger.info("Set global scenario")

    async def clear_global_scenario(self) -> None:
        """Clear the global scenario and persist."""
        self.server.scenario_manager.clear_global_scenario()
        await self._persist()
        logger.info("Cleared global scenario")

    def get_scope_scenario(self, scope: Scope, identifier: str) -> ScenarioConfig:
        """Return the scenario for a given scope and identifier.

        Raises:
            ScenarioNotFoundError: If no scenario is set.
        """
        getter, _, _ = _SCOPE_METHODS[scope]
        config = getattr(self.server.scenario_manager, getter)(identifier)
        if config is None:
            raise ScenarioNotFoundError(scope, identifier)
        return config

    async def set_scope_scenario(
        self, scope: Scope, identifier: str, config: ScenarioConfig
    ) -> None:
        """Set a scenario for a given scope and identifier, then persist.

        Raises:
            InvalidDeviceSerialError: If scope is "device" and the serial
                is not a valid 12-character hex string.
        """
        if scope == "device" and not self._is_valid_serial(identifier):
            raise InvalidDeviceSerialError(identifier)

        _, setter, _ = _SCOPE_METHODS[scope]
        getattr(self.server.scenario_manager, setter)(identifier, config)
        await self._persist()
        logger.info("Set %s scenario for %s", scope, identifier)

    async def delete_scope_scenario(self, scope: Scope, identifier: str) -> None:
        """Delete a scenario for a given scope and identifier, then persist.

        Raises:
            ScenarioNotFoundError: If no scenario is set.
        """
        _, _, deleter = _SCOPE_METHODS[scope]
        if not getattr(self.server.scenario_manager, deleter)(identifier):
            raise ScenarioNotFoundError(scope, identifier)
        await self._persist()
        logger.info("Deleted %s scenario for %s", scope, identifier)

    @staticmethod
    def _is_valid_serial(serial: str) -> bool:
        """Check that serial is a 12-character hex string."""
        return len(serial) == 12 and all(c in "0123456789abcdefABCDEF" for c in serial)
