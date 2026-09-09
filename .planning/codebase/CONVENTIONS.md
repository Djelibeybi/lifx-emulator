# Coding Conventions

**Analysis Date:** 2026-09-09

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `device_handlers.py`, `scenario_service.py`, `websocket_manager.py`.
- Split packet handlers by protocol namespace and packet-type range: `handlers/device_handlers.py` (2-59), `handlers/light_handlers.py` (101-149), `handlers/multizone_handlers.py` (501-512), `handlers/tile_handlers.py` (701-720).
- Name service-layer modules `<noun>_service.py` under `packages/lifx-emulator/src/lifx_emulator_app/api/services/`.
- Name FastAPI routers by resource under `packages/lifx-emulator/src/lifx_emulator_app/api/routers/` (`devices.py`, `scenarios.py`, `monitoring.py`, `products.py`, `websocket.py`).
- Frontend: Svelte 5 rune stores use `*.svelte.ts` (`frontend/src/lib/stores/devices.svelte.ts`); components use `PascalCase.svelte` (`frontend/src/lib/components/DeviceCard.svelte`); plain utilities use `camelCase.ts` (`frontend/src/lib/utils/api.ts`).

**Functions:**
- Use `snake_case`. Prefix module-private helpers with a single underscore: `_get_packet_type_name()`, `_format_packet_fields()` in `packages/lifx-emulator-core/src/lifx_emulator/server.py`; `_save_state()`, `_should_handle_packet()` in `devices/device.py`; `_apply_config_scenarios()`, `_setup_logging()` in `lifx_emulator_app/__main__.py`.
- Factory functions use `create_<thing>()`: `create_color_light()`, `create_multizone_light()`, `create_tile_device()`, `create_device()` in `packages/lifx-emulator-core/src/lifx_emulator/factories.py`.
- Router factories use `create_<resource>_router(server)` and return an `APIRouter` (see `api/routers/devices.py`).
- Pydantic validators are named `validate_<field>` or `convert_<field>_<what>` and decorated `@field_validator(...)` + `@classmethod` (see `lifx_emulator_app/config.py`).

**Variables:**
- `snake_case` for locals and attributes. Module-level constants are `UPPER_SNAKE_CASE`: `AUTO_DETECT_FILENAMES`, `ENV_VAR` (`config.py`); `LIFX_HEADER_SIZE`, `LIFX_UDP_PORT` (`lifx_emulator/constants.py`); `DEFAULT_STORAGE_DIR`, `STATE_CHANGING_PACKETS` (`lifx_emulator/devices/`).
- Module-private compiled regexes/constants take a leading underscore: `_SERIAL_PATTERN` in `config.py`.
- Module logger is always named `logger` (one exception: `_logger` in `__main__.py`). Use `logger`.
- Capability flags on `DeviceState` are `has_<capability>` booleans: `has_color`, `has_infrared`, `has_multizone`, `has_matrix`, `has_hev`, `has_relays`, `has_buttons`.

**Types:**
- Classes are `PascalCase`. Protocol interfaces take an `I` prefix: `IDeviceManager` (`devices/manager.py`), `IDeviceRepository`, `IDeviceStorageBackend`, `IScenarioStorageBackend` (`repositories/`). Decorate interfaces with `@runtime_checkable` on `typing.Protocol`.
- Handlers are `<PacketName>Handler(PacketHandler)` with a class attribute `PKT_TYPE = Device.<Packet>.PKT_TYPE` (`handlers/device_handlers.py`).
- Custom exceptions end in `Error` and subclass `Exception` directly: `DeviceNotFoundError`, `DeviceAlreadyExistsError`, `DeviceCreationError`, `DeviceStateUpdateError` (`api/services/device_service.py`); `ScenarioNotFoundError`, `InvalidDeviceSerialError` (`api/services/scenario_service.py`).
- Callback type aliases are `PascalCase` ending in `Callback`: `DeviceAddedCallback`, `DeviceRemovedCallback`, `StateChangeCallback`.
- State containers in the core library are `@dataclass` (`devices/states.py`, `protocol/header.py`, `devices/observers.py`). Anything that validates external input (YAML config, HTTP bodies, scenario definitions) is a Pydantic `BaseModel` (`lifx_emulator_app/config.py`, `api/models.py`, `lifx_emulator/scenarios/models.py`).
- Never use the term "wide tile device"; use "large matrix device" or "chained matrix device" (see fixture names in `packages/lifx-emulator-core/tests/conftest.py`).

