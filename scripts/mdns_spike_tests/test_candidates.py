"""Focused tests for the Phase 3 mDNS candidate evidence harness."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
HARNESS = REPOSITORY_ROOT / "scripts" / "spike_mdns_candidates.py"


def test_single_wifi_legacy_unicast_tracer() -> None:
    """Require the executable tracer harness before implementation begins."""
    assert HARNESS.is_file(), (
        "the mDNS spike harness must exist before the WiFi legacy-unicast "
        "tracer can run"
    )
