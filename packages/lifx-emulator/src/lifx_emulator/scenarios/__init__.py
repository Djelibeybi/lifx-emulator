"""Scenario management module for LIFX emulator.

This module contains all scenario-related functionality including:
- Scenario manager (HierarchicalScenarioManager)
- Scenario models (ScenarioConfig)
- Scenario persistence (async file storage)
- Device type classification (get_device_type)
"""

from lifx_emulator.scenarios.manager import (
    HierarchicalScenarioManager,
    get_device_type,
)
from lifx_emulator.scenarios.models import ScenarioConfig
from lifx_emulator.scenarios.persistence import ScenarioPersistenceAsyncFile

__all__ = [
    "HierarchicalScenarioManager",
    "ScenarioConfig",
    "ScenarioPersistenceAsyncFile",
    "get_device_type",
]
