---
phase: 02-ipv6-transport-and-thread-isolation
plan: 03
subsystem: udp-routing
tags: [asyncio, ipv6, thread, routing, datagram-context, tdd]

# Dependency graph
requires:
  - phase: 02-ipv6-transport-and-thread-isolation
    provides: "Plan 02-01 background-task ownership, exact target rendering and malformed-datagram counter contracts"
  - phase: 01-thread-device-identity
    provides: "Immutable device connectivity and Thread response-header identity"
provides:
  - "Family-aware WiFi/Thread target selection with IPv6 exact-unicast-only Thread eligibility"
  - "Immutable per-datagram family, peer and receiving-transport identity"
  - "Endpoint-affine acknowledgements and state replies with legacy tuple-call compatibility"
affects: [02-04-dual-stack-lifecycle, phase-03-mdns, phase-06-oracle-integration]

# Actuals (#2632)
actuals:
  tokens: 12312
  tasks: 2
  commits: 4
plan_head_before: 873e265736d0736504e1919e9d8a5f4a7c28615a

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Manager-layer transport eligibility consumes only parsed header, address family and public device state"
    - "Frozen datagram context is created by the receiving protocol and retained through every response send"
    - "Legacy peer tuples are coerced once with an explicit transport or the IPv4 compatibility alias"

key-files:
  created: []
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py
    - packages/lifx-emulator-core/src/lifx_emulator/server.py
    - packages/lifx-emulator-core/tests/test_device_manager.py
    - packages/lifx-emulator-core/tests/test_server.py
    - packages/lifx-emulator-core/tests/test_thread_identity.py

key-decisions:
  - "Evaluate every managed Thread identity against family, broadcast form and exact serial so each rejected candidate receives one concrete DEBUG reason without changing the public list result."
  - "Treat protocol-owned transport as authoritative in production; server.transport is read only once when adapting a legacy IPv4 direct call."
  - "Resolve eligible targets before receive statistics and activity, while short and header-unparsable datagrams retain the explicit Plan 02-01 receive/error outcomes."

patterns-established:
  - "Production routing: LifxProtocol family plus local transport -> frozen _DatagramContext -> manager resolution -> context.transport.sendto."
  - "Address rendering uses the explicit context family: host:port for IPv4 and [host]:port for IPv6."

requirements-completed: [NET-02, NET-03, NET-04]

coverage:
  - id: D1
    description: "Interleaved IPv4 and IPv6 datagrams retain their own family through public target resolution and cannot cross reply transports."
    requirement: NET-02
    verification:
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_interleaved_families_keep_resolution_and_reply_affinity"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestProtocolClass::test_protocol_datagram_received"
        status: pass
    human_judgment: false
  - id: D2
    description: "Thread devices are selected only for exact untagged IPv6 unicast, with rejected traffic producing no processing, counters, activity or replies."
    requirement: NET-03
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_device_manager.py::TestTransportAwareTargetResolution"
        status: pass
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_rejected_thread_packets_have_no_observable_side_effects"
        status: pass
    human_judgment: false
  - id: D3
    description: "WiFi devices remain eligible on both families and reply through the endpoint that received each request."
    requirement: NET-04
    verification:
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting"
        status: pass
      - kind: integration
        ref: "Plan 02-03 focused regression suite (156 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Existing direct handler and helper callers retain IPv4 tuple defaults while production protocols own immutable endpoint identity."
    requirement: NET-02
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_legacy_handler_prefers_explicit_transport"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_legacy_helper_calls_capture_ipv4_alias"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 3: Family-Aware Routing and Endpoint Affinity Summary

**Thread traffic is now filtered to exact IPv6 unicast before observable effects, while frozen per-datagram contexts keep concurrent WiFi replies on their receiving transports.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-10T07:05:04Z
- **Completed:** 2026-09-10T07:24:45Z
- **Tasks:** 2
- **Files modified:** 5 implementation/test files

## Accomplishments

- Extended the public device-manager contract with a backwards-compatible IPv4 family default and a complete WiFi/Thread transport eligibility decision table.
- Introduced a frozen datagram context carrying authoritative family, peer and protocol-local transport through parsing, target resolution, acknowledgements and response packets.
- Moved Thread rejection ahead of packet counters, activity, scenarios and device processing while retaining the Plan 02-01 malformed-input counter matrix.
- Preserved legacy peer-tuple calls to `handle_packet`, `_send_ack` and `_process_device_packet`, including the existing IPv4 `server.transport` compatibility alias.

