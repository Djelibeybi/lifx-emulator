"""CLI entry point for lifx-emulator."""

import asyncio
import json
import logging
import signal
import uuid
import warnings
from pathlib import Path
from typing import Annotated

import cyclopts
import yaml
from lifx_emulator.devices import (
    DEFAULT_STORAGE_DIR,
    DeviceManager,
    DevicePersistenceAsyncFile,
)
from lifx_emulator.devices.state_serializer import deserialize_device_state
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_device,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_switch,
    create_tile_device,
)
from lifx_emulator.products.registry import get_registry
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import (
    HierarchicalScenarioManager,
    ScenarioConfig,
    ScenarioPersistenceAsyncFile,
)
from lifx_emulator.server import EmulatedLifxServer
from rich.logging import RichHandler

from lifx_emulator_app.config import (
    EmulatorConfig,
    ScenarioDefinition,
    ScenariosConfig,
    load_config,
    merge_config,
    resolve_config_path,
)

app = cyclopts.App(
    name="lifx-emulator",
    help="LIFX LAN Protocol Emulator provides virtual LIFX devices for testing",
)
app.register_install_completion_command()

# Parameter groups for organizing help output
config_group = cyclopts.Group.create_ordered("Configuration")
server_group = cyclopts.Group.create_ordered("Server Options")
storage_group = cyclopts.Group.create_ordered("Storage & Persistence")
api_group = cyclopts.Group.create_ordered("HTTP API Server")
device_group = cyclopts.Group.create_ordered("Device Creation")
multizone_group = cyclopts.Group.create_ordered("Multizone Options")
tile_group = cyclopts.Group.create_ordered("Tile/Matrix Options")
serial_group = cyclopts.Group.create_ordered("Serial Number Options")


def _setup_logging(verbose: bool) -> logging.Logger:
    """Configure logging based on verbosity level."""
    log_format = "%(message)s"
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format=log_format, handlers=[RichHandler()], level=level)

    _logger = logging.getLogger(__package__)

    if verbose:
        _logger.debug("Verbose logging enabled")

    return _logger


def _format_capabilities(device) -> str:
    """Format device capabilities as a human-readable string."""
    capabilities = []
    if device.state.has_color:
        capabilities.append("color")
    elif not device.state.has_color:
        capabilities.append("white-only")
    if device.state.has_infrared:
        capabilities.append("infrared")
    if device.state.has_hev:
        capabilities.append("HEV")
    if device.state.has_multizone:
        if device.state.zone_count > 16:
            capabilities.append(f"extended-multizone({device.state.zone_count})")
        else:
            capabilities.append(f"multizone({device.state.zone_count})")
    if device.state.has_matrix:
        total_zones = device.state.tile_width * device.state.tile_height
        if total_zones > 64:
            dim = f"{device.state.tile_width}x{device.state.tile_height}"
            capabilities.append(f"tile({device.state.tile_count}x {dim})")
        else:
            capabilities.append(f"tile({device.state.tile_count})")
    return ", ".join(capabilities)


@app.command
def list_products(
    filter_type: str | None = None,
) -> None:
    """List all available LIFX products from the registry.

    Products are sorted by product ID and display their name and supported
    features including color, multizone, matrix, HEV, and infrared capabilities.

    Args:
        filter_type: Filter by capability (color, multizone, matrix, hev, infrared).
            If not specified, lists all products.

    Examples:
        List all products:
            lifx-emulator list-products

        List only multizone products:
            lifx-emulator list-products --filter-type multizone

        List only matrix/tile products:
            lifx-emulator list-products --filter-type matrix
    """
    registry = get_registry()

    # Get all products sorted by PID
    all_products = []
    for pid in sorted(registry._products.keys()):
        product = registry._products[pid]
        # Apply filter if specified
        if filter_type:
            filter_lower = filter_type.lower()
            if filter_lower == "color" and not product.has_color:
                continue
            if filter_lower == "multizone" and not product.has_multizone:
                continue
            if filter_lower == "matrix" and not product.has_matrix:
                continue
            if filter_lower == "hev" and not product.has_hev:
                continue
            if filter_lower == "infrared" and not product.has_infrared:
                continue
        all_products.append(product)

    if not all_products:
        if filter_type:
            print(f"No products found with filter: {filter_type}")
        else:
            print("No products in registry")
        return

    print(f"\nLIFX Product Registry ({len(all_products)} products)\n")
    print(f"{'PID':>4} │ {'Product Name':<40} │ {'Capabilities'}")
    print("─" * 4 + "─┼─" + "─" * 40 + "─┼─" + "─" * 40)

    for product in all_products:
        print(f"{product.pid:>4} │ {product.name:<40} │ {product.caps}")

    print()
    print("Use --product <PID> to emulate a specific product")
    print(f"Example: lifx-emulator --product {all_products[0].pid}")


