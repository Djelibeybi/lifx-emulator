---
phase: 03
reviewers: [claude, opencode, antigravity]
completed_reviewers: [claude, opencode, antigravity]
blocked_reviewers: []
status: review_complete_requires_revision
reviewed_at: "2026-09-22T14:23:33.845Z"
plans_reviewed: [03-01-PLAN.md]
reviewed_commit: "7d69642"
plan_sha256: "925d986708dd7b70a9bef6a91f8ff122c5830d954304bf00b2d77c601f96778c"
models:
  claude: "claude-opus-5 (reasoning=high)"
  opencode: "openrouter/z-ai/glm-5.3 (reasoning=high)"
  antigravity: "gemini-3.8-flash-high"
model_sources:
  claude: "pinned"
  opencode: "pinned"
  antigravity: "pinned"
---

> **2026-09-23 amendment:** The user approved complete-fleet discovery independent of packet grouping. See [03-PACKET-GROUPING-AMENDMENT.md](03-PACKET-GROUPING-AMENDMENT.md). Earlier packet-count requirements and zeroconf rejection on aggregation alone are superseded. Historical observations and reviews below remain unchanged; they do not establish compliance with the revised contract. Do not resume the old execution steps or change the local/CI harness under this amendment.


# Cross-AI Plan Review — Phase 3

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

All three configured reviewers returned substantive reviews covering 03-01 against the unchanged plan hash above. OpenCode completed after explicit user approval and a process-scoped permission for the referenced sibling source. No plan or implementation was changed by this review.

## Review quality and interpretation

- Claude supplied source-grounded findings. The orchestrator independently read the oracle address selector and CI triggers, confirming the mechanisms below.
- Antigravity supplied some useful source citations, but its plan/context/research line references use impossible offsets (for example plan line 1077 in a 270-line file). Those are not valid repository citations. Weight only independently grounded concerns; retain the raw review unchanged below.
- Antigravity's and OpenCode's claims that uv's isolated flag ignores project configuration are contradicted by the [official uv CLI reference](https://docs.astral.sh/uv/reference/cli/#uv-run--isolated): it uses a fresh project environment and still installs the project. The claimed conflict with frozen is not established. Exact workspace import availability remains an execution-preflight question, not a proven flag defect.
- Claude and OpenCode infer that the pinned oracle commit is unavailable remotely from local remote-tracking refs. A fresh GitHub API request to `repos/Djelibeybi/lifx-async/commits/48b7efbff59656499373b13ef17e3008d125feb5` returned that exact SHA during this review. Their claimed unpushed/unresolvable-pin blocker is not accepted; no push or re-pin is warranted on this evidence. Exact Git/uv acquisition remains a preflight check rather than a proven failure.
- OpenCode completed the required 03-01 section and supplied useful source citations. Its Ruff complexity claim is not supported: pyproject.toml:35 selects E/F/I/N/W/UP, not C90 or PLR. The configured mccabe/pylint thresholds at lines 39–45 do not themselves enable those rules.
- The installed `uv run --help` describes isolated as a fresh virtual environment and separately describes no-project as disabling project/workspace discovery; it does not support OpenCode's attributed wording that isolated omits the project.

## Consensus Summary

**Recommendation: revise the spike plan before execution.** The locked MDNS-10 boundary and honest negative/provisional outcomes are sound. The main risk is spending the timebox building evidence tooling while the protocol/oracle/CI paths remain under-specified.

### Agreed Strengths

- All three reviewers recognise the MDNS-10-only scope, pending production requirements, candidate ordering, pristine oracle intent, and separation of candidate rejection from harness errors.
- All three recognise the four-hour stop and evidence-gated decision; no platform result should be fabricated.

### Agreed Concerns

1. **HIGH — Reduce scaffolding and redundant fallback work within the existing budget.** All three reviewers flag the provenance runner, validator, snapshot tooling, multiple fallback prototypes, benchmarks and CI/PyApp setup as likely to consume the four active hours. This is a feasibility risk, not a measured duration. Plan source: .planning/phases/03-mdns-responder/03-01-PLAN.md:166. Preserve D-14/D-15; prioritise the cheapest decisive packet checks and bound reuse investigation before authoring substantial prototypes.
2. **HIGH — Specify default-suite isolation for spike tests.** All three reviewers flag new candidate-dependent tests under the default collection roots. Source: pyproject.toml:59 and .github/workflows/ci.yml:101. The future tests do not exist yet, so universal import failure is conditional; the actionable gap is the absence of an explicit collection/import boundary. Keep candidate imports and network experiments out of ordinary CI collection unless their environment is deliberately enabled.

### Additional source-grounded concerns

3. **HIGH — Prevent an oracle/environment defect becoming candidate rejection.** The pinned sibling selector ranks IPv4, ULA, GUA and scoped link-local, but not IPv6 loopback (../lifx-async/src/lifx/network/discovery/mdns/discovery.py:215). The default server bind is ::1 (packages/lifx-emulator-core/src/lifx_emulator/server.py:167). The plan must distinguish raw AAAA loopback fidelity from an oracle-compatible reachable address setup; do not weaken the locked loopback requirement or reject a responder because the client cannot select its advertised address.
4. **HIGH — Give CI evidence an executable trigger path.** Current CI triggers are main pushes and pull requests (.github/workflows/ci.yml:3). Adding a job alone does not run it from a phase branch. Specify a non-publishing triggering mechanism and acquisition commands; account for default-branch availability if considering workflow_dispatch. Ensure change filters cannot skip required evidence (.github/workflows/ci.yml:28).
5. **MEDIUM — Make candidate packaging and evidence reproducible without production edits.** Specify the temporary package/worktree used for candidate wheel metadata, the PyApp build and first-run inputs, and transfer of prototype overlays to CI. The existing release job uses a registry project/version (.github/workflows/release-binaries.yml:76); it is not candidate proof. A machine-readable evidence ledger could avoid a complex markdown parser.

### Divergent Views and suggestions not adopted

