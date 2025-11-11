"""CLI entry point for lifx-emulator."""

import asyncio
import logging
import signal
from typing import Annotated

import cyclopts
from rich.logging import RichHandler

from lifx_emulator.constants import LIFX_UDP_PORT
from lifx_emulator.devices import (
    DEFAULT_STORAGE_DIR,
    DeviceManager,
    DevicePersistenceAsyncFile,
)
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_device,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.products.registry import get_registry
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios import ScenarioPersistenceAsyncFile
from lifx_emulator.server import EmulatedLifxServer

app = cyclopts.App(
    name="lifx-emulator",
    help="LIFX LAN Protocol Emulator provides virtual LIFX devices for testing",
)
app.register_install_completion_command()

# Parameter groups for organizing help output
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
    from pathlib import Path

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


@app.default
async def run(
    *,
    # Server Options
    bind: Annotated[str, cyclopts.Parameter(group=server_group)] = "127.0.0.1",
    port: Annotated[int, cyclopts.Parameter(group=server_group)] = LIFX_UDP_PORT,
    verbose: Annotated[
        bool, cyclopts.Parameter(negative="", group=server_group)
    ] = False,
    # Storage & Persistence
    persistent: Annotated[
        bool, cyclopts.Parameter(negative="", group=storage_group)
    ] = False,
    persistent_scenarios: Annotated[
        bool, cyclopts.Parameter(negative="", group=storage_group)
    ] = False,
    # HTTP API Server
    api: Annotated[bool, cyclopts.Parameter(negative="", group=api_group)] = False,
    api_host: Annotated[str, cyclopts.Parameter(group=api_group)] = "127.0.0.1",
    api_port: Annotated[int, cyclopts.Parameter(group=api_group)] = 8080,
    api_activity: Annotated[bool, cyclopts.Parameter(group=api_group)] = True,
    # Device Creation
    product: Annotated[
        list[int] | None, cyclopts.Parameter(negative_iterable="", group=device_group)
    ] = None,
    color: Annotated[int, cyclopts.Parameter(group=device_group)] = 1,
    color_temperature: Annotated[int, cyclopts.Parameter(group=device_group)] = 0,
    infrared: Annotated[int, cyclopts.Parameter(group=device_group)] = 0,
    hev: Annotated[int, cyclopts.Parameter(group=device_group)] = 0,
    multizone: Annotated[int, cyclopts.Parameter(group=device_group)] = 0,
    tile: Annotated[int, cyclopts.Parameter(group=device_group)] = 0,
    # Multizone Options
    multizone_zones: Annotated[
        int | None, cyclopts.Parameter(group=multizone_group)
    ] = None,
    multizone_extended: Annotated[
        bool, cyclopts.Parameter(group=multizone_group)
    ] = True,
    # Tile/Matrix Options
    tile_count: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    tile_width: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    tile_height: Annotated[int | None, cyclopts.Parameter(group=tile_group)] = None,
    # Serial Number Options
    serial_prefix: Annotated[str, cyclopts.Parameter(group=serial_group)] = "d073d5",
    serial_start: Annotated[int, cyclopts.Parameter(group=serial_group)] = 1,
) -> bool | None:
    """Start the LIFX emulator with configurable devices.

    Creates virtual LIFX devices that respond to the LIFX LAN protocol. Supports
    creating devices by product ID or by device type (color, multizone, tile, etc).
    State can optionally be persisted across restarts.

    Args:
        bind: IP address to bind to.
        port: UDP port to listen on.
        verbose: Enable verbose logging showing all packets sent and received.
        persistent: Enable persistent storage of device state across restarts.
        persistent_scenarios: Enable persistent storage of test scenarios.
            Requires --persistent to be enabled.
        api: Enable HTTP API server for monitoring and runtime device management.
        api_host: API server host to bind to.
        api_port: API server port.
        api_activity: Enable activity logging in API. Disable to reduce traffic
            and save UI space on the monitoring dashboard.
        product: Create devices by product ID. Can be specified multiple times.
            Run 'lifx-emulator list-products' to see available products.
        color: Number of full-color RGB lights to emulate. Defaults to 1.
        color_temperature: Number of color temperature (white spectrum) lights.
        infrared: Number of infrared lights with night vision capability.
        hev: Number of HEV/Clean lights with UV-C germicidal capability.
        multizone: Number of multizone strip or beam devices.
        multizone_zones: Number of zones per multizone device. Uses product
            defaults if not specified.
        multizone_extended: Enable extended multizone support (Beam).
            Set --no-multizone-extended for basic multizone (Z) devices.
        tile: Number of tile/matrix chain devices.
        tile_count: Number of tiles per device. Uses product defaults if not
            specified (5 for Tile, 1 for Candle/Ceiling).
        tile_width: Width of each tile in pixels. Uses product defaults if not
            specified (8 for most devices).
        tile_height: Height of each tile in pixels. Uses product defaults if
            not specified (8 for most devices).
        serial_prefix: Serial number prefix as 6 hex characters.
        serial_start: Starting serial suffix for auto-incrementing device serials.

    Examples:
        Start with default configuration (1 color light):
            lifx-emulator

        Enable HTTP API server for monitoring:
            lifx-emulator --api

        Create specific products by ID (see list-products command):
            lifx-emulator --product 27 --product 32 --product 55

        Start on custom port with verbose logging:
            lifx-emulator --port 56700 --verbose

        Create diverse devices with API:
            lifx-emulator --color 2 --multizone 1 --tile 1 --api --verbose

        Create only specific device types:
            lifx-emulator --color 0 --infrared 3 --hev 2

        Custom serial prefix:
            lifx-emulator --serial-prefix cafe00 --color 5

        Mix products and device types:
            lifx-emulator --product 27 --color 2 --multizone 1

        Enable persistent storage:
            lifx-emulator --persistent --api
    """
    logger: logging.Logger = _setup_logging(verbose)

    # Validate that --persistent-scenarios requires --persistent
    if persistent_scenarios and not persistent:
        logger.error("--persistent-scenarios requires --persistent")
        return False

    # Initialize storage if persistence is enabled
    storage = DevicePersistenceAsyncFile() if persistent else None
    if persistent and storage:
        logger.info("Persistent storage enabled at %s", storage.storage_dir)

    # Build device list based on parameters
    devices = []
    serial_num = serial_start

    # Helper to generate serials
    def get_serial():
        nonlocal serial_num
        serial = f"{serial_prefix}{serial_num:06x}"
        serial_num += 1
        return serial

    # Check if we should restore devices from persistent storage
    # When persistent is enabled, we only create new devices if explicitly requested
    restore_from_storage = False
    if persistent and storage:
        saved_serials = storage.list_devices()
        # Check if user explicitly requested device creation
        user_requested_devices = (
            product is not None
            or color != 1  # color has default value of 1
            or color_temperature != 0
            or infrared != 0
            or hev != 0
            or multizone != 0
            or tile != 0
        )

        if saved_serials and not user_requested_devices:
            # Restore saved devices
            restore_from_storage = True
            logger.info(
                f"Restoring {len(saved_serials)} device(s) from persistent storage"
            )
            for saved_serial in saved_serials:
                saved_state = storage.load_device_state(saved_serial)
                if saved_state:
                    try:
                        # Create device with the saved serial and product ID
                        device = create_device(
                            saved_state["product"], serial=saved_serial, storage=storage
                        )
                        devices.append(device)
                    except Exception as e:
                        logger.error("Failed to restore device %s: %s", saved_serial, e)
        elif not saved_serials and not user_requested_devices:
            # Persistent storage is empty and no devices requested
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
        if product:
            for pid in product:
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
            # If using --product, don't create default devices
            # Set color to 0 by default
            if (
                color == 1
                and color_temperature == 0
                and infrared == 0
                and hev == 0
                and multizone == 0
            ):
                color = 0

        # When persistent is enabled, don't create default devices
        # User must explicitly request devices
        if (
            persistent
            and color == 1
            and color_temperature == 0
            and infrared == 0
            and hev == 0
            and multizone == 0
            and tile == 0
        ):
            color = 0

        # Create color lights
        for _ in range(color):
            devices.append(create_color_light(get_serial(), storage=storage))

        # Create color temperature lights
        for _ in range(color_temperature):
            devices.append(
                create_color_temperature_light(get_serial(), storage=storage)
            )

        # Create infrared lights
        for _ in range(infrared):
            devices.append(create_infrared_light(get_serial(), storage=storage))

        # Create HEV lights
        for _ in range(hev):
            devices.append(create_hev_light(get_serial(), storage=storage))

        # Create multizone devices (strips/beams)
        for _ in range(multizone):
            devices.append(
                create_multizone_light(
                    get_serial(),
                    zone_count=multizone_zones,
                    extended_multizone=multizone_extended,
                    storage=storage,
                )
            )

        # Create tile devices
        for _ in range(tile):
            devices.append(
                create_tile_device(
                    get_serial(),
                    tile_count=tile_count,
                    tile_width=tile_width,
                    tile_height=tile_height,
                    storage=storage,
                )
            )

    if not devices:
        if persistent:
            logger.warning("No devices configured. Server will run with no devices.")
            logger.info("Use API (--api) or restart with device flags to add devices.")
        else:
            logger.error(
                "No devices configured. Use --color, --multizone, --tile, "
                "etc. to add devices."
            )
            return

    # Set port for all devices
    for device in devices:
        device.state.port = port

    # Log device information
    logger.info("Starting LIFX Emulator on %s:%s", bind, port)
    logger.info("Created %s emulated device(s):", len(devices))
    for device in devices:
        label = device.state.label
        serial = device.state.serial
        caps = _format_capabilities(device)
        logger.info("  • %s (%s) - %s", label, serial, caps)

    # Create device manager with repository
    device_repository = DeviceRepository()
    device_manager = DeviceManager(device_repository)

    # Load scenarios from storage if persistence is enabled
    scenario_manager = None
    scenario_storage = None
    if persistent_scenarios:
        scenario_storage = ScenarioPersistenceAsyncFile()
        scenario_manager = await scenario_storage.load()
        logger.info("Loaded scenarios from persistent storage")

    # Start LIFX server
    server = EmulatedLifxServer(
        devices,
        device_manager,
        bind,
        port,
        track_activity=api_activity if api else False,
        storage=storage,
        scenario_manager=scenario_manager,
        persist_scenarios=persistent_scenarios,
        scenario_storage=scenario_storage,
    )
    await server.start()

    # Start API server if enabled
    api_task = None
    if api:
        from lifx_emulator.api import run_api_server

        logger.info("Starting HTTP API server on http://%s:%s", api_host, api_port)
        api_task = asyncio.create_task(run_api_server(server, api_host, api_port))

    # Set up graceful shutdown on signals
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully (thread-safe for asyncio)."""
        # Use call_soon_threadsafe to safely set event from signal handler
        loop.call_soon_threadsafe(shutdown_event.set)

    # Register signal handlers for graceful shutdown
    # Use signal.signal() instead of loop.add_signal_handler() for Windows compatibility
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # On Windows, also handle SIGBREAK
    sigbreak = getattr(signal, "SIGBREAK", None)
    if sigbreak is not None:
        signal.signal(sigbreak, signal_handler)

    try:
        if api:
            logger.info(
                f"LIFX server running on {bind}:{port}, API server on http://{api_host}:{api_port}"
            )
            logger.info(
                f"Open http://{api_host}:{api_port} in your browser "
                "to view the monitoring dashboard"
            )
        elif verbose:
            logger.info(
                "Server running with verbose packet logging... Press Ctrl+C to stop"
            )
        else:
            logger.info(
                "Server running... Press Ctrl+C to stop (use --verbose to see packets)"
            )

        await shutdown_event.wait()  # Wait for shutdown signal
    finally:
        logger.info("Shutting down server...")

        # Shutdown storage first to flush pending writes
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
