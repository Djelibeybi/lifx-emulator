---
phase: 03-mdns-responder
verified: 2026-09-23T10:09:30Z
status: gaps_found
score: pending review follow-up verification
covered_files:
  - .github/workflows/ci.yml
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/phases/03-mdns-responder/03-01-EVIDENCE.json
  - .planning/phases/03-mdns-responder/03-01-EVIDENCE.md
  - .planning/phases/03-mdns-responder/03-01-PLAN.md
  - .planning/phases/03-mdns-responder/03-01-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-02-PLAN.md
  - .planning/phases/03-mdns-responder/03-02-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-03-PLAN.md
  - .planning/phases/03-mdns-responder/03-03-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-04-PLAN.md
  - .planning/phases/03-mdns-responder/03-04-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-05-PLAN.md
  - .planning/phases/03-mdns-responder/03-05-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-06-PLAN.md
  - .planning/phases/03-mdns-responder/03-06-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-07-PLAN.md
  - .planning/phases/03-mdns-responder/03-07-SUMMARY.md
  - .planning/phases/03-mdns-responder/03-CONTEXT.md
  - .planning/phases/03-mdns-responder/03-REVIEW-FOLLOWUP.md
  - .planning/phases/03-mdns-responder/03-REVIEW.md
  - .planning/phases/03-mdns-responder/03-SECURITY.md
  - .planning/phases/03-mdns-responder/03-SPEC.md
  - .planning/phases/03-mdns-responder/03-ZEROCONF-CLOSEOUT.json
  - .planning/phases/03-mdns-responder/03-review-evidence/linux-interface-scope.py
  - packages/lifx-emulator-core/pyproject.toml
  - packages/lifx-emulator-core/src/lifx_emulator/__init__.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/states.py
  - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
  - packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py
  - packages/lifx-emulator-core/src/lifx_emulator/mdns.py
  - packages/lifx-emulator-core/src/lifx_emulator/server.py
  - packages/lifx-emulator-core/tests/test_device_manager.py
  - packages/lifx-emulator-core/tests/test_mdns_config.py
  - packages/lifx-emulator-core/tests/test_mdns_integration.py
  - packages/lifx-emulator-core/tests/test_mdns_lifecycle.py
  - packages/lifx-emulator-core/tests/test_mdns_platform.py
  - packages/lifx-emulator-core/tests/test_mdns_responder.py
  - packages/lifx-emulator-core/tests/test_mdns_review.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/app.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py
  - packages/lifx-emulator/tests/test_websocket.py
  - scripts/mdns_spike_inputs/active.json
  - scripts/mdns_spike_inputs/zeroconf_recovery.py
  - scripts/mdns_spike_tests/test_candidates.py
  - scripts/mdns_spike_tests/test_recovery.py
  - scripts/prepare_mdns_oracle.py
  - scripts/spike_mdns_candidates.py
  - uv.lock
covered_digest: "v1:sha256:d584c3291b0471ca3cdb62636a4c697c7b4bf325d7a8e36c122bd5420e48cc1e"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "The production loopback-multicast integration tests passed on both hosted Ubuntu and hosted macOS in run 35846599552 at f8d9f86501385fcf57999d2094eff4d6b72ec52d."
  gaps_remaining: []
  regressions: []
---

# Phase 3: mDNS Responder Verification Report

**Reopened 2026-09-23:** PR review revealed a confirmed Linux receive-interface isolation gap and lifecycle defects. Twelve comments have local fixes and 1,486 tests pass; hosted verification of the changed code remains pending. The Linux scope decision is unresolved. See `03-REVIEW-FOLLOWUP.md`. The report below is historical evidence for f8d9f86, not approval of the revised implementation.

## Historical verification

**Phase Goal:** `lifx-async` can find emulated devices over mDNS the way it actually queries — legacy-unicast from an ephemeral port — with Thread devices advertised AAAA-only and WiFi devices A-only.
**Verified:** 2026-09-23T10:09:30Z
**Status:** passed
**Re-verification:** Yes — after hosted CI gap closure and bounded Python 3.10 test-helper repair

## Goal Achievement

The production responder is implemented, substantive and wired through server ownership, factory configuration, live membership and the pristine client oracle. Local and hosted evidence proves complete 0/1/10/100-fleet discovery and IPv4/IPv6 control. The previously missing hosted gate is closed by successful Ubuntu and macOS production jobs at the exact final head, with the complete Python 3.10–3.14 two-OS matrix green.

