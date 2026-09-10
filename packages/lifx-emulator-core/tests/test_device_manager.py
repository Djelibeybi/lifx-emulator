"""Tests for DeviceManager class."""

import asyncio
import logging
import socket
from unittest.mock import AsyncMock, Mock, patch

import pytest
from lifx_emulator import Connectivity
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.devices.persistence import (
    DevicePersistenceAsyncFile,
    DevicePersistenceError,
)
from lifx_emulator.factories import create_color_light, create_multizone_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.scenarios.manager import (
    HierarchicalScenarioManager,
    ScenarioConfig,
)


def _target_header(
    serial: str,
    *,
    tagged: bool = False,
    zero_target: bool = False,
) -> LifxHeader:
    """Create a request header for target-resolution tests."""
    target = b"\x00" * 8 if zero_target else bytes.fromhex(serial) + b"\x00\x00"
    return LifxHeader(
        size=36,
        protocol=1024,
        tagged=tagged,
        source=12345,
        target=target,
        res_required=True,
        ack_required=True,
        sequence=1,
        pkt_type=2,
    )


class TestDeviceManager:
    """Test DeviceManager functionality."""

    @pytest.fixture
    def device_manager(self):
        """Create a DeviceManager with repository."""
        repository = DeviceRepository()
        return DeviceManager(repository)

    @pytest.fixture
    def sample_devices(self):
        """Create sample devices for testing."""
        return [
            create_color_light("d073d5000001"),
            create_color_light("d073d5000002"),
            create_multizone_light("d073d5000003", zone_count=16),
        ]

    def test_add_device(self, device_manager, sample_devices):
        """Test adding a device."""
        device = sample_devices[0]
        device_manager.add_device(device)
        assert device_manager.count_devices() == 1
        assert device_manager.get_device("d073d5000001") == device

    def test_add_duplicate_device(self, device_manager, sample_devices):
        """Test adding a duplicate device returns False."""
        device = sample_devices[0]
        result1 = device_manager.add_device(device)
        assert result1 is True

        # Adding same device again should return False
        result2 = device_manager.add_device(device)
        assert result2 is False

    def test_serial_alias_is_rejected_and_canonical_device_routes(self, device_manager):
        """Case variants collapse to one repository and wire identity."""
        accepted = create_color_light("d073d50000ab")
        alias = create_color_light("D073D50000AB")

        assert device_manager.add_device(accepted)
        assert not device_manager.add_device(alias)
        assert device_manager.get_device("d073d50000ab") is accepted
        assert device_manager.resolve_target_devices(
            _target_header("d073d50000ab")
        ) == [accepted]

    async def test_remove_device(self, device_manager, sample_devices):
        """Test removing a device."""
        device = sample_devices[0]
        device_manager.add_device(device)
        assert device_manager.count_devices() == 1

        await device_manager.remove_device("d073d5000001")
        assert device_manager.count_devices() == 0
        assert device_manager.get_device("d073d5000001") is None

    async def test_remove_nonexistent_device(self, device_manager):
        """Test removing a non-existent device returns False."""
        result = await device_manager.remove_device("d073d5999999")
        assert result is False

    def test_get_device(self, device_manager, sample_devices):
        """Test getting a device by serial."""
        device = sample_devices[0]
        device_manager.add_device(device)

        retrieved = device_manager.get_device("d073d5000001")
        assert retrieved == device
        assert retrieved.state.serial == "d073d5000001"

    def test_get_nonexistent_device(self, device_manager):
        """Test getting a non-existent device returns None."""
        assert device_manager.get_device("d073d5999999") is None

    def test_get_all_devices(self, device_manager, sample_devices):
        """Test getting all devices."""
        for device in sample_devices:
            device_manager.add_device(device)

        all_devices = device_manager.get_all_devices()
        assert len(all_devices) == 3
        assert all([d in sample_devices for d in all_devices])

    def test_count_devices(self, device_manager, sample_devices):
        """Test counting devices."""
        assert device_manager.count_devices() == 0

        device_manager.add_device(sample_devices[0])
        assert device_manager.count_devices() == 1

        device_manager.add_device(sample_devices[1])
        assert device_manager.count_devices() == 2

    def test_resolve_target_specific_device(self, device_manager, sample_devices):
        """Test resolving target to a specific device."""
        device = sample_devices[0]
        device_manager.add_device(device)

        # Create header targeting this device
        header = LifxHeader(
            size=36,
            protocol=1024,
            tagged=False,
            source=12345,
            target=bytes.fromhex("d073d5000001") + b"\x00\x00",
            res_required=True,
            ack_required=False,
            sequence=1,
            pkt_type=2,
        )

        targets = device_manager.resolve_target_devices(header)
        assert len(targets) == 1
        assert targets[0] == device

    def test_resolve_target_broadcast(self, device_manager, sample_devices):
        """Test resolving broadcast target to all devices."""
        for device in sample_devices:
            device_manager.add_device(device)

        # Create broadcast header (tagged=True)
        header = LifxHeader(
            size=36,
            protocol=1024,
            tagged=True,
            source=12345,
            target=b"\x00" * 8,
            res_required=True,
            ack_required=False,
            sequence=1,
            pkt_type=2,
        )

        targets = device_manager.resolve_target_devices(header)
        assert len(targets) == 3
        assert all([d in sample_devices for d in targets])

    def test_resolve_target_zero_target(self, device_manager, sample_devices):
        """Test resolving zero target (broadcast) to all devices."""
        for device in sample_devices:
            device_manager.add_device(device)

        # Create header with zero target (tagged=False but target=0)
        header = LifxHeader(
            size=36,
            protocol=1024,
            tagged=False,
            source=12345,
            target=b"\x00" * 8,
            res_required=True,
            ack_required=False,
            sequence=1,
            pkt_type=2,
        )

        targets = device_manager.resolve_target_devices(header)
        assert len(targets) == 3

    def test_resolve_target_nonexistent_device(self, device_manager):
        """Test resolving target to non-existent device returns empty list."""
        header = LifxHeader(
            size=36,
            protocol=1024,
            tagged=False,
            source=12345,
            target=bytes.fromhex("d073d5999999") + b"\x00\x00",
            res_required=True,
            ack_required=False,
            sequence=1,
            pkt_type=2,
        )

        targets = device_manager.resolve_target_devices(header)
        assert len(targets) == 0

    def test_invalidate_all_scenario_caches(self, device_manager, sample_devices):
        """Test invalidating scenario caches on all devices."""
        for device in sample_devices:
            device_manager.add_device(device)

        # Set cached scenarios (using a fake scenario object)
        fake_scenario = ScenarioConfig(drop_packets={101: 1.0})
        for device in sample_devices:
            device._cached_scenario = fake_scenario

        # Invalidate all caches
        device_manager.invalidate_all_scenario_caches()

        # Verify all caches were reset to None
        for device in sample_devices:
            assert device._cached_scenario is None

    def test_add_device_with_scenario_manager(self, device_manager):
        """Test adding a device with shared scenario manager."""
        # Create a scenario manager with configuration
        scenario_manager = HierarchicalScenarioManager()
        scenario_manager.set_global_scenario(ScenarioConfig(drop_packets={101: 1.0}))

        # Create device with its own scenario manager
        device = create_color_light("d073d5000001", scenario_manager=scenario_manager)

        # Create a new scenario manager to share
        shared_manager = HierarchicalScenarioManager()
        shared_manager.set_global_scenario(ScenarioConfig(drop_packets={102: 0.5}))

        # Add device with shared manager
        result = device_manager.add_device(device, scenario_manager=shared_manager)
        assert result is True

        # Verify device is using the shared manager
        assert device.scenario_manager is shared_manager

    async def test_remove_device_with_storage(self, device_manager, sample_devices):
        """Test removing a device with storage cleanup."""
        device = sample_devices[0]
        device_manager.add_device(device)

        # Create mock storage
        mock_storage = Mock()
        mock_storage.delete_device_state = AsyncMock(return_value=True)

        # Remove device with storage
        result = await device_manager.remove_device(
            "d073d5000001", storage=mock_storage
        )
        assert result is True

        # Verify storage deletion was called
        mock_storage.delete_device_state.assert_called_once_with("d073d5000001")

    async def test_remove_device_drains_save_before_storage_and_repository(self):
        """Removal retains a device until its admitted persistence work finishes."""
        save_started = asyncio.Event()
        release_save = asyncio.Event()

        class BlockingStorage:
            def __init__(self):
                self.deleted = False

            async def save_device_state(self, state):
                save_started.set()
                await release_save.wait()

            def load_device_state(self, serial):
                return None

            async def delete_device_state(self, serial):
                self.deleted = True
                return True

        storage = BlockingStorage()
        manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d50000aa", storage=storage)
        manager.add_device(device)
        await save_started.wait()

        removal = asyncio.create_task(
            manager.remove_device(device.state.serial, storage=storage)
        )
        await asyncio.sleep(0)

        assert manager.get_device(device.state.serial) is device
        assert not storage.deleted
        assert not removal.done()

        release_save.set()
        assert await removal
        assert storage.deleted
        assert manager.get_device(device.state.serial) is None

    async def test_remove_device_cancels_real_backend_queued_save(self, tmp_path):
        """A queued debounced save cannot recreate a removed device file."""
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=25)
        manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d50000ab", storage=storage)
        manager.add_device(device)

        try:
            assert await manager.remove_device(device.state.serial, storage=storage)
            await asyncio.sleep(0.05)

            assert device.state.serial not in storage.pending
            assert not storage._device_path(device.state.serial).exists()
        finally:
            await storage.shutdown()

    async def test_remove_device_retained_when_real_storage_delete_fails(
        self, tmp_path
    ):
        """A production unlink failure keeps the live device available."""
        storage = DevicePersistenceAsyncFile(tmp_path)
        manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d50000ae")
        manager.add_device(device)
        storage._device_path(device.state.serial).mkdir()

        try:
            with pytest.raises(DevicePersistenceError):
                await manager.remove_device(device.state.serial, storage=storage)

            assert manager.get_device(device.state.serial) is device
            assert device._background_tasks.accepting
        finally:
            storage._device_path(device.state.serial).rmdir()
            await storage.shutdown()

    async def test_remove_all_devices(self, device_manager, sample_devices):
        """Test removing all devices."""
        for device in sample_devices:
            device_manager.add_device(device)
        assert device_manager.count_devices() == 3

        # Remove all devices
        count = await device_manager.remove_all_devices()
        assert count == 3
        assert device_manager.count_devices() == 0

    async def test_remove_all_devices_with_storage(
        self, device_manager, sample_devices
    ):
        """Test removing all devices with storage cleanup."""
        for device in sample_devices:
            device_manager.add_device(device)

        # Create mock storage
        mock_storage = Mock()
        mock_storage.delete_device_states = AsyncMock(return_value=3)

        # Remove all with storage deletion
        count = await device_manager.remove_all_devices(
            delete_storage=True, storage=mock_storage
        )
        assert count == 3

        # Verify storage deletion was one atomic operation
        mock_storage.delete_device_states.assert_awaited_once_with(
            [device.state.serial for device in sample_devices]
        )

    async def test_remove_all_cancels_real_backend_queued_saves(self, tmp_path):
        """Bulk removal fences every queued save before releasing devices."""
        storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=25)
        manager = DeviceManager(DeviceRepository())
        devices = [
            create_color_light("d073d50000ac", storage=storage),
            create_color_light("d073d50000ad", storage=storage),
        ]
        for device in devices:
            manager.add_device(device)

        try:
            assert await manager.remove_all_devices(
                delete_storage=True, storage=storage
            ) == len(devices)
            await asyncio.sleep(0.05)

            assert storage.pending == {}
            assert all(
                not storage._device_path(device.state.serial).exists()
                for device in devices
            )
        finally:
            await storage.shutdown()

    async def test_remove_all_retains_every_device_when_storage_delete_fails(
        self, tmp_path
    ):
        """A partial bulk deletion failure commits no repository removals."""
        storage = DevicePersistenceAsyncFile(tmp_path)
        manager = DeviceManager(DeviceRepository())
        devices = [
            create_color_light("d073d50000b1"),
            create_color_light("d073d50000b2"),
        ]
        for device in devices:
            manager.add_device(device)
        first_path = storage._device_path(devices[0].state.serial)
        first_contents = '{"label": "first"}'
        first_path.write_text(first_contents)
        storage._device_path(devices[1].state.serial).mkdir()

        try:
            with pytest.raises(DevicePersistenceError):
                await manager.remove_all_devices(delete_storage=True, storage=storage)

            assert manager.get_all_devices() == devices
            assert all(device._background_tasks.accepting for device in devices)
            assert first_path.read_text() == first_contents
        finally:
            storage._device_path(devices[1].state.serial).rmdir()
            await storage.shutdown()

    async def test_remove_all_devices_no_storage_deletion(
        self, device_manager, sample_devices
    ):
        """Test removing all devices without storage deletion."""
        for device in sample_devices:
            device_manager.add_device(device)

        # Create mock storage (should not be called)
        mock_storage = Mock()
        mock_storage.delete_device_state = AsyncMock()

        # Remove all without storage deletion
        count = await device_manager.remove_all_devices(
            delete_storage=False, storage=mock_storage
        )
        assert count == 3

        # Verify storage deletion was NOT called
        mock_storage.delete_device_state.assert_not_awaited()

    async def test_cancelled_remove_reopens_retained_device_persistence(self):
        """Cancelling during close leaves the retained device able to save again."""
        first_save_started = asyncio.Event()
        later_save_completed = asyncio.Event()
        hold_first_save = asyncio.Event()

        class BlockingStorage:
            def __init__(self):
                self.save_count = 0

            def load_device_state(self, serial):
                return None

            async def save_device_state(self, state):
                self.save_count += 1
                if self.save_count == 1:
                    first_save_started.set()
                    await hold_first_save.wait()
                else:
                    later_save_completed.set()

            async def delete_device_state(self, serial):
                return True

        storage = BlockingStorage()
        manager = DeviceManager(DeviceRepository())
        device = create_color_light("d073d50000b3", storage=storage)
        manager.add_device(device)
        await first_save_started.wait()

        removal = asyncio.create_task(
            manager.remove_device(device.state.serial, storage=storage)
        )
        await asyncio.sleep(0)
        removal.cancel()

        with pytest.raises(asyncio.CancelledError):
            await removal

        assert manager.get_device(device.state.serial) is device
        assert device._background_tasks.accepting
        device._save_state()
        await asyncio.wait_for(later_save_completed.wait(), timeout=1.0)
        await device.close()

    async def test_cancelled_bulk_close_reopens_every_retained_device(self):
        """Cancellation part-way through bulk close reopens the closed prefix."""
        blocked_save_started = asyncio.Event()
        unblock_saves = asyncio.Event()
        saved_after_cancel: set[str] = set()
        blocking_serial = "d073d50000b5"

        class PartlyBlockingStorage:
            def load_device_state(self, serial):
                return None

            async def save_device_state(self, state):
                if state.serial == blocking_serial and not unblock_saves.is_set():
                    blocked_save_started.set()
                    await unblock_saves.wait()
                else:
                    saved_after_cancel.add(state.serial)

            async def delete_device_state(self, serial):
                return True

        storage = PartlyBlockingStorage()
        manager = DeviceManager(DeviceRepository())
        devices = [
            create_color_light("d073d50000b4", storage=storage),
            create_color_light(blocking_serial, storage=storage),
        ]
        for device in devices:
            manager.add_device(device)
        await blocked_save_started.wait()

        removal = asyncio.create_task(manager.remove_all_devices())
        await asyncio.sleep(0)
        removal.cancel()

        with pytest.raises(asyncio.CancelledError):
            await removal

        assert manager.get_all_devices() == devices
        assert all(device._background_tasks.accepting for device in devices)

        unblock_saves.set()
        saved_after_cancel.clear()
        for device in devices:
            device._save_state()

        async def wait_for_saves():
            while saved_after_cancel != {device.state.serial for device in devices}:
                await asyncio.sleep(0)

        await asyncio.wait_for(wait_for_saves(), timeout=1.0)
        for device in devices:
            await device.close()