## Code Style

**Formatting:**
- Ruff formatter (`ruff format`). Config in root `pyproject.toml` under `[tool.ruff]`/`[tool.ruff.format]`.
- Line length 88, 4-space indent, double quotes, `docstring-code-format = true`.
- Target Python 3.10 (`target-version = "py310"`, `requires-python = ">=3.10"`); CI tests 3.10 through 3.14 on Ubuntu and macOS (`.github/workflows/ci.yml`).
- Frontend: tabs, single quotes (see `frontend/src/lib/stores/devices.svelte.ts`); TypeScript `strict: true` in `frontend/tsconfig.json`; checked with `npm run check` (`svelte-check`). No ESLint/Prettier config present.

**Linting:**
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

**Order:**
1. `from __future__ import annotations` (present in 44 of 64 source modules -- add it to every new module).
2. Standard library (`asyncio`, `logging`, `time`, `collections.abc`, `typing`).
3. Third-party (`pydantic`, `fastapi`, `yaml`).
4. First-party, absolute: `from lifx_emulator.<pkg> import ...` then `from lifx_emulator_app.<pkg> import ...`.

Ruff isort (`I` rules) enforces the grouping. All imports go at the top of the file (`CONTRIBUTING.md`); the only sanctioned exception is inside test fixtures/tests (e.g. `device_with_scenarios` in `packages/lifx-emulator-core/tests/conftest.py`).

**Type-only imports:** wrap in `if TYPE_CHECKING:` to break cycles between layers. Real example from `handlers/device_handlers.py`:

```python
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, cast

from lifx_emulator.handlers.base import PacketHandler
from lifx_emulator.protocol.packets import Device
from lifx_emulator.protocol.protocol_types import DeviceService as ProtocolDeviceService

if TYPE_CHECKING:
    from lifx_emulator.devices import DeviceState

logger = logging.getLogger(__name__)
```

The app package does the same for core types it never instantiates (`api/services/device_service.py`, `api/routers/devices.py` import `EmulatedLifxServer` under `TYPE_CHECKING`).

**Path Aliases:**
- Python: none; always absolute package imports (`lifx_emulator.*`, `lifx_emulator_app.*`). Never relative imports.
- Frontend: SvelteKit `$lib` alias (`import type { Device } from '$lib/types'`).

**Public API surfaces:** every package `__init__.py` re-exports via explicit `__all__` (`lifx_emulator/__init__.py`, `lifx_emulator/devices/__init__.py`). Import from the subpackage, not the leaf module, in consuming code:

```python
from lifx_emulator.devices import EmulatedLifxDevice, DeviceState, DeviceManager
from lifx_emulator.scenarios import HierarchicalScenarioManager, ScenarioConfig
from lifx_emulator_app.api import create_api_app, run_api_server
```

## Error Handling

**Patterns:**
- Core library: validate arguments and `raise ValueError(...)` with an f-string message. Example from `handlers/registry.py`:

```python
if not hasattr(handler, "PKT_TYPE"):
    raise ValueError(
        f"Handler {handler.__class__.__name__} missing PKT_TYPE attribute"
    )
```

- Pydantic validators: assign the message to `msg` first, then `raise ValueError(msg)` (`lifx_emulator_app/config.py`):

```python
if not 0 <= v <= 65535:
    msg = "Value must be between 0 and 65535"
    raise ValueError(msg)
return v
```

- Service layer (app): define domain exceptions per service module, carry the identifying field as an attribute, and build the message in `__init__` (`api/services/device_service.py`):

```python
class DeviceNotFoundError(Exception):
    """Raised when a device with the specified serial is not found."""

    def __init__(self, serial: str):
        super().__init__(f"Device {serial} not found")
        self.serial = serial
```

