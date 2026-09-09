<!-- GSD:project-start source:PROJECT.md -->

## Project

**LIFX Emulator**

A LIFX LAN protocol emulator for testing LIFX client libraries without real hardware. It implements the binary UDP protocol from https://lan.developer.lifx.com and emulates colour lights, multizone strips, matrix devices (Tile, Candle, Ceiling), infrared, HEV and switch products, with a scenario engine for fault injection, a FastAPI management API, a WebSocket activity stream and a Svelte dashboard. It ships as a core library (`lifx-emulator-core`, import `lifx_emulator`) and a standalone CLI/API app (`lifx-emulator`, import `lifx_emulator_app`) in one uv workspace.

This milestone adds **Thread emulation**: LIFX bulbs now ship firmware that runs the LAN protocol over Thread (IPv6, via a border router) instead of WiFi, and the emulator must be able to present a device the way a Thread bulb presents itself on the wire, so that `lifx-async` (the primary consumer) can exercise its Thread discovery and transport paths against the emulator instead of synthetic fixtures or physical hardware.

**Core Value:** A LAN client library can discover and control an emulated Thread device exactly as it would a real one: found only over mDNS with an AAAA record, reachable only by IPv6 unicast, every reply carrying the Thread connection bit.

### Constraints

- **Compatibility**: Python 3.10–3.14, Linux/macOS/Windows — CI matrix and PyApp binaries cover all three; socket code must be portable
- **Tech stack**: asyncio, no threads in the packet path — mDNS responder and IPv6 transport must be asyncio `DatagramProtocol` based like `EmulatedLifxServer`; research decides whether a dependency such as `zeroconf` is acceptable or a hand-rolled responder (as lifx-async did for its client) is preferable
- **Protocol fidelity**: header bit 3 and mDNS TXT semantics must match `lifx-async` exactly; `lifx-async`'s test fixtures are the contract
- **Code quality**: cyclomatic complexity ≤ 10, Pyright standard, Ruff, imports at top of file, Australian English, conventional commits with `core-`/`app-` scopes, GPG-signed `-s` commits
- **Generated files**: `protocol/packets.py` and `products/registry.py` are not edited by hand; no Thread changes belong there
- **Backwards compatibility**: default behaviour (IPv4, WiFi, existing CLI/config/API) must be unchanged for existing users; `connectivity` defaults to `wifi`

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python >=3.10 (tested 3.10 through 3.14 in CI) - Core library (`packages/lifx-emulator-core/src/lifx_emulator/`) and standalone CLI/API app (`packages/lifx-emulator/src/lifx_emulator_app/`). Ruff and Pyright target `py310`.
- TypeScript 6.0.x (strict mode) - Web dashboard frontend in `packages/lifx-emulator/frontend/src/` (Svelte 5 runes-based stores `*.svelte.ts`, utilities, types)
- Svelte 5.57.x - UI components in `packages/lifx-emulator/frontend/src/lib/components/*.svelte`
- YAML - Product specs (`packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml`), emulator config files (`lifx-emulator.example.yaml`), CI and docs config
- Rust - Not present in the repository source. The `stable` Rust toolchain is used only in CI (`.github/workflows/release-binaries.yml`) to compile PyApp (`ofek/pyapp` v0.26.0) into self-contained platform binaries. There is no `Cargo.toml` in this repo.

## Runtime

- CPython 3.10+ (asyncio event loop; UDP via `asyncio.DatagramProtocol` in `packages/lifx-emulator-core/src/lifx_emulator/server.py`)
- CI matrix: Python 3.10, 3.11, 3.12, 3.13, 3.14 on `ubuntu-latest` and `macos-latest` (`.github/workflows/ci.yml`)
- Node.js (version unpinned; no `.nvmrc`) - only required to rebuild the frontend; the built output is committed to `packages/lifx-emulator/src/lifx_emulator_app/api/static/`
- uv (workspace mode; CI pins `UV_VERSION: 0.9.9` in `ci.yml`, `0.11.8` in `docs.yml`)
- Lockfile: present (`uv.lock` at repo root, single lock for the whole workspace)
- npm for the frontend - Lockfile: present (`packages/lifx-emulator/frontend/package-lock.json`)
- Workspace definition: `pyproject.toml` at root (`[tool.uv.workspace] members = ["packages/*"]`, `lifx-emulator-core = { workspace = true }`)

## Frameworks