class TestDeviceManagerCallbacks:
    """Test DeviceManager callback functionality."""

    def test_on_device_added_callback_invoked(self):
        """on_device_added callback is invoked when device is added."""
        callback = Mock()
        manager = DeviceManager(DeviceRepository(), on_device_added=callback)
        device = create_color_light("d073d5000001")

        manager.add_device(device)

        callback.assert_called_once_with(device)

    def test_on_device_added_not_called_on_duplicate(self):
        """on_device_added callback is not called when adding duplicate device."""
        callback = Mock()
        manager = DeviceManager(DeviceRepository(), on_device_added=callback)
        device = create_color_light("d073d5000001")

        manager.add_device(device)
        callback.reset_mock()

        # Adding duplicate should not trigger callback
        manager.add_device(device)
        callback.assert_not_called()

    def test_on_device_added_callback_exception_logged(self):
        """Exception in on_device_added callback is logged but doesn't prevent add."""
        callback = Mock(side_effect=Exception("callback error"))
        manager = DeviceManager(DeviceRepository(), on_device_added=callback)
        device = create_color_light("d073d5000001")

        # Should still succeed despite callback exception
        result = manager.add_device(device)
        assert result is True
        assert manager.count_devices() == 1

    async def test_on_device_removed_callback_invoked(self):
        """on_device_removed callback is invoked when device is removed."""
        callback = Mock()
        manager = DeviceManager(DeviceRepository(), on_device_removed=callback)
        device = create_color_light("d073d5000001")
        manager.add_device(device)

        await manager.remove_device("d073d5000001")

        callback.assert_called_once_with("d073d5000001")

    async def test_on_device_removed_not_called_on_nonexistent(self):
        """on_device_removed callback is not called when removing nonexistent device."""
        callback = Mock()
        manager = DeviceManager(DeviceRepository(), on_device_removed=callback)

        # Removing nonexistent device should not trigger callback
        await manager.remove_device("d073d5000001")
        callback.assert_not_called()

    async def test_on_device_removed_callback_exception_logged(self):
        """Exception in callback is logged but doesn't prevent remove."""
        callback = Mock(side_effect=Exception("callback error"))
        manager = DeviceManager(DeviceRepository(), on_device_removed=callback)
        device = create_color_light("d073d5000001")
        manager.add_device(device)

        # Should still succeed despite callback exception
        result = await manager.remove_device("d073d5000001")
        assert result is True
        assert manager.count_devices() == 0

    async def test_remove_all_devices_invokes_callback_for_each(self):
        """on_device_removed callback is invoked for each device when removing all."""
        callback = Mock()
        manager = DeviceManager(DeviceRepository(), on_device_removed=callback)

        # Add multiple devices
        manager.add_device(create_color_light("d073d5000001"))
        manager.add_device(create_color_light("d073d5000002"))
        manager.add_device(create_color_light("d073d5000003"))

        await manager.remove_all_devices()

        assert callback.call_count == 3
        # Verify all serials were passed to callback
        called_serials = {call.args[0] for call in callback.call_args_list}
        assert called_serials == {"d073d5000001", "d073d5000002", "d073d5000003"}

    async def test_both_callbacks_can_be_set(self):
        """Both on_device_added and on_device_removed callbacks can be set."""
        add_callback = Mock()
        remove_callback = Mock()
        manager = DeviceManager(
            DeviceRepository(),
            on_device_added=add_callback,
            on_device_removed=remove_callback,
        )
        device = create_color_light("d073d5000001")

        manager.add_device(device)
        add_callback.assert_called_once_with(device)
        remove_callback.assert_not_called()

        add_callback.reset_mock()
        await manager.remove_device("d073d5000001")
        add_callback.assert_not_called()
        remove_callback.assert_called_once_with("d073d5000001")


