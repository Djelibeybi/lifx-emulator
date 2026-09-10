"""Creation failures preserve repository consistency."""

from unittest.mock import patch

import pytest
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light, create_device
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from lifx_emulator_app.api.models import DeviceCreateRequest
from lifx_emulator_app.api.services.device_service import (
    DeviceCreationError,
    DeviceService,
)


@pytest.fixture
def service():
    return DeviceService(EmulatedLifxServer([], DeviceManager(DeviceRepository())))


async def test_factory_failure_is_reported_without_admitting_device(service):
    with (
        patch(
            "lifx_emulator_app.api.services.device_service.create_device",
            side_effect=ValueError("invalid product"),
        ),
        pytest.raises(DeviceCreationError, match="invalid product"),
    ):
        await service.create_device(DeviceCreateRequest(product_id=91))
    assert service.server.get_all_devices() == []


async def test_generated_serial_collisions_exhaust_bounded_retries(service):
    serial = "d073d5000001"
    existing = create_color_light(serial)
    service.server.add_device(existing)
    with patch(
        "lifx_emulator_app.api.services.device_service.create_device",
        side_effect=lambda **kwargs: create_color_light(serial),
    ) as factory:
        with pytest.raises(DeviceCreationError, match="100 attempts"):
            await service.create_device(DeviceCreateRequest(product_id=91))
    assert factory.call_count == 100
    assert service.server.get_device(serial) is existing
    await service.server.remove_all_devices()


async def test_bulk_creation_rolls_back_successful_preceding_devices(service):
    requests = [
        DeviceCreateRequest(product_id=91, serial="d073d5000001"),
        DeviceCreateRequest(product_id=91, serial="d073d5000002"),
    ]
    first = create_device(product_id=91, serial=requests[0].serial)
    with (
        patch(
            "lifx_emulator_app.api.services.device_service.create_device",
            side_effect=[first, ValueError("factory failed")],
        ),
        pytest.raises(DeviceCreationError, match="factory failed"),
    ):
        await service.create_devices_bulk(requests)
    assert service.server.get_all_devices() == []


@pytest.mark.parametrize("method", ["_apply_zone_colors", "_apply_tile_colors"])
def test_colour_helpers_reject_unsupported_device(service, method):
    state = create_color_light("d073d5000001").state
    with pytest.raises(ValueError, match="does not support"):
        getattr(service, method)(state, [])
