# Tech Stack

## Languages

| Language | Version | Usage |
| --- | --- | --- |
| Python | 3.10+ (target), 3.12+ (dev) | Core library, CLI, API server |
| TypeScript | 5.9+ | Frontend UI |

## Package Structure

uv workspace monorepo with two Python packages:

| Package | PyPI Name | Import Name | Description |
| --- | --- | --- | --- |
| Library | `lifx-emulator-core` | `lifx_emulator` | Core emulator library |
| Standalone | `lifx-emulator` | `lifx_emulator_app` | CLI + HTTP management API |

## Frameworks

### Backend

- **FastAPI** — HTTP management API + WebSocket real-time updates
- **asyncio DatagramProtocol** — UDP transport for LIFX LAN protocol
- **cyclopts** — CLI argument parsing
- **Pydantic** — Config validation and API request/response models

### Frontend

- **SvelteKit 2** with **Svelte 5** (runes: `$state`, `$derived`, `$effect`, `$props`)
- **@sveltejs/adapter-static** — Builds to static files served by FastAPI
- **Vite 8** — Build tooling

## Database / Persistence

- No traditional database
- Async file-based persistence with debouncing for device state and scenarios
- Protocol interfaces (`IDeviceStorageBackend`, `IScenarioStorageBackend`) for storage abstraction

## Infrastructure / Distribution

- Published to **PyPI** as two packages (`lifx-emulator-core`, `lifx-emulator`)
- Users install and run locally: `pip install lifx-emulator` or `uv add lifx-emulator`
- Frontend is pre-built and bundled into the Python package as static files

## Key Dependencies

### Python

- `fastapi` + `uvicorn` — API server
- `pydantic` — Data validation
- `cyclopts` — CLI
- `pyyaml` — Config file parsing
- `pytest` + `pytest-asyncio` + `pytest-cov` — Testing

### Frontend

- `svelte` 5.x — UI framework
- `@sveltejs/kit` 2.x — Application framework
- `typescript` 5.x — Type safety

## Package Management

- **Python**: `uv` exclusively (never pip/poetry/conda)
- **Frontend**: `npm`
