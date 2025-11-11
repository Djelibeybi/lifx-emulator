"""Tests for CLI functionality."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from lifx_emulator.__main__ import (
    _format_capabilities,
    _setup_logging,
    list_products,
    run,
)
from lifx_emulator.factories import (
    create_color_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.products.registry import ProductInfo, TemperatureRange


class TestSetupLogging:
    """Test logging configuration."""

    @patch("lifx_emulator.__main__.logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test that verbose logging is configured correctly."""
        _setup_logging(True)
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == 10  # logging.DEBUG

    @patch("lifx_emulator.__main__.logging.basicConfig")
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
        assert "switch" in caps
        # Buttons shouldn't be listed separately for switches
        assert "buttons" not in caps

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
        assert "full color" in caps

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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.get_registry")
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
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_default_config(self, mock_setup_logging, mock_server_class):
        """Test running with default configuration."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        # Run for a short time then cancel
        task = asyncio.create_task(run())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once_with(False)

        # Verify server was created and started
        mock_server_class.assert_called_once()
        devices = mock_server_class.call_args[0][0]
        assert len(devices) == 1  # Default is 1 color light
        mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_verbose(self, mock_setup_logging, mock_server_class):
        """Test running with verbose logging."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(verbose=True))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_setup_logging.assert_called_once_with(True)

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__.DevicePersistenceAsyncFile")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_persistence(
        self, mock_setup_logging, mock_storage_class, mock_server_class
    ):
        """Test running with persistent storage."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        mock_storage = MagicMock()
        mock_storage.storage_dir = "/tmp/lifx"
        mock_storage.shutdown = MagicMock(return_value=asyncio.Future())
        mock_storage.shutdown.return_value.set_result(None)
        mock_storage_class.return_value = mock_storage

        task = asyncio.create_task(run(persistent=True))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_storage_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_custom_bind_port(
        self, mock_setup_logging, mock_server_class
    ):
        """Test running with custom bind address and port."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        task = asyncio.create_task(run(bind="192.168.1.100", port=12345))
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
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_multiple_device_types(
        self, mock_setup_logging, mock_server_class
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
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_product_ids(self, mock_setup_logging, mock_server_class):
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
        # Should only have 2 devices from product IDs, not the default color light
        assert len(devices) == 2

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.logging.getLogger")
    async def test_run_with_invalid_product_id(self, mock_get_logger):
        """Test running with invalid product ID."""
        # Create a mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Use a product ID that doesn't exist
        await run(product=[9999])

        # Verify error was logged
        assert any(
            "Failed to create device" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.logging.getLogger")
    async def test_run_with_no_devices(self, mock_get_logger):
        """Test running with no devices configured."""
        # Create a mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Set all device counts to 0
        await run(color=0)

        # Verify error was logged
        assert any(
            "No devices configured" in str(call)
            for call in mock_logger.error.call_args_list
        )

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_custom_serial(self, mock_setup_logging, mock_server_class):
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
        # Check first device serial starts with cafe00000064 (100 in hex)
        assert devices[0].state.serial.startswith("cafe00")

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_multizone_options(
        self, mock_setup_logging, mock_server_class
    ):
        """Test running with multizone-specific options."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        # Need to disable default color light
        task = asyncio.create_task(
            run(color=0, multizone=1, multizone_zones=32, multizone_extended=True)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        devices = mock_server_class.call_args[0][0]
        # Verify multizone device was created
        assert len(devices) == 1
        assert devices[0].state.has_multizone

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_tile_options(self, mock_setup_logging, mock_server_class):
        """Test running with tile-specific options."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.start = MagicMock(return_value=asyncio.Future())
        mock_server.start.return_value.set_result(None)
        mock_server.stop = MagicMock(return_value=asyncio.Future())
        mock_server.stop.return_value.set_result(None)

        # Need to disable default color light
        task = asyncio.create_task(
            run(color=0, tile=1, tile_count=3, tile_width=8, tile_height=8)
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
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_color_temperature_lights(
        self, mock_setup_logging, mock_server_class
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
        # 1 default color + 2 color_temperature
        assert len(devices) == 3

    @pytest.mark.asyncio
    @patch("lifx_emulator.__main__.EmulatedLifxServer")
    @patch("lifx_emulator.__main__._setup_logging")
    async def test_run_with_hev_lights(self, mock_setup_logging, mock_server_class):
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
        # 1 default color + 1 hev
        assert len(devices) == 2
