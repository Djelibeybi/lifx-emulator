"""UDP server that emulates LIFX devices."""

from __future__ import annotations

import asyncio
import errno
import logging
import socket
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.constants import LIFX_HEADER_SIZE, LIFX_UDP_PORT
from lifx_emulator.devices import (
    ActivityLogger,
    ActivityObserver,
    EmulatedLifxDevice,
    IDeviceManager,
    NullObserver,
    PacketEvent,
)
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, get_packet_class
from lifx_emulator.repositories import IScenarioStorageBackend
from lifx_emulator.scenarios import HierarchicalScenarioManager

logger = logging.getLogger(__name__)

PeerAddress = tuple[str, int] | tuple[str, int, int, int]
_DUAL_BIND_ATTEMPTS = 5
_TRACKED_TASK_DRAIN_TIMEOUT = 5.0
_ENDPOINT_CLOSE_TIMEOUT = 1.0


@dataclass(frozen=True)
class _DatagramContext:
    """Immutable identity of the endpoint that received one datagram."""

    family: socket.AddressFamily
    peer: PeerAddress
    transport: asyncio.DatagramTransport | None


def _get_packet_type_name(pkt_type: int) -> str:
    """Get human-readable name for packet type.

    Args:
        pkt_type: Packet type number

    Returns:
        Packet class name or "Unknown"
    """
    packet_class = get_packet_class(pkt_type)
    if packet_class:
        return packet_class.__qualname__  # e.g., "Device.GetService"
    return f"Unknown({pkt_type})"


def _format_packet_fields(packet: Any) -> str:
    """Format packet fields for logging, excluding reserved fields.

    Args:
        packet: Packet instance to format

    Returns:
        Formatted string with field names and values
    """
    if packet is None:
        return "no payload"

    # Same root cause as _pack_payload: _apply_error_scenarios() returns an
    # already-packed bytes payload for malformed/invalid-field replies, so
    # this logging helper must not assume a packet object either.
    if isinstance(packet, bytes):
        return f"<{len(packet)} raw bytes>"

    fields = []
    for field_item in packet._fields:
        # Skip reserved fields (no name)
        if "name" not in field_item:
            continue

        # Get field value
        field_name = packet._protocol_to_python_name(field_item["name"])
        value = getattr(packet, field_name, None)

        # Format value based on type
        if isinstance(value, bytes):
            # For bytes, show hex if short, or length if long
            if len(value) <= 8:
                value_str = value.hex()
            else:
                value_str = f"<{len(value)} bytes>"
        elif isinstance(value, list):
            # For lists, show count and sample
            if len(value) <= 3:
                value_str = str(value)
            else:
                value_str = f"[{len(value)} items]"
        elif hasattr(value, "__dict__"):
            # For nested objects, show their string representation
            value_str = str(value)
        else:
            value_str = str(value)

        fields.append(f"{field_name}={value_str}")

    return ", ".join(fields) if fields else "no fields"


def _pack_payload(resp_packet: Any) -> bytes:
    """Pack a response payload, tolerating an already-packed bytes value.

    ``EmulatedLifxDevice._apply_error_scenarios()`` returns the payload
    already packed as ``bytes`` for ``malformed_packets`` and
    ``invalid_field_values`` replies (it truncates or corrupts the packed
    bytes directly rather than the packet object), so calling ``.pack()``
    again would raise ``AttributeError`` before anything reaches the wire.

    Args:
        resp_packet: A packet object, raw bytes from an error scenario, or
            a falsy value (None or empty bytes) for an empty payload.

    Returns:
        The payload bytes ready to concatenate after the packed header.
    """
    if not resp_packet:
        return b""
    if isinstance(resp_packet, bytes):
        return resp_packet
    return resp_packet.pack()


def _format_target(header: LifxHeader) -> str:
    """Render a packet target as broadcast or an exact six-byte serial."""
    if header.tagged or header.target == b"\x00" * 8:
        return "broadcast"
    return header.target[:6].hex()


def _format_peer(context: _DatagramContext) -> str:
    """Format a peer using its explicit address family."""
    host, port = context.peer[:2]
    if context.family == socket.AF_INET6:
        return f"[{host}]:{port}"
    return f"{host}:{port}"


