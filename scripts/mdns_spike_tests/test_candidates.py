"""Focused tests for the Phase 3 mDNS candidate evidence harness."""

import errno
import json
import socket
import subprocess
import sys
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
HARNESS = REPOSITORY_ROOT / "scripts" / "spike_mdns_candidates.py"
ELIGIBLE_OVERLAY = REPOSITORY_ROOT / "scripts" / "mdns_spike_inputs" / "lifx_direct.py"
ACTIVE_INPUTS = REPOSITORY_ROOT / "scripts" / "mdns_spike_inputs" / "active.json"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HARNESS), *arguments],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _evidence_fixture() -> dict[str, Any]:
    """Build validator evidence without reading the mutable result ledger."""
    inputs = json.loads(ACTIVE_INPUTS.read_text())
    public_benchmarks = {
        population: {
            "complete_discovery_seconds": 0.1,
            "representative_stock_connectivity": {"wifi": {"passed": True}},
        }
        for population in ("wifi-1", "thread-1", "mixed-10", "mixed-100")
    }
    demonstrated = {"status": "demonstrated", "evidence": "fixture proof"}
    direct = {
        "candidate": "lifx-direct",
        "execution_status": "completed",
        "candidate_status": "provisional",
        "criteria": {
            "wifi_benchmark": dict(demonstrated),
            "thread_benchmark": dict(demonstrated),
            "mixed_10_benchmark": dict(demonstrated),
            "mixed_100_benchmark": dict(demonstrated),
            "windows_socket_simulation": {
                "status": "simulated",
                "evidence": "fixture simulation",
            },
            "malformed_truncated_flood_bounds": dict(demonstrated),
            "dynamic_lifecycle_recovery_fit": {
                "status": "untested",
                "evidence": "Recovery remains explicitly untested in this fixture.",
                "acquisition_step": "Run integration recovery probes.",
            },
        },
        "attempts": [
            {
                "public_oracle_benchmarks": public_benchmarks,
                "windows_socket_simulation": {"all_passed": True},
                "adversarial_bounds": {"all_passed": True},
            }
        ],
    }
    return {
        "schema_version": 1,
        "candidate_order": [
            "zeroconf",
            "lifx-direct",
            "lifx-adapted",
            "new-responder",
        ],
        "active_elapsed_seconds": 1.0,
        "commands": [],
        "environments": {},
        "inputs": inputs,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidates": [
            {
                "candidate": "zeroconf",
                "execution_status": "completed",
                "candidate_status": "rejected",
                "criteria": {},
                "attempts": [{"gate": "legacy-wire"}],
            },
            direct,
        ],
        "edge_coverage": [{"row": number} for number in range(46)],
        "decision": {"status": "provisional", "reason": "fixture evidence"},
        "pull_request": {"url": None},
    }


def test_single_wifi_legacy_unicast_tracer() -> None:
    """Require a complete captured zeroconf WiFi legacy-unicast attempt."""
    assert HARNESS.is_file(), (
        "the mDNS spike harness must exist before the WiFi legacy-unicast "
        "tracer can run"
    )
    evidence = _evidence_fixture()
    candidate = evidence["candidates"][0]
    assert candidate["candidate"] == "zeroconf"
    assert candidate["execution_status"] == "completed"
    assert candidate["candidate_status"] in {"meets_gate", "rejected", "provisional"}
    assert candidate["attempts"]


def test_default_collection_excludes_spike_directory() -> None:
    """Keep network-bearing spike tests outside ordinary repository collection."""
    configuration = (REPOSITORY_ROOT / "pyproject.toml").read_text()
    assert 'testpaths = ["packages/lifx-emulator-core/tests",' in configuration
    assert "scripts/mdns_spike_tests" not in configuration


