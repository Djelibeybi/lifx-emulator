# Phase 3: mDNS Responder — Specification

**Amended 2026-09-23:** Packet grouping is unrestricted subject to complete-fleet discovery; zeroconf re-evaluation is pending. See [03-PACKET-GROUPING-AMENDMENT.md](03-PACKET-GROUPING-AMENDMENT.md).

**Accepted compatibility exception (2026-09-23):** Zeroconf continuation replies may omit the question section for the tested `lifx-async` client. This does not block candidate selection and requires no client/library patch; it is not a claim of full RFC conformance. All other protocol and evidence requirements remain in force. See [03-ZEROCONF-REEVALUATION.md](03-ZEROCONF-REEVALUATION.md).

**Created:** 2026-09-11
**Ambiguity score:** 0.075 (gate: ≤ 0.20)
**Requirements:** 11 locked

**Reconciled:** 2026-09-22 against `03-CONTEXT.md` D-01–D-18. The original ambiguity score describes the specification interview; it has not been recalculated for these later decisions.

## Discussion refinements

The following agreed refinements apply within the existing requirement IDs and acceptance criteria:

- **MDNS-01/06 (D-01–D-04):** Preserve existing factory/server calls. Use server `mdns_enabled=False`, factory `mdns_enabled=True` and `mdns_address=None`. Advertisement settings are fixed at device creation. Factories validate explicit addresses, families and Thread opt-out; startup validates bind-dependent settings, and additions validate before registration.
- **MDNS-09 (D-05–D-08):** Expose read-only `mdns_status` (`disabled`, `stopped`, `running`, `failed`) and `mdns_error`, with logged failures. Explicit `await server.retry_mdns()` recovers WiFi-only service without interrupting LIFX traffic. Failed enabled mDNS rejects Thread additions before membership changes. Runtime failure follows the same fleet policy: WiFi-only continues; Thread-only/mixed fleets shut down cleanly and retain failure details. AC-10/11 include these status, retry and runtime-failure cases.
- **MDNS-10 (D-09–D-13):** Evaluate current python-zeroconf first, then extending or adapting existing `lifx-async` mDNS code, then a new responder. Prefer zeroconf when requirements are met unless evidence shows a material alternative advantage; assess public APIs, adapter size, private internals, forks, coupling and maintenance. Compare direct sibling extension with adaptation rather than preselecting either. Missing platform or packaging evidence keeps the decision provisional and holds detailed planning of the remaining ten requirements. Benchmark complete-fleet discovery for sizes 1, 10 and 100, recording CPU and memory; these are not supported fleet limits.
- **MDNS-10 (D-14–D-18):** Share four active-work hours across candidates and record CI queue time separately. At the limit, record findings and unresolved evidence. An additional four hours requires concrete evidence, documentation links and exact source line references showing worthwhile depth, performance or feature completeness. Only within that justified extension, after required evidence and if time remains, define and provision a small Linux VM on `devproxmox.lot209.xyz` for optional Mac-to-guest discovery, state-query and control checks. VM definition, provisioning and cross-machine testing are excluded from the initial four hours. This experiment neither replaces required evidence nor automatically justifies an extension.

Only the MDNS-10 spike is ready for detailed planning. The other requirements remain locked and pending; their mention in spike evaluation criteria does not constitute implementation coverage.

## Goal

An explicitly enabled core mDNS responder lets `lifx-async` discover every emulated device from its DNS-SD records, independently of reply packet grouping, advertising Thread devices with AAAA records and WiFi devices with A records.

## Background

The core server in `packages/lifx-emulator-core/src/lifx_emulator/server.py` already binds an atomic same-port IPv4/IPv6 endpoint pair, exposes committed endpoints and retains bounded packet work through shutdown. Thread devices already accept only exact IPv6 unicast. There is no mDNS responder or advertised-address setting yet.

`packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` has single-slot `on_device_added` and `on_device_removed` callbacks. mDNS lifecycle observation must coexist with the app's existing WebSocket bridge.

The sibling client's `_LifxRecordCache` in `src/lifx/network/discovery/mdns/discovery.py` accumulates records across response packets. Neither one whole-fleet packet nor one packet per device is a client requirement. The original interview selected one reply per device to remove an artificial fleet-size restriction. On 2026-09-23 the user approved replacing that packet-boundary rule with complete, correct discovery of every advertised device, allowing aggregation and multiple packets without a fleet-size limit imposed by packet capacity. See `03-PACKET-GROUPING-AMENDMENT.md`.

