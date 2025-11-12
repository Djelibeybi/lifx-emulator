"""Base classes for packet handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState


class PacketHandler(ABC):
    """Base class for all packet handlers.

    Each handler implements the logic for processing a specific packet type
    and optionally generating a response packet.

    Handlers are stateless and operate on the provided DeviceState.
    """

    # Subclasses must define the packet type they handle
    PKT_TYPE: int

    @abstractmethod
    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        """Handle the packet and return response packet(s).

        Args:
            device_state: Current device state to read/modify
            packet: Unpacked packet object (None for packets with no payload)
            res_required: Whether client requested a response (res_required
                         flag from header)

        Returns:
            List of response packets (empty list if no response needed).
            This unified return type simplifies packet processing logic.

        Notes:
            - Handlers should modify device_state directly for SET operations
            - Handlers should check device capabilities before processing
            - Return empty list [] if the device doesn't support this packet type
            - Always return a list, even for single responses: [packet]
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(PKT_TYPE={self.PKT_TYPE})"
