"""Device builder with fluent API for creating emulated LIFX devices."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from lifx_emulator.devices import DeviceState, EmulatedLifxDevice
from lifx_emulator.devices.state_restorer import StateRestorer
from lifx_emulator.devices.states import (
    CoreDeviceState,
    GroupState,
    HevState,
    InfraredState,
    LocationState,
    MatrixState,
    MultiZoneState,
    NetworkState,
    WaveformState,
)
from lifx_emulator.factories.default_config import DefaultColorConfig
from lifx_emulator.factories.firmware_config import FirmwareConfig
from lifx_emulator.factories.serial_generator import SerialGenerator
from lifx_emulator.products.specs import (
    get_default_tile_count,
    get_default_zone_count,
    get_tile_dimensions,
)
from lifx_emulator.protocol.protocol_types import LightHsbk

if TYPE_CHECKING:
    from lifx_emulator.devices import DevicePersistenceAsyncFile
    from lifx_emulator.products.registry import ProductInfo
    from lifx_emulator.scenarios import HierarchicalScenarioManager


class DeviceBuilder:
    """Fluent API builder for creating emulated LIFX devices.

    This builder separates device construction into discrete, testable steps:
    1. Product configuration (serial, firmware, color)
    2. Capability-specific configuration (zones, tiles)
    3. State composition
    4. Device creation

    Examples:
        >>> from lifx_emulator.products.registry import get_product
        >>> product = get_product(27)  # LIFX A19
        >>> builder = DeviceBuilder(product)
        >>> device = builder.with_serial("d073d5000001").build()

        >>> # Multizone device with custom zones
        >>> product = get_product(32)  # LIFX Z
        >>> device = (
        ...     DeviceBuilder(product)
        ...     .with_zone_count(24)
        ...     .with_extended_multizone(False)
        ...     .build()
        ... )
    """

    def __init__(self, product_info: ProductInfo):
        """Initialize builder with product information.

        Args:
            product_info: Product information from registry
        """
        self._product_info = product_info

        # Configuration state
        self._serial: str | None = None
        self._zone_count: int | None = None
        self._extended_multizone: bool | None = None
        self._tile_count: int | None = None
        self._tile_width: int | None = None
        self._tile_height: int | None = None
        self._firmware_version: tuple[int, int] | None = None
        self._storage: DevicePersistenceAsyncFile | None = None
        self._scenario_manager: HierarchicalScenarioManager | None = None
        self._color: LightHsbk | None = None

        # Helper services
        self._serial_generator = SerialGenerator()
        self._color_config = DefaultColorConfig()
        self._firmware_config = FirmwareConfig()

    def with_serial(self, serial: str) -> DeviceBuilder:
        """Set device serial number.

        Args:
            serial: 12-character hex serial number

        Returns:
            Self for method chaining
        """
        self._serial = serial
        return self

    def with_zone_count(self, zone_count: int) -> DeviceBuilder:
        """Set zone count for multizone devices.

        Args:
            zone_count: Number of zones

        Returns:
            Self for method chaining
        """
        self._zone_count = zone_count
        return self

    def with_extended_multizone(self, extended: bool) -> DeviceBuilder:
        """Enable/disable extended multizone support.

        Args:
            extended: Whether to enable extended multizone

        Returns:
            Self for method chaining
        """
        self._extended_multizone = extended
        return self

    def with_tile_count(self, tile_count: int) -> DeviceBuilder:
        """Set tile count for matrix devices.

        Args:
            tile_count: Number of tiles

        Returns:
            Self for method chaining
        """
        self._tile_count = tile_count
        return self

    def with_tile_dimensions(self, width: int, height: int) -> DeviceBuilder:
        """Set tile dimensions for matrix devices.

        Args:
            width: Tile width in pixels
            height: Tile height in pixels

        Returns:
            Self for method chaining
        """
        self._tile_width = width
        self._tile_height = height
        return self

    def with_firmware_version(self, major: int, minor: int) -> DeviceBuilder:
        """Set firmware version.

        Args:
            major: Major version number
            minor: Minor version number

        Returns:
            Self for method chaining
        """
        self._firmware_version = (major, minor)
        return self

    def with_storage(self, storage: DevicePersistenceAsyncFile) -> DeviceBuilder:
        """Enable persistent storage.

        Args:
            storage: Async storage backend

        Returns:
            Self for method chaining
        """
        self._storage = storage
        return self

    def with_scenario_manager(
        self, scenario_manager: HierarchicalScenarioManager
    ) -> DeviceBuilder:
        """Set scenario manager for testing.

        Args:
            scenario_manager: Scenario manager instance

        Returns:
            Self for method chaining
        """
        self._scenario_manager = scenario_manager
        return self

    def with_color(self, color: LightHsbk) -> DeviceBuilder:
        """Set initial device color.

        Args:
            color: Initial color

        Returns:
            Self for method chaining
        """
        self._color = color
        return self

    def build(self) -> EmulatedLifxDevice:
        """Build the emulated device.

        Returns:
            Configured EmulatedLifxDevice instance
        """
        # 1. Generate/validate serial
        serial = self._serial or self._serial_generator.generate(self._product_info)

        # 2. Apply product-specific defaults
        self._apply_product_defaults()

        # 3. Determine firmware version
        version_major, version_minor = self._firmware_config.get_firmware_version(
            extended_multizone=self._extended_multizone, override=self._firmware_version
        )

        # 4. Get default color
        color = self._color or self._color_config.get_default_color(self._product_info)

        # 5. Create core state
        core = self._create_core_state(serial, color, version_major, version_minor)

        # 6. Create basic states
        network = NetworkState()
        location = LocationState()
        group = GroupState()
        waveform = WaveformState()

        # 7. Create capability-specific states
        infrared_state = self._create_infrared_state()
        hev_state = self._create_hev_state()
        multizone_state = self._create_multizone_state()
        matrix_state = self._create_matrix_state()

        # 8. Determine extended multizone support
        firmware_version_int = (version_major << 16) | version_minor
        has_extended_multizone = self._product_info.supports_extended_multizone(
            firmware_version_int
        )

        # 9. Compose device state
        state = DeviceState(
            core=core,
            network=network,
            location=location,
            group=group,
            waveform=waveform,
            infrared=infrared_state,
            hev=hev_state,
            multizone=multizone_state,
            matrix=matrix_state,
            has_color=self._product_info.has_color,
            has_infrared=self._product_info.has_infrared,
            has_multizone=self._product_info.has_multizone,
            has_extended_multizone=has_extended_multizone,
            has_matrix=self._product_info.has_matrix,
            has_hev=self._product_info.has_hev,
        )

        # 10. Restore saved state if persistence enabled
        if self._storage:
            restorer = StateRestorer(self._storage)
            restorer.restore_if_available(state)

        # 11. Create device
        return EmulatedLifxDevice(
            state, storage=self._storage, scenario_manager=self._scenario_manager
        )

    def _apply_product_defaults(self):
        """Apply product-specific defaults from specs."""
        # Zone count for multizone devices
        if self._product_info.has_multizone and self._zone_count is None:
            self._zone_count = get_default_zone_count(self._product_info.pid) or 16

        # Tile configuration for matrix devices
        if self._product_info.has_matrix:
            # Get tile dimensions from specs (always use specs for dimensions)
            tile_dims = get_tile_dimensions(self._product_info.pid)
            if tile_dims:
                self._tile_width, self._tile_height = tile_dims
            else:
                # Fallback to standard 8x8 tiles
                if self._tile_width is None:
                    self._tile_width = 8
                if self._tile_height is None:
                    self._tile_height = 8

            # Get default tile count from specs
            if self._tile_count is None:
                specs_tile_count = get_default_tile_count(self._product_info.pid)
                self._tile_count = (
                    specs_tile_count if specs_tile_count is not None else 5
                )

    def _create_core_state(
        self, serial: str, color: LightHsbk, version_major: int, version_minor: int
    ) -> CoreDeviceState:
        """Create core device state.

        Args:
            serial: Device serial number
            color: Initial color
            version_major: Firmware major version
            version_minor: Firmware minor version

        Returns:
            CoreDeviceState instance
        """
        label = f"{self._product_info.name} {serial[-6:]}"

        return CoreDeviceState(
            serial=serial,
            label=label,
            power_level=65535,  # Default to on
            color=color,
            vendor=self._product_info.vendor,
            product=self._product_info.pid,
            version_major=version_major,
            version_minor=version_minor,
            build_timestamp=int(time.time()),
            mac_address=bytes.fromhex(serial[:12]),
        )

    def _create_infrared_state(self) -> InfraredState | None:
        """Create infrared state if product has infrared capability.

        Returns:
            InfraredState instance or None
        """
        if self._product_info.has_infrared:
            return InfraredState(infrared_brightness=16384)
        return None

    def _create_hev_state(self) -> HevState | None:
        """Create HEV state if product has HEV capability.

        Returns:
            HevState instance or None
        """
        if self._product_info.has_hev:
            return HevState()
        return None

    def _create_multizone_state(self) -> MultiZoneState | None:
        """Create multizone state if product has multizone capability.

        Returns:
            MultiZoneState instance or None
        """
        if self._product_info.has_multizone and self._zone_count:
            return MultiZoneState(
                zone_count=self._zone_count,
                zone_colors=[],  # Will be initialized by EmulatedLifxDevice
            )
        return None

    def _create_matrix_state(self) -> MatrixState | None:
        """Create matrix state if product has matrix capability.

        Returns:
            MatrixState instance or None
        """
        if self._product_info.has_matrix and self._tile_count:
            return MatrixState(
                tile_count=self._tile_count,
                tile_devices=[],  # Will be initialized by EmulatedLifxDevice
                tile_width=self._tile_width or 8,
                tile_height=self._tile_height or 8,
            )
        return None