- asyncio (stdlib) - UDP server (`EmulatedLifxServer`), debounced async file persistence (`devices/persistence.py`, `scenarios/persistence.py`)
- Pydantic 2.12.x (`>=2.0.0`) - Config models in `packages/lifx-emulator/src/lifx_emulator_app/config.py`; API request/response models in `packages/lifx-emulator/src/lifx_emulator_app/api/models.py`; scenario models in `packages/lifx-emulator-core/src/lifx_emulator/scenarios/models.py`
- FastAPI 0.135.x (`>=0.115.0`) - HTTP management API and WebSocket endpoint; app factory `create_api_app()` in `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`
- Uvicorn 0.44.x (`>=0.34.0`) - ASGI server; `run_api_server()` in `api/app.py` builds `uvicorn.Config`/`uvicorn.Server` and awaits `serve()` inside the existing event loop
- websockets 16.0 (`>=16.0`) - WebSocket transport backend for Uvicorn (`/ws` endpoint in `api/routers/websocket.py`)
- cyclopts 4.10.x (`>=4.2.0`) - CLI framework; entry point `lifx_emulator_app.__main__:main` in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (commands: `run`, `list-products`, `clear-storage`, `export-config`)
- SvelteKit 2.70.x with `@sveltejs/adapter-static` 3.0.x - Frontend, statically exported into the FastAPI package (`packages/lifx-emulator/frontend/svelte.config.js` writes `pages`/`assets` to `../src/lifx_emulator_app/api/static` with `fallback: 'index.html'`)
- pytest 9.0.x (`>=8.4.2`) - Config in root `pyproject.toml` `[tool.pytest.ini_options]`; `testpaths` covers both packages' `tests/` dirs
- pytest-asyncio 1.3.x - `asyncio_mode = "auto"`, function-scoped loops
- pytest-cov 7.1.x - Branch coverage, XML + terminal reports; CI enforces `--cov-fail-under=80`
- pytest-sugar 1.1.x - Output formatting
- httpx 0.28.x - Used by FastAPI `TestClient` in `packages/lifx-emulator/tests/test_api.py`, `test_websocket.py`, `test_cli_validation.py`
- svelte-check 4.3.x - Frontend type checking (`npm run check`)
- hatchling 1.29.x - Build backend for both packages (`[build-system]` in each package `pyproject.toml`; wheel `packages = ["src/<pkg>"]`)
- Ruff 0.15.x - Formatter and linter (`select = ["E", "F", "I", "N", "W", "UP"]`, McCabe `max-complexity = 10`, pylint `max-args = 5`, `max-branches = 12`, `max-statements = 50`, line length 88)
- Pyright 1.1.408 - `typeCheckingMode = "standard"`, `include = ["packages/*/src"]`
- Bandit - Security linting in CI (`uv pip install bandit` step) and pre-commit; config `[tool.bandit]` in root `pyproject.toml`
- codespell - Spell checking via pre-commit (`[tool.codespell]` skips built frontend assets)
- prek 0.3.x - Pre-commit runner (dev dependency); hook definitions in `.pre-commit-config.yaml` (ruff-format, ruff, uv-lock, bandit, codespell, commitizen, pretty-format-yaml, pyright on manual stage)
- commitizen - Conventional commit enforcement (pre-commit `commitizen` and `commitizen-branch` hooks)
- python-semantic-release - Monorepo-aware release automation (`[tool.semantic_release]` in each package `pyproject.toml`; `commit_parser = "conventional-monorepo"`, tags `core-v{version}` / `app-v{version}`, scope prefixes `core-` / `app-`)
- Vite 8.2.x + `@sveltejs/vite-plugin-svelte` 7.x - Frontend bundler (`packages/lifx-emulator/frontend/vite.config.ts`)
- Zensical 0.0.37 + mkdocstrings-python 2.0.x + llmstxt-standalone 0.2.x - Documentation site build from `mkdocs.yml` (Material theme config) into `site/`
- PyApp 0.26.0 (Rust) - Produces standalone binaries for Linux x86_64, macOS x86_64/arm64, Windows x86_64 on GitHub release (`.github/workflows/release-binaries.yml`)

## Key Dependencies

- `pydantic>=2.0.0` - Only runtime validation layer; `EmulatorConfig` uses `extra="forbid"` so unknown config keys fail fast (`packages/lifx-emulator/src/lifx_emulator_app/config.py`)
- `pyyaml>=6.0.3` - Loads `specs.yml` product defaults (`products/specs.py`) and user config files (`config.py` via `yaml.safe_load`); also used by the code generators
- `fastapi>=0.115.0` - Entire management API surface; routers in `api/routers/` (`devices.py`, `monitoring.py`, `products.py`, `scenarios.py`, `websocket.py`)
- `cyclopts>=4.2.0` - CLI parsing including ordered parameter groups (`cyclopts.Group.create_ordered(...)` in `__main__.py`)
- `lifx-emulator-core>=2.4.0` - Workspace dependency of the app package (resolved from the workspace source, not PyPI, during development)
- `uvicorn>=0.34.0` - Serves FastAPI alongside the UDP server in one asyncio loop
- `websockets>=16.0` - Required so Uvicorn can upgrade `/ws` connections
- `rich>=14.2.0` - `RichHandler` logging output in `__main__.py`
- Stdlib only for protocol work: `struct` (`protocol/serializer.py`), `urllib.request.urlopen` (code generators only)
- `svelte ^5.55.7`, `@sveltejs/kit ^2.50.2`, `@sveltejs/adapter-static ^3.0.10`, `@sveltejs/adapter-auto ^7.0.0`, `@sveltejs/vite-plugin-svelte ^7.0.0`, `vite ^8.0.5`, `typescript ^6.0.0`, `svelte-check ^4.3.5`
- npm `overrides.cookie: ^0.7.0` pinned below 1.0 (SvelteKit needs the `parse`/`serialize` named exports; also enforced by `renovate.json` `allowedVersions: "<1.0.0"`)

## Configuration

