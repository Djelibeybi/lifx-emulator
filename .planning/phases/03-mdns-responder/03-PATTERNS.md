# Phase 3: mDNS Responder - Pattern Map

**Mapped:** 2026-09-22
**Reconciled:** 2026-09-23 against the completed continuation, recovery prototype and amended D-08
**Scope:** MDNS-10 spike closeout only; do not plan responder production changes.
**Historical mapping:** 6 proposed artefacts with analogs for all 6; the closeout addendum also maps the retained recovery and listener-health harnesses.

## Current Closeout Guidance (2026-09-23)

The historical harness restriction was lifted for focused evidence work, and the authorised budgets are exhausted. Zeroconf remains the preferred provisional foundation; do not restart generic candidate exploration, fallback construction, VM work or production integration. Silent listener loss is outside amended D-08, and `running` is lifecycle state rather than independently verified health. No fork, vendoring, private listener access, watchdog or upstream callback is needed for closeout.

| Remaining check | Reuse this existing seam | Do not inherit |
|---|---|---|
| Zeroconf robustness | Extend the existing `candidate-worker --expanded` payload in `scripts/spike_mdns_candidates.py`; add focused assertions in `scripts/mdns_spike_tests/test_candidates.py`. | Direct-prototype `_exercise_adversarial_bounds` results. |
| Zeroconf Windows simulation | Extend `scripts/mdns_spike_tests/test_candidates.py` and retain the evidence validator's explicit `simulated` classification. | The direct responder's generic `_socket_option_plan` result. |
| Configuration/interface fit | Use `run_discovery_benchmark()` and `_expanded_worker()` in `scripts/spike_mdns_candidates.py`, with focused negative cases in `test_candidates.py`. | Production server/factory implementation or automatic interface selection. |
| Final MDNS-10 decision | Use the existing `validate-evidence` and `render-evidence` entry points after the three checks; preserve `03-01-EVIDENCE.*` as historical and record a current closeout decision. | An inferred go from green continuation jobs. |

Recovery work stays in `scripts/mdns_spike_inputs/zeroconf_recovery.py`, `scripts/spike_mdns_recovery.py` and `scripts/mdns_spike_tests/test_recovery.py`. It already covers partial-start cleanup, explicit retry, surfaced-error policy, cancellation and concurrent retry. `scripts/spike_mdns_listener_health.py` is retained negative diagnostic evidence only; do not convert it into a production health detector.

## File Classification

| New/modified file | Role | Data flow | Closest tracked analog | Match |
|---|---|---|---|---|
| `scripts/spike_mdns_candidates.py` | utility / spike harness | datagram, batch | `packages/lifx-emulator-core/tests/test_ipv6_transport.py` | role-match |
| `scripts/mdns_spike_tests/test_candidates.py` | explicitly invoked spike test | datagram / lifecycle / environment classification | `packages/lifx-emulator-core/tests/test_ipv6_transport.py`, `packages/lifx-emulator-core/tests/test_server.py` | exact flow |
| `scripts/mdns_spike_inputs/active.json` | frozen candidate input manifest | batch / configuration | `.planning/phases/03-mdns-responder/03-01-EVIDENCE.json` | role-match |
| `.planning/phases/03-mdns-responder/03-01-EVIDENCE.json` | machine evidence | batch / transform | sibling `lifx-async` mDNS source | partial |
| `.planning/phases/03-mdns-responder/03-01-EVIDENCE.md` | rendered evidence | batch / transform | `.planning/phases/02-ipv6-transport-and-thread-isolation/02-VERIFICATION.md` | role-match |
| `.github/workflows/ci.yml` (only if a focused job is justified) | config | batch | `.github/workflows/ci.yml` | exact |

## Pattern Assignments

### `scripts/spike_mdns_candidates.py` (utility, datagram/batch)

**Analog:** sibling tracked source `../lifx-async/src/lifx/network/discovery/mdns/transport.py`.

Use an async context-managed candidate runner, explicit socket construction, and cleanup-on-error. Do **not** use its automatic route/interface selection: Phase 3 explicitly rejects automatic address selection.

```python
# transport.py:94-101, 131-148, 197-217
async def __aenter__(self):
    await self.open(); return self
...
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((local_address, 0))
...
except BaseException as e:
    if datagram_transport is not None: datagram_transport.close()
    elif sock is not None: sock.close()
    raise LifxNetworkError(...) from e
```

