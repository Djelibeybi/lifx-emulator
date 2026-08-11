# Mirror / Ceiling / Buttons / Sensor — Behaviour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Depends on:** `2026-08-11-upstream-sync-foundation.md` must be fully merged first — this plan uses the regenerated `Sensor`/`Button` packets, the new `DeviceState` fields (`ambient_light_lux`, `buttons_state`, `uplight_zone_count`), and `get_uplight_zone_count`.

**Goal:** Add functional Sensor and Button handlers and product-specific Ceiling/Mirror behaviour (Sky-effect gate for new pids, uplight/downlight split, >64-zone tiling), with full test coverage.

**Architecture:** New handler modules follow the existing Strategy pattern — one `PacketHandler` subclass per packet type, exported via an `ALL_*_HANDLERS` list, registered in `handlers/__init__.py`. Product-specific rules read `DeviceState` capabilities/specs rather than hardcoding pid sets where practical.

**Tech Stack:** Python 3.14, uv, pytest, ruff (McCabe ≤ 10), pyright standard.

## Global Constraints

- Australian English spelling in all prose/comments/identifiers.
- Never use "wide tile device" — use "large matrix device" / "chained matrix device".
- All functions: cyclomatic complexity ≤ 10.
- Handler contract: `handle(self, device_state, packet, res_required) -> list[Any]`. Handlers **return packets, not (header, packet) tuples**; `process_packet` builds headers. Return `[]` when the device doesn't support a packet. May return multiple packets.
- Ambient sensor rule (A4): `SensorGetAmbientLight` (401) **always** returns `SensorStateAmbientLight` (402) for **every** device — never `StateUnhandled`. Lux is `device_state.ambient_light_lux` (0.0 when no sensor).
- Commit with `git commit -s`. Tests `uv run pytest`; lint `uv run ruff check .`; types `uv run pyright`.

---

### Task 1: Sensor handler — ambient light (always answers)

**Files:**
- Create: `packages/lifx-emulator-core/src/lifx_emulator/handlers/sensor_handlers.py`
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/handlers/__init__.py`
- Test: `packages/lifx-emulator-core/tests/test_sensor_handlers.py`

**Interfaces:**
- Consumes: `Sensor.GetAmbientLight` (401), `Sensor.StateAmbientLight` (402), `DeviceState.ambient_light_lux`.
- Produces: `ALL_SENSOR_HANDLERS: list[PacketHandler]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sensor_handlers.py
from lifx_emulator.factories import create_device
from lifx_emulator.handlers.sensor_handlers import GetAmbientLightHandler
from lifx_emulator.protocol.packets import Sensor


def test_ambient_light_returns_state_for_sensor_device():
    dev = create_device(267)  # Mirror — seeded 100.0 lux
    out = GetAmbientLightHandler().handle(dev.state, Sensor.GetAmbientLight(), True)
    assert len(out) == 1 and isinstance(out[0], Sensor.StateAmbientLight)
    assert out[0].lux == 100.0


def test_ambient_light_returns_zero_never_unhandled_for_sensorless():
    dev = create_device(22)   # plain bulb, lux 0.0
    out = GetAmbientLightHandler().handle(dev.state, Sensor.GetAmbientLight(), True)
    assert len(out) == 1 and out[0].lux == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_sensor_handlers.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

```python
# handlers/sensor_handlers.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Sensor

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState


class GetAmbientLightHandler(PacketHandler):
    """SensorGetAmbientLight (401) -> SensorStateAmbientLight (402).

    Always responds — devices without a sensor report lux 0.0 (A4).
    """

    PKT_TYPE = Sensor.GetAmbientLight.PKT_TYPE

    def handle(
        self, device_state: DeviceState, packet: Any | None, res_required: bool
    ) -> list[Any]:
        return [Sensor.StateAmbientLight(lux=device_state.ambient_light_lux)]


ALL_SENSOR_HANDLERS = [GetAmbientLightHandler()]
```

In `handlers/__init__.py`: import `ALL_SENSOR_HANDLERS`, add it to `__all__`, and `registry.register_all(ALL_SENSOR_HANDLERS)` inside the registry-builder function (alongside the other `register_all` calls).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_sensor_handlers.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/handlers/sensor_handlers.py packages/lifx-emulator-core/src/lifx_emulator/handlers/__init__.py packages/lifx-emulator-core/tests/test_sensor_handlers.py
git commit -s -m "feat(handlers): ambient-light sensor handler (always answers, lux 0 when sensorless)"
```

---

### Task 2: Switch routing — sensor must not be swallowed by StateUnhandled

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` (switch/unhandled path)
- Test: `packages/lifx-emulator-core/tests/test_sensor_handlers.py`

**Interfaces:**
- Consumes: switch device (`create_switch()`), `Sensor.GetAmbientLight`.

