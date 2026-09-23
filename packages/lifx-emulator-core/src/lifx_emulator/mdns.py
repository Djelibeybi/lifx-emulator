"""Owned public-zeroconf adapter for LIFX DNS-SD advertisements."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from lifx_emulator.devices import EmulatedLifxDevice
from lifx_emulator.devices.states import Connectivity, validate_mdns_address

SERVICE_TYPE = "_lifx._udp.local."


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

    def __init__(self, address: str, port: int, ipv6_address: str = "::1"):
        self.address = address
        self.port = port
        self.ipv6_address = ipv6_address
        self._owner: AsyncZeroconf | None = None
        self._services: dict[str, ServiceInfo] = {}

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

    async def start(self, devices: Iterable[EmulatedLifxDevice]) -> None:
        """Register snapshots and finish announcements before reporting success."""
        if self._owner is not None:
            return
        infos = [
            info
            for device in devices
            if (info := self.service_info(device)) is not None
        ]
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
