"""Serial number generation service for LIFX devices."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.products.registry import ProductInfo


class SerialGenerator:
    """Generates serial numbers for emulated LIFX devices.

    Serial numbers are 12-character hex strings with different prefixes
    based on device capabilities for easier identification.

    Prefixes:
        - d073d9: Matrix/Tile devices
        - d073d8: Multizone devices (strips/beams)
        - d073d7: HEV devices
        - d073d6: Infrared devices
        - d073d5: Regular color/temperature lights

    Examples:
        >>> generator = SerialGenerator()
        >>> serial = generator.generate(product_info)
        >>> len(serial)
        12
        >>> serial.startswith("d073d")
        True
    """

    # Device type prefixes for easy identification
    PREFIX_MATRIX = "d073d9"
    PREFIX_MULTIZONE = "d073d8"
    PREFIX_HEV = "d073d7"
    PREFIX_INFRARED = "d073d6"
    PREFIX_DEFAULT = "d073d5"

    def generate(self, product_info: ProductInfo) -> str:
        """Generate a serial number based on product capabilities.

        Args:
            product_info: Product information from registry

        Returns:
            12-character hex serial number

        Examples:
            >>> from lifx_emulator.products.registry import get_product
            >>> generator = SerialGenerator()
            >>> product = get_product(55)  # LIFX Tile
            >>> serial = generator.generate(product)
            >>> serial.startswith("d073d9")  # Matrix prefix
            True
        """
        prefix = self._determine_prefix(product_info)
        suffix = random.randint(100000, 999999)  # nosec
        return f"{prefix}{suffix:06x}"

    def _determine_prefix(self, product_info: ProductInfo) -> str:
        """Determine the prefix based on product capabilities.

        Precedence: matrix > multizone > hev > infrared > default

        Args:
            product_info: Product information from registry

        Returns:
            6-character hex prefix
        """
        if product_info.has_matrix:
            return self.PREFIX_MATRIX
        elif product_info.has_multizone:
            return self.PREFIX_MULTIZONE
        elif product_info.has_hev:
            return self.PREFIX_HEV
        elif product_info.has_infrared:
            return self.PREFIX_INFRARED
        else:
            return self.PREFIX_DEFAULT
