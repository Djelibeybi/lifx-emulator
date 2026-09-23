# Plan 03-02: MDNS-10 decision checkpoint

Task 1 is complete: the user selected `approve-120`. Task 2 is complete. Task 3 awaits the human decision; Phase 3 is not complete and no production integration is authorised.

The validated ledger supports **go with zeroconf** or **provisional hold**. Go is recommended. No-go is unsupported because the evidence does not decisively reject the candidate routes.

## Exact evidence

- Evaluated code head: `481c06d41223339df94dfc93e474664c69742103`.
- Candidate: zeroconf `0.151.3`, official PyPI version rechecked at `2026-09-23T07:03:25.552852Z`. The full registry response is retained losslessly as ordered gzip parts, each below the repository file-size limit.
- Candidate distribution SHA-256: `ce6c548e665759b6150cef4db9ab9d7bdd89857e90c513abd6b7340bdd7dbd6a`.
- Pristine lifx-async source: `48b7efbff59656499373b13ef17e3008d125feb5`.
- [Exact-head CI run](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35829387744): Ubuntu and macOS spike jobs passed; all ten Python 3.10–3.14 regression jobs and code quality passed.
- Ledger: `03-ZEROCONF-CLOSEOUT.json`. Full file SHA-256: `f86e2fc54fe410932550fb118d430f40197c715412055e5a1d74af13494df84f`.
- Decision evidence digest (canonical ledger excluding the human decision): `364381ea54bde91b95afe6ff51117b4309128fa48538d3d74249b7c7a8a9c6b0`.
- Current local, Ubuntu and macOS evidence and matching hosted receipts: `03-closeout-evidence/`. The validator checks source, adapter, version, input, environment and receipt hashes.
- Historical continuation, recovery and direct-candidate records are unchanged from allowance baseline `.planning/phases/03-mdns-responder/03-02-ALLOWANCE.json` / `e6e9dbe8e33125ccbb76d6e7029fa2bc5b44a2e3`.

## Measured results

| Platform | Correlated flood replies | Flood time | Supported-operation cases | Whole-case descriptors |
|---|---|---|---|---|
| local | 256/256 | 6.308s | 18/18 | 8 → 8 |
| linux | 256/256 | 0.856s | 18/18 | 7 → 7 |
| darwin | 256/256 | 3.191s | 18/18 | 8 → 8 |

Each platform passed the five malformed datagrams followed by fresh valid queries and pristine-client discovery. Pending task and thread inventories returned to baseline. The 18 cases cover register, returned announcement, update, unregister, interface update and close failures across WiFi, Thread and mixed fleets. WiFi control continued after failure and after explicit retry; Thread/mixed endpoints stopped; cleanup failures prevented replacement until ownership was resolved.

All 16 configuration/address rows, opt-out, empty responder lifecycle, public interface update, complete 1/10/100 raw records, required direct A/AAAA queries, membership removal/restoration and host-daemon coexistence passed. Windows constructor/interface policy is **simulated**, not a real Windows network result.

Retained fleet evidence is explicitly a public-client 100-device local observation plus candidate-labelled raw 1/10/100 timings, CPU and RSS. Intel packaging is retained composite evidence for the exact zeroconf distribution and its public async import inside the packaged executable; the historical `lifx-direct` receipt is not relabelled.

## Contract limits

- D-08 accepts silent listener loss. `running` is lifecycle state, not a network-health or automatic fault-detection guarantee. Injected failures are at supported public-operation boundaries.
- Continuation response packets may omit the DNS question. Complete discovery across packets is demonstrated; full RFC conformance is not claimed.
- Hosted macOS networking uses loopback under AC-13. No VM or cross-machine proof is claimed.
- Configuration/status/recovery are candidate-fit prototypes. MDNS-01–09 and MDNS-11 remain pending production implementation.

## Verification and allowance

- Focused suite: **98 passed** at evaluated head; behavioural RED commits precede the fixes.
- Full local regression suite: **1,400 passed**, 4 warnings, 95% coverage. Production source and manifests did not change afterwards.
- Seven negative ledger mutations were rejected; see `03-closeout-evidence/validator-audit.json`.
- Repository commit hooks passed. Additional C901 inspection found six inherited complex functions in historical/direct spike paths; these are outside the approved closeout cases and were not rewritten. Repository code-quality CI passes.
- Protected-path comparison against the allowance baseline passes for production source, `pyproject.toml`, `uv.lock`, the old decision ledger/summary and historical continuation/recovery directories.
- Elapsed at final evidence capture: **2225.568 / 7200 seconds**, measured conservatively as wall time from the approved start, including concurrent CI. The separately recorded 71 seconds is final run creation to the later Ubuntu/macOS job start (11 seconds Ubuntu, 71 seconds macOS), including scheduling/detection; none is subtracted. The initial allowance record's zero queue value is the approval-time value.
- No further experimental work is authorised by this checkpoint. Documentation/signing delivery follows evidence capture within the same cap.

## Human decision required

1. **Go with zeroconf (recommended):** record `go`, binding the decision digest above. Return to `$gsd-plan-phase 3` to plan MDNS-01–09/11.
2. **Provisional hold:** record `provisional` with the user's rationale; retain the implementation gate.

After selection, record only decision status, rationale, authority and evidence digest in the new ledger, rerun the validator, and create `03-02-SUMMARY.md`. Do not alter historical evidence or mark Phase 3 complete. The later evidence/documentation commit may differ from the evaluated code head; the receipts certify the exact head above.
