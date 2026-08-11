# Design: Upstream Product & Protocol Sync + Mirror/Ceiling/Buttons/Sensor Support

**Date:** 2026-08-11
**Status:** Draft for review
**Scope:** Sync the product catalogue and protocol spec from LIFX upstream, then add
product-specific emulation for the new Mirror device, the new Ceiling variants
(uplight/downlight split), and the Button + Sensor protocol namespaces that
Luna/Mirror/Ceiling rely on.

## Background

The emulator generates two artefacts from upstream LIFX sources:

- `products/registry.py` from `products.json` (`python -m lifx_emulator.products.generator`)
- `protocol/packets.py` + `protocol/protocol_types.py` from `protocol.yml`
  (`python -m lifx_emulator.protocol.generator`)

Both are stale relative to upstream:

- **Registry:** regenerating adds **15 new products**, including **Mirror (267 US,
  268 Intl)** — matrix + buttons — plus new **Ceiling (265, 266)** and **Path (229)**.
  Regeneration also renames many existing products to their current upstream names
  (drops the ` US` suffix, `"LIFX Original 1000"` → `"Original 1000"`, etc.) and emits
  **placeholder** values for the new entries that need manual curation. No tests assert
  product names, so the rename churn is safe.
- **Protocol:** current `packets.py` has 4 namespaces (Device, Light, MultiZone, Tile).
  Upstream `protocol.yml` also defines **`sensor`** (401/402 AmbientLight) and
  **`button`** (905–911). `sensor` regenerates cleanly. **`button` is deliberately
  filtered out** by the generator (`filter_button_relay_items`, "not relevant for light
  control") because Button packets use `[8]<Button>` arrays and nested action unions.
  `relay` is likewise filtered and has no packet classes today; **relays are out of
  scope** for this change.

`products.json` carries **no matrix dimensions**, so every matrix device's geometry
(width × height, tile count, uplight zones) is hand-maintained in `specs.yml`. Mirror's
geometry must be added there.

## Locked decisions (from brainstorming)

1. **Mirror geometry:** single tile, single `Get64`. Represent as **5 × 10 = 50 zones**,
   zones 0–24 front, 25–49 rear. *Provisional* — real dimensions pending LIFX
   confirmation; chosen so a single `Get64` covers all 50 zones.
2. **Ceiling special handling:** model **uplight/downlight zone split**, **extend the
   Sky-effect gate to the new Ceiling pids**, and **verify >64-zone multi-request**
   tiling for the 16×8 (128-zone) variant.
3. **Button + Sensor depth:** **full working handlers** wired to device state.
4. **Registry churn:** **accept upstream names verbatim**, then hand-curate the 15
   placeholder specs.

## Assumptions flagged for review

- **A1 — Mirror dimensions:** 5×10 is a placeholder. When LIFX confirms, only
  `specs.yml` values change; no structural rework expected.
- **A2 — Uplight/downlight semantics:** modelled as metadata, not a separate addressable
  component. `specs.yml` gains an optional `uplight_zone_count` (default 1 for Ceiling).
  The last N zones of the matrix are the uplight; the downlight is the remaining
  `W*H - N` zones. Zones stay addressable through the existing single-matrix
  `Get64`/`Set64` path — the split is exposed via `DeviceState` helpers
  (`uplight_zone_count`, `downlight_zone_count`) and used by product-specific gates, not
  by re-routing packets. If LIFX exposes the uplight as an independent component, revisit.
- **A3 — Mirror uplight/downlight:** Mirror's front/rear is the *same mechanism* as
  Ceiling's uplight/downlight — a zone-index split within one matrix. Front = first 25,
  rear = last 25. No separate framebuffer or packet routing.
- **A4 — Ambient sensor is near-universal and always answers.** `SensorGetAmbientLight`
  (401) **always** returns `SensorStateAmbientLight` (402) — never `StateUnhandled`.
  Devices without a real sensor report **lux 0**; devices with one report a configurable
  value. All button devices have a sensor; almost certainly all matrix devices and most
  firmware 4.x devices do too, but this is unpublished and untestable — so there is **no
  capability gate on the response**. Model as a single `DeviceState.ambient_light_lux`
  (default `0.0`, configurable); factories seed a realistic non-zero default for
  sensor-bearing devices (button or matrix or firmware ≥ 4.x), all overridable. No
  `has_ambient_sensor` capability flag — it would only change a default, not behaviour.

## Architecture / work units

The change is one coherent milestone, delivered in dependency order. Units 1–4 are
"foundation" (catalogue + protocol + state); units 5–7 are "behaviour + tests".

### 1. Regenerate the product registry
- Run the products generator against current upstream `products.json`.
- Accept upstream names verbatim.
- Result: new pids present (incl. Mirror 267/268), existing entries renamed.
- Auto-generated file — do not hand-edit `registry.py` after regen.

### 2. Curate `specs.yml` for new + target products
> **Current blocker:** `specs.yml` is mid-edit and **does not parse** — the auto-added
> Ceiling entries have invalid escaping (`notes: "LIFX Ceiling 13\\""` at lines ~418/426).
> Fix the YAML first; the file must load before anything else works.

Existing base dimensions are already correct and stay as-is: **Candle 5×6, Tube 5×11,
Path (round/square) 3×2, Spot 3×1**. Only the auto-scaffolded **new** entries carry wrong
`8×8` placeholders and must be corrected:
- **Mirror 267/268:** `tile_width: 5`, `tile_height: 10`, `default_tile_count: 1`,
  `uplight_zone_count: 25` (rear), notes describing the front/rear split. *(5×10 is
  provisional per A1.)* Firmware per LIFX (TBD — sane matrix default, flagged).
- **Path 229:** `3×2` (currently `8×8`).
- **Spot 172:** `3×1` (currently `8×8`).
- **Ceiling 265/266 (13"):** `8×8` (confirmed); `uplight_zone_count: 1`; firmware 4.x.
- **Existing Ceiling (176/177 8×8, 201/202 16×8):** add `uplight_zone_count: 1` so the
  split is modelled uniformly.
- Fill any remaining in-scope new matrix/multizone products; leave non-matrix new bulbs
  at catalogue defaults.
- Extend `ProductSpec`/`SpecsRegistry` (`products/specs.py`) with the new
  `uplight_zone_count` field (optional, `int | None`) and `ambient_light_lux` seeding if
  spec-driven (see unit 4/A4).

### 3. Regenerate the protocol — enable Sensor, un-filter Button
- Regenerate `packets.py` + `protocol_types.py`; Sensor namespace (401/402) appears.
- **Un-filter Button:** stop `filter_button_relay_packets`/`filter_button_relay_items`
  from dropping `Button*`. Keep Relay filtered (out of scope).
  - **Risk R1:** the Button compound (`<Button>` with its action array/union) and
    `<ButtonBacklightHsbk>` may exceed the generator's current type support. Mitigation:
    first attempt regeneration; if the generator cannot emit valid Button classes,
    extend the generator's compound/union handling. Fallback: hand-author the Button
    packet classes in a non-generated module if generator work balloons — but prefer
    fixing the generator so future syncs stay clean.
- Confirm existing packet classes are unchanged apart from additions (spot-check
  Device/Light/MultiZone/Tile round-trips).

### 4. Wire capabilities + state
- `DeviceState` (`devices/states.py`): ensure `has_buttons` drives button state, add
  `ambient_light_lux: float = 0.0` (configurable; seeded non-zero for button/matrix/≥4.x
  devices per A4) and button config/backlight state, add uplight/downlight helper
  properties derived from specs.
- **Switch routing:** switches return `StateUnhandled` for Light/MultiZone/Tile, but
  `SensorGetAmbientLight (401)` must still be answered (A4) — ensure the switch
  unhandled path does not intercept Sensor packets.
- Factories (`factories/`): `create_device(product_id)` already reads specs — extend so
  Mirror/Ceiling/Luna get button + sensor + uplight state initialised. Add named
  factories if the existing pattern has them (`create_matrix_device` etc.); follow the
  current factory conventions rather than inventing new entry points.

### 5. Handlers — Sensor + Button
- New `handlers/sensor_handlers.py`: `SensorGetAmbientLight (401)` →
  `SensorStateAmbientLight (402)` returning `DeviceState.ambient_light_lux`. **Always
  responds for every device — never `StateUnhandled`** (A4). No-sensor devices return
  `0.0`; sensor-bearing devices return their (default-seeded, configurable) value.
  Register in `handlers/registry.py`.
- New `handlers/button_handlers.py`: `ButtonGet/Set (905/906)` → `ButtonState (907)`,
  `ButtonGetConfig/SetConfig (909/910)` → `ButtonStateConfig (911)`, backed by
  `DeviceState`. Gate on `has_buttons`; non-button devices return `StateUnhandled` per
  existing convention.
- Follow the existing handler contract: handlers return packets (not header tuples),
  may return lists, honour `res_required`.

### 6. Product-specific behaviour — Ceiling + Mirror
- **Sky-effect gate:** replace the hardcoded `{176,177,201,202}` set in
  `tile_handlers.py` with a spec/capability-driven check that includes new Ceiling pids
  (265/266) and keeps the firmware ≥ 4.4 requirement.
- **Uplight/downlight:** expose the split via `DeviceState` helpers (A2). No packet
  re-routing; existing `Get64`/`Set64` continues to address all zones.
- **Mirror front/rear:** same mechanism as Ceiling (A3) — driven by
  `uplight_zone_count: 25`. Verify a single `Get64` returns all 50 zones.
- **>64-zone multi-request:** verify (add tests, fix if needed) that the 16×8 Ceiling
  requires and correctly serves multiple `Get64`/`Set64` requests.

### 7. Tests
- Registry: Mirror/new pids resolve with correct capabilities (matrix, buttons).
- Specs: Mirror geometry (5×10, 50 zones), uplight zone counts.
- Protocol: Sensor + Button packet pack/unpack round-trips; existing packets unchanged.
- Handlers: Sensor ambient-light response **for every device type incl. switches
  (lux 0 when no sensor, never StateUnhandled)**; Button get/set/config; `has_buttons`
  gating for Button packets; StateUnhandled for non-button devices on Button packets.
- Behaviour: Sky effect accepted on new Ceiling pids, rejected elsewhere/old firmware;
  Mirror single-`Get64` covers 50 zones; Ceiling 16×8 multi-request tiling.
- Full `pytest`, `ruff check .`, `pyright` green. Complexity ≤ 10 per function.

## Out of scope

- **Relay packet classes / handlers** (816–818) — remain filtered; unchanged.
- Physical/spatial accuracy of Mirror dimensions beyond the provisional 5×10 (A1).
- HTTP API / frontend surfaces for the new devices (unless trivially free via existing
  generic device endpoints).

## Risks

- **R1 — Button generator support** (see unit 3): the largest unknown. If the generator
  needs non-trivial compound/union work, that becomes its own sub-task; the plan should
  sequence it early so the button handlers aren't blocked late.
- **R2 — Registry rename churn:** large diff. Mitigated by no name-based test
  assertions; still worth a scan of app/CLI/docs for hardcoded product-name strings.
- **R3 — Provisional Mirror geometry** (A1): accepted; low blast radius (specs-only).

## Delivery shape

Suggest two implementation plans:
1. **Foundation:** units 1–4 (registry regen, specs curation, protocol regen + Button
   un-filter, capabilities/state).
2. **Behaviour + tests:** units 5–7 (Sensor/Button handlers, Ceiling/Mirror behaviour,
   full test suite).

Writing-plans will finalise task breakdown.