This specification clarifies the conflicting default statements in PROJECT.md and CFG-06: core mDNS is opt-in; standalone defaults are Phase 4 work. Phase 2's existing IPv6 default is unchanged.

## Requirements

1. **MDNS-01 — Opt-in multicast reception:** An explicitly enabled responder receives `_lifx._udp.local` PTR queries on IPv4 multicast `224.0.0.251:5353` alongside the host mDNS daemon.
   - Current: The server has LIFX sockets only; there is no mDNS listener.
   - Target: Core construction without an mDNS option creates no mDNS listener. Enabling mDNS advertises all devices by default; individual WiFi devices may opt out, but individual Thread devices may not. The responder uses address reuse and multicast membership appropriate to the platform.
   - Acceptance: AC-01 and AC-02 prove opt-in behaviour, device eligibility and daemon coexistence.

2. **MDNS-02 — Legacy-unicast replies:** A query arriving from a source port other than 5353 receives its replies at that source address and port, with the query ID echoed, cache-flush bits clear and record TTLs no greater than 10 seconds.
   - Current: No DNS queries are handled.
   - Target: The client's ephemeral-port discovery path receives every eligible device's response without joining a multicast group.
   - Acceptance: AC-03 checks destination, ID, flags and TTL on each response, including repeated queries with different IDs.

3. **MDNS-03 — Complete discovery independent of packet grouping:** Every advertised device is discoverable from its correctly associated PTR, SRV, TXT and exactly one matching-family address record. Replies may contain records for multiple devices or span multiple packets; no eligible device may be lost or excluded because the fleet exceeds one packet.
   - Current: No DNS-SD record construction exists; the roadmap formerly required one packet for the fleet.
   - Target: PTR maps `_lifx._udp.local` to `<serial>._lifx._udp.local`; SRV has priority and weight zero, the actual bound LIFX UDP port and a per-device `.local` hostname. Discovery returns every eligible device with complete, correct records, independently of how replies group them into packets.
   - Acceptance: AC-04 compares the response set with the eligible device set, including zero, one and multiple devices, without requiring an inter-device packet order.

4. **MDNS-04 — Exact metadata:** Each device's TXT record contains exactly `id`, `p`, `fw` and `tm` with stable values across repeated queries of unchanged state.
   - Current: Serial, product, host firmware and connectivity exist on core devices.
   - Target: Values are the 12-hex lowercase serial, decimal product ID, firmware `major.minor` and `tm=1` for WiFi or `tm=2` for Thread. Firmware components remain integers; for example, 4.200 must not become 4.2 through numeric conversion.
   - Acceptance: AC-05 decodes the four fields, compares them with device state and repeats the query.

5. **MDNS-05 — Address-family fidelity:** Every advertised Thread device has one AAAA record and no A record; every advertised WiFi device has one A record and no AAAA record.
   - Current: Core connectivity and transport isolation already exist, but DNS address records do not.
   - Target: Advertised address family reflects device connectivity even though the server itself has both transports.
   - Acceptance: AC-06 checks a mixed fleet and shared-address devices without conflating their distinct service identities.

6. **MDNS-06 — Explicit, usable advertised addresses:** A per-device Thread address overrides its IPv6 bind fallback; a wildcard bind requires an explicit advertised address for each advertised family, and all link-local advertised addresses are rejected.
   - Current: Concrete IPv4 and IPv6 bind endpoints exist; no advertised-address configuration exists.
   - Target: Thread accepts ULA/GUA addresses and loopback for local tests. WiFi uses a usable IPv4 address, including loopback for local tests. Concrete binds supply the fallback when no override exists. Neither `0.0.0.0` nor `::` is advertised. No interface address is automatically selected. Scoped and unscoped link-local addresses are invalid. Empty, malformed and wrong-family explicit values fail clearly.
   - Acceptance: AC-07 checks overrides, fallbacks, equivalent IPv6 spellings, wildcard omissions and invalid addresses before they can enter a response.

7. **MDNS-07 — Follow-up address queries:** Direct A or AAAA queries for an advertised hostname return its configured address when the requested family matches the device.
   - Current: No hostname lookup responder exists.
   - Target: Follow-up lookups resolve the same hostname and address used by the device's SRV and address records; no opposite-family address is invented.
   - Acceptance: AC-08 checks each family against the matching hostname, including after removal or opt-out, when no advertised address remains for that device.

