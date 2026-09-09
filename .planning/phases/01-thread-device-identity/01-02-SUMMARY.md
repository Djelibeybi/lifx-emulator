---
phase: 01-thread-device-identity
plan: 02
subsystem: core-protocol
tags: [thread, firmware, connectivity, specs, precedence]

# Dependency graph
requires:
  - phase: 01-thread-device-identity
    provides: "Connectivity(str, Enum), coerce_connectivity(), frozen NetworkState.connectivity, LifxHeader.thread_connection, DeviceBuilder.with_connectivity()/_resolve_connectivity() at build() step 1a (Plan 01)"
provides:
  - "FirmwareConfig.VERSION_THREAD = (4, 200) and a connectivity parameter on get_firmware_version(), extending the single existing precedence chain (override > Thread default/floor > specs.yml default > extended-multizone flag)"
  - "ProductSpecs.max_firmware_major/minor, has_max_firmware_specs, SpecsRegistry.get_max_firmware_version() and the module-level get_max_firmware_version() accessor"
  - "specs.yml Tile (product 55) terminal-firmware default and ceiling (3, 50); updated precedence header comment"
  - "DeviceBuilder.build() step 3 threading the step-1a resolved connectivity into firmware resolution"
  - "Registry-wide test proving only product 55 is rejected for connectivity=\"thread\""
affects: ["01-03", "01-04"]

# Actuals (#2632)
actuals:
  tokens: 7083
  tasks: 2
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Firmware floor/ceiling validation lives in a private _validate_firmware() helper on FirmwareConfig, kept separate from resolution to stay under the project's cyclomatic-complexity budget while still being one single-call-site precedence chain"
    - "Terminal-firmware ceiling is pure specs.yml data (max_firmware_major/minor), read via a module-level accessor mirroring the existing default_firmware_* pair -- no product-ID literal anywhere in Python"

key-files:
  created: []
  modified:
    - packages/lifx-emulator-core/src/lifx_emulator/products/specs.py
    - packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml
    - packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py
    - packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py
    - packages/lifx-emulator-core/tests/test_products_specs.py
    - packages/lifx-emulator-core/tests/test_tile_handlers_extended.py
    - packages/lifx-emulator-core/tests/test_thread_identity.py

key-decisions:
  - "get_firmware_version() branch order, final: override -> Connectivity.THREAD (VERSION_THREAD) -> specs.yml product default -> extended_multizone flag. Validation runs after resolution, in _validate_firmware(): Thread floor check first, then the per-product ceiling check (not skipped when an override was supplied) -- floor-before-ceiling ordering is load-bearing, confirmed by test_tile_on_thread_sub_floor_override_names_floor_not_ceiling"
  - "Thread-on-Tile message text: base message is f\"Firmware {result} exceeds product {product_id}'s maximum {max_firmware}\" (e.g. \"Firmware (4, 200) exceeds product 55's maximum (3, 50)\"), which already names both bounds since result and max_firmware both appear; when the rejection was caused by an unrequested Thread default (connectivity is Thread and override is None) an enrichment clause is appended: \" (Thread's default firmware of (4, 200) cannot be reduced to fit)\" -- satisfying D-06's \"naming both\" instruction explicitly rather than incidentally"
  - "A _validate_firmware(self, result, product_id, connectivity, override) private helper was needed to keep get_firmware_version() itself simple -- not because either function individually approached the complexity-10 ceiling, but to keep the resolution chain and the two-check validation visually and structurally separate, matching the plan's explicit instruction to extract a helper rather than inline both checks"
  - "Ruff select = [\"E\", \"F\", \"I\", \"N\", \"W\", \"UP\"] does not include PLR (pylint, including PLR0913 max-args) or C901 (mccabe complexity); both are configured under [tool.ruff.lint.pylint]/[tool.ruff.lint.mccabe] but not enforced by `uv run ruff check .`. firmware_config.py's get_firmware_version() has 4 non-self parameters, well inside the documented max-args=5 limit either way, so this phase does not need to invoke the exception -- noted here per the plan's instruction so a future maintainer does not assume ruff enforces a limit it does not"
  - "Registry-wide rejection test iterates every entry in PRODUCTS (no has_matrix filter on the loop) per the SPEC's registry-wide prohibition (01-SPEC.md:136, cross-AI review round 2 concern); a secondary has_matrix-filtered diagnostic assertion is kept in the same test so a future failure immediately shows whether a regression is matrix-specific or registry-wide"
  - "The two SKY-effect tests (test_sky_effect_on_non_ceiling_tile_device, test_other_effects_on_non_ceiling_still_work) were migrated from product 55 to 185 (LIFX Candle Color US) in the SAME task and the SAME GREEN commit as the ceiling enforcement, per RESEARCH.md Pitfall 3 -- landing them separately would have left the suite red the instant the ceiling landed, since create_device(55, firmware_version=(4, 4)) now raises ValueError"

