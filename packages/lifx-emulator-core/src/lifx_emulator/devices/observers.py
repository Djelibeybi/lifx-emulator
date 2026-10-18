"""Observer pattern for activity tracking and event notification.

This module implements the Observer pattern to decouple activity tracking
from the server core, following the Open/Closed Principle.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class PacketEvent:
    """Represents a packet transmission or reception event.

    Attributes:
        timestamp: Unix timestamp of the event
        direction: 'rx' for received, 'tx' for transmitted
        packet_type: Numeric packet type identifier
        packet_name: Human-readable packet name
        addr: Network address string (host:port)
        device: Device serial (for tx events) or None
        target: Target identifier (for rx events) or None
        payload_hex: Raw payload bytes as hex when the packet could not be
            fully decoded, or None for decoded packets
        decode_error: Why the payload could not be decoded ("unknown type"
            or the unpack error message), or None for decoded packets
    """

    timestamp: float
    direction: str  # 'rx' or 'tx'
    packet_type: int
    packet_name: str
    addr: str
    device: str | None = None  # Device serial for tx events
    target: str | None = None  # Target for rx events
    payload_hex: str | None = None  # Raw payload for undecodable rx events
    decode_error: str | None = None  # Reason the payload was not decoded

    def undecodable_fields(self) -> dict[str, str]:
        """Return the payload hex and reason when the packet was not decoded.

        Returns:
            Dict with ``payload_hex`` and ``decode_error`` keys when both are
            set, otherwise an empty dict so decoded events stay compact
        """
        if self.payload_hex is None or self.decode_error is None:
            return {}
        return {"payload_hex": self.payload_hex, "decode_error": self.decode_error}


class ActivityObserver(Protocol):
    """Protocol for observers that track packet activity.

    Observers implementing this protocol can be attached to the server
    to receive notifications of packet events.
    """

    def on_packet_received(self, event: PacketEvent) -> None:
        """Called when a packet is received.

        Args:
            event: PacketEvent with direction='rx'
        """
        ...

    def on_packet_sent(self, event: PacketEvent) -> None:
        """Called when a packet is sent.

        Args:
            event: PacketEvent with direction='tx'
        """
        ...


class ActivityLogger:
    """Observer that logs recent packet activity.

    Maintains a rolling buffer of recent packet events for monitoring
    and debugging purposes.
    """

    def __init__(self, max_events: int = 100):
        """Initialize activity logger.

        Args:
            max_events: Maximum number of events to retain
        """
        self.recent_activity: deque[dict[str, Any]] = deque(maxlen=max_events)

    def on_packet_received(self, event: PacketEvent) -> None:
        """Record a received packet event.

        Args:
            event: PacketEvent with direction='rx'
        """
        self.recent_activity.append(
            {
                "timestamp": event.timestamp,
                "direction": "rx",
                "packet_type": event.packet_type,
                "packet_name": event.packet_name,
                "target": event.target,
                "addr": event.addr,
                **event.undecodable_fields(),
            }
        )

    def on_packet_sent(self, event: PacketEvent) -> None:
        """Record a sent packet event.

        Args:
            event: PacketEvent with direction='tx'
        """
        self.recent_activity.append(
            {
                "timestamp": event.timestamp,
                "direction": "tx",
                "packet_type": event.packet_type,
                "packet_name": event.packet_name,
                "device": event.device,
                "addr": event.addr,
            }
        )

    def get_recent_activity(self) -> list[dict[str, Any]]:
        """Get list of recent activity events.

        Returns:
            List of activity event dictionaries
        """
        return list(self.recent_activity)


class NullObserver:
    """No-op observer for when activity tracking is disabled.

    Allows code to unconditionally call notify without checking for None.
    """

    def on_packet_received(self, event: PacketEvent) -> None:
        """No-op packet received handler.

        Args:
            event: PacketEvent (ignored)
        """
        pass

    def on_packet_sent(self, event: PacketEvent) -> None:
        """No-op packet sent handler.

        Args:
            event: PacketEvent (ignored)
        """
        pass
