# Phase 1: Thread Device Identity - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

The core library (`lifx-emulator-core`) learns what a Thread device is, entirely in memory: a `connectivity` value on `NetworkState`, host firmware 4.200 with a hard floor, zero WiFi signal, per-tile firmware that mirrors the host, `connectivity` in persisted state, and frame-address flags bit 3 (`thread_connection`) on every header a Thread device emits. No sockets, no mDNS, no CLI, config or API surface — those are Phases 2 to 5.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**9 requirements are locked.** See `01-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `01-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `connectivity` on `NetworkState`, routed through `DeviceState._ATTRIBUTE_ROUTES`, immutable after construction
- `connectivity` argument on `create_device()`, all seven typed factories and `DeviceBuilder`
- Thread firmware default 4.200 and the 4.200 floor with `ValueError`
- Tile (55) special case: default 3.50 in `specs.yml`, terminal-firmware ceiling, Thread rejected; migration of the two SKY tests to another matrix product
- `wifi_signal = 0.0` at build time for Thread devices
- Per-tile firmware mirroring host firmware for all matrix devices
- `connectivity` in `serialize_device_state()` / `StateRestorer` with missing-key and bad-value handling
- `LifxHeader.thread_connection` (bit 3) pack/unpack
- Bit 3 stamped on every reply header of a Thread device via the per-device header template; never on a WiFi device
- Byte fixtures for WiFi output and header round trips, captured before the change
- Unit tests for all of the above in `packages/lifx-emulator-core/tests/`

**Out of scope (from SPEC.md):**
- IPv6 socket, address-family routing, dropping IPv4 or tagged packets aimed at Thread devices — Phase 2 (NET-*)
- mDNS responder, TXT records, AAAA advertisement — Phase 3 (MDNS-*)
- CLI flags, YAML `DeviceDefinition.connectivity`, `export-config` — Phase 4 (CFG-*)
- `DeviceCreateRequest.connectivity`, `DeviceInfo.connectivity`, `DeviceMapper` — Phase 5 (API-*)
- Wiring the `firmware_version` scenario into firmware replies — dead code today; dropped from CONN-02, recorded as a known gap
- Persisting `firmware_version` and `advertised_services` — pre-existing round-trip gap, unchanged
- Any behaviour change for incoming packets whose header has bit 3 set — unpacked faithfully and ignored
- Product-level Thread gating for any product other than Tile (55)
- Dashboard or frontend changes — deferred milestone (UI-01/02)
- Edits to `protocol/packets.py` or `products/registry.py` — generated files

</spec_lock>

<decisions>
## Implementation Decisions

### Connectivity type
- **D-01:** `connectivity` is a `class Connectivity(str, Enum)` with `WIFI = "wifi"` and `THREAD = "thread"`, mirroring `lifx-async`'s `Connectivity(str, Enum)` in `src/lifx/devices/base.py`. It compares equal to the plain strings, serialises to JSON as the string, and is accepted directly by Pydantic in Phases 4 and 5. — **Reversibility:** costly — it becomes part of the published `lifx_emulator` API; changing the type after release breaks every library consumer that imports it.
- **D-02:** The enum is defined in `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` beside `NetworkState` and added to the `__all__` of both `lifx_emulator.devices` and `lifx_emulator`, so consumers write `from lifx_emulator import Connectivity`.
- **D-03:** `create_device()`, every typed factory and `DeviceBuilder.with_connectivity()` take `connectivity: Connectivity | str | None = None`. `None` means "unspecified" (WiFi unless persisted state says otherwise, see D-09); strings are coerced with `Connectivity(value)`, which is what makes `"Thread"` or `"bluetooth"` raise the `ValueError` the spec requires. The coercion message must name the accepted values.

