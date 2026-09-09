# Testing Patterns

**Analysis Date:** 2026-09-09

## Test Framework

**Runner:**
- pytest >= 8.4.2 with pytest-asyncio >= 0.24.0, pytest-cov >= 7.0.0, pytest-sugar >= 1.1.1 (root `pyproject.toml` `[dependency-groups] dev`).
- Config: root `pyproject.toml` `[tool.pytest.ini_options]` is authoritative when running from the repo root. Each package `pyproject.toml` repeats a minimal `testpaths = ["tests"]`, `pythonpath = ["src"]`, `asyncio_mode = "auto"` block for running inside that package directory.
- `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"`: any `async def test_*` or `async def` fixture is collected automatically. The explicit `@pytest.mark.asyncio` seen in older tests (92 uses across 6 files, e.g. `test_server.py`, `test_scenario_service.py`) is redundant -- omit it in new tests.
- `-Wdefault` surfaces warnings; do not silence them with filters.
- `httpx` is a dev dependency solely so FastAPI's `TestClient` works.

**Assertion Library:**
- Plain `assert` with pytest rewriting. No `pytest.approx`, no third-party assertion libraries. `unittest.mock` assertion helpers (`assert_called_once_with`, `assert_awaited_once_with`) for mocks.

**Run Commands:**
```bash
uv run pytest                                                     # All tests, both packages, with coverage (addopts)
uv run pytest packages/lifx-emulator-core/tests/                  # Core library only
uv run pytest packages/lifx-emulator/tests/                       # CLI/API only
uv run pytest packages/lifx-emulator-core/tests/test_device.py    # Single file
uv run pytest packages/lifx-emulator-core/tests/test_device.py::TestEmulatedLifxDevice::test_device_initialization -v
uv run pytest --cov-fail-under=80                                 # What CI runs
uv run pytest -p no:cacheprovider --no-cov -x                     # Fast local loop without coverage
```

There is no watch mode configured; rerun the single-file command. Coverage is always on via `addopts` (`--cov=lifx_emulator --cov=lifx_emulator_app --cov-branch --cov-report=xml --cov-report=term-missing:skip-covered --junitxml=junit.xml`). `coverage.xml` and `junit.xml` land in the repo root.

## Test File Organization

**Location:**
- Separate `tests/` directory per package, never co-located with source:
  - `packages/lifx-emulator-core/tests/` (33 files) -- protocol, devices, handlers, scenarios, repositories, persistence, server, integration.
  - `packages/lifx-emulator/tests/` (8 files) -- CLI, config, API, services, WebSocket.
- Shared fixtures live in each package's `tests/conftest.py`. There is no `tests/fixtures/` or factories directory; device factories from `lifx_emulator.factories` serve that role.
- Frontend has no test suite; `npm run check` (svelte-check) is the only frontend verification.

**Naming:**
- Files: `test_<module_or_feature>.py` (enforced by pre-commit `name-tests-test --pytest-test-first`). Extended coverage files use the `_extended` suffix (`test_device_handlers_extended.py`, `test_tile_handlers_extended.py`); edge-case files use `_edge_cases`.
- Classes: `Test<Subject>` grouping related tests (`TestDeviceState`, `TestEmulatedLifxDevice`, `TestAPIEndpoints`, `TestGlobalScenario`, `TestWebSocketEndpoint`). Every test lives in a class.
- Functions: `test_<behaviour_under_test>` in snake_case, e.g. `test_handle_packet_null_target_broadcasts`, `test_set_global_scenario_persists`, `test_serial_prefix_validation_invalid_chars`.
- Fixtures: noun-named by what they produce: `color_device`, `extended_multizone_device`, `large_matrix_device`, `server_with_devices`, `api_client`, `mock_server`, `temp_storage`.

**Structure:**
```
packages/lifx-emulator-core/tests/
├── conftest.py                       # Device/server/integration fixtures
├── test_device.py                    # EmulatedLifxDevice + core handlers
├── test_*_handlers_extended.py       # Per-namespace handler coverage
├── test_server.py                    # EmulatedLifxServer.handle_packet unit tests
├── test_integration.py               # Real UDP sockets against a running server
├── test_async_storage.py             # Persistence with temp dirs
├── test_scenario_manager.py          # HierarchicalScenarioManager
├── test_serializer.py                # Binary packing (parametrised)
└── test_products_*.py / test_protocol_*.py  # Generators and registries

packages/lifx-emulator/tests/
├── conftest.py                       # anyio_backend only
├── test_api.py / test_api_validation.py     # FastAPI TestClient
├── test_cli.py / test_cli_validation.py     # __main__ helpers with patch()
├── test_config.py                    # Pydantic config + path resolution
├── test_scenario_service.py          # Service layer with MagicMock server
└── test_websocket.py                 # WebSocket endpoint + manager
```

