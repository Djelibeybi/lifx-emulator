# External Integrations

**Analysis Date:** 2026-09-09

## APIs & External Services

**LIFX upstream specifications (build-time only, not runtime):**
- LIFX public protocol definition - Source for the auto-generated packet classes
  - URL: `PROTOCOL_URL` in `packages/lifx-emulator-core/src/lifx_emulator/constants.py` (also duplicated in `protocol/const.py`) pointing at `LIFX/public-protocol` `protocol.yml` on raw.githubusercontent.com
  - Client: stdlib `urllib.request.urlopen` in `packages/lifx-emulator-core/src/lifx_emulator/protocol/generator.py` (`download_protocol()`)
  - Output: `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py` (do not edit; regenerate with `python -m lifx_emulator.protocol.generator`)
  - Auth: None (public repository)
- LIFX products registry - Source for the auto-generated product catalogue
  - URL: `PRODUCTS_URL` in `constants.py` pointing at `LIFX/products` `products.json`
  - Client: `urllib.request.urlopen` in `packages/lifx-emulator-core/src/lifx_emulator/products/generator.py` (`download_products()`)
  - Output: `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py` (do not edit; regenerate with `python -m lifx_emulator.products.generator`)
  - Auth: None

**Runtime outbound HTTP calls:** None. The emulator makes no network requests at runtime other than replying to LIFX LAN UDP clients and serving its own HTTP/WebSocket API.

**Self-hosted API (inbound, provided by this project):**
- FastAPI management API - Created by `create_api_app()` in `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`, served by Uvicorn via `run_api_server()`
  - `GET /api/stats`, `GET /api/activity` - `api/routers/monitoring.py`
  - `GET /api/devices`, `GET /api/devices/{serial}`, `POST /api/devices`, `POST /api/devices/bulk`, `PATCH /api/devices/{serial}/state`, `DELETE /api/devices/{serial}`, `DELETE /api/devices` - `api/routers/devices.py`
  - `GET /api/products` - `api/routers/products.py`
  - `GET|PUT|DELETE /api/scenarios/global`, `/api/scenarios/devices/{serial}`, `/api/scenarios/types/{device_type}`, `/api/scenarios/locations/{location}`, `/api/scenarios/groups/{group}` - `api/routers/scenarios.py`
  - `WS /ws` - `api/routers/websocket.py`
  - `GET /` and `/_app/*` - Embedded Svelte dashboard served from `packages/lifx-emulator/src/lifx_emulator_app/api/static/` via `StaticFiles`/`FileResponse`
  - OpenAPI docs at `/docs` (Swagger) and `/redoc`
  - Auth: None (bound to `127.0.0.1` by default)

**LIFX LAN protocol (inbound UDP):**
- Binary UDP protocol on port 56700 (`LIFX_UDP_PORT` in `constants.py`) implemented by `EmulatedLifxServer` in `packages/lifx-emulator-core/src/lifx_emulator/server.py` using `asyncio.DatagramProtocol`
- This is the primary "integration" surface: external LIFX client libraries under test talk to the emulator as if it were real hardware

## Data Storage

**Databases:**
- None. No SQL/NoSQL database or ORM.

