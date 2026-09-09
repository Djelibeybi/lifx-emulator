---
phase: 1
round: 2
reviewers: [codex, opencode, antigravity]
reviewed_at: 2026-09-09T05:29:48Z
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md, 01-03-PLAN.md, 01-04-PLAN.md]
reviewed_commit: 5148a76
previous_round: c667eb9
models:
  codex: "gpt-5.6-sol (reasoning=high)"
  opencode: "openrouter/z-ai/glm-5.3 (reasoning=high)"
  antigravity: "gemini-3.8-flash-high"
model_sources:
  codex: "pinned"
  opencode: "pinned"
  antigravity: "pinned"
---

# Cross-AI Plan Review — Phase 1 (Round 2)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Round 2 reviews the plans as revised at `5148a76` after Round 1 (`c667eb9`). Each plan carries a `## Review Dispositions Ledger` for Round 1; reviewers were asked to audit those dispositions and report anything still open.

## Codex Review

The plans are substantially improved from round 1, but I would not execute them unchanged. Plans 01-01 and 01-04 still contain contract-level blockers; plan 01-04 also overlooks a reproducible failure in the real malformed-packet send path.

## 01-01

### Summary

The wire-baseline ordering and single header-stamping architecture are sound. However, the plan does not fully implement its locked `DeviceBuilder` API and its proposed “immutability” can be bypassed by replacing `state.network`.

### Strengths

- The fixture commit is correctly isolated before source changes. The existing flags implementation confirms the standalone fixture’s byte 22 must be `0x03`, not zero, because `res_required` and `ack_required` occupy bits 0–1 ([header.py:81](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py:81)).

- Stamping the bit once on `_response_header_template` is the right design. Every ordinary reply copies that template ([device.py:218](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:218)), and the server acknowledgement path delegates to the same helper ([server.py:197](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/server.py:197)).

- Round-one concerns about reserved-bit assertions, `repr`, WiFi byte preservation and acknowledgement delegation are reflected in the executable tasks.

### Concerns

- **HIGH — `DeviceBuilder.with_connectivity()` does not satisfy locked D-03.** D-03 requires `Connectivity | str | None = None` on `DeviceBuilder.with_connectivity()` ([01-CONTEXT.md:53](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-CONTEXT.md:53)), but the plan specifies a required `Connectivity | str` argument ([01-01-PLAN.md:298](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-01-PLAN.md:298)). Factory guarding makes common calls work, but the builder is itself part of CONN-01 and has no direct contract test.

- **HIGH — connectivity remains mutable through wholesale `NetworkState` replacement.** The plan explicitly tests that `dataclasses.replace(device.state.network, connectivity=...)` followed by assignment to `device.state.network` succeeds ([01-01-PLAN.md:226](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-01-PLAN.md:226)). The current direct-assignment allow-list permits that replacement ([states.py:417](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:417)). That contradicts the locked requirement that connectivity is immutable after construction ([01-SPEC.md:23](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-SPEC.md:23)).

- **LOW — uppercase `"THREAD"` is named in success criteria but not exercised.** The behaviour list tests `"Thread"` and `"bluetooth"` only ([01-01-PLAN.md:222](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-01-PLAN.md:222)).

### Suggestions

- Give `with_connectivity()` the exact locked signature and add direct builder tests for omitted, `None`, valid enum/string and invalid string values.

- Either prevent post-build replacement of `state.network`, or provide a private build/restore mechanism for wholesale replacement while rejecting it through the public `DeviceState` surface. If replacement is intentionally public, amend the immutability requirement instead of claiming both behaviours.

- Add `"THREAD"` to the invalid-value parametrisation.

### Risk Assessment

**HIGH.** The wire work is well designed, but the builder contract and radio immutability are public API semantics, not test-detail issues.

## 01-02

### Summary

The generic firmware floor/ceiling design is coherent and avoids a product-55 branch in Python. The main remaining gap is that the plan’s test claiming to protect all non-55 products actually covers matrix products only.

### Strengths

- The precedence chain extends the existing single resolver rather than duplicating it ([firmware_config.py:28](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py:28)).

- Floor-before-ceiling ordering is explicitly tested, including explicit overrides. This correctly distinguishes a sub-floor Thread request from a product-ceiling failure.

- Product 55’s terminal firmware is expressed in data. Its current block is the precise place for those keys ([specs.yml:214](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml:214)).

- Migrating both product-55 SKY tests in the same task as enforcement avoids an intermediate red suite; those tests currently request firmware 4.4 on product 55 ([test_tile_handlers_extended.py:720](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/tests/test_tile_handlers_extended.py:720), [test_tile_handlers_extended.py:928](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/tests/test_tile_handlers_extended.py:928)).

### Concerns

- **MEDIUM — the no-other-product prohibition is tested only for matrix products.** The plan says no product other than 55 may be rejected, but its registry test filters on `info.has_matrix` ([01-02-PLAN.md:269](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-02-PLAN.md:269)). Matrix capability is only one product classification ([registry.py:91](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/registry.py:91)); the SPEC prohibition is not matrix-scoped ([01-SPEC.md:136](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-SPEC.md:136)).

- **LOW — malformed ceiling data is not validated.** The YAML loader passes `max_firmware_*` values through without runtime type validation ([specs.py:100](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/specs.py:100)). Partial values can safely mean “no ceiling”, but two non-integer values would reach tuple comparison rather than degrading safely as the threat narrative suggests.

### Suggestions

- Iterate over every entry in `PRODUCTS`, attempt Thread construction, and assert that the complete rejected set is exactly `{55}`. A separate matrix-specific assertion can remain for clearer diagnosis.

- Either validate firmware spec fields as integers during loading or revise the threat-model statement so it does not promise safe handling of non-integer values.

### Risk Assessment

**MEDIUM.** The implementation mechanism is strong, but the prohibition test currently proves a narrower claim than the plan and SPEC make.

## 01-03

### Summary

This is the strongest plan. It uses the right builder-derived-state architecture and correctly qualifies tile firmware mirroring as fresh-construction behaviour. Its principal unresolved issue is knowingly expanding public functions beyond the project’s stated argument limit without a formal exception.

### Strengths

- Deriving `wifi_signal` when constructing `NetworkState` is correct. `GetWifiInfoHandler` already returns the state value verbatim ([device_handlers.py:158](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py:158)), so no handler branching is necessary.

- Typed factories follow the established forwarding structure in `factory.py`, keeping validation centralised in `create_device()` and the builder ([factory.py:240](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py:240)).

- Tile firmware mirroring uses already-resolved host state. The current hard-coded values are localised to the fresh tile construction block ([device.py:116](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:116)).

- The restored-device qualification is accurate: `_restore_matrix_state()` replaces saved tile dictionaries wholesale ([state_restorer.py:191](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py:191)).

### Concerns

- **MEDIUM — the argument-count rule is documented but still violated.** The plan acknowledges that several final signatures exceed five arguments and chooses existing precedent ([01-03-PLAN.md:132](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-03-PLAN.md:132)). The project instruction nevertheless states a maximum of five ([.claude/CLAUDE.md:196](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.claude/CLAUDE.md:196)). Ruff’s current selection not enforcing `PLR0913` ([pyproject.toml:33](/Volumes/External/Developer/Djelibeybi/lifx-emulator/pyproject.toml:33)) does not itself waive the project rule.

- **LOW — typed-factory tests do not fully pin the roadmap’s firmware promise.** The parametrisation primarily checks connectivity forwarding, while the firmware-query comparison is limited to colour lights. A typed factory could preserve connectivity yet mishandle its explicit firmware argument without this plan detecting it.

### Suggestions

- Record a formal, scoped exception for the factory API, or introduce a shared keyword-options object in a separately designed compatibility change. Merely documenting that lint does not enforce the rule leaves policy and implementation inconsistent.

