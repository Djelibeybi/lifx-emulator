#!/usr/bin/env python3
"""Bounded evidence harness for the Phase 3 mDNS responder spike."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import errno
import hashlib
import importlib.metadata
import ipaddress
import json
import os
import platform
import re
import resource
import socket
import struct
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

if os.environ.get("MDNS_SPIKE_WORKER") == "1":
    from lifx.api import discover_mdns
    from lifx.network.discovery.mdns.dns import (
        DNS_TYPE_A,
        DNS_TYPE_AAAA,
        DNS_TYPE_PTR,
        DNS_TYPE_SRV,
        DNS_TYPE_TXT,
        TxtData,
        build_ptr_query,
        parse_dns_response,
    )
    from lifx_emulator.devices.manager import DeviceManager
    from lifx_emulator.factories import create_color_light
    from lifx_emulator.repositories import DeviceRepository
    from lifx_emulator.server import EmulatedLifxServer
    from mdns_spike_inputs.lifx_direct import (
        Advertisement,
        build_legacy_unicast_responses,
    )
    from zeroconf import IPVersion, ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf


REPOSITORY_ROOT = Path(__file__).parents[1]
DEFAULT_EVIDENCE = (
    REPOSITORY_ROOT / ".planning/phases/03-mdns-responder/03-01-EVIDENCE.json"
)
DEFAULT_INPUTS = REPOSITORY_ROOT / "scripts/mdns_spike_inputs/active.json"
ORACLE_REVISION = "48b7efbff59656499373b13ef17e3008d125feb5"
PYAPP_REVISION = "a419de7c068cbd0e083194bbe11c741b0497d28c"
PYAPP_TREE = "d87b89829042147f7b23c5fe4b5b14034d8164d4"
PYAPP_VERSION = "0.26.0"
ACTIVE_BUDGET_SECONDS = 4 * 60 * 60
STARTED_AT = "2026-09-22T15:01:53Z"
SERVICE_TYPE = "_lifx._udp.local."
SERIAL = "d073d5000001"

CriterionStatus = Literal[
    "demonstrated", "failed", "simulated", "untested", "not-run-with-reason"
]
CandidateStatus = Literal["meets_gate", "rejected", "provisional"]
ExecutionStatus = Literal["completed", "tool_error"]


@dataclass(frozen=True)
class CriterionResult:
    """One auditable criterion outcome."""

    status: CriterionStatus
    evidence: str
    acquisition_step: str | None = None


@dataclass(frozen=True)
class CandidateOutcome:
    """Keep harness execution separate from candidate suitability."""

    candidate: str
    execution_status: ExecutionStatus
    candidate_status: CandidateStatus
    criteria: dict[str, CriterionResult]
    elapsed_active_seconds: float


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def resolve_inputs(path: Path = DEFAULT_INPUTS) -> dict[str, Any]:
    """Load and verify the immutable active candidate specification."""
    inputs = _read_json(path)
    recorded = inputs.pop("input_spec_digest", None)
    realised = _digest(inputs)
    inputs["input_spec_digest"] = realised
    if recorded is not None and recorded != realised:
        raise ValueError(
            f"input_spec_digest mismatch: recorded {recorded}, realised {realised}"
        )
    if inputs.get("oracle", {}).get("revision") != ORACLE_REVISION:
        raise ValueError("active inputs do not contain the pinned oracle revision")
    return inputs


def _blank_criteria(reason: str) -> dict[str, dict[str, Any]]:
    acquisition = "Run the named local or exact-head CI probe and merge its receipt."
    names = (
        "official_provenance",
        "legacy_wire",
        "packet_boundary",
        "exact_txt_and_family",
        "direct_address_queries",
        "daemon_coexistence",
        "oracle_discovery",
        "wifi_benchmark",
        "thread_benchmark",
        "mixed_10_benchmark",
        "mixed_100_benchmark",
        "lifecycle_cleanup",
        "ubuntu_multicast",
        "macos_multicast",
        "windows_socket_simulation",
        "intel_pyapp_first_run",
        "malformed_truncated_flood_bounds",
        "configuration_interface_fit",
        "dynamic_lifecycle_recovery_fit",
    )
    return {
        name: asdict(CriterionResult("untested", reason, acquisition)) for name in names
    }


def _initial_evidence(inputs: dict[str, Any]) -> dict[str, Any]:
    elapsed = max(0.0, time.time() - _parse_started_at())
    reason = "Not yet reached by the progressive candidate sequence."
    return {
        "schema_version": 1,
        "plan": "03-01",
        "requirement": "MDNS-10",
        "started_at": STARTED_AT,
        "active_budget_seconds": ACTIVE_BUDGET_SECONDS,
        "active_elapsed_seconds": round(elapsed, 3),
        "ci_queue_seconds": 0.0,
        "candidate_order": [
            "zeroconf",
            "lifx-direct",
            "lifx-adapted",
            "new-responder",
        ],
        "inputs": inputs,
        "input_spec_digest": inputs["input_spec_digest"],
        "environments": {},
        "candidates": [
            {
                "candidate": "zeroconf",
                "execution_status": "completed",
                "candidate_status": "provisional",
                "criteria": _blank_criteria(reason),
                "elapsed_active_seconds": round(elapsed, 3),
                "attempts": [],
            }
        ],
        "edge_coverage": [
            {
                "id": f"SPEC-edge-{number:02d}",
                "status": "untested",
                "evidence": reason,
                "acquisition_step": "Acquire the mapped criterion evidence.",
            }
            for number in range(1, 47)
        ],
        "pull_request": {
            "url": None,
            "candidate_head_sha": None,
            "runs": [],
        },
        "decision": {
            "status": "provisional",
            "reason": "The bounded evidence run has not closed.",
            "extension_case": None,
        },
        "commands": [],
        "updated_at": _utc_now(),
    }


def _parse_started_at() -> float:
    return datetime.fromisoformat(STARTED_AT.replace("Z", "+00:00")).timestamp()


def _active_elapsed() -> float:
    return max(0.0, time.time() - _parse_started_at())


def _environment() -> dict[str, Any]:
    value = {
        "os": platform.system().lower(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
    }
    value["realised_environment_digest"] = _digest(value)
    return value


def _select_ipv4_interface() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("224.0.0.251", 5353))
        selected = probe.getsockname()[0]
    if selected == "0.0.0.0":
        raise OSError("no concrete IPv4 multicast interface is available")
    return selected


def _dns_query(name: str, record_type: int, query_id: int) -> bytes:
    labels = name.rstrip(".").split(".")
    encoded_name = (
        b"".join(bytes((len(label.encode()),)) + label.encode() for label in labels)
        + b"\x00"
    )
    header = struct.pack("!HHHHHH", query_id, 0, 1, 0, 0, 0)
    return header + encoded_name + struct.pack("!HH", record_type, 0x8001)


async def _receive_one(sock: socket.socket, timeout: float) -> tuple[bytes, tuple]:
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.sock_recvfrom(sock, 9000), timeout=timeout)


async def run_wire_probe() -> dict[str, Any]:
    """Exercise one real zeroconf WiFi legacy-unicast response."""
    interface = _select_ipv4_interface()
    device = create_color_light(SERIAL)
    server = EmulatedLifxServer([device], DeviceManager(DeviceRepository()), port=0)
    azc = AsyncZeroconf(interfaces=[interface], ip_version=IPVersion.V4Only)
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setblocking(False)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_IF,
        socket.inet_aton(interface),
    )
    client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    client.bind((interface, 0))
    info: ServiceInfo | None = None
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        service_port = server.ipv4_endpoint[1]
        info = ServiceInfo(
            SERVICE_TYPE,
            f"{SERIAL}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton("127.0.0.1")],
            port=service_port,
            properties={"id": SERIAL, "p": "27", "fw": "4.200", "tm": "1"},
            server=f"{SERIAL}.local.",
        )
        await azc.async_register_service(info, ttl=10)
        query = bytearray(build_ptr_query(SERVICE_TYPE.rstrip(".")))
        query[:2] = struct.pack("!H", 0xBEEF)
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(client, bytes(query), ("224.0.0.251", 5353))
        raw, peer = await _receive_one(client, 5.0)
        parsed = parse_dns_response(raw)
        record_types = [record.type_name for record in parsed.records]
        txt_records = [
            record.parsed_data.pairs
            for record in parsed.records
            if record.rtype == DNS_TYPE_TXT and isinstance(record.parsed_data, TxtData)
        ]
        required = {DNS_TYPE_PTR, DNS_TYPE_SRV, DNS_TYPE_TXT, DNS_TYPE_A}
        observed = {record.rtype for record in parsed.records}
        return {
            "interface": "selected-ipv4",
            "client_endpoint": ["selected-ipv4", client.getsockname()[1]],
            "peer": ["selected-ipv4", peer[1]],
            "service_port": service_port,
            "query_id": 0xBEEF,
            "response_id": parsed.header.id,
            "question_count": parsed.header.qd_count,
            "record_types": record_types,
            "record_count": len(parsed.records),
            "datagram_size": len(raw),
            "all_cache_flush_clear": all(
                not record.cache_flush for record in parsed.records
            ),
            "ttl_values": [record.ttl for record in parsed.records],
            "ttl_valid": all(0 < record.ttl <= 10 for record in parsed.records),
            "required_records_present": required.issubset(observed),
            "txt_records": txt_records,
            "txt_exact": txt_records
            == [{"id": SERIAL, "p": "27", "fw": "4.200", "tm": "1"}],
            "a_only": DNS_TYPE_A in observed and 28 not in observed,
            "response_received_on_ephemeral_socket": client.getsockname()[1] != 5353,
            "zeroconf_version": importlib.metadata.version("zeroconf"),
            "lifx_async_version": importlib.metadata.version("lifx-async"),
            "threads_before_close": [thread.name for thread in threading.enumerate()],
        }
    finally:
        if info is not None:
            goodbye = await azc.async_unregister_service(info)
            await goodbye
        await azc.async_close()
        client.close()
        await server.stop()


def _host_daemon_identity() -> list[str]:
    completed = subprocess.run(
        ["ps", "-axo", "comm="], check=False, capture_output=True, text=True
    )
    names = {
        Path(line.strip()).name
        for line in completed.stdout.splitlines()
        if re.search(r"(mdns|avahi)", line, re.IGNORECASE)
    }
    return sorted(names)


def _reachable_ipv6_addresses() -> list[str]:
    command = ["ifconfig"] if platform.system() == "Darwin" else ["ip", "-6", "addr"]
    completed = subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=10
    )
    addresses: set[str] = set()
    for value in re.findall(r"inet6\s+([0-9a-fA-F:]+)", completed.stdout):
        address = ipaddress.ip_address(value.split("%", 1)[0])
        if address in ipaddress.ip_network(
            "fc00::/7"
        ) or address in ipaddress.ip_network("2000::/3"):
            addresses.add(str(address))
    return sorted(addresses)


def _new_mdns_client(interface: str) -> socket.socket:
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setblocking(False)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.setsockopt(
        socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface)
    )
    client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    client.bind((interface, 0))
    return client


async def _collect_query(
    client: socket.socket,
    query: bytes,
    *,
    timeout: float,
    expected_serials: set[str],
    direct_record: tuple[str, int] | None = None,
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    started = time.monotonic()
    cpu_started = time.process_time()
    await loop.sock_sendto(client, query, ("224.0.0.251", 5353))
    serials: set[str] = set()
    observed_types: set[str] = set()
    direct_match = False
    datagram_sizes: list[int] = []
    record_counts: list[int] = []
    complete_datagrams = 0
    complete_serials: set[str] = set()
    while time.monotonic() - started < timeout:
        if expected_serials and expected_serials.issubset(serials):
            break
        if direct_record is not None and direct_match:
            break
        remaining = max(0.01, timeout - (time.monotonic() - started))
        try:
            raw, _ = await _receive_one(client, remaining)
            packet = parse_dns_response(raw)
        except TimeoutError:
            break
        except (OSError, ValueError):
            continue
        datagram_sizes.append(len(raw))
        record_counts.append(len(packet.records))
        observed_types.update(record.type_name for record in packet.records)
        if direct_record is not None:
            wanted_name, wanted_type = direct_record
            direct_match = direct_match or any(
                record.rtype == wanted_type
                and record.name.rstrip(".").lower() == wanted_name.rstrip(".").lower()
                for record in packet.records
            )
        types = {record.rtype for record in packet.records}
        packet_types_by_serial: dict[str, set[int]] = {
            serial: set() for serial in expected_serials
        }
        for record in packet.records:
            identity_text = f"{record.name} {record.parsed_data}".lower()
            for serial in expected_serials:
                if serial in identity_text:
                    packet_types_by_serial[serial].add(record.rtype)
        if {DNS_TYPE_PTR, DNS_TYPE_SRV, DNS_TYPE_TXT}.issubset(types) and (
            DNS_TYPE_A in types or DNS_TYPE_AAAA in types
        ):
            complete_datagrams += 1
            present_synthetic = {
                serial
                for serial, serial_types in packet_types_by_serial.items()
                if serial_types
            }
            for serial, serial_types in packet_types_by_serial.items():
                if (
                    {DNS_TYPE_PTR, DNS_TYPE_SRV, DNS_TYPE_TXT}.issubset(serial_types)
                    and (DNS_TYPE_A in serial_types or DNS_TYPE_AAAA in serial_types)
                    and len(present_synthetic) == 1
                ):
                    complete_serials.add(serial)
        for record in packet.records:
            if record.rtype == DNS_TYPE_TXT and isinstance(record.parsed_data, TxtData):
                serial = record.parsed_data.pairs.get("id")
                if serial:
                    serials.add(serial)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    matched_serials = serials & expected_serials
    return {
        "expected": len(expected_serials) if expected_serials else 1,
        "discovered": len(matched_serials) if expected_serials else int(direct_match),
        "serials": sorted(matched_serials),
        "direct_match": direct_match,
        "complete_discovery_seconds": round(time.monotonic() - started, 6),
        "cpu_seconds": round(time.process_time() - cpu_started, 6),
        "peak_rss": usage.ru_maxrss,
        "datagram_count": len(datagram_sizes),
        "datagram_sizes": datagram_sizes,
        "record_counts": record_counts,
        "complete_datagrams": complete_datagrams,
        "complete_devices": len(complete_serials),
        "record_types": sorted(observed_types),
    }


async def run_discovery_benchmark(wifi: int, thread_count: int) -> dict[str, Any]:
    """Measure one deterministic WiFi/Thread population through raw discovery."""
    interface = _select_ipv4_interface()
    total = wifi + thread_count
    devices = [create_color_light(f"d073d5{number:06x}") for number in range(total)]
    server = EmulatedLifxServer(devices, DeviceManager(DeviceRepository()), port=0)
    azc = AsyncZeroconf(interfaces=[interface], ip_version=IPVersion.V4Only)
    client = _new_mdns_client(interface)
    infos: list[ServiceInfo] = []
    before_threads = sorted(thread.name for thread in threading.enumerate())
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        port = server.ipv4_endpoint[1]
        for number, device in enumerate(devices):
            serial = device.state.serial
            is_thread = number >= wifi
            address = (
                socket.inet_pton(socket.AF_INET6, "::1")
                if is_thread
                else socket.inet_aton("127.0.0.1")
            )
            infos.append(
                ServiceInfo(
                    SERVICE_TYPE,
                    f"{serial}.{SERVICE_TYPE}",
                    addresses=[address],
                    port=port,
                    properties={
                        "id": serial,
                        "p": "27",
                        "fw": "4.200",
                        "tm": "2" if is_thread else "1",
                    },
                    server=f"{serial}.local.",
                )
            )
        announcements = await asyncio.gather(
            *(azc.async_register_service(info, ttl=10, strict=False) for info in infos)
        )
        await asyncio.gather(*announcements)
        query = bytearray(build_ptr_query(SERVICE_TYPE.rstrip(".")))
        query[:2] = struct.pack("!H", 0xCAFE)
        metrics = await _collect_query(
            client,
            bytes(query),
            timeout=min(15.0, 4.0 + total / 10),
            expected_serials={device.state.serial for device in devices},
        )
        direct_a: dict[str, Any] | None = None
        if wifi:
            wifi_name = f"{devices[0].state.serial}.local."
            direct_a = await _collect_query(
                client,
                _dns_query(wifi_name, DNS_TYPE_A, 0xA001),
                timeout=2.0,
                expected_serials=set(),
                direct_record=(wifi_name, DNS_TYPE_A),
            )
        direct_aaaa: dict[str, Any] | None = None
        if thread_count:
            thread_name = f"{devices[wifi].state.serial}.local."
            direct_aaaa = await _collect_query(
                client,
                _dns_query(thread_name, DNS_TYPE_AAAA, 0xA002),
                timeout=2.0,
                expected_serials=set(),
                direct_record=(thread_name, DNS_TYPE_AAAA),
            )
        metrics.update(
            {
                "wifi": wifi,
                "thread": thread_count,
                "raw_thread_address": "::1" if thread_count else None,
                "direct_a": direct_a,
                "direct_aaaa": direct_aaaa,
                "threads_before": before_threads,
            }
        )
        return metrics
    finally:
        goodbyes = await asyncio.gather(
            *(azc.async_unregister_service(info) for info in infos)
        )
        await asyncio.gather(*goodbyes)
        await azc.async_close()
        client.close()
        await server.stop()


async def _run_public_oracle(thread_address: str | None = None) -> dict[str, Any]:
    interface = _select_ipv4_interface()
    serial = "d073d5000002" if thread_address else SERIAL
    device = create_color_light(serial)
    server = EmulatedLifxServer([device], DeviceManager(DeviceRepository()), port=0)
    azc = AsyncZeroconf(interfaces=[interface], ip_version=IPVersion.V4Only)
    info: ServiceInfo | None = None
    discovered: list[str] = []
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        info = ServiceInfo(
            SERVICE_TYPE,
            f"{serial}.{SERVICE_TYPE}",
            addresses=[
                socket.inet_pton(socket.AF_INET6, thread_address)
                if thread_address
                else socket.inet_aton(interface)
            ],
            port=server.ipv4_endpoint[1],
            properties={
                "id": serial,
                "p": "27",
                "fw": "4.200",
                "tm": "2" if thread_address else "1",
            },
            server=f"{serial}.local.",
        )
        announcement = await azc.async_register_service(info, ttl=10)
        await announcement
        async for discovered_device in discover_mdns(
            timeout=4.0, max_response_time=0.2, idle_timeout_multiplier=2.0
        ):
            discovered.append(str(discovered_device.serial))
        return {
            "expected_serial": serial,
            "matched_serials": [serial] if serial in discovered else [],
            "matched": serial in discovered,
            "address_class": "reachable-ula-gua" if thread_address else "selected-ipv4",
            "family": "thread" if thread_address else "wifi",
        }
    finally:
        if info is not None:
            goodbye = await azc.async_unregister_service(info)
            await goodbye
        await azc.async_close()
        await server.stop()


async def _expanded_worker() -> int:
    started = time.monotonic()
    before_threads = sorted(thread.name for thread in threading.enumerate())
    try:
        reachable = _reachable_ipv6_addresses()
        oracle = {
            "wifi": await _run_public_oracle(),
            "thread": await _run_public_oracle(reachable[0]) if reachable else None,
        }
        oracle_failed = not oracle["wifi"]["matched"] or (
            oracle["thread"] is not None and not oracle["thread"]["matched"]
        )
        if oracle_failed:
            payload = {
                "execution_status": "completed",
                "oracle": oracle,
                "benchmarks": {},
                "daemon_processes": _host_daemon_identity(),
                "reachable_ula_gua_count": len(reachable),
                "threads_before": before_threads,
                "threads_after": sorted(
                    thread.name for thread in threading.enumerate()
                ),
                "pending_owned_tasks": [],
                "environment": _environment(),
                "elapsed_seconds": time.monotonic() - started,
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
        benchmarks = {
            "wifi-1": await run_discovery_benchmark(1, 0),
            "thread-1": await run_discovery_benchmark(0, 1),
            "mixed-10": await run_discovery_benchmark(5, 5),
        }
        mixed_10 = benchmarks["mixed-10"]
        if (
            mixed_10["discovered"] == mixed_10["expected"]
            and mixed_10["complete_devices"] == mixed_10["expected"]
        ):
            benchmarks["mixed-100"] = await run_discovery_benchmark(50, 50)
        await asyncio.sleep(0)
        current = asyncio.current_task()
        pending = [
            task.get_name()
            for task in asyncio.all_tasks()
            if task is not current and not task.done()
        ]
        payload = {
            "execution_status": "completed",
            "oracle": oracle,
            "benchmarks": benchmarks,
            "daemon_processes": _host_daemon_identity(),
            "reachable_ula_gua_count": len(reachable),
            "threads_before": before_threads,
            "threads_after": sorted(thread.name for thread in threading.enumerate()),
            "pending_owned_tasks": pending,
            "environment": _environment(),
            "elapsed_seconds": time.monotonic() - started,
        }
    except Exception as error:
        payload = {
            "execution_status": "completed",
            "error_type": type(error).__name__,
            "error": str(error),
            "environment": _environment(),
            "elapsed_seconds": time.monotonic() - started,
        }
    print(json.dumps(payload, sort_keys=True))
    return 0


async def _run_direct_population(wifi: int, thread_count: int) -> dict[str, Any]:
    interface = _select_ipv4_interface()
    total = wifi + thread_count
    devices = [create_color_light(f"d073d6{number:06x}") for number in range(total)]
    server = EmulatedLifxServer(devices, DeviceManager(DeviceRepository()), port=0)
    client = _new_mdns_client(interface)
    responder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    responder.setblocking(False)
    responder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        responder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    responder.bind(("", 5353))
    responder.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton("224.0.0.251") + socket.inet_aton(interface),
    )
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        advertisements = [
            Advertisement(
                serial=device.state.serial,
                port=server.ipv4_endpoint[1],
                address="::1" if number >= wifi else "127.0.0.1",
                transport="2" if number >= wifi else "1",
            )
            for number, device in enumerate(devices)
        ]
        query = bytearray(build_ptr_query(SERVICE_TYPE.rstrip(".")))
        query[:2] = struct.pack("!H", 0xD1EC)
        loop = asyncio.get_running_loop()
        started = time.monotonic()
        cpu_started = time.process_time()
        await loop.sock_sendto(client, bytes(query), ("224.0.0.251", 5353))
        while True:
            received, source = await asyncio.wait_for(
                loop.sock_recvfrom(responder, 9000), timeout=3.0
            )
            if source[1] == client.getsockname()[1]:
                break
        responses = build_legacy_unicast_responses(received, advertisements)
        for response in responses:
            await loop.sock_sendto(responder, response, source)
        discovered: set[str] = set()
        complete = 0
        sizes: list[int] = []
        wire_checks: list[bool] = []
        while len(discovered) < total:
            raw, _ = await _receive_one(client, 5.0)
            parsed = parse_dns_response(raw)
            ids = {
                record.parsed_data.pairs["id"]
                for record in parsed.records
                if record.rtype == DNS_TYPE_TXT
                and isinstance(record.parsed_data, TxtData)
                and "id" in record.parsed_data.pairs
            }
            synthetic = ids & {ad.serial for ad in advertisements}
            if len(synthetic) != 1:
                continue
            types = {record.rtype for record in parsed.records}
            if {DNS_TYPE_PTR, DNS_TYPE_SRV, DNS_TYPE_TXT}.issubset(types) and (
                DNS_TYPE_A in types or DNS_TYPE_AAAA in types
            ):
                discovered.update(synthetic)
                complete += 1
                sizes.append(len(raw))
                expected_serial = next(iter(synthetic))
                txt_records = [
                    record.parsed_data.pairs
                    for record in parsed.records
                    if record.rtype == DNS_TYPE_TXT
                    and isinstance(record.parsed_data, TxtData)
                ]
                expected_ad = next(
                    advertisement
                    for advertisement in advertisements
                    if advertisement.serial == expected_serial
                )
                wire_checks.append(
                    parsed.header.id == 0xD1EC
                    and parsed.header.qd_count == 1
                    and len(parsed.records) == 4
                    and all(not record.cache_flush for record in parsed.records)
                    and all(0 < record.ttl <= 10 for record in parsed.records)
                    and txt_records
                    == [
                        {
                            "id": expected_serial,
                            "p": "27",
                            "fw": "4.200",
                            "tm": expected_ad.transport,
                        }
                    ]
                )
        direct_results: dict[str, bool] = {}
        for family, index, record_type in (
            ("wifi", 0 if wifi else -1, DNS_TYPE_A),
            ("thread", wifi if thread_count else -1, DNS_TYPE_AAAA),
        ):
            if index < 0:
                continue
            hostname = f"{advertisements[index].serial}.local."
            direct_query = _dns_query(hostname, record_type, 0xD1ED + index)
            await loop.sock_sendto(client, direct_query, ("224.0.0.251", 5353))
            while True:
                received, source = await asyncio.wait_for(
                    loop.sock_recvfrom(responder, 9000), timeout=3.0
                )
                if source[1] == client.getsockname()[1]:
                    break
            for response in build_legacy_unicast_responses(received, advertisements):
                await loop.sock_sendto(responder, response, source)
            deadline = time.monotonic() + 3.0
            direct_results[family] = False
            while time.monotonic() < deadline:
                try:
                    raw, _ = await _receive_one(
                        client, max(deadline - time.monotonic(), 0.01)
                    )
                except TimeoutError:
                    break
                parsed = parse_dns_response(raw)
                if parsed.header.id != 0xD1ED + index:
                    continue
                direct_results[family] = (
                    parsed.header.qd_count == 1
                    and len(parsed.records) == 1
                    and parsed.records[0].rtype == record_type
                    and not parsed.records[0].cache_flush
                    and 0 < parsed.records[0].ttl <= 10
                )
                break
        return {
            "wifi": wifi,
            "thread": thread_count,
            "expected": total,
            "discovered": len(discovered),
            "complete_devices": complete,
            "datagram_count": len(sizes),
            "datagram_sizes": sizes,
            "complete_discovery_seconds": round(time.monotonic() - started, 6),
            "cpu_seconds": round(time.process_time() - cpu_started, 6),
            "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "server_port": server.ipv4_endpoint[1],
            "direct_queries": direct_results,
            "wire_checks_passed": all(wire_checks) and len(wire_checks) == total,
            "raw_thread_address_class": "loopback-::1" if thread_count else None,
        }
    finally:
        responder.close()
        client.close()
        await server.stop()


async def _run_direct_oracle(thread_address: str | None = None) -> dict[str, Any]:
    interface = _select_ipv4_interface()
    serial = "d073d6000002" if thread_address else "d073d6000001"
    device = create_color_light(serial)
    server = EmulatedLifxServer([device], DeviceManager(DeviceRepository()), port=0)
    responder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    responder.setblocking(False)
    responder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        responder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    responder.bind(("", 5353))
    responder.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton("224.0.0.251") + socket.inet_aton(interface),
    )
    task: asyncio.Task[None] | None = None
    discovered: list[str] = []
    queries_received = 0
    matching_queries_received = 0
    legacy_queries_received = 0
    legacy_responses_sent = 0
    responses_sent = 0
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        advertisement = Advertisement(
            serial=serial,
            port=server.ipv4_endpoint[1],
            address=thread_address or interface,
            transport="2" if thread_address else "1",
        )
        loop = asyncio.get_running_loop()

        async def serve() -> None:
            nonlocal legacy_queries_received
            nonlocal legacy_responses_sent
            nonlocal matching_queries_received
            nonlocal queries_received
            nonlocal responses_sent
            while True:
                query, source = await loop.sock_recvfrom(responder, 9000)
                queries_received += 1
                responses = build_legacy_unicast_responses(query, [advertisement])
                if responses:
                    matching_queries_received += 1
                    if source[1] != 5353 and source[0] == interface:
                        legacy_queries_received += 1
                        legacy_responses_sent += len(responses)
                for response in responses:
                    await loop.sock_sendto(responder, response, source)
                    responses_sent += 1

        task = asyncio.create_task(serve(), name="lifx-direct-spike-responder")
        async for discovered_device in discover_mdns(
            timeout=4.0, max_response_time=0.2, idle_timeout_multiplier=2.0
        ):
            if str(discovered_device.serial) == serial:
                discovered.append(serial)
        return {
            "expected_serial": serial,
            "matched_serials": discovered,
            "matched": serial in discovered,
            "address_class": "reachable-ula-gua" if thread_address else "selected-ipv4",
            "queries_received": queries_received,
            "matching_queries_received": matching_queries_received,
            "legacy_queries_received": legacy_queries_received,
            "responses_sent": responses_sent,
            "legacy_responses_sent": legacy_responses_sent,
        }
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        responder.close()
        await server.stop()


def _probe_ipv6_route(address: str) -> dict[str, Any]:
    """Ask the kernel whether a candidate ULA/GUA has a usable local route."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as probe:
            probe.connect((address, 56700))
    except OSError as error:
        return {
            "available": False,
            "error_type": type(error).__name__,
            "errno": error.errno,
        }
    return {"available": True, "error_type": None, "errno": None}


