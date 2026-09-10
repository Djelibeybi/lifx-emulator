"""Transport lifecycle failure boundaries and cleanup invariants."""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


@pytest.fixture
def server():
    return EmulatedLifxServer([], DeviceManager(DeviceRepository()), port=0)


async def test_inactive_protocol_rejects_datagram_before_allocation(server, caplog):
    protocol = server.LifxProtocol(server, accepting=False)
    with caplog.at_level(logging.DEBUG):
        protocol.datagram_received(b"untrusted", ("127.0.0.1", 1234))
    assert server._background_tasks.pending_count == 0
    assert server.packets_received == 0
    assert "inactive" in caplog.text


async def test_endpoint_failure_invalidates_both_families(server, caplog):
    await server.start()
    protocol = server._ipv6_protocol
    other_transport = server.transport
    assert protocol is not None and other_transport is not None
    try:
        protocol.connection_lost(OSError("endpoint unavailable"))
        await asyncio.gather(*server._endpoint_loss_tasks)
        assert server.ipv4_endpoint is None
        assert server.ipv6_endpoint is None
        assert other_transport.is_closing()
        assert "endpoint unavailable" in caplog.text
        assert "invalidating endpoint pair" in caplog.text
    finally:
        await server.stop()


async def test_endpoint_loss_cleanup_consumes_cancellation_and_failure(server, caplog):
    cancelled = asyncio.create_task(asyncio.sleep(100))
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled
    server._endpoint_loss_tasks.add(cancelled)
    server._on_endpoint_loss_done(cancelled)

    async def fail():
        raise OSError("cleanup unavailable")

    failed = asyncio.create_task(fail())
    await asyncio.gather(failed, return_exceptions=True)
    server._endpoint_loss_tasks.add(failed)
    server._on_endpoint_loss_done(failed)
    assert not server._endpoint_loss_tasks
    assert "cleanup unavailable" in caplog.text


def test_endpoint_helpers_validate_missing_socket_details():
    assert not EmulatedLifxServer._transport_is_open(None)
    with pytest.raises(RuntimeError, match="socket endpoint"):
        EmulatedLifxServer._endpoint_from_transport(Mock(get_extra_info=lambda _: None))
    transport = Mock()
    EmulatedLifxServer._close_unique_transports(object(), transport, transport)
    transport.close.assert_called_once()


async def test_ipv4_bind_failure_leaves_no_endpoint_state(server, caplog):
    loop = asyncio.get_running_loop()
    with patch.object(
        loop,
        "create_datagram_endpoint",
        AsyncMock(side_effect=OSError("bind unavailable")),
    ):
        with pytest.raises(OSError, match="bind unavailable"):
            await server.start()
    assert server.transport is None
    assert server.ipv6_endpoint is None
    assert not server._background_tasks.accepting
    assert "IPv4 bind failed" in caplog.text


async def test_admission_commit_failure_closes_pair_and_tracker(server):
    with patch.object(
        server.LifxProtocol,
        "start_accepting",
        side_effect=RuntimeError("admission failed"),
    ):
        with pytest.raises(RuntimeError, match="admission failed"):
            await server.start()
    assert not server._background_tasks.accepting
    assert server.transport is None
    assert server.ipv4_endpoint is None
    assert server.ipv6_endpoint is None


async def test_stop_closes_transports_even_when_device_drain_fails(server):
    device = create_color_light("d073d5000001")
    server.add_device(device)
    await server.start()
    transports = (server.transport, server._ipv6_transport)
    with patch.object(
        device, "close", AsyncMock(side_effect=RuntimeError("drain failed"))
    ):
        with pytest.raises(RuntimeError, match="drain failed"):
            await server.stop()
    assert all(transport.is_closing() for transport in transports)
    assert server.ipv4_endpoint is None
    assert server.ipv6_endpoint is None
    await device.close()


async def test_repeated_device_removal_does_not_leave_retained_device_closed():
    repository = DeviceRepository()
    manager = DeviceManager(repository)
    device = create_color_light("d073d5000001")
    manager.add_device(device)
    with patch.object(repository, "remove", return_value=False):
        assert not await manager.remove_device(device.state.serial)
    assert manager.get_device(device.state.serial) is device
    assert device._background_tasks.accepting


async def test_concurrent_removal_does_not_reopen_detached_device():
    repository = DeviceRepository()
    manager = DeviceManager(repository)
    device = create_color_light("d073d5000001")
    manager.add_device(device)

    async def detach_then_fail(*args):
        repository.remove(device.state.serial)
        raise OSError("detached concurrently")

    with patch.object(device, "close", side_effect=detach_then_fail):
        with pytest.raises(OSError):
            await manager.remove_device(device.state.serial)
    assert manager.get_device(device.state.serial) is None


async def test_bulk_failure_ignores_already_detached_devices():
    repository = DeviceRepository()
    manager = DeviceManager(repository)
    device = create_color_light("d073d5000001")
    manager.add_device(device)

    async def detach_then_fail(*args):
        repository.remove(device.state.serial)
        raise OSError("detached concurrently")

    with patch.object(device, "close", side_effect=detach_then_fail):
        with pytest.raises(OSError):
            await manager.remove_all_devices()
    assert manager.get_device(device.state.serial) is None