- Extend the typed-factory parametrisation to assert the Thread default is 4.200 for every successful entry point and that an explicit valid Thread firmware wins.

### Risk Assessment

**MEDIUM.** Behavioural implementation risk is low, but the unresolved API policy exception and incomplete cross-factory firmware assertion prevent a LOW rating.

## 01-04

### Summary

The persistence cache, real server acknowledgement test and revised matrix tests are thoughtfully designed. Nevertheless, this plan has two execution blockers: it cannot truthfully map every locked SPEC criterion, and its malformed-packet test bypasses a real server-path failure.

### Strengths

- A single `StateRestorer` shared between peek and restore is a sensible way to meet the one-read requirement. The current restore method owns the disk read ([state_restorer.py:32](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py:32)), making the proposed cache boundary natural.

- Invoking `_send_ack()` with a recording transport tests the actual server delegation and wire datagram, not merely the helper. The source supports that setup because `transport` is a plain optional attribute ([server.py:109](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/server.py:109)).

- The round-one `State64` issue is correctly repaired. PID 201 is one 16×8 tile ([specs.yml:324](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml:324)), and `Get64Handler` emits one response per requested tile ([tile_handlers.py:131](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py:131)). Two requests for the Ceiling plus a separate synthetic two-tile chain are the correct tests.

- Corrupted persistence fixtures, filtered log assertions and optional-restorer guards are now executable and source-aligned.

### Concerns

- **HIGH — the locked SPEC still contains an impossible single-device criterion.** It requires one Thread device to produce both a `StateMultiZone` list and a `State64` list in one test ([01-SPEC.md:130](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-SPEC.md:130)). The plan correctly separates multizone and matrix devices, but later requires all 31 SPEC checkboxes to map to named tests ([01-04-PLAN.md:420](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-04-PLAN.md:420)). The live registry contains no product with both capabilities, so both instructions cannot be satisfied simultaneously.

- **HIGH — malformed replies cannot currently be emitted by the real server.** `_apply_error_scenarios()` returns raw `bytes` for malformed or invalid-field replies ([device.py:392](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:392)), while `_process_device_packet()` unconditionally calls `resp_packet.pack()` ([server.py:274](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/server.py:274)). A live reproduction at this checkout raised `AttributeError: 'bytes' object has no attribute 'pack'`. The proposed direct `device.process_packet()` test can pass while the server fails to write the reply. Task 2’s test-only assumption therefore hides a real defect.

- **MEDIUM — persistence tests reuse a shut-down backend.** The prescribed sequence shuts down `temp_storage` and then passes the same object into `create_device()` ([01-04-PLAN.md:193](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-04-PLAN.md:193)). `shutdown()` permanently closes its executor ([persistence.py:292](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py:292)), while device construction schedules a save when storage is present ([device.py:151](/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:151)). That can leave a background failure even if immediate assertions pass.

- **MEDIUM — adding Bandit to the permanent dev dependency set is phase scope expansion.** CI already performs its own Bandit installation immediately before running it ([ci.yml:66](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.github/workflows/ci.yml:66)). Plan 04 adds `pyproject.toml` and `uv.lock` changes solely to reproduce that gate ([01-04-PLAN.md:394](/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/phases/01-thread-device-identity/01-04-PLAN.md:394)), while deliberately leaving the now-redundant CI install in place.

### Suggestions

- Amend SPEC AC 23 so one multizone device covers all applicable common and multizone reply shapes, while separate matrix tests cover `State64`. Then the 31-item mapping becomes truthful.

- Add a recording-transport integration test for a malformed reply and repair the bytes-versus-packet send contract. Do not leave Task 2 test-only if that assertion exposes the existing server failure.

- After flushing and shutting down the writer, create a fresh `DevicePersistenceAsyncFile` pointing at the same temporary directory for reload, and shut that instance down after the test.

- Keep Bandit dependency housekeeping separate, or update CI in the same maintenance change so there is one declared installation mechanism. For this phase, running Bandit through an ephemeral uv tool environment would avoid altering the lockfile.

### Risk Assessment

**HIGH.** The plan cannot meet its own final verification contract as written, and a scenario explicitly claimed as covered fails before reaching the wire.

## Cross-plan assessment

### Round-one disposition status

Resolved in executable content:

- Correct byte-22 baseline assertions.
- Real `_send_ack()` coverage.
- Floor-before-ceiling validation and explicit-override cases.
- Product-55 typed-factory exception.
- Fresh-versus-restored tile firmware scope.
- Correct two-request Ceiling and separate chained-matrix tests.
- Corrupted-file setup, filtered logging and optional-restorer guards.

Still open or only partially resolved:

- The matrix correction was applied to plan 04 but not to the locked SPEC.
- The maximum-argument concern is acknowledged rather than reconciled.
- Bandit reproducibility is addressed through a permanent dependency change that introduces avoidable scope.
- The all-products prohibition remains tested only over matrix products.

Newly identified in round 2:

- `DeviceBuilder.with_connectivity()` does not carry the locked `None` contract.
- Replacing `state.network` bypasses connectivity immutability.
- The malformed-packet server path raises before sending.
- Persistence tests are instructed to reuse a storage executor after shutdown.

### Overall risk assessment

**HIGH — amendments required before execution.**

The phase architecture is fundamentally sound, but the following should be corrected first:

1. Reconcile public connectivity immutability and the exact builder signature.
2. Expand firmware rejection coverage across the full product registry.
3. Amend the stale single-device SPEC criterion.
4. Repair and integration-test malformed reply emission.
5. Reload persistence through a fresh storage instance.
6. Decide the argument-limit and Bandit changes explicitly rather than treating non-enforcement as approval.

I reviewed the clean live checkout at `5148a766c6be4d8335ad921a55403250a2244429`; no files were changed.



---

## OpenCode Review

# Cross-AI Plan Review — Phase 01 (Thread Device Identity), Round 2

Verified against source at current tree (header.py, states.py, builder.py, factory.py, firmware_config.py, specs.py/specs.yml, device.py, server.py, tile_handlers.py, state_restorer.py, state_serializer.py, tests, pyproject.toml, ci.yml, .pre-commit-config.yaml) and against the lifx-async sibling repo.

## 01-01

**Summary**: Sound vertical-slice plan. Every load-bearing claim checked out against source: `pack()` only emits bits 0–1 of byte 22 (`header.py:81-83`), the response-header template at `device.py:91-98` is the sole `LifxHeader(` construction site outside `header.py` itself (grep-verified in `src/`), `_create_response_header()` shallow-copies only `source/sequence/pkt_type/size` (`device.py:238-243`), `"network"` is already in the `__setattr__` direct-assignment set (`states.py:419`), and the routed-write `setattr` at `states.py:462` is unguarded today — exactly where D-08 wraps. The round-1 byte-22 fixture correction (`0x03`, masked `& 0xFC == 0`) is mathematically right: the round-trip fixture carries `res_required=True, ack_required=True`, so bits 0–1 are set, and device-reply fixtures genuinely carry `0x00`.

**Strengths**:
- Fixture-before-change commit ordering with a mechanical `git show --name-only` gate — the D-12 invariant is enforced, not asserted.
- Single stamping point verified: the grep criterion and the source agree — no other `LifxHeader(` construction site exists in `src/` (only `__pycache__` binaries match; see concern below).
- `wifi_signal` freeze is now tested with the correct refusal-message semantics (interpolated `attr_name`), and the `dataclasses.replace` escape hatch is asserted — verified the escape hatch works today because `"network"` bypasses routing (`states.py:417-441`).
- `__repr__` extension is additive — verified no test asserts on the current repr string.
- The `__str__ = str.__str__` correction with the accurate 3.11+/3.14 rationale is right; lifx-async uses the same idiom (`devices/base.py:79`), and default dev env resolves to 3.14.

