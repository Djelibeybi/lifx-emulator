"""Device state and emulated device implementation."""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any

from lifx_emulator.constants import LIFX_HEADER_SIZE
from lifx_emulator.device_states import (
    CoreDeviceState,
    GroupState,
    HevState,
    InfraredState,
    LocationState,
    MatrixState,
    MultiZoneState,
    NetworkState,
    WaveformState,
)
from lifx_emulator.handlers import HandlerRegistry, create_default_registry
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import (
    Device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.scenario_manager import (
    HierarchicalScenarioManager,
    ScenarioConfig,
    get_device_type,
)

logger = logging.getLogger(__name__)

# Forward declaration for type hinting
TYPE_CHECKING = False
if TYPE_CHECKING:
    from lifx_emulator.async_storage import AsyncDeviceStorage


@dataclass
class DeviceState:
    """Composed device state following Single Responsibility Principle.

    Each aspect of device state is managed by a focused sub-state object.
    """

    core: CoreDeviceState
    network: NetworkState
    location: LocationState
    group: GroupState
    waveform: WaveformState

    # Optional capability-specific state
    infrared: InfraredState | None = None
    hev: HevState | None = None
    multizone: MultiZoneState | None = None
    matrix: MatrixState | None = None

    # Capability flags (kept for convenience)
    has_color: bool = True
    has_infrared: bool = False
    has_multizone: bool = False
    has_extended_multizone: bool = False
    has_matrix: bool = False
    has_hev: bool = False

    def get_target_bytes(self) -> bytes:
        """Get target bytes for this device"""
        return bytes.fromhex(self.core.serial) + b"\x00\x00"

    # Convenience properties for commonly accessed core fields
    @property
    def serial(self) -> str:
        return self.core.serial

    @property
    def label(self) -> str:
        return self.core.label

    @label.setter
    def label(self, value: str):
        self.core.label = value

    @property
    def power_level(self) -> int:
        return self.core.power_level

    @power_level.setter
    def power_level(self, value: int):
        self.core.power_level = value

    @property
    def color(self) -> LightHsbk:
        return self.core.color

    @color.setter
    def color(self, value: LightHsbk):
        self.core.color = value

    @property
    def vendor(self) -> int:
        return self.core.vendor

    @property
    def product(self) -> int:
        return self.core.product

    @property
    def version_major(self) -> int:
        return self.core.version_major

    @version_major.setter
    def version_major(self, value: int):
        self.core.version_major = value

    @property
    def version_minor(self) -> int:
        return self.core.version_minor

    @version_minor.setter
    def version_minor(self, value: int):
        self.core.version_minor = value

    @property
    def build_timestamp(self) -> int:
        return self.core.build_timestamp

    @property
    def uptime_ns(self) -> int:
        return self.core.uptime_ns

    @uptime_ns.setter
    def uptime_ns(self, value: int):
        self.core.uptime_ns = value

    @property
    def mac_address(self) -> bytes:
        return self.core.mac_address

    @property
    def port(self) -> int:
        return self.core.port

    @port.setter
    def port(self, value: int):
        self.core.port = value

    # Network properties
    @property
    def wifi_signal(self) -> float:
        return self.network.wifi_signal

    # Location properties
    @property
    def location_id(self) -> bytes:
        return self.location.location_id

    @location_id.setter
    def location_id(self, value: bytes):
        self.location.location_id = value

    @property
    def location_label(self) -> str:
        return self.location.location_label

    @location_label.setter
    def location_label(self, value: str):
        self.location.location_label = value

    @property
    def location_updated_at(self) -> int:
        return self.location.location_updated_at

    @location_updated_at.setter
    def location_updated_at(self, value: int):
        self.location.location_updated_at = value

    # Group properties
    @property
    def group_id(self) -> bytes:
        return self.group.group_id

    @group_id.setter
    def group_id(self, value: bytes):
        self.group.group_id = value

    @property
    def group_label(self) -> str:
        return self.group.group_label

    @group_label.setter
    def group_label(self, value: str):
        self.group.group_label = value

    @property
    def group_updated_at(self) -> int:
        return self.group.group_updated_at

    @group_updated_at.setter
    def group_updated_at(self, value: int):
        self.group.group_updated_at = value

    # Waveform properties
    @property
    def waveform_active(self) -> bool:
        return self.waveform.waveform_active

    @waveform_active.setter
    def waveform_active(self, value: bool):
        self.waveform.waveform_active = value

    @property
    def waveform_type(self) -> int:
        return self.waveform.waveform_type

    @waveform_type.setter
    def waveform_type(self, value: int):
        self.waveform.waveform_type = value

    @property
    def waveform_transient(self) -> bool:
        return self.waveform.waveform_transient

    @waveform_transient.setter
    def waveform_transient(self, value: bool):
        self.waveform.waveform_transient = value

    @property
    def waveform_color(self) -> LightHsbk:
        return self.waveform.waveform_color

    @waveform_color.setter
    def waveform_color(self, value: LightHsbk):
        self.waveform.waveform_color = value

    @property
    def waveform_period_ms(self) -> int:
        return self.waveform.waveform_period_ms

    @waveform_period_ms.setter
    def waveform_period_ms(self, value: int):
        self.waveform.waveform_period_ms = value

    @property
    def waveform_cycles(self) -> float:
        return self.waveform.waveform_cycles

    @waveform_cycles.setter
    def waveform_cycles(self, value: float):
        self.waveform.waveform_cycles = value

    @property
    def waveform_duty_cycle(self) -> int:
        return self.waveform.waveform_duty_cycle

    @waveform_duty_cycle.setter
    def waveform_duty_cycle(self, value: int):
        self.waveform.waveform_duty_cycle = value

    @property
    def waveform_skew_ratio(self) -> int:
        return self.waveform.waveform_skew_ratio

    @waveform_skew_ratio.setter
    def waveform_skew_ratio(self, value: int):
        self.waveform.waveform_skew_ratio = value

    # Infrared properties
    @property
    def infrared_brightness(self) -> int:
        if self.infrared is None:
            return 0
        return self.infrared.infrared_brightness

    @infrared_brightness.setter
    def infrared_brightness(self, value: int):
        if self.infrared is not None:
            self.infrared.infrared_brightness = value

    # HEV properties
    @property
    def hev_cycle_duration_s(self) -> int:
        if self.hev is None:
            return 0
        return self.hev.hev_cycle_duration_s

    @hev_cycle_duration_s.setter
    def hev_cycle_duration_s(self, value: int):
        if self.hev is not None:
            self.hev.hev_cycle_duration_s = value

    @property
    def hev_cycle_remaining_s(self) -> int:
        if self.hev is None:
            return 0
        return self.hev.hev_cycle_remaining_s

    @hev_cycle_remaining_s.setter
    def hev_cycle_remaining_s(self, value: int):
        if self.hev is not None:
            self.hev.hev_cycle_remaining_s = value

    @property
    def hev_cycle_last_power(self) -> bool:
        if self.hev is None:
            return False
        return self.hev.hev_cycle_last_power

    @hev_cycle_last_power.setter
    def hev_cycle_last_power(self, value: bool):
        if self.hev is not None:
            self.hev.hev_cycle_last_power = value

    @property
    def hev_indication(self) -> bool:
        if self.hev is None:
            return False
        return self.hev.hev_indication

    @hev_indication.setter
    def hev_indication(self, value: bool):
        if self.hev is not None:
            self.hev.hev_indication = value

    @property
    def hev_last_result(self) -> int:
        if self.hev is None:
            return 0
        return self.hev.hev_last_result

    @hev_last_result.setter
    def hev_last_result(self, value: int):
        if self.hev is not None:
            self.hev.hev_last_result = value

    # MultiZone properties
    @property
    def zone_count(self) -> int:
        if self.multizone is None:
            return 0
        return self.multizone.zone_count

    @property
    def zone_colors(self) -> list[LightHsbk]:
        if self.multizone is None:
            return []
        return self.multizone.zone_colors

    @zone_colors.setter
    def zone_colors(self, value: list[LightHsbk]):
        if self.multizone is not None:
            self.multizone.zone_colors = value

    @property
    def multizone_effect_type(self) -> int:
        if self.multizone is None:
            return 0
        return self.multizone.effect_type

    @multizone_effect_type.setter
    def multizone_effect_type(self, value: int):
        if self.multizone is not None:
            self.multizone.effect_type = value

    @property
    def multizone_effect_speed(self) -> int:
        if self.multizone is None:
            return 0
        return self.multizone.effect_speed

    @multizone_effect_speed.setter
    def multizone_effect_speed(self, value: int):
        if self.multizone is not None:
            self.multizone.effect_speed = value

    # Matrix (Tile) properties
    @property
    def tile_count(self) -> int:
        if self.matrix is None:
            return 0
        return self.matrix.tile_count

    @property
    def tile_devices(self) -> list[dict[str, Any]]:
        if self.matrix is None:
            return []
        return self.matrix.tile_devices

    @tile_devices.setter
    def tile_devices(self, value: list[dict[str, Any]]):
        if self.matrix is not None:
            self.matrix.tile_devices = value

    @property
    def tile_width(self) -> int:
        if self.matrix is None:
            return 8
        return self.matrix.tile_width

    @property
    def tile_height(self) -> int:
        if self.matrix is None:
            return 8
        return self.matrix.tile_height

    @property
    def tile_effect_type(self) -> int:
        if self.matrix is None:
            return 0
        return self.matrix.effect_type

    @tile_effect_type.setter
    def tile_effect_type(self, value: int):
        if self.matrix is not None:
            self.matrix.effect_type = value

    @property
    def tile_effect_speed(self) -> int:
        if self.matrix is None:
            return 0
        return self.matrix.effect_speed

    @tile_effect_speed.setter
    def tile_effect_speed(self, value: int):
        if self.matrix is not None:
            self.matrix.effect_speed = value

    @property
    def tile_effect_palette_count(self) -> int:
        if self.matrix is None:
            return 0
        return self.matrix.effect_palette_count

    @tile_effect_palette_count.setter
    def tile_effect_palette_count(self, value: int):
        if self.matrix is not None:
            self.matrix.effect_palette_count = value

    @property
    def tile_effect_palette(self) -> list[LightHsbk]:
        if self.matrix is None:
            return []
        return self.matrix.effect_palette

    @tile_effect_palette.setter
    def tile_effect_palette(self, value: list[LightHsbk]):
        if self.matrix is not None:
            self.matrix.effect_palette = value


class EmulatedLifxDevice:
    """Emulated LIFX device with configurable scenarios"""

    """Simulated LIFX device with configurable scenarios"""

    def __init__(
        self,
        device_state: DeviceState,
        storage: AsyncDeviceStorage | None = None,
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
                # Initialize with rainbow pattern
                self.state.zone_colors = []
                for i in range(self.state.zone_count):
                    hue = int((i / self.state.zone_count) * 65535)
                    self.state.zone_colors.append(
                        LightHsbk(
                            hue=hue, saturation=65535, brightness=32768, kelvin=3500
                        )
                    )

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

        Note: Only AsyncDeviceStorage is supported in production. For testing,
        you can still use DeviceStorage, but it will log a warning as it blocks.
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
            ack_header = self._create_response_header(
                header.source,
                header.sequence,
                ack_packet.PKT_TYPE,
                len(ack_packet.pack()),
            )
            responses.append((ack_header, ack_packet))

        # Handle specific packet types - handlers always return list
        response_packets = self._handle_packet_type(header, packet)
        # Handlers now always return list (empty if no response)
        for resp_packet in response_packets:
            resp_header = self._create_response_header(
                header.source,
                header.sequence,
                resp_packet.PKT_TYPE,
                len(resp_packet.pack()),
            )
            responses.append((resp_header, resp_packet))

        # Apply error scenarios to responses
        modified_responses = []
        for resp_header, resp_packet in responses:
            # Check if we should send malformed packet (truncate payload)
            if resp_header.pkt_type in scenario.malformed_packets:
                # For malformed packets, we'll pack it first then truncate
                resp_payload = resp_packet.pack() if resp_packet else b""
                truncated_len = len(resp_payload) // 2
                resp_payload = resp_payload[:truncated_len]
                resp_header.size = LIFX_HEADER_SIZE + truncated_len + 10  # Wrong size
                # Convert back to bytes for malformed case
                modified_responses.append((resp_header, resp_payload))
                logger.info(
                    "Sending malformed packet type %s (truncated)", resp_header.pkt_type
                )
                continue

            # Check if we should send invalid field values
            if resp_header.pkt_type in scenario.invalid_field_values:
                # Pack normally then corrupt the bytes
                resp_payload = resp_packet.pack() if resp_packet else b""
                resp_payload = b"\xff" * len(resp_payload)
                modified_responses.append((resp_header, resp_payload))
                pkt_type = resp_header.pkt_type
                logger.info("Sending invalid field values for packet type %s", pkt_type)
                continue

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
