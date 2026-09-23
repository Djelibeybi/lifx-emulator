"""Owned public-zeroconf adapter for LIFX DNS-SD advertisements."""

from __future__ import annotations

import asyncio
import ipaddress
from collections.abc import Awaitable, Callable, Iterable
from enum import Enum

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.devices import EmulatedLifxDevice
from lifx_emulator.devices.states import Connectivity, validate_mdns_address

SERVICE_TYPE = "_lifx._udp.local."
_OPERATION_TIMEOUT = 5.0


class MdnsStatus(str, Enum):
    """Lifecycle state, not an independently verified network-health signal."""

    DISABLED = "disabled"
    STOPPED = "stopped"
    RUNNING = "running"
    FAILED = "failed"

    __str__ = str.__str__


def resolve_address(device: EmulatedLifxDevice, ipv4: str, ipv6: str) -> str | None:
    """Resolve only explicit intent or a concrete matching-family bind."""
    state = device.state
    if not state.mdns_enabled:
        return None
    fallback = ipv6 if state.connectivity == Connectivity.THREAD else ipv4
    try:
        return validate_mdns_address(
            state.mdns_address if state.mdns_address is not None else fallback,
            state.connectivity,
        )
    except ValueError as error:
        raise ValueError(
            f"Device {state.serial} ({state.connectivity}): {error}"
        ) from error


class MdnsResponder:
    """Own complete service snapshots and await both zeroconf operation stages."""

    def __init__(
        self,
        address: str,
        port: int,
        ipv6_address: str = "::1",
        on_error: Callable[[BaseException], None] | None = None,
    ):
        self.address = address
        self.port = port
        self.ipv6_address = ipv6_address
        self._owner: AsyncZeroconf | None = None
        self._services: dict[str, ServiceInfo] = {}
        self._tombstones: dict[str, tuple[ServiceInfo, asyncio.TimerHandle]] = {}
        self._lock = asyncio.Lock()
        self._tasks = BackgroundTaskTracker("mdns-reconcile")
        self._tail: asyncio.Task[None] | None = None
        self._error: BaseException | None = None
        self._on_error = on_error

    def service_info(self, device: EmulatedLifxDevice) -> ServiceInfo | None:
        """Snapshot the complete device record before publishing it."""
        state = device.state
        address = resolve_address(device, self.address, self.ipv6_address)
        if address is None:
            return None
        serial = state.serial
        return ServiceInfo(
            SERVICE_TYPE,
            f"{serial}.{SERVICE_TYPE}",
            addresses=[ipaddress.ip_address(address).packed],
            port=self.port,
            properties={
                "id": serial,
                "p": str(state.product),
                "fw": f"{state.version_major}.{state.version_minor}",
                "tm": "2" if state.connectivity == Connectivity.THREAD else "1",
            },
            server=f"{serial}.local.",
            host_ttl=10,
            other_ttl=10,
        )

    @property
    def owns_resources(self) -> bool:
        """Retain failed-close ownership so a later stop can finish cleanup."""
        return self._owner is not None

    def snapshot(self, devices: Iterable[EmulatedLifxDevice]) -> dict[str, ServiceInfo]:
        """Capture a complete immutable record set before scheduling work."""
        return {
            info.name: info
            for device in devices
            if (info := self.service_info(device)) is not None
        }

    async def _operation(self, operation: str, info: ServiceInfo) -> None:
        owner = self._owner
        if owner is None:
            raise RuntimeError("mDNS responder is closed")
        if operation == "register":
            announcement = await owner.async_register_service(info, ttl=10)
        elif operation == "update":
            announcement = await owner.async_update_service(info)
        else:
            announcement = await owner.async_unregister_service(info)
        await announcement

    async def start(self, devices: Iterable[EmulatedLifxDevice]) -> None:
        """Register snapshots and finish announcements before reporting success."""
        if self._owner is not None:
            return
        infos = self.snapshot(devices)
        self._owner = AsyncZeroconf(
            interfaces=[self.address], ip_version=IPVersion.V4Only
        )
        try:
            async with self._lock:
                await self._reconcile(infos)
        except BaseException:
            await self.stop()
            raise

    def schedule(self, infos: dict[str, ServiceInfo]) -> None:
        """Queue one committed fleet generation, retaining every admitted update."""
        if self._error is not None or not self._tasks.accepting:
            return
        task = self._tasks.schedule(self._run_reconcile(infos), "mdns-membership")
        if task is not None:
            self._tail = task

    async def _run_reconcile(self, infos: dict[str, ServiceInfo]) -> None:
        try:
            async with self._lock:
                if self._error is not None:
                    raise self._error
                await self._reconcile(infos)
        except BaseException as error:
            self._error = error
            # Notify only after releasing the reconcile lock.
            if self._tasks.accepting and self._on_error is not None:
                self._on_error(error)
            raise

    async def _complete_operations(self, operations: list[Awaitable[None]]) -> None:
        """Finish all owned operations even when one fails, without orphan tasks."""
        if not operations:
            return
        results = await asyncio.gather(*operations, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result

    async def _reconcile(self, infos: dict[str, ServiceInfo]) -> None:
        removed = self._services.keys() - infos.keys()
        await self._complete_operations(
            [self._operation("unregister", self._services[name]) for name in removed]
        )
        for name in removed:
            info = self._services.pop(name)
            handle = asyncio.get_running_loop().call_later(10, self._expire, name)
            self._tombstones[name] = (info, handle)
        operations: list[Awaitable[None]] = []
        for name, info in infos.items():
            previous = self._services.get(name)
            if previous is not None:
                if self._same_records(previous, info):
                    continue
                self._services[name] = info
                operations.append(self._operation("update", info))
                continue
            tombstone = self._tombstones.pop(name, None)
            if tombstone is not None:
                owned, handle = tombstone
                handle.cancel()
                if self._same_records(owned, info):
                    info = owned
            self._services[name] = info
            operations.append(
                self._operation("update" if tombstone else "register", info)
            )
        await self._complete_operations(operations)

    @staticmethod
    def _same_records(first: ServiceInfo, second: ServiceInfo) -> bool:
        return (
            first.name,
            first.server,
            first.port,
            first.properties,
            first.addresses_by_version(IPVersion.All),
        ) == (
            second.name,
            second.server,
            second.port,
            second.properties,
            second.addresses_by_version(IPVersion.All),
        )

    def _expire(self, name: str) -> None:
        self._tombstones.pop(name, None)

    async def wait_for_updates(self) -> None:
        """Shield shared work from waiter cancellation; observe a stable tail."""
        while True:
            tail = self._tail
            if tail is not None:
                await asyncio.shield(tail)
            if self._error is not None:
                raise self._error
            if tail is self._tail:
                return

    async def stop(self) -> None:
        """Bound draining and goodbye work, then close the owned responder once."""
        self._tasks.stop_accepting()
        await self._tasks.shutdown(timeout=_OPERATION_TIMEOUT)
        for _, handle in self._tombstones.values():
            handle.cancel()
        self._tombstones.clear()
        owner = self._owner
        if owner is None:
            return
        error = (
            self._error if not isinstance(self._error, asyncio.CancelledError) else None
        )
        try:
            try:
                await asyncio.wait_for(
                    self._complete_operations(
                        [
                            self._operation("unregister", info)
                            for info in tuple(self._services.values())
                        ]
                    ),
                    _OPERATION_TIMEOUT,
                )
            except BaseException as exc:
                error = exc
        finally:
            await asyncio.wait_for(owner.async_close(), _OPERATION_TIMEOUT)
            self._owner = None
            self._services.clear()
        if error is not None:
            raise error
