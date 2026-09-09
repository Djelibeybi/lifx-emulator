# LIFX Emulator

## What This Is

A LIFX LAN protocol emulator for testing LIFX client libraries without real hardware. It implements the binary UDP protocol from https://lan.developer.lifx.com and emulates colour lights, multizone strips, matrix devices (Tile, Candle, Ceiling), infrared, HEV and switch products, with a scenario engine for fault injection, a FastAPI management API, a WebSocket activity stream and a Svelte dashboard. It ships as a core library (`lifx-emulator-core`, import `lifx_emulator`) and a standalone CLI/API app (`lifx-emulator`, import `lifx_emulator_app`) in one uv workspace.

This milestone adds **Thread emulation**: LIFX bulbs now ship firmware that runs the LAN protocol over Thread (IPv6, via a border router) instead of WiFi, and the emulator must be able to present a device the way a Thread bulb presents itself on the wire, so that `lifx-async` (the primary consumer) can exercise its Thread discovery and transport paths against the emulator instead of synthetic fixtures or physical hardware.

## Core Value

A LAN client library can discover and control an emulated Thread device exactly as it would a real one: found only over mDNS with an AAAA record, reachable only by IPv6 unicast, every reply carrying the Thread connection bit.

## Requirements

### Validated

<!-- Inferred from the existing codebase (.planning/codebase/ARCHITECTURE.md, STACK.md) and CLAUDE.md. -->

