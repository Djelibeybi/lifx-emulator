---
phase: 01-thread-device-identity
plan: 03
subsystem: core-protocol
tags: [thread, connectivity, factories, wifi-signal, firmware, matrix, docs]

# Dependency graph
requires:
  - phase: 01-thread-device-identity
    provides: "Connectivity(str, Enum), coerce_connectivity(), frozen NetworkState.connectivity, DeviceBuilder.with_connectivity()/_resolve_connectivity() at build() step 1a (Plan 01); FirmwareConfig.VERSION_THREAD, connectivity parameter on get_firmware_version(), specs.yml terminal-firmware ceiling for product 55 (Plan 02)"
provides:
  - "connectivity parameter on all seven typed factories (create_color_light, create_infrared_light, create_hev_light, create_multizone_light, create_tile_device, create_color_temperature_light, create_switch), forwarded into create_device()"
  - "wifi_signal derived from the effective connectivity at NetworkState construction (0.0 Thread, -45.0 WiFi)"
  - "Scoped max-args exception for the eight public factory entry points, recorded in the root CLAUDE.md Code Quality Standards list"
  - "Explanatory comment on the per-tile firmware_version_major/minor mirror in device.py (the mirror itself landed in Plan 01)"
affects: ["01-04"]

# Actuals (#2632)
actuals:
  tokens: 6504
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional per-device value threaded through all eight public factory entry points via create_device(), following the PR #156 advertised_services precedent -- connectivity is now on parity with advertised_services across the whole factory surface"
    - "Derived-at-build-time field (wifi_signal) computed once in DeviceBuilder.build() step 6 from the already-resolved connectivity, rather than a handler branch"

key-files:
  created: []
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py
    - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
    - packages/lifx-emulator-core/src/lifx_emulator/devices/device.py
    - packages/lifx-emulator-core/tests/test_thread_identity.py
    - packages/lifx-emulator-core/tests/test_tile_handlers_extended.py
    - CLAUDE.md

key-decisions:
  - "Scoped max-args exception recorded as a new bullet in the root CLAUDE.md Code Quality Standards list (not a SUMMARY-only note, and not a # noqa), per developer decision from Round 2 review: create_device() and the seven typed factories in factories/factory.py are exempt because every parameter is a user-facing device option and a keyword-options object would break a published API, with the advertised_services PR #156 precedent cited directly"
  - "Docstrings split into two treatments per Round 2 review correction: the four functions that already had full Args: blocks (create_multizone_light, create_tile_device, create_switch, create_device) got one appended connectivity: line each; the four bare one-liners (create_color_light, create_infrared_light, create_hev_light, create_color_temperature_light) were replaced with full Google-style docstrings (summary, Args:, Returns:) covering every parameter, not just the new one"
  - "The typed-factory parametrised test treats create_tile_device as an expected-ValueError case for connectivity='thread' (SPEC AC 2 amendment), and pins both the Thread default (4, 200) and an explicit override (5, 0) for each of the other seven entry points, so a factory cannot preserve connectivity forwarding while mishandling firmware_version"
  - "Task 2's core mirroring change (self.state.version_minor/major replacing the 3.70 literal in device.py) was already committed in Plan 01 (714321d) as a forward precedent named in that plan's own SUMMARY; this task added the explanatory protocol-quirk comment and the verification tests, and investigated the resulting 'unexpected GREEN' per the TDD fail-fast rule rather than treating it as a defect (see TDD Gate Compliance below)"

requirements-completed: [CONN-01, CONN-03]