8. **MDNS-08 — Live device membership:** The advertised record set follows successful runtime additions and removals through a multi-listener DeviceManager event registry while preserving existing WebSocket device events.
   - Current: DeviceManager supports only one added callback and one removed callback.
   - Target: mDNS and the existing bridge both observe device lifecycle changes. Completed changes appear in the next query's response set, including removal of the final device. Distinct devices remain distinct when they share an advertised address.
   - Acceptance: AC-09 adds, removes and re-adds devices while both consumers are registered, and checks discovery membership and existing events.

9. **MDNS-09 — Conditional startup failure and owned lifecycle:** mDNS starts and stops with the server; an mDNS startup failure is fatal when Thread devices are configured, while a WiFi-only server can continue serving LIFX traffic.
   - Current: The server owns its LIFX endpoint pair and retained tasks; no mDNS lifecycle exists.
   - Target: Thread configuration plus failed mDNS startup yields a clear startup error and cleanup. WiFi-only configuration plus failed mDNS startup yields an observable failure without disabling the functioning LIFX server. Explicitly leaving core mDNS disabled remains supported. Shutdown releases mDNS sockets, membership, listeners and tasks, including after partial startup or repeated lifecycle operations.
   - Acceptance: AC-10 and AC-11 cover Thread-only, mixed, WiFi-only and disabled configurations, failure injection and repeated start/stop across event loops.

10. **MDNS-10 — Evidence before implementation selection:** A time-boxed spike evaluates current python-zeroconf, then reuse of existing `lifx-async` mDNS code, then a new responder, and records a go/no-go decision before the responder implementation is built.
    - Current: The implementation choice is unresolved; no candidate has the required evidence in this phase.
    - Target: The recorded comparison covers `lifx-async` discovery, legacy-unicast replies, complete-fleet discovery independent of packet grouping, mixed TXT/address families, host-daemon coexistence and macOS x86_64 PyApp packaging. Record versions, time box, commands, results and unsupported or untested cases. Detailed implementation planning follows the decision.
    - Acceptance: AC-12 requires an explicit decision and evidence for every criterion, including complete-fleet discovery without packet-capacity truncation or a packet-derived fleet limit.

11. **MDNS-11 — Executable discovery evidence:** Datagram-injection unit tests and loopback-multicast integration tests prove the responder contract on Ubuntu and macOS.
    - Current: Native IPv6 tests exist; there are no mDNS responder tests.
    - Target: Tests exercise actual records and response destinations, mixed fleets, lifecycle failures and runtime changes. `lifx-async` discovery succeeds against the chosen responder in the spike and implementation checks. Windows-specific socket branches have simulation coverage because there is no Windows CI leg.
    - Acceptance: AC-13 records passing unit/integration results and distinguishes local, CI and simulated platform evidence. A skipped multicast test is not reported as a passing integration check.

## Boundaries

**In scope:**

- Core responder and configuration surface required to enable it and supply advertisement settings.
- Complete discovery of every advertised device from correctly associated DNS-SD records, with legacy-unicast response behaviour; packet aggregation and multiple reply packets are permitted.
- Address validation, WiFi opt-out, live device membership and non-displacing event listeners.
- Conditional startup failure, shutdown ownership, the implementation-selection spike and focused discovery tests.
- Corrections to MDNS-03 and Phase 3 roadmap criteria accompanying this specification.

**Out of scope:**

- Dropping eligible devices or imposing a fleet-size limit because their combined records exceed one packet. Packet aggregation itself is permitted.
- CLI flags, YAML, export-config and standalone default enablement — Phase 4.
- Management API models and validation responses — Phase 5.
- Dashboard controls — excluded from this milestone.
- Full sibling-suite migration and removal of its IPv6 test subclass — Phase 6; the spike's client discovery check remains in scope here.
- Border-router topology, delayed reappearance and stale-advertisement timing — deferred by the milestone.
- IPv6 mDNS multicast and IPv6 tagged LIFX discovery — excluded by the milestone.
- Automatic interface/address selection and advertised link-local addresses — rejected during this interview.
- Changes to the existing IPv6 transport default, generated protocol files or unrelated local configuration changes.

## Constraints

