"""Hierarchical scenario management for testing LIFX protocol behavior.

This module provides a flexible scenario system that allows configuring
test scenarios at multiple scopes with precedence-based resolution.
"""

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lifx_emulator.device import EmulatedLifxDevice


@dataclass
class ScenarioConfig:
    """Individual scenario configuration.

    Scenarios define testing behaviors for the emulator, such as:
    - Dropping specific packet types (no response)
    - Adding response delays
    - Sending malformed/corrupted responses
    - Overriding firmware version
    """

    drop_packets: dict[int, float] = field(default_factory=dict)
    """Packet types to drop with drop rates (0.1-1.0).

    Maps packet type to drop rate where:
    - 1.0 = always drop (100%)
    - 0.5 = drop 50% of packets
    - 0.1 = drop 10% of packets
    Examples: {101: 1.0} (always drop), {102: 0.6} (drop 60% of packets)
    """

    response_delays: dict[int, float] = field(default_factory=dict)
    """Response delays in seconds by packet type"""

    malformed_packets: list[int] = field(default_factory=list)
    """Packet types to send truncated/corrupted"""

    invalid_field_values: list[int] = field(default_factory=list)
    """Packet types to send with all 0xFF bytes"""

    firmware_version: tuple[int, int] | None = None
    """Override firmware version (major, minor)"""

    partial_responses: list[int] = field(default_factory=list)
    """Packet types to send incomplete multizone/tile data"""

    send_unhandled: bool = False
    """Send StateUnhandled for unknown packet types"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            "drop_packets": {str(k): v for k, v in self.drop_packets.items()},
            "response_delays": {str(k): v for k, v in self.response_delays.items()},
            "malformed_packets": self.malformed_packets,
            "invalid_field_values": self.invalid_field_values,
            "firmware_version": self.firmware_version,
            "partial_responses": self.partial_responses,
            "send_unhandled": self.send_unhandled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioConfig":
        """Create from dictionary (API input)."""
        firmware = data.get("firmware_version")
        if firmware and not isinstance(firmware, tuple):
            firmware = tuple(firmware)

        # Convert drop_packets keys from string to int
        drop_packets_input = data.get("drop_packets", {})
        drop_packets = (
            {int(k): v for k, v in drop_packets_input.items()}
            if isinstance(drop_packets_input, dict)
            else {}
        )

        # Convert response_delays keys from string to int
        response_delays_input = data.get("response_delays", {})
        response_delays = (
            {int(k): v for k, v in response_delays_input.items()}
            if isinstance(response_delays_input, dict)
            else {}
        )

        return cls(
            drop_packets=drop_packets,
            response_delays=response_delays,
            malformed_packets=data.get("malformed_packets", []),
            invalid_field_values=data.get("invalid_field_values", []),
            firmware_version=firmware,
            partial_responses=data.get("partial_responses", []),
            send_unhandled=data.get("send_unhandled", False),
        )


def get_device_type(device: "EmulatedLifxDevice") -> str:
    """Get device type identifier for scenario scoping.

    Args:
        device: EmulatedLifxDevice instance

    Returns:
        Device type string (matrix, extended_multizone, multizone,
        hev, infrared, color, or basic)
    """
    if device.state.has_matrix:
        return "matrix"
    elif device.state.has_extended_multizone:
        return "extended_multizone"
    elif device.state.has_multizone:
        return "multizone"
    elif device.state.has_hev:
        return "hev"
    elif device.state.has_infrared:
        return "infrared"
    elif device.state.has_color:
        return "color"
    else:
        return "basic"


class HierarchicalScenarioManager:
    """Manages scenarios across multiple scopes with precedence resolution.

    Supports 5 scope levels with precedence (specific to general):
    1. Device-specific (by serial) - Highest priority
    2. Device-type specific (by capability: color, multizone, matrix, etc.)
    3. Location-specific (all devices in location)
    4. Group-specific (all devices in group)
    5. Global (all emulated devices) - Lowest priority

    When resolving scenarios for a device, configurations from all applicable
    scopes are merged using union semantics for lists and override semantics
    for scalars.
    """

    def __init__(self):
        # Scenario storage by scope
        self.device_scenarios: dict[str, ScenarioConfig] = {}  # serial → config
        self.type_scenarios: dict[str, ScenarioConfig] = {}  # type → config
        self.location_scenarios: dict[str, ScenarioConfig] = {}  # location → config
        self.group_scenarios: dict[str, ScenarioConfig] = {}  # group → config
        self.global_scenario: ScenarioConfig = ScenarioConfig()

    def set_device_scenario(self, serial: str, config: ScenarioConfig):
        """Set scenario for specific device by serial."""
        self.device_scenarios[serial] = config

    def set_type_scenario(self, device_type: str, config: ScenarioConfig):
        """Set scenario for device type (color, multizone, matrix, etc.)."""
        self.type_scenarios[device_type] = config

    def set_location_scenario(self, location: str, config: ScenarioConfig):
        """Set scenario for all devices in a location."""
        self.location_scenarios[location] = config

    def set_group_scenario(self, group: str, config: ScenarioConfig):
        """Set scenario for all devices in a group."""
        self.group_scenarios[group] = config

    def set_global_scenario(self, config: ScenarioConfig):
        """Set global scenario for all devices."""
        self.global_scenario = config

    def delete_device_scenario(self, serial: str) -> bool:
        """Delete device-specific scenario. Returns True if existed."""
        return self.device_scenarios.pop(serial, None) is not None

    def delete_type_scenario(self, device_type: str) -> bool:
        """Delete type-specific scenario. Returns True if existed."""
        return self.type_scenarios.pop(device_type, None) is not None

    def delete_location_scenario(self, location: str) -> bool:
        """Delete location-specific scenario. Returns True if existed."""
        return self.location_scenarios.pop(location, None) is not None

    def delete_group_scenario(self, group: str) -> bool:
        """Delete group-specific scenario. Returns True if existed."""
        return self.group_scenarios.pop(group, None) is not None

    def clear_global_scenario(self):
        """Clear global scenario (reset to empty)."""
        self.global_scenario = ScenarioConfig()

    def get_global_scenario(self) -> ScenarioConfig:
        """Get global scenario configuration."""
        return self.global_scenario

    def get_device_scenario(self, serial: str) -> ScenarioConfig | None:
        """Get device-specific scenario by serial.

        Args:
            serial: Device serial number

        Returns:
            ScenarioConfig if scenario exists, None otherwise
        """
        return self.device_scenarios.get(serial)

    def get_type_scenario(self, device_type: str) -> ScenarioConfig | None:
        """Get type-specific scenario.

        Args:
            device_type: Device type (color, multizone, matrix, etc.)

        Returns:
            ScenarioConfig if scenario exists, None otherwise
        """
        return self.type_scenarios.get(device_type)

    def get_location_scenario(self, location: str) -> ScenarioConfig | None:
        """Get location-specific scenario.

        Args:
            location: Device location label

        Returns:
            ScenarioConfig if scenario exists, None otherwise
        """
        return self.location_scenarios.get(location)

    def get_group_scenario(self, group: str) -> ScenarioConfig | None:
        """Get group-specific scenario.

        Args:
            group: Device group label

        Returns:
            ScenarioConfig if scenario exists, None otherwise
        """
        return self.group_scenarios.get(group)

    def get_scenario_for_device(
        self,
        serial: str,
        device_type: str,
        location: str,
        group: str,
    ) -> ScenarioConfig:
        """Resolve scenario for device with precedence.

        Precedence (highest to lowest):
        1. Device-specific
        2. Device-type
        3. Location
        4. Group
        5. Global

        Returns merged configuration with most specific values taking priority.
        Lists are merged using union (all values combined).
        Dicts are merged with later values overriding earlier.
        Scalars use the most specific non-None value.

        Args:
            serial: Device serial number
            device_type: Device type (color, multizone, matrix, etc.)
            location: Device location label
            group: Device group label

        Returns:
            Merged ScenarioConfig
        """
        # Start with empty config
        merged = ScenarioConfig()

        # Layer in each scope (general to specific)
        # Later scopes override or merge with earlier ones
        for config in [
            self.global_scenario,
            self.group_scenarios.get(group),
            self.location_scenarios.get(location),
            self.type_scenarios.get(device_type),
            self.device_scenarios.get(serial),
        ]:
            if config is None:
                continue

            # Merge drop_packets dict (later overwrites earlier)
            merged.drop_packets.update(config.drop_packets)

            # Merge lists using union (combine all values)
            merged.malformed_packets = list(
                set(merged.malformed_packets + config.malformed_packets)
            )
            merged.invalid_field_values = list(
                set(merged.invalid_field_values + config.invalid_field_values)
            )
            merged.partial_responses = list(
                set(merged.partial_responses + config.partial_responses)
            )

            # Merge delays dict (later overwrites earlier)
            merged.response_delays.update(config.response_delays)

            # Scalars: use most specific non-default value
            if config.firmware_version is not None:
                merged.firmware_version = config.firmware_version
            if config.send_unhandled:
                merged.send_unhandled = True

        return merged

    def should_respond(self, packet_type: int, scenario: ScenarioConfig) -> bool:
        """Check if device should respond to packet type.

        Uses probabilistic dropping based on drop_packets configuration.

        Args:
            packet_type: LIFX packet type number
            scenario: Resolved scenario configuration

        Returns:
            False if packet should be dropped, True otherwise
        """
        if packet_type not in scenario.drop_packets:
            return True

        # Get drop rate for this packet type (0.1-1.0)
        drop_rate = scenario.drop_packets[packet_type]

        # Probabilistic drop: random value [0, 1) < drop_rate means drop
        return random.random() >= drop_rate  # nosec

    def get_response_delay(self, packet_type: int, scenario: ScenarioConfig) -> float:
        """Get response delay for packet type.

        Args:
            packet_type: LIFX packet type number
            scenario: Resolved scenario configuration

        Returns:
            Delay in seconds (0.0 if no delay configured)
        """
        return scenario.response_delays.get(packet_type, 0.0)

    def should_send_malformed(self, packet_type: int, scenario: ScenarioConfig) -> bool:
        """Check if response should be malformed/truncated.

        Args:
            packet_type: LIFX packet type number
            scenario: Resolved scenario configuration

        Returns:
            True if response should be corrupted
        """
        return packet_type in scenario.malformed_packets

    def should_send_invalid_fields(
        self, packet_type: int, scenario: ScenarioConfig
    ) -> bool:
        """Check if response should have invalid field values (all 0xFF).

        Args:
            packet_type: LIFX packet type number
            scenario: Resolved scenario configuration

        Returns:
            True if response should have invalid fields
        """
        return packet_type in scenario.invalid_field_values

    def get_firmware_version_override(
        self, scenario: ScenarioConfig
    ) -> tuple[int, int] | None:
        """Get firmware version override if configured.

        Args:
            scenario: Resolved scenario configuration

        Returns:
            (major, minor) tuple or None
        """
        return scenario.firmware_version

    def should_send_partial_response(
        self, packet_type: int, scenario: ScenarioConfig
    ) -> bool:
        """Check if response should be partial (incomplete multizone/tile data).

        Args:
            packet_type: LIFX packet type number
            scenario: Resolved scenario configuration

        Returns:
            True if response should be incomplete
        """
        return packet_type in scenario.partial_responses

    def should_send_unhandled(self, scenario: ScenarioConfig) -> bool:
        """Check if StateUnhandled should be sent for unknown packet types.

        Args:
            scenario: Resolved scenario configuration

        Returns:
            True if StateUnhandled should be sent
        """
        return scenario.send_unhandled