**Concerns**:
- LOW — the single-stamping-point acceptance criterion `grep -rn "LifxHeader(" ... | grep -v "/protocol/header.py:" | grep -v "/devices/device.py:"` does not produce empty output on a dirty tree: the `protocol/__pycache__/header.cpython-314.pyc` binary-match line contains neither excluded pattern and survives both filters (reproduced in this repo). Add `--include="*.py"` (or `-I`) or the gate fails on the executor's machine while the invariant actually holds.
- LOW — internal contradiction with Plan 04: Task 2 requires a comment on `_resolve_connectivity(self, serial)` saying the serial parameter exists "so Plan 04 can add the saved-state peek without a signature change" — but 01-04 Task 1 changes the signature anyway (adds `restorer: StateRestorer | None`). The in-code comment will be false the moment Plan 04 lands. Reword to "without disturbing call sites that pass no serial" or drop the claim.
- LOW — `_resolve_connectivity` placement after step 1 and before step 3 is verified feasible (`builder.py:255-265`); nothing else depends on ordering. No concern beyond the comment issue above.

**Suggestions**:
- Fix the grep with `--include="*.py"`.
- Align the serial-parameter comment with 01-04's actual change.

**Risk Assessment**: LOW. Well-grounded vertical slice; the two issues are gate hygiene and a stale comment, not design.

## 01-02

**Summary**: Correct and unusually well-verified plan. The precedence chain matches `firmware_config.py:28-77` exactly (3 params today; 4 with `connectivity` stays inside max-args even under the unenforced limit). specs.yml claims all check out: product 55 has no firmware keys today (`specs.yml:214-220`), 176/177 carry `default_firmware: 4.10`, 185/186 carry none. The SKY tests at `test_tile_handlers_extended.py:723` and `:931` construct `create_device(55, ..., firmware_version=(4, 4))` exactly as claimed, and a repo-wide grep confirms they are the *only* product-55 constructions with an explicit firmware above 3.50 — all other `create_tile_device(...)` calls use defaults, so the same-commit migration fully covers the breakage. `create_device(38, extended_multizone=False)` → `(2, 60)` is right (38 has no specs firmware default), and 91 is absent from specs.yml so `(3, 70)` falls through as claimed.

**Strengths**:
- Tile rejection by arithmetic alone is verified sound: thread branch yields `(4,200)`, floor passes (`(4,200) >= (4,200)`), ceiling `(3,50)` rejects. Floor-before-ceiling ordering is pinned by an explicit behavior bullet (`override=(3, 40)` + Thread must fail on the floor) — this was the right round-1 fix.
- Ceiling applies to explicit overrides (`create_device(55, firmware_version=(4, 200))` raises) — matches the stated semantics and is acceptance-criterion-pinned.
- The comment-filtered `grep -c` gate and the registry-derived Thread-rejection test both fix real round-1 brittleness.
- `get_firmware_version` param narrowed to `Connectivity | None` closes the silent-WiFi-branch hole for raw strings; coercion stays in the builder, which runs first. Coherent.
- Import acyclicity claim spot-checked: `states.py` imports only stdlib/`protocol_types`/`constants`.

**Concerns**:
- LOW — intermediate-state window: after Task 1, a WiFi Tile reports host firmware 3.50 while `device.py:139-140` still hard-codes per-tile 3.70 until Plan 03 Task 2. No test asserts either value (verified by grep), so the suite stays green, but the inconsistency spans Waves 2–3. The plans never name this window. One sentence in 01-02's SUMMARY noting it would prevent a reviewer of the intermediate commit from "fixing" it.
- LOW — `create_device(55)` default change 3.70 → 3.50 also changes `has_extended_multizone`/`has_sensor` derivations for the Tile (`version_major >= 4` is false either way; `has_matrix` already true), so ripples are benign — but the plan's own reasoning for this is implicit in research, not in the plan text. Acceptable.
- LOW — Task 1's `<behavior>` `get_default_firmware_version(55)` returning `(3, 50)` "(it currently returns `None`)" is verified correct.

**Suggestions**:
- Add the intermediate-window note to the Task 1 action or SUMMARY output instructions.
- None else; plan is executable as written.

**Risk Assessment**: LOW. Highest-verification plan of the four; every numeric claim I traced held.

## 01-03

**Summary**: Correct completion of the factory surface and the two derived values. `wifi_signal` derivation at step 6 with the already-resolved connectivity is the right site (`builder.py:274`); `GetWifiInfoHandler` reading state verbatim means no handler change, and the plan forbids them with a diff gate. Per-tile firmware mirror at `device.py:139-140` is a two-literal swap with `self.state` assigned at `device.py:70` — no ordering hazard, verified. Ceiling `(4, 10)` and Candle `(3, 70)` expectations match specs.yml (176 default 4.10; 185 none → `VERSION_EXTENDED` fall-through). The fresh-vs-restored tile qualification is a real correctness fix from round 1 and matches `_restore_matrix_state()` (`state_restorer.py:216-227`).

**Strengths**:
- The `create_tile_device` expected-`ValueError` parametrisation resolves the unsatisfiable round-1 SPEC honestly, with the SPEC amendment recorded.
- `firmware_build` asserted as non-zero `int` rather than pinned — correct, it's `int(time.time())` (`device.py:138`).
- The "large matrix device" terminology gate (negative grep on "wide") enforces the CLAUDE.md rule mechanically.
- Restorer untouched, with a diff gate.

**Concerns**:
- LOW (factual error in rationale): Task 1 claims "The seven typed factories currently carry only a bare one-line docstring with NO `Args:` section" — false for three of them: `create_multizone_light` (`factory.py:79-88`), `create_tile_device` (`factory.py:111-121`) and `create_switch` (`factory.py:164-178`) already have full `Args:` sections. Only four are one-liners. The action (full docstrings on all seven) remains correct and the `grep -c "Args:" >= 8` criterion still holds (4 exist today, 8 after), but the executor is told to "replace the one-liner" on functions that don't have one — harmless, still sloppy.
- LOW — acceptance criterion `grep -F -c "connectivity: Connectivity | str | None = None" factory.py is 8` requires byte-exact signature text across eight functions including Plan 01's `create_device`. Fragile to line-wrapping (ruff format may wrap long signatures at 88 chars). A `grep -c "connectivity:" factory.py`-style count or per-function AST check would be sturdier; at minimum the criterion should acknowledge wrapping.
- LOW — `create_multizone_light`'s `extended_multizone: bool = True` default (not `None`) means the parametrised "omitted/None" factory test can only exercise `None` via `create_device`; the plan's parametrisation says "omitted or None" for all eight entry points, which is inexpressible for that one. Minor test-design wrinkle; will surface as an executor decision.

**Suggestions**:
- Correct the docstring-status claim: four one-liners, three existing `Args:` blocks to extend with the `connectivity:` line rather than rewrite.
- Soften or wrap-proof the exact-signature grep criterion.

**Risk Assessment**: LOW. Mechanical threading plan with correct placements and honest handling of the Tile exception.

## 01-04

**Summary**: Strong closing plan; the round-1 fixes are all real and verified in the executable text. The real-`_send_ack()` test is feasible exactly as described: `_send_ack` is synchronous, builds via `device._create_response_header(...)` and sends via `self.transport.sendto(...)` (`server.py:182-217`), and `transport` is a plain attribute initialised `None` (`server.py:109`) — plain assignment of a recording double works with no socket. The `Get64` split into large-matrix (two requests, one reply each) and chained-matrix (one request, `length=2`, two replies) cases matches `Get64Handler` (`tile_handlers.py:131-193`: one `State64` per tile index, 64 colours, rect-sliced) and PID 201's `max_tile_count: 1` / 16x8 specs entry. The bandit finding is verified: `bandit` is absent from `[dependency-groups] dev` (pyproject.toml:7-21) while ci.yml:68 installs it ad hoc, so `uv run bandit` from a clean `uv sync` fails today — the dev-group addition is the right CI-parity fix. The serializer/restorer changes match the real code (`serialize_device_state` unconditional dict at `state_serializer.py:94-111`; `restore_if_available` at `state_restorer.py:32-70`).