- Python 3.10–3.14; Linux, macOS and Windows socket portability, with real CI evidence on Ubuntu/macOS and simulation evidence on Windows.
- Asyncio networking; the spike must assess the existing no-threads-in-the-packet-path constraint when choosing a dependency.
- Use the latest dependency release at implementation time, installed and locked with uv; this specification does not select a package version.
- Preserve Phase 2 transport isolation, endpoint publication and existing WiFi LIFX behaviour.
- Core mDNS disabled is an intentional opt-in state, not a failed startup. The Thread-fatal rule applies when mDNS is enabled but cannot start.
- Use the actual bound LIFX port, including when the caller requests port zero.
- Existing repository complexity, typing, Australian English and signed Conventional Commit rules apply.
- Requirement IDs retain MDNS-01 through MDNS-11; interview refinements are captured within those requirements rather than creating untracked milestone IDs.

## Acceptance Criteria

- [ ] **AC-01:** Default core construction opens no mDNS socket; enabling mDNS includes eligible devices, honours WiFi opt-out and rejects individual Thread opt-out.
- [ ] **AC-02:** With the host mDNS daemon active, an enabled responder receives an IPv4 multicast PTR query without displacing that daemon.
- [ ] **AC-03:** Every response to an ephemeral-port query targets its source address/port, echoes its query ID, clears cache-flush bits and uses positive record TTLs no greater than 10 seconds. Repeated queries with different IDs receive independently correct replies.
- [ ] **AC-04:** A discovery operation returns exactly the eligible device set with complete, correctly associated PTR/SRV/TXT/address records. Aggregated replies and records spread across packets are permitted. Zero eligible devices produce no device advertisements. Correctness is independent of packet count, grouping and order; packet capacity must not cause missing devices or a fleet-size restriction. SRV priority/weight are zero and its port equals the committed LIFX port, including port-zero startup.
- [ ] **AC-05:** TXT has exactly the four specified keys; serials retain all 12 hexadecimal characters, including trailing zeroes, and `fw=4.200` remains exactly that value. Repeated queries of unchanged state yield identical TXT content.
- [ ] **AC-06:** A mixed fleet advertises AAAA-only records for Thread devices and A-only records for WiFi devices, even when their records share a packet. Two distinct serials using one address remain two separately discoverable service instances.
- [ ] **AC-07:** Explicit per-device Thread addresses override concrete bind fallbacks; loopback is accepted; wildcard omission, blank or malformed overrides, wrong families and all link-local forms are rejected clearly. Equivalent IPv6 text representations encode the same address. No wildcard or invalid address reaches an advertised record.
- [ ] **AC-08:** Direct matching-family hostname queries return the advertised address. Opposite-family queries never produce an opposite-family address for that device, and completed removal/opt-out leaves no advertised address for it.
- [ ] **AC-09:** Successful add/remove/re-add operations are reflected by the next query, including an empty fleet, while both mDNS and the existing WebSocket listener observe the lifecycle events. Duplicate serial rejection retains the original device and does not create a second advertisement.
- [ ] **AC-10:** Injected mDNS startup failure causes Thread-only and mixed-fleet startup to fail and clean up. The same failure with WiFi-only devices leaves LIFX discovery/control functioning and exposes the mDNS failure. Explicitly disabled core mDNS is not treated as a failure.
- [ ] **AC-11:** Repeated start/stop, partial-start failure and function-scoped event-loop teardown leave no mDNS sockets, pending owned tasks or duplicate listener registrations. A query overlapping a device change does not emit a partial record set for a device; the next query after completion reflects that change.
- [ ] **AC-12:** The spike records its time box and candidate version plus evidence for every MDNS-10 criterion, makes an explicit go/no-go decision before responder construction, and distinguishes untested packaging/platform claims from demonstrated results.
- [ ] **AC-13:** Focused datagram-injection and actual multicast integration tests pass on Ubuntu/macOS; simulated Windows socket behaviour is identified as simulation. Tests prove `lifx-async` discovers the entire eligible fleet with the candidate's packet grouping, including a fleet whose complete records exceed one datagram. Skips and unavailable environments are explicitly reported.

## Edge Coverage

**Coverage:** 46/46 applicable review rows resolved; 0 unresolved; all resolutions use explicit acceptance criteria.

Both engine runs are retained in this union: the initial roadmap wording and the final specification wording. Initial provisional MDNS-12 (opt-in) maps into MDNS-01; MDNS-13 (wildcard policy) maps into MDNS-06. Manual-review rows are resolved against the concrete criteria rather than silently discarded, and manually identified numeric, encoding and lifecycle edges are included. Routine implications of complete-fleet discovery and existing identity/metadata requirements do not introduce an additional fleet limit or packet ordering guarantee.

