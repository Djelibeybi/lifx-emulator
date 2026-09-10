"""Tests for owner-local background task tracking."""

import asyncio
import gc
import logging
from unittest.mock import Mock, patch

import pytest
from lifx_emulator.background_tasks import BackgroundTaskTracker


class TestBackgroundTaskTracker:
    """Exercise the reusable tracker lifecycle contract."""

    async def test_background_task_is_retained_until_success(self):
        """A scheduled coroutine stays retained until its result is consumed."""
        tracker = BackgroundTaskTracker("test-owner")
        started = asyncio.Event()
        release = asyncio.Event()

        async def operation():
            started.set()
            await release.wait()
            return "complete"

        task = tracker.schedule(operation(), "retained-operation")
        assert task is not None
        await started.wait()

        gc.collect()

        assert tracker.pending_count == 1
        assert not task.done()

        release.set()
        assert await task == "complete"
        await asyncio.sleep(0)
        assert tracker.pending_count == 0

    def test_background_task_no_loop_closes_coroutine(self, caplog):
        """Scheduling without a running loop refuses and closes the coroutine."""
        tracker = BackgroundTaskTracker("test-owner")

        async def operation():
            return "unused"

        coroutine = operation()
        task = tracker.schedule(coroutine, "no-loop-operation")

        assert task is None
        assert coroutine.cr_frame is None
        assert "test-owner" in caplog.text
        assert "no-loop-operation" in caplog.text

    async def test_background_task_creation_failure_closes_coroutine(self, caplog):
        """A create-task failure closes the coroutine and preserves the exception."""
        tracker = BackgroundTaskTracker("test-owner")
        creation_error = RuntimeError("task creation failed")
        loop = Mock()
        loop.create_task.side_effect = creation_error

        async def operation():
            return "unused"

        coroutine = operation()
        with (
            patch(
                "lifx_emulator.background_tasks.asyncio.get_running_loop",
                return_value=loop,
            ),
            pytest.raises(RuntimeError) as raised,
        ):
            tracker.schedule(coroutine, "creation-failure")

        assert raised.value is creation_error
        assert coroutine.cr_frame is None
        assert tracker.pending_count == 0
        assert "test-owner" in caplog.text
        assert "creation-failure" in caplog.text

    async def test_background_task_failure_is_consumed_and_logged_once(self, caplog):
        """A raised exception is observed once before the task is released."""
        tracker = BackgroundTaskTracker("test-owner")

        async def operation():
            raise ValueError("operation failed")

        with caplog.at_level(logging.ERROR):
            task = tracker.schedule(operation(), "failed-operation")
            assert task is not None
            with pytest.raises(ValueError, match="operation failed"):
                await task
            await asyncio.sleep(0)

        failures = [
            record
            for record in caplog.records
            if "Background task failed" in record.getMessage()
        ]
        assert len(failures) == 1
        assert "test-owner" in failures[0].getMessage()
        assert "failed-operation" in failures[0].getMessage()
        assert tracker.pending_count == 0

    async def test_background_task_cancellation_is_debug_logged(self, caplog):
        """Expected cancellation avoids exception retrieval and empties the tracker."""
        tracker = BackgroundTaskTracker("test-owner")
        started = asyncio.Event()

        async def operation():
            started.set()
            await asyncio.Event().wait()

        with caplog.at_level(logging.DEBUG):
            task = tracker.schedule(operation(), "cancelled-operation")
            assert task is not None
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)

        assert tracker.pending_count == 0
        assert "cancelled-operation" in caplog.text
        assert "cancelled" in caplog.text.lower()

    async def test_background_task_closed_admission_closes_coroutine(self, caplog):
        """Closed admission refuses new work without leaking its coroutine."""
        tracker = BackgroundTaskTracker("test-owner")
        tracker.stop_accepting()

        async def operation():
            return "unused"

        coroutine = operation()
        task = tracker.schedule(coroutine, "closed-operation")

        assert task is None
        assert coroutine.cr_frame is None
        assert tracker.pending_count == 0
        assert "closed-operation" in caplog.text

    async def test_background_task_shutdown_allows_grace_completion(self):
        """Work completing inside the grace period is not cancelled."""
        tracker = BackgroundTaskTracker("test-owner")
        started = asyncio.Event()
        release = asyncio.Event()

        async def operation():
            started.set()
            await release.wait()
            return "graceful"

        task = tracker.schedule(operation(), "grace-operation")
        assert task is not None
        await started.wait()
        shutdown = asyncio.create_task(tracker.shutdown(timeout=1.0))
        release.set()
        await shutdown

        assert task.result() == "graceful"
        assert not task.cancelled()
        assert tracker.pending_count == 0

    async def test_background_task_shutdown_cancels_after_timeout(self, caplog):
        """Work exceeding the grace period is cancelled, awaited, and released."""
        tracker = BackgroundTaskTracker("test-owner")
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def operation():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with caplog.at_level(logging.DEBUG):
            task = tracker.schedule(operation(), "timeout-operation")
            assert task is not None
            await started.wait()
            await tracker.shutdown(timeout=0.0)

        assert cancelled.is_set()
        assert task.cancelled()
        assert tracker.pending_count == 0
        assert "timeout-operation" in caplog.text

    async def test_cancelled_shutdown_still_cancels_and_awaits_admitted_work(self):
        """Caller cancellation cannot let admitted work outlive tracker teardown."""
        tracker = BackgroundTaskTracker("test-owner")
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def operation():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        worker = tracker.schedule(operation(), "cancelled-shutdown-operation")
        assert worker is not None
        await started.wait()

        shutdown = asyncio.create_task(tracker.shutdown(timeout=60.0))
        await asyncio.sleep(0)
        shutdown.cancel()

        with pytest.raises(asyncio.CancelledError):
            await shutdown

        assert cancelled.is_set()
        assert worker.cancelled()
        assert tracker.pending_count == 0

    async def test_background_task_tracker_reopens_for_new_lifecycle(self):
        """Only an explicit reopen admits a second exactly-once lifecycle."""
        tracker = BackgroundTaskTracker("test-owner")
        executions = []

        async def operation(value):
            executions.append(value)

        first = tracker.schedule(operation("first"), "first-operation")
        assert first is not None
        await first
        await asyncio.sleep(0)
        await tracker.shutdown()

        refused_coroutine = operation("refused")
        assert tracker.schedule(refused_coroutine, "refused-operation") is None
        assert refused_coroutine.cr_frame is None

        tracker.start_accepting()
        tracker.start_accepting()
        second = tracker.schedule(operation("second"), "second-operation")
        assert second is not None
        await second
        await asyncio.sleep(0)
        await tracker.shutdown()

        assert executions == ["first", "second"]
        assert tracker.pending_count == 0
