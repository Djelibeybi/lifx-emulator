# Roadmap: LIFX Emulator — Thread Emulation

## Overview

Thread emulation is built as horizontal layers, bottom-up. First the core library learns what a Thread device *is* — a `connectivity` field, firmware 4.200, zero WiFi signal, and frame-address bit 3 on every header it emits — with no networking involved. Then the transport layer gains a native IPv6 socket and learns to route by address family, so a Thread device becomes reachable only by IPv6 unicast addressed to its serial and invisible to IPv4 broadcast. Then the mDNS/DNS-SD responder gives Thread devices the only discovery path they have, gated by a spike that decides between python-zeroconf and a hand-rolled responder. With the core surface complete, the standalone app exposes it through CLI flags and YAML config, then through the management API. Finally the whole thing is proved against `lifx-async` — its `discover_mdns()`, its IPv6 e2e suite with the `_Ipv6EmulatedLifxServer` conftest subclass deleted, and its negative discovery cases — running green on the Ubuntu and macOS CI legs.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Thread Device Identity** - `connectivity`, firmware 4.200, zero WiFi signal and the header Thread bit, entirely in-memory (completed 2026-09-09)
- [x] **Phase 2: IPv6 Transport and Thread Isolation** - Native `AF_INET6` socket, family-aware routing, Thread devices unreachable over IPv4, plus the server hygiene fixes (completed 2026-09-10)
- [ ] **Phase 3: mDNS Responder** - Spike-gated `_lifx._udp.local` responder answering legacy-unicast queries with AAAA-only Thread and A-only WiFi instances
- [ ] **Phase 4: CLI and Configuration** - `run()` decomposed, then flags, YAML and `export-config` for connectivity, IPv6 bind and mDNS
- [ ] **Phase 5: Management API** - Create and report Thread devices over HTTP, with 422s for impossible combinations
- [ ] **Phase 6: Verification Against lifx-async** - The acceptance oracle's own suites pass against the stock emulator on CI

## Phase Details

### Phase 1: Thread Device Identity

**Goal**: A core-library device can be created as a Thread device, and everything about its identity — firmware, WiFi reporting, persisted state and every header byte it emits — matches a real Thread bulb.
**Depends on**: Nothing (first phase)
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04, HDR-01, HDR-02, HDR-03
**Success Criteria** (what must be TRUE):

  1. `create_device(product_id, connectivity="thread")` and every typed factory except `create_tile_device` (`create_color_light`, `create_color_temperature_light`, `create_infrared_light`, `create_hev_light`, `create_multizone_light`, `create_switch`) produce a device reporting host firmware 4.200, while an explicit firmware argument at creation still wins over that default. `create_tile_device(connectivity="thread")` raises `ValueError`: it hard-codes product 55, discontinued at terminal firmware 3.50, below the Thread floor. The `firmware_version` scenario override stays out of scope for this milestone (dead code, recorded gap in `01-SPEC.md` Boundaries).
  2. A single Thread device sets frame-address flags bit 3 on all three of its reply shapes in one test: a `StateColor`-style data reply, an `Acknowledgement` (type 45), and a `StateUnhandled` (type 223).
  3. A WiFi device never sets bit 3, and every existing header round-trips through `pack()`/`unpack()` byte-for-byte unchanged.
  4. `GetWifiInfo` to a Thread device returns `StateWifiInfo` with signal 0.0, while `GetWifiFirmware` and `GetHostFirmware` answer exactly as they do for a WiFi device.
  5. A Thread device saved to storage and reloaded from disk is still a Thread device; a persisted file written before this milestone loads as `wifi`.

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Capture the pre-change wire byte baseline, then wire the Thread bit end-to-end through `Connectivity`, `LifxHeader.thread_connection` and the per-device response header template

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Thread firmware default 4.200 with a floor, and a `specs.yml` terminal-firmware ceiling that rejects Thread on the original Tile without a product-ID literal in Python

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — `connectivity` on all seven typed factories, zero WiFi signal for Thread, and per-tile firmware mirroring the host

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-04-PLAN.md — `connectivity` persistence round trip read once, the full reply-shape bit matrix, and the phase CI gates

**UI hint**: no

### Phase 2: IPv6 Transport and Thread Isolation