class TestTransportAwareTargetResolution:
    """Transport eligibility is decided at the public manager boundary."""

    @pytest.fixture
    def mixed_fleet(self):
        repository = DeviceRepository()
        manager = DeviceManager(repository)
        wifi_device = create_color_light("d073d5000101")
        thread_device = create_color_light(
            "d073d5000102", connectivity=Connectivity.THREAD
        )
        manager.add_device(wifi_device)
        manager.add_device(thread_device)
        return manager, wifi_device, thread_device

    def test_ipv4_broadcast_filters_thread_by_default(self, mixed_fleet, caplog):
        """Omitting family retains IPv4 semantics and filters Thread targets."""
        manager, wifi_device, _thread_device = mixed_fleet

        with caplog.at_level(logging.DEBUG, logger="lifx_emulator.devices.manager"):
            targets = manager.resolve_target_devices(
                _target_header("d073d5000101", tagged=True)
            )

        assert targets == [wifi_device]
        assert "d073d5000102" in caplog.text
        assert "IPv4" in caplog.text

    @pytest.mark.parametrize("connectivity", list(Connectivity))
    @pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
    @pytest.mark.parametrize(
        ("shape", "tagged", "zero_target"),
        [
            ("broadcast", True, True),
            ("zero", False, True),
            ("exact", False, False),
            ("mismatch", False, False),
            ("tagged", True, False),
        ],
    )
    def test_connectivity_family_target_decision_table(
        self,
        connectivity,
        family,
        shape,
        tagged,
        zero_target,
    ):
        """Cover WiFi/Thread x IPv4/IPv6 x every target shape."""
        serial = "d073d5000110"
        device = create_color_light(serial, connectivity=connectivity)
        manager = DeviceManager(DeviceRepository())
        manager.add_device(device)
        requested_serial = "d073d5000199" if shape == "mismatch" else serial
        header = _target_header(
            requested_serial,
            tagged=tagged,
            zero_target=zero_target,
        )

        targets = manager.resolve_target_devices(header, family=family)

        wifi_eligible = connectivity is Connectivity.WIFI and shape != "mismatch"
        thread_eligible = (
            connectivity is Connectivity.THREAD
            and family == socket.AF_INET6
            and shape == "exact"
        )
        assert targets == ([device] if wifi_eligible or thread_eligible else [])
        assert isinstance(targets, list)

    @pytest.mark.parametrize(
        ("family", "header", "reason"),
        [
            (socket.AF_INET, _target_header("d073d5000120"), "IPv4"),
            (
                socket.AF_INET6,
                _target_header("d073d5000120", tagged=True),
                "tagged",
            ),
            (
                socket.AF_INET6,
                _target_header("d073d5000120", zero_target=True),
                "broadcast",
            ),
            (
                socket.AF_INET6,
                _target_header("d073d5000121"),
                "does not match",
            ),
        ],
    )
    def test_thread_rejection_logs_concrete_reason(
        self, family, header, reason, caplog
    ):
        device = create_color_light("d073d5000120", connectivity="thread")
        manager = DeviceManager(DeviceRepository())
        manager.add_device(device)

        with caplog.at_level(logging.DEBUG, logger="lifx_emulator.devices.manager"):
            assert manager.resolve_target_devices(header, family=family) == []

        assert device.state.serial in caplog.text
        assert reason in caplog.text

    def test_repeated_interleaving_never_dispatches_rejected_thread_packets(
        self, mixed_fleet
    ):
        manager, _wifi_device, thread_device = mixed_fleet
        accepted = _target_header(thread_device.state.serial)
        rejected = [
            (accepted, socket.AF_INET),
            (
                _target_header(thread_device.state.serial, tagged=True),
                socket.AF_INET6,
            ),
            (
                _target_header(thread_device.state.serial, zero_target=True),
                socket.AF_INET6,
            ),
            (_target_header("d073d5000199"), socket.AF_INET6),
        ]

        with patch.object(
            thread_device, "process_packet", wraps=thread_device.process_packet
        ) as process_packet:
            for _ in range(2):
                for header, family in rejected:
                    for device in manager.resolve_target_devices(header, family=family):
                        device.process_packet(header, None)
                for device in manager.resolve_target_devices(
                    accepted, family=socket.AF_INET6
                ):
                    device.process_packet(accepted, None)

        assert process_packet.call_count == 2
