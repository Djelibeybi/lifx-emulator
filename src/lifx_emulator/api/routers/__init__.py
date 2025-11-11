"""API routers for LIFX emulator endpoints."""

from lifx_emulator.api.routers.devices import create_devices_router
from lifx_emulator.api.routers.monitoring import create_monitoring_router
from lifx_emulator.api.routers.scenarios import create_scenarios_router

__all__ = [
    "create_monitoring_router",
    "create_devices_router",
    "create_scenarios_router",
]
