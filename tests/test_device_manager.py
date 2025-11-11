"""Tests for DeviceManager class."""

import pytest

from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light, create_multizone_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.repositories import DeviceRepository


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

    def test_remove_device(self, device_manager, sample_devices):
        """Test removing a device."""
        device = sample_devices[0]
        device_manager.add_device(device)
        assert device_manager.count_devices() == 1

        device_manager.remove_device("d073d5000001")
        assert device_manager.count_devices() == 0
        assert device_manager.get_device("d073d5000001") is None

    def test_remove_nonexistent_device(self, device_manager):
        """Test removing a non-existent device returns False."""
        result = device_manager.remove_device("d073d5999999")
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
        from lifx_emulator.scenarios.manager import ScenarioConfig

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
        from lifx_emulator.scenarios.manager import (
            HierarchicalScenarioManager,
            ScenarioConfig,
        )

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

    def test_remove_device_with_storage(self, device_manager, sample_devices):
        """Test removing a device with storage cleanup."""
        from unittest.mock import Mock

        device = sample_devices[0]
        device_manager.add_device(device)

        # Create mock storage
        mock_storage = Mock()
        mock_storage.delete_device_state = Mock()

        # Remove device with storage
        result = device_manager.remove_device("d073d5000001", storage=mock_storage)
        assert result is True

        # Verify storage deletion was called
        mock_storage.delete_device_state.assert_called_once_with("d073d5000001")

    def test_remove_all_devices(self, device_manager, sample_devices):
        """Test removing all devices."""
        for device in sample_devices:
            device_manager.add_device(device)
        assert device_manager.count_devices() == 3

        # Remove all devices
        count = device_manager.remove_all_devices()
        assert count == 3
        assert device_manager.count_devices() == 0

    def test_remove_all_devices_with_storage(self, device_manager, sample_devices):
        """Test removing all devices with storage cleanup."""
        from unittest.mock import Mock

        for device in sample_devices:
            device_manager.add_device(device)

        # Create mock storage
        mock_storage = Mock()
        mock_storage.delete_all_device_states = Mock(return_value=3)

        # Remove all with storage deletion
        count = device_manager.remove_all_devices(
            delete_storage=True, storage=mock_storage
        )
        assert count == 3

        # Verify storage deletion was called
        mock_storage.delete_all_device_states.assert_called_once()

    def test_remove_all_devices_no_storage_deletion(
        self, device_manager, sample_devices
    ):
        """Test removing all devices without storage deletion."""
        from unittest.mock import Mock

        for device in sample_devices:
            device_manager.add_device(device)

        # Create mock storage (should not be called)
        mock_storage = Mock()
        mock_storage.delete_all_device_states = Mock()

        # Remove all without storage deletion
        count = device_manager.remove_all_devices(
            delete_storage=False, storage=mock_storage
        )
        assert count == 3

        # Verify storage deletion was NOT called
        mock_storage.delete_all_device_states.assert_not_called()
