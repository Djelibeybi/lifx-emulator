# Phase 1: Thread Device Identity - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 15 (11 modified source + 2 new test modules + 2 modified test modules explicitly enumerated in CONTEXT/RESEARCH; conftest.py and 2 more test modules noted as touch-points)
**Analogs found:** 15 / 15 — every file in scope is itself the file to modify (this phase extends existing single-responsibility modules; there are no *new* source modules). The "analog" for each is therefore the **existing precedent pattern within the same file or its established sibling**, principally the `advertised_services` plumbing (PR #156).

This phase has an unusual shape for pattern mapping: CONTEXT.md and RESEARCH.md already did the analog work (every insertion point is verified against live source with exact line numbers). This document restates those findings as direct copy-paste patterns for the planner, organized per file, so PLAN.md tasks can reference exact excerpts without re-deriving them.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `protocol/header.py` | model (wire format) | transform (pack/unpack) | same file, existing `res_required`/`ack_required` bit fields | exact |
| `devices/states.py` | model (dataclass state) | CRUD (attribute routing) | same file, existing `NetworkState.wifi_signal` + `_ATTRIBUTE_ROUTES` | exact |
| `devices/device.py` | domain/controller (packet processing) | request-response | same file, existing `_response_header_template` construction + hard-coded tile firmware | exact |
| `factories/builder.py` | service (builder) | CRUD (compose state) | same file, existing numbered `build()` steps + `with_advertised_services()` | exact |
| `factories/factory.py` | factory/service | CRUD | same file, existing `advertised_services` param threading (PR #156) | exact |
| `factories/firmware_config.py` | service (business rule) | transform | same file, existing `get_firmware_version()` precedence chain | exact |
| `products/specs.py` | model/config loader | transform | same file, existing `default_firmware_major/minor` + `has_firmware_specs` | exact |
| `products/specs.yml` | config (YAML data) | batch | same file, Ceiling entries (176/177) with `default_firmware_*` | exact |
| `devices/state_serializer.py` | utility (serialize) | file-I/O/transform | same file, existing unconditional top-level keys (`serial`, `label`) | exact |
| `devices/state_restorer.py` | utility (deserialize) | file-I/O/transform | same file, existing product-mismatch warning in `restore_if_available()` | exact |
| `devices/__init__.py` | module barrel | — | same file, existing `DeviceState` export | exact |
| `lifx_emulator/__init__.py` | module barrel | — | same file, existing typed-factory exports | exact |
| `tests/test_thread_identity.py` (new) | test | request-response | `tests/test_advertised_services.py` | exact |
| `tests/test_header.py` (new) | test | transform | none exists; use `protocol/header.py`'s own doctest style + `test_advertised_services.py` structure | role-match |
| `tests/test_async_storage.py` (modify) | test | file-I/O | same file, `test_device_storage_save_and_load` | exact |
| `tests/test_products_specs.py` (modify) | test | CRUD | same file, `test_every_switch_pins_its_firmware` | exact |
| `tests/test_tile_handlers_extended.py` (modify) | test | request-response | same file, lines 723 and 931 (SKY tests) | exact |
| `tests/conftest.py` (modify, optional) | test fixture | — | existing `d073d5000001`..`12` serial fixtures | exact |

## Pattern Assignments

### `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py`

**Analog:** same file's existing bit-flag handling.

**Current pack** (lines 81-83):
```python
addr_flags = (1 if self.res_required else 0) | (
    (1 if self.ack_required else 0) << 1
)
```

**Current unpack** (lines 134-135):
```python
res_required = bool(flags & 0b1)
ack_required = bool((flags >> 1) & 0b1)
```

**Pattern to apply:** append `thread_connection: bool = False` as the last dataclass field (after `pkt_type`, matching `lifx-async`'s `src/lifx/protocol/header.py:141-162,207-224` field order exactly), OR bit 3 in `pack()`:
```python
addr_flags = (
    (1 if self.res_required else 0)
    | ((1 if self.ack_required else 0) << 1)
    | ((1 if self.thread_connection else 0) << 3)
)
```
and read it back in `unpack()`:
```python
thread_connection = bool((flags >> 3) & 0b1)
```
Bits 2 and 4-7 need no explicit masking — they are simply never OR'd in, exactly as bits 2-7 are today.

**Byte fixtures to hard-code in `test_header.py`** (captured this session at `HEAD e610c08e8ea9eab6e2b37cb097b731542ff8d717`, before any change — see RESEARCH.md point 11 for the full capture script):
```python
_HEADER_FIXTURE_BEFORE = bytes.fromhex(
    "0000003463000000d073d5000001000000000000000003070000000000000000e7030000"
)
```

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py`

**Analog:** same file's `NetworkState` dataclass and `DeviceState.__setattr__` routed-write path.

**Current `NetworkState`** (lines 47-51):
```python
@dataclass
class NetworkState:
    """Network and connectivity state."""
    wifi_signal: float = -45.0
```

**Current direct-assignment allow-list in `__setattr__`** (lines 94-103) already includes `"network"` — no change needed there; this is what makes `dataclasses.replace(state.network, ...)` work today.

**Current routed-write path** (lines 443-463, the one line to wrap):
```python
if name in self._ATTRIBUTE_ROUTES:
    route = self._ATTRIBUTE_ROUTES[name]
    state_name = route if not isinstance(route, tuple) else route[0]
    ...
    state_obj = object.__getattribute__(self, state_name)
    if state_obj is None:
        return
    setattr(state_obj, attr_name, value)   # line 462 — wrap this
    return
```

**Pattern to apply** — new `Connectivity` enum beside `NetworkState`, mirroring `lifx-async`'s `src/lifx/devices/base.py:79-96`:
```python
from enum import Enum

class Connectivity(str, Enum):
    """How a device's radio reaches the network."""

    WIFI = "wifi"
    THREAD = "thread"

    # Render as the bare value on every supported Python version (3.10-3.14).
    __str__ = str.__str__


@dataclass(frozen=True)
class NetworkState:
    """Network and connectivity state.

    Immutable: a real LIFX device's radio (WiFi or Thread) cannot change
    without a firmware crossgrade. Assigning ``state.connectivity`` after
    construction raises ValueError; assigning ``state.network.connectivity``
    directly raises FrozenInstanceError.
    """

    wifi_signal: float = -45.0
    connectivity: Connectivity = Connectivity.WIFI
```

**`__setattr__` translation** — wrap the existing `setattr(state_obj, attr_name, value)` line:
```python
import dataclasses
...
try:
    setattr(state_obj, attr_name, value)
except dataclasses.FrozenInstanceError as e:
    raise ValueError(
        f"{attr_name} is fixed at device creation and cannot be reassigned"
    ) from e
return
```

Add `"connectivity": "network"` to `_ATTRIBUTE_ROUTES` beside the existing `"wifi_signal": "network"` entry.

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`

**Analog:** same file's `_response_header_template` construction and hard-coded tile firmware — this is the PITFALLS.md "single choke point" pattern.

**Current template** (lines 89-98):
```python
self._response_header_template = LifxHeader(
    source=0,
    target=self.state.get_target_bytes(),
    sequence=0,
    tagged=False,
    pkt_type=0,
    size=0,
)
```
**Pattern to apply** — add one kwarg, derived from `self.state.connectivity` which is already set at this point (`self.state` assigned at `device.py:70`):
```python
    thread_connection=self.state.connectivity == Connectivity.THREAD,
```
No other call site needs to change — `_create_response_header()` (lines 218-244) does `copy.copy()` of this template and only overwrites `source`/`sequence`/`pkt_type`/`size`, so every reply path (normal replies, both ack paths including the server's `_send_ack()` at `server.py:197`, and `StateUnhandled`) inherits the bit automatically.

**Current hard-coded per-tile firmware** (lines 136-143, inside `if self.state.has_matrix and self.state.tile_count > 0` / `if not self.state.tile_devices`):
```python
self.state.tile_devices.append(
    {
        ...
        "firmware_build": int(time.time()),
        "firmware_version_minor": 70,   # -> self.state.version_minor
        "firmware_version_major": 3,    # -> self.state.version_major
        "colors": tile_colors,
    }
)
```
**Pattern to apply:** replace the two literals with `self.state.version_major` / `self.state.version_minor` (already resolved by build time). Two-line value swap; no dict-key rename (confirmed against `handlers/tile_handlers.py:51-52` which reads these exact keys back).

---

### `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`

**Analog:** same file's `with_advertised_services()` and the numbered `build()` steps — direct precedent PR #156.

**Existing optional-param pattern** (lines 111, 219-233, 395):
```python
self._advertised_services: list[tuple[int, int]] | None = None
...
def with_advertised_services(
    self, advertised_services: list[tuple[int, int]]
) -> DeviceBuilder:
    """..."""
    self._advertised_services = advertised_services
    return self
...
# inside build(), passed straight through:
    advertised_services=self._advertised_services,
```
**Pattern to apply:** add `self._connectivity: Connectivity | str | None = None` in `__init__`, and `with_connectivity(self, connectivity: Connectivity | str) -> DeviceBuilder` following the identical shape.

**Current numbered `build()` steps** (lines 248-340, abbreviated):
```
1. Generate/validate serial (255)
2. _apply_product_defaults() (258)
3. self._firmware_config.get_firmware_version(product_id=..., extended_multizone=..., override=self._firmware_version) (261-265)
4. Default color (268)
5. _create_core_state(...) (271)
6. network = NetworkState(); location = ...; group = ...; waveform = ... (274-277)
7. Capability-specific states (280-283)
...
11. Restore saved state via StateRestorer (332-335) — only if self._storage is set
12. Construct EmulatedLifxDevice (337-340)
```
**Pattern to apply:** insert a new step 0 before step 1, resolving effective connectivity (argument > saved state > WiFi) — read the saved dict once via `self._storage.load_device_state(serial)` if storage is set, per D-10. This resolved value feeds step 3's `get_firmware_version(..., connectivity=effective_connectivity)` and step 6's `NetworkState(connectivity=effective_connectivity, wifi_signal=0.0 if effective_connectivity == Connectivity.THREAD else -45.0)`.

---

### `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py`

**Analog:** same file's `advertised_services` parameter, confirmed appended **last** to every function and threaded through unconditionally.

**Current pattern, `create_color_light`** (lines 16-30, full function read this session):
```python
def create_color_light(
    serial: str | None = None,
    firmware_version: tuple[int, int] | None = None,
    storage: DevicePersistenceAsyncFile | None = None,
    scenario_manager: HierarchicalScenarioManager | None = None,
    advertised_services: list[tuple[int, int]] | None = None,
) -> EmulatedLifxDevice:
    """Create a regular color light (LIFX Color)"""
    return create_device(
        91,
        serial=serial,
        firmware_version=firmware_version,
        storage=storage,
        scenario_manager=scenario_manager,
        advertised_services=advertised_services,
    )  # LIFX Color
```
**Current gating in `create_device()`** (lines 272-273):
```python
if advertised_services is not None:
    builder.with_advertised_services(advertised_services)
```
**Pattern to apply:** append `connectivity: Connectivity | str | None = None` as the last parameter to all 7 typed factories and `create_device()`, thread it through identically (`connectivity=connectivity` in every typed factory's `create_device(...)` call), and gate it in `create_device()`:
```python
if connectivity is not None:
    builder.with_connectivity(connectivity)
```
This repeats across all 8 functions — apply the identical diff shape at each of the parameter-count table's rows (RESEARCH.md section 5).

---

### `packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py`

**Analog:** same file's existing `get_firmware_version()` — single precedence chain, extend not duplicate.

**Current signature** (lines 24-77):
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
**Pattern to apply** — add `VERSION_THREAD = (4, 200)` constant and a fourth parameter (still within `max-args = 5`):
```python
    VERSION_THREAD = (4, 200)

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
            raise ValueError(
                f"Thread firmware must be >= {self.VERSION_THREAD}, got {result}"
            )

        if product_id is not None:
            max_fw = get_max_firmware_version(product_id)
            if max_fw is not None and result > max_fw:
                raise ValueError(
                    f"Firmware {result} exceeds product {product_id}'s maximum {max_fw}"
                )
        return result
```
Only one call site exists (`builder.py:261`) plus doctests in this file and three call sites in `test_products_specs.py:334-365` — all keep working with the new param defaulting to `None`.

---

### `packages/lifx-emulator-core/src/lifx_emulator/products/specs.py` / `specs.yml`

**Analog:** same file's existing `default_firmware_major/minor` + `has_firmware_specs` property, and `get_default_firmware_version()` accessor.

**Current `ProductSpecs` fields** (specs.py:16-68): `default_firmware_major`, `default_firmware_minor`, `has_firmware_specs` property (62-68).

**Pattern to apply:** add `max_firmware_major: int | None = None`, `max_firmware_minor: int | None = None` mirroring the default pair, plus `has_max_firmware_specs` property mirroring `has_firmware_specs`, plus `get_max_firmware_version(product_id) -> tuple[int, int] | None` mirroring `get_default_firmware_version` (specs.py:192-207) exactly. `SpecsRegistry.load_from_file()` needs two more `.get()` calls at the parse site (specs.py:112-113, immediately after the existing default-firmware parse).

**Current Tile entry, `specs.yml:214-220`:**
```yaml
55:  # LIFX Tile, 8x8 zone matrix, chainable up to 5
  default_tile_count: 5
  min_tile_count: 1
  max_tile_count: 5
  tile_width: 8
  tile_height: 8
  notes: LIFX Tile, 8x8 zone matrix, chainable up to 5
```
**Analog for the new keys** — Ceiling entries `176`/`177` already carry the pattern to copy:
```yaml
default_firmware_major: 4
default_firmware_minor: 10
```
**Pattern to apply to product 55:**
```yaml
55:  # LIFX Tile, 8x8 zone matrix, chainable up to 5 -- discontinued, terminal firmware 3.50
  default_tile_count: 5
  min_tile_count: 1
  max_tile_count: 5
  tile_width: 8
  tile_height: 8
  default_firmware_major: 3
  default_firmware_minor: 50
  max_firmware_major: 3
  max_firmware_minor: 50
  notes: LIFX Tile, 8x8 zone matrix, chainable up to 5. Discontinued; terminal firmware 3.50.
```
Also update the header comment block (`specs.yml:36-45`) documenting firmware precedence, in the same commit as the `FirmwareConfig` change (D-04).

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/state_serializer.py`

**Analog:** same file's unconditional top-level keys (`serial`, `label` — not inside any `if has_X:` guard, since every device has them).

**Pattern to apply** — add near the top of `serialize_device_state()`'s dict construction (lines 89-183), unconditionally, alongside `serial`/`label`:
```python
state_dict["connectivity"] = str(device_state.connectivity)
```
(relies on `Connectivity.__str__ = str.__str__` from `states.py` to serialize as the bare value, not `Connectivity.THREAD`).

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py`

**Analog:** same file's existing product-mismatch warning in `restore_if_available()` (lines 32-70) — the template for the connectivity-mismatch warning shape, and the "if key in saved_state" tolerant-read style in `_restore_core_state`.

**Important divergence from the naive analog:** connectivity restoration does **NOT** go inside `_restore_core_state`, `_restore_location_and_group`, or a new fourth `_restore_*` method — those all mutate non-frozen sub-states with `state.core.label = saved_state["label"]`-style direct assignment, which raises `FrozenInstanceError` against the now-frozen `NetworkState`. Instead, per D-10, add a small read-only helper (or have the builder call `self._storage.load_device_state(serial)` directly) that the builder's new step 0 calls **before** `NetworkState` is constructed. Whichever shape is chosen, `load_device_state` must be called exactly once per `build()` (Pitfall 2) — do not add a second internal call inside `restore_if_available()` if step 0 already read the file.

**Warning pattern to mirror** (existing product-mismatch shape — same log level and lazy-`%s` style applies to the bad-connectivity-value warning):
```python
logger.warning(
    "Saved connectivity %r for %s is unrecognised; defaulting to wifi",
    saved_value, serial,
)
```

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py` and `lifx_emulator/__init__.py`

**Analog:** same files' existing `DeviceState` / typed-factory export lines.

**Pattern to apply, `devices/__init__.py`:**
```python
from lifx_emulator.devices.states import Connectivity, DeviceState
```
and add `"Connectivity"` to `__all__`.

**Pattern to apply, `lifx_emulator/__init__.py`:**
```python
from lifx_emulator.devices import Connectivity, EmulatedLifxDevice
```
and add `"Connectivity"` to `__all__`.

---

### `packages/lifx-emulator-core/tests/test_thread_identity.py` (new)

**Analog:** `packages/lifx-emulator-core/tests/test_advertised_services.py` (lines 1-24) — module docstring, `Test*` classes, a small packet-building helper, `device.process_packet(header, None)` call style.

```python
"""Tests for Thread device identity: connectivity, firmware precedence, wifi_signal, header bit."""
```
Reuse the `test_every_switch_pins_its_firmware` iteration style from `tests/test_products_specs.py:394-401` for the "every matrix product except 55 accepts Thread" acceptance test:
```python
def test_every_switch_pins_its_firmware(self):
    from lifx_emulator.factories import create_device
    from lifx_emulator.products.registry import PRODUCTS

    for pid, info in PRODUCTS.items():
        if info.has_relays:
            state = create_device(pid).state
            assert (state.version_major, state.version_minor) == (4, 100), f"product {pid}"
```

### `packages/lifx-emulator-core/tests/test_header.py` (new)

**Analog:** no direct test-file analog exists (confirmed by `find`); use the RESEARCH.md-verified byte-fixture skeleton directly:
```python
from lifx_emulator.protocol.header import LifxHeader

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
        clear = LifxHeader(..., thread_connection=False).pack()
        setb = LifxHeader(..., thread_connection=True).pack()
        diff = [i for i in range(36) if clear[i] != setb[i]]
        assert diff == [22]
        assert setb[22] == clear[22] | 0x08
```

### `tests/test_async_storage.py` (modify)

**Analog:** same file's existing `test_device_storage_save_and_load` (lines 27-53):
```python
async def test_device_storage_save_and_load(self, temp_storage):
    device = create_color_light("d073d5123456", storage=temp_storage)
    ...
    await temp_storage.save_device_state(state)
    await temp_storage.shutdown()
    saved_state = temp_storage.load_device_state(state.serial)
    new_device = create_device(saved_state["product"], serial=saved_state["serial"], storage=temp_storage)
```
**Pattern to apply:** create a Thread device with `storage=temp_storage`, save, then `create_device(pid, serial=..., storage=temp_storage)` again with **no** `connectivity=` argument (proving restore not re-specification) and assert `new_device.state.connectivity == "thread"` plus bit 3 on its first reply.

### `tests/test_tile_handlers_extended.py` (modify)

**Analog:** the two SKY tests themselves (lines 720-757, 928-970) — only the product ID literal changes.
```python
device = create_device(55, tile_count=1, firmware_version=(4, 4))   # -> create_device(185, tile_count=1, firmware_version=(4, 4))
```
**Must land in the same task/commit as the `specs.yml` Tile ceiling change** (Pitfall 3) — otherwise these two tests go red the instant the ceiling ships, since `(4,4) > (3,50)` raises before the fixture device can even be constructed.

## Shared Patterns

### Optional per-device value threaded through factories (the master pattern for this whole phase)
**Source:** PR #156's `advertised_services` plumbing — `factories/factory.py` (append-last param, unconditional pass-through) + `factories/builder.py` (`with_<name>()` + `self._<name>` + unconditional `build()` pass-through).
**Apply to:** `factory.py` (8 functions), `builder.py` (`with_connectivity()`), and by extension `firmware_config.py`'s new `connectivity` parameter (same "optional, defaults to None, no-op when absent" shape).

### `ValueError` with f-string message for argument validation
**Source:** project convention (`CONVENTIONS.md`), confirmed live in `firmware_config.py`'s planned floor/ceiling checks and `states.py`'s planned `FrozenInstanceError` → `ValueError` translation.
```python
raise ValueError(f"Thread firmware must be >= {self.VERSION_THREAD}, got {result}")
```
**Apply to:** `states.py` (§Connectivity coercion + reassignment), `firmware_config.py` (floor/ceiling).

### `logger.warning("...%s", ...)` lazy formatting
**Source:** `state_restorer.py`'s existing product-mismatch warning.
**Apply to:** the bad/missing-connectivity restore path (D-09).

### Frozen dataclass + `dataclasses.replace()` for immutable sub-state
**Source:** stdlib mechanic, verified this session to interoperate with `DeviceState.__setattr__`'s existing `"network"` direct-assignment branch — no new mechanism, just apply `@dataclass(frozen=True)` to `NetworkState`.
**Apply to:** `devices/states.py` only.

## No Analog Found

None — every file in scope has a same-file or established-sibling precedent (PR #156's `advertised_services` plumbing is the load-bearing precedent for the factory/builder chain; the frozen-dataclass mechanic and header-bit addition are stdlib/sibling-repo (`lifx-async`) precedents rather than in-repo ones, but both were verified by direct execution this session per RESEARCH.md).

## Metadata

**Analog search scope:** `packages/lifx-emulator-core/src/lifx_emulator/{protocol,devices,factories,products}/`, `packages/lifx-emulator-core/tests/`
**Files scanned:** 11 source files (full read via RESEARCH.md verification session) + factory.py/specs.yml spot-checked directly this session + 5 test files
**Pattern extraction date:** 2026-09-09
**Note:** This phase is unusual — CONTEXT.md and RESEARCH.md already performed exhaustive line-level verification against live source (commit `e610c08e8ea9eab6e2b37cb097b731542ff8d717`) before this pattern-mapping pass ran. This document's job was to re-package those findings as planner-ready copy-paste patterns, not to discover new information. Excerpts above were cross-checked directly against `factory.py` and `specs.yml` this session; all others are taken verbatim from RESEARCH.md's verified reads (no re-read of ranges already in context).
