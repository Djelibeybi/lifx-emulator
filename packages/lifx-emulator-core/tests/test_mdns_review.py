"""Regressions for PR 224 lifecycle and ownership review findings."""

import asyncio
import socket
import struct

import pytest
from lifx_emulator import mdns
from lifx_emulator.factories import create_color_light
from test_mdns_lifecycle import MembershipOwner
from test_mdns_responder import dns_name, make_server, raw_query


async def test_committed_removals_survive_degraded_discovery(monkeypatch):
    owner = MembershipOwner()
    owner.failure = ("register", "outer")
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    first = create_color_light(serial="d073d5990001")
    server = make_server([first, create_color_light(serial="d073d5990002")])
    await server.start()
    try:
        assert await server.remove_device(first.state.serial)
        assert await server.remove_all_devices() == 1
        assert server.mdns_status == "failed"
    finally:
        await server.stop()


async def test_failed_probe_never_unregisters_foreign_service(monkeypatch):
    owner = MembershipOwner()
    owner.failure = ("register", "outer")
    unregistered = []
    original = owner.async_unregister_service

    async def unregister(info):
        unregistered.append(info.name)
        return await original(info)

    owner.async_unregister_service = unregister
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([create_color_light()])
    await server.start()
    await server.stop()
    assert unregistered == []


async def test_cancelled_retry_preserves_lifx_and_real_failure(monkeypatch):
    first, second = MembershipOwner(), MembershipOwner()
    first.failure = ("register", "outer")
    second.held = "register"
    owners = iter([first, second])
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: next(owners))
    server = make_server([create_color_light()])
    await server.start()
    endpoint = server.transport
    original_error = server.mdns_error
    retry = asyncio.create_task(server.retry_mdns())
    await second.entered.wait()
    retry.cancel()
    with pytest.raises(asyncio.CancelledError):
        await retry
    try:
        assert server.transport is endpoint
        assert server.mdns_error is original_error
        assert await server.remove_all_devices() == 1
    finally:
        await server.stop()


async def test_restart_cleans_retained_owner_before_thread_advertisement(monkeypatch):
    class CloseFailure(MembershipOwner):
        async def async_close(self):
            await super().async_close()
            if self.closes == 1:
                raise RuntimeError("close failed")

    first, second = CloseFailure(), MembershipOwner()
    owners = iter([first, second])
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: next(owners))
    server = make_server([create_color_light(connectivity="thread")])
    await server.start()
    with pytest.raises(RuntimeError, match="close failed"):
        await server.stop()
    await server.start()
    try:
        assert first.closes == 2
        assert server.mdns_status == "running"
        assert server._mdns._owner is second
        assert len(server._device_manager._lifecycle_listeners) == 1
    finally:
        await server.stop()


async def test_stop_closes_packet_admission_before_mdns_drain(monkeypatch):
    owner = MembershipOwner()
    owner.held = "register"
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    monkeypatch.setattr(mdns, "_OPERATION_TIMEOUT", 0.02)
    server = make_server([])
    await server.start()
    server.add_device(create_color_light())
    await owner.entered.wait()
    waiter = asyncio.create_task(server.wait_for_mdns_updates())
    stop = asyncio.create_task(server.stop())
    await asyncio.sleep(0)
    assert not server._ipv4_protocol._accepting
    result = await asyncio.gather(waiter, stop, return_exceptions=True)
    assert not waiter.cancelled()
    assert isinstance(result[0], RuntimeError)
    assert server.ipv4_endpoint is None


async def test_burst_adds_share_one_reconciliation(monkeypatch):
    owner = MembershipOwner()
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([])
    await server.start()
    calls = []
    original = server._mdns._reconcile

    async def reconcile(infos):
        calls.append(len(infos))
        await original(infos)

    monkeypatch.setattr(server._mdns, "_reconcile", reconcile)
    for i in range(10):
        server.add_device(create_color_light(serial=f"d073d599{i:04x}"))
    await server.wait_for_mdns_updates()
    await server.stop()
    assert calls == [10]


async def test_repeated_barrier_does_not_grow_retained_traceback(monkeypatch):
    owner = MembershipOwner()
    owner.failure = ("register", "outer")
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([create_color_light()])
    await server.start()
    original = server.mdns_error.__traceback__
    for _ in range(100):
        with pytest.raises(RuntimeError, match="register-outer"):
            await server.wait_for_mdns_updates()
    assert server.mdns_error.__traceback__ is original
    await server.stop()


async def test_start_cancellation_is_not_a_retained_failure(monkeypatch):
    owner = MembershipOwner()
    owner.held = "register"
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    server = make_server([create_color_light()])
    start = asyncio.create_task(server.start())
    await owner.entered.wait()
    start.cancel()
    with pytest.raises(asyncio.CancelledError):
        await start
    assert server.mdns_error is None
    assert server.mdns_status == "stopped"
    assert await server.remove_all_devices() == 1


async def test_failed_retry_reports_latest_supported_failure(monkeypatch):
    first, second = MembershipOwner(), MembershipOwner()
    first.failure = ("register", "outer")
    second.failure = ("register", "inner")
    owners = iter([first, second])
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: next(owners))
    server = make_server([create_color_light()])
    await server.start()
    assert not await server.retry_mdns()
    assert str(server.mdns_error) == "register-inner"
    await server.stop()


async def test_failed_announcement_unregisters_successfully_claimed_service(
    monkeypatch,
):
    owner = MembershipOwner()
    owner.failure = ("register", "inner")
    unregistered = []
    original = owner.async_unregister_service

    async def unregister(info):
        unregistered.append(info.name)
        return await original(info)

    owner.async_unregister_service = unregister
    monkeypatch.setattr(mdns, "AsyncZeroconf", lambda **kw: owner)
    device = create_color_light()
    server = make_server([device])
    await server.start()
    assert unregistered == [f"{device.state.serial}.{mdns.SERVICE_TYPE}"]
    await server.stop()


async def test_readd_after_wire_ttl_with_delayed_self_cached_ptr():
    """A late multicast answer must not make our owned name fail a fresh probe."""
    device = create_color_light(serial="d073d599beef", connectivity="thread")
    server = make_server([device])
    await server.start()
    try:
        assert await server.remove_device(device.state.serial)
        target = dns_name(f"{device.state.serial}.{mdns.SERVICE_TYPE}")
        delayed_answer = (
            struct.pack("!6H", 0, 0x8400, 0, 1, 0, 0)
            + dns_name(mdns.SERVICE_TYPE)
            + struct.pack("!HHIH", 12, 1, 10, len(target))
            + target
        )
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("127.0.0.1", 5353))
            sock.setsockopt(
                socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1")
            )
            sock.sendto(delayed_answer, ("224.0.0.251", 5353))
        await asyncio.sleep(10.1)
        assert server.add_device(device)
        await server.wait_for_mdns_updates()
        assert server.mdns_status == "running"
        assert server.ipv6_endpoint is not None
        assert await raw_query(9911)
    finally:
        await server.stop()