- `LIFX_EMULATOR_CONFIG` - Path to YAML config file; resolution order is `--config` flag > env var > auto-detect `lifx-emulator.yaml` / `lifx-emulator.yml` in cwd (`resolve_config_path()` in `packages/lifx-emulator/src/lifx_emulator_app/config.py`)
- No other runtime environment variables are read by the application. A `.env` file exists at the repo root (git-ignored); its contents were not read.
- Config schema: `EmulatorConfig` (`bind`, `port`, `verbose`, `api`, `api_host`, `api_port`, `api_activity`, device counts `color`/`color_temperature`/`infrared`/`hev`/`multizone`/`tile`/`switch`, `multizone_extended`, `serial_prefix`, `serial_start`, `devices[]`, `scenarios`). Reference example: `lifx-emulator.example.yaml`.
- CLI args override config file values; defaults are UDP `127.0.0.1:56700` and API `127.0.0.1:8080`.
- Persistent storage directory: `~/.lifx-emulator/` (`DEFAULT_STORAGE_DIR` in `devices/persistence.py` and `scenarios/persistence.py`); `--persistent` / `--persistent-scenarios` flags are deprecated in favour of `lifx-emulator export-config`.
- `pyproject.toml` (root) - uv workspace, dev dependency group, Ruff/Pyright/pytest/coverage/bandit/codespell config
- `packages/lifx-emulator-core/pyproject.toml`, `packages/lifx-emulator/pyproject.toml` - Package metadata, hatchling build, per-package pytest/pyright overrides, semantic-release config
- `packages/lifx-emulator/frontend/package.json`, `svelte.config.js`, `vite.config.ts`, `tsconfig.json` - Frontend build
- `.pre-commit-config.yaml` - Hook definitions
- `mkdocs.yml` - Docs site (Zensical consumes it)
- `renovate.json` - Dependency update policy (Australia/Melbourne schedule, digest pinning for GitHub Actions, auto-merge for dev/test/code-quality groups, Python version updates disabled)
- `.gitattributes` - Marks `packets.py`, `products/registry.py`, and `api/static/_app/**` as `linguist-generated`

## Platform Requirements

- uv installed; `uv sync` installs both packages plus the `dev` group
- Python 3.10+ (CI uses 3.14 for the quality job, 3.11 for docs)
- Node.js + npm only when changing the frontend (`cd packages/lifx-emulator/frontend && npm install && npm run build`)
- Commands: `pytest`, `ruff check .`, `ruff format --check .`, `pyright`, `bandit -r packages/*/src/`
- Auto-generated files must be regenerated, not edited: `python -m lifx_emulator.protocol.generator` (fetches protocol.yml from GitHub) and `python -m lifx_emulator.products.generator` (fetches products.json from GitHub)
- Distributed as two PyPI packages (`lifx-emulator-core`, `lifx-emulator`) published via trusted publishing (`pypa/gh-action-pypi-publish`, `id-token: write`) in `.github/workflows/ci.yml`
- Standalone PyApp binaries attached to GitHub releases tagged `app-v*` (Linux x86_64, macOS x86_64, macOS arm64, Windows x86_64)
- Runs locally on the developer's machine; binds UDP 56700 and HTTP 8080 on loopback by default; no container or cloud deployment target
- OS independent (classifier `Operating System :: OS Independent`); CI tests Linux and macOS

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Use `snake_case.py` for all Python modules: `device_handlers.py`, `scenario_service.py`, `websocket_manager.py`.
- Split packet handlers by protocol namespace and packet-type range: `handlers/device_handlers.py` (2-59), `handlers/light_handlers.py` (101-149), `handlers/multizone_handlers.py` (501-512), `handlers/tile_handlers.py` (701-720).
- Name service-layer modules `<noun>_service.py` under `packages/lifx-emulator/src/lifx_emulator_app/api/services/`.
- Name FastAPI routers by resource under `packages/lifx-emulator/src/lifx_emulator_app/api/routers/` (`devices.py`, `scenarios.py`, `monitoring.py`, `products.py`, `websocket.py`).
- Frontend: Svelte 5 rune stores use `*.svelte.ts` (`frontend/src/lib/stores/devices.svelte.ts`); components use `PascalCase.svelte` (`frontend/src/lib/components/DeviceCard.svelte`); plain utilities use `camelCase.ts` (`frontend/src/lib/utils/api.ts`).
- Use `snake_case`. Prefix module-private helpers with a single underscore: `_get_packet_type_name()`, `_format_packet_fields()` in `packages/lifx-emulator-core/src/lifx_emulator/server.py`; `_save_state()`, `_should_handle_packet()` in `devices/device.py`; `_apply_config_scenarios()`, `_setup_logging()` in `lifx_emulator_app/__main__.py`.
- Factory functions use `create_<thing>()`: `create_color_light()`, `create_multizone_light()`, `create_tile_device()`, `create_device()` in `packages/lifx-emulator-core/src/lifx_emulator/factories.py`.
- Router factories use `create_<resource>_router(server)` and return an `APIRouter` (see `api/routers/devices.py`).
- Pydantic validators are named `validate_<field>` or `convert_<field>_<what>` and decorated `@field_validator(...)` + `@classmethod` (see `lifx_emulator_app/config.py`).
- `snake_case` for locals and attributes. Module-level constants are `UPPER_SNAKE_CASE`: `AUTO_DETECT_FILENAMES`, `ENV_VAR` (`config.py`); `LIFX_HEADER_SIZE`, `LIFX_UDP_PORT` (`lifx_emulator/constants.py`); `DEFAULT_STORAGE_DIR`, `STATE_CHANGING_PACKETS` (`lifx_emulator/devices/`).
- Module-private compiled regexes/constants take a leading underscore: `_SERIAL_PATTERN` in `config.py`.
- Module logger is always named `logger` (one exception: `_logger` in `__main__.py`). Use `logger`.
- Capability flags on `DeviceState` are `has_<capability>` booleans: `has_color`, `has_infrared`, `has_multizone`, `has_matrix`, `has_hev`, `has_relays`, `has_buttons`.
- Classes are `PascalCase`. Protocol interfaces take an `I` prefix: `IDeviceManager` (`devices/manager.py`), `IDeviceRepository`, `IDeviceStorageBackend`, `IScenarioStorageBackend` (`repositories/`). Decorate interfaces with `@runtime_checkable` on `typing.Protocol`.
- Handlers are `<PacketName>Handler(PacketHandler)` with a class attribute `PKT_TYPE = Device.<Packet>.PKT_TYPE` (`handlers/device_handlers.py`).
- Custom exceptions end in `Error` and subclass `Exception` directly: `DeviceNotFoundError`, `DeviceAlreadyExistsError`, `DeviceCreationError`, `DeviceStateUpdateError` (`api/services/device_service.py`); `ScenarioNotFoundError`, `InvalidDeviceSerialError` (`api/services/scenario_service.py`).
- Callback type aliases are `PascalCase` ending in `Callback`: `DeviceAddedCallback`, `DeviceRemovedCallback`, `StateChangeCallback`.
- State containers in the core library are `@dataclass` (`devices/states.py`, `protocol/header.py`, `devices/observers.py`). Anything that validates external input (YAML config, HTTP bodies, scenario definitions) is a Pydantic `BaseModel` (`lifx_emulator_app/config.py`, `api/models.py`, `lifx_emulator/scenarios/models.py`).
- Never use the term "wide tile device"; use "large matrix device" or "chained matrix device" (see fixture names in `packages/lifx-emulator-core/tests/conftest.py`).

