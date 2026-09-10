---
phase: 02-ipv6-transport-and-thread-isolation
reviewed: 2026-09-11
depth: deep
base_commit: f31310e07c9193a90ad3f6aed529fac46417713e
pr: 218
files_reviewed: 15
files_reviewed_list:
  - packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/device.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py
  - packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py
  - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
  - packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py
  - packages/lifx-emulator-core/src/lifx_emulator/repositories/storage_backend.py
  - packages/lifx-emulator-core/src/lifx_emulator/server.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/app.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/models.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/routers/monitoring.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py
  - packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
resolved_findings: 3
status: clean
---

# Phase 2: PR Code Review

## Summary

Reviewed the complete PR production-source diff against main, including transport routing, task ownership, persistence, REST services and WebSocket delivery. Three additional correctness defects were found and fixed with regression coverage. No unresolved actionable finding remains from this review. Earlier review reports remain in Git history and iteration artefacts.

## Narrative Findings (AI reviewer)

### CR-01: Durable commits overwrite interleaved protocol mutations — resolved

**Classification:** BLOCKER.
**File:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `apply_state_mutation`.
**Evidence:** Blocking a durable power write, applying UDP SetLabel, then releasing the write restored the old label. The durable lock serialised only durable callers; the synchronous protocol path could publish newer state during disk I/O.
**Fix:** Detect replacement of the source state after I/O and reapply the durable mutation to the latest state before publication.
**Regression:** `test_durable_commit_preserves_interleaved_protocol_mutation` uses the actual packet handler and blocked real storage write, checking memory and disk.

### CR-02: Cancelled bulk deletion removes files for retained devices — resolved

**Classification:** BLOCKER.
**File:** `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `delete_device_states`.
**Evidence:** Cancelling while executor deletion is blocked reopens retained devices and releases the storage lock, but the executor subsequently deletes their files.
**Fix:** Await the executor transaction indivisibly under the storage lock, matching durable-write cancellation semantics. Repository removal or reopening follows the real transaction outcome.
**Regression:** `test_cancelled_bulk_delete_waits_for_transaction_outcome` checks success and failure after cancellation, including lock ownership, files and repository state.

### CR-03: Rejected durable candidates can persist during shutdown — resolved

**Classification:** BLOCKER.
**File:** `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, durable write path.
**Evidence:** Ordinary flush restores failed snapshots to the pending queue. Using it for an uncommitted REST candidate allowed shutdown to persist state that the request failed to commit.
**Fix:** Add `commit_device_state` to the storage contract. It writes a candidate directly and only supersedes queued state after success; failed candidates never enter the retry queue.
**Regression:** `test_failed_durable_candidate_is_never_retried_on_shutdown` injects a real backend write failure, then compares memory and disk after shutdown.

## CI Repairs

- Replace six production assertions with explicit runtime checks.
- Use Python 3.10-compatible asyncio timeout exceptions and bounded waits.
- Require full serial matches and enforce resolved-path containment inside storage, including symlink escape regression coverage.
- Cover storage rollback, cleanup failures, explicit flush retry, tracker admission, WebSocket worker recovery and invalid deletion results.
- Move imports in touched modules to module scope.

## Verification

- Full Python 3.14 and Python 3.10 suites: 1,400 passed on each interpreter.
- Changed executable lines compared against `origin/main`: zero missing lines and zero partial branches in local coverage.
- Added failure-boundary coverage for endpoint startup and loss, repository removal, persistence admission, creation rollback and WebSocket queue initialisation.
- Removed unreachable startup fallthrough and redundant postcondition checks; bounded collision retries are preserved.
- Ruff lint/format, Pyright and Bandit passed.
- Final GitHub and Codecov results must be checked on the pushed commit; local coverage does not assert those remote gates have passed.

Review performed inline using the gsd-code-reviewer guidance.
