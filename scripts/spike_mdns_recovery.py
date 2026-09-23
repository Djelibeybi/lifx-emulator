#!/usr/bin/env python3
"""Bounded local recovery probe using pinned external dependencies via uv --with."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import socket
import threading
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from pathlib import Path

from lifx.api import discover_mdns
from lifx.devices import Light
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.factories import create_color_light
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer
from mdns_spike_inputs.zeroconf_recovery import RecoveryPrototype
from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

SERVICE = "_lifx._udp.local."


class RegistrationBoundary:
    """Inject one failure after a real registration; own a real responder."""

    def __init__(self, interface, fail_at=None):
        self.responder = AsyncZeroconf(
            interfaces=[interface], ip_version=IPVersion.V4Only
        )
        self.fail_at = fail_at
        self.count = 0
        self.closed = False

    async def async_register_service(self, info, **kwargs):
        if self.count == self.fail_at:
            raise OSError("injected second-registration failure")
        self.count += 1
        return await self.responder.async_register_service(info, **kwargs)

    async def async_close(self):
        await self.responder.async_close()
        self.closed = True


def make_info(serial, interface, port):
    return ServiceInfo(
        SERVICE,
        f"{serial}.{SERVICE}",
        addresses=[socket.inet_aton(interface)],
        port=port,
        properties={"id": serial, "p": "27", "fw": "4.200", "tm": "1"},
        server=f"{serial}.local.",
    )


async def discover_expected(serials):
    found = []
    async for device in discover_mdns(timeout=3, max_response_time=0.2):
        try:
            if str(device.serial) in serials:
                found.append(str(device.serial))
        finally:
            await device.close()
    return sorted(found)


async def exercise_wifi(interface):
    serials = ["d073d503f001", "d073d503f002"]
    devices = [create_color_light(serial) for serial in serials]
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), bind_address=interface, port=0
    )
    owners = []
    attempts = 0

    def factory():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("injected listener-construction failure")
        owner = RegistrationBoundary(interface, fail_at=1 if attempts == 2 else None)
        owners.append(owner)
        return owner

    adapter = RecoveryPrototype(factory)
    client = None
    control_task = None
    powers = []
    control_errors = []
    finish = asyncio.Event()
    try:
        await server.start()
        endpoint = server.ipv4_endpoint
        client = Light(
            serials[0], interface, port=endpoint[1], timeout=1, max_retries=0
        )
        infos = [make_info(serial, interface, endpoint[1]) for serial in serials]

        async def control():
            while not finish.is_set():
                try:
                    powers.append(await client.get_power())
                except Exception as error:
                    control_errors.append(f"{type(error).__name__}: {error}")
                await asyncio.sleep(0.05)

        control_task = asyncio.create_task(control())
        startup_failed = not await adapter.retry_mdns(infos)
        before_partial = len(powers)
        partial_failed = not await adapter.retry_mdns(infos)
        absent = await discover_expected(serials)
        after_partial = len(powers)
        restored = await adapter.retry_mdns(infos)
        discovered = await discover_expected(serials)
        await adapter.runtime_failure(OSError("injected listener loss"), server)
        power_after_failure = await client.get_power()
        failure_state = adapter.mdns_status
        recovered = await adapter.retry_mdns(infos)
        power_after_retry = await client.get_power()
        return {
            "startup_failed": startup_failed,
            "partial_failed": partial_failed,
            "partial_owner_closed": owners[0].closed,
            "after_partial_discovered": absent,
            "restored": restored,
            "expected": serials,
            "discovered": discovered,
            "runtime_failure_status": failure_state,
            "explicit_retry": recovered,
            "same_lifx_endpoint": endpoint == server.ipv4_endpoint,
            "control_during_partial_failure": after_partial - before_partial,
            "power_after_failure": power_after_failure,
            "power_after_retry": power_after_retry,
            "control_replies": len(powers),
            "control_errors": control_errors,
            "all_control_values_match": bool(powers)
            and all(p == 65535 for p in powers),
        }
    finally:
        finish.set()
        async with AsyncExitStack() as cleanup:
            cleanup.push_async_callback(server.stop)
            cleanup.push_async_callback(adapter.stop)
            if client is not None:
                cleanup.push_async_callback(client.close)
            if control_task is not None:
                await control_task


async def exercise_thread_policy(interface, mixed):
    devices = [create_color_light("d073d503f003", connectivity="thread")]
    if mixed:
        devices.append(create_color_light("d073d503f004"))
    server = EmulatedLifxServer(
        devices, DeviceManager(DeviceRepository()), bind_address=interface, port=0
    )
    adapter = RecoveryPrototype(lambda: RegistrationBoundary(interface))
    try:
        await server.start()
        await adapter.retry_mdns([])
        await adapter.runtime_failure(OSError("injected listener loss"), server)
        await adapter.stop()
        return {
            "ipv4_closed": server.ipv4_endpoint is None,
            "ipv6_closed": server.ipv6_endpoint is None,
            "status": adapter.mdns_status,
            "error_retained": "listener loss" in (adapter.mdns_error or ""),
        }
    finally:
        async with AsyncExitStack() as cleanup:
            cleanup.push_async_callback(server.stop)
            cleanup.push_async_callback(adapter.stop)


async def run():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("224.0.0.251", 5353))
        interface = probe.getsockname()[0]
    result = {
        "wifi": await exercise_wifi(interface),
        "thread": await exercise_thread_policy(interface, False),
        "mixed": await exercise_thread_policy(interface, True),
    }
    await asyncio.sleep(0.1)
    current = asyncio.current_task()
    result["pending_tasks"] = sorted(
        task.get_name()
        for task in asyncio.all_tasks()
        if task is not current and not task.done()
    )
    result["threads"] = sorted(thread.name for thread in threading.enumerate())
    wifi = result["wifi"]
    result["passed"] = all(
        (
            wifi["startup_failed"],
            wifi["partial_failed"],
            wifi["partial_owner_closed"],
            not wifi["after_partial_discovered"],
            wifi["restored"],
            wifi["expected"] == wifi["discovered"],
            wifi["runtime_failure_status"] == "failed",
            wifi["explicit_retry"],
            wifi["same_lifx_endpoint"],
            wifi["control_during_partial_failure"] > 0,
            wifi["power_after_failure"] == wifi["power_after_retry"] == 65535,
            not wifi["control_errors"],
            wifi["all_control_values_match"],
            not result["pending_tasks"],
            result["threads"] == ["MainThread"],
            all(
                policy["ipv4_closed"]
                and policy["ipv6_closed"]
                and policy["status"] == "failed"
                and policy["error_retained"]
                for policy in (result["thread"], result["mixed"])
            ),
        )
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = [
        Path(__file__),
        Path(__file__).parent / "mdns_spike_inputs/zeroconf_recovery.py",
    ]
    result = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "zeroconf": importlib.metadata.version("zeroconf"),
        "lifx_async": importlib.metadata.version("lifx-async"),
        "fault_scope": (
            "Injected adapter-boundary failures; "
            "no actual listener-loss detection proof"
        ),
        "sha256": {
            str(p.relative_to(Path(__file__).parents[1])): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sources
        },
    }
    try:
        result["results"] = asyncio.run(run())
    except Exception as error:
        result["results"] = {
            "passed": False,
            "error": f"{type(error).__name__}: {error}",
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["results"], indent=2))
    return 0 if result["results"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
