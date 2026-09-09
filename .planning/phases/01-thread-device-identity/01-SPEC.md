# Phase 1: Thread Device Identity — Specification

**Created:** 2026-09-09
**Ambiguity score:** 0.10 (gate: ≤ 0.20)
**Requirements:** 9 locked

## Goal

A core-library device created with `connectivity="thread"` reports host firmware 4.200, zero WiFi signal and frame-address flags bit 3 on every header it emits, survives a persistence round trip as a Thread device, and a WiFi device's wire output is byte-for-byte unchanged — entirely in memory, with no transport, CLI, config or API changes.

## Background

`LifxHeader` (`packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py`) is hand-written and packs only bits 0-1 (`res_required`, `ack_required`) of the frame-address flags byte; bit 3 (`thread_connection` in `lifx-async`'s `src/lifx/protocol/header.py:144,209`) does not exist as a field. Every reply header a device emits — normal `State*` replies, multi-packet lists, the `Acknowledgement` built by `EmulatedLifxServer._send_ack()` and the one built inside `EmulatedLifxDevice.process_packet()` when a scenario targets acks, and `StateUnhandled` — is a `copy.copy()` of one per-device template built in `EmulatedLifxDevice.__init__` (`devices/device.py:91`).

`NetworkState` (`devices/states.py:48`) holds only `wifi_signal = -45.0`. There is no `connectivity` field anywhere. `DeviceBuilder.build()` (`factories/builder.py:248`) resolves firmware through `FirmwareConfig.get_firmware_version()` with precedence explicit override > `specs.yml` product default > extended-multizone flag (3.70 / 2.60). It also derives `has_sensor` from `version_major >= 4`, so any device at firmware 4.x reports an ambient light sensor. `EmulatedLifxDevice.__init__` hard-codes every tile's `firmware_version_major/minor` to 3.70 in `StateDeviceChain`, even for a WiFi Ceiling whose host firmware is 4.10 from `specs.yml`.

`serialize_device_state()` (`devices/state_serializer.py:89`) persists neither firmware version nor `advertised_services`; `StateRestorer` reads only known keys and ignores the rest. `ScenarioConfig.firmware_version` and `HierarchicalScenarioManager.get_firmware_version_override()` exist and are unit-tested but have zero call sites in `src/` — the scenario is dead code and stays that way in this phase.

The original LIFX Tile (product 55) is discontinued with terminal firmware 3.50; the emulator currently defaults it to 3.70, and two tests in `test_tile_handlers_extended.py` (lines 723 and 931) create it at 4.4 to prove the SKY effect is ignored on a non-Ceiling matrix device.

## Requirements

1. **Connectivity field (CONN-01)**: Every device carries a `connectivity` value of `"wifi"` (default) or `"thread"` on `NetworkState`, settable through `create_device()` and every typed factory (`create_color_light`, `create_color_temperature_light`, `create_infrared_light`, `create_hev_light`, `create_multizone_light`, `create_tile_device`, `create_switch`) and through `DeviceBuilder`.
   - Current: No `connectivity` field exists; `NetworkState` holds only `wifi_signal`.
   - Target: `state.connectivity` reads `"wifi"` when the argument is omitted or `None`, `"thread"` when passed; the match is exact and lowercase, so `"Thread"`, `"THREAD"` or any other string raises `ValueError` at creation; assigning `state.connectivity` after construction raises `ValueError` (the radio is immutable, as on real hardware).
   - Acceptance: A parametrised test over all seven typed factories plus `create_device()` asserts the default, the explicit Thread value, `ValueError` for `"Thread"` and `"bluetooth"`, and `ValueError` on post-construction reassignment. `create_tile_device` is parametrised as an expected-`ValueError` case for the Thread value: it hard-codes product 55, whose terminal-firmware ceiling makes Thread unresolvable (see requirement 3).

2. **Thread firmware default and floor (CONN-02)**: Creating a Thread device with no explicit firmware yields host firmware 4.200; Thread requires 4.200 or higher.
   - Current: Firmware comes from explicit override > `specs.yml` > extended-multizone flag; nothing knows about Thread.
   - Target: With `connectivity="thread"` and `firmware_version=None`, `version_major == 4` and `version_minor == 200` regardless of any `specs.yml` product default; an explicit `firmware_version` of `(4, 200)` or higher (e.g. `(4, 201)`, `(5, 0)`) is accepted as given; an explicit value below `(4, 200)` (e.g. `(4, 199)`, `(3, 70)`) raises `ValueError` naming the floor. The `firmware_version` scenario is not wired in this phase (recorded gap, see Boundaries).
   - Acceptance: Tests assert 4.200 default for a Thread device of a product with a `specs.yml` firmware default (Ceiling, 4.10) and one without (colour bulb); `(4, 200)` and `(5, 0)` accepted; `(4, 199)` and `(3, 70)` raise `ValueError`; a WiFi device's firmware resolution is unchanged.

3. **Tile exception**: The original LIFX Tile (product 55) is the single product that cannot be Thread, and it can never report firmware above its terminal 3.50.
   - Current: Tile defaults to 3.70 and accepts any explicit firmware; two tests create it at 4.4.
   - Target: `specs.yml` records Tile's default firmware as 3.50; `create_device(55, connectivity="thread")` raises `ValueError`; an explicit `firmware_version` above `(3, 50)` for product 55 raises `ValueError`; `(3, 50)` and lower are accepted; every other product ID in the registry can be created as Thread. The two SKY-effect tests migrate to a non-Ceiling matrix product that can run 4.4 (e.g. Candle Colour, pid 185) with their assertions unchanged.
   - Acceptance: Tests assert Tile default 3.50, `ValueError` for Thread on 55, `ValueError` for `(3, 51)` on 55, success for `(3, 50)` on 55; a parametrised test over every matrix product ID except 55 creates a Thread device successfully; the migrated SKY tests pass.

4. **WiFi reporting on Thread (CONN-03)**: A Thread device reports no WiFi radio signal but answers firmware queries normally.
   - Current: `wifi_signal` defaults to -45.0 for every device; `GetWifiInfo` returns it verbatim.
   - Target: A Thread device's `NetworkState.wifi_signal` is 0.0 at build time; `GetWifiInfo` (16) returns `StateWifiInfo` (17) with `signal == 0.0`; `GetWifiFirmware` (18) and `GetHostFirmware` (14) return the same packet shapes as for a WiFi device, carrying the device's firmware (4.200 by default). A Thread device at 4.200 reports the ambient light sensor exactly as any other firmware-4 device does (existing `has_sensor` rule, no special case).
   - Acceptance: One test sends all three Get packets to a Thread device and asserts `signal == 0.0`, `StateHostFirmware.version_major/minor == (4, 200)`, and `StateWifiFirmware` present with the same version; a WiFi device still reports -45.0.

5. **Per-tile firmware mirrors host**: Every freshly constructed matrix device's tiles report the device's host firmware.
   - Current: `EmulatedLifxDevice.__init__` hard-codes 3.70 per tile for all matrix devices.
   - Target: Each entry in `tile_devices` built by `EmulatedLifxDevice.__init__` has `firmware_version_major/minor` equal to the device's `version_major/minor` for WiFi and Thread devices alike. This is an intentional default-output change: a WiFi Ceiling now reports 4.10 per tile instead of 3.70. A device restored from persisted state is excluded: `StateRestorer._restore_matrix_state()` replaces `tile_devices` wholesale with the saved list, and host firmware is not persisted, so a file written before this phase restores tile 3.70 against host 4.10. That restore boundary is deliberately unchanged here.
   - Acceptance: Tests assert a freshly constructed Thread Ceiling reports 4.200 per tile in `StateDeviceChain` (702), a WiFi Ceiling reports 4.10, and a WiFi Candle without a `specs.yml` firmware default reports 3.70. No assertion is made about restored devices.

6. **Persistence round trip (CONN-04)**: `connectivity` survives save and restore.
   - Current: `serialize_device_state()` has no `connectivity` key; `StateRestorer` does not read one.
   - Target: `serialize_device_state()` writes `"connectivity": "wifi" | "thread"`; `StateRestorer` restores it before the device's response header template is built, so a reloaded Thread device is still Thread; a file with no `connectivity` key (written before this milestone) restores as `"wifi"`; a file with an unrecognised value (e.g. `"bluetooth"`) logs a warning, restores everything else and treats the device as `"wifi"`. A file written by this version still loads in the previous version, which ignores unknown keys.
   - Acceptance: Round-trip test through `DevicePersistenceAsyncFile` for a Thread device asserts `connectivity == "thread"` and bit 3 set on a reply after reload; a fixture file lacking the key restores as WiFi; a fixture with `"bluetooth"` restores as WiFi with a `WARNING` log record captured.

7. **Header bit 3 (HDR-01)**: `LifxHeader` gains `thread_connection` as frame-address flags bit 3.
   - Current: `pack()` emits only bits 0-1; `unpack()` reads only bits 0-1.
   - Target: `LifxHeader(thread_connection=True).pack()` differs from the same header with `False` in exactly byte 22, bit 3; `unpack()` recovers the bit; `thread_connection` defaults to `False`; bits 2 and 4-7 stay zero on pack; data shorter than 36 bytes still raises `ValueError`.
   - Acceptance: Every existing header test passes unchanged; a new test packs and unpacks a header with the bit set and clear and asserts the single-byte difference and full round trip; a byte-fixture test asserts a header with the bit clear packs to the identical bytes captured before this change.

8. **Thread bit on every reply (HDR-02)**: A Thread device sets bit 3 on every header it emits.
   - Current: No reply carries bit 3.
   - Target: For a Thread device, `thread_connection` is `True` on: a single `State*` reply (e.g. `StateColor`), every packet of a multi-packet reply (`StateMultiZone` list from a `GetColorZones` spanning 16+ zones; `State64` replies from a large matrix device read with two `Get64` requests, and from a chained matrix device answered with `length=2`), the `Acknowledgement` (45) sent by the server fast path, the `Acknowledgement` built inside `process_packet()` when a scenario targets acks, and `StateUnhandled` (223). The bit remains set on packets that survive `partial_responses` truncation and on `malformed_packets` payload truncation (the header is untouched). A WiFi and a Thread device in the same `DeviceManager` each carry their own bit.
   - Acceptance: One test drives a single Thread **multizone** device through `StateColor`, both acknowledgement paths, `StateUnhandled` and every packet of the `StateMultiZone` list, asserting the bit on every returned header; two matrix tests assert the bit on `State64` replies from a large matrix device (two `Get64` requests) and from a chained matrix device (`length=2`); a further test asserts the mixed-fleet case. The multizone and matrix shapes are covered by separate devices because no registry product carries both capabilities (amended after cross-AI review round 2, `d626690`).

9. **WiFi output unchanged (HDR-03)**: A WiFi device never sets bit 3.
   - Current: Bit 3 is never set (it does not exist).
   - Target: Every reply from a WiFi device, including acks and `StateUnhandled`, has bit 3 clear and packs to the same bytes as before this phase.
   - Acceptance: Byte-fixture test compares a WiFi device's `StateService`, `StateColor`, `Acknowledgement` and `StateUnhandled` packed replies against fixtures captured on `main` before this phase; all existing tests pass without modification other than the two migrated SKY tests.

## Boundaries

**In scope:**
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
- A bytes-aware branch in `EmulatedLifxServer._process_device_packet()`'s reply-payload assignment, so that a `malformed_packets` or `invalid_field_values` scenario — whose payload `_apply_error_scenarios()` already returns as `bytes` — reaches the transport instead of raising `AttributeError`. Repair of a pre-existing defect on `main`, added after cross-AI review round 2 (`d626690`) surfaced it; exercised through an in-process recording transport double, never a socket
- Unit tests for all of the above in `packages/lifx-emulator-core/tests/`

**Out of scope:**
- IPv6 socket, address-family routing, dropping IPv4 or tagged packets aimed at Thread devices — Phase 2 (NET-*)
- mDNS responder, TXT records, AAAA advertisement — Phase 3 (MDNS-*)
- CLI flags, YAML `DeviceDefinition.connectivity`, `export-config` — Phase 4 (CFG-*)
- `DeviceCreateRequest.connectivity`, `DeviceInfo.connectivity`, `DeviceMapper` — Phase 5 (API-*)
- Wiring the `firmware_version` scenario into firmware replies — dead code today; a Thread device would not participate in a sub-4.200 scenario, so the clause is dropped from CONN-02 and the gap is recorded for a later milestone
- Persisting `firmware_version` and `advertised_services` — pre-existing round-trip gap, unchanged by this phase
- Any behaviour change for incoming packets whose header has bit 3 set — the bit is unpacked faithfully and ignored; replies reflect the device's connectivity only
- Product-level Thread gating for any product other than Tile (55) — recorded decision: any product is testable as Thread
- Dashboard or frontend changes — deferred milestone (UI-01/02)
- Edits to `protocol/packets.py` or `products/registry.py` — generated files, no Thread changes belong there

## Constraints

- Python 3.10-3.14, portable; no networking in this phase, so no socket code. The one exception, added after cross-AI review round 2 (`d626690`) and approved by the developer, is a bytes-aware branch in `EmulatedLifxServer._process_device_packet()` repairing a pre-existing send-path defect: it is exercised through an in-process recording transport double assigned to the plain `server.transport` attribute, and no socket is opened, bound or connected anywhere in this phase
- Cyclomatic complexity ≤ 10, Pyright standard, Ruff; imports at top of file; Australian English in prose and comments
- `protocol/packets.py` and `products/registry.py` are generated and must not be edited; `header.py` is hand-written and may be
- Header bit 3 semantics must match `lifx-async` `src/lifx/protocol/header.py` exactly: bit 3 of frame-address byte 22, device-side report only
- `connectivity` defaults to `"wifi"`; default WiFi wire output is byte-for-byte unchanged
- Thread firmware floor is 4.200 (major 4, minor 200); Tile (55) firmware ceiling is 3.50
- The response header template in `EmulatedLifxDevice` is built once per device; immutability of `connectivity` is what keeps it valid
- Conventional commits with `core-` scope, GPG-signed `-s` commits; 80% coverage gate must still pass

## Acceptance Criteria

- [ ] `create_device(pid)` and every typed factory yield `state.connectivity == "wifi"` when the argument is omitted or `None`
- [ ] `create_device(pid, connectivity="thread")` and every typed factory except `create_tile_device` yield `state.connectivity == "thread"`; `create_tile_device(connectivity="thread")` raises `ValueError`, because it hard-codes product 55 whose terminal-firmware ceiling (3.50) sits below the Thread floor (4.200)
- [ ] `connectivity="Thread"` and `connectivity="bluetooth"` raise `ValueError` at creation
- [ ] Assigning `state.connectivity` after construction raises `ValueError`
- [ ] A Thread device with no explicit firmware reports host firmware `(4, 200)`, including for Ceiling whose `specs.yml` default is 4.10
- [ ] Explicit `firmware_version=(4, 200)` and `(5, 0)` on a Thread device are accepted as given
- [ ] Explicit `firmware_version=(4, 199)` and `(3, 70)` on a Thread device raise `ValueError`
- [ ] Product 55 defaults to firmware `(3, 50)`; explicit `(3, 50)` is accepted; explicit `(3, 51)` raises `ValueError`
- [ ] `create_device(55, connectivity="thread")` raises `ValueError`
- [ ] Every matrix product ID in the registry other than 55 can be created with `connectivity="thread"`
- [ ] The two SKY-effect tests formerly using product 55 at 4.4 pass on a non-Ceiling matrix product with unchanged assertions
- [ ] A Thread device's `NetworkState.wifi_signal` is `0.0` and `GetWifiInfo` returns `StateWifiInfo(signal=0.0)`
- [ ] `GetHostFirmware` and `GetWifiFirmware` to a Thread device return `(4, 200)` in the same packet shapes as a WiFi device
- [ ] A WiFi device still reports `wifi_signal == -45.0`
- [ ] A Thread device at 4.200 reports `ambient_light_lux == 100.0` (existing firmware-4 sensor rule, no special case)
- [ ] Every tile of a freshly constructed matrix device reports the host firmware in `StateDeviceChain`: Thread Ceiling 4.200, WiFi Ceiling 4.10, WiFi Candle 3.70. A device restored from persisted state keeps its saved per-tile firmware and is out of scope
- [ ] `serialize_device_state()` output contains `"connectivity"`; a Thread device reloaded through `DevicePersistenceAsyncFile` is still Thread and sets bit 3 on its first reply
- [ ] A persisted file with no `connectivity` key restores as `"wifi"`
- [ ] A persisted file with `"connectivity": "bluetooth"` restores as `"wifi"`, restores all other fields, and emits a `WARNING` log record
- [ ] `LifxHeader` exposes `thread_connection` defaulting to `False`; packing with `True` vs `False` differs only in byte 22 bit 3; `unpack()` round-trips the bit
- [ ] A header with `thread_connection=False` packs to bytes identical to a fixture captured before this phase; bits 2 and 4-7 of byte 22 are zero
- [ ] `LifxHeader.unpack()` on fewer than 36 bytes still raises `ValueError`
- [ ] One test on a single Thread **multizone** device asserts bit 3 set on: `StateColor`, fast-path `Acknowledgement`, scenario-path `Acknowledgement` (scenario `response_delays={45: 0.01}`), `StateUnhandled` (Light packet to a switch, or `send_unhandled` with an unknown type), and every packet of a `StateMultiZone` list. Separately, `State64` replies carry bit 3 on a large matrix device (product 201, read with two `Get64` requests, `y=0` then `y=4`, `width=16`, one 64-colour `State64` each) and on a chained matrix device (`tile_count=2`, one `Get64` with `length=2`, two `State64` replies). No product in the registry is both multizone and matrix, so one device cannot cover both reply shapes — amended after cross-AI review round 2 (`d626690`), which found the single-device wording unsatisfiable
- [ ] Bit 3 stays set on the surviving packets after a `partial_responses` truncation and on a `malformed_packets` truncated reply from a Thread device
- [ ] A WiFi and a Thread device in one `DeviceManager` each answer with their own bit
- [ ] A WiFi device's packed `StateService`, `StateColor`, `Acknowledgement` and `StateUnhandled` replies match byte fixtures captured before this phase
- [ ] All pre-existing tests pass unmodified except the two migrated SKY tests; `ruff check`, `ruff format --check`, `pyright` and the 80% coverage gate pass
- [ ] MUST NOT: no code path converts a requested Thread device to WiFi or vice versa without raising, except the bad-persisted-value fallback which logs a `WARNING`
- [ ] MUST NOT: no product ID other than 55 is rejected for `connectivity="thread"`
- [ ] MUST NOT: no WiFi reply and no header round trip differs byte-for-byte from the pre-phase fixtures
- [ ] MUST NOT: `git diff main -- packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` is empty at phase end

## Edge Coverage

**Coverage:** 35/35 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ⛔ dismissed | `connectivity` is a two-value scalar; no collection to merge or collide |
| empty | R1 | ✅ covered | Omitted or `None` → `"wifi"` (AC 1) |
| ordering | R1 | ⛔ dismissed | Scalar field; no ordering |
| encoding | R1 | ✅ covered | Exact lowercase match; `"Thread"` raises `ValueError` (AC 3) — engine missed, added |
| idempotency | R1 | ✅ covered | Any post-construction assignment raises, including the same value (AC 4) — engine missed, added |
| boundary | R2 | ✅ covered | `(4, 200)` accepted, `(4, 199)` raises, `(5, 0)` accepted (AC 6, 7) |
| adjacency | R2 | ⛔ dismissed | Scalar version tuple; no collection |
| empty | R2 | ✅ covered | `firmware_version=None` on Thread → `(4, 200)` (AC 5) |
| ordering | R2 | ⛔ dismissed | Scalar; no ordering |
| precision | R2 | ⛔ dismissed | Major and minor are integers packed as uint16 with no arithmetic; 200 fits |
| adjacency | R3 | ⛔ dismissed | Single product-ID exception; no collection |
| empty | R3 | ⛔ dismissed | Product ID is always present; no empty case |
| ordering | R3 | ⛔ dismissed | No ordering |
| boundary | R3 | ✅ covered | Tile `(3, 50)` accepted, `(3, 51)` raises; default 3.50 (AC 8) — engine missed, added |
| unclassified | R4 | ✅ covered | Explicit ACs for signal 0.0 and both firmware replies (AC 12, 13); scenario mutation of `StateWifiInfo` is orthogonal and unchanged |
| adjacency | R5 | ⛔ dismissed | Tiles are mirrored independently; no merge semantics |
| empty | R5 | ⛔ dismissed | `specs.yml` `min_tile_count` is ≥ 1 for every matrix product; an empty tile list cannot be built |
| ordering | R5 | ⛔ dismissed | Tile order is unchanged by this phase |
| boundary | R5 | ✅ covered | WiFi Ceiling default-output change 3.70 → 4.10 asserted (AC 16) — engine missed, added |
| concurrency | R6 | ⛔ dismissed | `connectivity` is immutable, so the debounced writer can never observe two values for one device |
| empty | R6 | ✅ covered | Missing key → `"wifi"` (AC 18) — engine missed, added |
| encoding | R6 | ✅ covered | Unrecognised value → warn + `"wifi"` (AC 19) — engine missed, added |
| boundary | R7 | ✅ covered | Set vs clear differs only in byte 22 bit 3; reserved bits zero (AC 20, 21) |
| adjacency | R7 | ⛔ dismissed | Single bit in a fixed-layout struct |
| empty | R7 | ✅ covered | < 36 bytes still raises (AC 22) |
| ordering | R7 | ⛔ dismissed | Fixed struct layout |
| precision | R7 | ⛔ dismissed | One bit; no numeric precision |
| adjacency | R8 | ✅ covered | Mixed WiFi + Thread fleet in one manager, each with its own bit (AC 25) |
| empty | R8 | ⛔ dismissed | A setter with `res_required=False` and no ack emits nothing; there is no header to check |
| ordering | R8 | ✅ covered | Every packet of a multi-packet reply carries the bit, including after `partial_responses` and `malformed_packets` truncation (AC 23, 24) |
| adjacency | R9 | ✅ covered | Same mixed-fleet test as R8 (AC 25) |
| empty | R9 | ⛔ dismissed | No reply emitted means nothing to compare |
| ordering | R9 | ⛔ dismissed | Reply order is unchanged by this phase |
| boundary | R9 | ✅ covered | Byte fixtures for four WiFi reply shapes (AC 26) — engine missed, added |
| idempotency | R6 | ⛔ dismissed | Restore runs once during build before the device object exists; a second load produces the same `DeviceState` by construction |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT silently convert a requested Thread device to WiFi or a WiFi device to Thread on any code path; invalid creation raises, and the only fallback (bad persisted value) logs a `WARNING` | R1, R2, R3, R6 | resolved | test — negative tests assert `ValueError` on every invalid creation path and a captured `WARNING` on the restore fallback (descriptor: `check_kind=node-test` not applicable; pytest tests in `packages/lifx-emulator-core/tests/test_thread_identity.py`, planner to name) |
| MUST NOT reject any product ID other than 55 for `connectivity="thread"` (guards the recorded no-product-gating decision) | R3 | resolved | test — parametrised over every product ID in the registry except 55 |
| MUST NOT change any WiFi reply or header round trip byte-for-byte | R7, R9 | resolved | test — byte fixtures captured on `main` before the phase |
| MUST NOT hand-edit `protocol/packets.py` or `products/registry.py` | all | resolved | test — `git diff main --stat` on the two paths is empty at phase end |

Canon items: none surfaced (no security, PII or fairness surface in this phase).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | Firmware floor and Tile exception pinned down      |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Explicit out-of-scope list; scenario wiring dropped|
| Constraint Clarity | 0.88  | 0.65 | ✓      | 4.200 floor, 3.50 Tile ceiling, byte fixtures      |
| Acceptance Criteria| 0.90  | 0.70 | ✓      | 31 pass/fail criteria (27 positive + 4 must-NOT)   |
| **Ambiguity**      | 0.10  | ≤0.20| ✓      |                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                                   | Decision locked                                                                 |
|-------|-----------------|----------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher      | Wire the dead `firmware_version` scenario?         | Thread requires ≥ 4.200; a Thread device would not run a 3.70 scenario          |
| 1     | Researcher      | Enforce `connectivity` immutability?               | Reassignment after construction raises `ValueError`                             |
| 1     | Researcher      | Where does the 0.0 WiFi signal live?               | Stored in `NetworkState.wifi_signal` at build time                              |
| 2     | Researcher      | Explicit firmware below 4.200 on Thread?           | `ValueError` at creation                                                        |
| 2     | Simplifier      | Scenario wiring in Phase 1?                        | Dropped from CONN-02; recorded as a known gap                                   |
| 2     | Simplifier      | Per-tile firmware on Thread matrix?                | Only ≥ 4.200 matrix products can be Thread; Tile excluded                       |
| 3     | Boundary Keeper | Product gating conflict with PROJECT.md decision   | No gating except Tile (55): discontinued, terminal firmware 3.50                |
| 3     | Boundary Keeper | Tile firmware reporting                            | Tiles mirror host firmware                                                      |
| 3     | Boundary Keeper | Out of scope confirmation                          | API `DeviceInfo`, CLI/YAML, firmware/advertised_services persistence, inbound bit 3 |
| Gate  | —               | Ambiguity 0.17, proceed?                           | Yes — write SPEC.md                                                             |
| Edge  | Failure Analyst | Mirror scope changes WiFi Ceiling tiles 3.70→4.10  | Mirror for all matrix devices; intentional default-output change with test      |
| Edge  | Failure Analyst | Tile default and explicit firmware                 | Default 3.50; explicit above 3.50 raises; migrate two SKY tests                 |
| Edge  | Failure Analyst | Bad persisted `connectivity` value                 | Warn and fall back to `"wifi"`                                                  |
| Edge  | Failure Analyst | Firmware-4 sensor rule applies to Thread?          | Accept; no special case                                                         |
| Prob. | —               | Keep four must-NOT statements?                     | All four kept, test-tier                                                        |

---

*Phase: 01-thread-device-identity*
*Spec created: 2026-09-09*
*Next step: /gsd-discuss-phase 1 — implementation decisions (where the floor check lives, how `specs.yml` records the Tile ceiling, template stamping vs per-call flag, fixture capture mechanics)*
