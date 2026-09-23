"""Spike-only lifecycle adapter; no production integration or private zeroconf API."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable, Sequence
from typing import Any

_LOGGER = logging.getLogger(__name__)


class RecoveryPrototype:
    """Own one responder per attempt and serialise explicit lifecycle operations."""

    def __init__(self, factory: Callable[[], Any], *, enabled: bool = True):
        self._factory = factory
        self._enabled = enabled
        self._status = "stopped" if enabled else "disabled"
        self._error: str | None = None
        self._responder: Any = None
        self._lock = asyncio.Lock()

    @property
    def mdns_status(self) -> str:
        return self._status

    @property
    def mdns_error(self) -> str | None:
        return self._error

    def admit_thread(self) -> None:
        """Run before changing fleet membership."""
        if self._status == "failed":
            raise RuntimeError(
                "Recover mDNS with retry_mdns before adding Thread devices"
            )

    async def _close(self) -> None:
        if self._responder is not None:
            # Keep ownership if close fails: retry must not orphan this responder.
            await self._responder.async_close()
            self._responder = None

    async def _fail(self, error: BaseException, operation: str = "startup") -> None:
        self._status = "failed"
        if self._error is None:
            self._error = f"{operation}: {type(error).__name__}: {error}"
        _LOGGER.warning("mDNS failed: %s", self._error)
        try:
            await self._close()
        except Exception as cleanup_error:
            self._error += f"; cleanup: {type(cleanup_error).__name__}: {cleanup_error}"
            _LOGGER.warning("mDNS cleanup failed: %s", cleanup_error)

    async def retry_mdns(self, infos: Sequence[Any]) -> bool:
        """Start or explicitly retry the entire fleet; never retry automatically."""
        async with self._lock:
            if not self._enabled:
                return False
            if self._status == "running":
                return True
            try:
                await self._close()
                self._responder = self._factory()
                for info in infos:
                    announcement = await self._responder.async_register_service(
                        info, ttl=10
                    )
                    await announcement
            except asyncio.CancelledError as error:
                await self._fail(error)
                raise
            except Exception as error:
                await self._fail(error)
                return False
            self._status = "running"
            self._error = None
            return True

    async def operate(
        self, operation: str, value: Any = None, *, server: Any = None
    ) -> bool:
        """Handle supported-operation errors; running is lifecycle state only."""
        methods = {
            "register": "async_register_service",
            "update": "async_update_service",
            "unregister": "async_unregister_service",
            "interfaces": "async_update_interfaces",
            "close": "async_close",
        }
        method_name = methods[operation]
        async with self._lock:
            if self._status != "running":
                return False
            boundary = operation
            try:
                method = getattr(self._responder, method_name)
                result = await method() if operation == "close" else await method(value)
                if inspect.isawaitable(result):
                    boundary = f"{operation}.announcement"
                    await result
                if operation == "close":
                    self._responder = None
                    self._status = "stopped"
            except asyncio.CancelledError as error:
                await self._fail(error, boundary)
                await self._apply_policy(server)
                raise
            except Exception as error:
                await self._fail(error, boundary)
                await self._apply_policy(server)
                return False
            return True

    async def _apply_policy(self, server: Any) -> None:
        if server is not None and any(
            str(device.state.connectivity) == "thread"
            for device in server.get_all_devices()
        ):
            await server.stop()

    async def runtime_failure(self, error: Exception, server: Any) -> None:
        """Injected notification; silent listener loss is outside the guarantee."""
        async with self._lock:
            await self._fail(error, "injected")
            await self._apply_policy(server)

    async def stop(self) -> None:
        async with self._lock:
            try:
                await self._close()
            except Exception as error:
                await self._fail(error)
                raise
            if self._status != "failed":
                self._status = "stopped" if self._enabled else "disabled"
