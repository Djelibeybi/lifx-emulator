"""Fault injection at the prototype boundary, without patching zeroconf internals."""

import asyncio
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

RecoveryPrototype = run_path(
    str(Path(__file__).parents[1] / "mdns_spike_inputs/zeroconf_recovery.py")
)["RecoveryPrototype"]


class FakeResponder:
    def __init__(self, fail_at=None, *, announcement_failure=False):
        self.registered = []
        self.closed = False
        self.fail_at = fail_at
        self.announcement_failure = announcement_failure

    async def async_register_service(self, info, **kwargs):
        if len(self.registered) == self.fail_at:
            raise OSError("injected registration failure")
        self.registered.append(info)

        async def announce():
            if self.announcement_failure:
                raise OSError("injected announcement failure")

        return announce()

    async def async_close(self):
        self.registered.clear()
        self.closed = True


@pytest.mark.parametrize("fail_at", [0, 1, 2])
async def test_partial_fleet_is_closed_and_explicit_retry_uses_fresh_owner(fail_at):
    first = FakeResponder(fail_at)
    second = FakeResponder()
    attempts = iter([first, second])
    adapter = RecoveryPrototype(lambda: next(attempts))
    assert not await adapter.retry_mdns([1, 2, 3])
    assert adapter.mdns_status == "failed"
    assert first.closed and not first.registered
    with pytest.raises(RuntimeError, match="retry_mdns"):
        adapter.admit_thread()
    await asyncio.sleep(0)
    assert not second.registered  # No automatic recovery.
    assert await adapter.retry_mdns([1, 2, 3])
    assert second.registered == [1, 2, 3]
    assert adapter.mdns_error is None
    adapter.admit_thread()
    await adapter.stop()
    await adapter.stop()
    assert second.closed and adapter.mdns_status == "stopped"


async def test_factory_failure_can_be_retried():
    attempts = [OSError("bind failed"), FakeResponder()]

    def factory():
        value = attempts.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    adapter = RecoveryPrototype(factory)
    assert not await adapter.retry_mdns([1])
    assert "bind failed" in adapter.mdns_error
    assert await adapter.retry_mdns([1])
    await adapter.stop()


async def test_announcement_failure_cleans_registered_service():
    responder = FakeResponder(announcement_failure=True)
    adapter = RecoveryPrototype(lambda: responder)
    assert not await adapter.retry_mdns([1])
    assert responder.closed and not responder.registered


@pytest.mark.parametrize(
    "families,stops", [(["wifi"], 0), (["thread"], 1), (["wifi", "thread"], 1)]
)
async def test_failure_policy_retains_error(families, stops):
    server = SimpleNamespace(
        get_all_devices=lambda: [
            SimpleNamespace(state=SimpleNamespace(connectivity=family))
            for family in families
        ],
        stop=AsyncMock(),
    )
    responder = FakeResponder()
    adapter = RecoveryPrototype(lambda: responder)
    assert await adapter.retry_mdns([1])
    await adapter.runtime_failure(OSError("listener lost"), server)
    assert server.stop.await_count == stops
    await adapter.stop()
    assert adapter.mdns_status == "failed"
    assert "listener lost" in adapter.mdns_error
    assert responder.closed


async def test_disabled_allows_thread_and_never_constructs():
    adapter = RecoveryPrototype(
        lambda: pytest.fail("unexpected construction"), enabled=False
    )
    adapter.admit_thread()
    assert not await adapter.retry_mdns([1])
    await adapter.stop()
    assert adapter.mdns_status == "disabled"


async def test_cancelled_registration_is_cleaned_before_cancellation_escapes():
    entered = asyncio.Event()
    responder = FakeResponder()

    async def register(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()

    responder.async_register_service = register
    adapter = RecoveryPrototype(lambda: responder)
    task = asyncio.create_task(adapter.retry_mdns([1]))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert responder.closed and adapter.mdns_status == "failed"


async def test_cleanup_failure_blocks_new_owner_until_close_succeeds():
    responder = FakeResponder(0)
    original_close = responder.async_close
    responder.async_close = AsyncMock(side_effect=OSError("close failed"))
    factory = iter([responder, FakeResponder()])
    adapter = RecoveryPrototype(lambda: next(factory))
    assert not await adapter.retry_mdns([1])
    assert not await adapter.retry_mdns([1])
    assert "close failed" in adapter.mdns_error
    responder.async_close = original_close
    assert await adapter.retry_mdns([1])
    await adapter.stop()


async def test_concurrent_retries_create_only_one_responder():
    calls = []
    responder = FakeResponder()

    def factory():
        calls.append(True)
        return responder

    adapter = RecoveryPrototype(factory)
    assert all(await asyncio.gather(*(adapter.retry_mdns([1]) for _ in range(3))))
    assert len(calls) == 1 and responder.registered == [1]
    with pytest.raises(AttributeError):
        adapter.mdns_status = "running"
    with pytest.raises(AttributeError):
        adapter.mdns_error = "hidden"
    await adapter.stop()


@pytest.mark.parametrize(
    "operation", ["register", "update", "unregister", "interfaces", "close"]
)
@pytest.mark.parametrize("family", ["wifi", "thread"])
async def test_supported_operation_failures_keep_identity_and_retry(operation, family):
    responder = FakeResponder()
    second = FakeResponder()
    owners = iter([responder, second])
    adapter = RecoveryPrototype(lambda: next(owners))
    assert await adapter.retry_mdns([1])
    server = SimpleNamespace(
        get_all_devices=lambda: [
            SimpleNamespace(state=SimpleNamespace(connectivity=family))
        ],
        stop=AsyncMock(),
    )
    methods = {
        "register": "async_register_service",
        "update": "async_update_service",
        "unregister": "async_unregister_service",
        "interfaces": "async_update_interfaces",
        "close": "async_close",
    }
    original_close = responder.async_close
    setattr(
        responder, methods[operation], AsyncMock(side_effect=OSError("operation fault"))
    )
    assert not await adapter.operate(operation, 1, server=server)
    assert adapter.mdns_status == "failed"
    assert operation in adapter.mdns_error and "operation fault" in adapter.mdns_error
    assert server.stop.await_count == (family == "thread")
    if operation == "close":
        assert not await adapter.retry_mdns([1])
        assert "operation fault" in adapter.mdns_error
        responder.async_close = original_close
    else:
        assert responder.closed
    assert not second.registered
    assert await adapter.retry_mdns([1])
    await adapter.stop()


async def test_update_announcement_failure_is_awaited():
    responder = FakeResponder()
    adapter = RecoveryPrototype(lambda: responder)
    assert await adapter.retry_mdns([1])
    responder.announcement_failure = True
    responder.async_update_service = responder.async_register_service
    assert not await adapter.operate("update", 2)
    assert "update.announcement" in adapter.mdns_error
    assert responder.closed
