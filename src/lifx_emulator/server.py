"""UDP server that emulates LIFX devices."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

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
from lifx_emulator.protocol.packets import get_packet_class
from lifx_emulator.repositories import IScenarioStorageBackend
from lifx_emulator.scenarios import HierarchicalScenarioManager

logger = logging.getLogger(__name__)


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
    ):
        # Device manager (required dependency injection)
        self._device_manager = device_manager
        self.bind_address = bind_address
        self.port = port
        self.transport = None
        self.storage = storage

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
            self._device_manager.add_device(device, self.scenario_manager)

        # Activity observer - defaults to ActivityLogger if track_activity=True
        if activity_observer is not None:
            self.activity_observer = activity_observer
        elif track_activity:
            self.activity_observer = ActivityLogger(max_events=100)
        else:
            self.activity_observer = NullObserver()

        # Statistics tracking
        self.start_time = time.time()
        self.packets_received = 0
        self.packets_sent = 0
        self.packets_received_by_type: dict[int, int] = defaultdict(int)
        self.packets_sent_by_type: dict[int, int] = defaultdict(int)
        self.error_count = 0

    class LifxProtocol(asyncio.DatagramProtocol):
        def __init__(self, server):
            self.server = server
            self.loop = None

        def connection_made(self, transport):
            self.transport = transport
            self.server.transport = transport
            # Cache event loop reference for optimized task scheduling
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop yet (happens in tests or edge cases)
                self.loop = None
            logger.info(
                "LIFX emulated server listening on %s:%s",
                self.server.bind_address,
                self.server.port,
            )

        def datagram_received(self, data, addr):
            # Use direct loop scheduling for lower task creation overhead
            # This is faster than asyncio.create_task() for high-frequency packets
            if self.loop:
                self.loop.call_soon(
                    self.loop.create_task, self.server.handle_packet(data, addr)
                )
            else:
                # Fallback for edge case where loop not yet cached
                asyncio.create_task(self.server.handle_packet(data, addr))

    async def _process_device_packet(
        self,
        device: EmulatedLifxDevice,
        header: LifxHeader,
        packet: Any | None,
        addr: tuple[str, int],
    ):
        """Process packet for a single device and send responses.

        Args:
            device: The device to process the packet
            header: Parsed LIFX header
            packet: Parsed packet payload (or None)
            addr: Client address (host, port)
        """
        responses = device.process_packet(header, packet)

        # Get resolved scenario for response delays
        scenario = device._get_resolved_scenario()

        # Send responses with delay if configured
        for resp_header, resp_packet in responses:
            delay = scenario.response_delays.get(resp_header.pkt_type, 0.0)
            if delay > 0:
                await asyncio.sleep(delay)

            # Pack the response packet
            resp_payload = resp_packet.pack() if resp_packet else b""
            response_data = resp_header.pack() + resp_payload
            if self.transport:
                self.transport.sendto(response_data, addr)

            # Update statistics
            self.packets_sent += 1
            self.packets_sent_by_type[resp_header.pkt_type] += 1

            # Log sent packet with details
            resp_packet_name = _get_packet_type_name(resp_header.pkt_type)
            resp_fields_str = _format_packet_fields(resp_packet)
            logger.debug(
                "→ TX %s to %s:%s (device=%s, seq=%s) [%s]",
                resp_packet_name,
                addr[0],
                addr[1],
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
                    addr=f"{addr[0]}:{addr[1]}",
                    device=device.state.serial,
                )
            )

    async def handle_packet(self, data: bytes, addr: tuple[str, int]):
        """Handle incoming UDP packet"""
        try:
            # Update statistics
            self.packets_received += 1

            if len(data) < LIFX_HEADER_SIZE:
                logger.warning("Packet too short: %s bytes from %s", len(data), addr)
                self.error_count += 1
                return

            # Parse header
            header = LifxHeader.unpack(data)
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
                            "Failed to unpack %s (type %s) from %s:%s: %s",
                            _get_packet_type_name(header.pkt_type),
                            header.pkt_type,
                            addr[0],
                            addr[1],
                            e,
                        )
                        logger.debug(
                            "Raw payload (%s bytes): %s", len(payload), payload.hex()
                        )
                        return
                # else: packet_class exists but no payload (valid for some packet types)
            else:
                # Unknown packet type - log it with raw payload
                target_str = "broadcast" if header.tagged else header.target.hex()
                logger.warning(
                    "← RX Unknown packet type %s from %s:%s (target=%s, seq=%s)",
                    header.pkt_type,
                    addr[0],
                    addr[1],
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
            target_str = "broadcast" if header.tagged else header.target.hex()
            fields_str = _format_packet_fields(packet)
            logger.debug(
                "← RX %s from %s:%s (target=%s, seq=%s) [%s]",
                packet_name,
                addr[0],
                addr[1],
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
                    addr=f"{addr[0]}:{addr[1]}",
                    target=target_str,
                )
            )

            # Determine target devices using device manager
            target_devices = self._device_manager.resolve_target_devices(header)

            # Process packet for each target device
            # Use parallel processing for broadcasts to improve scalability
            if len(target_devices) > 1:
                # Broadcast: process all devices concurrently (limited by GIL)
                tasks = [
                    self._process_device_packet(device, header, packet, addr)
                    for device in target_devices
                ]
                await asyncio.gather(*tasks)
            elif target_devices:
                # Single device: process directly without task overhead
                await self._process_device_packet(
                    target_devices[0], header, packet, addr
                )

        except Exception as e:
            self.error_count += 1
            logger.error("Error handling packet from %s: %s", addr, e, exc_info=True)

    def add_device(self, device: EmulatedLifxDevice) -> bool:
        """Add a device to the server.

        Args:
            device: The device to add

        Returns:
            True if added, False if device with same serial already exists
        """
        return self._device_manager.add_device(device, self.scenario_manager)

    def remove_device(self, serial: str) -> bool:
        """Remove a device from the server.

        Args:
            serial: Serial number of device to remove (12 hex chars)

        Returns:
            True if removed, False if device not found
        """
        return self._device_manager.remove_device(serial, self.storage)

    def remove_all_devices(self, delete_storage: bool = False) -> int:
        """Remove all devices from the server.

        Args:
            delete_storage: If True, also delete persistent storage files

        Returns:
            Number of devices removed
        """
        return self._device_manager.remove_all_devices(delete_storage, self.storage)

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
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "start_time": self.start_time,
            "device_count": self._device_manager.count_devices(),
            "packets_received": self.packets_received,
            "packets_sent": self.packets_sent,
            "packets_received_by_type": dict(self.packets_received_by_type),
            "packets_sent_by_type": dict(self.packets_sent_by_type),
            "error_count": self.error_count,
            "activity_enabled": isinstance(self.activity_observer, ActivityLogger),
        }

    def get_recent_activity(self) -> list[dict[str, Any]]:
        """Get recent activity events.

        Returns:
            List of activity event dictionaries, or empty list if observer
            doesn't support activity tracking
        """
        if isinstance(self.activity_observer, ActivityLogger):
            return self.activity_observer.get_recent_activity()
        return []

    async def start(self):
        """Start the server"""
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self.LifxProtocol(self), local_addr=(self.bind_address, self.port)
        )

    async def stop(self):
        """Stop the server"""
        if self.transport:
            self.transport.close()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        return False
