---
phase: 03-mdns-responder
plan: 01
subsystem: testing
tags: [mdns, dns-sd, zeroconf, lifx-async, pyapp, github-actions]
requires:
  - phase: 02-ipv6-transport-and-thread-isolation
    provides: Same-port IPv4 and IPv6 emulator transport
provides:
  - Reproducible candidate harness with immutable provenance and evidence validation
  - Rejected zeroconf result for the one-complete-datagram-per-device contract
  - Provisional lifx-direct result with exact acquisition steps for hosted macOS multicast and dynamic recovery
  - Non-publishing Ubuntu, macOS and Intel PyApp CI evidence
affects: [03-mdns-responder, MDNS-01, MDNS-02, MDNS-03, MDNS-04, MDNS-05, MDNS-06, MDNS-07, MDNS-08, MDNS-09, MDNS-11]
actuals:
  tokens: 100433
  tasks: 2
  commits: 24
plan_head_before: 8f31243d7760d61063989b24a146509304208317
tech-stack:
  added: []
  patterns: [immutable candidate inputs, exact-head CI receipts, machine-validated evidence ledger]
key-files:
  created:
    - scripts/spike_mdns_candidates.py
    - scripts/mdns_spike_inputs/active.json
    - scripts/mdns_spike_inputs/lifx_direct.py
    - scripts/mdns_spike_tests/test_candidates.py
    - .planning/phases/03-mdns-responder/03-01-EVIDENCE.json
    - .planning/phases/03-mdns-responder/03-01-EVIDENCE.md
  modified:
    - .github/workflows/ci.yml
key-decisions:
  - "Reject zeroconf 0.151.3 because its mixed fleet response aggregates devices instead of emitting one complete datagram per device."
  - "Keep lifx-direct provisional because hosted macOS multicast and dynamic listener failure/retry/partial-fleet recovery remain unproved."
  - "Keep MDNS-01–09 and MDNS-11 pending until the blocking human decision is recorded."
patterns-established:
  - "Candidate evidence binds source, base, overlay, final tree and input specification digests to one exact PR head."
  - "Environment acquisition failures remain provisional and preserve their exact failing stage and repeat step."
requirements-completed: []
coverage:
  - id: D1
    description: Reproducible mDNS candidate harness and evidence validator
    requirement: MDNS-10
    verification:
      - kind: integration
        ref: "uv run --frozen pytest scripts/mdns_spike_tests/test_candidates.py -q --no-cov"
        status: pass
      - kind: integration
        ref: "uv run --frozen python scripts/spike_mdns_candidates.py validate-evidence .planning/phases/03-mdns-responder/03-01-EVIDENCE.json"
        status: pass
    human_judgment: false
  - id: D2
    description: Evidence-backed responder foundation decision
    requirement: MDNS-10
    verification:
      - kind: manual_procedural
        ref: "Task 3 blocking-human decision checkpoint"
        status: unknown
    human_judgment: true
    rationale: "The plan explicitly requires a human to select the evidence-valid route; current evidence permits only a provisional hold."
duration: 3h 33m
completed: 2026-09-23
status: halted
---

# Phase 3 Plan 01: mDNS Foundation Spike Summary

**The corrected bounded spike rejects zeroconf packet aggregation and leaves the direct lifx-async responder provisional because hosted macOS multicast and dynamic recovery remain unproved.**

## Performance

- **Duration:** 3h 33m active work; no CI queue time excluded
- **Started:** 2026-09-22T15:01:53Z
- **Ledger closed:** 2026-09-22T18:34:56Z
- **Tasks:** 2 of 3 complete
- **Files modified:** 9 task artefacts, plus planning state and this summary

## Accomplishments

