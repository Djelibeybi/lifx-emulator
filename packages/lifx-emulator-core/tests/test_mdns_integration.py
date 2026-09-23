"""Required-mode real-stack production evidence, separate from simulation."""

import importlib
import ipaddress
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from lifx_emulator.devices import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from test_mdns_responder import parse_records, raw_query

REQUIRED = os.environ.get("MDNS_INTEGRATION_REQUIRED") == "1"
pytestmark = pytest.mark.skipif(
    not REQUIRED,
    reason="Required mode and a pristine oracle are needed for real-stack evidence",
)
ROOT = Path(__file__).resolve().parents[3]
INPUTS = ROOT / "scripts/mdns_spike_inputs/active.json"
PREFIX = "d073d7"


def run_git(path, *arguments):
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


@pytest.fixture
def oracle():
    source = os.environ.get("LIFX_ASYNC_PATH")
    assert source, "Required integration needs LIFX_ASYNC_PATH=<pristine checkout>/src"
    source = Path(source).resolve()
    checkout = source.parent
    inputs = json.loads(INPUTS.read_text())
    assert (
        run_git(checkout, "rev-parse", "HEAD")
        == inputs["oracle"]["revision"]
        == "48b7efbff59656499373b13ef17e3008d125feb5"
    )
    assert run_git(checkout, "rev-parse", "HEAD^{tree}") == inputs["oracle"]["tree"]
    assert run_git(checkout, "status", "--porcelain") == ""
    api = importlib.import_module("lifx.api")
    assert Path(api.__file__).resolve().is_relative_to(source), (
        "Client must load from pristine oracle"
    )
    daemon = "mDNSResponder" if sys.platform == "darwin" else "avahi-daemon"
    daemon_check = subprocess.run(
        ["pgrep", "-x", daemon], capture_output=True, timeout=10
    )
    assert daemon_check.returncode == 0, (
        f"Required real-stack coexistence needs {daemon}"
    )
    return api


@pytest.fixture
def addresses():
    ipv4 = os.environ.get("MDNS_TEST_INTERFACE", "127.0.0.1")
    ipv6 = os.environ.get("MDNS_TEST_THREAD_ADDRESS", "fd00:3:1::1")
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as probe:
        try:
            probe.bind((ipv6, 0))
        except OSError as error:
            pytest.fail(f"Required integration needs configured ULA {ipv6}: {error}")
    return ipv4, ipv6


def txt_properties(data):
    properties = {}
    while data:
        length = data[0]
        key, value = data[1 : length + 1].split(b"=", 1)
        properties[key] = value
        data = data[length + 1 :]
    return properties


async def records_for(query_id, interface, name="_lifx._udp.local.", qtype=12):
    replies = await raw_query(query_id, name, qtype, duration=0.8, interface=interface)
    records = []
    for packet, peer in replies:
        header, parsed = parse_records(packet)
        assert header[0] == query_id
        assert peer[1] == 5353
        owned = [
            r
            for r in parsed
            if r[0].startswith(PREFIX) or (r[1] == 12 and r[4].startswith(PREFIX))
        ]
        assert all(not (r[2] & 0x8000) and 0 < r[3] <= 10 for r in owned)
        records.extend(owned)
    return records


@pytest.mark.parametrize("size", [0, 1, 10, 100])
async def test_production_complete_fleet_raw_and_pristine_client(
    size, oracle, addresses
):
    ipv4, ipv6 = addresses
    devices = [
        create_color_light(
            serial=f"{PREFIX}{i:06x}",
            connectivity="thread" if i % 2 else "wifi",
            firmware_version=(4, 200),
        )
        for i in range(size)
    ]
    hidden = create_color_light(serial=f"{PREFIX}ffffff", mdns_enabled=False)
    server = EmulatedLifxServer(
        [*devices, hidden],
        DeviceManager(DeviceRepository()),
        bind_address=ipv4,
        ipv6_bind_address=ipv6,
        port=0,
        mdns_enabled=True,
    )
    found = {}
    try:
        await server.start()
        expected = {device.state.serial for device in devices}
        records = await records_for(410 + size, ipv4)
        instances = {
            r[4].split(".")[0]
            for r in records
            if r[0] == "_lifx._udp.local." and r[1] == 12 and r[4].startswith(PREFIX)
        }
        assert instances == expected
        for i, device in enumerate(devices):
            serial = device.state.serial
            instance = f"{serial}._lifx._udp.local."
            host = f"{serial}.local."
            kind, address = (28, ipv6) if i % 2 else (1, ipv4)
            assert any(
                r[0] == instance
                and r[1] == 33
                and r[4] == (0, 0, server.ipv4_endpoint[1], host)
                for r in records
            )
            assert any(
                r[0] == host
                and r[1] == kind
                and r[4] == ipaddress.ip_address(address).packed
                for r in records
            )
            assert not any(
                r[0] == host and r[1] == (1 if kind == 28 else 28) for r in records
            )
            txt = next(r[4] for r in records if r[0] == instance and r[1] == 16)
            assert txt_properties(txt) == {
                b"id": serial.encode(),
                b"p": b"91",
                b"fw": b"4.200",
                b"tm": b"2" if i % 2 else b"1",
            }
        started = time.monotonic()
        async for client in oracle.discover_mdns(
            timeout=4, max_response_time=0.2, device_timeout=1, max_retries=1
        ):
            serial = str(client.serial)
            if serial.startswith(PREFIX):
                found[serial] = client
            else:
                await client.close()
        assert set(found) == expected
        print(
            f"production oracle fleet={size} "
            f"discovery_seconds={time.monotonic() - started:.6f}"
        )
        for device in devices[:2]:
            client = found[device.state.serial]
            await client.connection.open()
            assert await client.get_power() == 65535
            await client.connection.close()
        if devices:
            device = devices[-1]
            await server.remove_device(device.state.serial)
            absent = await records_for(810 + size, ipv4)
            assert not any(device.state.serial in str(r) for r in absent)
            assert server.add_device(device)
            await server.wait_for_mdns_updates()
            restored = await records_for(910 + size, ipv4)
            assert any(device.state.serial in str(r) for r in restored)
            kind = 28 if device.state.connectivity == "thread" else 1
            direct = await records_for(
                1010 + size, ipv4, f"{device.state.serial}.local.", kind
            )
            assert any(
                r[0] == f"{device.state.serial}.local." and r[1] == kind for r in direct
            )
    finally:
        for client in found.values():
            await client.close()
        await server.stop()
