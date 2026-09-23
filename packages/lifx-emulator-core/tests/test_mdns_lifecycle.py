"""Live membership completion, supported failures and explicit recovery."""

import asyncio

import pytest
from lifx_emulator import mdns
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from test_mdns_responder import FakeOwner, make_server, raw_query


def test_mdns_lifecycle_public_contract():
    server = make_server([])
    assert callable(getattr(server, "wait_for_mdns_updates", None))
    assert callable(getattr(server, "retry_mdns", None))
    assert server.mdns_status == "stopped"
    assert server.mdns_error is None


async def test_membership_add_remove_readd_wire():
    server = make_server([])
    device = create_color_light(serial="d073d5000400", firmware_version=(4, 200))
    try:
        await server.start()
        assert server.add_device(device)
        await server.wait_for_mdns_updates()
        replies = await raw_query(1001)
        assert replies
        owner_info = server._mdns._services[f"{device.state.serial}._lifx._udp.local."]
        assert await server.remove_device(device.state.serial)
        assert not await raw_query(1002)
        assert server.add_device(device)
        await server.wait_for_mdns_updates()
        assert server._mdns._services[owner_info.name] is owner_info
        assert await raw_query(1003)
        assert await server.remove_all_devices() == 1
        assert not await raw_query(1004)
    finally:
        await server.stop()
    assert server._device_manager._lifecycle_listeners == []


@pytest.mark.parametrize("operation", ["register", "unregister", "update"])
async def test_membership_barrier_second_stage_and_waiter_cancellation(
    monkeypatch, operation
):
    owner = MembershipOwner()
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    device = create_color_light()
    server = make_server([])
    await server.start()
    if operation != "register":
        server.add_device(device)
        await server.wait_for_mdns_updates()
    if operation == "update":
        await server.remove_device(device.state.serial)
    owner.held = operation
    if operation == "unregister":
        mutation = asyncio.create_task(server.remove_device(device.state.serial))
    else:
        assert server.add_device(device)
        mutation = asyncio.create_task(server.wait_for_mdns_updates())
    await asyncio.wait_for(owner.entered.wait(), 1)
    assert not mutation.done()
    if operation != "unregister":
        mutation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await mutation
        assert not server._mdns._tail.cancelled()
    owner.release.set()
    if operation == "unregister":
        assert await mutation
    await server.wait_for_mdns_updates()
    await server.stop()
    assert owner.closes == 1


@pytest.mark.parametrize("radio", ["wifi", "thread"])
@pytest.mark.parametrize("stage", ["outer", "inner"])
async def test_mdns_start_failure_policy_and_retry(monkeypatch, radio, stage):
    owners = []

    def create(**kwargs):
        owner = MembershipOwner()
        if not owners:
            owner.failure = ("register", stage)
        owners.append(owner)
        return owner

    monkeypatch.setattr(mdns, "AsyncZeroconf", create)
    server = make_server([create_color_light(connectivity=radio)])
    if radio == "thread":
        with pytest.raises(RuntimeError, match=f"register-{stage}"):
            await server.start()
        assert server.ipv4_endpoint is None
    else:
        await server.start()
        assert server.ipv4_endpoint is not None
    assert server.mdns_status == "failed"
    assert isinstance(server.mdns_error, RuntimeError)
    assert owners[0].closes == 1
    assert server._device_manager._lifecycle_listeners == []
    if radio == "wifi":
        endpoint = server.transport
        with pytest.raises(RuntimeError, match="Recover mDNS"):
            server.add_device(create_color_light(connectivity="thread"))
        assert await asyncio.gather(server.retry_mdns(), server.retry_mdns()) == [
            True,
            True,
        ]
        assert len(owners) == 2
        assert server.transport is endpoint
        assert server.mdns_status == "running"
        assert server.mdns_error is None
    await server.stop()