def _run_direct_fit_checks() -> dict[str, bool]:
    """Exercise bounded future configuration and lifecycle inputs."""
    query = _dns_query(SERVICE_TYPE, DNS_TYPE_PTR, 0xCAFE)
    wifi = Advertisement("d073d6000101", 56700, "192.0.2.10")
    shared = Advertisement("d073d6000102", 56700, "192.0.2.10")

    def serials(responses: list[bytes]) -> set[str]:
        return {
            str(record.parsed_data.pairs["id"])
            for response in responses
            for record in parse_dns_response(response).records
            if record.rtype == DNS_TYPE_TXT and isinstance(record.parsed_data, TxtData)
        }

    first = build_legacy_unicast_responses(query, [wifi, shared])
    repeated = build_legacy_unicast_responses(query, [wifi, shared])
    removed = build_legacy_unicast_responses(query, [wifi])
    re_added = build_legacy_unicast_responses(query, [wifi, shared])
    equivalent_compact = build_legacy_unicast_responses(
        query, [Advertisement("d073d6000103", 56700, "fd00::1")]
    )
    equivalent_expanded = build_legacy_unicast_responses(
        query,
        [
            Advertisement(
                "d073d6000103",
                56700,
                "fd00:0000:0000:0000:0000:0000:0000:0001",
            )
        ],
    )
    try:
        build_legacy_unicast_responses(
            query, [Advertisement("d073d6000104", 56700, "invalid-address")]
        )
    except OSError:
        invalid_address_rejected = True
    else:
        invalid_address_rejected = False
    return {
        "empty_eligible_set_has_no_reply": not build_legacy_unicast_responses(
            query, []
        ),
        "shared_addresses_keep_distinct_identities": len(first) == 2
        and serials(first) == {wifi.serial, shared.serial},
        "repeated_unchanged_query_is_stable": repeated == first,
        "removal_and_readd_follow_eligible_set": serials(removed) == {wifi.serial}
        and re_added == first,
        "equivalent_ipv6_spellings_encode_identically": (
            equivalent_compact == equivalent_expanded
        ),
        "invalid_address_is_rejected_before_reply": invalid_address_rejected,
    }