- Do not adopt Claude's suggestion to replace required PyApp build/first-run evidence with a plain package import; D-12/MDNS-10 require packaging proof. An import may be a preliminary discriminator only.
- Do not move harness construction or environment preparation outside the four-active-hour budget without changing the user's decision. Simplify inside the cap instead.
- Do not treat absence of a responder in lifx-async as automatic decisive rejection. D-11 deliberately asks whether extending or adapting it is worthwhile; compare the delta against the requirements.
- Antigravity's and OpenCode's uv flag claims are not accepted, as explained above. Specifying which environment contains each candidate, the emulator and the pristine oracle remains useful.
- OpenCode's proposed push/re-pin and Ruff per-file exemptions are not adopted: the commit resolves on GitHub and the cited lint rule families are not enabled.
- OpenCode correctly locates public `discover_mdns()` in ../lifx-async/src/lifx/api.py:1266. Adding that explicit reference would improve clarity; the plan currently names it without asserting a defining module (03-01-PLAN.md:95).
- OpenCode suggests excluding the evidence ledger from published documentation and labelling the candidate-wheel proof precisely. These are optional presentation/provenance clarifications, not demonstrated blockers; preserve the required PyApp build and first-run evidence.
- The plan already says run-sequence consumes Task 1's result (.planning/phases/03-mdns-responder/03-01-PLAN.md:159). Claude's duplicate-probe concern is a request for clearer resume behaviour, not evidence that repetition is mandatory.
- Antigravity rates the plan more favourably overall than Claude; its unsupported plan offsets reduce confidence in plan-specific assertions. No review supersedes the locked requirements.

## OpenCode retry status

Configured destination/model: OpenRouter via OpenCode, openrouter/z-ai/glm-5.3. The prompt included project context, Phase 3 roadmap/requirements/context/research/specification and 03-01 plan, with referenced source access. The first attempt failed opening the local log; automatic approval review initially rejected broader runtime access. The user then explicitly approved that destination, payload and local runtime access.

The first approved retry returned only an opening sentence because OpenCode auto-rejected its external-directory request for the sibling lifx-async source. It was not counted as a review despite the launcher's ok:true result. A subsequent retry used a process-only external_directory permission restricted to /Volumes/External/Developer/Djelibeybi/lifx-async/** and edit:deny. It returned a full review, an exact 03-01 heading, source citations and no stderr. No persistent OpenCode configuration was changed. The combined prompt was passed through stdin; it was not opened as an external file.

## Raw reviewer responses

The following responses retain the reviewers' text, with trailing whitespace normalised by repository hooks. Byte-for-byte originals remain in the ignored .review-diagnostics directory. Their recommendations are feedback, not adopted plan decisions; the synthesis above identifies qualifications and conflicts.

## Claude Review

# Cross-AI Plan Review — Phase 3, MDNS-10 Spike

Review scope: `.planning/phases/03-mdns-responder/03-01-PLAN.md` only. Read-only; nothing in the repository or the sibling checkout was modified. All claims below were traced to source rather than taken from the plan's assertions.

---

## 03-01

### Summary

The plan is conceptually sound and unusually disciplined about the thing spikes most often get wrong: it separates "the harness ran" from "the candidate passed", forbids production integration, and refuses to let a `provisional` outcome unlock MDNS-01–09/11. The decisive discriminator identified by research — one complete datagram per device versus python-zeroconf's aggregating answer builder — is correctly made a packet-level gate rather than an oracle-level one.

What it does not survive is contact with the actual code. Two of the three evidence channels it depends on are blocked by mechanisms that have nothing to do with the candidate: `lifx-async`'s address selector cannot select an IPv6 loopback address, so Thread-over-`::1` discovery can never succeed through the oracle; and the CI workflow's triggers mean the `mdns-spike-evidence` job never runs on a phase branch, so the packaging gate — and therefore `go` — is unreachable by construction. A third problem is budgetary: the plan starts the D-14 four-hour clock before building a harness whose specification (provenance/tag/commit resolution with digests, per-candidate isolated environments, a markdown evidence validator with a status state machine, disposable git-snapshot candidate builds, CPU/RSS benchmarking at three fleet sizes, two test modules, a CI job) plausibly consumes the entire box on its own.

Net: as written, the most likely outcome is an expensive `provisional` with no candidate evidence in it. The fix is a re-cut, not a rewrite — the gate design is good, the scaffolding around it is not.

### Strengths

1. **Requirement boundary is held honestly.** `requirements: [MDNS-10]` plus the `<deferred_coverage_ledger>` listing MDNS-01–09/11 as "Pending" with their AC mappings, and the coverage audit marking them `PENDING by D-12 dependency gate` rather than covered. This matches `.planning/phases/03-mdns-responder/03-SPEC.md:18` and D-12 at `03-CONTEXT.md:62`. No responder design is smuggled in under spike cover.
2. **Outcome typing is the right primitive.** `<interfaces>` and Task 1 distinguish `candidate_status` (`meets_gate`/`rejected`/`provisional`) from `execution_status` (`completed`/`tool_error`), and make a validated rejection an exit-zero success. This is precisely the conflation that causes spikes to record "we could not get it working" as "the library does not work".
3. **The hard gate targets the real risk.** `03-RESEARCH.md:42` cites zeroconf's `_handlers/answers.py` collecting records across services into one outgoing answer, against locked AC-04 (`03-SPEC.md:129`) requiring one complete per-device packet. Task 1's behaviour block asserts "one self-contained PTR/SRV/TXT/A device record set" on the captured datagram, and `<action>` explicitly forbids inferring it from client success — correct, because `_LifxRecordCache` is an accumulator (`../lifx-async/src/lifx/network/discovery/mdns/discovery.py:281-289`, merge entry at `:707`) and would happily resolve a fleet from aggregated packets.
4. **Real consumer as oracle, kept pristine.** Task 2 requires the oracle to run "from the pristine pinned install, outside both candidate import roots", which prevents the adapted-code candidate from being validated by a client sharing its modified source — a genuine self-confirmation trap given D-11 adapts sibling modules.
5. **Sibling-repo safety is explicit and warranted.** `git clone --no-local` + `git archive` into disposable temp roots with "Never write to the sibling checkout or its Git metadata". The sibling is the acceptance oracle, is currently on a feature branch with an untracked file in its tree, and must not be disturbed.
6. **Production integration is structurally blocked.** `<verification>` requires `git diff -- pyproject.toml uv.lock packages/lifx-emulator-core/src packages/lifx-emulator/src` to be empty. That is the invariant D-12 exists to protect, asserted mechanically rather than by instruction.
7. **The human gate is correctly shaped.** Task 3 runs the validator *before* presenting options, withholds `go` when any required gate is untested, and makes the extension a single non-automatic route conditioned on D-15 evidence — faithful to AC-12 (`03-SPEC.md:137`) and to D-15/D-16 (`03-CONTEXT.md:68-69`).
8. **Threat model is proportionate and doubles as protocol evidence.** T-03-01/03 (destination, echoed ID, record ownership, cache-flush, TTL; TXT containing exactly `id/p/fw/tm`) are the same assertions MDNS-02 and MDNS-04 need, so the security work is not a separate tax.

### Concerns