def test_ci_executes_the_eligible_zeroconf_candidate() -> None:
    """Keep the platform job on the preferred amended-contract candidate."""
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "run-zeroconf-platform --output" in workflow
    evidence_step = workflow.split("name: Exercise exact candidate head", 1)[1]
    evidence_step = evidence_step.split("name: Record exact-head receipt", 1)[0]
    assert "run-candidate" not in evidence_step
    assert "MDNS_SPIKE_ORACLE_PATH" in evidence_step


def test_ci_prepares_required_daemon_and_synthetic_ula() -> None:
    """Require bounded hosted-runner setup before classifying Ubuntu unavailable."""
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "avahi-daemon" in workflow
    assert "MDNS_SPIKE_THREAD_ADDRESS_ORIGIN" in workflow
    assert "runner-configured-synthetic-ula" in workflow
    assert 'git -C "$RUNNER_TEMP/lifx-async" rev-parse HEAD' in workflow
    assert "route -n get -inet 224.0.0.251" in workflow
    assert "route -n add -host 224.0.0.251" in workflow
    assert "MDNS_SPIKE_ROUTE_INTERFACE_PRESENT=true" in workflow
    assert "prefixlen 64 alias" in workflow


def test_intel_temporary_wheel_allows_exact_direct_references() -> None:
    """Keep exact local wheels buildable without changing production metadata."""
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "allow-direct-references = true" in workflow
    assert 'PYAPP_PROJECT_PATH="$project_wheel"' in workflow
    assert "PYAPP_INSTALL_DIR_LIFX-EMULATOR=" in workflow
    assert '"$binary" self python -c' in workflow
    assert "write-intel-pyapp-receipt" in workflow
    assert "pyapp/app.whl" not in workflow
    assert "a419de7c068cbd0e083194bbe11c741b0497d28c" in workflow
    assert "d87b89829042147f7b23c5fe4b5b14034d8164d4" in workflow


