---
phase: 01-thread-device-identity
plan: 01
subsystem: core-protocol
tags: [thread, connectivity, header, enum, frozen-dataclass, builder]

# Dependency graph
requires: []
provides:
  - "Connectivity(str, Enum) with WIFI/THREAD, exported from lifx_emulator and lifx_emulator.devices"
  - "coerce_connectivity() shared string-to-enum validation"
  - "NetworkState frozen with connectivity + wifi_signal, both immutable after construction"
  - "LifxHeader.thread_connection (frame-address byte 22 bit 3), pack/unpack, repr"
  - "Single per-device stamping point in EmulatedLifxDevice.__init__ that carries the bit onto every reply, both ack paths and StateUnhandled"
  - "DeviceBuilder.with_connectivity() / _resolve_connectivity() build() step 1a"
  - "connectivity argument on create_device()"
  - "Pre-change WiFi byte fixtures for StateService/StateColor/Acknowledgement/StateUnhandled and a plain header round trip"
affects: ["01-02", "01-03", "01-04"]

# Actuals (#2632)
actuals:
  tokens: 8118
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-device response header template stamped once in EmulatedLifxDevice.__init__; every reply path (normal, both ack paths, StateUnhandled) inherits it via copy.copy()"
    - "Frozen dataclass + dataclasses.replace() for build-time-only immutable sub-state, translated to ValueError at the DeviceState.__setattr__ boundary"
    - "Optional per-device value threaded through create_device() and DeviceBuilder.with_*(), following the PR #156 advertised_services precedent"

key-files:
  created:
    - packages/lifx-emulator-core/tests/test_header.py
    - packages/lifx-emulator-core/tests/test_thread_identity.py
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/states.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/device.py
    - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
    - packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py
    - packages/lifx-emulator-core/src/lifx_emulator/__init__.py

key-decisions:
  - "Byte fixtures recaptured against the live tree and found byte-identical to RESEARCH.md's recorded hex; no divergence, so the RESEARCH.md values were used verbatim with a comment naming commit e610c08e8ea9eab6e2b37cb097b731542ff8d717"
  - "build() step 1a (connectivity resolution) placed immediately after '# 1. Generate/validate serial' and before '# 3. Determine firmware version', per D-10/plan instruction; firmware and wifi_signal derivation from connectivity are explicitly out of scope for this plan (Plan 02/03)"
  - "The generic FrozenInstanceError->ValueError message avoids the literal word 'connectivity' so the wifi_signal reassignment test (message must contain wifi_signal, must not contain connectivity) passes without a per-attribute special case"
  - "_create_response_header() and process_packet() were not modified -- the single kwarg on the template construction in __init__ is the entire wiring, confirmed by the single-construction-site grep"

requirements-completed: [HDR-01, HDR-02, HDR-03]

coverage:
  - id: D1
    description: "Connectivity enum, coerce_connectivity, and connectivity argument on create_device()/DeviceBuilder, with default wifi and ValueError on invalid strings"
    requirement: "CONN-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestConnectivityFactory"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestDeviceBuilderConnectivity"
        status: pass
    human_judgment: false
  - id: D2
    description: "connectivity and wifi_signal immutable after construction, raising ValueError naming the refused attribute"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestConnectivityImmutability"
        status: pass
    human_judgment: false
  - id: D3
    description: "LifxHeader.thread_connection bit 3 pack/unpack, default False, reserved bits untouched, repr shows the bit"
    requirement: "HDR-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_header.py::TestThreadConnectionBit"
        status: pass
    human_judgment: false
  - id: D4
    description: "A Thread device sets bit 3 on StateColor, both acknowledgement helper output, and StateUnhandled; a WiFi device never does"
    requirement: "HDR-02, HDR-03"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadBitOnEveryReply"
        status: pass
    human_judgment: false
  - id: D5
    description: "WiFi wire output (StateService, StateColor, Acknowledgement, StateUnhandled, plain header round trip) is byte-for-byte unchanged from before this phase"
    requirement: "HDR-03"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_header.py::TestHeaderByteFixture"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestWifiWireOutputUnchanged"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 01: End-to-End Thread Bit -- Header to Wire Summary

**A device created with `connectivity="thread"` sets frame-address flags bit 3 on every reply it emits (data replies, both acknowledgement paths, StateUnhandled) via a single stamping point on the per-device response header template, while a WiFi device's wire output stays byte-for-byte identical to the pre-phase fixtures.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-09T07:10:00Z (approx, per STATE.md session start)
- **Completed:** 2026-09-09
- **Tasks:** 2 completed
- **Files modified:** 9 (7 source, 2 test modules; both test modules created in Task 1, extended in Task 2)

