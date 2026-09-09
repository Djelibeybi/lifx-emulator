---
phase: 01-thread-device-identity
plan: 04
subsystem: persistence
tags: [thread, connectivity, persistence, udp-server, scenarios, matrix, multizone]

# Dependency graph
requires:
  - phase: 01-thread-device-identity (Plans 01-03)
    provides: "Connectivity enum, frozen NetworkState.connectivity, LifxHeader.thread_connection, DeviceBuilder.with_connectivity()/_resolve_connectivity(), connectivity on every typed factory, per-tile firmware mirroring"
provides:
  - "connectivity persisted unconditionally in serialize_device_state() output, restored via StateRestorer.peek_connectivity() with a single-read cache"
  - "DeviceBuilder.build() step 1a resolves connectivity precedence: explicit argument > saved value > WiFi, with WARNING on disagreement or unrecognised saved value"
  - "EmulatedLifxServer bytes-aware response-payload branch: malformed_packets/invalid_field_values scenario replies reach the wire instead of raising AttributeError"
  - "Full reply-shape test matrix proving bit 3 on StateColor, both acknowledgement paths, StateUnhandled, multi-packet StateMultiZone, State64 (large + chained matrix), scenario-mutated replies, and a mixed WiFi/Thread fleet"
affects: [phase-02-ipv6-transport]

# Actuals (#2632)
actuals:
  tokens: 10570
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-read StateRestorer cache: _load_saved_state() keyed by serial, shared between peek_connectivity() (step 1a) and restore_if_available() (step 11)"
    - "Bytes-aware response packing: _pack_payload()/_format_packet_fields() in server.py tolerate an already-packed bytes payload from _apply_error_scenarios()"
    - "Recording-transport test double (_RecordingTransport) assigned directly to EmulatedLifxServer.transport for wire-level assertions without binding a socket"

key-files:
  created: []
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py
    - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
    - packages/lifx-emulator-core/src/lifx_emulator/server.py
    - packages/lifx-emulator-core/tests/test_async_storage.py
    - packages/lifx-emulator-core/tests/test_thread_identity.py

key-decisions:
  - "connectivity serialised via str(), not .value, so a NetworkState built with a raw string still serialises correctly; the JSON-substring verify command makes the __str__ = str.__str__ dependency load-bearing and visible"
  - "StateRestorer's single-read cache is deliberately validation-free: peek_connectivity() and restore_if_available() each compare saved_state.get('product') independently, kept in agreement by a code comment rather than a shared filter"
  - "Extended the server.py bytes-aware repair to _format_packet_fields() as well as the payload-packing line: the same root-cause defect (_apply_error_scenarios() returning bytes) crashes the debug-logging helper too, and this crash happens even when track_activity logging is at INFO level, since the argument is evaluated eagerly"
  - "Chained matrix device test uses product 185 (Candle, max_tile_count: 1) with an explicit tile_count=2 to exercise Get64Handler's one-request-many-replies branch; documented in the test docstring as synthetic (the builder does not enforce max_tile_count), since product 55 is the only real chain-capable product and it cannot be Thread"

requirements-completed: [CONN-04, HDR-02, HDR-03]