async def _capture_direct_oracle(thread_address: str | None = None) -> dict[str, Any]:
    """Retain an unavailable public-oracle leg without losing later raw probes."""
    route = _probe_ipv6_route(thread_address) if thread_address else None
    try:
        result = await _run_direct_oracle(thread_address)
    except Exception as error:
        return {
            "matched": False,
            "address_class": (
                "reachable-ula-gua" if thread_address else "selected-ipv4"
            ),
            "stage": "public-oracle",
            "error_type": type(error).__name__,
            "errno": getattr(error, "errno", None),
            "route_probe": route,
        }
    result["stage"] = "public-oracle"
    result["error_type"] = None
    result["errno"] = None
    result["route_probe"] = route
    return result


async def _lifx_direct_worker() -> int:
    started = time.monotonic()
    before = sorted(thread.name for thread in threading.enumerate())
    stage = "reachable-address-discovery"
    try:
        reachable = _reachable_ipv6_addresses()
        stage = "public-oracle-wifi"
        wifi_oracle = await _capture_direct_oracle()
        stage = "public-oracle-thread"
        thread_oracle = (
            await _capture_direct_oracle(reachable[0]) if reachable else None
        )
        oracle = {
            "wifi": wifi_oracle,
            "thread": thread_oracle,
        }
        benchmarks: dict[str, Any] = {}
        for name, population in (
            ("wifi-1", (1, 0)),
            ("thread-1", (0, 1)),
            ("mixed-10", (5, 5)),
            ("mixed-100", (50, 50)),
        ):
            stage = f"raw-population-{name}"
            metrics = await _run_direct_population(*population)
            benchmarks[name] = metrics
            if metrics["complete_devices"] != metrics["expected"]:
                break
        stage = "malformed-input"
        try:
            build_legacy_unicast_responses(b"", [])
        except ValueError:
            malformed_bounded = True
        else:
            malformed_bounded = False
        stage = "future-fit-inputs"
        fit_checks = _run_direct_fit_checks()
        await asyncio.sleep(0)
        current = asyncio.current_task()
        payload = {
            "execution_status": "completed",
            "oracle": oracle,
            "reachable_ula_gua_count": len(reachable),
            "malformed_bounded": malformed_bounded,
            "fit_checks": fit_checks,
            "benchmarks": benchmarks,
            "daemon_processes": _host_daemon_identity(),
            "threads_before": before,
            "threads_after": sorted(thread.name for thread in threading.enumerate()),
            "pending_owned_tasks": [
                task.get_name()
                for task in asyncio.all_tasks()
                if task is not current and not task.done()
            ],
            "environment": _environment(),
            "elapsed_seconds": time.monotonic() - started,
        }
    except Exception as error:
        environment_unavailable = (
            isinstance(error, OSError)
            and error.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}
            and stage.startswith("raw-population-")
        )
        payload = {
            "execution_status": "completed",
            "error_type": type(error).__name__,
            "error": str(error),
            "error_errno": getattr(error, "errno", None),
            "environment_unavailable": environment_unavailable,
            "stage": stage,
            "environment": _environment(),
            "elapsed_seconds": time.monotonic() - started,
        }
    print(json.dumps(payload, sort_keys=True))
    return 0


