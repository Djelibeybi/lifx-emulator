---
phase: 02-ipv6-transport-and-thread-isolation
plan: 01
subsystem: asyncio-lifecycle
tags: [asyncio, udp, task-tracking, persistence, packet-targets, tdd]

# Dependency graph
requires:
  - phase: 01-thread-device-identity
    provides: "Immutable device connectivity, response-header Thread identity, and persistence foundations"
provides:
  - "Reusable owner-local BackgroundTaskTracker with labelled scheduling, outcome consumption, admission control, explicit reopen, and bounded shutdown"
  - "Strong retention of server packet work and device persistence work with warning-free coroutine refusal paths"
  - "Canonical 12-hex/broadcast target rendering and pinned malformed-datagram statistics"
affects: [02-02-event-bridge, 02-03-family-routing, 02-04-dual-stack-lifecycle]

# Actuals (#2632)
actuals:
  tokens: 7942
  tasks: 3
  commits: 6
plan_head_before: b7c24eb425927f95c6baed3abf566cfb509b6605

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Owner-local task tracker: create, retain, consume outcome, and remove exactly once"
    - "Bounded shutdown: asyncio.wait grace followed by cancel and gather(return_exceptions=True)"
    - "Canonical target rendering: tagged/all-zero broadcast, otherwise target[:6].hex()"

key-files:
  created:
    - packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py
    - packages/lifx-emulator-core/tests/test_background_tasks.py
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/server.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/device.py
    - packages/lifx-emulator-core/tests/test_server.py
    - packages/lifx-emulator-core/tests/test_device.py

key-decisions:
  - "BackgroundTaskTracker accepts work at construction so directly constructed LifxProtocol instances remain compatible; a drained tracker reopens only through explicit start_accepting()."
  - "Scheduling refusal closes the supplied coroutine, while task-creation failure closes it and re-raises the original exception; every non-cancelled outcome is retrieved before removal."
  - "Every operator-visible RX target uses one explicit tagged-or-all-zero broadcast predicate and otherwise renders exactly the first six bytes as lowercase hexadecimal."

patterns-established:
  - "Each long-lived owner constructs its own BackgroundTaskTracker; components share policy, never task collections."
  - "Tests coordinate asynchronous lifetime with events and forced garbage collection rather than timing sleeps."

requirements-completed: [HYG-01, HYG-02]

coverage:
  - id: D1
    description: "Server packet work remains strongly retained across forced garbage collection, replies exactly once, consumes all terminal outcomes, and drains under bounded shutdown."
    requirement: "HYG-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_background_tasks.py::TestBackgroundTaskTracker"
        status: pass
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestProtocolClass::test_protocol_datagram_received"
        status: pass
    human_judgment: false
  - id: D2
    description: "Device persistence uses an owner-local labelled tracker; successful and failed saves execute once without retained work or un-awaited-coroutine warnings."
    requirement: "HYG-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_device.py::TestDeviceBackgroundPersistence"
        status: pass
      - kind: integration
        ref: "uv run pytest test_background_tasks.py test_device.py test_async_storage.py test_thread_identity.py (140 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Unknown warnings, normal RX logs, and PacketEvent activity preserve all 12 serial digits and render tagged/all-zero targets as broadcast."
    requirement: "HYG-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestErrorHandling::test_unknown_target_preserves_all_twelve_hex_digits"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestErrorHandling::test_unknown_target_broadcast_forms_match_all_surfaces"
        status: pass
    human_judgment: false
  - id: D4
    description: "Short and header-unparsable datagrams count one receive/error with no type/activity, while payload-unparsable datagrams count receive/type without changing errors or activity."
    requirement: "HYG-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py -k 'too_short or unparsable'"
        status: pass
      - kind: integration
        ref: "Plan 02-01 focused suite (180 passed) and full repository suite (1252 passed)"
        status: pass
    human_judgment: false

duration: 26min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 1: IPv4 Task Lifetime and Exact Targets Summary

**Owner-local asyncio task retention now protects IPv4 packet and persistence work through completion or bounded shutdown, while one canonical formatter preserves exact 12-digit targets across logs and activity.**

## Performance

- **Duration:** 26 min
- **Started:** 2026-09-10T06:00:33Z
- **Completed:** 2026-09-10T06:26:53Z
- **Tasks:** 3
- **Files modified:** 6 implementation/test files

## Accomplishments

