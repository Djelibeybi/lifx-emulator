---
phase: "03"
slug: mdns-responder
status: blocked
threats_open: 1
asvs_level: 1
block_on: high
created: "2026-09-23"
---

# Phase 3 — Security

**Reopened 2026-09-23:** Current T-03-21 receive-interface isolation is OPEN (high). A Linux reproduction confirms that zeroconf can answer through a non-selected interface. The prior L1 presence check did not establish that boundary. See `03-REVIEW-FOLLOWUP.md`. No new risk acceptance or private socket modification has been authorised. The earlier audit below is retained as historical evidence.

L1 presence audit by the gsd-security-auditor subagent at implementation head `721601a`. All 32 plan-scoped rows resolved: 27 mitigations present and five previously documented accepted dispositions. Five rows belong to halted/superseded 03-01 and are historical controls, not a current direct-responder requirement. No new risk acceptance is introduced here.

Production short paths below resolve under `packages/lifx-emulator-core/src/lifx_emulator`; test short paths under `packages/lifx-emulator-core/tests`; `event_bridge.py` under `packages/lifx-emulator/src/lifx_emulator_app/api/services`. Phase document paths are relative to this directory.

## Trust Boundaries

| Boundary | Data crossing |
|---|---|
| LAN datagrams → zeroconf | Untrusted DNS queries and responses |
| Factory/bind inputs → immutable state → LAN records | Public synthetic identity, selected address and endpoint |
| Device manager → listeners → responder/WebSocket | Committed membership snapshots and callbacks |
| Public dependency operations → server lifecycle | Owned asynchronous operations, failures and cleanup |
| Registry/client checkout/CI → selection and verification | Exact pinned source, lock hashes and platform evidence |

## Threat Register