- Resolved zeroconf 0.151.3 from official metadata and proved one legacy-unicast path, then rejected it when a 5+5 fleet produced two aggregate datagrams rather than one complete datagram per device.
- Built a frozen direct lifx-async overlay at oracle revision `48b7efbff59656499373b13ef17e3008d125feb5`; local macOS and exact-head Ubuntu evidence demonstrate raw packet, public-oracle discovery, family, fleet, malformed-input, flood, socket-choice and cleanup gates.
- Public `discover_mdns()` benchmarks found the exact stock WiFi/Thread populations at 1, 1, 5+5 and 50+50, with separate representative `get_power()` control checks and aggregate CPU/RSS measurements. Raw parser timings remain labelled raw-wire rather than discovery timings.
- The v2 candidate input digest is `dedb9b03390bd0230e8cb503dc2f9a829db1aa12dc523b7ba1125d627d9ed75e`; the prior v1 candidate and receipts remain in revision history as superseded diagnostic evidence.
- Bound Ubuntu, hosted macOS and Intel PyApp receipts to exact security-fixed candidate input head `0669c07`; Ubuntu and Intel meet their gates while hosted macOS retains its scoped reply-source bind failure.
- Replaced all wildcard UDP 5353 listeners with a group-address receiver, explicit selected-interface membership and an RFC-compliant selected-interface UDP 5353 reply sender. Linux additionally disables `IP_MULTICAST_ALL`; Darwin uses `IP_BOUND_IF`.
- Retained hosted macOS `EADDRINUSE` at RFC-compliant reply-source creation as a precise provisional environment result while local Darwin and exact-head Ubuntu pass the scoped listener and full candidate probes.

## Task Commits

1. **Task 1 RED:** `3df658b` — failing legacy-unicast tracer contract.
2. **Task 1 GREEN:** `3016313` — zeroconf provenance, harness, tracer and PR-only evidence job.
3. **Task 2 RED:** `6c25a8f` — eligible fallback overlay contract.
4. **Task 2 implementation:** `57a13c1`, `5dffa1d`, `cd4e0a0`, `0fe5802`, `894f2dc`, `58fdb2c`, `c9450db`, `7f3ab9b`, `c80471d` — direct responder evaluation, exact receipts, platform diagnostics and behavioural fit coverage.
5. **Task 2 evidence:** `a917f91` — reconciled exact-head platform and packaging ledger.
6. **Corrective RED:** `bb2be73` — validator failures for unsupported public benchmark, Windows, adversarial and recovery claims.
7. **Corrective implementation:** `d0ac100`, `ab5f0d2`, `914e51b` — v2 measurements, revision preservation and portable focused fixtures.
8. **Corrective evidence:** `d9055d2`, `6b4aa09` — reconciled exact v2 platform, packaging and security-fixed receipts.
9. **Security RED:** `48551f8` — live regression rejecting wildcard responder listeners.
10. **Security fix:** `12b4e33`, `0669c07` — interface-scoped receive/reply sockets, UDP 5353 source assertion and hosted coexistence classification.

Task 3 is intentionally uncommitted and awaits the blocking human decision.

## Files Created/Modified

- `scripts/spike_mdns_candidates.py` — stdlib candidate runner, provenance resolver, platform probes, receipt checks and evidence validator.
- `scripts/mdns_spike_tests/test_candidates.py` — explicit-path TDD, receipt, lifecycle and hermetic materialiser-fit coverage.
- `scripts/mdns_spike_inputs/active.json` — immutable active direct candidate specification.
- `scripts/mdns_spike_inputs/lifx_direct.py` — frozen direct responder overlay evaluated by the spike.
- `.github/workflows/ci.yml` — non-publishing Ubuntu, hosted macOS and Intel PyApp evidence jobs with exact synchronize-input guards.
- `.planning/phases/03-mdns-responder/03-01-EVIDENCE.json` — authoritative machine-readable ledger.
- `.planning/phases/03-mdns-responder/03-01-EVIDENCE.md` — rendered human-readable evidence.

## Decisions Made

