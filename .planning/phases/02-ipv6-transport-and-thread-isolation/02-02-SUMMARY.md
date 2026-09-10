---
phase: 02-ipv6-transport-and-thread-isolation
plan: 02
subsystem: websocket-lifecycle
tags: [asyncio, fastapi, websocket, task-tracking, lifespan, tdd]

# Dependency graph
requires:
  - phase: 02-ipv6-transport-and-thread-isolation
    plan: 01
    provides: "Reusable owner-local BackgroundTaskTracker with labelled scheduling and bounded shutdown"
provides:
  - "Backward-compatible tracker injection for every synchronous WebSocket event bridge"
  - "Exact device, activity, and state-change operation labels with unchanged broadcast payloads"
  - "One application-owned bridge tracker with open construction admission and deterministic FastAPI lifespan drain"
affects: [02-04-dual-stack-lifecycle, websocket-events, fastapi-shutdown]

# Actuals (#2632)
actuals:
  tokens: 8296
  tasks: 2
  commits: 4
plan_head_before: 59f1efb225e82d64dd78da83c5580f98a326119d

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Synchronous callbacks submit labelled coroutines to an injected owner-local BackgroundTaskTracker"
    - "FastAPI lifespan stops producers before a five-second graceful drain and cancellation boundary"

key-files:
  created: []
  modified:
    - packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py
    - packages/lifx-emulator/src/lifx_emulator_app/api/app.py
    - packages/lifx-emulator/tests/test_websocket.py

key-decisions:
  - "Every bridge entry point preserves its positional arguments and accepts only an optional keyword-only task_tracker; omission creates an accepting adapter-local fallback with a DEBUG lifecycle diagnostic."
  - "create_api_app constructs its shared tracker open for direct and non-lifespan clients, reopens it idempotently on each lifespan entry, then stops StatsBroadcaster before bounded tracker shutdown."

patterns-established:
  - "Operation labels are exact colon-separated values: device-added:<serial>, device-removed:<serial>, activity:<direction>:<pkt_type>, and device-updated:<serial>:<pkt_type>."
  - "StatsBroadcaster retains its separate awaited task lifecycle because its broadcasts are not fire-and-forget bridge work."

requirements-completed: [HYG-01]

coverage:
  - id: D1
    description: "All five synchronous event-bridge operation families schedule unchanged WebSocket payloads through injected or adapter-local trackers with exact labels and preserved delegate order."
    requirement: "HYG-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator/tests/test_websocket.py::TestEventBridge"
        status: pass
      - kind: integration
        ref: "uv run --frozen pytest packages/lifx-emulator/tests/test_websocket.py -q --no-cov -k 'event_bridge or activity_observer or state_change' (12 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Forced collection loses no device-added broadcast, failures are consumed and logged once, and completed work leaves no retained tasks or un-awaited coroutine warnings."
    requirement: "HYG-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator/tests/test_websocket.py::TestEventBridge::test_device_added_bridge_survives_forced_collection"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator/tests/test_websocket.py::TestEventBridge::test_activity_delegate_precedes_schedule_and_failure_is_logged_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "One open app-owned tracker is shared by every adapter; non-lifespan construction accepts work while normal, exceptional, and repeated lifespans stop stats first and drain or cancel all bridge work."
    requirement: "HYG-01"
    verification:
      - kind: integration
        ref: "packages/lifx-emulator/tests/test_websocket.py::TestEventBridgeLifespan"
        status: pass
      - kind: integration
        ref: "uv run --frozen pytest packages/lifx-emulator/tests/test_websocket.py packages/lifx-emulator/tests/test_api.py -q --no-cov (123 passed)"
        status: pass
      - kind: integration
        ref: "uv run --frozen pytest -q --no-cov (1263 passed)"
        status: pass
    human_judgment: false

duration: 24min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 2: WebSocket Bridge Task Ownership Summary