## Code Style

- Ruff formatter (`ruff format`). Config in root `pyproject.toml` under `[tool.ruff]`/`[tool.ruff.format]`.
- Line length 88, 4-space indent, double quotes, `docstring-code-format = true`.
- Target Python 3.10 (`target-version = "py310"`, `requires-python = ">=3.10"`); CI tests 3.10 through 3.14 on Ubuntu and macOS (`.github/workflows/ci.yml`).
- Frontend: tabs, single quotes (see `frontend/src/lib/stores/devices.svelte.ts`); TypeScript `strict: true` in `frontend/tsconfig.json`; checked with `npm run check` (`svelte-check`). No ESLint/Prettier config present.
- Ruff with `select = ["E", "F", "I", "N", "W", "UP"]`, no ignores.
- McCabe `max-complexity = 10` -- every function must stay at or under 10. When a function grows, extract private `_helper()` functions rather than adding a `# noqa`.
- Pylint limits configured: `max-args = 5`, `max-branches = 12`, `max-statements = 50`.
- Per-file `E501` ignores only for auto-generated files (`protocol/generator.py`, `protocol/packets.py`, `protocol/protocol_types.py`).
- Type checking: Pyright `standard` mode over `packages/*/src` (root `pyproject.toml` `[tool.pyright]`; each package repeats it for `src`). Annotate all function signatures and public APIs.
- Suppressions are effectively banned by convention: exactly one `# type: ignore[misc]` exists in non-generated code (`protocol/base.py:283`). Zero `# noqa`, zero `TODO`/`FIXME`.
- Security: Bandit runs in pre-commit and CI (`bandit -r packages/*/src`). Spelling: codespell with ignore list `ommit,ser,nd,hass`.
- Pre-commit (`.pre-commit-config.yaml`, run via `prek`): trailing whitespace, EOF fixer, YAML/TOML/JSON checks, `detect-private-key`, `check-docstring-first`, `debug-statements`, `name-tests-test --pytest-test-first`, commitizen (conventional commits), `uv-lock`, `ruff-format`, `ruff --fix --exit-non-zero-on-fix`, bandit, codespell, `pretty-format-yaml --indent 2`. Pyright is a `manual` stage hook but runs in CI.
- Commits: conventional-commit messages enforced by commitizen; python-semantic-release uses `conventional-monorepo` parser with scope prefixes `core-` and `app-` (per-package `pyproject.toml`). Commit with `git commit -s`.

## Import Organization

- Python: none; always absolute package imports (`lifx_emulator.*`, `lifx_emulator_app.*`). Never relative imports.
- Frontend: SvelteKit `$lib` alias (`import type { Device } from '$lib/types'`).

## Error Handling

