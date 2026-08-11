# Upstream Sync — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sync the product catalogue and protocol spec from LIFX upstream, fix and curate `specs.yml`, and wire the new button/sensor/uplight device state — the foundation the behaviour plan builds on.

**Architecture:** Two artefacts are regenerated from upstream (`registry.py` from `products.json`, `packets.py`/`protocol_types.py` from `protocol.yml`). `specs.yml` is hand-maintained for matrix geometry the catalogue lacks. `DeviceStateBuilder` reads specs to populate `DeviceState`. This plan touches all four, in dependency order.

**Tech Stack:** Python 3.14, uv workspace, pytest, ruff (McCabe complexity ≤ 10), pyright (standard). Generators use PyYAML + urllib.

## Global Constraints

- Australian English spelling in all prose/comments/identifiers.
- Never use "wide tile device" — use "large matrix device" / "chained matrix device".
- All functions: cyclomatic complexity ≤ 10 (Ruff McCabe).
- Pyright standard mode must pass.
- `registry.py` and `packets.py`/`protocol_types.py` are **auto-generated — never hand-edit**. Change them only by editing the generator/source and re-running it.
- Regen commands:
  - `uv run python -m lifx_emulator.products.generator`
  - `uv run python -m lifx_emulator.protocol.generator`
- Commit with `git commit -s` (sign-off + GPG signing are automatic).
- Run tests with `uv run pytest`; lint `uv run ruff check .`; types `uv run pyright`.

---

### Task 1: Fix `specs.yml` parse error + correct new matrix dimensions

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml`
- Test: `packages/lifx-emulator-core/tests/test_specs.py` (create if absent)

**Interfaces:**
- Consumes: existing `SpecsRegistry.get_tile_dimensions(pid) -> tuple[int,int] | None`.
- Produces: valid, loadable `specs.yml` with Mirror 267/268 = 5×10, Path 229 = 3×2, Spot 172 = 3×1.

The file currently does not parse — the auto-added Ceiling entries have invalid escaping (`notes: "LIFX Ceiling 13\\""` around lines 418/426), and the new matrix entries (172, 229, 267, 268) carry wrong `8×8` placeholder dimensions.

- [ ] **Step 1: Write the failing test**

```python
# packages/lifx-emulator-core/tests/test_specs.py
from lifx_emulator.products.specs import SpecsRegistry


def test_specs_yaml_loads_and_new_matrix_dims_correct():
    reg = SpecsRegistry()  # loads specs.yml on init
    assert reg.get_tile_dimensions(267) == (5, 10)   # Mirror US
    assert reg.get_tile_dimensions(268) == (5, 10)   # Mirror Intl
    assert reg.get_tile_dimensions(229) == (3, 2)    # new Path Intl
    assert reg.get_tile_dimensions(172) == (3, 1)    # new Spot
    assert reg.get_tile_dimensions(265) == (8, 8)    # Ceiling 13"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_specs.py -v`
Expected: FAIL — YAML parse error on load (or wrong dims once parsing is fixed).

- [ ] **Step 3: Fix the YAML + dimensions**

In `specs.yml`:
1. Repair the two broken `notes` values. Use single quotes to avoid escaping the inch mark:
   - `265`: `notes: 'LIFX Ceiling 13"'`
   - `266`: `notes: 'LIFX Ceiling 13" Intl'`
   (Fix the block comments on those keys the same way, e.g. `# LIFX Ceiling 13"`.)