| Category | Requirement | Status | Verification | Resolution |
|----------|-------------|--------|--------------|------------|
| concurrency | MDNS-01 | resolved | explicit | AC-01/02/11: opt-in reception, daemon coexistence and no duplicate listener across repeated lifecycle operations. |
| idempotency | MDNS-01 | resolved | explicit | AC-01/02/11: opt-in reception, daemon coexistence and no duplicate listener across repeated lifecycle operations. |
| unclassified | MDNS-01 | resolved | explicit | AC-01/02/11: opt-in reception, daemon coexistence and no duplicate listener across repeated lifecycle operations. |
| adjacency | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| boundary | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| concurrency | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| empty | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| idempotency | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| ordering | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| precision | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| unclassified | MDNS-02 | resolved | explicit | AC-03/04: each query retains its own source and ID; TTL is positive and at most 10; zero eligible devices means no device replies; reply ordering does not alter destination or metadata. |
| adjacency | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| boundary | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| concurrency | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| empty | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| ordering | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| precision | MDNS-03 | resolved | explicit | AC-04/06/11: zero, one and multiple complete device record sets, independent of packet grouping; shared addresses do not merge identities; actual bound port is preserved; overlapping changes never yield half a device record set. |
| adjacency | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| empty | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| encoding | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| idempotency | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| ordering | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| precision | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| unclassified | MDNS-04 | resolved | explicit | AC-05: exactly four fields, exact serial and integer firmware representation, identical TXT content for repeated queries of unchanged state. |
| adjacency | MDNS-05 | resolved | explicit | AC-04/06: exactly one matching-family address per advertised device, including shared addresses; no record for absent devices; verify sets independently of packet order. |
| empty | MDNS-05 | resolved | explicit | AC-04/06: exactly one matching-family address per advertised device, including shared addresses; no record for absent devices; verify sets independently of packet order. |
| ordering | MDNS-05 | resolved | explicit | AC-04/06: exactly one matching-family address per advertised device, including shared addresses; no record for absent devices; verify sets independently of packet order. |
| unclassified | MDNS-05 | resolved | explicit | AC-04/06: exactly one matching-family address per advertised device, including shared addresses; no record for absent devices; verify sets independently of packet order. |
| adjacency | MDNS-06 | resolved | explicit | AC-07: override precedes concrete fallback; missing wildcard override fails; equivalent IPv6 spellings encode identically; invalid addresses never enter a reply; shared addresses remain allowed. |
| concurrency | MDNS-06 | resolved | explicit | AC-07: override precedes concrete fallback; missing wildcard override fails; equivalent IPv6 spellings encode identically; invalid addresses never enter a reply; shared addresses remain allowed. |
| empty | MDNS-06 | resolved | explicit | AC-07: override precedes concrete fallback; missing wildcard override fails; equivalent IPv6 spellings encode identically; invalid addresses never enter a reply; shared addresses remain allowed. |
| encoding | MDNS-06 | resolved | explicit | AC-07: override precedes concrete fallback; missing wildcard override fails; equivalent IPv6 spellings encode identically; invalid addresses never enter a reply; shared addresses remain allowed. |
| ordering | MDNS-06 | resolved | explicit | AC-07: override precedes concrete fallback; missing wildcard override fails; equivalent IPv6 spellings encode identically; invalid addresses never enter a reply; shared addresses remain allowed. |
| unclassified | MDNS-07 | resolved | explicit | AC-08: direct queries resolve the advertised family and address; removal/opt-out removes the advertised lookup result. |
| adjacency | MDNS-08 | resolved | explicit | AC-09/11: duplicate serial rejection preserves identity; remove-last leaves an empty set; completed changes appear on the next query; both listeners retain their events. |
| concurrency | MDNS-08 | resolved | explicit | AC-09/11: duplicate serial rejection preserves identity; remove-last leaves an empty set; completed changes appear on the next query; both listeners retain their events. |
| empty | MDNS-08 | resolved | explicit | AC-09/11: duplicate serial rejection preserves identity; remove-last leaves an empty set; completed changes appear on the next query; both listeners retain their events. |
| idempotency | MDNS-08 | resolved | explicit | AC-09/11: duplicate serial rejection preserves identity; remove-last leaves an empty set; completed changes appear on the next query; both listeners retain their events. |
| ordering | MDNS-08 | resolved | explicit | AC-09/11: duplicate serial rejection preserves identity; remove-last leaves an empty set; completed changes appear on the next query; both listeners retain their events. |
| concurrency | MDNS-09 | resolved | explicit | AC-10/11: failure policy depends on Thread membership; partial startup, repeated stop/start and loop teardown release owned resources. |
| idempotency | MDNS-09 | resolved | explicit | AC-10/11: failure policy depends on Thread membership; partial startup, repeated stop/start and loop teardown release owned resources. |
| unclassified | MDNS-09 | resolved | explicit | AC-10/11: failure policy depends on Thread membership; partial startup, repeated stop/start and loop teardown release owned resources. |
| boundary | MDNS-10 | resolved | explicit | AC-12: record the time box, exact candidate version, criterion-by-criterion evidence and decision before construction; untested results cannot masquerade as demonstrated results. |
| precision | MDNS-10 | resolved | explicit | AC-12: record the time box, exact candidate version, criterion-by-criterion evidence and decision before construction; untested results cannot masquerade as demonstrated results. |
| unclassified | MDNS-10 | resolved | explicit | AC-12: record the time box, exact candidate version, criterion-by-criterion evidence and decision before construction; untested results cannot masquerade as demonstrated results. |
| unclassified | MDNS-11 | resolved | explicit | AC-13: repeated tests retain platform/evidence distinctions; a skipped integration check is not a pass. |