## Test Structure

**Suite Organization:**
Module docstring, imports, module-level fixtures (if file-specific), then `Test*` classes with one-line docstrings on the class and every test. Pattern from `packages/lifx-emulator-core/tests/test_device.py`:

```python
"""Unit tests for EmulatedLifxDevice and device packet handlers."""

import time

from lifx_emulator.factories import create_color_light, create_infrared_light
from lifx_emulator.protocol.packets import Device, Light, MultiZone, Tile


class TestDeviceState:
    """Test DeviceState dataclass via factory functions."""

    def test_device_state_defaults(self):
        """Test default device state values via factory."""
        device = create_color_light("d073d5000001")
        state = device.state
        assert state.serial == "d073d5000001"
        assert state.power_level == 65535  # Factory defaults to on
        assert state.has_color is True
        assert state.has_multizone is False


class TestEmulatedLifxDevice:
    """Test EmulatedLifxDevice class."""

    def test_device_initialization(self, color_device):
        """Test device initializes correctly."""
        assert color_device.state.serial == "d073d5000001"
        assert color_device.scenario_manager is not None
```

**Patterns:**
- Setup: prefer factory functions (`create_color_light("d073d5000001")`) or conftest fixtures over hand-built `DeviceState`. Build a `DeviceState` directly only when testing state internals (see `device_state` fixture in `packages/lifx-emulator-core/tests/conftest.py`).
- Use the canonical test serials `d073d5000001` .. `d073d5000012` (and `d073d5000099` for scenario devices) so fixtures and assertions line up across files.
- Servers under test are built inline with the full DI chain: `EmulatedLifxServer([device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700)`. Unit tests call `await server.handle_packet(bytes, addr)` directly without binding a socket (`test_server.py`).
- Packets are built from `LifxHeader(source=..., target=..., sequence=..., pkt_type=..., tagged=..., res_required=...)` plus `Device.<Packet>(...)` and packed with `.pack()`; annotate `pkt_type` with a comment naming the packet.
- Teardown: rely on fixture scope and context managers (`async with server:`, `tempfile.TemporaryDirectory()`). No `setup_method`/`teardown_method`.
- Assertions: use `is True` / `is False` / `is None` for booleans and None, `==` for values, `in` for dict-key presence on JSON responses, and `len(...) ==` on response lists. Comment non-obvious expected values (`assert state.infrared_brightness == 16384  # Factory default 25%`).
- Exceptions: `with pytest.raises(ValueError, match="6 hex characters"):` -- always pass `match=` for `ValueError`/`FileNotFoundError` (`packages/lifx-emulator/tests/test_config.py`). Bare `pytest.raises(Exception)` is acceptable only for Pydantic `extra="forbid"` rejections.
- Parametrise sparingly (8 uses) for value tables such as serialiser bounds and invalid serials (`test_serializer.py:413`, `test_async_storage.py:251`):

```python
@pytest.mark.parametrize(
    "bad_serial",
    [
        "../../etc/passwd",
        "d073d5/000001",
        "not-hex-value",
        "d073d500000",  # 11 chars (too short)
    ],
)
```

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`). No pytest-mock.

**Patterns:**
Service-layer tests replace the whole server with a `MagicMock`, attaching `AsyncMock` for awaited methods (`packages/lifx-emulator/tests/test_scenario_service.py`):

```python
@pytest.fixture
def mock_server():
    """Create a mock server with a scenario_manager and persistence."""
    server = MagicMock()
    server.scenario_manager = MagicMock()
    server.scenario_persistence = MagicMock()
    server.scenario_persistence.save = AsyncMock()
    server.invalidate_all_scenario_caches = MagicMock()
    return server


@pytest.fixture
def service(mock_server):
    return ScenarioService(mock_server)


class TestGlobalScenario:
    async def test_set_global_scenario_persists(self, service, mock_server, sample_config):
        await service.set_global_scenario(sample_config)
        mock_server.scenario_manager.set_global_scenario.assert_called_once_with(sample_config)
        mock_server.invalidate_all_scenario_caches.assert_called_once()
        mock_server.scenario_persistence.save.assert_awaited_once_with(
            mock_server.scenario_manager
        )
