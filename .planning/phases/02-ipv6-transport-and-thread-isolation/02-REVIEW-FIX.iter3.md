---
phase: 02-ipv6-transport-and-thread-isolation
fixed_at: 2026-09-10T11:18:24Z
review_path: .planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md
iteration: 2
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-10T11:18:24Z
**Source review:** `.planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md`
**Iteration:** 2

**Summary:**

- Findings in scope: 7
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: A delayed storage flush can resurrect a deleted device

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/src/lifx_emulator/repositories/storage_backend.py`, `packages/lifx-emulator-core/tests/test_async_storage.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`
**Commit:** `4b1bd1f`
**Status:** fixed: requires human verification
**Applied fix:** Serialised per-device deletion with queued and in-flight writes under the storage lock, awaited it from both manager removal paths, and added real-backend single and bulk resurrection tests.

### CR-02: Production deletion failures are reported as successful removals

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/tests/test_async_storage.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`
**Commit:** `abadaa8`
**Status:** fixed: requires human verification
**Applied fix:** Added a typed persistence exception carrying failed serials, made production deletion results explicit, surfaced partial bulk failures, and retained and reopened live devices whenever durable deletion fails.

### CR-03: Cancelling removal can permanently disable persistence on a retained device

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`
**Commit:** `fca7bb9`
**Status:** fixed: requires human verification
**Applied fix:** Moved device closing inside the rollback boundary, tracked each closed device, and reopened every retained device after cancellation or failure. Added single and partial-bulk cancellation tests proving persistence resumes.

### CR-04: A rejected state PATCH can leave earlier fields mutated

**Files modified:** `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/tests/test_api.py`
**Commit:** `5d8abd2`
**Status:** fixed: requires human verification
**Applied fix:** Validated the complete request before mutation, applied valid changes to a deep copy, and committed only the complete candidate state. Added compound invalid-zone and invalid-tile rollback tests.

### CR-05: Successful REST state updates are lost on restart and invisible to WebSocket clients

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `packages/lifx-emulator-core/src/lifx_emulator/repositories/storage_backend.py`, `packages/lifx-emulator-core/tests/test_device.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`, `packages/lifx-emulator/tests/test_api.py`
**Commit:** `3d2c94d`
**Status:** fixed: requires human verification
**Applied fix:** Introduced one public device mutation transaction for protocol and REST callers, made REST persistence durable before success, rolled back failed commits, and emitted one full-state WebSocket event after durable commit. Added an integration test comparing disk, HTTP, and WebSocket snapshots.

### CR-06: Duplicate creation can overwrite existing persisted state

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`, `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/tests/test_api.py`
**Commit:** `38b69d9`
**Status:** fixed: requires human verification
**Applied fix:** Deferred initial persistence until repository admission, serialised insertion, closed rejected candidates, and retried generated collisions. Added real-backend tests proving explicit and generated collisions do not alter existing state.

### WR-01: REST ServerStats drops packets_dropped_overload

**Files modified:** `packages/lifx-emulator/src/lifx_emulator_app/api/models.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/monitoring.py`, `packages/lifx-emulator/tests/test_api.py`
**Commit:** `360ab0d`
**Applied fix:** Added the non-negative overload-drop counter to the REST response model and OpenAPI description, with an endpoint test asserting the live counter value survives response filtering.

## Verification

- Per-finding focused tests passed before each atomic commit.
- Combined Phase 02 and production-persistence suite: `407 passed, 1 warning`.
- Ruff formatting check: 17 files already formatted.
- Ruff lint check: all checks passed.
- Pyright: `0 errors, 0 warnings, 0 information`.
- All seven fix commits have a developer sign-off and a good GPG signature from key `27B3A9EA9D847501F05627B166D6066620F03B05`.
- Verification ran in the isolated worktree at `.claude/worktrees/rf-02-78757-1789036599`; the socket tests were rerun with local IPv4/IPv6 loopback access after the restricted sandbox correctly denied binds.

---

_Fixed: 2026-09-10T11:18:24Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 2_
