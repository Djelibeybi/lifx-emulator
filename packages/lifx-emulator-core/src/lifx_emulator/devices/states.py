"""Focused state dataclasses following Single Responsibility Principle."""

from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lifx_emulator.constants import LIFX_UDP_PORT
from lifx_emulator.protocol.protocol_types import Button as ButtonStruct
from lifx_emulator.protocol.protocol_types import (
    ButtonAction,
    ButtonBacklightHsbk,
    ButtonGesture,
    ButtonTarget,
    ButtonTargetType,
    LightHsbk,
)


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
    # Optional multi-service discovery advertisement: a list of
    # (service_id, port) tuples emitted as one StateService reply each, in
    # order, in response to GetService. service_id is a raw uint8 (0-255) and
    # may be a value outside the DeviceService enum (real hardware advertises
    # reserved/embedded services). None means "advertise UDP on this device's
    # port", preserving the historical single-reply behaviour.
    advertised_services: list[tuple[int, int]] | None = None


class Connectivity(str, Enum):
    """How a device's radio reaches the network.

    A real LIFX device's radio is either WiFi or Thread and cannot change
    without a firmware crossgrade, so this value is invariant for a given
    device rather than a per-request transport choice.
    """

    WIFI = "wifi"
    THREAD = "thread"

    # Render as the bare value on every supported Python version (3.10-3.14).
    # CPython 3.11 changed Enum.__format__ to use str(self) unless the enum
    # also inherits ReprEnum (only IntEnum/StrEnum/IntFlag do), so a
    # hand-written (str, Enum) member regresses to "Connectivity.THREAD" in
    # f-strings/%s on 3.11+ without this -- and this project's own default
    # `uv sync` environment resolves to Python 3.14.
    __str__ = str.__str__


def coerce_connectivity(value: Connectivity | str) -> Connectivity:
    """Coerce a caller-supplied value to a Connectivity member.

    Args:
        value: A Connectivity member, or one of its string values
            ("wifi", "thread").

    Returns:
        The corresponding Connectivity member.

    Raises:
        ValueError: If value is not a recognised connectivity.
    """
    try:
        return Connectivity(value)
    except ValueError as e:
        raise ValueError(
            f"Unrecognised connectivity {value!r}; expected 'wifi' or 'thread'"
        ) from e


@dataclass(frozen=True)
class NetworkState:
    """Network and connectivity state.

    Immutable: a real LIFX device's radio (WiFi or Thread) cannot change
    without a firmware crossgrade, so both ``wifi_signal`` and
    ``connectivity`` are fixed at construction. Assigning
    ``state.connectivity`` or ``state.wifi_signal`` after construction
    raises ValueError (translated from FrozenInstanceError by
    DeviceState.__setattr__); assigning ``state.network.connectivity`` or
    ``state.network.wifi_signal`` directly raises FrozenInstanceError. The
    way to set either value is the ``connectivity`` argument on the
    factories or ``DeviceBuilder.with_connectivity()`` at construction time.

    Wholesale replacement of the whole ``NetworkState`` object via
    ``dataclasses.replace(state.network, ...)`` followed by reassigning
    ``state.network`` is a builder-internal construction/restore mechanism
    used to compose and restore devices, not a supported way to change
    values after construction.
    """

    wifi_signal: float = -45.0
    connectivity: Connectivity = Connectivity.WIFI


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
class TileFramebuffers:
    """Internal storage for non-visible tile framebuffers (1-7).

    Framebuffer 0 is stored in tile_devices[i]["colors"] (the visible buffer).
    Framebuffers 1-7 are stored here for Set64/CopyFrameBuffer operations.
    Each framebuffer is a list of LightHsbk colors with length = width * height.
    """

    tile_index: int  # Which tile this belongs to
    framebuffers: dict[int, list[LightHsbk]] = field(default_factory=dict)

    def get_framebuffer(
        self, fb_index: int, width: int, height: int
    ) -> list[LightHsbk]:
        """Get framebuffer by index, creating it if needed."""
        if fb_index not in self.framebuffers:
            # Initialize with default black color
            zones = width * height
            self.framebuffers[fb_index] = [
                LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
                for _ in range(zones)
            ]
        return self.framebuffers[fb_index]