### Firmware rule placement
- **D-04:** `ProductSpecs` in `products/specs.py` gains `max_firmware_major` / `max_firmware_minor` (a terminal-firmware ceiling), loaded from new optional keys in `products/specs.yml`. Product 55 gets `default_firmware_major: 3`, `default_firmware_minor: 50`, `max_firmware_major: 3`, `max_firmware_minor: 50` with a note that Tile is discontinued at 3.50. No other product sets a ceiling. — **Reversibility:** reversible — a data-file key with one consumer.
- **D-05:** The Thread default and floor are one constant, `FirmwareConfig.VERSION_THREAD = (4, 200)`, beside the existing `VERSION_EXTENDED = (3, 70)` and `VERSION_LEGACY = (2, 60)` in `factories/firmware_config.py`.
- **D-06:** All firmware validation lives in `FirmwareConfig.get_firmware_version()`, which gains a `connectivity` argument (four parameters plus `self`, within the max-args budget). Precedence becomes: explicit override > Thread default (`VERSION_THREAD` when Thread and no override) > `specs.yml` product default > extended-multizone flag. After resolution it raises `ValueError` if a Thread device's version is below `VERSION_THREAD`, or if any device's version exceeds the product's `max_firmware`. Thread-on-Tile is rejected by those two rules alone (ceiling 3.50 < floor 4.200), with a message naming both; there is no pid-specific code anywhere. `DeviceBuilder.build()` step 3 passes connectivity through and does not validate itself.

### Immutability mechanism
- **D-07:** `NetworkState` becomes `@dataclass(frozen=True)`. Build-time changes replace the object wholesale with `dataclasses.replace(state.network, ...)`, which `DeviceState.__setattr__` already permits because `network` is in its direct-assignment set. `wifi_signal` is frozen too; nothing writes it at runtime today (`api/models.py:92` only reads it). — **Reversibility:** reversible — a single dataclass decorator and a handful of `replace()` call sites.
- **D-08:** Because a frozen dataclass raises `FrozenInstanceError` (an `AttributeError` subclass), `DeviceState.__setattr__` catches it on routed writes to the `network` sub-state and re-raises `ValueError` with a message stating that connectivity is fixed at creation. That satisfies the SPEC's "reassignment raises `ValueError`" for `state.connectivity = ...`; a direct `state.network.connectivity = ...` raises `FrozenInstanceError`, which is acceptable and should be documented in the `NetworkState` docstring.
- **D-09:** When persistence is enabled and the saved `connectivity` disagrees with the factory argument: an explicit `"wifi"` / `"thread"` argument wins and a `WARNING` is logged naming the serial, the saved value and the value kept; `connectivity=None` defers to the saved value; no saved key or an unrecognised saved value means WiFi (unrecognised logs a `WARNING`, per SPEC). This mirrors the product-mismatch handling already in `StateRestorer.restore_if_available()`.
- **D-10:** `DeviceBuilder.build()` resolves the effective connectivity as a new step 0 (argument > saved state > WiFi), before firmware resolution, so firmware, `wifi_signal`, the `has_sensor` flag and per-tile firmware are each derived exactly once from the effective value. `StateRestorer` no longer touches connectivity after the state is composed; it may expose a small "peek saved connectivity" helper the builder calls, or the builder may read `storage.load_device_state(serial)` itself — planner's choice, but the saved file must be read once, not twice. — **Reversibility:** costly — reordering `build()` touches every derived field; undoing it later means re-deriving four values after restore instead.

