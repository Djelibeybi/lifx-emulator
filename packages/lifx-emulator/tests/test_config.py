"""Tests for config file support."""


import pytest
import yaml
from lifx_emulator_app.config import (
    ENV_VAR,
    DeviceDefinition,
    EmulatorConfig,
    HsbkConfig,
    ScenarioDefinition,
    ScenariosConfig,
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


class TestHsbkConfig:
    """Test HsbkConfig model."""

    def test_default_values(self):
        """Test default HSBK values."""
        hsbk = HsbkConfig()
        assert hsbk.hue == 0
        assert hsbk.saturation == 0
        assert hsbk.brightness == 65535
        assert hsbk.kelvin == 3500

    def test_dict_form(self):
        """Test creating HSBK from dict."""
        hsbk = HsbkConfig(hue=21845, saturation=65535, brightness=65535, kelvin=3500)
        assert hsbk.hue == 21845
        assert hsbk.saturation == 65535

    def test_list_form(self):
        """Test creating HSBK from [h, s, b, k] list."""
        hsbk = HsbkConfig.model_validate([21845, 65535, 65535, 3500])
        assert hsbk.hue == 21845
        assert hsbk.saturation == 65535
        assert hsbk.brightness == 65535
        assert hsbk.kelvin == 3500

    def test_tuple_form(self):
        """Test creating HSBK from (h, s, b, k) tuple."""
        hsbk = HsbkConfig.model_validate((21845, 65535, 65535, 3500))
        assert hsbk.hue == 21845

    def test_list_wrong_length(self):
        """Test that list with wrong length is rejected."""
        with pytest.raises(ValueError, match="exactly 4 elements"):
            HsbkConfig.model_validate([1, 2, 3])

    def test_list_too_long(self):
        """Test that list with too many elements is rejected."""
        with pytest.raises(ValueError, match="exactly 4 elements"):
            HsbkConfig.model_validate([1, 2, 3, 4, 5])

    def test_hue_out_of_range(self):
        """Test that hue > 65535 is rejected."""
        with pytest.raises(ValueError, match="between 0 and 65535"):
            HsbkConfig(hue=70000)

    def test_negative_brightness(self):
        """Test that negative brightness is rejected."""
        with pytest.raises(ValueError, match="between 0 and 65535"):
            HsbkConfig(brightness=-1)

    def test_kelvin_too_low(self):
        """Test that kelvin below 1500 is rejected."""
        with pytest.raises(ValueError, match="between 1500 and 9000"):
            HsbkConfig(kelvin=1000)

    def test_kelvin_too_high(self):
        """Test that kelvin above 9000 is rejected."""
        with pytest.raises(ValueError, match="between 1500 and 9000"):
            HsbkConfig(kelvin=10000)

    def test_kelvin_boundary_values(self):
        """Test boundary kelvin values."""
        low = HsbkConfig(kelvin=1500)
        assert low.kelvin == 1500
        high = HsbkConfig(kelvin=9000)
        assert high.kelvin == 9000


class TestScenarioDefinition:
    """Test ScenarioDefinition model."""

    def test_empty_scenario(self):
        """Test that all fields default to None."""
        s = ScenarioDefinition()
        assert s.drop_packets is None
        assert s.response_delays is None
        assert s.malformed_packets is None
        assert s.send_unhandled is None

    def test_full_scenario(self):
        """Test scenario with all fields populated."""
        s = ScenarioDefinition(
            drop_packets={101: 1.0, 102: 0.5},
            response_delays={116: 0.2},
            malformed_packets=[506],
            invalid_field_values=[107],
            firmware_version=(3, 70),
            partial_responses=[512],
            send_unhandled=True,
        )
        assert s.drop_packets == {101: 1.0, 102: 0.5}
        assert s.response_delays == {116: 0.2}
        assert s.malformed_packets == [506]
        assert s.firmware_version == (3, 70)
        assert s.send_unhandled is True

    def test_string_keys_converted(self):
        """Test that string keys in drop_packets/response_delays are converted."""
        s = ScenarioDefinition.model_validate(
            {"drop_packets": {"101": 1.0}, "response_delays": {"116": "0.5"}}
        )
        assert s.drop_packets == {101: 1.0}
        assert s.response_delays == {116: 0.5}


class TestScenariosConfig:
    """Test ScenariosConfig model."""

    def test_empty_scenarios(self):
        """Test empty scenarios config."""
        s = ScenariosConfig()
        assert s.global_scenario is None
        assert s.devices is None

    def test_global_scenario_via_alias(self):
        """Test that 'global' alias works for global_scenario."""
        data = {"global": {"send_unhandled": True}}
        s = ScenariosConfig.model_validate(data)
        assert s.global_scenario is not None
        assert s.global_scenario.send_unhandled is True

    def test_all_scope_levels(self):
        """Test scenarios at all scope levels."""
        s = ScenariosConfig(
            global_scenario=ScenarioDefinition(send_unhandled=True),
            devices={"d073d5000001": ScenarioDefinition(drop_packets={101: 1.0})},
            types={"multizone": ScenarioDefinition(response_delays={506: 0.2})},
            locations={"Downstairs": ScenarioDefinition(malformed_packets=[506])},
            groups={"Lights": ScenarioDefinition(firmware_version=(2, 60))},
        )
        assert s.global_scenario.send_unhandled is True
        assert s.devices["d073d5000001"].drop_packets == {101: 1.0}
        assert s.types["multizone"].response_delays == {506: 0.2}
        assert s.locations["Downstairs"].malformed_packets == [506]
        assert s.groups["Lights"].firmware_version == (2, 60)


class TestExtendedDeviceDefinition:
    """Test new fields on DeviceDefinition."""

    def test_device_with_serial(self):
        """Test device with explicit serial."""
        dev = DeviceDefinition(product_id=27, serial="d073d5000001")
        assert dev.serial == "d073d5000001"

    def test_serial_validation_valid(self):
        """Test valid serial values."""
        dev = DeviceDefinition(product_id=27, serial="cafe00000001")
        assert dev.serial == "cafe00000001"

    def test_serial_validation_invalid_length(self):
        """Test serial with wrong length is rejected."""
        with pytest.raises(ValueError, match="12 hex characters"):
            DeviceDefinition(product_id=27, serial="abc")

    def test_serial_validation_invalid_chars(self):
        """Test serial with non-hex chars is rejected."""
        with pytest.raises(ValueError, match="12 hex characters"):
            DeviceDefinition(product_id=27, serial="gggggggggggg")

    def test_power_level_on(self):
        """Test power_level=65535 (on)."""
        dev = DeviceDefinition(product_id=27, power_level=65535)
        assert dev.power_level == 65535

    def test_power_level_off(self):
        """Test power_level=0 (off)."""
        dev = DeviceDefinition(product_id=27, power_level=0)
        assert dev.power_level == 0

    def test_power_level_invalid(self):
        """Test that intermediate power_level is rejected."""
        with pytest.raises(ValueError, match="0.*or.*65535"):
            DeviceDefinition(product_id=27, power_level=100)

    def test_color_dict_form(self):
        """Test device with color as dict."""
        dev = DeviceDefinition(
            product_id=27,
            color={
                "hue": 21845,
                "saturation": 65535,
                "brightness": 65535,
                "kelvin": 3500,
            },
        )
        assert dev.color is not None
        assert dev.color.hue == 21845

    def test_color_list_form(self):
        """Test device with color as [h, s, b, k] list."""
        dev = DeviceDefinition(
            product_id=27,
            color=[21845, 65535, 65535, 3500],
        )
        assert dev.color is not None
        assert dev.color.hue == 21845

    def test_location_and_group(self):
        """Test device with location and group labels."""
        dev = DeviceDefinition(product_id=27, location="Downstairs", group="Lights")
        assert dev.location == "Downstairs"
        assert dev.group == "Lights"

    def test_zone_colors(self):
        """Test device with zone_colors list."""
        dev = DeviceDefinition(
            product_id=32,
            zone_count=3,
            zone_colors=[
                [0, 65535, 65535, 3500],
                [21845, 65535, 65535, 3500],
                [43690, 65535, 65535, 3500],
            ],
        )
        assert dev.zone_colors is not None
        assert len(dev.zone_colors) == 3
        assert dev.zone_colors[0].hue == 0
        assert dev.zone_colors[1].hue == 21845

    def test_infrared_brightness(self):
        """Test device with infrared_brightness."""
        dev = DeviceDefinition(product_id=29, infrared_brightness=32768)
        assert dev.infrared_brightness == 32768

    def test_infrared_brightness_out_of_range(self):
        """Test infrared_brightness validation."""
        with pytest.raises(ValueError, match="between 0 and 65535"):
            DeviceDefinition(product_id=29, infrared_brightness=70000)

    def test_hev_fields(self):
        """Test device with HEV fields."""
        dev = DeviceDefinition(
            product_id=90,
            hev_cycle_duration=7200,
            hev_indication=True,
        )
        assert dev.hev_cycle_duration == 7200
        assert dev.hev_indication is True

    def test_hev_cycle_duration_negative(self):
        """Test negative hev_cycle_duration is rejected."""
        with pytest.raises(ValueError, match="non-negative"):
            DeviceDefinition(product_id=90, hev_cycle_duration=-1)

    def test_full_extended_device(self):
        """Test device with all new fields."""
        dev = DeviceDefinition(
            product_id=27,
            serial="d073d5000001",
            label="Living Room",
            power_level=65535,
            color=HsbkConfig(
                hue=21845, saturation=65535, brightness=65535, kelvin=3500
            ),
            location="Downstairs",
            group="Lights",
        )
        assert dev.serial == "d073d5000001"
        assert dev.label == "Living Room"
        assert dev.power_level == 65535
        assert dev.color.hue == 21845
        assert dev.location == "Downstairs"
        assert dev.group == "Lights"


class TestExtendedConfigLoad:
    """Test loading extended config from YAML."""

    def test_load_config_with_scenarios(self, tmp_path):
        """Test loading config file with scenarios section."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "color": 1,
                    "scenarios": {
                        "global": {"send_unhandled": True},
                        "devices": {
                            "d073d5000001": {"drop_packets": {"101": 1.0}},
                        },
                        "types": {
                            "multizone": {"response_delays": {"506": 0.2}},
                        },
                    },
                }
            )
        )
        config = load_config(config_file)
        assert config.scenarios is not None
        assert config.scenarios.global_scenario is not None
        assert config.scenarios.global_scenario.send_unhandled is True
        assert config.scenarios.devices is not None
        assert config.scenarios.devices["d073d5000001"].drop_packets == {101: 1.0}

    def test_load_config_with_extended_devices(self, tmp_path):
        """Test loading config with extended device definitions."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "devices": [
                        {
                            "product_id": 27,
                            "serial": "d073d5000001",
                            "label": "Living Room",
                            "power_level": 65535,
                            "color": {
                                "hue": 21845,
                                "saturation": 65535,
                                "brightness": 65535,
                                "kelvin": 3500,
                            },
                            "location": "Downstairs",
                            "group": "Lights",
                        },
                    ],
                }
            )
        )
        config = load_config(config_file)
        assert config.devices is not None
        assert len(config.devices) == 1
        dev = config.devices[0]
        assert dev.serial == "d073d5000001"
        assert dev.power_level == 65535
        assert dev.color is not None
        assert dev.color.hue == 21845
        assert dev.location == "Downstairs"

    def test_load_config_with_zone_colors_list_form(self, tmp_path):
        """Test loading config with zone_colors in compact list form."""
        config_file = tmp_path / "config.yaml"
        # Use raw YAML to test compact list notation
        config_file.write_text(
            "devices:\n"
            "  - product_id: 32\n"
            "    zone_count: 2\n"
            "    zone_colors:\n"
            "      - [0, 65535, 65535, 3500]\n"
            "      - [21845, 65535, 65535, 3500]\n"
        )
        config = load_config(config_file)
        assert config.devices is not None
        dev = config.devices[0]
        assert dev.zone_colors is not None
        assert len(dev.zone_colors) == 2
        assert dev.zone_colors[0].hue == 0
        assert dev.zone_colors[1].hue == 21845

    def test_round_trip_extended_config(self, tmp_path):
        """Test round-trip: create config, dump to YAML, load back."""
        original = EmulatorConfig(
            bind="10.0.0.1",
            port=56700,
            color=2,
            devices=[
                DeviceDefinition(
                    product_id=27,
                    serial="d073d5000001",
                    label="Test",
                    power_level=65535,
                    color=HsbkConfig(
                        hue=21845,
                        saturation=65535,
                        brightness=65535,
                        kelvin=3500,
                    ),
                    location="Room",
                    group="Group",
                ),
            ],
            scenarios=ScenariosConfig(
                global_scenario=ScenarioDefinition(send_unhandled=True),
            ),
        )

        config_file = tmp_path / "config.yaml"
        dumped = original.model_dump(exclude_none=True, by_alias=True)
        config_file.write_text(yaml.dump(dumped))

        loaded = load_config(config_file)
        assert loaded.bind == "10.0.0.1"
        assert loaded.devices is not None
        assert loaded.devices[0].serial == "d073d5000001"
        assert loaded.devices[0].color is not None
        assert loaded.devices[0].color.hue == 21845
        assert loaded.scenarios is not None
        assert loaded.scenarios.global_scenario is not None
        assert loaded.scenarios.global_scenario.send_unhandled is True
