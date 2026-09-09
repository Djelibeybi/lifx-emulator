# Technology Stack

**Analysis Date:** 2026-09-09

## Languages

**Primary:**
- Python >=3.10 (tested 3.10 through 3.14 in CI) - Core library (`packages/lifx-emulator-core/src/lifx_emulator/`) and standalone CLI/API app (`packages/lifx-emulator/src/lifx_emulator_app/`). Ruff and Pyright target `py310`.

**Secondary:**
- TypeScript 6.0.x (strict mode) - Web dashboard frontend in `packages/lifx-emulator/frontend/src/` (Svelte 5 runes-based stores `*.svelte.ts`, utilities, types)
- Svelte 5.57.x - UI components in `packages/lifx-emulator/frontend/src/lib/components/*.svelte`
- YAML - Product specs (`packages/lifx-emulator-core/src/lifx_emulator/products/specs.yml`), emulator config files (`lifx-emulator.example.yaml`), CI and docs config
- Rust - Not present in the repository source. The `stable` Rust toolchain is used only in CI (`.github/workflows/release-binaries.yml`) to compile PyApp (`ofek/pyapp` v0.26.0) into self-contained platform binaries. There is no `Cargo.toml` in this repo.

## Runtime

**Environment:**
- CPython 3.10+ (asyncio event loop; UDP via `asyncio.DatagramProtocol` in `packages/lifx-emulator-core/src/lifx_emulator/server.py`)
- CI matrix: Python 3.10, 3.11, 3.12, 3.13, 3.14 on `ubuntu-latest` and `macos-latest` (`.github/workflows/ci.yml`)
- Node.js (version unpinned; no `.nvmrc`) - only required to rebuild the frontend; the built output is committed to `packages/lifx-emulator/src/lifx_emulator_app/api/static/`

**Package Manager:**
- uv (workspace mode; CI pins `UV_VERSION: 0.9.9` in `ci.yml`, `0.11.8` in `docs.yml`)
- Lockfile: present (`uv.lock` at repo root, single lock for the whole workspace)
- npm for the frontend - Lockfile: present (`packages/lifx-emulator/frontend/package-lock.json`)
- Workspace definition: `pyproject.toml` at root (`[tool.uv.workspace] members = ["packages/*"]`, `lifx-emulator-core = { workspace = true }`)

## Frameworks

