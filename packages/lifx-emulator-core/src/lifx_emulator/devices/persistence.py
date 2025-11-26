"""Async persistent storage with debouncing to avoid blocking event loop."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from lifx_emulator.devices.state_serializer import (
    deserialize_device_state,
    serialize_device_state,
)

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path.home() / ".lifx-emulator"


class DevicePersistenceAsyncFile:
    """High-performance async storage with smart debouncing.

    Non-blocking asynchronous I/O for device state persistence.
    Recommended for production use.

    Features:
    - Per-device debouncing (coalesces rapid changes to same device)
    - Batch writes (groups multiple devices in single flush)
    - Executor-based I/O (no event loop blocking)
    - Adaptive flush (flushes early if queue size threshold met)
    - Task lifecycle management (prevents GC of background tasks)
    """

    def __init__(
        self,
        storage_dir: Path | str = DEFAULT_STORAGE_DIR,
        debounce_ms: int = 100,
        batch_size_threshold: int = 50,
    ):
        """Initialize async storage.

        Args:
            storage_dir: Directory to store device state files
            debounce_ms: Milliseconds to wait before flushing (default: 100ms)
            batch_size_threshold: Flush early if queue exceeds this size (default: 50)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.debounce_ms = debounce_ms
        self.batch_size_threshold = batch_size_threshold

        # Per-device pending writes (coalescence)
        self.pending: dict[str, dict] = {}

        # Single-thread executor (serialized writes)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="storage")

        # Flush task management
        self.flush_task: asyncio.Task | None = None
        self.lock = asyncio.Lock()

        # Background task tracking (prevents GC)
        self.background_tasks: set[asyncio.Task] = set()

        # Metrics
        self.writes_queued = 0
        self.writes_executed = 0
        self.flushes = 0

        logger.debug("Async storage initialized at %s", self.storage_dir)

    async def save_device_state(self, device_state: Any) -> None:
        """Queue device state for saving (non-blocking).

        Args:
            device_state: DeviceState instance to persist
        """
        async with self.lock:
            serial = device_state.serial

            # Coalesce: Latest state wins
            self.pending[serial] = serialize_device_state(device_state)
            self.writes_queued += 1

            # Adaptive flush: If queue large, flush early
            if len(self.pending) >= self.batch_size_threshold:
                if self.flush_task and not self.flush_task.done():
                    self.flush_task.cancel()

                # Create flush task and track it
                task = asyncio.create_task(self._flush())
                self._track_task(task)
                self.flush_task = task

            # Otherwise, debounce normally
            elif not self.flush_task or self.flush_task.done():
                # Create flush task and track it
                task = asyncio.create_task(self._flush_after_delay())
                self._track_task(task)
                self.flush_task = task

    def _track_task(self, task: asyncio.Task) -> None:
        """Track background task to prevent garbage collection.

        Args:
            task: Task to track
        """
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _flush_after_delay(self) -> None:
        """Wait for debounce period, then flush."""
        try:
            await asyncio.sleep(self.debounce_ms / 1000.0)
            await self._flush()
        except asyncio.CancelledError:
            # Cancelled by adaptive flush - this is normal
            logger.debug("Flush cancelled by adaptive flush")

    async def _flush(self) -> None:
        """Flush all pending writes to disk."""
        async with self.lock:
            if not self.pending:
                return

            writes = list(self.pending.items())
            self.pending.clear()
            self.flushes += 1

        # Execute batch write in background thread
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(self.executor, self._batch_write, writes)
            self.writes_executed += len(writes)
            logger.debug("Flushed %s device states to disk", len(writes))
        except Exception as e:
            logger.error("Error flushing device states: %s", e, exc_info=True)

    def _batch_write(self, writes: list[tuple[str, dict]]) -> None:
        """Synchronous batch write (runs in executor).

        Args:
            writes: List of (serial, state_dict) tuples to write
        """
        for serial, state_dict in writes:
            path = self.storage_dir / f"{serial}.json"

            # Atomic write: write to temp, then rename
            temp_path = path.with_suffix(".json.tmp")
            try:
                with open(temp_path, "w") as f:
                    json.dump(state_dict, f, indent=2)
                temp_path.replace(path)  # Atomic on POSIX
            except Exception as e:
                logger.error("Failed to write state for device %s: %s", serial, e)
                if temp_path.exists():
                    temp_path.unlink()

    def load_device_state(self, serial: str) -> dict[str, Any] | None:
        """Load device state from disk (synchronous).

        Loading only happens at startup, so blocking is acceptable here.
        This method can be called from both sync and async contexts.

        Args:
            serial: Device serial

        Returns:
            Dictionary with device state, or None if not found
        """
        return self._sync_load(serial)

    def _sync_load(self, serial: str) -> dict[str, Any] | None:
        """Synchronous load (runs in executor)."""
        device_path = self.storage_dir / f"{serial}.json"

        if not device_path.exists():
            logger.debug("No saved state found for device %s", serial)
            return None

        try:
            with open(device_path) as f:
                state_dict = json.load(f)

            state_dict = deserialize_device_state(state_dict)
            logger.info("Loaded saved state for device %s", serial)
            return state_dict

        except Exception as e:
            logger.error("Failed to load state for device %s: %s", serial, e)
            return None

    def delete_device_state(self, serial: str) -> None:
        """Delete device state from disk (synchronous).

        Deletion is rare and blocking is acceptable.

        Args:
            serial: Device serial
        """
        self._sync_delete(serial)

    def _sync_delete(self, serial: str) -> None:
        """Synchronous delete (runs in executor).

        Args:
            serial: Device serial
        """
        device_path = self.storage_dir / f"{serial}.json"

        if device_path.exists():
            try:
                device_path.unlink()
                logger.info("Deleted saved state for device %s", serial)
            except Exception as e:
                logger.error("Failed to delete state for device %s: %s", serial, e)

    def list_devices(self) -> list[str]:
        """List all devices with saved state (synchronous, safe to call anytime).

        Returns:
            List of device serials
        """
        serials = []
        for path in self.storage_dir.glob("*.json"):
            # Skip temp files
            if path.suffix == ".tmp":
                continue
            serials.append(path.stem)
        return sorted(serials)

    def delete_all_device_states(self) -> int:
        """Delete all device states from disk (synchronous).

        Returns:
            Number of devices deleted
        """
        deleted_count = 0
        for path in self.storage_dir.glob("*.json"):
            # Skip temp files
            if path.suffix == ".tmp":
                continue
            try:
                path.unlink()
                deleted_count += 1
                logger.info("Deleted saved state for device %s", path.stem)
            except Exception as e:
                logger.error("Failed to delete state for device %s: %s", path.stem, e)

        logger.info("Deleted %s device state(s) from persistent storage", deleted_count)
        return deleted_count

    async def shutdown(self) -> None:
        """Flush pending writes and shutdown executor.

        This should be called before the application exits to ensure
        all pending writes are persisted to disk.
        """
        logger.info("Shutting down async storage...")

        # Cancel pending flush task
        if self.flush_task and not self.flush_task.done():
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining pending writes
        await self._flush()

        # Wait for all background tasks to complete
        if self.background_tasks:
            logger.debug(
                f"Waiting for {len(self.background_tasks)} background tasks..."
            )
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Shutdown executor (non-blocking to avoid hanging on Windows)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.executor.shutdown, True)

        logger.info("Async storage shutdown complete")

    def get_stats(self) -> dict[str, Any]:
        """Get storage performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        coalesce_ratio = (
            (1 - (self.writes_executed / self.writes_queued))
            if self.writes_queued > 0
            else 0
        )

        return {
            "writes_queued": self.writes_queued,
            "writes_executed": self.writes_executed,
            "pending_writes": len(self.pending),
            "flushes": self.flushes,
            "coalesce_ratio": coalesce_ratio,
            "background_tasks": len(self.background_tasks),
            "debounce_ms": self.debounce_ms,
        }
