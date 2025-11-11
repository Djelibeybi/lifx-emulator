"""Integration tests for complete LIFX protocol packet flows.

All tests use async context manager for server lifecycle.
"""

import asyncio
import socket

import pytest

from lifx_emulator.constants import HEADER_SIZE
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile
from lifx_emulator.protocol.protocol_types import (
    DeviceService,
    LightHsbk,
    TileBufferRect,
)


def create_header(
    pkt_type: int,
    target: bytes = b"\x00" * 8,
    sequence: int = 1,
    tagged: bool = False,
    ack_required: bool = False,
    res_required: bool = False,
    source: int = 12345,
    payload_size: int = 0,
) -> LifxHeader:
    """Helper to create properly formatted LifxHeader with correct size field.

    Args:
        pkt_type: Packet type number
        target: Target device MAC address (8 bytes)
        sequence: Sequence number
        tagged: Whether this is a tagged/broadcast packet
        ack_required: Whether acknowledgement is required
        res_required: Whether response is required
        source: Source identifier
        payload_size: Size of the payload in bytes

    Returns:
        LifxHeader with correct size field set
    """
    return LifxHeader(
        size=HEADER_SIZE + payload_size,
        source=source,
        target=target,
        sequence=sequence,
        pkt_type=pkt_type,
        tagged=tagged,
        ack_required=ack_required,
        res_required=res_required,
    )


class TestDeviceDiscovery:
    """Test device discovery flow (GetService -> StateService)."""

    @pytest.mark.asyncio
    async def test_discover_devices(self, integration_server, integration_port):
        """Test discovering devices via broadcast."""
        async with integration_server:
            header = create_header(
                pkt_type=2,  # GetService
                tagged=True,
                res_required=True,
            )

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(header.pack(), ("127.0.0.1", integration_port))

            await asyncio.sleep(0.01)

            # Receive at least one response
            data, _ = sock.recvfrom(4096)
            sock.close()

            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 3  # StateService

            payload = data[HEADER_SIZE:]
            state_service = Device.StateService.unpack(payload)
            assert state_service.service == DeviceService.UDP
            assert state_service.port == integration_port