**Strengths**:
- Single-read design (`_load_saved_state` cache + shared restorer instance across step 1a and step 11) closes Pitfall 2 mechanically, with a counting-wrapper test to pin it. The `if not self.storage: return` guard in `_load_saved_state` mirrors `restore_if_available`'s existing guard (`state_restorer.py:41-42`) — correct for the storage-less common case.
- Corrupted/legacy fixture mechanism via `storage_dir` + `json.loads`/`write_text` is verified against reality: `save_device_state` takes a `DeviceState`, so dictionary mutation post-flush is the only public route, and the forbidden-private-API grep criterion enforces it.
- `caplog` filter-by-message rather than count is the right call — the restorer's product-mismatch warning (`state_restorer.py:51-56`) is real and co-fires in the product-mismatch test.
- `str(...)` vs `.value` decision recorded with rationale and backed by a verify command that fails if `__str__ = str.__str__` is dropped — good defence of a subtle dependency.
- Threat register is proportionate; T-01-13 correctly flags `_SERIAL_RE` as load-bearing and freezes `persistence.py` via a diff gate.

**Concerns**:
- MEDIUM — Task 2's all-shapes test relies on the scenario-path ack being produced "inside `process_packet()` with a scenario carrying `response_delays={45: 0.01}` so `affects_acks` is true". I could not fully verify `ScenarioConfig.affects_acks` semantics from the plan's read-first list alone (not read this session), and the plan does not state what `affects_acks` keys on. If `affects_acks` is keyed on `drop_packets`/`response_delays` packet-type membership, a `response_delays={45: ...}` entry must actually flip it. This is the one mechanism in Task 2 taken on faith; the executor has the read-first pointers (`scenarios/models.py`), but the plan should state the expected predicate so a silent `affects_acks == False` (test still passing via the fast-path ack) cannot masquerade as coverage of the scenario-path ack shape.
- LOW — Task 3 says "all 31 SPEC acceptance-criteria checkboxes (27 positive plus the 4 must-NOT items)" while CONTEXT/RESEARCH describe 30 acceptance criteria. The 30-vs-31 discrepancy is unexplained; the SUMMARY mapping task needs the authoritative count or an executor will either double-count or hunt a phantom checkbox.
- LOW — Task 3 acceptance `grep -rc "type: ignore"` totals 1 — verified exactly 1 today (`protocol/base.py:283`), so the criterion is sound; but the phrasing "totals 1 across the tree" via `grep -rc` sums per-file counts including zero-lines? `grep -rc` prints `file:count` including files with 0 matches only if… actually `grep -r -c` lists only files with ≥1 match by default? No — with `-r` and `-c`, files with zero matches are also listed in newer grep versions on some platforms. Minor gate-fragility; use `grep -rn "type: ignore" | wc -l == 1` instead.
- LOW — Task 1 changes `_resolve_connectivity`'s signature (adds `restorer`), contradicting Plan 01's in-code comment rationale (see 01-01 concern). Also the builder must now construct `StateRestorer` before step 1a *before serial validation happens* — wait, step 1a is after step 1 (serial generation), so `serial` is available. Verified feasible.

**Suggestions**:
- State the `affects_acks` predicate explicitly in Task 2's action (e.g. "assert `scenario.affects_acks` is True in the test setup" or cite the models.py line), so the scenario-path ack shape is provably exercised rather than assumed.
- Reconcile the 30/31 acceptance-criteria count.
- Replace `grep -rc` with `grep -rn ... | wc -l` for the type-ignore total.

**Risk Assessment**: LOW-to-MEDIUM (LOW if the `affects_acks` predicate is confirmed). Everything else traced cleanly.

## Cross-Plan Assessment

**Round-1 dispositions**: I checked every "addressed" disposition against the plan text and, where possible, source. All are genuinely reflected: the byte-22 `0x03`/masked assertion (and the grep proving `== 0x00` is absent), the `wifi_signal` frozen-write behaviour and message interpolation, the single step-1a placement instruction, the narrowed `Connectivity | None` on `firmware_config` with a grep criterion, the comment-filtered specs.yml gate, the registry-derived Thread-rejection test, SKY migration in the same task, the fresh-vs-restored tile qualification, the real-`_send_ack` datagram test, the bandit dev-group addition with the package audit, the peek guards, caplog filtering, and the storage_dir fixture mechanism. The one rejected round-1 item (Antigravity's "3-element response tuple") was correctly rejected — no `[2]` indexing or `(header, packet, payload)` exists in the plan. **No round-1 concern remains open.**

**Wave ordering**: Sound. Fixture commit → header bit → firmware rules → factory surface → persistence/matrix gates. Each plan's `depends_on` matches its actual data dependency (e.g. Plan 02 needs Plan 01's step-1a `connectivity` local; Plan 04 needs the serial param from Plan 01 and the restorer from the current code).

**Consistency issues found across plans**:
1. `_resolve_connectivity` signature-comment (01-01) vs actual signature change (01-04) — LOW.
2. 30 vs 31 acceptance-criteria count (01-04 vs SPEC/CONTEXT) — LOW.
3. 01-02/01-03 intermediate-state window (WiFi Tile host 3.50 + per-tile 3.70) unmentioned — LOW.
4. 01-03's docstring-status claim wrong for 3 of 7 factories — LOW.
5. Binary/pycache grep-gate fragility in 01-01 — LOW.

**Overall Risk Assessment**: **LOW**. All four plans are grounded in verified source; the architecture (single header template, single firmware chain, builder step 1a, single-read restorer peek) is correct for this codebase and each placement claim I traced matched the actual code at the cited lines. The concerns are gate hygiene, stale cross-plan comments, and one unverified scenario predicate (`affects_acks`) — none block execution. Fix the five consistency items above, ideally before Wave 1 starts since 01-01's grep gate and comment will otherwise fail/mislead during its own execution.


---

## Antigravity Review

## 01-01

