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
