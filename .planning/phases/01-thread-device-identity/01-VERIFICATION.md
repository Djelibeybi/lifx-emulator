---
phase: 01-thread-device-identity
verified: 2026-09-09T23:52:09Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - ".planning/PROJECT.md"
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/config.json"
  - ".planning/phases/01-thread-device-identity/01-01-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-01-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-02-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-02-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-03-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-03-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-04-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-04-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-CONTEXT.md"
  - ".planning/phases/01-thread-device-identity/01-RESEARCH.md"
  - ".planning/phases/01-thread-device-identity/01-SPEC.md"
  - "CLAUDE.md"
  - "packages/lifx-emulator-core/src/lifx_emulator/__init__.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/devices/device.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/devices/states.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/products/specs.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml"
  - "packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py"
  - "packages/lifx-emulator-core/src/lifx_emulator/server.py"
  - "packages/lifx-emulator-core/tests/test_async_storage.py"
  - "packages/lifx-emulator-core/tests/test_header.py"
  - "packages/lifx-emulator-core/tests/test_products_specs.py"
  - "packages/lifx-emulator-core/tests/test_thread_identity.py"
  - "packages/lifx-emulator-core/tests/test_tile_handlers_extended.py"
covered_digest: "v1:sha256:04e43993000ff76d78691ca2f96127e29ae6991c9372c1c505a400544bbdea93"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 1: Thread Device Identity Verification Report

**Phase Goal:** A core-library device can be created as a Thread device, and everything about its identity — firmware, WiFi reporting, persisted state and every header byte it emits — matches a real Thread bulb.
**Verified:** 2026-09-09T23:52:09Z
**Status:** passed
**Re-verification:** Yes — fresh verification of the released implementation plus the three current audit commits

## Goal Achievement

The prior report and four SUMMARY files identified claimed scope only. Verdicts below come from the current source, wiring, independent fixtures, and commands run during this verification.

### Roadmap Contract

| # | Roadmap success criterion | Status | Current evidence |
| --- | --- | --- | --- |
| 1 | `create_device()` and every typed factory except `create_tile_device()` can create Thread devices at firmware 4.200; explicit firmware wins; product 55 rejects Thread | ✓ VERIFIED | All eight entry points forward connectivity; the generic firmware resolver enforces the 4.200 floor and product 55's 3.50 ceiling. Named factory, floor, registry, and tile tests passed. |
| 2 | One Thread device sets frame-address bit 3 on `StateColor`, `Acknowledgement` (45), and `StateUnhandled` (223) | ✓ VERIFIED | `device.py:91-98` stamps a connectivity-derived response template used by normal, acknowledgement, and unhandled paths. Named reply-shape and real-server acknowledgement tests passed. |
| 3 | WiFi never sets bit 3 and existing WiFi headers remain byte-for-byte unchanged | ✓ VERIFIED | `LifxHeader.thread_connection` defaults false. The pre-phase header fixture and four exact WiFi packet fixtures passed. |
| 4 | Thread reports WiFi signal 0.0 while GetWifiFirmware and GetHostFirmware retain normal firmware data | ✓ VERIFIED | `builder.py:376-377` derives the signal from effective connectivity; unchanged handlers return state fields. `TestThreadIdentitySurface` passed. |
| 5 | Thread connectivity survives persistence; a pre-milestone file with no key restores as WiFi | ✓ VERIFIED | Serializer emits the bare enum string; cached restoration feeds builder precedence and safely defaults absent/invalid values. Named persistence tests passed. |

### Consolidated Observable Truths

