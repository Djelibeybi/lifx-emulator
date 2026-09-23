---
phase: 03-mdns-responder
reviewed: 2026-09-23T09:31:56Z
depth: deep
files_reviewed: 19
files_reviewed_list:
  - .github/workflows/ci.yml
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
  - packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py
  - packages/lifx-emulator/tests/test_websocket.py
  - scripts/prepare_mdns_oracle.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 3: Code Review Report

**Reviewed:** 2026-09-23T09:31:56Z
**Depth:** deep
**Files Reviewed:** 19
**Status:** clean

## Summary

The Phase 3 responder, server lifecycle, device registry, factory validation and production-evidence boundary were reviewed from base `26af0a4` through the current working tree. The review traced startup, live add/remove/re-add, supported-operation failure, cancellation, shutdown, retry and listener coexistence across module boundaries. Production code uses the public zeroconf surface only. The accepted D-08 boundary is represented honestly: `running` is lifecycle state and the implementation does not claim silent listener-health detection.

Two defects were found adversarially and fixed during the review. The current tree has no open Critical, Warning or Info findings.

## Narrative Findings (AI reviewer)

No open findings remain.

## Resolved During Review

### RESOLVED BLOCKER R-01: Shutdown discarded an admitted zeroconf failure

**Files:** `packages/lifx-emulator-core/src/lifx_emulator/mdns.py:142`, `packages/lifx-emulator-core/src/lifx_emulator/mdns.py:224`, `packages/lifx-emulator-core/src/lifx_emulator/server.py:999`

**Issue:** A reconcile operation could fail after `stop()` closed tracker admission. `_run_reconcile()` retained the exception locally but suppressed the server callback because admission was closed; `BackgroundTaskTracker.shutdown()` then consumed and logged the task exception. Cleanup completed successfully, so `server.stop()` returned success with `mdns_status == stopped` and `mdns_error is None`. A deterministic held-register reproduction produced exactly this false-success state.

**Fix applied:** `MdnsResponder.stop()` now carries a non-cancellation `_error` through unregister/close cleanup and raises it after cleanup, allowing `_stop_mdns_locked()` to retain the failure and publish `failed`. `test_stop_retains_admitted_operation_failure` releases a failing second-stage register only after shutdown has closed admission and asserts the failure remains observable.

### RESOLVED WARNING R-02: Wholesale network replacement bypassed fixed-at-creation mDNS state

**File:** `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:506`

**Issue:** Direct writes to `state.mdns_enabled`, `state.mdns_address` and the frozen `NetworkState` were rejected, but `DeviceState.__setattr__()` still allowed callers to replace `state.network` wholesale. A caller could therefore change advertisement eligibility or inject an invalid address without removing and recreating the device. The current advertisement would remain stale until an unrelated membership change triggered reconciliation, at which point the responder could silently remove the device or fail.

**Fix applied:** Post-initialisation replacement of `DeviceState.network` now raises `ValueError`. Parameterised tests cover replacement attempts for both `mdns_enabled` and `mdns_address`.

## Validation

- `git diff --check` passed.
- Ruff passed across the reviewed production, integration and oracle-preparation files.
- The bounded review suite passed: 186 passed, 4 skipped. The four skips are the explicitly gated `MDNS_INTEGRATION_REQUIRED=1` cases; the CI job enables required mode and rejects skipped cases.
- The required pristine-oracle integration passed all four fleet cases (0, 1, 10 and 100 devices), including IPv4/IPv6 power queries and membership re-add.
- The full local suite passed: 1,474 passed with the same four explicitly environment-gated integration skips.
- The configured root Pyright and Ruff checks passed.
- `prepare_mdns_oracle.py --help` completed successfully. Static review confirmed exact revision and tree verification, pristine-checkout enforcement, bounded subprocess calls and no mutation of sibling checkouts.

---

_Reviewed: 2026-09-23T09:31:56Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