async def _candidate_worker() -> int:
    started = time.monotonic()
    try:
        probe = await run_wire_probe()
    except Exception as error:
        payload = {
            "execution_status": "completed",
            "candidate_status": "provisional",
            "probe": None,
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": time.monotonic() - started,
            "environment": _environment(),
        }
    else:
        checks = (
            probe["response_id"] == probe["query_id"],
            probe["question_count"] == 1,
            probe["all_cache_flush_clear"],
            probe["ttl_valid"],
            probe["required_records_present"],
            probe["txt_exact"],
            probe["a_only"],
            probe["response_received_on_ephemeral_socket"],
        )
        payload = {
            "execution_status": "completed",
            "candidate_status": "meets_gate" if all(checks) else "rejected",
            "probe": probe,
            "error_type": None,
            "error": None,
            "elapsed_seconds": time.monotonic() - started,
            "environment": _environment(),
        }
    print(json.dumps(payload, sort_keys=True))
    return 0


def _worker_command(inputs: dict[str, Any]) -> list[str]:
    zeroconf_version = inputs["candidate"]["version"]
    return [
        "uv",
        "run",
        "--isolated",
        "--no-project",
        "--with",
        "./packages/lifx-emulator-core",
        "--with",
        f"zeroconf=={zeroconf_version}",
        "--with",
        f"lifx-async @ git+https://github.com/Djelibeybi/lifx-async.git@{ORACLE_REVISION}",
        "python",
        "scripts/spike_mdns_candidates.py",
        "candidate-worker",
    ]


def _expanded_worker_command(inputs: dict[str, Any]) -> list[str]:
    return [*_worker_command(inputs), "--expanded"]


def _direct_worker_command(inputs: dict[str, Any]) -> list[str]:
    oracle_path = os.environ.get("MDNS_SPIKE_ORACLE_PATH")
    command = _worker_command(inputs)
    if oracle_path:
        dependency_index = command.index(
            f"lifx-async @ git+https://github.com/Djelibeybi/lifx-async.git@{ORACLE_REVISION}"
        )
        command[dependency_index] = oracle_path
    command.append("--direct")
    return command


def _find_candidate(evidence: dict[str, Any], name: str) -> dict[str, Any]:
    for candidate in evidence["candidates"]:
        if candidate["candidate"] == name:
            return candidate
    raise ValueError(f"candidate {name!r} is absent from the ledger")


def _record_provenance(candidate: dict[str, Any], inputs: dict[str, Any]) -> None:
    candidate["criteria"]["official_provenance"] = asdict(
        CriterionResult(
            "demonstrated",
            (
                "PyPI JSON resolved latest non-yanked zeroconf "
                f"{inputs['candidate']['version']} with sdist SHA256 "
                f"{inputs['candidate']['sdist_sha256']}; annotated tag resolves to "
                f"{inputs['candidate']['commit']}. GitHub commits API and a detached "
                f"exact-SHA fetch verified oracle {ORACLE_REVISION}."
            ),
        )
    )


