# Codebase Concerns

**Analysis Date:** 2026-09-09

## Tech Debt

**Complexity limit is documented but not enforced:**
- Issue: `CLAUDE.md` and the CI step name ("Ruff linter (with complexity checks)") claim cyclomatic complexity <= 10 is enforced by Ruff McCabe. `[tool.ruff.lint.mccabe] max-complexity = 10` and `[tool.ruff.lint.pylint]` limits are configured in `pyproject.toml`, but `select = ["E", "F", "I", "N", "W", "UP"]` never enables `C901` or `PLR09xx`, so the limits are dead configuration. Running `uv run ruff check --select C901,PLR0913,PLR0912,PLR0915 packages/` reports 49 violations.
- Files: `pyproject.toml` (`[tool.ruff.lint]`), `.github/workflows/ci.yml` (quality job), `CLAUDE.md`
- Worst offenders in hand-written code: `packages/lifx-emulator/src/lifx_emulator_app/__main__.py:580` `run()` (complexity 61, 26 parameters, 197 statements, 59 branches); `__main__.py:230` `_device_state_to_yaml_dict` (18); `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py:28` `create_devices_router` (16); `packages/lifx-emulator-core/src/lifx_emulator/scenarios/persistence.py:67` `_sync_load` (13); `packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py:273` `CopyFrameBufferHandler.handle` (12); `packages/lifx-emulator-core/src/lifx_emulator/handlers/light_handlers.py:259` `SetWaveformOptionalHandler.handle` (20 branches)
- Impact: New code can silently regress in complexity; the documented standard is untrue, which erodes trust in `CLAUDE.md`.
- Fix approach: Add `"C90"` (and optionally `"PLR"`) to `select`, add `per-file-ignores` for the auto-generated `products/registry.py`, `protocol/generator.py`, `products/generator.py`, then decompose `run()` into device-construction, storage-setup, server-start and shutdown helpers so the rule passes.

**`run()` CLI entry point is a monolith:**
- Issue: `run()` in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py:580-1145` handles config merge, storage init, restore-from-persistence, device creation for eight device flavours, config-file device overrides, scenario loading, server start, API start, signal handling and shutdown in one 560-line coroutine.
- Files: `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`
- Impact: Every CLI feature touches the same function; `packages/lifx-emulator/tests/test_cli.py` is 2056 lines largely because behaviour cannot be exercised in isolation.
- Fix approach: Extract `_build_devices_from_flags()`, `_restore_or_create_devices()`, `_apply_config_device_overrides()`, `_start_servers()` and `_run_until_shutdown()`; keep `run()` as orchestration only.

**Zone/tile colour padding logic duplicated three ways:**
- Issue: The "pad a colour list to N entries by repeating the last colour, then truncate" logic exists in `DeviceService._pad_and_truncate` / `_fill_hsbk` (`packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py:255-281`) and again inline in `__main__.py:1000-1013` for config-file `zone_colors`. The two implementations differ: the CLI pads with `default_color`, the API pads with the last supplied colour.
- Files: `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`
- Impact: Same YAML/API input yields different zone fills depending on entry point.
- Fix approach: Move a single `pad_colors(colors, count, fill=...)` helper into `lifx_emulator.factories` (core) and call it from both.

**Matrix tile state is untyped dict soup:**
- Issue: `MatrixState.tile_devices` is `list[dict[str, Any]]` (`packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:131`). Twenty-seven call sites across handlers, services, mappers and the event bridge index it with string keys (`tile["width"]`, `tile.get("colors", [])`), with inconsistent defaults (`tile.get("width", 8)` in `device_service.py`, `tile.get("width", 0)` in `event_bridge.py:288`).
- Files: `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py`, `packages/lifx-emulator-core/src/lifx_emulator/handlers/tile_handlers.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/device_service.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`
- Impact: Pyright cannot catch key typos or missing fields; defaults diverge silently.
- Fix approach: Introduce a `TileDevice` dataclass (or `TypedDict`) in `states.py`, migrate `state_serializer.py`/`state_restorer.py` first, then handlers.

**Inline imports scattered through hot paths and app code:**
- Issue: Beyond the auto-generated files, 24 non-`TYPE_CHECKING` inline imports exist in `packages/lifx-emulator/src` and several in core: `protocol/base.py` re-imports `serializer` and `protocol_types` inside `_pack_field_value`, `_unpack_array_field`, `_unpack_single_field` (lines 191, 256, 271, 303, 312, 343, 396); `devices/device.py:433` imports `get_packet_class` inside `_handle_packet_type`; `api/app.py:246` imports `uvicorn` inside `run_api_server`; `__main__.py:1086` imports `run_api_server` inside `run()`; `event_bridge.py` imports `DeviceManager`, `ActivityLogger`, `DeviceMapper` inside functions.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/protocol/base.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`, `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`
- Impact: Violates the project rule that all imports go at the top; hides circular-import pressure between `protocol.base`, `protocol.serializer` and `protocol.protocol_types`; per-call `import` statements add a `sys.modules` lookup to every field pack/unpack.
- Fix approach: Break the `base` <-> `protocol_types` cycle by moving the enum-type table into `serializer.py` (which has no upstream deps), then hoist all imports. Add `ruff` rule `PLC0415` (import-outside-toplevel) once clean.

