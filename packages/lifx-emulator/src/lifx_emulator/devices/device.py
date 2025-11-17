"""Device state and emulated device implementation."""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from typing import Any

from lifx_emulator.constants import LIFX_HEADER_SIZE
from lifx_emulator.devices.states import DeviceState
from lifx_emulator.handlers import HandlerRegistry, create_default_registry
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import (
    Device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.scenarios import (
    HierarchicalScenarioManager,
    ScenarioConfig,
    get_device_type,
)

logger = logging.getLogger(__name__)

# Forward declaration for type hinting
TYPE_CHECKING = False
if TYPE_CHECKING:
    from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile


class EmulatedLifxDevice:
    """Emulated LIFX device with configurable scenarios and state management."""

    def __init__(
        self,
        device_state: DeviceState,
        storage: DevicePersistenceAsyncFile | None = None,
        handler_registry: HandlerRegistry | None = None,
        scenario_manager: HierarchicalScenarioManager | None = None,
    ):
        self.state = device_state
        # Use provided scenario manager or create a default empty one
        if scenario_manager is not None:
            self.scenario_manager = scenario_manager
        else:
            self.scenario_manager = HierarchicalScenarioManager()
        self.start_time = time.time()
        self.storage = storage

        # Scenario caching for performance (HierarchicalScenarioManager only)
        self._cached_scenario: ScenarioConfig | None = None

        # Track background save tasks to prevent garbage collection
        self.background_save_tasks: set[asyncio.Task] = set()

        # Use provided registry or create default one
        self.handlers = handler_registry or create_default_registry()

        # Pre-allocate response header template for performance (10-15% gain)
        # This avoids creating a new LifxHeader object for every response
        self._response_header_template = LifxHeader(
            source=0,
            target=self.state.get_target_bytes(),
            sequence=0,
            tagged=False,
            pkt_type=0,
            size=0,
        )

        # Initialize multizone colors if needed
        # Note: State restoration is handled by StateRestorer in factories
        if self.state.has_multizone and self.state.zone_count > 0:
            if not self.state.zone_colors:
                # Initialize with rainbow pattern using list comprehension
                # (performance optimization)
                self.state.zone_colors = [
                    LightHsbk(
                        hue=int((i / self.state.zone_count) * 65535),
                        saturation=65535,
                        brightness=32768,
                        kelvin=3500,
                    )
                    for i in range(self.state.zone_count)
                ]

        # Initialize tile state if needed
        # Note: Saved tile data is restored by StateRestorer in factories
        if self.state.has_matrix and self.state.tile_count > 0:
            if not self.state.tile_devices:
                for i in range(self.state.tile_count):
                    pixels = self.state.tile_width * self.state.tile_height
                    tile_colors = [
                        LightHsbk(hue=0, saturation=0, brightness=32768, kelvin=3500)
                        for _ in range(pixels)
                    ]

                    self.state.tile_devices.append(
                        {
                            "accel_meas_x": 0,
                            "accel_meas_y": 0,
                            "accel_meas_z": 0,
                            "user_x": float(i * self.state.tile_width),
                            "user_y": 0.0,
                            "width": self.state.tile_width,
                            "height": self.state.tile_height,
                            "device_version_vendor": 1,
                            "device_version_product": self.state.product,
                            "firmware_build": int(time.time()),
                            "firmware_version_minor": 70,
                            "firmware_version_major": 3,
                            "colors": tile_colors,
                        }
                    )

        # Save initial state if persistence is enabled
        # This ensures newly created devices are immediately persisted
        if self.storage:
            self._save_state()

    def get_uptime_ns(self) -> int:
        """Calculate current uptime in nanoseconds"""
        return int((time.time() - self.start_time) * 1e9)

    def _save_state(self) -> None:
        """Save device state asynchronously (non-blocking).

        Creates a background task to save state without blocking the event loop.
        The task is tracked to prevent garbage collection.

        Note: Only DevicePersistenceAsyncFile is supported in production. For testing,
        you can pass None to disable persistence.
        """
        if not self.storage:
            return

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self.storage.save_device_state(self.state))
            self._track_save_task(task)
        except RuntimeError:
            # No event loop (shouldn't happen in normal operation)
            logger.error("Cannot save state for %s: no event loop", self.state.serial)

    def _track_save_task(self, task: asyncio.Task) -> None:
        """Track background save task to prevent garbage collection.

        Args:
            task: Save task to track
        """
        self.background_save_tasks.add(task)
        task.add_done_callback(self.background_save_tasks.discard)

    def _get_resolved_scenario(self) -> ScenarioConfig:
        """Get resolved scenario configuration with caching.

        Resolves scenario from all applicable scopes and caches the result
        for performance.

        Returns:
            ScenarioConfig with resolved settings
        """
        if self._cached_scenario is not None:
            return self._cached_scenario

        # Resolve scenario with hierarchical scoping
        self._cached_scenario = self.scenario_manager.get_scenario_for_device(
            serial=self.state.serial,
            device_type=get_device_type(self),
            location=self.state.location_label,
            group=self.state.group_label,
        )
        return self._cached_scenario

    def invalidate_scenario_cache(self) -> None:
        """Invalidate cached scenario configuration.

        Call this when scenarios are updated at runtime to force
        recalculation on the next packet.
        """
        self._cached_scenario = None

    def _create_response_header(
        self, source: int, sequence: int, pkt_type: int, payload_size: int
    ) -> LifxHeader:
        """Create response header using pre-allocated template (performance).

        This method uses a pre-allocated template and creates a shallow copy,
        then updates the fields. This avoids full __init__ and __post_init__
        overhead while ensuring each response gets its own header object,
        providing ~10% improvement in response generation.

        Args:
            source: Source identifier from request
            sequence: Sequence number from request
            pkt_type: Packet type for response
            payload_size: Size of packed payload in bytes

        Returns:
            Configured LifxHeader ready to use
        """
        # Shallow copy of template is faster than full construction with validation
        header = copy.copy(self._response_header_template)
        # Update fields for this specific response
        header.source = source
        header.sequence = sequence
        header.pkt_type = pkt_type
        header.size = LIFX_HEADER_SIZE + payload_size
        return header

    def process_packet(
        self, header: LifxHeader, packet: Any | None
    ) -> list[tuple[LifxHeader, Any]]:
        """Process incoming packet and return response packets"""
        responses = []

        # Get resolved scenario configuration (cached for performance)
        scenario = self._get_resolved_scenario()

        # Check if packet should be dropped (with probabilistic drops)
        if not self.scenario_manager.should_respond(header.pkt_type, scenario):
            logger.info("Dropping packet type %s per scenario", header.pkt_type)
            return responses

        # Update uptime
        self.state.uptime_ns = self.get_uptime_ns()

        # Handle acknowledgment (packet type 45, no payload)
        if header.ack_required:
            ack_packet = Device.Acknowledgement()
            ack_payload = ack_packet.pack()
            ack_header = self._create_response_header(
                header.source,
                header.sequence,
                ack_packet.PKT_TYPE,
                len(ack_payload),
            )
            # Store header, packet, and pre-packed payload
            # (consistent with response format)
            responses.append((ack_header, ack_packet, ack_payload))

        # Handle specific packet types - handlers always return list
        response_packets = self._handle_packet_type(header, packet)
        # Handlers now always return list (empty if no response)
        for resp_packet in response_packets:
            # Cache packed payload to avoid double packing (performance optimization)
            resp_payload = resp_packet.pack()
            resp_header = self._create_response_header(
                header.source,
                header.sequence,
                resp_packet.PKT_TYPE,
                len(resp_payload),
            )
            # Store both header and pre-packed payload for error scenario processing
            responses.append((resp_header, resp_packet, resp_payload))

        # Apply error scenarios to responses
        modified_responses = []
        for resp_header, resp_packet, resp_payload in responses:
            # Check if we should send malformed packet (truncate payload)
            if resp_header.pkt_type in scenario.malformed_packets:
                # For malformed packets, truncate the pre-packed payload
                truncated_len = len(resp_payload) // 2
                resp_payload_modified = resp_payload[:truncated_len]
                resp_header.size = LIFX_HEADER_SIZE + truncated_len + 10  # Wrong size
                # Convert back to bytes for malformed case
                modified_responses.append((resp_header, resp_payload_modified))
                logger.info(
                    "Sending malformed packet type %s (truncated)", resp_header.pkt_type
                )
                continue

            # Check if we should send invalid field values
            if resp_header.pkt_type in scenario.invalid_field_values:
                # Corrupt the pre-packed payload
                resp_payload_modified = b"\xff" * len(resp_payload)
                modified_responses.append((resp_header, resp_payload_modified))
                pkt_type = resp_header.pkt_type
                logger.info("Sending invalid field values for packet type %s", pkt_type)
                continue

            # Normal case: use original packet object (will be packed later by server)
            modified_responses.append((resp_header, resp_packet))

        return modified_responses

    def _handle_packet_type(self, header: LifxHeader, packet: Any | None) -> list[Any]:
        """Handle specific packet types using registered handlers.

        Returns:
            List of response packets (empty list if no response)
        """
        pkt_type = header.pkt_type

        # Update uptime for this packet
        self.state.uptime_ns = self.get_uptime_ns()

        # Find handler for this packet type
        handler = self.handlers.get_handler(pkt_type)

        if handler:
            # Delegate to handler (always returns list now)
            response = handler.handle(self.state, packet, header.res_required)

            # Save state if storage is enabled (for SET operations)
            if packet and self.storage:
                self._save_state()

            return response
        else:
            # Unknown/unimplemented packet type
            from lifx_emulator.protocol.packets import get_packet_class

            packet_class = get_packet_class(pkt_type)
            if packet_class:
                logger.info(
                    "Device %s: Received %s (type %s) but no handler registered",
                    self.state.serial,
                    packet_class.__qualname__,
                    pkt_type,
                )
            else:
                serial = self.state.serial
                logger.warning(
                    "Device %s: Received unknown packet type %s", serial, pkt_type
                )

            # Check scenario for StateUnhandled response
            scenario = self._get_resolved_scenario()
            if scenario.send_unhandled:
                return [Device.StateUnhandled(unhandled_type=pkt_type)]
            return []
