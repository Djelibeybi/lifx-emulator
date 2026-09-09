# Feature Landscape: Thread Device Emulation

**Domain:** LIFX LAN protocol emulator — Thread/mDNS emulation addendum
**Researched:** 2026-09-09
**Confidence:** HIGH for wire-format/client-parsing claims (all cite `lifx-async` source lines or committed hardware evidence); MEDIUM for real-bulb/border-router behaviour not directly observable from client code (marked inline); LOW/speculative items are explicitly flagged and excluded from table stakes.

## Method note

`lifx-async` is both the reference client and, per PROJECT.md, "the acceptance oracle" for this milestone. Because its test fixtures encode exactly what it accepts or rejects, this document treats its parsing code as ground truth for wire format and its `docs/user-guide/discovery.md` + Phase 14 interim results as ground truth for real-hardware behaviour. Where a claim is inferred rather than directly observed on hardware, it says so.

---

## Table Stakes

Features the emulator must have to be a credible Thread stand-in for `lifx-async` (and, by extension, any DNS-SD-based LIFX client). Grouped by the categories that should become `REQUIREMENTS.md` sections.

### Connectivity (device model)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-device `connectivity: wifi \| thread` field | `lifx-async`'s `_LifxServiceRecord.connectivity` and `Device.connectivity` are first-class, and `Connectivity.THREAD` is only reachable via `tm=2` — every consumer branches on it (`hass-lifx-async-beta/.../sensor.py:41` skips the RSSI sensor entirely for non-WiFi) | Low | Already scoped in PROJECT.md Active requirements; matches `advertised_services` precedent |
| Setting `connectivity=thread` implies firmware major.minor `4.200` unless a scenario overrides it | `_LifxRecordCache._resolve_txt_metadata` treats `fw` as an independent, freely-settable TXT field with no coupling to `tm`, so real coupling is a LIFX firmware-line fact, not a client-parsing fact — MEDIUM confidence, sourced from PROJECT.md's own stated decision rather than `lifx-async` code | Low | Already decided in PROJECT.md; emulator-side default only |
| Thread devices never answer IPv4 or tagged/broadcast traffic | `lifx-async/docs/user-guide/discovery.md:129-144` and Phase-14 evidence: "Thread bulbs have no IPv4 address and do not answer IPv4 broadcast"; `discover_udp()`'s broadcast leg is explicitly a UDP/IPv4 path the client does not expect Thread devices to answer | Medium | Requires per-packet transport-origin check in the device/manager layer, not just a config flag |

### Header (wire format)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Frame-address flags byte 22, bit 3 = `thread_connection`, set on every reply from a Thread device | `header.py:144,150-153` (client's own hand-written header): flags byte layout is `res_required(bit0) \| ack_required(bit1) << 1 \| reserved(bit2) \| thread_connection(bit3) << 3`; client never *sets* it on send, only reads it on receive — "the flag is a device-side report, not a client assertion" (`header.py:147-149`) | Low | Emulator's own `header.py` is hand-written per CLAUDE.md, so this is a straightforward bit addition matching the existing `pack()`/`unpack()` shape |
| Bit set on **every** reply type, including acks (type 45) and StateUnhandled (223) | Phase-14 hardware evidence: `thread_connection` was `true` on all 800/800 request trials including acknowledgements — this is not scoped to State* replies only | Low | Already an Active requirement in PROJECT.md; the "including acks and StateUnhandled" phrasing there is correctly scoped from this evidence |
| No other header field changes; this is the only client known to read the bit | Searched only `lifx-async`'s own header/connection code for readers of bit 3; no other client in the required-reading set (aiolifx, photons, lifxlan, HA integration) was shown reading a header bit for Thread — HA's integration keys off `Connectivity` from the *library*, not the wire, per `sensor.py:5,41-42` | — | Do not invent additional bit semantics; PROJECT.md correctly scopes "new packet types" as out of scope |

