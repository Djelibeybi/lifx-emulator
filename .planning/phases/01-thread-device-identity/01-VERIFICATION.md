---
phase: 01-thread-device-identity
verified: 2026-09-09T09:27:46Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/01-thread-device-identity/01-01-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-01-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-02-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-02-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-03-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-03-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-04-PLAN.md"
  - ".planning/phases/01-thread-device-identity/01-04-SUMMARY.md"
  - ".planning/phases/01-thread-device-identity/01-CONTEXT.md"
  - ".planning/phases/01-thread-device-identity/01-REVIEW-FIX.md"
  - ".planning/phases/01-thread-device-identity/01-REVIEW.md"
  - ".planning/phases/01-thread-device-identity/01-SPEC.md"
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
covered_digest: "v1:sha256:39c35dc204f01d61d3ba37ed6c6a1ce03ad6b24ce176382c130f99dcad561777"
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
**Verified:** 2026-09-09T09:27:46Z
**Status:** passed
**Re-verification:** Yes — refresh after stale timestamp + 3 code-review fix commits (e9371ab, 08a9a49, abd74ce)

## Why This Pass Ran

The prior `01-VERIFICATION.md` recorded `verified: 2026-09-09T00:00:00Z` — a midnight
placeholder that predates every commit in the phase (the phase's own commits, including the
`docs(phase-01): complete phase execution` commit `6099e96`, all carry real timestamps later
that day), so GSD flagged the verification record as stale/unreliable regardless of its
`passed` content. Since that pass, three code-review fix commits landed:

- `e9371ab` — `fix(01): WR-01 add registry-wide invariant test for firmware ceiling defaults`
- `08a9a49` — `fix(01): IN-01 simplify redundant restorer guard in DeviceBuilder.build`
- `abd74ce` — `fix(01): IN-02 clarify duplicated log placeholder in connectivity-conflict warning`

plus one docs-only commit (`90fb643`, adds `01-REVIEW-FIX.md`). This report re-verifies the
phase goal from scratch against the current tree and confirms these three fixes did not
regress any must-have.

