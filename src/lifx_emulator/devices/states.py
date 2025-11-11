"""Focused state dataclasses following Single Responsibility Principle."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from lifx_emulator.constants import LIFX_UDP_PORT
from lifx_emulator.protocol.protocol_types import LightHsbk


@dataclass
class CoreDeviceState:
    """Core device identification and basic state."""

    serial: str
    label: str
    power_level: int
    color: LightHsbk
    vendor: int
    product: int
    version_major: int
    version_minor: int
    build_timestamp: int
    uptime_ns: int = 0
    mac_address: bytes = field(default_factory=lambda: bytes.fromhex("d073d5123456"))
    port: int = LIFX_UDP_PORT


@dataclass
class NetworkState:
    """Network and connectivity state."""

    wifi_signal: float = -45.0


@dataclass
class LocationState:
    """Device location metadata."""

    location_id: bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    location_label: str = "Test Location"
    location_updated_at: int = field(default_factory=lambda: int(time.time() * 1e9))


@dataclass
class GroupState:
    """Device group metadata."""

    group_id: bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    group_label: str = "Test Group"
    group_updated_at: int = field(default_factory=lambda: int(time.time() * 1e9))


@dataclass
class InfraredState:
    """Infrared capability state."""

    infrared_brightness: int = 0  # 0-65535


@dataclass
class HevState:
    """HEV (germicidal UV) capability state."""

    hev_cycle_duration_s: int = 7200  # 2 hours default
    hev_cycle_remaining_s: int = 0
    hev_cycle_last_power: bool = False
    hev_indication: bool = True
    hev_last_result: int = 0  # 0=success


@dataclass
class MultiZoneState:
    """Multizone (strip/beam) capability state."""

    zone_count: int
    zone_colors: list[LightHsbk]
    effect_type: int = 0  # 0=OFF, 1=MOVE, 2=RESERVED
    effect_speed: int = 5  # Duration of one cycle in seconds


@dataclass
class MatrixState:
    """Matrix (tile/candle) capability state."""

    tile_count: int
    tile_devices: list[dict[str, Any]]
    tile_width: int
    tile_height: int
    effect_type: int = 0  # 0=OFF, 2=MORPH, 3=FLAME
    effect_speed: int = 5  # Duration of one cycle in seconds
    effect_palette_count: int = 0
    effect_palette: list[LightHsbk] = field(default_factory=list)


@dataclass
class WaveformState:
    """Waveform effect state."""

    waveform_active: bool = False
    waveform_type: int = 0
    waveform_transient: bool = False
    waveform_color: LightHsbk = field(
        default_factory=lambda: LightHsbk(
            hue=0, saturation=0, brightness=0, kelvin=3500
        )
    )
    waveform_period_ms: int = 0
    waveform_cycles: float = 0
    waveform_duty_cycle: int = 0
    waveform_skew_ratio: int = 0


@dataclass
class DeviceState:
    """Composed device state following Single Responsibility Principle.

    Each aspect of device state is managed by a focused sub-state object.
    Properties are automatically delegated to the appropriate state object
    using __getattr__ and __setattr__ magic methods.

    Examples:
        >>> state.label  # Delegates to state.core.label
        >>> state.location_label  # Delegates to state.location.location_label
        >>> state.zone_count  # Delegates to state.multizone.zone_count (if present)
    """

    core: CoreDeviceState
    network: NetworkState
    location: LocationState
    group: GroupState
    waveform: WaveformState

    # Optional capability-specific state
    infrared: InfraredState | None = None
    hev: HevState | None = None
    multizone: MultiZoneState | None = None
    matrix: MatrixState | None = None

    # Capability flags (kept for convenience)
    has_color: bool = True
    has_infrared: bool = False
    has_multizone: bool = False
    has_extended_multizone: bool = False
    has_matrix: bool = False
    has_hev: bool = False

    # Attribute routing map: maps attribute prefixes to state objects
    # This eliminates ~360 lines of property boilerplate
    _ATTRIBUTE_ROUTES = {
        # Core properties (no prefix)
        "serial": "core",
        "label": "core",
        "power_level": "core",
        "color": "core",
        "vendor": "core",
        "product": "core",
        "version_major": "core",
        "version_minor": "core",
        "build_timestamp": "core",
        "uptime_ns": "core",
        "mac_address": "core",
        "port": "core",
        # Network properties
        "wifi_signal": "network",
        # Location properties
        "location_id": "location",
        "location_label": "location",
        "location_updated_at": "location",
        # Group properties
        "group_id": "group",
        "group_label": "group",
        "group_updated_at": "group",
        # Waveform properties
        "waveform_active": "waveform",
        "waveform_type": "waveform",
        "waveform_transient": "waveform",
        "waveform_color": "waveform",
        "waveform_period_ms": "waveform",
        "waveform_cycles": "waveform",
        "waveform_duty_cycle": "waveform",
        "waveform_skew_ratio": "waveform",
        # Infrared properties
        "infrared_brightness": "infrared",
        # HEV properties
        "hev_cycle_duration_s": "hev",
        "hev_cycle_remaining_s": "hev",
        "hev_cycle_last_power": "hev",
        "hev_indication": "hev",
        "hev_last_result": "hev",
        # Multizone properties
        "zone_count": "multizone",
        "zone_colors": "multizone",
        "multizone_effect_type": ("multizone", "effect_type"),
        "multizone_effect_speed": ("multizone", "effect_speed"),
        # Matrix/Tile properties
        "tile_count": "matrix",
        "tile_devices": "matrix",
        "tile_width": "matrix",
        "tile_height": "matrix",
        "tile_effect_type": ("matrix", "effect_type"),
        "tile_effect_speed": ("matrix", "effect_speed"),
        "tile_effect_palette_count": ("matrix", "effect_palette_count"),
        "tile_effect_palette": ("matrix", "effect_palette"),
    }

    # Default values for optional state attributes when state object is None
    _OPTIONAL_DEFAULTS = {
        "infrared_brightness": 0,
        "hev_cycle_duration_s": 0,
        "hev_cycle_remaining_s": 0,
        "hev_cycle_last_power": False,
        "hev_indication": False,
        "hev_last_result": 0,
        "zone_count": 0,
        "zone_colors": [],
        "multizone_effect_type": 0,
        "multizone_effect_speed": 0,
        "tile_count": 0,
        "tile_devices": [],
        "tile_width": 8,
        "tile_height": 8,
        "tile_effect_type": 0,
        "tile_effect_speed": 0,
        "tile_effect_palette_count": 0,
        "tile_effect_palette": [],
    }

    def get_target_bytes(self) -> bytes:
        """Get target bytes for this device."""
        return bytes.fromhex(self.core.serial) + b"\x00\x00"

    def __getattr__(self, name: str) -> Any:
        """Dynamically delegate attribute access to appropriate state object.

        This eliminates ~180 lines of @property boilerplate.

        Args:
            name: Attribute name being accessed

        Returns:
            Attribute value from the appropriate state object

        Raises:
            AttributeError: If attribute is not found
        """
        # Check if this attribute has a routing rule
        if name in self._ATTRIBUTE_ROUTES:
            route = self._ATTRIBUTE_ROUTES[name]

            # Route can be either 'state_name' or ('state_name', 'attr_name')
            if isinstance(route, tuple):
                state_name, attr_name = route
            else:
                state_name = route
                attr_name = name

            # Get the state object
            state_obj = object.__getattribute__(self, state_name)

            # Handle optional state objects (infrared, hev, multizone, matrix)
            if state_obj is None:
                # Return default value for optional attributes
                return self._OPTIONAL_DEFAULTS.get(name)

            # Delegate to the state object
            return getattr(state_obj, attr_name)

        # If not in routing map, raise AttributeError
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """Dynamically delegate attribute writes to appropriate state object.

        This eliminates ~180 lines of @property.setter boilerplate.

        Args:
            name: Attribute name being set
            value: Value to set

        Note:
            Dataclass fields and private attributes bypass delegation.
        """
        # Dataclass fields and private attributes use normal assignment
        if name in {
            "core",
            "network",
            "location",
            "group",
            "waveform",
            "infrared",
            "hev",
            "multizone",
            "matrix",
            "has_color",
            "has_infrared",
            "has_multizone",
            "has_extended_multizone",
            "has_matrix",
            "has_hev",
        } or name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        # Check if this attribute has a routing rule
        if name in self._ATTRIBUTE_ROUTES:
            route = self._ATTRIBUTE_ROUTES[name]

            # Route can be either 'state_name' or ('state_name', 'attr_name')
            if isinstance(route, tuple):
                state_name, attr_name = route
            else:
                state_name = route
                attr_name = name

            # Get the state object
            state_obj = object.__getattribute__(self, state_name)

            # Handle optional state objects - silently ignore writes if None
            if state_obj is None:
                return

            # Delegate to the state object
            setattr(state_obj, attr_name, value)
            return

        # For unknown attributes, use normal assignment (allows adding new attributes)
        object.__setattr__(self, name, value)