**Server reaches into device/manager privates:**
- Issue: `EmulatedLifxServer._send_ack` calls `device._create_response_header(...)` and `_process_device_packet` calls `device._get_resolved_scenario()` / `device._should_handle_packet()` (`server.py:197, 251, 265`). `create_api_app` uses `server._device_manager` (`api/app.py:198,202`).
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`
- Impact: Layer boundaries described in `CLAUDE.md` are porous; renaming a private on `EmulatedLifxDevice` breaks the server.
- Fix approach: Promote the three device methods to public API (`create_response_header`, `resolved_scenario`, `handles_packet`) and expose `EmulatedLifxServer.device_manager` as a read-only property.

**Tooling config drift:**
- Issue: `.pre-commit-config.yaml` pins `ruff-pre-commit` at `v0.9.1` while `uv.lock` resolves `ruff` `0.15.9` and `pyproject.toml` requires `>=0.14.2`; pyright hook is `stages: [manual]` so it never runs locally; `ci.skip` lists a non-existent `run-tests` hook; header comment says "Pre-commit hooks for lifx-async". `renovate.json` includes `postUpdateOptions: ["gomodTidy"]` with no Go module, a `pip_requirements` manager pointed at `pyproject.toml` (the pep621 manager already covers it), and a `customManagers` regex for `uv add --dev` in `CLAUDE.md` that matches nothing (`grep -c "uv add --dev" CLAUDE.md` = 0). CI installs bandit via `uv pip install bandit` outside the lockfile.
- Files: `.pre-commit-config.yaml`, `renovate.json`, `.github/workflows/ci.yml`
- Impact: Local hooks format with a different ruff than CI, producing spurious diffs; type errors surface only in CI; Renovate config carries noise.
- Fix approach: Switch the ruff and pyright hooks to `uv run ruff` / `uv run pyright` local hooks (or `prek` which is already a dev dependency), delete the dead Renovate stanzas, add `bandit` to the `dev` dependency group.

**Banned terminology still present in tests:**
- Issue: `CLAUDE.md` forbids the phrase "wide tile device"; `packages/lifx-emulator-core/tests/test_matrix_products.py:5,138` uses "wide tile".
- Impact: Contradicts stated convention; minor.
- Fix approach: Reword to "large matrix device".

## Known Bugs

**Activity log target serial is corrupted when the serial ends in `0`:**
- Symptoms: `server.py:375` computes `target_str = header.target.hex().rstrip("0000")`. `str.rstrip` strips a character set, not a suffix, so any trailing `0` digits of the serial itself are removed. Verified: target `d073d5000100` + 2 null bytes -> `"d073d50001"`; `d073d5000001` -> correct.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py:375`
- Trigger: Send any unicast packet to a device whose serial ends in one or more `0` hex digits (e.g. `d073d8000010`). The RX debug log line and the `PacketEvent.target` pushed to `/api/activity` and the WebSocket `activity` topic carry the truncated value, so the dashboard cannot correlate the packet to the device.
- Workaround: None from the client side. Fix: `header.target[:6].hex()`.