- ✓ Binary LAN protocol: 36-byte header pack/unpack, auto-generated packet classes for Device/Light/MultiZone/Tile namespaces, ack (type 45) and StateUnhandled (223) handling — existing
- ✓ Device emulation for colour lights, multizone (standard and extended), matrix/tile chains with 8 framebuffers, infrared, HEV, relays/switches and buttons — existing
- ✓ UDP broadcast discovery (GetService/StateService) over IPv4, including multi-service `advertised_services` advertisement (PR #156) — existing
- ✓ Product registry generated from LIFX products.json plus `specs.yml` product defaults; universal `create_device(product_id)` factory — existing
- ✓ Hierarchical scenario engine (device > type > location > group > global) with drop_packets, response_delays, malformed_packets, invalid_field_values, firmware_version, partial_responses, send_unhandled — existing
- ✓ Debounced async persistence of device state and scenarios — existing
- ✓ FastAPI management API (devices, scenarios, monitoring), WebSocket activity stream, Svelte 5 dashboard served from the app package — existing
- ✓ cyclopts CLI with YAML config file (CLI flag > `LIFX_EMULATOR_CONFIG` > auto-detect), `export-config`, `list-products`, `clear-storage` — existing
- ✓ CI on Python 3.10–3.14 across Ubuntu and macOS; PyApp standalone binaries for Linux, macOS and Windows — existing
- ✓ Every device has a `connectivity` of `wifi` (default) or `thread` held on a frozen `NetworkState`, settable through `create_device()` and every typed core factory, and persisted with device state (single-read restore) — Phase 1
- ✓ A Thread device sets frame-address flags bit 3 (`thread_connection`) on every reply header it emits — data replies, both ack paths, StateUnhandled, multi-packet and scenario-mutated replies — while a WiFi device's wire output stays byte-identical to the pre-phase fixtures — Phase 1
- ✓ A Thread device defaults to host firmware 4.200 with a floor (explicit value wins; below-floor raises `ValueError`); a product-level terminal-firmware ceiling in `specs.yml` rejects Thread on the original Tile with no product-ID literal in Python — Phase 1
- ✓ A Thread device answers GetWifiInfo with StateWifiInfo signal 0.0 and answers GetWifiFirmware and GetHostFirmware normally; matrix tiles report the host firmware — Phase 1

### Active

- [ ] `connectivity` is settable per device via the CLI flag, YAML config `DeviceDefinition` and the device-create API (core factories and persistence done in Phase 1)
- [ ] A Thread device processes a packet only if it arrived on the emulator's IPv6 socket and is addressed to its serial (`tagged=0`); IPv4 packets and tagged/broadcast packets addressed to it are silently dropped
- [ ] The emulator natively binds an IPv6 UDP socket (separate `AF_INET6` socket with `IPV6_V6ONLY=1`, default `::1`, configurable) alongside the existing IPv4 socket, on Linux, macOS and Windows, so `lifx-async` can retire its `_Ipv6EmulatedLifxServer` conftest subclass
- [ ] The emulator runs an mDNS/DNS-SD responder for `_lifx._udp.local` that answers PTR queries received on the IPv4 multicast group 224.0.0.251:5353 (the group `lifx-async` queries) with PTR, SRV, TXT and address records
- [ ] mDNS TXT records carry `id=<serial>`, `p=<product id>`, `fw=<major.minor>` and `tm=1` (WiFi) or `tm=2` (Thread); the SRV record points at the emulator's UDP port
- [ ] Thread devices are advertised with an AAAA record only (the IPv6 bind or a configured advertise address); WiFi devices with an A record
- [ ] mDNS advertisement is on for all devices by default, with an option to disable it for WiFi devices (Thread devices are always advertised, since mDNS is their only discovery path)
- [ ] The device info API and `export-config` expose `connectivity`; the dashboard shows the field read-only at most (no new UI work)
- [ ] `lifx-async` can, against the emulator alone: `discover_mdns()` an emulated Thread device with `Device.connectivity == Connectivity.THREAD`, connect to it over IPv6, read and set colour and power, and observe `thread_connection` true on every reply

### Out of Scope

- Border router behaviours (stale advertisements lingering ~70 min after a device is removed, ~69 s reappearance delay after power-on, per-mesh responder topology) — deferred; user chose not to include in this milestone
- Dashboard UI for connectivity (badge, create-form toggle) — deferred to a later milestone; backend surfaces only now
- Product-level Thread gating in `specs.yml` — user chose per-device configuration; products.json carries no Thread flag
- Answering mDNS queries on the IPv6 multicast group `ff02::fb` — `lifx-async` queries only 224.0.0.251; can be added later if another client needs it
- IPv6 multicast UDP discovery (tagged GetService over IPv6) — Thread devices are unicast-only by decision; no known client uses it
- Thread bandwidth/latency scenarios (animation throttling, RTT shaping) — `lifx-async` locks animation to WiFi (SEED-003); existing `response_delays` scenarios already cover latency
- Returning StateUnhandled for WiFi packets on Thread devices — rejected in favour of zero signal, which matches the Home Assistant integration's expectation that WiFi info packets simply do not describe a Thread radio
- New packet types — the public protocol.yml (checked 2026-09-09) defines no Thread-specific packets; only the header bit and mDNS metadata differ
- `firmware_version` scenario override interacting with Thread firmware — `ScenarioConfig.firmware_version` has no call sites in `src/` and stays dead code this milestone; recorded as a known gap in `01-SPEC.md` Boundaries (Phase 1)

## Context

**Reference implementation.** `lifx-async` (sibling repo at `/Volumes/External/Developer/Djelibeybi/lifx-async`) already implements the client side and is the acceptance oracle. Key locations:
- `src/lifx/protocol/header.py:144,209` — `thread_connection` is frame-address byte 22 (flags byte), bit 3; the client never sets it, it is a device-side report
- `src/lifx/network/discovery/mdns/discovery.py:172` — `tm=2` means Thread, anything else means WiFi; TXT keys `id`, `p`, `fw`, `tm`; instance validation at `_is_lifx_service_instance`; `_validate_txt_id` requires exactly 12 hex chars, unicast MAC
- `src/lifx/const.py:72-78` — `MDNS_ADDRESS = 224.0.0.251`, `MDNS_PORT = 5353`, `LIFX_MDNS_SERVICE = "_lifx._udp.local"`
- `src/lifx/network/connection.py:231-260,312-330` — connectivity is invariant once observed; IPv6 wildcard bind for Thread peers; `V6ONLY` socket
- `tests/conftest.py:302` — `_Ipv6EmulatedLifxServer` subclass that this milestone should make unnecessary
- `tests/test_api/test_ipv6_e2e.py` — existing IPv6 e2e tests against the emulator bound to `::1`
- `tests/test_network/test_mdns/test_discovery.py:44` — `_txt()` fixture showing exact TXT shapes (`tm=1`, `tm=2`, AAAA-only Thread instances, border-router multi-instance replies)
- `.planning/milestones/v2.0-phases/14-thread-revalidation-and-docs/14-INTERIM-RESULTS.md` — physical evidence: thread bit true on 800/800 trials; ack RTT p50 43.9 ms, p95 94.3 ms, max 326.8 ms; 8-device Thread fleet across Light, MultiZone, Matrix and Ceiling classes

**Hardware facts (from lifx-async Phase 14 evidence).** Thread bulbs have no IPv4 address and do not answer IPv4 broadcast; they are advertised by the border router over mDNS with ULA/GUA AAAA records (unscoped link-local is rejected by the client). A radio is either WiFi or Thread and cannot change without a firmware crossgrade.

**Emulator gaps today.** `EmulatedLifxServer.start()` (`server.py:515`) binds one IPv4 socket via `create_datagram_endpoint(local_addr=...)`; there is no IPv6 path, no mDNS, no connectivity field on `DeviceState`, and `LifxHeader.pack()` (`protocol/header.py:81`) only emits bits 0–1 of the flags byte. `header.py` is hand-written (not generated), so the bit can be added there. `DeviceState` has a `NetworkState` group (`wifi_signal`) that is the natural home for `connectivity`. `advertised_services` (PR #156) is the closest precedent for a per-device network setting that spans factories, config, API and persistence.

**Platform pitfalls known up front.** macOS `mDNSResponder` and Windows both own UDP 5353, and lifx-async's probe documents an "mDNSResponder unicast-stealing bug" when a client binds 5353; a responder that must receive multicast PTR queries needs `SO_REUSEADDR`/`SO_REUSEPORT` and `IP_ADD_MEMBERSHIP` handled per platform. `IPV6_V6ONLY` must be set before bind (macOS raises `EINVAL` afterwards). Windows defaults `V6ONLY=1`, Linux and macOS default to dual-stack, which is why a separate v6 socket was chosen over `::` dual-stack.

**Codebase map.** `.planning/codebase/` (generated 2026-09-09) documents architecture, conventions, testing and concerns. Relevant concerns to keep in mind while touching `server.py`: the `rstrip("0000")` serial truncation bug at `server.py:375` and untracked fire-and-forget tasks at `server.py:174-180`.

## Constraints

- **Compatibility**: Python 3.10–3.14, Linux/macOS/Windows — CI matrix and PyApp binaries cover all three; socket code must be portable
- **Tech stack**: asyncio, no threads in the packet path — mDNS responder and IPv6 transport must be asyncio `DatagramProtocol` based like `EmulatedLifxServer`; research decides whether a dependency such as `zeroconf` is acceptable or a hand-rolled responder (as lifx-async did for its client) is preferable
- **Protocol fidelity**: header bit 3 and mDNS TXT semantics must match `lifx-async` exactly; `lifx-async`'s test fixtures are the contract
- **Code quality**: cyclomatic complexity ≤ 10, Pyright standard, Ruff, imports at top of file, Australian English, conventional commits with `core-`/`app-` scopes, GPG-signed `-s` commits
- **Generated files**: `protocol/packets.py` and `products/registry.py` are not edited by hand; no Thread changes belong there
- **Backwards compatibility**: default behaviour (IPv4, WiFi, existing CLI/config/API) must be unchanged for existing users; `connectivity` defaults to `wifi`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Per-device `connectivity` instead of product gating | products.json has no Thread flag; user wants any product testable as Thread | ✓ Phase 1 (core factories, persistence); CLI/config/API surfaces follow in later phases |
| Thread enables firmware 4.200 | User-specified; matches the firmware line that introduced Thread on real bulbs | ✓ Phase 1 — default plus floor; explicit value wins, below-floor raises |
| Terminal-firmware ceiling lives in `specs.yml` as data, not as product-ID checks in Python | Keeps the no-product-gating decision intact; only the original Tile (55, terminal 3.50) declares one, so Thread-on-Tile is rejected by arithmetic alone | ✓ Phase 1 |
| Matrix tiles report the host firmware rather than a hard-coded 3.70 | SPEC requires per-tile firmware to mirror the device; the literal was a pre-existing shortcut | ✓ Phase 1 |
| Public factory functions exempt from the five-argument limit (documented in CLAUDE.md) | Each argument is a user-facing device option; a keyword-options object would break the published API (precedent: `advertised_services`, PR #156) | ✓ Phase 1 |
| Thread devices are IPv6-unicast-only (drop IPv4 and tagged packets) | Real Thread bulbs have no IPv4 address and do not answer broadcast; forces clients onto the mDNS path | — Pending |
| GetWifiInfo on Thread returns signal 0.0, not StateUnhandled | Real behaviour undocumented; zero signal is inert for consumers that skip RSSI on Thread (hass integration) | ✓ Phase 1 — `wifi_signal` derived at build time from effective connectivity |
| Separate `AF_INET6` `V6ONLY` socket, default `::1`, rather than `::` dual-stack | Cross-platform: Windows defaults V6ONLY on, macOS/Linux off; a second socket behaves identically everywhere and keeps IPv4 defaults untouched | — Pending |
| mDNS responder answers IPv4 multicast 224.0.0.251 only | That is the only group lifx-async queries; `ff02::fb` deferred | — Pending |
| All devices advertised via mDNS, WiFi opt-out | Real WiFi bulbs advertise `tm=1`; Thread bulbs have no other discovery path | — Pending |
| Backend surfaces only (core, CLI, config, API); dashboard read-only | User scoped UI work out of this milestone | — Pending |
| Horizontal layers roadmap structure | User preference: finish core library changes, then CLI/config, then API, then assemble | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-09 after Phase 1*
