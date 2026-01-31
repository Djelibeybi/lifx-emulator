"""Tests for config file support."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from lifx_emulator_app.config import (
    ENV_VAR,
    DeviceDefinition,
    EmulatorConfig,
    load_config,
    merge_config,
    resolve_config_path,
)


class TestEmulatorConfig:
    """Test EmulatorConfig Pydantic model."""

    def test_empty_config(self):
        """Test that an empty config is valid."""
        config = EmulatorConfig()
        assert config.bind is None
        assert config.color is None
        assert config.devices is None

    def test_full_config(self):
        """Test a fully populated config."""
        config = EmulatorConfig(
            bind="192.168.1.100",
            port=56700,
            verbose=True,
            persistent=True,
            api=True,
            api_host="0.0.0.0",
            api_port=9090,
            color=3,
            multizone=1,
            multizone_zones=24,
            serial_prefix="cafe00",
            products=[27, 32],
            devices=[
                DeviceDefinition(product_id=27, label="Living Room"),
                DeviceDefinition(product_id=32, zone_count=16),
            ],
        )
        assert config.bind == "192.168.1.100"
        assert config.color == 3
        assert len(config.devices) == 2
        assert config.devices[0].label == "Living Room"
        assert config.products == [27, 32]

    def test_extra_fields_rejected(self):
        """Test that unknown fields are rejected."""
        with pytest.raises(Exception):
            EmulatorConfig(unknown_field="value")

    def test_serial_prefix_validation_valid(self):
        """Test valid serial prefix."""
        config = EmulatorConfig(serial_prefix="cafe00")
        assert config.serial_prefix == "cafe00"

    def test_serial_prefix_validation_invalid_length(self):
        """Test that serial prefix with wrong length is rejected."""
        with pytest.raises(ValueError, match="6 hex characters"):
            EmulatorConfig(serial_prefix="abc")

    def test_serial_prefix_validation_invalid_chars(self):
        """Test that serial prefix with non-hex chars is rejected."""
        with pytest.raises(ValueError, match="6 hex characters"):
            EmulatorConfig(serial_prefix="gggggg")


class TestDeviceDefinition:
    """Test DeviceDefinition model."""

    def test_minimal_device(self):
        """Test device with only product_id."""
        dev = DeviceDefinition(product_id=27)
        assert dev.product_id == 27
        assert dev.label is None
        assert dev.zone_count is None

    def test_full_device(self):
        """Test device with all fields."""
        dev = DeviceDefinition(
            product_id=55,
            label="Art Wall",
            tile_count=5,
            tile_width=8,
            tile_height=8,
        )
        assert dev.product_id == 55
        assert dev.label == "Art Wall"
        assert dev.tile_count == 5


class TestResolveConfigPath:
    """Test config file resolution."""

    def test_explicit_flag_existing_file(self, tmp_path):
        """Test --config flag with existing file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("bind: 127.0.0.1\n")

        result = resolve_config_path(str(config_file))
        assert result == config_file

    def test_explicit_flag_missing_file(self):
        """Test --config flag with nonexistent file."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            resolve_config_path("/nonexistent/config.yaml")

    def test_env_var(self, tmp_path, monkeypatch):
        """Test LIFX_EMULATOR_CONFIG env var."""
        config_file = tmp_path / "env-config.yaml"
        config_file.write_text("bind: 127.0.0.1\n")
        monkeypatch.setenv(ENV_VAR, str(config_file))

        result = resolve_config_path(None)
        assert result == config_file

    def test_env_var_missing_file(self, monkeypatch):
        """Test LIFX_EMULATOR_CONFIG env var with nonexistent file."""
        monkeypatch.setenv(ENV_VAR, "/nonexistent/config.yaml")
        with pytest.raises(FileNotFoundError, match=ENV_VAR):
            resolve_config_path(None)

    def test_auto_detect_yaml(self, tmp_path, monkeypatch):
        """Test auto-detection of lifx-emulator.yaml in cwd."""
        config_file = tmp_path / "lifx-emulator.yaml"
        config_file.write_text("color: 2\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(ENV_VAR, raising=False)

        result = resolve_config_path(None)
        assert result == config_file

    def test_auto_detect_yml(self, tmp_path, monkeypatch):
        """Test auto-detection of lifx-emulator.yml in cwd."""
        config_file = tmp_path / "lifx-emulator.yml"
        config_file.write_text("color: 2\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(ENV_VAR, raising=False)

        result = resolve_config_path(None)
        assert result == config_file

    def test_auto_detect_yaml_preferred_over_yml(self, tmp_path, monkeypatch):
        """Test that .yaml is preferred over .yml."""
        yaml_file = tmp_path / "lifx-emulator.yaml"
        yml_file = tmp_path / "lifx-emulator.yml"
        yaml_file.write_text("color: 1\n")
        yml_file.write_text("color: 2\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(ENV_VAR, raising=False)

        result = resolve_config_path(None)
        assert result == yaml_file

    def test_no_config_found(self, tmp_path, monkeypatch):
        """Test that None is returned when no config file exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(ENV_VAR, raising=False)

        result = resolve_config_path(None)
        assert result is None

    def test_flag_overrides_env_var(self, tmp_path, monkeypatch):
        """Test that --config flag takes priority over env var."""
        flag_file = tmp_path / "flag.yaml"
        env_file = tmp_path / "env.yaml"
        flag_file.write_text("color: 1\n")
        env_file.write_text("color: 2\n")
        monkeypatch.setenv(ENV_VAR, str(env_file))

        result = resolve_config_path(str(flag_file))
        assert result == flag_file

    def test_env_var_overrides_auto_detect(self, tmp_path, monkeypatch):
        """Test that env var takes priority over auto-detection."""
        env_file = tmp_path / "custom.yaml"
        auto_file = tmp_path / "lifx-emulator.yaml"
        env_file.write_text("color: 1\n")
        auto_file.write_text("color: 2\n")
        monkeypatch.setenv(ENV_VAR, str(env_file))
        monkeypatch.chdir(tmp_path)

        result = resolve_config_path(None)
        assert result == env_file