class EmulatedLifxServer:
    """UDP server that simulates LIFX devices"""

    def __init__(
        self,
        devices: list[EmulatedLifxDevice],
        device_manager: IDeviceManager,
        bind_address: str = "127.0.0.1",
        port: int = LIFX_UDP_PORT,
        track_activity: bool = True,
        storage=None,
        activity_observer: ActivityObserver | None = None,
        scenario_manager: HierarchicalScenarioManager | None = None,
        persist_scenarios: bool = False,
        scenario_storage: IScenarioStorageBackend | None = None,
        *,
        ipv6_bind_address: str = "::1",
        max_pending_packets: int = 1024,
    ):
        # Device manager (required dependency injection)
        self._device_manager = device_manager
        self.bind_address = bind_address
        self.ipv6_bind_address = ipv6_bind_address
        self.port = port
        self.transport: asyncio.DatagramTransport | None = None
        self._ipv4_transport: asyncio.DatagramTransport | None = None
        self._ipv6_transport: asyncio.DatagramTransport | None = None
        self._ipv4_protocol: EmulatedLifxServer.LifxProtocol | None = None
        self._ipv6_protocol: EmulatedLifxServer.LifxProtocol | None = None
        self._ipv4_endpoint: tuple[str, int] | None = None
        self._ipv6_endpoint: tuple[str, int] | None = None
        self._effective_port: int | None = None
        self.storage = storage
        self._max_pending_packets = max_pending_packets
        self._packet_generation = 0
        self._background_tasks = BackgroundTaskTracker(
            "server-generation-0", max_pending=max_pending_packets
        )
        self._retired_background_tasks: set[BackgroundTaskTracker] = set()
        self._lifecycle_lock = asyncio.Lock()
        self._endpoint_loss_tasks: set[asyncio.Task[None]] = set()

        # Scenario storage backend (optional - only needed for persistence)
        self.scenario_persistence: IScenarioStorageBackend | None = None
        if persist_scenarios:
            if scenario_storage is None:
                raise ValueError(
                    "scenario_storage is required when persist_scenarios=True"
                )
            if scenario_manager is None:
                raise ValueError(
                    "scenario_manager is required when persist_scenarios=True "
                    "(must be pre-loaded from storage before server initialization)"
                )
            self.scenario_persistence = scenario_storage

        # Scenario manager (shared across all devices for runtime updates)
        self.scenario_manager = scenario_manager or HierarchicalScenarioManager()

        # Add initial devices to the device manager
        for device in devices:
            # Update device port to match server port
            device.state.port = self.port
            if not self._device_manager.add_device(device, self.scenario_manager):
                device.reject_admission()
                logger.warning(
                    "Rejected initial device with duplicate serial: %s",
                    device.state.serial,
                )

        # Activity observer - defaults to ActivityLogger if track_activity=True
        if activity_observer is not None:
            self.activity_observer = activity_observer
        elif track_activity:
            self.activity_observer = ActivityLogger(max_events=100)
        else:
            self.activity_observer = NullObserver()

        # Statistics tracking
        self.start_time = time.time()
        self._started_monotonic = time.monotonic()
        self.packets_received = 0
        self.packets_sent = 0
        self.packets_received_by_type: dict[int, int] = defaultdict(int)
        self.packets_sent_by_type: dict[int, int] = defaultdict(int)
        self.error_count = 0
        self.packets_dropped_overload = 0
        self.websocket_events_dropped = 0

    class LifxProtocol(asyncio.DatagramProtocol):
        def __init__(
            self,
            server: EmulatedLifxServer,
            family: socket.AddressFamily = socket.AF_INET,
            accepting: bool = True,
        ) -> None:
            self.server = server
            self.family = family
            self._accepting = accepting
            self._background_tasks = server._background_tasks
            self.loop = None
            self.transport: asyncio.DatagramTransport | None = None
            self.closed = asyncio.Event()
            self._expected_close = False

        def start_accepting(self) -> None:
            """Admit new datagrams after the endpoint pair is committed."""
            self._accepting = True

        def stop_accepting(self) -> None:
            """Reject new datagrams without affecting already scheduled work."""
            self._accepting = False

        def connection_made(self, transport):
            self.transport = transport
            # Cache event loop reference for optimized task scheduling
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop yet (happens in tests or edge cases)
                self.loop = None
            logger.info("LIFX emulated server protocol connected")

        def datagram_received(self, data, addr):
            if not self._accepting:
                logger.debug(
                    "Ignoring datagram on inactive %s endpoint from %s",
                    self.family.name,
                    addr,
                )
                return
            if not self._background_tasks.has_capacity:
                self.server.packets_dropped_overload += 1
                logger.warning(
                    "Dropping datagram on %s endpoint from %s: "
                    "pending packet limit reached",
                    self.family.name,
                    addr,
                )
                return
            context = _DatagramContext(self.family, addr, self.transport)
            operation = f"packet:{_format_peer(context)}"
            self._background_tasks.schedule(
                self.server.handle_packet(data, context), operation
            )

        def connection_lost(self, exc):
            """Publish transport closure for lifecycle coordination."""
            self.transport = None
            self.closed.set()
            if exc is not None:
                logger.warning("LIFX datagram endpoint closed with error: %s", exc)
            if not self._expected_close:
                self.server._schedule_endpoint_loss(self)

    def _coerce_datagram_context(
        self,
        context_or_addr: _DatagramContext | PeerAddress,
        *,
        family: socket.AddressFamily = socket.AF_INET,
        transport: asyncio.DatagramTransport | None = None,
    ) -> _DatagramContext:
        """Adapt a legacy address once without downstream transport reselection."""
        if isinstance(context_or_addr, _DatagramContext):
            return context_or_addr
        resolved_transport = self.transport if transport is None else transport
        return _DatagramContext(family, context_or_addr, resolved_transport)

    def _unpack_header(self, data: bytes, peer_text: str) -> LifxHeader | None:
        """Validate and unpack a header with the established counter outcomes."""
        if len(data) < LIFX_HEADER_SIZE:
            self.packets_received += 1
            self.error_count += 1
            logger.warning("Packet too short: %s bytes from %s", len(data), peer_text)
            return None

        try:
            header = LifxHeader.unpack(data)
        except Exception as error:
            self.packets_received += 1
            self.error_count += 1
            logger.error(
                "Error handling packet from %s: %s",
                peer_text,
                error,
                exc_info=True,
            )
            return None

        if header.size < LIFX_HEADER_SIZE or header.size != len(data):
            self.packets_received += 1
            self.error_count += 1
            logger.warning(
                "Invalid declared packet size %s for %s-byte datagram from %s",
                header.size,
                len(data),
                peer_text,
            )
            return None
        return header

    def _send_ack(
        self,
        device: EmulatedLifxDevice,
        header: LifxHeader,
        context_or_addr: _DatagramContext | PeerAddress,
        *,
        family: socket.AddressFamily = socket.AF_INET,
        transport: asyncio.DatagramTransport | None = None,
    ) -> None:
        """Send an acknowledgment packet immediately via UDP.

        Args:
            device: The device acknowledging the packet
            header: Request header (source/sequence are copied)
            context_or_addr: Datagram context or legacy client address
            family: Address family for a legacy client address
            transport: Explicit receiving transport for a legacy client address
        """
        context = self._coerce_datagram_context(
            context_or_addr,
            family=family,
            transport=transport,
        )
        if context.transport is None:
            logger.warning(
                "Cannot send acknowledgement to %s: no datagram transport",
                _format_peer(context),
            )
            return
        ack_packet = Device.Acknowledgement()
        ack_payload = ack_packet.pack()
        ack_header = device._create_response_header(
            header.source,
            header.sequence,
            ack_packet.PKT_TYPE,
            len(ack_payload),
        )
        response_data = ack_header.pack() + ack_payload
        context.transport.sendto(response_data, context.peer)

        self.packets_sent += 1
        self.packets_sent_by_type[ack_header.pkt_type] += 1

        logger.debug(
            "→ TX %s to %s (target=%s, seq=%s) [no fields]",
            _get_packet_type_name(ack_header.pkt_type),
            _format_peer(context),
            device.state.serial,
            ack_header.sequence,
        )

        self.activity_observer.on_packet_sent(
            PacketEvent(
                timestamp=time.time(),
                direction="tx",
                packet_type=ack_header.pkt_type,
                packet_name=_get_packet_type_name(ack_header.pkt_type),
                addr=_format_peer(context),
                device=device.state.serial,
            )
        )

    async def _process_device_packet(
        self,
        device: EmulatedLifxDevice,
        header: LifxHeader,
        packet: Any | None,
        context_or_addr: _DatagramContext | PeerAddress,
        *,
        family: socket.AddressFamily = socket.AF_INET,
        transport: asyncio.DatagramTransport | None = None,
    ):
        """Process packet for a single device and send responses.

        Args:
            device: The device to process the packet
            header: Parsed LIFX header
            packet: Parsed packet payload (or None)
            context_or_addr: Datagram context or legacy client address
            family: Address family for a legacy client address
            transport: Explicit receiving transport for a legacy client address
        """
        context = self._coerce_datagram_context(
            context_or_addr,
            family=family,
            transport=transport,
        )
        # Check if packet should be dropped BEFORE sending any ack.
        # This must happen first so that drop_packets suppresses all
        # responses including acknowledgements.
        scenario = device._get_resolved_scenario()
        if not device.scenario_manager.should_respond(header.pkt_type, scenario):
            logger.info("Dropping packet type %s per scenario", header.pkt_type)
            return

        # Fast-path ack: send before device processing when no scenario
        # modifies the ack itself (e.g. delays or malforms type 45). When
        # a scenario does target acks, process_packet() generates them so
        # the scenario pipeline can apply its effects.
        # Skip for packets the device can't handle — those get a
        # StateUnhandled response instead.
        if (
            header.ack_required
            and not scenario.affects_acks
            and device._should_handle_packet(header.pkt_type)
        ):
            self._send_ack(device, header, context)

        responses = device.process_packet(
            header,
            packet,
            scenario=scenario,
            should_respond=True,
        )

        # Send responses with delay if configured
        for resp_header, resp_packet in responses:
            delay = scenario.response_delays.get(resp_header.pkt_type, 0.0)
            if delay > 0:
                await asyncio.sleep(delay)

            # Pack the response packet (bytes-aware: see _pack_payload)
            resp_payload = _pack_payload(resp_packet)
            response_data = resp_header.pack() + resp_payload
            if context.transport is None:
                logger.warning(
                    "Cannot send packet type %s to %s: no datagram transport",
                    resp_header.pkt_type,
                    _format_peer(context),
                )
                continue
            context.transport.sendto(response_data, context.peer)

            # Update statistics
            self.packets_sent += 1
            self.packets_sent_by_type[resp_header.pkt_type] += 1

            # Log sent packet with details
            resp_packet_name = _get_packet_type_name(resp_header.pkt_type)
            resp_fields_str = _format_packet_fields(resp_packet)
            logger.debug(
                "→ TX %s to %s (target=%s, seq=%s) [%s]",
                resp_packet_name,
                _format_peer(context),
                device.state.serial,
                resp_header.sequence,
                resp_fields_str,
            )

            # Notify observer
            self.activity_observer.on_packet_sent(
                PacketEvent(
                    timestamp=time.time(),
                    direction="tx",
                    packet_type=resp_header.pkt_type,
                    packet_name=resp_packet_name,
                    addr=_format_peer(context),
                    device=device.state.serial,
                )
            )

    async def handle_packet(
        self,
        data: bytes,
        context_or_addr: _DatagramContext | PeerAddress,
        *,
        family: socket.AddressFamily = socket.AF_INET,
        transport: asyncio.DatagramTransport | None = None,
    ):
        """Handle incoming UDP packet"""
        context = self._coerce_datagram_context(
            context_or_addr,
            family=family,
            transport=transport,
        )
        peer_text = _format_peer(context)
        try:
            header = self._unpack_header(data, peer_text)
            if header is None:
                return

            # Reject ineligible devices before any observable receive effect.
            target_devices = self._device_manager.resolve_target_devices(
                header, context.family
            )
            if not target_devices:
                return

            self.packets_received += 1
            payload = (
                data[LIFX_HEADER_SIZE : header.size]
                if header.size > LIFX_HEADER_SIZE
                else b""
            )

            # Unpack payload into packet object
            packet = None
            packet_class = get_packet_class(header.pkt_type)

            # Update packet type statistics
            self.packets_received_by_type[header.pkt_type] += 1

            if packet_class:
                if payload:
                    try:
                        packet = packet_class.unpack(payload)
                    except Exception as e:
                        logger.warning(
                            "Failed to unpack %s (type %s) from %s: %s",
                            _get_packet_type_name(header.pkt_type),
                            header.pkt_type,
                            peer_text,
                            e,
                        )
                        logger.debug(
                            "Raw payload (%s bytes): %s", len(payload), payload.hex()
                        )
                        return
                # else: packet_class exists but no payload (valid for some packet types)
            else:
                # Unknown packet type - log it with raw payload
                target_str = _format_target(header)
                logger.warning(
                    "← RX Unknown packet type %s from %s (target=%s, seq=%s)",
                    header.pkt_type,
                    peer_text,
                    target_str,
                    header.sequence,
                )
                if payload:
                    logger.info(
                        "Unknown packet payload (%s bytes): %s",
                        len(payload),
                        payload.hex(),
                    )
                # Continue processing - device might still want to respond or log it

            # Log received packet with details
            packet_name = _get_packet_type_name(header.pkt_type)
            target_str = _format_target(header)
            fields_str = _format_packet_fields(packet)
            logger.debug(
                "← RX %s from %s (target=%s, seq=%s) [%s]",
                packet_name,
                peer_text,
                target_str,
                header.sequence,
                fields_str,
            )

            # Notify observer
            self.activity_observer.on_packet_received(
                PacketEvent(
                    timestamp=time.time(),
                    direction="rx",
                    packet_type=header.pkt_type,
                    packet_name=packet_name,
                    addr=peer_text,
                    target=target_str,
                )
            )

            # Process packet for each target device
            # Use parallel processing for broadcasts to improve scalability
            if len(target_devices) > 1:
                # Broadcast: process all devices concurrently (limited by GIL)
                tasks = [
                    self._process_device_packet(device, header, packet, context)
                    for device in target_devices
                ]
                await asyncio.gather(*tasks)
            elif target_devices:
                # Single device: process directly without task overhead
                await self._process_device_packet(
                    target_devices[0], header, packet, context
                )

        except Exception as e:
            self.error_count += 1
            logger.error(
                "Error handling packet from %s: %s", peer_text, e, exc_info=True
            )

    def add_device(self, device: EmulatedLifxDevice) -> bool:
        """Add a device to the server.

        Args:
            device: The device to add

        Returns:
            True if added, False if device with same serial already exists
        """
        # A live port-zero server advertises the committed endpoint, while an
        # inactive server retains the historical configured-port behaviour.
        device.state.port = self._effective_port or self.port
        return self._device_manager.add_device(device, self.scenario_manager)

    async def remove_device(self, serial: str) -> bool:
        """Remove a device from the server.

        Args:
            serial: Serial number of device to remove (12 hex chars)

        Returns:
            True if removed, False if device not found
        """
        return await self._device_manager.remove_device(serial, self.storage)

    async def remove_all_devices(self, delete_storage: bool = False) -> int:
        """Remove all devices from the server.

        Args:
            delete_storage: If True, also delete persistent storage files

        Returns:
            Number of devices removed
        """
        return await self._device_manager.remove_all_devices(
            delete_storage, self.storage
        )

    def get_device(self, serial: str) -> EmulatedLifxDevice | None:
        """Get a device by serial number.

        Args:
            serial: Serial number (12 hex chars)

        Returns:
            Device if found, None otherwise
        """
        return self._device_manager.get_device(serial)

    def get_all_devices(self) -> list[EmulatedLifxDevice]:
        """Get all devices.

        Returns:
            List of all devices
        """
        return self._device_manager.get_all_devices()

    def invalidate_all_scenario_caches(self) -> None:
        """Invalidate scenario cache for all devices.

        This should be called when scenario configuration changes to ensure
        devices reload their scenario settings from the scenario manager.
        """
        self._device_manager.invalidate_all_scenario_caches()

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics.

        Returns:
            Dictionary with statistics
        """
        uptime = time.monotonic() - self._started_monotonic
        return {
            "uptime_seconds": uptime,
            "start_time": self.start_time,
            "device_count": self._device_manager.count_devices(),
            "packets_received": self.packets_received,
            "packets_sent": self.packets_sent,
            "packets_received_by_type": dict(self.packets_received_by_type),
            "packets_sent_by_type": dict(self.packets_sent_by_type),
            "error_count": self.error_count,
            "packets_dropped_overload": self.packets_dropped_overload,
            "websocket_events_dropped": self.websocket_events_dropped,
            "activity_enabled": hasattr(self.activity_observer, "get_recent_activity"),
        }

    def get_recent_activity(self) -> list[dict[str, Any]]:
        """Get recent activity events.

        Returns:
            List of activity event dictionaries, or empty list if observer
            doesn't support activity tracking
        """
        get_activity = getattr(self.activity_observer, "get_recent_activity", None)
        if get_activity is not None:
            return get_activity()
        return []

    @property
    def ipv4_endpoint(self) -> tuple[str, int] | None:
        """Return the committed IPv4 endpoint, if the complete pair is live."""
        return self._ipv4_endpoint if self._has_complete_endpoint_pair() else None

    @property
    def ipv6_endpoint(self) -> tuple[str, int] | None:
        """Return the committed IPv6 endpoint, if the complete pair is live."""
        return self._ipv6_endpoint if self._has_complete_endpoint_pair() else None

    def _has_complete_endpoint_pair(self) -> bool:
        """Return whether all private and compatibility endpoint state is live."""
        ipv4_protocol = self._ipv4_protocol
        ipv6_protocol = self._ipv6_protocol
        return bool(
            self.transport is not None
            and self.transport is self._ipv4_transport
            and self._transport_is_open(self._ipv4_transport)
            and self._transport_is_open(self._ipv6_transport)
            and ipv4_protocol is not None
            and ipv4_protocol.transport is self._ipv4_transport
            and not ipv4_protocol.closed.is_set()
            and ipv6_protocol is not None
            and ipv6_protocol.transport is self._ipv6_transport
            and not ipv6_protocol.closed.is_set()
            and self._ipv4_endpoint is not None
            and self._ipv6_endpoint is not None
            and self._effective_port is not None
        )

    @staticmethod
    def _transport_is_open(transport: asyncio.DatagramTransport | None) -> bool:
        """Return whether a transport exists and is not closing."""
        if transport is None:
            return False
        is_closing = getattr(transport, "is_closing", None)
        return is_closing is None or not is_closing()

    def _schedule_endpoint_loss(self, protocol: LifxProtocol) -> None:
        """Schedule pair invalidation after one committed endpoint is lost."""
        task = asyncio.get_running_loop().create_task(
            self._handle_endpoint_loss(protocol)
        )
        self._endpoint_loss_tasks.add(task)
        task.add_done_callback(self._on_endpoint_loss_done)

    def _on_endpoint_loss_done(self, task: asyncio.Task[None]) -> None:
        """Consume endpoint-loss task outcomes and release their references."""
        self._endpoint_loss_tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Endpoint-loss cleanup failed: %s",
                error,
                exc_info=(type(error), error, error.__traceback__),
            )

    async def _handle_endpoint_loss(self, failed_protocol: LifxProtocol) -> None:
        """Invalidate both endpoints when a committed family closes unexpectedly."""
        async with self._lifecycle_lock:
            if failed_protocol not in (self._ipv4_protocol, self._ipv6_protocol):
                return
            logger.warning(
                "%s endpoint was lost unexpectedly; invalidating endpoint pair",
                failed_protocol.family.name,
            )
            await self._discard_existing_endpoints()

    @staticmethod
    def _endpoint_from_transport(
        transport: asyncio.DatagramTransport,
    ) -> tuple[str, int]:
        """Normalise the host and port from an asyncio transport sockname."""
        sockname = transport.get_extra_info("sockname")
        if not isinstance(sockname, tuple) or len(sockname) < 2:
            raise RuntimeError("Datagram transport did not expose a socket endpoint")
        return str(sockname[0]), int(sockname[1])

    def _reset_endpoint_state(self) -> None:
        """Clear all public and private live endpoint state."""
        self.transport = None
        self._ipv4_transport = None
        self._ipv6_transport = None
        self._ipv4_protocol = None
        self._ipv6_protocol = None
        self._ipv4_endpoint = None
        self._ipv6_endpoint = None
        self._effective_port = None

    @staticmethod
    def _close_unique_transports(*transports: object) -> None:
        """Close each transport-like object at most once."""
        closed_ids: set[int] = set()
        for transport in transports:
            if transport is None or id(transport) in closed_ids:
                continue
            closed_ids.add(id(transport))
            close = getattr(transport, "close", None)
            if close is not None:
                close()

    async def _discard_existing_endpoints(self) -> None:
        """Close stale or partial endpoint state before a fresh start."""
        protocols = (
            getattr(self, "_ipv4_protocol", None),
            getattr(self, "_ipv6_protocol", None),
        )
        for protocol in protocols:
            if protocol is not None:
                protocol._expected_close = True
                protocol.stop_accepting()
        self._close_unique_transports(
            getattr(self, "transport", None),
            getattr(self, "_ipv4_transport", None),
            getattr(self, "_ipv6_transport", None),
        )
        self._reset_endpoint_state()
        await asyncio.sleep(0)

    def _prepare_packet_generation(self) -> None:
        """Use a fresh packet tracker when an earlier generation is still active."""
        tracker = self._background_tasks
        tracker.stop_accepting()
        if tracker.pending_count == 0:
            return

        self._retired_background_tasks.add(tracker)
        self._packet_generation += 1
        self._background_tasks = BackgroundTaskTracker(
            f"server-generation-{self._packet_generation}",
            accepting=False,
            max_pending=self._max_pending_packets,
        )

    async def start(self):
        """Atomically bind and publish one IPv4/IPv6 endpoint pair."""
        async with self._lifecycle_lock:
            await self._start_locked()

    async def _start_locked(self) -> None:
        """Start one endpoint pair while holding the lifecycle lock."""
        if self._has_complete_endpoint_pair():
            logger.debug("LIFX emulated server endpoint pair is already running")
            return

        await self._discard_existing_endpoints()
        self._prepare_packet_generation()
        loop = asyncio.get_running_loop()

        attempt = 0
        while True:
            attempt += 1
            ipv4_transport: asyncio.DatagramTransport | None = None
            ipv6_transport: asyncio.DatagramTransport | None = None
            ipv6_socket: socket.socket | None = None
            ipv4_protocol = self.LifxProtocol(self, socket.AF_INET, accepting=False)
            ipv6_protocol = self.LifxProtocol(self, socket.AF_INET6, accepting=False)
            previous_ports: list[tuple[EmulatedLifxDevice, int]] = []
            tracker_reopened = False
            committed = False
            try:
                ipv4_transport, _ = await loop.create_datagram_endpoint(
                    lambda: ipv4_protocol,
                    local_addr=(self.bind_address, self.port),
                    family=socket.AF_INET,
                )
                ipv4_endpoint = self._endpoint_from_transport(ipv4_transport)

                ipv6_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                ipv6_socket.setblocking(False)
                ipv6_socket.setsockopt(
                    socket.IPPROTO_IPV6,
                    socket.IPV6_V6ONLY,
                    1,
                )
                ipv6_socket.bind((self.ipv6_bind_address, ipv4_endpoint[1]))
                ipv6_transport, _ = await loop.create_datagram_endpoint(
                    lambda: ipv6_protocol,
                    sock=ipv6_socket,
                )
                ipv6_socket = None
                ipv6_endpoint = self._endpoint_from_transport(ipv6_transport)

                effective_port = ipv4_endpoint[1]
                devices = self._device_manager.get_all_devices()
                previous_ports = [(device, device.state.port) for device in devices]
                for device in devices:
                    device.state.port = effective_port
                    device.reopen()
                self._background_tasks.start_accepting()
                tracker_reopened = True
                ipv4_protocol.start_accepting()
                ipv6_protocol.start_accepting()

                self._ipv4_transport = ipv4_transport
                self._ipv6_transport = ipv6_transport
                self._ipv4_protocol = ipv4_protocol
                self._ipv6_protocol = ipv6_protocol
                self._ipv4_endpoint = ipv4_endpoint
                self._ipv6_endpoint = (ipv6_endpoint[0], ipv6_endpoint[1])
                self._effective_port = effective_port
                self.transport = ipv4_transport
                committed = True
                return
            except BaseException as error:
                if ipv6_socket is not None:
                    ipv6_socket.close()
                ipv4_protocol.stop_accepting()
                ipv6_protocol.stop_accepting()
                if tracker_reopened:
                    self._background_tasks.stop_accepting()
                for device, previous_port in previous_ports:
                    device.state.port = previous_port
                self._close_unique_transports(ipv4_transport, ipv6_transport)
                self._reset_endpoint_state()
                await asyncio.sleep(0)

                retry_collision = (
                    self.port == 0
                    and ipv4_transport is not None
                    and isinstance(error, OSError)
                    and error.errno == errno.EADDRINUSE
                    and attempt < _DUAL_BIND_ATTEMPTS
                )
                if retry_collision:
                    logger.debug(
                        "IPv6 bind collision for %s on attempt %s/%s; retrying pair",
                        self.ipv6_bind_address,
                        attempt,
                        _DUAL_BIND_ATTEMPTS,
                    )
                    continue

                if ipv4_transport is None:
                    logger.error(
                        "IPv4 bind failed for %s: %s",
                        self.bind_address,
                        error,
                    )
                else:
                    logger.error(
                        "IPv6 bind failed for %s: %s",
                        self.ipv6_bind_address,
                        error,
                    )
                raise
            finally:
                if not committed:
                    if ipv6_socket is not None:
                        ipv6_socket.close()
                    self._close_unique_transports(ipv4_transport, ipv6_transport)

    async def stop(self):
        """Drain admitted work, then close and clear every known endpoint."""
        lifecycle_lock = getattr(self, "_lifecycle_lock", None)
        if lifecycle_lock is None:
            await self._stop_locked()
            return
        async with lifecycle_lock:
            await self._stop_locked()

    async def _stop_locked(self) -> None:
        """Stop the endpoint pair while holding the lifecycle lock."""
        protocols = (
            getattr(self, "_ipv4_protocol", None),
            getattr(self, "_ipv6_protocol", None),
        )
        for protocol in protocols:
            if protocol is not None:
                protocol._expected_close = True
                protocol.stop_accepting()

        tracker = getattr(self, "_background_tasks", None)
        retired_trackers = tuple(getattr(self, "_retired_background_tasks", set()))
        transports = (
            getattr(self, "transport", None),
            getattr(self, "_ipv4_transport", None),
            getattr(self, "_ipv6_transport", None),
        )
        transports_closed = False
        try:
            trackers = (*retired_trackers, *((tracker,) if tracker is not None else ()))
            if trackers:
                await asyncio.gather(
                    *(
                        packet_tracker.shutdown(timeout=_TRACKED_TASK_DRAIN_TIMEOUT)
                        for packet_tracker in trackers
                    )
                )
                self._retired_background_tasks.clear()

            manager = getattr(self, "_device_manager", None)
            if manager is not None:
                devices = manager.get_all_devices()
                await asyncio.gather(
                    *(device.close(_TRACKED_TASK_DRAIN_TIMEOUT) for device in devices)
                )

            self._close_unique_transports(*transports)
            transports_closed = True
            for name, protocol, transport in (
                ("IPv4", protocols[0], transports[1] or transports[0]),
                ("IPv6", protocols[1], transports[2]),
            ):
                if protocol is None or transport is None:
                    continue
                try:
                    await asyncio.wait_for(
                        protocol.closed.wait(),
                        timeout=_ENDPOINT_CLOSE_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timed out waiting for %s endpoint closure after %.1fs",
                        name,
                        _ENDPOINT_CLOSE_TIMEOUT,
                    )
        finally:
            if not transports_closed:
                self._close_unique_transports(*transports)
            self._reset_endpoint_state()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        return False