requirements-completed: [CONN-02]

coverage:
  - id: D1
    description: "ProductSpecs gains max_firmware_major/minor and has_max_firmware_specs (isinstance-checked on both fields so a malformed specs.yml entry degrades to no-ceiling instead of raising TypeError); SpecsRegistry/module-level get_max_firmware_version() mirrors get_default_firmware_version()"
    requirement: "CONN-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestProductSpecs::test_has_max_firmware_specs_true"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestProductSpecs::test_has_max_firmware_specs_false_non_integer"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestTileTerminalFirmware::test_get_max_firmware_version_returns_tile_ceiling"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestTileTerminalFirmware::test_get_max_firmware_version_none_for_ceiling_product_default"
        status: pass
    human_judgment: false
  - id: D2
    description: "Product 55 (Tile) defaults to and is capped at firmware (3, 50); explicit (3, 50) accepted, (3, 51) raises naming both values"
    requirement: "CONN-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestTileTerminalFirmware::test_tile_default_firmware_is_now_terminal_version"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_products_specs.py::TestTileTerminalFirmware::test_create_device_55_reports_terminal_firmware"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_override_above_ceiling_raises"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_override_at_ceiling_accepted"
        status: pass
    human_judgment: false
  - id: D3
    description: "A Thread device with no explicit firmware defaults to and is floored at (4, 200), overriding any specs.yml product default; explicit override at/above the floor accepted, below raises naming the floor"
    requirement: "CONN-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_default_for_product_with_no_specs_default"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_default_overrides_specs_default"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_explicit_override_at_floor_accepted"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_thread_override_just_below_floor_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "Thread-on-Tile raises naming both the floor and the ceiling; floor check runs before ceiling check; an explicit override does not bypass the product ceiling"
    requirement: "CONN-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_on_thread_names_both_bounds"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_on_thread_override_does_not_bypass_ceiling"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_tile_on_thread_sub_floor_override_names_floor_not_ceiling"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every product ID in the whole registry other than 55 accepts connectivity=\"thread\" -- registry-wide, not matrix-scoped"
    requirement: "CONN-02"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadOnTileRejectionRegistryWide::test_only_product_55_is_rejected_registry_wide"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadOnTileRejectionRegistryWide::test_matrix_diagnostic_subset"
        status: pass
    human_judgment: false
  - id: D6
    description: "extended_multizone=False + connectivity=\"thread\" still reports has_extended_multizone True, because the Thread firmware default clears the product's min_ext_mz_firmware threshold; WiFi behaviour with the same argument is unchanged"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadExtendedMultizoneInteraction::test_extended_multizone_false_still_grants_extended_on_thread"
        status: pass
    human_judgment: false
  - id: D7
    description: "The two SKY-effect tests pass unchanged on product 185 instead of 55"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_tile_handlers_extended.py::TestSkyEffectRestrictions::test_sky_effect_on_non_ceiling_tile_device"
        status: pass
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_tile_handlers_extended.py::TestSkyEffectRestrictions::test_other_effects_on_non_ceiling_still_work"
        status: pass
    human_judgment: false
  - id: D8
    description: "A WiFi device's firmware resolution is unchanged (extended multizone 3.70, non-extended 2.60, and any specs.yml default still reported)"
    verification:
      - kind: unit
        ref: "packages/lifx-emulator-core/tests/test_thread_identity.py::TestThreadFirmwarePrecedence::test_wifi_extended_multizone_unaffected"
        status: pass
      - kind: integration
        ref: "uv run pytest -q --no-cov (1198 passed)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 02: Thread Firmware Precedence -- Default, Floor and Tile Ceiling Summary