coverage:
  - id: D1
    description: "connectivity survives the persistence round trip: a Thread device saved and reloaded from disk is still Thread and still sets bit 3, read exactly once per build()"
    requirement: "CONN-04"
    verification:
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_thread_connectivity_round_trips"
        status: pass
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_load_device_state_called_once_per_build"
        status: pass
    human_judgment: false
  - id: D2
    description: "A pre-milestone file (missing key) or a corrupted connectivity value degrades to WiFi -- silently for the missing key, with one WARNING for the corrupted value -- and every other field still restores"
    requirement: "CONN-04"
    verification:
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_missing_connectivity_key_restores_as_wifi"
        status: pass
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_corrupted_connectivity_value_restores_as_wifi_with_warning"
        status: pass
    human_judgment: false
  - id: D3
    description: "An explicit connectivity argument always wins over a saved value, in both directions, with a WARNING naming the serial on disagreement; a product mismatch contributes no connectivity"
    verification:
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_explicit_wifi_argument_wins_over_saved_thread"
        status: pass
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_explicit_thread_argument_wins_over_saved_wifi"
        status: pass
      - kind: unit
        ref: "tests/test_async_storage.py::TestConnectivityPersistence::test_product_mismatch_contributes_no_connectivity"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Thread bit is proved on every reply shape the SPEC enumerates from a single Thread multizone device: StateColor, fast-path Acknowledgement (real server), scenario-path Acknowledgement, StateUnhandled, and every packet of a multi-packet StateMultiZone list"
    requirement: "HDR-02"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestThreadBitOnEveryReplyShapeMultizone::test_thread_multizone_device_sets_bit_on_all_reply_shapes"
        status: pass
      - kind: unit
        ref: "tests/test_thread_identity.py::TestSendAckRealServerWifiAndThread::test_send_ack_thread_and_wifi_bytes"
        status: pass
    human_judgment: false
  - id: D5
    description: "State64 carries bit 3 on a large matrix device (single oversized tile, two Get64 requests) and a chained matrix device (multiple tiles, one Get64 request, many State64 replies)"
    requirement: "HDR-02"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestMatrixThreadBit::test_large_matrix_device_two_get64_requests"
        status: pass
      - kind: unit
        ref: "tests/test_thread_identity.py::TestMatrixThreadBit::test_chained_matrix_device_single_get64_request"
        status: pass
    human_judgment: false
  - id: D6
    description: "Bit 3 stays set on the packets surviving a partial_responses truncation and a malformed_packets truncated reply, at the device level"
    requirement: "HDR-02"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestScenarioMutationPreservesThreadBitDeviceLevel::test_partial_responses_preserve_thread_bit"
        status: pass
      - kind: unit
        ref: "tests/test_thread_identity.py::TestScenarioMutationPreservesThreadBitDeviceLevel::test_malformed_packets_preserve_thread_bit_device_level"
        status: pass
    human_judgment: false
  - id: D7
    description: "A malformed_packets and an invalid_field_values scenario reply reach the real server transport with bit 3 set, instead of raising AttributeError before anything is sent (developer-approved repair of a pre-existing server.py defect)"
    requirement: "HDR-03"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestScenarioMutationReachesTransport::test_malformed_scenario_reaches_transport_with_bit_set"
        status: pass
      - kind: unit
        ref: "tests/test_thread_identity.py::TestScenarioMutationReachesTransport::test_invalid_field_scenario_reaches_transport_with_bit_set"
        status: pass
    human_judgment: false
  - id: D8
    description: "A WiFi and a Thread device in one DeviceManager each answer with their own bit, including through the tagged-broadcast target-resolution path (Phase 2 NET-03 baseline)"
    requirement: "HDR-02"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestMixedFleetThreadAndWifi::test_mixed_fleet_each_device_answers_with_its_own_bit"
        status: pass
    human_judgment: false
  - id: D9
    description: "A WiFi device's four reply shapes are byte-identical to the pre-phase fixtures; every CI-equivalent gate (ruff format, ruff check, pyright, prek/bandit, 80% coverage) passes locally with the generated files, app package, and pyproject.toml/uv.lock/ci.yml untouched"
    requirement: "HDR-03"
    verification:
      - kind: unit
        ref: "tests/test_thread_identity.py::TestWifiWireOutputUnchanged (4 tests)"
        status: pass
      - kind: other
        ref: "uv run ruff format --check . && uv run ruff check . && uv run pyright"
        status: pass
      - kind: other
        ref: "uv run prek run --all-files"
        status: pass
      - kind: other
        ref: "uv run --frozen pytest --cov-fail-under=80 (94.06% total)"
        status: pass
    human_judgment: false

duration: 24min
completed: 2026-09-09
status: complete
---

