# Phase 4: CLI and Configuration - Research

**Researched:** 2026-09-24
**Domain:** cyclopts CLI/YAML configuration surface over an existing asyncio core (Python 3.10-3.14)
**Confidence:** HIGH

## Summary

This phase has almost no external-library risk: every dependency it touches (`cyclopts` 4.10.1, `pydantic` 2.x, `pyyaml`, `zeroconf` via the core's `mdns.py`) is already installed and already used for the exact same purpose elsewhere in the codebase. The real risk is entirely structural: `run()` is a 567-line `@app.default` coroutine in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (lines 580-1149 including its docstring and body) that the existing test suite drives almost entirely through `unittest.mock.patch("lifx_emulator_app.__main__.<name>", ...)`. Every one of those patch targets resolves the name in `lifx_emulator_app.__main__`'s own module namespace at call time; a helper that is *moved* into a new `startup/` module and does its own `from lifx_emulator.server import EmulatedLifxServer` import will not be intercepted by `@patch("lifx_emulator_app.__main__.EmulatedLifxServer")`, and the real class will run in a test that expects a mock — this is the single biggest risk to R1's "existing app test suite passes unchanged" acceptance criterion and must shape how the planner splits `run()`.

Two implementation questions the discussion left open are now resolved by direct execution against the installed `cyclopts==4.10.1`: (1) an async `@app.default` command that returns `False` already produces process exit code `1` today, and returning `None` (the implicit no-`return` path) already produces exit code `0` — no `sys.exit()` call is needed anywhere in `run()`, the existing `print(...); return False` idiom already satisfies R5's "exits non-zero" requirement; (2) a plain `bool | None = None` parameter (no `negative=""`) already produces both `--mdns` and `--no-mdns` on the CLI with `None` as the unset state, exactly the tri-state R2 needs, with zero extra `cyclopts.Parameter` configuration.

The core-library surface this phase must extend (`mdns.resolve_address()`, `MdnsResponder.__init__`/`service_info()`, `EmulatedLifxServer.__init__`, `devices/observers.py`) is fully read and cited below with line numbers. Two gaps stand out: `coerce_connectivity` and `validate_mdns_address` (`devices/states.py:70-103`) are not re-exported through the `lifx_emulator.devices` barrel (`devices/__init__.py`'s `__all__` omits both), so the app currently has no barrel-conformant way to reuse them as CONTEXT's "Reusable Assets" instructs; and the CLI's actual shutdown order today is `storage.shutdown()` -> `server.stop()` -> `api_task.cancel()` (`__main__.py:1135-1144`), which is the reverse of the "(API task, server/mDNS, storage flush)" order named in `04-CONTEXT.md`'s R1 acceptance-criteria paraphrase — the planner's shutdown-order test must assert the code's actual current sequence, not the CONTEXT prose, or it will fail against unchanged behaviour on day one.

**Primary recommendation:** Do the `run()` split by extracting *pure, non-patched* logic (device-list construction from counts/products/config, scenario-manager assembly, preflight validation) into a new `lifx_emulator_app/startup/` package, while leaving every currently-mocked side-effecting call (`EmulatedLifxServer(...)`, `DevicePersistenceAsyncFile()`, `_setup_logging()`, `resolve_config_path()`/`load_config()`, `logging.getLogger()`, `logging.basicConfig()`, `webbrowser.open()`, `get_registry()`) invoked from inside `__main__.py` itself — either directly in the thinned `run()`, or through helpers that receive the already-imported class/callable as a parameter so the *lookup* still happens in `__main__`'s namespace.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `run()` decomposition (R1) | App / CLI (`lifx_emulator_app.__main__`, new `startup/` package) | — | Pure control-flow refactor; no core change |
| CLI flags + tri-state parsing (R2, R3) | App / CLI | — | cyclopts `@app.default` signature in `__main__.py` |
| YAML schema (R4) | App / Config | Core (validation reuse) | `EmulatorConfig`/`DeviceDefinition` in `config.py`; validators call core's `coerce_connectivity`/`validate_mdns_address` |
| mDNS auto-enable / refuse-to-start rule (R5) | App / Startup preflight | Core (`EmulatedLifxServer(mdns_enabled=...)`) | App computes the boolean from Thread-presence + CLI/YAML tri-state; core just receives the final flag (CFG-06: core defaults unchanged) |
| Server-level advertised-address defaults (R6) | Core (`EmulatedLifxServer.__init__`, `mdns.resolve_address()`, `MdnsResponder`) | App (passes flags through) | D-01: core owns the fallback chain so Phase 5 API-created devices inherit it for free |
| mDNS lifecycle activity events (R7) | Core (`devices/observers.py`, `mdns.py`, `server.py` emit) | App (`WebSocketActivityObserver`, `api/models.py`) | D-07/D-08: new optional `on_mdns_event` observer hook, core-owned; app only forwards |
| Library-default invariance (R8) | Core | — | `EmulatedLifxServer(devices, manager)` with no new kwargs must be behaviourally identical |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Server-level advertised address (R6)**
- **D-01:** Server-level advertised addresses are a **core** feature: `EmulatedLifxServer` gains optional `mdns_ipv4_address: str | None = None` and `mdns_ipv6_address: str | None = None`. `mdns.resolve_address()` uses the matching-family server default when a device has no `mdns_address`, and falls back to the concrete bind address only when that default is also `None`. A device's own `mdns_address` always wins. With both defaults `None` the core behaves exactly as today (R8). The app passes `--mdns-ipv4-address` / `--mdns-ipv6-address` (and YAML equivalents) straight through; it does **not** write them into each device's `mdns_address`. This keeps the distinction between an explicit device address and an inherited one, and Phase 5 API-created devices inherit the default with no extra work. — **Reversibility:** costly — the constructor parameters and properties become published `lifx-emulator-core` API.
- **D-02:** The server-level addresses are validated in `EmulatedLifxServer.__init__` with the core's `validate_mdns_address` against the matching family, fixed for the server's lifetime, and exposed as read-only `mdns_ipv4_address` / `mdns_ipv6_address` properties. There is no setter or runtime re-advertisement (consistent with Phase 3 D-04). — **Reversibility:** costly — public read-only property names.
- **D-03:** If any advertised-address option (server-level or per-device `mdns_address`) is set but mDNS resolves to off (e.g. a WiFi-only fleet with no `--mdns`), the app logs one `WARNING` saying the address is ignored because mDNS is disabled, and starts normally. Setting an address never turns mDNS on; R5 remains the only enablement rule.

**mDNS activity event shape (R7)**
- **D-04:** mDNS lifecycle events reuse the existing activity schema. Every current `ActivityEvent` field keeps its name and type. mDNS events set `direction: "mdns"`, `packet_type: 0`, a human-readable `packet_name` (e.g. `"mDNS registered"`, `"mDNS updated"`, `"mDNS withdrawn"`, `"mDNS started"`, `"mDNS stopped"`), `device` set to the serial for per-device events, and `addr` set to the advertised address. An additive optional `kind` field (`"lifx"` default, `"mdns"` for these events) goes on the API `ActivityEvent` model and the WebSocket payload so consumers can filter without relying on the sentinel. The dashboard renders them through the existing activity rendering (no Svelte change beyond what the existing types need). — **Reversibility:** costly — `kind` and the `direction: "mdns"` value become part of the `/api/activity` and WebSocket contract.
- **D-05:** Responder-level events (started, stopped, failed) have `device` and `target` set to `None` and `addr` set to the IPv4/IPv6 bind addresses. A failure event carries a short reason in `packet_name` as `"mDNS failed: <error summary>"`. The full error stays in the log and in `server.mdns_error`. No new `detail` field.
- **D-06:** After a successful `retry_mdns()` recovery, the events match a fresh start: one "started" event, then one "registered" event per advertised device. "updated" is reserved for a reconcile that changes the data of an existing record.

**Core observer hook (R7, R8)**
- **D-07:** The core emits mDNS events through a new optional observer method `on_mdns_event(event)`, implemented on `ActivityLogger`, `NullObserver` and the app's `WebSocketActivityObserver`. The server calls it via `getattr(observer, "on_mdns_event", None)`, so third-party `ActivityObserver` implementations that define only the two packet methods keep working unchanged. The events go into the same `ActivityLogger` deque that `/api/activity` reads, and the WebSocket decorator forwards them on the activity topic. Library users with the default `ActivityLogger` see mDNS events once they enable mDNS; with mDNS off (the default) no events are produced. — **Reversibility:** costly — a new optional method on a published observer protocol.
- **D-08:** The event type is the existing `PacketEvent` dataclass with a new field `kind: str = "lifx"`. mDNS events are constructed with `kind="mdns"`, `direction="mdns"` and `packet_type=0`. The addition is backwards compatible for existing constructors and keeps one type in the logger deque and a one-to-one mapping to the API `ActivityEvent`.
- **D-09:** Settled defaults: every `on_mdns_event` call is wrapped so an observer exception is logged and never stops mDNS or LIFX serving (the SPEC's failing-WebSocket-consumer backstop). mDNS events do not increment the LIFX packet statistics (`packets_received_by_type`, `packets_sent_by_type`).

**`run()` decomposition and startup flow (R1, R5, R6)**
- **D-10:** The helpers extracted from `run()` move into new focused app modules beside `config.py`, for example a `lifx_emulator_app/startup/` package with modules for device construction, storage setup, and server start/shutdown (exact names at planner discretion). `__main__.py` keeps the cyclopts command definitions and a thin `run()` that delegates. HYG-03 is still the first plan and adds no new flags.
- **D-11:** `_load_merged_config()` (or its replacement) returns a typed frozen settings object (e.g. a `RunSettings` dataclass) instead of the current `dict`. It carries the resolved values plus provenance for the options where it matters, in particular whether `mdns` came from a CLI flag, from YAML or from neither (the R5 tri-state). Helpers take this object, which lets Pyright check every key and lets errors name the CLI flag (`--ipv6-bind`) or the YAML key (`ipv6_bind`) according to where the value came from.
- **D-12:** All pre-bind checks run in one preflight step after the devices are constructed and before any socket, storage or API task is opened. The preflight covers the R5 refuse-to-start check (explicit `--no-mdns` / `mdns: false` with Thread devices), the R6 wildcard-bind check (a wildcard bind with no server-level address for an advertised device's family) and the D-03 warning. It collects every problem, i.e. all Thread serials and every device lacking an address, into one error message, then exits non-zero. Field-local problems that YAML alone decides (unknown key, Thread `mdns: false` on a device, wrong-family `mdns_address`, unknown `connectivity`) still fail in the Pydantic models, per R4.
- **D-13:** R1 equivalence is proven with a golden snapshot committed **before** `run()` is touched (same approach as Phase 1 D-11/D-12). The snapshot records (serial, product, firmware, connectivity, order) for a matrix of legacy flag and YAML combinations as inline test constants, and the refactored code must reproduce them exactly. `--thread` devices take serials after all existing count-flag kinds, so legacy serials never shift (P3).

### Claude's Discretion
- Whether the responder or the server raises each mDNS lifecycle event, provided the counts in R7 and D-06 hold.
- Exact module and helper names under the new app startup package, and the name and fields of the settings dataclass.
- Exact `packet_name` wording for each lifecycle action, and how `addr` formats multiple bind addresses for responder-level events.
- Whether `--thread-product` checks up front that the product is Thread-capable, or relies on the core's existing firmware ceiling and factory errors, provided the error names the product ID (R3).
- How to make the preflight failure exit non-zero. Research must verify whether cyclopts turns `run()` returning `False` into a non-zero exit code; the current error paths `print(...)` and `return False`. **Resolved below: yes, already non-zero — see "cyclopts exit-code behaviour".**

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within the phase scope. (API reporting of the server-level advertised addresses via the D-02 properties is Phase 5 work that already exists on the roadmap.)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HYG-03 | Decompose `run()` into device-construction/storage/server-start/shutdown helpers, unchanged behaviour, first plan | Exact line-range map of current `run()` below; mock-patch-preservation constraint identified as the dominant design pressure; shutdown-order discrepancy flagged with evidence |
| CFG-01 | CLI flags for IPv6 bind, mDNS on/off, advertised addresses, Thread count/product | Tri-state bool pattern verified empirically against installed cyclopts 4.10.1; existing `product`/`color` etc. flag patterns in `__main__.py:622-648` to mirror for `--thread`/`--thread-product` |
| CFG-02 | YAML schema on `EmulatorConfig`/`DeviceDefinition`, `extra="forbid"` retained | `config.py:104-231` read in full; validator style (`msg = ...; raise ValueError(msg)`) and `model_validator(mode="before")` precedent identified; cross-field Thread+`mdns:false` check needs a new `model_validator(mode="after")` (no existing precedent in this file) |
| CFG-04 | Thread-triggered mDNS auto-enable + refuse-to-start rule | `EmulatedLifxServer._has_thread_devices()` (`server.py:919-923`) is the exact core primitive the app-side preflight should mirror; `NetworkState.__post_init__` (`states.py:132-138`) already refuses to construct a Thread device with `mdns_enabled=False` at the *device* level, which is a distinct, earlier-firing guard from the app's fleet-level refuse-to-start check |
| CFG-05 (narrowed) | mDNS lifecycle events in activity log + WS topic | Full `devices/observers.py` read; exact emission points identified in `mdns.py` (`_operation`, `_reconcile`) and `server.py` (`_start_mdns_locked`, `_stop_mdns_locked`, `_mdns_failed`) |
| CFG-06 (narrowed) | Library `EmulatedLifxServer` defaults unchanged unless new kwargs passed | `EmulatedLifxServer.__init__` signature quoted in full (`server.py:163-179`); default `mdns_enabled=False`, no `mdns_ipv4_address`/`mdns_ipv6_address` params today confirms D-01/D-02 are additive |

## Standard Stack

No new external packages are introduced by this phase. Everything needed is already a resolved dependency:

### Core (already in use, confirmed via installed venv)
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cyclopts` | 4.10.1 `[VERIFIED: local venv — uv run python -c "import cyclopts; print(cyclopts.__version__)"]` | CLI parsing, `@app.default` | Already the project's CLI framework; `pyproject.toml` pins `>=4.2.0` |
| `pydantic` | 2.x (project-pinned `>=2.0.0`) | `EmulatorConfig`/`DeviceDefinition` validation | Already the project's only validation layer |
| `pyyaml` | project-pinned `>=6.0.3` | Config file parsing (`yaml.safe_load`) | Already used in `config.py:269` |
| `zeroconf` (via core `mdns.py`) | `>=0.151.3` (Phase 3 decision, `.planning/STATE.md:35`) | mDNS responder | Already the Phase 3 core dependency; this phase only wires the app to it, no new usage pattern |

No `npm view` / `pip index versions` check is needed: no new package is being added to either `pyproject.toml`.

## Package Legitimacy Audit

Not applicable — this phase adds zero new third-party packages to either package's `pyproject.toml`. All libraries used are pre-existing, already-audited project dependencies (see Standard Stack above).

## Architecture Patterns

### `run()` current structure — exact line map

Read in full from `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (source is 1150 lines total):

| Stage | Lines | What happens |
|---|---|---|
| Signature / cyclopts params | 579-649 | `@app.default async def run(*, config=None, bind=None, ... serial_start=None) -> bool \| None:` |
| Docstring | 650-726 | Help text only |
| Config load & merge | 727-757 | `cfg = _load_merged_config(config_flag=config, bind=bind, ...)`; `if cfg is None: return False` |
| Extract merged values | 759-786 | `f_bind`, `f_port`, ... `config_devices`, `config_scenarios` pulled from the `cfg` dict |
| Logging setup | 788-793 | `logger = _setup_logging(f_verbose)`; logs config path if used |
| `--persistent-scenarios` requires `--persistent` | 795-798 | `if f_persistent_scenarios and not f_persistent: logger.error(...); return False` |
| Deprecation warnings | 800-824 | `warnings.warn(...)` + `logger.warning(...)` for `--persistent`/`--persistent-scenarios` |
| Storage init | 826-829 | `storage = DevicePersistenceAsyncFile() if f_persistent else None` |
| Device list & serial setup | 831-849 | `devices = []`; `explicit_serials` from `config_devices`; `get_serial()` closure |
| Restore-from-storage branch | 851-890 | Only when `f_persistent and storage`; restores or logs "empty storage" |
| New-device creation (skipped if restoring) | 892-1027 | `f_products` loop, then `f_color`/`f_color_temperature`/`f_infrared`/`f_hev`/`f_multizone`/`f_tile`/`f_switch` loops (908-951), then `config_devices` loop building per-device state (953-1027) |
| No-devices check | 1029-1038 | Warn+continue if `f_persistent`, else `logger.error(...); return` |
| Port assignment | 1040-1042 | `for device in devices: device.state.port = f_port` |
| Device info logging | 1044-1051 | |
| DeviceManager construction | 1053-1055 | `device_repository = DeviceRepository(); device_manager = DeviceManager(device_repository)` |
| Scenario manager setup | 1057-1067 | Persistent-scenario load, or `_apply_config_scenarios(config_scenarios, logger)` |
| Server construction + start | 1069-1081 | `server = EmulatedLifxServer(devices, device_manager, f_bind, f_port, track_activity=..., storage=..., scenario_manager=..., persist_scenarios=..., scenario_storage=...)`; `await server.start()` |
| API task start | 1083-1095 | `asyncio.create_task(run_api_server(server, f_api_host, f_api_port))`; optional `webbrowser.open(...)` |
| Signal handlers | 1097-1110 | SIGTERM/SIGINT/SIGBREAK -> `shutdown_event.set()` |
| Run banner + wait | 1112-1131 | Logs, then `await shutdown_event.wait()` |
| **Shutdown (`finally`)** | 1132-1144 | See below — order matters |

**Shutdown order — verbatim, exact code:**
```
1132	    finally:
1133	        logger.info("Shutting down server...")
1134	
1135	        if storage:
1136	            await storage.shutdown()
1137	
1138	        await server.stop()
1139	        if api_task:
1140	            api_task.cancel()
1141	            try:
1142	                await api_task
1143	            except asyncio.CancelledError:
1144	                pass
```
`[VERIFIED: packages/lifx-emulator/src/lifx_emulator_app/__main__.py:1132-1144]`

**Discrepancy for the planner to resolve during planning, not silently pick a side on:** `04-CONTEXT.md`'s R1 acceptance criterion says *"Shutdown order (API task, server/mDNS, storage flush) is unchanged, asserted by a test"* — that parenthetical lists API task first. The code above shows the actual current order is **storage flush, then `server.stop()` (which internally calls `_stop_mdns_locked()` — confirmed at `server.py:1219`, so "server/mDNS" is one step), then API task cancellation** — the reverse of the CONTEXT list. Since R1 requires *unchanged* behaviour and the acceptance criterion says the order must be "unchanged", the new shutdown-order test must assert the code's actual current sequence (storage -> server/mDNS -> API task), not the CONTEXT prose order. Flag this explicitly to the user/planner rather than silently reordering shutdown to match the CONTEXT text, which would violate "unchanged behaviour."

### The dominant constraint: `unittest.mock.patch("lifx_emulator_app.__main__.X", ...)` targets

`grep -oE '@patch\("lifx_emulator_app\.__main__\.[A-Za-z_.]+"' packages/lifx-emulator/tests/test_cli.py` (only file with any `@patch` on this module; `test_cli_validation.py` and `test_config.py` have zero `@patch` calls — they use subprocess/pure-function testing instead) `[VERIFIED: ran locally]` returns exactly these targets, all resolved against `lifx_emulator_app.__main__`'s own namespace:

```
lifx_emulator_app.__main__.DevicePersistenceAsyncFile
lifx_emulator_app.__main__.EmulatedLifxServer
lifx_emulator_app.__main__._load_merged_config
lifx_emulator_app.__main__._setup_logging
lifx_emulator_app.__main__.get_registry
lifx_emulator_app.__main__.load_config
lifx_emulator_app.__main__.logging.basicConfig
lifx_emulator_app.__main__.logging.getLogger
lifx_emulator_app.__main__.resolve_config_path
lifx_emulator_app.__main__.webbrowser.open
```

Representative examples, quoted verbatim, showing exactly how load-bearing this is:
```
586	    @patch("lifx_emulator_app.__main__.resolve_config_path", return_value=None)
587	    @patch("lifx_emulator_app.__main__.EmulatedLifxServer")
588	    @patch("lifx_emulator_app.__main__._setup_logging")
...
712	        # Verify server was created with correct bind and port
713	        call_args = mock_server_class.call_args[0]
714	        assert call_args[2] == "192.168.1.100"
715	        assert call_args[3] == 12345
```
`[VERIFIED: packages/lifx-emulator/tests/test_cli.py:586-588,712-715]`

Python resolves `EmulatedLifxServer` (or `DevicePersistenceAsyncFile`, `_setup_logging`, etc.) as a **global name lookup in the module where the calling code is textually defined**, at call time. `unittest.mock.patch` only rebinds the name in the target module's `__dict__`. This means:

- If a helper function that constructs `EmulatedLifxServer(...)` is *moved* into `lifx_emulator_app/startup/server_start.py` and that module does its own `from lifx_emulator.server import EmulatedLifxServer`, then `@patch("lifx_emulator_app.__main__.EmulatedLifxServer")` **will not intercept it** — the test will construct and (attempt to) start a *real* `EmulatedLifxServer`, which is not what `test_run_with_color` et al. expect (they assert on `mock_server_class.call_args`, `mock_server.start.assert_called_once()`, etc., and never `await` a real `asyncio.create_task` cleanup for a real bound socket).
- The same applies to `DevicePersistenceAsyncFile`, `_setup_logging`, `resolve_config_path`/`load_config` (both called from inside `_load_merged_config`, which itself must stay defined in `__main__.py` — or be re-exported there — for the `resolve_config_path`/`load_config` patches to keep working), `logging.getLogger`/`logging.basicConfig` (called from `_setup_logging`, same constraint), and `webbrowser.open` (called from inside `run()`'s API-task branch).
- `get_registry` is patched only in `TestListProducts` tests (`list_products`, not `run()`), so it constrains `list_products()` specifically, not the R1 decomposition — but the same name-resolution rule applies if `list_products` internals ever move.

**Actionable guidance for the planner:** Extraction is safe (does not need patch-target changes) for *pure* logic with no patched external call inside it — e.g. a `build_device_list(f_products, f_color, ..., config_devices, get_serial) -> list[EmulatedLifxDevice]` helper is safe because `create_color_light`/`create_device`/etc. are never mocked in these tests (the tests rely on real device construction and only assert on the resulting list). Extraction is **unsafe** (breaks tests silently, or worse, opens real sockets in CI) for `EmulatedLifxServer(...)` construction, `DevicePersistenceAsyncFile()` construction, `_setup_logging()`, `resolve_config_path()`/`load_config()`, `logging.getLogger()`/`logging.basicConfig()`, and `webbrowser.open()` **unless** the extracted helper receives the class/callable as an injected parameter from `run()` (so the name lookup that matters — `EmulatedLifxServer` inside `run()`'s own frame — still happens in `__main__.py`), or the helper stays a private function physically defined inside `__main__.py` (which is still the `lifx_emulator_app.__main__` module for patch purposes, regardless of D-10's "new focused app modules" framing — a function can be *called from* a `startup/` module's orchestrator while still being *defined in* `__main__.py`, if that split is chosen).

### cyclopts exit-code behaviour — verified against installed 4.10.1

Ran directly against the project's own `.venv` (cyclopts 4.10.1, matching `uv.lock:239-252`):

```python
import cyclopts
app = cyclopts.App()

@app.default
async def run() -> bool | None:
    return False

if __name__ == "__main__":
    app()
```
`$ uv run python test.py; echo $?` -> **`1`**. The same file with `return None` (or no `return`) -> **`0`**. `[VERIFIED: local execution against .venv/lib/python3.11/site-packages/cyclopts 4.10.1]`

Root cause in the library itself: `App.__call__` (`cyclopts/core.py:1888-1890`) calls `self._handle_result_action(result)` with no explicit `result_action`, and `_handle_result_action`'s `fallback` parameter defaults to `"print_non_int_sys_exit"` (`cyclopts/core.py:2597`). `handle_result_action` for that action (`cyclopts/_result_action.py:68-77`) does `sys.exit(0 if result else 1)` when `result` is a `bool`, and `sys.exit(0)` when `result is None`. `[VERIFIED: .venv/lib/python3.11/site-packages/cyclopts/core.py:1888-1890,2597; cyclopts/_result_action.py:68-77]`

**Implication for the planner:** every existing `print(...); return` / `logger.error(...); return False` path in `run()` already produces the correct exit code today. The new preflight failure (D-12) needs no `sys.exit()` call and no new cyclopts configuration — `return False` (or any falsy/`int` return) after `logger.error(...)` is the idiomatic, already-tested pattern, and is what the codebase's existing error paths already do (`__main__.py:797-798`, `901-906`, `1022-1027`, `1037-1038`).

### cyclopts tri-state bool — verified against installed 4.10.1

Existing precedent in `run()`'s own signature already uses `negative=""` to *suppress* the negative flag and keep a plain unset-vs-set tri-state for `verbose`:
```
587	    verbose: Annotated[
588	        bool | None, cyclopts.Parameter(negative="", group=server_group)
589	    ] = None,
```
`[VERIFIED: packages/lifx-emulator/src/lifx_emulator_app/__main__.py:587-589]` — this pattern gives only `--verbose` (no `--no-verbose`), with `None` as unset.

`--mdns`/`--no-mdns` needs **both** flags with `None` as the unset third state — the opposite of `negative=""`. Verified empirically that a bare, unannotated `bool | None = None` parameter already produces exactly this:
```python
@app.default
def run(*, mdns: bool | None = None) -> None:
    print("mdns=", mdns)
```
- no flag -> `mdns= None`
- `--mdns` -> `mdns= True`
- `--no-mdns` -> `mdns= False`
- `--help` renders one combined row: `--mdns --no-mdns`

`[VERIFIED: local execution against .venv cyclopts 4.10.1]`. No `cyclopts.Parameter(...)` annotation is needed at all for `--mdns`/`--no-mdns` — the project's existing `negative=""` usage on `verbose`/`persistent`/`api`/`browser` is for the *opposite* case (suppressing the negative flag), and must not be copied onto `mdns`.

### Core mDNS event emission points (for D-06/D-07)

`MdnsResponder._operation()` (`mdns.py:114-128`) is the one place that calls `owner.async_register_service`/`async_update_service`/`async_unregister_service` per device record — this is the natural per-device hook for "registered"/"updated"/"withdrawn". `[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/mdns.py:114-128]` `_reconcile()` (`mdns.py:177-200`) is the caller that decides register vs. update vs. unregister per device, comparing against `self._services`/`self._tombstones` — this is where the event *kind* (registered vs. updated vs. withdrawn) is already disambiguated, so it is the natural place to also emit the per-device activity event rather than re-deriving that logic in `server.py`.

Responder-level start/stop/fail: `MdnsResponder.start()` (`mdns.py:130-143`) and `.stop()` (`mdns.py:233-265`) are the two lifecycle boundaries; `EmulatedLifxServer._start_mdns_locked()` (`server.py:982-999`) and `._stop_mdns_locked()` (`server.py:1019-1040`) are the server-side callers that already track `_mdns_status` transitions (`DISABLED`/`STOPPED`/`RUNNING`/`FAILED`, `mdns.py:25-33`) — the "started"/"stopped"/"failed" events map directly onto these status transitions, and `_mdns_failed()`/`_record_mdns_failure()` (`server.py:925-939`) is the existing single funnel for failures, already deduplicating repeated failure reports via `self._mdns_status != MdnsStatus.FAILED` checks (`server.py:944`) — reuse that funnel for the single "failed" event rather than adding a second one in the responder.

`retry_mdns()` (`server.py:1042-1057`) calls `_stop_mdns_locked()` then `_start_mdns_locked()` — since D-06 requires the recovery event sequence to look exactly like a fresh start (one "started" + one "registered" per device), and `_start_mdns_locked()` -> `_open_mdns_locked()` -> `responder.start(self.get_all_devices())` -> `MdnsResponder.start()` -> `_reconcile()` already re-registers every device from a clean `self._services = {}` state (each device transitions through the same "no previous entry" branch in `_reconcile()` at `mdns.py:186-199`), no special-casing is needed in the new event code for the retry path — it naturally replays the same emission points as first start.

### Address resolution threading for D-01/D-02

Current `resolve_address()` signature and body:
```python
def resolve_address(device: EmulatedLifxDevice, ipv4: str, ipv6: str) -> str | None:
    """Resolve only explicit intent or a concrete matching-family bind."""
    state = device.state
    if not state.mdns_enabled:
        return None
    fallback = ipv6 if state.connectivity == Connectivity.THREAD else ipv4
    try:
        return validate_mdns_address(
            state.mdns_address if state.mdns_address is not None else fallback,
            state.connectivity,
        )
    ...
```
`[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/mdns.py:36-50]`

Three call sites pass **bind** addresses as `ipv4`/`ipv6` today, not server-level advertised-address defaults:
- `MdnsResponder.service_info()`: `resolve_address(device, self.address, self.ipv6_address)` where `self.address`/`self.ipv6_address` are set from the constructor args `MdnsResponder(self.bind_address, self._effective_port or self.port, self.ipv6_bind_address, self._mdns_failed)` (`server.py:1005-1010`, `mdns.py:56-66,81`).
- `EmulatedLifxServer.add_device()`: `resolve_address(device, self.bind_address, self.ipv6_bind_address)` (`server.py:668`).
- `EmulatedLifxServer.start()`: `resolve_address(device, self.bind_address, self.ipv6_bind_address)` in the per-device loop (`server.py:1063-1064`).

D-01 requires a **third precedence tier** — server-level advertised-address default, tried before falling back to the concrete bind address. This means `resolve_address()`'s signature must grow (two more optional params, or the two bind addresses need to become "already-resolved effective address" inputs computed one level up) **and** `MdnsResponder` must be constructed with the two new addresses so `service_info()` can pass them through — `MdnsResponder.__init__` (`mdns.py:56-66`) currently has no such parameters. All three call sites plus the `MdnsResponder` constructor call in `server.py:1005-1010` need coordinated changes; this is core work, not app work (per D-01's architectural placement), and should be planned as one atomic core change before the app-side flag wiring that depends on it.

### Reuse gap: `coerce_connectivity`/`validate_mdns_address` are not barrel-exported

`devices/__init__.py`'s `__all__` (lines 40-61) exports `Connectivity` and `DeviceState` from `devices/states.py` but **not** `coerce_connectivity` or `validate_mdns_address`, even though both are defined in the same source file (`states.py:70-88` and `states.py:91-103`) and CONTEXT's "Established Patterns" explicitly names them as the functions the app must reuse rather than re-implement. `[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py:1-61 — full file read; grep confirms coerce_connectivity/validate_mdns_address appear nowhere in this file's imports or __all__]` Per this project's own Module Design convention ("Consumers import from the barrel"), the cleanest fix is a one-line core change: add both names to the existing `from lifx_emulator.devices.states import Connectivity, DeviceState` import and to `__all__`. Without this, `config.py`'s new validators would have to import from `lifx_emulator.devices.states` directly, which works functionally but violates the barrel convention documented in `.claude/CLAUDE.md` Module Design.

### Firmware/product gating for `--thread-product` (R3)

`FirmwareConfig.get_firmware_version()` / `_validate_firmware()` (`factories/firmware_config.py:40-161`) already enforces the Thread floor (4.200) and any product's terminal-firmware ceiling, and already names the product ID in the raised `ValueError`:
```python
message = (
    f"Firmware {result} exceeds product {product_id}'s maximum {max_firmware}"
)
if connectivity == Connectivity.THREAD and override is None:
    message += (
        f" (Thread's default firmware of {self.VERSION_THREAD} "
        "cannot be reduced to fit)"
    )
raise ValueError(message)
```
`[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py:153-161]` The only product with a documented terminal-firmware ceiling today is LIFX Tile (product 55) — `factories/factory.py`'s `create_tile_device` docstring states *"LIFX Tile (product 55) has a terminal firmware ceiling of 3.50, below the Thread floor of 4.200, so connectivity='thread' always raises ValueError for this factory"* `[VERIFIED: packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py:223-226]`. Because this error already names the product ID via the message text above, R3's "an unknown product ID fails with an error naming the ID" and the Thread-incompatible-product case are both already satisfied by calling `create_device(pid, connectivity="thread", ...)` and letting the existing `ValueError` propagate — no upfront product-capability lookup is required in the CLI layer (matches CONTEXT's "Claude's Discretion" on this point); it is simplest to just call `create_device` and catch `ValueError`, exactly as the existing `f_products` loop already does at `__main__.py:895-906`.

### Recommended Project Structure

```
packages/lifx-emulator/src/lifx_emulator_app/
├── __main__.py              # cyclopts commands; thin run() that delegates;
│                             #   keeps EmulatedLifxServer/_setup_logging/
│                             #   DevicePersistenceAsyncFile/resolve_config_path/
│                             #   load_config/webbrowser.open/logging.* calls
│                             #   directly in this module's namespace
├── config.py                 # + ipv6_bind, mdns, mdns_ipv4_address,
│                             #   mdns_ipv6_address, thread, thread_product on
│                             #   EmulatorConfig; + connectivity, mdns,
│                             #   mdns_address on DeviceDefinition
├── startup/                  # NEW (D-10) — pure logic, no patched globals
│   ├── __init__.py
│   ├── devices.py            # build_device_list(...) — counts, products,
│   │                         #   config_devices, --thread; no I/O
│   ├── settings.py           # RunSettings dataclass (D-11) + provenance
│   ├── preflight.py          # R5/R6 checks (D-12): refuse-to-start,
│   │                         #   wildcard-bind, D-03 warning
│   └── scenarios.py          # _apply_config_scenarios / _scenario_def_to_core
│                             #   (pure; can move safely, not patched in tests)
└── api/
    ├── models.py              # ActivityEvent + kind: str = "lifx"
    └── services/event_bridge.py  # WebSocketActivityObserver.on_mdns_event
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Tri-state `--mdns`/`--no-mdns` flag | A custom `str`-based flag or manual `sys.argv` scan | Plain `mdns: bool | None = None` cyclopts parameter | Verified empirically to already produce both flags with `None` unset — zero extra code |
| Non-zero exit on preflight failure | `sys.exit(1)` calls scattered through `run()` | `logger.error(...); return False` (existing idiom) | Already produces exit code 1 via cyclopts's default `result_action`; consistent with every existing error path in the file |
| Connectivity/mDNS-address validation | Re-implementing IPv4/IPv6-family checks, link-local/multicast rejection in `config.py` | Core's `coerce_connectivity`/`validate_mdns_address` (`devices/states.py:70-103`) | CONTEXT explicitly names this as the single source of truth; re-implementing risks CLI/YAML/API disagreeing on edge cases (scoped addresses, broadcast, unspecified) that the core already handles |
| mDNS lifecycle event de-duplication logic | A parallel "did this device's record change" comparison in the event-emission code | `MdnsResponder._reconcile()`'s existing register/update/unregister branching (`mdns.py:177-200`) | The branch that decides register vs. update vs. unregister already exists and is tested; emit the event from inside/adjacent to that decision rather than re-deriving it |

## Common Pitfalls

### Pitfall 1: Moving a `run()` helper breaks `unittest.mock.patch` silently
**What goes wrong:** A helper is extracted into `startup/server_start.py` with its own `from lifx_emulator.server import EmulatedLifxServer` import; `@patch("lifx_emulator_app.__main__.EmulatedLifxServer")` in `test_cli.py` no longer intercepts the constructor call, and the real server attempts to bind a real UDP socket during a unit test.
**Why it happens:** Python resolves free variables (including imported names) against the module where the *calling code* is textually defined, not where it's imported from. `mock.patch` only rewrites the target module's namespace entry.
**How to avoid:** Keep `EmulatedLifxServer(...)`, `DevicePersistenceAsyncFile()`, `_setup_logging()`, `resolve_config_path()`/`load_config()`, `logging.getLogger()`/`logging.basicConfig()`, and `webbrowser.open()` calls physically inside `__main__.py` (either in `run()` itself, or in private functions still defined in that file), or pass the class/callable into a `startup/` helper as an explicit parameter so the lookup happens in `__main__`'s frame.
**Warning signs:** A test that used to run in milliseconds starts taking longer, or fails with `OSError: [Errno 98] Address already in use` / hangs waiting on a real socket, or `mock_server_class.assert_called_once()` fails with "0 calls".

### Pitfall 2: Reordering shutdown to match CONTEXT's prose instead of the actual current code
**What goes wrong:** A new shutdown-order test is written against the CONTEXT.md parenthetical "(API task, server/mDNS, storage flush)" instead of the code's actual current order (storage, then server/mDNS, then API task — `__main__.py:1132-1144`), silently changing shutdown behaviour while believing R1's "unchanged behaviour" is satisfied.
**Why it happens:** CONTEXT.md is a planning artifact, written before this research pass re-read the source; its author's mental model of the order did not match the code.
**How to avoid:** Assert the order the code in `__main__.py:1135-1144` actually executes today; if the user wants the order changed, that must be raised explicitly as a decision, not silently absorbed into "R1 unchanged" test-writing.
**Warning signs:** A shutdown-order test passes against the refactored code but would have failed if run against the pre-refactor `run()` — that is the signature of testing intent instead of testing preserved behaviour.

### Pitfall 3: Writing `resolve_address()` changes without touching all three call sites plus the `MdnsResponder` constructor
**What goes wrong:** `EmulatedLifxServer.__init__`/`add_device()`/`start()` are updated to know about `mdns_ipv4_address`/`mdns_ipv6_address`, but `MdnsResponder.service_info()` (which is what actually runs at advertisement time via `_reconcile()` -> `snapshot()` -> `service_info()`) still calls the old two-argument `resolve_address(device, self.address, self.ipv6_address)`, so the server-level default silently never applies to live registrations.
**Why it happens:** `resolve_address()` has three call sites across two files (`server.py:668`, `server.py:1063-1064`, `mdns.py:81`), and `MdnsResponder` is constructed once, in `_open_mdns_locked()` (`server.py:1005-1010`), with no path today to carry the two new addresses.
**How to avoid:** Plan the `resolve_address()` signature change and the `MdnsResponder.__init__` parameter addition as one atomic core commit; grep for all `resolve_address(` call sites before considering the change complete.
**Warning signs:** R6's acceptance test ("a device without `mdns_address` is advertised at the server-level address of its family") passes for `add_device()` but a device added before `server.start()` and then re-registered via a scenario/reconcile falls back to the raw bind address instead.

## Code Examples

Illustrative patterns for the planner — not existing code, no provenance claimed beyond the verified cyclopts behaviour cited above.

### Tri-state `--mdns`/`--no-mdns` (mirrors verified local test)
```python
mdns: Annotated[bool | None, cyclopts.Parameter(group=server_group)] = None
```
No `negative=""` — that suppresses the negative flag, which is the opposite of what R2 needs.

### D-12 preflight collecting all problems before exiting
```python
def _preflight(settings: RunSettings, devices: list[EmulatedLifxDevice]) -> list[str]:
    """Collect every R5/R6 problem; caller decides to log+return False."""
    problems: list[str] = []
    thread_serials = [
        d.state.serial for d in devices if d.state.connectivity == Connectivity.THREAD
    ]
    if settings.mdns_resolved is False and thread_serials:
        problems.append(
            f"--no-mdns / mdns: false with Thread device(s): {', '.join(thread_serials)}"
        )
    # ... wildcard-bind-without-matching-address check, per family ...
    return problems
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The planner should keep `run()`'s currently-patched calls physically in `__main__.py` (or pass classes as injected parameters) rather than moving them wholesale into `startup/`. This is a design recommendation derived from the verified patch-target list, not a locked decision from CONTEXT.md. | Architecture Patterns / mock-patch constraint | If ignored, R1's "existing app test suite passes unchanged" acceptance criterion will fail in CI, not in planning — costly to discover late |
| A2 | The shutdown-order test should assert the code's actual current order (storage -> server/mDNS -> API task), not the CONTEXT.md prose order. | Architecture Patterns / shutdown order discrepancy | If the user actually wants shutdown reordered, treating this as `[ASSUMED]` and building the test against current behaviour would silently drop that intent; flag to the user during planning rather than deciding unilaterally |
| A3 | Adding `coerce_connectivity`/`validate_mdns_address` to the `lifx_emulator.devices` barrel `__all__` is an in-scope, low-risk core change for this phase (not a Phase 5 concern), because CONTEXT names both functions as required reuse targets. | Architecture Patterns / reuse gap | If out of scope, `config.py` validators must import from `lifx_emulator.devices.states` directly, which works but is a documented convention violation the plan-checker may flag |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Exact shutdown order intent**
   - What we know: the code today runs storage -> server/mDNS -> API task (`__main__.py:1132-1144`); CONTEXT.md's R1 acceptance criterion names the order as "(API task, server/mDNS, storage flush)".
   - What's unclear: whether CONTEXT's ordering is a drafting slip (just naming the three participants) or reflects an intent to reorder shutdown as part of this phase.
   - Recommendation: planner/discuss-phase should surface this discrepancy to the user explicitly rather than picking silently; default to "unchanged" (current code order) per R1's literal text if no answer is available before planning must proceed.

2. **`resolve_address()` signature shape for D-01**
   - What we know: three call sites need the new server-level defaults threaded through, plus a `MdnsResponder` constructor change.
   - What's unclear: whether to add two more positional/keyword params to `resolve_address()` directly, or to pre-resolve "effective ipv4/ipv6 default" once in `EmulatedLifxServer.__init__`/`MdnsResponder.__init__` and pass those down instead (fewer call-site changes, but changes what "ipv4"/"ipv6" mean semantically at each site).
   - Recommendation: this is an implementation-detail decision appropriate for the planner, not something requiring a further discuss-phase round; flagged here so the plan explicitly accounts for all three call sites plus the responder constructor as one atomic change.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cyclopts` | CLI flags (R2, R3) | ✓ | 4.10.1 `[VERIFIED: local venv]` | — |
| `pydantic` | YAML schema (R4) | ✓ | 2.x (project-pinned) | — |
| `pyyaml` | Config file loading | ✓ | project-pinned `>=6.0.3` | — |
| `zeroconf` | mDNS responder (already Phase 3 core dep) | ✓ | `>=0.151.3` per `.planning/STATE.md:35` | — |
| Real multicast/loopback mDNS in CI | Any test that actually starts the responder | Conditional | — | Phase 3's own pattern: unit tests inject datagrams directly / mock `AsyncZeroconf`; real-stack tests are gated behind `MDNS_INTEGRATION_REQUIRED=1` and skipped otherwise (`packages/lifx-emulator-core/tests/test_mdns_integration.py:20-24`) — reuse this pattern for any Phase 4 test that exercises `--mdns` end-to-end rather than requiring a real socket in every CI job |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Real-network mDNS integration tests — use the existing `MDNS_INTEGRATION_REQUIRED` gate and mock/inject patterns already established in Phase 3, consistent with cross-platform CI (Ubuntu + macOS; no hosted Windows socket run per `.planning/STATE.md:92`).

## Security Domain

`security_enforcement` is not set to `false` anywhere in `.planning/config.json`, so it is treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local loopback-bound CLI tool; no auth surface added by this phase |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes | Pydantic `EmulatorConfig`/`DeviceDefinition` with `extra="forbid"` (already the pattern), plus reuse of core's `coerce_connectivity`/`validate_mdns_address` for the new fields rather than re-implementing address-family/link-local/multicast checks |
| V6 Cryptography | no | N/A — no crypto surface in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted YAML deserialisation | Tampering | Already `yaml.safe_load` (`config.py:269`) — canon, owned by `/gsd-secure-phase` + Bandit per SPEC's "Canon referral"; not re-minted here |
| A CLI/YAML-supplied address accidentally advertising a device on a real LAN interface (AR-06, accepted in Phase 3) | Information Disclosure | R5's Thread-triggered auto-enable rule + D-12's refuse-to-start preflight are the mitigation already locked in CONTEXT; this phase's job is to implement them faithfully, not to add new mitigation |

## Sources

### Primary (HIGH confidence — direct source read and/or local execution this session)
- `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` — full file read (1150 lines)
- `packages/lifx-emulator/src/lifx_emulator_app/config.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/mdns.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` (lines 1-180) — `Connectivity`, `coerce_connectivity`, `validate_mdns_address`, `NetworkState`
- `packages/lifx-emulator-core/src/lifx_emulator/devices/__init__.py` — full file read, confirms barrel export gap
- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/factories/firmware_config.py` — full file read
- `packages/lifx-emulator/src/lifx_emulator_app/api/models.py` — full file read
- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` — full file read
- `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` (lines 33-192) — `DeviceLifecycleListener`, `IDeviceLifecycleSource`
- `.venv/lib/python3.11/site-packages/cyclopts/core.py` (`App.__call__`, `_handle_result_action`) and `cyclopts/_result_action.py` — read + empirically executed against installed 4.10.1
- `packages/lifx-emulator/tests/test_cli.py` — full `@patch` target enumeration via grep, plus representative test bodies read
- `packages/lifx-emulator-core/tests/test_mdns_integration.py` (lines 1-40), `test_mdns_platform.py` — CI/cross-platform test gating pattern
- `packages/lifx-emulator/frontend/src/lib/types.ts`, `ActivityLog.svelte`, `stores/connection.svelte.ts` — `direction` typing and WS consumption
- `docs/cli/websocket-api.md` (grep) — existing `direction: rx|tx` documentation needing an `mdns` addition
- `lifx-emulator.example.yaml` — full file read, for doc-update guidance
- `.planning/phases/04-cli-and-configuration/04-SPEC.md`, `04-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/config.json` — full reads

### Secondary (MEDIUM confidence)
None used — all findings for this phase were verifiable directly against the checked-out source or local execution.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all versions confirmed against the installed `.venv`
- Architecture (`run()` decomposition constraints, mDNS event wiring, address-resolution threading): HIGH — every claim backed by a direct source read with line citations, and the two open cyclopts questions resolved by local execution rather than documentation lookup
- Pitfalls: HIGH — derived directly from the verified mock-patch target list and the verified shutdown-order code, not from general CLI-testing folklore

**Research date:** 2026-09-24
**Valid until:** Should be re-verified if `cyclopts`, `pydantic`, or `zeroconf` are upgraded before this phase is planned/executed, or if `run()` is touched by any other change before this phase starts (re-read line numbers, which are exact-line citations and will drift).
