---
phase: 02-ipv6-transport-and-thread-isolation
plan: 04
subsystem: udp-lifecycle
tags: [asyncio, ipv6, udp, thread, lifecycle, sockets, tdd]

# Dependency graph
requires:
  - phase: 02-ipv6-transport-and-thread-isolation
    provides: "Plan 02-01 background-task ownership and Plan 02-03 family-aware endpoint-affine routing"
  - phase: 01-thread-device-identity
    provides: "Immutable WiFi/Thread connectivity and Thread response-header identity"
provides:
  - "Atomic IPv4/IPv6-only same-port UDP startup with configurable IPv6 loopback default"
  - "Committed effective endpoint publication and port-zero device service propagation"
  - "Ordered tracked-work drain plus bounded dual-endpoint closure"
  - "Real-loopback WiFi reply-affinity and Thread-isolation proof"
affects: [phase-03-mdns, phase-04-cli-config, phase-06-oracle-integration]

# Actuals (#2632)
actuals:
  tokens: 10597
  tasks: 3
  commits: 5
plan_head_before: 95fc7cb4c2f49b5b0814c71261b7e036df0ddffd

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IPv4-first bind supplies the effective port to an explicit AF_INET6 V6-only socket"
    - "Protocols begin non-accepting and publish only after the complete endpoint pair and device state commit"
    - "Shutdown rejects admission, drains tracked work, then closes and observes each endpoint within a finite bound"

key-files:
  created:
    - packages/lifx-emulator-core/tests/test_ipv6_transport.py
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/server.py
    - packages/lifx-emulator-core/tests/conftest.py
    - packages/lifx-emulator-core/tests/test_server.py

key-decisions:
  - "Keep server.port as the caller-configured value and publish the live allocation through private _effective_port plus atomic endpoint properties."
  - "Retry only port-zero IPv6 EADDRINUSE failures, discarding the entire provisional pair before each of at most five attempts."
  - "Keep transports usable while server-owned work drains, then await IPv4 and IPv6 connection_lost signals independently with one-second bounds."

patterns-established:
  - "Atomic lifecycle: non-accepting protocols -> IPv4 bind -> V6-only IPv6 same-port bind -> device port propagation -> public commit -> admission."
  - "Defensive teardown uses safe attribute access and identity-based transport de-duplication for legacy subclasses."

requirements-completed: [NET-01, NET-03, NET-04, NET-05, HYG-01]

coverage:
  - id: D1
    description: "A stock server atomically binds distinct IPv4 and IPv6-only transports on one effective port, with a configurable ::1 IPv6 default and bounded collision rollback."
    requirement: NET-01
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle"
        status: pass
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_private_ipv6_socket_is_kernel_enforced_v6only"
        status: pass
    human_judgment: false
  - id: D2
    description: "Public IPv4 and IPv6 endpoint properties expose only a complete live pair and port-zero devices advertise the committed non-zero service port."
    requirement: NET-05
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_port_zero_updates_live_added_device_service_port"
        status: pass
      - kind: integration
        ref: "packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_wifi_replies_follow_repeated_interleaved_origin_family"
        status: pass
    human_judgment: false
  - id: D3
    description: "Shutdown stops admission, drains or cancels tracked work before transport closure, bounds both closure waits and clears all endpoint state."
    requirement: HYG-01
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_stop_drains_work_before_closing_endpoints"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_stop_bounds_missing_endpoint_closure_signal"
        status: pass
    human_judgment: false
  - id: D4
    description: "Repeated and interleaved WiFi requests over real IPv4 and IPv6 loopback receive replies only from their originating family."
    requirement: NET-04
    verification:
      - kind: e2e
        ref: "packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_wifi_replies_follow_repeated_interleaved_origin_family"
        status: pass
    human_judgment: false
  - id: D5
    description: "A Thread device answers exact untagged IPv6 unicast and stays externally silent without receive effects for IPv4, broadcast, zero, tagged and mismatched traffic."
    requirement: NET-03
    verification:
      - kind: e2e
        ref: "packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_thread_exact_ipv6_unicast_is_sole_response_path"
        status: pass
    human_judgment: false

duration: 34min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 4: Atomic Dual-Family UDP Lifecycle Summary

**The stock emulator now commits one configurable IPv4/IPv6-only same-port UDP pair, advertises its effective port, drains work before bounded closure, and proves WiFi/Thread isolation on real loopback sockets.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-09-10T07:29:00Z
- **Completed:** 2026-09-10T08:03:00Z
- **Tasks:** 3
- **Files modified:** 4 implementation/test files

## Accomplishments

- Added backwards-compatible configurable IPv6 binding, IPv4-first same-port allocation, V6-only socket configuration, five-attempt ephemeral collision recovery and atomic rollback/publication.
- Preserved configured `server.port` while synchronously propagating the committed non-zero allocation to initial and live-added device StateService replies before packet admission.
- Ordered shutdown so both protocols reject new datagrams before the five-second tracker drain, then close and observe each endpoint with a one-second timeout and deterministic state clearing.
- Added real-loopback proof for repeated/interleaved WiFi reply affinity, the complete Thread rejection matrix, exact IPv6-unicast response and kernel-enforced V6-only state.

