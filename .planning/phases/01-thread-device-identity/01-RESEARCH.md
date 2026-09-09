# Phase 1: Thread Device Identity - Research

**Researched:** 2026-09-09
**Domain:** In-memory core-library data model change (connectivity enum, firmware precedence, header bit) — no sockets, no I/O
**Confidence:** HIGH — every claim below is grounded in a specific file/line read this session, or in a command actually executed against the repository at `HEAD e610c08e8ea9eab6e2b37cb097b731542ff8d717`

## Summary

This phase is a verification pass over 13 already-locked implementation decisions (D-01 to D-13 in `01-CONTEXT.md`), not a design exercise. Every decision was checked against the real source this session: all thirteen hold up as written, with one correction (the Python-version rationale behind D-13's `.value`-in-logs note is backwards — see Pitfall 5 below) and several concrete precision points the planner needs (exact byte offsets, exact dict keys, exact existing test line numbers, exact ruff-enforcement gap).

The change touches ten files in a straight line: `header.py` (one field, two bit ops), `states.py` (one enum, one frozen dataclass, one routing entry, one `__setattr__` branch), `firmware_config.py` (one constant, one parameter, two `ValueError` checks), `specs.py`/`specs.yml` (two new optional keys, one product entry changed), `builder.py` (one new build step, one changed `NetworkState()` call, one changed `get_firmware_version()` call), `factory.py` (one parameter on eight functions), `device.py` (one template kwarg, two hard-coded literals replaced), `state_serializer.py`/`state_restorer.py` (one key each way), and the two `__init__.py` barrel files (one export each). No handler in `handlers/*.py` needs to change — `GetWifiInfoHandler`, `GetHostFirmwareHandler` and `GetWifiFirmwareHandler` already read state fields verbatim, and no `LifxHeader(` construction exists anywhere in `src/` outside the one template site this phase extends.

**Primary recommendation:** Follow D-01 through D-13 exactly as written; the deviations this research surfaces are all *additive precision* (exact line numbers, exact byte fixtures, one Python-version correction), not changes of direction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `connectivity` field + immutability | Domain (Device layer: `devices/states.py`) | — | Per-device attribute alongside `wifi_signal`; no new layer |
| Firmware precedence (Thread default/floor, Tile ceiling) | Domain (`factories/firmware_config.py`) | Product data (`products/specs.yml`) | Single existing precedence chain extended, not duplicated |
| Header bit 3 (`thread_connection`) | Protocol wire format (`protocol/header.py`) | Domain (`devices/device.py` template) | Struct-level field lives in the wire-format module; stamping-per-device lives where the response template is built |
| Per-tile firmware mirror | Domain (`devices/device.py` matrix init) | — | Same layer that already hard-codes 3.70 today |
| Persistence round trip | Persistence (`devices/state_serializer.py`, `state_restorer.py`) | Domain (`factories/builder.py` step 0) | Serialization is a pure (de)serialize concern; *when* it's read (once, before firmware resolution) is a builder-ordering concern |
| Public export (`Connectivity`) | Module barrels (`__init__.py` × 2) | — | Existing barrel-file convention |

No Frontend, CDN, or API-tier capability exists in this phase — everything is core-library, in-memory, single-process. This matches the phase boundary in `01-CONTEXT.md` exactly ("No sockets, no mDNS, no CLI, config or API surface").

## User Constraints (from CONTEXT.md and SPEC.md)

`01-CONTEXT.md` and `01-SPEC.md` are the locked requirements documents for this phase (30 acceptance criteria, 13 implementation decisions D-01–D-13). They are reproduced in full in those files and are **not restated here** — this research assumes the planner reads both directly. The one-line summary: `connectivity` on `NetworkState` (immutable, `str, Enum`), Thread firmware default 4.200 with a floor, Tile (55) capped at 3.50 as the sole product exception, `wifi_signal=0.0` for Thread, per-tile firmware mirroring host, persistence round-trip with warn-and-default-to-wifi on bad/missing data, `LifxHeader.thread_connection` as frame-address byte 22 bit 3, stamped once via the per-device response header template, byte fixtures captured before the header change.

**Claude's Discretion areas** (from CONTEXT.md, unchanged by this research): warning-emission site (builder step 0 vs restorer helper), coercion-helper name/location, how `device.py` reads host version for the tile mirror, test serials/fixture names, whether `Connectivity` gets `__str__ = str.__str__` (this research strengthens the recommendation to **yes**, see Pitfall 5).

## Standard Stack

No new dependencies. This phase is 100% stdlib (`dataclasses`, `enum`, `struct`) plus the existing `pyyaml`-loaded `specs.yml`. `Connectivity(str, Enum)` mirrors the sibling `lifx-async` package's own `Connectivity` — no library, just a pattern match.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `str, Enum` for `Connectivity` | `enum.StrEnum` (3.11+) | Rejected: project supports Python 3.10, and `StrEnum` doesn't exist there. `lifx-async`'s own enum is `(str, Enum)`, not `StrEnum` — mirroring it is also mirroring this constraint correctly. |
| Frozen dataclass immutability (D-07) | A `@property` with a private `_connectivity` and a setter that always raises | Rejected: `dataclasses.replace()` is the existing idiom for "wholesale replace an immutable sub-state" and the codebase already has other frozen-adjacent patterns; a hand-rolled property is more code for the same guarantee. |

## Package Legitimacy Audit

Not applicable — no external packages are installed in this phase.

## Verified Findings (per required-reading item)

### 1. `protocol/header.py` — exact struct layout and where bit 3 lands

`[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py:18]` `_HEADER_STRUCT = struct.Struct("<HHI Q6sBB QHH")`.

Byte layout, confirmed both by reading the struct format and by decoding actual packed output (see "Byte fixture capture" below): `H`(size,0-1) `H`(frame_flags,2-3) `I`(source,4-7) `Q`(target,8-15) `6s`(reserved,16-21) `B`(addr_flags,**byte 22**) `B`(sequence,byte 23) `Q`(reserved,24-31) `H`(pkt_type,32-33) `H`(reserved,34-35).

`[VERIFIED: header.py:81-83]` Current `pack()`:
```python
addr_flags = (1 if self.res_required else 0) | (
    (1 if self.ack_required else 0) << 1
)
```
`[VERIFIED: header.py:134-135]` Current `unpack()`:
```python
res_required = bool(flags & 0b1)
ack_required = bool((flags >> 1) & 0b1)
```
Only bits 0-1 exist today; bits 2-7 of byte 22 are always packed as 0 (no explicit masking needed — `addr_flags` is only ever OR'd from those two terms).

**Sibling repo confirms bit 3 exactly** `[VERIFIED: /Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/protocol/header.py:141-156,207-224]`:
```python
flags = (
    (int(self.res_required) & 0b1)
    | ((int(self.ack_required) & 0b1) << 1)
    | ((int(self.thread_connection) & 0b1) << 3)
)
...
thread_connection = bool((flags >> 3) & 0b1)
```
`thread_connection: bool = False` is the last dataclass field, after `pkt_type` — same position this emulator should use (append after `pkt_type`, keep default `False` so every existing `LifxHeader(...)` call site keeps working unchanged). lifx-async's docstring: *"Inbound-only: the device sets this bit on its replies, so `create()` does not expose it and a client never asserts it."* Bits 2 and 4-7 are documented reserved-and-zero on both sides — no masking bug risk since bit 3 is added the same way bit 1 was.

**No other `LifxHeader(` construction site exists in `src/`** `[VERIFIED: grep across packages/lifx-emulator-core/src/lifx_emulator/]` — the only construction site outside `header.py` itself is `devices/device.py:91` (the template). This means Pitfall 6's "audit every construction site" concern from PITFALLS.md is trivially satisfied: there is exactly one site to change.

### 2. `devices/states.py` — routing, frozen dataclass mechanics, and a load-bearing precedent

`[VERIFIED: devices/states.py:47-51]` Current `NetworkState`:
```python
@dataclass
class NetworkState:
    """Network and connectivity state."""
    wifi_signal: float = -45.0
```

`[VERIFIED: devices/states.py:417-441]` `DeviceState.__setattr__`'s direct-assignment set **already includes `"network"`**:
```python
if name in {
    "core", "network", "location", "group", "waveform",
    "infrared", "hev", "multizone", "matrix",
    "has_color", ... , "buttons_state",
} or name.startswith("_"):
    object.__setattr__(self, name, value)
    return
```
This confirms D-07's claim exactly: `state.network = dataclasses.replace(state.network, ...)` already works today with zero changes to this branch, because whole-sub-state replacement bypasses the routing table entirely.

`[VERIFIED: devices/states.py:443-463]` The **routed-write path** (what runs for `state.connectivity = ...` and `state.wifi_signal = ...`, both routed to `"network"`) is:
```python
if name in self._ATTRIBUTE_ROUTES:
    route = self._ATTRIBUTE_ROUTES[name]
    state_name = route if not isinstance(route, tuple) else route[0]
    ...
    state_obj = object.__getattribute__(self, state_name)
    if state_obj is None:
        return
    setattr(state_obj, attr_name, value)   # <-- line 462, NOT wrapped in try/except today
    return
```
D-08 requires wrapping **this specific line** in `try/except dataclasses.FrozenInstanceError` and re-raising `ValueError`. Confirmed empirically this session:
```python
>>> import dataclasses
>>> dataclasses.FrozenInstanceError.__mro__
(FrozenInstanceError, AttributeError, Exception, BaseException, object)
```
`FrozenInstanceError` is a subclass of `AttributeError`, so a bare `except AttributeError` would also catch it, but catching `FrozenInstanceError` specifically is more precise and self-documenting — recommend the narrower except.

**Frozen-dataclass mechanics confirmed by direct execution** (not assumed):
```python
@dataclass(frozen=True)
class NetworkState:
    wifi_signal: float = -45.0
    connectivity: Connectivity = Connectivity.WIFI

n = NetworkState()
n.connectivity = Connectivity.THREAD   # raises FrozenInstanceError: cannot assign to field 'connectivity'
n2 = dataclasses.replace(n, connectivity=Connectivity.THREAD, wifi_signal=0.0)  # works, returns new instance
```
No pyright issue expected: both fields are immutable value types (`float`, a `str`-subclass enum), so there is no mutable-default-with-frozen-dataclass hazard (that hazard only applies to `list`/`dict` defaults, which neither field uses).

**`wifi_signal` is read-only at runtime today** `[VERIFIED: grep -rn "wifi_signal\s*=" packages/*/src]` — the only match is `api/mappers/device_mapper.py:95: wifi_signal=device.state.wifi_signal,` which is a *read* (constructing a `DeviceInfo`), not a write. Freezing `wifi_signal` alongside `connectivity` is safe.

### 3. `factories/builder.py` — exact `build()` step order (12 numbered steps today)

`[VERIFIED: factories/builder.py:248-340]` Current numbered steps inside `build()`:
1. Generate/validate serial (line 255)
2. `_apply_product_defaults()` (line 258)
3. `self._firmware_config.get_firmware_version(product_id=..., extended_multizone=..., override=self._firmware_version)` (lines 261-265)
4. Default color (line 268)
5. `_create_core_state(...)` (line 271)
6. `network = NetworkState(); location = ...; group = ...; waveform = ...` (lines 274-277)
7. Capability-specific states: infrared/hev/multizone/matrix (lines 280-283)
8. `has_extended_multizone` via `firmware_version_int` (lines 286-289)
9. `has_sensor` derivation: `has_buttons or has_matrix or version_major >= 4` (lines 293-297), `ambient_light_lux = 100.0 if has_sensor else 0.0` (line 298)
10. Compose `DeviceState(...)` (lines 301-322)
11. Restore saved state via `StateRestorer` (lines 332-335) — **only if `self._storage` is set**
12. Construct `EmulatedLifxDevice` (lines 337-340)

D-10's "new step 0" must run **before step 3** (firmware resolution needs the effective connectivity) and necessarily before step 6 (network needs it too). Concretely: insert connectivity resolution between the existing docstring's numbered comment `# 2. Apply product-specific defaults` and `# 3. Determine firmware version`, i.e. as a new `# 0.` step physically located wherever is clearest (before step 1 is fine too, since the builder has no dependency from step 0 on serial/product-defaults).

**The "read the saved file once, not twice" tension is real and unresolved by the codebase today.** `StateRestorer.restore_if_available()` (`devices/state_restorer.py:44`) calls `self.storage.load_device_state(state.serial)` internally, at **step 11** — after `NetworkState` will already have been constructed (frozen) at step 6. Because `NetworkState` is frozen, `_restore_core_state`'s existing per-field-mutation pattern (`state.core.label = saved_state["label"]`, line 82 — this works today because `CoreDeviceState` is *not* frozen) **cannot** be reused for `connectivity`: `state.network.connectivity = ...` would raise `FrozenInstanceError` if attempted after step 6. This is exactly why D-10 moves connectivity resolution to step 0, ahead of `NetworkState` construction, rather than leaving it in `StateRestorer`.

Two concrete options for the "single read" requirement, both consistent with D-10's "planner's choice":
- **Option A:** Builder step 0 calls `self._storage.load_device_state(serial)` directly (it's a plain sync method, `devices/persistence.py:190`, safe to call from sync code), extracts `saved_state.get("connectivity")`, and passes the whole `saved_state` dict down so step 11's `StateRestorer` reuses it instead of re-reading. Requires changing `StateRestorer.restore_if_available(state)` to optionally accept a pre-loaded dict, or adding a second method.
- **Option B:** `StateRestorer` gains a `peek_connectivity(serial) -> str | None` method that reads-and-caches (`self._cached_saved_state`); the builder constructs the `StateRestorer` at step 0 instead of step 11, calls `peek_connectivity()`, and the later `restore_if_available()` call checks its own cache before hitting disk again.

Either is a legitimate structural choice; the risk to flag for the plan-checker is that **whichever is chosen, `load_device_state` must be called exactly once per `build()` call when persistence is enabled** — a naive first pass will likely call it twice (once for the peek, once inside the existing `restore_if_available`), which is not a correctness bug (both reads return the same disk content) but is wasted I/O and, if `load_device_state` performance ever becomes non-trivial, an easy regression to reintroduce.

`load_device_state` signature confirmed: `[VERIFIED: devices/persistence.py:190-202]` `def load_device_state(self, serial: str) -> dict[str, Any] | None` — synchronous, safe to call from the (synchronous) `DeviceBuilder.build()`.

### 4. `factories/firmware_config.py` — exact signature and max-args headroom

`[VERIFIED: factories/firmware_config.py:24-77]` Current class:
```python
class FirmwareConfig:
    VERSION_EXTENDED = (3, 70)
    VERSION_LEGACY = (2, 60)

    def get_firmware_version(
        self,
        product_id: int | None = None,
        extended_multizone: bool | None = None,
        override: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
```
Adding `connectivity: Connectivity | str | None = None` makes this **4 non-`self` parameters** — well inside the `max-args = 5` ceiling (`self` does not count toward Ruff's `PLR0913`, confirmed by direct test below). No helper extraction needed to stay under budget; add two `ValueError` checks (floor, ceiling) as simple `if` statements, which stays well under `max-branches = 12`.

**Ruff enforcement gap confirmed by direct test** — this matters for the whole phase's compliance story:
```
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```
`[VERIFIED: pyproject.toml:33-34]` — **`PLR` (pylint, including `PLR0913` max-args) and `C901` (mccabe complexity) are configured under `[tool.ruff.lint.pylint]`/`[tool.ruff.lint.mccabe]` but are NOT in `select`, so ruff does not currently enforce either limit.** Confirmed by running `ruff check --select PLR0913` against a throwaway 6-argument method: it reports the violation only when explicitly selected; the default `uv run ruff check .` (which uses the project's `select`) would not catch it. This is also independently evidenced by the *existing* code: `create_multizone_light`/`create_tile_device` already have 7 parameters and `create_device` has 10 — all already over the documented "5" limit, and none currently fails CI. **Practical implication for the planner:** adding `connectivity` to every typed factory (pushing already-6/7-param functions to 7/8) will not fail `ruff check .` or CI, but CLAUDE.md still declares `max-args = 5` as a hard rule for human review purposes. Recommend the planner note this discrepancy explicitly in the plan rather than either (a) contorting the factories to hit an unenforced limit, or (b) silently ignoring a documented convention — a one-line note ("max-args is configured but not selected in ruff; this phase follows the existing precedent of exceeding it, consistent with `create_multizone_light`/`create_tile_device`/`create_device`") is the honest resolution.

```
$ cat > /tmp/plr_test.py <<'EOF'
class Foo:
    def bar(self, a, b, c, d, e, f):
        pass
EOF
$ uv run ruff check --select PLR0913 --isolated /tmp/plr_test.py
PLR0913 Too many arguments in function definition (6 > 5)   # only fires when explicitly selected
```

**Precedence implementation, worked through against every acceptance criterion:**
```python
def get_firmware_version(
    self,
    product_id: int | None = None,
    extended_multizone: bool | None = None,
    override: tuple[int, int] | None = None,
    connectivity: Connectivity | str | None = None,
) -> tuple[int, int]:
    if override is not None:
        result = override
    elif connectivity == Connectivity.THREAD:
        result = self.VERSION_THREAD
    elif product_id is not None and (
        specs_version := get_default_firmware_version(product_id)
    ) is not None:
        result = specs_version
    elif extended_multizone is False:
        result = self.VERSION_LEGACY
    else:
        result = self.VERSION_EXTENDED

    if connectivity == Connectivity.THREAD and result < self.VERSION_THREAD:
        raise ValueError(f"Thread firmware must be >= {self.VERSION_THREAD}, got {result}")

    if product_id is not None:
        max_fw = get_max_firmware_version(product_id)  # NEW specs.py accessor
        if max_fw is not None and result > max_fw:
            raise ValueError(
                f"Firmware {result} exceeds product {product_id}'s maximum {max_fw}"
            )
    return result
```
Tuple comparison (`(4, 199) < (4, 200)`, `(3, 51) > (3, 50)`) is lexicographic and correct here because major always dominates minor at the same or higher order of magnitude — verified no edge case where a differing major produces a wrong ordering for this domain (majors are single digits, minors up to 200; `(4, 0) > (3, 99)` is correctly `True`).

**Tile+Thread rejection walkthrough (confirms "one message naming both" is achievable with the two checks above, in this order):** `create_device(55, connectivity="thread")`, no override → `result = VERSION_THREAD = (4, 200)` (thread-default branch fires before the specs-default branch, per precedence). Floor check: `(4,200) >= (4,200)` passes (not below floor). Ceiling check: product 55's `max_firmware = (3, 50)`, `(4,200) > (3,50)` → raises `"Firmware (4, 200) exceeds product 55's maximum (3, 50)"`. This message names the resolved value and the ceiling but not explicitly "this is because Thread forced 4.200" — **recommend enriching the ceiling-check message specifically when the rejection was caused by an unrequested Thread default**, e.g. append `" (Thread's default firmware of (4, 200) cannot be reduced to fit)"` when `connectivity == Connectivity.THREAD and override is None`, satisfying D-06's "naming both" instruction precisely rather than incidentally.

**Only one call site exists for `get_firmware_version`** `[VERIFIED: grep -rn "get_firmware_version(" packages/*/src packages/*/tests]` — `factories/builder.py:261`, plus doctests in `firmware_config.py` itself and three call sites in `test_products_specs.py:334-365`. Adding a fourth optional parameter with a default of `None` (behaving as WiFi/no-Thread-effect) keeps every existing call site and doctest passing unchanged.

### 5. `factories/factory.py` — exact current arg counts per factory

`[VERIFIED: factories/factory.py, full file read]` Current non-`product_id` parameter counts (all keyword, matching the existing call style):

| Factory | Current params | Current count | After `+connectivity` |
|---|---|---|---|
| `create_color_light` | serial, firmware_version, storage, scenario_manager, advertised_services | 5 | 6 |
| `create_infrared_light` | same shape | 5 | 6 |
| `create_hev_light` | same shape | 5 | 6 |
| `create_color_temperature_light` | same shape | 5 | 6 |
| `create_switch` | serial, product_id, firmware_version, storage, scenario_manager, advertised_services | 6 | 7 |
| `create_multizone_light` | serial, zone_count, extended_multizone, firmware_version, storage, scenario_manager, advertised_services | 7 | 8 |
| `create_tile_device` | serial, tile_count, tile_width, tile_height, firmware_version, storage, scenario_manager, advertised_services | 8 | 9 |
| `create_device` | product_id, serial, zone_count, extended_multizone, tile_count, tile_width, tile_height, firmware_version, storage, scenario_manager, advertised_services | 11 | 12 |

**PR #156 precedent confirmed exact:** `advertised_services` was appended as the **last** parameter to every one of these functions and threaded through unconditionally as `advertised_services=advertised_services` in every `create_device(...)` call inside each typed factory. `connectivity` should follow the identical pattern — appended last, threaded through the same way, with `builder.with_connectivity(connectivity)` gated the same way every other optional param is (`if connectivity is not None: builder.with_connectivity(connectivity)` in `create_device()`, matching the `if advertised_services is not None:` block at `factory.py:272-273`).

**Switches can be Thread devices with no conflict** `[VERIFIED: products/specs.yml, executed lookup]` — the four relay/switch product IDs (70, 71, 84, 89, 115, 116, 226) all carry `default_firmware_major=4, default_firmware_minor=100` in `specs.yml` (not a code-level pin — no hard-coded "4,100" exists in `factories/` or `handlers/`, confirmed by grep). Since `4.100 < 4.200`, a Thread switch simply takes the Thread default via the new precedence branch (Thread-default fires before specs-default), same as any other product without a `max_firmware` ceiling. No switch-specific code path needed.

### 6. `products/specs.py` / `specs.yml` — exact `ProductSpecs` fields, Tile entry, and the 28 matrix products

`[VERIFIED: products/specs.py:16-68]` Current `ProductSpecs` dataclass fields: `product_id, default_zone_count, min_zone_count, max_zone_count, default_tile_count, min_tile_count, max_tile_count, tile_width, tile_height, default_firmware_major, default_firmware_minor, uplight_zone_count, button_count, notes`. Adding `max_firmware_major: int | None = None` and `max_firmware_minor: int | None = None` (mirroring the existing `default_firmware_*` pair exactly) plus a `has_max_firmware_specs` property (mirroring `has_firmware_specs` at line 62-68) is a pure additive change — `SpecsRegistry.load_from_file()` needs two more `.get()` calls at the parse site (`specs.py:112-113` is where `default_firmware_major/minor` are parsed; add the two new keys immediately after), and one new accessor function `get_max_firmware_version(product_id) -> tuple[int,int] | None` mirroring `get_default_firmware_version` (`specs.py:192-207`) exactly.

`[VERIFIED: products/specs.yml:214-220]` **Product 55's current entry has no firmware keys at all**:
```yaml
55:  # LIFX Tile, 8x8 zone matrix, chainable up to 5
  default_tile_count: 5
  min_tile_count: 1
  max_tile_count: 5
  tile_width: 8
  tile_height: 8
  notes: LIFX Tile, 8x8 zone matrix, chainable up to 5
```
D-04 adds `default_firmware_major: 3`, `default_firmware_minor: 50`, `max_firmware_major: 3`, `max_firmware_minor: 50` to this block. Today, with no firmware keys, product 55 falls through to `VERSION_EXTENDED = (3, 70)` (the SPEC's documented "Current: Tile defaults to 3.70" is exact).

`[VERIFIED: products/specs.yml:286-293, 297-306]` Ceiling entries (176, 177, both examined; 201, 202 share the pattern) already carry `default_firmware_major: 4, default_firmware_minor: 10` — confirms SPEC's "including for Ceiling whose specs.yml default is 4.10" test target is real, present data, not hypothetical.

`[VERIFIED: products/specs.yml:238-244, 246-252]` Product 185 (LIFX Candle Color US) and 186 (Candle Colour Intl) have **no** `default_firmware_*` keys — confirming both are valid non-Ceiling matrix products with no firmware default to interact with a Thread override; **185 is the CONTEXT.md-suggested migration target for the two SKY tests** and is confirmed clean.

**Full matrix-product enumeration, executed directly against the loaded registry** (this is the population the "every matrix product ID except 55" acceptance test iterates):
```
28 matrix products: [55, 57, 68, 137, 138, 171, 172, 173, 174, 176, 177, 185, 186,
                      201, 202, 215, 216, 217, 218, 219, 220, 221, 222, 229, 265, 266, 267, 268]
```
`[VERIFIED: uv run python3 -c "from lifx_emulator.products.registry import PRODUCTS; ..."]` — product 55 is the only one to exclude; the other 27 are fair game.

**Test precedent for iterating the full product set already exists** `[VERIFIED: tests/test_products_specs.py:394-401]`:
```python
def test_every_switch_pins_its_firmware(self):
    from lifx_emulator.factories import create_device
    from lifx_emulator.products.registry import PRODUCTS

    for pid, info in PRODUCTS.items():
        if info.has_relays:
            state = create_device(pid).state
            assert (state.version_major, state.version_minor) == (4, 100), f"product {pid}"
```
This is the exact style to copy for "every matrix product except 55 can be created as Thread" (`if info.has_matrix and pid != 55: create_device(pid, connectivity="thread")`).

The `specs.yml` header comment (`specs.yml:36-45`) documents the current precedence order in English prose and must be updated in the same commit as the `FirmwareConfig` change, per D-04's "header comment documents the firmware precedence that D-06 extends."

### 7. `devices/device.py` — template construction, both ack paths, `StateUnhandled`, and the hard-coded tile firmware

`[VERIFIED: devices/device.py:89-98]` Template construction (the one and only site needing the new kwarg):
```python
self._response_header_template = LifxHeader(
    source=0,
    target=self.state.get_target_bytes(),
    sequence=0,
    tagged=False,
    pkt_type=0,
    size=0,
    # NEW: thread_connection=self.state.connectivity == Connectivity.THREAD,
)
```

`[VERIFIED: devices/device.py:218-244]` `_create_response_header()` does a **shallow `copy.copy()`** of the template and only overwrites `source`, `sequence`, `pkt_type`, `size` — `thread_connection` (and every other template field) survives the copy untouched. This is the single choke point every reply path funnels through:
- Normal replies: `process_packet()` line 364, inside the `for resp_packet in response_packets:` loop.
- Scenario-path ack (when `scenario.affects_acks`): `process_packet()` lines 300-316 and 330-338, both call `_create_response_header`.
- `StateUnhandled` (capability-mismatch path): `process_packet()` lines 298-305, also via `_create_response_header`.
- **Server-side fast-path ack** `[VERIFIED: server.py:182-217]`: `EmulatedLifxServer._send_ack()` calls `device._create_response_header(...)` directly (line 197) — this is the documented "reach into device privates" pattern already flagged in the codebase's own concerns list, but it means the fast-path ack **automatically inherits `thread_connection` with zero code change** in `server.py`, because it goes through the same helper.

This confirms Pitfall 6 from PITFALLS.md is fully mitigated by the existing structure: there is genuinely only one place to add the bit, and both ack paths plus `StateUnhandled` already funnel through it.

`[VERIFIED: devices/device.py:136-143]` The hard-coded per-tile firmware, inside the `if self.state.has_matrix and self.state.tile_count > 0:` block (only runs when `not self.state.tile_devices`, i.e. fresh construction, not a restored device):
```python
self.state.tile_devices.append(
    {
        ...
        "firmware_build": int(time.time()),
        "firmware_version_minor": 70,   # <- change to self.state.version_minor
        "firmware_version_major": 3,    # <- change to self.state.version_major
        "colors": tile_colors,
    }
)
```
`self.state` is assigned at the very top of `__init__` (line 70), before this block runs, so `self.state.version_major`/`version_minor` are already the fully-resolved build-time firmware values — no ordering hazard.

**Scope nuance the planner should know:** this mirroring only applies to *freshly constructed* tiles. A device restored from persistence has its `tile_devices` list (including whatever `firmware_version_major/minor` was saved historically) overwritten wholesale by `StateRestorer._restore_matrix_state()` (`state_restorer.py:226`, `state.matrix.tile_devices = saved_tiles`) — the persisted values are **not** re-derived from the current host firmware on restore. This is consistent with the SPEC's acceptance criteria (which test fresh `create_device()` calls, not restore), but is worth one sentence in the plan so nobody "fixes" restore to also re-mirror and inadvertently changes restore semantics outside this phase's scope.

`[VERIFIED: handlers/tile_handlers.py:51-52]` confirms the exact dict keys the wire-encoding handler reads back: `version_minor=tile["firmware_version_minor"]`, `version_major=tile["firmware_version_major"]` — matching the keys above exactly, so the fix is a two-line value swap, no key renaming.

### 8. `devices/state_serializer.py` / `state_restorer.py` — exact absence of firmware fields (confirms the "pre-existing gap" claim) and the add-site for `connectivity`

`[VERIFIED: devices/state_serializer.py:89-183]` `serialize_device_state()` currently persists: `serial, label, product, power_level, color, location_*, group_*, has_*` flags, then conditionally `infrared_brightness`, `hev_*`, multizone fields, matrix fields (including per-tile `firmware_version_minor/major` — persisted, but never *re-derived* on restore, per point 7 above), and `buttons_config`. **`version_major`, `version_minor`, `wifi_signal`, and `advertised_services` are absent from this function entirely** — confirms SPEC's "pre-existing round-trip gap, unchanged by this phase" claim for firmware/advertised_services, and confirms that `wifi_signal` doesn't need special persistence handling either (it's re-derived at build time from the restored `connectivity`, same as it is for a fresh device).

Add `state_dict["connectivity"] = str(device_state.connectivity)` (or `.value`, see Pitfall 5) unconditionally (not inside an `if has_X:` guard — every device has a connectivity, unlike optional capabilities) near the top of the dict, alongside `serial`/`label`.

`[VERIFIED: devices/state_restorer.py:32-70]` `restore_if_available()`'s existing flow: load dict → product-mismatch check (warn + early return) → `_restore_core_state` → `_restore_location_and_group` → `_restore_capability_state`. **Connectivity restoration does NOT belong in any of these three existing private methods** — as established in point 3 above, by the time `restore_if_available` runs (build step 11), `NetworkState` is already constructed and frozen; none of the existing per-field mutation patterns (`state.core.label = ...`) work for a frozen sub-state. Connectivity resolution must happen at builder step 0, reading the saved dict directly or via a new `StateRestorer` peek method (see point 3's two options) — **not** as a fourth private method inside `StateRestorer` that runs at the normal step-11 restore point.

### 9. Tests — exact SKY-test bodies to migrate, conftest serial range, and existing persistence-test idiom

`[VERIFIED: tests/test_tile_handlers_extended.py:720-757]` `test_sky_effect_on_non_ceiling_tile_device` — body is `device = create_device(55, tile_count=1, firmware_version=(4, 4))` (line 723) then asserts `device.state.tile_effect_type == int(TileEffectType.OFF)` after sending a SKY effect packet. **Only the product ID needs to change** (`55` → `185`); the assertion is unaffected because product 185 is not a Ceiling product either way.

`[VERIFIED: tests/test_tile_handlers_extended.py:928-970]` `test_other_effects_on_non_ceiling_still_work` — same shape, `create_device(55, tile_count=1, firmware_version=(4, 4))` at line 931, asserts a MORPH effect *is* applied. Same one-line fix.

Both tests will start raising `ValueError` at `create_device(55, ..., firmware_version=(4, 4))` the moment D-04's ceiling lands (since `(4,4) > (3,50)`), which is precisely why CONTEXT.md flags them for migration — **this migration must land in the same commit/plan-task as the Tile ceiling change**, or the test suite breaks mid-phase.

`[VERIFIED: tests/conftest.py]` Canonical serials in use: `d073d5000001` through `d073d5000012` (`large_matrix_device`), plus `d073d5000099` for scenario-config fixtures. The `d073d50000{13..98}` range is free for new Thread-identity fixtures.

`[VERIFIED: tests/test_async_storage.py:27-53]` Exact round-trip idiom to copy for CONN-04:
```python
async def test_device_storage_save_and_load(self, temp_storage):
    device = create_color_light("d073d5123456", storage=temp_storage)
    ...
    await temp_storage.save_device_state(state)
    await temp_storage.shutdown()
    saved_state = temp_storage.load_device_state(state.serial)
    new_device = create_device(saved_state["product"], serial=saved_state["serial"], storage=temp_storage)
    ...
```
The CONN-04 round-trip test should follow this exact shape: create a Thread device with `storage=temp_storage`, save, then `create_device(pid, serial=..., storage=temp_storage)` again (no `connectivity=` argument on the second call — proving restore, not re-specification, produces Thread) and assert `new_device.state.connectivity == "thread"` and bit 3 on its first reply.

`[VERIFIED: tests/test_advertised_services.py:1-24]` The exact style precedent for a new dedicated test module (module docstring, a small `_get_service`-style helper building a raw `LifxHeader` + calling `device.process_packet`, `Test*` classes) — `test_thread_identity.py` should follow this shape.

**No `test_header.py` exists today** `[VERIFIED: find ... -iname "*header*"]` returns nothing in `tests/`; no existing test module exercises `LifxHeader.pack()`/`.unpack()` directly (existing tests build headers only as request scaffolding). This confirms D-13's "new `test_header.py`" is genuinely new ground, not a rename/consolidation of existing coverage.

### 10. `__init__.py` barrel exports — exact current state, confirms two additions needed

`[VERIFIED: devices/__init__.py:12-50]` exports `DeviceState` but not `NetworkState` or any enum; `[VERIFIED: lifx_emulator/__init__.py:9-31]` exports the six typed factories and `EmulatedLifxServer`/`EmulatedLifxDevice` but **does not export `create_device` or `create_switch` at all** (pre-existing gap, out of scope for this phase — noted only so the planner doesn't assume `create_device`/`create_switch` are part of the public `lifx_emulator.*` surface today; they're currently reachable only via `lifx_emulator.factories`). Add `Connectivity` to both `__all__` lists: `devices/__init__.py` imports it `from lifx_emulator.devices.states import Connectivity, DeviceState`; `lifx_emulator/__init__.py` imports it `from lifx_emulator.devices import Connectivity, EmulatedLifxDevice`.

### 11. Byte fixture capture — exact recipe, executed, real output at `HEAD e610c08e8ea9eab6e2b37cb097b731542ff8d717`

Ran directly against the current tree (not simulated). This is the runnable recipe D-11/D-12 call for, with real captured bytes the planner can paste directly into `test_thread_identity.py`/`test_header.py` as `bytes.fromhex(...)` constants:

```python
from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device, Light

device = create_color_light("d073d5000001")

# StateService (from GetService, tagged discovery reply)
header = LifxHeader(source=1, target=device.state.get_target_bytes(), sequence=1,
                     pkt_type=Device.GetService.PKT_TYPE, res_required=True)
responses = device.process_packet(header, None)
# h.pack() = 2900001401000000d073d500000100000000000000000001000000000000000003000000
# p.pack() = 017cdd0000

# StateColor (from Light.GetColor — the "State* data reply" shape)
header2 = LifxHeader(source=2, target=device.state.get_target_bytes(), sequence=2,
                      pkt_type=Light.GetColor.PKT_TYPE, res_required=True)
responses2 = device.process_packet(header2, None)
# h.pack() = 5800001402000000d073d50000010000000000000000000200000000000000006b000000
# p.pack() = 5555ffff0080ac0d0000ffff4c49465820436f6c6f72203830306c6d203030303030310000000000000000000000000000000000

# Acknowledgement (type 45) — via the same helper the server's fast path calls
ack_header = device._create_response_header(3, 3, Device.Acknowledgement.PKT_TYPE,
                                             len(Device.Acknowledgement().pack()))
# ack_header.pack() = 2400001403000000d073d50000010000000000000000000300000000000000002d000000
# Acknowledgement().pack() = b"" (empty payload)

# StateUnhandled (223) — send a Tile packet (701) to a color light (no matrix capability)
header3 = LifxHeader(source=4, target=device.state.get_target_bytes(), sequence=4,
                      pkt_type=701, res_required=True)
responses3 = device.process_packet(header3, None)
# h.pack() = 2600001404000000d073d5000001000000000000000000040000000000000000df000000
# p.pack() = bd02

# Plain header round trip (no device involved — proves pack/unpack symmetry unaffected)
plain_header = LifxHeader(source=99, target=device.state.get_target_bytes(), sequence=7,
                           pkt_type=999, res_required=True, ack_required=True, tagged=True)
packed = plain_header.pack()
# packed.hex() = 0000003463000000d073d5000001000000000000000003070000000000000000e7030000
assert LifxHeader.unpack(packed) == plain_header   # True, verified
```

**Byte 22 (the addr_flags byte) is `0x00` in all four response headers above** — decoded directly (`bytes.fromhex(...)[22]`), confirming the current baseline is exactly what HDR-03 requires to stay unchanged: a WiFi device's byte 22 is `0x00` today across `StateService`, `StateColor`, `Acknowledgement` and `StateUnhandled`. After this phase, a Thread device's byte 22 becomes `0x08` (bit 3 set) on the identical four reply shapes, while a WiFi device's byte 22 stays `0x00` — the fixture comparison is a single-byte diff, exactly as PITFALLS.md's Pitfall 6 recommends testing.

Git provenance for the fixture comment: `git rev-parse HEAD` at capture time = `e610c08e8ea9eab6e2b37cb097b731542ff8d717`.

### 12. Python 3.10 vs 3.11+ `(str, Enum)` formatting — CONTEXT.md's stated rationale is backwards (executed both ways this session)

CONTEXT.md's discretion note says: *"Python 3.10 formats as `Connectivity.THREAD`, so any log line that prints it should use `.value` explicitly"* (implying 3.11+ is fine unadorned). **This is backwards — verified by executing the identical class body under both interpreters:**

```
$ uv run --python 3.10 python3 -c "... f'{Connectivity.THREAD}' ..."
str(): Connectivity.THREAD
f-string: thread          # <- clean on 3.10
$ uv run python3 -c "..."   # default env resolves to 3.14.7
str(): Connectivity.THREAD
f-string: Connectivity.THREAD   # <- NOT clean on 3.14 (and, per CPython's enum changelog, 3.11+ generally)
```
Root cause: CPython 3.11 changed `Enum.__format__` to always use `str(self)` for consistency, *unless* the enum also inherits `ReprEnum` (which only `IntEnum`/`StrEnum`/`IntFlag` do). A hand-written `class X(str, Enum)` — which is what D-01 specifies, and what `lifx-async` itself uses — does **not** get `ReprEnum` treatment, so on 3.11+ it regresses to the ugly `ClassName.MEMBER` form in f-strings, `%s`, and `str()` alike. **This project's own default dev environment (`uv sync` with no `.python-version` pin) resolves to Python 3.14.7** — so the "ugly" format is what a contributor sees locally *by default*, not an edge case confined to old CI legs.

`lifx-async`'s precedent line, confirmed as the fix, tested working identically on both 3.10 and 3.14:
```python
__str__ = str.__str__
```
```
$ uv run --python 3.10 python3 -c "...with __str__ = str.__str__..."
str(): thread
f-string: thread
%s: thread
$ uv run python3 -c "...same, default 3.14 env..."
str(): thread
f-string: thread
%s: thread
```
`json.dumps({"c": Connectivity.THREAD})` also correctly produces `{"c": "thread"}` regardless of `__str__` (JSON serialization goes through the `str` base class directly, independent of `__format__`/`__str__` overrides).

**Recommendation, correcting CONTEXT.md's stated discretion:** add `__str__ = str.__str__` to `Connectivity` unconditionally — not "harmless either way" but actively necessary on this project's own default toolchain (3.14), and it makes every `%s`-style log line correct without needing `.value` sprinkled everywhere, which is both less code and matches the `lifx-async` precedent byte-for-byte.

## Architecture Patterns

### Recommended Project Structure

No new files or directories beyond one new test module:
```
packages/lifx-emulator-core/
├── src/lifx_emulator/
│   ├── protocol/header.py        # + thread_connection field, 2 bit ops
│   ├── devices/
│   │   ├── states.py             # + Connectivity enum, frozen NetworkState, routing entry, FrozenInstanceError→ValueError
│   │   ├── device.py             # + template kwarg, 2 literals → state fields
│   │   ├── state_serializer.py   # + "connectivity" key
│   │   └── state_restorer.py     # unchanged (connectivity resolved in builder, not here)
│   ├── factories/
│   │   ├── builder.py            # + step 0 connectivity resolution, with_connectivity()
│   │   ├── factory.py            # + connectivity param on 8 functions
│   │   └── firmware_config.py    # + VERSION_THREAD, connectivity param, floor/ceiling checks
│   └── products/
│       ├── specs.py              # + max_firmware_major/minor, get_max_firmware_version()
│       └── specs.yml             # + Tile ceiling, precedence comment update
└── tests/
    ├── test_thread_identity.py   # NEW — factories, coercion, firmware, wifi_signal, bit-on-every-reply
    ├── test_header.py            # NEW — thread_connection pack/unpack
    ├── test_async_storage.py     # + persistence round trip, bad/missing key
    ├── test_products_specs.py    # + Tile ceiling, max_firmware loading
    └── test_tile_handlers_extended.py  # 2 lines changed (product 55 → 185), + per-tile mirror test
```

### Pattern 1: One template, not several call sites, for the wire-level Thread bit

Already covered in point 7 above with exact line numbers. This is the single most important structural fact for the plan: the entire "stamp bit 3 on every reply" requirement (HDR-02) is satisfiable with **one line changed** (`devices/device.py:91-98`, adding one kwarg), because every reply path — including both ack paths and `StateUnhandled` — already funnels through `_create_response_header()`.

### Pattern 2: Builder step 0, not a `StateRestorer` fourth method, for connectivity resolution

Already covered in point 3 above. The generalizable lesson: when adding an immutable, build-time-resolved field that *also* needs to survive persistence, the field must be resolved **before** the dataclass holding it is constructed, which for this codebase's `DeviceBuilder.build()` means before step 6 (state composition) rather than at step 11 (the existing post-composition restore point) — because restore of an already-frozen sub-state cannot use the existing per-field-mutation restore pattern.

### Anti-Patterns to Avoid

- **Adding a `family`/`connectivity`-aware branch to `PacketHandler.handle()` or any handler class.** Every handler in `handlers/*.py` is already scenario-blind and state-blind beyond `device_state`; `GetWifiInfoHandler` doesn't need to know connectivity exists — it just reads `device_state.wifi_signal`, which is already correct by the time any handler runs, because it was resolved at build time. Do not thread `connectivity` into `PacketHandler.handle()` signatures.
- **Fixing Tile-on-Thread with a `if product_id == 55:` check anywhere in Python.** The floor/ceiling arithmetic in `FirmwareConfig.get_firmware_version()` rejects it structurally; a literal `55` check would duplicate logic that `specs.yml`'s data-driven ceiling already expresses, and would violate CONTEXT.md's explicit "no pid-specific code anywhere" instruction (D-06).
- **Re-deriving per-tile firmware inside `StateRestorer._restore_matrix_state()`.** That method's job is "restore exactly what was saved"; changing it to also re-mirror host firmware would silently alter restore semantics for pre-existing persisted tile devices outside this phase's tested scope (see point 7's "scope nuance").

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String-to-enum coercion with a custom error message | A hand-rolled `if value not in ("wifi", "thread"): raise ...` | `Connectivity(value)` wrapped in a `try/except ValueError` that re-raises with a message naming the accepted values | The enum already validates membership; re-raising just improves the message, it doesn't reimplement validation |
| Immutability enforcement | A custom `__setattr__` override on `NetworkState` itself | `@dataclass(frozen=True)` + `dataclasses.replace()` | Stdlib mechanism, already proven to interoperate correctly with `DeviceState.__setattr__`'s existing direct-assignment branch (verified this session) |
| Firmware floor/ceiling validation | A second precedence chain or a scenario-adjacent validator | Two `if`/`raise ValueError` statements inside the existing single-call-site `FirmwareConfig.get_firmware_version()` | One chain, one call site, already confirmed to have parameter headroom |

**Key insight:** every "don't hand-roll" item above is really the same insight restated: this codebase already has exactly one authoritative place for each of these concerns (attribute routing, header construction, firmware resolution), and the entire job of this phase is extending those three places, not adding new ones.

## Runtime State Inventory

Not applicable — this phase is not a rename/refactor/migration. It is confirmed additive: no existing field is renamed, no existing wire format changes for WiFi devices (verified via byte fixtures above), and the one intentional default-output change (WiFi Ceiling tiles reporting 4.10 instead of 3.70) is a data-correctness fix already called out and accepted in SPEC AC 16, not an unintended side effect.

## Common Pitfalls

### Pitfall 1: Persisted-value restore conflicting with frozen `NetworkState`

**What goes wrong:** A naive implementation adds `connectivity` restoration to `StateRestorer._restore_core_state()` following the existing `state.core.label = saved_state["label"]` pattern, which raises `FrozenInstanceError` (or requires ad-hoc `dataclasses.replace()` inside a restorer method that returns nothing, breaking the void-mutation contract every other `_restore_*` method follows).
**Why it happens:** Every other restored field lives on a non-frozen sub-state (`CoreDeviceState`, `LocationState`, etc.), so the existing restore pattern generalizes incorrectly to the one frozen field.
**How to avoid:** Resolve connectivity in `DeviceBuilder.build()` step 0, before `NetworkState` is constructed at all — see point 3 above.
**Warning signs:** Any diff that adds a line to `_restore_core_state`, `_restore_location_and_group`, or a new fourth `_restore_*` method that touches `state.network.connectivity` directly.

### Pitfall 2: Double disk read for the persistence peek

**What goes wrong:** Builder step 0 calls `storage.load_device_state(serial)` to peek connectivity; step 11's existing `StateRestorer.restore_if_available()` calls it again internally. Not a correctness bug, but wasted I/O on every device creation with persistence enabled, and a regression magnet if `load_device_state` ever grows real cost.
**How to avoid:** Pick one of the two options in point 3 above and implement it so the read happens exactly once; add a test (or at minimum a code comment) making the single-read invariant explicit.

### Pitfall 3: Migrating the SKY tests in a separate commit from the Tile ceiling

**What goes wrong:** `test_sky_effect_on_non_ceiling_tile_device` and `test_other_effects_on_non_ceiling_still_work` both call `create_device(55, tile_count=1, firmware_version=(4, 4))`. The moment the Tile ceiling (3.50) lands, this call raises `ValueError` — the tests do not merely need a *new* assertion, they **fail to construct their fixture device at all** the instant D-04 ships. If the ceiling and the test migration land in different plan tasks/commits, the test suite is red in between.
**How to avoid:** Land the `specs.yml` Tile ceiling change and the two-line test migration (55 → 185) in the same task, verified together.

### Pitfall 4: Assuming `wifi_signal` needs new persistence handling

**What goes wrong:** Seeing `NetworkState` gain a persisted `connectivity` field, an implementer might reflexively also add `wifi_signal` to `serialize_device_state`/`deserialize_device_state`, since both fields now live on the same (frozen) sub-state.
**Why it's unnecessary:** `wifi_signal` is fully re-derived at build time from the (now-restored) `connectivity` value — a restored Thread device gets `wifi_signal=0.0` from step 0's derivation, not from a persisted number. Persisting it would be redundant and could even introduce a staleness bug if the derivation rule ever changes (persisted `-45.0` surviving into a future rule change).
**How to avoid:** Persist `connectivity` only; leave `wifi_signal` exactly as it is today (unpersisted, rederived).

### Pitfall 5: Trusting CONTEXT.md's Python-version claim about `(str, Enum)` formatting without checking it

Covered in full in point 12 above — the claim in CONTEXT.md's "Claude's Discretion" section has the two Python versions' behavior backwards. Executed and confirmed both ways this session. The corrected recommendation (add `__str__ = str.__str__` unconditionally) still lands in the same place D-13 would have picked "if in doubt," so this doesn't change the plan's shape — but the plan should state the *correct* reason, not the swapped one, in case a future maintainer re-derives the decision from the wrong premise.

### Pitfall 6: Header bit added correctly but reserved bits accidentally polluted

**What goes wrong:** A careless bit-OR when adding bit 3 (e.g. `flags = res | (ack << 1) | (thread << 2)` — off-by-one shift) sets bit 2 instead of bit 3, silently breaking wire compatibility with `lifx-async`'s expectation (bit 3 exactly) while every *local* round-trip test still passes (since both `pack()` and `unpack()` would use the same wrong bit consistently).
**How to avoid:** The byte fixtures captured in point 11 above are the actual defence here — a byte-fixture comparison catches a wrong-bit-position bug immediately (the WiFi fixture would still match since `thread_connection=False` either way, but a manually-constructed `LifxHeader(thread_connection=True).pack()[22] == 0x08` assertion, checked against the exact hex literal, catches a shift-position bug that a "does it round-trip" test alone would not).

## Code Examples

### Frozen `NetworkState` + `Connectivity` enum (states.py)
```python
# Source: verified by direct execution this session, pattern from
# /Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/devices/base.py:79-96
from enum import Enum

class Connectivity(str, Enum):
    """How a device's radio reaches the network.

    A LIFX device operates in either WiFi or Thread mode. Changing between
    them requires a firmware crossgrade, so the value is invariant for a
    given device rather than a per-request transport choice.
    """

    WIFI = "wifi"
    THREAD = "thread"

    # Render as the bare value on every supported Python version (3.10-3.14).
    # Without this, a (str, Enum) member formats as "Connectivity.THREAD" in
    # f-strings/%s on Python 3.11+ (verified this session against 3.10 and 3.14).
    __str__ = str.__str__


@dataclass(frozen=True)
class NetworkState:
    """Network and connectivity state.

    Immutable: a real LIFX device's radio (WiFi or Thread) cannot change
    without a firmware crossgrade. Assigning ``state.connectivity`` after
    construction raises ValueError (translated from FrozenInstanceError by
    DeviceState.__setattr__); assigning ``state.network.connectivity``
    directly raises FrozenInstanceError.
    """

    wifi_signal: float = -45.0
    connectivity: Connectivity = Connectivity.WIFI
```

### `DeviceState.__setattr__` translation (states.py:462, the one line needing a wrap)
```python
# Source: packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:461-463 (current)
import dataclasses
...
            # Delegate to the state object
            try:
                setattr(state_obj, attr_name, value)
            except dataclasses.FrozenInstanceError as e:
                raise ValueError(
                    f"{attr_name} is fixed at device creation and cannot be reassigned"
                ) from e
            return
```

### Byte-fixture test skeleton (test_header.py)
```python
# Source: verified byte output, captured this session at HEAD e610c08e8ea9eab6e2b37cb097b731542ff8d717
from lifx_emulator.protocol.header import LifxHeader

# Header with thread_connection clear, captured before this phase's change.
_HEADER_FIXTURE_BEFORE = bytes.fromhex(
    "0000003463000000d073d5000001000000000000000003070000000000000000e7030000"
)


class TestThreadConnectionBit:
    def test_clear_bit_matches_pre_phase_fixture(self):
        header = LifxHeader(
            source=99, target=bytes.fromhex("d073d5000001") + b"\x00\x00",
            sequence=7, pkt_type=999, res_required=True, ack_required=True,
            tagged=True, thread_connection=False,
        )
        assert header.pack() == _HEADER_FIXTURE_BEFORE

    def test_set_bit_differs_only_in_byte_22(self):
        clear = LifxHeader(
            source=99, target=bytes.fromhex("d073d5000001") + b"\x00\x00",
            sequence=7, pkt_type=999, res_required=True, ack_required=True,
            tagged=True, thread_connection=False,
        ).pack()
        setb = LifxHeader(
            source=99, target=bytes.fromhex("d073d5000001") + b"\x00\x00",
            sequence=7, pkt_type=999, res_required=True, ack_required=True,
            tagged=True, thread_connection=True,
        ).pack()
        diff = [i for i in range(36) if clear[i] != setb[i]]
        assert diff == [22]
        assert setb[22] == clear[22] | 0x08
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| WiFi Ceiling tiles report firmware 3.70 (hard-coded) | WiFi Ceiling tiles report firmware 4.10 (mirrors host) | This phase | Intentional default-output change, called out in SPEC AC 16; not a regression |
| Tile (55) defaults to firmware 3.70, accepts any explicit version | Tile (55) defaults to 3.50, rejects >3.50 and Thread entirely | This phase | Matches real hardware's terminal firmware; two existing tests must migrate in the same commit |

**Deprecated/outdated:** None — no removal of any existing capability, only additive fields and one corrected default.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Tile+Thread rejection message should be enriched to explicitly name "Thread's default cannot be reduced" when the rejection stems from an unrequested Thread default (vs. an explicit override) | Firmware precedence walkthrough | Low — D-06 only requires "a message naming both"; the specific wording enrichment is this researcher's interpretation of how to satisfy that instruction most clearly, not a locked requirement. If skipped, the two-check implementation still satisfies the acceptance criteria (ValueError raised, values present in the message), just with a slightly less explicit message. |
| A2 | Builder step 0 (or a `StateRestorer.peek_connectivity()` helper) is the correct single-read mechanism, rather than some other refactor of `restore_if_available`'s signature | Point 3 / Pitfall 2 | Low — both options were verified to be mechanically sound (methods and types checked to exist); which one the planner picks is explicitly "planner's choice" per D-10, this is not a locked decision either way. |

**If this table is empty:** N/A — see above, both entries are low-risk implementation-detail choices already flagged as discretionary in CONTEXT.md, not load-bearing assumptions about requirements.

## Open Questions

None outstanding. All 13 CONTEXT.md decisions were checked against live source and hold; the one correction (Pitfall 5 / point 12) strengthens rather than reverses the existing recommendation.

## Environment Availability

Not applicable — no external tool/service/runtime dependency exists in this phase beyond the already-installed dev toolchain (confirmed working this session: `uv sync` resolves cleanly, `uv run pytest -q --no-cov -x` passes 1146 tests at baseline `HEAD e610c08`).

**Note on Validation Architecture:** `.planning/config.json` sets `workflow.nyquist_validation: false` explicitly, so the Validation Architecture section is intentionally omitted per the research contract's skip condition. Two facts worth carrying into planning anyway, since they're load-bearing for verification regardless of the nyquist toggle: the exact test commands are `uv run pytest -p no:cacheprovider --no-cov -x` (fast loop) and `uv run pytest` (full suite, `--cov-fail-under=80` enforced in CI); and the baseline is confirmed clean this session — `1146 passed`, zero pre-existing failures, at `HEAD e610c08e8ea9eab6e2b37cb097b731542ff8d717`.

## Security Domain

`.planning/config.json` has no `security_enforcement` key, so per the default rule (absent = enabled) this section applies. This phase has no security-relevant surface: no new input parsing beyond an enum-membership check (`Connectivity(value)`, which is memory-safe stdlib validation, not hand-rolled parsing), no new I/O, no new network exposure. ASVS categories V2 (Auth), V3 (Session), V4 (Access Control), V6 (Crypto) do not apply — this is a pure data-model change to an in-memory test double already documented as "intended for local test use only." V5 (Input Validation) applies narrowly: `Connectivity(value)` and the firmware floor/ceiling `ValueError`s are the input-validation surface, both stdlib/simple-comparison based, no injection or deserialization risk (the persisted JSON `connectivity` key is read via the same `json.load` already used for every other field, not a new parser).

## Sources

### Primary (HIGH confidence — direct source reads and executed commands, this session)
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml` (relevant sections)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py` (full file)
- `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py` (relevant sections)
- `packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py` (relevant sections)
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` (relevant sections)
- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` (relevant sections)
- `packages/lifx-emulator-core/tests/conftest.py`, `test_tile_handlers_extended.py`, `test_async_storage.py`, `test_products_specs.py`, `test_advertised_services.py` (relevant sections)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/protocol/header.py` (full file)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/devices/base.py:79-108` (Connectivity enum)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/tests/test_network/test_connection_connectivity.py` (excerpt)
- `.planning/phases/01-thread-device-identity/01-CONTEXT.md`, `01-SPEC.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` (full)
- `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` (full)
- `.planning/codebase/TESTING.md`, `.planning/codebase/CONVENTIONS.md` (full)
- Executed commands this session: `uv run pytest -q --no-cov -x` (1146 passed baseline), `uv run ruff check --select PLR0913` (confirmed enforcement gap), byte-fixture capture script (point 11), frozen-dataclass mechanics script (point 2), Python 3.10 vs 3.14 enum-formatting scripts (point 12), matrix-product enumeration (point 6), switch-firmware-specs lookup (point 5)

### Secondary (MEDIUM confidence)
- None used beyond primary sources — this phase required no external documentation lookup (pure stdlib/in-repo research).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no dependencies, pure stdlib pattern matched against a sibling repo's existing, working implementation
- Architecture: HIGH — every placement claim backed by a specific file/line read or an executed command this session
- Pitfalls: HIGH — six pitfalls, five directly evidenced by reading the relevant code path or running a reproduction; one (Pitfall 6) is a defensive recommendation for a bug class, not an observed occurrence

**Research date:** 2026-09-09
**Valid until:** Stable — this is an internal data-model change with no external dependency drift risk; re-verify only if `01-SPEC.md`/`01-CONTEXT.md` change or if the codebase's `main` branch moves significantly before planning begins (re-check `git rev-parse HEAD` against `e610c08e8ea9eab6e2b37cb097b731542ff8d717`)