@pytest.mark.parametrize("radio", ["wifi", "thread"])
@pytest.mark.parametrize("operation", ["register", "update", "unregister"])
@pytest.mark.parametrize("stage", ["outer", "inner"])
async def test_reconcile_failure_retained_and_policy(
    monkeypatch, radio, operation, stage
):
    owner = MembershipOwner()
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    device = create_color_light()
    server = make_server([create_color_light(connectivity=radio)])
    await server.start()
    if operation != "register":
        server.add_device(device)
        await server.wait_for_mdns_updates()
    if operation == "update":
        await server.remove_device(device.state.serial)
    owner.failure = (operation, stage)
    if operation == "unregister":
        with pytest.raises(RuntimeError, match=f"{operation}-{stage}"):
            await asyncio.wait_for(server.remove_device(device.state.serial), 2)
    else:
        server.add_device(device)
        with pytest.raises(RuntimeError, match=f"{operation}-{stage}"):
            await asyncio.wait_for(server.wait_for_mdns_updates(), 2)
    assert server.mdns_status == "failed"
    assert owner.closes == 1
    assert (server.ipv4_endpoint is None) == (radio == "thread")
    with pytest.raises(RuntimeError):
        await server.wait_for_mdns_updates()
    await server.stop()


async def test_status_readonly_repeated_lifecycle(monkeypatch):
    owners = []

    def create(**kw):
        owner = MembershipOwner()
        owners.append(owner)
        return owner

    monkeypatch.setattr(mdns, "AsyncZeroconf", create)
    server = make_server([])
    for _ in range(3):
        await asyncio.gather(server.start(), server.start())
        assert server.mdns_status == "running"
        assert len(server._device_manager._lifecycle_listeners) == 1
        with pytest.raises(AttributeError):
            server.mdns_status = "failed"
        with pytest.raises(AttributeError):
            server.mdns_error = None
        await asyncio.gather(server.stop(), server.stop())
        assert server.mdns_status == "stopped"
        assert not server._device_manager._lifecycle_listeners
    assert len(owners) == 3
    assert all(owner.closes == 1 for owner in owners)


class MembershipOwner(FakeOwner):
    async def async_update_service(self, info):
        return await self.operation("update")


async def test_start_cancellation_cleans_owned_resources(monkeypatch):
    owner = MembershipOwner()
    owner.held = "register"
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([create_color_light()])
    task = asyncio.create_task(server.start())
    await owner.entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert owner.closes == 1
    assert server.ipv4_endpoint is None
    assert not server._device_manager._lifecycle_listeners
    await server.stop()


async def test_stop_bounds_reconcile_and_expires_tombstones(monkeypatch):
    monkeypatch.setattr(mdns, "_OPERATION_TIMEOUT", 0.02)
    owner = MembershipOwner()
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    device = create_color_light()
    server = make_server([device])
    await server.start()
    responder = server._mdns
    await server.remove_device(device.state.serial)
    name = f"{device.state.serial}._lifx._udp.local."
    info, handle = responder._tombstones[name]
    assert info.name == name
    handle.cancel()
    responder._expire(name)
    assert not responder._tombstones
    owner.held = "register"
    server.add_device(device)
    await owner.entered.wait()
    await asyncio.wait_for(server.stop(), 1)
    assert responder._tasks.pending_count == 0
    assert owner.closes == 1
    assert not server._device_manager._lifecycle_listeners


async def test_supported_close_failure_retains_error(monkeypatch):
    class CloseFailure(MembershipOwner):
        async def async_close(self):
            await super().async_close()
            if self.closes == 1:
                raise RuntimeError("close failure")

    owner = CloseFailure()
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([])
    await server.start()
    with pytest.raises(RuntimeError, match="close failure"):
        await server.stop()
    assert server.mdns_status == "failed"
    assert server.ipv4_endpoint is None
    assert str(server.mdns_error) == "close failure"
    assert server._mdns.owns_resources
    await server.stop()
    assert server._mdns is None
    assert owner.closes == 2


async def test_disabled_status_and_retry_rejected():
    server = EmulatedLifxServer([], DeviceManager(DeviceRepository()), port=0)
    await server.start()
    assert server.mdns_status == "disabled"
    assert server.mdns_error is None
    with pytest.raises(RuntimeError):
        await server.retry_mdns()
    await server.stop()
    assert server.mdns_status == "disabled"
