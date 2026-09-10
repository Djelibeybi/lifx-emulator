"""WebSocket worker failure and admission boundary coverage."""

import asyncio

import pytest
from lifx_emulator_app.api.services.event_bridge import WebSocketEventQueue


@pytest.mark.parametrize("options", [{"max_pending": 0}, {"worker_count": 0}])
def test_queue_rejects_invalid_capacity(options):
    with pytest.raises(ValueError, match="positive"):
        WebSocketEventQueue(**options)


async def test_worker_failure_does_not_lose_following_event(caplog):
    queue = WebSocketEventQueue(worker_count=1)
    completed = asyncio.Event()

    async def failure():
        raise ValueError("broadcast failed")

    async def success():
        completed.set()

    queue.start()
    workers = set(queue._workers)
    queue.start()
    assert queue._workers == workers
    assert queue.schedule_factory(failure, "failure")
    assert queue.schedule_factory(success, "success")
    await asyncio.wait_for(completed.wait(), 1)
    await queue.shutdown()
    assert queue.pending_count == 0
    assert "broadcast failed" in caplog.text
    assert not queue._workers


async def test_closed_queue_closes_preconstructed_coroutine():
    queue = WebSocketEventQueue()
    await queue.shutdown()
    coroutine = asyncio.sleep(0)
    assert not queue.schedule(coroutine, "closed")
    assert coroutine.cr_frame is None
    assert queue.dropped_events == 1


async def test_pending_generation_cannot_restart_without_workers():
    queue = WebSocketEventQueue()
    queue._pending_count = 1
    with pytest.raises(RuntimeError, match="pending"):
        queue.start()
    queue._pending_count = 0
    await queue.shutdown()


async def test_worker_requires_initialised_queue():
    queue = WebSocketEventQueue()
    with pytest.raises(RuntimeError, match="has not started"):
        await queue._worker(0)
    assert queue.pending_count == 0


async def test_schedule_rejects_incomplete_queue_initialisation(monkeypatch):
    queue = WebSocketEventQueue()
    monkeypatch.setattr(queue, "start", lambda: None)
    with pytest.raises(RuntimeError, match="has not started"):
        queue.schedule_factory(lambda: asyncio.sleep(0), "incomplete")
    assert queue.pending_count == 0
