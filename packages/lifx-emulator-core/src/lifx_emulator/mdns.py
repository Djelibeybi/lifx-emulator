"""Owned public-zeroconf adapter for LIFX DNS-SD advertisements."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from lifx_emulator.devices import EmulatedLifxDevice

SERVICE_TYPE = "_lifx._udp.local."


class MdnsResponder:
    """Own complete service snapshots and await both zeroconf operation stages."""

    def __init__(self, address: str, port: int):
        self.address = address
        self.port = port
        self._owner: AsyncZeroconf | None = None
        self._services: dict[str, ServiceInfo] = {}

    def service_info(self, device: EmulatedLifxDevice) -> ServiceInfo:
        """Snapshot the complete device record before publishing it."""
        state = device.state
        serial = state.serial
        return ServiceInfo(
            SERVICE_TYPE,
            f"{serial}.{SERVICE_TYPE}",
            addresses=[ipaddress.ip_address(self.address).packed],
            port=self.port,
            properties={
                "id": serial,
                "p": str(state.product),
                "fw": f"{state.version_major}.{state.version_minor}",
                "tm": "1",
            },
            server=f"{serial}.local.",
            host_ttl=10,
            other_ttl=10,
        )

    async def start(self, devices: Iterable[EmulatedLifxDevice]) -> None:
        """Register snapshots and finish announcements before reporting success."""
        if self._owner is not None:
            return
        infos = [self.service_info(device) for device in devices]
        self._owner = AsyncZeroconf(
            interfaces=[self.address], ip_version=IPVersion.V4Only
        )
        try:
            for info in infos:
                # Track before the call: either stage can fail after registration.
                self._services[info.name] = info
                announcement = await self._owner.async_register_service(info, ttl=10)
                await announcement
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        """Unregister every attempted service, then close the owned responder."""
        owner = self._owner
        if owner is None:
            return
        error: BaseException | None = None
        try:
            for info in tuple(self._services.values()):
                try:
                    goodbye = await owner.async_unregister_service(info)
                    await goodbye
                except BaseException as exc:
                    if error is None:
                        error = exc
        finally:
            await owner.async_close()
            self._owner = None
            self._services.clear()
        if error is not None:
            raise error