- Core library: validate arguments and `raise ValueError(...)` with an f-string message. Example from `handlers/registry.py`:
- Pydantic validators: assign the message to `msg` first, then `raise ValueError(msg)` (`lifx_emulator_app/config.py`):
- Service layer (app): define domain exceptions per service module, carry the identifying field as an attribute, and build the message in `__init__` (`api/services/device_service.py`):
- Routers: catch service exceptions and translate to `HTTPException` with `detail=str(e)`; 404 for not-found, 400 for validation/capability errors, 409 for already-exists (`api/routers/devices.py`):
- Network boundary: the UDP server must never crash on bad input. `server.py` wraps per-packet work in `except Exception as e`, increments `self.error_count`, and logs with `exc_info=True`; a malformed payload is logged at `warning` and the packet is skipped. Packets shorter than the header are ignored with a warning, not raised.
- CLI (`__main__.py`): catch narrow exceptions where possible (`ValueError`, `FileNotFoundError`, `json.JSONDecodeError`, `OSError`), `logger.error(...)` a human-readable message, then continue or exit. Broad `except Exception` is reserved for per-device restore loops so one bad device does not abort startup.
- Switch devices return `StateUnhandled` (type 223) rather than raising for Light/MultiZone/Tile packets.
- Return values, not exceptions, signal expected misses: `get_device()` returns `None`, `add_device()`/`remove_device()` return `bool`, `remove_all_devices()` returns a count (`devices/manager.py`).

## Logging

- Use `%s`-style lazy formatting, never f-strings, in log calls (75 `%`-style vs 3 f-string occurrences; the f-strings in `handlers/registry.py` are the outliers -- do not copy them):
- Levels: `debug` for per-packet detail and handler registration; `info` for state changes, startup, device creation, shutdown; `warning` for recoverable oddities (short packets, replaced handlers, no devices configured); `error` for failures with `exc_info=True` when a traceback is useful.
- The core library never calls `print()`. `print()` is used only in the CLI entry point `lifx_emulator_app/__main__.py` (23 uses, e.g. `list_products`) for user-facing console output; `rich` is available for tables.
- `_setup_logging(verbose)` in `__main__.py` calls `logging.basicConfig` with `DEBUG` when `--verbose`, otherwise `INFO`.
- Packet activity for the dashboard flows through the observer abstraction (`ActivityObserver`, `ActivityLogger`, `NullObserver`, `PacketEvent` in `devices/observers.py`), not ad-hoc log parsing.

## Comments

- Comment the *why* of protocol quirks and non-obvious wire behaviour, inline, directly above the affected statement. Example from `handlers/device_handlers.py`:
- Annotate magic protocol numbers with the packet name: `pkt_type=2,  # GetService`, `drop_packets={101: 1.0},  # Drop LightGet packets`.
- Do not leave `TODO`/`FIXME` markers (there are none). Open an issue or fix it.
- Use Australian English in prose and comments (`behaviour`, `honoured`, `initialise`) -- see `handlers/device_handlers.py`.
- Every module starts with a one-line (or short paragraph) module docstring; `check-docstring-first` pre-commit hook enforces docstring-before-code.
- Every public class and function has a Google-style docstring with `Args:`, `Returns:`, `Raises:`, and optionally `Note:`/`Example:` sections (`handlers/registry.py`, `devices/manager.py`):
- Handler classes use a one-line docstring naming the request and response packet with type numbers: `"""Handle DeviceSetPower (21) -> DeviceStatePower (22)."""`.
- `handle()` methods on handlers omit docstrings (the class docstring covers them); everything else public is documented. Docstrings feed mkdocstrings (`mkdocs.yml`, `zensical`), so keep them accurate.
- Doctest-style examples in docstrings are formatted by Ruff (`docstring-code-format = true`).

## Function Design

- Maximum 5 positional/keyword arguments (`max-args = 5`). Beyond that, pass a dataclass/Pydantic model (e.g. `DeviceStateUpdate`, `ScenarioConfig`).
- Handler signature is fixed: `handle(self, device_state: DeviceState, packet: <PacketType> | None, res_required: bool) -> list[Any]`. Type `packet` as the concrete packet class for setters and `Any | None` for getters.
- Optional collaborators default to `None` and are typed `X | None` (PEP 604 unions; `UP` rules forbid `Optional[X]`). Use `list[...]`, `dict[...]`, `tuple[...]` builtins, not `typing.List`.
- Dependency injection through constructors: `DeviceManager(DeviceRepository())`, `EmulatedLifxServer(devices, device_manager, host, port)`, `DeviceService(server)`, `create_devices_router(server)`. Depend on Protocol interfaces (`IDeviceManager`, `IDeviceRepository`), not concrete classes, in type hints.
- Handlers return a `list` of packets (possibly empty), never `(header, packet)` tuples; `EmulatedLifxDevice.process_packet()` builds headers. Return `[]` when `res_required` is false on a setter.
- Lookups return `X | None`; mutations return `bool` or a count.
- Services return Pydantic response models (`DeviceInfo`, `PaginatedDeviceList`) built via mappers in `api/mappers/`, so routers pass them straight through with `response_model=`.

## Module Design