@app.command
def clear_storage(
    storage_dir: str | None = None,
    yes: bool = False,
) -> None:
    """Clear all persistent device state from storage.

    Deletes all saved device state files from the persistent storage directory.
    Use this when you want to start fresh without any saved devices. A confirmation
    prompt is shown unless --yes is specified.

    Args:
        storage_dir: Storage directory to clear. Defaults to ~/.lifx-emulator if
            not specified.
        yes: Skip confirmation prompt and delete immediately.

    Examples:
        Clear default storage location (with confirmation):
            lifx-emulator clear-storage

        Clear without confirmation prompt:
            lifx-emulator clear-storage --yes

        Clear custom storage directory:
            lifx-emulator clear-storage --storage-dir /path/to/storage
    """
    # Use default storage directory if not specified
    storage_path = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR

    # Create storage instance
    storage = DevicePersistenceAsyncFile(storage_path)

    # List devices
    devices = storage.list_devices()

    if not devices:
        print(f"No persistent device states found in {storage_path}")
        return

    # Show what will be deleted
    print(f"\nFound {len(devices)} persistent device state(s) in {storage_path}:")
    for serial in devices:
        print(f"  • {serial}")

    # Confirm deletion
    if not yes:
        print(
            f"\nThis will permanently delete all {len(devices)} device state file(s)."
        )
        response = input("Are you sure you want to continue? [y/N] ")
        if response.lower() not in ("y", "yes"):
            print("Operation cancelled.")
            return

    # Delete all device states
    deleted = storage.delete_all_device_states()
    print(f"\nSuccessfully deleted {deleted} device state(s).")


def _device_state_to_yaml_dict(state_dict: dict) -> dict:
    """Convert a persistent device state dict to a config-file device entry.

    Only includes fields that are meaningful for initial configuration.
    Skips runtime-only fields (effects, tile positions, framebuffers, etc.).
    """
    entry: dict = {"product_id": state_dict["product"]}

    entry["serial"] = state_dict["serial"]

    if state_dict.get("label"):
        entry["label"] = state_dict["label"]

    if state_dict.get("power_level", 0) != 0:
        entry["power_level"] = state_dict["power_level"]

    # Color - always include since defaults vary per product
    color = state_dict.get("color")
    if color:
        if isinstance(color, dict):
            entry["color"] = [
                color["hue"],
                color["saturation"],
                color["brightness"],
                color["kelvin"],
            ]
        else:
            # LightHsbk dataclass (already deserialized)
            entry["color"] = [
                color.hue,
                color.saturation,
                color.brightness,
                color.kelvin,
            ]

    loc_label = state_dict.get("location_label")
    if loc_label and loc_label != "Test Location":
        entry["location"] = loc_label

    grp_label = state_dict.get("group_label")
    if grp_label and grp_label != "Test Group":
        entry["group"] = grp_label

    # Multizone zone_colors
    if state_dict.get("has_multizone") and state_dict.get("zone_colors"):
        zone_colors = state_dict["zone_colors"]
        # Check if all zones are the same color - if so, just use color
        all_same = all(
            (
                z.hue == zone_colors[0].hue
                and z.saturation == zone_colors[0].saturation
                and z.brightness == zone_colors[0].brightness
                and z.kelvin == zone_colors[0].kelvin
            )
            if hasattr(z, "hue")
            else (
                z["hue"] == zone_colors[0]["hue"]
                and z["saturation"] == zone_colors[0]["saturation"]
                and z["brightness"] == zone_colors[0]["brightness"]
                and z["kelvin"] == zone_colors[0]["kelvin"]
            )
            for z in zone_colors[1:]
        )
        if not all_same:
            entry["zone_colors"] = [
                [z.hue, z.saturation, z.brightness, z.kelvin]
                if hasattr(z, "hue")
                else [z["hue"], z["saturation"], z["brightness"], z["kelvin"]]
                for z in zone_colors
            ]
        if state_dict.get("zone_count"):
            entry["zone_count"] = state_dict["zone_count"]

    # Infrared
    if state_dict.get("has_infrared") and state_dict.get("infrared_brightness", 0) != 0:
        entry["infrared_brightness"] = state_dict["infrared_brightness"]

    # HEV
    if state_dict.get("has_hev"):
        if state_dict.get("hev_cycle_duration_s", 7200) != 7200:
            entry["hev_cycle_duration"] = state_dict["hev_cycle_duration_s"]
        if state_dict.get("hev_indication") is False:
            entry["hev_indication"] = False

    # Matrix/tile
    if state_dict.get("has_matrix"):
        if state_dict.get("tile_count"):
            entry["tile_count"] = state_dict["tile_count"]
        if state_dict.get("tile_width"):
            entry["tile_width"] = state_dict["tile_width"]
        if state_dict.get("tile_height"):
            entry["tile_height"] = state_dict["tile_height"]

    return entry


