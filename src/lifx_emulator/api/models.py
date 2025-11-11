"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, field_validator

# Import shared domain models
from lifx_emulator.scenarios import ScenarioConfig


class DeviceCreateRequest(BaseModel):
    """Request to create a new device."""

    product_id: int = Field(
        ..., description="Product ID from LIFX registry", gt=0, lt=10000
    )
    serial: str | None = Field(
        None,
        description="Optional serial (auto-generated if not provided)",
        min_length=12,
        max_length=12,
    )
    zone_count: int | None = Field(
        None, description="Number of zones for multizone devices", ge=0, le=1000
    )
    tile_count: int | None = Field(
        None, description="Number of tiles for matrix devices", ge=0, le=100
    )
    tile_width: int | None = Field(
        None, description="Width of each tile in pixels", ge=1, le=256
    )
    tile_height: int | None = Field(
        None, description="Height of each tile in pixels", ge=1, le=256
    )
    firmware_major: int | None = Field(
        None, description="Firmware major version", ge=0, le=255
    )
    firmware_minor: int | None = Field(
        None, description="Firmware minor version", ge=0, le=255
    )

    @field_validator("serial")
    @classmethod
    def validate_serial_format(cls, v: str | None) -> str | None:
        """Validate serial number format (12 hex characters)."""
        if v is None:
            return v
        if len(v) != 12:
            raise ValueError("Serial must be exactly 12 characters")
        try:
            # Validate it's valid hexadecimal by parsing as base-16 integer
            int(v, 16)
        except ValueError as e:
            raise ValueError("Serial must be valid hexadecimal (0-9, a-f, A-F)") from e
        return v.lower()  # Normalize to lowercase


class ColorHsbk(BaseModel):
    """HSBK color representation."""

    hue: int = Field(..., ge=0, le=65535, description="Hue (0-65535)")
    saturation: int = Field(..., ge=0, le=65535, description="Saturation (0-65535)")
    brightness: int = Field(..., ge=0, le=65535, description="Brightness (0-65535)")
    kelvin: int = Field(
        ..., ge=1500, le=9000, description="Color temperature in Kelvin (1500-9000)"
    )


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


class ScenarioResponse(BaseModel):
    """Response model for scenario operations."""

    scope: str = Field(
        ..., description="Scope of the scenario (global, device, type, location, group)"
    )
    identifier: str | None = Field(
        None, description="Identifier for the scope (serial, type name, etc.)"
    )
    scenario: ScenarioConfig | None = Field(
        None, description="The scenario configuration (None if not set)"
    )