The roadmap criteria and all 36 PLAN truth entries deduplicate into these 12 observable truths.

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Connectivity is a public, exactly validated `wifi`/`thread` identity and every factory exposes it with WiFi as the omitted/`None` default | ✓ VERIFIED | Public exports, coercion, all signatures, and eight-entry factory parametrisation verified. |
| 2 | Connectivity and WiFi signal cannot be reassigned after construction, and builder coercion accepts only `None`, the enum, or exact lower-case strings | ✓ VERIFIED | Frozen state, routed errors, and named immutability/builder tests passed, including same-value reassignment. |
| 3 | Firmware precedence is explicit override, Thread 4.200 floor/default, product default, then legacy default; ceilings remain generic, only product 55 rejects Thread, and existing WiFi/extended-multizone/SKY behaviour remains valid | ✓ VERIFIED | No product-ID branch exists in the resolver; named floor, registry-wide, extended-multizone, factory, and SKY tests passed. |
| 4 | `LifxHeader` packs/unpacks Thread on bit 3 only, leaves reserved bits clear, rejects short input, and round-trips both values | ✓ VERIFIED | `header.py:79-89,119,138-158`; independent header fixture and bit-difference tests passed. |
| 5 | Thread bit 3 reaches state replies, acknowledgements, unhandled, multi-packet, partial/malformed, matrix, scenario, and mixed-fleet output | ✓ VERIFIED | Single response-template stamping point plus named device, server, scenario, matrix, and mixed-fleet tests. |
| 6 | Default WiFi protocol output is byte-for-byte unchanged and never carries bit 3 | ✓ VERIFIED | Independent pre-phase fixture and exact `StateService`, `StateColor`, acknowledgement, and `StateUnhandled` fixtures passed. |
| 7 | Thread reports WiFi signal 0.0 and firmware normally; WiFi remains -45.0; ambient light retains the firmware-major rule | ✓ VERIFIED | State derivation and handlers are wired without a Thread-specific handler branch; identity-surface tests passed. |
| 8 | Fresh matrix tile firmware mirrors host firmware for Thread Ceiling 4.200, WiFi Ceiling 4.10, and WiFi Candle 3.70; persisted tile firmware remains verbatim by the declared boundary | ✓ VERIFIED | Named three-case tile and persisted-tile equality tests passed. |
| 9 | Persistence writes bare strings; round-trip, missing key, invalid warning, explicit precedence, and exactly-one-load behaviour hold | ✓ VERIFIED | `state_serializer.py:103`, cached restorer wiring, and all named persistence invariant tests. |
| 10 | Server packing/logging accepts scenario-produced raw bytes and delivers mutated Thread packets without losing bit 3 | ✓ VERIFIED | Bytes-aware helpers and named malformed/invalid scenario transport tests passed. |
| 11 | No product-55 firmware branch or generated-file edits exist, and the factory max-argument exception is narrowly documented | ✓ VERIFIED | No `55` in `firmware_config.py`; generated-file diff is empty; `CLAUDE.md:41` scopes the exception. |
| 12 | Tests, coverage, formatting, lint, types, active-test, and decision-coverage gates pass | ✓ VERIFIED | 1,234 tests, 94.11% coverage, clean Ruff/Pyright, 190 linked tests with no skip/xfail markers, 13/13 decisions honoured. |

**Score:** 12/12 truths verified (0 present, behaviour-unverified)

### PLAN Must-Have Traceability

Every PLAN truth was checked individually and maps to a verified consolidated truth.

| Plan | Individual truth status and mapping | Result |
| --- | --- | --- |
| 01-01 | T1→#6; T2→#1; T3→#2; T4→#2; T5→#4; T6→#4; T7→#5; T8→#6; T9→#2; T10→#1 | 10/10 ✓ VERIFIED |
| 01-02 | T1→#3; T2→#3; T3→#3; T4→#3; T5→#11; T6→#3; T7→#3; T8→#3 | 8/8 ✓ VERIFIED |
| 01-03 | T1→#1/#3; T2→#7; T3→#7; T4→#7; T5→#8; T6→#8; T7→#11 | 7/7 ✓ VERIFIED |
| 01-04 | T1→#9; T2→#9; T3→#9; T4→#5; T5→#5; T6→#10; T7→#5; T8→#5; T9→#6; T10→#12; T11→#9 | 11/11 ✓ VERIFIED |

### Prohibition Verification

All test-tier prohibitions have wired enforcement evidence.