#### HIGH-1 — Thread-over-loopback evidence is unobtainable through the oracle; failures would be misattributed to the candidate

`_pick_address` (`../lifx-async/src/lifx/network/discovery/mdns/discovery.py:215-243`) assigns a priority only to IPv4 (`0`), ULA `fc00::/7` (`1`), GUA `2000::/3` (`2`) and *scoped* link-local (`3`). `::1` passes `_is_usable_mdns_address` (`:201-212`) but matches none of those classes, so `priority` stays `None`, the address is never appended, and the function returns `None` from an empty candidate list. `_LifxRecordCache.resolve` then hits `if ip is None: continue` (`:820-827`) and `pending_targets` (`:846-886`) keeps re-querying the same target forever, so the instance is never yielded by `discover_devices_mdns` (`:1602`) — which is exactly what `discover_mdns` delegates to (`../lifx-async/src/lifx/api.py:1266,1322`).

WiFi is unaffected: `A=127.0.0.1` is priority `0`, and `validate_address` explicitly accepts loopback (`../lifx-async/src/lifx/network/address.py`, rule 7 in the module docstring).

The emulator's IPv6 default bind is `::1` (`packages/lifx-emulator-core/src/lifx_emulator/server.py:167`), and `03-SPEC.md:63` makes the concrete bind the advertised fallback — so the default configuration lands squarely on this. Every Task 2 gate involving Thread devices and the oracle (AAAA-only fidelity, per-device boundaries proven end-to-end, the size-1 Thread case, the 5+5 and 50+50 mixed fleets) would fail for a reason wholly external to the candidate, and the plan's outcome machine would record it as candidate `rejected` — the worst possible error, because it would advance D-09 to the fallback candidates on a false negative.

**Fix:** advertise a ULA (`fd00::/8`) for Thread test devices — either bind the emulator's IPv6 socket to a ULA added to a loopback/dummy interface, or set a per-device advertised ULA — and record the `::1`-is-unadvertisable finding in the ledger. It is itself useful MDNS-06 evidence that the spec's "loopback allowed for local tests" holds for A records but not for AAAA against this client.

#### HIGH-2 — The spike tests will break the normal CI matrix on all ten legs

`pyproject.toml:59` sets `testpaths = ["packages/lifx-emulator-core/tests", "packages/lifx-emulator/tests"]`, and `.github/workflows/ci.yml:101` runs `uv run --frozen pytest --cov-fail-under=80` across ubuntu/macOS × Python 3.10–3.14. The plan's two new modules land in `packages/lifx-emulator-core/tests/`, so they are collected by that job. They exercise the candidate, which the plan deliberately never adds to `pyproject.toml`/`uv.lock` — so under `uv sync --frozen` (`ci.yml:98`) the import fails at collection and every leg goes red. Binding UDP 5353 and joining a multicast group inside the standard unit-test job is also non-hermetic on shared runners.

**Fix:** relocate the spike tests outside `testpaths` (the harness can invoke them by path), or gate them with `importlib.util.find_spec("zeroconf") is None` skips plus a `spike` marker deselected by default, and say so in the plan.

#### HIGH-3 — The CI and packaging evidence cannot be produced by this plan, which makes `go` unreachable

`.github/workflows/ci.yml:3-7` triggers only on `push` to `main` and on `pull_request`. The spike executes on a phase branch; the plan neither opens a PR nor adds `workflow_dispatch`. The new `mdns-spike-evidence` job therefore never runs — no Ubuntu/macOS multicast leg, no Intel macOS (`macos-15-intel`, `.github/workflows/release-binaries.yml:30-33`) packaging evidence, no run URL, no artefact hashes. Under D-12 that forces `provisional` regardless of how well the candidate performs, so Task 3's `go` option is structurally unavailable.

Secondary: if the job copies the existing `needs: changes` / `if: needs.changes.outputs.source == 'true'` pattern (`ci.yml:36-38, 74-75`), the `changes` filter (`ci.yml:28-32`: `packages/**`, `pyproject.toml`, `uv.lock`) excludes `scripts/**` and `docs/**` entirely.

**Fix:** add `workflow_dispatch` to `ci.yml` and invoke it explicitly (`gh workflow run`), or plan a draft PR as part of Task 2; and do not gate the spike job behind the `changes` filter.

#### HIGH-4 — Scope exceeds the four-hour budget, and the budget is spent on tooling rather than evidence

Task 1's `<action>` starts the D-14 clock "before implementation". What follows must be built inside it: execution-time PyPI resolution plus official-tag-to-commit verification with archive digests; one uv-isolated environment per candidate with recorded environment digests; raw DNS capture and assertion; disposable clone/archive snapshots with base/overlay/final digests; a stdlib-only markdown evidence validator enforcing a status state machine, candidate ordering and a permitted-not-run-reason taxonomy; CPU/peak-RSS/datagram/thread-inventory benchmarking at 1, 10 and 100; two test modules; and a CI job — all Ruff-clean in `scripts/spike_mdns_candidates.py`. The plan's own `estimate.confidence: low` agrees.

Compounding this, D-09/D-11 are budgeted as three prototype paths, but `03-RESEARCH.md:44` already establishes that the sibling modules contain query construction, parsing and an ephemeral-port *client* transport — no responder encoder or listener. `lifx-direct` and `lifx-adapted` are therefore the same new-responder work in two locations, and candidate 3 largely duplicates both. The plan budgets three builds for what is one build and a placement decision.

**Fix:** either declare harness construction outside the D-14 evaluation budget (it is tooling, not candidate evaluation) or shrink it hard (see Suggestions 2 and 4). As written the plan buys the most expensive possible route to "we still do not know".

#### MEDIUM-1 — The pinned oracle is not installable by the declared mechanism

Frontmatter `key_links` requires `git+https://github.com/.+@[0-9a-f]{40}` for `lifx-async@48b7efbff59656499373b13ef17e3008d125feb5`. That commit is the sibling's current local `HEAD` on branch `feat/mirror-light`; it appears on no remote-tracking ref (`origin/main` is `d09c842`), and the remote is `git@github.com:Djelibeybi/lifx-async.git` (SSH, apparently private). A `git+https://…@48b7efb…` install will fail. Task 2's local `git clone --no-local ../lifx-async` path does work.

Provenance quality is also weaker than the plan claims: an unpublished feature-branch tip can be rebased away and garbage-collected, and the sibling worktree is currently dirty (`?? morph.py`).

**Fix:** install the oracle from the local clone at that SHA, drop the `git+https` link pattern, and record `git rev-parse HEAD` plus the tree hash as provenance.

#### MEDIUM-2 — Hermetic loopback probing and oracle-driven probing are different environments, and the plan treats them as one