## Task Commits

Each TDD task was committed as a RED test commit followed by its GREEN implementation commit:

1. **Task 1 RED: family-aware targeting decision table** - `da85895` (test)
2. **Task 1 GREEN: WiFi/Thread transport eligibility** - `03d27a2` (feat)
3. **Task 2 RED: endpoint-affine reply and compatibility coverage** - `6e6c2b3` (test)
4. **Task 2 GREEN: immutable datagram routing context** - `7e099d6` (feat)

**Plan metadata:** commit to follow (docs: complete plan)

## TDD Gate Compliance

- Task 1 RED: `test_ipv4_broadcast_filters_thread_by_default` failed because the default IPv4 broadcast still selected both WiFi and Thread devices; `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed 111 tests, and the automated-only tracer verification was rerun successfully before Task 2.
- Task 2 RED: `test_protocol_connection_made_owns_transport_without_mutating_server_alias` failed because `connection_made()` still replaced `server.transport`; `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed all 45 server tests and the focused C901 gate.
- The plan-wide suite passed 156 tests; the final repository suite passed all 1,294 tests. Changed-file Ruff, server C901 and changed-source Pyright all passed.

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` - family-aware WiFi/Thread target eligibility and concrete per-rejection DEBUG diagnostics
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` - frozen endpoint context, one-time compatibility coercion, explicit family formatting and endpoint-affine replies
- `packages/lifx-emulator-core/tests/test_device_manager.py` - complete connectivity/family/target table, rejection reasons and repeated-interleaving dispatch proof
- `packages/lifx-emulator-core/tests/test_server.py` - immutable context, legacy helper, reply-affinity, IPv6 formatting, malformed-counter and side-effect-isolation coverage
- `packages/lifx-emulator-core/tests/test_thread_identity.py` - mixed-fleet broadcast expectation updated while retaining direct identity-bit proof

## Decisions Made

- Iterated over public managed device identity during target resolution so mismatched Thread candidates receive the required diagnostic instead of disappearing through an exact repository lookup.
- Kept `_DatagramContext` private and allowed a `None` transport only for legacy no-socket diagnostic calls; production protocol contexts always capture their receiving transport.
- Formatted every request/reply address from the context family rather than peer tuple length, making IPv6 brackets deterministic even for compatibility calls.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - AGENTS.md Compliance] Moved existing nested imports to module scope**
- **Found during:** Tasks 1 and 2
- **Issue:** Both modified test modules contained function-local imports, conflicting with the mandatory project rule that all Python imports remain at the top of the file.
- **Fix:** Consolidated those existing imports at module scope while adding the planned tests; behaviour was unchanged.
- **Files modified:** `packages/lifx-emulator-core/tests/test_device_manager.py`, `packages/lifx-emulator-core/tests/test_server.py`
- **Verification:** Changed-file Ruff passed and the plan-wide suite passed 156 tests.
- **Committed in:** `da85895`, `6e6c2b3`

---

**Total deviations:** 1 auto-fixed (Rule 2 project-instruction compliance)
**Impact on plan:** The adjustment was limited to the two planned test files and introduced no production scope.

## Issues Encountered

- The default uv cache was outside the writable sandbox, so all Python tooling used the project-safe temporary cache at `/tmp/lifx-emulator-uv`.
- The restricted sandbox denied the existing loopback UDP lifecycle tests; the identical focused and plan-wide commands passed with authorised loopback access.
- The full suite retained one pre-existing Starlette/httpx deprecation warning and three intentional `--persistent` CLI deprecation warnings; the dependency transition is recorded in `deferred-items.md` rather than expanded into this transport plan.

## Known Stubs

None - the added optional transport values support legacy diagnostic calls and do not flow to a UI or leave production routing unwired.

## User Setup Required

None - no dependency, external service or configuration change is required.

## Next Phase Readiness

- Plan 02-04 can construct distinct IPv4/IPv6 protocols with explicit families and rely on protocol-local transport ownership without changing packet dispatch.
- Dual-stack lifecycle work can retain `server.transport` as the IPv4 alias while publishing the second socket only after atomic startup.
- No blocker remains for native dual-family binding and real-loopback integration coverage.

## Self-Check: PASSED

- All five implementation/test files and this summary exist.
- All four RED/GREEN task commits resolve in Git.
- Each task commit was created with the corrected required GPG fingerprint and a DCO sign-off.

---
*Phase: 02-ipv6-transport-and-thread-isolation*
*Completed: 2026-09-10*