```

CLI tests patch by import location using the decorator form and inspect `call_args` (`packages/lifx-emulator/tests/test_cli.py`):

```python
@patch("lifx_emulator_app.__main__.logging.basicConfig")
def test_setup_logging_verbose(self, mock_basic_config):
    """Test that verbose logging is configured correctly."""
    _setup_logging(True)
    mock_basic_config.assert_called_once()
    call_kwargs = mock_basic_config.call_args[1]
    assert call_kwargs["level"] == 10  # logging.DEBUG
```

Environment and filesystem are controlled with built-in fixtures, not mocks (`packages/lifx-emulator/tests/test_config.py`):

```python
monkeypatch.setenv(ENV_VAR, str(config_file))
result = resolve_config_path(None)
assert result == config_file

monkeypatch.setenv(ENV_VAR, "/nonexistent/config.yaml")
with pytest.raises(FileNotFoundError, match=ENV_VAR):
    resolve_config_path(None)
```

**What to Mock:**
- The `EmulatedLifxServer` when unit-testing an app service (`ScenarioService`) -- the service only needs `scenario_manager`, `scenario_persistence`, `invalidate_all_scenario_caches`.
- `logging.basicConfig`, `asyncio.run`, and other process-level side effects in `__main__` tests.
- Environment variables via `monkeypatch.setenv`; config files via `tmp_path` (81 uses in `test_config.py`/`test_export_config.py`).

**What NOT to Mock:**
- Devices, `DeviceManager`, `DeviceRepository`, `HierarchicalScenarioManager`, handlers, or the protocol layer. Use real objects from `lifx_emulator.factories`; they are cheap and deterministic.
- The FastAPI app: exercise it through `TestClient(create_api_app(server))` with a real server instance holding real devices (`test_api.py`, `test_websocket.py`).
- Persistence: use `DevicePersistenceAsyncFile(tmpdir)` against a real temporary directory (`test_async_storage.py`), never a mocked filesystem.
- Time: tests use real `time.sleep(0.01)` / `asyncio.sleep(0.01)` for uptime and delay checks; keep sleeps at 10 ms or less.

## Fixtures and Factories

**Test Data:**
Core fixtures in `packages/lifx-emulator-core/tests/conftest.py` wrap the factory functions with fixed serials:

```python
@pytest.fixture
def color_hsbk():
    """Standard color value for testing."""
    return LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500)


@pytest.fixture
def multizone_device():
    """Create a multizone device with 16 zones."""
    return create_multizone_light("d073d5000004", zone_count=16)


@pytest.fixture
def extended_multizone_device():
    """Create an extended multizone device with 82 zones."""
    return create_multizone_light("d073d5000005", zone_count=82, extended_multizone=True)


@pytest.fixture
def large_matrix_device():
    """Create a large matrix device (single 16x8 tile with >64 zones)."""
    return create_tile_device("d073d5000012", tile_count=1, tile_width=16, tile_height=8)


@pytest.fixture
def server_with_devices(color_device, multizone_device, tile_device):
    """Create a server with multiple device types."""
    devices = [color_device, multizone_device, tile_device]
    device_manager = DeviceManager(DeviceRepository())
    return EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)
```

Available core fixtures: `color_hsbk`, `device_state`, `color_device`, `infrared_device`, `hev_device`, `multizone_device`, `extended_multizone_device`, `tile_device` (5x 8x8), `single_tile_device`, `multi_tile_device` (3x 8x8), `large_matrix_device` (1x 16x8), `white_device`, `server_with_devices`, `device_with_scenarios`, plus integration fixtures `integration_port` (module), `integration_devices` (module), `integration_server`, `device_lookup`.

App tests define fixtures per file rather than in conftest (`packages/lifx-emulator/tests/conftest.py` only sets `anyio_backend = "asyncio"`):

```python
@pytest.fixture
def api_client(server_with_devices):
    """Create a test client for the API."""
    app = create_api_app(server_with_devices)
    return TestClient(app)
