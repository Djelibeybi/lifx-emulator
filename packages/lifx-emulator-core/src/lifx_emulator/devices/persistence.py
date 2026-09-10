"""Async persistent storage with debouncing to avoid blocking event loop."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from lifx_emulator.devices.state_serializer import (
    deserialize_device_state,
    serialize_device_state,
)

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path.home() / ".lifx-emulator"
_SHUTDOWN_FLUSH_ATTEMPTS = 2

# Device serials are 12-char hex strings (6-byte MAC). Validating against this
# pattern before using a serial in a filesystem path prevents path traversal.
_SERIAL_RE = re.compile(r"^[0-9a-fA-F]{12}$")


class DevicePersistenceError(RuntimeError):
    """Raised when persistent device state cannot be committed safely."""

    def __init__(self, failed_serials: list[str], message: str):
        self.failed_serials = tuple(failed_serials)
        super().__init__(message)


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

    def _device_path(self, serial: str) -> Path:
        """Resolve the on-disk path for a device serial.

        Validates the serial against the 12-char hex format before building the
        path, preventing path-traversal via crafted serials (e.g. "../../etc").

        Args:
            serial: Device serial (12 hex chars)

        Returns:
            Path to the device's state file inside storage_dir

        Raises:
            ValueError: If the serial is not a valid 12-char hex string
        """
        if not _SERIAL_RE.fullmatch(serial):
            raise ValueError(f"Invalid device serial: {serial!r}")
        # Resolve links as well as traversal components before enforcing the
        # storage boundary. A valid serial alone cannot constrain a symlink.
        root = os.path.realpath(self.storage_dir)
        path = os.path.realpath(os.path.join(root, f"{serial}.json"))
        if not path.startswith(root + os.sep):
            raise ValueError("Device state path escapes the storage directory")
        return Path(path)

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

            # Keep the lock until the captured batch has finished. Per-device
            # deletion uses the same lock, so an older batch can never write a
            # device back after its deletion has committed.
            loop = asyncio.get_running_loop()
            flush_future = loop.run_in_executor(
                self.executor, self._batch_write, writes
            )
            failed = await self._await_indivisible(flush_future, "batch state flush")
            self.writes_executed += len(writes) - len(failed)
            for serial, state_dict in failed:
                self.pending.setdefault(serial, state_dict)

            if failed:
                failed_serials = [serial for serial, _state in failed]
                raise DevicePersistenceError(
                    failed_serials,
                    "Failed to flush device states for: "
                    + ", ".join(sorted(failed_serials)),
                )
            logger.debug("Flushed %s device states to disk", len(writes))

    async def _await_indivisible(
        self, future: asyncio.Future[Any], operation: str
    ) -> Any:
        """Wait for executor work to finish even if its caller is cancelled."""
        cancellation_requested = False
        while True:
            try:
                result = await asyncio.shield(future)
                if cancellation_requested:
                    logger.debug("Completed %s after cancellation", operation)
                return result
            except asyncio.CancelledError:
                cancellation_requested = True

    def _batch_write(self, writes: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
        """Synchronous batch write (runs in executor).

        Args:
            writes: List of (serial, state_dict) tuples to write
        """
        failed_writes = []
        for serial, state_dict in writes:
            try:
                self._write_state(serial, state_dict)
            except DevicePersistenceError as e:
                failed_writes.append((serial, state_dict))
                logger.error("%s", e)
        return failed_writes

    def _write_state(self, serial: str, state_dict: dict) -> None:
        """Atomically write one serialised state or raise a typed error."""
        try:
            path = self._device_path(serial)
        except ValueError as e:
            raise DevicePersistenceError(
                [serial], f"Cannot write state for device {serial}: {e}"
            ) from e

        temp_path = path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w") as file_handle:
                json.dump(state_dict, file_handle, indent=2)
            temp_path.replace(path)
        except Exception as e:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                logger.exception("Failed to remove temporary state file %s", temp_path)
            raise DevicePersistenceError(
                [serial], f"Failed to write state for device {serial}: {e}"
            ) from e

    async def commit_device_state(self, device_state: Any) -> None:
        """Write a candidate without queueing failed, uncommitted mutations."""
        serial = device_state.serial
        state_dict = serialize_device_state(device_state)
        async with self.lock:
            future = asyncio.get_running_loop().run_in_executor(
                self.executor, self._write_state, serial, state_dict
            )
            await self._await_indivisible(future, f"state commit for {serial}")
            # Only a successful commit supersedes previously queued state.
            self.pending.pop(serial, None)
            self.writes_queued += 1
            self.writes_executed += 1
            self.flushes += 1

    async def flush_device_state(self, serial: str) -> bool:
        """Flush one queued state after all earlier captured batches finish."""
        async with self.lock:
            state_dict = self.pending.pop(serial, None)
            if state_dict is None:
                return False

            loop = asyncio.get_running_loop()
            write_future = loop.run_in_executor(
                self.executor, self._write_state, serial, state_dict
            )
            try:
                await self._await_indivisible(
                    write_future, f"state commit for {serial}"
                )
            except BaseException:
                self.pending.setdefault(serial, state_dict)
                raise

            self.writes_executed += 1
            self.flushes += 1
            return True

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
        try:
            device_path = self._device_path(serial)
        except ValueError as e:
            logger.error("Cannot load state: %s", e)
            return None

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

    async def delete_device_state(self, serial: str) -> bool:
        """Delete queued and persisted device state as one ordered operation.

        Deletion is rare and blocking is acceptable.

        Args:
            serial: Device serial
        """
        async with self.lock:
            self.pending.pop(serial, None)
            return self._sync_delete(serial)

    async def delete_device_states(self, serials: list[str]) -> int:
        """Delete selected states transactionally while writes are fenced."""
        async with self.lock:
            pending = {
                serial: self.pending.pop(serial)
                for serial in serials
                if serial in self.pending
            }
            loop = asyncio.get_running_loop()
            try:
                future = loop.run_in_executor(
                    self.executor,
                    self._sync_delete_transaction,
                    serials,
                )
                return await self._await_indivisible(future, "bulk state deletion")
            except BaseException:
                # No newer snapshots can arrive while the lock is held.
                self.pending.update(pending)
                raise

    def _sync_delete_transaction(self, serials: list[str]) -> int:
        """Stage selected files, roll back failed staging, then unlink."""
        paths: list[tuple[str, Path]] = []
        for serial in serials:
            try:
                path = self._device_path(serial)
            except ValueError as e:
                raise DevicePersistenceError(
                    [serial], f"Cannot delete state for device {serial}: {e}"
                ) from e
            if path.exists() and not path.is_file():
                raise DevicePersistenceError(
                    [serial], f"State path for device {serial} is not a file"
                )
            paths.append((serial, path))

        staged: list[tuple[str, Path, Path]] = []
        failed_serial = "unknown"
        try:
            for serial, path in paths:
                failed_serial = serial
                if not path.exists():
                    continue
                staging_path = path.with_suffix(".json.deleting")
                if staging_path.exists():
                    raise OSError(f"staging path already exists: {staging_path}")
                path.replace(staging_path)
                staged.append((serial, path, staging_path))
        except OSError as e:
            rollback_failures: list[str] = []
            for serial, path, staging_path in reversed(staged):
                try:
                    staging_path.replace(path)
                except OSError:
                    rollback_failures.append(serial)
                    logger.exception("Failed to roll back staged state for %s", serial)
            failed = [failed_serial]
            failed.extend(rollback_failures)
            raise DevicePersistenceError(
                failed,
                f"Failed to stage device-state deletion for {failed_serial}: {e}",
            ) from e

        for serial, _path, staging_path in staged:
            try:
                staging_path.unlink()
            except OSError:
                # Staging completed, so the transaction is committed. A leftover
                # non-JSON staging file cannot resurrect a device on restart.
                logger.exception("Failed to remove staged state for %s", serial)
        return len(staged)

    def _sync_delete(self, serial: str) -> bool:
        """Delete one persisted state file while the caller holds ``lock``.

        Args:
            serial: Device serial
        """
        try:
            device_path = self._device_path(serial)
        except ValueError as e:
            raise DevicePersistenceError(
                [serial], f"Cannot delete state for device {serial}: {e}"
            ) from e

        try:
            if device_path.exists():
                device_path.unlink()
                logger.info("Deleted saved state for device %s", serial)
                return True
        except OSError as e:
            raise DevicePersistenceError(
                [serial], f"Failed to delete state for device {serial}: {e}"
            ) from e
        return False

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
        failed_serials: list[str] = []
        for path in self.storage_dir.glob("*.json"):
            # Skip temp files
            if path.suffix == ".tmp":
                continue
            try:
                deleted_count += int(self._sync_delete(path.stem))
            except DevicePersistenceError:
                failed_serials.append(path.stem)

        if failed_serials:
            serials = ", ".join(sorted(failed_serials))
            raise DevicePersistenceError(
                failed_serials,
                f"Failed to delete device states for: {serials}",
            )

        logger.info("Deleted %s device state(s) from persistent storage", deleted_count)
        return deleted_count

    async def shutdown(self) -> None:
        """Flush pending writes and shutdown executor.

        This should be called before the application exits to ensure
        all pending writes are persisted to disk.
        """
        logger.info("Shutting down async storage...")

        try:
            # Cancel pending debounce delay. An in-flight executor flush treats
            # cancellation as deferred until its indivisible write completes.
            if self.flush_task and not self.flush_task.done():
                self.flush_task.cancel()
                try:
                    await self.flush_task
                except (asyncio.CancelledError, DevicePersistenceError):
                    pass

            if self.background_tasks:
                logger.debug(
                    "Waiting for %s background tasks...", len(self.background_tasks)
                )
                await asyncio.gather(*self.background_tasks, return_exceptions=True)

            last_error: DevicePersistenceError | None = None
            for _attempt in range(_SHUTDOWN_FLUSH_ATTEMPTS):
                if not self.pending:
                    break
                try:
                    await self._flush()
                except DevicePersistenceError as error:
                    last_error = error

            if self.pending:
                failed_serials = sorted(self.pending)
                raise DevicePersistenceError(
                    failed_serials,
                    "Persistent state remained unwritten after shutdown retries: "
                    + ", ".join(failed_serials),
                ) from last_error
        finally:
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