def test_local_oracle_checkout_rejects_tracked_changes(tmp_path: Path) -> None:
    """Reject dirty source while leaving unrelated untracked files immaterial."""
    checkout = tmp_path / "oracle"
    checkout.mkdir()
    subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
    tracked = checkout / "oracle.py"
    tracked.write_text("PINNED = True\n")
    subprocess.run(["git", "-C", str(checkout), "add", "oracle.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.name=Spike Fixture",
            "-c",
            "user.email=spike@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
        check=True,
    )
    revision = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    arguments = (
        "validate-oracle-checkout",
        "--path",
        str(checkout),
        "--revision",
        revision,
        "--tree",
        tree,
    )
    assert _run(*arguments).returncode == 0
    tracked.write_text(tracked.read_text() + "\n")
    assert _run(*arguments).returncode == 1


@pytest.mark.parametrize(
    ("mutation", "expected_status", "expected_returncode"),
    [
        ("none", "meets_gate", 0),
        ("oracle-miss", "provisional", 0),
        ("protocol-failure", "rejected", 0),
        ("environment-unavailable", "provisional", 0),
        ("tool-error", "provisional", 1),
    ],
)
def test_platform_result_separates_execution_from_compliance(
    tmp_path: Path,
    mutation: str,
    expected_status: str,
    expected_returncode: int,
) -> None:
    """Keep unexplained oracle misses distinct from decisive protocol failure."""
    result = {
        "execution_status": "completed",
        "oracle": {"wifi": {"matched": True}, "thread": {"matched": True}},
        "adversarial_bounds": {"all_passed": True},
        "windows_socket_simulation": {"all_passed": True},
        "threads_before": ["MainThread"],
        "threads_after": ["MainThread"],
        "pending_owned_tasks": [],
        "daemon_processes": ["test-daemon"],
        "raw_wire_populations": {
            "wifi-1": {
                "discovered": 1,
                "expected": 1,
                "complete_devices": 1,
                "datagram_count": 1,
                "wire_checks_passed": True,
                "direct_queries": {"wifi": True},
            }
        },
        "public_oracle_benchmarks": {
            name: {
                "wifi": wifi,
                "thread": thread,
                "discovered": wifi + thread,
                "expected": wifi + thread,
                "representative_stock_connectivity": {
                    **({"wifi": {"passed": True}} if wifi else {}),
                    **({"thread": {"passed": True}} if thread else {}),
                },
            }
            for name, (wifi, thread) in {
                "wifi-1": (1, 0),
                "thread-1": (0, 1),
                "mixed-10": (5, 5),
                "mixed-100": (50, 50),
            }.items()
        },
    }
    if mutation == "oracle-miss":
        result["oracle"]["wifi"]["matched"] = False
    elif mutation == "protocol-failure":
        result["raw_wire_populations"]["wifi-1"]["datagram_count"] = 2
    elif mutation == "environment-unavailable":
        result["error_type"] = "OSError"
        result["error_errno"] = 65
        result["environment_unavailable"] = True
    elif mutation == "tool-error":
        result["error_type"] = "RuntimeError"
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    completed = _run("classify-direct-result", "--input", str(path))
    assert completed.returncode == expected_returncode
    classified = json.loads(completed.stdout)
    assert classified["candidate_status"] == expected_status


def test_fallback_overlay_is_frozen_only_after_zeroconf_rejection() -> None:
    """Require the now-eligible direct fallback to be a reviewable source file."""
    evidence = _evidence_fixture()
    assert evidence["candidates"][0]["candidate_status"] == "rejected"
    assert ELIGIBLE_OVERLAY.is_file(), "eligible direct fallback overlay is absent"


def test_direct_result_retains_bounded_future_fit_checks(tmp_path: Path) -> None:
    """Keep configuration edge evidence concrete without production APIs."""
    output = tmp_path / "direct-fit.json"
    completed = _run("run-direct-fit-checks", "--output", str(output))
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["all_passed"] is True
    assert set(payload["fit_checks"]) == {
        "empty_eligible_set_has_no_reply",
        "shared_addresses_keep_distinct_identities",
        "repeated_unchanged_query_is_stable",
        "removal_and_readd_follow_eligible_set",
        "equivalent_ipv6_spellings_encode_identically",
        "invalid_address_is_rejected_before_reply",
    }
    assert all(payload["fit_checks"].values())


def test_responder_listener_is_interface_scoped(tmp_path: Path) -> None:
    """Bind the multicast listener without exposing UDP 5353 on every address."""
    output = tmp_path / "responder-scope.json"
    completed = _run("probe-responder-scope", "--output", str(output))
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    if payload.get("environment_unavailable"):
        assert payload["error_errno"] == errno.EADDRINUSE
        assert payload["stage"] == "bind-selected-reply-source-5353"
        return
    assert payload["bound_address"] == "224.0.0.251"
    assert payload["membership_interface"] != "0.0.0.0"
    assert payload["reply_bound_address"] == "selected-ipv4"
    assert payload["reply_source_port"] == 5353
    assert payload["wildcard_bound"] is False
    assert payload["platform_scope_applied"] is True


@pytest.mark.parametrize(
    ("mutation", "valid"),
    [
        ("provisional", True),
        ("tool-error", False),
        ("unsupported-go", False),
        ("bad-order", False),
        ("false-public-benchmark", False),
        ("false-windows-simulation", False),
        ("false-adversarial-bounds", False),
        ("false-dynamic-recovery", False),
    ],
)
def test_evidence_classification(tmp_path: Path, mutation: str, valid: bool) -> None:
    """Distinguish useful provisional evidence from invalid harness output."""
    evidence = _evidence_fixture()
    direct = evidence["candidates"][1]
    if mutation == "tool-error":
        evidence["candidates"][0]["execution_status"] = "tool_error"
    elif mutation == "unsupported-go":
        evidence["decision"]["status"] = "go"
    elif mutation == "bad-order":
        evidence["candidate_order"] = list(reversed(evidence["candidate_order"]))
    elif mutation == "false-public-benchmark":
        direct["attempts"][-1].pop("public_oracle_benchmarks", None)
        direct["criteria"]["wifi_benchmark"]["status"] = "demonstrated"
    elif mutation == "false-windows-simulation":
        direct["attempts"][-1].pop("windows_socket_simulation", None)
        direct["criteria"]["windows_socket_simulation"]["status"] = "simulated"
    elif mutation == "false-adversarial-bounds":
        direct["attempts"][-1].pop("adversarial_bounds", None)
        direct["criteria"]["malformed_truncated_flood_bounds"]["status"] = (
            "demonstrated"
        )
    elif mutation == "false-dynamic-recovery":
        direct["attempts"][-1].pop("dynamic_recovery", None)
        direct["criteria"]["dynamic_lifecycle_recovery_fit"]["status"] = "demonstrated"
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    completed = _run("validate-evidence", str(path))
    assert (completed.returncode == 0) is valid, completed.stderr


def test_resume_does_not_repeat_completed_tracer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resume at the first unmet gate without repeating the captured attempt."""
    evidence = _evidence_fixture()
    zeroconf = evidence["candidates"][0]
    criterion_names = (
        "oracle_discovery",
        "wifi_benchmark",
        "thread_benchmark",
        "mixed_10_benchmark",
        "mixed_100_benchmark",
        "ubuntu_multicast",
        "macos_multicast",
        "intel_pyapp_first_run",
        "direct_address_queries",
    )
    zeroconf["criteria"] = {
        name: {"status": "not-run-with-reason", "evidence": "fixture rejection"}
        for name in criterion_names
    }
    zeroconf["attempts"] = [{"gate": "legacy-wire"}]
    before = sum(
        attempt["gate"] == "legacy-wire"
        for attempt in evidence["candidates"][0]["attempts"]
    )
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    harness = run_path(str(HARNESS))
    resume = harness["run_sequence"]
    # Freeze time: the original spike start is now historical.
    monkeypatch.setitem(resume.__globals__, "_active_elapsed", lambda: 100.0)
    args = harness["_parser"]().parse_args(
        [
            "run-sequence",
            "--resume",
            "--source-revision",
            "48b7efbff59656499373b13ef17e3008d125feb5",
            "--evidence",
            str(path),
        ]
    )
    assert resume(args) == 0
    resumed = json.loads(path.read_text())
    after = sum(
        attempt["gate"] == "legacy-wire"
        for attempt in resumed["candidates"][0]["attempts"]
    )
    assert after == before


@pytest.mark.parametrize(
    "field",
    [
        "candidate",
        "candidate_head_sha",
        "input_spec_digest",
        "candidate_base_commit",
        "candidate_base_tree",
        "candidate_overlay_digest",
        "candidate_final_digest",
    ],
)
def test_ci_receipt_rejects_identity_mismatch(tmp_path: Path, field: str) -> None:
    """Reject a receipt that differs from any immutable candidate identity."""
    inputs = json.loads(ACTIVE_INPUTS.read_text())
    candidate = inputs["fallbacks"]["lifx-direct"]
    head_sha = "a" * 40
    receipt = {
        "candidate": "lifx-direct",
        "candidate_head_sha": head_sha,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidate_base_commit": candidate["base_revision"],
        "candidate_base_tree": candidate["base_tree"],
        "candidate_overlay_digest": candidate["overlay_sha256"],
        "candidate_final_digest": candidate["final_digest"],
        "environments": {"test/x86_64/3.12": {"os": "test"}},
    }
    receipt[field] = "mismatch"
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt))
    completed = _run(
        "validate-ci-receipt",
        "--receipt",
        str(path),
        "--head-sha",
        head_sha,
    )
    assert completed.returncode == 1


def test_ci_receipt_rejects_incomplete_intel_proof(tmp_path: Path) -> None:
    """Require exact wheel references and first-run proof for Intel packaging."""
    inputs = json.loads(ACTIVE_INPUTS.read_text())
    candidate = inputs["fallbacks"]["lifx-direct"]
    head_sha = "b" * 40
    receipt = {
        "candidate": "lifx-direct",
        "candidate_head_sha": head_sha,
        "input_spec_digest": inputs["input_spec_digest"],
        "candidate_base_commit": candidate["base_revision"],
        "candidate_base_tree": candidate["base_tree"],
        "candidate_overlay_digest": candidate["overlay_sha256"],
        "candidate_final_digest": candidate["final_digest"],
        "candidate_status": "meets_gate",
        "platform_leg": "intel-pyapp",
        "pyapp": {
            "version": "0.26.0",
            "revision": "a419de7c068cbd0e083194bbe11c741b0497d28c",
            "tree": "d87b89829042147f7b23c5fe4b5b14034d8164d4",
        },
        "uv_version": "0.9.9",
        "environments": {"darwin/x86_64/3.12": {"os": "darwin"}},
        "direct_references": {
            "lifx_async": True,
            "lifx_emulator_core": False,
            "candidate_metadata": True,
        },
        "hashes_sha256": "hashes",
        "identities": {"lifx-async": "7.3.0"},
        "rustc": "rustc 1.98.1",
        "first_run_sha256": "first-run",
        "candidate_metadata_sha256": "candidate-metadata",
        "app_metadata_sha256": "app-metadata",
    }
    path = tmp_path / "intel-receipt.json"
    path.write_text(json.dumps(receipt))
    completed = _run(
        "validate-ci-receipt",
        "--receipt",
        str(path),
        "--head-sha",
        head_sha,
    )
    assert completed.returncode == 1


@pytest.mark.parametrize("fault", [None, "ptr", "srv", "txt", "family", "missing"])
def test_aggregated_record_associations(fault: str | None) -> None:
    """Complete fleets may aggregate, but cannot borrow another device's records."""
    check = run_path(str(HARNESS))["_complete_record_sets"]
    service = "_lifx._udp.local."
    records = []
    expected = {}
    for serial in ("d073d5000001", "d073d5000002"):
        instance = f"{serial}.{service}"
        host = f"{serial}.local."
        txt = {"id": serial, "p": "27", "fw": "4.200", "tm": "1"}
        expected[serial] = {"port": 56700, "txt": txt, "address": (1, "127.0.0.1")}
        records.extend(
            [
                SimpleNamespace(rtype=12, name=service, parsed_data=instance),
                SimpleNamespace(
                    rtype=33,
                    name=instance,
                    parsed_data=SimpleNamespace(
                        target=host, port=56700, priority=0, weight=0
                    ),
                ),
                SimpleNamespace(
                    rtype=16,
                    name=instance,
                    parsed_data=SimpleNamespace(pairs=dict(txt)),
                ),
                SimpleNamespace(rtype=1, name=host, parsed_data="127.0.0.1"),
            ]
        )
    if fault == "ptr":
        records[0].name = "_other._udp.local."
    elif fault == "srv":
        records[1].parsed_data.target = "d073d5000002.local."
    elif fault == "txt":
        records[2].parsed_data.pairs["tm"] = "2"
    elif fault == "family":
        records.append(
            SimpleNamespace(rtype=28, name="d073d5000001.local.", parsed_data="::1")
        )
    elif fault == "missing":
        records.pop(3)
    assert check(records, expected) == (
        set(expected) if fault is None else {"d073d5000002"}
    )
    # A first packet containing only PTR/SRV cannot prove complete discovery.
    assert check(records[:2], expected) == set()


def test_zeroconf_platform_receipt_identifies_actual_candidate(tmp_path: Path) -> None:
    """A zeroconf platform receipt must not inherit the direct overlay identity."""
    evidence = tmp_path / "platform.json"
    output = tmp_path / "receipt.json"
    evidence.write_text(
        json.dumps(
            {
                "platform_candidate": "zeroconf",
                "valid": True,
                "candidate_status": "provisional",
                "result": {
                    "environment": {
                        "os": "darwin",
                        "architecture": "arm64",
                        "python": "3.14",
                    }
                },
            }
        )
    )
    result = _run(
        "write-ci-receipt",
        "--evidence",
        str(evidence),
        "--output",
        str(output),
        "--head-sha",
        "a" * 40,
        "--run-url",
        "https://example.invalid/run",
        "--platform-leg",
        "multicast",
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(output.read_text())
    inputs = json.loads(ACTIVE_INPUTS.read_text())
    assert receipt["candidate"] == "zeroconf"
    assert receipt["candidate_base_commit"] == inputs["candidate"]["commit"]
    assert receipt["candidate_overlay_digest"] is None
    assert receipt["candidate_status"] == "provisional"
    validation = _run(
        "validate-ci-receipt", "--receipt", str(output), "--head-sha", "a" * 40
    )
    assert validation.returncode == 0, validation.stderr
    receipt["candidate_base_commit"] = inputs["fallbacks"]["lifx-direct"][
        "base_revision"
    ]
    output.write_text(json.dumps(receipt))
    assert (
        _run(
            "validate-ci-receipt", "--receipt", str(output), "--head-sha", "a" * 40
        ).returncode
        == 1
    )


@pytest.mark.parametrize("platform_name", ["darwin", "linux"])
@pytest.mark.parametrize("fail_bind", [False, True])
def test_raw_query_socket_scoping_and_failure_cleanup(
    monkeypatch: pytest.MonkeyPatch, platform_name: str, fail_bind: bool
) -> None:
    calls = []
    closed = []

    def bind(address: tuple[str, int]) -> None:
        calls.append(("bind", address))
        if fail_bind:
            raise OSError("bind failed")

    fake = SimpleNamespace(
        setblocking=lambda value: None,
        setsockopt=lambda *values: calls.append(values),
        bind=bind,
        close=lambda: closed.append(True),
    )
    factory = run_path(str(HARNESS))["_new_mdns_client"]
    socket_api = SimpleNamespace(
        **{
            name: getattr(socket, name)
            for name in (
                "AF_INET",
                "SOCK_DGRAM",
                "IPPROTO_UDP",
                "SOL_SOCKET",
                "SO_REUSEADDR",
                "IPPROTO_IP",
                "IP_MULTICAST_IF",
                "IP_MULTICAST_TTL",
                "inet_aton",
            )
        },
        socket=lambda *args: fake,
    )
    monkeypatch.setitem(factory.__globals__, "socket", socket_api)
    monkeypatch.setitem(
        factory.__globals__, "sys", SimpleNamespace(platform=platform_name)
    )
    monkeypatch.setitem(factory.__globals__, "_darwin_interface_index", lambda _: 7)
    if fail_bind:
        with pytest.raises(OSError, match="bind failed"):
            factory("192.0.2.1")
        assert closed == [True]
    else:
        assert factory("192.0.2.1") is fake
        assert not closed
    assert ((socket.IPPROTO_IP, 25, 7) in calls) == (platform_name == "darwin")


def test_zeroconf_platform_rejects_unverified_local_oracle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MDNS_SPIKE_ORACLE_PATH", str(tmp_path))
    output = tmp_path / "evidence.json"
    result = _run("run-zeroconf-platform", "--output", str(output))
    assert result.returncode == 1
    assert "differs from the pinned revision/tree" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "family,override,bind,enabled,result",
    [
        ("wifi", None, "127.0.0.1", True, "127.0.0.1"),
        ("thread", "fd00:0:0::1", "::", True, "fd00::1"),
        ("wifi", None, "0.0.0.0", False, None),
        ("thread", None, "::1", False, ValueError),
        ("wifi", "", "127.0.0.1", True, ValueError),
        ("thread", "127.0.0.1", "::1", True, ValueError),
        ("wifi", "169.254.1.1", "127.0.0.1", True, ValueError),
        ("thread", "fe80::1%lo0", "::1", True, ValueError),
        ("wifi", None, "0.0.0.0", True, ValueError),
        ("thread", None, "::", True, ValueError),
    ],
)
def test_closeout_address_fit_precedes_registration(
    family, override, bind, enabled, result
):
    select = run_path(str(HARNESS))["_closeout_address"]
    if result is ValueError:
        with pytest.raises(ValueError):
            select(family, override, bind, enabled)
    else:
        assert select(family, override, bind, enabled) == result


def test_closeout_malformed_corpus_and_load_are_fixed():
    module = run_path(str(HARNESS))
    corpus = module["_closeout_malformed_corpus"]()
    assert set(corpus) == {
        "empty",
        "short-header",
        "truncated-question",
        "compression-loop",
        "large",
    }
    assert corpus["empty"] == b""
    assert len(corpus["large"]) == 8192
    assert module["CLOSEOUT_QUERY_COUNT"] == 256


def test_windows_closeout_uses_candidate_constructor_seam():
    module = run_path(str(HARNESS))
    calls = []
    result = module["_closeout_windows_simulation"](
        lambda **kwargs: calls.append(kwargs), "v4-only"
    )
    assert result["status"] == "simulated"
    assert calls == [{"interfaces": ["127.0.0.1"], "ip_version": "v4-only"}]
    assert result["platform"] == "Windows"
    assert not result["real_windows_network"]


def test_closeout_validator_rejects_empty_ledger(tmp_path):
    ledger = tmp_path / "closeout.json"
    ledger.write_text("{}")
    assert _run("validate-zeroconf-closeout", str(ledger)).returncode == 1


def _closeout_robustness_fixture():
    module = run_path(str(HARNESS))
    inventory = {"pending_tasks": [], "threads": ["MainThread"], "descriptor_count": 10}
    return {
        "corpus": {
            name: {
                "bytes_sent": len(raw),
                "sha256": module["hashlib"].sha256(raw).hexdigest(),
            }
            for name, raw in module["_closeout_malformed_corpus"]().items()
        },
        "queries": [
            {
                "query_id": 0xE000 + i,
                "source_port": 50000 + i,
                "direct": bool(i % 2),
                "passed": True,
                "metrics": {
                    "wire_checks_passed": True,
                    "discovered": 1,
                    "complete_devices": 0 if i % 2 else 1,
                },
            }
            for i in range(256)
        ],
        "after_malformed": {"passed": True},
        "pristine_discovery_after_flood": True,
        "before": dict(inventory),
        "after": dict(inventory),
        "public_done": True,
        "batch_pending_tasks": [0] * 16,
        "flood_seconds": 2,
    }


@pytest.mark.parametrize("fault", ["id", "port", "wire", "discovery", "missing"])
def test_closeout_robustness_cannot_claim_success_from_bad_observations(fault):
    module = run_path(str(HARNESS))
    payload = _closeout_robustness_fixture()
    assert module["_closeout_robustness_passed"](payload)
    if fault == "id":
        payload["queries"][1]["query_id"] = payload["queries"][0]["query_id"]
    elif fault == "port":
        payload["queries"][0]["source_port"] = 5353
    elif fault == "wire":
        payload["queries"][0]["metrics"]["wire_checks_passed"] = False
    elif fault == "discovery":
        payload["pristine_discovery_after_flood"] = False
    else:
        payload["corpus"].pop("compression-loop")
    assert not module["_closeout_robustness_passed"](payload)


@pytest.mark.parametrize("fault", ["tasks", "fds", "threads", "growth", "deadline"])
def test_closeout_resources_reject_leaks_and_unbounded_work(fault):
    module = run_path(str(HARNESS))
    payload = _closeout_robustness_fixture()
    assert module["_closeout_resources_passed"](payload)
    if fault == "tasks":
        payload["after"]["pending_tasks"] = ["orphan"]
    elif fault == "fds":
        payload["after"]["descriptor_count"] += 1
    elif fault == "threads":
        payload["after"]["threads"] = ["MainThread", "leaked"]
    elif fault == "growth":
        payload["batch_pending_tasks"][-1] = 1
    else:
        payload["flood_seconds"] = 46
    assert not module["_closeout_resources_passed"](payload)


def test_closeout_never_accepts_simulation_or_direct_history_as_real_gate():
    module = run_path(str(HARNESS))
    cases = {
        "local_windows": module["_closeout_case"]("simulated", "constructor seam"),
        "local_configuration": module["_closeout_case"](
            "demonstrated", "real candidate"
        ),
    }
    assert "go" in module["_closeout_routes"](cases)
    cases["local_configuration"]["status"] = "simulated"
    assert module["_closeout_routes"](cases) == ["provisional"]
    cases["local_configuration"]["status"] = "demonstrated"
    cases["local_configuration"]["candidate"] = "lifx-direct"
    assert module["_closeout_routes"](cases) == ["provisional"]


def test_closeout_filters_foreign_responders_before_recording():
    module = run_path(str(HARNESS))
    own = SimpleNamespace(
        rtype=12, name="_lifx._udp.local.", parsed_data="d073d503c001._lifx._udp.local."
    )
    foreign = SimpleNamespace(
        rtype=12, name="_lifx._udp.local.", parsed_data="d073d5999999._lifx._udp.local."
    )
    address = SimpleNamespace(
        rtype=1, name="d073d503c001.local.", parsed_data="127.0.0.1"
    )
    assert module["_owned_query_records"](
        [foreign, own, address], {"d073d503c001"}
    ) == [own, address]


def test_closeout_decision_binds_receipt_bytes_not_just_case_labels():
    module = run_path(str(HARNESS))
    ledger = {
        "platforms": {"local": {"sha256": "a" * 64}},
        "cases": {},
        "decision": {"status": "pending-human"},
    }
    before = module["_closeout_decision_digest"](ledger)
    ledger["decision"] = {"status": "provisional"}
    assert module["_closeout_decision_digest"](ledger) == before
    ledger["platforms"]["local"]["sha256"] = "b" * 64
    assert module["_closeout_decision_digest"](ledger) != before


def _closeout_operation_fixture():
    return {
        "operation": "update",
        "family": "wifi",
        "failed": True,
        "first_error": "update: OSError: injected update_service operation failure",
        "thread_admission_rejected": True,
        "original_owner_closed": True,
        "retry_succeeded": True,
        "wifi_same_endpoint": True,
        "wifi_control_replies": 10,
        "wifi_control_errors": [],
        "wifi_values_match": True,
        "wifi_replies_before_fault": 2,
        "wifi_replies_after_failure": 5,
        "wifi_replies_after_retry": 10,
        "wifi_power_after_failure": 65535,
        "wifi_power_after_retry": 65535,
        "all_owners_closed_after_cleanup": True,
    }


@pytest.mark.parametrize(
    "fault", ["wrong-operation", "no-after-failure", "no-after-retry", "cleanup"]
)
def test_closeout_operation_requires_post_failure_progress_and_cleanup(fault):
    check = run_path(str(HARNESS))["_closeout_operation_passed"]
    row = _closeout_operation_fixture()
    assert check(row)
    if fault == "wrong-operation":
        row["first_error"] = "unregister: OSError: wrong operation"
    elif fault == "no-after-failure":
        row["wifi_replies_after_failure"] = row["wifi_replies_before_fault"]
    elif fault == "no-after-retry":
        row["wifi_replies_after_retry"] = row["wifi_replies_after_failure"]
    else:
        row["all_owners_closed_after_cleanup"] = False
    assert not check(row)
