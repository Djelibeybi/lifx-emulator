---
phase: 01-thread-device-identity
fixed_at: 2026-09-09T00:00:00Z
review_path: .planning/phases/01-thread-device-identity/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-09-09
**Source review:** .planning/phases/01-thread-device-identity/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope: all -- 1 warning, 2 info)
- Fixed: 3
- Skipped: 0

**Verification environment:** `workflow.use_worktrees` is `false` in this project's config,
so all edits, commits, and verification (pytest/ruff/pyright) ran directly in the main
checkout on branch `gsd/phase-01-thread-device-identity` -- no isolated worktree was created.
The numbers below are reproducible from this tree as-is.

## Fixed Issues

### WR-01: No invariant enforced between a product's firmware ceiling and its own default/fallback resolution

**Files modified:** `packages/lifx-emulator-core/tests/test_products_specs.py`
**Commit:** e9371ab
**Applied fix:** Added `test_every_ceiling_product_has_a_compatible_default` to
`TestCuratedProductSpecs` (mirroring the registry-wide pattern of
`TestThreadOnTileRejectionRegistryWide` in `test_thread_identity.py`). It iterates every
product in `PRODUCTS`, and for any product where `get_specs(pid).has_max_firmware_specs` is
true, asserts `FirmwareConfig().get_firmware_version(product_id=pid)` (no connectivity, no
override -- the plain default path) does not raise. This is a registry-wide test computed
from live data rather than a pinned product-ID literal, per the project rule for this
finding, and will catch a future `specs.yml` edit that adds a ceiling without a compatible
default. Currently only product 55 has a ceiling and it already passes.

### IN-01: Redundant condition when reusing the pre-built restorer

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`
**Commit:** 08a9a49
**Applied fix:** Simplified `if self._storage and restorer is not None:` to
`if restorer is not None:` at the top of step 11 in `DeviceBuilder.build()`, since `restorer`
is only ever non-`None` when `self._storage` is truthy (set at line 344). Added a one-line
comment noting the invariant so it doesn't look like an oversight.

### IN-02: Duplicated log argument in the connectivity-conflict warning

**Files modified:** `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`
**Commit:** abd74ce
**Applied fix:** Kept the two `%r` placeholders (dropping one would change the message
wording unnecessarily) and added an inline comment explaining that "requested" and "keeping"
are intentionally the same value today, since the explicit connectivity argument always wins
over a disagreeing saved value -- addressing the reviewer's second suggested option.

## Skipped Issues

None -- all in-scope findings were fixed.

## Verification

- `uv run pytest -q -p no:sugar`: 1229 passed, 0 failed
- `uv run ruff check .`: all checks passed
- `uv run ruff format --check .`: 108 files already formatted, no changes needed
- `uv run pyright`: 0 errors, 0 warnings, 0 informational

---

_Fixed: 2026-09-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
