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


def test_fallback_overlay_is_frozen_only_after_zeroconf_rejection() -> None:
    """Require the now-eligible direct fallback to be a reviewable source file."""
    evidence = json.loads(EVIDENCE.read_text())
    assert evidence["candidates"][0]["candidate_status"] == "rejected"
    assert ELIGIBLE_OVERLAY.is_file(), "eligible direct fallback overlay is absent"


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
