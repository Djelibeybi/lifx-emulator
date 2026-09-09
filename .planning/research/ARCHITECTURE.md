# Architecture Research

**Domain:** Extending a layered asyncio LIFX LAN protocol emulator with Thread-device emulation (IPv6 transport, mDNS/DNS-SD responder, per-device `connectivity`)
**Researched:** 2026-09-09
**Confidence:** HIGH (every placement below is grounded in a specific existing file/line, a precedent commit, or a confirmed absence found by reading the source; the two genuinely novel decisions — multi-listener device events and the dead scenario-firmware wiring — are called out explicitly as such)

This is not a greenfield architecture. It is a placement map: where each new piece of Thread support attaches to the six layers already documented in `.planning/codebase/ARCHITECTURE.md`, and which of those attachment points require a small structural change to the existing layer (not a new layer).

## Standard Architecture

### System Overview

```
                    Clients (lifx-async, other LIFX libraries)
        ┌──────────────────────┬──────────────────────┬───────────────────────┐
        │ UDP 56700 IPv4       │ UDP 56700 IPv6 (NEW)  │ mDNS 224.0.0.251:5353 (NEW)
        ▼                      ▼                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  Network Layer (core, server.py)                                              │
│  EmulatedLifxServer                                                           │
│   ├─ LifxProtocol (v4)  [existing, gains a `family` tag]                      │
│   ├─ LifxProtocol (v6)  [NEW: second instance, same class, AF_INET6/V6ONLY]   │
│   └─ MdnsResponder      [NEW: owned sibling, own DatagramProtocol, IPv4 mcast]│
└───────────────────────┬────────────────────────────────┬──────────────────────┘
                         │ header, family                 │ device add/remove
                         ▼                                 │ (listener, not owner)
┌───────────────────────────────────────────────────────────────────────────────┐
│  Domain Layer (core, devices/, scenarios/)                                    │
│  DeviceManager.resolve_target_devices(header, family)  [CHANGED: family-aware]│
│  DeviceManager.add_device_added_listener(...)          [NEW: multi-subscriber]│
│  EmulatedLifxDevice._response_header_template          [CHANGED: thread bit]  │
│  EmulatedLifxDevice.process_packet()                    [CHANGED: firmware    │
│                                                           override, first use]│
│  DeviceState.network.connectivity                       [NEW field]           │
└───────────────────────┬─────────────────────────────────────────────────────┘
                         ▼
     Repository / Persistence / Products-Factories layers — unchanged shape,
     `connectivity` flows through exactly where `advertised_services` (PR #156)
     already flows, plus one extra stop (state_serializer/state_restorer) that
     `advertised_services` skipped and this milestone cannot skip (see below).
                         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  Application Layer (app package, unchanged component set)                     │
│  config.py DeviceDefinition.connectivity, __main__.py --connectivity          │
│  api/models.py DeviceCreateRequest/DeviceInfo.connectivity                    │
└───────────────────────────────────────────────────────────────────────────────┘
```

No new layer is introduced. Thread support is additive fields and one additional Network-layer collaborator (`MdnsResponder`), placed exactly where the existing layer boundaries in `.planning/codebase/ARCHITECTURE.md` already say this kind of thing belongs.

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `LifxProtocol` (nested in `server.py`) | One instance per bound socket; now tags itself `family="inet"` / `"inet6"` at construction and passes its own transport + family into `handle_packet` | Existing class, extended, not duplicated |
| `EmulatedLifxServer` | Owns both UDP transports and the `MdnsResponder`; replies on whichever transport a request arrived on | Existing, gains a second transport attribute and one new constructor collaborator |
| `DeviceManager.resolve_target_devices` | Now the single place that decides whether a Thread device is reachable for a given packet (family + tagged bit) | Existing method, signature extended with a defaulted `family` parameter |
| `DeviceManager` listener registry | Lets more than one subscriber (WebSocket bridge, `MdnsResponder`) observe device add/remove without one clobbering the other | **New capability** — today's `on_device_added`/`on_device_removed` are single-slot, last-writer-wins attributes |
| `MdnsResponder` | New core-library component: IPv4-multicast `DatagramProtocol` answering `_lifx._udp.local` PTR queries from an in-memory record set kept current via the listener registry | New, core library (`lifx_emulator/mdns/`) |
| `LifxHeader` | Adds `thread_connection: bool` as bit 3 of the frame-address flags byte | Existing hand-written module, one field + two bit operations |
| `EmulatedLifxDevice._response_header_template` | Single point that stamps `thread_connection` onto every header the device ever emits, including both ack paths | Existing pre-allocated template, one constructor-time value added |
| `DeviceState.network.connectivity` | Per-device WiFi/Thread flag, routed like every other `NetworkState` field | New field on an existing sub-state |

## Recommended Project Structure

