"""FastAPI-based management API for LIFX emulator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

logger = logging.getLogger(__name__)


class DeviceCreateRequest(BaseModel):
    """Request to create a new device."""

    product_id: int = Field(..., description="Product ID from LIFX registry")
    serial: str | None = Field(
        None, description="Optional serial (auto-generated if not provided)"
    )
    zone_count: int | None = Field(
        None, description="Number of zones for multizone devices"
    )
    tile_count: int | None = Field(
        None, description="Number of tiles for matrix devices"
    )
    tile_width: int | None = Field(None, description="Width of each tile in pixels")
    tile_height: int | None = Field(None, description="Height of each tile in pixels")
    firmware_major: int | None = Field(None, description="Firmware major version")
    firmware_minor: int | None = Field(None, description="Firmware minor version")


class ColorHsbk(BaseModel):
    """HSBK color representation."""

    hue: int
    saturation: int
    brightness: int
    kelvin: int


class DeviceInfo(BaseModel):
    """Device information response."""

    serial: str
    label: str
    product: int
    vendor: int
    power_level: int
    has_color: bool
    has_infrared: bool
    has_multizone: bool
    has_extended_multizone: bool
    has_matrix: bool
    has_hev: bool
    zone_count: int
    tile_count: int
    color: ColorHsbk | None = None
    zone_colors: list[ColorHsbk] = Field(default_factory=list)
    tile_devices: list[dict] = Field(default_factory=list)
    # Metadata fields
    version_major: int = 0
    version_minor: int = 0
    build_timestamp: int = 0
    group_label: str = ""
    location_label: str = ""
    uptime_ns: int = 0
    wifi_signal: float = 0.0


class ServerStats(BaseModel):
    """Server statistics response."""

    uptime_seconds: float
    start_time: float
    device_count: int
    packets_received: int
    packets_sent: int
    packets_received_by_type: dict[int, int]
    packets_sent_by_type: dict[int, int]
    error_count: int
    activity_enabled: bool


class ActivityEvent(BaseModel):
    """Recent activity event."""

    timestamp: float
    direction: str
    packet_type: int
    packet_name: str
    device: str | None = None
    target: str | None = None
    addr: str


# Scenario Management Models


class ScenarioConfigModel(BaseModel):
    """Scenario configuration model for API."""

    drop_packets: dict[int, float] = Field(
        default_factory=dict,
        description="Map of packet types to drop rates (0.1-1.0). "
        "1.0 = always drop, 0.5 = drop 50%, 0.1 = drop 10%. "
        "Example: {101: 1.0, 102: 0.6}",
    )
    response_delays: dict[int, float] = Field(
        default_factory=dict,
        description="Map of packet types to delay in seconds before responding",
    )
    malformed_packets: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with truncated/corrupted payloads",
    )
    invalid_field_values: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with all 0xFF bytes in fields",
    )
    firmware_version: tuple[int, int] | None = Field(
        None, description="Override firmware version (major, minor). Example: [3, 70]"
    )
    partial_responses: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with incomplete data",
    )
    send_unhandled: bool = Field(
        False, description="Send unhandled message responses for unknown packet types"
    )

    @field_validator("drop_packets", mode="before")
    @classmethod
    def convert_drop_packets_keys(cls, v):
        """Convert string keys to integers for drop_packets."""
        if isinstance(v, dict):
            return {int(k): float(val) for k, val in v.items()}
        return v

    @field_validator("response_delays", mode="before")
    @classmethod
    def convert_response_delays_keys(cls, v):
        """Convert string keys to integers for response_delays."""
        if isinstance(v, dict):
            return {int(k): float(val) for k, val in v.items()}
        return v


class ScenarioResponse(BaseModel):
    """Response model for scenario operations."""

    scope: str = Field(
        ..., description="Scope of the scenario (global, device, type, location, group)"
    )
    identifier: str | None = Field(
        None, description="Identifier for the scope (serial, type name, etc.)"
    )
    scenario: ScenarioConfigModel = Field(..., description="The scenario configuration")


def create_api_app(server: EmulatedLifxServer) -> FastAPI:
    """Create FastAPI application for emulator management.

    Args:
        server: The LIFX emulator server instance

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="LIFX Emulator API",
        description="""
Runtime management and monitoring API for LIFX device emulator.

This API provides read-only monitoring of the emulator state and device management
capabilities (add/remove devices). Device state changes must be performed via the
LIFX LAN protocol.

## Features
- Real-time server statistics and packet monitoring
- Device inspection and management
- Recent activity tracking
- OpenAPI 3.1.0 compliant schema
        """,
        version="1.0.0",
        contact={
            "name": "LIFX Emulator",
            "url": "https://github.com/Djelibeybi/lifx-emulator",
        },
        license_info={
            "name": "UPL-1.0",
            "url": "https://opensource.org/licenses/UPL",
        },
        openapi_tags=[
            {
                "name": "monitoring",
                "description": "Server statistics and activity monitoring",
            },
            {
                "name": "devices",
                "description": "Device management and inspection",
            },
            {
                "name": "scenarios",
                "description": (
                    "Test scenario management for simulating device behaviors"
                ),
            },
        ],
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        """Serve web UI."""
        return HTML_UI

    @app.get(
        "/api/stats",
        response_model=ServerStats,
        tags=["monitoring"],
        summary="Get server statistics",
        description=(
            "Returns server uptime, packet counts, error counts, and device count."
        ),
    )
    async def get_stats():
        """Get server statistics."""
        return server.get_stats()

    @app.get(
        "/api/devices",
        response_model=list[DeviceInfo],
        tags=["devices"],
        summary="List all devices",
        description=(
            "Returns a list of all emulated devices with their current configuration."
        ),
    )
    async def list_devices():
        """List all emulated devices."""
        devices = server.get_all_devices()
        result = []
        for dev in devices:
            device_info = DeviceInfo(
                serial=dev.state.serial,
                label=dev.state.label,
                product=dev.state.product,
                vendor=dev.state.vendor,
                power_level=dev.state.power_level,
                has_color=dev.state.has_color,
                has_infrared=dev.state.has_infrared,
                has_multizone=dev.state.has_multizone,
                has_extended_multizone=dev.state.has_extended_multizone,
                has_matrix=dev.state.has_matrix,
                has_hev=dev.state.has_hev,
                zone_count=dev.state.multizone.zone_count
                if dev.state.multizone is not None
                else 0,
                tile_count=dev.state.matrix.tile_count
                if dev.state.matrix is not None
                else 0,
                color=ColorHsbk(
                    hue=dev.state.color.hue,
                    saturation=dev.state.color.saturation,
                    brightness=dev.state.color.brightness,
                    kelvin=dev.state.color.kelvin,
                )
                if dev.state.has_color
                else None,
                zone_colors=[
                    ColorHsbk(
                        hue=c.hue,
                        saturation=c.saturation,
                        brightness=c.brightness,
                        kelvin=c.kelvin,
                    )
                    for c in dev.state.multizone.zone_colors
                ]
                if dev.state.multizone is not None
                else [],
                tile_devices=dev.state.matrix.tile_devices
                if dev.state.matrix is not None
                else [],
                version_major=dev.state.version_major,
                version_minor=dev.state.version_minor,
                build_timestamp=dev.state.build_timestamp,
                group_label=dev.state.group.group_label,
                location_label=dev.state.location.location_label,
                uptime_ns=dev.state.uptime_ns,
                wifi_signal=dev.state.wifi_signal,
            )
            result.append(device_info)
        return result

    @app.get(
        "/api/devices/{serial}",
        response_model=DeviceInfo,
        tags=["devices"],
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
        device = server.get_device(serial)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {serial} not found")

        return DeviceInfo(
            serial=device.state.serial,
            label=device.state.label,
            product=device.state.product,
            vendor=device.state.vendor,
            power_level=device.state.power_level,
            has_color=device.state.has_color,
            has_infrared=device.state.has_infrared,
            has_multizone=device.state.has_multizone,
            has_extended_multizone=device.state.has_extended_multizone,
            has_matrix=device.state.has_matrix,
            has_hev=device.state.has_hev,
            zone_count=device.state.multizone.zone_count
            if device.state.multizone is not None
            else 0,
            tile_count=device.state.matrix.tile_count
            if device.state.matrix is not None
            else 0,
            color=ColorHsbk(
                hue=device.state.color.hue,
                saturation=device.state.color.saturation,
                brightness=device.state.color.brightness,
                kelvin=device.state.color.kelvin,
            )
            if device.state.has_color
            else None,
            zone_colors=[
                ColorHsbk(
                    hue=c.hue,
                    saturation=c.saturation,
                    brightness=c.brightness,
                    kelvin=c.kelvin,
                )
                for c in device.state.multizone.zone_colors
            ]
            if device.state.multizone is not None
            else [],
            tile_devices=device.state.matrix.tile_devices
            if device.state.matrix is not None
            else [],
            version_major=device.state.version_major,
            version_minor=device.state.version_minor,
            build_timestamp=device.state.build_timestamp,
            group_label=device.state.group.group_label,
            location_label=device.state.location.location_label,
            uptime_ns=device.state.uptime_ns,
            wifi_signal=device.state.wifi_signal,
        )

    @app.post(
        "/api/devices",
        response_model=DeviceInfo,
        status_code=201,
        tags=["devices"],
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
        from lifx_emulator.factories import create_device

        # Build firmware_version tuple if both major and minor are provided
        firmware_version = None
        if request.firmware_major is not None and request.firmware_minor is not None:
            firmware_version = (request.firmware_major, request.firmware_minor)

        try:
            device = create_device(
                product_id=request.product_id,
                serial=request.serial,
                zone_count=request.zone_count,
                tile_count=request.tile_count,
                tile_width=request.tile_width,
                tile_height=request.tile_height,
                firmware_version=firmware_version,
                storage=server.storage,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create device: {e}")

        if not server.add_device(device):
            raise HTTPException(
                status_code=409,
                detail=f"Device with serial {device.state.serial} already exists",
            )

        return DeviceInfo(
            serial=device.state.serial,
            label=device.state.label,
            product=device.state.product,
            vendor=device.state.vendor,
            power_level=device.state.power_level,
            has_color=device.state.has_color,
            has_infrared=device.state.has_infrared,
            has_multizone=device.state.has_multizone,
            has_extended_multizone=device.state.has_extended_multizone,
            has_matrix=device.state.has_matrix,
            has_hev=device.state.has_hev,
            zone_count=device.state.multizone.zone_count
            if device.state.multizone is not None
            else 0,
            tile_count=device.state.matrix.tile_count
            if device.state.matrix is not None
            else 0,
            color=ColorHsbk(
                hue=device.state.color.hue,
                saturation=device.state.color.saturation,
                brightness=device.state.color.brightness,
                kelvin=device.state.color.kelvin,
            )
            if device.state.has_color
            else None,
            zone_colors=[
                ColorHsbk(
                    hue=c.hue,
                    saturation=c.saturation,
                    brightness=c.brightness,
                    kelvin=c.kelvin,
                )
                for c in device.state.multizone.zone_colors
            ]
            if device.state.multizone is not None
            else [],
            tile_devices=device.state.matrix.tile_devices
            if device.state.matrix is not None
            else [],
            version_major=device.state.version_major,
            version_minor=device.state.version_minor,
            build_timestamp=device.state.build_timestamp,
            group_label=device.state.group.group_label,
            location_label=device.state.location.location_label,
            uptime_ns=device.state.uptime_ns,
            wifi_signal=device.state.wifi_signal,
        )

    @app.delete(
        "/api/devices/{serial}",
        status_code=204,
        tags=["devices"],
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
        if not server.remove_device(serial):
            raise HTTPException(status_code=404, detail=f"Device {serial} not found")

    @app.delete(
        "/api/devices",
        status_code=200,
        tags=["devices"],
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
        count = server.remove_all_devices(delete_storage=False)
        return {"deleted": count, "message": f"Removed {count} device(s) from server"}

    @app.delete(
        "/api/storage",
        status_code=200,
        tags=["devices"],
        summary="Clear persistent storage",
        description=(
            "Deletes all persistent device state files from disk. "
            "This does not affect currently running devices, only saved state files."
        ),
        responses={
            200: {"description": "Storage cleared successfully"},
            503: {"description": "Persistent storage not enabled"},
        },
    )
    async def clear_storage():
        """Clear all persistent device state from storage."""
        if not server.storage:
            raise HTTPException(
                status_code=503, detail="Persistent storage is not enabled"
            )

        deleted = server.storage.delete_all_device_states()
        return {
            "deleted": deleted,
            "message": f"Deleted {deleted} device state(s) from persistent storage",
        }

    @app.get(
        "/api/activity",
        response_model=list[ActivityEvent],
        tags=["monitoring"],
        summary="Get recent activity",
        description=(
            "Returns the last 100 packet events (TX/RX) "
            "with timestamps and packet details."
        ),
    )
    async def get_activity():
        """Get recent activity events."""
        return [ActivityEvent(**event) for event in server.get_recent_activity()]

    # Scenario Management Endpoints

    def _scenario_config_to_model(config) -> ScenarioConfigModel:
        """Convert ScenarioConfig to Pydantic model."""
        from lifx_emulator.scenario_manager import ScenarioConfig

        if isinstance(config, ScenarioConfig):
            return ScenarioConfigModel(
                drop_packets=config.drop_packets,
                response_delays=config.response_delays,
                malformed_packets=config.malformed_packets,
                invalid_field_values=config.invalid_field_values,
                firmware_version=config.firmware_version,
                partial_responses=config.partial_responses,
                send_unhandled=config.send_unhandled,
            )
        return ScenarioConfigModel(**config)

    def _model_to_scenario_config(model: ScenarioConfigModel):
        """Convert Pydantic model to ScenarioConfig."""
        from lifx_emulator.scenario_manager import ScenarioConfig

        return ScenarioConfig(
            drop_packets=model.drop_packets,
            response_delays=model.response_delays,
            malformed_packets=model.malformed_packets,
            invalid_field_values=model.invalid_field_values,
            firmware_version=model.firmware_version,
            partial_responses=model.partial_responses,
            send_unhandled=model.send_unhandled,
        )

    @app.get(
        "/api/scenarios/global",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Get global scenario",
        description=(
            "Returns the global scenario that applies to all devices as a baseline."
        ),
    )
    async def get_global_scenario():
        """Get global scenario configuration."""
        config = server.scenario_manager.get_global_scenario()
        return ScenarioResponse(
            scope="global", identifier=None, scenario=_scenario_config_to_model(config)
        )

    @app.put(
        "/api/scenarios/global",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Set global scenario",
        description=(
            "Sets the global scenario that applies to all devices as a baseline."
        ),
    )
    async def set_global_scenario(scenario: ScenarioConfigModel):
        """Set global scenario configuration."""
        config = _model_to_scenario_config(scenario)
        server.scenario_manager.set_global_scenario(config)

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

        return ScenarioResponse(scope="global", identifier=None, scenario=scenario)

    @app.delete(
        "/api/scenarios/global",
        status_code=204,
        tags=["scenarios"],
        summary="Clear global scenario",
        description="Clears the global scenario, resetting it to defaults.",
    )
    async def clear_global_scenario():
        """Clear global scenario configuration."""
        server.scenario_manager.clear_global_scenario()

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

    @app.get(
        "/api/scenarios/devices/{serial}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Get device-specific scenario",
        description=(
            "Returns the scenario configuration for a specific device by serial number."
        ),
        responses={404: {"description": "Device scenario not found"}},
    )
    async def get_device_scenario(serial: str):
        """Get device-specific scenario."""
        config = server.scenario_manager.get_device_scenario(serial)
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"No scenario found for device {serial}"
            )
        return ScenarioResponse(
            scope="device",
            identifier=serial,
            scenario=_scenario_config_to_model(config),
        )

    @app.put(
        "/api/scenarios/devices/{serial}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Set device-specific scenario",
        description="Sets a scenario that applies only to the specified device.",
    )
    async def set_device_scenario(serial: str, scenario: ScenarioConfigModel):
        """Set device-specific scenario."""
        # Verify device exists
        device = server.get_device(serial)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {serial} not found")

        config = _model_to_scenario_config(scenario)
        server.scenario_manager.set_device_scenario(serial, config)

        # Invalidate cache for this device
        device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

        return ScenarioResponse(scope="device", identifier=serial, scenario=scenario)

    @app.delete(
        "/api/scenarios/devices/{serial}",
        status_code=204,
        tags=["scenarios"],
        summary="Clear device-specific scenario",
        description="Clears the scenario for the specified device.",
        responses={404: {"description": "Device scenario not found"}},
    )
    async def clear_device_scenario(serial: str):
        """Clear device-specific scenario."""
        if not server.scenario_manager.delete_device_scenario(serial):
            raise HTTPException(
                status_code=404, detail=f"No scenario found for device {serial}"
            )

        # Invalidate cache if device exists
        device = server.get_device(serial)
        if device:
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

    @app.get(
        "/api/scenarios/types/{device_type}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Get type-specific scenario",
        description=(
            "Returns the scenario for a device type (matrix, multizone, color, etc.)."
        ),
        responses={404: {"description": "Type scenario not found"}},
    )
    async def get_type_scenario(device_type: str):
        """Get type-specific scenario."""
        config = server.scenario_manager.get_type_scenario(device_type)
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"No scenario found for type {device_type}"
            )
        return ScenarioResponse(
            scope="type",
            identifier=device_type,
            scenario=_scenario_config_to_model(config),
        )

    @app.put(
        "/api/scenarios/types/{device_type}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Set type-specific scenario",
        description=(
            "Sets a scenario that applies to all devices "
            "of a specific type. "
            "Valid types: matrix, multizone, color, infrared, hev"
        ),
    )
    async def set_type_scenario(device_type: str, scenario: ScenarioConfigModel):
        """Set type-specific scenario."""
        config = _model_to_scenario_config(scenario)
        server.scenario_manager.set_type_scenario(device_type, config)

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

        return ScenarioResponse(scope="type", identifier=device_type, scenario=scenario)

    @app.delete(
        "/api/scenarios/types/{device_type}",
        status_code=204,
        tags=["scenarios"],
        summary="Clear type-specific scenario",
        description="Clears the scenario for the specified device type.",
        responses={404: {"description": "Type scenario not found"}},
    )
    async def clear_type_scenario(device_type: str):
        """Clear type-specific scenario."""
        if not server.scenario_manager.delete_type_scenario(device_type):
            raise HTTPException(
                status_code=404, detail=f"No scenario found for type {device_type}"
            )

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

    @app.get(
        "/api/scenarios/locations/{location}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Get location-specific scenario",
        description="Returns the scenario for a specific location.",
        responses={404: {"description": "Location scenario not found"}},
    )
    async def get_location_scenario(location: str):
        """Get location-specific scenario."""
        config = server.scenario_manager.get_location_scenario(location)
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"No scenario found for location {location}"
            )
        return ScenarioResponse(
            scope="location",
            identifier=location,
            scenario=_scenario_config_to_model(config),
        )

    @app.put(
        "/api/scenarios/locations/{location}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Set location-specific scenario",
        description=(
            "Sets a scenario that applies to all devices in a specific location."
        ),
    )
    async def set_location_scenario(location: str, scenario: ScenarioConfigModel):
        """Set location-specific scenario."""
        config = _model_to_scenario_config(scenario)
        server.scenario_manager.set_location_scenario(location, config)

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

        return ScenarioResponse(
            scope="location", identifier=location, scenario=scenario
        )

    @app.delete(
        "/api/scenarios/locations/{location}",
        status_code=204,
        tags=["scenarios"],
        summary="Clear location-specific scenario",
        description="Clears the scenario for the specified location.",
        responses={404: {"description": "Location scenario not found"}},
    )
    async def clear_location_scenario(location: str):
        """Clear location-specific scenario."""
        if not server.scenario_manager.delete_location_scenario(location):
            raise HTTPException(
                status_code=404, detail=f"No scenario found for location {location}"
            )

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

    @app.get(
        "/api/scenarios/groups/{group}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Get group-specific scenario",
        description="Returns the scenario for a specific group.",
        responses={404: {"description": "Group scenario not found"}},
    )
    async def get_group_scenario(group: str):
        """Get group-specific scenario."""
        config = server.scenario_manager.get_group_scenario(group)
        if config is None:
            raise HTTPException(
                status_code=404, detail=f"No scenario found for group {group}"
            )
        return ScenarioResponse(
            scope="group", identifier=group, scenario=_scenario_config_to_model(config)
        )

    @app.put(
        "/api/scenarios/groups/{group}",
        response_model=ScenarioResponse,
        tags=["scenarios"],
        summary="Set group-specific scenario",
        description=(
            "Sets a scenario that applies to all devices in a specific group."
        ),
    )
    async def set_group_scenario(group: str, scenario: ScenarioConfigModel):
        """Set group-specific scenario."""
        config = _model_to_scenario_config(scenario)
        server.scenario_manager.set_group_scenario(group, config)

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

        return ScenarioResponse(scope="group", identifier=group, scenario=scenario)

    @app.delete(
        "/api/scenarios/groups/{group}",
        status_code=204,
        tags=["scenarios"],
        summary="Clear group-specific scenario",
        description="Clears the scenario for the specified group.",
        responses={404: {"description": "Group scenario not found"}},
    )
    async def clear_group_scenario(group: str):
        """Clear group-specific scenario."""
        if not server.scenario_manager.delete_group_scenario(group):
            raise HTTPException(
                status_code=404, detail=f"No scenario found for group {group}"
            )

        # Invalidate cache for all devices
        for device in server.get_all_devices():
            device.invalidate_scenario_cache()

        # Save to disk if persistence is enabled
        if server.scenario_persistence:
            server.scenario_persistence.save(server.scenario_manager)

    return app


async def run_api_server(
    server: EmulatedLifxServer, host: str = "127.0.0.1", port: int = 8080
):
    """Run the FastAPI server.

    Args:
        server: The LIFX emulator server instance
        host: Host to bind to
        port: Port to bind to
    """
    import uvicorn

    app = create_api_app(server)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    api_server = uvicorn.Server(config)

    logger.info("Starting API server on http://%s:%s", host, port)
    await api_server.serve()


# Embedded web UI
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LIFX Emulator Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #fff;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            color: #888;
            margin-bottom: 30px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        .devices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
        }
        .card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
        }
        .card h2 {
            color: #fff;
            font-size: 1.2em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #2a2a2a;
        }
        .stat:last-child {
            border-bottom: none;
        }
        .stat-label {
            color: #888;
        }
        .stat-value {
            color: #fff;
            font-weight: 600;
        }
        .device {
            background: #252525;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 8px;
            margin-bottom: 8px;
            font-size: 0.85em;
        }
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .device-serial {
            font-family: 'Monaco', 'Courier New', monospace;
            color: #4a9eff;
            font-weight: bold;
            font-size: 0.9em;
        }
        .device-label {
            color: #aaa;
            font-size: 0.85em;
        }
        .zones-container {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #333;
        }
        .zones-toggle, .metadata-toggle {
            cursor: pointer;
            color: #4a9eff;
            font-size: 0.8em;
            margin-top: 4px;
            user-select: none;
        }
        .zones-toggle:hover, .metadata-toggle:hover {
            color: #6bb0ff;
        }
        .zones-display, .metadata-display {
            display: none;
            margin-top: 6px;
        }
        .zones-display.show, .metadata-display.show {
            display: block;
        }
        .metadata-display {
            font-size: 0.75em;
            color: #888;
            padding: 6px;
            background: #1a1a1a;
            border-radius: 3px;
            border: 1px solid #333;
        }
        .metadata-row {
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
        }
        .metadata-label {
            color: #666;
        }
        .metadata-value {
            color: #aaa;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        .zone-strip {
            display: flex;
            height: 20px;
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 4px;
        }
        .zone-segment {
            flex: 1;
            min-width: 4px;
        }
        .color-swatch {
            display: inline-block;
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid #333;
            vertical-align: middle;
            margin-right: 4px;
        }
        .tile-grid {
            display: grid;
            gap: 2px;
            margin-top: 4px;
        }
        .tile-pixel {
            width: 8px;
            height: 8px;
            border-radius: 1px;
        }
        .tiles-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 4px;
        }
        .tile-item {
            display: inline-block;
        }
        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7em;
            font-weight: 600;
            margin-right: 4px;
            margin-bottom: 2px;
        }
        .badge-power-on {
            background: #2d5;
            color: #000;
        }
        .badge-power-off {
            background: #555;
            color: #aaa;
        }
        .badge-capability {
            background: #333;
            color: #4a9eff;
        }
        .badge-extended-mz {
            background: #2d4a2d;
            color: #5dff5d;
        }
        .activity-log {
            background: #0d0d0d;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
        }
        .activity-item {
            padding: 6px 0;
            border-bottom: 1px solid #1a1a1a;
            display: flex;
            gap: 10px;
        }
        .activity-item:last-child {
            border-bottom: none;
        }
        .activity-time {
            color: #666;
            min-width: 80px;
        }
        .activity-rx {
            color: #4a9eff;
        }
        .activity-tx {
            color: #f9a825;
        }
        .activity-packet {
            color: #aaa;
        }
        .btn {
            background: #4a9eff;
            color: #000;
            border: none;
            padding: 4px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.75em;
        }
        .btn:hover {
            background: #6bb0ff;
        }
        .btn-delete {
            background: #d32f2f;
            color: #fff;
        }
        .btn-delete:hover {
            background: #e57373;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            color: #aaa;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        .form-group input, .form-group select {
            width: 100%;
            background: #0d0d0d;
            border: 1px solid #333;
            color: #fff;
            padding: 8px;
            border-radius: 4px;
        }
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #2d5;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .no-devices {
            text-align: center;
            color: #666;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>LIFX Emulator Monitor</h1>
        <p class="subtitle">Real-time monitoring and device management</p>

        <div class="grid">
            <div class="card">
                <h2><span class="status-indicator"></span> Server Statistics</h2>
                <div id="stats">
                    <div class="stat">
                        <span class="stat-label">Loading...</span>
                        <span class="stat-value"></span>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Add Device</h2>
                <form id="add-device-form">
                    <div class="form-group">
                        <label>Product ID</label>
                        <select id="product-id" required>
                            <option value="27">27 - LIFX A19</option>
                            <option value="29">29 - LIFX A19 Night Vision</option>
                            <option value="32">32 - LIFX Z (Strip)</option>
                            <option value="38">38 - LIFX Beam</option>
                            <option value="50">50 - LIFX Mini White to Warm</option>
                            <option value="55">55 - LIFX Tile</option>
                            <option value="90">90 - LIFX Clean (HEV)</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">Add Device</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>
                Devices (<span id="device-count">0</span>)
                <span style="float: right; display: flex; gap: 8px;">
                    <button
                        class="btn btn-delete"
                        onclick="removeAllDevices()"
                        title="Remove all devices from server (runtime only)"
                    >Remove All</button>
                    <button
                        class="btn btn-delete"
                        onclick="clearStorage()"
                        id="clear-storage-btn"
                        title="Delete all persistent device state files"
                    >Clear Storage</button>
                </span>
            </h2>
            <div id="devices" class="devices-grid"></div>
        </div>

        <div class="card" id="activity-card">
            <h2>Recent Activity</h2>
            <div class="activity-log" id="activity-log"></div>
        </div>
    </div>

    <script>
        let updateInterval;

        // Convert HSBK to RGB for display
        function hsbkToRgb(hsbk) {
            const h = hsbk.hue / 65535;
            const s = hsbk.saturation / 65535;
            const v = hsbk.brightness / 65535;

            let r, g, b;
            const i = Math.floor(h * 6);
            const f = h * 6 - i;
            const p = v * (1 - s);
            const q = v * (1 - f * s);
            const t = v * (1 - (1 - f) * s);

            switch (i % 6) {
                case 0: r = v; g = t; b = p; break;
                case 1: r = q; g = v; b = p; break;
                case 2: r = p; g = v; b = t; break;
                case 3: r = p; g = q; b = v; break;
                case 4: r = t; g = p; b = v; break;
                case 5: r = v; g = p; b = q; break;
            }

            const red = Math.round(r * 255);
            const green = Math.round(g * 255);
            const blue = Math.round(b * 255);
            return `rgb(${red}, ${green}, ${blue})`;
        }

        function toggleZones(serial) {
            const element = document.getElementById(`zones-${serial}`);
            const toggle = document.getElementById(`zones-toggle-${serial}`);
            if (element && toggle) {
                const isShown = element.classList.toggle('show');
                // Update toggle icon
                toggle.textContent = isShown
                    ? toggle.textContent.replace('▸', '▾')
                    : toggle.textContent.replace('▾', '▸');
                // Save state to localStorage
                localStorage.setItem(`zones-${serial}`, isShown ? 'show' : 'hide');
            }
        }

        function toggleMetadata(serial) {
            const element = document.getElementById(`metadata-${serial}`);
            const toggle = document.getElementById(`metadata-toggle-${serial}`);
            if (element && toggle) {
                const isShown = element.classList.toggle('show');
                // Update toggle icon
                toggle.textContent = isShown
                    ? toggle.textContent.replace('▸', '▾')
                    : toggle.textContent.replace('▾', '▸');
                // Save state to localStorage
                localStorage.setItem(`metadata-${serial}`, isShown ? 'show' : 'hide');
            }
        }

        function restoreToggleStates(serial) {
            // Restore zones toggle state
            const zonesState = localStorage.getItem(`zones-${serial}`);
            if (zonesState === 'show') {
                const element = document.getElementById(`zones-${serial}`);
                const toggle = document.getElementById(`zones-toggle-${serial}`);
                if (element && toggle) {
                    element.classList.add('show');
                    toggle.textContent = toggle.textContent.replace('▸', '▾');
                }
            }

            // Restore metadata toggle state
            const metadataState = localStorage.getItem(`metadata-${serial}`);
            if (metadataState === 'show') {
                const element = document.getElementById(`metadata-${serial}`);
                const toggle = document.getElementById(`metadata-toggle-${serial}`);
                if (element && toggle) {
                    element.classList.add('show');
                    toggle.textContent = toggle.textContent.replace('▸', '▾');
                }
            }
        }

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const stats = await response.json();

                const uptimeValue = Math.floor(stats.uptime_seconds);
                const statsHtml = `
                    <div class="stat">
                        <span class="stat-label">Uptime</span>
                        <span class="stat-value">${uptimeValue}s</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Devices</span>
                        <span class="stat-value">${stats.device_count}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Packets RX</span>
                        <span class="stat-value">${stats.packets_received}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Packets TX</span>
                        <span class="stat-value">${stats.packets_sent}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Errors</span>
                        <span class="stat-value">${stats.error_count}</span>
                    </div>
                `;
                document.getElementById('stats').innerHTML = statsHtml;

                // Show/hide activity log based on server configuration
                const activityCard = document.getElementById('activity-card');
                if (activityCard) {
                    const displayValue = (
                        stats.activity_enabled ? 'block' : 'none'
                    );
                    activityCard.style.display = displayValue;
                }

                return stats.activity_enabled;
            } catch (error) {
                console.error('Failed to fetch stats:', error);
                const errorLabelStyle = 'color: #d32f2f;';
                const errorHtml = `
                    <div class="stat">
                        <span class="stat-label" style="${errorLabelStyle}">
                            Error loading stats
                        </span>
                        <span class="stat-value">${error.message}</span>
                    </div>
                `;
                document.getElementById('stats').innerHTML = errorHtml;
                return false;
            }
        }

        async function fetchDevices() {
            try {
                const response = await fetch('/api/devices');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const devices = await response.json();

                document.getElementById('device-count').textContent = devices.length;

                if (devices.length === 0) {
                    const noDevicesHtml = (
                        '<div class="no-devices">No devices emulated</div>'
                    );
                    document.getElementById('devices').innerHTML = noDevicesHtml;
                    return;
                }

                const devicesHtml = devices.map(dev => {
                const capabilities = [];
                const capabilityBadges = [];

                if (dev.has_color) capabilities.push('color');
                if (dev.has_infrared) capabilities.push('IR');

                // Show extended-mz badge instead of multizone when both are present
                if (dev.has_extended_multizone) {
                    const badgeHtml = (
                        '<span class="badge badge-extended-mz">' +
                        `extended-mz×${dev.zone_count}</span>`
                    );
                    capabilityBadges.push(badgeHtml);
                } else if (dev.has_multizone) {
                    capabilities.push(`multizone×${dev.zone_count}`);
                }

                if (dev.has_matrix) capabilities.push(`matrix×${dev.tile_count}`);
                if (dev.has_hev) capabilities.push('HEV');

                const powerBadge = dev.power_level > 0
                    ? '<span class="badge badge-power-on">ON</span>'
                    : '<span class="badge badge-power-off">OFF</span>';

                // Generate capabilities list for metadata
                const capabilitiesMetadata = [];
                if (dev.has_color) capabilitiesMetadata.push('Color');
                if (dev.has_infrared) {
                    capabilitiesMetadata.push('Infrared');
                }
                if (dev.has_multizone) {
                    capabilitiesMetadata.push(
                        `Multizone (${dev.zone_count} zones)`
                    );
                }
                if (dev.has_extended_multizone) {
                    capabilitiesMetadata.push('Extended Multizone');
                }
                if (dev.has_matrix) {
                    capabilitiesMetadata.push(
                        `Matrix (${dev.tile_count} tiles)`
                    );
                }
                if (dev.has_hev) capabilitiesMetadata.push('HEV/Clean');
                const capabilitiesText = (
                    capabilitiesMetadata.join(', ') || 'None'
                );

                // Generate metadata display
                const uptimeSeconds = Math.floor(dev.uptime_ns / 1e9);
                const metaToggleId = `metadata-toggle-${dev.serial}`;
                const metaToggleClick = `toggleMetadata('${dev.serial}')`;
                const metadataHtml = `
                    <div
                        class="metadata-toggle"
                        id="${metaToggleId}"
                        onclick="${metaToggleClick}"
                    >
                        ▸ Show metadata
                    </div>
                    <div id="metadata-${dev.serial}" class="metadata-display">
                        <div class="metadata-row">
                            <span class="metadata-label">Firmware:</span>
                            <span class="metadata-value">
                                ${dev.version_major}.${dev.version_minor}
                            </span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Vendor:</span>
                            <span class="metadata-value">${dev.vendor}</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Product:</span>
                            <span class="metadata-value">${dev.product}</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Capabilities:</span>
                            <span
                                class="metadata-value"
                                style="color: #4a9eff;"
                            >${capabilitiesText}</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Group:</span>
                            <span class="metadata-value">${dev.group_label}</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Location:</span>
                            <span class="metadata-value">${dev.location_label}</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Uptime:</span>
                            <span class="metadata-value">${uptimeSeconds}s</span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">WiFi Signal:</span>
                            <span class="metadata-value">
                                ${dev.wifi_signal.toFixed(1)} dBm
                            </span>
                        </div>
                    </div>
                `;

                // Generate zones display
                let zonesHtml = '';
                if (dev.has_multizone && dev.zone_colors &&
                    dev.zone_colors.length > 0
                ) {
                    const zoneSegments = dev.zone_colors.map(color => {
                        const rgb = hsbkToRgb(color);
                        const bgStyle = `background: ${rgb};`;
                        return `<div class="zone-segment" style="${bgStyle}"></div>`;
                    }).join('');

                    const zoneCount = dev.zone_colors.length;
                    const toggleId = `zones-toggle-${dev.serial}`;
                    const toggleClick = `toggleZones('${dev.serial}')`;
                    zonesHtml = `
                        <div
                            class="zones-toggle"
                            id="${toggleId}"
                            onclick="${toggleClick}"
                        >
                            ▸ Show zones (${zoneCount})
                        </div>
                        <div id="zones-${dev.serial}" class="zones-display">
                            <div class="zone-strip">${zoneSegments}</div>
                        </div>
                    `;
                } else if (dev.has_matrix && dev.tile_devices &&
                           dev.tile_devices.length > 0) {
                    // Render actual tile pixels
                    const tilesHtml = dev.tile_devices.map((tile, tileIndex) => {
                        if (!tile.colors || tile.colors.length === 0) {
                            return '<div style="color: #666;">No color data</div>';
                        }

                        const width = tile.width || 8;
                        const height = tile.height || 8;
                        const totalPixels = width * height;

                        // Create grid of pixels
                        const slicedColors = tile.colors.slice(0, totalPixels);
                        const pixelsHtml = slicedColors.map(color => {
                            const rgb = hsbkToRgb(color);
                            const bgStyle = `background: ${rgb};`;
                            return `<div class="tile-pixel" style="${bgStyle}"></div>`;
                        }).join('');

                        const labelStyle = (
                            'font-size: 0.7em; color: #666; ' +
                            'margin-bottom: 2px; text-align: center;'
                        );
                        const gridStyle = (
                            `grid-template-columns: repeat(${width}, 8px);`
                        );
                        return `
                            <div class="tile-item">
                                <div style="${labelStyle}">
                                    T${tileIndex + 1}
                                </div>
                                <div class="tile-grid" style="${gridStyle}">
                                    ${pixelsHtml}
                                </div>
                            </div>
                        `;
                    }).join('');

                    const tileCount = dev.tile_devices.length;
                    const toggleId = `zones-toggle-${dev.serial}`;
                    const toggleClick = `toggleZones('${dev.serial}')`;
                    zonesHtml = `
                        <div
                            class="zones-toggle"
                            id="${toggleId}"
                            onclick="${toggleClick}"
                        >
                            ▸ Show tiles (${tileCount})
                        </div>
                        <div id="zones-${dev.serial}" class="zones-display">
                            <div class="tiles-container">
                                ${tilesHtml}
                            </div>
                        </div>
                    `;
                } else if (dev.has_color && dev.color) {
                    const rgb = hsbkToRgb(dev.color);
                    const swatchStyle = `background: ${rgb};`;
                    const textStyle = 'color: #888; font-size: 0.75em;';
                    zonesHtml = `
                        <div style="margin-top: 4px;">
                            <span class="color-swatch" style="${swatchStyle}"></span>
                            <span style="${textStyle}">Current color</span>
                        </div>
                    `;
                }

                return `
                    <div class="device">
                        <div class="device-header">
                            <div>
                                <div class="device-serial">${dev.serial}</div>
                                <div class="device-label">${dev.label}</div>
                            </div>
                            <button
                                class="btn btn-delete"
                                onclick="deleteDevice('${dev.serial}')"
                            >Del</button>
                        </div>
                        <div>
                            ${powerBadge}
                            <span class="badge badge-capability">P${dev.product}</span>
                            ${capabilities.map(c => (
                                `<span class="badge badge-capability">${c}</span>`
                            )).join('')}
                            ${capabilityBadges.join('')}
                        </div>
                        ${metadataHtml}
                        ${zonesHtml}
                    </div>
                `;
                }).join('');

                document.getElementById('devices').innerHTML = devicesHtml;

                // Restore toggle states for all devices
                devices.forEach(dev => restoreToggleStates(dev.serial));
            } catch (error) {
                console.error('Failed to fetch devices:', error);
                const errorStyle = 'color: #d32f2f;';
                const errorHtml = (
                    `<div class="no-devices" style="${errorStyle}">` +
                    `Error loading devices: ${error.message}</div>`
                );
                document.getElementById('devices').innerHTML = errorHtml;
            }
        }

        async function fetchActivity() {
            try {
                const response = await fetch('/api/activity');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const activities = await response.json();

                const activityHtml = activities.slice().reverse().map(act => {
                    const timestamp = act.timestamp * 1000;
                    const time = new Date(timestamp).toLocaleTimeString();
                    const isRx = act.direction === 'rx';
                    const dirClass = isRx ? 'activity-rx' : 'activity-tx';
                    const dirLabel = isRx ? 'RX' : 'TX';
                    const device = act.device || act.target || 'N/A';

                    return `
                        <div class="activity-item">
                            <span class="activity-time">${time}</span>
                            <span class="${dirClass}">${dirLabel}</span>
                            <span class="activity-packet">${act.packet_name}</span>
                            <span class="device-serial">${device}</span>
                            <span style="color: #666">${act.addr}</span>
                        </div>
                    `;
                }).join('');

                const noActivity = '<div style="color: #666">No activity yet</div>';
                const logElement = document.getElementById('activity-log');
                logElement.innerHTML = activityHtml || noActivity;
            } catch (error) {
                console.error('Failed to fetch activity:', error);
                const errorStyle = 'color: #d32f2f;';
                const errorHtml = (
                    `<div style="${errorStyle}">` +
                    `Error loading activity: ${error.message}</div>`
                );
                document.getElementById('activity-log').innerHTML = errorHtml;
            }
        }

        async function deleteDevice(serial) {
            if (!confirm(`Delete device ${serial}?`)) return;

            const response = await fetch(`/api/devices/${serial}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await updateAll();
            } else {
                alert('Failed to delete device');
            }
        }

        async function removeAllDevices() {
            const deviceCount = document.getElementById('device-count').textContent;
            if (deviceCount === '0') {
                alert('No devices to remove');
                return;
            }

            const line1 = (
                `Remove all ${deviceCount} device(s) from the server?\\n\\n`
            );
            const line2 = (
                'This will stop all devices from ' +
                'responding to LIFX protocol packets, '
            );
            const line3 = 'but will not delete persistent storage.';
            const confirmMsg = line1 + line2 + line3;
            if (!confirm(confirmMsg)) return;

            const response = await fetch('/api/devices', {
                method: 'DELETE'
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                await updateAll();
            } else {
                alert('Failed to remove all devices');
            }
        }

        async function clearStorage() {
            const confirmMsg = `Clear all persistent device state from storage?\\n\\n` +
                `This will permanently delete all saved device state files. ` +
                `Currently running devices will not be affected.\\n\\n` +
                `This action cannot be undone.`;
            if (!confirm(confirmMsg)) return;

            const response = await fetch('/api/storage', {
                method: 'DELETE'
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
            } else if (response.status === 503) {
                alert('Persistent storage is not enabled on this server');
            } else {
                alert('Failed to clear storage');
            }
        }

        const addDeviceForm = document.getElementById('add-device-form');
        addDeviceForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const productId = parseInt(document.getElementById('product-id').value);

            const response = await fetch('/api/devices', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ product_id: productId })
            });

            if (response.ok) {
                await updateAll();
            } else {
                const error = await response.json();
                alert(`Failed to create device: ${error.detail}`);
            }
        });

        async function updateAll() {
            const activityEnabled = await fetchStats();
            const tasks = [fetchDevices()];
            if (activityEnabled) {
                tasks.push(fetchActivity());
            }
            await Promise.all(tasks);
        }

        // Initial load
        updateAll();

        // Auto-refresh every 2 seconds
        updateInterval = setInterval(updateAll, 2000);
    </script>
</body>
</html>
"""