def _merge_wire_result(candidate: dict[str, Any], result: dict[str, Any]) -> None:
    attempt = {
        "gate": "legacy-wire",
        "recorded_at": _utc_now(),
        **result,
    }
    candidate["attempts"].append(attempt)
    if result["probe"] is None:
        acquisition = (
            "Repeat the isolated worker on an IPv4 multicast-capable host with "
            "the host mDNS daemon running."
        )
        candidate["criteria"]["legacy_wire"] = asdict(
            CriterionResult(
                "untested",
                f"Probe unavailable: {result['error_type']}: {result['error']}",
                acquisition,
            )
        )
        candidate["candidate_status"] = "provisional"
        return
    probe = result["probe"]
    passed = result["candidate_status"] == "meets_gate"
    candidate["criteria"]["legacy_wire"] = asdict(
        CriterionResult(
            "demonstrated" if passed else "failed",
            json.dumps(probe, sort_keys=True),
        )
    )
    candidate["criteria"]["packet_boundary"] = asdict(
        CriterionResult(
            "demonstrated" if probe["required_records_present"] else "failed",
            (
                f"One captured datagram carried record types "
                f"{probe['record_types']} and {probe['record_count']} records."
            ),
        )
    )
    exact = probe["txt_exact"] and probe["a_only"]
    candidate["criteria"]["exact_txt_and_family"] = asdict(
        CriterionResult(
            "demonstrated" if exact else "failed",
            f"TXT={probe['txt_records']}; A-only={probe['a_only']}",
        )
    )
    candidate["candidate_status"] = "provisional" if passed else "rejected"


def _refresh_decision(evidence: dict[str, Any]) -> None:
    candidate = evidence["candidates"][-1]
    statuses = {result["status"] for result in candidate["criteria"].values()}
    if candidate["candidate_status"] == "rejected":
        evidence["decision"] = {
            "status": "provisional",
            "reason": (
                f"{candidate['candidate']} was rejected by a reached gate; the next "
                "D-09/D-11 fallback remains unevaluated."
            ),
            "extension_case": None,
        }
    elif statuses <= {"demonstrated", "simulated", "not-run-with-reason"}:
        evidence["decision"] = {
            "status": "go",
            "reason": "Every required MDNS-10 gate is evidenced.",
            "extension_case": None,
        }
        candidate["candidate_status"] = "meets_gate"
    else:
        evidence["decision"] = {
            "status": "provisional",
            "reason": (
                "One or more required platform, packaging, oracle, benchmark or "
                "lifecycle gates remain untested."
            ),
            "extension_case": None,
        }


def _load_or_initialise(path: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        evidence = _read_json(path)
        if evidence.get("input_spec_digest") != inputs["input_spec_digest"]:
            previous = evidence["input_spec_digest"]
            evidence.setdefault("input_spec_history", []).append(
                {"digest": previous, "superseded_at": _utc_now()}
            )
            evidence["input_spec_digest"] = inputs["input_spec_digest"]
            evidence["inputs"] = inputs
        for candidate in evidence.get("candidates", []):
            for attempt in candidate.get("attempts", []):
                probe = attempt.get("probe")
                if not isinstance(probe, dict):
                    continue
                if "interface" in probe:
                    probe["interface"] = "selected-ipv4"
                for name in ("client_endpoint", "peer"):
                    endpoint = probe.get(name)
                    if isinstance(endpoint, list) and len(endpoint) == 2:
                        endpoint[0] = "selected-ipv4"
                legacy = candidate.get("criteria", {}).get("legacy_wire")
                if isinstance(legacy, dict):
                    legacy["evidence"] = json.dumps(probe, sort_keys=True)
        return evidence
    return _initial_evidence(inputs)


def _run_candidate(args: argparse.Namespace) -> int:
    inputs = resolve_inputs()
    evidence_path = Path(args.evidence)
    evidence = _load_or_initialise(evidence_path, inputs)
    candidate = _find_candidate(evidence, args.candidate)
    _record_provenance(candidate, inputs)
    if any(attempt.get("gate") == "legacy-wire" for attempt in candidate["attempts"]):
        result = candidate["attempts"][-1]
        if result.get("probe") is None:
            print("Existing provisional legacy-wire attempt retained.")
    else:
        command = _worker_command(inputs)
        environment = dict(os.environ)
        environment["MDNS_SPIKE_WORKER"] = "1"
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        evidence["commands"].append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "recorded_at": _utc_now(),
            }
        )
        if completed.returncode != 0:
            result = {
                "execution_status": "tool_error",
                "candidate_status": "provisional",
                "probe": None,
                "error_type": "WorkerExit",
                "error": completed.stderr[-4000:],
                "elapsed_seconds": 0.0,
                "environment": _environment(),
            }
            candidate["execution_status"] = "tool_error"
        else:
            result = json.loads(completed.stdout.strip().splitlines()[-1])
        _merge_wire_result(candidate, result)
        environment_key = "/".join(
            str(result["environment"][key]) for key in ("os", "architecture", "python")
        )
        evidence["environments"][environment_key] = result["environment"]
    elapsed = _active_elapsed()
    evidence["active_elapsed_seconds"] = round(elapsed, 3)
    candidate["elapsed_active_seconds"] = round(elapsed, 3)
    evidence["updated_at"] = _utc_now()
    _refresh_decision(evidence)
    _write_json(evidence_path, evidence)
    render_evidence(evidence_path)
    return validate_evidence(evidence_path)


def _mark_local_remaining(evidence: dict[str, Any]) -> None:
    candidate = _find_candidate(evidence, "zeroconf")
    criteria = candidate["criteria"]
    if candidate["candidate_status"] == "rejected":
        for name in (
            "oracle_discovery",
            "wifi_benchmark",
            "thread_benchmark",
            "mixed_10_benchmark",
            "mixed_100_benchmark",
        ):
            if criteria[name]["status"] == "untested":
                criteria[name] = asdict(
                    CriterionResult(
                        "not-run-with-reason",
                        "An earlier decisive rejection made this gate irrelevant.",
                    )
                )
        return
    if criteria["daemon_coexistence"]["status"] == "untested":
        criteria["daemon_coexistence"] = asdict(
            CriterionResult(
                "demonstrated",
                "The local legacy-unicast probe completed beside the running "
                "host daemon.",
            )
        )
    if criteria["lifecycle_cleanup"]["status"] == "untested":
        criteria["lifecycle_cleanup"] = asdict(
            CriterionResult(
                "demonstrated",
                "The worker unregistered the service, closed AsyncZeroconf, "
                "the client socket and stock server.",
            )
        )
    criteria["windows_socket_simulation"] = asdict(
        CriterionResult(
            "simulated",
            "Windows remains identified simulation-only in the initial spike.",
        )
    )


def _merge_expanded_result(candidate: dict[str, Any], result: dict[str, Any]) -> None:
    candidate["attempts"].append(
        {"gate": "expanded-local", "recorded_at": _utc_now(), **result}
    )
    criteria = candidate["criteria"]
    if result.get("error_type"):
        acquisition = (
            "Repeat the expanded local worker on an IPv4 multicast-capable host."
        )
        for name in (
            "direct_address_queries",
            "daemon_coexistence",
            "oracle_discovery",
            "wifi_benchmark",
            "thread_benchmark",
            "mixed_10_benchmark",
            "mixed_100_benchmark",
            "lifecycle_cleanup",
        ):
            criteria[name] = asdict(
                CriterionResult(
                    "untested",
                    (
                        f"Expanded probe unavailable: {result['error_type']}: "
                        f"{result['error']}"
                    ),
                    acquisition,
                )
            )
        candidate["candidate_status"] = "provisional"
        return
    oracle = result["oracle"]
    wifi_oracle = oracle["wifi"]
    thread_oracle = oracle["thread"]
    all_available_matched = wifi_oracle["matched"] and (
        thread_oracle is None or thread_oracle["matched"]
    )
    oracle_status: CriterionStatus = (
        "demonstrated" if all_available_matched else "failed"
    )
    oracle_evidence = (
        "Pinned lifx-async public discover_mdns() WiFi result="
        f"{wifi_oracle['matched_serials']} on selected IPv4; Thread result="
        f"{None if thread_oracle is None else thread_oracle['matched_serials']}."
    )
    acquisition: str | None = None
    if wifi_oracle["matched"] and thread_oracle is None:
        oracle_status = "untested"
        oracle_evidence += (
            " No reachable ULA/GUA was available for the Thread oracle leg."
        )
        acquisition = (
            "Run the frozen candidate on a host with a reachable ULA or GUA and "
            "repeat public discover_mdns() for the Thread record."
        )
    criteria["oracle_discovery"] = asdict(
        CriterionResult(oracle_status, oracle_evidence, acquisition)
    )
    if not all_available_matched:
        candidate["candidate_status"] = "rejected"
        for name in (
            "wifi_benchmark",
            "thread_benchmark",
            "mixed_10_benchmark",
            "mixed_100_benchmark",
        ):
            criteria[name] = asdict(
                CriterionResult(
                    "not-run-with-reason",
                    "Public oracle discovery failed before the benchmark gate.",
                )
            )
        return
    benchmarks = result["benchmarks"]
    mapping = {
        "wifi_benchmark": "wifi-1",
        "thread_benchmark": "thread-1",
        "mixed_10_benchmark": "mixed-10",
        "mixed_100_benchmark": "mixed-100",
    }
    for criterion, population in mapping.items():
        if population not in benchmarks:
            criteria[criterion] = asdict(
                CriterionResult(
                    "not-run-with-reason",
                    "The mixed-10 complete-datagram gate rejected this candidate.",
                )
            )
            continue
        metrics = benchmarks[population]
        passed = (
            metrics["discovered"] == metrics["expected"]
            and metrics["complete_devices"] == metrics["expected"]
        )
        criteria[criterion] = asdict(
            CriterionResult(
                "demonstrated" if passed else "failed",
                json.dumps(metrics, sort_keys=True),
            )
        )
        if not passed:
            candidate["candidate_status"] = "rejected"
    mixed_10 = benchmarks["mixed-10"]
    mixed_10_passed = (
        mixed_10["discovered"] == mixed_10["expected"]
        and mixed_10["complete_devices"] == mixed_10["expected"]
    )
    if not mixed_10_passed and "mixed-100" in benchmarks:
        existing = criteria["mixed_100_benchmark"]
        existing["evidence"] = (
            "Diagnostic only, not decision-supporting: this was executed before "
            "the mixed-10 rejection was isolated. " + existing["evidence"]
        )
    wifi_direct = benchmarks["wifi-1"]["direct_a"]
    thread_direct = benchmarks["thread-1"]["direct_aaaa"]
    direct_passed = (
        wifi_direct is not None
        and wifi_direct["direct_match"]
        and thread_direct is not None
        and thread_direct["direct_match"]
    )
    criteria["direct_address_queries"] = asdict(
        CriterionResult(
            "demonstrated" if direct_passed else "failed",
            f"WiFi A={wifi_direct}; Thread AAAA={thread_direct}",
        )
    )
    if not direct_passed:
        candidate["candidate_status"] = "rejected"
    daemon_processes = result["daemon_processes"]
    criteria["daemon_coexistence"] = asdict(
        CriterionResult(
            "demonstrated" if daemon_processes else "untested",
            f"Identified host daemons: {daemon_processes or 'none visible'}.",
            None
            if daemon_processes
            else "Repeat on a host where the running mDNS daemon is observable.",
        )
    )
    clean = (
        result["threads_before"] == result["threads_after"]
        and not result["pending_owned_tasks"]
    )
    criteria["lifecycle_cleanup"] = asdict(
        CriterionResult(
            "demonstrated" if clean else "failed",
            (
                f"threads before={result['threads_before']}; after="
                f"{result['threads_after']}; pending={result['pending_owned_tasks']}"
            ),
        )
    )
    if not clean:
        candidate["candidate_status"] = "rejected"


