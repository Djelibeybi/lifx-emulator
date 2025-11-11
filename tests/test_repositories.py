"""Tests for repository implementations."""

import pytest

from lifx_emulator.factories import create_color_light, create_multizone_light
from lifx_emulator.repositories import DeviceRepository


class TestDeviceRepository:
    """Test DeviceRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a fresh device repository."""
        return DeviceRepository()

    @pytest.fixture
    def sample_devices(self):
        """Create sample devices for testing."""
        return [
            create_color_light("d073d5000001"),
            create_color_light("d073d5000002"),
            create_multizone_light("d073d5000003", zone_count=16),
        ]

    def test_add_device(self, repository, sample_devices):
        """Test adding a device to repository."""
        device = sample_devices[0]
        result = repository.add(device)
        assert result is True
        assert repository.count() == 1

    def test_add_duplicate_device(self, repository, sample_devices):
        """Test adding a duplicate device returns False."""
        device = sample_devices[0]
        result1 = repository.add(device)
        assert result1 is True

        # Adding same serial again should return False
        result2 = repository.add(device)
        assert result2 is False
        assert repository.count() == 1

    def test_remove_device(self, repository, sample_devices):
        """Test removing a device from repository."""
        device = sample_devices[0]
        repository.add(device)

        result = repository.remove("d073d5000001")
        assert result is True
        assert repository.count() == 0

    def test_remove_nonexistent_device(self, repository):
        """Test removing a non-existent device returns False."""
        result = repository.remove("d073d5999999")
        assert result is False

    def test_get_device(self, repository, sample_devices):
        """Test getting a device by serial."""
        device = sample_devices[0]
        repository.add(device)

        retrieved = repository.get("d073d5000001")
        assert retrieved is not None
        assert retrieved == device
        assert retrieved.state.serial == "d073d5000001"

    def test_get_nonexistent_device(self, repository):
        """Test getting a non-existent device returns None."""
        result = repository.get("d073d5999999")
        assert result is None

    def test_get_all_devices(self, repository, sample_devices):
        """Test getting all devices."""
        for device in sample_devices:
            repository.add(device)

        all_devices = repository.get_all()
        assert len(all_devices) == 3
        assert all([d in sample_devices for d in all_devices])

    def test_get_all_empty_repository(self, repository):
        """Test getting all devices from empty repository."""
        all_devices = repository.get_all()
        assert len(all_devices) == 0
        assert all_devices == []

    def test_clear_repository(self, repository, sample_devices):
        """Test clearing all devices from repository."""
        for device in sample_devices:
            repository.add(device)
        assert repository.count() == 3

        count = repository.clear()
        assert count == 3
        assert repository.count() == 0

    def test_clear_empty_repository(self, repository):
        """Test clearing an already empty repository."""
        count = repository.clear()
        assert count == 0

    def test_count_devices(self, repository, sample_devices):
        """Test counting devices in repository."""
        assert repository.count() == 0

        repository.add(sample_devices[0])
        assert repository.count() == 1

        repository.add(sample_devices[1])
        assert repository.count() == 2

        repository.remove("d073d5000001")
        assert repository.count() == 1

    def test_repository_persistence(self, repository, sample_devices):
        """Test that devices persist across operations."""
        # Add all devices
        for device in sample_devices:
            repository.add(device)

        # Remove one
        repository.remove("d073d5000001")

        # Verify remaining devices are still accessible
        device2 = repository.get("d073d5000002")
        device3 = repository.get("d073d5000003")
        assert device2 is not None
        assert device3 is not None
        assert device2 == sample_devices[1]
        assert device3 == sample_devices[2]
