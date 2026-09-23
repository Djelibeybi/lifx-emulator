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


class MdnsUpdateError(RuntimeError):
    """An advertisement barrier failed without cancelling its caller."""


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
        # Keep successful identities for this owner lifetime: zeroconf may
        # self-cache delayed PTR answers much longer than our wire TTL.
        self._tombstones: dict[str, ServiceInfo] = {}
        self._pending: Callable[[], dict[str, ServiceInfo]] | None = None
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
        if operation in {"register", "update"}:
            # The first public stage owns the registry entry; a failed probe
            # never reaches this point and must never receive our goodbyes.
            self._services[info.name] = info
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

    def schedule(self, snapshot: Callable[[], dict[str, ServiceInfo]]) -> None:
        """Coalesce committed changes into one owned latest-snapshot worker."""
        if self._error is not None or not self._tasks.accepting:
            return
        self._pending = snapshot
        if self._tail is None or self._tail.done():
            self._tail = self._tasks.schedule(self._run_reconcile(), "mdns-membership")

    async def _run_reconcile(self) -> None:
        try:
            while self._pending is not None:
                snapshot, self._pending = self._pending, None
                async with self._lock:
                    await self._reconcile(snapshot())
        except asyncio.CancelledError:
            raise
        except Exception as error:
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
            self._tombstones[name] = info
        operations: list[Awaitable[None]] = []
        for name, info in infos.items():
            previous = self._services.get(name)
            if previous is not None:
                if self._same_records(previous, info):
                    continue
                operations.append(self._operation("update", info))
                continue
            tombstone = self._tombstones.pop(name, None)
            if tombstone is not None:
                if self._same_records(tombstone, info):
                    info = tombstone
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

    async def wait_for_updates(self) -> None:
        """Observe a stable worker without propagating its task cancellation."""
        while True:
            tail = self._tail
            if tail is not None:
                # asyncio.wait does not cancel the shared task when this caller
                # is cancelled, nor re-raise and mutate its retained exception.
                await asyncio.wait({tail})
                if tail.cancelled():
                    raise MdnsUpdateError("mDNS update interrupted by shutdown")
            if self._error is not None:
                raise MdnsUpdateError(str(self._error)) from self._error
            if tail is self._tail:
                return

    async def stop(self) -> None:
        """Bound draining and goodbye work, then close the owned responder once."""
        self._tasks.stop_accepting()
        await self._tasks.shutdown(timeout=_OPERATION_TIMEOUT)
        self._pending = None
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
            self._tombstones.clear()
        if error is not None:
            if isinstance(error, asyncio.CancelledError):
                raise error
            raise MdnsUpdateError(str(error)) from error
