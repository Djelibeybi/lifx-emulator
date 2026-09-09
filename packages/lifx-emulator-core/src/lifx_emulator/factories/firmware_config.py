"""Firmware version configuration for devices."""

from __future__ import annotations

from lifx_emulator.devices.states import Connectivity
from lifx_emulator.products.specs import (
    get_default_firmware_version,
    get_max_firmware_version,
)


class FirmwareConfig:
    """Determines firmware versions for devices.

    Extended multizone support requires firmware 3.70+.
    Devices without extended multizone use firmware 2.60.
    A Thread device defaults to and is floored at firmware 4.200 -- this
    takes precedence over any product-specific specs.yml default. A
    product may also declare a terminal-firmware ceiling in specs.yml
    (currently only the original LIFX Tile, product 55); a resolved value
    above that ceiling raises ValueError, even when explicitly requested.

    Examples:
        >>> config = FirmwareConfig()
        >>> major, minor = config.get_firmware_version(extended_multizone=True)
        >>> (major, minor)
        (3, 70)
        >>> major, minor = config.get_firmware_version(extended_multizone=False)
        >>> (major, minor)
        (2, 60)
        >>> config.get_firmware_version(connectivity=Connectivity.THREAD)
        (4, 200)
    """

    # Firmware versions
    VERSION_EXTENDED = (3, 70)  # Extended multizone support
    VERSION_LEGACY = (2, 60)  # Legacy firmware
    VERSION_THREAD = (4, 200)  # Thread minimum and default firmware

    def get_firmware_version(
        self,
        product_id: int | None = None,
        extended_multizone: bool | None = None,
        override: tuple[int, int] | None = None,
        connectivity: Connectivity | None = None,
    ) -> tuple[int, int]:
        """Get firmware version based on connectivity, product specs or
        extended multizone support.

        Precedence order:
        1. Explicit override parameter
        2. Thread connectivity default/floor (4.200)
        3. Product-specific default from specs.yml
        4. Extended multizone flag (3.70 for True/None, 2.60 for False)

        The resolved value is then validated: a Thread device's firmware
        must be at least 4.200, and a product's declared terminal-firmware
        ceiling (if any) may never be exceeded -- either check raises
        ValueError, even when the offending value came from an explicit
        override.

        Args:
            product_id: Optional product ID to check specs for defaults
                and for a terminal-firmware ceiling
            extended_multizone: Whether device supports extended multizone.
                               None or True defaults to 3.70, False gives 2.60
            override: Optional explicit firmware version to use
            connectivity: The device's connectivity. Narrowed to the enum
                (not a raw string) because this method compares directly
                against Connectivity.THREAD -- string coercion is the
                builder's job, in DeviceBuilder._resolve_connectivity(),
                which runs before this method is reached.

        Returns:
            Tuple of (major, minor) firmware version

        Raises:
            ValueError: If a Thread device's resolved firmware is below
                4.200, or if the resolved firmware exceeds the product's
                declared terminal-firmware ceiling.

        Examples:
            >>> config = FirmwareConfig()
            >>> config.get_firmware_version(extended_multizone=True)
            (3, 70)
            >>> config.get_firmware_version(extended_multizone=False)
            (2, 60)
            >>> config.get_firmware_version(override=(4, 0))
            (4, 0)
            >>> # With product_id, uses specs if defined
            >>> config.get_firmware_version(product_id=27)  # doctest: +SKIP
            (3, 70)
            >>> config.get_firmware_version(connectivity=Connectivity.THREAD)
            (4, 200)
        """
        if override is not None:
            result = override
        elif connectivity == Connectivity.THREAD:
            result = self.VERSION_THREAD
        elif (
            product_id is not None
            and (specs_version := get_default_firmware_version(product_id)) is not None
        ):
            result = specs_version
        elif extended_multizone is False:
            result = self.VERSION_LEGACY
        else:
            result = self.VERSION_EXTENDED

        self._validate_firmware(result, product_id, connectivity, override)
        return result

    def _validate_firmware(
        self,
        result: tuple[int, int],
        product_id: int | None,
        connectivity: Connectivity | None,
        override: tuple[int, int] | None,
    ) -> None:
        """Raise ValueError if the resolved firmware violates the Thread
        floor or a product's terminal-firmware ceiling.

        The floor check runs first: a sub-floor Thread request must never
        be silently accepted just because it also happens to fit under a
        product's ceiling. The ceiling check is not skipped when an
        override was supplied -- a product's terminal firmware is never
        exempted by an explicit request.

        Args:
            result: The firmware version resolved by get_firmware_version()
            product_id: Optional product ID, for the ceiling check
            connectivity: The device's connectivity, for the floor check
            override: The caller's explicit override, if any -- used only
                to decide whether to enrich the ceiling-violation message
                when the rejection was caused by an unrequested Thread
                default

        Raises:
            ValueError: See get_firmware_version().
        """
        if connectivity == Connectivity.THREAD and result < self.VERSION_THREAD:
            raise ValueError(
                f"Thread firmware must be at least {self.VERSION_THREAD}, got {result}"
            )

        if product_id is None:
            return

        max_firmware = get_max_firmware_version(product_id)
        if max_firmware is None or result <= max_firmware:
            return

        message = (
            f"Firmware {result} exceeds product {product_id}'s maximum {max_firmware}"
        )
        if connectivity == Connectivity.THREAD and override is None:
            message += (
                f" (Thread's default firmware of {self.VERSION_THREAD} "
                "cannot be reduced to fit)"
            )
        raise ValueError(message)
