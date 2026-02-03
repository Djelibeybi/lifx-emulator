"""Tests for CLI functionality."""

import asyncio
import logging
import uuid
import warnings
from unittest.mock import MagicMock, patch

import pytest
from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.products.registry import ProductInfo, TemperatureRange
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator_app.__main__ import (
    _apply_config_scenarios,
    _format_capabilities,
    _load_merged_config,
    _scenario_def_to_core,
    _setup_logging,
    list_products,
    run,
)
from lifx_emulator_app.config import (
    HsbkConfig,
    ScenarioDefinition,
    ScenariosConfig,
)


class TestSetupLogging:
    """Test logging configuration."""

    @patch("lifx_emulator_app.__main__.logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test that verbose logging is configured correctly."""
        _setup_logging(True)
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == 10  # logging.DEBUG

    @patch("lifx_emulator_app.__main__.logging.basicConfig")
    def test_setup_logging_not_verbose(self, mock_basic_config):
        """Test that non-verbose logging is configured correctly."""
        _setup_logging(False)
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == 20  # logging.INFO


class TestFormatCapabilities:
    """Test device capability formatting."""

    def test_format_color_device(self):
        """Test formatting capabilities for a color device."""
        device = create_color_light("d073d5000001")
        caps = _format_capabilities(device)
        assert "color" in caps
        assert "infrared" not in caps
        assert "multizone" not in caps

    def test_format_white_only_device(self):
        """Test formatting capabilities for white-only device."""
        # Create device with color disabled
        device = create_color_light("d073d5000001")
        device.state.has_color = False
        caps = _format_capabilities(device)
        assert "white-only" in caps
        assert "color" not in caps

    def test_format_infrared_device(self):
        """Test formatting capabilities for infrared device."""
        from lifx_emulator.factories import create_infrared_light

        device = create_infrared_light("d073d5000001")
        caps = _format_capabilities(device)
        assert "infrared" in caps

    def test_format_hev_device(self):
        """Test formatting capabilities for HEV device."""
        from lifx_emulator.factories import create_hev_light

        device = create_hev_light("d073d5000001")
        caps = _format_capabilities(device)
        assert "HEV" in caps

    def test_format_multizone_device(self):
        """Test formatting capabilities for multizone device."""
        device = create_multizone_light("d073d5000001", zone_count=16)
        caps = _format_capabilities(device)
        assert "multizone(16)" in caps

    def test_format_extended_multizone_device(self):
        """Test formatting capabilities for extended multizone device."""
        device = create_multizone_light(
            "d073d5000001", zone_count=80, extended_multizone=True
        )
        caps = _format_capabilities(device)
        assert "extended-multizone(80)" in caps

    def test_format_tile_device(self):
        """Test formatting capabilities for tile device."""
        device = create_tile_device("d073d5000001", tile_count=5)
        caps = _format_capabilities(device)
        assert "tile(5)" in caps

    def test_format_large_tile_device(self):
        """Test formatting capabilities for large tile device (>64 zones)."""
        # Large tiles have 16x8 = 128 zones, which is > 64
        device = create_tile_device(
            "d073d5000001", tile_count=1, tile_width=16, tile_height=8
        )
        caps = _format_capabilities(device)
        # For large tiles with more than 64 zones, the format includes dimensions
        assert "tile" in caps
        assert "16x8" in caps or "1" in caps  # Either shows dimensions or count


class TestFormatProductCapabilities:
    """Test product capability formatting."""

    def test_format_switch_product(self):
        """Test formatting for switch products."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=89,
            name="LIFX Switch",
            vendor=1,
            capabilities=ProductCapability.RELAYS | ProductCapability.BUTTONS,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        # Switches show individual capabilities (buttons, relays)
        assert "buttons" in caps
        assert "relays" in caps

    def test_format_full_color_product(self):
        """Test formatting for full color products."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=27,
            name="LIFX A19",
            vendor=1,
            capabilities=ProductCapability.COLOR,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "color" in caps

    def test_format_color_temperature_product(self):
        """Test formatting for color temperature products."""
        product = ProductInfo(
            pid=50,
            name="LIFX Mini White to Warm",
            vendor=1,
            capabilities=0,
            temperature_range=TemperatureRange(min=2700, max=6500),
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "color temperature" in caps

    def test_format_brightness_only_product_fixed_temp(self):
        """Test formatting for brightness-only products with fixed temperature."""
        product = ProductInfo(
            pid=10,
            name="LIFX White 800 (Low Voltage)",
            vendor=1,
            capabilities=0,
            temperature_range=TemperatureRange(min=2700, max=2700),
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "brightness only" in caps

    def test_format_brightness_only_product_no_temp(self):
        """Test formatting for brightness-only products without temperature info."""
        product = ProductInfo(
            pid=99,
            name="Generic White",
            vendor=1,
            capabilities=0,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "brightness only" in caps

    def test_format_product_with_infrared(self):
        """Test formatting for products with infrared."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=29,
            name="LIFX+ A19",
            vendor=1,
            capabilities=ProductCapability.COLOR | ProductCapability.INFRARED,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "infrared" in caps

    def test_format_product_with_multizone(self):
        """Test formatting for products with multizone."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=32,
            name="LIFX Z",
            vendor=1,
            capabilities=ProductCapability.COLOR | ProductCapability.MULTIZONE,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "multizone" in caps

    def test_format_product_with_extended_multizone(self):
        """Test formatting for products with extended multizone."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=38,
            name="LIFX Beam",
            vendor=1,
            capabilities=ProductCapability.COLOR
            | ProductCapability.MULTIZONE
            | ProductCapability.EXTENDED_MULTIZONE,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "extended-multizone" in caps

    def test_format_product_with_matrix(self):
        """Test formatting for products with matrix."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=55,
            name="LIFX Tile",
            vendor=1,
            capabilities=ProductCapability.COLOR | ProductCapability.MATRIX,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "matrix" in caps

    def test_format_product_with_hev(self):
        """Test formatting for products with HEV."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=90,
            name="LIFX Clean",
            vendor=1,
            capabilities=ProductCapability.COLOR | ProductCapability.HEV,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "HEV" in caps

    def test_format_product_with_chain(self):
        """Test formatting for products with chain capability."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=55,
            name="LIFX Tile",
            vendor=1,
            capabilities=ProductCapability.COLOR
            | ProductCapability.MATRIX
            | ProductCapability.CHAIN,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "chain" in caps

    def test_format_product_with_buttons_not_switch(self):
        """Test formatting for products with buttons that aren't switches."""
        from lifx_emulator.products.registry import ProductCapability

        product = ProductInfo(
            pid=70,
            name="LIFX Downlight",
            vendor=1,
            capabilities=ProductCapability.COLOR | ProductCapability.BUTTONS,
            temperature_range=None,
            min_ext_mz_firmware=None,
        )
        caps = product.caps
        assert "buttons" in caps


class TestListProducts:
    """Test list-products command."""

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_no_filter(self, mock_get_registry, mock_print):
        """Test listing all products."""
        from lifx_emulator.products.registry import ProductCapability

        # Mock registry with a few products
        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            32: ProductInfo(
                pid=32,
                name="LIFX Z",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.MULTIZONE,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            55: ProductInfo(
                pid=55,
                name="LIFX Tile",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.MATRIX,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type=None)

        # Verify print was called multiple times
        assert mock_print.call_count > 0
        # Check that product info was printed
        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX A19" in output
        assert "LIFX Z" in output
        assert "LIFX Tile" in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_filter_multizone(self, mock_get_registry, mock_print):
        """Test listing products filtered by multizone."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            32: ProductInfo(
                pid=32,
                name="LIFX Z",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.MULTIZONE,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="multizone")

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX Z" in output
        assert "LIFX A19" not in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_filter_color(self, mock_get_registry, mock_print):
        """Test listing products filtered by color."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            50: ProductInfo(
                pid=50,
                name="LIFX Mini White",
                vendor=1,
                capabilities=0,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="color")

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX A19" in output
        assert "LIFX Mini White" not in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_filter_matrix(self, mock_get_registry, mock_print):
        """Test listing products filtered by matrix."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            55: ProductInfo(
                pid=55,
                name="LIFX Tile",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.MATRIX,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="matrix")

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX Tile" in output
        assert "LIFX A19" not in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_filter_hev(self, mock_get_registry, mock_print):
        """Test listing products filtered by HEV."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            90: ProductInfo(
                pid=90,
                name="LIFX Clean",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.HEV,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="hev")

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX Clean" in output
        assert "LIFX A19" not in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_filter_infrared(self, mock_get_registry, mock_print):
        """Test listing products filtered by infrared."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
            29: ProductInfo(
                pid=29,
                name="LIFX+ A19",
                vendor=1,
                capabilities=ProductCapability.COLOR | ProductCapability.INFRARED,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="infrared")

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "LIFX+ A19" in output
        assert "LIFX A19" not in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_no_results(self, mock_get_registry, mock_print):
        """Test listing products with filter that matches nothing."""
        from lifx_emulator.products.registry import ProductCapability

        mock_registry = MagicMock()
        mock_registry._products = {
            27: ProductInfo(
                pid=27,
                name="LIFX A19",
                vendor=1,
                capabilities=ProductCapability.COLOR,
                temperature_range=None,
                min_ext_mz_firmware=None,
            ),
        }
        mock_get_registry.return_value = mock_registry

        list_products(filter_type="hev")

        # Verify "no products found" message
        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "No products found" in output

    @patch("builtins.print")
    @patch("lifx_emulator_app.__main__.get_registry")
    def test_list_products_empty_registry(self, mock_get_registry, mock_print):
        """Test listing products with empty registry."""
        mock_registry = MagicMock()
        mock_registry._products = {}
        mock_get_registry.return_value = mock_registry

        list_products(filter_type=None)

        output = "".join(
            str(call.args[0]) if call.args else str(call)
            for call in mock_print.call_args_list
        )
        assert "No products in registry" in output


class TestRunCommand:
    """Test run command."""

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_default_no_devices(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with no arguments creates no devices."""
        # With no default color device, running with no args should error
        await run()

        # Verify no server was created (returns None on error)
        mock_server_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_color(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with explicit color light."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(color=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_setup_logging.assert_called_once_with(False)
        mock_server_class.assert_called_once()
        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1
        mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_verbose(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with verbose logging."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(verbose=True, color=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_setup_logging.assert_called_once_with(True)

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__.DevicePersistenceAsyncFile")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_persistence(
        self, mock_setup_logging, mock_storage_class, mock_server_class, mock_resolve
    ):
        """Test running with persistent storage."""
        from unittest.mock import AsyncMock

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        mock_storage = MagicMock()
        mock_storage.storage_dir = "/tmp/lifx"
        mock_storage.shutdown = AsyncMock()
        mock_storage.save_device_state = AsyncMock()
        mock_storage.load_device_state.return_value = None
        mock_storage.list_devices.return_value = []
        mock_storage_class.return_value = mock_storage

        task = asyncio.create_task(run(persistent=True, color=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_storage_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_custom_bind_port(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with custom bind address and port."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(bind="192.168.1.100", port=12345, color=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify server was created with correct bind and port
        call_args = mock_server_class.call_args[0]
        assert call_args[2] == "192.168.1.100"
        assert call_args[3] == 12345

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_multiple_device_types(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with multiple device types."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(color=2, infrared=1, multizone=1, tile=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 5  # 2 color + 1 infrared + 1 multizone + 1 tile

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_product_ids(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with product IDs."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(product=[27, 32]))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.logging.getLogger")
    async def test_run_with_invalid_product_id(self, mock_get_logger, mock_resolve):
        """Test running with invalid product ID."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        await run(product=[9999])

        assert any(
            "Failed to create device" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.logging.getLogger")
    async def test_run_with_no_devices(self, mock_get_logger, mock_resolve):
        """Test running with no devices configured."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        await run()

        assert any(
            "No devices configured" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_custom_serial(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with custom serial prefix and start."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(
            run(color=2, serial_prefix="cafe00", serial_start=100)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert devices[0].state.serial.startswith("cafe00")

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_multizone_options(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with multizone-specific options."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(
            run(multizone=1, multizone_zones=32, multizone_extended=True)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1
        assert devices[0].state.has_multizone

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_tile_options(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with tile-specific options."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(
            run(tile=1, tile_count=3, tile_width=8, tile_height=8)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1
        assert devices[0].state.has_matrix

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_color_temperature_lights(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with color temperature lights."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(color_temperature=2))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_hev_lights(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with HEV lights."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(hev=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1


class TestDeprecationWarnings:
    """Test deprecation warnings for --persistent flags."""

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_persistent_deprecation_warning(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """--persistent emits a DeprecationWarning."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task = asyncio.create_task(run(persistent=True, color=1))
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        assert "export-config" in str(deprecation_warnings[0].message)
        assert "--persistent" in str(deprecation_warnings[0].message)

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_persistent_deprecation_logged(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """--persistent logs a deprecation warning via logger."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(persistent=True, color=1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "--persistent is deprecated" in str(call)
        ]
        assert len(warning_calls) >= 1

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_persistent_scenarios_deprecation_warning(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """--persistent-scenarios emits a DeprecationWarning."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task = asyncio.create_task(
                run(persistent=True, persistent_scenarios=True, color=1)
            )
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        scenario_warnings = [
            x
            for x in deprecation_warnings
            if "--persistent-scenarios" in str(x.message)
        ]
        assert len(scenario_warnings) >= 1
        assert "export-config" in str(scenario_warnings[0].message)

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_no_deprecation_without_persistent(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """No deprecation warnings when --persistent is not used."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task = asyncio.create_task(run(color=1))
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0


class TestScenarioDefToCore:
    """Test _scenario_def_to_core conversion."""

    def test_empty_definition(self):
        """All-None ScenarioDefinition produces default ScenarioConfig."""
        defn = ScenarioDefinition()
        result = _scenario_def_to_core(defn)
        assert isinstance(result, ScenarioConfig)
        assert result.drop_packets == {}
        assert result.malformed_packets == []
        assert result.send_unhandled is True  # Default is on

    def test_full_definition(self):
        """All fields populated are forwarded."""
        defn = ScenarioDefinition(
            drop_packets={101: 1.0},
            response_delays={116: 0.5},
            malformed_packets=[506],
            invalid_field_values=[107],
            firmware_version=(3, 70),
            partial_responses=[512],
            send_unhandled=True,
        )
        result = _scenario_def_to_core(defn)
        assert result.drop_packets == {101: 1.0}
        assert result.response_delays == {116: 0.5}
        assert result.malformed_packets == [506]
        assert result.invalid_field_values == [107]
        assert result.firmware_version == (3, 70)
        assert result.partial_responses == [512]
        assert result.send_unhandled is True

    def test_partial_definition(self):
        """Only specified fields are set, rest get defaults."""
        defn = ScenarioDefinition(drop_packets={101: 0.5})
        result = _scenario_def_to_core(defn)
        assert result.drop_packets == {101: 0.5}
        assert result.response_delays == {}
        assert result.malformed_packets == []


class TestApplyConfigScenarios:
    """Test _apply_config_scenarios function."""

    def test_global_scenario(self):
        """Global scenario is applied."""
        scenarios = ScenariosConfig(
            global_scenario=ScenarioDefinition(drop_packets={101: 1.0}),
        )
        logger = logging.getLogger("test")
        manager = _apply_config_scenarios(scenarios, logger)
        assert isinstance(manager, HierarchicalScenarioManager)
        assert manager.global_scenario is not None
        assert manager.global_scenario.drop_packets == {101: 1.0}

    def test_device_scenario(self):
        """Device-specific scenario is applied."""
        scenarios = ScenariosConfig(
            devices={"d073d5000001": ScenarioDefinition(send_unhandled=True)},
        )
        logger = logging.getLogger("test")
        manager = _apply_config_scenarios(scenarios, logger)
        assert "d073d5000001" in manager.device_scenarios

    def test_type_scenario(self):
        """Type scenario is applied."""
        scenarios = ScenariosConfig(
            types={"multizone": ScenarioDefinition(malformed_packets=[506])},
        )
        logger = logging.getLogger("test")
        manager = _apply_config_scenarios(scenarios, logger)
        assert "multizone" in manager.type_scenarios

    def test_location_and_group_scenarios(self):
        """Location and group scenarios are applied."""
        scenarios = ScenariosConfig(
            locations={"Office": ScenarioDefinition(drop_packets={101: 0.5})},
            groups={"Testing": ScenarioDefinition(response_delays={116: 1.0})},
        )
        logger = logging.getLogger("test")
        manager = _apply_config_scenarios(scenarios, logger)
        assert "Office" in manager.location_scenarios
        assert "Testing" in manager.group_scenarios

    def test_empty_scenarios(self):
        """Empty ScenariosConfig returns manager with default state."""
        scenarios = ScenariosConfig()
        logger = logging.getLogger("test")
        manager = _apply_config_scenarios(scenarios, logger)
        # Default global scenario has empty drop_packets
        assert manager.global_scenario.drop_packets == {}
        assert len(manager.device_scenarios) == 0


class TestLoadMergedConfigErrors:
    """Test _load_merged_config error paths."""

    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        side_effect=FileNotFoundError("Config file not found: /bad/path.yaml"),
    )
    def test_config_file_not_found(self, mock_resolve, capsys):
        """Returns None when config file is not found."""
        result = _load_merged_config(config_flag="/bad/path.yaml")
        assert result is None
        captured = capsys.readouterr()
        assert "Error:" in captured.out

    @patch(
        "lifx_emulator_app.__main__.load_config",
        side_effect=ValueError("invalid config"),
    )
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_config_load_exception(self, mock_resolve, mock_load, capsys):
        """Returns None when config file fails to load."""
        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is None
        captured = capsys.readouterr()
        assert "Error loading config file" in captured.out

    @patch("lifx_emulator_app.__main__.load_config")
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_devices_carried_from_config(self, mock_resolve, mock_load):
        """Devices list from config file is carried through to result."""
        from lifx_emulator_app.config import DeviceDefinition, EmulatorConfig

        devices = [DeviceDefinition(product_id=27, label="Test")]
        mock_load.return_value = EmulatorConfig(devices=devices)

        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is not None
        assert "devices" in result
        assert len(result["devices"]) == 1
        assert result["devices"][0].label == "Test"

    @patch("lifx_emulator_app.__main__.load_config")
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_config_path_stored(self, mock_resolve, mock_load):
        """Config path is stored in result for logging."""
        from lifx_emulator_app.config import EmulatorConfig

        mock_load.return_value = EmulatorConfig()
        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is not None
        assert result["_config_path"] == "/fake/config.yaml"

    @patch("lifx_emulator_app.__main__.load_config")
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_empty_devices_list_preserved(self, mock_resolve, mock_load):
        """Explicit `devices: []` is preserved, not treated as None."""
        from lifx_emulator_app.config import EmulatorConfig

        mock_load.return_value = EmulatorConfig(devices=[])
        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is not None
        assert result["devices"] == []

    @patch("lifx_emulator_app.__main__.load_config")
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_empty_scenarios_preserved(self, mock_resolve, mock_load):
        """Explicit `scenarios: {}` is preserved, not treated as None."""
        from lifx_emulator_app.config import EmulatorConfig

        mock_load.return_value = EmulatorConfig(scenarios=ScenariosConfig())
        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is not None
        assert "scenarios" in result


class TestLoadMergedConfigScenarios:
    """Test _load_merged_config passes scenarios from file config."""

    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    def test_no_scenarios_by_default(self, mock_resolve):
        """Without config file, no scenarios key in result."""
        result = _load_merged_config(config_flag=None)
        assert result is not None
        assert "scenarios" not in result

    @patch("lifx_emulator_app.__main__.load_config")
    @patch(
        "lifx_emulator_app.__main__.resolve_config_path",
        return_value="/fake/config.yaml",
    )
    def test_scenarios_passed_through(self, mock_resolve, mock_load):
        """Scenarios from file config are included in result."""
        from lifx_emulator_app.config import EmulatorConfig

        scenarios = ScenariosConfig(
            global_scenario=ScenarioDefinition(drop_packets={101: 1.0}),
        )
        mock_load.return_value = EmulatorConfig(color=1, scenarios=scenarios)

        result = _load_merged_config(config_flag="/fake/config.yaml")
        assert result is not None
        assert "scenarios" in result
        assert result["scenarios"] is scenarios


# Helper to build a standard config dict for run() tests
def _make_cfg(**overrides):
    base = {
        "bind": "127.0.0.1",
        "port": 56700,
        "verbose": False,
        "persistent": False,
        "persistent_scenarios": False,
        "api": False,
        "api_host": "127.0.0.1",
        "api_port": 8080,
        "api_activity": True,
        "browser": False,
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
    base.update(overrides)
    return base


class TestRunWithConfigDevices:
    """Test run command with per-device config definitions."""

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_device_with_explicit_serial(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Device with explicit serial uses that serial."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[DeviceDefinition(product_id=27, serial="aabbcc000001")]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1
        assert devices[0].state.serial == "aabbcc000001"

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_device_with_power_and_color(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Device power_level and color are applied."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(
                    product_id=27,
                    power_level=65535,
                    color=HsbkConfig(
                        hue=21845,
                        saturation=65535,
                        brightness=65535,
                        kelvin=3500,
                    ),
                ),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert devices[0].state.power_level == 65535
        assert devices[0].state.color.hue == 21845
        assert devices[0].state.color.saturation == 65535

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_device_with_location_and_group(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Devices with same location share the same location_id."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(product_id=27, location="Office", group="Testing"),
                DeviceDefinition(product_id=27, location="Office", group="Other"),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2
        # Same location = same location_id
        assert devices[0].state.location_id == devices[1].state.location_id
        assert devices[0].state.location_label == "Office"
        # Different group = different group_id
        assert devices[0].state.group_id != devices[1].state.group_id
        assert devices[0].state.group_label == "Testing"
        assert devices[1].state.group_label == "Other"
        # Location IDs should be deterministic (uuid5)
        ns = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        expected_loc_id = uuid.uuid5(ns, "Office").bytes
        assert devices[0].state.location_id == expected_loc_id

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_device_with_zone_colors(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Zone colors are applied to multizone device."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(
                    product_id=38,
                    zone_count=8,
                    zone_colors=[
                        HsbkConfig(
                            hue=i * 8000,
                            saturation=65535,
                            brightness=65535,
                            kelvin=3500,
                        )
                        for i in range(8)
                    ],
                ),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1
        assert devices[0].state.has_multizone
        zone_colors = devices[0].state.zone_colors
        assert len(zone_colors) == 8
        assert zone_colors[0].hue == 0
        assert zone_colors[1].hue == 8000

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_zone_colors_padded_to_zone_count(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Zone colors shorter than zone_count are padded with default color."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(
                    product_id=38,
                    zone_count=80,
                    zone_colors=[
                        HsbkConfig(
                            hue=21845,
                            saturation=65535,
                            brightness=65535,
                            kelvin=3500,
                        ),
                        HsbkConfig(
                            hue=43690,
                            saturation=65535,
                            brightness=65535,
                            kelvin=3500,
                        ),
                    ],
                ),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        zone_colors = devices[0].state.zone_colors
        assert len(zone_colors) == 80
        # First two are the configured colors
        assert zone_colors[0].hue == 21845
        assert zone_colors[1].hue == 43690
        # Remaining are padded with default (0, 0, 0, 3500)
        assert zone_colors[2].hue == 0
        assert zone_colors[2].saturation == 0
        assert zone_colors[2].brightness == 0
        assert zone_colors[2].kelvin == 3500
        assert zone_colors[79].kelvin == 3500

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_zone_colors_truncated_to_zone_count(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Zone colors longer than zone_count are truncated."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(
                    product_id=38,
                    zone_count=8,
                    zone_colors=[
                        HsbkConfig(
                            hue=i * 3000,
                            saturation=65535,
                            brightness=65535,
                            kelvin=3500,
                        )
                        for i in range(20)
                    ],
                ),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        zone_colors = devices[0].state.zone_colors
        assert len(zone_colors) == 8
        assert zone_colors[7].hue == 21000

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_explicit_serial_skips_in_auto_generator(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Auto-generated serials skip explicitly assigned serials."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            color=1,
            devices=[DeviceDefinition(product_id=27, serial="d073d5000001")],
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2
        serials = [d.state.serial for d in devices]
        # The auto-generated color device should skip 000001
        assert "d073d5000001" in serials
        assert "d073d5000002" in serials
        assert serials.count("d073d5000001") == 1

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_device_with_infrared_and_hev_fields(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Infrared brightness and HEV fields are applied."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[
                DeviceDefinition(product_id=29, infrared_brightness=32768),
                DeviceDefinition(
                    product_id=90,
                    hev_cycle_duration=3600,
                    hev_indication=False,
                ),
            ]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2
        # Infrared device
        assert devices[0].state.infrared_brightness == 32768
        # HEV device
        assert devices[1].state.hev_cycle_duration_s == 3600
        assert devices[1].state.hev_indication is False

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_config_scenarios_applied_to_server(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Scenarios from config are applied to the server."""
        mock_load_cfg.return_value = _make_cfg(
            color=1,
            scenarios=ScenariosConfig(
                global_scenario=ScenarioDefinition(drop_packets={101: 1.0}),
            ),
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify scenario_manager was passed to server
        call_kwargs = mock_server_class.call_args[1]
        scenario_manager = call_kwargs["scenario_manager"]
        assert scenario_manager is not None
        assert isinstance(scenario_manager, HierarchicalScenarioManager)
        assert scenario_manager.global_scenario.drop_packets == {101: 1.0}

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__._load_merged_config", return_value=None)
    async def test_run_returns_false_when_config_fails(self, mock_load_cfg):
        """run() returns False when config loading fails."""
        result = await run()
        assert result is False

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_persistent_scenarios_without_persistent(
        self, mock_setup_logging, mock_resolve
    ):
        """run() returns False when --persistent-scenarios used without --persistent."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = await run(persistent_scenarios=True, color=1)
        assert result is False
        assert any(
            "--persistent-scenarios requires --persistent" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    async def test_run_with_switch_devices(
        self, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Test running with switch devices."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(switch=2))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 2
        assert devices[0].state.has_relays

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_run_config_device_with_label(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Device label from config definition is applied."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_load_cfg.return_value = _make_cfg(
            devices=[DeviceDefinition(product_id=27, label="My Lamp")]
        )

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        assert devices[0].state.label == "My Lamp"

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_run_config_device_invalid_product(
        self, mock_load_cfg, mock_setup_logging, mock_resolve
    ):
        """run() returns early when config device has invalid product_id."""
        from lifx_emulator_app.config import DeviceDefinition

        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_load_cfg.return_value = _make_cfg(
            devices=[DeviceDefinition(product_id=9999)]
        )

        result = await run()
        assert result is None
        assert any(
            "Failed to create device from config" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__.DevicePersistenceAsyncFile")
    async def test_run_persistent_no_devices_warning(
        self, mock_storage_class, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Persistent mode with no devices logs warning instead of error."""
        from unittest.mock import AsyncMock

        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_storage = MagicMock()
        mock_storage.storage_dir = "/tmp/lifx"
        mock_storage.shutdown = AsyncMock()
        mock_storage.list_devices.return_value = []
        mock_storage_class.return_value = mock_storage

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(persistent=True))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert any(
            "No devices configured" in str(call)
            for call in mock_logger.warning.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_run_logs_config_path(
        self, mock_load_cfg, mock_setup_logging, mock_server_class, mock_resolve
    ):
        """Config path is logged when a config file was loaded."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_load_cfg.return_value = _make_cfg(color=1, _config_path="/my/config.yaml")

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert any(
            "Loaded config from" in str(call)
            for call in mock_logger.info.call_args_list
        )


class TestBrowserFlag:
    """Tests for --browser flag functionality."""

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.webbrowser.open")
    @patch("lifx_emulator_app.api.run_api_server")
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_browser_flag_opens_browser(
        self,
        mock_load_cfg,
        mock_setup_logging,
        mock_server_class,
        mock_resolve,
        mock_run_api,
        mock_webbrowser_open,
    ):
        """--browser flag opens dashboard in default browser when API enabled."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_load_cfg.return_value = _make_cfg(
            api=True, browser=True, color=1, api_host="127.0.0.1", api_port=8080
        )

        mock_server = MagicMock()
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)
        mock_server_class.return_value = mock_server

        # Mock run_api_server to return a completed future
        api_future = asyncio.Future()
        api_future.set_result(None)
        mock_run_api.return_value = api_future

        task = asyncio.create_task(run())
        await asyncio.sleep(0.2)  # Give more time for browser opening
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify webbrowser.open was called with the dashboard URL
        mock_webbrowser_open.assert_called_once_with("http://127.0.0.1:8080")

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.webbrowser.open")
    @patch("lifx_emulator_app.api.run_api_server")
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_browser_flag_not_called_when_false(
        self,
        mock_load_cfg,
        mock_setup_logging,
        mock_server_class,
        mock_resolve,
        mock_run_api,
        mock_webbrowser_open,
    ):
        """Browser is not opened when --browser flag is not set."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_load_cfg.return_value = _make_cfg(
            api=True,
            browser=False,
            color=1,  # browser=False
        )

        mock_server = MagicMock()
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)
        mock_server_class.return_value = mock_server

        # Mock run_api_server to return a completed future
        api_future = asyncio.Future()
        api_future.set_result(None)
        mock_run_api.return_value = api_future

        task = asyncio.create_task(run())
        await asyncio.sleep(0.2)  # Give more time for browser check
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify webbrowser.open was NOT called
        mock_webbrowser_open.assert_not_called()

    @pytest.mark.asyncio
    @patch("lifx_emulator_app.__main__.webbrowser.open")
    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
    @patch("lifx_emulator_app.__main__._setup_logging")
    @patch("lifx_emulator_app.__main__._load_merged_config")
    async def test_browser_flag_not_called_without_api(
        self,
        mock_load_cfg,
        mock_setup_logging,
        mock_server_class,
        mock_resolve,
        mock_webbrowser_open,
    ):
        """Browser is not opened when --api flag is not set."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_load_cfg.return_value = _make_cfg(
            api=False,
            browser=True,
            color=1,  # api=False
        )

        mock_server = MagicMock()
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)
        mock_server_class.return_value = mock_server

        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify webbrowser.open was NOT called (API not enabled)
        mock_webbrowser_open.assert_not_called()
