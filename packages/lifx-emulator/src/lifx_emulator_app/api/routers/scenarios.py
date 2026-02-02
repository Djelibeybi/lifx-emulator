"""Scenario management endpoints for testing LIFX protocol behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator_app.api.models import ScenarioConfig, ScenarioResponse
from lifx_emulator_app.api.services.scenario_service import (
    InvalidDeviceSerialError,
    ScenarioNotFoundError,
    ScenarioService,
)


def _add_global_endpoints(router: APIRouter, service: ScenarioService):
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
        config = service.get_global_scenario()
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
        await service.set_global_scenario(scenario)
        return ScenarioResponse(scope="global", identifier=None, scenario=scenario)

    @router.delete(
        "/global",
        status_code=204,
        summary="Clear global scenario",
        description="Clears the global scenario, resetting it to defaults.",
    )
    async def clear_global_scenario():
        await service.clear_global_scenario()


def _add_device_endpoints(router: APIRouter, service: ScenarioService):
    """Add device-specific scenario endpoints to router."""

    @router.get(
        "/devices/{serial}",
        response_model=ScenarioResponse,
        summary="Get device scenario",
        description="Returns the scenario for a specific device by serial number.",
        responses={404: {"description": "Device scenario not set"}},
    )
    async def get_device_scenario(serial: str):
        try:
            config = service.get_scope_scenario("device", serial)
        except ScenarioNotFoundError:
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
        try:
            await service.set_scope_scenario("device", serial, scenario)
        except InvalidDeviceSerialError:
            raise HTTPException(404, f"Invalid device serial format: {serial}.")
        return ScenarioResponse(scope="device", identifier=serial, scenario=scenario)

    @router.delete(
        "/devices/{serial}",
        status_code=204,
        summary="Clear device scenario",
        description="Clears the scenario for a specific device.",
        responses={404: {"description": "Device scenario not found"}},
    )
    async def clear_device_scenario(serial: str):
        try:
            await service.delete_scope_scenario("device", serial)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for device {serial}")


def _add_type_endpoints(router: APIRouter, service: ScenarioService):
    """Add type-specific scenario endpoints to router."""

    @router.get(
        "/types/{device_type}",
        response_model=ScenarioResponse,
        summary="Get type scenario",
        description="Returns the scenario for all devices of a specific type.",
        responses={404: {"description": "Type scenario not set"}},
    )
    async def get_type_scenario(device_type: str):
        try:
            config = service.get_scope_scenario("type", device_type)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for type {device_type}")
        return ScenarioResponse(scope="type", identifier=device_type, scenario=config)

    @router.put(
        "/types/{device_type}",
        response_model=ScenarioResponse,
        summary="Set type scenario",
        description="Sets the scenario for all devices of a specific type.",
    )
    async def set_type_scenario(device_type: str, scenario: ScenarioConfig):
        await service.set_scope_scenario("type", device_type, scenario)
        return ScenarioResponse(scope="type", identifier=device_type, scenario=scenario)

    @router.delete(
        "/types/{device_type}",
        status_code=204,
        summary="Clear type scenario",
        description="Clears the scenario for a device type.",
        responses={404: {"description": "Type scenario not found"}},
    )
    async def clear_type_scenario(device_type: str):
        try:
            await service.delete_scope_scenario("type", device_type)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for type {device_type}")


def _add_location_endpoints(router: APIRouter, service: ScenarioService):
    """Add location-based scenario endpoints to router."""

    @router.get(
        "/locations/{location}",
        response_model=ScenarioResponse,
        summary="Get location scenario",
        description="Returns the scenario for all devices in a location.",
        responses={404: {"description": "Location scenario not set"}},
    )
    async def get_location_scenario(location: str):
        try:
            config = service.get_scope_scenario("location", location)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for location {location}")
        return ScenarioResponse(scope="location", identifier=location, scenario=config)

    @router.put(
        "/locations/{location}",
        response_model=ScenarioResponse,
        summary="Set location scenario",
        description="Sets the scenario for all devices in a location.",
    )
    async def set_location_scenario(location: str, scenario: ScenarioConfig):
        await service.set_scope_scenario("location", location, scenario)
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
        try:
            await service.delete_scope_scenario("location", location)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for location {location}")


def _add_group_endpoints(router: APIRouter, service: ScenarioService):
    """Add group-based scenario endpoints to router."""

    @router.get(
        "/groups/{group}",
        response_model=ScenarioResponse,
        summary="Get group scenario",
        description="Returns the scenario for all devices in a group.",
        responses={404: {"description": "Group scenario not set"}},
    )
    async def get_group_scenario(group: str):
        try:
            config = service.get_scope_scenario("group", group)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for group {group}")
        return ScenarioResponse(scope="group", identifier=group, scenario=config)

    @router.put(
        "/groups/{group}",
        response_model=ScenarioResponse,
        summary="Set group scenario",
        description="Sets the scenario for all devices in a group.",
    )
    async def set_group_scenario(group: str, scenario: ScenarioConfig):
        await service.set_scope_scenario("group", group, scenario)
        return ScenarioResponse(scope="group", identifier=group, scenario=scenario)

    @router.delete(
        "/groups/{group}",
        status_code=204,
        summary="Clear group scenario",
        description="Clears the scenario for a group.",
        responses={404: {"description": "Group scenario not found"}},
    )
    async def clear_group_scenario(group: str):
        try:
            await service.delete_scope_scenario("group", group)
        except ScenarioNotFoundError:
            raise HTTPException(404, f"No scenario set for group {group}")


def create_scenarios_router(server: EmulatedLifxServer) -> APIRouter:
    """Create scenarios router with server dependency.

    Args:
        server: The LIFX emulator server instance

    Returns:
        Configured APIRouter for scenario endpoints
    """
    router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])
    service = ScenarioService(server)

    _add_global_endpoints(router, service)
    _add_device_endpoints(router, service)
    _add_type_endpoints(router, service)
    _add_location_endpoints(router, service)
    _add_group_endpoints(router, service)

    return router