@dataclass
class MatrixState:
    """Matrix (tile/candle) capability state."""

    tile_count: int
    tile_devices: list[dict[str, Any]]
    tile_width: int
    tile_height: int
    effect_type: int = 0  # 0=OFF, 2=MORPH, 3=FLAME, 5=SKY
    effect_speed: int = 5  # Duration of one cycle in seconds
    effect_palette_count: int = 0
    effect_palette: list[LightHsbk] = field(default_factory=list)
    effect_sky_type: int = 0  # 0=SUNRISE, 1=SUNSET, 2=CLOUDS (only when effect_type=5)
    effect_cloud_sat_min: int = (
        0  # Min cloud saturation 0-200 (only when effect_type=5)
    )
    effect_cloud_sat_max: int = (
        0  # Max cloud saturation 0-200 (only when effect_type=5)
    )
    # Internal storage for non-visible framebuffers (1-7) per tile
    # Framebuffer 0 remains in tile_devices[i]["colors"]
    tile_framebuffers: list[TileFramebuffers] = field(default_factory=list)


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


# Button.State/Set pack a fixed [8]<Button> array on the wire, and each Button
# struct always unpacks exactly 5 ButtonAction entries (see
# protocol_types.Button.unpack). Any button we synthesise must match that shape
# exactly, or a round trip through pack()/unpack() misaligns every subsequent
# button in the array.
BUTTONS_ARRAY_LENGTH = 8
ACTIONS_PER_BUTTON = 5


def default_button_action() -> ButtonAction:
    """A neutral, valid ButtonAction used to fill unused action slots."""
    return ButtonAction(
        gesture=ButtonGesture.PRESS,
        target_type=ButtonTargetType.RESERVED_0,
        target=ButtonTarget(data=b"\x00" * 16),
    )


def default_button() -> ButtonStruct:
    """A neutral Button struct with exactly 5 action slots (wire-format shape)."""
    return ButtonStruct(
        actions_count=0,
        actions=[default_button_action() for _ in range(ACTIONS_PER_BUTTON)],
    )


@dataclass
class ButtonsState:
    """Button config + per-button state for button-capable devices."""

    haptic_duration_ms: int = 0
    backlight_on: ButtonBacklightHsbk = field(
        default_factory=lambda: ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=0, kelvin=3500
        )
    )
    backlight_off: ButtonBacklightHsbk = field(
        default_factory=lambda: ButtonBacklightHsbk(
            hue=0, saturation=0, brightness=0, kelvin=3500
        )
    )
    buttons: list = field(default_factory=list)


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
    has_chain: bool = False
    has_hev: bool = False
    has_relays: bool = False
    has_buttons: bool = False

    # Ambient light sensor, button and uplight state (Ceiling/Mirror devices)
    ambient_light_lux: float = 0.0
    uplight_zone_count: int | None = None
    buttons_state: ButtonsState = field(default_factory=ButtonsState)

    @property
    def has_uplight(self) -> bool:
        """Whether this device reports a separate uplight zone range."""
        return self.uplight_zone_count is not None

    @property
    def downlight_zone_count(self) -> int | None:
        """Matrix zones excluding the uplight range, if applicable."""
        # `matrix` must be present as well as the flag: tile_width/tile_height
        # otherwise resolve through the 8x8 fallback defaults and yield a zone
        # count that belongs to no real device.
        if self.uplight_zone_count is None or not self.has_matrix or not self.matrix:
            return None
        return self.tile_width * self.tile_height - self.uplight_zone_count

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
        "advertised_services": "core",
        # Network properties
        "wifi_signal": "network",
        "connectivity": "network",
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
        "tile_effect_sky_type": ("matrix", "effect_sky_type"),
        "tile_effect_cloud_sat_min": ("matrix", "effect_cloud_sat_min"),
        "tile_effect_cloud_sat_max": ("matrix", "effect_cloud_sat_max"),
        "tile_framebuffers": "matrix",
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
        "tile_effect_sky_type": 0,
        "tile_effect_cloud_sat_min": 0,
        "tile_effect_cloud_sat_max": 0,
        "tile_framebuffers": [],
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
            # dataclasses.replace(state.network, ...)-then-assign is a
            # construction/restore route retained for the builder; it is
            # builder-internal, not part of the published API.
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
            "has_chain",
            "has_hev",
            "has_relays",
            "has_buttons",
            "ambient_light_lux",
            "uplight_zone_count",
            "buttons_state",
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
            try:
                setattr(state_obj, attr_name, value)
            except dataclasses.FrozenInstanceError as e:
                raise ValueError(
                    f"{attr_name} is fixed at device creation and cannot be "
                    "reassigned; pass it as an argument to the device "
                    "factory or DeviceBuilder when constructing the device "
                    "instead"
                ) from e
            return

        # For unknown attributes, use normal assignment (allows adding new attributes)
        object.__setattr__(self, name, value)
