# Phase 4: CLI and Configuration - Pattern Map

**Mapped:** 2026-09-24
**Files analyzed:** 13 (new/modified)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (`run()` thinned, new flags) | CLI entrypoint | request-response (startup) | itself (pre-refactor `run()`, `__main__.py:579-1146`) | exact — modify in place |
| `packages/lifx-emulator/src/lifx_emulator_app/startup/__init__.py` | barrel | n/a | `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py` | role-match (barrel-with-`__all__` convention) |
| `packages/lifx-emulator/src/lifx_emulator_app/startup/devices.py` (`build_device_list`) | service/utility | CRUD (device construction) | `__main__.py:892-952` device-creation loops (in-place logic to extract) | exact |
| `packages/lifx-emulator/src/lifx_emulator_app/startup/settings.py` (`RunSettings` dataclass) | model | transform (config → typed settings) | `config.py` `EmulatorConfig`/`DeviceDefinition` (Pydantic model style) + `devices/observers.py` `PacketEvent` (plain `@dataclass` style) | role-match |
| `packages/lifx-emulator/src/lifx_emulator_app/startup/preflight.py` (`_preflight`) | utility/validator | transform (pure validation) | `server.py::_has_thread_devices` (`server.py:919-923`) + `states.py::validate_mdns_address`/`coerce_connectivity` error-raising style | role-match |
| `packages/lifx-emulator/src/lifx_emulator_app/startup/scenarios.py` (moved `_apply_config_scenarios`) | utility | transform | itself (existing private helper in `__main__.py`, pure — safe to move) | exact |
| `packages/lifx-emulator/src/lifx_emulator_app/config.py` (`EmulatorConfig` + `DeviceDefinition` new fields, validators) | config/model | CRUD (validation) | itself — `HsbkConfig`/`DeviceDefinition`/`EmulatorConfig` existing `@field_validator` blocks (`config.py:20-231`) | exact |
| `packages/lifx-emulator-core/src/lifx_emulator/server.py` (`EmulatedLifxServer.__init__`, `mdns_ipv4_address`/`mdns_ipv6_address` props, event emission at `_start_mdns_locked`/`_stop_mdns_locked`/`_mdns_failed`) | service/core | event-driven | itself (`server.py:163-186`, `919-999`, `1019-1057`) | exact — modify in place |
| `packages/lifx-emulator-core/src/lifx_emulator/mdns.py` (`resolve_address` signature, `MdnsResponder.__init__`, `_reconcile` event emission) | service/core | event-driven | itself (`mdns.py:36-50`, `56-66`, `114-200`) | exact — modify in place |
| `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` (`PacketEvent.kind`, `ActivityLogger.on_mdns_event`, `NullObserver.on_mdns_event`) | model + service | event-driven | itself — `ActivityLogger.on_packet_received`/`on_packet_sent` (`observers.py:76-108`), `NullObserver.on_packet_received` (`observers.py:125-131`) | exact — modify in place |
| `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py` (barrel export `coerce_connectivity`, `validate_mdns_address`) | barrel | n/a | itself (`devices/__init__.py:1-61`) | exact — modify in place |
| `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` (`WebSocketActivityObserver.on_mdns_event`) | service | event-driven | itself — `WebSocketActivityObserver.on_packet_received`/`on_packet_sent` (`event_bridge.py:292-...`) | exact — modify in place |
| `packages/lifx-emulator/src/lifx_emulator_app/api/models.py` (`ActivityEvent.kind`) | model | request-response | itself — `ActivityEvent` (`api/models.py:119-128`) | exact — modify in place |
| `packages/lifx-emulator/tests/test_startup_*.py` (new) | test | CRUD/transform | `packages/lifx-emulator/tests/test_cli.py::TestRunCommand` (patch-target style) | role-match |

## Pattern Assignments

### `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (CLI entrypoint, thinned `run()`)

**Analog:** itself, current `run()` (lines 579-1146)

