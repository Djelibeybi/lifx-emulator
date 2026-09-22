"""Focused tests for the Phase 3 mDNS candidate evidence harness."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
HARNESS = REPOSITORY_ROOT / "scripts" / "spike_mdns_candidates.py"
ELIGIBLE_OVERLAY = REPOSITORY_ROOT / "scripts" / "mdns_spike_inputs" / "lifx_direct.py"
EVIDENCE = (
    REPOSITORY_ROOT
    / ".planning"
    / "phases"
    / "03-mdns-responder"
    / "03-01-EVIDENCE.json"
)
ACTIVE_INPUTS = REPOSITORY_ROOT / "scripts" / "mdns_spike_inputs" / "active.json"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HARNESS), *arguments],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_single_wifi_legacy_unicast_tracer() -> None:
    """Require a complete captured zeroconf WiFi legacy-unicast attempt."""
    assert HARNESS.is_file(), (
        "the mDNS spike harness must exist before the WiFi legacy-unicast "
        "tracer can run"
    )
    evidence = json.loads(EVIDENCE.read_text())
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


def test_ci_executes_the_eligible_direct_candidate() -> None:
    """Prevent a green platform job from accidentally rerunning zeroconf."""
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "run-direct-platform --output" in workflow
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
    subprocess.run(
        ["git", "clone", "--shared", "--quiet", str(REPOSITORY_ROOT), str(checkout)],
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
    tracked = checkout / "scripts" / "spike_mdns_candidates.py"
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
        "malformed_bounded": True,
        "threads_before": ["MainThread"],
        "threads_after": ["MainThread"],
        "pending_owned_tasks": [],
        "daemon_processes": ["test-daemon"],
        "benchmarks": {
            "wifi-1": {
                "discovered": 1,
                "expected": 1,
                "complete_devices": 1,
                "datagram_count": 1,
                "wire_checks_passed": True,
                "direct_queries": {"wifi": True},
            }
        },
    }
    if mutation == "oracle-miss":
        result["oracle"]["wifi"]["matched"] = False
    elif mutation == "protocol-failure":
        result["benchmarks"]["wifi-1"]["datagram_count"] = 2
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
    evidence = json.loads(EVIDENCE.read_text())
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


@pytest.mark.parametrize(
    ("mutation", "valid"),
    [
        ("provisional", True),
        ("tool-error", False),
        ("unsupported-go", False),
        ("bad-order", False),
    ],
)
def test_evidence_classification(tmp_path: Path, mutation: str, valid: bool) -> None:
    """Distinguish useful provisional evidence from invalid harness output."""
    evidence = json.loads(EVIDENCE.read_text())
    if mutation == "tool-error":
        evidence["candidates"][0]["execution_status"] = "tool_error"
    elif mutation == "unsupported-go":
        evidence["decision"]["status"] = "go"
    elif mutation == "bad-order":
        evidence["candidate_order"] = list(reversed(evidence["candidate_order"]))
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    completed = _run("validate-evidence", str(path))
    assert (completed.returncode == 0) is valid, completed.stderr


def test_resume_does_not_repeat_completed_tracer(tmp_path: Path) -> None:
    """Resume at the first unmet gate without repeating the captured attempt."""
    evidence = json.loads(EVIDENCE.read_text())
    before = sum(
        attempt["gate"] == "legacy-wire"
        for attempt in evidence["candidates"][0]["attempts"]
    )
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence))
    completed = _run(
        "run-sequence",
        "--resume",
        "--source-revision",
        "48b7efbff59656499373b13ef17e3008d125feb5",
        "--evidence",
        str(path),
    )
    assert completed.returncode == 0, completed.stderr
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
