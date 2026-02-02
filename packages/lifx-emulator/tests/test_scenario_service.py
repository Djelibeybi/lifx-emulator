"""Unit tests for ScenarioService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from lifx_emulator.scenarios import ScenarioConfig
from lifx_emulator_app.api.services.scenario_service import (
    InvalidDeviceSerialError,
    ScenarioNotFoundError,
    ScenarioService,
)


@pytest.fixture
def mock_server():
    """Create a mock server with a scenario_manager and persistence."""
    server = MagicMock()
    server.scenario_manager = MagicMock()
    server.scenario_persistence = MagicMock()
    server.scenario_persistence.save = AsyncMock()
    server.invalidate_all_scenario_caches = MagicMock()
    return server


@pytest.fixture
def service(mock_server):
    return ScenarioService(mock_server)


@pytest.fixture
def sample_config():
    return ScenarioConfig(
        drop_packets={101: 1.0},
        response_delays={116: 0.5},
    )


class TestGlobalScenario:
    """Test global scenario operations."""

    def test_get_global_scenario(self, service, mock_server):
        config = ScenarioConfig()
        mock_server.scenario_manager.get_global_scenario.return_value = config
        result = service.get_global_scenario()
        assert result is config

    @pytest.mark.asyncio
    async def test_set_global_scenario_persists(
        self, service, mock_server, sample_config
    ):
        await service.set_global_scenario(sample_config)
        mock_server.scenario_manager.set_global_scenario.assert_called_once_with(
            sample_config
        )
        mock_server.invalidate_all_scenario_caches.assert_called_once()
        mock_server.scenario_persistence.save.assert_awaited_once_with(
            mock_server.scenario_manager
        )

    @pytest.mark.asyncio
    async def test_clear_global_scenario_persists(self, service, mock_server):
        await service.clear_global_scenario()
        mock_server.scenario_manager.clear_global_scenario.assert_called_once()
        mock_server.invalidate_all_scenario_caches.assert_called_once()
        mock_server.scenario_persistence.save.assert_awaited_once()


class TestScopeScenario:
    """Test scoped scenario get/set/delete across all non-global scopes."""

    @pytest.mark.parametrize("scope", ["device", "type", "location", "group"])
    def test_get_scope_scenario_returns_config(self, service, mock_server, scope):
        config = ScenarioConfig()
        getter = f"get_{scope}_scenario"
        getattr(mock_server.scenario_manager, getter).return_value = config

        result = service.get_scope_scenario(scope, "some-id")
        assert result is config
        getattr(mock_server.scenario_manager, getter).assert_called_once_with("some-id")

    @pytest.mark.parametrize("scope", ["device", "type", "location", "group"])
    def test_get_scope_scenario_not_found(self, service, mock_server, scope):
        getter = f"get_{scope}_scenario"
        getattr(mock_server.scenario_manager, getter).return_value = None

        with pytest.raises(ScenarioNotFoundError) as exc_info:
            service.get_scope_scenario(scope, "missing")
        assert exc_info.value.scope == scope
        assert exc_info.value.identifier == "missing"

    @pytest.mark.parametrize("scope", ["type", "location", "group"])
    @pytest.mark.asyncio
    async def test_set_scope_scenario_persists(
        self, service, mock_server, scope, sample_config
    ):
        await service.set_scope_scenario(scope, "some-id", sample_config)
        setter = f"set_{scope}_scenario"
        getattr(mock_server.scenario_manager, setter).assert_called_once_with(
            "some-id", sample_config
        )
        mock_server.invalidate_all_scenario_caches.assert_called_once()
        mock_server.scenario_persistence.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_device_scenario_valid_serial(
        self, service, mock_server, sample_config
    ):
        await service.set_scope_scenario("device", "d073d5000001", sample_config)
        mock_server.scenario_manager.set_device_scenario.assert_called_once_with(
            "d073d5000001", sample_config
        )

    @pytest.mark.asyncio
    async def test_set_device_scenario_invalid_serial(self, service, sample_config):
        with pytest.raises(InvalidDeviceSerialError) as exc_info:
            await service.set_scope_scenario("device", "bad", sample_config)
        assert exc_info.value.serial == "bad"

    @pytest.mark.asyncio
    async def test_set_device_scenario_invalid_hex(self, service, sample_config):
        with pytest.raises(InvalidDeviceSerialError):
            await service.set_scope_scenario("device", "zzzzzzzzzzzz", sample_config)

    @pytest.mark.parametrize("scope", ["device", "type", "location", "group"])
    @pytest.mark.asyncio
    async def test_delete_scope_scenario_persists(self, service, mock_server, scope):
        deleter = f"delete_{scope}_scenario"
        getattr(mock_server.scenario_manager, deleter).return_value = True

        await service.delete_scope_scenario(scope, "some-id")
        getattr(mock_server.scenario_manager, deleter).assert_called_once_with(
            "some-id"
        )
        mock_server.invalidate_all_scenario_caches.assert_called_once()
        mock_server.scenario_persistence.save.assert_awaited_once()

    @pytest.mark.parametrize("scope", ["device", "type", "location", "group"])
    @pytest.mark.asyncio
    async def test_delete_scope_scenario_not_found(self, service, mock_server, scope):
        deleter = f"delete_{scope}_scenario"
        getattr(mock_server.scenario_manager, deleter).return_value = False

        with pytest.raises(ScenarioNotFoundError) as exc_info:
            await service.delete_scope_scenario(scope, "missing")
        assert exc_info.value.scope == scope


class TestPersistenceEdgeCases:
    """Test persistence when scenario_persistence is None."""

    @pytest.mark.asyncio
    async def test_persist_without_persistence_backend(
        self, mock_server, sample_config
    ):
        mock_server.scenario_persistence = None
        service = ScenarioService(mock_server)

        # Should not raise even without persistence
        await service.set_global_scenario(sample_config)
        mock_server.invalidate_all_scenario_caches.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_without_persistence_backend(self, mock_server):
        mock_server.scenario_persistence = None
        service = ScenarioService(mock_server)

        await service.clear_global_scenario()
        mock_server.invalidate_all_scenario_caches.assert_called_once()


class TestSerialValidation:
    """Test the serial validation logic."""

    @pytest.mark.parametrize(
        "serial,valid",
        [
            ("d073d5000001", True),
            ("AABBCCDDEEFF", True),
            ("aabbccddeeff", True),
            ("123456789abc", True),
            ("short", False),
            ("d073d500000100", False),  # too long
            ("d073d5gggg01", False),  # non-hex
            ("", False),
        ],
    )
    def test_is_valid_serial(self, serial, valid):
        assert ScenarioService._is_valid_serial(serial) is valid