**Flag declaration pattern** (lines 613-649, tri-state precedent at 587-589):
```python
verbose: Annotated[
    bool | None, cyclopts.Parameter(negative="", group=server_group)
] = None,
```
For `--mdns`/`--no-mdns`, do **not** copy `negative=""` — research verified a bare `bool | None = None` parameter already yields both `--mdns` and `--no-mdns` with `None` unset (RESEARCH "cyclopts tri-state bool"). Model `--ipv6-bind`, `--mdns-ipv4-address`, `--mdns-ipv6-address` on the plain `str | None` pattern used by `bind`/`api_host` (line 586); model `--thread`/`--thread-product` on `color`/`color_temperature` (lines 645-648) and `products`/`product` (line 643).

**Device-creation loop pattern to mirror for `--thread`** (lines 892-952):
```python
for _ in range(f_color):
    devices.append(create_color_light(get_serial(), storage=storage))
```
`--thread N --thread-product PID` should call `create_device(pid, serial=get_serial(), connectivity="thread", storage=storage)` inside a loop appended **after** all existing count-flag kinds (D-13/P3: legacy serials must not shift), reusing the existing `try/except ValueError` + `logger.error(...); return` pattern already used for `f_products` (lines 897-906) — that pattern already names the product ID via the core's `ValueError` message (RESEARCH "Firmware/product gating").

**Error-path / non-zero-exit pattern** (existing, verified idiomatic — do not add `sys.exit`):
```python
logger.error("Failed to create device: %s", e)
return
```
Use identically for the D-12 preflight failure: `logger.error(...)`; `return False`.

