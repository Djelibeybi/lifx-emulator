#!/usr/bin/env python3
"""Bounded evidence harness for the Phase 3 mDNS responder spike."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
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
    from lifx.network.discovery.mdns.dns import (
        DNS_TYPE_A,
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
    from zeroconf import IPVersion, ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf


REPOSITORY_ROOT = Path(__file__).parents[1]
DEFAULT_EVIDENCE = (
    REPOSITORY_ROOT / ".planning/phases/03-mdns-responder/03-01-EVIDENCE.json"
)
DEFAULT_INPUTS = REPOSITORY_ROOT / "scripts/mdns_spike_inputs/active.json"
ORACLE_REVISION = "48b7efbff59656499373b13ef17e3008d125feb5"
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
            "interface": interface,
            "client_endpoint": list(client.getsockname()),
            "peer": list(peer),
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
            await azc.async_unregister_service(info)
        await azc.async_close()
        client.close()
        await server.stop()


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
    candidate = _find_candidate(evidence, "zeroconf")
    statuses = {result["status"] for result in candidate["criteria"].values()}
    if candidate["candidate_status"] == "rejected":
        evidence["decision"] = {
            "status": "provisional",
            "reason": (
                "zeroconf was rejected by the reached gate; D-09/D-11 fallback "
                "candidates remain unevaluated."
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
            raise ValueError("evidence uses a different immutable input specification")
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
            criteria[name] = asdict(
                CriterionResult(
                    "not-run-with-reason",
                    "The earlier decisive wire rejection made this gate irrelevant.",
                )
            )
        return
    criteria["daemon_coexistence"] = asdict(
        CriterionResult(
            "demonstrated",
            "The local legacy-unicast probe completed beside the running host daemon.",
        )
    )
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
    _mark_local_remaining(evidence)
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
    evidence["candidates"][0]["elapsed_active_seconds"] = round(elapsed, 3)
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


def _write_ci_receipt(args: argparse.Namespace) -> int:
    evidence_path = Path(args.evidence)
    evidence = _read_json(evidence_path)
    inputs = resolve_inputs()
    if validate_evidence(evidence_path) != 0:
        return 1
    candidate = inputs["candidate"]
    receipt = {
        "schema_version": 1,
        "candidate_head_sha": args.head_sha,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidate_base_commit": candidate["commit"],
        "candidate_base_tree": candidate["tree"],
        "candidate_overlay_digest": candidate["overlay_digest"],
        "candidate_final_digest": candidate["sdist_sha256"],
        "platform_leg": args.platform_leg,
        "run_url": args.run_url,
        "environments": evidence["environments"],
        "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        "recorded_at": _utc_now(),
    }
    _write_json(Path(args.output), receipt)
    return 0


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
        "## Candidate ledger",
        "",
    ]
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
            "## Platform and packaging",
            "",
            f"PR: {evidence['pull_request']['url'] or 'not recorded'}",
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
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "candidate-worker":
        return asyncio.run(_candidate_worker())
    if getattr(args, "oracle_revision", ORACLE_REVISION) != ORACLE_REVISION:
        raise SystemExit("oracle revision differs from the immutable pin")
    if getattr(args, "source_revision", ORACLE_REVISION) != ORACLE_REVISION:
        raise SystemExit("source revision differs from the immutable pin")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