### Transport (IPv6 socket)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Native `AF_INET6` `IPV6_V6ONLY=1` socket bound alongside the existing IPv4 socket, port 56700 | `lifx-async/.planning/.../PROJECT.md` context: "IPV6_V6ONLY must be set before bind (macOS raises EINVAL afterwards)... Windows defaults V6ONLY=1, Linux and macOS default to dual-stack" — this is the reason a second explicit socket beats a single dual-stack `::` bind | Medium | Server today opens one `create_datagram_endpoint(local_addr=...)` (`server.py:515-520`); this needs a second endpoint using the same `LifxProtocol`/`DeviceManager`, default bind `::1`, configurable |
| Default IPv6 bind address `::1`, overridable | Mirrors existing precedent — `lifx-async/tests/test_api/test_ipv6_e2e.py` already exercises the emulator bound to `::1` via a client-side subclass (`_Ipv6EmulatedLifxServer`, `conftest.py:302`) that this milestone should retire by making the bind native | Low | |
| Thread devices process a packet only if received on the IPv6 socket, addressed to their serial, `tagged=0` | Same hardware/behaviour basis as the IPv4/broadcast-drop rule above; this is the flip side — unicast IPv6 only | Medium | Needs the socket/transport origin threaded down to per-device dispatch in `DeviceManager` |