**Goal**: The stock server listens on IPv6 alongside IPv4, and a Thread device answers only IPv6 unicast packets addressed to its serial — with the two known `server.py` defects fixed before the file grows a second and third protocol.
**Depends on**: Phase 1
**Requirements**: NET-01, NET-02, NET-03, NET-04, NET-05, HYG-01, HYG-02
**Success Criteria** (what must be TRUE):

  1. A stock `EmulatedLifxServer` started with default options binds an `AF_INET6` socket whose `getsockopt(IPPROTO_IPV6, IPV6_V6ONLY)` reads 1 on both the Ubuntu and macOS CI legs, defaulting to `::1`, alongside an unchanged IPv4 socket, and exposes that IPv6 bind address and port to callers.
  2. A `GetColor` addressed to a Thread device's serial over IPv6 unicast gets a reply; the same packet over IPv4, and a tagged/broadcast packet over either socket, yields no response, no acknowledgement, no `packets_sent` increment and no activity event.
  3. A WiFi device answers on both sockets, and a library user who passes no new constructor arguments sees identical IPv4 discovery and control behaviour to today.
  4. A packet flood interleaved with forced garbage collection loses no admitted responses or admitted WebSocket broadcasts: every admitted packet task and queued bridge event is retained until completion, while work beyond the bounded server or bridge capacity is rejected before allocation and recorded in an observable overload-drop metric.
  5. The activity log and the `PacketEvent.target` on `/api/activity` show the full 12-hex serial for a device whose serial ends in `0`.

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Trace retained IPv4 packet work and exact activity targets, then generalise the tracker to device persistence

**Wave 2** *(after Wave 1; plans execute in parallel)*

- [x] 02-02-PLAN.md — Route every event-bridge broadcast through one FastAPI-lifespan-owned tracker
- [x] 02-03-PLAN.md — Promote immutable per-datagram identity and enforce Thread/WiFi family eligibility before side effects

**Wave 3** *(after both Wave 2 plans)*

- [x] 02-04-PLAN.md — Atomically bind/publish the shared-port V6-only endpoint and prove the complete contract on real loopback sockets

**UI hint**: no
**Note**: HYG-01 (task tracking) and HYG-02 (`rstrip` serial fix) land before the IPv6 protocol instance is added, so there is one correct pattern in `server.py` to copy rather than two.

### Phase 3: mDNS Responder

**Goal**: `lifx-async` can find emulated devices over mDNS the way it actually queries — legacy-unicast from an ephemeral port — with Thread devices advertised AAAA-only and WiFi devices A-only.
**Depends on**: Phase 1 (technically independent of Phase 2; sequenced after it because parallelization is off and Phase 2's task-tracking fix is reused by the responder's socket)
**Requirements**: MDNS-01, MDNS-02, MDNS-03, MDNS-04, MDNS-05, MDNS-06, MDNS-07, MDNS-08, MDNS-09, MDNS-10, MDNS-11
**Success Criteria** (what must be TRUE):

  1. A recorded go/no-go decision exists for python-zeroconf versus a hand-rolled responder, backed by a time-boxed spike run against `lifx-async` `discover_mdns()` that reports on legacy-unicast replies, multi-instance TXT and AAAA-only records, port 5353 coexistence with the host mDNS daemon, and macOS x86_64 PyApp packaging.
  2. A PTR query for `_lifx._udp.local` sent to 224.0.0.251:5353 from an ephemeral port, on a machine whose own mDNS daemon is running, receives a unicast reply at that source address and port with the query ID echoed, the cache-flush bit clear and TTL ≤ 10 s.
  3. One reply carries, for every advertised device, a PTR record, an SRV record pointing at the emulator's UDP port and a per-device `.local` hostname, a TXT record containing exactly `id`, `p`, `fw` and `tm` (`1` for WiFi, `2` for Thread), and exactly one address record — AAAA for Thread, A for WiFi — with a Thread device's own configured ULA/GUA used when set, the IPv6 bind address when not, and an unscoped link-local address rejected with a clear error.
  4. A direct A or AAAA query for any advertised hostname is answered, and adding or removing a device at runtime changes the next reply's record set while the existing WebSocket device events keep firing unchanged.
  5. The responder starts and stops with the server, leaves no sockets or tasks behind across pytest-asyncio function-scoped loops, and is covered by both datagram-injection unit tests and loopback-multicast integration tests that pass on the Ubuntu and macOS CI legs.

