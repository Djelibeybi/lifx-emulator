"""Device packet handlers."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Device
from lifx_emulator.protocol.protocol_types import DeviceService as ProtocolDeviceService

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)


class GetServiceHandler(PacketHandler):
    """Handle DeviceGetService (2) -> DeviceStateService (3)."""

    PKT_TYPE = Device.GetService.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        logger.debug(
            "Sending StateService: %s [%s]",
            ProtocolDeviceService.UDP,
            device_state.port,
        )
        return [
            Device.StateService(
                service=ProtocolDeviceService.UDP, port=device_state.port
            )
        ]


class GetPowerHandler(PacketHandler):
    """Handle DeviceGetPower (20) -> DeviceStatePower (22)."""

    PKT_TYPE = Device.GetPower.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Device.StatePower(level=device_state.power_level)]


class SetPowerHandler(PacketHandler):
    """Handle DeviceSetPower (21) -> DeviceStatePower (22)."""

    PKT_TYPE = Device.SetPower.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Device.SetPower | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.power_level = packet.level
            logger.info("Power set to %s", device_state.power_level)

        if res_required:
            return [Device.StatePower(level=device_state.power_level)]
        return []


class GetLabelHandler(PacketHandler):
    """Handle DeviceGetLabel (23) -> DeviceStateLabel (25)."""

    PKT_TYPE = Device.GetLabel.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Device.StateLabel(label=device_state.label)]


class SetLabelHandler(PacketHandler):
    """Handle DeviceSetLabel (24) -> DeviceStateLabel (25)."""

    PKT_TYPE = Device.SetLabel.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Device.SetLabel | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.label = packet.label
            logger.info("Label set to '%s'", device_state.label)

        if res_required:
            return [Device.StateLabel(label=device_state.label)]
        return []


class GetVersionHandler(PacketHandler):
    """Handle DeviceGetVersion (32) -> DeviceStateVersion (33)."""

    PKT_TYPE = Device.GetVersion.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [
            Device.StateVersion(
                vendor=device_state.vendor, product=device_state.product
            )
        ]


class GetInfoHandler(PacketHandler):
    """Handle DeviceGetInfo (34) -> DeviceStateInfo (35)."""

    PKT_TYPE = Device.GetInfo.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        current_time = int(time.time() * 1e9)  # nanoseconds
        return [
            Device.StateInfo(
                time=current_time, uptime=device_state.uptime_ns, downtime=0
            )
        ]


class GetHostFirmwareHandler(PacketHandler):
    """Handle DeviceGetHostFirmware (14) -> DeviceStateHostFirmware (15)."""

    PKT_TYPE = Device.GetHostFirmware.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [
            Device.StateHostFirmware(
                build=device_state.build_timestamp,
                version_minor=device_state.version_minor,
                version_major=device_state.version_major,
            )
        ]


class GetWifiInfoHandler(PacketHandler):
    """Handle DeviceGetWifiInfo (16) -> DeviceStateWifiInfo (17)."""

    PKT_TYPE = Device.GetWifiInfo.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Device.StateWifiInfo(signal=device_state.wifi_signal)]


class GetLocationHandler(PacketHandler):
    """Handle DeviceGetLocation (48) -> DeviceStateLocation (50)."""

    PKT_TYPE = Device.GetLocation.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [
            Device.StateLocation(
                location=device_state.location_id,
                label=device_state.location_label,
                updated_at=device_state.location_updated_at,
            )
        ]


class SetLocationHandler(PacketHandler):
    """Handle DeviceSetLocation (49) -> DeviceStateLocation (50)."""

    PKT_TYPE = Device.SetLocation.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Device.SetLocation | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.location_id = packet.location
            device_state.location_label = packet.label
            device_state.location_updated_at = packet.updated_at
            loc_id = packet.location.hex()[:8]
            logger.info(
                "Location set to '%s' (id=%s...)", device_state.location_label, loc_id
            )

        if res_required:
            return [
                Device.StateLocation(
                    location=device_state.location_id,
                    label=device_state.location_label,
                    updated_at=device_state.location_updated_at,
                )
            ]
        return []


class GetGroupHandler(PacketHandler):
    """Handle DeviceGetGroup (51) -> DeviceStateGroup (53)."""

    PKT_TYPE = Device.GetGroup.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [
            Device.StateGroup(
                group=device_state.group_id,
                label=device_state.group_label,
                updated_at=device_state.group_updated_at,
            )
        ]


class SetGroupHandler(PacketHandler):
    """Handle DeviceSetGroup (52) -> DeviceStateGroup (53)."""

    PKT_TYPE = Device.SetGroup.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Device.SetGroup | None,
        res_required: bool,
    ) -> list[Any]:
        if packet:
            device_state.group_id = packet.group
            device_state.group_label = packet.label
            device_state.group_updated_at = packet.updated_at
            grp_id = packet.group.hex()[:8]
            logger.info(
                "Group set to '%s' (id=%s...)", device_state.group_label, grp_id
            )

        if res_required:
            return [
                Device.StateGroup(
                    group=device_state.group_id,
                    label=device_state.group_label,
                    updated_at=device_state.group_updated_at,
                )
            ]
        return []


class EchoRequestHandler(PacketHandler):
    """Handle DeviceEchoRequest (58) -> DeviceEchoResponse (59)."""

    PKT_TYPE = Device.EchoRequest.PKT_TYPE

    def handle(
        self,
        device_state: DeviceState,
        packet: Device.EchoRequest | None,
        res_required: bool,
    ) -> list[Any]:
        payload = packet.payload if packet else b"\x00" * 64
        return [Device.EchoResponse(payload=payload[:64].ljust(64, b"\x00"))]


class GetWifiFirmwareHandler(PacketHandler):
    """Handle DeviceGetWifiFirmware (18) -> DeviceStateWifiFirmware (19)."""

    PKT_TYPE = Device.GetWifiFirmware.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        build = int(time.time()) - 1000000000  # Example build timestamp
        return [
            Device.StateWifiFirmware(
                build=build,
                version_minor=device_state.version_minor,
                version_major=device_state.version_major,
            )
        ]


class SetRebootHandler(PacketHandler):
    """Handle DeviceSetReboot (38) - just acknowledge, don't actually reboot."""

    PKT_TYPE = Device.SetReboot.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        serial = device_state.serial
        logger.info("Device %s: Received reboot request (ignored in emulator)", serial)
        # In a real device, this would trigger a reboot
        # In emulator, we just acknowledge it
        return []


# List of all device handlers for easy registration
ALL_DEVICE_HANDLERS = [
    GetServiceHandler(),
    GetPowerHandler(),
    SetPowerHandler(),
    GetLabelHandler(),
    SetLabelHandler(),
    GetVersionHandler(),
    GetInfoHandler(),
    GetHostFirmwareHandler(),
    GetWifiInfoHandler(),
    GetLocationHandler(),
    SetLocationHandler(),
    GetGroupHandler(),
    SetGroupHandler(),
    EchoRequestHandler(),
    GetWifiFirmwareHandler(),
    SetRebootHandler(),
]