coverage:
  - id: D1
    description: "connectivity parameter on all seven typed factories plus create_device, forwarded through to DeviceBuilder.with_connectivity(); create_tile_device raises ValueError for connectivity=\"thread\" (product 55's 3.50 ceiling sits below the Thread floor); invalid strings (\"Thread\", \"bluetooth\") rejected on every entry point"
    requirement: "CONN-01"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestTypedFactoryConnectivity::test_connectivity_forwarding_and_firmware"
        status: pass
    human_judgment: false
  - id: D2
    description: "wifi_signal is derived from the effective connectivity at build time: 0.0 for Thread, -45.0 for WiFi, with no handler change"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestWifiSignalDerivation"
        status: pass
    human_judgment: false
  - id: D3
    description: "GetWifiInfo/GetHostFirmware/GetWifiFirmware on a Thread device report signal=0.0 and firmware (4, 200); a WiFi device at the same firmware reports identical firmware fields; ambient_light_lux is 100.0 via the existing firmware-4 rule with no Thread branch"
    requirement: "CONN-03"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadIdentitySurface::test_thread_device_identity_surface"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every freshly constructed matrix device's tiles report the device's own resolved host firmware in StateDeviceChain: a Thread Ceiling reports (4, 200), a WiFi Ceiling reports (4, 10) (corrected from the pre-phase (3, 70)), and a Candle with no specs.yml firmware default falls through to (3, 70)"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_tile_handlers_extended.py::TestTileFirmwareMirrorsHost"
        status: pass
    human_judgment: false
  - id: D5
    description: "The root CLAUDE.md Code Quality Standards list carries a scoped, documented max-args exception for the eight public factory entry points; no # noqa added anywhere, pyproject.toml untouched"
    verification:
      - kind: other
        ref: "grep -c bullet count in CLAUDE.md; grep -rn '# noqa' packages/lifx-emulator-core/src/lifx_emulator/ (no output); git diff --stat -- pyproject.toml (no output)"
        status: pass
    human_judgment: false
  - id: D6
    description: "No handler and no restorer method modified across this plan"
    verification:
      - kind: other
        ref: "git diff --stat 1dcd047..HEAD -- packages/lifx-emulator-core/src/lifx_emulator/handlers/ packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py (no output)"
        status: pass
    human_judgment: false

duration: 19min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 03: Typed Factory Connectivity, WiFi Signal Derivation, and Per-Tile Firmware Mirror Summary

**All seven typed factories now accept `connectivity` (with `create_tile_device` correctly rejecting Thread for its hard-capped product 55), a Thread device reports zero WiFi signal and 4.200 firmware on every relevant query, and a freshly constructed matrix device's tiles mirror the device's own host firmware instead of a hard-coded 3.70 -- with a scoped `CLAUDE.md` exception now documenting why these eight factories exceed the project's five-argument limit.**

## Performance

- **Duration:** 19 min
- **Started:** 2026-09-09T07:50:38Z (approx, per STATE.md session marker at the close of Plan 02)
- **Completed:** 2026-09-09T08:09:02Z
- **Tasks:** 2 completed
- **Files modified:** 6 (4 source, including `CLAUDE.md`; 2 test modules)

## Accomplishments