**Every synchronous WebSocket bridge callback now has strong, labelled task ownership, while one FastAPI application tracker preserves direct-client admission and guarantees stop-before-drain teardown.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-10T06:35:46Z
- **Completed:** 2026-09-10T06:59:28Z
- **Tasks:** 2
- **Files modified:** 3 implementation/test files

## Accomplishments

- Replaced the bare bridge scheduler with optional keyword-only `BackgroundTaskTracker` injection across device lifecycle, activity, and state-change adapters without changing existing positional construction or WebSocket payloads.
- Added exact operation labels, owner-local fallback diagnostics, forced-GC retention, synchronous delegate-order, and exactly-once failure-observation coverage for every bridge operation family.
- Added one open application-owned tracker, exposed it for diagnostics, shared it across all adapters, and made every FastAPI lifespan stop the periodic stats producer before a five-second drain and cancellation boundary.
- Verified 123 focused API/WebSocket tests and all 1,263 repository tests; no event-bridge coroutine/task `RuntimeWarning` remains.

## Task Commits

Each TDD task was committed as a RED test commit followed by its GREEN implementation commit:

1. **Task 1 RED: bridge tracker signatures, labels, retention, ordering, and failures** - `85a4ab6` (test)
2. **Task 1 GREEN: tracked bridge callbacks with compatible fallbacks** - `b84be85` (feat)
3. **Task 2 RED: app ownership, admission, repeated lifespan, and cancellation** - `450452a` (test)
4. **Task 2 GREEN: shared app tracker and bounded lifespan drain** - `2eac0ea` (feat)

**Plan metadata:** commit to follow (docs: complete plan)

## TDD Gate Compliance

- Task 1 RED: `test_event_bridge_entry_points_have_optional_keyword_only_tracker` failed because the old entry points had no tracker parameter; `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed 12 focused tests, and the automated-only tracer verification was rerun successfully before Task 2.
- Task 2 RED: `test_create_api_app_exposes_open_background_task_tracker` failed because the factory did not expose an application tracker; `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed all 123 API/WebSocket tests.

## Files Created/Modified

- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` - compatible owner-local/injected task scheduling with exact operation labels and unchanged payloads
- `packages/lifx-emulator/src/lifx_emulator_app/api/app.py` - one shared application tracker with open construction admission, lifespan reopen, and stop-before-drain teardown
- `packages/lifx-emulator/tests/test_websocket.py` - signature, label, payload, fallback, forced-GC, failure, non-lifespan, and lifespan regression coverage

## Decisions Made

- Preserved legacy direct construction by making `task_tracker` optional and keyword-only, with each omitted tracker owned by the adapter that captures it rather than by module-global state.
- Kept `StatsBroadcaster` on its existing explicitly awaited task because it is a producer with its own lifecycle; application teardown stops it before draining fire-and-forget broadcasts.
- Kept the production tracker open from app construction for non-context-managed `TestClient` compatibility, while every entered lifespan establishes the deterministic drain boundary and supports later re-entry.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The Task 2 RED commit hook corrected one import-order issue; the corrected file was restaged explicitly and all hooks then passed.
- The restricted sandbox denied local UDP binds during the first full regression run. The unchanged suite passed with authorised loopback access: 1,263 tests passed. No source or test behaviour was altered for the sandbox limitation.

## User Setup Required

None - no dependency installation or external service configuration is required.

## Next Phase Readiness

- Plan 02-04 can compose application shutdown with the core server lifecycle using the same proven producer-stop, task-drain, and cancellation order.
- HYG-01 is complete across the standalone WebSocket bridge: all callback tasks are retained, observed, and empty after application lifespan teardown.

## Self-Check: PASSED

- All three implementation/test files and this summary exist.
- All four RED/GREEN task commits resolve in Git and contain GPG signature material plus developer sign-off.
- `gsd-tools verify-summary` passed its summary, created-file, and commit checks.

---
*Phase: 02-ipv6-transport-and-thread-isolation*
*Completed: 2026-09-10*