- Zeroconf is rejected at the first decisive mixed-fleet packet-boundary failure. The already-run 100-device diagnostic remains labelled non-decision-supporting.
- The direct candidate remains the furthest viable candidate. Adapted and new-responder candidates were not eligible after a provisional direct result.
- Go, no-go and extension are unavailable from this ledger. The evidence supports a provisional hold pending hosted macOS multicast and injected dynamic recovery proof.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bound CI receipts to the active direct candidate**
- **Found during:** Task 2
- **Issue:** Early receipts could appear green without proving candidate, head, input, base, overlay and final identities.
- **Fix:** Added strict receipt validation and regression coverage for every identity mismatch.
- **Files modified:** `scripts/spike_mdns_candidates.py`, `scripts/mdns_spike_tests/test_candidates.py`, `.github/workflows/ci.yml`
- **Verification:** The final Ubuntu, macOS and Intel receipts validate against exact head `0669c07`.

**2. [Rule 3 - Blocking] Acquired bounded platform prerequisites and retained failures**
- **Found during:** Task 2
- **Issue:** Hosted Ubuntu lacked an mDNS daemon and selector-compatible ULA; hosted macOS failed before useful stage isolation; PyApp initially used an invalid wheel name/reference shape.
- **Fix:** Started Avahi and configured a synthetic runner ULA on Ubuntu, isolated each macOS stage and attempted a destination-specific multicast route, and built PyApp from exact local wheels with supported names and references.
- **Files modified:** `.github/workflows/ci.yml`, `scripts/spike_mdns_candidates.py`, `scripts/mdns_spike_tests/test_candidates.py`
- **Verification:** Ubuntu and Intel gates pass; the remaining hosted macOS failure is precisely recorded as provisional rather than masked.

**3. [Rule 1 - Bug] Replaced a source-shape fit assertion with behavioural coverage**
- **Found during:** Task 2
- **Issue:** A focused test asserted harness strings and depended on unreconciled evidence instead of executing candidate-fit behaviour.
- **Fix:** Added a hermetic materialiser command that loads the frozen overlay in a temporary environment and checks eligibility, shared addresses, stable replies, removal/re-add, equivalent IPv6 and invalid-address rejection.
- **Files modified:** `scripts/spike_mdns_candidates.py`, `scripts/mdns_spike_tests/test_candidates.py`
- **Verification:** 30 focused tests pass from the local checkout and a clean exported exact-input tree; final exact-head CI is green.

**4. [Ordering deviation] Retained a diagnostic executed before rejection was isolated**
- **Found during:** Task 1 expansion
- **Issue:** The 100-device zeroconf diagnostic ran before the mixed-10 packet-boundary failure was isolated.
- **Fix:** Retained the actual result, marked it diagnostic and non-decision-supporting, and stopped further zeroconf work after decisive rejection.
- **Files modified:** `.planning/phases/03-mdns-responder/03-01-EVIDENCE.json`

**5. [Rule 1 - Bug] Corrected unsupported evidence claims**
- **Found during:** Parent checkpoint spot-check after Task 2
- **Issue:** Raw capture timings were labelled complete discovery, Windows was marked simulated without execution, malformed/flood coverage was incomplete, and independent cleanup cycles were treated as dynamic recovery.
- **Fix:** Added distinct pristine public-oracle benchmarks and representative controls, executed Windows socket-plan simulation and bounded malformed/oversized/compression/high-rate/101-device cases, and returned dynamic recovery to `untested` with an exact acquisition step. Mutable-ledger focused tests were replaced with portable fixtures.
- **Files modified:** `scripts/spike_mdns_candidates.py`, `scripts/mdns_spike_inputs/lifx_direct.py`, `scripts/mdns_spike_tests/test_candidates.py`, evidence artefacts
- **Verification:** Corrective RED recorded four unsupported-claim failures; the v2 focused suite passes 30 tests from a clean exported commit tree.