## Prohibitions (must-NOT)

**Coverage:** 0 applicable bespoke prohibitions; 0 unresolved.

The two-stage prohibition pass considered silent default enablement, unwanted interface selection, wrong device identity, stale records, omitted devices, socket leaks, listener displacement, false test evidence, data disclosure and interference with host discovery. The phase-specific items are functional correctness and lifecycle concerns already covered by the requirements and edge criteria; no additional values/ethics prohibition survives the precision filter. Generic network-security concerns belong to security review and `$gsd-secure-phase`, not a duplicate prohibition invented here.

## Ambiguity Report

| Dimension | Score | Minimum | Status | Notes |
|-----------|-------|---------|--------|-------|
| Goal clarity | 0.95 | 0.75 | Met | Per-device discovery outcome explicit |
| Boundary clarity | 0.95 | 0.70 | Met | Core defaults and later app phases separated |
| Constraint clarity | 0.90 | 0.65 | Met | Address policy and conditional failure agreed |
| Acceptance criteria | 0.875 | 0.70 | Met | Falsifiable checks; spike retains implementation choices |
| **Ambiguity** | **0.075** | **≤ 0.20** | **Passed** | 1 − (0.35×0.95 + 0.25×0.95 + 0.20×0.90 + 0.20×0.875) |

Initial scores were 0.90 / 0.80 / 0.65 / 0.80 (ambiguity 0.195, displayed as 0.20). After the first answers they were 0.90 / 0.90 / 0.85 / 0.85 (ambiguity 0.12; the conversation's 12.3% was an arithmetic error). The user approved proceeding through the gate. The final scores incorporate the per-device correction and failure/address answers.

## Interview Log

| Round | Perspective | Question | Decision locked |
|-------|-------------|----------|-----------------|
| 1 | Researcher | Core versus app default? | Core opt-in; app default-on belongs to Phase 4 |
| 1 | Researcher | Wildcard bind advertisement? | Require an explicit address; no interface selection |
| 1 | Workspace scope | Existing modified files? | Leave `.gitignore` and `.planning/config.json` untouched |
| Gate | Clarity check | Proceed through the specification gate? | Yes |
| 2 | Failure analyst | Whole-fleet reply and size restriction? | Historical decision: user challenged the whole-fleet premise and selected one reply per device. Superseded on 2026-09-23 by complete-fleet discovery independent of packet grouping |
| 3 | Failure analyst | Is enabled mDNS startup failure fatal? | Only when Thread devices are configured; WiFi-only may continue |
| 3 | Boundary keeper | Loopback allowed; all link-local rejected? | Yes, including rejection of scoped link-local addresses |

The previously suggested blanket silence for all malformed/unknown queries and expanded standard-port query behaviour were not explicitly approved as additional requirements. This specification retains the original query scope and does not claim those proposals were agreed. Protocol-level details remain for research and discuss-phase within this scope.

---

*Phase: 03-mdns-responder*
*Next step: $gsd-discuss-phase 3 — implementation decisions within these requirements.*