**`FirmwareConfig.get_firmware_version()` now resolves a Thread device to firmware 4.200 by default and floors it there, while a per-product terminal-firmware ceiling declared in `specs.yml` (currently only the discontinued LIFX Tile, at 3.50) rejects any resolution above it -- so Thread-on-Tile fails on arithmetic alone, with zero product-ID comparisons anywhere in the source.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-09-09 (immediately following Plan 01)
- **Completed:** 2026-09-09
- **Tasks:** 2 completed
- **Files modified:** 7 (4 source, 3 test modules)

## Accomplishments

- Added `ProductSpecs.max_firmware_major/minor` and `has_max_firmware_specs` (both fields `isinstance`-checked as `int`, so a hand-corrupted `specs.yml` entry degrades to "no ceiling" instead of reaching a tuple comparison and raising `TypeError`), plus `SpecsRegistry.get_max_firmware_version()` and its module-level wrapper, mirroring the existing `default_firmware_*` machinery line for line
- Recorded product 55's (LIFX Tile) terminal firmware in `specs.yml`: `default_firmware_major/minor` and `max_firmware_major/minor` both `3`/`50` -- previously it fell through to the extended-multizone fallback of 3.70 with no ceiling at all
- Extended `FirmwareConfig.get_firmware_version()` with a fourth parameter, `connectivity: Connectivity | None = None` (narrowed to the enum, not `Connectivity | str | None`, since this internal resolver compares directly against `Connectivity.THREAD`), a new `VERSION_THREAD = (4, 200)` class constant, and a `_validate_firmware()` helper enforcing the Thread floor (checked first) and the product ceiling (checked second, never skipped for an explicit override)
- Wired `DeviceBuilder.build()` step 3 to pass the step-1a resolved `connectivity` into `get_firmware_version()`
- Migrated the two SKY-effect tests from product 55 to 185 in the same commit as the ceiling enforcement (RESEARCH.md Pitfall 3), added a firmware-precedence test class, a registry-wide Thread-rejection test iterating every `PRODUCTS` entry (not just matrix products), and a pinning test for the `extended_multizone=False` + Thread interaction

## Task Commits

Each task followed the RED-GREEN TDD cycle with a dedicated `test(...)` commit followed by a `feat(...)` commit; no `refactor(...)` commit was needed for either task (the implementation was already clean on the first GREEN pass, including the `_validate_firmware()` extraction called for by the plan).

1. **Task 1: Terminal-firmware ceiling in the product specs data layer**
   - `b04f9d4` (test) -- failing tests for `has_max_firmware_specs`, `get_max_firmware_version`, and the Tile default-firmware change
   - `c991a00` (feat) -- `ProductSpecs`/`SpecsRegistry`/`specs.yml` changes; full suite green (1183 passed)
2. **Task 2: Thread firmware default, floor and ceiling in the one precedence chain**
   - `f065a39` (test) -- failing tests for the `connectivity` parameter, Thread floor, Tile ceiling, registry-wide rejection and the extended-multizone pinning test; SKY tests migrated to product 185 in the same commit
   - `8ddabac` (feat) -- `firmware_config.py`/`builder.py` changes; full suite green (1198 passed), `ruff check`, `ruff format --check` and `pyright` all clean

_Plan-metadata commit follows this SUMMARY per the standard close-out step._

## Files Created/Modified

- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.py` - `max_firmware_major/minor` fields, `has_max_firmware_specs` property, `SpecsRegistry.get_max_firmware_version()` and its module-level wrapper
- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml` - Product 55's four firmware keys; header comment documents the two new optional keys and the extended precedence order
- `packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py` - `VERSION_THREAD`, `connectivity` parameter, `_validate_firmware()` floor/ceiling checks, updated docstring and doctests
- `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` - step 3 now passes `connectivity=connectivity` into `get_firmware_version()`
- `packages/lifx-emulator-core/tests/test_products_specs.py` - `has_max_firmware_specs` tests, `TestTileTerminalFirmware` class
- `packages/lifx-emulator-core/tests/test_tile_handlers_extended.py` - two SKY tests migrated from product 55 to 185
- `packages/lifx-emulator-core/tests/test_thread_identity.py` - `TestThreadFirmwarePrecedence`, `TestThreadOnTileRejectionRegistryWide`, `TestThreadExtendedMultizoneInteraction` classes

## Decisions Made

See `key-decisions` in frontmatter for the full list. The two most load-bearing:
- Floor-before-ceiling ordering in `_validate_firmware()` is intentional and tested directly (`test_tile_on_thread_sub_floor_override_names_floor_not_ceiling`): a sub-floor Thread override on product 55 must report the Thread floor violation, not the ceiling violation, even though both are true simultaneously.
- The Thread-on-Tile message enrichment (naming "Thread's default firmware ... cannot be reduced to fit") only fires when the rejection stemmed from an *unrequested* Thread default (`connectivity == THREAD and override is None`); an explicit override that also violates the ceiling gets the base ceiling message without the enrichment clause, since there the override -- not an unrequested default -- is what forced the value.

## Intermediate Wave 2-3 Window (recorded per plan `<output>` instruction)

As of this plan's commits, a WiFi Tile (product 55) reports host firmware `(3, 50)` (changed from the prior fallback of `(3, 70)`), but `devices/device.py`'s `EmulatedLifxDevice.__init__` still hard-codes each tile's `firmware_version_major/minor` to `3.70` in `StateDeviceChain` -- unchanged in this plan. A freshly built Tile therefore briefly reports a host firmware of 3.50 and a per-tile firmware of 3.70 that disagree with each other. No existing or new test in this plan asserts either the host or per-tile value for a *fresh* product-55 Tile specifically (the SKY tests that used to construct product 55 now use 185, and no other test in the suite happens to check product 55's per-tile firmware), so the suite stays green through this window. Plan 03 Task 2 closes the gap by mirroring the host firmware onto each tile at construction time. This is intentional and expected -- do not "fix" the per-tile literals ahead of Plan 03, and do not read the host/per-tile mismatch as a regression introduced by this plan.

## Deviations from Plan

None - plan executed exactly as written, including the TDD RED-GREEN cycle for both tasks (git log confirms `test(01-02): ...` immediately preceding each `feat(01-02): ...`), the `_validate_firmware()` helper extraction, and the registry-wide (not matrix-scoped) rejection test mandated by the Round 2 review disposition already baked into the plan text.

## Ruff Enforcement Gap (recorded per plan `<output>` instruction)

`max-args` (`PLR0913`) and `mccabe` (`C901`) complexity limits are configured under `[tool.ruff.lint.pylint]`/`[tool.ruff.lint.mccabe]` in the root `pyproject.toml` but are absent from `[tool.ruff.lint].select = ["E", "F", "I", "N", "W", "UP"]`, so `uv run ruff check .` does not currently enforce either limit. `firmware_config.py`'s public method stays within the documented `max-args = 5` limit regardless (4 non-`self` parameters), so this phase needed no exception; Plan 03 Task 1 is expected to record the scoped exception for the typed factory entry points, which already exceed the limit today.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 03 (typed factories + `wifi_signal` derivation, and closing the intermediate per-tile firmware mismatch noted above) and Plan 04 (persistence round trip) can build directly on `FirmwareConfig.VERSION_THREAD`, the `connectivity` parameter on `get_firmware_version()`, and `products.specs.get_max_firmware_version()` introduced here. No blockers.

---
*Phase: 01-thread-device-identity*
*Completed: 2026-09-09*

## Self-Check: PASSED

All 7 modified files verified present on disk with the expected changes; all four task commits (`b04f9d4`, `c991a00`, `f065a39`, `8ddabac`) verified present in git history via `git log --oneline`.