**6. [Rule 1 - Security] Removed wildcard UDP 5353 listener exposure**
- **Found during:** GHAS review after the corrected Task 2 checkpoint
- **Issue:** Three harness listeners bound UDP 5353 to every local address.
- **Fix:** Centralised group-address/interface-scoped receive sockets, selected-interface UDP 5353 reply sockets, Linux `IP_MULTICAST_ALL=0` and Darwin `IP_BOUND_IF`; added a live bind-scope regression and raw source-port assertions.
- **Files modified:** `scripts/spike_mdns_candidates.py`, `scripts/mdns_spike_tests/test_candidates.py`
- **Verification:** Full local candidate proof and exact-head Ubuntu pass; CodeQL alerts 16/17 are fixed and no open alert remains for `refs/pull/224/head`.

**Total deviations:** 6 handled inline. They improved evidence correctness and did not add production scope.

## Verification

- Focused suite: 31 passed on local macOS and 31 passed from a fresh `git archive` of exact input head `0669c07`.
- Final exact-input CI run: [35767055166](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35767055166) at candidate head `0669c07`.
- Exact receipts: Ubuntu and Intel PyApp meet their gates; hosted macOS is valid provisional evidence at selected-interface UDP 5353 reply-source creation.
- Final-head Python CodeQL passes; alerts 16 and 17 report `fixed`, and the PR-head open-alert query is empty.
- Production source, `pyproject.toml` and `uv.lock` have no diff from the plan base.
- Sibling `lifx-async` remains at the pinned oracle revision; its pre-existing untracked `morph.py` is untouched.
- Draft PR: [#224](https://github.com/Djelibeybi/lifx-emulator/pull/224).

## TDD Gate Compliance

- Task 1 RED is recorded in `.planning/phases/03-mdns-responder/03-01-TDD-RED.json` and commit `3df658b`.
- Task 2 RED is recorded in `.planning/phases/03-mdns-responder/03-01-TDD-TASK2-RED.json` and commit `6c25a8f`.
- Corrective RED is recorded in `.planning/phases/03-mdns-responder/03-01-TDD-CORRECTION-RED.json` and commit `bb2be73`.
- Security RED is recorded in `.planning/phases/03-mdns-responder/03-01-TDD-GHAS-RED.json` and commit `48551f8`.
- GREEN and subsequent fixes preserve separately committed RED evidence.

## Deferred Evidence

Exact-head hosted macOS multicast remains untested because mDNSResponder prevented the RFC-required selected-interface UDP 5353 reply-source bind (`EADDRINUSE`) beside the group/interface-scoped listener. Repeat the exact candidate head and input digest on a disposable macOS executor whose daemon permits that scoped UDP 5353 coexistence. Local macOS proof is retained separately and does not replace that platform receipt.

Dynamic listener failure, retry, partial-fleet recovery and production status integration remain untested. Independent clean shutdown cycles prove resource cleanup only. Acquire this evidence with injected responder failure and recovery after the human selects a production foundation.

MDNS-01–09 and MDNS-11 remain pending. No production responder or dependency was added.

## User Setup Required

None.

## Next Phase Readiness

Task 3 must record the blocking human choice. The validated ledger supports only **provisional hold** until hosted macOS multicast and dynamic recovery evidence are acquired; detailed Phase 3 planning remains paused.

## Authorised constrained follow-up

The user subsequently authorised up to 60 additional minutes with no local or CI harness work. [03-01-EXTENSION.md](03-01-EXTENSION.md) records the source investigation and unsuccessful direct socket experiment. The follow-up stopped early without changing implementation or harness files. The result remains provisional; the existing evidence ledger and its historical budget are unchanged. The earlier statement that extension was unavailable describes the original checkpoint, before this explicit user authorisation.

## Self-Check: PASSED

- All created task artefacts exist.
- All 24 task and evidence commits before this checkpoint-summary update exist on `codex/phase-03-mdns-responder`.
- The evidence validator passes with `decision=provisional`.
- The working tree contains only the intended execution-state and checkpoint-summary edits before the final checkpoint commit.

---
*Phase: 03-mdns-responder*
*Checkpoint recorded: 2026-09-23*
