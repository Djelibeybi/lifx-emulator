"""Configuration file support for lifx-emulator CLI."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

AUTO_DETECT_FILENAMES = ("lifx-emulator.yaml", "lifx-emulator.yml")
ENV_VAR = "LIFX_EMULATOR_CONFIG"


class DeviceDefinition(BaseModel):
    """A single device definition in the config file."""

    product_id: int
    label: str | None = None
    zone_count: int | None = None
    tile_count: int | None = None
    tile_width: int | None = None
    tile_height: int | None = None


class EmulatorConfig(BaseModel):
    """Configuration file schema for lifx-emulator."""

    # Server options
    bind: str | None = None
    port: int | None = None
    verbose: bool | None = None

    # Storage & Persistence
    persistent: bool | None = None
    persistent_scenarios: bool | None = None

    # HTTP API Server
    api: bool | None = None
    api_host: str | None = None
    api_port: int | None = None
    api_activity: bool | None = None

    # Device creation (counts)
    products: list[int] | None = None
    color: int | None = None
    color_temperature: int | None = None
    infrared: int | None = None
    hev: int | None = None
    multizone: int | None = None
    tile: int | None = None
    switch: int | None = None

    # Multizone options
    multizone_zones: int | None = None
    multizone_extended: bool | None = None

    # Tile/Matrix options
    tile_count: int | None = None
    tile_width: int | None = None
    tile_height: int | None = None

    # Serial number options
    serial_prefix: str | None = None
    serial_start: int | None = None

    # Per-device definitions
    devices: list[DeviceDefinition] | None = None

    @field_validator("serial_prefix")
    @classmethod
    def validate_serial_prefix(cls, v: str | None) -> str | None:
        if v is not None and (
            len(v) != 6
            or not all(c in "0123456789abcdefABCDEF" for c in v)
        ):
            msg = "serial_prefix must be exactly 6 hex characters"
            raise ValueError(msg)
        return v

    model_config = {"extra": "forbid"}


def resolve_config_path(config_flag: str | None) -> Path | None:
    """Resolve the config file path from flag, env var, or auto-detect.

    Priority: --config flag > LIFX_EMULATOR_CONFIG env var > auto-detect in cwd.
    Returns None if no config file is found.
    """
    # 1. Explicit --config flag
    if config_flag is not None:
        path = Path(config_flag)
        if not path.is_file():
            msg = f"Config file not found: {path}"
            raise FileNotFoundError(msg)
        return path

    # 2. Environment variable
    env_path = os.environ.get(ENV_VAR)
    if env_path:
        path = Path(env_path)
        if not path.is_file():
            msg = f"Config file from {ENV_VAR} not found: {path}"
            raise FileNotFoundError(msg)
        return path

    # 3. Auto-detect in current working directory
    for filename in AUTO_DETECT_FILENAMES:
        path = Path.cwd() / filename
        if path.is_file():
            return path

    return None


def load_config(path: Path) -> EmulatorConfig:
    """Load and validate a config file from the given path."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        return EmulatorConfig()

    if not isinstance(raw, dict):
        msg = f"Config file must contain a YAML mapping, got {type(raw).__name__}"
        raise ValueError(msg)

    return EmulatorConfig.model_validate(raw)


def merge_config(
    config: EmulatorConfig,
    cli_overrides: dict[str, Any],
) -> dict[str, Any]:
    """Merge config file values with CLI overrides.

    CLI overrides (non-None values) take priority over config file values.
    Returns a flat dict of final parameter values with defaults applied.
    """
    defaults: dict[str, Any] = {
        "bind": "127.0.0.1",
        "port": 56700,
        "verbose": False,
        "persistent": False,
        "persistent_scenarios": False,
        "api": False,
        "api_host": "127.0.0.1",
        "api_port": 8080,
        "api_activity": True,
        "products": None,
        "color": 0,
        "color_temperature": 0,
        "infrared": 0,
        "hev": 0,
        "multizone": 0,
        "tile": 0,
        "switch": 0,
        "multizone_zones": None,
        "multizone_extended": True,
        "tile_count": None,
        "tile_width": None,
        "tile_height": None,
        "serial_prefix": "d073d5",
        "serial_start": 1,
        "devices": None,
    }

    # Start with defaults
    result = dict(defaults)

    # Layer config file values (override defaults where set)
    config_dict = config.model_dump(exclude_none=True)
    for key, value in config_dict.items():
        if key in result:
            result[key] = value

    # Layer CLI overrides (override config where explicitly set)
    for key, value in cli_overrides.items():
        if value is not None and key in result:
            result[key] = value

    return result