```

Async fixtures yield inside a context manager (`test_async_storage.py`):

```python
@pytest.fixture
async def temp_storage():
    """Create temporary storage directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DevicePersistenceAsyncFile(tmpdir)
```

**Location:**
- Shared: `packages/lifx-emulator-core/tests/conftest.py`.
- File-specific: top of the test module, above the first `Test*` class.
- Add a new shared device shape to `conftest.py` with a fresh serial in the `d073d50000xx` range and a docstring describing the shape.

## Coverage

**Requirements:** 80% minimum enforced in CI (`uv run --frozen pytest --cov-fail-under=80` in `.github/workflows/ci.yml`). Branch coverage is on. Reports upload to Codecov (`slug: Djelibeybi/lifx-emulator`) from the Ubuntu/3.10 matrix cell; JUnit test results upload from every cell.

Excluded from measurement (`[tool.coverage.run] omit` in root `pyproject.toml`): `protocol/generator.py`, `protocol/protocol_types.py`, `products/generator.py`, `products/registry.py`. Excluded lines: `pragma: no cover`, `@overload`, `if TYPE_CHECKING`, `raise NotImplementedError`, `if __name__ == "__main__":`.

**View Coverage:**
```bash
uv run pytest                                  # term-missing summary (covered files skipped)
uv run pytest --cov-report=html && open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- The bulk of the ~1,110 tests. Handlers are tested by calling `device.process_packet(header, packet)` on a factory-built device and inspecting the returned packet list (`test_device.py`, `test_*_handlers_extended.py`).
- Server routing is tested by `await server.handle_packet(packet_bytes, addr)` with no socket (`test_server.py`).
- App services are tested against a `MagicMock` server (`test_scenario_service.py`); config models against Pydantic validation (`test_config.py`).

**Integration Tests:**
- `packages/lifx-emulator-core/tests/test_integration.py` starts the real UDP server with `async with integration_server:` on a free port from `find_free_port()` and talks to it over a raw `socket.socket(AF_INET, SOCK_DGRAM)`:

```python
async def test_discover_devices(self, integration_server, integration_port):
    async with integration_server:
        header = create_header(pkt_type=2, tagged=True, res_required=True)  # GetService

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.sendto(header.pack(), ("127.0.0.1", integration_port))

        await asyncio.sleep(0.01)

        data, _ = sock.recvfrom(4096)
        sock.close()
```

- Device fixtures for integration are module-scoped and all share `integration_port` (set on `device.state.port`); the server fixture is function-scoped so each test gets a fresh lifecycle.
- HTTP/WebSocket integration uses FastAPI `TestClient` synchronously, including `with client.websocket_connect("/ws") as websocket:` and `websocket.send_json(...)` (`test_websocket.py`).
- No pytest markers distinguish unit from integration tests; everything runs in one invocation.

**E2E Tests:**
- Not used. No Playwright/Cypress for the Svelte dashboard.

## Common Patterns

**Async Testing:**
Write `async def` tests inside ordinary `Test*` classes; no marker or event-loop fixture required (`test_async_storage.py`):

```python
class TestDevicePersistenceAsyncFile:
    """Test asynchronous device storage."""

    async def test_device_storage_save_and_load(self, temp_storage):
        """Test saving and loading basic device state."""
        device = create_color_light("d073d5123456", storage=temp_storage)
        state = device.state
        state.label = "Test Light"
        state.power_level = 32768

        await temp_storage.save_device_state(state)
        loaded = await temp_storage.load_device_state("d073d5123456")
        assert loaded is not None
        assert loaded.label == "Test Light"
```

For scenario delays and debounced saves, `await asyncio.sleep(...)` slightly longer than the configured delay, then assert (`test_server.py::test_response_delay_applied`).

**Error Testing:**
```python
def test_serial_prefix_validation_invalid_length(self):
    """Test that serial prefix with wrong length is rejected."""
    with pytest.raises(ValueError, match="6 hex characters"):
        EmulatorConfig(serial_prefix="abc")
```

For "must not raise" behaviour at the network boundary, call the method and add a comment rather than wrapping in `try` (`test_server.py`):

```python
async def test_handle_packet_too_short(self, server_with_devices):
    """Test server ignores packets shorter than header size."""
    short_packet = b"\x00\x01\x02"  # Only 3 bytes
    addr = ("127.0.0.1", 56700)

    # Should not raise exception, just log warning
    await server_with_devices.handle_packet(short_packet, addr)
```

For HTTP error mapping, assert the status code and `detail` text from the JSON body (`test_api.py`, `test_api_validation.py`).

**Log Assertions:**
Use `caplog.at_level(logging.ERROR)` only when the log line is the observable behaviour (single use in `test_websocket.py:722`). Prefer asserting on state or return values.

**Adding tests for a new handler:**
1. Add the handler in the matching `handlers/<namespace>_handlers.py` and register it in `handlers/registry.py`.
2. Add tests to the matching `test_<namespace>_handlers_extended.py`: one `Get*` round-trip, one `Set*` with `res_required=True` and one with `res_required=False` (expect `[]`), and one capability-mismatch case (switches must return `StateUnhandled`).
3. If the packet changes persisted state, add a save/load case in `test_async_storage.py`.
4. If it is client-visible, add a raw-UDP case to `test_integration.py`.

---

*Testing analysis: 2026-09-09*