```
packages/lifx-emulator-core/src/lifx_emulator/
├── protocol/
│   └── header.py                # + thread_connection field (bit 3), pack/unpack
├── devices/
│   ├── states.py                # + Connectivity enum, NetworkState.connectivity, routing entry
│   ├── device.py                # + template thread_connection; + firmware-override stage in process_packet
│   ├── manager.py                # + family-aware resolve_target_devices; + multi-listener registry
│   ├── state_serializer.py       # + connectivity in serialize_device_state (see "Persistence" below)
│   └── state_restorer.py         # + connectivity restore
├── factories/
│   ├── builder.py                 # + with_connectivity(); Thread → firmware 4.200 default
│   └── factory.py                 # + connectivity param on create_device() (+ typed wrappers)
├── handlers/
│   └── device_handlers.py         # GetWifiInfoHandler: signal 0.0 when connectivity == thread
├── mdns/                          # NEW subpackage
│   ├── __init__.py
│   ├── records.py                 # DNS/DNS-SD wire encode: PTR, SRV, TXT, A, AAAA
│   └── responder.py               # MdnsResponder(DatagramProtocol)
└── server.py                      # + v6 socket lifecycle, family-tagged LifxProtocol,
                                    #   MdnsResponder ownership, transport threaded through
                                    #   handle_packet/_process_device_packet/_send_ack

packages/lifx-emulator/src/lifx_emulator_app/
├── config.py                      # + DeviceDefinition.connectivity (+ validator);
                                    #   + EmulatorConfig mDNS/IPv6 bind options
├── __main__.py                    # + --connectivity CLI flag; wiring into factory calls,
                                    #   server construction, _device_state_to_yaml_dict
└── api/
    ├── models.py                  # + DeviceCreateRequest.connectivity, DeviceInfo.connectivity
    ├── services/device_service.py  # + connectivity passthrough to create_device()
    └── mappers/device_mapper.py    # + connectivity in to_device_info()
```

### Structure Rationale

