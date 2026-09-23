---
phase: 03-mdns-responder
plan: '03'
subsystem: networking
tags: [mdns, zeroconf, asyncio]
requires:
  - phase: 03-02
    provides: Approved zeroconf 0.151.3 selection
provides:
  - Opt-in server responder with complete WiFi records and owned cleanup
  - Raw legacy-unicast and two-stage public operation tests
affects: [03-04, 03-06, 03-07]
tech-stack:
  added: [zeroconf==0.151.3]
  patterns: [Two-stage public zeroconf operations]
key-files:
  created:
    - packages/lifx-emulator-core/src/lifx_emulator/mdns.py
    - packages/lifx-emulator-core/tests/test_mdns_responder.py
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/server.py
    - packages/lifx-emulator-core/pyproject.toml
    - uv.lock
requirements-completed: [MDNS-01, MDNS-02, MDNS-03, MDNS-04, MDNS-05, MDNS-11]
coverage:
  - id: responder-tracer
    description: Opt-in loopback legacy-unicast discovery and owned cleanup
    verification:
      - kind: integration
        ref: packages/lifx-emulator-core/tests/test_mdns_responder.py
        status: pass
    human_judgment: false
duration: 8min
completed: 2026-09-23
status: complete
---

# Phase 3 Plan 03: Responder tracer

The explicitly enabled server owns a public AsyncZeroconf responder after the LIFX endpoint pair commits, with complete WiFi DNS-SD snapshots and awaited announcements/goodbyes.

## Accomplishments

- Live PyPI metadata confirmed 0.151.3 before `uv add`; the exact approved version is locked.
- Raw ephemeral-port loopback queries assert source port, independent IDs, TTL <= 10, clear cache-flush bits and complete associated PTR/SRV/TXT/A records.
- Empty, single and three-device fleets, firmware 4.200, trailing-zero serials and direct A/opposite-family queries pass.
- Controlled outer and returned-awaitable failures/holds prove cleanup and completion ordering, with one close per owner.

## Verification

- Tracer plus existing server regression: 83 passed.
- Expanded responder suite: 11 passed, no skips.
- Ruff and focused Pyright passed.
- RED: `test_disabled_default` failed its explicit opt-in assertion before implementation.

## Commits

- 0420cfa — failing opt-in contract test.
- c6bba03 — adapter, server integration and expanded wire/cleanup tests.

## Deviations from Plan

- The two closely related implementation tasks share one production commit; tests were expanded after the initial opt-in RED assertion. The newer GSD RED-evidence validator only parses Node TAP, so pytest's actual assertion output was reviewed directly rather than converted into invented TAP evidence.
- GSD worktree base-check selected sequential execution on the existing phase branch.

## Issues Encountered

An initial placement error in the shutdown integration caused NameError failures; moved cleanup into `_stop_locked`, then reran the complete server regression successfully.

## Next Phase Readiness

Ready for immutable advertisement configuration (03-04) and independent lifecycle listeners (03-05). Requirements shared with later plans remain pending phase-wide verification.

## Self-Check: PASSED