| Source | Prohibition | Enforcement | Status |
| --- | --- | --- | --- |
| 01-01 | Do not change pre-existing WiFi reply/header bytes | Header fixture plus four exact WiFi packet fixtures | ✓ VERIFIED |
| 01-02 | Do not reject Thread on products other than 55 | Registry-wide test asserts the rejected set is exactly `{55}` | ✓ VERIFIED |
| 01-04 | Do not silently convert invalid caller input or bad persisted values | Caller input raises; corrupt persisted values fall back only with a captured warning | ✓ VERIFIED |
| 01-04 | Do not hand-edit generated `packets.py` or `registry.py` | `git diff 6d4e61c^..HEAD --` on both files returned no paths | ✓ VERIFIED |

## Required Artifacts

`verify.artifacts` passed 17/17 declared entries across the four plans (6 + 3 + 4 + 4). Direct reading confirmed they are substantive.

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `protocol/header.py` | Bit-3 model, pack, unpack, repr | ✓ VERIFIED | Field and exact bit operations present and exercised. |
| `devices/states.py` | Connectivity domain and immutable network identity | ✓ VERIFIED | Enum, coercion, frozen dataclass, defaults, routing. |
| `devices/device.py` | Response-header stamping and tile firmware | ✓ VERIFIED | Template derives from identity and is copied on every response path. |
| `factories/builder.py` | Connectivity precedence and state derivation | ✓ VERIFIED | Explicit > saved > WiFi flow is wired before state construction. |
| `factories/factory.py` | Eight public creation entry points | ✓ VERIFIED | Every signature exposes and forwards connectivity last. |
| `factories/firmware_config.py` | Thread default/floor and generic ceiling | ✓ VERIFIED | Implemented without product-specific branching. |
| `products/specs.py` / `products/specs.yml` | Generic ceiling and product 55 data | ✓ VERIFIED | Typed accessor plus 3.50 default/maximum. |
| Serializer/restorer | Persisted connectivity and compatibility | ✓ VERIFIED | Bare write, cached read, warning/fallback, product check. |
| `server.py` | Server acknowledgements and byte scenarios | ✓ VERIFIED | Device header helper and bytes-aware transport path. |
| Five linked test files | Independent protocol/end-to-end evidence | ✓ VERIFIED | 190 tests collect; no disabled-test markers. |
| `CLAUDE.md` | Narrow factory argument exception | ✓ VERIFIED | Explicit without suppression or broader waiver. |

## Key Link Verification

`verify.key-links` passed 9/9 declared links across the four plans (3 + 2 + 2 + 2).

| From | To | Via | Status |
| --- | --- | --- | --- |
| `devices/device.py` | `protocol/header.py` | connectivity-derived template | ✓ WIRED |
| `factories/builder.py` | `devices/states.py` | `NetworkState(connectivity=..., wifi_signal=...)` | ✓ WIRED |
| `factories/factory.py` | `factories/builder.py` | `with_connectivity()` | ✓ WIRED |
| `firmware_config.py` | `products/specs.py` | default/maximum accessors | ✓ WIRED |
| `builder.py` | `firmware_config.py` | effective connectivity | ✓ WIRED |
| `device.py` | tile handler output | host firmware copied to fresh tiles | ✓ WIRED |
| `builder.py` | `state_restorer.py` | one cached restorer | ✓ WIRED |
| `state_serializer.py` | `states.py` | stringified enum | ✓ WIRED |
| `server.py` | transport | bytes-aware packing after scenario mutation | ✓ WIRED |

## Data-Flow Trace (Level 4)

No rendered dynamic UI exists. Core identity still traces end-to-end through real data.

| Value | Source and flow | Terminal consumer | Status |
| --- | --- | --- | --- |
| Connectivity | factory/saved JSON → builder precedence → `NetworkState` | header template and serializer | ✓ FLOWING |
| Firmware | override/Thread/spec/legacy → resolver → host/fresh tiles | firmware and tile replies | ✓ FLOWING |
| WiFi signal | effective connectivity → builder literal → state | `StateWifiInfo` | ✓ FLOWING |
| Thread bit | state connectivity → device template → `LifxHeader.pack()` | UDP byte 22 bit 3 | ✓ FLOWING |
| Persisted connectivity | serializer → storage → cached peek → builder | reconstructed state | ✓ FLOWING |

## Behavioural Spot-Checks

