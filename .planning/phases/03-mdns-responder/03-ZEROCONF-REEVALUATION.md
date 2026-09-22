# Zeroconf direct re-evaluation

**Date:** 2026-09-23 (Australia/Melbourne)
**Authorisation:** User approved the proposed direct 100-device experiment after the packet-grouping amendment. No local or CI harness changes.
**Result:** Complete-fleet discovery, record contents and representative control pass locally. Production selection remains provisional because a separate legacy-unicast question-echo issue and other evidence gaps remain.

## Inputs and method

- Emulator checkout: clean `594613d6a14edb69fc31b63c704a633957b51ab0` before recording these findings; stock core installed into a disposable uv environment.
- Zeroconf: `0.151.3`, confirmed as the latest PyPI release for this run.
- Pristine public client: `lifx-async` revision `48b7efbff59656499373b13ef17e3008d125feb5` (package version `7.3.0`), installed from that Git revision, with no responder overlay. Sibling checkout and its pre-existing `morph.py` were untouched.
- Runtime: Python 3.14.7, macOS 27.0, arm64. `mDNSResponder` remained running as `_mdnsresponder`; no daemon, route or network configuration was changed.
- Population: 50 stock WiFi and 50 stock Thread colour lights, serials `d073d8000000` through `d073d8000063`, on the stock server's same-port IPv4/IPv6 endpoints with port-zero allocation.
- Addresses: explicitly selected existing `en0` IPv4 and stable global IPv6 addresses. Actual local addresses are omitted from the committed report. This is same-host multicast and control evidence, not cross-machine evidence.
- Public `AsyncZeroconf`/`ServiceInfo` APIs registered all 100 service instances on the selected IPv4 interface. Thread records advertised only the selected IPv6 address; WiFi records advertised only IPv4. TXT was exactly `id`, `p=27`, `fw=4.200`, and `tm=1` or `tm=2`.
- A direct ephemeral-port PTR query collected replies for two seconds and parsed them with the pinned client's DNS parser. Record associations, exact TXT, matching address family/address, SRV target/port/priority/weight and PTR target were checked for all 100 identities.
- A separate public `discover_mdns(timeout=4, max_response_time=0.2, idle_timeout_multiplier=2, device_timeout=1, max_retries=1)` call checked discovery, addresses, ports and connectivity classifications. Representative WiFi and Thread devices then answered `get_power()`; their returned values matched the emulator state.
- Services were unregistered, zeroconf closed and the emulator stopped in `finally` cleanup. Only `MainThread` remained. This run did not measure pending tasks or socket counts and does not prove recovery or absence of every resource leak.

Execution used a disposable one-off script, not the existing harness:

```sh
uv run --isolated --no-project \
  --with ./packages/lifx-emulator-core \
  --with zeroconf==0.151.3 \
  --with 'lifx-async @ git+https://github.com/Djelibeybi/lifx-async.git@48b7efbff59656499373b13ef17e3008d125feb5' \
  python /tmp/lifx-zeroconf-direct-check.py
```

The temporary script's SHA-256 was `20f27bad9f3fc102f2e5fd50046aa2a46c620565ee62c856c6d49de744f95c4e`. It is a local experiment artefact, not a retained or CI-supported runner. The checked output is preserved in `03-ZEROCONF-REEVALUATION.json` (SHA-256 `d6ac73f9d41961624031ef98bceffc9c08cdc74f2b5830c320006e0c764f6e1e`). The original spike ledger and frozen inputs remain unchanged.

## Observations

| Check | Result |
| --- | --- |
| Complete PTR/SRV/TXT/address associations | 100/100 |
| Exact TXT and matching-family addresses | 100/100 |
| Public-client discovery | 100/100, no missing synthetic identities |
| Endpoint and connectivity classification | 100/100 correct |
| Public-client discovery elapsed time | 0.538357 seconds |
| Representative WiFi `get_power()` | 65535, matching emulator |
| Representative Thread `get_power()` | 65535, matching emulator |
| Raw reply datagrams | 12; 703–1459 bytes |
| Source port / query ID / cache-flush / TTL | All 12 used source 5353, echoed ID, cleared cache-flush and had positive TTL <=10 |
| Question count | First packet: 1; remaining 11 packets: 0 |

These are two local discovery observations, not a statistical performance study. The first invocation already discovered all 100 in 0.615110 seconds and passed both controls, but its separate raw query incorrectly passed a trailing dot to `build_ptr_query`, yielding no matching raw replies. Correcting that invocation to `build_ptr_query(SERVICE.rstrip("."))` produced the recorded second result. The initial raw failure is an experiment error, not candidate rejection. No harness file was edited to correct it.

## Remaining protocol issue

[RFC 6762 section 6.7](https://www.rfc-editor.org/rfc/rfc6762.html#section-6.7) requires a legacy-unicast response to repeat the query ID and question. The observed 11 continuation datagrams have no question section. The pinned client's successful discovery does not demonstrate conformance to that requirement.

The release's [DNSOutgoing.packets implementation](https://github.com/python-zeroconf/python-zeroconf/blob/0.151.3/src/zeroconf/_protocol/outgoing.py#L177-L247) advances `questions_offset` after the first packet and retains it when resetting for subsequent packets. This accounts for the observed question omission. No library patch, private hook or upstream report was made in this task. Resolving this library behaviour is the next technical investigation before a claim of complete legacy-unicast compliance; it must not be silently waived as part of the aggregation amendment.

## Assessment of the remaining gates

The old packet-count rejection is superseded, and zeroconf now has direct local evidence for the amended 100-device discovery requirement. Local coexistence also worked; the direct prototype's selected-address bind failure did not occur here.

The earlier zeroconf ledger contains useful local single-device wire, direct-address-query and cleanup observations. Its raw benchmark timings are not substituted for public-client benchmarks. The old Windows simulation label is not independently verified by this experiment. Exact candidate-specific hosted Ubuntu/macOS receipts and Intel PyApp packaging remain unproved for the revised decision; passing receipts for the direct prototype are not transferable. Dynamic membership, injected failure/retry, partial-start recovery and production status integration were not exercised here.

**Disposition:** Retain zeroconf as the preferred candidate for further targeted work. Do not claim a full go or restart fallback implementation based solely on this run. No production, dependency, test, harness or workflow file changed, and no CI evidence run was explicitly requested.