**Untracked fire-and-forget tasks in the packet and event paths:**
- Symptoms: `LifxProtocol.datagram_received` schedules `handle_packet` via `loop.call_soon(loop.create_task, ...)` and `asyncio.create_task(...)` without retaining a reference (`server.py:174-180`). `_schedule_async` in `event_bridge.py:29-38` does the same for every WebSocket broadcast (one task per RX and TX packet when `--api-activity` is on). No `add_done_callback`/set-tracking exists anywhere in `packages/lifx-emulator/src` (`grep background_tasks|add_done_callback` returns nothing), unlike `device.py:_track_save_task` and `persistence.py:_track_task` which do it correctly.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`
- Trigger: Under GC pressure asyncio may collect a pending task before it runs (documented asyncio caveat), dropping a packet response or a broadcast with no log.
- Workaround: None. Fix: keep a `set[asyncio.Task]` on `EmulatedLifxServer` and `WebSocketManager` and mirror the `_track_save_task` pattern.

## Security Considerations

**Management API is unauthenticated and can bind to all interfaces:**
- Risk: `--api-host` accepts any address (`__main__.py:611`; docstring in `api/app.py:252` even shows `0.0.0.0`). No auth dependency, API key, or CORS middleware exists (`grep -n "CORS|Depends|api_key" packages/lifx-emulator/src` returns none). `DELETE /api/devices` wipes every device, `PUT /api/scenarios/global` can set `drop_packets`/`response_delays` for all devices, and `/ws` streams every packet.
- Files: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/devices.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/routers/scenarios.py`, `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`
- Current mitigation: Default bind `127.0.0.1`; no browser CORS headers means cross-origin `fetch` from a hostile page is blocked for reads, but a same-origin-free WebSocket connection to `ws://127.0.0.1:8080/ws` is not (WebSockets are not subject to CORS).
- Recommendations: Add an optional `--api-token` that installs a bearer-token dependency on all mutating routes and the WebSocket handshake; check the `Origin` header in `websocket_endpoint`; log a warning when `api_host` is not loopback.

**Scenario scope identifiers are unvalidated and persisted:**
- Risk: `PUT /api/scenarios/{types,locations,groups}/{identifier}` accepts arbitrary strings as dictionary keys which are written to `~/.lifx-emulator/scenarios.json` (`scenarios/persistence.py:163-191`). Only the `device` scope validates its identifier (`scenario_service.py:150`).
- Files: `packages/lifx-emulator/src/lifx_emulator_app/api/services/scenario_service.py`, `packages/lifx-emulator-core/src/lifx_emulator/scenarios/persistence.py`
- Current mitigation: Identifiers are JSON dict keys, not file paths, so no traversal is possible; device-state paths are guarded by `_SERIAL_RE` in `devices/persistence.py:24,84-99`.
- Recommendations: Cap identifier length and restrict to printable characters in a Pydantic path-param validator; add a maximum count of scoped scenarios to bound file growth.

**Malformed UDP input is logged at ERROR with tracebacks:**
- Risk: `LifxHeader.unpack` raises `ValueError` for wrong origin/addressable bits (`header.py:129-132`); this propagates to the catch-all in `handle_packet` (`server.py:418-420`) which logs `logger.error(..., exc_info=True)`. Any host on the LAN can flood the log (and inflate `error_count`) by sending 36 bytes of garbage to 56700.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py`
- Current mitigation: Packets shorter than 36 bytes are handled at WARNING without traceback.
- Recommendations: Catch `ValueError` from `LifxHeader.unpack` explicitly and log at WARNING without `exc_info`; reserve the outer `except Exception` for genuine handler bugs.

**Code generators fetch from the network without checksum:**
- Risk: `products/generator.py:151` and `protocol/generator.py:1226` use `urlopen(PRODUCTS_URL/PROTOCOL_URL)` (raw GitHub, `# nosec`) and regenerate committed source.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/products/generator.py`, `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py`, `packages/lifx-emulator-core/src/lifx_emulator/constants.py`
- Current mitigation: Generation is a manual developer action; output is reviewed in the diff.
- Recommendations: Pin to a commit SHA rather than `refs/heads/main|master`, and print the upstream commit into the generated file header so drift is auditable.