class TestLoadConfig:
    """Test config file loading."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "bind": "192.168.1.100",
                    "port": 56700,
                    "color": 2,
                    "multizone": 1,
                    "devices": [
                        {"product_id": 27, "label": "Test Light"},
                    ],
                }
            )
        )

        config = load_config(config_file)
        assert config.bind == "192.168.1.100"
        assert config.port == 56700
        assert config.color == 2
        assert config.multizone == 1
        assert len(config.devices) == 1
        assert config.devices[0].label == "Test Light"

    def test_load_empty_file(self, tmp_path):
        """Test loading an empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = load_config(config_file)
        assert config.bind is None
        assert config.color is None

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("{{invalid yaml")

        with pytest.raises(Exception):
            load_config(config_file)

    def test_load_non_dict_yaml(self, tmp_path):
        """Test loading YAML that is not a mapping."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="YAML mapping"):
            load_config(config_file)

    def test_load_unknown_fields(self, tmp_path):
        """Test that unknown fields in config raise validation error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"unknown_key": "value"}))

        with pytest.raises(Exception):
            load_config(config_file)


class TestMergeConfig:
    """Test config merging logic."""

    def test_defaults_when_no_config_or_cli(self):
        """Test that defaults are returned when config is empty and no CLI overrides."""
        config = EmulatorConfig()
        result = merge_config(config, {})

        assert result["bind"] == "127.0.0.1"
        assert result["port"] == 56700
        assert result["verbose"] is False
        assert result["color"] == 0
        assert result["multizone"] == 0
        assert result["serial_prefix"] == "d073d5"

    def test_config_overrides_defaults(self):
        """Test that config file values override defaults."""
        config = EmulatorConfig(bind="10.0.0.1", color=3, verbose=True)
        result = merge_config(config, {})

        assert result["bind"] == "10.0.0.1"
        assert result["color"] == 3
        assert result["verbose"] is True
        # Unset values should still be defaults
        assert result["port"] == 56700
        assert result["multizone"] == 0

    def test_cli_overrides_config(self):
        """Test that CLI values override config file values."""
        config = EmulatorConfig(bind="10.0.0.1", color=3, port=12345)
        cli = {"bind": "192.168.1.1", "port": None, "color": 5}
        result = merge_config(config, cli)

        # CLI overrides config
        assert result["bind"] == "192.168.1.1"
        assert result["color"] == 5
        # CLI None does not override config
        assert result["port"] == 12345

    def test_cli_overrides_defaults(self):
        """Test that CLI values override defaults."""
        config = EmulatorConfig()
        cli = {"color": 2, "verbose": True}
        result = merge_config(config, cli)

        assert result["color"] == 2
        assert result["verbose"] is True
        assert result["bind"] == "127.0.0.1"

    def test_full_merge_priority(self):
        """Test three-layer merge: CLI > config > defaults."""
        config = EmulatorConfig(
            bind="10.0.0.1",
            port=12345,
            color=3,
            multizone=2,
        )
        cli = {"bind": "192.168.1.1", "port": None, "color": None, "multizone": 5}
        result = merge_config(config, cli)

        assert result["bind"] == "192.168.1.1"  # CLI wins
        assert result["port"] == 12345  # Config wins (CLI is None)
        assert result["color"] == 3  # Config wins (CLI is None)
        assert result["multizone"] == 5  # CLI wins
        assert result["verbose"] is False  # Default

    def test_products_merge(self):
        """Test that products list merges correctly."""
        config = EmulatorConfig(products=[27, 32])
        cli = {"products": [55]}
        result = merge_config(config, cli)

        # CLI overrides entire products list
        assert result["products"] == [55]

    def test_products_from_config_only(self):
        """Test products from config when CLI doesn't specify."""
        config = EmulatorConfig(products=[27, 32])
        result = merge_config(config, {})

        assert result["products"] == [27, 32]
