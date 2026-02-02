# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LIFX Emulator for testing LIFX LAN protocol libraries. Implements the binary UDP protocol from https://lan.developer.lifx.com and emulates color lights, multizone strips, tiles, infrared, HEV, and switch devices.

## Package Structure

This is a **uv workspace monorepo** with two packages:

| Package    | PyPI Name            | Import Name         | Description               |
| ---------- | -------------------- | ------------------- | ------------------------- |
| Library    | `lifx-emulator-core` | `lifx_emulator`     | Core emulator library     |
| Standalone | `lifx-emulator`      | `lifx_emulator_app` | CLI + HTTP management API |

Library code lives in `packages/lifx-emulator-core/src/lifx_emulator/`, standalone in `packages/lifx-emulator/src/lifx_emulator_app/`. Each package has its own `pyproject.toml` and `tests/` directory.

## Development Commands

```bash
uv sync                                          # Install dependencies
pytest                                           # Run all tests (both packages)
pytest packages/lifx-emulator-core/tests/        # Library tests only
pytest packages/lifx-emulator/tests/             # CLI/API tests only
pytest packages/lifx-emulator-core/tests/test_device.py  # Single test file
ruff check .                                     # Lint
ruff check --fix .                               # Lint with auto-fix
pyright                                          # Type check
python -m lifx_emulator_app --color 1            # Run emulator (no devices by default)
lifx-emulator --help                             # Full CLI reference
```

## Code Quality Standards

- All functions must have cyclomatic complexity ≤ 10 (enforced by Ruff McCabe)
- Pyright in standard mode
- Pre-commit hooks run format, lint, and type-check on every commit
- Never use the term "wide tile device" -- use "large matrix device" or "chained matrix device" instead

## Architecture

### Layered Design

1. **Network Layer** (`EmulatedLifxServer` in `server.py`): UDP transport via asyncio DatagramProtocol. Single responsibility: receives packets, delegates to DeviceManager, sends responses.
2. **Domain Layer** (`DeviceManager` in `devices/manager.py`, `HierarchicalScenarioManager` in `scenarios/manager.py`): Device lifecycle, packet routing, scenario resolution.
3. **Repository Layer** (`IDeviceRepository`, `IDeviceStorageBackend` in `repositories/`): Protocol interfaces for storage abstraction.
4. **Persistence Layer** (`DevicePersistenceAsyncFile`, `ScenarioPersistenceAsyncFile`): Async file I/O with debouncing.

All layers depend on Protocol interfaces, not concrete implementations. `EmulatedLifxServer` requires a `DeviceManager` instance (second constructor argument).

### Packet Flow

1. UDP packet → `EmulatedLifxServer.handle_packet()`
2. `LifxHeader.unpack()` → `get_packet_class()` + `.unpack()` for payload
3. Target devices resolved (broadcast or specific serial from header target field)
4. Each device: `device.process_packet()` → list of (header, packet) responses
5. Acknowledgment (type 45) auto-sent if `ack_required=True`
6. Responses packed and sent via UDP

### Key Patterns

- **Handlers return packets, not (header, packet) tuples** -- `process_packet()` constructs response headers
- **Handlers can return lists** for multi-packet responses (multizone/tile)
- **res_required flag** passed to handlers to decide whether to return state
- **Serial format**: 12-char hex string (e.g., "d073d5000001") → 6-byte MAC + 2 null bytes
- **Switches** return `StateUnhandled` (type 223) for Light/MultiZone/Tile packets; handle Device.\* packets normally

### Core Library Modules (`packages/lifx-emulator-core/src/lifx_emulator/`)

