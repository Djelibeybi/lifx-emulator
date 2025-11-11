"""Shared domain models for LIFX emulator.

This module contains Pydantic models that are used across multiple layers
of the application (domain, API, persistence, etc.).
"""

from pydantic import BaseModel, Field, field_validator


class ScenarioConfig(BaseModel):
    """Scenario configuration for testing LIFX protocol behavior.

    Scenarios define testing behaviors for the emulator:
    - Dropping specific packet types (no response)
    - Adding response delays
    - Sending malformed/corrupted responses
    - Overriding firmware version
    - Sending incomplete data

    This is used by:
    - HierarchicalScenarioManager (domain layer)
    - API endpoints (API layer)
    - ScenarioPersistence (persistence layer)
    """

    drop_packets: dict[int, float] = Field(
        default_factory=dict,
        description="Map of packet types to drop rates (0.0-1.0). "
        "1.0 = always drop, 0.5 = drop 50%, 0.1 = drop 10%. "
        "Example: {101: 1.0, 102: 0.6}",
    )
    response_delays: dict[int, float] = Field(
        default_factory=dict,
        description="Map of packet types to delay in seconds before responding",
    )
    malformed_packets: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with truncated/corrupted payloads",
    )
    invalid_field_values: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with all 0xFF bytes in fields",
    )
    firmware_version: tuple[int, int] | None = Field(
        None, description="Override firmware version (major, minor). Example: [3, 70]"
    )
    partial_responses: list[int] = Field(
        default_factory=list,
        description="List of packet types to send with incomplete data",
    )
    send_unhandled: bool = Field(
        False, description="Send unhandled message responses for unknown packet types"
    )

    @field_validator("drop_packets", mode="before")
    @classmethod
    def convert_drop_packets_keys(cls, v):
        """Convert string keys to integers for drop_packets.

        This allows JSON serialization where keys must be strings,
        but internally we use integer packet types.
        """
        if isinstance(v, dict):
            return {int(k): float(val) for k, val in v.items()}
        return v

    @field_validator("response_delays", mode="before")
    @classmethod
    def convert_response_delays_keys(cls, v):
        """Convert string keys to integers for response_delays.

        This allows JSON serialization where keys must be strings,
        but internally we use integer packet types.
        """
        if isinstance(v, dict):
            return {int(k): float(val) for k, val in v.items()}
        return v

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioConfig":
        """Create from dictionary (backward compatibility wrapper).

        Note: This wraps Pydantic's .model_validate() for backward compatibility.
        The field_validators automatically handle string-to-int key conversion.

        Args:
            data: Dictionary with scenario configuration

        Returns:
            ScenarioConfig instance
        """
        return cls.model_validate(data)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Note: Pydantic models have .model_dump() which does this,
        but we keep this method for backward compatibility with
        existing code that expects string keys for packet types.

        Returns:
            Dictionary with string keys for drop_packets and response_delays
        """
        return {
            "drop_packets": {str(k): v for k, v in self.drop_packets.items()},
            "response_delays": {str(k): v for k, v in self.response_delays.items()},
            "malformed_packets": self.malformed_packets,
            "invalid_field_values": self.invalid_field_values,
            "firmware_version": self.firmware_version,
            "partial_responses": self.partial_responses,
            "send_unhandled": self.send_unhandled,
        }