`../lifx-async/src/lifx/network/discovery/mdns/transport.py:38-61` connects a probe socket to `224.0.0.251:5353` to ask the routing table for the concrete outbound IPv4 source, raises `OSError` if it is unspecified, then binds *that* address (`:148`) and sets `IP_MULTICAST_IF` to it (`:149-153`). Oracle-driven checks therefore always traverse the host's real LAN interface; a responder bound only to `127.0.0.1` will never see those queries. That is simultaneously the mDNSResponder-coexistence path and the least reliable path on hosted runners. PATTERNS.md:44-65 prescribes hermetic loopback injection; both tiers are needed, with different reliability expectations recorded separately in the ledger rather than blended into one "demonstrated".

#### MEDIUM-3 — The Intel macOS packaging step contradicts an invariant of this plan and is heavier than the question

Task 2 requires a "job-local candidate wheel", proof "its metadata contains the candidate", and `PYAPP_PROJECT_PATH`. A wheel whose `METADATA` lists zeroconf can only be produced from a modified project manifest, while `<verification>` requires the `pyproject.toml`/`uv.lock` diff to be empty. The temp-copy mechanism that reconciles these is never stated. Separately, `03-RESEARCH.md:144` notes no macOS x86_64 wheel for zeroconf 0.151.3, so PyApp's first run would fall back to an sdist build (compiler/Cython) inside its install step — slow and failure-prone, and unanticipated by the plan.

**Cheaper equivalent:** on `macos-15-intel`, `uv pip install zeroconf==<resolved>` against CPython 3.12 (`PYAPP_PYTHON_VERSION`, `.github/workflows/release-binaries.yml:9`) plus `python -c "import zeroconf; print(zeroconf.__version__)"`. That answers the actual question — can the candidate install and load on Intel macOS under the runtime PyApp ships — without a Rust build.

#### MEDIUM-4 — The gate is a validator, but the evidence format is prose

`docs/evidence/phase-03-mdns-spike.md` carries the ledger while `…-provenance.json` carries only provenance. `validate-evidence` must nonetheless reject "unsupported go", "invalid ordering", "missing metrics/artefacts without a permitted not-run reason" — by parsing markdown headings and tables. That validator is brittle to write and brittle to satisfy, inside a four-hour box.

**Fix:** make the ledger JSON (per-criterion status, timings, digests, decision) and render the markdown from it; the validator then checks data.

#### MEDIUM-5 — The zeroconf probe is specified to run twice

Task 1's verify runs `run-candidate --candidate zeroconf …`. Task 2's `run-sequence` "delegates to `run-candidate --candidate zeroconf|…`" and "continues zeroconf only while its validated status remains `meets_gate`". No caching or resume-from-recorded-outcome is specified, so the full probe — including `--isolated` environment construction — plausibly repeats against the clock. State that `run-sequence` reads Task 1's recorded outcome and resumes at the first unmet gate.

#### MEDIUM-6 — Task 1 is declared TDD but no gate runs a test

Task 1 carries `tdd="true"`, lists `test_mdns_spike_datagrams.py` in `<files>`, and asserts "The focused test starts red" and "zero collected tests or missing result evidence is a tool failure". Its `<verify><automated>` runs only `resolve-provenance` and `run-candidate`; pytest is never invoked. Per `execute-plan.md:227` the tracer gate re-runs exactly that `<verify>`, so the red→green claim is unverifiable and the test module is owned by no gate until Task 2.

#### LOW-1 — `docs/evidence/` conflicts with repo convention and publishes internal telemetry

Every prior phase artefact lives under `.planning/phases/<phase>/` (commit `4b553b5` adds `02-UAT.md`, `02-VERIFICATION.md`, `deferred-items.md` there); there is no `docs/evidence/` precedent. `docs/` is the published site (`mkdocs.yml:207` nav; `.github/workflows/docs.yml:1-20` triggers on `docs/**` and runs `zensical build --clean` + `llmstxt-standalone validate`, then deploys). The plan would add an unlisted page plus a raw `.json` asset to the public documentation build on every PR touching it. `.planning/phases/03-mdns-responder/03-01-EVIDENCE.{md,json}` matches convention and sidesteps the docs workflow.

#### LOW-2 — Quality tooling covers the harness asymmetrically

`ruff check .` and `ruff format --check .` (`ci.yml:58-61`) do lint `scripts/`, but Pyright's `include = ["packages/*/src"]` (`pyproject.toml:55`) excludes it and bandit runs only over the two `src/` trees (`ci.yml:69`). A "production-quality" harness in `scripts/` gets style enforcement without type checking. Also worth knowing before writing it: `select = ["E","F","I","N","W","UP"]` (`pyproject.toml:35`) includes neither `C90` nor `PL`, so the configured `max-complexity = 10` (`:40`) and `max-args = 5` (`:43`) are currently inert despite CLAUDE.md's claim that Ruff McCabe enforces complexity. Do not rely on Ruff to catch a sprawling harness.

#### LOW-3 — `uv run --isolated` semantics are worth confirming once, off the clock

`uv run --help` (uv 0.12.7) documents `--isolated` as "Run the command in an isolated virtual environment", i.e. a fresh environment per invocation. The root `pyproject.toml` has no `[project]` table (workspace-only root), so the harness's ability to `import lifx_emulator` under `--frozen --isolated` should be proven once before the clock starts, and repeated isolated environment builds counted against the budget.

### Open questions (not verifiable in this read-only review)

- `<interfaces>` asserts "PyApp 0.26.0 supports a local candidate wheel through `PYAPP_PROJECT_PATH`". I could not open the pinned PyApp documentation or source here; treat as unverified rather than established.
- The latest non-yanked zeroconf release and its wheel matrix at execution time are time-dependent; the "no macOS x86_64 wheel" observation comes from `03-RESEARCH.md:144`, not from a check performed in this review.

### Suggestions