- Routers: catch service exceptions and translate to `HTTPException` with `detail=str(e)`; 404 for not-found, 400 for validation/capability errors, 409 for already-exists (`api/routers/devices.py`):

```python
try:
    return device_service.update_device_state(serial, update)
except DeviceNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except DeviceStateUpdateError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

  Keep HTTP concerns out of services; services never import FastAPI.

- Network boundary: the UDP server must never crash on bad input. `server.py` wraps per-packet work in `except Exception as e`, increments `self.error_count`, and logs with `exc_info=True`; a malformed payload is logged at `warning` and the packet is skipped. Packets shorter than the header are ignored with a warning, not raised.
- CLI (`__main__.py`): catch narrow exceptions where possible (`ValueError`, `FileNotFoundError`, `json.JSONDecodeError`, `OSError`), `logger.error(...)` a human-readable message, then continue or exit. Broad `except Exception` is reserved for per-device restore loops so one bad device does not abort startup.
- Switch devices return `StateUnhandled` (type 223) rather than raising for Light/MultiZone/Tile packets.
- Return values, not exceptions, signal expected misses: `get_device()` returns `None`, `add_device()`/`remove_device()` return `bool`, `remove_all_devices()` returns a count (`devices/manager.py`).

## Logging

**Framework:** stdlib `logging`. Every module declares `logger = logging.getLogger(__name__)` immediately after imports.

**Patterns:**
- Use `%s`-style lazy formatting, never f-strings, in log calls (75 `%`-style vs 3 f-string occurrences; the f-strings in `handlers/registry.py` are the outliers -- do not copy them):

```python
logger.info("Power set to %s", device_state.power_level)
logger.debug("Sending %d StateService reply/replies: %s", len(services), services)
logger.error("Error handling packet from %s: %s", addr, e, exc_info=True)
```

- Levels: `debug` for per-packet detail and handler registration; `info` for state changes, startup, device creation, shutdown; `warning` for recoverable oddities (short packets, replaced handlers, no devices configured); `error` for failures with `exc_info=True` when a traceback is useful.
- The core library never calls `print()`. `print()` is used only in the CLI entry point `lifx_emulator_app/__main__.py` (23 uses, e.g. `list_products`) for user-facing console output; `rich` is available for tables.
- `_setup_logging(verbose)` in `__main__.py` calls `logging.basicConfig` with `DEBUG` when `--verbose`, otherwise `INFO`.
- Packet activity for the dashboard flows through the observer abstraction (`ActivityObserver`, `ActivityLogger`, `NullObserver`, `PacketEvent` in `devices/observers.py`), not ad-hoc log parsing.

## Comments

**When to Comment:**
- Comment the *why* of protocol quirks and non-obvious wire behaviour, inline, directly above the affected statement. Example from `handlers/device_handlers.py`:

```python
# service ids are passed through verbatim (raw uint8); values outside
# the DeviceService enum are emitted unchanged, never remapped.
```

- Annotate magic protocol numbers with the packet name: `pkt_type=2,  # GetService`, `drop_packets={101: 1.0},  # Drop LightGet packets`.
- Do not leave `TODO`/`FIXME` markers (there are none). Open an issue or fix it.
- Use Australian English in prose and comments (`behaviour`, `honoured`, `initialise`) -- see `handlers/device_handlers.py`.

**JSDoc/TSDoc (Python docstrings):**
- Every module starts with a one-line (or short paragraph) module docstring; `check-docstring-first` pre-commit hook enforces docstring-before-code.
- Every public class and function has a Google-style docstring with `Args:`, `Returns:`, `Raises:`, and optionally `Note:`/`Example:` sections (`handlers/registry.py`, `devices/manager.py`):

```python
def register(self, handler: PacketHandler) -> None:
    """Register a packet handler.

    Args:
        handler: Handler instance to register

    Raises:
        ValueError: If handler doesn't have PKT_TYPE attribute

    Note:
        If a handler for this packet type already exists, it will be replaced.
    """
```

