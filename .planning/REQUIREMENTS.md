# Requirements: LIFX Emulator — Thread Emulation

**Defined:** 2026-09-09
**Core Value:** A LAN client library can discover and control an emulated Thread device exactly as it would a real one: found only over mDNS with an AAAA record, reachable only by IPv6 unicast, every reply carrying the Thread connection bit.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Connectivity

- [x] **CONN-01**: Every device has a `connectivity` of `wifi` (default) or `thread`, held on `NetworkState`, settable through every core factory and `create_device()`
- [x] **CONN-02**: Creating a device with `connectivity=thread` sets host firmware to 4.200 (major 4, minor 200) unless an explicit firmware version is supplied at creation; an explicit value always wins, and an explicit value below 4.200 raises `ValueError`. The `firmware_version` scenario override is **not** part of this milestone: `ScenarioConfig.firmware_version` and `HierarchicalScenarioManager.get_firmware_version_override()` have zero call sites in `src/` and stay dead code — recorded as a known gap in `.planning/phases/01-thread-device-identity/01-SPEC.md` Boundaries
- [x] **CONN-03**: A Thread device answers GetWifiInfo with StateWifiInfo signal 0.0 and answers GetWifiFirmware and GetHostFirmware normally
- [x] **CONN-04**: `connectivity` survives a persistence round trip (serialised with device state, restored on restart)

### Header

- [x] **HDR-01**: `LifxHeader` packs and unpacks frame-address flags bit 3 as `thread_connection`; all existing headers round-trip byte-for-byte unchanged
- [x] **HDR-02**: A Thread device sets bit 3 on every reply it emits: State* responses, multi-packet responses, acknowledgements (type 45) and StateUnhandled (type 223)
- [x] **HDR-03**: A WiFi device never sets bit 3, so default emulator output is unchanged

### Transport

- [ ] **NET-01**: `EmulatedLifxServer` binds a second `AF_INET6` UDP socket with `IPV6_V6ONLY=1` set before bind, defaulting to `::1` with a configurable address, alongside the unchanged IPv4 socket, on Linux, macOS and Windows
- [ ] **NET-02**: Every received datagram carries its address family from the protocol callback through `handle_packet()` into `DeviceManager` target resolution, without the server reaching into device private methods
- [ ] **NET-03**: A Thread device processes a packet only if it arrived on the IPv6 socket and is addressed to its serial with `tagged=0`; any other packet aimed at it is dropped before acknowledgement, response, statistics or activity-log side effects fire (debug logging only)
- [ ] **NET-04**: A WiFi device answers on both the IPv4 and IPv6 sockets, so existing IPv6 e2e tests keep passing
- [ ] **NET-05**: The stock server exposes its IPv6 endpoint (bind address and port) so `lifx-async` can delete its `_Ipv6EmulatedLifxServer` conftest subclass

### mDNS Responder