### Byte fixtures and test layout
- **D-11:** Pre-change fixtures are inline `bytes.fromhex("...")` constants in the test module, each commented with the commit hash of the unmodified `main` they were captured from. No `tests/fixtures/` directory is introduced.
- **D-12:** The first plan task captures the fixtures by running the unmodified code once (a WiFi device's packed `StateService`, `StateColor`, `Acknowledgement` and `StateUnhandled` replies, plus a header pack/unpack round trip), commits them, and only then may `header.py` change. The fixture commit precedes the behaviour change in history so the diff proves the bytes are unchanged.
- **D-13:** New tests go in a new `packages/lifx-emulator-core/tests/test_thread_identity.py` (factories and coercion, firmware floor and Tile ceiling, `wifi_signal`, bit-on-every-reply across all five reply shapes, multi-packet replies, mixed fleet, WiFi byte fixtures) and a new `test_header.py` (`LifxHeader.thread_connection` pack/unpack, single-byte difference, reserved bits, short-data error). Module-local cases join their existing modules: persistence round trip and bad/missing key in `test_async_storage.py`, Tile ceiling and `max_firmware` loading in `test_products_specs.py`, per-tile firmware mirror in `test_tile_handlers_extended.py`. The two migrated SKY tests stay in `test_tile_handlers_extended.py` on a non-Ceiling matrix product (Candle Colour, pid 185, is the suggested target).

### Claude's Discretion
- Where the bad-persisted-value `WARNING` is emitted (builder step 0 or a restorer helper), as long as it is logged once with `%s`-style lazy formatting.
- The name and location of the string-to-enum coercion helper, provided every factory and the builder share one implementation.
- How `EmulatedLifxDevice.__init__` reads the host version for the tile-firmware mirror (it already has `self.state.version_major` / `version_minor` in scope).
- Stamping `thread_connection` on the pre-allocated response header template in `EmulatedLifxDevice.__init__` is the research-recommended single point (`.planning/research/ARCHITECTURE.md` "Header template"); the planner should follow it unless a concrete reason emerges.
- Test serials from the `d073d50000xx` range and any new `conftest.py` fixtures (e.g. `thread_color_device`, `thread_ceiling_device`).
- Whether `Connectivity` also gets a `__str__` returning the value; harmless either way since `str, Enum` members already format as the value in f-strings on Python 3.11+, but Python 3.10 formats as `Connectivity.THREAD`, so any log line that prints it should use `.value` explicitly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/01-thread-device-identity/01-SPEC.md` — Locked requirements, boundaries, 30 acceptance criteria, edge coverage and prohibitions — MUST read before planning

### Design research (this milestone)
- `.planning/research/ARCHITECTURE.md` — "Header template" section (single stamping point for bit 3), "Firmware override" section (two precedence chains; scenario wiring explicitly out of scope now), persistence table (why `connectivity` is persisted while `firmware_version` is not)
- `.planning/research/PITFALLS.md` — Pitfall 6: forgetting acks and `StateUnhandled` when stamping bit 3; the "one test, all reply shapes" recommendation the SPEC adopts

### Wire contract (sibling repo, absolute paths)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/protocol/header.py` — `thread_connection` is frame-address byte 22 bit 3; device-side report only; reserved bits 2 and 4-7 emitted as zero (lines ~141-162, ~207-224)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/devices/base.py` — `class Connectivity(str, Enum)` (line 79) that D-01 mirrors
- `/Volumes/External/Developer/Djelibeybi/lifx-async/tests/test_network/test_connection_connectivity.py` — how the client reads the bit from correlated responses

### Codebase maps
- `.planning/codebase/TESTING.md` — Test layout, naming, fixture and assertion conventions D-11 to D-13 follow
- `.planning/codebase/CONVENTIONS.md` — Naming, error-handling (`ValueError` with f-string message), logging (`%s` lazy formatting), docstring conventions

### Product data
- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml` — Where D-04 adds `max_firmware_*` and Tile's 3.50 default; header comment documents the firmware precedence that D-06 extends

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EmulatedLifxDevice._response_header_template` (`devices/device.py:91`) and `_create_response_header()` (`device.py:218`): every reply header, including both ack paths and `StateUnhandled`, is a `copy.copy()` of this one template — stamp `thread_connection` there once.
- `FirmwareConfig.get_firmware_version()` (`factories/firmware_config.py`): already the single firmware precedence chain; D-06 extends it rather than adding a second.
- `ProductSpecs` / `SpecsRegistry` (`products/specs.py`) with `default_firmware_major/minor` and `has_firmware_specs`: the exact pattern for D-04's `max_firmware_*` keys.
- `StateRestorer.restore_if_available()` (`devices/state_restorer.py:32`): product-mismatch warning is the template for D-09's connectivity-mismatch warning; `_restore_core_state` shows the "if key in saved_state" style.
- `serialize_device_state()` / `deserialize_device_state()` (`devices/state_serializer.py:89,186`): add the `connectivity` key here; the buttons_config block shows tolerant handling of hand-edited files.
- `DeviceState._ATTRIBUTE_ROUTES` and `_OPTIONAL_DEFAULTS` (`devices/states.py:263-354`): add `"connectivity": "network"` to the routing table.
- Existing `advertised_services` plumbing (PR #156): the precedent for threading one per-device value through `create_device()`, every typed factory, `DeviceBuilder.with_*()` and `_create_core_state()`.

### Established Patterns
- Handlers are stateless and scenario-blind; `GetWifiInfoHandler` simply returns `device_state.wifi_signal`, so storing 0.0 in state (SPEC R4) needs no handler change.
- `DeviceState.__setattr__` bypasses routing for the sub-state names (`network` included), which is what lets D-07 replace a frozen `NetworkState` wholesale.
- `ValueError` with an f-string message for argument validation; `logger.warning("...%s", ...)` lazy formatting; Australian English in prose and comments.
- Tests: every test in a `Test*` class with docstrings, `pytest.raises(ValueError, match=...)`, factory-built devices rather than hand-built state, canonical serials `d073d5000001..12`.

### Integration Points
- `protocol/header.py` (hand-written): add the `thread_connection` field, pack bit 3, unpack bit 3.
- `devices/states.py`: `Connectivity` enum, frozen `NetworkState(connectivity, wifi_signal)`, routing entry, `__setattr__` translation (D-08).
- `factories/builder.py`: step 0 connectivity resolution (D-10), `with_connectivity()`, frozen `NetworkState` construction with `wifi_signal` derived, firmware call with connectivity, tile firmware no longer hard-coded downstream.
- `factories/factory.py`: `connectivity` parameter on `create_device()` and all seven typed factories.
- `devices/device.py`: template stamping; per-tile `firmware_version_major/minor` from `self.state.version_major/minor` instead of 3/70.
- `devices/state_serializer.py`, `devices/state_restorer.py`: persistence of `connectivity`.
- `products/specs.py`, `products/specs.yml`: `max_firmware_*` keys and Tile entries.
- `lifx_emulator/__init__.py`, `lifx_emulator/devices/__init__.py`: export `Connectivity`.

</code_context>

<specifics>
## Specific Ideas

- Mirror `lifx-async` exactly where a choice is arbitrary: the enum shape (`str, Enum`, lowercase values) and the bit position both come from the sibling repo, which is the acceptance oracle for Phase 6.
- The fixture commit must land before the header change so a reviewer can see the WiFi bytes did not move; this ordering is a deliberate part of the plan, not a nicety.
- Thread-on-Tile must fall out of the generic floor/ceiling rules with no `55` literal in Python; the only place pid 55 appears is `specs.yml`.

</specifics>

<deferred>
## Deferred Ideas

- Wiring the `firmware_version` scenario into `StateHostFirmware` / `StateWifiFirmware` replies — dead code today; not part of this milestone (recorded in SPEC.md Boundaries).
- Persisting `firmware_version` and `advertised_services` so they survive a `--persistent` restart — pre-existing gap noted in `.planning/research/ARCHITECTURE.md`; a later milestone.
- A `thread_capable` per-product spec key — rejected for now (Tile's ceiling makes it redundant); revisit only if a product ever needs to opt out of Thread without a firmware ceiling.

None of these came up as scope creep during discussion; they are recorded so later phases know they were considered.

</deferred>

---

*Phase: 01-thread-device-identity*
*Context gathered: 2026-09-09*