## Task Commits

1. **Task 1 RED: dual-family startup lifecycle coverage** - `244435e` (test)
2. **Task 1 GREEN: atomic dual-family endpoint pair** - `8615bfd` (feat)
3. **Task 2 RED: ordered bounded shutdown coverage** - `e9a7eae` (test)
4. **Task 2 GREEN: tracked-work drain and endpoint closure** - `9d9e994` (feat)
5. **Task 3: real-loopback transport and isolation proof** - `7b9b580` (test)

**Plan metadata:** commit to follow (docs: complete plan)

## TDD Gate Compliance

- Task 1 RED: `test_server_start` failed because the server had no `ipv4_endpoint`; five additional assertions exposed the absent IPv6 constructor, retry, rollback and effective-port behaviour. `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed 10 focused tests and all 52 server tests; the tracer feedback gate then reran the 10 focused tests successfully.
- Task 2 RED: `test_stop_drains_work_before_closing_endpoints` failed because the IPv4 transport closed before accepted work was released; cancellation, closure-timeout and legacy teardown tests also exposed the missing lifecycle behaviour. `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`. GREEN passed 9 focused tests and all 57 server tests.
- Task 3 modifies only the new real-socket verification module. Its complete planned behaviour passed immediately against Tasks 1-2 and Plan 02-03, so no legitimate production GREEN change existed; the tests were committed once as verification rather than manufacturing an intentional failure. The plan-level TDD commit patterns remain present through Tasks 1-2.
- Final acceptance passed all 1,309 tests at 94.11% coverage, Ruff lint and format, Pyright with zero errors/warnings and every pre-commit hook.

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/server.py` - configurable dual-family binding, effective endpoints, admission commit, collision rollback and bounded ordered shutdown
- `packages/lifx-emulator-core/tests/conftest.py` - collision-resistant dual-family test-port probing
- `packages/lifx-emulator-core/tests/test_server.py` - constructor, bind, rollback, service-port, idempotency, shutdown, timeout and legacy compatibility coverage
- `packages/lifx-emulator-core/tests/test_ipv6_transport.py` - real IPv4/IPv6 loopback affinity, Thread isolation, V6-only and cleanup proof

## Decisions Made

- Retained the configured port as public caller intent and separated it from the live committed port used for endpoint/device publication.
- Kept the raw IPv6 transport private; only the test suite uses a narrow white-box socket inspection to prove the kernel option required by D-04.
- Used protocol-local admission flags in addition to the server tracker so no datagram can enter between the first bind and complete pair commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restricted retry and diagnostic classification to the IPv6 bind stage**
- **Found during:** Task 1 GREEN review
- **Issue:** The first implementation draft could label an IPv4 bind failure as IPv6 and consider an IPv4 `EADDRINUSE` eligible for the port-zero retry path.
- **Fix:** Required a successfully created provisional IPv4 transport before collision retry and emitted family-specific bind diagnostics.
- **Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/server.py`
- **Verification:** Task 1 focused tests, all server tests and the 1,309-test full suite passed.
- **Committed in:** `8615bfd`

### Plan Execution Variance

- Task 3's `tdd="true"` marker conflicted with its test-only file scope and behaviour already delivered by its dependencies. The complete test module passed on first execution; no false RED or unrelated production change was introduced.

---

**Total deviations:** 1 auto-fixed bug and 1 documented test-only TDD variance.
**Impact on plan:** Functional scope is unchanged; the correction tightened required failure semantics and the variance preserves honest test evidence.

## Issues Encountered

- The default uv cache required authorised access outside the workspace; all Python commands still used uv exclusively.
- The bare `prek` executable was not on the shell PATH. The identical required gate passed as `uv run prek run --all-files` from the locked project environment.
- The full suite retained one pre-existing Starlette/httpx transition warning and three intentional `--persistent` CLI deprecation warnings already recorded in Phase 2's deferred-items ledger.

## Known Stubs

None - optional `None` endpoint values are lifecycle state, not unwired production data.

## User Setup Required

None - no dependency, CLI/YAML configuration or external service change is required.

## Next Phase Readiness

- Phase 3 can publish an IPv6 endpoint backed by the stock server rather than a test-only subclass.
- Phase 4 can add CLI/YAML wiring for the existing core-library `ipv6_bind_address` without changing constructor compatibility.
- No Phase 2 blocker remains; dual-family transport, Thread isolation and lifecycle ownership are fully automated and verified.

## Self-Check: PASSED

- All four implementation/test files and this summary exist.
- All five task commits resolve in Git and carry valid signatures from the required key plus DCO sign-offs.
- Coverage metadata parsed successfully with all five deliverables classified as automatically covered.
- The measured ledger base and five pre-summary commits match the summary actuals.

---
*Phase: 02-ipv6-transport-and-thread-isolation*
*Completed: 2026-09-10*