**Confirmed scope of change since the prior pass:** `git diff --stat db5b221..HEAD --
packages/` (the commit the prior verification's `covered_digest` was computed against) shows
exactly two files touched: `factories/builder.py` (+4/-2, comment clarification and a
provably-safe conditional simplification) and `tests/test_products_specs.py` (+15, one new
registry-wide invariant test). Nothing else in `packages/` changed.

## Goal Achievement

### Observable Truths

All five roadmap success criteria were re-executed live against the current tree (fresh `uv
run python3` sessions calling `create_color_light()`, `create_tile_device()`,
`process_packet()`, and the relevant test classes directly) rather than trusted from
SUMMARY.md or the prior VERIFICATION.md.

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `create_device(pid, connectivity="thread")` and typed factories (except `create_tile_device`) yield host firmware 4.200; explicit firmware wins; `create_tile_device(connectivity="thread")` raises `ValueError` | ✓ VERIFIED | Live re-check: `create_color_light(connectivity="thread")` → `(version_major, version_minor) == (4, 200)`; `firmware_version=(5,0)` → `(5, 0)` (override wins); `firmware_version=(4,199)` → `ValueError: "Thread firmware must be at least (4, 200), got (4, 199)"`; `create_tile_device(connectivity="thread")` → `ValueError: "Firmware (4, 200) exceeds product 55's maximum (3, 50) (Thread's default firmware of (4, 200) cannot be reduced to fit)"`. New registry-wide test `test_every_ceiling_product_has_a_compatible_default` (added by WR-01 fix) passes standalone (1/1) |
| 2 | A single Thread device sets bit 3 on `StateColor`, `Acknowledgement` (45), and `StateUnhandled` (223) | ✓ VERIFIED | `TestThreadBitOnEveryReply` + `TestSendAckRealServerWifiAndThread` in `test_thread_identity.py` pass (part of the 55/55 passing in that file); no code touched by the fix commits lies on this path |
| 3 | A WiFi device never sets bit 3; every existing header round-trips byte-for-byte | ✓ VERIFIED | `test_header.py` (`TestHeaderByteFixture`, `TestThreadConnectionBit`, 9/9) passes unchanged; `protocol/header.py` untouched by the three fix commits (`git diff db5b221..HEAD` confirms) |
| 4 | `GetWifiInfo` on Thread returns signal 0.0; `GetWifiFirmware`/`GetHostFirmware` answer normally | ✓ VERIFIED | `TestThreadIdentitySurface` in `test_thread_identity.py` passes; no touched file lies on this path |
| 5 | A Thread device survives persistence round trip; a pre-milestone file loads as `wifi` | ✓ VERIFIED | `TestConnectivityPersistence` (7/7) in `test_async_storage.py` re-run standalone and passes; this is the exact area `factories/builder.py` was touched (step 11 restore guard, step 1a warning comment) — re-verified the invariant behind the IN-01 simplification directly: `restorer = StateRestorer(self._storage) if self._storage else None` (line 348) means `restorer is not None` implies `self._storage` was truthy, so `if self._storage and restorer is not None:` → `if restorer is not None:` is behaviour-preserving. No test regressed |

**Score:** 5/5 roadmap truths verified (0 present-but-behavior-unverified)

### PLAN-Level Must-Haves (spot-checked across all four plans)

| # | Must-have | Status | Evidence |
| --- | --- | --- | --- |
| 6 | `Connectivity(str, Enum)` importable from `lifx_emulator` and `lifx_emulator.devices`; invalid strings raise `ValueError`; post-construction reassignment raises `ValueError` naming the refused attribute | ✓ VERIFIED | Unchanged file (`devices/states.py` not in the 2-file diff); `TestConnectivityFactory`, `TestDeviceBuilderConnectivity` pass in current run |
| 7 | `LifxHeader.thread_connection` bit 3 pack/unpack, single-byte diff, reserved bits untouched, short-unpack still raises | ✓ VERIFIED | `protocol/header.py` untouched since prior pass; `test_header.py` 9/9 pass |
| 8 | Per-tile firmware mirrors host firmware (Thread Ceiling 4.200, WiFi Ceiling 4.10, WiFi Candle 3.70) | ✓ VERIFIED | `devices/device.py` untouched since prior pass; relevant tests in `test_thread_identity.py` pass |
| 9 | `git diff main` on `protocol/packets.py` / `products/registry.py` is empty (generated files untouched) | ✓ VERIFIED | Re-ran `git diff --stat ba1222d..HEAD -- packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` — zero output, exit 0 |
| 10 | Single stamping point: no `LifxHeader(` construction site outside `header.py`/`device.py` | ✓ VERIFIED | Neither file touched since prior pass; grep re-run confirms no new construction sites introduced anywhere |
| 11 | `EmulatedLifxServer` bytes-aware repair reaches the transport for `malformed_packets`/`invalid_field_values` scenarios, preserving bit 3 | ✓ VERIFIED | `server.py` untouched since prior pass; `TestScenarioMutationReachesTransport` (2/2) pass |
| 12 | Two SKY-effect tests migrated from product 55 to product 185 with unchanged assertions | ✓ VERIFIED | `test_tile_handlers_extended.py` untouched since prior pass; tests pass |

**Score:** 12/12 must-haves verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `protocol/header.py` | `thread_connection` bit 3 field, pack/unpack, repr | ✓ VERIFIED | Unchanged since prior pass; still present and exercised |
| `devices/states.py` | `Connectivity` enum, `coerce_connectivity()`, frozen `NetworkState`, routing entry | ✓ VERIFIED | Unchanged since prior pass |
| `devices/device.py` | Single stamping point on `_response_header_template`; per-tile firmware mirror | ✓ VERIFIED | Unchanged since prior pass |
| `factories/builder.py` | `with_connectivity()`, `_resolve_connectivity()`, restore guard | ✓ VERIFIED | Modified by IN-01/IN-02 fixes; re-read in full — `_resolve_connectivity()` logic unchanged, only a comment added; `build()` step 11 guard simplified but provably equivalent (see Truth 5 evidence) |
| `factories/factory.py` | `connectivity` on `create_device()` + all 7 typed factories | ✓ VERIFIED | Unchanged since prior pass |
| `factories/firmware_config.py` | `VERSION_THREAD = (4, 200)`, floor/ceiling validation | ✓ VERIFIED | Unchanged since prior pass |
| `products/specs.yml` | Product 55 terminal firmware (3, 50) default + ceiling | ✓ VERIFIED | Unchanged since prior pass |
| `devices/state_serializer.py` / `state_restorer.py` | `connectivity` persisted/restored with fallback rules | ✓ VERIFIED | Unchanged since prior pass; 7/7 `TestConnectivityPersistence` pass live |
| `server.py` | Bytes-aware payload branch | ✓ VERIFIED | Unchanged since prior pass |
| `tests/test_header.py`, `tests/test_thread_identity.py` | Pre-change byte fixtures + end-to-end assertions | ✓ VERIFIED | Unchanged since prior pass; 9 + 55 pass |
| `tests/test_products_specs.py` | Registry-wide firmware-ceiling/default invariant (new, WR-01) | ✓ VERIFIED | `test_every_ceiling_product_has_a_compatible_default` present, substantive (iterates live `PRODUCTS` registry, asserts no `ValueError` on the plain-default path for any product declaring a firmware ceiling), passes |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `devices/device.py` | `protocol/header.py` | `thread_connection=` kwarg on `_response_header_template` | ✓ WIRED | Unchanged since prior pass |
| `factories/builder.py` | `devices/states.py` | `NetworkState(connectivity=connectivity)` | ✓ WIRED | Unchanged since prior pass |
| `factories/factory.py` | `factories/builder.py` | `builder.with_connectivity(connectivity)` | ✓ WIRED | Unchanged since prior pass |
| `factories/builder.py` | `factories/firmware_config.py` | `get_firmware_version(..., connectivity=connectivity)` | ✓ WIRED | Unchanged since prior pass |
| `devices/state_restorer.py` | `factories/builder.py` | `peek_connectivity()` single-read cache, `restorer is not None` gate at step 11 | ✓ WIRED | Re-verified directly: `restorer` construction (`builder.py:348`) is the sole assignment site and is `None` exactly when `self._storage` is falsy, so the IN-01 simplification at step 11 preserves "only restore when storage is configured" |
| `factories/builder.py` (new) | `products/registry.py` + `products/specs.py` | `test_every_ceiling_product_has_a_compatible_default` iterates `PRODUCTS`, calls `FirmwareConfig().get_firmware_version(product_id=pid)` for every ceiling product | ✓ WIRED | Confirmed by reading the test body and by standalone execution (1/1 pass) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| CONN-01 | 01-01, 01-03 | `connectivity` field on `NetworkState`, all factories + `DeviceBuilder` | ✓ SATISFIED | Unchanged since prior pass; live checks above |
| CONN-02 | 01-02 | Thread firmware default 4.200 + floor, explicit override wins; now with registry-wide ceiling/default invariant test | ✓ SATISFIED | Live checks above; WR-01 fix strengthens this requirement's test coverage without changing behaviour |
| CONN-03 | 01-03 | Thread WiFi signal 0.0, firmware queries unaffected | ✓ SATISFIED | Unchanged since prior pass |
| CONN-04 | 01-04 | Persistence round trip | ✓ SATISFIED | `TestConnectivityPersistence` (7/7) pass live; the touched restore-guard code sits directly on this requirement and was proven behaviour-preserving |
| HDR-01 | 01-01 | `LifxHeader` bit 3 pack/unpack, byte-for-byte unchanged elsewhere | ✓ SATISFIED | Unchanged since prior pass |
| HDR-02 | 01-01, 01-04 | Bit 3 on every reply shape | ✓ SATISFIED | Unchanged since prior pass |
| HDR-03 | 01-01 | WiFi device never sets bit 3 | ✓ SATISFIED | Unchanged since prior pass |

No orphaned requirements: REQUIREMENTS.md maps exactly CONN-01 through CONN-04 and HDR-01
through HDR-03 to Phase 1, all seven marked `Complete`.

### Anti-Patterns Found

Scanned the two files touched since the prior pass (`factories/builder.py`,
`tests/test_products_specs.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/stub
patterns, and re-confirmed the full-phase diff (`git diff --name-only db5b221..HEAD --
packages/lifx-emulator-core/src/`) is limited to these two files.

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `factories/builder.py:310` | "both placeholders are retained for clarity" | `PLACEHOLDER` grep hit | ℹ️ Info | False positive — refers to the two `%r` string-format placeholders in the `logger.warning()` call, not a debt marker. No unreferenced `TODO`/`FIXME`/`XXX`/`HACK` exists in either touched file |

No blockers.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full test suite | `uv run pytest -q -p no:sugar` | `1229 passed, 14 warnings` (1228 prior + 1 new WR-01 test) | ✓ PASS |
| `test_thread_identity.py` | `uv run pytest ... -q -p no:sugar` | 55 passed | ✓ PASS |
| `test_async_storage.py -k Connectivity` | `uv run pytest ... -q -p no:sugar` | 7 passed, 23 deselected | ✓ PASS |
| `test_header.py` | `uv run pytest ... -q -p no:sugar` | 9 passed | ✓ PASS |
| `test_products_specs.py -k test_every_ceiling_product_has_a_compatible_default` | `uv run pytest ... -v` | 1 passed | ✓ PASS |
| Lint | `uv run ruff check .` | All checks passed | ✓ PASS |
| Format | `uv run ruff format --check .` | 108 files already formatted | ✓ PASS |
| Types | `uv run pyright` | 0 errors, 0 warnings, 0 informational diagnostics | ✓ PASS |
| Generated-file guard | `git diff --stat ba1222d..HEAD -- .../protocol/packets.py .../products/registry.py` | empty | ✓ PASS |
| Fix-commit scope guard | `git diff --stat db5b221..HEAD -- packages/` | 2 files, +23/-2 lines total | ✓ PASS |
| Live end-to-end: Thread firmware default/floor/ceiling | ad-hoc `uv run python3` session | all assertions passed (see Truth 1 evidence) | ✓ PASS |

### Human Verification Required

None. Every roadmap success criterion and PLAN must-have was re-verified live against the
current tree, and the three code-review fix commits were shown by direct source read plus a
passing standalone invariant test to be behaviour-preserving on every path they touch.

### Gaps Summary

No gaps found, and no regressions introduced by the three code-review fix commits. All 7
requirement IDs (CONN-01 through CONN-04, HDR-01 through HDR-03) remain implemented, tested,
and independently re-verified live. All 5 roadmap success criteria still hold. Generated files
(`protocol/packets.py`, `products/registry.py`) remain untouched across the whole phase.
`uv run pytest` (1229 tests), `ruff check`, `ruff format --check`, and `pyright` are all clean.
The two fix-commit changes to `factories/builder.py` (a comment clarifying intentional
duplicate `%r` placeholders, and a conditional simplified from
`if self._storage and restorer is not None:` to `if restorer is not None:`) were verified
directly against the `restorer` construction site to be behaviour-preserving, and the new
`test_every_ceiling_product_has_a_compatible_default` registry-wide test passes and closes a
documented review finding (WR-01) without altering any existing must-have.

This report supersedes the prior `01-VERIFICATION.md`, which was accurate in substance but
carried a stale placeholder timestamp (`2026-09-09T00:00:00Z`) that predated the phase's own
commits.

---

_Verified: 2026-09-09T09:27:46Z_
_Verifier: Claude (gsd-verifier)_
