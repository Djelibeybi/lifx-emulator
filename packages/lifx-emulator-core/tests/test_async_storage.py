"""Tests for persistent storage."""

import asyncio
import json
import logging
import tempfile
from unittest.mock import patch

import pytest
from lifx_emulator import Connectivity
from lifx_emulator.devices.persistence import (
    DevicePersistenceAsyncFile,
    DevicePersistenceError,
)
from lifx_emulator.devices.state_restorer import StateRestorer
from lifx_emulator.factories import (
    create_color_light,
    create_device,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device
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
        await temp_storage.delete_device_state(state.serial)

        # Verify it's gone
        assert temp_storage.load_device_state(state.serial) is None

    async def test_device_storage_delete_not_found(self, temp_storage):
        """Deleting absent state returns the explicit not-found result."""
        assert not await temp_storage.delete_device_state("d073d50000ee")

    async def test_device_storage_delete_failure_raises(self, temp_storage):
        """A filesystem deletion failure is surfaced to the caller."""
        serial = "d073d50000ef"
        temp_storage._device_path(serial).mkdir()

        with pytest.raises(DevicePersistenceError) as caught:
            await temp_storage.delete_device_state(serial)

        assert caught.value.failed_serials == (serial,)

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

    async def test_device_storage_delete_all_surfaces_partial_failure(
        self, temp_storage
    ):
        """Bulk deletion reports every state file that could not be removed."""
        removable = temp_storage._device_path("d073d50000f1")
        blocked = temp_storage._device_path("d073d50000f2")
        removable.write_text("{}")
        blocked.mkdir()

        try:
            with pytest.raises(DevicePersistenceError) as caught:
                temp_storage.delete_all_device_states()

            assert caught.value.failed_serials == ("d073d50000f2",)
            assert not removable.exists()
            assert blocked.is_dir()
        finally:
            blocked.rmdir()

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

    async def test_failed_batch_is_retried_with_latest_snapshot(self, tmp_path):
        """A failed batch stays queued while a newer snapshot wins the retry."""
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
        device = create_color_light("d073d50000f3")
        original_write = storage._write_state
        attempts = 0

        def fail_once(serial, state_dict):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise DevicePersistenceError([serial], "forced batch failure")
            original_write(serial, state_dict)

        try:
            with patch.object(storage, "_write_state", side_effect=fail_once):
                device.state.power_level = 0
                await storage.save_device_state(device.state)
                with pytest.raises(DevicePersistenceError):
                    await storage._flush()
                assert storage.pending[device.state.serial]["power_level"] == 0

                device.state.power_level = 12345
                await storage.save_device_state(device.state)
                await storage._flush()

            saved = storage.load_device_state(device.state.serial)
            assert saved is not None
            assert saved["power_level"] == 12345
        finally:
            await storage.shutdown()

    async def test_shutdown_retries_a_transient_batch_failure(self, tmp_path):
        """Shutdown retries queued state after one failed batch."""
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
        device = create_color_light("d073d50000f4")
        original_write = storage._write_state
        attempts = 0

        def fail_once(serial, state_dict):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise DevicePersistenceError([serial], "forced batch failure")
            original_write(serial, state_dict)

        await storage.save_device_state(device.state)
        with patch.object(storage, "_write_state", side_effect=fail_once):
            await storage.shutdown()

        assert attempts == 2
        assert storage.load_device_state(device.state.serial) is not None

    async def test_shutdown_surfaces_terminal_batch_failure(self, tmp_path):
        """Shutdown raises and retains state after its bounded retries fail."""
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
        device = create_color_light("d073d50000f5")

        def always_fail(serial, _state_dict):
            raise DevicePersistenceError([serial], "forced terminal failure")

        await storage.save_device_state(device.state)
        with (
            patch.object(storage, "_write_state", side_effect=always_fail),
            pytest.raises(DevicePersistenceError) as caught,
        ):
            await storage.shutdown()

        assert caught.value.failed_serials == (device.state.serial,)
        assert device.state.serial in storage.pending
        assert not storage._device_path(device.state.serial).exists()

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


class TestSerialValidation:
    """Serials are validated before use in filesystem paths (path-traversal guard)."""

    @pytest.mark.parametrize(
        "bad_serial",
        [
            "../../etc/passwd",
            "d073d5/000001",
            "not-hex-value",
            "d073d500000",  # 11 chars (too short)
            "d073d50000012",  # 13 chars (too long)
            "d073d5000001\n",  # A dollar anchor alone accepts a final newline
            "",
        ],
    )
    async def test_device_path_rejects_invalid_serial(self, temp_storage, bad_serial):
        """_device_path raises ValueError for anything but a 12-char hex serial."""
        with pytest.raises(ValueError, match="Invalid device serial"):
            temp_storage._device_path(bad_serial)

    async def test_device_path_accepts_valid_serial(self, temp_storage):
        """A valid 12-char hex serial resolves to a path inside storage_dir."""
        path = temp_storage._device_path("d073d5AbCdEf")
        assert path.parent == temp_storage.storage_dir.resolve()
        assert path.name == "d073d5AbCdEf.json"

    async def test_batch_write_skips_invalid_serial(self, temp_storage):
        """_batch_write logs and skips invalid serials without writing files."""
        temp_storage._batch_write([("../evil", {"serial": "../evil"})])

        # No file escaped the storage directory and none was created inside it.
        assert list(temp_storage.storage_dir.glob("*.json")) == []

    async def test_load_rejects_invalid_serial(self, temp_storage):
        """load_device_state returns None for an invalid serial."""
        assert temp_storage.load_device_state("../../etc/passwd") is None

    @pytest.mark.parametrize("serial", ["../../etc/passwd", "d073d5000001\n"])
    async def test_delete_rejects_invalid_serial(self, temp_storage, serial):
        """delete_device_state surfaces invalid serials as typed failures."""
        with pytest.raises(DevicePersistenceError) as caught:
            await temp_storage.delete_device_state(serial)

        assert caught.value.failed_serials == (serial,)


class TestConnectivityPersistence:
    """connectivity survives a save-and-reload cycle, read exactly once.

    Never reload through a DevicePersistenceAsyncFile on which shutdown()
    has already been awaited: shutdown() permanently closes the backend's
    executor, while creating a device with storage= set schedules a
    background save. Every reload here constructs a fresh
    DevicePersistenceAsyncFile pointed at the same storage_dir instead.
    """

    def test_peek_connectivity_without_storage(self):
        """An optional restorer without a backend contributes no saved value."""
        restorer = StateRestorer(None)

        assert restorer.peek_connectivity("d073d5000032", 91) is None

    async def test_thread_connectivity_round_trips(self, temp_storage):
        """A Thread device saved and reloaded is still Thread; bit 3 survives
        on both the first reply and StateUnhandled (belt and braces, since
        the reloaded device rebuilds its header template in __init__)."""
        device = create_color_light(
            "d073d5000032", connectivity="thread", storage=temp_storage
        )
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        saved = temp_storage.load_device_state(state.serial)
        assert saved["connectivity"] == "thread"

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            new_device = create_device(
                saved["product"], serial=saved["serial"], storage=reload_storage
            )
            assert new_device.state.connectivity == Connectivity.THREAD

            first_request = LifxHeader(
                source=1,
                target=new_device.state.get_target_bytes(),
                sequence=1,
                pkt_type=Device.GetService.PKT_TYPE,
                res_required=True,
            )
            first_header, _ = new_device.process_packet(first_request, None)[0]
            assert first_header.thread_connection is True
            assert first_header.pack()[22] & 0x08 == 0x08

            unhandled_request = LifxHeader(
                source=2,
                target=new_device.state.get_target_bytes(),
                sequence=2,
                pkt_type=701,  # Tile.Get64 -- unhandled by a color light
                res_required=True,
            )
            unhandled_header, _ = new_device.process_packet(unhandled_request, None)[0]
            assert unhandled_header.thread_connection is True
            assert unhandled_header.pack()[22] & 0x08 == 0x08
        finally:
            await reload_storage.shutdown()

    async def test_missing_connectivity_key_restores_as_wifi(self, temp_storage):
        """A pre-milestone file with no connectivity key restores silently
        as wifi -- no warning is emitted for the missing-key case."""
        device = create_color_light("d073d5000033", storage=temp_storage)
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        path = temp_storage.storage_dir / f"{state.serial}.json"
        data = json.loads(path.read_text())
        del data["connectivity"]
        path.write_text(json.dumps(data))

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            new_device = create_device(
                data["product"], serial=data["serial"], storage=reload_storage
            )
            assert new_device.state.connectivity == Connectivity.WIFI
        finally:
            await reload_storage.shutdown()

    async def test_corrupted_connectivity_value_restores_as_wifi_with_warning(
        self, temp_storage, caplog
    ):
        """A corrupted connectivity value degrades to wifi, preserves every
        other field, and emits exactly one WARNING naming the serial and
        the substring 'connectivity' -- filtered by message content, not
        counted across all WARNING records (the restorer's own
        product-mismatch path also warns elsewhere)."""
        device = create_color_light("d073d5000034", storage=temp_storage)
        state = device.state
        state.label = "Corrupted Fixture"
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        path = temp_storage.storage_dir / f"{state.serial}.json"
        data = json.loads(path.read_text())
        data["connectivity"] = "bluetooth"
        path.write_text(json.dumps(data))

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            caplog.set_level(logging.WARNING)
            new_device = create_device(
                data["product"], serial=data["serial"], storage=reload_storage
            )
            assert new_device.state.connectivity == Connectivity.WIFI
            assert new_device.state.label == "Corrupted Fixture"

            matching = [
                r
                for r in caplog.records
                if state.serial in r.getMessage() and "connectivity" in r.getMessage()
            ]
            assert len(matching) == 1
        finally:
            await reload_storage.shutdown()

    async def test_explicit_wifi_argument_wins_over_saved_thread(
        self, temp_storage, caplog
    ):
        """An explicit connectivity="wifi" argument wins over a saved
        "thread" value, with one WARNING naming the serial and the
        substring 'connectivity'."""
        device = create_color_light(
            "d073d5000035", connectivity="thread", storage=temp_storage
        )
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            caplog.set_level(logging.WARNING)
            new_device = create_device(
                state.product,
                serial=state.serial,
                storage=reload_storage,
                connectivity="wifi",
            )
            assert new_device.state.connectivity == Connectivity.WIFI

            matching = [
                r
                for r in caplog.records
                if state.serial in r.getMessage() and "connectivity" in r.getMessage()
            ]
            assert len(matching) == 1
        finally:
            await reload_storage.shutdown()

    async def test_explicit_thread_argument_wins_over_saved_wifi(
        self, temp_storage, caplog
    ):
        """The reverse direction: connectivity="thread" wins over a saved
        "wifi" value, with one matching WARNING."""
        device = create_color_light("d073d5000036", storage=temp_storage)
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            caplog.set_level(logging.WARNING)
            new_device = create_device(
                state.product,
                serial=state.serial,
                storage=reload_storage,
                connectivity="thread",
            )
            assert new_device.state.connectivity == Connectivity.THREAD

            matching = [
                r
                for r in caplog.records
                if state.serial in r.getMessage() and "connectivity" in r.getMessage()
            ]
            assert len(matching) == 1
        finally:
            await reload_storage.shutdown()

    async def test_product_mismatch_contributes_no_connectivity(self, temp_storage):
        """A saved state whose product differs from the product being built
        contributes no connectivity -- matching the existing "skipping
        restore" semantics applied to every other field."""
        device = create_color_light(
            "d073d5000037", connectivity="thread", storage=temp_storage
        )
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            # Rebuild the same serial as a different product (91 Color -> 90
            # Clean/HEV); the saved file's connectivity must not leak across
            # the product mismatch.
            new_device = create_device(90, serial=state.serial, storage=reload_storage)
            assert new_device.state.connectivity == Connectivity.WIFI
        finally:
            await reload_storage.shutdown()

    async def test_load_device_state_called_once_per_build(
        self, temp_storage, monkeypatch
    ):
        """load_device_state is invoked exactly once per DeviceBuilder.build()
        call when storage is set -- the peek and the restore share one read."""
        device = create_color_light(
            "d073d5000038", connectivity="thread", storage=temp_storage
        )
        state = device.state
        await temp_storage.save_device_state(state)
        await temp_storage.shutdown()

        reload_storage = DevicePersistenceAsyncFile(
            storage_dir=temp_storage.storage_dir
        )
        try:
            call_count = 0
            original = DevicePersistenceAsyncFile.load_device_state

            def counting_load(self, serial):
                nonlocal call_count
                call_count += 1
                return original(self, serial)

            monkeypatch.setattr(
                DevicePersistenceAsyncFile, "load_device_state", counting_load
            )

            create_device(state.product, serial=state.serial, storage=reload_storage)
            assert call_count == 1
        finally:
            await reload_storage.shutdown()