**Core:**
- asyncio (stdlib) - UDP server (`EmulatedLifxServer`), debounced async file persistence (`devices/persistence.py`, `scenarios/persistence.py`)
- Pydantic 2.12.x (`>=2.0.0`) - Config models in `packages/lifx-emulator/src/lifx_emulator_app/config.py`; API request/response models in `packages/lifx-emulator/src/lifx_emulator_app/api/models.py`; scenario models in `packages/lifx-emulator-core/src/lifx_emulator/scenarios/models.py`
- FastAPI 0.135.x (`>=0.115.0`) - HTTP management API and WebSocket endpoint; app factory `create_api_app()` in `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`
- Uvicorn 0.44.x (`>=0.34.0`) - ASGI server; `run_api_server()` in `api/app.py` builds `uvicorn.Config`/`uvicorn.Server` and awaits `serve()` inside the existing event loop
- websockets 16.0 (`>=16.0`) - WebSocket transport backend for Uvicorn (`/ws` endpoint in `api/routers/websocket.py`)
- cyclopts 4.10.x (`>=4.2.0`) - CLI framework; entry point `lifx_emulator_app.__main__:main` in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` (commands: `run`, `list-products`, `clear-storage`, `export-config`)
- SvelteKit 2.70.x with `@sveltejs/adapter-static` 3.0.x - Frontend, statically exported into the FastAPI package (`packages/lifx-emulator/frontend/svelte.config.js` writes `pages`/`assets` to `../src/lifx_emulator_app/api/static` with `fallback: 'index.html'`)

**Testing:**
- pytest 9.0.x (`>=8.4.2`) - Config in root `pyproject.toml` `[tool.pytest.ini_options]`; `testpaths` covers both packages' `tests/` dirs
- pytest-asyncio 1.3.x - `asyncio_mode = "auto"`, function-scoped loops
- pytest-cov 7.1.x - Branch coverage, XML + terminal reports; CI enforces `--cov-fail-under=80`
- pytest-sugar 1.1.x - Output formatting
- httpx 0.28.x - Used by FastAPI `TestClient` in `packages/lifx-emulator/tests/test_api.py`, `test_websocket.py`, `test_cli_validation.py`
- svelte-check 4.3.x - Frontend type checking (`npm run check`)

**Build/Dev:**
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

**Critical:**
- `pydantic>=2.0.0` - Only runtime validation layer; `EmulatorConfig` uses `extra="forbid"` so unknown config keys fail fast (`packages/lifx-emulator/src/lifx_emulator_app/config.py`)
- `pyyaml>=6.0.3` - Loads `specs.yml` product defaults (`products/specs.py`) and user config files (`config.py` via `yaml.safe_load`); also used by the code generators
- `fastapi>=0.115.0` - Entire management API surface; routers in `api/routers/` (`devices.py`, `monitoring.py`, `products.py`, `scenarios.py`, `websocket.py`)
- `cyclopts>=4.2.0` - CLI parsing including ordered parameter groups (`cyclopts.Group.create_ordered(...)` in `__main__.py`)
- `lifx-emulator-core>=2.4.0` - Workspace dependency of the app package (resolved from the workspace source, not PyPI, during development)

**Infrastructure:**
- `uvicorn>=0.34.0` - Serves FastAPI alongside the UDP server in one asyncio loop
- `websockets>=16.0` - Required so Uvicorn can upgrade `/ws` connections
- `rich>=14.2.0` - `RichHandler` logging output in `__main__.py`
- Stdlib only for protocol work: `struct` (`protocol/serializer.py`), `urllib.request.urlopen` (code generators only)

**Frontend (dev-only, all built assets committed):**
- `svelte ^5.55.7`, `@sveltejs/kit ^2.50.2`, `@sveltejs/adapter-static ^3.0.10`, `@sveltejs/adapter-auto ^7.0.0`, `@sveltejs/vite-plugin-svelte ^7.0.0`, `vite ^8.0.5`, `typescript ^6.0.0`, `svelte-check ^4.3.5`
- npm `overrides.cookie: ^0.7.0` pinned below 1.0 (SvelteKit needs the `parse`/`serialize` named exports; also enforced by `renovate.json` `allowedVersions: "<1.0.0"`)

## Configuration

**Environment:**
- `LIFX_EMULATOR_CONFIG` - Path to YAML config file; resolution order is `--config` flag > env var > auto-detect `lifx-emulator.yaml` / `lifx-emulator.yml` in cwd (`resolve_config_path()` in `packages/lifx-emulator/src/lifx_emulator_app/config.py`)
- No other runtime environment variables are read by the application. A `.env` file exists at the repo root (git-ignored); its contents were not read.
- Config schema: `EmulatorConfig` (`bind`, `port`, `verbose`, `api`, `api_host`, `api_port`, `api_activity`, device counts `color`/`color_temperature`/`infrared`/`hev`/`multizone`/`tile`/`switch`, `multizone_extended`, `serial_prefix`, `serial_start`, `devices[]`, `scenarios`). Reference example: `lifx-emulator.example.yaml`.
- CLI args override config file values; defaults are UDP `127.0.0.1:56700` and API `127.0.0.1:8080`.
- Persistent storage directory: `~/.lifx-emulator/` (`DEFAULT_STORAGE_DIR` in `devices/persistence.py` and `scenarios/persistence.py`); `--persistent` / `--persistent-scenarios` flags are deprecated in favour of `lifx-emulator export-config`.

**Build:**
- `pyproject.toml` (root) - uv workspace, dev dependency group, Ruff/Pyright/pytest/coverage/bandit/codespell config
- `packages/lifx-emulator-core/pyproject.toml`, `packages/lifx-emulator/pyproject.toml` - Package metadata, hatchling build, per-package pytest/pyright overrides, semantic-release config
- `packages/lifx-emulator/frontend/package.json`, `svelte.config.js`, `vite.config.ts`, `tsconfig.json` - Frontend build
- `.pre-commit-config.yaml` - Hook definitions
- `mkdocs.yml` - Docs site (Zensical consumes it)
- `renovate.json` - Dependency update policy (Australia/Melbourne schedule, digest pinning for GitHub Actions, auto-merge for dev/test/code-quality groups, Python version updates disabled)
- `.gitattributes` - Marks `packets.py`, `products/registry.py`, and `api/static/_app/**` as `linguist-generated`

## Platform Requirements

**Development:**
- uv installed; `uv sync` installs both packages plus the `dev` group
- Python 3.10+ (CI uses 3.14 for the quality job, 3.11 for docs)
- Node.js + npm only when changing the frontend (`cd packages/lifx-emulator/frontend && npm install && npm run build`)
- Commands: `pytest`, `ruff check .`, `ruff format --check .`, `pyright`, `bandit -r packages/*/src/`
- Auto-generated files must be regenerated, not edited: `python -m lifx_emulator.protocol.generator` (fetches protocol.yml from GitHub) and `python -m lifx_emulator.products.generator` (fetches products.json from GitHub)

**Production:**
- Distributed as two PyPI packages (`lifx-emulator-core`, `lifx-emulator`) published via trusted publishing (`pypa/gh-action-pypi-publish`, `id-token: write`) in `.github/workflows/ci.yml`
- Standalone PyApp binaries attached to GitHub releases tagged `app-v*` (Linux x86_64, macOS x86_64, macOS arm64, Windows x86_64)
- Runs locally on the developer's machine; binds UDP 56700 and HTTP 8080 on loopback by default; no container or cloud deployment target
- OS independent (classifier `Operating System :: OS Independent`); CI tests Linux and macOS

---

*Stack analysis: 2026-09-09*