1. **Preflight off the clock, then start it.** Before the four hours begin: confirm a ULA is available for Thread advertisement (HIGH-1); confirm the oracle installs from the local clone (MEDIUM-1); add `workflow_dispatch` to `ci.yml` and trigger the job so queue time overlaps the local work (HIGH-3); confirm `uv run --frozen --isolated` imports `lifx_emulator` (LOW-3). Then spend the budget on candidate evaluation only.
2. **Cut the harness to its load-bearing parts:** one `run-candidate` entry point, a JSON ledger, raw packet assertions, one oracle sweep. Replace the provenance/tag/commit/digest machinery with "record the resolved version and a `uv pip freeze` hash". Replace the markdown validator with a JSON schema check.
3. **Reorder the gates cheapest-decisive-first:** per-device packet boundary (pure datagram injection — no oracle, no LAN, no CI) → legacy-unicast destination/ID/cache-flush/TTL → TXT and address-family fidelity → daemon coexistence → oracle discovery → benchmarks → packaging. The MDNS-03 gate is the one most likely to rule zeroconf out and needs none of the fragile infrastructure; if it fails, three-quarters of this plan is never built.
4. **Collapse D-11 into one estimate.** Per `03-RESEARCH.md:44`, neither sibling form ships a responder encoder, so produce a single "minimum responder" estimate plus a location recommendation (extend the sibling versus adapt into the emulator) rather than two prototype builds.
5. **Move the ledger** to `.planning/phases/03-mdns-responder/03-01-EVIDENCE.{md,json}`.
6. **Downgrade the packaging gate** to `uv pip install zeroconf` + import on `macos-15-intel` under CPython 3.12; escalate to a full PyApp build only if that passes and time remains.
7. **Relocate or guard the spike tests** so the ten-leg matrix stays green (HIGH-2).
8. **Record `::1`-unadvertisable as a finding**, not a workaround — it is direct MDNS-06 input for the phase that follows.

### Risk Assessment

**Overall: HIGH.** Not because the plan is wrong about what to measure — the gate design is the strongest part of it — but because the path to measuring is blocked in two places and over-built in a third.

| Risk | Likelihood | Impact | Driver |
|---|---|---|---|
| Thread gates fail for oracle-internal reasons and are recorded as candidate rejection | High | Severe — a false negative advances D-09 to the wrong candidate | HIGH-1 |
| Four hours consumed by harness construction; zero candidate evidence | High | Severe — `provisional` at maximum cost, phase still blocked | HIGH-4, MEDIUM-4, MEDIUM-5 |
| `go` unreachable because CI/packaging evidence never materialises | High | High — Task 3 can only produce `provisional` | HIGH-3, MEDIUM-3 |
| Main CI matrix goes red on all ten legs | High | Moderate — noisy, but caught immediately and cheap to fix | HIGH-2 |
| Oracle install fails at the declared `git+https` pin | Medium | Moderate — local clone fallback exists in Task 2 | MEDIUM-1 |
| Flaky multicast on hosted runners misread as candidate failure | Medium | Moderate — mitigated if tiers are recorded separately | MEDIUM-2 |

Security posture is adequate for the work: no privileged operation, no secrets in TXT, bounded parsing and flood cases specified, and the CI job constrained to non-publishing artefacts. The supply-chain control (T-03-SC) is well-intentioned but is the same machinery driving HIGH-4; the `uv pip freeze` hash suggested above retains the property at a fraction of the cost.

**Recommendation: re-cut before execution.** HIGH-1 and HIGH-3 are correctness problems in the evidence path and must be resolved regardless of budget; HIGH-2 is a one-line fix; HIGH-4 is a decision the user should make explicitly — whether harness construction is inside or outside the D-14 budget — because the plan currently makes it implicitly, and in the more expensive direction.


---

## OpenCode Review

## 03-01

### Summary

The plan is a single-purpose MDNS-10 evidence spike: a stdlib-first harness (`scripts/spike_mdns_candidates.py`), two spike test files inside the core package's test suite, a non-publishing CI evidence job, a provenance JSON plus a markdown decision ledger, and a blocking human checkpoint. I traced its claims against the emulator source, the sibling `lifx-async` checkout, both workflow files, `pyproject.toml` and the PyApp documentation. The plan is faithful to the locked decisions (D-09–D-18), handles negative and provisional outcomes explicitly, and does not plan MDNS-01–09/11. Its main defects are one hard blocker (the pinned oracle commit is not pushed to GitHub, so the mandated `git+https` install path cannot resolve), and several under-specified integration mechanics (test-suite placement, `uv --isolated` environment boundaries, CI job triggers and cost).

### Strengths

- **Verified interface claims.** `EmulatedLifxServer.ipv4_endpoint`/`ipv6_endpoint` exist and publish the committed same-port pair (`packages/lifx-emulator-core/src/lifx_emulator/server.py:734-741`, with the IPv6 socket bound to the IPv4 port at `server.py:910`), so the spike can run the stock server without production changes — exactly as the `<interfaces>` section promises.
- **Atomic startup/rollback pattern is real and reusable as evidence context.** `server.py:874-985` implements the lock-guarded dual bind with full rollback on failure (`server.py:939-949`), matching the research's characterisation and giving the spike a truthful baseline for lifecycle comparisons.
- **Oracle behaviour claims are accurate to source.** `_LifxRecordCache.add_packet(self, records: list, source_ip: str)` exists at `../lifx-async/src/lifx/network/discovery/mdns/discovery.py:707`; TXT `tm` mapping (`"thread" if value == "2"`) at `discovery.py:172-174`; 12-hex unicast-MAC validation at `discovery.py:177-194`; exact-instance matching at `discovery.py:163-169`. The plan's TXT assertions (`id`, `p`, `fw`, `tm`) test what the oracle actually enforces.
- **The sibling transport pattern is correctly characterised, including its flaw.** `MdnsTransport` at `../lifx-async/src/lifx/network/discovery/mdns/transport.py:64-101` provides the explicit-socket, async-context, cleanup-on-error pattern (`transport.py:131-217`), and the plan correctly notes that its automatic interface selection (`_select_mdns_ipv4_address`, `transport.py:38-61`, called at `transport.py:136`) must be rejected in favour of a caller-supplied interface — an accurate reading, not a copy.
- **Negative and provisional outcomes are first-class, without weakening locked decisions.** The `meets_gate`/`rejected`/`provisional`/`tool_error` state machine makes a validated rejection a *successful* harness result, forces provisional on missing platform/packaging/provenance evidence (D-12), makes no-go require decisive rejection, and gates the new-responder candidate on both D-11 forms being `rejected` (D-09 ordering). Permitted not-run reasons (decisive rejection, unavailable environment, unverifiable provenance, cap exhaustion) implement D-14's hard stop without converting missing proof into a pass.
- **Scope discipline holds.** `files_modified` touches only spike tooling, tests, CI wiring and evidence docs; the deferred coverage ledger keeps MDNS-01–09/11 pending; VM work is explicitly excluded (D-16–D-18); the verification section requires an empty diff over `pyproject.toml`, `uv.lock` and both `src` trees.
- **Packaging claims verified.** The Intel runner `macos-15-intel` exists (`.github/workflows/release-binaries.yml:30-33`), PyApp is pinned at 0.26.0 (`.github/workflows/release-binaries.yml:8`), and PyApp's `PYAPP_PROJECT_PATH` does accept a local wheel for embedding (PyApp project configuration docs, "Embedding" section), so the CI leg's mechanism is sound.
- **The pinned revision exists locally.** `48b7efbff59656499373b13ef17e3008d125feb5` is the sibling checkout's current HEAD, so local `git clone --no-local ../lifx-async` snapshots can work (see HIGH concern for the remote side).

