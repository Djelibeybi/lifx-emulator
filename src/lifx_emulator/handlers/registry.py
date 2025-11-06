"""Handler registry for managing packet handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifx_emulator.handlers.base import PacketHandler

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Registry for packet handlers using Strategy pattern.

    The registry maps packet type numbers to handler instances.
    Handlers can be registered individually or in bulk.

    Example:
        >>> registry = HandlerRegistry()
        >>> registry.register(GetServiceHandler())
        >>> handler = registry.get_handler(2)  # Device.GetService
        >>> response = handler.handle(device_state, None, True)
    """

    def __init__(self):
        """Initialize an empty handler registry."""
        self._handlers: dict[int, PacketHandler] = {}

    def register(self, handler: PacketHandler) -> None:
        """Register a packet handler.

        Args:
            handler: Handler instance to register

        Raises:
            ValueError: If handler doesn't have PKT_TYPE attribute

        Note:
            If a handler for this packet type already exists, it will be replaced.
        """
        if not hasattr(handler, "PKT_TYPE"):
            raise ValueError(
                f"Handler {handler.__class__.__name__} missing PKT_TYPE attribute"
            )

        pkt_type = handler.PKT_TYPE

        # Warn if replacing existing handler
        if pkt_type in self._handlers:
            old_handler = self._handlers[pkt_type]
            logger.warning(
                f"Replacing handler for packet type {pkt_type}: "
                f"{old_handler.__class__.__name__} -> {handler.__class__.__name__}"
            )

        self._handlers[pkt_type] = handler
        logger.debug(
            f"Registered {handler.__class__.__name__} for packet type {pkt_type}"
        )

    def register_all(self, handlers: list[PacketHandler]) -> None:
        """Register multiple handlers at once.

        Args:
            handlers: List of handler instances to register
        """
        for handler in handlers:
            self.register(handler)

    def get_handler(self, pkt_type: int) -> PacketHandler | None:
        """Get handler for a packet type.

        Args:
            pkt_type: Packet type number

        Returns:
            Handler instance if registered, None otherwise
        """
        return self._handlers.get(pkt_type)

    def has_handler(self, pkt_type: int) -> bool:
        """Check if a handler is registered for a packet type.

        Args:
            pkt_type: Packet type number

        Returns:
            True if handler is registered, False otherwise
        """
        return pkt_type in self._handlers

    def list_handlers(self) -> list[tuple[int, str]]:
        """List all registered handlers.

        Returns:
            List of (packet_type, handler_class_name) tuples
        """
        return [
            (pkt_type, handler.__class__.__name__)
            for pkt_type, handler in sorted(self._handlers.items())
        ]

    def __len__(self) -> int:
        """Return number of registered handlers."""
        return len(self._handlers)

    def __repr__(self) -> str:
        return f"HandlerRegistry({len(self)} handlers)"
