"""State restoration for devices with persistent storage.

This module provides centralized state restoration logic, eliminating
duplication between factories and device initialization.
"""

from __future__ import annotations

import logging
from typing import Any

from lifx_emulator.devices.device import DeviceState

logger = logging.getLogger(__name__)


class StateRestorer:
    """Handles restoration of device state from persistent storage.

    Consolidates state restoration logic that was previously duplicated
    between factories and device initialization.
    """

    def __init__(self, storage: Any):
        """Initialize state restorer.

        Args:
            storage: Storage instance (DeviceStorage or DevicePersistenceAsyncFile)
        """
        self.storage = storage

    def restore_if_available(self, state: DeviceState) -> DeviceState:
        """Restore saved state if available and compatible.

        Args:
            state: DeviceState to restore into

        Returns:
            The same DeviceState instance with restored values
        """
        if not self.storage:
            return state

        saved_state = self.storage.load_device_state(state.serial)
        if not saved_state:
            logger.debug("No saved state found for device %s", state.serial)
            return state

        # Only restore if product matches
        if saved_state.get("product") != state.product:
            logger.warning(
                "Saved state for %s has different product (%s vs %s), skipping restore",
                state.serial,
                saved_state.get("product"),
                state.product,
            )
            return state

        logger.info("Restoring saved state for device %s", state.serial)

        # Restore core state
        self._restore_core_state(state, saved_state)

        # Restore location and group
        self._restore_location_and_group(state, saved_state)

        # Restore capability-specific state
        self._restore_capability_state(state, saved_state)

        return state

    def _restore_core_state(
        self, state: DeviceState, saved_state: dict[str, Any]
    ) -> None:
        """Restore core device state fields.

        Args:
            state: DeviceState to restore into
            saved_state: Dictionary with saved state values
        """
        if "label" in saved_state:
            state.core.label = saved_state["label"]
        if "power_level" in saved_state:
            state.core.power_level = saved_state["power_level"]
        if "color" in saved_state:
            state.core.color = saved_state["color"]

    def _restore_location_and_group(
        self, state: DeviceState, saved_state: dict[str, Any]
    ) -> None:
        """Restore location and group metadata.

        Args:
            state: DeviceState to restore into
            saved_state: Dictionary with saved state values
        """
        # Location
        if "location_id" in saved_state:
            state.location.location_id = saved_state["location_id"]
        if "location_label" in saved_state:
            state.location.location_label = saved_state["location_label"]
        if "location_updated_at" in saved_state:
            state.location.location_updated_at = saved_state["location_updated_at"]

        # Group
        if "group_id" in saved_state:
            state.group.group_id = saved_state["group_id"]
        if "group_label" in saved_state:
            state.group.group_label = saved_state["group_label"]
        if "group_updated_at" in saved_state:
            state.group.group_updated_at = saved_state["group_updated_at"]

    def _restore_capability_state(
        self, state: DeviceState, saved_state: dict[str, Any]
    ) -> None:
        """Restore capability-specific state.

        Args:
            state: DeviceState to restore into
            saved_state: Dictionary with saved state values
        """
        # Infrared
        if (
            state.has_infrared
            and state.infrared
            and "infrared_brightness" in saved_state
        ):
            state.infrared.infrared_brightness = saved_state["infrared_brightness"]

        # HEV
        if state.has_hev and state.hev:
            if "hev_cycle_duration_s" in saved_state:
                state.hev.hev_cycle_duration_s = saved_state["hev_cycle_duration_s"]
            if "hev_cycle_remaining_s" in saved_state:
                state.hev.hev_cycle_remaining_s = saved_state["hev_cycle_remaining_s"]
            if "hev_cycle_last_power" in saved_state:
                state.hev.hev_cycle_last_power = saved_state["hev_cycle_last_power"]
            if "hev_indication" in saved_state:
                state.hev.hev_indication = saved_state["hev_indication"]
            if "hev_last_result" in saved_state:
                state.hev.hev_last_result = saved_state["hev_last_result"]

        # Multizone
        if state.has_multizone and state.multizone:
            self._restore_multizone_state(state, saved_state)

        # Matrix (Tile)
        if state.has_matrix and state.matrix:
            self._restore_matrix_state(state, saved_state)

    def _restore_multizone_state(
        self, state: DeviceState, saved_state: dict[str, Any]
    ) -> None:
        """Restore multizone-specific state.

        Args:
            state: DeviceState to restore into
            saved_state: Dictionary with saved state values
        """
        if state.multizone is None:
            return

        # First restore zone_count from saved state
        # This ensures the device matches what was previously saved
        if "zone_count" in saved_state:
            state.multizone.zone_count = saved_state["zone_count"]
            logger.debug("Restored zone_count: %s", state.multizone.zone_count)

        # Now restore zone colors if available
        if "zone_colors" in saved_state:
            # Verify zone count matches (should match now that we restored it)
            if len(saved_state["zone_colors"]) == state.multizone.zone_count:
                state.multizone.zone_colors = saved_state["zone_colors"]
                logger.debug("Restored %s zone colors", len(saved_state["zone_colors"]))
            else:
                logger.warning(
                    "Zone count mismatch: saved has %s zones, current has %s zones",
                    len(saved_state["zone_colors"]),
                    state.multizone.zone_count,
                )

        if "multizone_effect_type" in saved_state:
            state.multizone.effect_type = saved_state["multizone_effect_type"]
        if "multizone_effect_speed" in saved_state:
            state.multizone.effect_speed = saved_state["multizone_effect_speed"]

    def _restore_matrix_state(
        self, state: DeviceState, saved_state: dict[str, Any]
    ) -> None:
        """Restore matrix (tile) specific state.

        Args:
            state: DeviceState to restore into
            saved_state: Dictionary with saved state values
        """
        if state.matrix is None:
            return

        # First restore tile configuration (count, width, height) from saved state
        # This ensures the device matches what was previously saved
        if "tile_count" in saved_state:
            state.matrix.tile_count = saved_state["tile_count"]
            logger.debug("Restored tile_count: %s", state.matrix.tile_count)
        if "tile_width" in saved_state:
            state.matrix.tile_width = saved_state["tile_width"]
            logger.debug("Restored tile_width: %s", state.matrix.tile_width)
        if "tile_height" in saved_state:
            state.matrix.tile_height = saved_state["tile_height"]
            logger.debug("Restored tile_height: %s", state.matrix.tile_height)

        # Now restore tile devices if available
        if "tile_devices" in saved_state:
            saved_tiles = saved_state["tile_devices"]
            # Verify tile count matches (should match now that we restored it)
            if len(saved_tiles) == state.matrix.tile_count:
                # Verify all tiles have matching dimensions
                if all(
                    t["width"] == state.matrix.tile_width
                    and t["height"] == state.matrix.tile_height
                    for t in saved_tiles
                ):
                    state.matrix.tile_devices = saved_tiles
                    logger.debug("Restored %s tile devices", len(saved_tiles))
                else:
                    logger.warning(
                        "Tile dimensions mismatch, skipping tile restoration"
                    )
            else:
                logger.warning(
                    f"Tile count mismatch: saved has {len(saved_tiles)} tiles, "
                    f"current has {state.matrix.tile_count} tiles"
                )

        if "tile_effect_type" in saved_state:
            state.matrix.effect_type = saved_state["tile_effect_type"]
        if "tile_effect_speed" in saved_state:
            state.matrix.effect_speed = saved_state["tile_effect_speed"]
        if "tile_effect_palette_count" in saved_state:
            state.matrix.effect_palette_count = saved_state["tile_effect_palette_count"]
        if "tile_effect_palette" in saved_state:
            state.matrix.effect_palette = saved_state["tile_effect_palette"]


class NullStateRestorer:
    """No-op state restorer for devices without persistence.

    Allows code to unconditionally call restore without checking for None.
    """

    def restore_if_available(self, state: DeviceState) -> DeviceState:
        """No-op restoration.

        Args:
            state: DeviceState (returned unchanged)

        Returns:
            The same DeviceState instance
        """
        return state
