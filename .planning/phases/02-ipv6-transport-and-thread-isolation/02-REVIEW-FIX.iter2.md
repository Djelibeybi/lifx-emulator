---
phase: 02-ipv6-transport-and-thread-isolation
fixed_at: 2026-09-10T10:09:05Z
review_path: .planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-10T10:09:05Z
**Source review:** `.planning/phases/02-ipv6-transport-and-thread-isolation/02-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 9
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: `start()` is neither serialised nor transactional

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `f9cc461`
**Applied fix:** Serialised endpoint lifecycle operations with one lock and made startup publication transactional, including rollback of provisional transports, endpoints, device ports, and task admission. Added concurrent-start and commit-failure coverage.

### CR-02: Unexpected endpoint loss is still reported as a live pair

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `738151b`
**Applied fix:** Propagated unexpected protocol loss to the server, invalidated the committed pair under the lifecycle lock, strengthened pair liveness checks, and covered independent IPv4 and IPv6 loss and restart.

### CR-03: Cancelling tracker shutdown leaves admitted work running

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py`, `packages/lifx-emulator-core/tests/test_background_tasks.py`
**Commit:** `e7a9f26`
**Applied fix:** Made cancellation cleanup unconditional, shielded worker collection, consumed all snapshot outcomes, and re-raised caller cancellation only after workers were cancelled and awaited.

### CR-04: Device persistence tasks have no removal or server-shutdown lifecycle

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py`, `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_device_manager.py`, `packages/lifx-emulator-core/tests/test_server.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/tests/test_websocket.py`
**Commit:** `122337b`
**Applied fix:** Added device close and reopen lifecycle operations, made removal APIs asynchronous and transactional, drained persistence before deletion or shutdown, and retained devices when storage deletion fails.

### CR-05: Probabilistic packet-drop logic is evaluated twice

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `6eab3c1`
**Status:** fixed: requires human verification
**Applied fix:** Resolved the scenario and packet-drop decision once in the server before acknowledgement or processing, then passed the accepted decision into device processing. Added a two-draw sentinel test proving one decision and all-or-nothing output.

### CR-06: Declared LIFX frame size is not validated against the datagram

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`, `packages/lifx-emulator-core/tests/test_ipv6_transport.py`
**Commits:** `75b32a1`, `ca296a5`
**Applied fix:** Rejected declared sizes below the header length or unequal to the datagram before target resolution and decoding. Added malformed-size regression coverage and corrected nominal packet fixtures to declare their actual frame length.

### CR-07: Untrusted UDP traffic creates an unbounded number of tasks

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py`, `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `9b596de`
**Applied fix:** Added a configurable positive pending-task limit, rejected overload before coroutine allocation, exposed an overload-drop metric, and covered flood behaviour with blocked handlers.

### WR-01: Statistics and activity report responses that were never sent

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `c001db2`
**Applied fix:** Moved sent counters and observer events after successful `sendto()` calls and returned without accounting when no transport exists. Covered missing and throwing transports.

### WR-02: Uptime is based on adjustable wall-clock time

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/tests/test_device.py`, `packages/lifx-emulator-core/tests/test_server.py`
**Commit:** `e1b8b6a`
**Applied fix:** Switched elapsed device and server uptime to monotonic clocks while retaining the server's wall-clock start timestamp, with deterministic patched-clock tests.

## Verification

- Per-finding focused tests passed before each atomic commit.
- Affected-file suite: `302 passed, 1 warning`.
- Ruff formatting check: 12 files already formatted.
- Ruff lint check: all checks passed.
- All ten fix commits have a developer sign-off and a good GPG signature from key `27B3A9EA9D847501F05627B166D6066620F03B05`.
- Verification ran in the isolated worktree at `.claude/worktrees/rf-02-29450-1789029823`.

---

_Fixed: 2026-09-10T10:09:05Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 1_