| Plan / Threat ID | Category | Component | Severity | Disposition | Mitigation | Status | Evidence |
|---|---|---|---|---|---|---|---|
| 03-01/T-03-01 | Spoofing/Tampering | DNS query/reply correlation | high | mitigate | Raw tests assert source destination, echoed ID/questions, record ownership, cache-flush and TTL per datagram. | closed (historical) | scripts/spike_mdns_candidates.py:375-448,658-660 |
| 03-01/T-03-02 | Denial of Service | Parser and candidate work | high | mitigate | Bounded malformed/truncated/flood cases, packet/record limits and zero pending work after close. | closed (historical) | scripts/spike_mdns_candidates.py:1254-1324 |
| 03-01/T-03-03 | Information Disclosure | Interface/TXT selection | high | mitigate | Explicit IPv4 interface only; assert TXT contains exactly public `id/p/fw/tm` and replies target the legacy-unicast source. | closed (historical) | scripts/spike_mdns_candidates.py:272-325,400-437 |
| 03-01/T-03-04 | Denial of Service | Lifecycle/thread ownership | medium | mitigate | Repeat open/close with socket, task and thread inventories before/during/after. | closed (historical) | scripts/mdns_spike_tests/test_candidates.py:611-657; scripts/spike_mdns_candidates.py:1280-1324 |
| 03-01/T-03-SC | Tampering | Candidate package and PyApp payload | high | mitigate | Official provenance, immutable commits, uv isolation, local-wheel hash/METADATA proof and non-publishing CI artefacts. | closed (historical) | scripts/spike_mdns_candidates.py:2405-2422,2708-2835; .github/workflows/ci.yml:235-241,312-409 |
| 03-02/T-03-20 | Denial of Service | zeroconf datagram ingestion | high | mitigate | Fixed malformed/truncated corpus and 256-query pressure case must preserve a fresh valid query path, bounded completion and unchanged pending-task/thread inventory. | closed | scripts/spike_mdns_candidates.py:3014-3036,3155-3197,3488-3527 |
| 03-02/T-03-21 | Spoofing / Information Disclosure | interface and legacy-unicast routing | high | mitigate | Exact-head receipts retain explicit IPv4 interface, source/destination/query correlation and exact public TXT/address records. | OPEN — blocking | scripts/spike_mdns_candidates.py:2997-3000,3039-3052,3120-3151 |
| 03-02/T-03-22 | Tampering | candidate/version and historical evidence | high | mitigate | Validator checks official provenance, exact version/revision, SHA-256 inputs and candidate labels; direct-responder passes cannot fill zeroconf rows. | closed | scripts/spike_mdns_candidates.py:3654-3679,3802-3952 |
| 03-02/T-03-23 | Denial of Service | lifecycle operation failures | high | mitigate | Public-operation boundary tests require retained error identity, owned cleanup, blocked replacement after cleanup failure and explicit retry only. | closed | scripts/mdns_spike_inputs/zeroconf_recovery.py:40-138; scripts/mdns_spike_tests/test_recovery.py:134-216 |
| 03-02/T-03-24 | Denial of Service | silent listener loss | medium | accept | D-08 explicitly accepts nondetection for this test-oriented emulator; status text and the decision must avoid a network-health guarantee. | closed | 03-CONTEXT.md:58-61; 03-02-SUMMARY.md:88-90 |
| 03-02/T-03-SC | Tampering | isolated zeroconf distribution | high | mitigate | Resolve official PyPI/project provenance, pin exact isolated versions, measure drift before selection and leave project manifests/lockfile unchanged. | closed | scripts/spike_mdns_candidates.py:3436-3463,3730-3759,3910-3952; packages/lifx-emulator-core/pyproject.toml:10; uv.lock:1474-1482 |
| 03-03/T-03-03-01 | Denial of Service | `MdnsResponder` query path | high | mitigate | Use zeroconf's public parser, perform no per-query task allocation in emulator code, snapshot bounded device state once per registration/reconcile operation and cover malformed/empty input in focused tests. | closed | mdns.py:10-15,49-105,119-140; scripts/spike_mdns_candidates.py:3014-3197; test_mdns_responder.py:test_default_record_sets |
| 03-03/T-03-03-02 | Spoofing | legacy-unicast reply routing | medium | mitigate | Let zeroconf reply only to the observed query source for the legacy path and assert source, destination and query-ID affinity on raw datagrams. | closed | test_mdns_responder.py:test_tracer_legacy_unicast,raw_query |
| 03-03/T-03-03-03 | Information Disclosure | TXT and address records | low | accept | The emulator intentionally publishes serial/product/firmware/connectivity and selected endpoint only; no secrets or persistence paths enter ServiceInfo. | closed | 03-03-PLAN.md:176; mdns.py:71-92 |
| 03-03/T-03-03-SC | Tampering | `uv add` / PyPI distribution | high | mitigate | Require live latest-version equality with the human-approved 0.151.3 selection, mutate through uv only and verify the locked distribution before tests. | closed | packages/lifx-emulator-core/pyproject.toml:10; uv.lock:1474-1482 |
| 03-04/T-03-04-01 | Information Disclosure | advertised address fallback | high | mitigate | Reject wildcard and link-local fallback/overrides, require explicit addresses for wildcard binds and prohibit automatic interface enumeration. | closed | devices/states.py:91-103; server.py:1042-1044 |
| 03-04/T-03-04-02 | Tampering | factory address/family inputs | medium | mitigate | Parse and validate once before state construction, store canonical immutable intent and revalidate bind-dependent rules before membership. | closed | devices/states.py:91-135,494-509; factories/builder.py:348-401; server.py:655-667 |
| 03-04/T-03-04-03 | Spoofing | shared-address service identity | medium | mitigate | Key service instances by immutable 12-hex serial rather than address and test two serials sharing one address. | closed | mdns.py:77-105; test_mdns_responder.py:test_default_record_sets |
| 03-04/T-03-04-04 | Denial of Service | invalid live additions | low | mitigate | Reject before repository mutation, callbacks, persistence activation or zeroconf work allocation. | closed | server.py:655-667; test_mdns_config.py:81-86 |
| 03-05/T-03-05-01 | Denial of Service | lifecycle listener dispatch | medium | mitigate | Isolate/log each listener exception, use an immutable dispatch snapshot and preserve bounded async scheduling in the WebSocket bridge. | closed | devices/manager.py:192-214; event_bridge.py:226-249 |
| 03-05/T-03-05-02 | Tampering | listener add/remove during dispatch | medium | mitigate | Identity-deduplicate registrations and apply registry mutations only to future dispatch snapshots. | closed | devices/manager.py:181-205; test_device_manager.py:810-837 |
| 03-05/T-03-05-03 | Repudiation | failed membership mutation | low | mitigate | Emit no event until repository/storage commit succeeds and retain serial-labelled diagnostics for callback errors. | closed | devices/manager.py:236-242,259-280; test_device_manager.py:851-865 |
| 03-05/T-03-05-04 | Elevation of Privilege | custom listener | low | accept | Listeners are in-process library callbacks with no privilege boundary; exceptions are contained and no external code loading is introduced. | closed | 03-05-PLAN.md:167; devices/manager.py:181-214 |
| 03-06/T-03-06-01 | Denial of Service | lifecycle lock and failure handler | high | mitigate | Surface errors after responder locks release, schedule one handler, acquire server lock once and call locked helpers directly; add a deadlock regression test. | closed | mdns.py:142-153; server.py:917-935; test_mdns_lifecycle.py:123-149 |
| 03-06/T-03-06-02 | Tampering | overlapping membership generations | high | mitigate | Serialise immutable snapshot reconciliation, use monotonic generation/tail barriers and assert no stale re-add/partial publication. | closed | mdns.py:99-105,134-147,213-222; test_mdns_lifecycle.py:22-76 |
| 03-06/T-03-06-03 | Denial of Service | retained tasks/sockets/listeners | high | mitigate | Stop admission, remove listener, boundedly drain/cancel work, unregister and close idempotently across partial/repeated lifecycle paths. | closed | mdns.py:224-255; server.py:999-1020; test_mdns_lifecycle.py:152-241 |
| 03-06/T-03-06-04 | Repudiation | mDNS status/error | medium | mitigate | Retain the surfaced exception and log state transitions; define running as lifecycle state so unsupported health is never misreported. | closed | mdns.py:21-27; server.py:895-915; test_mdns_lifecycle.py:14-19,152-174 |
| 03-06/T-03-06-05 | Information Disclosure | automatic recovery/interface change | low | accept | No automatic retry or interface selection occurs; explicit retry reuses validated configured addresses only. | closed | 03-CONTEXT.md:58-61; mdns.py:124-126; server.py:1022-1037 |
| 03-07/T-03-07-01 | Spoofing | client oracle checkout | high | mitigate | Fetch detached pinned revision 48b7efbff59656499373b13ef17e3008d125feb5 and assert HEAD before importing/running it. | closed | scripts/prepare_mdns_oracle.py:10,25-50 |
| 03-07/T-03-07-02 | Repudiation | skipped/simulated evidence | high | mitigate | Required-mode job fails on missing prerequisites/skips and Windows test names/output explicitly record simulation. | closed | test_mdns_integration.py:20-24,40-65; .github/workflows/ci.yml:92-101; test_mdns_platform.py:1-12 |
| 03-07/T-03-07-03 | Information Disclosure | CI logs/artifacts | medium | mitigate | Assert protocol metadata only; do not record host interface inventories, secrets, physical addresses or cross-machine captures. | closed | test_mdns_integration.py:90-104,167-180; .github/workflows/ci.yml:38-101 |
| 03-07/T-03-07-04 | Denial of Service | 100-device integration | low | accept | Deterministic bounded test fleet runs in a dedicated path-filtered job; no performance threshold or unbounded generator is introduced. | closed | test_mdns_integration.py:107-119; .github/workflows/ci.yml:38-61 |

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---|---|---|---|---|
| AR-01 | T-03-24 | Silent listener loss may remain undetected; running is lifecycle state. | User-approved D-08 and 03-02 selection | 2026-09-23 |
| AR-02 | T-03-03-03 | LAN publication deliberately exposes synthetic serial, product, firmware, connectivity and selected endpoint. | Existing 03-03 plan disposition | 2026-09-23 |
| AR-03 | T-03-05-04 | Lifecycle listeners are trusted in-process callbacks with no privilege boundary. | Existing 03-05 plan disposition | 2026-09-23 |
| AR-04 | T-03-06-05 | No automatic retry or interface selection; recovery is explicit. | Existing plan and user-approved D-08 | 2026-09-23 |
| AR-05 | T-03-07-04 | Bounded 100-device CI integration has no performance threshold. | Existing 03-07 plan disposition | 2026-09-23 |

The already-approved zeroconf continuation-question exception remains in 03-CONTEXT.md:3-5 and 03-02-SUMMARY.md:88-90. It is an existing selection boundary, not a new acceptance.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Blocking Open | Run By |
|---|---|---|---|---|
| 2026-09-23 | 32 | 32 | 0 | gsd-security-auditor, ASVS L1 |

No SUMMARY Threat Flags or unregistered flags were found. This is a presence audit, not a general penetration test. Hosted functional CI is a separate gate. A subsequent test-only Python 3.10 fixture repair uses the public DatagramProtocol API and preserves the raw-wire assertions and owned socket cleanup; production mitigations are unchanged.

## Sign-Off

- [x] All threats have a declared disposition.
- [x] Previously accepted risks recorded.
- [ ] Zero blocking threats (Linux receive scope remains open).
- [ ] Revised implementation and receive boundary verified.

**Approval:** blocked pending T-03-21 resolution.