**`.env` file present at repo root:**
- Risk: `.env` exists in the working tree (contents not read). It is listed in `.gitignore` and `git status` is clean, so it is not tracked.
- Recommendations: None beyond keeping it ignored; nothing in `packages/` reads `.env` (no `dotenv` dependency in `uv.lock`).

## Performance Bottlenecks

**Reflection-driven pack/unpack on every packet:**
- Problem: `Packet.pack()`/`unpack()` in `protocol/base.py` iterate `_fields` metadata per call, re-parse the field type string (`_parse_field_type`), rebuild the `enum_types` set literal on every `_pack_field_value` call (`base.py:195-206`), and resolve nested struct classes with `getattr(protocol_types, base_type)` per field. The 38 `from lifx_emulator.protocol import serializer` statements inside `protocol_types.py` methods execute on each nested pack/unpack.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/protocol/base.py`, `packages/lifx-emulator-core/src/lifx_emulator/protocol/protocol_types.py`, `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py`
- Cause: The generator emits metadata-driven classes rather than per-packet `struct.Struct` formats. This is in contrast to `header.py` which already uses a precompiled `_HEADER_STRUCT`.
- Improvement path: Have `protocol/generator.py` emit a precompiled `struct.Struct` per flat packet (most packets are flat primitives) with a fast path in `pack()`/`unpack()`, falling back to the generic path only for packets with nested arrays (`Set64`, `StateMultiZone`, `ExtendedStateMultiZone`). Hoist `enum_types` to a module constant.

**Persistence save triggered by read packets:**
- Problem: `_handle_packet_type` calls `self._save_state()` whenever `packet and self.storage` (`device.py:422-424`), i.e. for any packet with a non-empty payload, including reads such as `Tile.Get64`, `MultiZone.GetColorZones` and `Light.GetPower` when a client includes payload fields. Each call serialises the full `DeviceState` via `serialize_device_state` (`persistence.py:104-108`) before debouncing coalesces it.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`, `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`
- Cause: The save condition uses "has payload" as a proxy for "mutating".
- Improvement path: Gate on `pkt_type in STATE_CHANGING_PACKETS` (already defined and used two lines later for the state-change callback) or on the packet's `_packet_kind == "SET"` metadata.

**Per-packet WebSocket fan-out and full-device serialisation:**
- Problem: With `--api-activity`, every RX and TX packet creates a task that acquires `WebSocketManager._lock`, builds a message, and `gather`s `send_json` to each client (`websocket_manager.py:213-236`). `WebSocketStateChangeObserver.on_state_changed` calls `DeviceMapper.to_device_info(device)` and dumps all zone/tile colours on each Set packet (`event_bridge.py:262-305`), so a 5x(16x8) matrix pushes 640 HSBK dicts per `Set64`.
- Files: `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/websocket_manager.py`
- Cause: No batching or rate limiting; slow clients are only dropped after `send_json` raises.
- Improvement path: Buffer activity events into a per-tick batch flushed by `StatsBroadcaster`'s 1 s loop (or a 50-100 ms coalescing window); for `device_updated`, send only the tile index/zone range touched by the packet.