**Plans**: TBD
**UI hint**: no
**Note**: MDNS-10 is the first plan of this phase. The remaining ten requirements are planned against whichever implementation the recorded go/no-go selects.

### Phase 4: CLI and Configuration

**Goal**: Someone running the standalone emulator can create and configure Thread devices, the IPv6 bind and mDNS advertisement entirely from CLI flags and YAML, and see mDNS traffic in the activity stream.
**Depends on**: Phase 3 (and, through it, Phases 1 and 2 — the full core surface must exist to be exposed)
**Requirements**: HYG-03, CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06
**Success Criteria** (what must be TRUE):

  1. `lifx-emulator` starts a Thread device and configures the IPv6 bind address, mDNS enable/disable and the advertised mDNS address from documented flags that appear in `--help`.
  2. A YAML config carrying `connectivity`, a per-device `advertise_address` and an `mdns` opt-out loads and runs; an unknown key, or a Thread device with `mdns: false`, fails validation with a message naming the offending field.
  3. `export-config` against a running emulator writes a file that, fed back in, reproduces the same devices with the same connectivity, advertised addresses and mDNS settings.
  4. mDNS queries received and replies sent appear in `/api/activity` and on the WebSocket activity topic alongside LIFX packets.
  5. The standalone app has IPv6 and mDNS on by default while a library user constructing `EmulatedLifxServer` without the new options sees no behaviour change, and `run()` is decomposed into device-construction, storage, server-start and shutdown helpers that each pass the complexity budget with CLI behaviour unchanged.

**Plans**: TBD
**UI hint**: no
**Note**: HYG-03 (the `run()` decomposition) is the first plan of this phase and lands before any new flag is added.

### Phase 5: Management API

**Goal**: The HTTP management API can create Thread devices, report their connectivity and advertisement state, and reject combinations that cannot exist.
**Depends on**: Phase 4
**Requirements**: API-01, API-02, API-03
**Success Criteria** (what must be TRUE):

  1. `POST /api/devices` with `connectivity: "thread"`, an `advertise_address` and an `mdns` flag creates a Thread device that the next mDNS query discovers.
  2. `GET /api/devices` and `GET /api/devices/{serial}` report `connectivity`, the advertised address and whether the device is currently advertised over mDNS.
  3. A Thread device with `mdns: false`, a non-IPv6 advertise address, and an unscoped link-local advertise address each return 422 with a message describing what is wrong.
  4. An existing API client that omits the new fields gets `connectivity: "wifi"` and otherwise unchanged request and response shapes.

**Plans**: TBD
**UI hint**: no

### Phase 6: Verification Against lifx-async

**Goal**: The acceptance oracle exercises Thread discovery and control against the stock emulator, with no emulator-specific test scaffolding left in the sibling repo.
**Depends on**: Phase 5
**Requirements**: VER-01, VER-02, VER-03, VER-04, VER-05
**Success Criteria** (what must be TRUE):

  1. Against the stock emulator, `lifx-async` `discover_mdns()` finds an emulated Thread device with `Device.connectivity == Connectivity.THREAD`, connects to it over IPv6, reads and sets colour and power, and observes `thread_connection` true on every reply.
  2. `lifx-async`'s `tests/test_api/test_ipv6_e2e.py` passes against the stock server's IPv6 bind with `_Ipv6EmulatedLifxServer` deleted from its `tests/conftest.py`.
  3. An emulated WiFi device is discovered by `discover_mdns()` as `Connectivity.WIFI` from an A record and is still discovered by IPv4 UDP broadcast exactly as before.
  4. An emulated Thread device never appears in `lifx-async` `discover_udp()` results and never answers an IPv4 unicast packet.
  5. The CI matrix (Ubuntu and macOS, Python 3.10 to 3.14) runs the IPv6 and mDNS tests and the 80% coverage gate still passes.

**Plans**: TBD
**UI hint**: no

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Thread Device Identity | 4/4 | Complete    | 2026-09-09 |
| 2. IPv6 Transport and Thread Isolation | 4/4 | Complete    | 2026-09-10 |
| 3. mDNS Responder | 0/TBD | Not started | - |
| 4. CLI and Configuration | 0/TBD | Not started | - |
| 5. Management API | 0/TBD | Not started | - |
| 6. Verification Against lifx-async | 0/TBD | Not started | - |
