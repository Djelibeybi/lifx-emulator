"""Acquire the exact pristine client oracle without touching sibling checkouts."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

PINNED_REVISION = "48b7efbff59656499373b13ef17e3008d125feb5"
INPUTS = Path(__file__).parent / "mdns_spike_inputs" / "active.json"


def git(directory: Path, *arguments: str) -> str:
    """Run a bounded git command against only the caller's isolated directory."""
    return subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout.strip()


def prepare(destination: Path) -> None:
    """Fetch and verify an exact revision into a fresh destination."""
    inputs = json.loads(INPUTS.read_text())
    install = inputs["constraints"]["lifx_async_install"]
    prefix = "lifx-async @ git+"
    if not install.startswith(prefix):
        raise ValueError("Oracle install must identify an exact Git source")
    url, revision = install[len(prefix) :].rsplit("@", 1)
    if url != "https://github.com/Djelibeybi/lifx-async.git":
        raise ValueError("Unexpected oracle repository")
    if revision != inputs["oracle"]["revision"] or revision != PINNED_REVISION:
        raise ValueError("Oracle install revision does not match approved revision")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Oracle destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    git(destination, "init")
    git(destination, "remote", "add", "origin", url)
    git(destination, "fetch", "--depth", "1", "origin", revision)
    git(destination, "checkout", "--detach", "FETCH_HEAD")
    if git(destination, "rev-parse", "HEAD") != PINNED_REVISION:
        raise ValueError("Oracle HEAD mismatch")
    if git(destination, "rev-parse", "HEAD^{tree}") != inputs["oracle"]["tree"]:
        raise ValueError("Oracle tree mismatch")
    if git(destination, "status", "--porcelain"):
        raise ValueError("Oracle is not pristine")
    print(f"Verified pristine oracle {revision} at {destination}")


def main() -> None:
    """Prepare the caller-supplied temporary oracle checkout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.destination.resolve())


if __name__ == "__main__":
    main()