- Handler classes use a one-line docstring naming the request and response packet with type numbers: `"""Handle DeviceSetPower (21) -> DeviceStatePower (22)."""`.
- `handle()` methods on handlers omit docstrings (the class docstring covers them); everything else public is documented. Docstrings feed mkdocstrings (`mkdocs.yml`, `zensical`), so keep them accurate.
- Doctest-style examples in docstrings are formatted by Ruff (`docstring-code-format = true`).

## Function Design

**Size:** McCabe complexity 10 hard limit, 50 statements, 12 branches (Ruff). Extract private helpers aggressively; `server.py` demonstrates `_get_packet_type_name()` and `_format_packet_fields()` split out of the packet path.

**Parameters:**
- Maximum 5 positional/keyword arguments (`max-args = 5`). Beyond that, pass a dataclass/Pydantic model (e.g. `DeviceStateUpdate`, `ScenarioConfig`).
- Handler signature is fixed: `handle(self, device_state: DeviceState, packet: <PacketType> | None, res_required: bool) -> list[Any]`. Type `packet` as the concrete packet class for setters and `Any | None` for getters.
- Optional collaborators default to `None` and are typed `X | None` (PEP 604 unions; `UP` rules forbid `Optional[X]`). Use `list[...]`, `dict[...]`, `tuple[...]` builtins, not `typing.List`.
- Dependency injection through constructors: `DeviceManager(DeviceRepository())`, `EmulatedLifxServer(devices, device_manager, host, port)`, `DeviceService(server)`, `create_devices_router(server)`. Depend on Protocol interfaces (`IDeviceManager`, `IDeviceRepository`), not concrete classes, in type hints.

**Return Values:**
- Handlers return a `list` of packets (possibly empty), never `(header, packet)` tuples; `EmulatedLifxDevice.process_packet()` builds headers. Return `[]` when `res_required` is false on a setter.
- Lookups return `X | None`; mutations return `bool` or a count.
- Services return Pydantic response models (`DeviceInfo`, `PaginatedDeviceList`) built via mappers in `api/mappers/`, so routers pass them straight through with `response_model=`.

## Module Design

**Exports:**
- Each package/subpackage `__init__.py` declares an explicit `__all__` and re-exports the public surface (`lifx_emulator/__init__.py`, `lifx_emulator/devices/__init__.py`). Add new public symbols to the relevant `__all__`.
- `lifx_emulator/__init__.py` exposes `__version__` via `importlib.metadata.version("lifx-emulator-core")` -- do not hard-code versions in source.
- Leaf modules keep a single responsibility: one `*_service.py` per resource, one router per resource, one handler module per protocol namespace.

**Barrel Files:**
- Python: `__init__.py` files act as barrels (`lifx_emulator.devices`, `lifx_emulator.scenarios`, `lifx_emulator.repositories`, `lifx_emulator_app.api`, `lifx_emulator_app.api.services`). Consumers import from the barrel.
- Frontend: `frontend/src/lib/index.ts`, `lib/stores/index.ts`, `lib/components/index.ts` re-export stores and components.

**Layering rules (enforced by convention, guard them):**
- `lifx_emulator` (core) never imports `lifx_emulator_app`.
- `api/services/*` never import FastAPI; `api/routers/*` never touch `server.device_manager` directly -- they call a service.
- Auto-generated files are never hand-edited: `protocol/packets.py` (`python -m lifx_emulator.protocol.generator`) and `products/registry.py` (`python -m lifx_emulator.products.generator`). `protocol/protocol_types.py` is also generator-maintained.
- The Svelte build writes into `packages/lifx-emulator/src/lifx_emulator_app/api/static/` (`frontend/svelte.config.js`); treat that directory as a build artefact and edit only `frontend/src/`.

**Async conventions:**
- Core I/O is `asyncio` (DatagramProtocol server, async file persistence with debouncing). Services that persist are `async def` and `await server.scenario_persistence.save(...)`; pure getters stay synchronous (`api/services/scenario_service.py`).
- Fire-and-forget save tasks are tracked (`_track_save_task()` in `devices/device.py`) so they can be awaited on shutdown.

---

*Convention analysis: 2026-09-09*
