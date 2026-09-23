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
