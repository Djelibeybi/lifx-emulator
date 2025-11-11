"""Tests for persistent storage."""

import asyncio
import tempfile

import pytest

from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile
from lifx_emulator.factories import (
    create_color_light,
    create_device,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk


@pytest.fixture
async def temp_storage():
    """Create temporary storage directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DevicePersistenceAsyncFile(tmpdir)


class TestDevicePersistenceAsyncFile:
    """Test asynchronous device storage."""

    async def test_device_storage_save_and_load(self, temp_storage):
        """Test saving and loading basic device state."""
        # Create a device via factory
        device = create_color_light("d073d5123456", storage=temp_storage)
        state = device.state

        # Modify some values
        state.label = "Test Light"
        state.power_level = 32768
        state.color = LightHsbk(
            hue=10000, saturation=50000, brightness=40000, kelvin=4000
        )

        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        saved_state = temp_storage.load_device_state(state.serial)
        new_device = create_device(
            saved_state["product"], serial=saved_state["serial"], storage=temp_storage
        )
        new_state = new_device.state
        assert new_state.label == state.label
        assert new_state.power_level == state.power_level
        assert new_state.color.hue == state.color.hue
        assert new_state.color.saturation == state.color.saturation
        assert new_state.color.brightness == state.color.brightness
        assert new_state.color.kelvin == state.color.kelvin

    async def test_device_storage_location_and_group(self, temp_storage):
        """Test saving and loading location and group metadata."""
        device = create_color_light("d073d5abcdef", storage=temp_storage)
        state = device.state
        state.label = "Test Light"
        state.location_label = "Living Room"
        state.group_label = "Downstairs"
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()
        saved_state = temp_storage.load_device_state(state.serial)
        new_device = create_device(
            saved_state["product"], serial=saved_state["serial"], storage=temp_storage
        )
        new_state = new_device.state
        assert new_state.location_label == state.location_label
        assert new_state.group_label == state.group_label
        assert new_state.location_id == state.location_id
        assert new_state.group_id == state.group_id

    async def test_device_storage_multizone(self, temp_storage):
        """Test saving and loading multizone device state."""
        device = create_multizone_light(
            "d073d8111111", zone_count=8, storage=temp_storage
        )
        state = device.state
        state.label = "Test Strip"
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()
        saved_state = temp_storage.load_device_state(state.serial)
        new_device = create_device(
            saved_state["product"], serial=saved_state["serial"], storage=temp_storage
        )
        new_state = new_device.state
        assert new_state.label == state.label
        assert new_state.zone_count == state.zone_count
        assert new_state.zone_colors == state.zone_colors
        assert new_state.multizone_effect_type == state.multizone_effect_type
        assert new_state.multizone_effect_speed == state.multizone_effect_speed

    async def test_device_storage_tile(self, temp_storage):
        """Test saving and loading tile device state."""
        device = create_tile_device("d073d9222222", tile_count=2, storage=temp_storage)
        state = device.state
        state.label = "Test Tile"
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()
        saved_state = temp_storage.load_device_state(state.serial)
        new_device = create_device(
            saved_state["product"], serial=saved_state["serial"], storage=temp_storage
        )
        new_state = new_device.state
        assert new_state.label == state.label
        assert new_state.tile_count == state.tile_count
        assert new_state.tile_width == state.tile_width
        assert new_state.tile_height == state.tile_height
        assert new_state.tile_devices == state.tile_devices
        assert new_state.tile_effect_type == state.tile_effect_type
        assert new_state.tile_effect_speed == state.tile_effect_speed

    async def test_device_storage_list_devices(self, temp_storage):
        """Test listing all devices with saved state."""
        serials = ["d073d5aaaaaa", "d073d5bbbbbb", "d073d5cccccc"]
        for serial in serials:
            device = create_color_light(serial, storage=temp_storage)
            state = device.state
            state.label = f"Device {serial}"
            await temp_storage.save_device_state(state)
        await temp_storage.shutdown()
        listed_serials = temp_storage.list_devices()
        assert len(listed_serials) == 3
        assert sorted(listed_serials) == sorted(serials)

    async def test_device_storage_not_found(self, temp_storage):
        """Test loading non-existent device returns None."""
        loaded_state = temp_storage.load_device_state("nonexistent")
        assert loaded_state is None

    async def test_device_storage_delete(self, temp_storage):
        """Test deleting device state."""
        device = create_color_light("d073d5dddddd", storage=temp_storage)
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        # Verify it exists
        assert temp_storage.load_device_state(state.serial) is not None

        # Delete it
        temp_storage.delete_device_state(state.serial)

        # Verify it's gone
        assert temp_storage.load_device_state(state.serial) is None

    async def test_device_storage_delete_all(self, temp_storage):
        """Test deleting all device states."""
        # Create and save multiple devices
        serials = ["d073d5aaaaaa", "d073d5bbbbbb", "d073d5cccccc"]
        for serial in serials:
            device = create_color_light(serial, storage=temp_storage)
            state = device.state
            state.label = f"Device {serial}"
            await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        # List devices
        listed_serials = temp_storage.list_devices()
        assert len(listed_serials) == 3

        # Delete all
        deleted = temp_storage.delete_all_device_states()
        assert deleted == 3

        # Verify all are gone
        assert len(temp_storage.list_devices()) == 0

    async def test_storage_with_empty_list(self, temp_storage):
        """Test listing devices when no devices exist."""
        await temp_storage.shutdown()
        listed_serials = temp_storage.list_devices()
        assert len(listed_serials) == 0

    async def test_storage_get_stats(self, temp_storage):
        """Test retrieving storage statistics."""
        device = create_color_light("d073d5000001", storage=temp_storage)
        await temp_storage.save_device_state(device.state)

        stats = temp_storage.get_stats()
        assert "writes_queued" in stats
        assert "writes_executed" in stats
        assert "flushes" in stats
        assert "coalesce_ratio" in stats
        assert stats["writes_queued"] > 0

    async def test_storage_multiple_rapid_saves(self, temp_storage):
        """Test coalescing of rapid saves to same device."""
        device = create_color_light("d073d5111111", storage=temp_storage)
        state = device.state

        # Rapidly save the same device multiple times
        for i in range(5):
            state.label = f"Label {i}"
            await temp_storage.save_device_state(state)

        # Wait for flush to complete
        await temp_storage.shutdown()

        # Should have coalesced multiple writes
        stats = temp_storage.get_stats()
        # More writes queued than executed due to coalescing
        assert stats["writes_queued"] >= stats["writes_executed"]

    async def test_storage_batch_size_threshold(self, temp_storage):
        """Test flush triggered by batch size threshold."""
        # Create storage with low threshold
        small_threshold_storage = DevicePersistenceAsyncFile(
            temp_storage.storage_dir, debounce_ms=10000, batch_size_threshold=2
        )

        device1 = create_color_light("d073d5aaaaaa", storage=small_threshold_storage)
        device2 = create_color_light("d073d5bbbbbb", storage=small_threshold_storage)
        device3 = create_color_light("d073d5cccccc", storage=small_threshold_storage)

        # Save devices - should trigger flush when hitting threshold
        await small_threshold_storage.save_device_state(device1.state)
        await small_threshold_storage.save_device_state(device2.state)
        await asyncio.sleep(0.1)  # Give flush time to complete
        await small_threshold_storage.save_device_state(device3.state)

        await small_threshold_storage.shutdown()

        # All devices should be persisted
        assert small_threshold_storage.load_device_state("d073d5aaaaaa") is not None
        assert small_threshold_storage.load_device_state("d073d5bbbbbb") is not None
        assert small_threshold_storage.load_device_state("d073d5cccccc") is not None

    async def test_storage_shutdown_flushes_pending(self, temp_storage):
        """Test that shutdown flushes all pending writes."""
        device = create_color_light("d073d5000001", storage=temp_storage)
        state = device.state
        state.label = "Test Device"

        # Queue a save but don't wait for flush
        await temp_storage.save_device_state(state)

        # Shutdown should flush pending writes
        await temp_storage.shutdown()

        # Device state should be persisted
        loaded = temp_storage.load_device_state(state.serial)
        assert loaded is not None
        assert loaded["label"] == "Test Device"