- Each package/subpackage `__init__.py` declares an explicit `__all__` and re-exports the public surface (`lifx_emulator/__init__.py`, `lifx_emulator/devices/__init__.py`). Add new public symbols to the relevant `__all__`.
- `lifx_emulator/__init__.py` exposes `__version__` via `importlib.metadata.version("lifx-emulator-core")` -- do not hard-code versions in source.
- Leaf modules keep a single responsibility: one `*_service.py` per resource, one router per resource, one handler module per protocol namespace.
- Python: `__init__.py` files act as barrels (`lifx_emulator.devices`, `lifx_emulator.scenarios`, `lifx_emulator.repositories`, `lifx_emulator_app.api`, `lifx_emulator_app.api.services`). Consumers import from the barrel.
- Frontend: `frontend/src/lib/index.ts`, `lib/stores/index.ts`, `lib/components/index.ts` re-export stores and components.
- `lifx_emulator` (core) never imports `lifx_emulator_app`.
- `api/services/*` never import FastAPI; `api/routers/*` never touch `server.device_manager` directly -- they call a service.
- Auto-generated files are never hand-edited: `protocol/packets.py` (`python -m lifx_emulator.protocol.generator`) and `products/registry.py` (`python -m lifx_emulator.products.generator`). `protocol/protocol_types.py` is also generator-maintained.
- The Svelte build writes into `packages/lifx-emulator/src/lifx_emulator_app/api/static/` (`frontend/svelte.config.js`); treat that directory as a build artefact and edit only `frontend/src/`.
- Core I/O is `asyncio` (DatagramProtocol server, async file persistence with debouncing). Services that persist are `async def` and `await server.scenario_persistence.save(...)`; pure getters stay synchronous (`api/services/scenario_service.py`).
- Fire-and-forget save tasks are tracked (`_track_save_task()` in `devices/device.py`) so they can be awaited on shutdown.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

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

- Core library (`lifx_emulator`) has no web dependencies (only `pydantic`, `pyyaml`); app package (`lifx_emulator_app`) adds `cyclopts`, `fastapi`, `uvicorn`, `rich`, `websockets`.
- Every layer depends on `typing.Protocol` interfaces (`IDeviceManager`, `IDeviceRepository`, `IDeviceStorageBackend`, `IScenarioStorageBackend`, `ActivityObserver`), all `@runtime_checkable`.
- `EmulatedLifxServer` requires a `DeviceManager` as its second constructor argument (`server.py:92-104`); it never touches the repository directly.
- Handlers are stateless singletons instantiated once in module-level `ALL_*_HANDLERS` lists and return **packet objects**, never headers; `EmulatedLifxDevice.process_packet()` builds headers (`device.py:218`).
- Scenario behaviour is applied in two places by design: drops and ack fast-path in the server (`server.py:249-264`), capability filtering, partial responses, malformed/invalid-field mutation and `send_unhandled` in the device (`device.py:281-460`).
- Performance-motivated choices are explicit: pre-allocated response header template (`device.py:99-107`), cached resolved scenario per device (`device.py:189`), `loop.call_soon(loop.create_task, ...)` scheduling (`server.py:175`), pre-packed payload reuse.
- Protocol packet classes and product registry are **generated** (`protocol/generator.py`, `products/generator.py`) from upstream LIFX YAML/JSON; never hand-edit `packets.py` or `registry.py`.

## Layers

