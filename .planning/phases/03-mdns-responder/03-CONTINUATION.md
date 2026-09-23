# Phase 3 targeted zeroconf continuation

## Authority and scope

On 2026-09-23 the user explicitly lifted the local/CI harness restriction where it moves the work forward faster. This supersedes the no-harness wording in earlier amendments and follow-up reports. It does not waive evidence requirements or authorise production integration.

The earlier 60-minute allowance used 4 minutes 33 seconds. This continuation uses the remaining allowance (55 minutes 27 seconds), including investigation, implementation, verification and documentation; CI queue time is separate. Work began around 2026-09-23T00:03Z. No new four-hour extension is assumed.

The existing runner rejected aggregation by requiring one device per packet. Its collector now assembles and checks exact PTR, SRV, TXT and family/address associations across datagrams. The accepted continuation-question exception remains limited to subsequent packets; query ID, source port, cache-flush and TTL checks remain enforced.

## Execution scope

1. Reuse the existing runner for corrected complete-fleet validation and focused regression tests.
2. Collect fresh zeroconf local and hosted Ubuntu/macOS results with runner hashes and candidate-specific receipts; preserve the original ledger as historical evidence.
3. Add a bounded public registration removal/re-add observation. This does not establish listener failure recovery or production status integration.
4. Include pinned zeroconf in the existing disposable Intel PyApp dependency graph and verify its version and public async API import from inside the packaged environment. The older direct-candidate receipt alone is not zeroconf evidence.
5. Record passed, failed and untested gates before the time limit. Do not mark Phase 3 complete or begin production integration on incomplete evidence.

The original plan remains halted at its decision gate. This continuation supersedes only its obsolete execution constraints; it does not turn its historical summary into a completed implementation.

## Intermediate findings

The first revised run (`da6053b`) passed local and hosted Ubuntu raw fleet discovery but exposed same-name re-registration failure. Source inspection and a local diagnostic found the cached PTR TTL was 1,125 seconds despite a ten-second advertisement. The bounded eleven-second retry therefore could not clear it. This is retained as evidence about fresh registration of a previously removed identity, not erased.

A targeted local follow-up restored that previously owned identity using the public `async_update_service` API: nine remaining devices were observed after removal, the removed identity was absent, and all ten returned after restoration. Independent query IDs avoid zeroconf's duplicate-payload suppression; the original repeated query undercounted the remaining fleet. No private cache mutation, identity renaming or library patch is used. This is candidate-fit evidence; production conflict policy, listener failure recovery and status integration remain unproved.

The first hosted macOS public oracle found neither WiFi nor Thread. The next revision retains raw-query diagnostic measurements even when public discovery fails, to identify which path is failing instead of dropping later evidence. No macOS success is inferred from Ubuntu or local macOS results.


The hosted virtual-interface query still returned `EHOSTUNREACH` after explicit Darwin socket scoping. AC-13 explicitly permits loopback-multicast integration, so the final bounded attempt moves the disposable macOS test route and synthetic ULA to `lo0`. It retains the real daemon and pristine client. This is same-host multicast evidence, not cross-machine or physical-interface evidence; the virtual-interface failure remains recorded.


## Recorded outcome

**Zeroconf remains the preferred, provisional foundation.** The targeted harness changes produced candidate-specific platform and membership evidence; they do not complete Phase 3 or authorise production integration.

| Check | Local macOS | Hosted Ubuntu | Hosted macOS |
| --- | --- | --- | --- |
| Complete raw record sets, 1 WiFi / 1 Thread / 10 mixed / 100 mixed | Passed | Passed | Passed on explicit loopback multicast |
| Pristine public client, one WiFi and one Thread | Passed | Passed | Passed on explicit loopback multicast |
| Removal/restoration of previously owned identity | 9 remaining, removed absent, 10 restored | Same | Same |
| Direct A/AAAA queries | Passed | Passed | Passed |
| Daemon visible and clean final task/thread inventory | Passed | Passed | Passed |

The final platform inputs are commit `b8a4607bc00de09ad014a4e9d03b41c9015d7aa9`, run [35803195241](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35803195241). Receipts and runner hashes were checked before retaining the JSON. The retained local run uses `12a71bd`, whose runner hash is also verified. Candidate version and oracle revision are unchanged. This does not transfer the old direct responder's receipts to zeroconf.

The Intel PyApp artefacts from the initial run `35801477606` and final run `35803195241` demonstrate a packaged app containing `zeroconf==0.151.3`, successful first run, and import of `AsyncZeroconf` inside that environment. Exact app metadata and output hashes are retained. The additional direct-prototype dependency in that disposable app is not represented as zeroconf implementation code.

### Scope limits and remaining gates

- Hosted 100-device results are raw record-set checks, not 100-device public-client benchmarks. The earlier separate local experiment in `03-ZEROCONF-REEVALUATION.md` remains the public 100-device/control evidence.
- Restoring a previously owned identity uses `async_update_service` after the public registration name-conflict check. It is not a blanket bypass for new service-name conflicts, and the production ownership/conflict policy is not implemented.
- Listener startup failure, explicit retry, partial-fleet startup/recovery and production status integration remain unproved. Membership restoration and independent cleanup are narrower observations.
- Zeroconf-specific malformed/flood behaviour, Windows simulation and full configuration/interface enforcement are not demonstrated by the old direct prototype's tests. The remaining broad criterion cells stay untested.
- Hosted virtual-interface multicast still produced `EHOSTUNREACH`; the final hosted macOS proof is specifically loopback multicast permitted by AC-13. Local macOS used its existing interface. No cross-machine result is claimed.
- The accepted continuation-question omission remains a standards exception for the tested client, not full legacy-unicast RFC conformance.

Validation: 43 focused tests pass locally, including exact record association, candidate receipt identity, invalid oracle checkout rejection, Darwin socket scoping and socket cleanup on bind failure. Repository commit hooks pass. Production source, dependency manifests and `uv.lock` remain unchanged. The original spike evidence files retain their historical contents.

The next substantive work is a bounded failure/recovery and robustness prototype using the selected public APIs, followed by the explicit MDNS-10 decision. Do not restart the generic responder comparison or infer production approval from green evidence jobs.


Final run `35803195241` completed successfully, including ordinary CI checks and all three mDNS evidence jobs. Final Intel metadata, first-run and hash-list digests match its receipt. Both the zeroconf platform receipt and the separately labelled direct-dependency packaging receipt validate for `b8a4607`; the supplemental zeroconf import result and app metadata establish which library was packaged.

Evidence closeout recorded at 2026-09-23T00:52:05.259990Z. Work began around 00:03 UTC and remained within the unused 55 minutes 27 seconds of the earlier allowance, conservatively counting CI waits. No further prototype work was started. MDNS-10 and Phase 3 remain provisional.
