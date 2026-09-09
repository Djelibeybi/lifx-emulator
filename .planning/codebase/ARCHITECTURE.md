<!-- refreshed: 2026-09-09 -->
# Architecture

**Analysis Date:** 2026-09-09

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Clients (LIFX LAN libraries / browser)               │
└──────────┬──────────────────────────────────┬────────────────────────────────┘
           │ UDP 56700 (binary LIFX protocol) │ HTTP/WS 8080 (management)
           ▼                                  ▼
┌──────────────────────────────┐   ┌───────────────────────────────────────────┐
│  Network Layer (core)        │   │  Standalone App (`lifx_emulator_app`)     │
│  `EmulatedLifxServer`        │   │  CLI `__main__.py` (cyclopts)             │
│  `lifx_emulator/server.py`   │◄──┤  FastAPI `api/app.py`                     │
│  asyncio DatagramProtocol    │   │  routers/ → services/ → mappers/          │
└──────────┬───────────────────┘   │  WebSocket bridge `services/event_bridge` │
           │                       │  Svelte 5 dashboard `frontend/` → static/ │
           ▼                       └──────────────────┬────────────────────────┘
┌──────────────────────────────────────────────────────▼───────────────────────┐
│  Domain Layer (core)                                                          │
│  `DeviceManager` `devices/manager.py`   ─ lifecycle, target resolution        │
│  `EmulatedLifxDevice` `devices/device.py` ─ scenario gate, capability filter, │
│      handler dispatch, response header construction, error scenarios          │
│  `HandlerRegistry` `handlers/registry.py` ─ pkt_type → `PacketHandler`        │
│  `HierarchicalScenarioManager` `scenarios/manager.py` ─ 5-scope merge         │
│  `DeviceState` `devices/states.py` ─ composed state dataclasses               │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Repository Layer (Protocol interfaces)  `lifx_emulator/repositories/`        │
│  `IDeviceRepository` / `DeviceRepository` (in-memory dict keyed by serial)    │
│  `IDeviceStorageBackend`, `IScenarioStorageBackend`                           │
└──────────┬───────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Persistence Layer (async file I/O, debounced)                               │
│  `DevicePersistenceAsyncFile` `devices/persistence.py` → `~/.lifx-emulator/*` │
│  `ScenarioPersistenceAsyncFile` `scenarios/persistence.py`                    │
└──────────────────────────────────────────────────────────────────────────────┘