- Purpose: UDP transport; decode header + payload; route to devices; encode and send responses; keep stats.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/server.py`
- Contains: `EmulatedLifxServer`, nested `LifxProtocol`, logging helpers `_get_packet_type_name`, `_format_packet_fields`.
- Depends on: `IDeviceManager`, `LifxHeader`, `get_packet_class`, `HierarchicalScenarioManager`, `ActivityObserver`, `IScenarioStorageBackend`.
- Used by: CLI `__main__.py:1070`, API services (via `server` reference), library consumers, tests.
- Purpose: Device lifecycle, packet semantics, state mutation, scenario resolution.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/devices/`, `handlers/`, `scenarios/`
- Contains: `DeviceManager`, `EmulatedLifxDevice`, `DeviceState` and sub-states, `PacketHandler` subclasses, `HandlerRegistry`, `HierarchicalScenarioManager`, `ScenarioConfig`.
- Depends on: `protocol/` (packets, types, header), `repositories/` interfaces, `constants.py`.
- Used by: Network layer, factories, app services.
- Purpose: Abstract storage of live devices and persisted state/scenarios behind Protocols.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/repositories/`
- Contains: `IDeviceRepository`, `DeviceRepository` (in-memory), `IDeviceStorageBackend`, `IScenarioStorageBackend`.
- Depends on: `EmulatedLifxDevice` (type only).
- Used by: `DeviceManager`, `EmulatedLifxServer` (scenario storage), CLI wiring.
- Purpose: Concrete async file backends implementing the storage Protocols.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`, `scenarios/persistence.py`
- Contains: `DevicePersistenceAsyncFile` (per-device debounce 100 ms, batch threshold 50, single-thread `ThreadPoolExecutor`), `ScenarioPersistenceAsyncFile`.
- Depends on: `state_serializer.py`, `HierarchicalScenarioManager`.
- Used by: `EmulatedLifxDevice._save_state()` (`device.py:160`), `DeviceBuilder.build()` via `StateRestorer` (`builder.py:333-336`), CLI.
- Purpose: Wire format for the LIFX LAN protocol.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/protocol/`
- Contains: `header.py` (`LifxHeader`, `_HEADER_STRUCT = "<HHI Q6sBB QHH"`), `base.py` (`Packet` with `_fields` metadata), `serializer.py`, `protocol_types.py` (`LightHsbk`, `TileStateDevice`, enums), `packets.py` (generated), `const.py`, `generator.py`.
- Depends on: `constants.py` only.
- Used by: Everything above.
- Purpose: Turn a product ID into a fully configured device.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/products/`, `factories/`
- Contains: `ProductRegistry`/`ProductInfo`/`ProductCapability` (generated), `SpecsRegistry` loading `specs.yml`, `DeviceBuilder`, `SerialGenerator`, `DefaultColorConfig`, `FirmwareConfig`, `create_*` functions.
- Depends on: Domain layer (`DeviceState`, `EmulatedLifxDevice`), persistence (`StateRestorer`).
- Used by: CLI, `DeviceService`, tests, library consumers.
- Purpose: CLI, HTTP management API, WebSocket streaming, embedded dashboard.
- Location: `packages/lifx-emulator/src/lifx_emulator_app/`
- Contains: `__main__.py` (cyclopts `app` with `run` default plus `list_products`, `clear_storage`, `export_config`), `config.py`, `api/app.py`, `api/routers/`, `api/services/`, `api/mappers/`, `api/models.py`, `api/static/` (built Svelte output).
- Depends on: Core library public exports.
- Used by: End users via `lifx-emulator` console script; browser via `/`.
- Purpose: Real-time dashboard (Visualizer, Devices, Activity, Scenarios tabs).
- Location: `packages/lifx-emulator/frontend/src/`
- Contains: `routes/+page.svelte`, `lib/components/*.svelte`, `lib/stores/*.svelte.ts` (Svelte 5 runes), `lib/utils/api.ts` (REST calls), `lib/utils/color.ts`, `lib/types.ts`.
- Depends on: `/api/*` REST and `/ws` WebSocket.
- Used by: Browser; built into `api/static/` via `@sveltejs/adapter-static` (`frontend/svelte.config.js`).

## Data Flow

### Primary Request Path (UDP packet in → response out)

### Device Creation via HTTP API

### Scenario Update via HTTP API

### State Persistence

### Real-Time Dashboard Flow

- Live device state lives only in `DeviceState` instances held by `DeviceRepository` (single process, in-memory).
- Scenario state lives in one shared `HierarchicalScenarioManager` (`server.scenario_manager`); devices cache the merged result until invalidated.
- Server statistics are plain counters on `EmulatedLifxServer` (`server.py:140-146`).
- Frontend state lives in Svelte 5 rune stores under `frontend/src/lib/stores/`, hydrated exclusively from the WebSocket `sync` message and subsequent events; REST is used only for mutations (`frontend/src/lib/utils/api.ts`).

## Key Abstractions

- Purpose: Encapsulate one packet type's semantics against a `DeviceState`.
- Examples: `GetServiceHandler` (`handlers/device_handlers.py:19`), `SetColorHandler` (`handlers/light_handlers.py:116`), `Set64Handler` (`handlers/tile_handlers.py:198`), `ExtendedGetColorZonesHandler` (`handlers/multizone_handlers.py:116`).
- Pattern: Class attribute `PKT_TYPE = <Namespace>.<Packet>.PKT_TYPE`; `handle(device_state, packet, res_required) -> list[Any]`; append instance to the module's `ALL_*_HANDLERS`; `create_default_registry()` in `handlers/__init__.py` registers all lists.
- Purpose: Single façade over focused sub-state dataclasses; optional sub-states return defaults from `_OPTIONAL_DEFAULTS` when absent.
- Examples: `state.zone_colors` → `state.multizone.zone_colors`; `state.tile_devices` → `state.matrix.tile_devices`; `state.location_label` → `state.location.location_label`.
- Pattern: `__getattr__`/`__setattr__` consult `_ATTRIBUTE_ROUTES` (`devices/states.py:263-354, 363-466`). Adding a field means adding it to the sub-state **and** the routing table.
- Purpose: Fault-injection configuration with 5 scope levels.
- Examples: `scenarios/manager.py`, `scenarios/models.py` (Pydantic; `drop_packets: dict[int, float]`, `response_delays`, `malformed_packets`, `invalid_field_values`, `partial_responses`, `firmware_version`, `send_unhandled`, `affects_acks` property).
- Pattern: Device type string from `get_device_type()` (`matrix` > `extended_multizone` > `multizone` > `hev` > `infrared` > `color` > `basic`).
- Purpose: Allow substitution of manager, repository, storage and observer implementations.
- Examples: `IDeviceManager` (`devices/manager.py:27`), `IDeviceRepository` (`repositories/device_repository.py:15`), `IDeviceStorageBackend`/`IScenarioStorageBackend` (`repositories/storage_backend.py`), `ActivityObserver` (`devices/observers.py:37`).
- Pattern: Constructor injection; `EmulatedLifxServer(devices, device_manager, ...)`.
- Purpose: Deterministic composition of a device from `ProductInfo` + `specs.yml` + fluent overrides.
- Examples: `factories/builder.py:67`, `factories/factory.py:189` (`create_device`), typed wrappers `create_color_light` (PID 91), `create_multizone_light`, `create_tile_device`, `create_switch`.
- Pattern: `with_*()` chain then `build()`; delegates serial/colour/firmware decisions to `SerialGenerator`, `DefaultColorConfig`, `FirmwareConfig`.
- Purpose: Declarative binary layout; `pack()`/`unpack()`/`as_dict()`; `PKT_TYPE`; `get_packet_class(pkt_type)`.
- Examples: `protocol/packets.py` (`Device.StateService`, `Light.StateColor`, `MultiZone.ExtendedStateMultiZone`, `Tile.State64`, `Device.StateUnhandled`).
- Pattern: Regenerate with `python -m lifx_emulator.protocol.generator`; never edit by hand.
- Purpose: Keep FastAPI handlers thin; put logic in services that raise typed exceptions mapped to HTTP codes in routers.
- Examples: `create_devices_router(server)` (`api/routers/devices.py:28`), `DeviceService` (`api/services/device_service.py:60`), `ScenarioService` (`api/services/scenario_service.py:52`), exceptions `DeviceNotFoundError`, `DeviceAlreadyExistsError`, `ScenarioNotFoundError`, `InvalidDeviceSerialError`.
- Pattern: `create_<name>_router(...) -> APIRouter` closure capturing `server`/`ws_manager`; included in `create_api_app`.
- Purpose: Core library callbacks are synchronous; the bridge schedules WebSocket coroutines with `_schedule_async` (`event_bridge.py:30`).
- Examples: `wire_device_events`, `wire_device_state_events` (wraps existing `on_device_added` so new devices get `on_state_changed`), `WebSocketActivityObserver` (decorator over `ActivityLogger`).