def _scenarios_to_yaml_dict(scenario_file: Path) -> dict | None:
    """Load scenarios.json and convert to config-file format.

    Returns a dict suitable for the 'scenarios' key in the YAML config,
    or None if no scenario file exists or it's empty.
    """
    if not scenario_file.exists():
        return None

    try:
        with open(scenario_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    result: dict = {}

    # Convert global scenario
    global_sc = data.get("global", {})
    if global_sc:
        cleaned_global = _clean_scenario(global_sc)
        if cleaned_global:
            result["global"] = cleaned_global

    # Convert scoped scenarios
    for scope in ("devices", "types", "locations", "groups"):
        scope_data = data.get(scope, {})
        if scope_data:
            cleaned = {}
            for key, sc in scope_data.items():
                cleaned_sc = _clean_scenario(sc)
                if cleaned_sc:
                    cleaned[key] = cleaned_sc
            if cleaned:
                result[scope] = cleaned

    return result if result else None


def _clean_scenario(sc: dict) -> dict | None:
    """Remove empty/default fields from a scenario dict."""
    cleaned: dict = {}
    for key, val in sc.items():
        if val is None:
            continue
        if isinstance(val, dict | list) and not val:
            continue
        if val is False and key != "send_unhandled":
            continue
        # Convert string keys in drop_packets/response_delays to int
        if key in ("drop_packets", "response_delays") and isinstance(val, dict):
            cleaned[key] = {int(k): v for k, v in val.items()}
        else:
            cleaned[key] = val
    return cleaned if cleaned else None


@app.command
def export_config(
    storage_dir: str | None = None,
    output: str | None = None,
    no_scenarios: bool = False,
) -> None:
    """Export persistent device storage as a YAML config file.

    Reads saved device state from persistent storage and outputs a valid
    YAML configuration file. This allows migrating from --persistent to a
    config file-based workflow.

    Args:
        storage_dir: Storage directory to read from. Defaults to ~/.lifx-emulator
            if not specified.
        output: Output file path. If not specified, outputs to stdout.
        no_scenarios: Exclude scenarios from the exported config.

    Examples:
        Export to stdout:
            lifx-emulator export-config

        Export to a file:
            lifx-emulator export-config --output my-config.yaml

        Export without scenarios:
            lifx-emulator export-config --no-scenarios

        Export from custom storage directory:
            lifx-emulator export-config --storage-dir /path/to/storage
    """
    storage_path = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR

    if not storage_path.exists():
        print(f"Storage directory not found: {storage_path}")
        return

    # Find all device state files
    device_files = sorted(storage_path.glob("*.json"))
    device_files = [f for f in device_files if f.name != "scenarios.json"]

    if not device_files and not (storage_path / "scenarios.json").exists():
        print(f"No persistent device states found in {storage_path}")
        return

    config: dict = {}
    devices = []

    for device_file in device_files:
        try:
            with open(device_file) as f:
                state_dict = json.load(f)
            state_dict = deserialize_device_state(state_dict)
            entry = _device_state_to_yaml_dict(state_dict)
            devices.append(entry)
        except Exception as e:
            print(f"Warning: Failed to read {device_file.name}: {e}")

    if devices:
        config["devices"] = devices

    # Load scenarios unless excluded
    if not no_scenarios:
        scenario_file = storage_path / "scenarios.json"
        scenarios = _scenarios_to_yaml_dict(scenario_file)
        if scenarios:
            config["scenarios"] = scenarios

    if not config:
        print("No device states or scenarios found to export.")
        return

    # Output YAML
    yaml_output = yaml.dump(
        config,
        default_flow_style=None,
        sort_keys=False,
        allow_unicode=True,
    )

    if output:
        output_path = Path(output)
        with open(output_path, "w") as f:
            f.write(yaml_output)
        print(f"Config exported to {output_path}")
    else:
        print(yaml_output)


def _load_merged_config(**cli_kwargs) -> dict | None:
    """Load config file and merge with CLI overrides.

    Returns the merged config dict, or None on error.
    """
    config_flag = cli_kwargs.pop("config_flag", None)

    try:
        config_path = resolve_config_path(config_flag)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None

    file_config = EmulatorConfig()
    if config_path:
        try:
            file_config = load_config(config_path)
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")
            return None

    cli_overrides = dict(cli_kwargs)

    result = merge_config(file_config, cli_overrides)

    # Carry the devices list from the config (not a CLI parameter)
    if file_config.devices:
        result["devices"] = file_config.devices

    # Carry scenarios from the config (not a CLI parameter)
    if file_config.scenarios:
        result["scenarios"] = file_config.scenarios

    # Store config path for logging
    if config_path:
        result["_config_path"] = str(config_path)

    return result


def _scenario_def_to_core(defn: ScenarioDefinition) -> ScenarioConfig:
    """Convert a config ScenarioDefinition to a core ScenarioConfig."""
    kwargs: dict = {}
    if defn.drop_packets is not None:
        kwargs["drop_packets"] = defn.drop_packets
    if defn.response_delays is not None:
        kwargs["response_delays"] = defn.response_delays
    if defn.malformed_packets is not None:
        kwargs["malformed_packets"] = defn.malformed_packets
    if defn.invalid_field_values is not None:
        kwargs["invalid_field_values"] = defn.invalid_field_values
    if defn.firmware_version is not None:
        kwargs["firmware_version"] = defn.firmware_version
    if defn.partial_responses is not None:
        kwargs["partial_responses"] = defn.partial_responses
    if defn.send_unhandled is not None:
        kwargs["send_unhandled"] = defn.send_unhandled
    return ScenarioConfig(**kwargs)


def _apply_config_scenarios(
    scenarios: ScenariosConfig,
    logger: logging.Logger,
) -> HierarchicalScenarioManager:
    """Create a HierarchicalScenarioManager from config file scenarios."""
    manager = HierarchicalScenarioManager()

    if scenarios.global_scenario:
        manager.set_global_scenario(_scenario_def_to_core(scenarios.global_scenario))
        logger.info("Applied global scenario from config")

    if scenarios.devices:
        for serial, defn in scenarios.devices.items():
            manager.set_device_scenario(serial, _scenario_def_to_core(defn))
        logger.info(
            "Applied %d device scenario(s) from config",
            len(scenarios.devices),
        )

    if scenarios.types:
        for type_name, defn in scenarios.types.items():
            manager.set_type_scenario(type_name, _scenario_def_to_core(defn))
        logger.info(
            "Applied %d type scenario(s) from config",
            len(scenarios.types),
        )

    if scenarios.locations:
        for location, defn in scenarios.locations.items():
            manager.set_location_scenario(location, _scenario_def_to_core(defn))
        logger.info(
            "Applied %d location scenario(s) from config",
            len(scenarios.locations),
        )

    if scenarios.groups:
        for group, defn in scenarios.groups.items():
            manager.set_group_scenario(group, _scenario_def_to_core(defn))
        logger.info(
            "Applied %d group scenario(s) from config",
            len(scenarios.groups),
        )

    return manager


@app.default
async def run(
    *,
    # Configuration
    config: Annotated[str | None, cyclopts.Parameter(group=config_group)] = None,
    # Server Options
    bind: Annotated[str | None, cyclopts.Parameter(group=server_group)] = None,
    port: Annotated[int | None, cyclopts.Parameter(group=server_group)] = None,
    verbose: Annotated[
        bool | None, cyclopts.Parameter(negative="", group=server_group)
    ] = None,
    # Storage & Persistence
    persistent: Annotated[
        bool | None, cyclopts.Parameter(negative="", group=storage_group)
    ] = None,
    persistent_scenarios: Annotated[
        bool | None, cyclopts.Parameter(negative="", group=storage_group)
    ] = None,
    # HTTP API Server
    api: Annotated[
        bool | None, cyclopts.Parameter(negative="", group=api_group)
    ] = None,
    api_host: Annotated[str | None, cyclopts.Parameter(group=api_group)] = None,
    api_port: Annotated[int | None, cyclopts.Parameter(group=api_group)] = None,
    api_activity: Annotated[bool | None, cyclopts.Parameter(group=api_group)] = None,
    # Device Creation
    product: Annotated[
        list[int] | None, cyclopts.Parameter(negative_iterable="", group=device_group)
    ] = None,
    color: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    color_temperature: Annotated[
        int | None, cyclopts.Parameter(group=device_group)
    ] = None,
    infrared: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    hev: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    multizone: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    tile: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    switch: Annotated[int | None, cyclopts.Parameter(group=device_group)] = None,
    # Multizone Options
    multizone_zones: Annotated[
        int | None, cyclopts.Parameter(group=multizone_group)
    ] = None,
    multizone_extended: Annotated[
        bool | None, cyclopts.Parameter(group=multizone_group)
    ] = None,
    # Tile/Matrix Options
    tile_count: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    tile_width: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    tile_height: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    # Serial Number Options
    serial_prefix: Annotated[str | None, cyclopts.Parameter(group=serial_group)] = None,
    serial_start: Annotated[int | None, cyclopts.Parameter(group=serial_group)] = None,
) -> bool | None:
    """Start the LIFX emulator with configurable devices.

    Creates virtual LIFX devices that respond to the LIFX LAN protocol. Supports
    creating devices by product ID or by device type (color, multizone, tile, etc).
    Settings can be provided via a YAML config file, environment variable, or
    command-line parameters. CLI parameters override config file values.

    Config file resolution order (first match wins):
        1. --config path/to/file.yaml (explicit flag)
        2. LIFX_EMULATOR_CONFIG environment variable
        3. lifx-emulator.yaml or lifx-emulator.yml in current directory

    Args:
        config: Path to YAML config file. If not specified, checks
            LIFX_EMULATOR_CONFIG env var, then auto-detects
            lifx-emulator.yaml or lifx-emulator.yml in current directory.
        bind: IP address to bind to. Default: 127.0.0.1.
        port: UDP port to listen on. Default: 56700.
        verbose: Enable verbose logging showing all packets sent and received.
        persistent: Enable persistent storage of device state across restarts.
        persistent_scenarios: Enable persistent storage of test scenarios.
            Requires --persistent to be enabled.
        api: Enable HTTP API server for monitoring and runtime device management.
        api_host: API server host to bind to. Default: 127.0.0.1.
        api_port: API server port. Default: 8080.
        api_activity: Enable activity logging in API. Disable to reduce traffic
            and save UI space on the monitoring dashboard. Default: true.
        product: Create devices by product ID. Can be specified multiple times.
            Run 'lifx-emulator list-products' to see available products.
        color: Number of full-color RGB lights to emulate.
        color_temperature: Number of color temperature (white spectrum) lights.
        infrared: Number of infrared lights with night vision capability.
        hev: Number of HEV/Clean lights with UV-C germicidal capability.
        multizone: Number of multizone strip or beam devices.
        multizone_zones: Number of zones per multizone device. Uses product
            defaults if not specified.
        multizone_extended: Enable extended multizone support (Beam).
            Set --no-multizone-extended for basic multizone (Z) devices.
            Default: true.
        tile: Number of tile/matrix chain devices.
        switch: Number of LIFX Switch devices (relays, no lighting).
        tile_count: Number of tiles per device. Uses product defaults if not
            specified (5 for Tile, 1 for Candle/Ceiling).
        tile_width: Width of each tile in zones. Uses product defaults if not
            specified (8 for most devices).
        tile_height: Height of each tile in zones. Uses product defaults if
            not specified (8 for most devices).
        serial_prefix: Serial number prefix as 6 hex characters. Default: d073d5.
        serial_start: Starting serial suffix for auto-incrementing device serials.
            Default: 1.

    Examples:
        Start with a config file:
            lifx-emulator --config my-setup.yaml

        Auto-detect config file in current directory:
            lifx-emulator

        Enable HTTP API server for monitoring:
            lifx-emulator --api

        Create specific products by ID (see list-products command):
            lifx-emulator --product 27 --product 32 --product 55

        Start on custom port with verbose logging:
            lifx-emulator --port 56700 --verbose

        Create diverse devices with API:
            lifx-emulator --color 2 --multizone 1 --tile 1 --api --verbose

        Override a config file setting:
            lifx-emulator --config setup.yaml --port 56701

        Enable persistent storage:
            lifx-emulator --persistent --api
    """
    # Load and merge config file with CLI overrides
    cfg = _load_merged_config(
        config_flag=config,
        bind=bind,
        port=port,
        verbose=verbose,
        persistent=persistent,
        persistent_scenarios=persistent_scenarios,
        api=api,
        api_host=api_host,
        api_port=api_port,
        api_activity=api_activity,
        products=product,
        color=color,
        color_temperature=color_temperature,
        infrared=infrared,
        hev=hev,
        multizone=multizone,
        tile=tile,
        switch=switch,
        multizone_zones=multizone_zones,
        multizone_extended=multizone_extended,
        tile_count=tile_count,
        tile_width=tile_width,
        tile_height=tile_height,
        serial_prefix=serial_prefix,
        serial_start=serial_start,
    )
    if cfg is None:
        return False

    # Extract final merged values
    f_bind: str = cfg["bind"]
    f_port: int = cfg["port"]
    f_verbose: bool = cfg["verbose"]
    f_persistent: bool = cfg["persistent"]
    f_persistent_scenarios: bool = cfg["persistent_scenarios"]
    f_api: bool = cfg["api"]
    f_api_host: str = cfg["api_host"]
    f_api_port: int = cfg["api_port"]
    f_api_activity: bool = cfg["api_activity"]
    f_products: list[int] | None = cfg["products"]
    f_color: int = cfg["color"]
    f_color_temperature: int = cfg["color_temperature"]
    f_infrared: int = cfg["infrared"]
    f_hev: int = cfg["hev"]
    f_multizone: int = cfg["multizone"]
    f_tile: int = cfg["tile"]
    f_switch: int = cfg["switch"]
    f_multizone_zones: int | None = cfg["multizone_zones"]
    f_multizone_extended: bool = cfg["multizone_extended"]
    f_tile_count: int | None = cfg["tile_count"]
    f_tile_width: int | None = cfg["tile_width"]
    f_tile_height: int | None = cfg["tile_height"]
    f_serial_prefix: str = cfg["serial_prefix"]
    f_serial_start: int = cfg["serial_start"]
    config_devices: list | None = cfg.get("devices")
    config_scenarios = cfg.get("scenarios")

    logger: logging.Logger = _setup_logging(f_verbose)

    # Log config file source if one was used
    config_path = cfg.get("_config_path")
    if config_path:
        logger.info("Loaded config from %s", config_path)

    # Validate that --persistent-scenarios requires --persistent
    if f_persistent_scenarios and not f_persistent:
        logger.error("--persistent-scenarios requires --persistent")
        return False

    # Deprecation warnings for --persistent / --persistent-scenarios
    if f_persistent:
        warnings.warn(
            "--persistent is deprecated and will be removed in a future "
            "release. Use 'lifx-emulator export-config' to migrate to a "
            "config file.",
            DeprecationWarning,
            stacklevel=1,
        )
        logger.warning(
            "--persistent is deprecated. Use 'lifx-emulator export-config' "
            "to migrate your device state to a config file."
        )
    if f_persistent_scenarios:
        warnings.warn(
            "--persistent-scenarios is deprecated and will be removed in a "
            "future release. Use 'lifx-emulator export-config' to migrate "
            "scenarios to a config file.",
            DeprecationWarning,
            stacklevel=1,
        )
        logger.warning(
            "--persistent-scenarios is deprecated. Use 'lifx-emulator "
            "export-config' to migrate your scenarios to a config file."
        )

    # Initialize storage if persistence is enabled
    storage = DevicePersistenceAsyncFile() if f_persistent else None
    if f_persistent and storage:
        logger.info("Persistent storage enabled at %s", storage.storage_dir)

    # Build device list based on parameters
    devices = []
    serial_num = f_serial_start

    # Collect explicit serials from config device definitions
    explicit_serials: set[str] = set()
    if config_devices:
        for dev_def in config_devices:
            if dev_def.serial:
                explicit_serials.add(dev_def.serial.lower())

    # Helper to generate serials (skipping explicitly assigned ones)
    def get_serial():
        nonlocal serial_num
        while True:
            serial = f"{f_serial_prefix}{serial_num:06x}"
            serial_num += 1
            if serial.lower() not in explicit_serials:
                return serial

    # Check if we should restore devices from persistent storage
    restore_from_storage = False
    has_any_device_config = (
        bool(f_products)
        or f_color > 0
        or f_color_temperature > 0
        or f_infrared > 0
        or f_hev > 0
        or f_multizone > 0
        or f_tile > 0
        or f_switch > 0
        or (config_devices is not None and len(config_devices) > 0)
    )

    if f_persistent and storage:
        saved_serials = storage.list_devices()

        if saved_serials and not has_any_device_config:
            restore_from_storage = True
            logger.info(
                f"Restoring {len(saved_serials)} device(s) from persistent storage"
            )
            for saved_serial in saved_serials:
                saved_state = storage.load_device_state(saved_serial)
                if saved_state:
                    try:
                        device = create_device(
                            saved_state["product"], serial=saved_serial, storage=storage
                        )
                        devices.append(device)
                    except Exception as e:
                        logger.error("Failed to restore device %s: %s", saved_serial, e)
        elif not saved_serials and not has_any_device_config:
            logger.info(
                "Persistent storage enabled but empty. Starting with no devices."
            )
            logger.info(
                "Use API or restart with device flags "
                "(--color, --product, etc.) to add devices."
            )

    # Create new devices if not restoring from storage
    if not restore_from_storage:
        # Create devices from product IDs if specified
        if f_products:
            for pid in f_products:
                try:
                    devices.append(
                        create_device(pid, serial=get_serial(), storage=storage)
                    )
                except ValueError as e:
                    logger.error("Failed to create device: %s", e)
                    logger.info(
                        "Run 'lifx-emulator list-products' to see available products"
                    )
                    return

        # Create color lights
        for _ in range(f_color):
            devices.append(create_color_light(get_serial(), storage=storage))

        # Create color temperature lights
        for _ in range(f_color_temperature):
            devices.append(
                create_color_temperature_light(get_serial(), storage=storage)
            )

        # Create infrared lights
        for _ in range(f_infrared):
            devices.append(create_infrared_light(get_serial(), storage=storage))

        # Create HEV lights
        for _ in range(f_hev):
            devices.append(create_hev_light(get_serial(), storage=storage))

        # Create multizone devices (strips/beams)
        for _ in range(f_multizone):
            devices.append(
                create_multizone_light(
                    get_serial(),
                    zone_count=f_multizone_zones,
                    extended_multizone=f_multizone_extended,
                    storage=storage,
                )
            )

        # Create tile devices
        for _ in range(f_tile):
            devices.append(
                create_tile_device(
                    get_serial(),
                    tile_count=f_tile_count,
                    tile_width=f_tile_width,
                    tile_height=f_tile_height,
                    storage=storage,
                )
            )

        # Create switch devices
        for _ in range(f_switch):
            devices.append(create_switch(get_serial(), storage=storage))

        # Create devices from per-device definitions in config
        if config_devices:
            # Namespace for deterministic location/group UUIDs
            ns = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            location_ids: dict[str, bytes] = {}
            group_ids: dict[str, bytes] = {}

            for dev_def in config_devices:
                try:
                    serial = dev_def.serial or get_serial()
                    device = create_device(
                        dev_def.product_id,
                        serial=serial,
                        zone_count=dev_def.zone_count,
                        tile_count=dev_def.tile_count,
                        tile_width=dev_def.tile_width,
                        tile_height=dev_def.tile_height,
                        storage=storage,
                    )
                    if dev_def.label:
                        device.state.label = dev_def.label
                    if dev_def.power_level is not None:
                        device.state.power_level = dev_def.power_level
                    if dev_def.color is not None:
                        device.state.color = LightHsbk(
                            hue=dev_def.color.hue,
                            saturation=dev_def.color.saturation,
                            brightness=dev_def.color.brightness,
                            kelvin=dev_def.color.kelvin,
                        )
                    if dev_def.location is not None:
                        loc = dev_def.location
                        if loc not in location_ids:
                            location_ids[loc] = uuid.uuid5(ns, loc).bytes
                        device.state.location_id = location_ids[loc]
                        device.state.location_label = loc
                    if dev_def.group is not None:
                        grp = dev_def.group
                        if grp not in group_ids:
                            group_ids[grp] = uuid.uuid5(ns, grp).bytes
                        device.state.group_id = group_ids[grp]
                        device.state.group_label = grp
                    if dev_def.zone_colors is not None:
                        device.state.zone_colors = [
                            LightHsbk(
                                hue=zc.hue,
                                saturation=zc.saturation,
                                brightness=zc.brightness,
                                kelvin=zc.kelvin,
                            )
                            for zc in dev_def.zone_colors
                        ]
                    if dev_def.infrared_brightness is not None:
                        device.state.infrared_brightness = dev_def.infrared_brightness
                    if dev_def.hev_cycle_duration is not None:
                        device.state.hev_cycle_duration_s = dev_def.hev_cycle_duration
                    if dev_def.hev_indication is not None:
                        device.state.hev_indication = dev_def.hev_indication
                    devices.append(device)
                except ValueError as e:
                    logger.error("Failed to create device from config: %s", e)
                    logger.info(
                        "Run 'lifx-emulator list-products' to see available products"
                    )
                    return

    if not devices:
        if f_persistent:
            logger.warning("No devices configured. Server will run with no devices.")
            logger.info("Use API (--api) or restart with device flags to add devices.")
        else:
            logger.error(
                "No devices configured. Use --color, --multizone, --tile, --switch, "
                "--product, or a config file to add devices."
            )
            return

    # Set port for all devices
    for device in devices:
        device.state.port = f_port

    # Log device information
    logger.info("Starting LIFX Emulator on %s:%s", f_bind, f_port)
    logger.info("Created %s emulated device(s):", len(devices))
    for device in devices:
        label = device.state.label
        serial = device.state.serial
        caps = _format_capabilities(device)
        logger.info("  • %s (%s) - %s", label, serial, caps)

    # Create device manager with repository
    device_repository = DeviceRepository()
    device_manager = DeviceManager(device_repository)

    # Load scenarios from storage or config
    scenario_manager = None
    scenario_storage = None
    if f_persistent_scenarios:
        scenario_storage = ScenarioPersistenceAsyncFile()
        scenario_manager = await scenario_storage.load()
        logger.info("Loaded scenarios from persistent storage")

    # Apply scenarios from config file (only if not using persistent scenarios)
    if config_scenarios and not f_persistent_scenarios:
        scenario_manager = _apply_config_scenarios(config_scenarios, logger)

    # Start LIFX server
    server = EmulatedLifxServer(
        devices,
        device_manager,
        f_bind,
        f_port,
        track_activity=f_api_activity if f_api else False,
        storage=storage,
        scenario_manager=scenario_manager,
        persist_scenarios=f_persistent_scenarios,
        scenario_storage=scenario_storage,
    )
    await server.start()

    # Start API server if enabled
    api_task = None
    if f_api:
        from lifx_emulator_app.api import run_api_server

        logger.info("Starting HTTP API server on http://%s:%s", f_api_host, f_api_port)
        api_task = asyncio.create_task(run_api_server(server, f_api_host, f_api_port))

    # Set up graceful shutdown on signals
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully (thread-safe for asyncio)."""
        loop.call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    sigbreak = getattr(signal, "SIGBREAK", None)
    if sigbreak is not None:
        signal.signal(sigbreak, signal_handler)

    try:
        if f_api:
            logger.info(
                f"LIFX server running on {f_bind}:{f_port}, "
                f"API server on http://{f_api_host}:{f_api_port}"
            )
            logger.info(
                f"Open http://{f_api_host}:{f_api_port} in your browser "
                "to view the monitoring dashboard"
            )
        elif f_verbose:
            logger.info(
                "Server running with verbose packet logging... Press Ctrl+C to stop"
            )
        else:
            logger.info(
                "Server running... Press Ctrl+C to stop (use --verbose to see packets)"
            )

        await shutdown_event.wait()
    finally:
        logger.info("Shutting down server...")

        if storage:
            await storage.shutdown()

        await server.stop()
        if api_task:
            api_task.cancel()
            try:
                await api_task
            except asyncio.CancelledError:
                pass


def main():
    """Entry point for the CLI."""
    app()