- [ ] **MDNS-01**: A responder joins `224.0.0.251` on UDP 5353 with `SO_REUSEADDR` (and `SO_REUSEPORT` where available) and receives PTR queries for `_lifx._udp.local` while the host's own mDNS daemon (mDNSResponder, Bonjour, avahi) is running
- [ ] **MDNS-02**: A query from a source port other than 5353 receives a legacy-unicast reply sent to the query's source address and port, with the query ID echoed and the cache-flush bit clear, so `lifx-async` (which never joins the multicast group) receives it
- [ ] **MDNS-03**: A reply contains, for every advertised device, a PTR record `_lifx._udp.local` → `<serial>._lifx._udp.local`, an SRV record (priority 0, weight 0, the emulator's UDP port, a per-device `.local` hostname), a TXT record and one address record, packed into one packet for the whole fleet
- [ ] **MDNS-04**: The TXT record carries exactly `id=<12-hex lowercase serial>`, `p=<product id>`, `fw=<major.minor>` and `tm=1` (WiFi) or `tm=2` (Thread), with identical content across repeated replies
- [ ] **MDNS-05**: A Thread device is advertised with an AAAA record only and a WiFi device with an A record only
- [ ] **MDNS-06**: Each Thread device can be given its own advertised IPv6 address (ULA or GUA); when none is set the responder advertises the IPv6 bind address, and an unscoped link-local address is rejected with a clear error
- [ ] **MDNS-07**: The responder answers direct A and AAAA queries for any hostname it advertises, so a client's follow-up address lookup succeeds
- [ ] **MDNS-08**: The advertised record set follows runtime device additions and removals via a multi-listener `DeviceManager` event registry that does not displace the existing WebSocket event bridge
- [ ] **MDNS-09**: The responder starts and stops with the server, tracks its own asyncio tasks, and leaks no sockets across pytest-asyncio function-scoped loops
- [ ] **MDNS-10**: A time-boxed spike evaluates python-zeroconf (current release) against `lifx-async` `discover_mdns()` for legacy-unicast replies, multi-instance TXT and AAAA-only records, port 5353 coexistence and macOS x86_64 PyApp packaging, and records a go/no-go decision (zeroconf vs hand-rolled) before the responder is built
- [ ] **MDNS-11**: The responder is unit-tested by injecting datagrams directly into its protocol and integration-tested with loopback multicast on the CI runners

### Configuration and Management

- [ ] **CFG-01**: The CLI can create Thread devices and configure the IPv6 bind address, enable or disable mDNS, and set the advertised mDNS address, each with a documented flag
- [ ] **CFG-02**: YAML `DeviceDefinition` accepts `connectivity`, an optional per-device `advertise_address` and an `mdns` opt-out; `EmulatorConfig` accepts the server-level IPv6 bind, mDNS enable and advertised address settings, all validated with `extra="forbid"`
- [ ] **CFG-03**: `export-config` emits the new fields so an exported file reproduces the running setup
- [ ] **CFG-04**: mDNS advertisement is on for every device by default in the standalone app; a WiFi device can opt out, and opting a Thread device out is a validation error because mDNS is its only discovery path
- [ ] **CFG-05**: mDNS queries received and replies sent appear in the activity log and the WebSocket activity stream through the existing activity observer
- [ ] **CFG-06**: Library users constructing `EmulatedLifxServer` directly see no behaviour change unless they pass the new IPv6 or mDNS options; the standalone app enables them by default

### API

- [ ] **API-01**: `DeviceCreateRequest` accepts `connectivity` (default `wifi`), an optional `advertise_address` and an `mdns` flag
- [ ] **API-02**: `DeviceInfo` exposes `connectivity`, the advertised address and whether the device is currently advertised over mDNS
- [ ] **API-03**: Invalid combinations (Thread with `mdns=false`, a non-IPv6 or unscoped link-local advertise address) return a 422 with a descriptive message

### Hygiene

- [ ] **HYG-01**: Fire-and-forget tasks in `server.py` and `event_bridge.py` are tracked with strong references and done callbacks, following the existing `_track_save_task` pattern
- [ ] **HYG-02**: The activity-log serial truncation at `server.py:375` (`rstrip("0000")`) is fixed to use the first six target bytes, with a regression test for a serial ending in zero
- [ ] **HYG-03**: The CLI `run()` coroutine is decomposed into device-construction, storage, server-start and shutdown helpers with unchanged behaviour before any new CLI flags are added

### Verification

- [ ] **VER-01**: Against the stock emulator, `lifx-async` `discover_mdns()` finds an emulated Thread device with `Device.connectivity == Connectivity.THREAD`, connects over IPv6, reads and sets colour and power, and observes `thread_connection` true on every reply
- [ ] **VER-02**: `lifx-async`'s `tests/test_api/test_ipv6_e2e.py` passes against the stock server's IPv6 bind with its conftest subclass removed
- [ ] **VER-03**: An emulated WiFi device discovered via mDNS reports `Connectivity.WIFI` from an A record, and is still discovered via IPv4 UDP broadcast as before
- [ ] **VER-04**: An emulated Thread device never appears in `lifx-async` `discover_udp()` results and never answers an IPv4 unicast packet
- [ ] **VER-05**: The CI matrix (Ubuntu and macOS, Python 3.10 to 3.14) runs the IPv6 and mDNS tests and the 80% coverage gate still passes

## v2 Requirements

Deferred to a future milestone. Tracked but not in the current roadmap.

### mDNS Responder

- **MDNS-12**: Send TTL=0 goodbye records when a device is removed via the API
- **MDNS-13**: Scenario hooks for mDNS fault injection (drop reply, malformed TXT, conflicting TXT values)
- **MDNS-14**: Answer queries on the IPv6 multicast group `ff02::fb`

### Border Router Behaviours

- **BR-01**: Configurable stale-advertisement window after a device is removed
- **BR-02**: Configurable reappearance delay after a device is powered on

### Dashboard

- **UI-01**: Connectivity badge on device cards and table rows
- **UI-02**: Connectivity and mDNS toggles in the create-device form

### CI

- **CI-01**: Windows CI leg exercising the IPv6 socket and mDNS responder

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Product-level Thread gating in `specs.yml` | User chose per-device configuration; products.json carries no Thread flag |
| IPv6 multicast UDP discovery (tagged GetService over IPv6) | Thread devices are unicast-only by decision; no known client uses it |
| Thread bandwidth or latency shaping | Measured Thread ack RTT is lower than WiFi under load; existing `response_delays` scenarios cover latency |
| StateUnhandled for WiFi packets on Thread devices | Rejected in favour of zero signal, matching the Home Assistant integration's expectation |
| New Thread-specific packet types | The public protocol.yml defines none; only the header bit and mDNS metadata differ |
| Multi-mesh or multi-border-router topologies | No consumer need; one responder advertising all devices already matches the border-router reply shape |
| Relying on the mDNS cache-flush bit | `lifx-async` ignores it on legacy-unicast replies; set for realism only, never gate on it |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONN-01 | Phase 1 | Complete |
| CONN-02 | Phase 1 | Complete |
| CONN-03 | Phase 1 | Complete |
| CONN-04 | Phase 1 | Complete |
| HDR-01 | Phase 1 | Complete |
| HDR-02 | Phase 1 | Complete |
| HDR-03 | Phase 1 | Complete |
| NET-01 | Phase 2 | Pending |
| NET-02 | Phase 2 | Pending |
| NET-03 | Phase 2 | Pending |
| NET-04 | Phase 2 | Pending |
| NET-05 | Phase 2 | Pending |
| MDNS-01 | Phase 3 | Pending |
| MDNS-02 | Phase 3 | Pending |
| MDNS-03 | Phase 3 | Pending |
| MDNS-04 | Phase 3 | Pending |
| MDNS-05 | Phase 3 | Pending |
| MDNS-06 | Phase 3 | Pending |
| MDNS-07 | Phase 3 | Pending |
| MDNS-08 | Phase 3 | Pending |
| MDNS-09 | Phase 3 | Pending |
| MDNS-10 | Phase 3 | Pending |
| MDNS-11 | Phase 3 | Pending |
| CFG-01 | Phase 4 | Pending |
| CFG-02 | Phase 4 | Pending |
| CFG-03 | Phase 4 | Pending |
| CFG-04 | Phase 4 | Pending |
| CFG-05 | Phase 4 | Pending |
| CFG-06 | Phase 4 | Pending |
| API-01 | Phase 5 | Pending |
| API-02 | Phase 5 | Pending |
| API-03 | Phase 5 | Pending |
| HYG-01 | Phase 2 | Pending |
| HYG-02 | Phase 2 | Pending |
| HYG-03 | Phase 4 | Pending |
| VER-01 | Phase 6 | Pending |
| VER-02 | Phase 6 | Pending |
| VER-03 | Phase 6 | Pending |
| VER-04 | Phase 6 | Pending |
| VER-05 | Phase 6 | Pending |

**Coverage:**

- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

**By phase:**

| Phase | Name | Requirements |
|-------|------|--------------|
| 1 | Thread Device Identity | 7 |
| 2 | IPv6 Transport and Thread Isolation | 7 |
| 3 | mDNS Responder | 11 |
| 4 | CLI and Configuration | 7 |
| 5 | Management API | 3 |
| 6 | Verification Against lifx-async | 5 |

---
*Requirements defined: 2026-09-09*
*Last updated: 2026-09-09 after roadmap creation*