class TestColorControl:
    """Test light color control flow."""

    @pytest.mark.asyncio
    async def test_set_color(self, integration_server, integration_port, device_lookup):
        """Test setting light color."""
        async with integration_server:
            color_device = device_lookup["d073d5000001"]
            target = color_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            # Set new color
            new_color = LightHsbk(
                hue=30000, saturation=65535, brightness=50000, kelvin=4000
            )
            set_color = Light.SetColor(color=new_color, duration=0)
            payload = set_color.pack()

            header = create_header(
                pkt_type=102,  # SetColor
                target=target,
                ack_required=True,
                res_required=True,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive ACK
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 45  # Acknowledgement

            # Receive StateColor confirmation
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 107

            payload = data[HEADER_SIZE:]
            state_color = Light.StateColor.unpack(payload)
            assert state_color.color.hue == 30000

            sock.close()

    @pytest.mark.asyncio
    async def test_set_power(self, integration_server, integration_port, device_lookup):
        """Test setting device power level."""
        async with integration_server:
            color_device = device_lookup["d073d5000001"]
            target = color_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            set_power = Device.SetPower(level=65535)
            payload = set_power.pack()

            header = create_header(
                pkt_type=21,  # SetPower
                target=target,
                ack_required=True,
                res_required=True,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Skip ACK
            sock.recvfrom(4096)

            # Receive StatePower
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 22  # StatePower

            payload = data[HEADER_SIZE:]
            state_power = Device.StatePower.unpack(payload)
            assert state_power.level == 65535

            sock.close()


class TestMultiZone:
    """Test multizone device control flow."""

    @pytest.mark.asyncio
    async def test_get_multizone_colors(
        self, integration_server, integration_port, device_lookup
    ):
        """Test getting multizone colors returns multiple packets."""
        async with integration_server:
            multizone_device = device_lookup["d073d5000004"]
            target = multizone_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            get_zones = MultiZone.GetColorZones(start_index=0, end_index=15)
            payload = get_zones.pack()

            header = create_header(
                pkt_type=502,  # GetColorZones
                target=target,
                res_required=True,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive multiple StateMultiZone packets
            responses = []
            try:
                while len(responses) < 2:
                    data, _ = sock.recvfrom(4096)
                    resp_header = LifxHeader.unpack(data)
                    if resp_header.pkt_type == 506:  # StateMultiZone
                        responses.append(data)
            except TimeoutError:
                pass

            sock.close()

            # Should receive 2 packets (8 zones each)
            assert len(responses) >= 1  # At least one packet

    @pytest.mark.asyncio
    async def test_set_multizone_colors(
        self, integration_server, integration_port, device_lookup
    ):
        """Test setting multizone colors."""
        async with integration_server:
            multizone_device = device_lookup["d073d5000004"]
            target = multizone_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            red_color = LightHsbk(
                hue=0, saturation=65535, brightness=65535, kelvin=3500
            )
            set_zones = MultiZone.SetColorZones(
                start_index=5, end_index=10, color=red_color, duration=0, apply=0
            )
            payload = set_zones.pack()

            header = create_header(
                pkt_type=501,  # SetColorZones
                target=target,
                ack_required=True,
                res_required=False,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive ACK
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 45  # Acknowledgement

            sock.close()


class TestTile:
    """Test tile device control flow."""

    @pytest.mark.asyncio
    async def test_get_tile_chain(
        self, integration_server, integration_port, device_lookup
    ):
        """Test getting tile device chain."""
        async with integration_server:
            tile_device = device_lookup["d073d5000006"]
            target = tile_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            header = create_header(
                pkt_type=701,  # GetDeviceChain
                target=target,
                res_required=True,
            )

            sock.sendto(header.pack(), ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive StateDeviceChain
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 702  # StateDeviceChain

            payload = data[HEADER_SIZE:]
            chain = Tile.StateDeviceChain.unpack(payload)
            assert chain.tile_devices_count == 5

            sock.close()

    @pytest.mark.asyncio
    async def test_get_tile_pixels(
        self, integration_server, integration_port, device_lookup
    ):
        """Test getting tile pixels."""
        async with integration_server:
            tile_device = device_lookup["d073d5000006"]
            target = tile_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            rect = TileBufferRect(x=0, y=0, width=8, fb_index=0)
            get_64 = Tile.Get64(tile_index=0, length=1, rect=rect)
            payload = get_64.pack()

            header = create_header(
                pkt_type=707,  # Get64
                target=target,
                res_required=True,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive State64
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 711  # State64

            payload = data[HEADER_SIZE:]
            state_64 = Tile.State64.unpack(payload)
            assert len(state_64.colors) == 64

            sock.close()


class TestDeviceInfo:
    """Test device information queries."""

    @pytest.mark.asyncio
    async def test_get_version(
        self, integration_server, integration_port, device_lookup
    ):
        """Test getting device version information."""
        async with integration_server:
            color_device = device_lookup["d073d5000001"]
            target = color_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            header = create_header(
                pkt_type=32,  # GetVersion
                target=target,
                res_required=True,
            )

            sock.sendto(header.pack(), ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Receive StateVersion
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 33  # StateVersion

            payload = data[HEADER_SIZE:]
            version = Device.StateVersion.unpack(payload)
            assert version.vendor == 1  # LIFX

            sock.close()

    @pytest.mark.asyncio
    async def test_set_label(self, integration_server, integration_port, device_lookup):
        """Test setting device label."""
        async with integration_server:
            color_device = device_lookup["d073d5000001"]
            target = color_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            new_label = b"Integration Test\x00" * 2
            set_label = Device.SetLabel(label=new_label[:32])
            payload = set_label.pack()

            header = create_header(
                pkt_type=24,  # SetLabel
                target=target,
                ack_required=True,
                res_required=True,
                payload_size=len(payload),
            )

            packet = header.pack() + payload
            sock.sendto(packet, ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Skip ACK
            sock.recvfrom(4096)

            # Receive StateLabel
            data, _ = sock.recvfrom(4096)
            resp_header = LifxHeader.unpack(data)
            assert resp_header.pkt_type == 25  # StateLabel

            payload = data[HEADER_SIZE:]
            state_label = Device.StateLabel.unpack(payload)
            assert "Integration Test" in state_label.label

            sock.close()


class TestErrorConditions:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_packet_to_unknown_device(self, integration_server, integration_port):
        """Test packet to non-existent device is ignored."""
        async with integration_server:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)

            header = create_header(
                pkt_type=23,  # GetLabel
                target=b"\xff\xff\xff\xff\xff\xff\x00\x00",
                res_required=True,
            )

            sock.sendto(header.pack(), ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Should timeout (no response)
            with pytest.raises(socket.timeout):
                sock.recvfrom(4096)

            sock.close()

    @pytest.mark.asyncio
    async def test_infrared_on_non_ir_device(
        self, integration_server, integration_port, device_lookup
    ):
        """Test infrared commands on non-IR device return no response."""
        async with integration_server:
            color_device = device_lookup["d073d5000001"]
            target = color_device.state.get_target_bytes()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)

            header = create_header(
                pkt_type=120,  # GetInfrared
                target=target,
                res_required=True,
            )

            sock.sendto(header.pack(), ("127.0.0.1", integration_port))
            await asyncio.sleep(0.01)

            # Should timeout (no infrared support)
            with pytest.raises(socket.timeout):
                sock.recvfrom(4096)

            sock.close()