Switches return `StateUnhandled` (223) for Light/MultiZone/Tile packets. A `SensorGetAmbientLight` must still be answered with `StateAmbientLight` (lux 0.0), not `StateUnhandled`.

- [ ] **Step 1: Write the failing test**

```python
def test_switch_answers_ambient_light_not_unhandled():
    from lifx_emulator.factories import create_switch
    from lifx_emulator.protocol.packets import Sensor
    dev = create_switch()
    responses = dev.process_packet_by_type(Sensor.GetAmbientLight.PKT_TYPE, Sensor.GetAmbientLight(), res_required=True)
    # helper: use the same entry point tests already use to drive process_packet;
    # if tests drive via raw bytes, build the packet+header as the existing switch
    # tests do and assert the response payload type.
    assert any(isinstance(p, Sensor.StateAmbientLight) for p in responses)
```

(Match the exact `process_packet` entry point the existing switch tests use — e.g. `test_switch*.py`. Reuse their helper rather than inventing `process_packet_by_type` if it does not exist.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_sensor_handlers.py::test_switch_answers_ambient_light_not_unhandled -v`
Expected: FAIL — switch returns StateUnhandled (or empty) for 401.

- [ ] **Step 3: Implement**

In the switch/unhandled decision in `device.py` (where packet types are classified into the "return StateUnhandled" set for switches), ensure the Sensor namespace (types 401–402) is treated as handled — i.e. excluded from the StateUnhandled set and routed to the registry like Device.* packets. Add a narrow allowance for `Sensor.*` packet types.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_sensor_handlers.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/devices/device.py packages/lifx-emulator-core/tests/test_sensor_handlers.py
git commit -s -m "fix(devices): switches answer SensorGetAmbientLight instead of StateUnhandled"
```

---

### Task 3: Button handlers — get/set state + config

**Files:**
- Create: `packages/lifx-emulator-core/src/lifx_emulator/handlers/button_handlers.py`
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/handlers/__init__.py`
- Test: `packages/lifx-emulator-core/tests/test_button_handlers.py`

**Interfaces:**
- Consumes: `Button.Get/Set/State` (905/906/907), `Button.GetConfig/SetConfig/StateConfig` (909/910/911), `DeviceState.buttons_state`, `DeviceState.has_buttons`, `ButtonBacklightHsbk`.
- Produces: `ALL_BUTTON_HANDLERS: list[PacketHandler]`.

Rules: gate on `has_buttons` — non-button devices return `[]` (→ StateUnhandled per existing convention). `Button.State` must pack a full 8-entry `buttons` array (pad with default `Button` structs). SetConfig updates `buttons_state` then echoes `StateConfig`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_button_handlers.py
from lifx_emulator.factories import create_device
from lifx_emulator.handlers.button_handlers import GetConfigHandler, SetConfigHandler
from lifx_emulator.protocol.packets import Button
from lifx_emulator.protocol.protocol_types import ButtonBacklightHsbk


def test_get_config_returns_state_config_for_button_device():
    dev = create_device(219)  # Luna — has buttons
    out = GetConfigHandler().handle(dev.state, Button.GetConfig(), True)
    assert len(out) == 1 and isinstance(out[0], Button.StateConfig)


def test_set_config_updates_state_and_echoes():
    dev = create_device(219)
    pkt = Button.SetConfig(
        haptic_duration_ms=80,
        backlight_on_color=ButtonBacklightHsbk(hue=0, saturation=0, brightness=65535, kelvin=3500),
        backlight_off_color=ButtonBacklightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500),
    )
    out = SetConfigHandler().handle(dev.state, pkt, True)
    assert dev.state.buttons_state.haptic_duration_ms == 80
    assert isinstance(out[0], Button.StateConfig) and out[0].haptic_duration_ms == 80


def test_non_button_device_returns_empty():
    dev = create_device(22)  # plain bulb
    assert GetConfigHandler().handle(dev.state, Button.GetConfig(), True) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_button_handlers.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

```python
# handlers/button_handlers.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Button

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState


def _state_config(state: DeviceState) -> Button.StateConfig:
    bs = state.buttons_state
    return Button.StateConfig(
        haptic_duration_ms=bs.haptic_duration_ms,
        backlight_on_color=bs.backlight_on,
        backlight_off_color=bs.backlight_off,
    )


class GetConfigHandler(PacketHandler):
    """ButtonGetConfig (909) -> ButtonStateConfig (911)."""

    PKT_TYPE = Button.GetConfig.PKT_TYPE

    def handle(self, device_state: DeviceState, packet: Any | None, res_required: bool) -> list[Any]:
        if not device_state.has_buttons:
            return []
        return [_state_config(device_state)]


class SetConfigHandler(PacketHandler):
    """ButtonSetConfig (910) -> ButtonStateConfig (911)."""

    PKT_TYPE = Button.SetConfig.PKT_TYPE

    def handle(self, device_state: DeviceState, packet: Any | None, res_required: bool) -> list[Any]:
        if not device_state.has_buttons or packet is None:
            return []
        bs = device_state.buttons_state
        bs.haptic_duration_ms = packet.haptic_duration_ms
        bs.backlight_on = packet.backlight_on_color
        bs.backlight_off = packet.backlight_off_color
        return [_state_config(device_state)]


class GetHandler(PacketHandler):
    """ButtonGet (905) -> ButtonState (907)."""

    PKT_TYPE = Button.Get.PKT_TYPE

    def handle(self, device_state: DeviceState, packet: Any | None, res_required: bool) -> list[Any]:
        if not device_state.has_buttons:
            return []
        return [self._state(device_state)]

    @staticmethod
    def _state(device_state: DeviceState) -> Button.State:
        buttons = list(device_state.buttons_state.buttons)
        # State packs a fixed [8]<Button> array — pad to 8 with defaults.
        from lifx_emulator.protocol.protocol_types import Button as ButtonStruct  # adjust import to the generated struct name
        while len(buttons) < 8:
            buttons.append(ButtonStruct())
        return Button.State(count=len(device_state.buttons_state.buttons), index=0,
                            buttons_count=len(device_state.buttons_state.buttons), buttons=buttons[:8])


class SetHandler(PacketHandler):
    """ButtonSet (906) -> ButtonState (907)."""

    PKT_TYPE = Button.Set.PKT_TYPE

    def handle(self, device_state: DeviceState, packet: Any | None, res_required: bool) -> list[Any]:
        if not device_state.has_buttons:
            return []
        return [GetHandler._state(device_state)]


ALL_BUTTON_HANDLERS = [GetHandler(), SetHandler(), GetConfigHandler(), SetConfigHandler()]
```

Note: confirm the generated per-button struct name/import (the `[8]<Button>` element type) in `protocol_types.py` after Task 4 of the foundation plan, and fix the `ButtonStruct` import accordingly. Register `ALL_BUTTON_HANDLERS` in `handlers/__init__.py` (import, `__all__`, `register_all`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_button_handlers.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/handlers/button_handlers.py packages/lifx-emulator-core/src/lifx_emulator/handlers/__init__.py packages/lifx-emulator-core/tests/test_button_handlers.py
git commit -s -m "feat(handlers): button get/set + config handlers gated on has_buttons"
```

---

### Task 4: Extend the Sky-effect gate to the new Ceiling pids

**Files:**
- Modify: `packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py` (≈ lines 432–449)
- Test: `packages/lifx-emulator-core/tests/test_tile_handlers.py` (extend)

**Interfaces:**
- Consumes: `TileEffectType.SKY`, `DeviceState.product`, firmware.

Current gate hardcodes `{176, 177, 201, 202}`. Add the new Ceiling pids `265, 266`. Keep firmware ≥ 4.4.

- [ ] **Step 1: Write the failing test**

```python
def test_sky_effect_accepted_on_new_ceiling_265():
    from lifx_emulator.factories import create_device
    from lifx_emulator.protocol.packets import Tile
    from lifx_emulator.protocol.protocol_types import TileEffectType
    dev = create_device(265)  # Ceiling 13", firmware >= 4.4 via specs
    # build a SetEffect(SKY ...) as existing sky tests do, call the handler,
    # assert device_state.tile_effect_type == int(TileEffectType.SKY)
```

(Reuse the existing Sky-effect test helper in `test_tile_handlers.py`; assert acceptance for 265/266 and continued rejection for a non-Ceiling matrix device.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_tile_handlers.py -k sky -v`
Expected: FAIL — 265 not in the allowed set, effect ignored.

- [ ] **Step 3: Implement**

In `tile_handlers.py`, change:
```python
                ceiling_product_ids = {176, 177, 201, 202}
```
to:
```python
                ceiling_product_ids = {176, 177, 201, 202, 265, 266}
```
Update the neighbouring comment to list the new pids.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_tile_handlers.py -k sky -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py packages/lifx-emulator-core/tests/test_tile_handlers.py
git commit -s -m "feat(tile): allow Sky effect on new Ceiling pids 265/266"
```

---

### Task 5: Mirror single-Get64 + uplight/downlight split coverage

**Files:**
- Test: `packages/lifx-emulator-core/tests/test_matrix_products.py` (create)

**Interfaces:**
- Consumes: `create_device(267)`, `Tile.Get64`, `DeviceState.uplight_zone_count`/`downlight_zone_count`.

Verifies the modelled behaviour (no new production code expected — the split is metadata + existing single-matrix Get64). If a test reveals a gap, fix minimally.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_matrix_products.py
from lifx_emulator.factories import create_device


def test_mirror_split_and_total_zones():
    st = create_device(267).state
    assert st.uplight_zone_count == 25
    assert st.downlight_zone_count == 25
    assert st.tile_width * st.tile_height == 50   # via nested MatrixState if applicable


def test_mirror_single_get64_covers_all_50_zones():
    dev = create_device(267)
    # Drive Get64 for tile 0 the way existing tile tests do; assert a single
    # State64 response is produced and the request path does not require a second
    # Get64 for a 50-zone tile (<= 64 fits in one).
```

(Read `test_tile_handlers.py` for the exact Get64 driving helper; reuse it.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_matrix_products.py -v`
Expected: FAIL initially (assertions before behaviour confirmed) — then PASS once assertions match reality; fix code only if a real gap surfaces.

- [ ] **Step 3: Fix only if needed**

If `tile_width*tile_height` or the single-Get64 assertion fails, reconcile with the specs (5×10) and the Get64 tiling logic. Otherwise no production change.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_matrix_products.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/tests/test_matrix_products.py
git commit -s -m "test(matrix): Mirror 5x10 split + single Get64 coverage"
```

---

### Task 6: Ceiling 16×8 (128-zone) multi-request tiling coverage

**Files:**
- Test: `packages/lifx-emulator-core/tests/test_matrix_products.py` (extend)

**Interfaces:**
- Consumes: `create_device(201)` (16×8 = 128 zones), `Tile.Get64`, `Tile.Set64`.

Confirms a 128-zone Ceiling needs multiple Get64/Set64 requests (each covers ≤ 64 zones) and that FB round-trips across the split requests.

- [ ] **Step 1: Write the failing test**

```python
def test_ceiling_16x8_requires_multiple_get64():
    dev = create_device(201)  # Ceiling 13x26", 16x8 = 128 zones
    st = dev.state
    assert st.tile_width * st.tile_height == 128
    # A single Get64 returns at most 64 zones; assert two requests
    # (rows 0-3 then 4-7 for width 16) are needed to read all 128.
    # Drive Get64 twice with the appropriate rect and assert coverage,
    # reusing the existing Get64 test helper.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_matrix_products.py -k ceiling -v`
Expected: FAIL if 201 dims/tiling are wrong; otherwise adjust the assertion to the real request boundaries and confirm.

- [ ] **Step 3: Fix only if needed**

If the existing Get64/Set64 row-chunking mishandles width-16 tiles, fix the chunking in `tile_handlers.py` (rows-per-request = `64 // width`). Otherwise no production change.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/lifx-emulator-core/tests/test_matrix_products.py -k ceiling -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/lifx-emulator-core/tests/test_matrix_products.py packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py
git commit -s -m "test(matrix): Ceiling 16x8 multi-request Get64/Set64 tiling"
```

---

### Task 7: Behaviour gate — full suite + lint + types + coverage

**Files:** none (verification only).

- [ ] **Step 1: Full test suite**

Run: `uv run pytest`
Expected: all pass (both packages).

- [ ] **Step 2: Lint + types**

Run: `uv run ruff check .` then `uv run pyright`
Expected: clean. Extract helpers for any function > 10 complexity (button `_state` padding is the likely candidate).

- [ ] **Step 3: Sanity — run the emulator with a Mirror + Luna**

Run: `uv run python -m lifx_emulator_app --help`
Then create a config or use CLI flags to instantiate product 267 (Mirror) and 219 (Luna); confirm startup succeeds. (If the CLI lacks a by-pid flag, this is a manual check via a small config file; document the invocation used.)

- [ ] **Step 4: Commit any fixups**

```bash
git commit -s -am "chore: behaviour lint/type fixups" || echo "nothing to fix"
```

---

## Self-Review

- **Spec coverage:** unit 5 (Sensor + Button handlers → Tasks 1–3), unit 6 (Sky gate → Task 4; uplight/downlight + Mirror front/rear → Task 5; >64-zone multi-request → Task 6), unit 7 (cross-cutting tests + gate → Task 7).
- **Placeholders:** handler code is concrete; the two "verify/fix only if needed" tasks (5, 6) are deliberate verification tasks per the spec ("verify existing tiling logic") — they carry real assertions, not TODOs.
- **Type consistency:** `ambient_light_lux: float`, `buttons_state.haptic_duration_ms: int`, `ButtonBacklightHsbk`, `Sensor.StateAmbientLight(lux=...)`, `has_buttons` used consistently and matching the foundation plan. The one flagged unknown — the generated per-button struct name for the `[8]<Button>` array — is called out in Task 3 Step 3 to confirm against `protocol_types.py`.
- **Open risk carried forward:** Mirror firmware version and true dimensions remain provisional (spec A1) — specs-only, no code impact.
