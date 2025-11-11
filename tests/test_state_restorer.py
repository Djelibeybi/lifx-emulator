"""Tests for state restoration."""

from lifx_emulator.devices.state_restorer import NullStateRestorer, StateRestorer
from lifx_emulator.factories import (
    create_color_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk


class MockStorage:
    """Mock storage for testing state restoration."""

    def __init__(self, saved_states=None):
        """Initialize with optional saved states."""
        self.saved_states = saved_states or {}

    def load_device_state(self, serial):
        """Load device state or return None."""
        return self.saved_states.get(serial)


class TestStateRestorer:
    """Test state restoration functionality."""

    def test_restore_with_no_storage(self):
        """Test restoration when storage is None."""
        device = create_color_light("d073d5000001", storage=None)
        restorer = StateRestorer(None)
        result = restorer.restore_if_available(device.state)
        assert result is device.state

    def test_restore_with_no_saved_state(self):
        """Test restoration when device has no saved state."""
        device = create_color_light("d073d5000001")
        storage = MockStorage({})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result is device.state

    def test_restore_with_product_mismatch(self):
        """Test restoration skipped when product doesn't match."""
        device = create_color_light("d073d5000001")
        saved_state = {
            "product": 999,  # Different product
            "label": "Saved Label",
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        restorer.restore_if_available(device.state)
        # Should not have restored the label
        assert device.state.label != "Saved Label"

    def test_restore_core_state(self):
        """Test restoration of core device state."""
        device = create_color_light("d073d5000001")
        saved_state = {
            "product": device.state.product,
            "label": "My Light",
            "power_level": 32768,
            "color": LightHsbk(
                hue=10000, saturation=50000, brightness=40000, kelvin=4000
            ),
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.label == "My Light"
        assert result.power_level == 32768
        assert result.color.hue == 10000
        assert result.color.saturation == 50000
        assert result.color.brightness == 40000
        assert result.color.kelvin == 4000

    def test_restore_location_and_group(self):
        """Test restoration of location and group metadata."""
        device = create_color_light("d073d5000001")
        saved_state = {
            "product": device.state.product,
            "location_id": "abc123",
            "location_label": "Living Room",
            "location_updated_at": 1234567890,
            "group_id": "def456",
            "group_label": "Downstairs",
            "group_updated_at": 1234567891,
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.location_label == "Living Room"
        assert result.group_label == "Downstairs"
        assert result.location_id == "abc123"
        assert result.group_id == "def456"

    def test_restore_infrared_state(self):
        """Test restoration of infrared state."""
        device = create_infrared_light("d073d5000001")
        saved_state = {
            "product": device.state.product,
            "infrared_brightness": 25000,
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.infrared_brightness == 25000

    def test_restore_hev_state(self):
        """Test restoration of HEV state."""
        device = create_hev_light("d073d5000001")
        saved_state = {
            "product": device.state.product,
            "hev_cycle_duration_s": 3600,
            "hev_cycle_remaining_s": 1800,
            "hev_cycle_last_power": 1,
            "hev_indication": 1,
            "hev_last_result": 1,
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.hev_cycle_duration_s == 3600
        assert result.hev_cycle_remaining_s == 1800
        assert result.hev_cycle_last_power == 1
        assert result.hev_indication == 1
        assert result.hev_last_result == 1

    def test_restore_multizone_state(self):
        """Test restoration of multizone state."""
        device = create_multizone_light("d073d5000001", zone_count=4)
        zone_colors = [
            LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=16384, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=32768, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=49152, saturation=65535, brightness=32768, kelvin=3500),
        ]
        saved_state = {
            "product": device.state.product,
            "zone_count": 4,
            "zone_colors": zone_colors,
            "multizone_effect_type": 2,
            "multizone_effect_speed": 5,
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.zone_count == 4
        assert len(result.zone_colors) == 4
        assert result.zone_colors[0].hue == 0
        assert result.zone_colors[1].hue == 16384
        assert result.multizone_effect_type == 2

    def test_restore_multizone_zone_mismatch(self):
        """Test multizone restoration skipped when zone count doesn't match."""
        device = create_multizone_light("d073d5000001", zone_count=4)
        zone_colors = [
            LightHsbk(hue=0, saturation=65535, brightness=32768, kelvin=3500),
            LightHsbk(hue=16384, saturation=65535, brightness=32768, kelvin=3500),
        ]  # Only 2 zones, but device has 4
        saved_state = {
            "product": device.state.product,
            "zone_count": 4,
            "zone_colors": zone_colors,
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        # Should not restore mismatched zones
        restorer.restore_if_available(device.state)

    def test_restore_matrix_state(self):
        """Test restoration of matrix (tile) state."""
        device = create_tile_device("d073d5000001", tile_count=2)
        saved_state = {
            "product": device.state.product,
            "tile_count": 2,
            "tile_width": 8,
            "tile_height": 8,
            "tile_devices": [
                {"width": 8, "height": 8, "colors": [], "user_x": 0.0, "user_y": 0.0},
                {"width": 8, "height": 8, "colors": [], "user_x": 100.0, "user_y": 0.0},
            ],
            "tile_effect_type": 0,
            "tile_effect_speed": 0,
            "tile_effect_palette_count": 16,
            "tile_effect_palette": [],
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.tile_count == 2
        assert result.tile_width == 8
        assert result.tile_height == 8
        assert len(result.tile_devices) == 2

    def test_restore_matrix_tile_count_mismatch(self):
        """Test matrix restoration skipped when tile count doesn't match."""
        device = create_tile_device("d073d5000001", tile_count=2)
        saved_state = {
            "product": device.state.product,
            "tile_count": 2,
            "tile_width": 8,
            "tile_height": 8,
            "tile_devices": [
                {"width": 8, "height": 8, "colors": [], "user_x": 0.0, "user_y": 0.0},
            ],  # Only 1 tile, but device has 2
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        # Should not restore mismatched tiles
        restorer.restore_if_available(device.state)

    def test_restore_matrix_tile_dimensions_mismatch(self):
        """Test matrix restoration skipped when tile dimensions don't match."""
        device = create_tile_device("d073d5000001", tile_count=2)
        saved_state = {
            "product": device.state.product,
            "tile_count": 2,
            "tile_width": 8,
            "tile_height": 8,
            "tile_devices": [
                {
                    "width": 16,
                    "height": 8,
                    "colors": [],
                    "user_x": 0.0,
                    "user_y": 0.0,
                },  # Wrong width
                {
                    "width": 16,
                    "height": 8,
                    "colors": [],
                    "user_x": 100.0,
                    "user_y": 0.0,
                },
            ],
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        # Should not restore mismatched dimensions
        restorer.restore_if_available(device.state)

    def test_restore_partial_state(self):
        """Test restoration with only some fields present."""
        device = create_color_light("d073d5000001")
        original_label = device.state.label
        saved_state = {
            "product": device.state.product,
            "power_level": 20000,
            # Not providing label - should keep original
        }
        storage = MockStorage({"d073d5000001": saved_state})
        restorer = StateRestorer(storage)
        result = restorer.restore_if_available(device.state)
        assert result.power_level == 20000
        assert result.label == original_label  # Unchanged


class TestNullStateRestorer:
    """Test no-op state restorer."""

    def test_null_restorer_returns_state_unchanged(self):
        """Test that NullStateRestorer returns state unchanged."""
        device = create_color_light("d073d5000001")
        original_label = device.state.label
        restorer = NullStateRestorer()
        result = restorer.restore_if_available(device.state)
        assert result is device.state
        assert result.label == original_label
