"""Tests for export-config subcommand."""

import json

import yaml
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator_app.__main__ import (
    _clean_scenario,
    _device_state_to_yaml_dict,
    _scenarios_to_yaml_dict,
    export_config,
)
from lifx_emulator_app.config import EmulatorConfig


class TestDeviceStateToYamlDict:
    """Test _device_state_to_yaml_dict conversion."""

    def test_minimal_device(self):
        """Minimal device state produces product_id and serial."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["product_id"] == 27
        assert result["serial"] == "d073d5000001"
        assert "label" not in result
        assert "power_level" not in result
        assert "location" not in result
        assert "group" not in result

    def test_device_with_label_and_power(self):
        """Label and power_level are included when non-default."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "Kitchen Light",
            "power_level": 65535,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["label"] == "Kitchen Light"
        assert result["power_level"] == 65535

    def test_device_with_color_dict(self):
        """Color from dict format is converted to list."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "color": {
                "hue": 21845,
                "saturation": 65535,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["color"] == [21845, 65535, 65535, 3500]

    def test_device_with_color_dataclass(self):
        """Color from LightHsbk dataclass is converted to list."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "color": LightHsbk(
                hue=21845, saturation=65535,
                brightness=65535, kelvin=3500,
            ),
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["color"] == [21845, 65535, 65535, 3500]

    def test_device_with_location_and_group(self):
        """Non-default location and group are included."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "location_label": "Office",
            "group_label": "Lights",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["location"] == "Office"
        assert result["group"] == "Lights"

    def test_device_default_location_excluded(self):
        """Default 'Test Location' and 'Test Group' are excluded."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert "location" not in result
        assert "group" not in result

    def test_multizone_with_varied_zone_colors(self):
        """Multizone with varied zone colors includes zone_colors."""
        state = {
            "product": 38,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_multizone": True,
            "zone_count": 3,
            "zone_colors": [
                LightHsbk(hue=0, saturation=65535, brightness=65535, kelvin=3500),
                LightHsbk(hue=21845, saturation=65535, brightness=65535, kelvin=3500),
                LightHsbk(hue=43690, saturation=65535, brightness=65535, kelvin=3500),
            ],
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert "zone_colors" in result
        assert len(result["zone_colors"]) == 3
        assert result["zone_colors"][0] == [0, 65535, 65535, 3500]
        assert result["zone_count"] == 3

    def test_multizone_with_uniform_colors_omits_zone_colors(self):
        """Multizone with all same zone colors omits zone_colors."""
        same_color = LightHsbk(
            hue=21845, saturation=65535, brightness=65535, kelvin=3500,
        )
        state = {
            "product": 38,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_multizone": True,
            "zone_count": 8,
            "zone_colors": [same_color] * 8,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert "zone_colors" not in result
        assert result["zone_count"] == 8

    def test_infrared_device(self):
        """Infrared brightness is included when non-zero."""
        state = {
            "product": 29,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_infrared": True,
            "infrared_brightness": 32768,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["infrared_brightness"] == 32768

    def test_infrared_zero_excluded(self):
        """Zero infrared brightness is excluded."""
        state = {
            "product": 29,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_infrared": True,
            "infrared_brightness": 0,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert "infrared_brightness" not in result

    def test_hev_device_non_default(self):
        """HEV fields included when non-default."""
        state = {
            "product": 90,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_hev": True,
            "hev_cycle_duration_s": 3600,
            "hev_indication": False,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["hev_cycle_duration"] == 3600
        assert result["hev_indication"] is False

    def test_hev_default_values_excluded(self):
        """Default HEV values are excluded."""
        state = {
            "product": 90,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_hev": True,
            "hev_cycle_duration_s": 7200,
            "hev_indication": True,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert "hev_cycle_duration" not in result
        assert "hev_indication" not in result

    def test_matrix_device(self):
        """Tile/matrix fields are included."""
        state = {
            "product": 55,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "has_matrix": True,
            "tile_count": 5,
            "tile_width": 8,
            "tile_height": 8,
            "location_label": "Test Location",
            "group_label": "Test Group",
        }
        result = _device_state_to_yaml_dict(state)
        assert result["tile_count"] == 5
        assert result["tile_width"] == 8
        assert result["tile_height"] == 8


class TestCleanScenario:
    """Test _clean_scenario helper."""

    def test_removes_empty_dicts(self):
        """Empty dict values are removed."""
        result = _clean_scenario({
            "drop_packets": {},
            "response_delays": {},
            "malformed_packets": [],
        })
        assert result is None

    def test_removes_none_values(self):
        """None values are removed."""
        result = _clean_scenario({
            "drop_packets": None,
            "firmware_version": None,
        })
        assert result is None

    def test_keeps_meaningful_values(self):
        """Non-empty values are kept."""
        result = _clean_scenario({
            "drop_packets": {"101": 1.0},
            "send_unhandled": True,
        })
        assert result == {"drop_packets": {101: 1.0}, "send_unhandled": True}

    def test_converts_string_keys(self):
        """String keys in drop_packets/response_delays become ints."""
        result = _clean_scenario({
            "drop_packets": {"101": 0.5, "116": 1.0},
            "response_delays": {"506": 0.2},
        })
        assert result["drop_packets"] == {101: 0.5, 116: 1.0}
        assert result["response_delays"] == {506: 0.2}


class TestScenariosToYamlDict:
    """Test _scenarios_to_yaml_dict function."""

    def test_missing_file_returns_none(self, tmp_path):
        """Non-existent file returns None."""
        result = _scenarios_to_yaml_dict(tmp_path / "scenarios.json")
        assert result is None

    def test_empty_scenarios_returns_none(self, tmp_path):
        """All-empty scenarios returns None."""
        path = tmp_path / "scenarios.json"
        path.write_text(json.dumps({
            "global": {},
            "devices": {},
            "types": {},
        }))
        result = _scenarios_to_yaml_dict(path)
        assert result is None

    def test_global_scenario(self, tmp_path):
        """Global scenario is included."""
        path = tmp_path / "scenarios.json"
        path.write_text(json.dumps({
            "global": {"drop_packets": {"101": 1.0}},
            "devices": {},
        }))
        result = _scenarios_to_yaml_dict(path)
        assert result is not None
        assert result["global"]["drop_packets"] == {101: 1.0}

    def test_device_scenarios(self, tmp_path):
        """Device-scoped scenarios are included."""
        path = tmp_path / "scenarios.json"
        path.write_text(json.dumps({
            "global": {},
            "devices": {
                "d073d5000001": {"send_unhandled": True},
            },
            "types": {},
        }))
        result = _scenarios_to_yaml_dict(path)
        assert result is not None
        assert "d073d5000001" in result["devices"]

    def test_invalid_json_returns_none(self, tmp_path):
        """Invalid JSON returns None."""
        path = tmp_path / "scenarios.json"
        path.write_text("not valid json")
        result = _scenarios_to_yaml_dict(path)
        assert result is None


class TestExportConfigCommand:
    """Test the export_config CLI command."""

    def test_empty_storage_dir(self, tmp_path, capsys):
        """Empty storage directory prints message."""
        export_config(storage_dir=str(tmp_path))
        captured = capsys.readouterr()
        assert "No persistent device states found" in captured.out

    def test_missing_storage_dir(self, tmp_path, capsys):
        """Non-existent storage directory prints message."""
        missing = tmp_path / "nonexistent"
        export_config(storage_dir=str(missing))
        captured = capsys.readouterr()
        assert "Storage directory not found" in captured.out

    def test_export_single_device(self, tmp_path, capsys):
        """Single device state exports as valid YAML."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "Test Light",
            "power_level": 65535,
            "color": {
                "hue": 21845,
                "saturation": 65535,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Office",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Lights",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        export_config(storage_dir=str(tmp_path))
        captured = capsys.readouterr()

        # Parse the YAML output
        config = yaml.safe_load(captured.out)
        assert config is not None
        assert len(config["devices"]) == 1

        device = config["devices"][0]
        assert device["product_id"] == 27
        assert device["serial"] == "d073d5000001"
        assert device["label"] == "Test Light"
        assert device["power_level"] == 65535
        assert device["color"] == [21845, 65535, 65535, 3500]
        assert device["location"] == "Office"
        assert device["group"] == "Lights"

    def test_export_to_file(self, tmp_path):
        """Export writes to file when --output specified."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "Test",
            "power_level": 0,
            "color": {
                "hue": 0,
                "saturation": 0,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Test Location",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Test Group",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        output_file = tmp_path / "output.yaml"
        export_config(
            storage_dir=str(tmp_path),
            output=str(output_file),
        )

        assert output_file.exists()
        config = yaml.safe_load(output_file.read_text())
        assert len(config["devices"]) == 1

    def test_export_with_scenarios(self, tmp_path, capsys):
        """Scenarios are included by default."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "color": {
                "hue": 0,
                "saturation": 0,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Test Location",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Test Group",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        scenarios = {
            "global": {"drop_packets": {"101": 1.0}},
            "devices": {},
            "types": {},
            "locations": {},
            "groups": {},
        }
        (tmp_path / "scenarios.json").write_text(json.dumps(scenarios))

        export_config(storage_dir=str(tmp_path))
        captured = capsys.readouterr()

        config = yaml.safe_load(captured.out)
        assert "scenarios" in config
        assert config["scenarios"]["global"]["drop_packets"] == {101: 1.0}

    def test_export_no_scenarios_flag(self, tmp_path, capsys):
        """--no-scenarios excludes scenarios from output."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "color": {
                "hue": 0,
                "saturation": 0,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Test Location",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Test Group",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        scenarios = {"global": {"drop_packets": {"101": 1.0}}}
        (tmp_path / "scenarios.json").write_text(json.dumps(scenarios))

        export_config(
            storage_dir=str(tmp_path),
            no_scenarios=True,
        )
        captured = capsys.readouterr()

        config = yaml.safe_load(captured.out)
        assert "scenarios" not in config

    def test_round_trip_export_load(self, tmp_path):
        """Exported YAML can be loaded as a valid EmulatorConfig."""
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "Round Trip",
            "power_level": 65535,
            "color": {
                "hue": 21845,
                "saturation": 65535,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Office",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Lights",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        output_file = tmp_path / "output.yaml"
        export_config(
            storage_dir=str(tmp_path),
            output=str(output_file),
        )

        # Load the exported file as EmulatorConfig
        raw = yaml.safe_load(output_file.read_text())
        config = EmulatorConfig.model_validate(raw)
        assert config.devices is not None
        assert len(config.devices) == 1
        assert config.devices[0].product_id == 27
        assert config.devices[0].serial == "d073d5000001"
        assert config.devices[0].label == "Round Trip"
        assert config.devices[0].power_level == 65535
        assert config.devices[0].color is not None
        assert config.devices[0].color.hue == 21845
        assert config.devices[0].location == "Office"

    def test_export_multiple_devices(self, tmp_path, capsys):
        """Multiple device files are all exported."""
        for i in range(3):
            state = {
                "product": 27,
                "serial": f"d073d500000{i + 1}",
                "label": f"Light {i + 1}",
                "power_level": 0,
                "color": {
                    "hue": 0,
                    "saturation": 0,
                    "brightness": 65535,
                    "kelvin": 3500,
                },
                "location_id": "00" * 16,
                "location_label": "Test Location",
                "location_updated_at": 1000000000,
                "group_id": "00" * 16,
                "group_label": "Test Group",
                "group_updated_at": 1000000000,
                "has_color": True,
                "has_infrared": False,
                "has_multizone": False,
                "has_matrix": False,
                "has_hev": False,
            }
            fname = f"d073d500000{i + 1}.json"
            (tmp_path / fname).write_text(json.dumps(state))

        export_config(storage_dir=str(tmp_path))
        captured = capsys.readouterr()

        config = yaml.safe_load(captured.out)
        assert len(config["devices"]) == 3

    def test_bad_device_file_skipped(self, tmp_path, capsys):
        """Corrupt device file is skipped with warning."""
        (tmp_path / "bad_serial.json").write_text("not valid json")

        # Also add a valid one
        state = {
            "product": 27,
            "serial": "d073d5000001",
            "label": "",
            "power_level": 0,
            "color": {
                "hue": 0,
                "saturation": 0,
                "brightness": 65535,
                "kelvin": 3500,
            },
            "location_id": "00" * 16,
            "location_label": "Test Location",
            "location_updated_at": 1000000000,
            "group_id": "00" * 16,
            "group_label": "Test Group",
            "group_updated_at": 1000000000,
            "has_color": True,
            "has_infrared": False,
            "has_multizone": False,
            "has_matrix": False,
            "has_hev": False,
        }
        (tmp_path / "d073d5000001.json").write_text(json.dumps(state))

        export_config(storage_dir=str(tmp_path))
        captured = capsys.readouterr()

        assert "Warning:" in captured.out
