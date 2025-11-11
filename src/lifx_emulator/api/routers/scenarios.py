"""Scenario management endpoints for testing LIFX protocol behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator.api.models import ScenarioConfig, ScenarioResponse


def _validate_device_serial(serial: str) -> bool:
    """Validate that serial is a properly formatted 12-character hex string."""
    return len(serial) == 12 and all(c in "0123456789abcdefABCDEF" for c in serial)


def _add_global_endpoints(router: APIRouter, server: EmulatedLifxServer, persist_fn):
    """Add global scenario endpoints to router."""

    @router.get(
        "/global",
        response_model=ScenarioResponse,
        summary="Get global scenario",
        description=(
            "Returns the global scenario that applies to all devices as a baseline."
        ),
    )
    async def get_global_scenario():
        config = server.scenario_manager.get_global_scenario()
        return ScenarioResponse(scope="global", identifier=None, scenario=config)

    @router.put(
        "/global",
        response_model=ScenarioResponse,
        summary="Set global scenario",
        description=(
            "Sets the global scenario that applies to all devices as a baseline."
        ),
    )
    async def set_global_scenario(scenario: ScenarioConfig):
        server.scenario_manager.set_global_scenario(scenario)
        await persist_fn()
        return ScenarioResponse(scope="global", identifier=None, scenario=scenario)

    @router.delete(
        "/global",
        status_code=204,
        summary="Clear global scenario",
        description="Clears the global scenario, resetting it to defaults.",
    )
    async def clear_global_scenario():
        server.scenario_manager.clear_global_scenario()
        await persist_fn()


def _add_device_endpoints(router: APIRouter, server: EmulatedLifxServer, persist_fn):
    """Add device-specific scenario endpoints to router."""

    @router.get(
        "/devices/{serial}",
        response_model=ScenarioResponse,
        summary="Get device scenario",
        description="Returns the scenario for a specific device by serial number.",
        responses={404: {"description": "Device scenario not set"}},
    )
    async def get_device_scenario(serial: str):
        config = server.scenario_manager.get_device_scenario(serial)
        if config is None:
            raise HTTPException(404, f"No scenario set for device {serial}")
        return ScenarioResponse(scope="device", identifier=serial, scenario=config)

    @router.put(
        "/devices/{serial}",
        response_model=ScenarioResponse,
        summary="Set device scenario",
        description="Sets the scenario for a specific device by serial number.",
        responses={404: {"description": "Invalid device serial format"}},
    )
    async def set_device_scenario(serial: str, scenario: ScenarioConfig):
        if not _validate_device_serial(serial):
            raise HTTPException(404, f"Invalid device serial format: {serial}.")
        server.scenario_manager.set_device_scenario(serial, scenario)
        await persist_fn()
        return ScenarioResponse(scope="device", identifier=serial, scenario=scenario)

    @router.delete(
        "/devices/{serial}",
        status_code=204,
        summary="Clear device scenario",
        description="Clears the scenario for a specific device.",
        responses={404: {"description": "Device scenario not found"}},
    )
    async def clear_device_scenario(serial: str):
        if not server.scenario_manager.delete_device_scenario(serial):
            raise HTTPException(404, f"No scenario set for device {serial}")
        await persist_fn()


def _add_type_endpoints(router: APIRouter, server: EmulatedLifxServer, persist_fn):
    """Add type-specific scenario endpoints to router."""

    @router.get(
        "/types/{device_type}",
        response_model=ScenarioResponse,
        summary="Get type scenario",
        description="Returns the scenario for all devices of a specific type.",
        responses={404: {"description": "Type scenario not set"}},
    )
    async def get_type_scenario(device_type: str):
        config = server.scenario_manager.get_type_scenario(device_type)
        if config is None:
            raise HTTPException(404, f"No scenario set for type {device_type}")
        return ScenarioResponse(scope="type", identifier=device_type, scenario=config)

    @router.put(
        "/types/{device_type}",
        response_model=ScenarioResponse,
        summary="Set type scenario",
        description="Sets the scenario for all devices of a specific type.",
    )
    async def set_type_scenario(device_type: str, scenario: ScenarioConfig):
        server.scenario_manager.set_type_scenario(device_type, scenario)
        await persist_fn()
        return ScenarioResponse(scope="type", identifier=device_type, scenario=scenario)

    @router.delete(
        "/types/{device_type}",
        status_code=204,
        summary="Clear type scenario",
        description="Clears the scenario for a device type.",
        responses={404: {"description": "Type scenario not found"}},
    )
    async def clear_type_scenario(device_type: str):
        if not server.scenario_manager.delete_type_scenario(device_type):
            raise HTTPException(404, f"No scenario set for type {device_type}")
        await persist_fn()


def _add_location_endpoints(router: APIRouter, server: EmulatedLifxServer, persist_fn):
    """Add location-based scenario endpoints to router."""

    @router.get(
        "/locations/{location}",
        response_model=ScenarioResponse,
        summary="Get location scenario",
        description="Returns the scenario for all devices in a location.",
        responses={404: {"description": "Location scenario not set"}},
    )
    async def get_location_scenario(location: str):
        config = server.scenario_manager.get_location_scenario(location)
        if config is None:
            raise HTTPException(404, f"No scenario set for location {location}")
        return ScenarioResponse(scope="location", identifier=location, scenario=config)

    @router.put(
        "/locations/{location}",
        response_model=ScenarioResponse,
        summary="Set location scenario",
        description="Sets the scenario for all devices in a location.",
    )
    async def set_location_scenario(location: str, scenario: ScenarioConfig):
        server.scenario_manager.set_location_scenario(location, scenario)
        await persist_fn()
        return ScenarioResponse(
            scope="location", identifier=location, scenario=scenario
        )

    @router.delete(
        "/locations/{location}",
        status_code=204,
        summary="Clear location scenario",
        description="Clears the scenario for a location.",
        responses={404: {"description": "Location scenario not found"}},
    )
    async def clear_location_scenario(location: str):
        if not server.scenario_manager.delete_location_scenario(location):
            raise HTTPException(404, f"No scenario set for location {location}")
        await persist_fn()


def _add_group_endpoints(router: APIRouter, server: EmulatedLifxServer, persist_fn):
    """Add group-based scenario endpoints to router."""

    @router.get(
        "/groups/{group}",
        response_model=ScenarioResponse,
        summary="Get group scenario",
        description="Returns the scenario for all devices in a group.",
        responses={404: {"description": "Group scenario not set"}},
    )
    async def get_group_scenario(group: str):
        config = server.scenario_manager.get_group_scenario(group)
        if config is None:
            raise HTTPException(404, f"No scenario set for group {group}")
        return ScenarioResponse(scope="group", identifier=group, scenario=config)

    @router.put(
        "/groups/{group}",
        response_model=ScenarioResponse,
        summary="Set group scenario",
        description="Sets the scenario for all devices in a group.",
    )
    async def set_group_scenario(group: str, scenario: ScenarioConfig):
        server.scenario_manager.set_group_scenario(group, scenario)
        await persist_fn()
        return ScenarioResponse(scope="group", identifier=group, scenario=scenario)

    @router.delete(
        "/groups/{group}",
        status_code=204,
        summary="Clear group scenario",
        description="Clears the scenario for a group.",
        responses={404: {"description": "Group scenario not found"}},
    )
    async def clear_group_scenario(group: str):
        if not server.scenario_manager.delete_group_scenario(group):
            raise HTTPException(404, f"No scenario set for group {group}")
        await persist_fn()


def create_scenarios_router(server: EmulatedLifxServer) -> APIRouter:
    """Create scenarios router with server dependency.

    Args:
        server: The LIFX emulator server instance

    Returns:
        Configured APIRouter for scenario endpoints
    """
    router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

    async def persist():
        """Helper to invalidate device caches and persist scenarios."""
        server.invalidate_all_scenario_caches()
        if server.scenario_persistence:
            await server.scenario_persistence.save(server.scenario_manager)

    _add_global_endpoints(router, server, persist)
    _add_device_endpoints(router, server, persist)
    _add_type_endpoints(router, server, persist)
    _add_location_endpoints(router, server, persist)
    _add_group_endpoints(router, server, persist)

    return router
