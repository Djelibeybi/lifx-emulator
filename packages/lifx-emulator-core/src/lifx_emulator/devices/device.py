"""Device state and emulated device implementation."""

from __future__ import annotations

import asyncio
import copy
import logging
import random
import time
from collections.abc import Callable
from typing import Any

from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.constants import LIFX_HEADER_SIZE
from lifx_emulator.devices.states import Connectivity, DeviceState, TileFramebuffers
from lifx_emulator.handlers import HandlerRegistry, create_default_registry
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import (
    Device,
    get_packet_class,
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

# Type alias for state change callback
# Signature: (device, packet_type, duration_ms) -> None
StateChangeCallback = Callable[["EmulatedLifxDevice", int, int], None]

# Packet types that modify device state (for state change notifications)
STATE_CHANGING_PACKETS: frozenset[int] = frozenset(
    {
        21,  # Device.SetPower
        24,  # Device.SetLabel
        49,  # Device.SetLocation
        52,  # Device.SetGroup
        102,  # Light.SetColor
        103,  # Light.SetWaveform
        117,  # Light.SetPower
        119,  # Light.SetWaveformOptional
        501,  # MultiZone.SetColorZones
        510,  # MultiZone.ExtendedSetColorZones
        715,  # Tile.Set64
        716,  # Tile.CopyFrameBuffer
        906,  # Button.Set
        910,  # Button.SetConfig
    }
)

# Synthetic change type for mutations initiated outside the LAN protocol.
EXTERNAL_STATE_UPDATE = -1
StateMutation = Callable[[DeviceState], None]


class EmulatedLifxDevice:
    """Emulated LIFX device with configurable scenarios and state management."""

    def __init__(
        self,
        device_state: DeviceState,
        storage: DevicePersistenceAsyncFile | None = None,
        handler_registry: HandlerRegistry | None = None,
        scenario_manager: HierarchicalScenarioManager | None = None,
        on_state_changed: StateChangeCallback | None = None,
        persist_initial_state: bool = False,
    ):
        self.state = device_state
        self.on_state_changed = on_state_changed
        # Use provided scenario manager or create a default empty one
        if scenario_manager is not None:
            self.scenario_manager = scenario_manager
        else:
            self.scenario_manager = HierarchicalScenarioManager()
        self._started_monotonic_ns = time.monotonic_ns()
        self.storage = storage

        # Scenario caching for performance (HierarchicalScenarioManager only)
        self._cached_scenario: ScenarioConfig | None = None

        self._background_tasks = BackgroundTaskTracker(f"device:{self.state.serial}")
        self._state_mutation_lock = asyncio.Lock()
        self._initial_persistence_started = False

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
            thread_connection=self.state.connectivity == Connectivity.THREAD,
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
                    zones = self.state.tile_width * self.state.tile_height
                    tile_colors = [
                        LightHsbk(hue=0, saturation=0, brightness=32768, kelvin=3500)
                        for _ in range(zones)
                    ]

                    self.state.tile_devices.append(
                        {
                            "accel_meas_x": 0,
                            "accel_meas_y": 0,
                            "accel_meas_z": 0,
                            "user_x": float(i),
                            "user_y": 0.0,
                            "width": self.state.tile_width,
                            "height": self.state.tile_height,
                            "device_version_vendor": 1,
                            "device_version_product": self.state.product,
                            "firmware_build": int(time.time()),
                            # Each tile mirrors the device's own resolved host
                            # firmware rather than a fixed value: real LIFX
                            # matrix hardware reports the same firmware on
                            # every tile as GetHostFirmware, and a Thread
                            # device's firmware floor must show up here too.
                            # This is an intentional default-output change for
                            # WiFi matrix products carrying a specs.yml
                            # firmware default (see 01-SPEC.md AC 16).
                            "firmware_version_minor": self.state.version_minor,
                            "firmware_version_major": self.state.version_major,
                            "colors": tile_colors,
                        }
                    )

            # Initialize framebuffer storage for each tile (framebuffers 1-7)
            # Framebuffer 0 is stored in tile_devices[i]["colors"]
            if not self.state.tile_framebuffers:
                for i in range(self.state.tile_count):
                    self.state.tile_framebuffers.append(TileFramebuffers(tile_index=i))

        # Save initial state if persistence is enabled
        # This ensures newly created devices are immediately persisted
        if self.storage and persist_initial_state:
            self.activate_persistence()

    def get_uptime_ns(self) -> int:
        """Calculate current uptime in nanoseconds"""
        return time.monotonic_ns() - self._started_monotonic_ns

    async def _persist_state(self, state: DeviceState, *, durable: bool) -> None:
        """Queue one immutable state snapshot and optionally flush it to disk."""
        if self.storage is None:
            raise RuntimeError("Cannot persist device state without storage")
        if durable:
            await self.storage.commit_device_state(state)
        else:
            await self.storage.save_device_state(state)

    def _save_state(
        self,
        state: DeviceState | None = None,
        *,
        durable: bool = False,
    ) -> asyncio.Task[Any] | None:
        """Save device state asynchronously (non-blocking).

        Creates a background task to save state without blocking the event loop.
        The task is tracked to prevent garbage collection.

        Note: Only DevicePersistenceAsyncFile is supported in production. For testing,
        you can pass None to disable persistence.
        """
        if not self.storage:
            return

        state_snapshot = self.state if state is None else state
        return self._background_tasks.schedule(
            self._persist_state(state_snapshot, durable=durable),
            f"save-device:{self.state.serial}",
        )

    def activate_persistence(self) -> asyncio.Task[Any] | None:
        """Start the initial save after repository admission succeeds."""
        if self.storage is None or self._initial_persistence_started:
            return None

        task = self._save_state()
        if task is not None:
            self._initial_persistence_started = True
        return task

    def _notify_state_changed(self, change_type: int, duration_ms: int) -> None:
        """Notify the configured observer after a state commit."""
        if self.on_state_changed is None:
            return
        try:
            self.on_state_changed(self, change_type, duration_ms)
        except Exception:
            logger.exception(
                "State change callback failed for %s (change_type=%s)",
                self.state.serial,
                change_type,
            )

    def apply_state_mutation(
        self,
        mutation: StateMutation,
        *,
        change_type: int,
        duration_ms: int = 0,
        durable: bool = False,
    ) -> asyncio.Task[Any] | None:
        """Validate and commit one isolated mutation, persistence, and event unit.

        The mutation runs against a deep copy. Protocol callers use the normal
        debounced persistence path; management callers can request a durable
        write and await the returned task before replying.
        """
        if durable and self.storage is not None:

            async def persist_then_commit() -> None:
                async with self._state_mutation_lock:
                    while True:
                        previous = self.state
                        candidate = copy.deepcopy(previous)
                        mutation(candidate)
                        await self._persist_state(candidate, durable=True)
                        # Synchronous protocol mutations can commit while disk
                        # I/O yields. Rebase this mutation on their latest state
                        # before publishing, preserving their acknowledged edits.
                        if self.state is not previous:
                            continue
                        self.state = candidate
                        self._notify_state_changed(change_type, duration_ms)
                        break

            task = self._background_tasks.schedule(
                persist_then_commit(),
                f"mutate-device:{self.state.serial}",
            )
            if task is None:
                raise RuntimeError(
                    f"Persistence admission is closed for {self.state.serial}"
                )
            return task

        candidate = copy.deepcopy(self.state)
        mutation(candidate)
        self.state = candidate
        persistence_task = self._save_state(candidate)
        self._notify_state_changed(change_type, duration_ms)
        return persistence_task

    async def close(self, timeout: float = 5.0) -> None:
        """Stop persistence admission and drain all previously scheduled saves."""
        await self._background_tasks.shutdown(timeout=timeout)

    def reopen(self) -> None:
        """Reopen persistence admission after a retained device remains active."""
        self._background_tasks.start_accepting()

    def reject_admission(self) -> None:
        """Close task admission for a device rejected by its repository."""
        self._background_tasks.stop_accepting()

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

    def _should_handle_packet(self, pkt_type: int) -> bool:
        """Check if device should handle a packet type based on capabilities.

        Args:
            pkt_type: Packet type number

        Returns:
            True if device should handle, False if should return StateUnhandled
        """
        # Device.* packets are always handled (2-59)
        if 2 <= pkt_type <= 59:
            return True

        # Light.* packets (101-149) require light capabilities
        # Switches (devices with relays) don't support light operations
        if 101 <= pkt_type <= 149:
            return not self.state.has_relays

        # MultiZone.* packets (501-512) require multizone capability
        if 501 <= pkt_type <= 512:
            return self.state.has_multizone

        # Tile.* packets (701-720) require matrix capability
        if 701 <= pkt_type <= 720:
            return self.state.has_matrix

        # Button.* packets (905-911) require button capability.
        # Sensor.* (401/402) is deliberately excluded: every device answers
        # SensorGetAmbientLight, reporting lux 0 when it has no sensor.
        if 905 <= pkt_type <= 911:
            return self.state.has_buttons

        # Unknown packets - let handler decide
        return True

    def process_packet(
        self,
        header: LifxHeader,
        packet: Any | None,
        *,
        scenario: ScenarioConfig | None = None,
        should_respond: bool | None = None,
    ) -> list[tuple[LifxHeader, Any]]:
        """Process incoming packet and return response packets"""
        responses = []

        # Get resolved scenario configuration (cached for performance)
        if scenario is None:
            scenario = self._get_resolved_scenario()

        # Direct callers resolve probabilistic drops here. The UDP server passes
        # its already-resolved decision so acknowledgements and processing share
        # one packet-atomic outcome.
        if should_respond is None:
            should_respond = self.scenario_manager.should_respond(
                header.pkt_type, scenario
            )
        if not should_respond:
            logger.info("Dropping packet type %s per scenario", header.pkt_type)
            return responses

        # Check if device should handle this packet type (capability-based filtering)
        if not self._should_handle_packet(header.pkt_type):
            # Return StateUnhandled for unsupported packet types
            state_unhandled = Device.StateUnhandled(unhandled_type=header.pkt_type)
            unhandled_payload = state_unhandled.pack()
            unhandled_header = self._create_response_header(
                header.source,
                header.sequence,
                state_unhandled.PKT_TYPE,
                len(unhandled_payload),
            )
            # Send ack before StateUnhandled when scenario controls ack behavior
            if header.ack_required and scenario.affects_acks:
                ack_packet = Device.Acknowledgement()
                ack_payload = ack_packet.pack()
                ack_header = self._create_response_header(
                    header.source,
                    header.sequence,
                    ack_packet.PKT_TYPE,
                    len(ack_payload),
                )
                responses.append((ack_header, ack_packet, ack_payload))

            responses.append((unhandled_header, state_unhandled, unhandled_payload))
            return self._apply_error_scenarios(responses, scenario)

        # Update uptime
        self.state.uptime_ns = self.get_uptime_ns()

        # Handle acknowledgment (packet type 45, no payload)
        # Only generate ack here when a scenario targets ack behavior;
        # otherwise the server sends the ack immediately before calling us.
        if header.ack_required and scenario.affects_acks:
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

        # Apply partial_responses: truncate multi-packet responses to random subset
        if len(response_packets) > 1:
            first_pkt = response_packets[0]
            if (
                hasattr(first_pkt, "PKT_TYPE")
                and first_pkt.PKT_TYPE in scenario.partial_responses
            ):
                original_count = len(response_packets)
                partial_count = random.randint(1, original_count - 1)  # nosec
                response_packets = response_packets[:partial_count]
                logger.info(
                    "Sending partial response for packet type %s (%d of %d packets)",
                    first_pkt.PKT_TYPE,
                    partial_count,
                    original_count,
                )

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

        return self._apply_error_scenarios(responses, scenario)

    def _apply_error_scenarios(
        self,
        responses: list[tuple],
        scenario: ScenarioConfig,
    ) -> list[tuple[LifxHeader, Any]]:
        """Apply malformed/invalid-field error scenarios to response packets.

        Args:
            responses: List of (header, packet, payload) tuples
            scenario: Resolved scenario config

        Returns:
            List of (header, packet) tuples with error scenarios applied
        """
        modified_responses: list[tuple[LifxHeader, Any]] = []
        for resp_header, resp_packet, resp_payload in responses:
            # Check if we should send malformed packet (truncate payload)
            if resp_header.pkt_type in scenario.malformed_packets:
                truncated_len = len(resp_payload) // 2
                resp_payload_modified = resp_payload[:truncated_len]
                resp_header.size = LIFX_HEADER_SIZE + truncated_len + 10  # Wrong size
                modified_responses.append((resp_header, resp_payload_modified))
                logger.info(
                    "Sending malformed packet type %s (truncated)", resp_header.pkt_type
                )
                continue

            # Check if we should send invalid field values
            if resp_header.pkt_type in scenario.invalid_field_values:
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
            if pkt_type in STATE_CHANGING_PACKETS:
                duration_ms = getattr(packet, "duration", 0) if packet else 0
                responses: list[Any] = []

                def mutate(candidate: DeviceState) -> None:
                    responses.extend(
                        handler.handle(candidate, packet, header.res_required)
                    )

                self.apply_state_mutation(
                    mutate,
                    change_type=pkt_type,
                    duration_ms=duration_ms,
                )
                return responses

            # Delegate non-mutating packets directly to the current state.
            response = handler.handle(self.state, packet, header.res_required)
            if packet and self.storage:
                self._save_state()

            return response
        else:
            # Unknown/unimplemented packet type
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