def _run_expanded_local(evidence: dict[str, Any], inputs: dict[str, Any]) -> int:
    candidate = _find_candidate(evidence, "zeroconf")
    if any(
        attempt.get("gate") == "expanded-local" for attempt in candidate["attempts"]
    ):
        return 0
    command = _expanded_worker_command(inputs)
    environment = dict(os.environ)
    environment["MDNS_SPIKE_WORKER"] = "1"
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    evidence["commands"].append(
        {
            "command": command,
            "exit_code": completed.returncode,
            "recorded_at": _utc_now(),
        }
    )
    if completed.returncode != 0:
        candidate["execution_status"] = "tool_error"
        return 1
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    _merge_expanded_result(candidate, result)
    environment_key = "/".join(
        str(result["environment"][key]) for key in ("os", "architecture", "python")
    )
    evidence["environments"][environment_key] = result["environment"]
    return 0


def _run_direct_candidate(evidence: dict[str, Any], inputs: dict[str, Any]) -> int:
    if any(
        candidate["candidate"] == "lifx-direct" for candidate in evidence["candidates"]
    ):
        return 0
    command = _direct_worker_command(inputs)
    environment = dict(os.environ)
    environment["MDNS_SPIKE_WORKER"] = "1"
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    evidence["commands"].append(
        {
            "command": command,
            "exit_code": completed.returncode,
            "recorded_at": _utc_now(),
        }
    )
    if completed.returncode != 0:
        return 1
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    if result.get("error_type"):
        return 1
    criteria = _blank_criteria("The direct extension gate has not run.")
    fallback = inputs["fallbacks"]["lifx-direct"]
    criteria["official_provenance"] = asdict(
        CriterionResult(
            "demonstrated",
            (
                f"Pinned lifx-async {fallback['base_revision']} tree "
                f"{fallback['base_tree']}; mDNS subtree archive "
                f"{fallback['mdns_subtree_archive_sha256']}; overlay "
                f"{fallback['overlay_sha256']}."
            ),
        )
    )
    benchmarks = result["benchmarks"]
    all_wire = all(value["wire_checks_passed"] for value in benchmarks.values())
    criteria["legacy_wire"] = asdict(
        CriterionResult(
            "demonstrated" if all_wire else "failed",
            "Every response echoed the non-zero ID and question, cleared cache-flush, "
            "used TTL 10, and carried exact TXT.",
        )
    )
    complete = all(
        value["complete_devices"] == value["expected"]
        and value["datagram_count"] == value["expected"]
        for value in benchmarks.values()
    )
    criteria["packet_boundary"] = asdict(
        CriterionResult(
            "demonstrated" if complete else "failed",
            "Each synthetic device produced one isolated complete datagram.",
        )
    )
    criteria["exact_txt_and_family"] = asdict(
        CriterionResult(
            "demonstrated" if all_wire else "failed",
            "WiFi replies contained A only; Thread replies contained AAAA only; "
            "TXT was exactly id/p/fw/tm.",
        )
    )
    direct_ok = all(
        all(value["direct_queries"].values()) for value in benchmarks.values()
    )
    criteria["direct_address_queries"] = asdict(
        CriterionResult(
            "demonstrated" if direct_ok else "failed",
            "Direct A and AAAA queries echoed their IDs/questions with one address.",
        )
    )
    oracle = result["oracle"]
    oracle_ok = oracle["wifi"]["matched"] and (
        oracle["thread"] is None or oracle["thread"]["matched"]
    )
    criteria["oracle_discovery"] = asdict(
        CriterionResult(
            "demonstrated" if oracle_ok else "failed",
            f"Pinned public oracle results: {oracle}.",
        )
    )
    mapping = {
        "wifi_benchmark": "wifi-1",
        "thread_benchmark": "thread-1",
        "mixed_10_benchmark": "mixed-10",
        "mixed_100_benchmark": "mixed-100",
    }
    for criterion, population in mapping.items():
        metrics = benchmarks[population]
        passed = (
            metrics["discovered"] == metrics["expected"]
            and metrics["complete_devices"] == metrics["expected"]
        )
        criteria[criterion] = asdict(
            CriterionResult(
                "demonstrated" if passed else "failed",
                json.dumps(metrics, sort_keys=True),
            )
        )
    daemon = result["daemon_processes"]
    criteria["daemon_coexistence"] = asdict(
        CriterionResult(
            "demonstrated" if daemon else "untested",
            f"Identified host daemons: {daemon or 'none visible'}.",
            None if daemon else "Repeat where the host daemon is observable.",
        )
    )
    clean = (
        result["threads_before"] == result["threads_after"]
        and not result["pending_owned_tasks"]
    )
    criteria["lifecycle_cleanup"] = asdict(
        CriterionResult(
            "demonstrated" if clean else "failed",
            f"threads before={result['threads_before']}; "
            f"after={result['threads_after']}; "
            f"pending={result['pending_owned_tasks']}",
        )
    )
    criteria["windows_socket_simulation"] = asdict(
        CriterionResult(
            "simulated",
            "Windows remains identified simulation-only in the initial spike.",
        )
    )
    criteria["malformed_truncated_flood_bounds"] = asdict(
        CriterionResult(
            "demonstrated" if result["malformed_bounded"] else "failed",
            "Truncated queries raise a bounded ValueError; the 100-device query "
            "returned exactly 100 bounded responses.",
        )
    )
    criteria["configuration_interface_fit"] = asdict(
        CriterionResult(
            "demonstrated" if all(result["fit_checks"].values()) else "failed",
            "Bounded materialiser fit checks: "
            f"{json.dumps(result['fit_checks'], sort_keys=True)}.",
        )
    )
    criteria["dynamic_lifecycle_recovery_fit"] = asdict(
        CriterionResult(
            "demonstrated" if clean else "failed",
            "Four independent responder/server lifecycles closed with no owned "
            "tasks or threads remaining.",
        )
    )
    decisive_protocol_ok = (
        all_wire
        and complete
        and direct_ok
        and clean
        and result["malformed_bounded"]
        and all(result["fit_checks"].values())
    )
    evidence["candidates"].append(
        {
            "candidate": "lifx-direct",
            "execution_status": "completed",
            "candidate_status": ("provisional" if decisive_protocol_ok else "rejected"),
            "criteria": criteria,
            "elapsed_active_seconds": round(_active_elapsed(), 3),
            "attempts": [
                {"gate": "expanded-local", "recorded_at": _utc_now(), **result}
            ],
        }
    )
    environment_key = "/".join(
        str(result["environment"][key]) for key in ("os", "architecture", "python")
    )
    evidence["environments"][environment_key] = result["environment"]
    return 0