Record each candidate's installed version, command, wall/active time, 1/10/100 fleet result, RSS/CPU measurement method, and each unmet criterion. The harness is evidence tooling: use isolated uv-managed candidate dependencies and preserve the production dependency graph. Importing existing core code for the experiment is permitted; integrating a production responder is deferred.

### `scripts/mdns_spike_inputs/active.json` (frozen candidate input manifest)

Freeze only the currently eligible candidate's source/version, generator revision, overlay and dependency constraints before its CI run. Derive one shared `input_spec_digest` from those immutable inputs; record realised OS, architecture and Python environment digests separately. Replace this manifest only in a new commit after decisive rejection makes the next D-09/D-11 candidate eligible.

### `scripts/mdns_spike_tests/test_candidates.py` (explicit spike test, datagram/lifecycle)

**Analog:** `packages/lifx-emulator-core/tests/test_ipv6_transport.py`.

```python
# test_ipv6_transport.py:31-43, 66-75, 120-146
class _ClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.received = asyncio.Queue()
        self.closed = asyncio.Event()
    def datagram_received(self, data, addr): self.received.put_nowait((data, addr))
...
transport, _ = await loop.create_datagram_endpoint(
    lambda: protocol, local_addr=(host, 0), family=family
)
...
await asyncio.wait_for(protocol.received.get(), timeout=1.0)
...
finally:
    transport.close()
    await asyncio.wait_for(protocol.closed.wait(), timeout=1.0)
```

Keep injection hermetic: bind loopback/ephemeral ports, parse real datagrams, assert complete correctly associated record sets across one or more datagrams and legacy-unicast source destination/ID. Keep this file outside root `testpaths`; candidate and network work is run only by an explicit path. Use `AsyncMock`, fake transports and patched sockets from `test_server.py` to distinguish simulated Windows evidence from Ubuntu/macOS integration.

### `.planning/phases/03-mdns-responder/03-01-EVIDENCE.{json,md}` (evidence, batch/transform)

**Analog:** sibling tracked source `../lifx-async/src/lifx/network/discovery/mdns/discovery.py`.

JSON is the validator's only input and Markdown is rendered from it. Treat multiple packets as valid discovery input because `_LifxRecordCache` accumulates them (`discovery.py:281-284`, `add_packet` at `:707-724`). Separate raw loopback, reachable oracle, Ubuntu/macOS CI, macOS x86_64 PyApp, simulated Windows and untested evidence, then record go/no-go/provisional plus active-work and CI-queue accounting.

### `.github/workflows/ci.yml` (config, batch)

**Analog:** `.github/workflows/ci.yml`.

```yaml
# ci.yml:71-101
test:
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest]
      python-version: ['3.10', '3.11', '3.12', '3.13', '3.14']
...
    - run: uv sync --frozen
    - run: uv run --frozen pytest --cov-fail-under=80
```

Use the existing matrix if focused CI is warranted after the local spike; do not change it merely to create a spike. Packaging evidence follows the separate release workflow: macOS Intel is `macos-15-intel` / `x86_64-apple-darwin` (`release-binaries.yml:30-33`) and its PyApp build inputs are `PYAPP_*` plus `CARGO_BUILD_TARGET` (`release-binaries.yml:73-89`).

## Shared Patterns

### uv-managed execution

Root workspace test configuration names core/application source roots (`pyproject.toml:1-15, 58-63`). CI installs with `uv sync --frozen` before `uv run --frozen pytest` (`ci.yml:97-101`). Isolated candidate dependencies and their reproducible resolution belong to spike execution; production dependency changes await selection.

### Datagram lifecycle and evidence quality

Use real loopback sockets for protocol facts and mocks for deterministic surfaced failures. State which kind of evidence each result is. Closing zeroconf transports does not produce a supported owner notification, and amended D-08 does not require detecting that silent loss. VM work remains extension-only; production responder implementation awaits the explicit selection decision.

## No Analog Found

| File | Reason |
|---|---|
| A production responder module | Intentionally deferred until MDNS-10 records a justified decision. |

## Metadata

**Analog search scope:** core UDP tests/server, sibling `lifx-async` mDNS transport/cache, CI and PyApp workflow.
**Tracked-source gate:** verified for every named analog, including from the sibling repository root.
**Files scanned:** 8.
**Pattern extraction date:** 2026-09-22.