Plan 03-01 is a historical halted spike and is superseded by the approved 03-02 closeout. It does not block implementation verification. The retained 03-02 closeout validates as `go` for zeroconf 0.151.3.

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A recorded, fully evidenced go/no-go decision selects the responder foundation under D-09–D-18. | ✓ VERIFIED | `validate-zeroconf-closeout` returned `{"valid": true, "allowed": ["go", "provisional"], "decision": "go"}` for the hash-linked zeroconf 0.151.3 ledger. |
| 2 | An ephemeral-port `_lifx._udp.local` PTR query receives a legacy-unicast reply with source affinity, echoed ID, clear cache-flush and TTL ≤ 10 beside the host daemon. | ✓ VERIFIED | `test_tracer_legacy_unicast` passed independently; the required-mode production run also passed on local macOS beside mDNSResponder. `MdnsResponder` publishes TTL 10 through public zeroconf operations. |
| 3 | Every eligible device is discoverable with correct PTR/SRV/TXT and one matching-family address, without packet grouping or fleet-capacity loss. | ✓ VERIFIED | Required-mode production cases passed for fleets 0/1/10/100 against the exact pristine client revision; code constructs exact `id`, `p`, `fw`, `tm`, service port and A/AAAA records. `test_mdns_mixed_records` passed independently. |
| 4 | Direct address queries and live add/remove/re-add update the record set while WebSocket membership events remain intact. | ✓ VERIFIED | `test_membership_add_remove_readd_wire` and `test_event_bridge_listener_coexistence` passed independently. The listener registry is ordered, identity-based and exception-isolated; the server queues complete snapshots and exposes an awaitable completion boundary. |
| 5 | The opt-in responder has correct lifecycle/failure cleanup and both injection and loopback integration tests pass on Ubuntu and macOS CI. | ✓ VERIFIED | Run [35846599552](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552) completed successfully at exact head `f8d9f86501385fcf57999d2094eff4d6b72ec52d`; both required-mode production jobs passed 4/4 with no skips, and all ten Python 3.10–3.14 Ubuntu/macOS matrix jobs passed. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/lifx-emulator-core/src/lifx_emulator/mdns.py` | Public zeroconf adapter, records, reconciliation and owned cleanup | ✓ VERIFIED | 255 substantive lines; complete snapshots feed register/update/unregister operations; no placeholder or debt marker. |
| `packages/lifx-emulator-core/src/lifx_emulator/server.py` | Opt-in lifecycle, validation, status, retry and fleet failure policy | ✓ VERIFIED | `mdns_enabled=False`, pre-mutation `resolve_address`, lifecycle listener wiring, completion barrier and cleanup are all called from live server paths. |
| `devices/states.py`, `factories/builder.py`, `factories/factory.py` | Immutable validated per-device mDNS intent | ✓ VERIFIED | Every factory carries `mdns_enabled=True` and `mdns_address=None`; address family, wildcard, multicast, link-local and Thread opt-out validation occurs before construction. Wholesale network replacement is rejected. |
| `devices/manager.py` and `event_bridge.py` | Non-displacing runtime membership notifications | ✓ VERIFIED | Ordered identity-based listeners coexist with legacy callbacks and both WebSocket consumers. |
| Production mDNS tests | Datagram, configuration, membership, lifecycle and platform coverage | ✓ VERIFIED | Artifact checks pass for responder, config, lifecycle, platform and integration test modules; focused behavioural checks pass. |
| `scripts/prepare_mdns_oracle.py` | Exact isolated pristine client acquisition | ✓ VERIFIED | Enforces repository URL, revision, tree and clean status without touching the sibling checkout. |
| `.github/workflows/ci.yml` | Fail-closed production integration on Ubuntu and macOS | ✓ VERIFIED | Exact-head run 35846599552 passed required-mode production integration on both OSes and all ten standard matrix jobs. |
| `.planning/phases/03-mdns-responder/03-SECURITY.md` | Phase threat-mitigation audit | ✓ VERIFIED | Committed audit status is `verified`, with all 32 plan-scoped threats closed and zero blocking threats; the Python 3.10 helper repair changes no production mitigation. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `server.py` | `mdns.py` | Construct after committed LIFX port; stop under owned lifecycle | ✓ WIRED | `_start_mdns_locked()` constructs `MdnsResponder` using the effective port, registers one listener and awaits startup; `_stop_mdns_locked()` removes the listener and closes the owner. |
| Factories | `NetworkState` | `DeviceBuilder.with_mdns()` | ✓ WIRED | All public factory arguments flow into frozen device state. |
| `server.py` | address validation | `resolve_address()` before startup and `add_device()` mutation | ✓ WIRED | Manual trace resolves the plan regex false negative: startup validates every initial device at lines 1042–1044; add validates at lines 655–663 before manager mutation at line 667. |
| `DeviceManager` | responder reconciliation | `DeviceLifecycleListener` full-snapshot callback | ✓ WIRED | Successful committed changes trigger `_queue_mdns_update()`; duplicate/failed mutations do not notify. |
| `DeviceManager` | WebSocket event bridge | independent listener registrations | ✓ WIRED | Device events and state-change observers register separately; coexistence test passed. |
| CI workflow | production integration test | required mode plus exact oracle path | ✓ WIRED AND EXECUTED | The job sets `MDNS_INTEGRATION_REQUIRED=1`, `LIFX_ASYNC_PATH` and `PYTHONPATH`; final hosted Ubuntu and macOS jobs each acquired the exact pristine oracle and passed 4 tests with the no-skip JUnit assertion. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `mdns.py` | `ServiceInfo` snapshot | Live `EmulatedLifxDevice.state` plus committed server port/bind addresses | Yes — serial, product, firmware, connectivity and addresses populate PTR/SRV/TXT/A/AAAA records | ✓ FLOWING |
| `server.py` | membership snapshot | `DeviceManager.get_all_devices()` after committed add/remove | Yes — scheduled reconciliation registers, updates and unregisters real zeroconf services | ✓ FLOWING |
| `test_mdns_integration.py` | discovered client map | Raw multicast replies and pristine `lifx-async.discover_mdns()` | Yes — exact eligible serial sets and endpoint power queries passed for 0/1/10/100 locally | ✓ FLOWING |
| WebSocket bridge | membership payload | Same committed `DeviceManager` events | Yes — independent listeners preserve existing device/state event streams | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Legacy-unicast wire contract | `uv run pytest .../test_mdns_responder.py::test_tracer_legacy_unicast -q --no-cov` | 1 passed in 2.70 s | ✓ PASS |
| Mixed A/AAAA records and direct queries | `uv run pytest .../test_mdns_config.py::test_mdns_mixed_records -q --no-cov` | 1 passed in 3.14 s | ✓ PASS |
| Add/remove/re-add wire visibility | `uv run pytest .../test_mdns_lifecycle.py::test_membership_add_remove_readd_wire -q --no-cov` | 1 passed in 4.23 s | ✓ PASS |
| Shutdown retains admitted operation failure | `uv run pytest .../test_mdns_lifecycle.py::test_stop_retains_admitted_operation_failure -q --no-cov` | 1 passed in 0.02 s | ✓ PASS |
| WebSocket listener coexistence | `uv run pytest .../test_websocket.py::test_event_bridge_listener_coexistence -q --no-cov` | 1 passed in 0.25 s | ✓ PASS |

The retained whole-suite output records 1,474 passed, 4 environment-gated skips and 95% coverage. The retained required-mode local macOS output records 4 passed with no skips. The configured root Pyright output records 0 errors, 0 warnings and 0 information messages. The bounded Python 3.10 repair output records 68 focused tests passed. Final hosted execution independently closes the platform gate.

### Probe Execution

No Phase 3 `probe-*.sh` probe is declared. The selection ledger validator was run directly and returned a valid `go` decision; production behaviour is exercised through the test modules above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| MDNS-01 | 03-03, 03-04, 03-07 | Opt-in multicast reception and host-daemon coexistence | ✓ SATISFIED | Default disabled test, public zeroconf owner and local macOS required-mode host-daemon run. |
| MDNS-02 | 03-03, 03-07 | Legacy-unicast destination, ID, flags and TTL | ✓ SATISFIED | Named tracer test and required-mode raw capture. |
| MDNS-03 | 03-03, 03-04, 03-07 | Complete associated discovery independent of grouping | ✓ SATISFIED | Exact 0/1/10/100 eligible serial sets through pristine client. |
| MDNS-04 | 03-03, 03-04, 03-07 | Exact stable TXT metadata | ✓ SATISFIED | Service construction and raw integration assert exactly four keys including `4.200`. |
| MDNS-05 | 03-03, 03-04, 03-07 | Thread AAAA-only and WiFi A-only | ✓ SATISFIED | Mixed record and pristine client integration tests. |
| MDNS-06 | 03-04, 03-07 | Explicit/fallback usable addresses and early rejection | ✓ SATISFIED | Frozen state validation plus startup/add preflight tests. |
| MDNS-07 | 03-04, 03-07 | Direct hostname A/AAAA queries | ✓ SATISFIED | Mixed-record named test and required-mode direct-query assertions. |
| MDNS-08 | 03-05, 03-06, 03-07 | Runtime membership without displacing WebSocket events | ✓ SATISFIED | Named membership and coexistence tests. |
| MDNS-09 | 03-06, 03-07 | Owned lifecycle, failure policy and cleanup | ✓ SATISFIED | Named shutdown-failure test plus focused lifecycle coverage and full-suite pass. |
| MDNS-10 | 03-02 | Evidence-gated responder selection | ✓ SATISFIED | Hash-linked closeout validator returned `go` for zeroconf 0.151.3. |
| MDNS-11 | 03-03–03-07 | Injection tests and loopback multicast on CI runners | ✓ SATISFIED | Final hosted Ubuntu and macOS production jobs each passed all four required-mode cases with no skips at exact head f8d9f86; all ten standard OS/Python jobs also passed. |

The previous `gaps_found` routing affected tracking metadata only; this re-verification supersedes that verdict with the exact-head hosted evidence above.

No orphaned Phase 3 requirement was found: MDNS-01 through MDNS-11 are all claimed by canonical plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | No unreferenced TBD/FIXME/XXX markers, production placeholders, hollow values or console-only implementations found in Phase 3 changed code | — | None |

The initial empty dictionaries, lists and `None` owners in the responder/server are lifecycle state populated by live device snapshots and public zeroconf ownership; they are not stubs. The deep code review is clean after its two documented fixes.

### Advisory (New Scope, Unevidenced)

None. Re-verification found no new-scope concern. Commit `007679a` is a test-only compatibility repair using the public `DatagramProtocol` transport API; it explicitly awaits `connection_lost`, preserves raw-wire assertions and leaves production source unchanged.

### Hosted CI Closure

| Evidence | Result | Link |
|---|---|---|
| Final exact-head run `f8d9f86501385fcf57999d2094eff4d6b72ec52d` | ✓ SUCCESS | [Run 35846599552](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552) |
| Production integration — macOS | ✓ 4 passed, no skips | [Job 107134190612](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190612) |
| Production integration — Ubuntu | ✓ 4 passed, no skips | [Job 107134190690](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190690) |
| Python 3.10 — Ubuntu | ✓ PASS | [Job 107134190872](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190872) |
| Python 3.10 — macOS | ✓ PASS | [Job 107134190947](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190947) |
| Python 3.11 — Ubuntu | ✓ PASS | [Job 107134190910](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190910) |
| Python 3.11 — macOS | ✓ PASS | [Job 107134190988](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190988) |
| Python 3.12 — Ubuntu | ✓ PASS | [Job 107134191019](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134191019) |
| Python 3.12 — macOS | ✓ PASS | [Job 107134191187](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134191187) |
| Python 3.13 — Ubuntu | ✓ PASS | [Job 107134190939](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190939) |
| Python 3.13 — macOS | ✓ PASS | [Job 107134190972](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134190972) |
| Python 3.14 — Ubuntu | ✓ PASS | [Job 107134191081](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134191081) |
| Python 3.14 — macOS | ✓ PASS | [Job 107134191047](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35846599552/job/107134191047) |

The first hosted run [35845339733](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35845339733) already passed both production jobs ([macOS](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35845339733/job/107130058162), [Ubuntu](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35845339733/job/107130058182)) 4/4 without skips, while its standard Python 3.10 jobs exposed the test-helper compatibility defect. Commit `007679a` repaired that helper; `/tmp/lifx-phase3-py310-fix.txt` records 68 focused tests passed under CPython 3.10.19, and the final run proves both repaired Python 3.10 matrix jobs green.

### Human Verification Required

None. The remaining gap is a deterministic external execution gate, not a subjective human check.

### Gaps Summary

None. The sole carried gap is closed, no regression was found, and the Phase 3 goal is achieved.

---

_Verified: 2026-09-23T10:09:30Z_
_Verifier: the agent (gsd-verifier)_