| Behaviour | Command | Result | Status |
| --- | --- | --- | --- |
| Critical identity/header/server/matrix/persistence invariants | Targeted `uv run --frozen pytest ... --no-cov` with 16 named nodes/classes | 25 passed in 0.04s | ✓ PASS |
| Immutability/floor/WiFi compatibility/tile/SKY invariants | Targeted invocation with 9 named nodes/classes | 12 passed in 0.04s | ✓ PASS |
| Workspace suite and coverage | `uv run --frozen pytest -q -p no:sugar --cov-fail-under=80` | 1,234 passed; 94.11% | ✓ PASS |
| Lint | `uv run --frozen ruff check .` | All checks passed | ✓ PASS |
| Format | `uv run --frozen ruff format --check .` | 108 files already formatted | ✓ PASS |
| Types | `uv run --frozen pyright` | 0 errors, warnings, or information diagnostics | ✓ PASS |
| Decision coverage | `gsd-tools query check.decision-coverage-verify ...` | 13/13 honoured | ✓ PASS |
| Generated-file guard | `git diff --name-only 6d4e61c^..HEAD -- ...` | Empty | ✓ PASS |

## Probe Execution

No PLAN/SUMMARY declares a probe and no `scripts/*/tests/probe-*.sh` exists. Not applicable.

## Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| --- | --- | --- | --- |
| CONN-01 | 01-01, 01-03 | ✓ SATISFIED | Public enum, builder coercion, eight-entry factory tests. |
| CONN-02 | 01-02, 01-03 | ✓ SATISFIED | Thread 4.200 precedence/floor/ceiling tests; documented scenario override remains outside this milestone and has no call site. |
| CONN-03 | 01-03 | ✓ SATISFIED | Signal derivation, unchanged handlers, identity-surface test. |
| CONN-04 | 01-04 | ✓ SATISFIED | Serializer/restorer flow and real-file persistence tests. |
| HDR-01 | 01-01 | ✓ SATISFIED | Exact bit operations and independent fixtures. |
| HDR-02 | 01-01, 01-04 | ✓ SATISFIED | Single stamping point and every response-shape test. |
| HDR-03 | 01-01, 01-04 | ✓ SATISFIED | Default false and exact WiFi fixtures. |

All seven PLAN IDs exist in `REQUIREMENTS.md`, are mapped to Phase 1, and are satisfied. No other requirement maps to Phase 1; there are no orphaned requirements.

## Test Quality Audit

| Test set | Active | Disabled | Circularity | Strength | Status |
| --- | ---: | ---: | --- | --- | --- |
| Five linked files | 190 collected | 0 | Fixture writes supply independent inputs; expected bytes/values are not generated by the implementation under test | Exact bytes, fields, errors, warnings, persistence, transport | ✓ PASS |

## Anti-Patterns Found

No `TBD`, `FIXME`, `XXX`, `TODO`, or `HACK` marker exists in Phase 1 files. Empty-list returns inspected are valid “no response/activity” paths, not stubs.

| File | Line | Pattern | Severity | Impact |
| --- | ---: | --- | --- | --- |
| `factories/builder.py` | 310 | “placeholders” | ℹ️ Info | False positive: two `%r` logging placeholders, not incomplete code. |
| Workspace test output | — | 14 deprecation/runtime warnings, chiefly app WebSocket scheduling | ℹ️ Info | Outside Phase 1 core identity and does not falsify a phase truth; recorded rather than ignored. |

No blocker or warning-level Phase 1 anti-pattern was found.

## Human Verification Required

None. Every state transition, precedence rule, persistence invariant, and wire-ordering claim has a passing behavioural test; no visual/external-service claim exists.

## Deferred-Item Filter

No gap was found. Later phases cover UDP transport, mDNS, config/API exposure, and oracle validation; none is needed to make the Phase 1 core-library goal true.

## Gaps Summary

**No gaps found.** Current core factories create Thread devices with correct firmware, persisted identity, WiFi reporting, and bit-3 output on every tested response path without changing WiFi bytes. The three audit commits alter planning evidence only; the released implementation remains intact and passes fresh behavioural and workspace gates.

---

_Verified: 2026-09-09T23:52:09Z_
_Verifier: the agent (gsd-verifier)_