### Concerns

**HIGH**

- **The pinned oracle revision is unpushed, so the mandated install path cannot resolve.** The sibling's `origin/main` is `d09c842c...`, and no remote branch contains `48b7efb` (`git branch -r --contains` is empty; `merge-base --is-ancestor` exits 1). The plan hard-pins `--oracle-revision 48b7efb...` in Task 1/2 commands and the key_links pattern mandates `git+https://github.com/.+@[0-9a-f]{40}`. A `git+https` install from GitHub of an unpushed commit fails, both locally and in CI where `../lifx-async` does not exist at all. The repo itself is public (`gh repo view` reports `isPrivate: false`), so the fix is simply to push the commit or re-pin to `d09c842c`; as written, the spike's first run risks burning active hours diagnosing an unresolvable pin, which under the plan's own rules is a `tool_error`, not candidate evidence.

**MEDIUM**

- **Spike tests placed in the standard suite will be collected on every CI matrix leg with no stated skip strategy.** `pyproject.toml:59` makes `packages/lifx-emulator-core/tests/` a pytest root, and the CI test job runs `uv run --frozen pytest --cov-fail-under=80` across 10 legs (`.github/workflows/ci.yml:77-101`). But zeroconf and lifx-async are not project dependencies (`pyproject.toml:7-21`), `scripts/` is not on `pythonpath` (`pyproject.toml:60`), and the discovery-oracle tests need the pinned oracle installed. Either these tests spawn their own uv environments (network-dependent, slow, run 10× per push) or they skip — and the plan's own `fails_when` treats "zero collected tests" as invalid unless the ledger records a cause. The plan never says how `test_mdns_spike_datagrams.py` and `test_mdns_spike_socket_failures.py` degrade in the stock environment; this needs an explicit marking/skip contract so spike-evidence tests don't destabilise the ordinary suite or silently vanish.
- **The `uv run --frozen --isolated` environment boundary is implied but never stated.** `--isolated` runs the command in an isolated virtual environment without the project installed (uv 0.12.7 `uv run --help`). Task 1's probe needs the stock emulator, zeroconf and the oracle in one isolated environment, yet the top-level verify command can only work if `spike_mdns_candidates.py` is stdlib-only at the top level (Task 3 says the validator is stdlib-only, but Task 1's probe requirements do not) and all candidate work is delegated to spawned `uv run --with ...` child environments — including installing `lifx_emulator` itself (e.g. `--with ./packages/lifx-emulator-core`). Without that boundary being explicit, the verify commands as written fail on the first `import lifx_emulator`.
- **CI job triggers and cost are unspecified.** The plan adds `mdns-spike-evidence` to `.github/workflows/ci.yml`, which runs on every push to main and PR (`ci.yml:3-6`), and the `changes` filter only fires on `packages/**`, `pyproject.toml`, `uv.lock` (`ci.yml:28-32`) — not `scripts/**` or workflow edits. A job that resolves live PyPI/GitHub provenance, runs 1/10/100-device benchmarks and builds PyApp on the Intel runner is expensive to run implicitly on qualifying pushes, and won't run at all on harness-only changes. The plan should pin the job to an explicit trigger (for example `workflow_dispatch` plus the spike's own paths) rather than leaving cadence to implementation.
- **Ruff constraints apply to the harness and are unacknowledged.** `ruff check .` and `ruff format --check .` cover the whole repo (`ci.yml:57-61`), and the config imposes max-complexity 10, max-args 5, max-statements 50 with no per-file ignores outside the generated protocol files (`pyproject.toml:34-50`). A single script containing provenance resolution, a wire probe, benchmark runner, evidence validator and CLI subcommands will need deliberate decomposition; the CLAUDE.md exemption precedent covers only factory entry points. (Pyright is not an issue — its include is `packages/*/src` only, `pyproject.toml:55`.)

**LOW**

- **The evidence ledger lives inside the published docs tree.** `docs/` is the mkdocs site root (nav at `mkdocs.yml:207`), so `docs/evidence/phase-03-mdns-spike.md` will be swept into the public documentation site as an unlisted page. Evidence is arguably publishable, but the plan should either exclude `docs/evidence/` in mkdocs config or relocate it (for example under `.planning/` or a top-level `evidence/`).
- **Interface citation points to the wrong module.** The public oracle `discover_mdns()` is defined at `../lifx-async/src/lifx/api.py:1266-1272`, not in `mdns/discovery.py` as the `<interfaces>` section's phrasing suggests; an implementer following the context references would search the wrong file.
- **The Intel PyApp proof is a proxy, and its scope should be stated in the ledger.** A job-local wheel embedded via `PYAPP_PROJECT_PATH` proves PyApp can fetch and install the candidate on Intel macOS at first run, but not that the *published app's* own manifest can carry the candidate (that would require the forbidden `pyproject.toml` change). This is a reasonable reading of MDNS-10's "macOS x86_64 PyApp packaging" criterion, but the ledger must label it as candidate-installability evidence, not app-packaging evidence, to keep AC-12's demonstrated/untested distinction honest.

### Suggestions

1. Before starting Task 1, either push `48b7efb` to a branch on `Djelibeybi/lifx-async` or re-pin the oracle (and the Task 2 `--source-revision`) to `d09c842c...`, and add a preflight check to `resolve-provenance` that fails fast when the pinned revision is not reachable from the remote — this converts the current HIGH blocker into a one-line ledger entry.
2. State explicitly in Task 1 that the top-level script is stdlib-only and that every candidate/oracle/emulator import happens inside spawned `uv run --with`-based environments, with the exact child-invocation shape recorded in the provenance file's `environment_digest`.
3. Define the test-suite contract: mark `test_mdns_spike_*` files so they self-skip with a recorded reason when zeroconf/oracle/network are unavailable, keep pure datagram-injection cases always-running, and confirm the skip does not count as the spike's evidence pass (consistent with the plan's own AC-13-style honesty rule).
4. Give `mdns-spike-evidence` an explicit trigger (`workflow_dispatch` and/or its own path filter including `scripts/**` and `docs/evidence/**`) and state expected artefact retention, so evidence runs are deliberate rather than incidental to every qualifying push.
5. Add `scripts/spike_mdns_candidates.py` decompositional guidance or per-file ignores decision now (complexity ≤ 10, max-statements 50) to avoid a pre-commit/CI fight during a time-boxed spike.
6. Exclude `docs/evidence/` from the mkdocs build (or relocate it), and correct the `discover_mdns()` citation to `../lifx-async/src/lifx/api.py:1266`.