Supporting: `protocol/` (auto-generated packets, 36-byte header, struct serializer),
`products/` (auto-generated registry + `specs.yml`), `factories/` (builder + factory fns)
```

All paths under `packages/lifx-emulator-core/src/` unless prefixed with `lifx_emulator_app`, which lives under `packages/lifx-emulator/src/`.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `EmulatedLifxServer` | UDP bind, header/payload unpack, target resolution, ack fast-path, response delay + send, stats, activity observer notification | `packages/lifx-emulator-core/src/lifx_emulator/server.py` |
| `EmulatedLifxServer.LifxProtocol` | asyncio `DatagramProtocol`; schedules `handle_packet` per datagram | `packages/lifx-emulator-core/src/lifx_emulator/server.py:151` |
| `DeviceManager` / `IDeviceManager` | Add/remove/get devices, share scenario manager, resolve broadcast vs targeted, lifecycle callbacks, cache invalidation | `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` |
| `EmulatedLifxDevice` | Per-device packet processing: scenario resolution + caching, capability gating (`StateUnhandled`), handler dispatch, response header creation, partial/malformed/invalid-field scenarios, state-change callbacks, debounced persistence trigger | `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` |
| `DeviceState` + sub-states | Composed dataclass; delegates attribute access via `_ATTRIBUTE_ROUTES` to `CoreDeviceState`, `NetworkState`, `LocationState`, `GroupState`, `WaveformState`, optional `InfraredState`, `HevState`, `MultiZoneState`, `MatrixState`, `ButtonsState` | `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` |
| `PacketHandler` (ABC) + `HandlerRegistry` | Strategy pattern: one stateless handler class per packet type, keyed by `PKT_TYPE` | `packages/lifx-emulator-core/src/lifx_emulator/handlers/base.py`, `handlers/registry.py` |
| Handler modules | Device (2-59), Light (101-149), MultiZone (501-512), Tile (701-720), Sensor (401/402), Button (905-911) | `packages/lifx-emulator-core/src/lifx_emulator/handlers/*_handlers.py` |
| `HierarchicalScenarioManager` + `ScenarioConfig` | Store scenarios at device/type/location/group/global scope; merge with precedence; probabilistic drops | `packages/lifx-emulator-core/src/lifx_emulator/scenarios/manager.py`, `scenarios/models.py` |
| `LifxHeader` | 36-byte header pack/unpack via pre-compiled `struct.Struct` | `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py` |
| `Packet` base + generated packets | Declarative `_fields` with struct-based pack/unpack; nested classes `Device.*`, `Light.*`, `MultiZone.*`, `Tile.*`, `Button.*`, `Sensor.*`; `get_packet_class()` | `packages/lifx-emulator-core/src/lifx_emulator/protocol/base.py`, `protocol/packets.py` (generated), `protocol/serializer.py` |
| `ProductRegistry` + `SpecsRegistry` | Product capabilities from LIFX `products.json` (generated) and emulator-specific defaults from `specs.yml` | `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py`, `products/specs.py`, `products/specs.yml` |
| `DeviceBuilder` + factory functions | Compose `DeviceState` from product info + specs + optional overrides; restore persisted state; construct device | `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py`, `factories/factory.py` |
| `StateRestorer` / `state_serializer` | Load saved JSON into a fresh `DeviceState`; (de)serialise HSBK, buttons, tiles | `packages/lifx-emulator-core/src/lifx_emulator/devices/state_restorer.py`, `devices/state_serializer.py` |
| `ActivityObserver` / `ActivityLogger` / `NullObserver` | Observer protocol for RX/TX `PacketEvent`s; rolling deque of recent activity | `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` |
| `DevicePersistenceAsyncFile` | Debounced, batched, executor-backed JSON writes per device serial | `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py` |
| `ScenarioPersistenceAsyncFile` | Load/save/delete the whole scenario manager as one JSON file | `packages/lifx-emulator-core/src/lifx_emulator/scenarios/persistence.py` |
| CLI (`run`, `list-products`, `clear-storage`, `export-config`) | Config resolution/merge, device creation from flags or YAML, wiring `DeviceRepository` → `DeviceManager` → `EmulatedLifxServer`, optional API task, signal handling | `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` |
| `EmulatorConfig` and friends | Pydantic config models (`extra="forbid"`), `resolve_config_path`, `load_config`, `merge_config` | `packages/lifx-emulator/src/lifx_emulator_app/config.py` |
| `create_api_app` / `run_api_server` | FastAPI factory: mounts static Svelte build, wires event bridge, includes 5 routers | `packages/lifx-emulator/src/lifx_emulator_app/api/app.py` |
| Routers | Thin HTTP layer per resource: `monitoring`, `devices`, `scenarios`, `products`, `websocket` | `packages/lifx-emulator/src/lifx_emulator_app/api/routers/` |
| Services | `DeviceService` (CRUD, bulk, pagination, colour application), `ScenarioService` (5-scope get/set/delete + cache invalidation + persistence + WS broadcast), `WebSocketManager` (connections, topics, broadcast), event bridge (sync callback → async broadcast) | `packages/lifx-emulator/src/lifx_emulator_app/api/services/` |
| `DeviceMapper` | `EmulatedLifxDevice` → `DeviceInfo` API model | `packages/lifx-emulator/src/lifx_emulator_app/api/mappers/device_mapper.py` |
| Svelte dashboard | SvelteKit static SPA (`ssr=false`, `prerender=true`); rune-based stores fed by one WebSocket | `packages/lifx-emulator/frontend/src/` |

## Pattern Overview

**Overall:** Layered architecture with dependency inversion (Protocol interfaces), Strategy pattern for packet handling, Builder pattern for device construction, Observer/callback pattern for activity and state events. The standalone app is a thin adapter layer (CLI + HTTP/WS) over the core library.

**Key Characteristics:**
- Core library (`lifx_emulator`) has no web dependencies (only `pydantic`, `pyyaml`); app package (`lifx_emulator_app`) adds `cyclopts`, `fastapi`, `uvicorn`, `rich`, `websockets`.
- Every layer depends on `typing.Protocol` interfaces (`IDeviceManager`, `IDeviceRepository`, `IDeviceStorageBackend`, `IScenarioStorageBackend`, `ActivityObserver`), all `@runtime_checkable`.
- `EmulatedLifxServer` requires a `DeviceManager` as its second constructor argument (`server.py:92-104`); it never touches the repository directly.
- Handlers are stateless singletons instantiated once in module-level `ALL_*_HANDLERS` lists and return **packet objects**, never headers; `EmulatedLifxDevice.process_packet()` builds headers (`device.py:218`).
- Scenario behaviour is applied in two places by design: drops and ack fast-path in the server (`server.py:249-264`), capability filtering, partial responses, malformed/invalid-field mutation and `send_unhandled` in the device (`device.py:281-460`).
- Performance-motivated choices are explicit: pre-allocated response header template (`device.py:99-107`), cached resolved scenario per device (`device.py:189`), `loop.call_soon(loop.create_task, ...)` scheduling (`server.py:175`), pre-packed payload reuse.
- Protocol packet classes and product registry are **generated** (`protocol/generator.py`, `products/generator.py`) from upstream LIFX YAML/JSON; never hand-edit `packets.py` or `registry.py`.

## Layers

**Network Layer:**
- Purpose: UDP transport; decode header + payload; route to devices; encode and send responses; keep stats.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/server.py`
- Contains: `EmulatedLifxServer`, nested `LifxProtocol`, logging helpers `_get_packet_type_name`, `_format_packet_fields`.
- Depends on: `IDeviceManager`, `LifxHeader`, `get_packet_class`, `HierarchicalScenarioManager`, `ActivityObserver`, `IScenarioStorageBackend`.
- Used by: CLI `__main__.py:1070`, API services (via `server` reference), library consumers, tests.

**Domain Layer:**
- Purpose: Device lifecycle, packet semantics, state mutation, scenario resolution.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/devices/`, `handlers/`, `scenarios/`
- Contains: `DeviceManager`, `EmulatedLifxDevice`, `DeviceState` and sub-states, `PacketHandler` subclasses, `HandlerRegistry`, `HierarchicalScenarioManager`, `ScenarioConfig`.
- Depends on: `protocol/` (packets, types, header), `repositories/` interfaces, `constants.py`.
- Used by: Network layer, factories, app services.

**Repository Layer:**
- Purpose: Abstract storage of live devices and persisted state/scenarios behind Protocols.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/repositories/`
- Contains: `IDeviceRepository`, `DeviceRepository` (in-memory), `IDeviceStorageBackend`, `IScenarioStorageBackend`.
- Depends on: `EmulatedLifxDevice` (type only).
- Used by: `DeviceManager`, `EmulatedLifxServer` (scenario storage), CLI wiring.

**Persistence Layer:**
- Purpose: Concrete async file backends implementing the storage Protocols.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `scenarios/persistence.py`
- Contains: `DevicePersistenceAsyncFile` (per-device debounce 100 ms, batch threshold 50, single-thread `ThreadPoolExecutor`), `ScenarioPersistenceAsyncFile`.
- Depends on: `state_serializer.py`, `HierarchicalScenarioManager`.
- Used by: `EmulatedLifxDevice._save_state()` (`device.py:160`), `DeviceBuilder.build()` via `StateRestorer` (`builder.py:333-336`), CLI.

**Protocol Layer:**
- Purpose: Wire format for the LIFX LAN protocol.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/protocol/`
- Contains: `header.py` (`LifxHeader`, `_HEADER_STRUCT = "<HHI Q6sBB QHH"`), `base.py` (`Packet` with `_fields` metadata), `serializer.py`, `protocol_types.py` (`LightHsbk`, `TileStateDevice`, enums), `packets.py` (generated), `const.py`, `generator.py`.
- Depends on: `constants.py` only.
- Used by: Everything above.

**Products / Factories:**
- Purpose: Turn a product ID into a fully configured device.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/products/`, `factories/`
- Contains: `ProductRegistry`/`ProductInfo`/`ProductCapability` (generated), `SpecsRegistry` loading `specs.yml`, `DeviceBuilder`, `SerialGenerator`, `DefaultColorConfig`, `FirmwareConfig`, `create_*` functions.
- Depends on: Domain layer (`DeviceState`, `EmulatedLifxDevice`), persistence (`StateRestorer`).
- Used by: CLI, `DeviceService`, tests, library consumers.

**Application Layer (standalone package):**
- Purpose: CLI, HTTP management API, WebSocket streaming, embedded dashboard.
- Location: `packages/lifx-emulator/src/lifx_emulator_app/`
- Contains: `__main__.py` (cyclopts `app` with `run` default plus `list_products`, `clear_storage`, `export_config`), `config.py`, `api/app.py`, `api/routers/`, `api/services/`, `api/mappers/`, `api/models.py`, `api/static/` (built Svelte output).
- Depends on: Core library public exports.
- Used by: End users via `lifx-emulator` console script; browser via `/`.

**Presentation Layer (frontend):**
- Purpose: Real-time dashboard (Visualizer, Devices, Activity, Scenarios tabs).
- Location: `packages/lifx-emulator/frontend/src/`
- Contains: `routes/+page.svelte`, `lib/components/*.svelte`, `lib/stores/*.svelte.ts` (Svelte 5 runes), `lib/utils/api.ts` (REST calls), `lib/utils/color.ts`, `lib/types.ts`.
- Depends on: `/api/*` REST and `/ws` WebSocket.
- Used by: Browser; built into `api/static/` via `@sveltejs/adapter-static` (`frontend/svelte.config.js`).

## Data Flow

### Primary Request Path (UDP packet in → response out)

1. Datagram arrives; `LifxProtocol.datagram_received` schedules `handle_packet` on the cached loop (`packages/lifx-emulator-core/src/lifx_emulator/server.py:171-180`).
2. `handle_packet` bumps `packets_received`, rejects packets shorter than 36 bytes, unpacks `LifxHeader` (`server.py:321`) and slices payload by `header.size`.
3. `get_packet_class(header.pkt_type)` then `packet_class.unpack(payload)`; unknown types are logged and still forwarded (`server.py:330-372`).
4. Activity observer notified with an RX `PacketEvent` (`server.py:389-399`).
5. `DeviceManager.resolve_target_devices(header)`: tagged or all-zero target → all devices; otherwise `header.target[:6].hex()` lookup (`packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:268-290`).
6. Broadcasts fan out with `asyncio.gather`; single targets run inline (`server.py:401-417`).
7. `_process_device_packet`: resolve cached scenario, apply `drop_packets` gate **before** any ack (`server.py:246-251`); fast-path ack when `ack_required` and scenario does not affect acks and device can handle the type (`server.py:258-264`, `_send_ack` at `server.py:182`).
8. `EmulatedLifxDevice.process_packet(header, packet)` (`packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:281`):
   - `_should_handle_packet` capability gate → `Device.StateUnhandled` (type 223) for e.g. Light packets on switches (`device.py:246-279`).
   - `_handle_packet_type` looks up `HandlerRegistry.get_handler(pkt_type)` and calls `handler.handle(state, packet, res_required)` → `list[packet]` (`device.py:415-435`); triggers `_save_state()` when storage is set and fires `on_state_changed` for `STATE_CHANGING_PACKETS` (`device.py:40-57`, `device.py:438-448`).
   - Unknown/unregistered types return `StateUnhandled` if `scenario.send_unhandled` (default `True`).
   - `partial_responses` truncates multi-packet lists; each packet gets a header from the pre-allocated template via `_create_response_header` (`device.py:218`); `_apply_error_scenarios` truncates (`malformed_packets`) or fills `0xFF` (`invalid_field_values`) (`device.py:375-413`).
9. Server iterates `(header, packet_or_bytes)` responses, sleeps `response_delays[pkt_type]` if set, packs and `transport.sendto` (`server.py:268-278`), updates TX stats and notifies observer.

### Device Creation via HTTP API

1. `POST /api/devices` → `create_device` in `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py:118`.
2. `DeviceService.create_device(request)` (`packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py:124`) calls `lifx_emulator.factories.create_device(product_id, ...)` (`device_service.py:151`).
3. `create_device` → `DeviceBuilder(product_info)` → `build()` (`packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py:248-339`): serial generation, specs defaults, firmware, default colour, composed `DeviceState`, optional `StateRestorer`, then `EmulatedLifxDevice(...)`.
4. `server.add_device(device)` sets `device.state.port` and delegates to `DeviceManager.add_device(device, scenario_manager)` (`server.py:422-433`, `manager.py:146-177`), which shares the server's scenario manager, stores in `DeviceRepository`, and fires `on_device_added`.
5. Event bridge callback (`packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:67-71`) maps to `DeviceInfo` and schedules `WebSocketManager.broadcast_device_added` (`api/services/websocket_manager.py:271`).
6. Router returns `DeviceMapper.to_device_info(device)` as `DeviceInfo` (201).

### Scenario Update via HTTP API

1. `PUT /api/scenarios/{scope}/{id}` (router functions built by `_add_*_endpoints` in `api/routers/scenarios.py:22-227`).
2. `ScenarioService` calls the matching `set_*_scenario` on `server.scenario_manager` via `_SCOPE_METHODS` (`api/services/scenario_service.py:23-31`).
3. `_persist()` → `server.invalidate_all_scenario_caches()` → every device drops `_cached_scenario`; then `scenario_persistence.save(manager)` if `--persistent-scenarios` (`scenario_service.py:66-70`).
4. `_broadcast_change()` → `WebSocketManager.broadcast_scenario_changed` (`websocket_manager.py:312`).
5. Next packet to any device re-resolves via `HierarchicalScenarioManager.get_scenario_for_device` (`scenarios/manager.py:174-236`): merge order global → group → location → type → device; dicts overwrite, lists union, `send_unhandled` most-specific wins.

### State Persistence

1. Handler mutates `DeviceState`; `_handle_packet_type` calls `_save_state()` when `packet and self.storage` (`device.py:433-435`).
2. `_save_state` creates a tracked task for `storage.save_device_state(state)` (`device.py:160-187`).
3. `DevicePersistenceAsyncFile.save_device_state` serialises via `serialize_device_state`, coalesces per serial, and schedules `_flush_after_delay` (100 ms) or immediate `_flush` at 50 pending (`persistence.py:99-127`).
4. `_flush` runs `_batch_write` in the single-worker executor writing `{serial}.json` under `DEFAULT_STORAGE_DIR` (`persistence.py:147-188`).
5. On next start, `DeviceBuilder.build()` → `StateRestorer.restore_if_available(state)` (`builder.py:333-336`, `devices/state_restorer.py:32`).

### Real-Time Dashboard Flow

1. Browser loads `/` → `api/static/index.html` (`api/app.py:193-202`).
2. `connection.connect()` opens `ws://host/ws` on mount (`frontend/src/routes/+page.svelte`, `frontend/src/lib/stores/connection.svelte.ts`), subscribes to topics, requests `sync`.
3. `WebSocketManager.handle_message` handles `subscribe`/`sync` (`websocket_manager.py:123`); `StatsBroadcaster` pushes `stats` every second (`event_bridge.py:176-235`).
4. Server-side events (`device_added`, `device_removed`, `device_updated`, `activity`, `scenario_changed`) originate from `DeviceManager` callbacks, `WebSocketStateChangeObserver.on_state_changed` (`event_bridge.py:237-343`) and `WebSocketActivityObserver` wrapping the server's `ActivityLogger` (`event_bridge.py:84-173`, installed at `api/app.py:214-216`).
5. Frontend stores update; `devices.svelte.ts` batches updates via `requestAnimationFrame`.

**State Management:**
- Live device state lives only in `DeviceState` instances held by `DeviceRepository` (single process, in-memory).
- Scenario state lives in one shared `HierarchicalScenarioManager` (`server.scenario_manager`); devices cache the merged result until invalidated.
- Server statistics are plain counters on `EmulatedLifxServer` (`server.py:140-146`).
- Frontend state lives in Svelte 5 rune stores under `frontend/src/lib/stores/`, hydrated exclusively from the WebSocket `sync` message and subsequent events; REST is used only for mutations (`frontend/src/lib/utils/api.ts`).

## Key Abstractions

**`PacketHandler` (Strategy):**
- Purpose: Encapsulate one packet type's semantics against a `DeviceState`.
- Examples: `GetServiceHandler` (`handlers/device_handlers.py:19`), `SetColorHandler` (`handlers/light_handlers.py:116`), `Set64Handler` (`handlers/tile_handlers.py:198`), `ExtendedGetColorZonesHandler` (`handlers/multizone_handlers.py:116`).
- Pattern: Class attribute `PKT_TYPE = <Namespace>.<Packet>.PKT_TYPE`; `handle(device_state, packet, res_required) -> list[Any]`; append instance to the module's `ALL_*_HANDLERS`; `create_default_registry()` in `handlers/__init__.py` registers all lists.

**`DeviceState` (composed state with attribute routing):**
- Purpose: Single façade over focused sub-state dataclasses; optional sub-states return defaults from `_OPTIONAL_DEFAULTS` when absent.
- Examples: `state.zone_colors` → `state.multizone.zone_colors`; `state.tile_devices` → `state.matrix.tile_devices`; `state.location_label` → `state.location.location_label`.
- Pattern: `__getattr__`/`__setattr__` consult `_ATTRIBUTE_ROUTES` (`devices/states.py:263-354, 363-466`). Adding a field means adding it to the sub-state **and** the routing table.

**`HierarchicalScenarioManager` / `ScenarioConfig`:**
- Purpose: Fault-injection configuration with 5 scope levels.
- Examples: `scenarios/manager.py`, `scenarios/models.py` (Pydantic; `drop_packets: dict[int, float]`, `response_delays`, `malformed_packets`, `invalid_field_values`, `partial_responses`, `firmware_version`, `send_unhandled`, `affects_acks` property).
- Pattern: Device type string from `get_device_type()` (`matrix` > `extended_multizone` > `multizone` > `hev` > `infrared` > `color` > `basic`).

**Protocol interfaces (`typing.Protocol`, `@runtime_checkable`):**
- Purpose: Allow substitution of manager, repository, storage and observer implementations.
- Examples: `IDeviceManager` (`devices/manager.py:27`), `IDeviceRepository` (`repositories/device_repository.py:15`), `IDeviceStorageBackend`/`IScenarioStorageBackend` (`repositories/storage_backend.py`), `ActivityObserver` (`devices/observers.py:37`).
- Pattern: Constructor injection; `EmulatedLifxServer(devices, device_manager, ...)`.

**`DeviceBuilder` (Builder) + factory functions:**
- Purpose: Deterministic composition of a device from `ProductInfo` + `specs.yml` + fluent overrides.
- Examples: `factories/builder.py:67`, `factories/factory.py:189` (`create_device`), typed wrappers `create_color_light` (PID 91), `create_multizone_light`, `create_tile_device`, `create_switch`.
- Pattern: `with_*()` chain then `build()`; delegates serial/colour/firmware decisions to `SerialGenerator`, `DefaultColorConfig`, `FirmwareConfig`.

**Generated `Packet` classes:**
- Purpose: Declarative binary layout; `pack()`/`unpack()`/`as_dict()`; `PKT_TYPE`; `get_packet_class(pkt_type)`.
- Examples: `protocol/packets.py` (`Device.StateService`, `Light.StateColor`, `MultiZone.ExtendedStateMultiZone`, `Tile.State64`, `Device.StateUnhandled`).
- Pattern: Regenerate with `python -m lifx_emulator.protocol.generator`; never edit by hand.

**Router factories + Service classes (app):**
- Purpose: Keep FastAPI handlers thin; put logic in services that raise typed exceptions mapped to HTTP codes in routers.
- Examples: `create_devices_router(server)` (`api/routers/devices.py:28`), `DeviceService` (`api/services/device_service.py:60`), `ScenarioService` (`api/services/scenario_service.py:52`), exceptions `DeviceNotFoundError`, `DeviceAlreadyExistsError`, `ScenarioNotFoundError`, `InvalidDeviceSerialError`.
- Pattern: `create_<name>_router(...) -> APIRouter` closure capturing `server`/`ws_manager`; included in `create_api_app`.

**Event bridge (sync → async):**
- Purpose: Core library callbacks are synchronous; the bridge schedules WebSocket coroutines with `_schedule_async` (`event_bridge.py:30`).
- Examples: `wire_device_events`, `wire_device_state_events` (wraps existing `on_device_added` so new devices get `on_state_changed`), `WebSocketActivityObserver` (decorator over `ActivityLogger`).

## Entry Points

**Console script `lifx-emulator` / `python -m lifx_emulator_app`:**
- Location: `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (`main()` at line 1147 → `cyclopts.App`; default command `run` at line 580)
- Triggers: User CLI invocation; `[project.scripts]` in `packages/lifx-emulator/pyproject.toml`.
- Responsibilities: Resolve config (`--config` > `LIFX_EMULATOR_CONFIG` > `lifx-emulator.yaml` in cwd, `config.py:234`), merge CLI over config, create devices, build `DeviceRepository` → `DeviceManager` → `EmulatedLifxServer` (`__main__.py:1052-1080`), optionally start `run_api_server` as a task (`__main__.py:1086-1089`), install SIGINT/SIGTERM/SIGBREAK handlers, shut down storage and server.

**Library API:**
- Location: `packages/lifx-emulator-core/src/lifx_emulator/__init__.py` (exports `EmulatedLifxServer`, `EmulatedLifxDevice`, `create_*`), plus sub-package `__init__.py` files.
- Triggers: `import lifx_emulator` in test suites of LIFX client libraries.
- Responsibilities: Construct devices, run server as async context manager (`server.py:527-535`).

**FastAPI app:**
- Location: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:45` (`create_api_app`), `:238` (`run_api_server`)
- Triggers: `--api` flag from CLI; direct use by tests (`packages/lifx-emulator/tests/test_api.py`).
- Responsibilities: Serve dashboard at `/`, static under `/_app` and `/static`, REST under `/api/*`, WebSocket at `/ws`, OpenAPI at `/docs`.

**UDP endpoint:**
- Location: `EmulatedLifxServer.start()` (`server.py:515`) binding `bind_address:port` (default `127.0.0.1:56700`).
- Triggers: LIFX client discovery/broadcast and targeted packets.

**Code generators:**
- Location: `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py`, `products/generator.py`
- Triggers: Manual `python -m lifx_emulator.protocol.generator` / `python -m lifx_emulator.products.generator` when upstream LIFX specs change.

**Frontend dev server / build:**
- Location: `packages/lifx-emulator/frontend/package.json` (`vite dev`, `vite build`)
- Triggers: Developer; build output lands in `packages/lifx-emulator/src/lifx_emulator_app/api/static/`.

## Architectural Constraints

- **Threading:** Single asyncio event loop. UDP handling, FastAPI (uvicorn in-loop) and WebSocket broadcasting share it. The only worker thread is the single-worker `ThreadPoolExecutor` inside `DevicePersistenceAsyncFile` (`devices/persistence.py:64`) and default-executor calls in `ScenarioPersistenceAsyncFile`. Signal handlers use `loop.call_soon_threadsafe` (`__main__.py:1101-1103`). Handlers must stay synchronous and non-blocking.
- **Global state:** Module-level singletons `_registry = ProductRegistry()` (`products/registry.py:1802`) and `_specs_registry = SpecsRegistry()` (`products/specs.py:245`); handler instances in module-level `ALL_*_HANDLERS` lists are shared across all devices and must remain stateless; cyclopts `app` object in `__main__.py:50`.
- **Circular imports:** Avoided via `TYPE_CHECKING` guards and local imports: `devices/manager.py` imports `HierarchicalScenarioManager` inside `add_device`; `device.py` imports `get_packet_class` inside `_handle_packet_type`; `handlers/*` import `DeviceState` under `TYPE_CHECKING`; `api/services/event_bridge.py` imports `DeviceManager`/`DeviceMapper` inside functions. Dependency direction is `protocol` → `devices/handlers/scenarios` → `repositories` → `factories` → `server`; app imports core, never the reverse.
- **Scenario consistency:** Any scenario mutation must be followed by `server.invalidate_all_scenario_caches()`; devices otherwise keep serving the cached merge.
- **Serial format:** 12 hex chars; `header.target[:6].hex()` must equal `state.serial`; persistence validates with `_SERIAL_RE` to prevent path traversal (`persistence.py:80-96`).
- **Auto-generated files:** `protocol/packets.py` and `products/registry.py` are excluded from coverage and line-length lint; do not edit.
- **Complexity budget:** Ruff McCabe max 10, max 5 args, 12 branches, 50 statements (`pyproject.toml`); this is why routers use `_add_*_endpoints` helpers and the device pipeline is split across `process_packet`, `_apply_error_scenarios`, `_handle_packet_type`.
- **Terminology:** Describe multi-tile or oversized matrix products as "large matrix device" or "chained matrix device" (the legacy "wide"-prefixed phrasing is prohibited by `CLAUDE.md`).

## Anti-Patterns

### Returning `(header, packet)` tuples from handlers

**What happens:** A new handler builds its own `LifxHeader` and returns tuples.
**Why it's wrong:** `EmulatedLifxDevice.process_packet()` owns header construction (source/sequence copy, size, target) and error-scenario mutation; tuples break `partial_responses`, `_apply_error_scenarios` and the `resp_packet.pack()` call in `server.py:275`.
**Do this instead:** Return `list[Packet]` (empty list for no response). See `SetColorHandler` in `handlers/light_handlers.py:116` and the contract in `handlers/base.py:25-46`.

### Reading `device.state.<capability_field>` without checking the capability flag

**What happens:** Code accesses `state.zone_count` on a colour bulb and relies on the delegated default.
**Why it's wrong:** `DeviceState.__getattr__` returns `_OPTIONAL_DEFAULTS` values (e.g. `0`, `[]`) for absent sub-states, silently masking logic errors; writes to an absent sub-state raise.
**Do this instead:** Gate on `state.has_multizone` / `state.has_matrix` / `state.has_hev` / `state.has_infrared` / `state.has_buttons` first, as done in `_should_handle_packet` (`device.py:246`) and every capability handler.

### Bypassing `DeviceManager` to mutate the repository or device list

**What happens:** App code appends to a repository or list directly.
**Why it's wrong:** Skips scenario-manager sharing, port assignment, `on_device_added`/`on_device_removed` callbacks (so WebSocket clients and state-change wiring are never informed) and persistence deletion on removal.
**Do this instead:** Use `server.add_device()` / `server.remove_device()` (`server.py:422-455`) which delegate to `DeviceManager` (`devices/manager.py:146-239`).

### Mutating scenarios without invalidating caches

**What happens:** Code calls `scenario_manager.set_device_scenario(...)` and expects immediate effect.
**Why it's wrong:** Devices cache the merged `ScenarioConfig` (`device.py:189-208`).
**Do this instead:** Go through `ScenarioService` (`api/services/scenario_service.py`) or call `server.invalidate_all_scenario_caches()` after every mutation, as `_apply_config_scenarios` and the service do.

### Blocking I/O or `time.sleep` inside handlers or the server path

**What happens:** Synchronous file or network calls inside `handle()`.
**Why it's wrong:** Everything runs on one event loop; a blocking call stalls all devices, the API and WebSocket broadcasts.
**Do this instead:** Mutate state only; persistence is asynchronous and debounced via `DevicePersistenceAsyncFile`; delays are implemented with `await asyncio.sleep` in `server.py:272`.

### Hand-editing generated protocol or product files

**What happens:** Adding a packet or product by editing `protocol/packets.py` / `products/registry.py`.
**Why it's wrong:** Regeneration overwrites the change; lint/coverage exclusions assume generated content.
**Do this instead:** Update the generator or upstream source and re-run `python -m lifx_emulator.protocol.generator` / `python -m lifx_emulator.products.generator`; put emulator-specific defaults in `products/specs.yml`.

## Error Handling

**Strategy:** Defensive at boundaries, permissive in the middle. The UDP path never raises to the transport; the API maps typed service exceptions to HTTP status codes; callbacks are isolated so one failing observer cannot break packet processing.

**Patterns:**
- `handle_packet` wraps everything in `try/except Exception`, increments `error_count` and logs with `exc_info=True` (`server.py:419-421`); payload unpack failures log a warning with hex dump and drop the packet (`server.py:333-347`).
- Unknown packet types are logged and still routed; devices reply `StateUnhandled` when `send_unhandled` is true (`device.py:449-460`).
- Lifecycle and state-change callbacks are wrapped in `try/except` with `logger.exception` (`manager.py:164-168`, `device.py:441-448`).
- Services raise domain exceptions (`DeviceNotFoundError`, `DeviceAlreadyExistsError`, `DeviceCreationError`, `DeviceStateUpdateError`, `ScenarioNotFoundError`, `InvalidDeviceSerialError`); routers translate to `HTTPException` 404/409/400/500 (`api/routers/devices.py`, `api/routers/scenarios.py`).
- Pydantic validation guards inputs: `EmulatorConfig` uses `extra="forbid"`, `DeviceCreateRequest.validate_serial_format`, `HsbkConfig` uint16/kelvin validators (`config.py`, `api/models.py`).
- Constructor invariants raise `ValueError` early (e.g. `persist_scenarios=True` without storage/manager, `server.py:111-121`; unknown product ID, `factory.py:245-246`).
- CLI logs errors and returns instead of raising for user-facing failures (`__main__.py:1023-1027`, `1029-1039`).

## Cross-Cutting Concerns

**Logging:** Standard `logging` with `logger = logging.getLogger(__name__)` per module. Server logs `← RX` / `→ TX` at DEBUG with formatted fields (`server.py:43-84`), drops and scenario effects at INFO. CLI installs `RichHandler` and toggles DEBUG with `--verbose` (`__main__.py:68`). No structured logging framework.

**Validation:** Protocol-level via struct sizes and enum decoding in `protocol/base.py`; domain-level via capability flags; API/config via Pydantic models; serial format via regex in persistence and services.

**Authentication:** None. API and UDP bind to `127.0.0.1` by default; intended for local test use only.

**Observability:** `get_stats()` counters (`server.py:484`), `ActivityLogger` ring buffer (100 events), `DevicePersistenceAsyncFile.get_stats()`, WebSocket `stats` topic every second, `/api/stats` and `/api/activity` endpoints (`api/routers/monitoring.py`).

**Configuration:** YAML config merged under CLI flags (`config.py:266-333`); `--persistent` / `--persistent-scenarios` select file backends; default storage dir `DEFAULT_STORAGE_DIR` in `devices/persistence.py`.

**Testing hooks:** Every collaborator is injectable (`handler_registry`, `scenario_manager`, `storage`, `activity_observer`, `device_manager`), enabling unit tests without sockets; shared fixtures in `packages/lifx-emulator-core/tests/conftest.py`.

---

*Architecture analysis: 2026-09-09*