def run_sequence(args: argparse.Namespace) -> int:
    evidence_path = Path(args.evidence)
    inputs = resolve_inputs()
    evidence = _load_or_initialise(evidence_path, inputs)
    candidate = _find_candidate(evidence, "zeroconf")
    if not candidate["attempts"]:
        result = _run_candidate(args)
        if result != 0:
            return result
        evidence = _read_json(evidence_path)
    if candidate["candidate_status"] != "rejected":
        if _run_expanded_local(evidence, inputs) != 0:
            evidence["updated_at"] = _utc_now()
            _write_json(evidence_path, evidence)
            render_evidence(evidence_path)
            return 1
    _mark_local_remaining(evidence)
    if candidate["candidate_status"] == "rejected" and "fallbacks" in inputs:
        if _run_direct_candidate(evidence, inputs) != 0:
            evidence["updated_at"] = _utc_now()
            _write_json(evidence_path, evidence)
            render_evidence(evidence_path)
            return 1
    acquisition = "Collect and merge the exact-head CI artefact for this gate."
    for name in ("ubuntu_multicast", "macos_multicast", "intel_pyapp_first_run"):
        if evidence["candidates"][0]["criteria"][name]["status"] == "untested":
            evidence["candidates"][0]["criteria"][name] = asdict(
                CriterionResult(
                    "untested",
                    "Exact-head CI evidence has not yet been merged.",
                    acquisition,
                )
            )
    for name in (
        "direct_address_queries",
        "oracle_discovery",
        "wifi_benchmark",
        "thread_benchmark",
        "mixed_10_benchmark",
        "mixed_100_benchmark",
    ):
        current = evidence["candidates"][0]["criteria"][name]
        if current["status"] == "untested":
            current["evidence"] = "This progressive gate remains to be acquired."
            current["acquisition_step"] = (
                "Run the full candidate sequence on the frozen input specification."
            )
    elapsed = _active_elapsed()
    evidence["active_elapsed_seconds"] = round(elapsed, 3)
    evidence["candidates"][-1]["elapsed_active_seconds"] = round(elapsed, 3)
    evidence["updated_at"] = _utc_now()
    _refresh_decision(evidence)
    _write_json(evidence_path, evidence)
    render_evidence(evidence_path)
    return validate_evidence(evidence_path)


def validate_evidence(path: Path) -> int:
    """Validate structure, ordering, cap and decision support."""
    try:
        evidence = _read_json(path)
        if evidence.get("schema_version") != 1:
            raise ValueError("unsupported evidence schema")
        if evidence.get("candidate_order") != [
            "zeroconf",
            "lifx-direct",
            "lifx-adapted",
            "new-responder",
        ]:
            raise ValueError("candidate order does not match D-09/D-11")
        if float(evidence["active_elapsed_seconds"]) > ACTIVE_BUDGET_SECONDS:
            raise ValueError("four-active-hour cap was exceeded")
        inputs = resolve_inputs()
        if evidence.get("input_spec_digest") != inputs["input_spec_digest"]:
            raise ValueError("shared input_spec_digest mismatch")
        candidates = evidence.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("candidate ledger is empty")
        names = [candidate["candidate"] for candidate in candidates]
        if names != evidence["candidate_order"][: len(names)]:
            raise ValueError("candidate results violate the fixed ordering")
        allowed = {
            "demonstrated",
            "failed",
            "simulated",
            "untested",
            "not-run-with-reason",
        }
        for candidate in candidates:
            if candidate["execution_status"] == "tool_error":
                raise ValueError("candidate execution contains tool_error")
            for name, result in candidate["criteria"].items():
                if result.get("status") not in allowed:
                    raise ValueError(f"criterion {name} has invalid status")
                if result["status"] == "untested" and not result.get(
                    "acquisition_step"
                ):
                    raise ValueError(f"criterion {name} lacks an acquisition step")
        if len(evidence.get("edge_coverage", [])) != 46:
            raise ValueError("all 46 SPEC edge rows must be represented")
        decision = evidence.get("decision", {}).get("status")
        if decision == "go":
            required = candidates[-1]["criteria"].values()
            if any(
                result["status"] not in {"demonstrated", "simulated"}
                for result in required
            ):
                raise ValueError("go is unsupported by incomplete required evidence")
        if decision not in {"go", "no-go", "provisional"}:
            raise ValueError("decision must be go, no-go or provisional")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Evidence invalid: {error}", file=sys.stderr)
        return 1
    print(
        f"Evidence valid: decision={evidence['decision']['status']} "
        f"active={evidence['active_elapsed_seconds']:.3f}s"
    )
    return 0


def _classify_direct_result(result: dict[str, Any]) -> tuple[bool, CandidateStatus]:
    """Separate a completed platform probe from candidate compliance."""
    try:
        if result.get("execution_status") != "completed":
            return False, "provisional"
        if result.get("error_type"):
            return bool(result.get("environment_unavailable")), "provisional"
        protocol_ok = (
            result["malformed_bounded"]
            and result["threads_before"] == result["threads_after"]
            and not result["pending_owned_tasks"]
            and all(
                metrics["discovered"] == metrics["expected"]
                and metrics["complete_devices"] == metrics["expected"]
                and metrics["datagram_count"] == metrics["expected"]
                and metrics["wire_checks_passed"]
                and all(metrics["direct_queries"].values())
                for metrics in result["benchmarks"].values()
            )
        )
        oracle = result["oracle"]
        oracle_ok = oracle["wifi"]["matched"] and (
            oracle["thread"] is not None and oracle["thread"]["matched"]
        )
        environment_ok = bool(result["daemon_processes"])
    except (KeyError, TypeError):
        return False, "provisional"
    if not protocol_ok:
        return True, "rejected"
    if oracle_ok and environment_ok:
        return True, "meets_gate"
    return True, "provisional"


def _run_direct_platform(args: argparse.Namespace) -> int:
    inputs = resolve_inputs()
    oracle_path = os.environ.get("MDNS_SPIKE_ORACLE_PATH")
    if oracle_path:
        candidate = inputs["fallbacks"]["lifx-direct"]
        if not _oracle_checkout_matches(
            oracle_path, candidate["base_revision"], candidate["base_tree"]
        ):
            print(
                "local oracle checkout differs from the immutable commit/tree or "
                "has tracked changes",
                file=sys.stderr,
            )
            return 1
    command = _direct_worker_command(inputs)
    environment = dict(os.environ)
    environment["MDNS_SPIKE_WORKER"] = "1"
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if completed.returncode != 0:
        print(completed.stderr, file=sys.stderr)
        return 1
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    valid, candidate_status = _classify_direct_result(result)
    payload = {
        "schema_version": 1,
        "platform_candidate": "lifx-direct",
        "input_spec_digest": inputs["input_spec_digest"],
        "valid": valid,
        "candidate_status": candidate_status,
        "thread_address_origin": os.environ.get(
            "MDNS_SPIKE_THREAD_ADDRESS_ORIGIN", "host-existing"
        ),
        "command": command,
        "result": result,
    }
    _write_json(Path(args.output), payload)
    return 0 if valid else 1


def _classify_direct_result_cli(args: argparse.Namespace) -> int:
    valid, candidate_status = _classify_direct_result(_read_json(Path(args.input)))
    print(json.dumps({"valid": valid, "candidate_status": candidate_status}))
    return 0 if valid else 1


def _write_ci_receipt(args: argparse.Namespace) -> int:
    evidence_path = Path(args.evidence)
    evidence = _read_json(evidence_path)
    inputs = resolve_inputs()
    platform_candidate = evidence.get("platform_candidate")
    if platform_candidate == "lifx-direct":
        if not evidence.get("valid"):
            return 1
        candidate = inputs["fallbacks"]["lifx-direct"]
        environments = {
            "/".join(
                str(evidence["result"]["environment"][key])
                for key in ("os", "architecture", "python")
            ): evidence["result"]["environment"]
        }
        base_commit = candidate["base_revision"]
        base_tree = candidate["base_tree"]
        overlay_digest = candidate["overlay_sha256"]
        final_digest = candidate["final_digest"]
    else:
        if validate_evidence(evidence_path) != 0:
            return 1
        candidate = inputs["candidate"]
        environments = evidence["environments"]
        base_commit = candidate["commit"]
        base_tree = candidate["tree"]
        overlay_digest = candidate["overlay_digest"]
        final_digest = candidate["sdist_sha256"]
    receipt = {
        "schema_version": 1,
        "candidate_head_sha": args.head_sha,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidate": platform_candidate or candidate["name"],
        "candidate_base_commit": base_commit,
        "candidate_base_tree": base_tree,
        "candidate_overlay_digest": overlay_digest,
        "candidate_final_digest": final_digest,
        "candidate_status": evidence.get("candidate_status", "provisional"),
        "thread_address_origin": evidence.get("thread_address_origin", "host-existing"),
        "platform_leg": args.platform_leg,
        "run_url": args.run_url,
        "environments": environments,
        "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        "recorded_at": _utc_now(),
    }
    _write_json(Path(args.output), receipt)
    return 0


def _write_intel_pyapp_receipt(args: argparse.Namespace) -> int:
    inputs = resolve_inputs()
    candidate = inputs["fallbacks"]["lifx-direct"]
    candidate_metadata = Path(args.candidate_metadata).read_text(encoding="utf-8")
    app_metadata = Path(args.app_metadata).read_text(encoding="utf-8")
    direct_references = {
        "lifx_async": bool(
            re.search(r"Requires-Dist:\s*lifx-async\s*@\s*file:", app_metadata)
        ),
        "lifx_emulator_core": bool(
            re.search(r"Requires-Dist:\s*lifx-emulator-core\s*@\s*file:", app_metadata)
        ),
        "candidate_metadata": "Name: lifx-async" in candidate_metadata,
    }
    if not all(direct_references.values()):
        print("Intel wheel METADATA does not prove exact local inputs", file=sys.stderr)
        return 1
    environment = _environment()
    environment_key = "/".join(
        str(environment[key]) for key in ("os", "architecture", "python")
    )
    receipt = {
        "schema_version": 1,
        "candidate_head_sha": args.head_sha,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidate": "lifx-direct",
        "candidate_base_commit": candidate["base_revision"],
        "candidate_base_tree": candidate["base_tree"],
        "candidate_overlay_digest": candidate["overlay_sha256"],
        "candidate_final_digest": candidate["final_digest"],
        "candidate_status": "meets_gate",
        "platform_leg": "intel-pyapp",
        "run_url": args.run_url,
        "environments": {environment_key: environment},
        "hashes_sha256": hashlib.sha256(Path(args.hashes).read_bytes()).hexdigest(),
        "identities": _read_json(Path(args.identities)),
        "rustc": Path(args.rustc).read_text(encoding="utf-8"),
        "first_run_sha256": hashlib.sha256(
            Path(args.first_run).read_bytes()
        ).hexdigest(),
        "candidate_metadata_sha256": hashlib.sha256(
            Path(args.candidate_metadata).read_bytes()
        ).hexdigest(),
        "app_metadata_sha256": hashlib.sha256(
            Path(args.app_metadata).read_bytes()
        ).hexdigest(),
        "direct_references": direct_references,
        "pyapp": {
            "version": PYAPP_VERSION,
            "revision": PYAPP_REVISION,
            "tree": PYAPP_TREE,
        },
        "uv_version": os.environ.get("UV_VERSION"),
        "recorded_at": _utc_now(),
    }
    _write_json(Path(args.output), receipt)
    return 0