### Risk Assessment

The plan's internal logic is sound and unusually honest about failure: the outcome state machine, permitted not-run reasons and blocking human checkpoint mean a negative or time-capped result is a designed exit, not an accident, and D-12's hold on MDNS-01–09/11 planning is structurally enforced rather than merely promised. The dominant execution risks are external: the unpushed oracle pin (HIGH — it can silently consume the four-hour budget as `tool_error` diagnosis and blocks the CI evidence path entirely), and the three under-specified integration mechanics (test placement, isolated-environment boundary, CI cadence), each of which is recoverable but likely to cost spike hours if discovered mid-run. Budget realism is itself a risk: building the provenance resolver, wire probe, state machine, tests and CI job plausibly exceeds four active hours before any candidate evaluation depth, making a provisional first outcome the realistic expectation — which the plan accommodates correctly, but the user should expect the checkpoint to land on "provisional" unless the harness is kept deliberately minimal. Security posture is appropriate for a spike (legacy replies only to the query source, exact TXT content, bounded parsing, non-publishing CI, immutable provenance), and the no-production-change verification gate keeps the blast radius at zero for the codebase itself. Overall: approvable after the pin is fixed and the three MEDIUM mechanics are specified, ideally as plan amendments rather than discovered during execution.

## Antigravity Review

## 03-01

### Summary
Plan `03-01` defines a bounded implementation-selection spike for requirement MDNS-10 to evaluate mDNS responder candidates (`python-zeroconf`, direct or adapted `lifx-async` reuse, and a minimal custom responder) before detailed planning or production implementation of requirements MDNS-01–09 and MDNS-11. It establishes an evidence harness in `scripts/spike_mdns_candidates.py`, focused datagram and socket failure tests under `packages/lifx-emulator-core/tests/`, a CI evidence job in `.github/workflows/ci.yml`, and structured evidence outputs in `docs/evidence/`. The spike enforces a strict four-active-hour budget, preserves the production dependency graph via isolated candidate execution, and culminates in a human decision checkpoint to authorise `go`, `no-go`, `provisional`, or an evidenced extension.

---

### Strengths

1. **Strict phase boundary and dependency discipline (`.planning/phases/03-mdns-responder/03-01-PLAN.md:926-927, 1138-1153`)**  
   The plan respects locked decision D-12 by scoping execution strictly to MDNS-10. Requirements MDNS-01–09 and MDNS-11 are explicitly retained as pending in the `deferred_coverage_ledger` rather than claimed as implemented or dropped. Production source directories (`packages/lifx-emulator-core/src` and `packages/lifx-emulator/src`) remain untouched, preventing premature integration before an evidence-backed foundation is chosen.

2. **Ordered candidate fallback and anti-bias controls (`.planning/phases/03-mdns-responder/03-01-PLAN.md:1070-1077`, `.planning/phases/03-mdns-responder/03-CONTEXT.md:364-367`)**  
   The plan executes the candidate sequence strictly in accordance with D-09, D-10, and D-11: evaluating `python-zeroconf` first using public APIs only, evaluating both direct extension and code adaptation of sibling `lifx-async` only after a decisive zeroconf rejection, and reaching a new responder only after both reuse options fail. The harness explicitly distinguishes harness infrastructure errors (`execution_status=tool_error`) from valid candidate disqualifications (`candidate_status=rejected`), ensuring decisive negative findings advance the evaluation pipeline cleanly.

3. **Inviolable four-hour budget circuit breaker with honest provisional handling (`.planning/phases/03-mdns-responder/03-01-PLAN.md:1004, 1077, 1084`, `.planning/phases/03-mdns-responder/03-CONTEXT.md:372-376`)**  
   The plan operationalises decisions D-14 and D-15 by enforcing an immediate stop when the four-active-hour ceiling is reached, recording unexecuted checks as `not-run-with-reason` and defaulting to `provisional` rather than failing the harness or fabricating data. It also explicitly excludes VM provisioning and cross-machine network experiments from the initial four hours (D-16, D-17, D-18).

4. **Rigorous wire-level datagram assertions against consumer acceptance oracle (`.planning/phases/03-mdns-responder/03-01-PLAN.md:1036-1039`, `../lifx-async/src/lifx/network/discovery/mdns/discovery.py:281-289, 707-740`)**  
   Datagram verification is grounded directly in RFC 6762 §6.7 and the sibling client's actual record accumulation logic. The harness checks destination IP and port, echoed query ID and question records, cleared cache-flush bits, positive TTLs $\le 10$\,s, and per-device record isolation, cross-checking results against `_LifxRecordCache.add_packet()` and `discover_mdns()` pinned immutably to sibling revision `48b7efbff59656499373b13ef17e3008d125feb5`.

---

### Concerns

#### HIGH: Candidate fallback authoring creates extreme risk of timebox exhaustion if zeroconf fails
- **Citing:** `.planning/phases/03-mdns-responder/03-01-PLAN.md:1077`, `../lifx-async/src/lifx/network/discovery/mdns/dns.py:303-330, 346-390`, and `../lifx-async/src/lifx/network/discovery/mdns/transport.py:38-60, 134-150`.
- **Mechanism:** As documented in `03-RESEARCH.md:497`, `python-zeroconf` aggregates records across services into a single reply datagram, which creates an immediate likelihood of rejection against MDNS-03 / AC-04 (requiring exactly one complete datagram per device). When zeroconf is rejected, Task 2 requires implementing an extension overlay for `lifx-direct`, an adapted version for `lifx-adapted`, and potentially a custom `new-responder` prototype. However, source inspection of `../lifx-async/src/lifx/network/discovery/mdns/dns.py` confirms that `lifx-async` contains only response parsing and query construction (`build_ptr_query`, `build_address_query`) with no response encoding logic, while `transport.py` contains only an ephemeral client socket. Implementing functional response encoders and multicast listeners across two sibling-reuse variants and a custom responder within the remainder of a shared four-hour active budget will inevitably exhaust the timebox. While the plan correctly handles budget exhaustion by defaulting to `provisional`, this high likelihood means the spike will almost certainly stall without yielding conclusive fallback comparative data.

