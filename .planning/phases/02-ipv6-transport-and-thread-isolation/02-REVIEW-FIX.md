---
phase: 02-ipv6-transport-and-thread-isolation
fixed_at: 2026-09-10T12:27:22Z
review_path: .planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md
iteration: 3
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-10T12:27:22Z
**Source review:** `.planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md`
**Iteration:** 3

**Summary:**

- Findings in scope: 8
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: Concurrent durable mutations retain and persist a failed request's changes

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/tests/test_api.py`
**Commit:** `81e6c29`
**Status:** fixed: requires human verification
**Applied fix:** Serialised each device's durable mutation transaction, built and validated candidates against the latest committed state inside the lock, persisted before publication, and added a concurrent failure test proving a later request cannot inherit a rejected change.

### CR-02: Cancelling a durable mutation can roll memory back after its disk write commits

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/tests/test_device.py`
**Commit:** `0072690`
**Status:** fixed: requires human verification
**Applied fix:** Shielded executor writes as indivisible operations and deferred cancellation until their outcome was known, with a blocked-write cancellation test asserting memory and disk remain consistent.

### CR-03: Partial bulk-deletion failure deletes durable state for devices retained at runtime

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/src/lifx_emulator/repositories/storage_backend.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`
**Commit:** `271d100`
**Status:** fixed: requires human verification
**Applied fix:** Added transactional bulk deletion that stages every state file before commit and rolls staged files back on failure; repository removal now follows the durable transaction, and tests compare retained file contents after a partial failure.

### CR-04: Debounced batch-write failures are discarded and shutdown reports success

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/tests/test_async_storage.py`
**Commit:** `b0cfcf5`
**Status:** fixed: requires human verification
**Applied fix:** Returned failed snapshots from batch writes, requeued them without replacing newer snapshots, added bounded shutdown retry, and surfaced typed terminal persistence errors. Tests cover transient retry, newer-snapshot preservation, successful shutdown retry, and terminal failure.

### CR-05: A rejected duplicate device can overwrite the accepted device's persisted state

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`, `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py`, `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_device.py`, `packages/lifx-emulator-core/tests/test_server.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`
**Commit:** `d544701`
**Status:** fixed: requires human verification
**Applied fix:** Removed initial persistence side effects from construction, made successful manager admission the sole activation point, explicitly rejected duplicate constructor devices, and added a real shared-storage test proving only the accepted device is persisted.

### CR-06: Public factories accept non-canonical serials that cannot be targeted on the wire

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`, `packages/lifx-emulator-core/tests/test_device.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `f4af292`
**Status:** fixed: requires human verification
**Applied fix:** Required exactly 12 ASCII hexadecimal characters at the shared builder boundary, canonicalised accepted serials to lowercase, and added factory, manager-alias, target-byte, and exact packet-routing tests.

### CR-07: UDP activity can create unbounded WebSocket bridge tasks behind a slow client

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/models.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`, `packages/lifx-emulator/tests/test_websocket.py`
**Commit:** `9eb1455`
**Status:** fixed: requires human verification
**Applied fix:** Replaced per-event bridge tasks with a finite queue and fixed worker pool, reserved capacity before coroutine construction, applied a drop-newest policy with an exposed counter, and added a 5,000-event blocked-client flood test with deterministic shutdown.

### CR-08: Endpoint-loss recovery cannot restart while an old packet task is still pending

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `2507092`
**Status:** fixed: requires human verification
**Applied fix:** Bound protocols to endpoint-generation packet trackers, rotated to a fresh tracker when restart encounters pending old-generation work, retained old generations for shutdown drainage, and tested one-call restart while an old packet task remains blocked.

## Verification

- Verification ran in the isolated review-fix worktree at `.claude/worktrees/rf-02-58748-1789041003`.
- Per-finding focused tests passed before each atomic commit.
- Combined concurrency, cancellation, persistence, serial, bridge, and endpoint-generation suite: `422 passed, 1 warning`.
- Ruff formatting check: 17 changed Python files already formatted.
- Ruff lint check: all checks passed.
- Pyright: `0 errors, 0 warnings, 0 information`.
- All eight commits contain a developer sign-off and a valid GPG signature from Avi Miller.

---

_Fixed: 2026-09-10T12:27:22Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 3_