**Mock-patch constraint (critical):** keep `EmulatedLifxServer(...)`, `DevicePersistenceAsyncFile()`, `_setup_logging()`, `resolve_config_path()`/`load_config()`, `logging.getLogger()`/`logging.basicConfig()`, `webbrowser.open()` calls physically defined/called inside `__main__.py` (see `packages/lifx-emulator/tests/test_cli.py:585-590` — `@patch("lifx_emulator_app.__main__.EmulatedLifxServer")` etc. resolve only against this module's namespace). Pure logic (`build_device_list`, `RunSettings` construction, `_preflight`, `_apply_config_scenarios`) is safe to move into `startup/`.

---

### `packages/lifx-emulator/src/lifx_emulator_app/startup/devices.py` (`build_device_list`)

**Analog:** `__main__.py:892-952` (in-place device-creation loops — extract as-is into a function, no behaviour change)

**Core pattern:** same `for _ in range(f_color): devices.append(create_color_light(get_serial(), storage=storage))` style, parameterised by a `RunSettings`-like input instead of loose locals. Function signature must stay ≤ 5 args (Ruff `max-args`) — pass the settings dataclass instead of one arg per count flag.

---

### `packages/lifx-emulator/src/lifx_emulator_app/startup/settings.py` (`RunSettings`)

**Analog:** `devices/observers.py` `PacketEvent` (plain frozen-ish `@dataclass`, lines 12-30) for the container shape; `config.py` `EmulatorConfig` (lines 172-224) for the field set to mirror (one field per resolved CLI/YAML key plus provenance for `mdns`).

**Core pattern** (from `PacketEvent`):
```python
@dataclass
class PacketEvent:
    timestamp: float
    direction: str
    ...
    device: str | None = None
```
Apply the same flat-dataclass-with-defaults shape to `RunSettings`, adding a provenance field such as `mdns_source: Literal["cli", "yaml", "unset"]` (D-11).

---

### `packages/lifx-emulator/src/lifx_emulator_app/startup/preflight.py` (`_preflight`)

**Analog:** `server.py::_has_thread_devices` (`server.py:919-923`) for the "scan devices, collect matches" shape; `states.py::validate_mdns_address`/`coerce_connectivity` (`states.py:70-103`) for the message style (`raise ValueError(f"...: {reason}")`, always naming the offending field/serial).

**Core pattern** (from RESEARCH's own illustrative example, consistent with codebase error-collection style elsewhere):
```python
def _preflight(settings: RunSettings, devices: list[EmulatedLifxDevice]) -> list[str]:
    problems: list[str] = []
    thread_serials = [
        d.state.serial for d in devices if d.state.connectivity == Connectivity.THREAD
    ]
    if settings.mdns_resolved is False and thread_serials:
        problems.append(
            f"--no-mdns / mdns: false with Thread device(s): {', '.join(thread_serials)}"
        )
    return problems
```
Caller in `__main__.py` does `logger.error("\n".join(problems)); return False` — matches the existing `logger.error(...); return` idiom (see `__main__.py:797-798`, `901-906`, `1022-1027`, `1037-1038`).

---

### `packages/lifx-emulator/src/lifx_emulator_app/config.py` (`EmulatorConfig`/`DeviceDefinition` new fields)

**Analog:** itself — existing validators on the same file

**Imports pattern** (lines 1-11, unchanged — add nothing new; reuse core's validators):
```python
from lifx_emulator.devices import coerce_connectivity, validate_mdns_address  # after barrel fix
```
(Barrel gap noted in RESEARCH — the barrel-export fix to `devices/__init__.py` must land first; otherwise import from `lifx_emulator.devices.states` directly as a fallback, documented as a convention deviation.)

**Validator style to copy** (`config.py:47-53`, `104-113`):
```python
@field_validator("kelvin")
@classmethod
def validate_kelvin(cls, v: int) -> int:
    if not 1500 <= v <= 9000:
        msg = "Kelvin must be between 1500 and 9000"
        raise ValueError(msg)
    return v
```
Apply this `msg = ...; raise ValueError(msg)` shape to `mdns_address`/`connectivity`/`mdns_ipv4_address`/`mdns_ipv6_address` validators, delegating the actual check to `coerce_connectivity`/`validate_mdns_address` per RESEARCH's "Don't Hand-Roll" table — do not reimplement address-family logic.

**Cross-field validator precedent (new — no exact prior in this file):** `HsbkConfig.accept_list_form` (`config.py:27-42`) is the only `@model_validator(mode="before")` example; for the new Thread+`mdns:false` refuse check on `DeviceDefinition`, use `@model_validator(mode="after")` (RESEARCH confirms no existing precedent — first usage in this file) with the same `msg = ...; raise ValueError(msg)` body style.

**`extra="forbid"` retained** (`config.py:224`):
```python
model_config = {"extra": "forbid"}
```
Do not remove; new fields are additive members of the same models.

---

### `packages/lifx-emulator-core/src/lifx_emulator/server.py` (`EmulatedLifxServer.__init__`, mDNS properties, event emission)

**Analog:** itself (constructor at `server.py:163-186`; `_start_mdns_locked`/`_stop_mdns_locked`/`_mdns_failed` at `server.py:919-999`, `1019-1057`)

**Constructor pattern** (lines 163-186) — add `mdns_ipv4_address: str | None = None, mdns_ipv6_address: str | None = None` as new keyword-only params after `mdns_enabled`, validated with `validate_mdns_address` against the matching family and stored as private attrs backing read-only properties (D-02), mirroring how `ipv6_bind_address` is already a plain constructor param stored directly (line 189, `self.ipv6_bind_address = ipv6_bind_address`) but exposed as read-only per D-02 (no existing read-only-property precedent in this class — first usage; use a plain `@property` returning the private attr).

**Failure funnel to reuse** (`server.py:925-939`, `944` per RESEARCH): `_mdns_failed()`/`_record_mdns_failure()` already dedupe repeated failures via `self._mdns_status != MdnsStatus.FAILED`; emit the single "failed" `on_mdns_event` from inside this existing funnel, not a new one.

---

### `packages/lifx-emulator-core/src/lifx_emulator/mdns.py` (`resolve_address`, `MdnsResponder`, `_reconcile`)

**Analog:** itself (`mdns.py:36-50` `resolve_address`; `56-66` `MdnsResponder.__init__`; `114-200` `_operation`/`_reconcile`)

**Current fallback pattern to extend** (lines 36-50):
```python
def resolve_address(device: EmulatedLifxDevice, ipv4: str, ipv6: str) -> str | None:
    state = device.state
    if not state.mdns_enabled:
        return None
    fallback = ipv6 if state.connectivity == Connectivity.THREAD else ipv4
    try:
        return validate_mdns_address(
            state.mdns_address if state.mdns_address is not None else fallback,
            state.connectivity,
        )
    except ValueError as error:
        raise ValueError(f"Device {state.serial} ({state.connectivity}): {error}") from error
```
D-01 needs a third precedence tier (server-level default before bind fallback) — extend the `fallback` computation to prefer a new server-default param over `ipv4`/`ipv6`, keeping the same `try/except ValueError` wrapping style that names the device serial.

**Error-wrapping pattern to copy:** every `ValueError` re-raised here is prefixed with `f"Device {state.serial} (...)"` — apply the identical prefix style to any new validation errors for server-level addresses (R6 acceptance: "fails startup with an error naming the device").

**Event emission point:** `_reconcile()` (lines 177-200, per RESEARCH) already distinguishes register/update/unregister — emit `on_mdns_event` calls from inside/adjacent to that branching rather than re-deriving the distinction elsewhere (RESEARCH "Don't Hand-Roll").

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` (`PacketEvent.kind`, `on_mdns_event`)

**Analog:** itself — `ActivityLogger.on_packet_received`/`on_packet_sent` (lines 76-108), `NullObserver.on_packet_received`/`on_packet_sent` (lines 125-139)

**Dataclass extension pattern** (lines 12-30):
```python
@dataclass
class PacketEvent:
    timestamp: float
    direction: str  # 'rx' or 'tx'
    packet_type: int
    packet_name: str
    addr: str
    device: str | None = None
    target: str | None = None
```
Add `kind: str = "lifx"` as a new trailing defaulted field (D-08) — backwards compatible with every existing positional/keyword construction site.

**Observer method pattern to copy exactly** (lines 76-91, `ActivityLogger.on_packet_received`):
```python
def on_packet_received(self, event: PacketEvent) -> None:
    self.recent_activity.append(
        {
            "timestamp": event.timestamp,
            "direction": "rx",
            "packet_type": event.packet_type,
            "packet_name": event.packet_name,
            "target": event.target,
            "addr": event.addr,
        }
    )
```
`on_mdns_event(self, event: PacketEvent) -> None` should append the same dict shape (now including `"kind": event.kind`) to `self.recent_activity`, reusing the same deque — no new storage.

**`NullObserver` no-op pattern to copy exactly** (lines 125-131):
```python
def on_packet_received(self, event: PacketEvent) -> None:
    """No-op packet received handler."""
    pass
```
`on_mdns_event` on `NullObserver` is the same one-line `pass` body.

**Optional-hook call-site pattern (server-side):** per D-07, the server calls this via `getattr(observer, "on_mdns_event", None)` — no exact prior instance of this `getattr`-optional-hook pattern exists in `server.py` today (new pattern, first usage in this codebase per D-07's own text); wrap every call in `try/except Exception: logger.exception(...)` matching the existing lifecycle/state-change callback wrapping style (`manager.py:164-168`, `device.py:441-448`).

---

### `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py` (barrel export)

**Analog:** itself (lines 1-61)

**Pattern to copy exactly** (lines 11-33, 39-61):
```python
from lifx_emulator.devices.states import Connectivity, DeviceState
...
__all__ = [
    ...
    "Connectivity",
    "DeviceState",
    ...
]
```
Change to `from lifx_emulator.devices.states import Connectivity, DeviceState, coerce_connectivity, validate_mdns_address` and add both new names to `__all__`, closing the reuse gap RESEARCH identified.

---

### `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` (`WebSocketActivityObserver.on_mdns_event`)

**Analog:** itself — `on_packet_received`/`on_packet_sent` on the same class (constructor at lines 266-290; methods follow at line 292 onward)

**Delegation pattern to copy:** the existing `on_packet_received`/`on_packet_sent` methods forward to `self._inner.on_packet_received(event)` (if present) and then schedule a WebSocket broadcast via `self._task_tracker`. `on_mdns_event` should do the identical two-step: `getattr(self._inner, "on_mdns_event", None)` call (inner may be a plain `ActivityLogger` after D-07, or a third-party observer without the hook) wrapped in `try/except`, then schedule the broadcast through the same `_task_tracker`/`WebSocketEventQueue` machinery already used for packet events — no new broadcast path.

---

### `packages/lifx-emulator/src/lifx_emulator_app/api/models.py` (`ActivityEvent.kind`)

**Analog:** itself (lines 119-128)

**Pattern to copy exactly:**
```python
class ActivityEvent(BaseModel):
    """Recent activity event."""

    timestamp: float
    direction: str
    packet_type: int
    packet_name: str
    device: str | None = None
    target: str | None = None
    addr: str
```
Add `kind: str = "lifx"` as a new trailing defaulted field — additive, matches D-04's "existing fields keep their name and type" requirement.

---

### `packages/lifx-emulator/tests/test_startup_*.py` (new)

**Analog:** `packages/lifx-emulator/tests/test_cli.py::TestRunCommand` (patch-target and fixture style, lines 583-600)

**Pattern to copy:**
```python
@pytest.mark.asyncio
@patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
@patch("lifx_emulator_app.__main__.EmulatedLifxServer")
@patch("lifx_emulator_app.__main__._setup_logging")
async def test_run_default_no_devices(self, mock_setup_logging, mock_server_class, mock_resolve):
    await run()
    mock_server_class.assert_not_called()
```
Pure `startup/` helpers (`build_device_list`, `_preflight`, `RunSettings` construction) should get their own unpatched unit tests calling the functions directly (no `@patch` needed, since RESEARCH confirms `create_color_light`/`create_device`/etc. are never mocked in the existing suite); `run()`-level integration/equivalence and shutdown-order tests must keep using the `@patch("lifx_emulator_app.__main__.X", ...)` targets listed in RESEARCH verbatim (`EmulatedLifxServer`, `DevicePersistenceAsyncFile`, `_load_merged_config`, `_setup_logging`, `resolve_config_path`, `load_config`, `logging.basicConfig`, `logging.getLogger`, `webbrowser.open`).

---

## Shared Patterns

### Pydantic validator error style
**Source:** `packages/lifx-emulator/src/lifx_emulator_app/config.py:47-53` (`validate_kelvin`)
**Apply to:** every new `EmulatorConfig`/`DeviceDefinition` field validator (`ipv6_bind`, `mdns`, `mdns_ipv4_address`, `mdns_ipv6_address`, `thread`, `thread_product`, `connectivity`, `mdns_address`)
```python
@field_validator("<field>")
@classmethod
def validate_<field>(cls, v):
    if <invalid>:
        msg = "<field> ..."
        raise ValueError(msg)
    return v
```

### Optional-observer / `getattr` hook pattern
**Source:** D-07's design, no exact prior instance in `server.py`; nearest precedent is the existing `try/except Exception: logger.exception(...)` wrapping on `manager.py:164-168` and `device.py:441-448`
**Apply to:** `server.py` call sites that emit `on_mdns_event`, and `WebSocketActivityObserver.on_mdns_event`'s own delegation to `self._inner`
```python
hook = getattr(observer, "on_mdns_event", None)
if hook is not None:
    try:
        hook(event)
    except Exception:
        logger.exception("mDNS observer failed to handle event")
```

### `logger.error(...); return False` non-zero-exit idiom
**Source:** `packages/lifx-emulator/src/lifx_emulator_app/__main__.py:797-798, 901-906, 1022-1027, 1037-1038`
**Apply to:** the new D-12 preflight failure path — no `sys.exit()` needed (verified against installed cyclopts 4.10.1 in RESEARCH).

### mock-patch-target preservation
**Source:** `packages/lifx-emulator/tests/test_cli.py:585-590` and the full patch-target enumeration in `04-RESEARCH.md` ("The dominant constraint" section)
**Apply to:** every `run()` decomposition change — keep `EmulatedLifxServer`, `DevicePersistenceAsyncFile`, `_setup_logging`, `resolve_config_path`, `load_config`, `logging.getLogger`/`logging.basicConfig`, `webbrowser.open` calls physically inside `__main__.py`.

## No Analog Found

None — every file in scope has an exact or role-matched analog, mostly itself (in-place modification of existing modules) per the phase's decompose-and-extend nature.

## Metadata

**Analog search scope:** `packages/lifx-emulator/src/lifx_emulator_app/`, `packages/lifx-emulator-core/src/lifx_emulator/`, `packages/lifx-emulator/tests/`
**Files scanned:** `__main__.py`, `config.py`, `server.py`, `mdns.py`, `devices/observers.py`, `devices/states.py`, `devices/__init__.py`, `api/models.py`, `api/services/event_bridge.py`, `factories/factory.py`, `factories/firmware_config.py`, `tests/test_cli.py`
**Pattern extraction date:** 2026-09-24