- **`devices/`**: `EmulatedLifxDevice` (packet processing), `DeviceManager` (lifecycle/routing), `DeviceState` (state dataclasses with capability flags: `has_color`, `has_infrared`, `has_multizone`, `has_matrix`, `has_hev`, `has_relays`, `has_buttons`)
- **`handlers/`**: Packet handlers split by protocol namespace -- `device_handlers.py` (types 2-59), `light_handlers.py` (101-149), `multizone_handlers.py` (501-512), `tile_handlers.py` (701-720). Registry in `registry.py` maps packet types to handlers.
- **`protocol/`**: Auto-generated `packets.py` (nested classes `Device.*`, `Light.*`, `MultiZone.*`, `Tile.*` with `PKT_TYPE`, `pack()`/`unpack()`), `header.py` (36-byte header), `serializer.py` (struct-based binary packing), `protocol_types.py` (LightHsbk, TileStateDevice, enums)
- **`products/`**: Auto-generated `registry.py` (137+ products), `specs.py`/`specs.yml` (product-specific defaults like zone counts and tile dimensions)
- **`factories/`**: `create_color_light()`, `create_multizone_light()`, `create_tile_device()`, `create_switch()`, `create_device(product_id)` (universal). All use specs system for product defaults.
- **`scenarios/`**: `HierarchicalScenarioManager` with 5 scope levels (device > type > location > group > global). `ScenarioConfig` supports `drop_packets`, `response_delays`, `malformed_packets`, `invalid_field_values`, `firmware_version`, `partial_responses`, `send_unhandled`.
- **`repositories/`**: `IDeviceRepository` (in-memory collection), `IDeviceStorageBackend`/`IScenarioStorageBackend` (persistence interfaces)

### Standalone App Modules (`packages/lifx-emulator/src/lifx_emulator_app/`)

- **`__main__.py`**: CLI entry point using cyclopts. Config file loading, device creation, server startup.
- **`config.py`**: Pydantic models (`EmulatorConfig` with `extra="forbid"`, `DeviceDefinition`, `HsbkConfig`, `ScenariosConfig`). Config resolution: CLI flag > env var `LIFX_EMULATOR_CONFIG` > auto-detect `lifx-emulator.yaml` in cwd. CLI args override config values.
- **`api/`**: FastAPI app with routers (`monitoring`, `devices`, `scenarios`), Pydantic request/response models (`models.py`), service layer (`services/`). `DeviceService` handles device CRUD; `ScenarioService` handles scenario get/set/delete across all 5 scope levels with automatic cache invalidation and persistence.

### Import Guidelines

```python
# Library (lifx-emulator-core)
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState, DeviceManager
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.factories import create_color_light, create_device
from lifx_emulator.server import EmulatedLifxServer

# App (lifx-emulator)
from lifx_emulator_app.api import create_api_app, run_api_server
```

## Key Domain Details

### MultiZone

- Standard: multiple `StateMultiZone` packets (type 506), 8 zones each
- Extended: one or more `ExtendedStateMultiZone` packets (type 512), 82 zones each
- Minimum 8 zones, no maximum. Zone count and extended capability are independent.
- Firmware: extended multizone → 3.70, non-extended → 2.60

### Matrix/Tile

- Up to 5 tiles per chain (most have 1). All tiles on a chain must be identical in size.
- `Get64`/`Set64` transfer up to 64 zones at a time; tiles >64 zones (16x8) need multiple requests
- 8 framebuffers (0-7): FB0 is visible (`tile_devices[i]["colors"]`), FB1-7 stored in `MatrixState.tile_framebuffers`, lazily initialized
- `Get64` always returns FB0; `Set64` respects `rect.fb_index`; `CopyFrameBuffer` copies between any FBs

### Product Defaults (from `specs.yml`)

- LIFX Beam: 80 zones, extended multizone
- LIFX Tile: 5 tiles of 8x8
- LIFX Candle: 1 tile of 5x6
- Factory functions use these defaults when parameters aren't specified

## Auto-Generated Files (Do Not Edit)

- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` → `python -m lifx_emulator.products.generator`
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py` → `python -m lifx_emulator.protocol.generator`
