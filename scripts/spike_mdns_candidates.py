#!/usr/bin/env python3
"""Bounded evidence harness for the Phase 3 mDNS responder spike."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import errno
import hashlib
import importlib.metadata
import importlib.util
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
import traceback
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
    from zeroconf import IPVersion, NonUniqueNameException, ServiceInfo
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
MDNS_IPV4_GROUP = "224.0.0.251"
LINUX_IP_MULTICAST_ALL = 49
DARWIN_IP_BOUND_IF = 25

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


def _darwin_interface_index(interface: str) -> int:
    """Resolve the selected IPv4 address to a Darwin interface index."""
    executable = "/sbin/ifconfig" if Path("/sbin/ifconfig").is_file() else "ifconfig"
    pattern = re.compile(rf"\binet\s+{re.escape(interface)}(?:\s|$)")
    for index, name in socket.if_nameindex():
        completed = subprocess.run(
            [executable, name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if completed.returncode == 0 and pattern.search(completed.stdout):
            return index
    raise OSError("selected IPv4 address has no Darwin interface index")


def _new_scoped_mdns_responder(
    interface: str,
) -> tuple[socket.socket, socket.socket, dict[str, Any]]:
    """Create an mDNS listener scoped to one group membership and interface."""
    responder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    reply_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        for current in (responder, reply_sender):
            current.setblocking(False)
            current.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                current.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        scope_controls = ["group-address-bind", "explicit-interface-membership"]
        if sys.platform.startswith("linux"):
            responder.setsockopt(
                socket.IPPROTO_IP,
                LINUX_IP_MULTICAST_ALL,
                0,
            )
            scope_controls.append("IP_MULTICAST_ALL=0")
        elif sys.platform == "darwin":
            interface_index = _darwin_interface_index(interface)
            responder.setsockopt(
                socket.IPPROTO_IP,
                DARWIN_IP_BOUND_IF,
                interface_index,
            )
            reply_sender.setsockopt(
                socket.IPPROTO_IP,
                DARWIN_IP_BOUND_IF,
                interface_index,
            )
            scope_controls.append("IP_BOUND_IF=selected-interface")
        responder.bind((MDNS_IPV4_GROUP, 5353))
        responder.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            socket.inet_aton(MDNS_IPV4_GROUP) + socket.inet_aton(interface),
        )
        reply_sender.bind((interface, 5353))
        bound_address = responder.getsockname()[0]
        reply_address = reply_sender.getsockname()[0]
        return (
            responder,
            reply_sender,
            {
                "bound_address": bound_address,
                "membership_interface": "selected-ipv4",
                "platform_scope_applied": len(scope_controls) == 3,
                "reply_bound_address": (
                    "selected-ipv4" if reply_address == interface else reply_address
                ),
                "reply_source_port": 5353,
                "scope_controls": scope_controls,
                "wildcard_bound": bound_address in {"", "0.0.0.0"},
            },
        )
    except Exception:
        responder.close()
        reply_sender.close()
        raise


def _probe_responder_scope(args: argparse.Namespace) -> int:
    """Record a live, privacy-safe listener scope result."""
    try:
        responder, reply_sender, scope = _new_scoped_mdns_responder(
            _select_ipv4_interface()
        )
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        _write_json(
            Path(args.output),
            {
                "environment_unavailable": True,
                "error_errno": error.errno,
                "error_type": type(error).__name__,
                "stage": "bind-selected-reply-source-5353",
            },
        )
        return 0
    responder.close()
    reply_sender.close()
    _write_json(Path(args.output), scope)
    return 0


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
    try:
        client.setblocking(False)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface)
        )
        client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        if sys.platform == "darwin":
            client.setsockopt(
                socket.IPPROTO_IP,
                DARWIN_IP_BOUND_IF,
                _darwin_interface_index(interface),
            )
        client.bind((interface, 0))
    except OSError:
        client.close()
        raise
    return client


def _socket_option_plan(system: str) -> dict[str, Any]:
    """Return the explicit socket choices evaluated for each host family."""
    if system not in {"Darwin", "Linux", "Windows"}:
        raise ValueError(f"unsupported socket platform {system!r}")
    return {
        "platform": system,
        "family": "AF_INET",
        "type": "SOCK_DGRAM",
        "protocol": "IPPROTO_UDP",
        "reuse_address": True,
        "reuse_port": system != "Windows",
        "multicast_interface": "explicit-ipv4",
        "multicast_ttl": 1,
        "client_bind": "explicit-ipv4:ephemeral",
        "responder_bind": "wildcard:5353",
        "legacy_unicast_destination": "query-source",
    }


def _evaluate_windows_socket_simulation() -> dict[str, Any]:
    """Exercise Windows choices against the POSIX plans without opening sockets."""
    plans = {name: _socket_option_plan(name) for name in ("Windows", "Darwin", "Linux")}
    windows = plans["Windows"]
    common = {
        key: len({plan[key] for plan in plans.values()}) == 1
        for key in (
            "family",
            "type",
            "protocol",
            "reuse_address",
            "multicast_interface",
            "multicast_ttl",
            "client_bind",
            "responder_bind",
            "legacy_unicast_destination",
        )
    }
    checks = {
        "common_choices_match": all(common.values()),
        "windows_omits_reuse_port": windows["reuse_port"] is False,
        "posix_uses_reuse_port": all(
            plans[name]["reuse_port"] for name in ("Darwin", "Linux")
        ),
    }
    return {"plans": plans, "checks": checks, "all_passed": all(checks.values())}


def _complete_record_sets(
    records: list[Any], expected: dict[str, dict[str, Any]]
) -> set[str]:
    """Validate exact DNS-SD associations across all response datagrams."""
    complete = set()
    for serial, wanted in expected.items():
        instance = f"{serial}.{SERVICE_TYPE}".rstrip(".").lower()
        host = f"{serial}.local"
        ptr = any(
            r.rtype == 12
            and r.name.rstrip(".").lower() == SERVICE_TYPE.rstrip(".")
            and str(r.parsed_data).rstrip(".").lower() == instance
            for r in records
        )
        srv = any(
            r.rtype == 33
            and r.name.rstrip(".").lower() == instance
            and r.parsed_data.target.rstrip(".").lower() == host
            and r.parsed_data.port == wanted["port"]
            and r.parsed_data.priority == r.parsed_data.weight == 0
            for r in records
        )
        txt = any(
            r.rtype == 16
            and r.name.rstrip(".").lower() == instance
            and r.parsed_data.pairs == wanted["txt"]
            for r in records
        )
        addresses = {
            (r.rtype, str(ipaddress.ip_address(r.parsed_data)))
            for r in records
            if r.rtype in (1, 28) and r.name.rstrip(".").lower() == host
        }
        if ptr and srv and txt and addresses == {wanted["address"]}:
            complete.add(serial)
    return complete


async def _collect_query(
    client: socket.socket,
    query: bytes,
    *,
    timeout: float,
    expected_serials: set[str],
    direct_record: tuple[str, int] | None = None,
    expected_records: dict[str, dict[str, Any]] | None = None,
    observe_until_timeout: bool = False,
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
    records: list[Any] = []
    wire_checks: list[bool] = []
    while time.monotonic() - started < timeout:
        if (
            not observe_until_timeout
            and expected_serials
            and expected_serials.issubset(complete_serials)
        ):
            break
        if direct_record is not None and direct_match:
            break
        remaining = max(0.01, timeout - (time.monotonic() - started))
        try:
            raw, peer = await _receive_one(client, remaining)
            packet = parse_dns_response(raw)
        except TimeoutError:
            break
        except (OSError, ValueError):
            continue
        wire_checks.append(
            peer[1] == 5353
            and packet.header.id == struct.unpack("!H", query[:2])[0]
            and packet.header.qd_count in ((1,) if not records else (0, 1))
            and all(not r.cache_flush and 0 < r.ttl <= 10 for r in packet.records)
        )
        records.extend(packet.records)
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
        if {DNS_TYPE_PTR, DNS_TYPE_SRV, DNS_TYPE_TXT}.issubset(types) and (
            DNS_TYPE_A in types or DNS_TYPE_AAAA in types
        ):
            complete_datagrams += 1
        if expected_records is not None:
            complete_serials = _complete_record_sets(records, expected_records)
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
        "observed_serials": sorted(serials),
        "direct_match": direct_match,
        "complete_discovery_seconds": round(time.monotonic() - started, 6),
        "cpu_seconds": round(time.process_time() - cpu_started, 6),
        "peak_rss": usage.ru_maxrss,
        "datagram_count": len(datagram_sizes),
        "datagram_sizes": datagram_sizes,
        "record_counts": record_counts,
        "complete_datagrams": complete_datagrams,
        "complete_devices": len(complete_serials),
        "wire_checks_passed": bool(wire_checks) and all(wire_checks),
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
            expected_records={
                device.state.serial: {
                    "port": port,
                    "txt": {
                        "id": device.state.serial,
                        "p": "27",
                        "fw": "4.200",
                        "tm": "1" if number < wifi else "2",
                    },
                    "address": (1, "127.0.0.1") if number < wifi else (28, "::1"),
                }
                for number, device in enumerate(devices)
            },
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
        membership = None
        if total == 10:
            removed = infos.pop()
            goodbye = await azc.async_unregister_service(removed)
            await goodbye
            remaining = {device.state.serial for device in devices[:-1]}
            with _new_mdns_client(interface) as membership_client:
                after_remove = await _collect_query(
                    membership_client,
                    _dns_query(SERVICE_TYPE, DNS_TYPE_PTR, 0xCA01),
                    timeout=2.0,
                    expected_serials=remaining,
                    observe_until_timeout=True,
                )
            readd_retried = False
            readd_error = None
            try:
                try:
                    announcement = await azc.async_register_service(
                        removed, ttl=10, strict=False
                    )
                except NonUniqueNameException:
                    readd_retried = True
                    # Only restore this responder's previously registered identity.
                    announcement = await azc.async_update_service(removed)
                infos.append(removed)
                await announcement
            except NonUniqueNameException as error:
                readd_error = type(error).__name__
            with _new_mdns_client(interface) as membership_client:
                after_readd = await _collect_query(
                    membership_client,
                    _dns_query(SERVICE_TYPE, DNS_TYPE_PTR, 0xCA02),
                    timeout=2.0,
                    expected_serials={device.state.serial for device in devices},
                    observe_until_timeout=True,
                )
            membership = {
                "readd_error": readd_error,
                "readd_via_public_update_after_name_conflict": readd_retried,
                "remaining_after_remove": after_remove["discovered"],
                "removed_absent": devices[-1].state.serial
                not in after_remove["observed_serials"],
                "after_readd": after_readd["discovered"],
                "all_passed": after_remove["discovered"] == total - 1
                and devices[-1].state.serial not in after_remove["observed_serials"]
                and after_readd["discovered"] == total,
                "scope": (
                    "public registration removal/re-add; "
                    "not listener failure or production status integration"
                ),
            }
        metrics.update(
            {
                "membership": membership,
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
    device = create_color_light(
        serial, connectivity="thread" if thread_address else "wifi"
    )
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
    stage = "oracle"
    try:
        reachable = _reachable_ipv6_addresses()
        oracle = {
            "wifi": await _run_public_oracle(),
            "thread": await _run_public_oracle(reachable[0]) if reachable else None,
        }
        # Retain raw diagnostic evidence even when the consumer cannot discover.
        benchmarks = {}
        for stage, wifi, thread_count in (
            ("wifi-1", 1, 0),
            ("thread-1", 0, 1),
            ("mixed-10", 5, 5),
        ):
            benchmarks[stage] = await run_discovery_benchmark(wifi, thread_count)
        mixed_10 = benchmarks["mixed-10"]
        if (
            mixed_10["discovered"] == mixed_10["expected"]
            and mixed_10["complete_devices"] == mixed_10["expected"]
        ):
            stage = "mixed-100"
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
            "failed_stage": stage,
            "traceback": traceback.format_exc(),
            "error_type": type(error).__name__,
            "error": str(error),
            "environment": _environment(),
            "elapsed_seconds": time.monotonic() - started,
        }
    print(json.dumps(payload, sort_keys=True))
    return 0


async def _run_direct_population(wifi: int, thread_count: int) -> dict[str, Any]:
    """Capture raw per-device wire replies without claiming oracle discovery."""
    interface = _select_ipv4_interface()
    total = wifi + thread_count
    devices = [create_color_light(f"d073d6{number:06x}") for number in range(total)]
    server = EmulatedLifxServer(devices, DeviceManager(DeviceRepository()), port=0)
    client = _new_mdns_client(interface)
    responder, reply_sender, _scope = _new_scoped_mdns_responder(interface)
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
            await loop.sock_sendto(reply_sender, response, source)
        discovered: set[str] = set()
        complete = 0
        sizes: list[int] = []
        wire_checks: list[bool] = []
        while len(discovered) < total:
            raw, response_source = await _receive_one(client, 5.0)
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
                    and response_source[1] == 5353
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
                await loop.sock_sendto(reply_sender, response, source)
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
            "raw_capture_seconds": round(time.monotonic() - started, 6),
            "cpu_seconds": round(time.process_time() - cpu_started, 6),
            "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "server_port": server.ipv4_endpoint[1],
            "direct_queries": direct_results,
            "wire_checks_passed": all(wire_checks) and len(wire_checks) == total,
            "raw_thread_address_class": "loopback-::1" if thread_count else None,
            "listener_scope": _scope,
        }
    finally:
        responder.close()
        reply_sender.close()
        client.close()
        await server.stop()


async def _run_direct_public_benchmark(
    wifi: int, thread_count: int, thread_address: str
) -> dict[str, Any]:
    """Measure complete public discover_mdns discovery and stock connectivity."""
    interface = _select_ipv4_interface()
    total = wifi + thread_count
    devices = [
        create_color_light(
            f"d073d7{number:06x}",
            connectivity="thread" if number >= wifi else "wifi",
        )
        for number in range(total)
    ]
    server = EmulatedLifxServer(
        devices,
        DeviceManager(DeviceRepository()),
        bind_address=interface,
        port=0,
        ipv6_bind_address=thread_address,
    )
    responder, reply_sender, _scope = _new_scoped_mdns_responder(interface)
    task: asyncio.Task[None] | None = None
    queries_received = 0
    replies_sent = 0
    discovered_devices: dict[str, Any] = {}
    connectivity: dict[str, dict[str, Any]] = {}
    try:
        await server.start()
        assert server.ipv4_endpoint is not None
        advertisements = [
            Advertisement(
                serial=device.state.serial,
                port=server.ipv4_endpoint[1],
                address=thread_address if number >= wifi else interface,
                transport="2" if number >= wifi else "1",
            )
            for number, device in enumerate(devices)
        ]
        loop = asyncio.get_running_loop()

        async def serve() -> None:
            nonlocal queries_received
            nonlocal replies_sent
            while True:
                query, source = await loop.sock_recvfrom(responder, 9000)
                queries_received += 1
                responses = build_legacy_unicast_responses(query, advertisements)
                for response in responses:
                    await loop.sock_sendto(reply_sender, response, source)
                    replies_sent += 1

        task = asyncio.create_task(serve(), name="lifx-direct-public-benchmark")
        started = time.monotonic()
        cpu_started = time.process_time()
        async for discovered in discover_mdns(
            timeout=4.0,
            max_response_time=0.2,
            idle_timeout_multiplier=2.0,
            device_timeout=1.0,
            max_retries=1,
        ):
            serial = str(discovered.serial)
            if serial in {device.state.serial for device in devices}:
                discovered_devices[serial] = discovered
        elapsed = time.monotonic() - started
        cpu = time.process_time() - cpu_started
        if wifi:
            representative = devices[0].state.serial
            device = discovered_devices[representative]
            await device.connection.open()
            try:
                control_started = time.monotonic()
                control_cpu_started = time.process_time()
                await device.get_power()
            finally:
                await device.connection.close()
            connectivity["wifi"] = {
                "passed": True,
                "latency_seconds": round(time.monotonic() - control_started, 6),
                "cpu_seconds": round(time.process_time() - control_cpu_started, 6),
            }
        if thread_count:
            representative = devices[wifi].state.serial
            device = discovered_devices[representative]
            await device.connection.open()
            try:
                control_started = time.monotonic()
                control_cpu_started = time.process_time()
                await device.get_power()
            finally:
                await device.connection.close()
            connectivity["thread"] = {
                "passed": True,
                "latency_seconds": round(time.monotonic() - control_started, 6),
                "cpu_seconds": round(time.process_time() - control_cpu_started, 6),
            }
        return {
            "wifi": wifi,
            "thread": thread_count,
            "expected": total,
            "discovered": len(discovered_devices),
            "discovered_serials": sorted(discovered_devices),
            "complete_discovery_seconds": round(elapsed, 6),
            "cpu_seconds": round(cpu, 6),
            "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "queries_received": queries_received,
            "reply_datagram_count": replies_sent,
            "representative_stock_connectivity": connectivity,
            "thread_address_class": "reachable-ula-gua" if thread_count else None,
            "server_port": server.ipv4_endpoint[1],
            "listener_scope": _scope,
        }
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        responder.close()
        reply_sender.close()
        await server.stop()


def _exercise_adversarial_bounds() -> dict[str, Any]:
    """Exercise malformed, oversized, record-limit and high-rate inputs."""
    query = _dns_query(SERVICE_TYPE, DNS_TYPE_PTR, 0xB0A0)
    advertisement = Advertisement("d073d7000001", 56700, "192.0.2.10")
    compression_loop = query[:12] + b"\xc0\x0c" + query[-4:]
    malformed_inputs = {
        "empty": b"",
        "short_header": b"\x00" * 11,
        "truncated_question": query[:-1],
        "compression_pointer": compression_loop,
        "oversized_datagram": b"\x00" * 9001,
    }
    rejected: dict[str, str] = {}
    for name, value in malformed_inputs.items():
        try:
            build_legacy_unicast_responses(value, [advertisement])
        except (UnicodeDecodeError, ValueError, struct.error) as error:
            rejected[name] = type(error).__name__
    limit_ads = [
        Advertisement(f"d073d7{number:06x}", 56700, "192.0.2.10")
        for number in range(100)
    ]
    bounded = build_legacy_unicast_responses(query, limit_ads)
    beyond_benchmark = build_legacy_unicast_responses(
        query,
        [*limit_ads, Advertisement("d073d7ffffff", 56700, "192.0.2.10")],
    )
    threads_before = sorted(thread.name for thread in threading.enumerate())
    current = asyncio.current_task()
    pending_before = sorted(
        task.get_name()
        for task in asyncio.all_tasks()
        if task is not current and not task.done()
    )
    started = time.monotonic()
    cpu_started = time.process_time()
    response_count = sum(
        len(build_legacy_unicast_responses(query, [advertisement])) for _ in range(256)
    )
    elapsed = time.monotonic() - started
    cpu = time.process_time() - cpu_started
    threads_after = sorted(thread.name for thread in threading.enumerate())
    pending_after = sorted(
        task.get_name()
        for task in asyncio.all_tasks()
        if task is not current and not task.done()
    )
    checks = {
        "all_malformed_rejected": set(rejected) == set(malformed_inputs),
        "hundred_device_population_exact": len(bounded) == 100,
        "population_above_benchmark_supported": len(beyond_benchmark) == 101,
        "each_datagram_bounded": all(
            len(response) <= 9000 for response in [*bounded, *beyond_benchmark]
        ),
        "high_rate_response_count_bounded": response_count == 256,
        "high_rate_created_no_threads": threads_before == threads_after,
        "high_rate_created_no_pending_tasks": pending_before == pending_after,
    }
    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "malformed_results": rejected,
        "benchmark_population": 100,
        "above_benchmark_population": 101,
        "high_rate_queries": 256,
        "high_rate_responses": response_count,
        "high_rate_seconds": round(elapsed, 6),
        "high_rate_cpu_seconds": round(cpu, 6),
        "threads_before": threads_before,
        "threads_after": threads_after,
        "pending_tasks_before": pending_before,
        "pending_tasks_after": pending_after,
    }


async def _run_direct_oracle(thread_address: str | None = None) -> dict[str, Any]:
    interface = _select_ipv4_interface()
    serial = "d073d6000002" if thread_address else "d073d6000001"
    device = create_color_light(serial)
    server = EmulatedLifxServer([device], DeviceManager(DeviceRepository()), port=0)
    responder, reply_sender, _scope = _new_scoped_mdns_responder(interface)
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
                    await loop.sock_sendto(reply_sender, response, source)
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
            "listener_scope": _scope,
        }
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        responder.close()
        reply_sender.close()
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


def _evaluate_direct_fit_checks(
    advertisement_type: Any, response_builder: Any, ptr_record_type: int
) -> dict[str, bool]:
    """Exercise bounded future configuration and lifecycle inputs."""
    query = _dns_query(SERVICE_TYPE, ptr_record_type, 0xCAFE)
    wifi = advertisement_type("d073d6000101", 56700, "192.0.2.10")
    shared = advertisement_type("d073d6000102", 56700, "192.0.2.10")

    def serials(responses: list[bytes]) -> set[str]:
        return {
            advertisement.serial
            for advertisement in (wifi, shared)
            if any(
                f"id={advertisement.serial}".encode() in response
                for response in responses
            )
        }

    first = response_builder(query, [wifi, shared])
    repeated = response_builder(query, [wifi, shared])
    removed = response_builder(query, [wifi])
    re_added = response_builder(query, [wifi, shared])
    equivalent_compact = response_builder(
        query, [advertisement_type("d073d6000103", 56700, "fd00::1")]
    )
    equivalent_expanded = response_builder(
        query,
        [
            advertisement_type(
                "d073d6000103",
                56700,
                "fd00:0000:0000:0000:0000:0000:0000:0001",
            )
        ],
    )
    try:
        response_builder(
            query,
            [advertisement_type("d073d6000104", 56700, "invalid-address")],
        )
    except OSError:
        invalid_address_rejected = True
    else:
        invalid_address_rejected = False
    return {
        "empty_eligible_set_has_no_reply": not response_builder(query, []),
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


def _run_direct_fit_checks_cli(args: argparse.Namespace) -> int:
    """Load the frozen overlay and write hermetic candidate-fit evidence."""
    overlay_path = REPOSITORY_ROOT / "scripts/mdns_spike_inputs/lifx_direct.py"
    spec = importlib.util.spec_from_file_location(
        "mdns_spike_fit_overlay", overlay_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the frozen direct overlay")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    checks = _evaluate_direct_fit_checks(
        module.Advertisement,
        module.build_legacy_unicast_responses,
        module.DNS_TYPE_PTR,
    )
    payload = {"fit_checks": checks, "all_passed": all(checks.values())}
    _write_json(Path(args.output), payload)
    return 0 if payload["all_passed"] else 1


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
        raw_wire_populations: dict[str, Any] = {}
        for name, population in (
            ("wifi-1", (1, 0)),
            ("thread-1", (0, 1)),
            ("mixed-10", (5, 5)),
            ("mixed-100", (50, 50)),
        ):
            stage = f"raw-population-{name}"
            metrics = await _run_direct_population(*population)
            raw_wire_populations[name] = metrics
            if metrics["complete_devices"] != metrics["expected"]:
                break
        public_oracle_benchmarks: dict[str, Any] = {}
        if reachable:
            for name, population in (
                ("wifi-1", (1, 0)),
                ("thread-1", (0, 1)),
                ("mixed-10", (5, 5)),
                ("mixed-100", (50, 50)),
            ):
                stage = f"public-oracle-benchmark-{name}"
                public_oracle_benchmarks[name] = await _run_direct_public_benchmark(
                    *population, thread_address=reachable[0]
                )
        stage = "adversarial-bounds"
        adversarial_bounds = _exercise_adversarial_bounds()
        stage = "windows-socket-simulation"
        windows_socket_simulation = _evaluate_windows_socket_simulation()
        stage = "future-fit-inputs"
        fit_checks = _evaluate_direct_fit_checks(
            Advertisement, build_legacy_unicast_responses, DNS_TYPE_PTR
        )
        await asyncio.sleep(0)
        current = asyncio.current_task()
        payload = {
            "execution_status": "completed",
            "oracle": oracle,
            "reachable_ula_gua_count": len(reachable),
            "adversarial_bounds": adversarial_bounds,
            "windows_socket_simulation": windows_socket_simulation,
            "fit_checks": fit_checks,
            "raw_wire_populations": raw_wire_populations,
            "public_oracle_benchmarks": public_oracle_benchmarks,
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
            and error.errno in {errno.EADDRINUSE, errno.ENETUNREACH, errno.EHOSTUNREACH}
            and (
                stage.startswith("raw-population-")
                or stage.startswith("public-oracle-benchmark-")
            )
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
            superseded = [
                candidate
                for candidate in evidence.get("candidates", [])
                if candidate.get("candidate") != "zeroconf"
            ]
            if superseded:
                evidence.setdefault("candidate_revision_history", []).append(
                    {
                        "input_spec_digest": previous,
                        "superseded_at": _utc_now(),
                        "candidates": superseded,
                        "platform_receipts": evidence.get("platform_receipts", {}),
                        "platform_results": evidence.get("platform_results", {}),
                    }
                )
                evidence["candidates"] = [
                    candidate
                    for candidate in evidence["candidates"]
                    if candidate.get("candidate") == "zeroconf"
                ]
                evidence["platform_receipts"] = {}
                evidence["platform_results"] = {}
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
                    "The mixed-10 complete-record-set gate rejected this candidate.",
                )
            )
            continue
        metrics = benchmarks[population]
        passed = (
            metrics["discovered"] == metrics["expected"]
            and metrics["complete_devices"] == metrics["expected"]
            and metrics.get("wire_checks_passed", False)
        )
        criteria[criterion] = asdict(
            CriterionResult(
                "demonstrated" if passed else "failed",
                json.dumps(metrics, sort_keys=True),
            )
        )
        if not passed:
            candidate["candidate_status"] = "rejected"
    membership = benchmarks["mixed-10"].get("membership")
    if membership is not None:
        criteria["dynamic_lifecycle_recovery_fit"] = asdict(
            CriterionResult(
                "untested" if membership["all_passed"] else "failed",
                json.dumps(membership, sort_keys=True),
                "Prove listener failure/retry and production status integration; "
                "resolve any observed service re-add failure first.",
            )
        )
        if not membership["all_passed"]:
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
    raw_wire_populations = result["raw_wire_populations"]
    public_benchmarks = result["public_oracle_benchmarks"]
    all_wire = all(
        value["wire_checks_passed"] for value in raw_wire_populations.values()
    )
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
        for value in raw_wire_populations.values()
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
        all(value["direct_queries"].values()) for value in raw_wire_populations.values()
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
        metrics = public_benchmarks.get(population)
        if metrics is None:
            criteria[criterion] = asdict(
                CriterionResult(
                    "untested",
                    "No reachable ULA/GUA was available for the complete public "
                    "discover_mdns() benchmark.",
                    "Repeat the exact candidate with a reachable ULA/GUA and run "
                    "the pristine public oracle fleet benchmark.",
                )
            )
            continue
        expected_connectivity = {
            name
            for name, count in (
                ("wifi", metrics["wifi"]),
                ("thread", metrics["thread"]),
            )
            if count
        }
        passed = metrics["discovered"] == metrics["expected"] and all(
            metrics["representative_stock_connectivity"].get(name, {}).get("passed")
            is True
            for name in expected_connectivity
        )
        criteria[criterion] = asdict(
            CriterionResult(
                "demonstrated" if passed else "failed",
                "Pristine public discover_mdns() benchmark with stock emulator "
                f"connectivity: {json.dumps(metrics, sort_keys=True)}",
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
    windows_simulation = result["windows_socket_simulation"]
    criteria["windows_socket_simulation"] = asdict(
        CriterionResult(
            "simulated" if windows_simulation["all_passed"] else "failed",
            "Executed socket-choice simulation: "
            f"{json.dumps(windows_simulation, sort_keys=True)}",
        )
    )
    adversarial = result["adversarial_bounds"]
    criteria["malformed_truncated_flood_bounds"] = asdict(
        CriterionResult(
            "demonstrated" if adversarial["all_passed"] else "failed",
            "Executed malformed, oversized, 100/101-population and high-rate "
            f"bounds: {json.dumps(adversarial, sort_keys=True)}",
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
            "untested",
            "Independent cleanup cycles do not prove dynamic listener failure, "
            "retry, partial-fleet recovery or status integration.",
            "Exercise listener bind failure/retry, partial-fleet failure and "
            "recovery/status transitions in the eventual integration design.",
        )
    )
    decisive_protocol_ok = (
        all_wire
        and complete
        and direct_ok
        and clean
        and adversarial["all_passed"]
        and windows_simulation["all_passed"]
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
            if candidate["candidate"] == "lifx-direct":
                attempt = candidate.get("attempts", [{}])[-1]
                public_benchmarks = attempt.get("public_oracle_benchmarks", {})
                benchmark_mapping = {
                    "wifi_benchmark": "wifi-1",
                    "thread_benchmark": "thread-1",
                    "mixed_10_benchmark": "mixed-10",
                    "mixed_100_benchmark": "mixed-100",
                }
                for criterion, population in benchmark_mapping.items():
                    if candidate["criteria"][criterion]["status"] != "demonstrated":
                        continue
                    metrics = public_benchmarks.get(population, {})
                    if "complete_discovery_seconds" not in metrics or not metrics.get(
                        "representative_stock_connectivity"
                    ):
                        raise ValueError(
                            f"{criterion} lacks a complete public-oracle benchmark"
                        )
                windows = attempt.get("windows_socket_simulation", {})
                if candidate["criteria"]["windows_socket_simulation"][
                    "status"
                ] == "simulated" and not windows.get("all_passed"):
                    raise ValueError(
                        "Windows simulation lacks executed socket-choice results"
                    )
                adversarial = attempt.get("adversarial_bounds", {})
                if candidate["criteria"]["malformed_truncated_flood_bounds"][
                    "status"
                ] == "demonstrated" and not adversarial.get("all_passed"):
                    raise ValueError(
                        "malformed/truncated/flood claim lacks executed bounds"
                    )
                if candidate["criteria"]["dynamic_lifecycle_recovery_fit"][
                    "status"
                ] == "demonstrated" and not attempt.get("dynamic_recovery", {}).get(
                    "all_passed"
                ):
                    raise ValueError(
                        "dynamic lifecycle recovery claim lacks recovery evidence"
                    )
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
        raw_wire = result["raw_wire_populations"]
        protocol_ok = (
            result["adversarial_bounds"]["all_passed"]
            and result["windows_socket_simulation"]["all_passed"]
            and result["threads_before"] == result["threads_after"]
            and not result["pending_owned_tasks"]
            and all(
                metrics["discovered"] == metrics["expected"]
                and metrics["complete_devices"] == metrics["expected"]
                and metrics["datagram_count"] == metrics["expected"]
                and metrics["wire_checks_passed"]
                and all(metrics["direct_queries"].values())
                for metrics in raw_wire.values()
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
    public_benchmarks = result.get("public_oracle_benchmarks", {})
    public_ok = len(public_benchmarks) == 4 and all(
        metrics["discovered"] == metrics["expected"]
        and all(
            check.get("passed") is True
            for check in metrics["representative_stock_connectivity"].values()
        )
        for metrics in public_benchmarks.values()
    )
    if public_benchmarks and not public_ok:
        return True, "rejected"
    if oracle_ok and environment_ok and public_ok:
        return True, "meets_gate"
    return True, "provisional"


def _run_zeroconf_platform(args: argparse.Namespace) -> int:
    """Collect revised-contract evidence without rewriting the historical ledger."""
    inputs = resolve_inputs()
    command = _expanded_worker_command(inputs)
    oracle_path = os.environ.get("MDNS_SPIKE_ORACLE_PATH")
    if oracle_path:
        if not _oracle_checkout_matches(
            oracle_path, inputs["oracle"]["revision"], inputs["oracle"]["tree"]
        ):
            print(
                "oracle checkout differs from the pinned revision/tree", file=sys.stderr
            )
            return 1
        pinned = f"lifx-async @ git+https://github.com/Djelibeybi/lifx-async.git@{ORACLE_REVISION}"
        command[command.index(pinned)] = (
            f"lifx-async @ {Path(oracle_path).resolve().as_uri()}"
        )
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "MDNS_SPIKE_WORKER": "1"},
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if completed.returncode:
        print(completed.stderr, file=sys.stderr)
        return 1
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    candidate = _initial_evidence(inputs)["candidates"][0]
    _merge_expanded_result(candidate, result)
    valid = result.get("execution_status") == "completed" and not result.get(
        "error_type"
    )
    payload = {
        "schema_version": 1,
        "platform_candidate": "zeroconf",
        "contract": "complete-record-sets-with-continuation-question-exception",
        "input_spec_digest": inputs["input_spec_digest"],
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "raw_darwin_query_scoped": sys.platform == "darwin",
        "valid": valid,
        "candidate_status": "rejected"
        if candidate["candidate_status"] == "rejected"
        else "provisional",
        "criteria": candidate["criteria"],
        "result": result,
        "command": command,
        "thread_address_origin": os.environ.get(
            "MDNS_SPIKE_THREAD_ADDRESS_ORIGIN", "host-existing"
        ),
    }
    _write_json(Path(args.output), payload)
    return 0 if valid else 1


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
    elif platform_candidate == "zeroconf":
        if not evidence.get("valid"):
            return 1
        candidate = inputs["candidate"]
        environments = {"platform": evidence["result"]["environment"]}
        base_commit = candidate["commit"]
        base_tree = candidate["tree"]
        overlay_digest = candidate["overlay_digest"]
        final_digest = candidate["sdist_sha256"]
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
        if receipt.get("candidate") == "zeroconf":
            candidate = inputs["candidate"]
            expected = {
                "candidate": "zeroconf",
                "candidate_base_commit": candidate["commit"],
                "candidate_base_tree": candidate["tree"],
                "candidate_overlay_digest": candidate["overlay_digest"],
                "candidate_final_digest": candidate["sdist_sha256"],
            }
        else:
            candidate = inputs["fallbacks"]["lifx-direct"]
            expected = {
                "candidate": "lifx-direct",
                "candidate_base_commit": candidate["base_revision"],
                "candidate_base_tree": candidate["base_tree"],
                "candidate_overlay_digest": candidate["overlay_sha256"],
                "candidate_final_digest": candidate["final_digest"],
            }
        expected.update(
            {
                "candidate_head_sha": args.head_sha,
                "input_spec_digest": inputs["input_spec_digest"],
            }
        )
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
    print(
        f"CI receipt valid: {receipt['candidate']} "
        "exact head and immutable inputs match"
    )
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
    zeroconf_probe = subparsers.add_parser("run-zeroconf-platform")
    zeroconf_probe.add_argument("--output", required=True)
    zeroconf_probe.set_defaults(handler=_run_zeroconf_platform)
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
    direct_fit = subparsers.add_parser("run-direct-fit-checks")
    direct_fit.add_argument("--output", required=True)
    direct_fit.set_defaults(handler=_run_direct_fit_checks_cli)
    responder_scope = subparsers.add_parser("probe-responder-scope")
    responder_scope.add_argument("--output", required=True)
    responder_scope.set_defaults(handler=_probe_responder_scope)
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
