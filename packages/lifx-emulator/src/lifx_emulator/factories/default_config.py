"""Default configuration helpers for device factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lifx_emulator.protocol.protocol_types import LightHsbk

if TYPE_CHECKING:
    from lifx_emulator.products.registry import ProductInfo


class DefaultColorConfig:
    """Determines default colors for devices based on product capabilities.

    Different device types get unique default colors for visual identification:
    - Brightness-only: White at 2700K
    - Color temperature: White at 3500K (middle of range)
    - Matrix devices: Cyan
    - Multizone devices: Red
    - HEV devices: Green
    - Infrared devices: Red
    - Color devices: Orange

    Examples:
        >>> from lifx_emulator.products.registry import get_product
        >>> config = DefaultColorConfig()
        >>> product = get_product(27)  # LIFX A19 (color)
        >>> color = config.get_default_color(product)
        >>> color.saturation
        65535
    """

    # Hue values for different device types (0-65535)
    HUE_CYAN = 43690
    HUE_RED = 0
    HUE_GREEN = 32768
    HUE_ORANGE = 21845

    # Default brightness (50%)
    DEFAULT_BRIGHTNESS = 32768

    # Default kelvin values
    KELVIN_WARM = 2700
    KELVIN_NEUTRAL = 3500

    def get_default_color(self, product_info: ProductInfo) -> LightHsbk:
        """Get default color for a product.

        Args:
            product_info: Product information from registry

        Returns:
            Default LightHsbk color for the device
        """
        if not product_info.has_color and self._is_brightness_only(product_info):
            return self._brightness_only_color()
        elif not product_info.has_color and self._is_temperature_adjustable(
            product_info
        ):
            return self._temperature_adjustable_color()
        else:
            return self._color_device_color(product_info)

    def _is_brightness_only(self, product_info: ProductInfo) -> bool:
        """Check if device has fixed color temperature.

        Args:
            product_info: Product information from registry

        Returns:
            True if temperature range has identical min/max
        """
        return (
            product_info.temperature_range is not None
            and product_info.temperature_range.min == product_info.temperature_range.max
        )

    def _is_temperature_adjustable(self, product_info: ProductInfo) -> bool:
        """Check if device has adjustable color temperature.

        Args:
            product_info: Product information from registry

        Returns:
            True if temperature range has different min/max
        """
        return (
            product_info.temperature_range is not None
            and product_info.temperature_range.min != product_info.temperature_range.max
        )

    def _brightness_only_color(self) -> LightHsbk:
        """Get default color for brightness-only devices.

        Returns:
            White at 2700K with 50% brightness
        """
        return LightHsbk(
            hue=0,
            saturation=0,
            brightness=self.DEFAULT_BRIGHTNESS,
            kelvin=self.KELVIN_WARM,
        )

    def _temperature_adjustable_color(self) -> LightHsbk:
        """Get default color for temperature-adjustable devices.

        Returns:
            White at 3500K with 50% brightness
        """
        return LightHsbk(
            hue=0,
            saturation=0,
            brightness=self.DEFAULT_BRIGHTNESS,
            kelvin=self.KELVIN_NEUTRAL,
        )

    def _color_device_color(self, product_info: ProductInfo) -> LightHsbk:
        """Get default color for color-capable devices.

        Different hues based on device capabilities for easy visual identification.

        Args:
            product_info: Product information from registry

        Returns:
            Colored LightHsbk with full saturation
        """
        hue = self._get_hue_for_capability(product_info)
        return LightHsbk(
            hue=hue,
            saturation=65535,
            brightness=self.DEFAULT_BRIGHTNESS,
            kelvin=self.KELVIN_NEUTRAL,
        )

    def _get_hue_for_capability(self, product_info: ProductInfo) -> int:
        """Determine hue based on product capabilities.

        Precedence: matrix > multizone > hev > infrared > default

        Args:
            product_info: Product information from registry

        Returns:
            Hue value (0-65535)
        """
        if product_info.has_matrix:
            return self.HUE_CYAN
        elif product_info.has_multizone:
            return self.HUE_RED
        elif product_info.has_hev:
            return self.HUE_GREEN
        elif product_info.has_infrared:
            return self.HUE_RED
        else:
            return self.HUE_ORANGE