### mDNS Responder — record set

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Answer PTR queries for `_lifx._udp.local` sent to IPv4 multicast `224.0.0.251:5353` | `lifx-async/src/lifx/const.py:72-78` (`MDNS_ADDRESS`, `MDNS_PORT`, `LIFX_MDNS_SERVICE`); `dns.py:346-365` `build_ptr_query()` builds exactly this query | Medium | Must join `224.0.0.251` multicast group (`IP_ADD_MEMBERSHIP`) to *receive* the query even though replies are unicast — see legacy-unicast note below |
| **Reply via legacy unicast to the query's source `(ip, port)`, not by multicast** | `lifx-async/src/lifx/network/discovery/mdns/transport.py:1-21`: the client sends from "a socket bound to one route-selected interface and an ephemeral port, which is what makes every query it sends a legacy unicast query under RFC 6762 section 6.7: responders answer straight back to that port instead of broadcasting the reply." The client's socket **"does not join the multicast group and does not receive unsolicited announcements"** (`docs/user-guide/discovery.md:112-118`) | Medium | **This is the single most load-bearing wire-format fact in this research.** A responder that only ever multicasts its answer back to `224.0.0.251:5353` will never be seen by `lifx-async`, because its transport never joins that group. The responder MUST `sendto()` the reply directly at the source `(ip, port)` of the received query. |
| PTR record: `_lifx._udp.local` → `<instance>._lifx._udp.local` | `dns.py` `DNS_TYPE_PTR = 12`; `_is_lifx_service_instance()` (`discovery.py:163-169`) requires the owner name to be exactly `<non-empty-label>._lifx._udp.local` (case-insensitive, trailing dot stripped) — anything else (`prefix_lifx._udp.local`, `_lifx._udp.local` itself, trailing suffixes) is rejected by the client's own test suite (`test_discovery.py:222-237`) | Low | Instance label is otherwise free-form on the wire; a stable convention (e.g. serial-based, `d073d5xxxxxx._lifx._udp.local`) is sensible but not mandated by the client |
| SRV record: instance → `(priority=0, weight=0, port=56700, target=<hostname>.local)` | `dns.py` `SrvData` fields; `discovery.py:675-697` `_resolve_srv_endpoint()` requires every live SRV RR for an instance to agree on `(target, port)` or the instance is unresolved; `validate_port()` is applied to the port | Low | Port should be the emulator's actual bound port (usually 56700, but CLI supports a custom port) |
| A record for WiFi devices, AAAA record for Thread devices, keyed by the SRV target hostname | Active requirement in PROJECT.md, matches `_pick_address()` class ordering (`discovery.py:215-243`): IPv4 > ULA > GUA > scoped link-local. Test fixtures explicitly exercise `test_resolve_ipv6_aaaa_record` and `test_resolve_prefers_ipv4_over_ipv6` (`test_discovery.py:741-789`) | Low-Medium | A WiFi device only needs an A record; a Thread device only needs an AAAA record — do not emit both for one device (mixing them is legal on the wire but not representative of a real bulb and dilutes the emulator's fidelity value) |
| TXT record keys `id=<12-hex-serial>`, `p=<product-id>`, `fw=<major.minor>`, `tm=1\|2` | `discovery.py:172-195` (`_connectivity_from_txt`, `_validate_txt_id`) and `_resolve_txt_metadata` (`discovery.py:607-673`) define the exact accepted shapes: `id` must be exactly 12 lowercase/uppercase hex chars decoding to a 6-byte unicast (not broadcast, not all-zero/all-ff) MAC; `p` must parse as `int`; `fw` is a free string (only meaningfully consumed as `major.minor` by `_parse_firmware_components`, `discovery.py:1322-1329`); `tm` maps to `Connectivity.THREAD` **iff the value is the exact string `"2"`** — every other value (`"1"`, `"0"`, `"02"`, `" 2"`, `"thread"`, missing) maps to WiFi (`test_discovery.py:1237-1247`, `_connectivity_from_txt`) | Low | `tm` is a strict sentinel-string match, not a general enum — do not accept synonyms |
| TXT consensus: within one instance, every repeated TXT RR/value for `id`/`p`/`fw`/`tm` must agree, or the instance is unresolved | `discovery.py:607-673` and the whole `TestLifxRecordCache` conflict-detection suite (`test_discovery.py:430-680`) | — | This is a *client acceptance* rule, not something the emulator needs to implement — but it means the emulator must emit **consistent** TXT content across any repeated/refreshed announcements, or a real client (this one) will silently drop the device |
| One instance per device; a border-router-style responder can pack many instances (TXT+SRV+address for each) into a single reply packet | `test_discovery.py:791-822` `test_resolve_multi_instance_packet`, and `discovery.py`'s doc comment on `_LifxRecordCache`: "a Thread border router advertises every device on its mesh at once" | Medium | For an emulator hosting N devices, one PTR query response can (and, to be representative of a real Thread border router, arguably should) answer with records for every currently-advertised device in one packet |
| Address records may be split across multiple response packets if a batched reply exceeds a practical payload size ("overflow") | `test_discovery.py:823-855` `test_multi_instance_unresolvable_not_misattributed`: an instance's TXT/SRV can appear in one packet while its AAAA arrives later or not at all; the client's `pending_targets()` mechanism sends bounded follow-up A/AAAA queries per hostname (max 2 attempts, ≤64 targets, `discovery.py:846-887`, `docs/user-guide/discovery.md:53-60`) | Medium-High | The emulator does not have to reproduce overflow to be usable (a small emulated fleet fits in one UDP packet), but should **support answering direct A/AAAA queries for a hostname** (`build_address_query`, `dns.py:368-389`) so that the client's follow-up path has something to talk to if a test deliberately forces overflow |

### mDNS Responder — TTL, cache-flush, class

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Records carry class `IN` (0x0001), optionally with the cache-flush bit (0x8000) set (`DNS_CLASS_UNIQUE`) | `dns.py:24-25`, `cache_flush` property (`dns.py:136-139`) | Low | `transport.py:19-20` states explicitly: "cache-flush semantics do not apply to these replies" for the client's legacy-unicast leg — the client neither requires nor penalises the cache-flush bit on unicast replies. Setting it (as a real bulb likely does per mDNS convention for its own unique records) is harmless but not load-bearing for `lifx-async` |
| TTL value on records | `test_discovery.py` fixtures use `ttl=120` throughout as the working default; the client's cache also honours `ttl=0` as an RFC 6762 "goodbye" (immediate-expiry) signal (`discovery.py`'s `_add_record`: `if record.ttl == 0: ... expires_at = time.monotonic() + 1.0`) | Low | 120s is a safe, representative default. Do not emit `ttl=0` for a live/present device — that is specifically the goodbye/removal signal and doing so on a healthy device would make the client immediately treat it as gone |
| Sending a `ttl=0` "goodbye" record when a device is removed/powered off via the API | Direct implication of the goodbye-handling code above; matches real Bonjour/mDNS-SD convention (RFC 6762 §10.1) | Low-Medium | Not explicitly required by PROJECT.md's Active list, but cheap to add and materially improves fidelity for API-driven device removal/toggling tests — see Differentiators below for the fuller version |