# Phase 1 Plan 4: Connectivity Persistence and the Full Reply-Shape Proof Summary

**`connectivity` now survives a save-and-reload cycle through a single-read `StateRestorer` peek, and every reply shape the SPEC enumerates — including a pre-existing malformed/invalid-field send-path crash repaired in `server.py` — proves bit 3 on the wire from one Thread multizone device, two matrix devices, and a mixed WiFi/Thread fleet.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-09T08:11:24Z (approx, from STATE.md session marker)
- **Completed:** 2026-09-09T08:35:36Z
- **Tasks:** 3 completed (Task 1 TDD, Task 2 auto, Task 3 verification-only)
- **Files modified:** 6

## Accomplishments

- `serialize_device_state()` now writes `"connectivity"` unconditionally (via `str()`, not `.value`), and `StateRestorer` gained a single-read `_load_saved_state()` cache shared by a new `peek_connectivity()` and the existing `restore_if_available()`.
- `DeviceBuilder.build()` step 1a resolves connectivity with full precedence — explicit argument > saved value > WiFi — logging a `WARNING` on disagreement or an unrecognised saved value, and never raising on a corrupted persisted file.
- Repaired a pre-existing `server.py` defect (present on `main` before this phase): `_apply_error_scenarios()` returns an already-packed `bytes` payload for `malformed_packets`/`invalid_field_values` replies, but `_process_device_packet()` unconditionally called `.pack()` on it, raising `AttributeError` before anything reached the wire. Also found and fixed the same root-cause bug in `_format_packet_fields()`'s debug-logging helper, which crashed on the same bytes payload one line later.
- Built the full SPEC reply-shape test matrix: one all-shapes test on a Thread multizone device (`StateColor`, fast-path ack via the real server, scenario-path ack, `StateUnhandled`, multi-packet `StateMultiZone`), two matrix tests (large matrix device with two `Get64` requests; a synthetic chained matrix device with one `Get64(length=2)`), two scenario-mutation-survives-truncation tests, two scenario-mutation-reaches-transport regression tests (the repair's gate), and a mixed WiFi/Thread `DeviceManager` fleet test including a tagged broadcast baseline for Phase 2's NET-03.
- Confirmed all CI-equivalent gates pass locally with the codebase otherwise untouched: `ruff format --check`, `ruff check`, `pyright`, `prek run --all-files` (including `bandit` and `uv-lock`), and `pytest --cov-fail-under=80` (94.06% total coverage, 1228 tests passing).

## Task Commits

TDD task (Task 1) produced a RED commit and a GREEN commit; Task 2 (auto) produced one commit; Task 3 made no code changes (verification only, all gates already green).

1. **Task 1 RED: failing tests for connectivity persistence round trip** - `01bfa6a` (test)
2. **Task 1 GREEN: connectivity survives the persistence round trip, read once** - `9fb6f0d` (feat)
3. **Task 2: repair malformed-reply send path, prove bit 3 on every reply shape** - `5398dcc` (feat)

**Plan metadata:** commit to follow (docs: complete plan)

## TDD Gate Compliance

Task 1 carried `tdd="true"`. RED phase verified by temporarily reverting the three implementation files to `HEAD` (copy-aside, not `git stash`, per this project's sequential-executor convention) and re-running the new tests: 5 of 7 failed for the intentional reason (missing `"connectivity"` key / `KeyError`, unmodified `_resolve_connectivity` never consulting a restorer). The remaining 2 (`test_product_mismatch_contributes_no_connectivity`, `test_load_device_state_called_once_per_build`) passed unexpectedly against the unmodified code — investigated and confirmed as legitimate unexpected GREENs, not test bugs: the pre-existing "product mismatch skips restore" semantics already defaulted to WiFi with no connectivity persisted at all, and the pre-existing `build()` already called `load_device_state` exactly once (via a single `StateRestorer` construction at the old step 11), so neither behavior regressed by the absence of the new feature — both are pinning tests for behavior this task's change must not break, not tests of the new feature itself. Implementation restored, all 7 new tests passed GREEN. Both `test(01-04): ...` and `feat(01-04): ...` gate commits exist in the log (`git log --oneline -E --grep="^test\(01-04\):"` / `--grep="^feat\(01-04\):"` both match).

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py` - `"connectivity": str(device_state.connectivity)` added to the unconditional dict literal
- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py` - `_load_saved_state()` single-read cache, `peek_connectivity()`, `restore_if_available()` now routes through the cache
- `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` - module `logger`, restorer constructed once in `build()` and reused at step 11, `_resolve_connectivity()` extended to full D-09/D-10 precedence
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` - `_pack_payload()` helper, bytes-aware branch in `_process_device_packet()`'s response loop, bytes-aware branch in `_format_packet_fields()`
- `packages/lifx-emulator-core/tests/test_async_storage.py` - `TestConnectivityPersistence` (7 tests: round trip, missing key, corrupted value, explicit-wins both directions, product mismatch, single-read)
- `packages/lifx-emulator-core/tests/test_thread_identity.py` - `_RecordingTransport` double; `TestThreadBitOnEveryReplyShapeMultizone`, `TestSendAckRealServerWifiAndThread`, `TestScenarioMutationReachesTransport`, `TestScenarioMutationPreservesThreadBitDeviceLevel`, `TestMatrixThreadBit`, `TestMixedFleetThreadAndWifi` (10 new tests)

## Decisions Made

- **`str()` over `.value` for serialisation** (kept from plan, reaffirmed): a caller who builds a `NetworkState` with a raw `"thread"` string still serialises correctly under `str()`; `.value` would raise `AttributeError` on that path. The exact-substring verify command (`"connectivity": "thread"`) makes `Connectivity.__str__ = str.__str__` load-bearing rather than incidental.
- **Extended the `server.py` repair to `_format_packet_fields()`**: discovered while writing the server-level regression tests — the debug-logging helper crashes on the same bytes payload immediately after the packing line succeeds, because its argument (`_format_packet_fields(resp_packet)`) is evaluated eagerly regardless of the configured log level. This is the same root cause (`_apply_error_scenarios()` returning bytes) surfacing at a second call site; fixing only the packing line would still leave `AttributeError` propagating out of `_process_device_packet()` when called directly (as this task's regression tests do), and would still increment `error_count` silently in production via `handle_packet()`'s outer `try/except` even though the datagram had already reached the wire. Scoped narrowly (one `isinstance` guard, one docstring cross-reference) and does not touch `_send_ack`, the statistics counters, or the observer notification.
- **Chained matrix device is synthetic**: product 185 (Candle, `max_tile_count: 1`) built with an explicit `tile_count=2` to exercise `Get64Handler`'s one-request-many-replies branch. Product 55 is the only registry product whose `specs.yml` declares `max_tile_count > 1`, and it cannot be Thread (terminal firmware 3.50 sits below the Thread floor 4.200), so no real Thread product ships as a chain. The test docstring says so explicitly.
- **Task 3 made no source changes**: every CI-equivalent gate (ruff format/check, pyright, prek/bandit, 80% coverage) was already green after Tasks 1-2, so Task 3 is verification-only with no commit of its own.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_format_packet_fields()` crashes on the same bytes payload `_pack_payload()` was built to tolerate**
- **Found during:** Task 2, while writing `TestScenarioMutationReachesTransport` (the server-level regression tests for the named `server.py` repair)
- **Issue:** After the `_pack_payload()` fix let a malformed/invalid-field reply's `bytes` payload pack correctly and reach `transport.sendto(...)`, the very next statement in the same loop — `resp_fields_str = _format_packet_fields(resp_packet)`, used for a `logger.debug(...)` call — raised the identical `AttributeError: 'bytes' object has no attribute '_fields'`, because Python evaluates the argument eagerly regardless of whether DEBUG logging is enabled.
- **Fix:** Added an `isinstance(packet, bytes)` guard at the top of `_format_packet_fields()` returning `f"<{len(packet)} raw bytes>"`, with a comment cross-referencing `_pack_payload()`'s docstring for the shared root cause.
- **Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`
- **Verification:** `TestScenarioMutationReachesTransport`'s two tests pass; reverting only this guard (with the `_pack_payload()` fix still in place) reproduces the crash, confirming both fixes are independently necessary.
- **Committed in:** `5398dcc` (part of Task 2's commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix). **Impact:** Necessary for correctness — without it, the task's own regression tests (and any real scenario-driven client exercising a malformed/invalid-field reply against a running server) would still crash after the datagram was sent, silently inflating `error_count`. No scope creep beyond the same root-cause defect this task was already repairing.

## Authentication Gates

None - no external service configuration required.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Acceptance-Criteria-to-Test Mapping (01-SPEC.md, 31 total: 27 positive + 4 must-NOT)

| # | Criterion (abbreviated) | Test module :: function |
|---|---|---|
| 1 | Omitted/None connectivity -> wifi (all factories) | `test_thread_identity.py::TestConnectivityFactory::test_default_is_wifi`, `::TestTypedFactoryConnectivity::test_connectivity_forwarding_and_firmware` |
| 2 | connectivity="thread" works except create_tile_device raises | `test_thread_identity.py::TestConnectivityFactory::test_explicit_thread`, `::TestTypedFactoryConnectivity::test_connectivity_forwarding_and_firmware` (succeeds=False case for create_tile_device) |
| 3 | "Thread"/"bluetooth" raise ValueError | `test_thread_identity.py::TestConnectivityFactory::test_invalid_connectivity_raises` |
| 4 | Assigning state.connectivity raises | `test_thread_identity.py::TestConnectivityImmutability` (3 tests) |
| 5 | Thread device no firmware -> (4,200) incl. Ceiling | `test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_default_for_product_with_no_specs_default`, `::test_thread_default_overrides_specs_default` |
| 6 | Explicit (4,200)/(5,0) accepted | `test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_explicit_override_at_floor_accepted`, `::test_thread_explicit_override_above_floor_accepted` |
| 7 | Explicit (4,199)/(3,70) raise | `test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_override_just_below_floor_raises`, `::test_thread_override_well_below_floor_raises` |
| 8 | Product 55 default (3,50); (3,50) OK, (3,51) raises | `test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_override_at_ceiling_accepted`, `::test_tile_override_above_ceiling_raises` |
| 9 | create_device(55, thread) raises | `test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_on_thread_names_both_bounds` |
| 10 | Every matrix product except 55 accepts thread | `test_thread_identity.py::TestThreadOnTileRejectionRegistryWide` (2 tests) |
| 11 | Two SKY tests migrated off product 55 | `test_tile_handlers_extended.py::test_sky_effect_on_non_ceiling_tile_device`, `::test_other_effects_on_non_ceiling_still_work` (product 185) |
| 12 | Thread wifi_signal 0.0, GetWifiInfo | `test_thread_identity.py::TestWifiSignalDerivation::test_thread_wifi_signal_is_zero`, `::TestThreadIdentitySurface::test_thread_device_identity_surface` |
| 13 | GetHostFirmware/GetWifiFirmware same shapes | `test_thread_identity.py::TestThreadIdentitySurface::test_thread_device_identity_surface` |
| 14 | WiFi wifi_signal -45.0 | `test_thread_identity.py::TestWifiSignalDerivation::test_wifi_wifi_signal_is_minus_45` |
| 15 | Thread 4.200 ambient_light_lux 100.0 | `test_thread_identity.py::TestThreadIdentitySurface::test_thread_device_identity_surface` |
| 16 | Tiles mirror host firmware (Thread Ceiling 4.200, WiFi Ceiling 4.10, WiFi Candle 3.70) | `test_tile_handlers_extended.py::TestTileFirmwareMirrorsHost` (3 tests) |
| 17 | serialize_device_state has "connectivity"; Thread reload keeps bit 3 | `test_async_storage.py::TestConnectivityPersistence::test_thread_connectivity_round_trips` |
| 18 | Missing key -> wifi | `test_async_storage.py::TestConnectivityPersistence::test_missing_connectivity_key_restores_as_wifi` |
| 19 | "bluetooth" -> wifi + WARNING | `test_async_storage.py::TestConnectivityPersistence::test_corrupted_connectivity_value_restores_as_wifi_with_warning` |
| 20 | thread_connection default False, packs/unpacks the bit | `test_header.py::TestThreadConnectionBit::test_default_is_false`, `::test_set_bit_differs_only_in_byte_22`, `::test_unpack_round_trips_both_values` |
| 21 | False packs identical to fixture, bits 2/4-7 zero | `test_header.py::TestHeaderByteFixture::test_pack_matches_pre_phase_fixture`, `::test_reserved_bits_of_byte_22_are_clear`; `::TestThreadConnectionBit::test_reserved_bits_stay_zero_when_bit_set` |
| 22 | unpack() <36 bytes raises | `test_header.py::TestHeaderByteFixture::test_unpack_short_data_raises` |
| 23 | All-shapes multizone test + two matrix tests (amended, 3 test functions) | `test_thread_identity.py::TestThreadBitOnEveryReplyShapeMultizone::test_thread_multizone_device_sets_bit_on_all_reply_shapes`, `::TestMatrixThreadBit::test_large_matrix_device_two_get64_requests`, `::test_chained_matrix_device_single_get64_request` |
| 24 | Bit 3 survives partial_responses and malformed_packets truncation | `test_thread_identity.py::TestScenarioMutationPreservesThreadBitDeviceLevel` (2 tests) |
| 25 | Mixed WiFi/Thread fleet, each own bit | `test_thread_identity.py::TestMixedFleetThreadAndWifi::test_mixed_fleet_each_device_answers_with_its_own_bit` |
| 26 | WiFi byte fixtures match pre-phase | `test_thread_identity.py::TestWifiWireOutputUnchanged` (4 tests) |
| 27 | All pre-existing tests pass; ruff/pyright/coverage gates pass | Full suite: `uv run --frozen pytest --cov-fail-under=80` (1228 passed, 94.06% coverage); `uv run ruff format --check .`; `uv run ruff check .`; `uv run pyright` (all exit 0) |
| MUST-NOT 1 | No silent Thread<->WiFi conversion except bad-persisted-value fallback (warns) | `test_thread_identity.py::TestConnectivityImmutability`; `test_async_storage.py::TestConnectivityPersistence::test_explicit_wifi_argument_wins_over_saved_thread`, `::test_explicit_thread_argument_wins_over_saved_wifi`, `::test_corrupted_connectivity_value_restores_as_wifi_with_warning` |
| MUST-NOT 2 | No product ID other than 55 rejected for thread | `test_thread_identity.py::TestThreadOnTileRejectionRegistryWide::test_only_product_55_is_rejected_registry_wide` |
| MUST-NOT 3 | No WiFi reply/header round trip differs from pre-phase fixtures | `test_thread_identity.py::TestWifiWireOutputUnchanged` (4 tests); `test_header.py::TestHeaderByteFixture` |
| MUST-NOT 4 | `git diff main -- protocol/packets.py products/registry.py` empty | Verified: `git diff main --stat -- packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` produces no output |

## Confirmation: Untouched Files

- `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py` - untouched (verified via `git diff main --stat`)
- `packages/lifx-emulator-core/src/lifx_emulator/handlers/` - untouched (verified via `git diff main --stat`)
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py` - untouched (generated file)
- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` - untouched (generated file)
- `pyproject.toml`, `uv.lock` - untouched
- `.github/workflows/ci.yml` - untouched
- `packages/lifx-emulator/` (standalone app package) - untouched

## Single-Read Mechanism (as implemented)

`DeviceBuilder.build()` constructs one `StateRestorer(self._storage)` (if storage is configured) before step 1a, holds it in a local `restorer: StateRestorer | None`, and passes it to `_resolve_connectivity(serial, restorer)`. `StateRestorer._load_saved_state(serial)` caches by serial (`_cached_serial`/`_cached_saved_state`) and only calls `self.storage.load_device_state(serial)` when the cache misses. Step 11 reuses the same `restorer` instance for `restore_if_available()`, so the file is read exactly once per `build()` call — confirmed by `test_load_device_state_called_once_per_build`'s monkeypatched counting wrapper.

## Product-Mismatch Peek Decision

`peek_connectivity()` returns `None` when `saved_state.get("product") != product`, matching the "skipping restore" semantics `restore_if_available()` already applies to every other field. Both checks are independent (the cache itself is validation-free, by design) but must stay in agreement — documented with a code comment rather than a shared filter, so a future reader does not "optimise" the cache into pre-filtering.

## Recording-Transport Shape

`_RecordingTransport` is a small test-only class with one method, `sendto(data, addr)`, that appends `(data, addr)` to a list. It is assigned directly to `server.transport` (a plain attribute initialised to `None` in `EmulatedLifxServer.__init__`), so no socket is ever bound. Used for the fast-path `_send_ack()` assertion and both scenario-mutation-reaches-transport regression tests.

## Matrix Cases and Why the Ceiling Is Not a Chain

- **Large matrix device** (product 201, LIFX Ceiling 13x26"): a single 16x8 tile (`max_tile_count: 1`). Reading its 128 zones takes **two** `Get64` requests (`rect` at `y=0` then `y=4`, both `width=16`, `length=1`), each answered by exactly one 64-colour `State64`.
- **Chained matrix device** (product 185, LIFX Candle, built with explicit `tile_count=2`): **one** `Get64(tile_index=0, length=2, ...)` request answered by **two** `State64` replies — `Get64Handler` emits one `State64` per requested tile index. This is synthetic: product 55 is the only registry product whose `specs.yml` declares `max_tile_count > 1`, and it cannot be Thread, so no real Thread product ships as a chain. The builder does not enforce `max_tile_count`, which is what makes the synthetic construction possible; the test docstring says so.

## `server.py` Bytes Branch — Exact Shape

```python
def _pack_payload(resp_packet: Any) -> bytes:
    if not resp_packet:
        return b""
    if isinstance(resp_packet, bytes):
        return resp_packet
    return resp_packet.pack()
```

Used at the response-payload line in `_process_device_packet()`'s send loop (`resp_payload = _pack_payload(resp_packet)`). No `_pack_payload` complexity issue arose (the function is 4 branches, well under the McCabe budget), so no further extraction was needed there. A second, independent `isinstance(packet, bytes)` guard was added at the top of `_format_packet_fields()` for the same root cause (see Deviations). `_send_ack`, the statistics counters, and the observer notification are all unchanged.

## Final Coverage

**94.06%** total (gate: 80%). All 1228 tests pass. No file under `packages/lifx-emulator-core/src/lifx_emulator/` needed additional coverage tests to clear the gate.

## Next Phase Readiness

Phase 1 (Thread Device Identity) is complete: `connectivity` is a first-class, persisted, single-read-restored property of every device; every reply shape a Thread device can produce carries bit 3 correctly, including scenario-mutated and multi-packet replies; and a WiFi device's wire output is proven byte-identical to the pre-phase baseline. Phase 2 (IPv6 transport) can build directly on `Connectivity`, the mixed-fleet `DeviceManager` test (a recorded both-answer baseline for NET-03's tagged-packet drop rule), and the now-complete persistence round trip. No blockers.

---
*Phase: 01-thread-device-identity*
*Completed: 2026-09-09*

## Self-Check: PASSED

All claimed files and commit hashes verified present on disk / in git log.