2. Correct the placeholder dimensions:
   - `267` and `268` (Mirror): `tile_width: 5`, `tile_height: 10`.
   - `229` (Path Intl): `tile_width: 3`, `tile_height: 2`.
   - `172` (Spot): `tile_width: 3`, `tile_height: 1`.
   - Leave `265`/`266` (Ceiling 13") at `tile_width: 8`, `tile_height: 8`.
3. Update the Mirror `notes` to describe the split, e.g. `notes: 'LIFX Mirror, 5x10 matrix (provisional), zones 0-24 front, 25-49 rear'`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_specs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml packages/lifx-emulator-core/tests/test_specs.py
git commit -s -m "fix(specs): repair specs.yml YAML + correct Mirror/Path/Spot matrix dims"
```

---

### Task 2: Add `uplight_zone_count` to specs + populate Ceiling/Mirror

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/products/specs.py`
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml`
- Test: `packages/lifx-emulator-core/tests/test_specs.py`

**Interfaces:**
- Produces:
  - `ProductSpec.uplight_zone_count: int | None`
  - `SpecsRegistry.get_uplight_zone_count(pid: int) -> int | None`
  - module-level `get_uplight_zone_count(pid: int) -> int | None` (mirrors existing `get_tile_dimensions` convenience function)

`uplight_zone_count` = number of trailing matrix zones that are the uplight (Ceiling) / rear (Mirror). Ceiling = 1; Mirror = 25.

- [ ] **Step 1: Write the failing test**

```python
def test_uplight_zone_count():
    from lifx_emulator.products.specs import get_uplight_zone_count
    assert get_uplight_zone_count(176) == 1    # Ceiling 8x8
    assert get_uplight_zone_count(201) == 1    # Ceiling 16x8
    assert get_uplight_zone_count(265) == 1    # Ceiling 13"
    assert get_uplight_zone_count(267) == 25   # Mirror rear
    assert get_uplight_zone_count(55) is None  # plain Tile — no uplight
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_specs.py::test_uplight_zone_count -v`
Expected: FAIL — `ImportError`/`AttributeError` (no such function).

- [ ] **Step 3: Implement**

In `specs.py`:
1. Add to the `ProductSpec` dataclass (alongside `tile_width`/`tile_height`):
   `uplight_zone_count: int | None = None`
2. In the loader (where `specs_data.get("tile_height")` etc. are read), add:
   `uplight_zone_count=specs_data.get("uplight_zone_count"),`
3. Add the registry method + module convenience function, mirroring `get_tile_dimensions`:

```python
    def get_uplight_zone_count(self, product_id: int) -> int | None:
        """Number of trailing matrix zones that form the uplight (Ceiling)
        or rear (Mirror). None for matrix devices without a split."""
        spec = self._specs.get(product_id)
        return spec.uplight_zone_count if spec else None
```
   ...and the module-level wrapper next to the existing ones:
```python
def get_uplight_zone_count(product_id: int) -> int | None:
    return _default_registry().get_uplight_zone_count(product_id)
```
   (Match the exact singleton/wrapper pattern already used by `get_tile_dimensions` in this file.)

In `specs.yml`, add `uplight_zone_count:` to:
   - `176`, `177` → `1`
   - `201`, `202` → `1`
   - `265`, `266` → `1`
   - `267`, `268` → `25`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_specs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/products/specs.py packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml packages/lifx-emulator-core/tests/test_specs.py
git commit -s -m "feat(specs): add uplight_zone_count for Ceiling + Mirror"
```

---

### Task 3: Regenerate the product registry from upstream

**Files:**
- Modify (regenerate): `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py`
- Test: `packages/lifx-emulator-core/tests/test_registry.py` (create if absent)

**Interfaces:**
- Consumes: `products.generator` module, live `products.json`.
- Produces: `PRODUCTS[267]`/`PRODUCTS[268]` (Mirror, matrix+buttons), plus new Ceiling 265/266, Path 229, and other new pids.

- [ ] **Step 1: Write the failing test**

```python
# packages/lifx-emulator-core/tests/test_registry.py
from lifx_emulator.products.registry import PRODUCTS, ProductCapability


def test_mirror_and_new_products_present():
    for pid in (267, 268):
        info = PRODUCTS[pid]
        assert info.has_matrix
        assert info.has_buttons
        assert "Mirror" in info.name
    assert 265 in PRODUCTS and 266 in PRODUCTS   # Ceiling 13"
    assert 229 in PRODUCTS                        # Path Intl
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_registry.py -v`
Expected: FAIL — `KeyError: 267`.

- [ ] **Step 3: Regenerate**

Run: `uv run python -m lifx_emulator.products.generator`
This rewrites `registry.py` from current upstream `products.json`. Names change to upstream verbatim (drops ` US` suffixes); 15 new products appear. Do not hand-edit the output.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Guard against name-string breakage**

Run: `uv run pytest packages/lifx-emulator-core/ packages/lifx-emulator/ -q`
Expected: PASS. If anything asserts an old product name string, update that assertion (names now follow upstream). Also grep app/CLI/docs for hardcoded old names:
Run: `grep -rniE "LIFX (Luna|Mirror|Ceiling|Spot|Path|Candle|Tube) (US|Intl)" packages/lifx-emulator/src`
Fix any hardcoded matches to not depend on the ` US` suffix.

- [ ] **Step 6: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/products/registry.py packages/lifx-emulator-core/tests/test_registry.py
git commit -s -m "feat(products): regenerate registry from upstream (adds Mirror 267/268 + new products)"
```

---

### Task 4: Regenerate protocol + enable Button (keep Relay filtered)

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py`
- Modify (regenerate): `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py`, `.../protocol/protocol_types.py`
- Test: `packages/lifx-emulator-core/tests/test_protocol_new_packets.py` (create)

**Interfaces:**
- Produces: `Sensor.GetAmbientLight` (401) / `Sensor.StateAmbientLight` (402); `Button.Get/Set/State` (905/906/907) + `Button.GetConfig/SetConfig/StateConfig` (909/910/911); `protocol_types.ButtonBacklightHsbk`.

Spiked 2026-08-11: un-filtering Button regenerates cleanly. Relay stays filtered (out of scope).

- [ ] **Step 1: Write the failing test**

```python
# packages/lifx-emulator-core/tests/test_protocol_new_packets.py
from lifx_emulator.protocol.packets import Sensor, Button
from lifx_emulator.protocol.protocol_types import ButtonBacklightHsbk


def test_sensor_ambient_light_roundtrip():
    s = Sensor.StateAmbientLight(lux=123.5)
    assert Sensor.StateAmbientLight.unpack(s.pack()).lux == 123.5
    assert Sensor.GetAmbientLight.PKT_TYPE == 401
    assert Sensor.StateAmbientLight.PKT_TYPE == 402


def test_button_config_roundtrip():
    cfg = Button.StateConfig(
        haptic_duration_ms=65,
        backlight_on_color=ButtonBacklightHsbk(hue=0, saturation=0, brightness=65535, kelvin=3500),
        backlight_off_color=ButtonBacklightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500),
    )
    rt = Button.StateConfig.unpack(cfg.pack())
    assert rt.haptic_duration_ms == 65
    assert Button.State.PKT_TYPE == 907
    assert Button.StateConfig.PKT_TYPE == 911
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_protocol_new_packets.py -v`
Expected: FAIL — `ImportError` (no `Sensor`/`Button` in packets.py).

- [ ] **Step 3: Un-filter Button in the generator**

In `protocol/generator.py`:
1. `should_skip_button_relay` (≈ line 1234): change the body to only skip Relay:
   ```python
   return name.startswith("Relay")
   ```
   and rename is optional; update the docstring to say "Relay related" only.
2. `filter_button_relay_packets` (≈ line 1265): change the category exclusion to:
   ```python
   if category not in ("relay",)
   ```
3. Update the "Filtering out Button and Relay items..." print string to "Filtering out Relay items...".

- [ ] **Step 4: Regenerate**

Run: `uv run python -m lifx_emulator.protocol.generator`
Expected output includes `Validation passed!` and `Found 1 unions`. `packets.py` now has `class Sensor` and `class Button`.

- [ ] **Step 5: Run tests to verify they pass + existing protocol unchanged**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_protocol_new_packets.py packages/lifx-emulator-core/tests/ -k "protocol or packet or header" -v`
Expected: PASS, including all pre-existing protocol round-trip tests (Device/Light/MultiZone/Tile unchanged).

- [ ] **Step 6: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py packages/lifx-emulator-core/src/lifx_emulator/protocol/protocol_types.py packages/lifx-emulator-core/tests/test_protocol_new_packets.py
git commit -s -m "feat(protocol): regenerate + enable Button/Sensor packets (Relay still filtered)"
```

---

### Task 5: Wire ambient-light, button and uplight state into `DeviceState` + builder

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py`
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`
- Test: `packages/lifx-emulator-core/tests/test_device_state_new_fields.py` (create)

**Interfaces:**
- Consumes: `get_uplight_zone_count` (Task 2); `ButtonBacklightHsbk` (Task 4); `PRODUCTS` (Task 3).
- Produces on `DeviceState`:
  - `ambient_light_lux: float = 0.0`
  - `buttons_state: ButtonsState` (new nested dataclass) with
    `haptic_duration_ms: int = 0`, `backlight_on: ButtonBacklightHsbk`, `backlight_off: ButtonBacklightHsbk`, `buttons: list = field(default_factory=list)`
  - `uplight_zone_count: int | None = None`
  - helper properties `downlight_zone_count -> int | None`, `has_uplight -> bool`

Seeding rule (A4): a device is treated as sensor-bearing (default lux seeded non-zero, `100.0`) when `has_buttons or has_matrix or version_major >= 4`; otherwise lux stays `0.0`. Always configurable.

- [ ] **Step 1: Write the failing test**

```python
# packages/lifx-emulator-core/tests/test_device_state_new_fields.py
from lifx_emulator.factories import create_device


def test_mirror_state_has_buttons_sensor_uplight():
    dev = create_device(267)          # Mirror
    st = dev.state
    assert st.has_buttons
    assert st.ambient_light_lux == 100.0     # seeded (buttons + matrix)
    assert st.uplight_zone_count == 25
    assert st.downlight_zone_count == 25     # 50 total - 25


def test_plain_bulb_reports_zero_lux():
    dev = create_device(22)           # LIFX Color 1000 A19-class bulb, no sensor
    assert dev.state.ambient_light_lux == 0.0
    assert dev.state.uplight_zone_count is None
```

(If pid 22 is not a plain non-matrix, non-4.x bulb in the regenerated registry, pick any colour bulb whose firmware major < 4 and `has_matrix`/`has_buttons` are false; verify with `PRODUCTS`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_device_state_new_fields.py -v`
Expected: FAIL — `AttributeError: ambient_light_lux`.

- [ ] **Step 3: Implement state fields + builder seeding**

In `states.py`:
1. Add a nested dataclass near the other nested states:
```python
@dataclass
class ButtonsState:
    """Button config + per-button state for button-capable devices."""
    haptic_duration_ms: int = 0
    backlight_on: ButtonBacklightHsbk = field(
        default_factory=lambda: ButtonBacklightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
    )
    backlight_off: ButtonBacklightHsbk = field(
        default_factory=lambda: ButtonBacklightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500)
    )
    buttons: list = field(default_factory=list)
```
   Import `ButtonBacklightHsbk` from `lifx_emulator.protocol.protocol_types`.
2. On `DeviceState` add:
   - `ambient_light_lux: float = 0.0`
   - `uplight_zone_count: int | None = None`
   - `buttons_state: ButtonsState = field(default_factory=ButtonsState)`
3. Add helper properties:
```python
    @property
    def has_uplight(self) -> bool:
        return self.uplight_zone_count is not None

    @property
    def downlight_zone_count(self) -> int | None:
        if self.uplight_zone_count is None or not self.has_matrix:
            return None
        return self.tile_width * self.tile_height - self.uplight_zone_count
```
   (Use whatever the DeviceState exposes for total matrix zones — if width/height live on a nested `MatrixState`, read them from there.)

In `builder.py`, in the method that finalises `DeviceState` (near where `has_buttons=...` is set, ≈ line 280 / `_apply_product_defaults`):
```python
from lifx_emulator.products.specs import get_uplight_zone_count
...
uplight = get_uplight_zone_count(self._product_info.pid)
has_sensor = (
    self._product_info.has_buttons
    or self._product_info.has_matrix
    or version_major >= 4
)
ambient_lux = 100.0 if has_sensor else 0.0
```
   Pass `ambient_light_lux=ambient_lux` and `uplight_zone_count=uplight` into the `DeviceState(...)` construction. Use the builder's already-resolved firmware major for `version_major`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_device_state_new_fields.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/devices/states.py packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py packages/lifx-emulator-core/tests/test_device_state_new_fields.py
git commit -s -m "feat(devices): add ambient-light, button and uplight state + builder seeding"
```

---

### Task 6: Foundation gate — full suite + lint + types

**Files:** none (verification only).

- [ ] **Step 1: Full test suite**

Run: `uv run pytest`
Expected: all pass (both packages).

- [ ] **Step 2: Lint**

Run: `uv run ruff check .`
Expected: clean. Fix any complexity > 10 by extracting helpers.

- [ ] **Step 3: Types**

Run: `uv run pyright`
Expected: clean.

- [ ] **Step 4: Commit any fixups**

```bash
git commit -s -am "chore: foundation lint/type fixups" || echo "nothing to fix"
```

---

## Self-Review

- **Spec coverage:** units 1 (registry regen → Task 3), 2 (specs curation → Tasks 1–2), 3 (protocol regen + Button un-filter → Task 4), 4 (capabilities/state → Task 5). Units 5–7 (handlers, behaviour, cross-cutting tests) are the **behaviour plan**.
- **Placeholders:** none — all steps carry real code/commands.
- **Type consistency:** `uplight_zone_count` (`int | None`), `ambient_light_lux` (`float`), `ButtonBacklightHsbk`, `ButtonsState`, `get_uplight_zone_count` used consistently across tasks and match the behaviour plan.