### Configuration & Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `connectivity` settable via core factories, CLI flag, YAML `DeviceDefinition`, device-create API | Explicit Active requirement, matching the `advertised_services` (PR #156) precedent already in the codebase for a per-device network setting spanning factories/config/API | Low-Medium | Follow the exact same touch-points `advertised_services` used |
| `connectivity` persisted with device state, exposed read-only via device-info API and `export-config` | Explicit Active requirement | Low | `DeviceState`'s `NetworkState` group (holds `wifi_signal`) is the natural home per PROJECT.md's own architecture note |
| mDNS advertisement on by default for all devices; opt-out only for WiFi devices | Explicit Active requirement + real-world justification: WiFi devices are also discoverable over IPv4 UDP broadcast, so disabling mDNS for a WiFi device is a realistic test scenario (network segmented from multicast, etc.); Thread devices have no other discovery path so disabling would make them permanently invisible, which is not representative of any real deployment | Low | |
| Observing mDNS activity (queries received, responses sent, TXT/records emitted) in the existing WebSocket activity log | Not explicitly in PROJECT.md's Active list, but the existing activity-stream architecture (`server.py`'s `activity_observer`) is a stated integration point, and mDNS traffic is otherwise invisible compared to the LAN-protocol packets already logged — a Thread milestone that adds a whole new UDP responder without any observability regresses the existing UX bar for the rest of the tool | Low-Medium | Reuse the existing activity-event shape/sink rather than inventing a parallel logging path |

### Verification (acceptance criteria, not a shippable "feature" per se, but table stakes for the milestone to be considered done)

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| `lifx-async` can `discover_mdns()` an emulated Thread device, see `Device.connectivity == Connectivity.THREAD`, connect over IPv6, read/set colour and power, and observe `thread_connection` true on every reply | Verbatim from PROJECT.md's Active requirements — this is the milestone's own acceptance oracle | — |
| `GetWifiInfo` on a Thread device returns `StateWifiInfo` with signal `0.0`; `GetWifiFirmware` answers normally | PROJECT.md Active requirement + `hass-lifx-async-beta/.../sensor.py:38-44`: the HA integration's own comment states "The WiFi info packets do not describe a Thread radio, so a Thread device gets no signal sensor until LIFX documents the Thread equivalents" — i.e. the *client ecosystem's* expectation is that WiFi-info packets on Thread hardware are inert/zeroed, not that they error or go unhandled. No public evidence (hardware capture or LIFX docs) confirms the exact real-bulb wire response for `GetWifiFirmware`/`GetHostFirmware` on Thread beyond the firmware-version coupling already decided in PROJECT.md — treat "answers normally" as the pragmatic default absent contrary evidence | Low |

---

## Differentiators

Not required for the milestone's stated acceptance criteria, but each is a natural, low-risk extension of table-stakes work that would let the emulator exercise edge cases no other tooling currently covers. None of these should block the milestone; consider them backlog candidates.