- Added `BackgroundTaskTracker`, which retains each task before returning, consumes success/failure/cancellation exactly once, closes refused coroutines, supports explicit empty-state reopen, and guarantees an empty collection after bounded shutdown.
- Routed directly constructed IPv4 protocol callbacks through the server tracker and migrated device persistence from its bespoke set to a serial-labelled owner-local tracker.
- Unified unknown-warning, normal RX, and activity target text around exact six-byte serial rendering, including trailing-zero serials and both broadcast forms, while pinning malformed-input statistics.
- Verified the plan with 180 focused tests and the repository with 1,252 tests; Ruff formatting/lint and Pyright are clean.

## Task Commits

Each TDD task was committed as a RED test commit followed by its GREEN implementation commit:

1. **Task 1 RED: retained IPv4 tracer and tracker contract** - `1de9928` (test)
2. **Task 1 GREEN: server-owned background task retention** - `73254c3` (feat)
3. **Task 2 RED: tracker terminal matrix and persistence ownership** - `7f91002` (test)
4. **Task 2 GREEN: device persistence outcome tracking** - `8123741` (feat)
5. **Task 3 RED: exact targets and malformed-datagram counters** - `387a286` (test)
6. **Task 3 GREEN: exact packet-target correction** - `d643428` (fix)

**Plan metadata:** commit to follow (docs: complete plan)

## TDD Gate Compliance

- Task 1 RED: `test_background_task_is_retained_until_success` failed on the absent tracker and `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`; the GREEN suite passed 4 tests. The automated-only tracer verification was then rerun and passed before Task 2 began.
- Task 2 RED: 137 tests passed and the three device-persistence ownership tests failed on the old bespoke set/unconsumed failure; the named target returned `RED_EVIDENCE_OK`. GREEN passed all 140 tests.
- Task 3 RED: 13 tests passed and four target-rendering cases failed on padding, legitimate-zero truncation, and all-zero rendering; the named target returned `RED_EVIDENCE_OK`. GREEN passed all 17 selected tests. Its implementation commit uses conventional type `fix` because it corrects the documented HYG-02 defect.

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` - reusable owner-local task scheduling, outcome consumption, admission, reopen, and bounded shutdown
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` - server-owned tracker scheduling and canonical target formatter
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` - device-owned persistence tracker with stable serial-bearing labels
- `packages/lifx-emulator-core/tests/test_background_tasks.py` - deterministic success, failure, cancellation, refusal, creation-failure, grace, timeout, and reopen coverage
- `packages/lifx-emulator-core/tests/test_server.py` - forced-GC protocol tracer, exact operator surfaces, broadcasts, and malformed-input statistics
- `packages/lifx-emulator-core/tests/test_device.py` - retained exactly-once persistence, logged failure, and no-loop warning regression coverage

## Decisions Made

- Kept server tracker admission open from construction to preserve direct `LifxProtocol(server)` usage before `server.start()`; lifecycle plans can stop admission and explicitly reopen only after the collection is empty.
- Used `asyncio.wait()` for the grace period and explicit cancellation plus `gather(return_exceptions=True)` for the remainder, preserving the required two-stage shutdown contract.
- Kept packet bytes and counters unchanged; only the defective operator-visible target representation changed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The restricted command sandbox denied loopback UDP binds in the first baseline run. The identical suite passed when rerun with authorised local-socket access; no test or implementation change was made for the sandbox limitation.
- The full repository suite retained pre-existing standalone-app WebSocket coroutine warnings. Plan 02-02 explicitly owns those files and their tracker migration, so the warning evidence is recorded in `deferred-items.md` without crossing this plan's file boundary.

## User Setup Required

None - no external service configuration or dependency installation is required.

## Next Phase Readiness

- Plan 02-02 can reuse `BackgroundTaskTracker` for WebSocket event-bridge work without sharing the server/device collections.
- Plans 02-03 and 02-04 can route multiple family-specific protocol instances behind the proven retained scheduling and bounded-shutdown policy.
- No IPv6 socket, address-family routing parameter, or public endpoint property was introduced early.

## Self-Check: PASSED

- All six implementation/test files and both newly created tracker files exist.
- All six RED/GREEN task commits resolve in Git.
- `gsd-tools verify-summary` passed its summary, created-file, and commit checks.

---
*Phase: 02-ipv6-transport-and-thread-isolation*
*Completed: 2026-09-10*
