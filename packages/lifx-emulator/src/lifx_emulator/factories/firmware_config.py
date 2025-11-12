"""Firmware version configuration for devices."""

from __future__ import annotations


class FirmwareConfig:
    """Determines firmware versions for devices.

    Extended multizone support requires firmware 3.70+.
    Devices without extended multizone use firmware 2.60.

    Examples:
        >>> config = FirmwareConfig()
        >>> major, minor = config.get_firmware_version(extended_multizone=True)
        >>> (major, minor)
        (3, 70)
        >>> major, minor = config.get_firmware_version(extended_multizone=False)
        >>> (major, minor)
        (2, 60)
    """

    # Firmware versions
    VERSION_EXTENDED = (3, 70)  # Extended multizone support
    VERSION_LEGACY = (2, 60)  # Legacy firmware

    def get_firmware_version(
        self,
        extended_multizone: bool | None = None,
        override: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        """Get firmware version based on extended multizone support.

        Args:
            extended_multizone: Whether device supports extended multizone.
                               None or True defaults to 3.70, False gives 2.60
            override: Optional explicit firmware version to use

        Returns:
            Tuple of (major, minor) firmware version

        Examples:
            >>> config = FirmwareConfig()
            >>> config.get_firmware_version(extended_multizone=True)
            (3, 70)
            >>> config.get_firmware_version(extended_multizone=False)
            (2, 60)
            >>> config.get_firmware_version(override=(4, 0))
            (4, 0)
        """
        # Explicit override takes precedence
        if override is not None:
            return override

        # None or True defaults to extended (3.70)
        # Only explicit False gives legacy (2.60)
        if extended_multizone is False:
            return self.VERSION_LEGACY
        else:
            return self.VERSION_EXTENDED