#### MEDIUM: Test discovery pollution and CI failure from placing spike tests in the core package test suite
- **Citing:** `.planning/phases/03-mdns-responder/03-01-PLAN.md:920-921, 1023, 1057`, `pyproject.toml:58-75`, and `.github/workflows/ci.yml:72-106`.
- **Mechanism:** The plan places `test_mdns_spike_datagrams.py` and `test_mdns_spike_socket_failures.py` under `packages/lifx-emulator-core/tests/`. In `pyproject.toml:59-63`, `testpaths` includes `packages/lifx-emulator-core/tests` and `python_files` matches `test_*.py`. Consequently, standard `pytest` invocations—specifically `.github/workflows/ci.yml:101` (`uv run --frozen pytest --cov-fail-under=80`)—will discover and execute these spike test files. Because `python-zeroconf` is not a workspace dependency in `pyproject.toml:8-21` or `packages/lifx-emulator-core/pyproject.toml:7-10`, any direct or unshielded import of `zeroconf` will cause `ModuleNotFoundError` in the standard CI test matrix across Python 3.10–3.14. Furthermore, running spike tests during standard test runs will distort the 80% test coverage enforcement.

#### MEDIUM: Flag conflict and dependency isolation gap in top-level harness verification invocation
- **Citing:** `.planning/phases/03-mdns-responder/03-01-PLAN.md:1049, 1086`, `packages/lifx-emulator-core/pyproject.toml:7-10`, and `packages/lifx-emulator-core/src/lifx_emulator/server.py:154-175`.
- **Mechanism:** Tasks 1 and 2 specify verification commands using `uv run --frozen --isolated python scripts/spike_mdns_candidates.py ...`. In `uv`, `--isolated` directs the runner to ignore the project environment and configuration files (`pyproject.toml`). In an isolated environment with no dependencies installed, importing `lifx_emulator.server.EmulatedLifxServer` (permitted by line 1005 for endpoint binding) will fail because `lifx-emulator-core` runtime dependencies (`pydantic>=2.0.0` and `pyyaml>=6.0.3` at `packages/lifx-emulator-core/pyproject.toml:8-9`) are absent. Concurrently, `--frozen` requires an existing project lockfile, creating a semantic clash with `--isolated`. The top-level driver needs access to the local workspace packages, whereas candidate sub-processes require isolation.

#### LOW: Incomplete PyApp build prerequisites in CI evidence job specification
- **Citing:** `.planning/phases/03-mdns-responder/03-01-PLAN.md:1075, 1077` and `.github/workflows/release-binaries.yml:62-84`.
- **Mechanism:** Task 2 specifies adding an `mdns-spike-evidence` job to `.github/workflows/ci.yml` that builds PyApp on Intel macOS (`macos-15-intel`) from a local candidate wheel using `PYAPP_PROJECT_PATH`. However, unlike `release-binaries.yml:62-72`—which explicitly installs the Rust toolchain via `dtolnay/rust-toolchain` and clones the PyApp repository—the task action does not articulate these toolchain setup steps, risking CI failure during PyApp compilation if Rust or the PyApp source is omitted from the runner steps.

---

### Suggestions

1. **Clarify delta-assessment bounds for `lifx-async` reuse before coding overlays**  
   Update Task 2 action guidance to permit a rapid static delta evaluation of `lifx-async` (specifically citing the absence of DNS response encoders in `../lifx-async/src/lifx/network/discovery/mdns/dns.py:303-390`). If adapting `lifx-async` requires writing the entire response encoder and multicast listener from scratch, document that parity gap immediately as rejection evidence rather than burning multiple active hours implementing redundant prototypes.

2. **Isolate spike test files from the standard pytest collection**  
   Move `test_mdns_spike_datagrams.py` and `test_mdns_spike_socket_failures.py` to a dedicated spike directory (e.g. `scripts/tests/` or `tests/spike/`), or register an explicit custom marker (e.g. `@pytest.mark.spike`) and add `skipif` guards when candidate libraries or the spike environment are not present. This prevents breaking `uv run --frozen pytest` at `.github/workflows/ci.yml:101`.

3. **Separate top-level execution flags from candidate subprocess isolation**  
   Adjust verification commands to execute the top-level runner within the project environment (`uv run --frozen python scripts/spike_mdns_candidates.py ...`), while ensuring that candidate-specific invocations managed inside `scripts/spike_mdns_candidates.py` invoke isolated subprocesses (`uv run --isolated --with ...`) using the resolved candidate pins from provenance.

4. **Mirror PyApp toolchain steps from `release-binaries.yml` into `ci.yml`**  
   Ensure the proposed `mdns-spike-evidence` job in `.github/workflows/ci.yml` incorporates the Rust toolchain installation (`dtolnay/rust-toolchain@6bed0761d98439e5a578e2877258200ad565ba87`) and repository checkout steps modelled in `.github/workflows/release-binaries.yml:62-72`.

---

### Risk Assessment

- **Feasibility & Execution:** Medium-High. The runner architecture, wire-level assertions, and provenance tracking are sound. However, attempting to build working prototypes for `lifx-direct`, `lifx-adapted`, and `new-responder` upon zeroconf rejection within the remaining fraction of four active hours will almost certainly exhaust the timebox, forcing a `provisional` result.
- **CI / Regression Risk:** Medium. Placing spike tests inside `packages/lifx-emulator-core/tests/` without import guards will break default `pytest` runs in CI if `zeroconf` is imported outside an isolated environment.
- **Security & Integrity:** Low. Sandboxed candidate dependency installation, read-only handling of sibling checkouts, non-publishing CI jobs, and STRIDE mitigations (`T-03-01` to `T-03-SC`) protect repository integrity.

---

## Overall Findings

Plan `03-01` is well-aligned with the project roadmap, locked decisions (D-09 through D-18), and the MDNS-10 specification. It successfully resists scope creep by keeping requirements MDNS-01–09 and MDNS-11 strictly pending, avoiding production code modification, and framing the spike around reproducible, falsifiable evidence.

The primary operational risks lie in:
1. The authoring burden of the fallback candidate paths (`lifx-direct` and `lifx-adapted`), which will challenge the four-active-hour ceiling if `python-zeroconf` fails packet-boundary requirements;
2. Unintended interaction between new spike test files in `packages/lifx-emulator-core/tests/` and the default CI pytest suite;
3. Subtleties in `uv run` flag combinations (`--frozen --isolated`) when accessing core workspace utilities.

With test isolation clarified and fallback delta assessments scoped to avoid excessive prototype authoring, the plan provides a defensible framework for mDNS responder selection.


---

## Next step

Use `$gsd-plan-phase 3 --reviews` to incorporate the actionable findings while preserving the locked constraints. All configured review lanes are now complete.