| Feature | Value Proposition | Complexity | Notes |
|---------|--------------------|------------|-------|
| mDNS "goodbye" packet (TTL=0) on device removal/power-off via API | Lets a client test suite exercise prompt-removal behaviour distinctly from staleness/timeout behaviour, without waiting for any TTL expiry | Low-Medium | Builds directly on the TTL/cache-flush table-stakes work above |
| Configurable advertised IPv6 address per Thread device (beyond just the bind address) | Real Thread border routers advertise ULA/GUA addresses, not the bind loopback; letting a user set e.g. `fd00::1234` per device makes multi-device IPv6-class-selection tests (`_pick_address` ULA > GUA > link-local ordering) directly testable against the emulator instead of only against synthetic `lifx-async` unit fixtures | Low-Medium | The Active requirement already allows "the IPv6 bind or a configured advertise address" — this differentiator is simply making that per-device rather than global |
| Answering direct A/AAAA queries for a hostname (`build_address_query` shape) in addition to PTR | Exercises the client's `pending_targets()` follow-up path deliberately (e.g. a scenario that omits the address record from the initial PTR reply to force the follow-up) | Medium | Natural companion to the "batching/overflow" table-stakes item; can be scenario-gated |
| Scenario-engine hook for mDNS: e.g. `drop_mdns_response`, `malformed_txt`, `conflicting_txt_field` | The existing scenario engine already has `drop_packets`, `malformed_packets`, `invalid_field_values` for the LAN protocol; mirroring the same fault-injection philosophy for mDNS responses would let a client test its own TXT-consensus rejection paths (`test_discovery.py`'s entire `test_construction_metadata_conflict_*` suite) against a live emulator instead of only synthetic unit fixtures | Medium-High | Highest-value differentiator for `lifx-async` specifically, since that client has unusually strict TXT-consensus and conflict-detection logic worth testing end-to-end |
| Simulated multi-instance "border router" mode: one mDNS responder fronting several Thread devices in a single PTR reply, exercising the batching-into-one-packet behaviour explicitly | Matches `test_resolve_multi_instance_packet` shape; useful for testing a client's handling of a busy mesh | Medium | The emulator already manages multiple devices in one process, so this is largely "answer once per query with all currently-Thread-and-mDNS-enabled devices," not a new subsystem |
| CLI/dashboard visibility for "which devices are currently mDNS-advertised" (read-only, distinct from PROJECT.md's deferred create-form/badge UI work) | Small, complements the "observe mDNS activity in the activity log" table-stakes item without touching the dashboard scope PROJECT.md explicitly deferred | Low | Could be satisfied by the device-info API alone (already listing `connectivity`) plus the activity log — may not need dedicated UI at all |

---

## Anti-Features

Deliberately excluded from this milestone (some permanently, some just for now). Each maps to an existing PROJECT.md "Out of Scope" entry or is newly identified by this research; reasons are given so the roadmap can cite them.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|---------------------|
| Border-router staleness emulation (stale advertisement lingering ~70 min after device removal; ~69s reappearance delay after power-on) | Already Out of Scope in PROJECT.md. Phase-14 evidence is explicitly a **single-trial** observation ("Do not read 4200s as a lease... A single trial cannot distinguish a genuine 70-minute lease from the 2-hour default sampled mid-cycle") — there is no stable, reproducible timing contract to emulate, and baking a guessed constant into the emulator would give client developers false confidence in a number LIFX has never documented | If a future milestone wants this, model it as an explicit, user-configurable scenario delay (reusing the existing `response_delays` scenario shape) rather than a hardcoded "realistic" timer |
| Answering mDNS queries on the IPv6 multicast group `ff02::fb` | Already Out of Scope in PROJECT.md — confirmed correct by this research: `lifx-async`'s `MdnsTransport` (`transport.py`) is IPv4-only (`AF_INET`), sends only to `MDNS_ADDRESS = 224.0.0.251`, and there is no IPv6-mDNS code path anywhere in `discovery.py`/`dns.py`/`transport.py`/`const.py` to serve | Revisit only if a different target client (not `lifx-async`) is added as an acceptance oracle and it is shown to query `ff02::fb` |
| IPv6 multicast UDP discovery (tagged `GetService` over IPv6) | Already Out of Scope in PROJECT.md — confirmed: Phase-14 hardware evidence states Thread bulbs "do not answer IPv4 broadcast," and no evidence anywhere in the required reading shows a client sending a tagged `GetService` to an IPv6 multicast address; `lifx-async` reaches Thread devices exclusively via mDNS-discovered unicast IPv6 | If ever needed, it is additive to the existing IPv4 broadcast/tagged-`GetService` handling already in `server.py`/`devices/manager.py`, not new protocol work |
| Thread bandwidth/latency shaping (animation throttling, RTT modelling beyond the existing `response_delays` scenario) | Already Out of Scope in PROJECT.md, and reinforced by Phase-14 evidence: measured Thread ack p50 was 43.9ms — *lower* than the ~100ms WiFi-under-load figure the project's own v1.1 spike series assumed — so there is no validated "Thread is slower" model to encode. The one animation-throughput measurement attempted (THREAD-03) was explicitly disowned by the source document as methodologically unsound (identical, zero-brightness frames that let firmware short-circuit real work) | The existing generic `response_delays` scenario already lets a user model arbitrary latency per device/type/location/group/global — sufficient without inventing a Thread-specific model |
| Multi-mesh/multi-border-router topology simulation (more than one responder identity, per-mesh network partitioning) | Not requested by PROJECT.md and not evidenced as something any of the four target clients (`lifx-async`, `aiolifx`, `photons`, `lifxlan`) or the HA integration test against; adds significant complexity (responder identity, mesh membership, partition semantics) for no demonstrated consumer need | The single-responder-answers-for-everything model (one process, N devices, one mDNS responder advertising all of them) already satisfies the "border router packs many instances into one reply" table-stakes item without multi-mesh complexity |
| Returning `StateUnhandled` for WiFi-info packets (`GetWifiInfo`/`GetWifiFirmware`) on Thread devices | Already Out of Scope / explicitly rejected in PROJECT.md's Key Decisions, and validated by this research: the HA integration's own code comment (`sensor.py:38-42`) frames the real-world expectation as "packets... simply do not describe a Thread radio" (i.e. answered but empty/zeroed), not "unsupported command." Returning `StateUnhandled` would train client authors to write unsupported-command handling for a case real bulbs (per the ecosystem's working assumption) do not exercise that way | Zero-signal `StateWifiInfo` as already decided |
| New Thread-specific packet types | Already Out of Scope in PROJECT.md: "the public protocol.yml (checked 2026-09-09) defines no Thread-specific packets; only the header bit and mDNS metadata differ" — confirmed independently: nothing in `lifx-async`'s `packets.py`/`protocol/` namespace references Thread beyond the header bit and TXT metadata already covered above | N/A — no gap to fill |
| Emitting the mDNS cache-flush bit as a hard requirement / relying on it for correctness | Not requested, and this research shows it would be a wasted effort: `transport.py:19-20` states plainly that "cache-flush semantics do not apply to these replies" for the client's legacy-unicast discovery leg, because that socket keeps no long-lived cache across calls | Set the bit for cosmetic realism if convenient (harmless), never gate any emulator behaviour on it |
| Product-level Thread gating in `specs.yml` | Already Out of Scope in PROJECT.md — user chose per-device configuration; `products.json` carries no Thread flag and there is no ecosystem evidence that Thread capability is fixed per product model rather than per unit/firmware | Per-device `connectivity` field only, as already decided |

---

## Feature Dependencies

```
IPv6 native socket bind (Transport)
  └─→ Thread unicast-only packet filtering (Connectivity)
        └─→ thread_connection header bit set on Thread device replies (Header)
              └─→ end-to-end verification: lifx-async controls a device over IPv6 (Verification)

per-device connectivity field (Connectivity: factories/CLI/YAML/API/persistence)
  └─→ mDNS TXT tm=1|2 emission (mDNS)
  └─→ AAAA-vs-A record selection per device (mDNS)
  └─→ GetWifiInfo zero-signal / firmware 4.200 behaviour (Connectivity → Header/handlers)

mDNS responder: join 224.0.0.251 + receive PTR query (mDNS)
  └─→ legacy-unicast reply to query source (mDNS) — MUST come before any TXT/SRV/address
      work has value, since a multicast-only reply is invisible to lifx-async
  └─→ PTR + SRV + TXT + address record assembly per device (mDNS)
        └─→ multi-instance packing into one reply (mDNS, table stakes at small scale)
              └─→ overflow / split-packet + address follow-up support (mDNS, differentiator threshold)

mDNS advertisement toggle (Configuration)
  └─→ depends on per-device connectivity field existing first (Thread devices cannot be toggled off)

activity-log visibility for mDNS (Configuration)
  └─→ depends on the mDNS responder existing and reusing the existing activity_observer sink
```

---

## MVP Recommendation

Prioritise, in this order (mirrors the "Horizontal layers" roadmap structure already chosen in PROJECT.md's Key Decisions — core library, then CLI/config, then API):

1. **Header bit + connectivity field on `DeviceState`** — cheapest, unblocks everything else, matches existing `advertised_services` pattern.
2. **Native IPv6 socket + unicast-only Thread packet filtering** — the second-most load-bearing change; without it, "control a Thread device over IPv6" (the milestone's stated core value) is impossible regardless of mDNS.
3. **mDNS responder with correct legacy-unicast reply semantics** — this is the item most at risk of being built wrong in a way that looks correct in isolation (a naive implementation that multicasts its answer back to `224.0.0.251:5353` will pass a manual `dns-sd`/`avahi-browse` smoke test but silently fail every `lifx-async` `discover_mdns()` call, because that client's socket never joins the multicast group). Build the legacy-unicast reply path first and write the acceptance test against `lifx-async` itself before anything else in the mDNS layer.
4. **TXT record correctness (`id`/`p`/`fw`/`tm`) and A/AAAA-per-connectivity** — straightforward once the reply path works; validate directly against `_LifxRecordCache._resolve_txt_metadata`'s acceptance rules (exact 12-hex serial, exact `tm=2` sentinel).
5. **CLI/YAML/API/persistence surfacing of `connectivity`** — same shape as prior work, low risk.
6. **mDNS opt-out for WiFi + activity-log visibility** — polish layer, no new wire-format risk.

Defer (Differentiators section): mDNS goodbye packets, per-device advertised-address configuration beyond the bind default, scenario-engine hooks for mDNS fault injection, and multi-instance/overflow batching beyond what a small emulated fleet naturally produces. None of these block `lifx-async` proving Thread discovery + control against the emulator; all are cheap to layer on afterward given the dependency chain above.

## Sources

- `/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/PROJECT.md` — milestone scope, decisions, hardware-facts summary (context, confirmed against primary sources below)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/tests/test_network/test_mdns/test_discovery.py` — TXT/record acceptance fixtures, border-router multi-instance test, connectivity-sentinel tests (lines 44-70, 430-680, 741-855, 1230-1297) — HIGH confidence, primary source
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/network/discovery/mdns/discovery.py` — client parsing rules: `_is_lifx_service_instance`, `_connectivity_from_txt`, `_validate_txt_id`, `_pick_address`, `_LifxRecordCache` (lines 163-243, 553-948) — HIGH confidence, primary source
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/network/discovery/mdns/dns.py` — DNS wire format: record types, TTL/cache-flush, query builders (lines 1-390) — HIGH confidence, primary source
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/network/discovery/mdns/transport.py` — legacy-unicast reply requirement, no multicast-group join (lines 1-21, 64-77) — HIGH confidence, the single most load-bearing finding in this document
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/protocol/header.py` — `thread_connection` bit layout, pack/unpack (lines 119-225) — HIGH confidence, primary source
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/const.py` — `MDNS_ADDRESS`, `MDNS_PORT`, `LIFX_MDNS_SERVICE` (lines 71-78) — HIGH confidence
- `/Volumes/External/Developer/Djelibeybi/lifx-async/docs/user-guide/discovery.md` — consumer-facing Thread/mDNS behaviour, staleness caveats, limitations (lines 1-196) — HIGH confidence for client behaviour; MEDIUM for the single-trial hardware staleness figures it reports
- `/Volumes/External/Developer/Djelibeybi/lifx-async/.planning/milestones/v2.0-phases/14-thread-revalidation-and-docs/14-INTERIM-RESULTS.md` — physical hardware evidence: thread bit 800/800, ack RTT distribution, staleness single-trial caveats, animation methodology disowned — MEDIUM confidence (explicitly single-trial/single-fleet, flagged as such throughout the source document itself)
- `/Volumes/External/Developer/Djelibeybi/hass-lifx-async-beta/custom_components/lifx/sensor.py` (lines 1-60) — ecosystem expectation that WiFi-info packets are inert (not "unsupported") on Thread devices — HIGH confidence for what this consumer does, MEDIUM confidence as evidence of real-bulb wire behaviour (it is the client author's stated assumption, not a hardware capture)
- `/Volumes/External/Developer/Djelibeybi/lifx-emulator/packages/lifx-emulator-core/src/lifx_emulator/server.py` (lines 490-535) — existing single-socket `create_datagram_endpoint` shape the IPv6 socket work extends — HIGH confidence, primary source, current codebase