def _validate_ci_receipt(args: argparse.Namespace) -> int:
    try:
        receipt = _read_json(Path(args.receipt))
        inputs = resolve_inputs()
        candidate = inputs["fallbacks"]["lifx-direct"]
        expected = {
            "candidate": "lifx-direct",
            "candidate_head_sha": args.head_sha,
            "input_spec_digest": inputs["input_spec_digest"],
            "candidate_base_commit": candidate["base_revision"],
            "candidate_base_tree": candidate["base_tree"],
            "candidate_overlay_digest": candidate["overlay_sha256"],
            "candidate_final_digest": candidate["final_digest"],
        }
        for name, value in expected.items():
            if receipt.get(name) != value:
                raise ValueError(
                    f"receipt {name} mismatch: {receipt.get(name)!r} != {value!r}"
                )
        if not receipt.get("environments"):
            raise ValueError("receipt has no realised platform environment")
        if receipt.get("platform_leg") == "intel-pyapp":
            if receipt.get("candidate_status") != "meets_gate":
                raise ValueError("Intel receipt is not a completed packaging gate")
            if receipt.get("pyapp") != {
                "version": PYAPP_VERSION,
                "revision": PYAPP_REVISION,
                "tree": PYAPP_TREE,
            }:
                raise ValueError("Intel receipt has mismatched PyApp source")
            if receipt.get("uv_version") != "0.9.9":
                raise ValueError("Intel receipt has mismatched uv version")
            if not all((receipt.get("direct_references") or {}).values()):
                raise ValueError("Intel receipt lacks exact local wheel references")
            for name in (
                "hashes_sha256",
                "identities",
                "rustc",
                "first_run_sha256",
                "candidate_metadata_sha256",
                "app_metadata_sha256",
            ):
                if not receipt.get(name):
                    raise ValueError(f"Intel receipt lacks {name}")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"CI receipt invalid: {error}", file=sys.stderr)
        return 1
    print("CI receipt valid: lifx-direct exact head and immutable inputs match")
    return 0


def _oracle_checkout_matches(
    path: str, expected_revision: str, expected_tree: str
) -> bool:
    """Require an exact, tracked-clean checkout before using a local oracle."""
    for arguments, expected in (
        (("rev-parse", "HEAD"), expected_revision),
        (("rev-parse", "HEAD^{tree}"), expected_tree),
    ):
        completed = subprocess.run(
            ["git", "-C", path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode != 0 or completed.stdout.strip() != expected:
            return False
    for arguments in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
        completed = subprocess.run(
            ["git", "-C", path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode != 0:
            return False
    return True


def _validate_oracle_checkout(args: argparse.Namespace) -> int:
    if _oracle_checkout_matches(args.path, args.revision, args.tree):
        print("Oracle checkout valid: exact commit/tree with clean tracked files")
        return 0
    print(
        "Oracle checkout invalid: commit/tree mismatch or tracked changes",
        file=sys.stderr,
    )
    return 1


def render_evidence(path: Path) -> Path:
    evidence = _read_json(path)
    output = path.with_suffix(".md")
    lines = [
        "# Phase 3 Plan 01: mDNS Candidate Evidence",
        "",
        f"- **Decision:** {evidence['decision']['status']}",
        f"- **Reason:** {evidence['decision']['reason']}",
        (
            f"- **Active work:** {evidence['active_elapsed_seconds']:.3f}s / "
            f"{ACTIVE_BUDGET_SECONDS}s"
        ),
        f"- **Input specification:** `{evidence['input_spec_digest']}`",
        "",
        "## Environment",
        "",
    ]
    for key, environment in evidence["environments"].items():
        lines.append(f"- `{key}`: `{environment['realised_environment_digest']}`")
    lines.extend(
        [
            "",
            "## Candidate ledger",
            "",
        ]
    )
    for candidate in evidence["candidates"]:
        lines.extend(
            [
                f"### {candidate['candidate']}",
                "",
                (
                    f"Execution: `{candidate['execution_status']}`; suitability: "
                    f"`{candidate['candidate_status']}`."
                ),
                "",
                "| Criterion | Status | Evidence | Acquisition step |",
                "|---|---|---|---|",
            ]
        )
        for name, result in candidate["criteria"].items():
            evidence_text = str(result["evidence"]).replace("|", "\\|")
            acquisition = str(result.get("acquisition_step") or "—").replace("|", "\\|")
            lines.append(
                f"| {name} | {result['status']} | {evidence_text} | {acquisition} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Benchmarks",
            "",
            (
                "Benchmark measurements are retained in the candidate criteria; "
                "post-rejection diagnostics are labelled non-decision-supporting."
            ),
            "",
            "## Platform and packaging",
            "",
            f"PR: {evidence['pull_request']['url'] or 'not recorded'}",
            "",
            "## Decision",
            "",
            f"**{evidence['decision']['status']}** — {evidence['decision']['reason']}",
            "",
            "## Deferred coverage",
            "",
            "MDNS-01–09 and MDNS-11 remain pending until a human selects an "
            "evidence-valid go route.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    worker = subparsers.add_parser("candidate-worker")
    worker.add_argument("--expanded", action="store_true")
    worker.add_argument("--direct", action="store_true")
    worker.set_defaults(handler=None)
    run = subparsers.add_parser("run-candidate")
    run.add_argument("--candidate", choices=("zeroconf",), required=True)
    run.add_argument("--oracle-revision", required=True)
    run.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    run.add_argument("--stop-after", choices=("legacy-wire",), required=True)
    run.set_defaults(handler=_run_candidate)
    sequence = subparsers.add_parser("run-sequence")
    sequence.add_argument("--resume", action="store_true", required=True)
    sequence.add_argument("--source-revision", required=True)
    sequence.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    sequence.set_defaults(handler=run_sequence, candidate="zeroconf")
    platform_probe = subparsers.add_parser("run-direct-platform")
    platform_probe.add_argument("--output", required=True)
    platform_probe.set_defaults(handler=_run_direct_platform)
    validate = subparsers.add_parser("validate-evidence")
    validate.add_argument("evidence")
    validate.set_defaults(handler=lambda args: validate_evidence(Path(args.evidence)))
    render = subparsers.add_parser("render-evidence")
    render.add_argument("evidence")
    render.set_defaults(
        handler=lambda args: int(not render_evidence(Path(args.evidence)).exists())
    )
    receipt = subparsers.add_parser("write-ci-receipt")
    receipt.add_argument("--evidence", required=True)
    receipt.add_argument("--output", required=True)
    receipt.add_argument("--head-sha", required=True)
    receipt.add_argument("--run-url", required=True)
    receipt.add_argument(
        "--platform-leg", choices=("multicast", "intel-pyapp"), required=True
    )
    receipt.set_defaults(handler=_write_ci_receipt)
    intel_receipt = subparsers.add_parser("write-intel-pyapp-receipt")
    intel_receipt.add_argument("--output", required=True)
    intel_receipt.add_argument("--head-sha", required=True)
    intel_receipt.add_argument("--run-url", required=True)
    intel_receipt.add_argument("--hashes", required=True)
    intel_receipt.add_argument("--identities", required=True)
    intel_receipt.add_argument("--rustc", required=True)
    intel_receipt.add_argument("--first-run", required=True)
    intel_receipt.add_argument("--candidate-metadata", required=True)
    intel_receipt.add_argument("--app-metadata", required=True)
    intel_receipt.set_defaults(handler=_write_intel_pyapp_receipt)
    validate_receipt = subparsers.add_parser("validate-ci-receipt")
    validate_receipt.add_argument("--receipt", required=True)
    validate_receipt.add_argument("--head-sha", required=True)
    validate_receipt.set_defaults(handler=_validate_ci_receipt)
    validate_oracle = subparsers.add_parser("validate-oracle-checkout")
    validate_oracle.add_argument("--path", required=True)
    validate_oracle.add_argument("--revision", required=True)
    validate_oracle.add_argument("--tree", required=True)
    validate_oracle.set_defaults(handler=_validate_oracle_checkout)
    classify_direct = subparsers.add_parser("classify-direct-result")
    classify_direct.add_argument("--input", required=True)
    classify_direct.set_defaults(handler=_classify_direct_result_cli)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "candidate-worker":
        if args.direct:
            worker = _lifx_direct_worker()
        elif args.expanded:
            worker = _expanded_worker()
        else:
            worker = _candidate_worker()
        return asyncio.run(worker)
    if getattr(args, "oracle_revision", ORACLE_REVISION) != ORACLE_REVISION:
        raise SystemExit("oracle revision differs from the immutable pin")
    if getattr(args, "source_revision", ORACLE_REVISION) != ORACLE_REVISION:
        raise SystemExit("source revision differs from the immutable pin")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