**Broadcast processing awaits response delays serially per device:**
- Problem: In `_process_device_packet`, `await asyncio.sleep(delay)` runs inside the response loop (`server.py:272-275`); for a broadcast the per-device tasks are gathered, but within one device with `partial_responses` producing multiple packets the delays accumulate.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py`
- Cause: Delay is applied per response packet rather than once per device.
- Improvement path: Acceptable for a test emulator; document it, or apply the delay once before the loop when all responses share a delay.

## Fragile Areas

**Auto-generated protocol and product modules:**
- Files: `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py` (1527 lines), `packages/lifx-emulator-core/src/lifx_emulator/protocol/protocol_types.py` (1304 lines, hand-edited section with 38 inline imports), `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` (1836 lines), generators `protocol/generator.py` (1480 lines) and `products/generator.py` (1108 lines)
- Why fragile: Generators pull from moving upstream branches; `protocol_types.py` and `registry.py` are excluded from coverage (`pyproject.toml [tool.coverage.run] omit`) and `packets.py` has `E501` ignored, so regressions in generated code are invisible to CI metrics. `products/specs.yml` (513 lines) is a hand-maintained overlay that must stay in step with `registry.py` product IDs.
- Safe modification: Never edit generated files; change the generator, regenerate, and diff. Run `packages/lifx-emulator-core/tests/test_protocol_generator.py`, `test_products_generator.py`, `test_backwards_compatibility.py` and `test_specs.py` after regeneration.
- Test coverage: Generator output is validated by `test_protocol_new_packets.py` and `test_protocol_types_coverage.py`, but only for packets those tests enumerate.

**Frontend build output committed alongside source with no CI check:**
- Files: `packages/lifx-emulator/frontend/src/**` (3800 lines Svelte/TS), built artefacts committed under `packages/lifx-emulator/src/lifx_emulator_app/api/static/_app/` (16 tracked files), adapter config `packages/lifx-emulator/frontend/svelte.config.js`
- Why fragile: `.github/workflows/ci.yml` `changes` filter only watches `packages/**`, `pyproject.toml`, `uv.lock` for Python jobs; there is no job that runs `npm ci && npm run check && npm run build` or verifies the committed `static/_app` matches `frontend/src`. Last commit touching `static/` (2026-04-07, vite CVE bump) post-dates the last `frontend/src` change (2026-03-19), but nothing guarantees this going forward. `frontend/README.md` is the unmodified `sv` template and does not document the build-into-`static` step. The frontend has no test files (`find frontend/src -name "*.test.*"` is empty) and `svelte-check` is never run in CI.
- Safe modification: After any `frontend/src` change run `npm run check && npm run build` in `packages/lifx-emulator/frontend` and commit the regenerated `static/` in the same commit.
- Test coverage: None for the Svelte app; API contract is covered indirectly by `packages/lifx-emulator/tests/test_api.py` and `test_websocket.py`.

**Scenario cache invalidation is manual:**
- Files: `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` (`_cached_scenario`, `invalidate_scenario_cache`), `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:160-166`, `packages/lifx-emulator/src/lifx_emulator_app/api/services/scenario_service.py:63-67`
- Why fragile: Each device caches its resolved `ScenarioConfig`; correctness depends on every writer remembering to call `server.invalidate_all_scenario_caches()`. `ScenarioService._persist` does; direct library users mutating `HierarchicalScenarioManager` (the documented library import path in `CLAUDE.md`) will not, and the config-file path in `__main__.py:_apply_config_scenarios` builds the manager before devices are attached so it happens to work.
- Safe modification: Route all mutations through `HierarchicalScenarioManager` methods and have the manager bump a generation counter that devices compare against instead of requiring explicit invalidation.
- Test coverage: `test_scenario_manager.py` and `test_scenario_service.py` cover the API path; no test asserts stale-cache behaviour for library callers.

**`SetWaveformOptional` handler duplicates colour propagation logic:**
- Files: `packages/lifx-emulator-core/src/lifx_emulator/handlers/light_handlers.py:259-322`
- Why fragile: Four `set_*` flag checks are repeated three times (device colour, each multizone zone, each tile zone). Adding a fifth component or a new device class requires editing three blocks in lockstep.
- Safe modification: Extract `_apply_optional_components(target: LightHsbk, packet)` and call it for each target.
- Test coverage: `test_light_handlers_extended.py` covers the single-colour path; verify zone/tile propagation cases exist before refactoring.

**`WebSocketManager.broadcast` mutates client map while iterating results:**
- Files: `packages/lifx-emulator/src/lifx_emulator_app/api/services/websocket_manager.py:213-236`
- Why fragile: After `gather`, failed sends call `await self.disconnect(ws)`, which re-acquires `_lock` per failure; concurrent broadcasts scheduled by `_schedule_async` can interleave and call `disconnect` for the same socket twice (harmless today because `pop(ws, None)` tolerates it, but log noise and double-count of "remaining").
- Safe modification: Collect failed sockets and disconnect once under a single lock acquisition.

## Scaling Limits

**Single-process asyncio, single UDP socket:**
- Current capacity: One `DatagramProtocol` on one port; broadcasts fan out with `asyncio.gather` per device (`server.py:405-415`) but all packing is CPU-bound Python under the GIL.
- Limit: Throughput is bounded by the reflection-based pack/unpack cost multiplied by device count; a broadcast `GetColor` to N devices performs N full response builds serially on one core.
- Scaling path: Precompiled struct fast path (see Performance) first; multi-process sharding by port is possible because `DeviceManager` is per-server, but persistence directory would need per-process namespacing.

**Persistent storage is one JSON file per device in one directory:**
- Current capacity: `DevicePersistenceAsyncFile.list_devices()` globs `*.json` on startup (`persistence.py:265-277`); `export-config` reads every file synchronously (`__main__.py:426-441`).
- Limit: Thousands of devices make startup and export O(N) synchronous file reads on the event loop thread (`load_device_state` is documented as blocking).
- Scaling path: Batch loads through the existing single-thread executor; or a single `devices.json` written atomically.

**Activity log fixed at 100 events:**
- Current capacity: `ActivityLogger(max_events=100)` hardcoded in `server.py:139` and `event_bridge.py:113`; `/api/activity` description says "last 100".
- Limit: At LAN discovery rates the buffer covers well under a second of traffic.
- Scaling path: Expose `--activity-buffer` CLI flag; make the WebSocket the primary consumer (already the case for the dashboard).

## Dependencies at Risk

**`lifx-emulator` declares `lifx-emulator-core>=2.4.0` while core is 3.8.0:**
- Risk: `packages/lifx-emulator/pyproject.toml` allows the app to install against core 2.x/3.0-3.7 from PyPI, but the app calls APIs such as `DeviceManager` as a required second `EmulatedLifxServer` argument, `scenario_persistence`, `invalidate_all_scenario_caches`, `create_device(... firmware_version=...)`. The workspace lock hides this locally.
- Impact: `pip install lifx-emulator` with a cached older core produces import/attribute errors at runtime.
- Migration plan: Bump the floor to the core version that introduced the newest API the app relies on (at minimum `>=3.0.0`), and have `semantic-release` for the app update it automatically when core releases a major.

**Frontend `cookie` pinned `<1.0.0`:**
- Risk: `renovate.json` and `frontend/package.json` `overrides` pin `cookie` to `^0.7.0` because `@sveltejs/kit` depends on named exports removed in 1.x. Security fixes for `cookie` 1.x will not be picked up.
- Impact: Low today (CVE-2024-47764 is fixed in 0.7.0); increases with time.
- Migration plan: Remove the override once `@sveltejs/kit` supports `cookie` 1.x; Renovate's dashboard will show the blocked update.

**Pre-commit hook versions frozen independently of `uv.lock`:**
- Risk: `ruff-pre-commit v0.9.1` vs locked `ruff 0.15.9`; `pyright-python v1.1.407`; `bandit 1.8.0`; `codespell v2.3.0`; `pre-commit-hooks v5.0.0`. None are managed by Renovate (`renovate.json` has no `pre-commit` manager enabled).
- Impact: Formatting rules drift between local commits and CI (`ruff format --check` in `ci.yml`).
- Migration plan: Enable Renovate's `pre-commit` manager or replace tool hooks with `uv run` local hooks.

**PyApp binary build depends on `ofek/pyapp` at `v0.26.0` cloned at release time:**
- Risk: `.github/workflows/release-binaries.yml:70-71` clones the upstream repo by tag; if the tag is moved or deleted the release job fails. Rust toolchain is `stable` (digest-pinned action, but floating toolchain).
- Impact: Binary releases are non-reproducible across time.
- Migration plan: Vendor the PyApp source tarball hash check or install the published Cargo package with `cargo install pyapp --version`.

## Missing Critical Features

**No authentication or origin check on the management API:**
- Problem: See Security. Exposing the dashboard beyond loopback (the documented use-case of `--api-host` for containers) has no access control.
- Blocks: Safe use in shared CI runners or Docker networks without an external reverse proxy.

**No frontend test or type-check gate:**
- Problem: `svelte-check` exists as an npm script but is never executed in CI; there is no Vitest/Playwright suite despite `.playwright-mcp/` artefacts at the repo root.
- Blocks: Refactoring the 612-line `ScenarioPanel.svelte` or 606-line `Visualizer.svelte` safely.

**No structured way to observe dropped/malformed scenario effects:**
- Problem: When `drop_packets` triggers, the server logs at INFO (`server.py:257`) but does not emit a `PacketEvent`, so the dashboard shows an RX with no TX and no reason.
- Blocks: Test authors diagnosing why a client saw a timeout.

## Test Coverage Gaps

**Malformed UDP header handling:**
- What's not tested: No test sends a header with a bad origin/addressable bit or protocol number through `EmulatedLifxServer.handle_packet` (`grep "Invalid origin|Addressable" packages/lifx-emulator-core/tests/test_server.py` returns nothing). `header.py` sits at 87% line coverage.
- Files: `packages/lifx-emulator-core/src/lifx_emulator/server.py`, `packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py`, `packages/lifx-emulator-core/tests/test_server.py`
- Risk: Log-flood behaviour and `error_count` semantics change unnoticed.
- Priority: Medium

**Activity `target` formatting:**
- What's not tested: The `rstrip("0000")` bug above ships with 92% coverage of `server.py` because no assertion inspects `PacketEvent.target` for a serial ending in `0`.
- Files: `packages/lifx-emulator-core/tests/test_server.py`, `packages/lifx-emulator-core/tests/test_observers.py`
- Risk: Regression of the fix.
- Priority: High (cheap, and pins a real bug)

**Frontend:**
- What's not tested: All of `packages/lifx-emulator/frontend/src` (stores, WebSocket reconnection in `connection.svelte.ts`, colour maths in `utils/color.ts`).
- Risk: Dashboard breakage only discovered manually.
- Priority: Medium

**Lowest-covered core modules (from `coverage.xml`, generated 2026-08-16; overall 95.3%):**
- `handlers/base.py` 80%, `repositories/device_repository.py` 85%, `scenarios/persistence.py` 86%, `protocol/header.py` 87%, `protocol/serializer.py` 88%, `handlers/tile_handlers.py` 89%, `devices/manager.py` 89%, `devices/device.py` 90%.
- Files: as listed under `packages/lifx-emulator-core/src/lifx_emulator/`
- Risk: `tile_handlers.py` gaps concentrate in `CopyFrameBufferHandler` bounds handling and uninitialised-framebuffer branches; `scenarios/persistence.py` gaps are the corrupted-file recovery paths.
- Priority: Medium. Note: `coverage.xml` and `junit.xml` are gitignored local artefacts and may be stale relative to HEAD; CI enforces only `--cov-fail-under=80`.

**Generated modules excluded from coverage:**
- What's not tested: `protocol_types.py`, `products/registry.py` and both generators are in `[tool.coverage.run] omit`, so hand-written logic inside them (e.g. `registry.py:133 caps()` and `registry.py:1635 load_from_dict()`, both flagged by C901) has no coverage signal.
- Files: `pyproject.toml`, `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py`
- Risk: Product capability derivation bugs go unmeasured.
- Priority: Low

---

*Concerns audit: 2026-09-09*