**File Storage:**
- Local filesystem only
  - Device state: one JSON file per device (`<serial>.json`) under `~/.lifx-emulator/` (`DEFAULT_STORAGE_DIR`), written atomically via `.json.tmp` rename with debounced batching in `DevicePersistenceAsyncFile` (`packages/lifx-emulator-core/src/lifx_emulator/devices/persistence.py`)
  - Scenarios: single `~/.lifx-emulator/scenarios.json` managed by `ScenarioPersistenceAsyncFile` (`packages/lifx-emulator-core/src/lifx_emulator/scenarios/persistence.py`)
  - Storage is abstracted behind `IDeviceStorageBackend` / `IScenarioStorageBackend` Protocols in `packages/lifx-emulator-core/src/lifx_emulator/repositories/storage_backend.py`; in-memory collection behind `IDeviceRepository` in `repositories/device_repository.py`
  - Persistence flags (`--persistent`, `--persistent-scenarios`) are deprecated; the preferred model is a YAML config file (`lifx-emulator export-config` in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`)
- Config file input: YAML (`lifx-emulator.yaml` / `.yml`) parsed with `yaml.safe_load` in `packages/lifx-emulator/src/lifx_emulator_app/config.py`

**Caching:**
- None external. In-process only: `HierarchicalScenarioManager` resolution cache (`packages/lifx-emulator-core/src/lifx_emulator/scenarios/manager.py`), invalidated by `ScenarioService` (`packages/lifx-emulator/src/lifx_emulator_app/api/services/scenario_service.py`)

## Authentication & Identity

**Auth Provider:**
- None. The HTTP API, WebSocket endpoint, and UDP server are unauthenticated.
  - Implementation: Relies on loopback binding by default (`bind` / `api_host` default `127.0.0.1`). Changing `api_host` to `0.0.0.0` exposes an unauthenticated control plane; this is a deliberate design for a local test tool.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or equivalent)

**Logs:**
- Python `logging` with `rich.logging.RichHandler` configured in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py`; `--verbose` raises the level
- Uvicorn access logging enabled (`access_log=True` in `run_api_server()` in `api/app.py`)
- In-app observability: `GET /api/stats` and `GET /api/activity`, plus a `StatsBroadcaster` that pushes server stats every second over WebSocket (`packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py`); device observers in `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py`

**Coverage/Test Reporting:**
- Codecov - Coverage (`coverage.xml`) and JUnit test results (`junit.xml`) uploaded from CI (`codecov/codecov-action` in `.github/workflows/ci.yml`, slug `Djelibeybi/lifx-emulator`); auth via `CODECOV_TOKEN` repository secret

## CI/CD & Deployment

**Hosting:**
- PyPI - `lifx-emulator-core` and `lifx-emulator` published with trusted publishing (`pypa/gh-action-pypi-publish`, environment `pypi`, `id-token: write`) in `.github/workflows/ci.yml`; CLI package deploys only after core succeeds
- GitHub Releases - Version tags `core-v*` / `app-v*` created by python-semantic-release; PyApp binaries for four targets attached by `.github/workflows/release-binaries.yml` (`softprops/action-gh-release`) on `app-v*` releases
- GitHub Pages - Documentation site (`https://djelibeybi.github.io/lifx-emulator`) built by Zensical from `mkdocs.yml` and deployed with `actions/deploy-pages` in `.github/workflows/docs.yml`; also runs `llmstxt-standalone validate` and `build`

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`):
  1. `changes` - `dorny/paths-filter` gates on `packages/**`, `pyproject.toml`, `uv.lock`
  2. `quality` - `ruff format --check`, `ruff check`, `pyright`, `bandit`
  3. `test` - Matrix (Ubuntu + macOS x Python 3.10-3.14), `pytest --cov-fail-under=80`, Codecov upload
  4. `release` - python-semantic-release per package (`--noop` on non-main branches; real release on `main`), checkout uses `DEPLOY_KEY` SSH secret so release commits can push
  5. `deploy-core` / `deploy-cli` - PyPI publish
- All third-party actions are pinned to commit digests (enforced by `renovate.json` `pinDigests: true`)
- Renovate - Dependency update bot (`renovate.json`); Melbourne-timezone schedule, auto-merge for dev/test/code-quality/GitHub Actions minor+patch, security alerts auto-merged, major updates require review by `Djelibeybi`, Python version updates disabled, custom regex manager for versions mentioned in `CLAUDE.md`
- pre-commit.ci - Configured in `.pre-commit-config.yaml` `ci:` block (weekly autoupdate, autofix PRs, skips `pyright`)

## Environment Configuration

**Required env vars:**
- None required at runtime.
- Optional: `LIFX_EMULATOR_CONFIG` - Absolute path to a YAML config file (`ENV_VAR` in `packages/lifx-emulator/src/lifx_emulator_app/config.py`)
- CI-only: `PYTHON_VERSION`, `UV_VERSION`, `PYAPP_VERSION`, `PYAPP_PROJECT_NAME`, `PYAPP_PROJECT_VERSION`, `PYAPP_PYTHON_VERSION`, `PYAPP_EXEC_SPEC`, `CARGO_BUILD_TARGET` (set inline in workflow files)

**Secrets location:**
- GitHub repository secrets only: `CODECOV_TOKEN`, `DEPLOY_KEY` (SSH deploy key for release pushes), `GITHUB_TOKEN` (automatic). PyPI uses OIDC trusted publishing; no PyPI token is stored.
- A `.env` file exists at the repo root and is git-ignored. It is not read by any application code (no `dotenv` dependency; only `os.environ.get("LIFX_EMULATOR_CONFIG")` is consulted). Contents were not inspected.
- `.claude/settings.local.json` is git-ignored local tooling config.

## Webhooks & Callbacks

**Incoming:**
- None (no webhook receivers). The only push-style inbound channel is the WebSocket at `/ws`, where clients send `{"type": "subscribe", "topics": [...]}` or `{"type": "sync"}` (`packages/lifx-emulator/src/lifx_emulator_app/api/routers/websocket.py`, connection lifecycle in `api/services/websocket_manager.py`)

**Outgoing:**
- None to external systems.
- Internal event fan-out: `WebSocketActivityObserver` and `WebSocketStateChangeObserver` in `api/services/event_bridge.py` bridge core device observer events (`lifx_emulator/devices/observers.py`) to WebSocket subscribers with message types `stats`, `device_added`, `device_removed`, `device_updated`, `activity`, `scenario_changed`. The Svelte dashboard consumes these in `packages/lifx-emulator/frontend/src/lib/stores/connection.svelte.ts` (URL derived from `window.location`, `ws:`/`wss:` selected by page protocol).
- The CLI can open the dashboard in the local browser via stdlib `webbrowser` (`packages/lifx-emulator/src/lifx_emulator_app/__main__.py`).

---

*Integration audit: 2026-09-09*