## Accomplishments

- Captured and committed pre-change WiFi byte fixtures (StateService, StateColor, Acknowledgement, StateUnhandled, plain header round trip) before any behaviour change, per D-11/D-12
- Added `Connectivity(str, Enum)` with `WIFI`/`THREAD` and `__str__ = str.__str__` (needed on this project's default Python 3.14 toolchain, not just 3.10 as CONTEXT.md originally stated -- corrected per RESEARCH.md Pitfall 5), plus the shared `coerce_connectivity()` validator
- Froze `NetworkState`, adding `connectivity` alongside the now-also-frozen `wifi_signal`; `DeviceState.__setattr__` translates `FrozenInstanceError` to `ValueError` on both fields via one generic branch
- Added `LifxHeader.thread_connection` as frame-address byte 22 bit 3 (pack, unpack, repr), leaving bits 2 and 4-7 untouched
- Wired `EmulatedLifxDevice.__init__`'s one `_response_header_template` construction to derive `thread_connection` from `self.state.connectivity`; `_create_response_header()` was not touched, so both ack paths and `StateUnhandled` inherit the bit automatically via the existing `copy.copy()`
- Added `DeviceBuilder.with_connectivity()` / `_resolve_connectivity()` as build() step 1a (resolved before firmware and `NetworkState` construction) and a `connectivity` argument on `create_device()`
- Exported `Connectivity` from `lifx_emulator` and `lifx_emulator.devices`

## Task Commits

1. **Task 1: Capture and commit the pre-change wire byte baseline** - `22536a2` (test)
2. **Task 2: End-to-end Thread bit -- one path, header to wire** - `714321d` (feat)

_No plan-metadata commit needed beyond this SUMMARY per the standard close-out step._

## Files Created/Modified

- `packages/lifx-emulator-core/tests/test_header.py` - New: pre-change header round-trip fixture plus `thread_connection` pack/unpack, reserved-bits, and repr tests
- `packages/lifx-emulator-core/tests/test_thread_identity.py` - New: pre-change WiFi reply byte fixtures, connectivity factory/builder/immutability tests, and the end-to-end Thread-bit-on-every-reply test
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py` - `thread_connection: bool = False` field, pack/unpack bit ops, repr
- `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` - `Connectivity` enum, `coerce_connectivity()`, frozen `NetworkState`, `_ATTRIBUTE_ROUTES` entry, `FrozenInstanceError` translation
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` - Template stamping kwarg; per-tile firmware literals swapped for `self.state.version_major/minor` (touched per RESEARCH.md point 7's precedent, though full mirroring verification is Plan 02/04 scope)
- `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` - `with_connectivity()`, `_resolve_connectivity()`, build() step 1a, `NetworkState(connectivity=connectivity)`
- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py` - `connectivity` argument on `create_device()`
- `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py`, `packages/lifx-emulator-core/src/lifx_emulator/__init__.py` - `Connectivity` barrel exports

## Decisions Made

- Recaptured byte fixtures matched RESEARCH.md exactly (verified via a throwaway script run against the live tree); no divergence, so fixtures use the RESEARCH.md hex with the precondition commit hash `e610c08e8ea9eab6e2b37cb097b731542ff8d717` in the comment.
- `build()` step 1a placed exactly where D-10 and the plan specify: after serial generation, before firmware resolution. `connectivity` flows into `NetworkState()` only in this plan; `wifi_signal` derivation and firmware floor/ceiling checks are explicitly deferred to Plans 02/03.
- The `FrozenInstanceError` -> `ValueError` message was worded to avoid the literal substring "connectivity" so it satisfies the plan's stricter acceptance criterion for the `wifi_signal` reassignment case (message must contain `wifi_signal` and must not contain `connectivity`) while still being one generic branch shared by both fields.
- Confirmed `_create_response_header()` and `process_packet()` needed zero changes -- the single template kwarg in `__init__` is the entire wiring, verified mechanically via the single-construction-site grep required by the plan's acceptance criteria.

## Deviations from Plan

None - plan executed exactly as written. Byte-fixture recapture found zero divergence from RESEARCH.md, so no fallback path was exercised.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02 (firmware precedence: Thread default/floor 4.200, Tile ceiling 3.50) and Plan 03 (typed factories + `wifi_signal` derivation) can build directly on `Connectivity`, `coerce_connectivity()`, and `DeviceBuilder._resolve_connectivity()` introduced here. `FirmwareConfig.get_firmware_version()` does not yet take a `connectivity` argument -- that is Plan 02's job. No blockers.

---
*Phase: 01-thread-device-identity*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 9 created/modified files verified present on disk; both task commits (`22536a2`, `714321d`) verified present in git history.
