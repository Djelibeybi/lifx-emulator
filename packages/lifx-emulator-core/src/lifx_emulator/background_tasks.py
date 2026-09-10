"""Owner-local lifecycle management for fire-and-forget asyncio tasks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskTracker:
    """Retain, observe, and drain labelled background tasks for one owner."""

    def __init__(
        self,
        owner: str,
        *,
        accepting: bool = True,
        max_pending: int | None = None,
    ) -> None:
        if max_pending is not None and max_pending <= 0:
            raise ValueError("max_pending must be positive when configured")
        self._owner = owner
        self._accepting = accepting
        self._max_pending = max_pending
        self._tasks: set[asyncio.Task[Any]] = set()
        self._operations: dict[asyncio.Task[Any], str] = {}

    @property
    def pending_count(self) -> int:
        """Return the number of retained tasks that have not been consumed."""
        return len(self._tasks)

    @property
    def accepting(self) -> bool:
        """Return whether new background work is currently admitted."""
        return self._accepting

    @property
    def has_capacity(self) -> bool:
        """Return whether another task can be admitted without exceeding the limit."""
        return self._max_pending is None or len(self._tasks) < self._max_pending

    def start_accepting(self) -> None:
        """Open admission for a new lifecycle after all earlier work has drained."""
        if self._accepting:
            return
        if self._tasks:
            raise RuntimeError(
                "Cannot reopen background tasks for "
                f"{self._owner} while work is pending"
            )
        self._accepting = True

    def stop_accepting(self) -> None:
        """Close admission while allowing already scheduled work to complete."""
        self._accepting = False

    def schedule(
        self, coroutine: Coroutine[Any, Any, Any], operation: str
    ) -> asyncio.Task[Any] | None:
        """Create and retain a labelled task, closing work that cannot be admitted."""
        if not self._accepting:
            coroutine.close()
            logger.warning(
                "Background task refused (owner=%s, operation=%s): admission closed",
                self._owner,
                operation,
            )
            return None

        if not self.has_capacity:
            coroutine.close()
            logger.warning(
                "Background task refused (owner=%s, operation=%s): capacity reached",
                self._owner,
                operation,
            )
            return None

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            coroutine.close()
            logger.error(
                "Background task refused (owner=%s, operation=%s): "
                "no running event loop",
                self._owner,
                operation,
            )
            return None

        try:
            task = loop.create_task(coroutine)
        except BaseException:
            coroutine.close()
            logger.exception(
                "Background task creation failed (owner=%s, operation=%s)",
                self._owner,
                operation,
            )
            raise

        self._tasks.add(task)
        self._operations[task] = operation
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        """Consume one completed task outcome and release its strong reference."""
        if task not in self._tasks:
            return

        operation = self._operations.get(task, "unknown")
        try:
            if task.cancelled():
                logger.debug(
                    "Background task cancelled (owner=%s, operation=%s)",
                    self._owner,
                    operation,
                )
                return

            exception = task.exception()
            if exception is not None:
                logger.error(
                    "Background task failed (owner=%s, operation=%s): %s",
                    self._owner,
                    operation,
                    exception,
                    exc_info=(
                        type(exception),
                        exception,
                        exception.__traceback__,
                    ),
                )
        finally:
            self._tasks.discard(task)
            self._operations.pop(task, None)

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Drain admitted work, then cancel and await anything beyond the grace."""
        self.stop_accepting()
        snapshot = set(self._tasks)
        if not snapshot:
            return

        try:
            _, pending = await asyncio.wait(snapshot, timeout=timeout)
        except asyncio.CancelledError:
            pending = {task for task in snapshot if not task.done()}
            for task in pending:
                task.cancel()
            try:
                await asyncio.shield(asyncio.gather(*pending, return_exceptions=True))
            finally:
                for task in snapshot:
                    self._on_done(task)
            raise

        try:
            if pending:
                logger.debug(
                    "Cancelling %s background task(s) after shutdown grace (owner=%s)",
                    len(pending),
                    self._owner,
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        finally:
            for task in snapshot:
                self._on_done(task)