- Added `connectivity: Connectivity | str | None = None` as the last parameter on all seven typed factories (`create_color_light`, `create_infrared_light`, `create_hev_light`, `create_multizone_light`, `create_tile_device`, `create_color_temperature_light`, `create_switch`), forwarded unconditionally as `connectivity=connectivity` into `create_device()`, matching the `advertised_services` precedent (PR #156)
- Rewrote docstrings across all eight entry points in `factory.py`: the four bare one-liners became full Google-style docstrings (`Args:`/`Returns:`), and the four that already had `Args:` blocks each gained one `connectivity:` line
- Derived `wifi_signal` in `DeviceBuilder.build()` step 6 from the already-resolved effective `connectivity` (`0.0` for Thread, `-45.0` for WiFi) -- no handler touched; `GetWifiInfoHandler`, `GetHostFirmwareHandler` and `GetWifiFirmwareHandler` were already correct once the state was right
- Recorded a scoped `max-args` exception for the eight public factory entry points as a new bullet in the root `CLAUDE.md` `## Code Quality Standards` list, superseding the Round 1 disposition that had treated a SUMMARY-only note as sufficient
- Added an explanatory protocol-quirk comment above the per-tile `firmware_version_major`/`minor` mirror in `device.py`, and locked the mirror invariant under test for a Thread Ceiling, a WiFi Ceiling (now `(4, 10)`, corrected from the pre-phase `(3, 70)`), and a Candle falling through to `(3, 70)` with no `specs.yml` firmware default
- Added `TestTypedFactoryConnectivity` (parametrised over all eight entry points), `TestWifiSignalDerivation`, and `TestThreadIdentitySurface` to `test_thread_identity.py`; added `TestTileFirmwareMirrorsHost` to `test_tile_handlers_extended.py`

## Task Commits

1. **Task 1: connectivity on every typed factory, and a Thread radio that reports no signal**
   - `aff19a7` (test) -- failing tests for typed-factory connectivity forwarding, `wifi_signal` derivation, and the Thread identity surface (GetWifiInfo/GetHostFirmware/GetWifiFirmware/ambient_light_lux); confirmed 9 new failures, 37 pre-existing tests unaffected
   - `2a1f13f` (feat) -- `factory.py`/`builder.py`/`CLAUDE.md` changes; full suite green (1209 passed), `ruff check`, `ruff format --check` and `pyright` all clean
2. **Task 2: Tiles report their host firmware**
   - `bc78491` (feat) -- explanatory comment in `device.py` plus `TestTileFirmwareMirrorsHost`; full suite green (1212 passed); see **TDD Gate Compliance** below -- no preceding `test(01-03):` commit for this task, because the mirroring behaviour under test was already implemented in Plan 01

_Plan-metadata commit follows this SUMMARY per the standard close-out step._

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py` - `connectivity` parameter and forwarding on all seven typed factories; docstrings rewritten/extended for all eight entry points
- `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` - `wifi_signal` derived from the resolved `connectivity` at `NetworkState` construction (build step 6)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` - Explanatory comment above the per-tile firmware mirror (the mirror itself was already in place from Plan 01)
- `packages/lifx-emulator-core/tests/test_thread_identity.py` - `TestTypedFactoryConnectivity`, `TestWifiSignalDerivation`, `TestThreadIdentitySurface`
- `packages/lifx-emulator-core/tests/test_tile_handlers_extended.py` - `TestTileFirmwareMirrorsHost`
- `CLAUDE.md` - New `## Code Quality Standards` bullet recording the scoped `max-args` exception for the eight public factory entry points

## Decisions Made

See `key-decisions` in frontmatter for the full list. The two most load-bearing:
- The `max-args` exception lives in `CLAUDE.md` itself, not only in this SUMMARY -- per the developer's Round 2 decision, a SUMMARY note alone was judged insufficient to make the policy auditable to future maintainers reading the project instructions rather than phase history.
- `create_tile_device` is deliberately the one entry point in the parametrised test expected to raise for `connectivity="thread"`, matching the SPEC AC 2 amendment from Round 1 review rather than treating it as a gap to close.

### Final parameter counts (per-CLAUDE.md exception, all exceed the documented `max-args = 5`)

| Factory | Parameter count (incl. `connectivity`) |
|---|---|
| `create_color_light` | 6 |
| `create_infrared_light` | 6 |
| `create_hev_light` | 6 |
| `create_color_temperature_light` | 6 |
| `create_multizone_light` | 8 |
| `create_tile_device` | 9 |
| `create_switch` | 7 |
| `create_device` | 12 |

### Ruff enforcement gap (recorded per plan `<output>` instruction)

`max-args` (`PLR0913`, pylint) and `mccabe` (`C901`) complexity limits are configured under `[tool.ruff.lint.pylint]`/`[tool.ruff.lint.mccabe]` in the root `pyproject.toml`, but neither appears in `[tool.ruff.lint].select = ["E", "F", "I", "N", "W", "UP"]`, so `uv run ruff check .` enforces neither limit. This means none of the eight over-limit signatures above trip CI on their own -- the `CLAUDE.md` bullet added in this plan is the only enforcement mechanism, by design (a keyword-options redesign was explicitly rejected for this milestone; see Round 2 "Deferred" ledger in `01-03-PLAN.md`).

## TDD Gate Compliance

Per `tdd.md`'s Executor Gate Validation, `git log --oneline -E --grep` was run for both `test(01-03):` and `feat(01-03):` commits:

```
test(01-03): aff19a7 add failing tests for typed-factory connectivity, wifi_signal derivation and thread identity surface
feat(01-03): 2a1f13f connectivity on every typed factory, Thread reports zero WiFi signal
feat(01-03): bc78491 tiles report their host firmware, with tests locking the invariant
```

**Task 1** followed the full RED-GREEN cycle: `aff19a7` (test) was committed first against the pre-change `factory.py`/`builder.py`/`CLAUDE.md` (temporarily reverted to the Plan 02 HEAD versions via `git checkout --`, with the new test code already in place), confirmed 9 failures with `TypeError: unexpected keyword argument 'connectivity'` and 37 pre-existing tests in the module unaffected, then the implementation was restored and committed GREEN as `2a1f13f` (1209 passed).

**Task 2** has no `test(01-03):` commit preceding `bc78491`, which is a genuine gap against the letter of the RED-GREEN-REFACTOR cycle -- flagged here per the Gate Enforcement Rules rather than silently omitted. The root cause, investigated per the "Unexpected GREEN in RED phase" fail-fast rule: the mirroring behaviour the new `TestTileFirmwareMirrorsHost` tests exercise (`self.state.version_minor`/`self.state.version_major` replacing the `3.70` literal in `device.py`) was **already implemented and committed in Plan 01** (commit `714321d`, `feat(core-protocol): end-to-end Thread bit, header to wire`), landed ahead of its own plan scope as a forward precedent per RESEARCH.md point 7 -- this is documented in `01-01-SUMMARY.md`'s Files Created/Modified list. Confirmed via `git log -p --follow` on `device.py`: the literal-to-derived-field diff sits entirely inside `714321d`, with no further change to those two lines in Plan 02 or this plan. This task's actual work was the explanatory comment (a non-behavioural documentation change, for which a RED phase is not meaningful) and the verification tests, which pass immediately because the behaviour they assert already exists -- not because the test is vacuous (all three tests drive real packets through `process_packet()` and assert on both in-memory state and the wire response). No production code in this task's diff required a preceding failing test, so the missing `test(01-03):` commit for Task 2 reflects the actual sequencing of work across the phase, not a skipped verification step.

The tdd-red-evidence tool (`gsd_run check tdd-red-evidence`) was not used for Task 1's RED evidence: it parses Node.js `--test` TAP output (`# tests N` / `# pass N` / `# fail N` summary lines and `ok N - <name>` / `not ok N - <name>` test lines), and this is a pytest project with no TAP-emitting plugin installed. Running it against pytest's default `-q` output would misclassify genuine RED evidence as `zero_tests_discovered` (INVALID_RED) purely from a parser mismatch, not from any defect in the RED phase itself. Verification instead followed the same precedent as Plans 01 and 02 in this phase: the RED-phase pytest run was captured directly (9 failed, 37 passed, with the exact `TypeError` naming the missing `connectivity` keyword for every failing entry point), and the git-log-based Executor Gate Validation check above confirms commit ordering.

## Deviations from Plan

None that changed behaviour or scope. One process deviation, documented above under **TDD Gate Compliance**: Task 2's `tdd="true"` designation could not produce a genuine RED phase for the mirroring assertions because that production code already existed from Plan 01; the task's actual new work (comment + tests) was completed and verified, but does not carry a preceding failing-test commit. No `[Rule N]` auto-fix was needed for either task -- both tasks' `<acceptance_criteria>` passed on the first implementation pass.

## Issues Encountered

During Task 1's RED-phase capture, an initial attempt to isolate the pre-implementation state via `git stash push --keep-index -- <files>` was a no-op because those files were already fully staged (the stash immediately reapplied the index, leaving the working tree unchanged) -- caught before any commit, `git reset` + `git stash pop` + `git stash drop` cleanly restored the prior state with no data loss (verified via `git diff --stat` before dropping), and the redundant stash entry (confirmed identical to the working tree) was the only one touched; four unrelated stash entries from other branches in the shared stash list were left untouched. The RED-phase isolation was then done without `git stash` at all: `cp` a working copy of the GREEN source files to `/tmp`, `git checkout --` the three source files back to the Plan 02 HEAD version (test file untouched), run the RED-phase test, then restore the GREEN copies from `/tmp` and re-verify GREEN before committing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 04 (persistence round trip: `StateRestorer.peek_connectivity()`, `"connectivity"` in `serialize_device_state()` output) can build directly on `Connectivity`, `coerce_connectivity()`, `DeviceBuilder.with_connectivity()`/`_resolve_connectivity()`, and the now-complete typed-factory `connectivity` surface introduced across Plans 01-03. The restored-matrix-device per-tile firmware limitation is recorded (see `key-decisions`/`must_haves` in `01-03-PLAN.md`) as explicitly out of scope for this phase's persistence work: a Ceiling file written before this phase restores tile `3.70` against a host that now resolves to `4.10`, which is existing restore semantics, not a regression. No blockers.

---
*Phase: 01-thread-device-identity*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 6 modified files verified present on disk with the expected changes; all three task commits (`aff19a7`, `2a1f13f`, `bc78491`) verified present in git history via `git log --oneline`.