- **`mdns/` is a new core-library subpackage, not an app-package module.** The acceptance oracle (`lifx-async`) drives the emulator as a *library* — its `tests/conftest.py:302` subclasses `EmulatedLifxServer` directly, never touches `lifx_emulator_app`. PROJECT.md's own acceptance line is unambiguous: *"lifx-async can, against the emulator alone: `discover_mdns()` an emulated Thread device..."* — "the emulator alone" is the core library. Putting mDNS in the app package would make it invisible to the one consumer this milestone exists for. This also matches the existing rule that the app depends on core, never the reverse (`.planning/codebase/ARCHITECTURE.md` Architectural Constraints, "Circular imports").
- **No new layer for connectivity.** It is a per-device attribute, so it belongs in `DeviceState` next to `wifi_signal` (PROJECT.md's own "Emulator gaps today" note already identifies `NetworkState` as its natural home) and flows through the same Factories → Repository/Persistence → App pipeline every other per-device attribute uses.
- **`mdns/records.py` is separated from `mdns/responder.py`** to mirror the existing `protocol/header.py` (pure struct pack/unpack) vs `server.py` (socket I/O) split — wire-format code with no I/O, and I/O code with no wire-format knowledge, following the codebase's existing separation of concerns.

## Architectural Patterns

### Pattern 1: Family threaded as an explicit call parameter, never inferred from device state

**What:** `LifxProtocol.datagram_received` already runs once per bound socket and already knows, at construction time, which family it serves. That fact is passed down the existing call chain as a plain argument — `handle_packet(data, addr, transport, family)` → `DeviceManager.resolve_target_devices(header, family)` — rather than the server inspecting `device.state.connectivity` to decide how to route, and rather than `EmulatedLifxDevice` inspecting anything about the arriving socket.

**When to use:** Any time a fact is knowable at the point a datagram is received and is needed only for *routing/filtering* that datagram, thread it as data through the existing pipeline instead of adding a second query surface (e.g. a "which family did this arrive on" lookup) that callers must remember to consult.

**Why this satisfies the constraint in the question:** The two things the server is explicitly told not to do — reach into device privates (CONCERNS.md `server.py:197,251,265`), and break the single-socket constructor API — are both avoided because the addition is a *parameter*, not a new accessor on `EmulatedLifxDevice`, and it defaults to today's behaviour (`family="inet"`) when omitted, so `EmulatedLifxServer(devices, device_manager, bind_address, port)` continues to work unchanged for every existing caller and test.

**Trade-off:** `resolve_target_devices`, `handle_packet`, `_process_device_packet` and `_send_ack` each gain one parameter. This is a wider but shallower change than adding a device-level "can I be reached from here" method, and it is the shallower change specifically because it keeps the decision in the Domain layer (`DeviceManager`) where target resolution already lives, rather than pushing it into `EmulatedLifxDevice.process_packet()`.

**Where it lands, concretely:**
```python
# devices/manager.py — resolve_target_devices, extended (default preserves old behaviour)
def resolve_target_devices(
    self, header: LifxHeader, family: str = "inet"
) -> list[EmulatedLifxDevice]:
    def _reachable(device: EmulatedLifxDevice) -> bool:
        if device.state.connectivity != Connectivity.THREAD:
            return True
        return family == "inet6" and not header.tagged
    if header.tagged or header.target == b"\x00" * 8:
        return [d for d in self._device_repository.get_all() if _reachable(d)]
    target_serial = header.target[:6].hex()
    device = self._device_repository.get(target_serial)
    return [device] if device and _reachable(device) else []
```
This is the *entire* implementation of "a Thread device processes a packet only if it arrived on the emulator's IPv6 socket and is addressed to its serial" — it lives in one method, in the layer that already owns target resolution, and `EmulatedLifxDevice.process_packet()` is never called for a rejected Thread device at all (not called-and-ignored; simply never invoked), so no new drop-logging path or scenario interaction is needed.

### Pattern 2: One template, not several call sites, for the wire-level Thread bit

**What:** `EmulatedLifxDevice._response_header_template` (`devices/device.py:91-98`) is a `LifxHeader` built once per device and shallow-copied by `_create_response_header` (`device.py:218`) for every response the device ever sends. Every response header — normal replies, `StateUnhandled`, and the ack built inside `process_packet()` when a scenario targets acks — is `copy.copy()` of that one template. Adding `thread_connection=self.state.connectivity == Connectivity.THREAD` to the template's construction means every one of those paths carries the bit with zero further code changes.

**When to use:** Whenever a per-device, per-response-invariant fact needs to appear on every outgoing header, and the codebase already funnels header construction through one factory method — extend the template, not the call sites.

**Why this is the *one* place, not several:** The question asks whether the bit belongs in `LifxHeader`, the template, `_send_ack`, or the `StateUnhandled` paths — one place or several. It is one, and it is the template, for a structural reason worth stating precisely: `EmulatedLifxServer._send_ack` (`server.py:182-228`) already calls `device._create_response_header(...)` (the exact line CONCERNS.md flags for reaching into device privates, `server.py:197`) rather than building its own header. Because that reach-through already exists and already goes through the template-copying method, the fast-path ack inherits the bit automatically the moment the template carries it — the server-side ack path needs **no change at all** for the Thread bit specifically (it still needs the `transport` parameter from Pattern 1, but that is unrelated). The `StateUnhandled` path inside `process_packet()` (`device.py:298-319`) also calls `_create_response_header`, so it too is already covered. This means the change footprint for "every reply carries the Thread connection bit" is: one new field on `LifxHeader`, two bit operations in `pack()`, and one new keyword argument at `device.py:91-98`.

**Example (the only device.py change this requires):**
```python
self._response_header_template = LifxHeader(
    source=0,
    target=self.state.get_target_bytes(),
    sequence=0,
    tagged=False,
    pkt_type=0,
    size=0,
    thread_connection=self.state.connectivity == Connectivity.THREAD,  # NEW
)
```

**Trade-off:** If `connectivity` could change at runtime after device construction (it cannot per the requirements — "a radio is either WiFi or Thread and cannot change without a firmware crossgrade" — PROJECT.md Context), the template would need invalidation on write, mirroring the existing `_cached_scenario` invalidation pattern. Because connectivity is immutable post-creation, no invalidation hook is needed, and this should be documented as an invariant (a `ValueError` on `DeviceState.connectivity` reassignment, or simply no setter path exposed by any handler, would make the invariant enforced rather than merely documented).

### Pattern 3: Multi-subscriber device lifecycle events (new capability, not precedent-following)

**What:** `DeviceManager.on_device_added` / `on_device_removed` (`devices/manager.py:132-144`) are plain instance attributes, not a list. `event_bridge.wire_device_events` (`api/services/event_bridge.py:78-79`) sets them with direct assignment: `device_manager.on_device_added = on_device_added`. Whoever assigns last wins; there is no mechanism today for two independent subscribers to both observe device add/remove.

**Why this matters for mDNS specifically:** `MdnsResponder` must observe the same add/remove events the WebSocket bridge already observes, to keep its record set current (this is the literal question asked: "how it observes device add/remove ... to keep its record set current"). If `MdnsResponder` is constructed and wired inside `EmulatedLifxServer.__init__`/`.start()` — which happens before `create_api_app(server)` calls `wire_device_events` (`api/app.py:208`) — then today's single-slot assignment would silently discard the responder's callback the moment the API layer starts. This is not a theoretical risk; it is deterministic given the existing call order (server constructed and started first; API layer wired second, in `run_api_server`/`create_api_app`).

**Recommended fix (new, not a precedent — call this out explicitly in planning):** Add a small list-based registry to `DeviceManager`, additive and backward compatible with the existing attribute-assignment style:
```python
class DeviceManager:
    def __init__(self, device_repository, on_device_added=None, on_device_removed=None):
        self._added_listeners: list[DeviceAddedCallback] = []
        self._removed_listeners: list[DeviceRemovedCallback] = []
        if on_device_added is not None:
            self._added_listeners.append(on_device_added)
        if on_device_removed is not None:
            self._removed_listeners.append(on_device_removed)

    def add_device_added_listener(self, cb: DeviceAddedCallback) -> None:
        self._added_listeners.append(cb)

    def add_device_removed_listener(self, cb: DeviceRemovedCallback) -> None:
        self._removed_listeners.append(cb)
```
`add_device()`/`remove_device()` iterate `self._added_listeners`/`self._removed_listeners` (each wrapped in the existing `try/except Exception: logger.exception(...)` isolation already present at `manager.py:172-176`) instead of calling a single attribute. `event_bridge.wire_device_events` switches from `device_manager.on_device_added = on_device_added` to `device_manager.add_device_added_listener(on_device_added)`; `EmulatedLifxServer` calls `self._device_manager.add_device_added_listener(self.mdns_responder.on_device_added)` during `start()` (after both are constructed) or inside `__init__` if `MdnsResponder` is eagerly constructed. Existing direct-attribute-assignment callers (if any exist outside this codebase, since this is a library) still work if `on_device_added`/`on_device_removed` constructor kwargs are kept as sugar for "append one listener at construction time," as shown above — no breaking change to the public constructor signature.

**Trade-off:** This is a genuine (small) core-library API change beyond anything `advertised_services` required, because `advertised_services` never needed a second subscriber to device lifecycle. Flag it as its own task in the core-library phase; it is cheap (under 20 lines) but is a prerequisite for mDNS, not an mDNS detail.

### Pattern 4: Hand-rolled mDNS responder, not a `zeroconf` dependency

**What:** `MdnsResponder` is a bespoke `asyncio.DatagramProtocol` bound to `224.0.0.251:5353` with `SO_REUSEADDR`/`SO_REUSEPORT` and `IP_ADD_MEMBERSHIP` (per-platform, matching the note already captured in PROJECT.md's "Platform pitfalls" paragraph), encoding PTR/SRV/TXT/A/AAAA records by hand in `mdns/records.py`.

**When to use / why not `zeroconf`:** Three independent reasons converge on hand-rolling:
1. **Threading model.** `zeroconf`'s Python implementation runs its own background thread for socket I/O. `.planning/codebase/ARCHITECTURE.md`'s Architectural Constraints section is explicit: *"Single asyncio event loop... Handlers must stay synchronous and non-blocking"* and the only sanctioned worker thread is the single-worker executor inside `DevicePersistenceAsyncFile`. Introducing a second, unrelated background thread for mDNS conflicts with that documented constraint and reintroduces exactly the kind of concurrency surface the codebase has deliberately avoided everywhere else.
2. **Protocol fidelity is a hard requirement, not a nice-to-have.** PROJECT.md: *"header bit 3 and mDNS TXT semantics must match lifx-async exactly; lifx-async's test fixtures are the contract."* `zeroconf` is a general-purpose responder/browser; making it emit exactly `id=`, `p=`, `fw=`, `tm=` with no other keys, and exactly one A-or-AAAA record depending on connectivity, means fighting a general library's defaults rather than writing ~150 lines of exact-format encoding once.
3. **Precedent already exists.** `lifx-async` itself hand-rolled its client-side mDNS discovery rather than depending on a general library (PROJECT.md Context: *"a hand-rolled responder (as lifx-async did for its client) is preferable"*). Matching that precedent keeps both sides of the wire contract owned by code that has to match a fixed, small spec — no unsolicited announcements, no service browsing, no goodbye packets, since border-router behaviours are explicitly out of scope.

**Trade-off:** A hand-rolled responder must get DNS name-compression and record framing right without a battle-tested library underneath it. This is mitigated by scope: exactly one query type is answered (PTR for `_lifx._udp.local` on one multicast group), and `lifx-async`'s own test fixtures (`tests/test_network/test_mdns/test_discovery.py:44`) are an executable spec for the exact TXT/record shapes expected, so round-trip testing against the sibling repo substitutes for depending on a general-purpose library's correctness.

**Consequence for task-tracking (CONCERNS.md's flagged fire-and-forget-task risk):** Because border-router announcement behaviour is out of scope, `MdnsResponder` needs no periodic/background tasks at all — it only ever reacts to an inbound multicast datagram (already on the loop, like `LifxProtocol.datagram_received`) or a synchronous device-added/removed callback that only mutates an in-memory dict (no I/O, no task creation). This is a place where the milestone can avoid repeating the untracked-task pattern CONCERNS.md flags elsewhere (`server.py:174-180`, `event_bridge.py:29-38`), rather than a place where that pattern would need to be reproduced.

## Data Flow

### Flow 1: A datagram's transport family reaching the device-reachability decision

```
socket (AF_INET or AF_INET6, V6ONLY)
    ↓ datagram_received(data, addr)
LifxProtocol[family]                         # family fixed at construction, one instance per socket
    ↓ handle_packet(data, addr, self.transport, family=self.family)
EmulatedLifxServer.handle_packet             # unpacks LifxHeader as today; family is pass-through, not stored
    ↓ resolve_target_devices(header, family)
DeviceManager                                 # NEW: family + header.tagged decide reachability here, once
    ↓ target_devices (already filtered — Thread devices on the wrong family/tagged are simply absent)
EmulatedLifxServer._process_device_packet(device, header, packet, addr, transport)
    ↓ (unchanged) device._get_resolved_scenario(), device._should_handle_packet(), device.process_packet()
EmulatedLifxDevice.process_packet             # never sees a request its connectivity should reject —
                                               # no family parameter needed here at all
    ↓ resp_header via _create_response_header  # thread_connection already baked into the template
transport.sendto(response_data, addr)         # NEW: the *arriving* transport, not always self.transport
```

Key point for the roadmap: `EmulatedLifxDevice` needs **zero** new parameters or knowledge of "family" — the filtering happens entirely upstream, in the Domain layer's existing target-resolution method. This keeps the blast radius of the IPv6 feature almost entirely inside `server.py` and `devices/manager.py`.

### Flow 2: Device lifecycle reaching the mDNS record set

```
factories.create_device(...) → DeviceBuilder.build() → EmulatedLifxDevice
    ↓ server.add_device(device)                          # existing entry point, unchanged
DeviceManager.add_device(device, scenario_manager)
    ↓ self._device_repository.add(device)
    ↓ for cb in self._added_listeners: cb(device)         # NEW: iterate, don't overwrite
        ├─ event_bridge.on_device_added   → WebSocket broadcast (existing, async, needs a task)
        └─ MdnsResponder.on_device_added  → NEW: synchronous, in-memory record upsert, no task
```
`MdnsResponder.on_device_added(device)` reads `device.state.serial`, `.label`, `.product`, `.version_major/minor`, `.connectivity` and writes one `DeviceRecord` into an in-memory `dict[str, DeviceRecord]` keyed by serial — no socket I/O happens at add/remove time. Socket I/O happens only when `datagram_received` fires for an inbound PTR query, at which point the responder walks its current dict and emits PTR/SRV/TXT/A-or-AAAA answers. `remove_device()` fires the mirror `on_device_removed(serial)`, deleting the dict entry. On `EmulatedLifxServer.start()`, before the mDNS socket binds, the responder is seeded once from `device_manager.get_all_devices()` (listener registration only covers *future* add/remove, not devices already present at server construction — same as the existing WebSocket bridge would need to do, and does, via the `sync` message described in `.planning/codebase/ARCHITECTURE.md`'s "Real-Time Dashboard Flow").

### Flow 3: `connectivity` from creation to every consumer (precedent: `advertised_services`, PR #156/#91e58a9, with one deliberate deviation)

`git show --stat 91e58a9` is the exact precedent for "a per-device network setting spanning factories, config, API, persistence":
```
lifx-emulator.example.yaml                                     | 17 ++
packages/.../lifx_emulator/devices/states.py                   |  8 ++
packages/.../lifx_emulator/factories/builder.py                 | 19 ++
packages/.../lifx_emulator/factories/factory.py                 | 23 ++
packages/.../lifx_emulator/handlers/device_handlers.py           | 23 +--
packages/.../lifx_emulator-core/tests/test_advertised_services.py| 93 ++
packages/.../lifx_emulator-core/tests/test_integration.py        | 50 ++
packages/lifx-emulator/src/lifx_emulator_app/__main__.py         |  1 +
packages/lifx-emulator/src/lifx_emulator_app/config.py            | 17 ++
packages/lifx-emulator/tests/test_config.py                      | 18 ++
```
`connectivity` should touch the same ten files, **plus three that `advertised_services` conspicuously did not touch**, because PROJECT.md's requirements for `connectivity` are strictly wider than what shipped for `advertised_services`:

| Stop in the pipeline | Did `advertised_services` touch it? | Does `connectivity` need it? |
|---|---|---|
| `devices/states.py` (field + routing) | Yes | Yes — `NetworkState.connectivity`, not `CoreDeviceState` |
| `factories/builder.py` / `factory.py` (build-time param) | Yes | Yes |
| `handlers/device_handlers.py` (a handler reads it) | Yes (`GetServiceHandler`) | Yes (`GetWifiInfoHandler`) |
| `config.py` `DeviceDefinition` (+ validator) | Yes | Yes |
| `__main__.py` (pass config value to factory) | Yes (config-file only, no CLI flag) | Yes — **and** needs a CLI flag, which `advertised_services` never got (PROJECT.md requires "settable ... via CLI flag") |
| `devices/state_serializer.py` / `state_restorer.py` | **No** — confirmed absent from `serialize_device_state()` (`devices/state_serializer.py:89-111` enumerates every persisted field; `advertised_services` and `firmware_version` are both absent) | **Yes, and this is the one deliberate deviation.** `export_config` (`__main__.py:384-458`) reads *only* the on-disk JSON written by `serialize_device_state` — it has no access to a live `EmulatedLifxDevice`. Since PROJECT.md requires *"export-config expose connectivity"*, and `export-config` cannot see anything `state_serializer` didn't persist, `connectivity` **must** be added to `serialize_device_state`/`deserialize_device_state`/`state_restorer.restore_if_available`, even though the general pattern for build-time-only fields (as demonstrated by `firmware_version` and `advertised_services`) is to skip persistence entirely. This also happens to fix, for `connectivity` only, a round-trip gap that quietly exists today for `advertised_services` and `firmware_version` (neither survives `--persistent` restart with correct wire behaviour reported back through `export-config` — out of scope to fix for this milestone, but worth a one-line note in PITFALLS for whoever picks it up later). |
| `api/models.py` `DeviceCreateRequest`/`DeviceInfo` | **No** — confirmed absent; only `firmware_major`/`firmware_minor` (`api/models.py:32-37`) made it into the HTTP create API, not `advertised_services` | **Yes** — PROJECT.md requires *"the device info API ... expose connectivity"*, following the `firmware_major`/`firmware_minor` precedent (a plain field, not a nested model), not the `advertised_services` gap |
| `api/services/device_service.py` / `api/mappers/device_mapper.py` | **No** (advertised_services has no API surface at all) | **Yes** — `device_service.py:145-158` already shows the exact pattern to copy (`firmware_version` build-up before the `create_device(...)` call); `device_mapper.py:86-95` already shows where to add `connectivity=device.state.connectivity` next to `version_major`/`wifi_signal` |

### Flow 4: Firmware precedence at response time (the "unless a scenario overrides" clause)

This is the one part of the milestone that is **not** simply "follow the `advertised_services` pattern" — it activates a scenario capability that exists in the codebase today but has never been wired to any handler.

**Confirmed by reading the source, not assumed:** `ScenarioConfig.firmware_version` (`scenarios/models.py:46-48`) and `HierarchicalScenarioManager.get_firmware_version_override()` (`scenarios/manager.py:287-298`) exist, merge correctly through the five scope levels (`scenarios/manager.py:221-222`), and are unit-tested directly (`test_scenario_manager.py:358-363`) — but `get_firmware_version_override` has **zero call sites** anywhere in `packages/*/src`. `GetHostFirmwareHandler` (`handlers/device_handlers.py:141-155`) unconditionally reports `device_state.version_major`/`version_minor`, the values baked in at build time; it has no access to the resolved scenario at all, because `PacketHandler.handle(device_state, packet, res_required)` is never given one (`handlers/base.py`).

**Two independent precedence chains, not one:**
1. **Build-time (baked into `DeviceState`, immutable thereafter):** `DeviceBuilder.build()` calls `self._firmware_config.get_firmware_version(..., override=self._firmware_version)` (`factories/builder.py:261-264`). Extend this: if `connectivity == Connectivity.THREAD` and no explicit `with_firmware_version()` override was supplied, default to `(4, 200)` instead of the specs-derived default — a one-line change to the precedence already computed in `FirmwareConfig.get_firmware_version()`, keeping "explicit builder override always wins" as the existing rule.
2. **Response-time (the scenario override, wired for the first time):** Because `GetHostFirmwareHandler` cannot see the scenario, and because handlers must stay stateless and scenario-blind by design (`handlers/base.py`'s contract, and the "Anti-Patterns" entry in `.planning/codebase/ARCHITECTURE.md` about handlers never touching anything outside `device_state`), the override has to be applied the same way `malformed_packets`/`invalid_field_values` already are: as a post-processing stage in `EmulatedLifxDevice.process_packet()`, keyed on `resp_packet.PKT_TYPE == Device.StateHostFirmware.PKT_TYPE`, executed **before** `resp_packet.pack()` at `device.py:363` (mutating `version_major`/`version_minor` on the packet object, not the header). This sits naturally alongside `_apply_error_scenarios` (`device.py:375-413`) as a sibling stage — call it once, right after `_handle_packet_type` returns, so it composes correctly with `partial_responses` truncation which already runs at that point in `process_packet()`.

**Why this belongs in `device.py`, not `scenarios/manager.py` or the handler:** The manager's job is resolving *what the scenario says*, which it already does correctly (`get_firmware_version_override` is correct, just unused). The handler's job is producing the *default* answer, which it also already does correctly. The only layer that legitimately holds both "what did the handler produce" and "what does the resolved scenario say" at the same time is `EmulatedLifxDevice.process_packet()`, which is exactly where every other scenario-driven mutation (`malformed_packets`, `invalid_field_values`, `partial_responses`) already lives, per `.planning/codebase/ARCHITECTURE.md`'s own note: *"Scenario behaviour is applied in two places by design: ... capability filtering, partial responses, malformed/invalid-field mutation and send_unhandled in the device (device.py:281-460)."* Firmware override is a fourth member of that same family, not a new design.

## Scaling Considerations

Not applicable in the usual sense — this is a local test double, not a production service (`.planning/codebase/ARCHITECTURE.md`'s Cross-Cutting Concerns already states "Authentication: None... intended for local test use only"). The one scale axis worth naming:

| Axis | Consideration |
|------|----------------|
| Device count | `MdnsResponder`'s in-memory record dict is O(device count) per PTR query response, matching the existing O(N) broadcast fan-out noted in CONCERNS.md's "Scaling Limits"; fine at the tens-to-low-hundreds of devices this emulator targets, not designed for thousands |
| Socket count | Two UDP sockets (v4 LIFX, v6 LIFX) plus one multicast socket (mDNS) per server instance — triples the file descriptors and ephemeral-port pressure of today's single-socket model; worth a CI note (see Build Order, phase 6) since some sandboxes disable IPv6 or multicast |

## Anti-Patterns

### Anti-Pattern 1: Giving `EmulatedLifxDevice.process_packet()` a `family` parameter

**What people might do:** Thread the transport family all the way down to `process_packet()` "just in case a handler needs it," mirroring how `res_required` is already threaded through.
**Why it's wrong:** Per Flow 1 above, filtering is complete before `process_packet()` is ever called — a Thread device is simply not in `target_devices` for a mismatched-family or tagged packet. Adding `family` to `process_packet()` would be dead-weight plumbing with no consumer, and would tempt someone to duplicate the reachability check inside the device (two sources of truth for the same rule).
**Do this instead:** Keep the check exactly once, in `DeviceManager.resolve_target_devices`.

### Anti-Pattern 2: Checking `device.state.connectivity` inside `EmulatedLifxServer`

**What people might do:** Have the server itself decide "this looks like a Thread device, drop it if family is wrong," to avoid touching `DeviceManager`.
**Why it's wrong:** This is precisely the "server reaching into device state to make domain decisions" pattern the codebase already avoids (`.planning/codebase/ARCHITECTURE.md`'s Anti-Patterns: "Bypassing `DeviceManager` to mutate the repository or device list"). It would also duplicate logic that `resolve_target_devices` needs anyway for the broadcast-fan-out case, and it would make `EmulatedLifxServer` responsible for a Domain-layer decision, contrary to the Network layer's stated purpose ("route to devices," not "decide device eligibility").
**Do this instead:** `DeviceManager.resolve_target_devices(header, family)`, per Pattern 1.

### Anti-Pattern 3: Passing scenario config into `PacketHandler.handle()`

**What people might do:** To wire the firmware override, add a `scenario: ScenarioConfig` parameter to `PacketHandler.handle()` so `GetHostFirmwareHandler` can consult it directly.
**Why it's wrong:** This changes the signature of every one of the ~13 handler modules and the `PacketHandler` ABC itself (`handlers/base.py`), for a need that affects exactly one packet type. It also violates the existing contract that handlers operate purely on `DeviceState` (`.planning/codebase/ARCHITECTURE.md`'s "Anti-Patterns" section doesn't call this out explicitly, but the entire handler layer is built as stateless, scenario-blind functions of `(device_state, packet, res_required)` — introducing scenario-awareness into one handler breaks that uniformity for every handler author who reads the codebase afterwards).
**Do this instead:** Apply the override as a post-processing step in `process_packet()`, per Flow 4, alongside the existing `_apply_error_scenarios` stage.

### Anti-Pattern 4: A `zeroconf`-based responder for protocol-fidelity reasons alone

**What people might do:** Reach for `zeroconf` because it is the well-known Python mDNS library and "why reinvent DNS wire format."
**Why it's wrong here specifically:** Covered in Pattern 4 — the threading-model conflict with the documented single-event-loop constraint is the decisive reason, not a preference. A dependency that spawns its own thread for socket I/O undermines the exact guarantee (`.planning/codebase/ARCHITECTURE.md`: "Handlers must stay synchronous and non-blocking," "The only worker thread is...") that the rest of this codebase's design leans on.
**Do this instead:** Hand-rolled `mdns/records.py` + `mdns/responder.py`, scoped to exactly the query/answer shapes `lifx-async`'s fixtures require.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| `lifx-async` (sibling repo, acceptance oracle) | Imports `lifx_emulator` (core library) directly in `tests/conftest.py`; currently subclasses `EmulatedLifxServer` as `_Ipv6EmulatedLifxServer` to hand-bind a V6ONLY socket before `create_datagram_endpoint` | This milestone's `start()` must absorb that subclass's exact bind sequence (V6ONLY set **before** bind — `IPV6_V6ONLY` is immutable post-bind, raises `EINVAL` on macOS) so the subclass can be deleted; `lifx-async`'s `tests/test_api/test_ipv6_e2e.py` and `tests/test_network/test_mdns/test_discovery.py` fixtures are the executable contract for wire shapes, not just documentation |
| 224.0.0.251:5353 (mDNS multicast group) | `MdnsResponder` joins via `IP_ADD_MEMBERSHIP`; platform-specific `SO_REUSEADDR`/`SO_REUSEPORT` handling required (macOS `mDNSResponder` and Windows both already own 5353) | Out of scope: `ff02::fb` (IPv6 mDNS group) — `lifx-async` never queries it |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `LifxProtocol` (v4) ↔ `LifxProtocol` (v6) | No direct communication; both are independent instances of the same class sharing one `EmulatedLifxServer` | Each forwards its own transport + family into `handle_packet`; neither knows the other exists |
| `EmulatedLifxServer` ↔ `MdnsResponder` | Composition (owned sibling), constructor-injectable like every other collaborator (`storage`, `scenario_manager`, `activity_observer`) | `start()`/`stop()` cascade; `MdnsResponder` reads `device_manager.get_all_devices()` once at startup for seeding, then relies on the listener registry (Pattern 3) |
| `DeviceManager` ↔ `MdnsResponder` / WebSocket bridge | New multi-listener registry (Pattern 3), replacing today's single-slot `on_device_added`/`on_device_removed` | Both subscribers coexist; neither can starve the other of events |
| `EmulatedLifxDevice` ↔ transport family | **None** — deliberately no boundary here; see Anti-Pattern 1 | Filtering happens entirely upstream in `DeviceManager` |
| Core library ↔ app package | Unchanged direction (app depends on core, never the reverse); `connectivity`/mDNS config surfaces added to `config.py`/`api/models.py` are thin passthroughs to core factory/API parameters, following the `firmware_major`/`firmware_minor` (API) and `advertised_services` (config) precedents already in the codebase | No new app-layer business logic; the app package remains "a thin adapter layer (CLI + HTTP/WS) over the core library" per `.planning/codebase/ARCHITECTURE.md`'s Pattern Overview |

## Suggested Build Order

Per PROJECT.md's Key Decision ("Horizontal layers roadmap structure: finish core library changes, then CLI/config, then API, then assemble"), phased as:

**Phase A — Core: device identity (no networking).** `protocol/header.py` (`thread_connection` field + pack/unpack); `devices/states.py` (`Connectivity` enum, `NetworkState.connectivity`, routing table entry); `devices/device.py` (`_response_header_template` gets the bit — Pattern 2; new firmware-override stage in `process_packet()` — Flow 4); `factories/builder.py`/`factory.py` (Thread → 4.200 default, `with_connectivity()`); `handlers/device_handlers.py` (`GetWifiInfoHandler` signal 0.0); `devices/state_serializer.py`/`state_restorer.py` (connectivity round-trip). Fully testable with existing unit-test patterns (`EmulatedLifxDevice`, `LifxHeader`, no sockets). **No dependency on Phase B or C.**

**Phase B — Core: IPv6 transport.** `devices/manager.py` (`resolve_target_devices(header, family)` — Pattern 1); `server.py` (family-tagged `LifxProtocol`, transport threaded through `handle_packet`/`_process_device_packet`/`_send_ack`, v6 socket lifecycle in `start()`/`stop()`). **Depends on Phase A** (`device.state.connectivity` must exist for the reachability check). Independently testable without mDNS.

**Phase C — Core: mDNS responder.** `devices/manager.py` multi-listener registry (Pattern 3 — small, independent of Phase B, needed regardless of IPv6); new `mdns/` subpackage (Pattern 4); `EmulatedLifxServer` ownership/lifecycle. **Depends on Phase A** (connectivity, firmware fields feed TXT record content) but is **independent of Phase B** — the mDNS query channel is IPv4 multicast; it only needs to know the *configured* v6 advertise address as a string for AAAA records, not a working v6 socket. Note this for parallelization: B and C can be planned as parallel phases if the roadmap wants to split work, both gated only on A.

**Phase D — CLI/config.** `config.py` (`DeviceDefinition.connectivity` + validator, `EmulatorConfig` mDNS/IPv6 bind options); `__main__.py` (`--connectivity` flag — new relative to the `advertised_services` precedent, which had no CLI flag; wiring into factory calls and server construction; `_device_state_to_yaml_dict` export-config branch). **Depends on A, B, C** (needs the full core surface to expose).

**Phase E — API.** `api/models.py` (`DeviceCreateRequest.connectivity`, `DeviceInfo.connectivity`); `api/services/device_service.py`; `api/mappers/device_mapper.py`. **Depends on A** only, technically — could run parallel to D — but PROJECT.md's stated preference is strictly sequential (core → CLI/config → API), so keep it last unless the roadmap explicitly wants to parallelize D and E.

**Phase F — Assembly and verification against `lifx-async`.** Delete `_Ipv6EmulatedLifxServer` from `lifx-async/tests/conftest.py`; run `lifx-async`'s Thread and mDNS test suites (`tests/test_api/test_ipv6_e2e.py`, `tests/test_network/test_mdns/test_discovery.py`) against this milestone's emulator; confirm the full acceptance line from PROJECT.md end-to-end. Flag for this phase specifically: CI sandboxes that disable IPv6 or multicast will need a documented skip/xfail path — the existing `emulator_enabled` fixture in `lifx-async/tests/conftest.py` already skips the whole emulator suite on Windows for UDP timing flakiness, which is the precedent to extend rather than invent a new skip mechanism.

## Sources

- `.planning/PROJECT.md` — requirements, constraints, key decisions, hardware facts from `lifx-async` Phase 14 evidence
- `.planning/codebase/ARCHITECTURE.md` — layer boundaries, existing patterns, anti-patterns (authoritative for "how this codebase already does things")
- `.planning/codebase/CONCERNS.md` — `server.py:197,251,265` device-privates reach-through; `server.py:174-180`/`event_bridge.py:29-38` untracked fire-and-forget tasks
- `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `devices/device.py`, `devices/manager.py`, `devices/states.py`, `protocol/header.py`, `scenarios/models.py`, `scenarios/manager.py`, `handlers/device_handlers.py`, `factories/builder.py`, `factories/factory.py`, `devices/state_serializer.py`, `devices/state_restorer.py` — read directly to confirm current behaviour, including confirming `get_firmware_version_override` has no call sites and `advertised_services`/`firmware_version` are absent from `serialize_device_state`
- `packages/lifx-emulator/src/lifx_emulator_app/config.py`, `__main__.py`, `api/models.py`, `api/services/device_service.py`, `api/mappers/device_mapper.py`, `api/app.py`, `api/services/event_bridge.py` — read directly to confirm the app-layer precedent and the single-slot device-event callback limitation
- `git show --stat 91e58a9` (`feat: emit multi-service StateService discovery replies`, PR #156) and `git show --stat 4e2a8a4` — exact file list for the `advertised_services` precedent
- `/Volumes/External/Developer/Djelibeybi/lifx-async/tests/conftest.py:302-336` — `_Ipv6EmulatedLifxServer`, the V6ONLY-before-bind constraint this milestone must satisfy natively

---
*Architecture research for: Thread-device emulation (IPv6 transport, mDNS responder, connectivity) in the LIFX emulator*
*Researched: 2026-09-09*
