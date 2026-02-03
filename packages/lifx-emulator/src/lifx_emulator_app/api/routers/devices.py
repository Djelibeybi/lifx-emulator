"""Device management endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator_app.api.models import (
    BulkDeviceCreateRequest,
    DeviceCreateRequest,
    DeviceInfo,
    DeviceStateUpdate,
    PaginatedDeviceList,
)
from lifx_emulator_app.api.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceCreationError,
    DeviceNotFoundError,
    DeviceService,
    DeviceStateUpdateError,
)


def create_devices_router(server: EmulatedLifxServer) -> APIRouter:
    """Create devices router with server dependency.

    Args:
        server: The LIFX emulator server instance

    Returns:
        Configured APIRouter for device endpoints
    """
    # Create fresh router instance for this server
    router = APIRouter(prefix="/api/devices", tags=["devices"])

    # Create service layer
    device_service = DeviceService(server)

    @router.get(
        "",
        response_model=PaginatedDeviceList,
        summary="List all devices",
        description=(
            "Returns a paginated list of all emulated devices "
            "with their current configuration."
        ),
    )
    async def list_devices(
        offset: int = Query(0, ge=0, description="Number of devices to skip"),
        limit: int = Query(
            50, ge=1, le=1000, description="Maximum number of devices to return"
        ),
    ):
        """List all emulated devices with pagination."""
        devices, total = device_service.list_devices_paginated(offset, limit)
        return PaginatedDeviceList(
            devices=devices, total=total, offset=offset, limit=limit
        )

    @router.get(
        "/{serial}",
        response_model=DeviceInfo,
        summary="Get device information",
        description=(
            "Returns detailed information about a specific device by its serial number."
        ),
        responses={
            404: {"description": "Device not found"},
        },
    )
    async def get_device(serial: str):
        """Get specific device information."""
        try:
            return device_service.get_device_info(serial)
        except DeviceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post(
        "/bulk",
        response_model=list[DeviceInfo],
        status_code=201,
        summary="Create multiple devices",
        description="Creates multiple emulated devices at once.",
        responses={
            201: {"description": "All devices created successfully"},
            400: {"description": "Invalid product ID or parameters"},
            409: {"description": "Duplicate serial in batch or existing device"},
        },
    )
    async def create_devices_bulk(request: BulkDeviceCreateRequest):
        """Create multiple devices at once."""
        try:
            return device_service.create_devices_bulk(request.devices)
        except DeviceCreationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except DeviceAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @router.post(
        "",
        response_model=DeviceInfo,
        status_code=201,
        summary="Create a new device",
        description=(
            "Creates a new emulated device by product ID. "
            "The device will be added to the emulator immediately."
        ),
        responses={
            201: {"description": "Device created successfully"},
            400: {"description": "Invalid product ID or parameters"},
            409: {"description": "Device with this serial already exists"},
        },
    )
    async def create_device(request: DeviceCreateRequest):
        """Create a new device."""
        try:
            return device_service.create_device(request)
        except DeviceCreationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except DeviceAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @router.patch(
        "/{serial}/state",
        response_model=DeviceInfo,
        summary="Update device state",
        description="Updates the state of an existing device. All fields are optional.",
        responses={
            200: {"description": "Device state updated successfully"},
            400: {"description": "Invalid state update for device capabilities"},
            404: {"description": "Device not found"},
        },
    )
    async def update_device_state(serial: str, update: DeviceStateUpdate):
        """Update device state."""
        try:
            return device_service.update_device_state(serial, update)
        except DeviceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DeviceStateUpdateError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete(
        "/{serial}",
        status_code=204,
        summary="Delete a device",
        description=(
            "Removes an emulated device from the server. "
            "The device will stop responding to LIFX protocol packets."
        ),
        responses={
            204: {"description": "Device deleted successfully"},
            404: {"description": "Device not found"},
        },
    )
    async def delete_device(serial: str):
        """Delete a device."""
        try:
            device_service.delete_device(serial)
        except DeviceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.delete(
        "",
        status_code=200,
        summary="Delete all devices",
        description=(
            "Removes all emulated devices from the server. "
            "All devices will stop responding to LIFX protocol packets."
        ),
        responses={
            200: {"description": "All devices deleted successfully"},
        },
    )
    async def delete_all_devices():
        """Delete all devices from the running server."""
        count = device_service.clear_all_devices(delete_storage=False)
        return {"deleted": count, "message": f"Removed {count} device(s) from server"}

    return router