## Entry Points

- Location: `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (`main()` at line 1147 → `cyclopts.App`; default command `run` at line 580)
- Triggers: User CLI invocation; `[project.scripts]` in `packages/lifx-emulator/pyproject.toml`.
- Responsibilities: Resolve config (`--config` > `LIFX_EMULATOR_CONFIG` > `lifx-emulator.yaml` in cwd, `config.py:234`), merge CLI over config, create devices, build `DeviceRepository` → `DeviceManager` → `EmulatedLifxServer` (`__main__.py:1052-1080`), optionally start `run_api_server` as a task (`__main__.py:1086-1089`), install SIGINT/SIGTERM/SIGBREAK handlers, shut down storage and server.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/__init__.py` (exports `EmulatedLifxServer`, `EmulatedLifxDevice`, `create_*`), plus sub-package `__init__.py` files.
- Triggers: `import lifx_emulator` in test suites of LIFX client libraries.
- Responsibilities: Construct devices, run server as async context manager (`server.py:527-535`).
- Location: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:45` (`create_api_app`), `:238` (`run_api_server`)
- Triggers: `--api` flag from CLI; direct use by tests (`packages/lifx-emulator/tests/test_api.py`).
- Responsibilities: Serve dashboard at `/`, static under `/_app` and `/static`, REST under `/api/*`, WebSocket at `/ws`, OpenAPI at `/docs`.
- Location: `EmulatedLifxServer.start()` (`server.py:515`) binding `bind_address:port` (default `127.0.0.1:56700`).
- Triggers: LIFX client discovery/broadcast and targeted packets.
- Location: `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py`, `products/generator.py`
- Triggers: Manual `python -m lifx_emulator.protocol.generator` / `python -m lifx_emulator.products.generator` when upstream LIFX specs change.
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

### Reading `device.state.<capability_field>` without checking the capability flag

### Bypassing `DeviceManager` to mutate the repository or device list

### Mutating scenarios without invalidating caches

### Blocking I/O or `time.sleep` inside handlers or the server path

### Hand-editing generated protocol or product files

## Error Handling

- `handle_packet` wraps everything in `try/except Exception`, increments `error_count` and logs with `exc_info=True` (`server.py:419-421`); payload unpack failures log a warning with hex dump and drop the packet (`server.py:333-347`).
- Unknown packet types are logged and still routed; devices reply `StateUnhandled` when `send_unhandled` is true (`device.py:449-460`).
- Lifecycle and state-change callbacks are wrapped in `try/except` with `logger.exception` (`manager.py:164-168`, `device.py:441-448`).
- Services raise domain exceptions (`DeviceNotFoundError`, `DeviceAlreadyExistsError`, `DeviceCreationError`, `DeviceStateUpdateError`, `ScenarioNotFoundError`, `InvalidDeviceSerialError`); routers translate to `HTTPException` 404/409/400/500 (`api/routers/devices.py`, `api/routers/scenarios.py`).
- Pydantic validation guards inputs: `EmulatorConfig` uses `extra="forbid"`, `DeviceCreateRequest.validate_serial_format`, `HsbkConfig` uint16/kelvin validators (`config.py`, `api/models.py`).
- Constructor invariants raise `ValueError` early (e.g. `persist_scenarios=True` without storage/manager, `server.py:111-121`; unknown product ID, `factory.py:245-246`).
- CLI logs errors and returns instead of raising for user-facing failures (`__main__.py:1023-1027`, `1029-1039`).

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