### 1. Summary
Plan 01-01 establishes the foundational wire-level and in-memory representation of Thread identity for LIFX devices. It introduces the `Connectivity` enum in [`packages/lifx-emulator-core/src/lifx_emulator/devices/states.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/states.py#L47-L52), freezes `NetworkState` to enforce radio immutability, adds the `thread_connection` bit (frame-address byte 22, bit 3) to [`LifxHeader`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py#L21-L51), and leverages [`EmulatedLifxDevice._response_header_template`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L89-L98) as the single stamping point for all outgoing replies. The two-task sequence—locking baseline wire byte fixtures in `test_header.py` and `test_thread_identity.py` before touching any production code—guarantees backward compatibility for existing WiFi devices. All round-1 review feedback items for this plan have been properly addressed.

### 2. Strengths
- **Pre-change wire baseline isolation**: Task 1 commits wire byte fixtures (`_HEADER_FIXTURE_BEFORE` and reply headers for `StateService`, `StateColor`, `Acknowledgement`, and `StateUnhandled`) prior to any code changes in `header.py` or `device.py`. Executing the capture recipe against the unmodified tree at `HEAD` confirms `_HEADER_FIXTURE_BEFORE[22] == 0x03` (due to `res_required` and `ack_required` in bits 0–1) with reserved bits clear (`& 0xFC == 0`), while all device response headers have byte 22 strictly `0x00`.
- **Single template stamping point**: Stamping `thread_connection=self.state.connectivity == Connectivity.THREAD` directly onto `self._response_header_template` in [`device.py:91-98`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L91-L98) cleanly propagates to standard data responses ([`device.py:364`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L364)), scenario acks ([`device.py:310,330`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L310)), `StateUnhandled` ([`device.py:300`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L300)), and the server's fast-path ack ([`server.py:197`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/server.py#L197)) via `_create_response_header()` without touching individual packet handlers.
- **Robust immutability via stdlib**: Making `NetworkState` a `@dataclass(frozen=True)` in [`states.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/states.py#L47) and intercepting `dataclasses.FrozenInstanceError` in [`DeviceState.__setattr__`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/states.py#L461-L463) cleanly raises `ValueError` when callers attempt to modify `state.connectivity` or `state.wifi_signal`. Meanwhile, `state.network` remains on the direct assignment bypass list ([`states.py:417-440`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/states.py#L417-L440)), preserving the supported `dataclasses.replace(state.network, ...)` escape hatch.
- **Sibling repo parity**: `Connectivity(str, Enum)` with `__str__ = str.__str__` mirrors [`lifx-async/src/lifx/devices/base.py:79-96`](file:///Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/devices/base.py#L79-L96), ensuring clean formatting as `"thread"` and `"wifi"` across Python 3.10 through 3.14.

### 3. Concerns
- **Binary pycache matches in acceptance grep (LOW)**: In Task 2 acceptance criteria and `<verification>` step 6, the check `grep -rn "LifxHeader(" packages/lifx-emulator-core/src/lifx_emulator/ | grep -v "/protocol/header.py:" | grep -v "/devices/device.py:"` fails when Python bytecode files exist in `__pycache__` (e.g. `packages/lifx-emulator-core/src/lifx_emulator/protocol/__pycache__/header.cpython-314.pyc matches`). Because the string is binary, `grep -v "/protocol/header.py:"` does not filter it out.
  - *Evidence*: Running `grep -rn "LifxHeader(" packages/lifx-emulator-core/src/lifx_emulator/ | grep -v "/protocol/header.py:" | grep -v "/devices/device.py:"` on the workspace emits `Binary file packages/lifx-emulator-core/src/lifx_emulator/protocol/__pycache__/header.cpython-314.pyc matches`.
  - *Mechanism*: `grep -r` searches binary files unless instructed otherwise. Passing `-I` (ignore binary) or `--include="*.py"` resolves this.

### 4. Suggestions
- Update the grep verification command in Task 2 to include `-I` or `--include="*.py"`: `grep -rn -I "LifxHeader(" packages/lifx-emulator-core/src/lifx_emulator/ | grep -v "/protocol/header.py:" | grep -v "/devices/device.py:"`.

### 5. Risk Assessment
- **Risk Level: LOW**
- *Justification*: The plan is tightly scoped, touches no network I/O or packet routing, and captures regression fixtures before modifying code. The single stamping point in `_response_header_template` minimizes wire mutation bugs, and the round-1 feedback on byte 22 assertions and `wifi_signal` error messages has been fully incorporated.

---

## 01-02

### 1. Summary
Plan 01-02 implements host firmware resolution and ceiling constraints. It introduces `FirmwareConfig.VERSION_THREAD = (4, 200)` in [`factories/firmware_config.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py#L24-L27), extends the precedence chain in `get_firmware_version()`, adds optional `max_firmware_major` and `max_firmware_minor` fields to `ProductSpecs` in [`products/specs.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/specs.py#L46-L50), and defines a terminal-firmware ceiling of 3.50 for product 55 (LIFX Tile) in [`products/specs.yml`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml#L214-L220). Crucially, the plan migrates the two existing SKY effect tests on product 55 in [`test_tile_handlers_extended.py:723,931`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/tests/test_tile_handlers_extended.py#L723) to product 185 (Candle Color) in the exact same task, preventing suite breakage. All round-1 concerns are resolved.

### 2. Strengths
- **Generic arithmetic rejection without product ID literals**: Rejection of Thread on the original LIFX Tile (product 55) is derived purely from arithmetic: `get_max_firmware_version(55)` returns `(3, 50)`, which is lower than `VERSION_THREAD = (4, 200)`. There are zero product ID literals in `firmware_config.py`, verified by checking `grep -nE "(product_id|pid)\s*==" factories/firmware_config.py`.
- **Strict validation ordering**: `FirmwareConfig.get_firmware_version()` enforces floor validation *before* ceiling validation. Thus, `create_device(55, firmware_version=(3, 40), connectivity="thread")` correctly fails with a message indicating the Thread floor of (4, 200), rather than passing the floor check or failing solely on the ceiling. Conversely, an explicit override above the product ceiling (`create_device(55, firmware_version=(4, 200))`) is rejected by the ceiling rule.
- **Coordinated atomic migration**: The Tile terminal ceiling of 3.50 would immediately cause `test_sky_effect_on_non_ceiling_tile_device` and `test_other_effects_on_non_ceiling_still_work` to fail during device creation because they currently pass `firmware_version=(4, 4)` to product 55 ([`test_tile_handlers_extended.py:723,931`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/tests/test_tile_handlers_extended.py#L723)). Coupling this migration to product 185 in Task 2 prevents broken intermediate states.
- **Narrowed type signature**: As requested in round 1, `get_firmware_version()` accepts `connectivity: Connectivity | None = None` rather than the wide union `Connectivity | str | None`. String coercion occurs in `DeviceBuilder._resolve_connectivity()` before calling `get_firmware_version()`, eliminating runtime type ambiguity.

### 3. Concerns
- **Potential ambiguity in two-lookahead regex matching (LOW)**: In Task 2 tests, the plan suggests `pytest.raises(..., match=r"(?=.*200)(?=.*50)")` to verify that both the floor and ceiling appear in the Thread-on-Tile error message. In Python's `re` module, `re.search(r"(?=.*200)(?=.*50)", text)` matches the empty prefix if both substrings are present anywhere in `text`. While functionally correct, using an explicit regex with message capture (e.g. `exc_info.value`) or `r"(?=.*200)(?=.*50)"` in `pytest.raises(..., match=...)` is concise but can be sensitive to newline boundaries in error formatting.
  - *Evidence*: `pytest.raises(ValueError, match=r"(?=.*200)(?=.*50)")`.
  - *Mechanism*: Standard `re.search` handles lookaheads across single lines; ensuring dotall flag or single-line error string prevents unexpected match failures.

### 4. Suggestions
- Ensure the error message string in `FirmwareConfig.get_firmware_version()` for Thread-on-Tile is formatted as a single line, or test `assert "200" in str(exc.value) and "50" in str(exc.value)` to avoid regex engine edge cases across multiline exception formatting.

### 5. Risk Assessment
- **Risk Level: LOW**
- *Justification*: The firmware precedence hierarchy is simple and clean. Data-layer additions to `specs.yml` and `specs.py` follow the exact patterns already established for `default_firmware_*`. The test migration is atomic, and round-1 concerns around dead scenario code and type narrowing have been cleanly resolved.

---

## 01-03

### 1. Summary
Plan 01-03 completes the device identity surface. It extends all seven typed factories in [`factories/factory.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py#L16-L188) with the `connectivity: Connectivity | str | None = None` parameter, deriving `wifi_signal = 0.0` at build time for Thread devices ([`builder.py:274`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py#L274)) so that [`GetWifiInfoHandler`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py#L166) automatically reports 0.0 without changing handler signatures. In Task 2, it dynamically mirrors the device's host firmware to each tile in [`EmulatedLifxDevice.__init__`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L139-L140) for freshly constructed matrix devices. Round-1 adjustments (such as amending SPEC AC 2 regarding `create_tile_device` raising `ValueError` for Thread) are faithfully implemented.

### 2. Strengths
- **Handler insulation**: Neither `GetWifiInfoHandler`, `GetHostFirmwareHandler`, nor `GetWifiFirmwareHandler` is modified. By resolving `wifi_signal = 0.0` and `version_major, version_minor = (4, 200)` into `DeviceState` at build time in `builder.py`, handlers continue to read state properties directly. This adheres strictly to the architectural design rule forbidding transport or connectivity logic in packet handlers.
- **Accurate typed factory documentation**: As identified in round 1, several typed factories in `factory.py` previously had minimal one-line docstrings lacking `Args:` blocks. Task 1 expands all seven typed factories with comprehensive Google-style docstrings documenting all parameters, fully aligning the module with project conventions.
- **Handling of `create_tile_device`**: Acknowledging that `create_tile_device()` hard-codes product 55 (capped at 3.50), the plan correctly treats `create_tile_device(connectivity="thread")` as an expected `ValueError` in the factory test parametrisation, aligning code, tests, and amended SPEC AC 2.
- **Host firmware mirroring in tiles**: Replacing the hardcoded 3.70 in `tile_devices` ([`device.py:139-140`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/device.py#L139-L140)) with `self.state.version_major` and `self.state.version_minor` correctly yields (4, 200) for Thread Ceiling, (4, 10) for WiFi Ceiling, and (3, 70) for Candle. The plan explicitly notes that restored matrix devices keep their saved tile firmware, leaving `StateRestorer._restore_matrix_state()` untouched.

### 3. Concerns
- **Exceeding pylint max-args on factories (LOW)**: Adding `connectivity` to `create_multizone_light` (now 8 parameters), `create_tile_device` (now 9 parameters), and `create_device` (now 12 parameters) exceeds the documented `max-args = 5` in [`pyproject.toml:43`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/pyproject.toml#L43).
  - *Evidence*: `pyproject.toml` defines `[tool.ruff.lint.pylint] max-args = 5`, but `PLR0913` is not included in `[tool.ruff.lint] select`.
  - *Mechanism*: As noted in the plan, `ruff check .` passes because `PLR` is not in `select`. The plan documents this intentional trade-off in the SUMMARY, following the precedent set by `advertised_services` in PR #156.

### 4. Suggestions
- Ensure that the SUMMARY explicitly lists the parameter counts of all updated factory functions as required by the plan instructions.

### 5. Risk Assessment
- **Risk Level: LOW**
- *Justification*: The changes in `factory.py`, `builder.py`, and `device.py` are straightforward forwarding and derivation steps. No handler interfaces are altered, and the matrix tile firmware mirror only applies to newly initialized state objects.

---

## 01-04

### 1. Summary
Plan 01-04 finishes the phase by implementing persistence for `connectivity`, providing complete test coverage across all LIFX reply shapes, and enforcing CI parity. In Task 1, `connectivity` is added unconditionally to [`serialize_device_state()`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py#L94-L111). `StateRestorer` gains `peek_connectivity()` with a single-read cache ([`state_restorer.py:24-35`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py#L24-L35)), allowing `DeviceBuilder.build()` to resolve connectivity in step 1a before `NetworkState` is constructed, reading disk exactly once. In Task 2, all reply shapes—data replies, fast-path acks via `server._send_ack()`, scenario-path acks, `StateUnhandled`, and multi-packet replies (including large matrix devices via two `Get64` calls and synthetic chained matrix devices)—are verified to carry bit 3. In Task 3, `bandit` is added to `[dependency-groups] dev` in `pyproject.toml` and locked in `uv.lock`, establishing true local CI parity. All round-1 concerns are resolved.

### 2. Strengths
- **Single disk read with frozen dataclass**: Resolving persistence before state construction in `DeviceBuilder.build()` step 1a avoids the pitfall of attempting to mutate a frozen `NetworkState` during step 11 restore. Caching the loaded state dict in `StateRestorer._load_saved_state(serial)` ensures that `storage.load_device_state(serial)` is invoked exactly once per build.
- **Robust test doubles for server ack**: Rather than testing fast-path acks via direct calls to `device._create_response_header()`, Task 2 sets up an `EmulatedLifxServer` with a lightweight recording transport double assigned to `server.transport`. Calling `server._send_ack(device, request_header, addr)` exercises the actual server method that serialises and transmits datagrams, verifying byte 22 on the real wire payload without binding a UDP socket.
- **Accurate matrix test architecture**: In response to round-1 feedback, matrix testing is split into:
  1. *Large matrix device*: LIFX Ceiling (PID 201), a single 16x8 tile read via two sequential `Get64` requests (`y=0` then `y=4`, `width=16`, `length=1`), returning one 64-color `State64` per request with bit 3 set.
  2. *Chained matrix device*: Synthetic matrix device with `tile_count=2` read via a single `Get64(length=2)` request, returning two `State64` replies with bit 3 set.
  This accurately models the behavior of `Get64Handler` ([`tile_handlers.py:135-195`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py#L135-L195)) without conflating large tiles with tile chains.
- **CI parity via `uv add --group dev bandit`**: Adding `bandit` directly to the `dev` dependency group in `pyproject.toml` ensures that `uv run bandit -r ...` can be executed in any environment without requiring an out-of-band `uv pip install bandit` step.

### 3. Concerns
- **Missing `logger` definition in `builder.py` (LOW)**: Task 1 specifies that `DeviceBuilder._resolve_connectivity()` emits `logger.warning` when saved connectivity disagrees with factory arguments or when an unrecognised value is encountered. However, `builder.py` does not currently import `logging` or define `logger = logging.getLogger(__name__)`.
  - *Evidence*: Searching `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` shows no import of `logging` or definition of `logger`.
  - *Mechanism*: If the implementer calls `logger.warning(...)` without adding the logger boilerplate, a `NameError` will occur at runtime.
- **Verify command git inspection timing in Task 2 (LOW)**: Task 2 includes the automated verify command:
  `<automated>git show --name-only --format= HEAD -- packages/lifx-emulator-core/src/</automated>`
  with `<fails_when>any output line other than a file the task explicitly repaired ...</fails_when>`.
  - *Evidence*: Plan 01-04 Task 2 verify block.
  - *Mechanism*: If the test verification command is executed before Task 2 is committed, `git show HEAD` will inspect the commit from Task 1, which modified three files under `src/` (`state_serializer.py`, `state_restorer.py`, `builder.py`), causing the verification step to fail. Checking working tree modifications via `git diff HEAD --stat -- packages/lifx-emulator-core/src/` or ensuring Task 2 is committed prior to running `git show HEAD` prevents this.

### 4. Suggestions
- Explicitly instruct the executor in Plan 01-04 Task 1 to add `import logging` and `logger = logging.getLogger(__name__)` at the top of [`factories/builder.py`](file:///Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py).
- In Plan 01-04 Task 2, change the automated check to `git diff HEAD --stat -- packages/lifx-emulator-core/src/` (or `git status --porcelain -- packages/lifx-emulator-core/src/`) to ensure uncommitted working tree changes in `src/` are flagged during task execution.

### 5. Risk Assessment
- **Risk Level: LOW**
- *Justification*: The plan thoroughly covers all edge cases: corrupt files, missing keys, explicit argument precedence, single-read disk caching, all wire reply shapes, and CI parity. The matrix test restructuring cleanly matches emulator architecture and protocol specifications.

---

## Round 1 Ledger Audit & Cross-Plan Synthesis

### Round 1 Feedback Dispositions Review
All 12 concerns raised during Round 1 (`c667eb9`) across the four plans have been reviewed against the revised plan texts and the repository source code:

| Plan | Concern / Finding | Round 1 Disposition | Round 2 Verification | Status |
|---|---|---|---|---|
| **01-01** | Byte 22 fixture assertion mathematically wrong (`0x00` vs `0x03`) | Addressed in Task 1 | Masked `& 0xFC == 0` and whole-byte `== 0x03` added; verified against captured hex | **CLOSED** |
| **01-01** | Freezing `NetworkState` also freezes `wifi_signal`; untested | Addressed in Task 2 | `<behavior>` and tests added for `wifi_signal` rejection and `dataclasses.replace` | **CLOSED** |
| **01-01** | Builder step-0 placement stated two contradictory ways | Addressed in Task 2 | Single placement instruction: step 1a between serial gen and firmware | **CLOSED** |
| **01-01** | `_resolve_connectivity(self, serial)` unused param | Addressed in Task 2 | Documented with code comment explaining forward compatibility with Plan 04 | **CLOSED** |
| **01-01** | `grep -c "LifxHeader("` cannot express single construction site | Addressed in Task 2 | Replaced with file-filtering grep (minor binary flag refinement noted above) | **CLOSED** |
| **01-01** | `LifxHeader.__repr__` omits bit 3 | Addressed in Task 2 | `thread={self.thread_connection}` added to repr and tested | **CLOSED** |
| **01-02** | CONN-02 promises dead `firmware_version` scenario override | Addressed in SPEC / Plan | Scenario override removed from CONN-02 and success criteria; gap recorded | **CLOSED** |
| **01-02** | `FirmwareConfig.get_firmware_version` wide union signature | Addressed in Task 2 | Parameter narrowed to `Connectivity \| None = None` | **CLOSED** |
| **01-02** | Grep gate prevented documenting `max_firmware_major` in YAML | Addressed in Task 1 | Comment-filtering grep (`grep -v '^[[:space:]]*#'`) implemented | **CLOSED** |
| **01-02** | Verify command hard-coded `thread matrix products: 27` | Addressed in Task 2 | Replaced with dynamic calculation from `PRODUCTS` registry | **CLOSED** |
| **01-02** | Override ceiling rejection & floor-before-ceiling order unpinned | Addressed in Task 2 | Pinned with explicit test cases and ordered validation logic | **CLOSED** |
| **01-02** | `extended_multizone=False` + Thread interaction unpinned | Addressed in Task 2 | Documented and pinned with test asserting `has_extended_multizone=True` | **CLOSED** |
| **01-03** | SPEC AC 2 unsatisfiable (`create_tile_device` hard-codes PID 55) | Addressed in SPEC / Plan | SPEC and plan amended; `create_tile_device` tested as expected `ValueError` | **CLOSED** |
| **01-03** | Persisted matrix devices tile firmware claimed universally | Addressed in Task 2 | Truth qualified as "FRESHLY CONSTRUCTED"; limitation documented | **CLOSED** |
| **01-03** | Docstring updates underspecified for typed factories | Addressed in Task 1 | Replaced one-line docstrings with full Google-style docstrings with `Args:` | **CLOSED** |
| **01-04** | `State64` Ceiling test was 1-element tautology | Addressed in Task 2 | Split into large matrix device (2 requests) & chained matrix device (`length=2`) | **CLOSED** |
| **01-04** | Fast-path ack tested indirectly | Addressed in Task 2 | Uses real `server._send_ack()` with recording transport test double | **CLOSED** |
| **01-04** | Bandit gate not CI-equivalent | Addressed in Task 3 | Added `uv add --group dev bandit` step and locked in `uv.lock` | **CLOSED** |
| **01-04** | Corrupted fixture setup underspecified | Addressed in Task 1 | Exact recipe rewriting `<serial>.json` on disk specified | **CLOSED** |
| **01-04** | Caplog count assertion brittle | Addressed in Task 1 | Filtered by serial and `"connectivity"` substring | **CLOSED** |
| **01-04** | Storage/Restorer `None` guards | Addressed in Task 1 | Guards added to `_load_saved_state` and `_resolve_connectivity` | **CLOSED** |

**Zero Round 1 concerns remain open.**

### Overall Phase Risk Assessment
- **Overall Phase Risk: LOW**
- **Conclusion**: The four implementation plans for Phase 1 provide an exceptionally thorough, robust, and well-sequenced roadmap. The division of work across waves (Wave 1: wire format and basic model; Wave 2: firmware rules and Tile ceiling; Wave 3: factory surface and matrix tile firmware mirror; Wave 4: persistence and full reply matrix) ensures that each concept is verified before dependent rules are layered on top. With the few minor grep and logger suggestions noted above, the plans are ready for autonomous execution.


---

## Consensus Summary

All three reviewers ran source-grounded against `5148a76` with `file:line` evidence and covered all four plans. **Round 1 dispositions:** OpenCode and Antigravity each audited every Round 1 "addressed" row against the plan text and source and report zero Round 1 concerns still open; Codex agrees on the executable fixes but lists four Round 1 items as only partially resolved (the SPEC not carrying the matrix correction, `max-args` acknowledged rather than reconciled, Bandit via a permanent dependency, the prohibition test scoped to matrix products). Verdicts diverge again: Codex **HIGH until amended**, OpenCode **LOW**, Antigravity **LOW**. As in Round 1 the split is about weighting a handful of concrete text defects, most of them new; the orchestrator checked each contested Codex claim against the plan files and source before weighting it.

### Agreed Strengths

- **All Round 1 executable fixes landed and are correct** (all three): byte-22 `0x03`/masked assertion; real `_send_ack()` datagram test on a plain `server.transport` attribute (`server.py:109`, `:182-217`); the Ceiling case as two `Get64` requests to PID 201 plus a separate chained-matrix case, matching `Get64Handler` (`tile_handlers.py:131-193`); floor-before-ceiling with explicit-override cases; `get_firmware_version` narrowed to `Connectivity | None`; `create_tile_device` expected-`ValueError` parametrisation with SPEC AC 2 amended; fresh-vs-restored tile-firmware qualification matching `_restore_matrix_state()`; corrupted-file fixture through the public `storage_dir`; `caplog` filtered by serial + "connectivity"; `restorer`/`storage` `None` guards; Bandit added to the dev group (OpenCode and Antigravity endorse; Codex objects, see below).
- **Architecture unchanged and re-verified** (all three): single header template (`device.py:91-98`) is the only `LifxHeader(` construction site in `src/`; `_create_response_header()` copies only `source/sequence/pkt_type/size`; `"network"` already in the direct-assignment set (`states.py:417-441`); single firmware chain; builder step 1a after serial generation; single-read restorer cache.
- **Fixture-first commit gate is mechanical** (all three) and the Antigravity 3-tuple rejection from Round 1 was correct (OpenCode, Antigravity).

### Agreed Concerns

Ordered by priority. A concern is listed when two or more reviewers raised it, or when a single reviewer's claim was confirmed by the orchestrator against the plan text or source.

1. **[HIGH — confirmed] `DeviceBuilder.with_connectivity()` does not carry the locked D-03 signature** (Codex HIGH; orchestrator verified). 01-01-PLAN.md:299-300 specifies `with_connectivity(self, connectivity: Connectivity | str) -> DeviceBuilder`, but D-03 (01-CONTEXT.md:53) locks `connectivity: Connectivity | str | None = None` on the builder as well as the factories, and the builder is part of CONN-01 with no direct contract test. **Fix:** make the signature `Connectivity | str | None = None`, have `None` mean "unspecified" exactly as in `create_device()`, and add direct builder tests for omitted, `None`, enum, valid string and invalid string.
2. **[HIGH — confirmed, pre-existing defect outside the plan text] the server cannot send a malformed or invalid-field reply** (Codex HIGH; orchestrator verified in source). `_apply_error_scenarios()` appends `(resp_header, resp_payload_modified)` where the payload is already `bytes` (`device.py:392-405`), but `_process_device_packet()` unconditionally calls `resp_packet.pack()` (`server.py:275`), so a `malformed_packets` or `invalid_field_values` scenario raises `AttributeError: 'bytes' object has no attribute 'pack'` on the wire path today. Plan 01-04 Task 2's device-level "bit survives malformed truncation" test is valid but cannot see this. **This is a real bug in `main`, not a plan defect.** Decide explicitly: fix it inside Phase 1 (add an `isinstance(resp_packet, bytes)` branch in `server.py:275` plus a recording-transport test, and record it as a deviation from the SPEC's "in-memory only" boundary) or capture it as a separate quick task before Phase 6 needs scenario-driven wire tests. Do not leave it unrecorded.
3. **[HIGH — confirmed] SPEC AC 23 still names a single device that no product can be** (Codex HIGH; orchestrator verified at 01-SPEC.md:130). It requires one Thread device to produce both a `StateMultiZone` list and a `State64` list; no product has both capabilities, and the plan correctly uses separate devices. Plan 01-04 Task 3 then requires all 31 checkboxes to map to named tests (01-04-PLAN.md:420, :442, :553), which cannot be truthful while AC 23 reads this way. **Fix:** amend AC 23 so one multizone Thread device covers `StateColor`, both acks, `StateUnhandled` and the `StateMultiZone` list, and a separate sentence covers `State64` on a large matrix device (two requests) and a chained matrix device (`length=2`). Record the amendment in the 01-04 ledger.
4. **[MEDIUM — confirmed] the "no product other than 55 is rejected" prohibition is tested over matrix products only** (Codex MEDIUM; orchestrator verified at 01-02-PLAN.md:271, `if i.has_matrix`). The SPEC prohibition (01-SPEC.md:136) is registry-wide. **Fix:** iterate every entry in `PRODUCTS`, attempt `create_device(pid, connectivity="thread")`, and assert the rejected set is exactly `{55}`; keep the matrix-only assertion as a diagnostic if useful.
5. **[MEDIUM — plausible, not independently reproduced] persistence round-trip reuses a shut-down storage backend** (Codex MEDIUM). 01-04-PLAN.md:196-197 calls `await temp_storage.shutdown()` and then `create_device(..., storage=temp_storage)`. `shutdown()` cancels the flush task and shuts the executor; device construction schedules a save when storage is present (`device.py:151`), so the reload can queue a write onto a closed executor. **Fix:** after the shutdown-flush, construct a fresh `DevicePersistenceAsyncFile(storage_dir=temp_storage.storage_dir)` for the reload and shut that down at test end.
6. **[MEDIUM — confirmed] `factories/builder.py` has no `logger`** (Antigravity LOW, upgraded by the orchestrator because it is a guaranteed `NameError`). 01-04 Task 1 has `_resolve_connectivity()` emit `logger.warning(...)`, but `builder.py` neither imports `logging` nor defines `logger`. **Fix:** the task action must add `import logging` and `logger = logging.getLogger(__name__)` at the top of `builder.py`, per the module `logger` convention.
7. **[LOW — mechanism confirmed] the single-construction-site grep matches `__pycache__` binaries** (OpenCode LOW, Antigravity LOW). `grep -rn "LifxHeader(" …` reports "Binary file … header.cpython-314.pyc matches", which neither `grep -v` filter removes. **Fix:** add `-I` or `--include="*.py"` to the 01-01 Task 2 criterion and `<verification>` step 6.
8. **[LOW] cross-plan wording drift** (OpenCode, Antigravity): the 01-01 comment on `_resolve_connectivity(self, serial)` promising "no signature change" is falsified by 01-04 adding `restorer`; 01-03 claims all seven typed factories have one-line docstrings when `create_multizone_light`, `create_tile_device` and `create_switch` already carry `Args:` blocks (`factory.py:79-88`, `:111-121`, `:164-178`); 01-03's byte-exact `grep -F -c "connectivity: Connectivity | str | None = None" … is 8` is fragile under Ruff line-wrapping; the 30-vs-31 criteria count is corrected in SPEC and 01-04 but CONTEXT/RESEARCH still say 30 (informational). **Fix:** reword the comment, correct the docstring claim to "four one-liners, three existing `Args:` blocks to extend", and loosen the signature grep.

### Divergent Views

- **Connectivity immutability vs the `state.network` escape hatch.** Codex (HIGH) reads the SPEC's "immutable after construction" strictly and objects that 01-01-PLAN.md:226 *tests* that `dataclasses.replace(device.state.network, …)` followed by `device.state.network = …` succeeds. OpenCode and Antigravity treat that as the intended D-07 mechanism (build-time replacement of a frozen sub-state) and count it a strength. The orchestrator's reading: D-07 is a locked decision that the escape hatch exists for the builder; the SPEC only requires `state.connectivity = …` to raise, which the plan satisfies. The residual issue is that 01-01 asserts the escape hatch as a *public* behaviour guarantee, which over-promises. **Recommendation:** keep the mechanism, drop the acceptance criterion that pins wholesale `state.network` replacement as supported public API (or move it to a comment naming it builder-internal), and let the SPEC's immutability wording stand.
- **`max-args` policy.** Codex (MEDIUM) says documenting that Ruff does not enforce `PLR0913` does not waive the CLAUDE.md rule and wants a formal, scoped exception or a keyword-options object. OpenCode and Antigravity accept the SUMMARY note as sufficient given the `advertised_services` precedent. A keyword-options object is a public-API redesign outside this phase; the practical resolution is a one-line scoped exception recorded in CLAUDE.md or the SUMMARY for the eight factory entry points, decided by the developer rather than the executor.
- **Bandit in the dev group.** Codex (MEDIUM) calls the `uv add --group dev bandit` step scope expansion while CI keeps its ad-hoc install; OpenCode and Antigravity call it the right CI-parity fix. CLAUDE.md requires `uv add` for dependencies, which favours the plan; the loose end Codex identifies is real, so the plan should also note that `ci.yml:66-68` can drop its explicit install once the lock carries Bandit, as a follow-up.
- **`affects_acks` predicate.** OpenCode (MEDIUM, sole raiser, self-described as not verified this session) wants 01-04 Task 2 to state what `ScenarioConfig.affects_acks` keys on so the scenario-path ack is provably exercised. Round 1 OpenCode verified `scenarios/models.py:58-66` includes `response_delays` membership of type 45, so the mechanism is sound; adding `assert scenario.affects_acks` to the test setup is cheap insurance.
- **Single-reviewer LOW items worth carrying:** malformed `max_firmware_*` YAML values reach tuple comparison unvalidated (Codex; validate as `int` at load or soften the threat-model claim); typed-factory tests should also assert the 4.200 default and an explicit valid Thread firmware for every successful entry point (Codex); `"THREAD"` named in criteria but not parametrised (Codex); the intermediate Wave 2–3 window where a WiFi Tile reports host 3.50 with per-tile 3.70 should be named in the 01-02 SUMMARY (OpenCode); `grep -rc "type: ignore"` should be `grep -rn … | wc -l` (OpenCode); the `(?=.*200)(?=.*50)` regex should assert on `str(exc.value)` instead (Antigravity); `create_multizone_light`'s `extended_multizone: bool = True` cannot express "omitted or `None`" in the eight-way parametrisation (OpenCode); the 01-04 Task 2 `git show HEAD` gate is post-commit by design but should say so (Antigravity).

### Recommended disposition

Concerns 1, 3, 4 and 6 are plan or SPEC text defects that would produce a failing or dishonest phase and should be fixed before execution. Concern 2 is a real pre-existing server bug the review surfaced; it needs an explicit in-phase-or-follow-up decision, not silence. Concern 5 is a cheap test-hygiene fix. The divergent items are policy calls for the developer (escape-hatch wording, `max-args` exception, Bandit follow-up). After those, all three reviewers converge on **LOW** implementation risk.
