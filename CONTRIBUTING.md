# Contributing to LIFX Emulator

## How to Contribute

### Bug Fixes

Feel free to open a pull request directly for bug fixes. Opening an issue first is appreciated but not required.

### New Features and Behavior Changes

Please [open an issue](https://github.com/Djelibeybi/lifx-emulator/issues/new) to discuss the proposal before starting work. This helps avoid duplicated effort and ensures the change aligns with the project's direction.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for package management

## Setup

```bash
# Clone the repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install all dependencies (both packages + dev tools)
uv sync
```

## Project Structure

This is a **uv workspace monorepo** with two packages:

| Package | PyPI Name | Import Name | Location |
|---------|-----------|-------------|----------|
| Library | `lifx-emulator-core` | `lifx_emulator` | `packages/lifx-emulator-core/` |
| Standalone | `lifx-emulator` | `lifx_emulator_app` | `packages/lifx-emulator/` |

Each package has its own `pyproject.toml` and `tests/` directory. The root `pyproject.toml` contains workspace configuration, tool settings, and dev dependencies.

## Running Tests

```bash
# Run all tests (both packages)
uv run pytest

# Library tests only
uv run pytest packages/lifx-emulator-core/tests/

# CLI/API tests only
uv run pytest packages/lifx-emulator/tests/

# Single test file
uv run pytest packages/lifx-emulator-core/tests/test_device.py

# Single test
uv run pytest packages/lifx-emulator-core/tests/test_device.py::TestDevice::test_label -v
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`, so async test functions are detected automatically.

## Code Quality

### Linting and Formatting

```bash
# Check for lint errors
uv run ruff check .

# Auto-fix lint errors
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Type Checking

```bash
uv run pyright
```

Pyright runs in `standard` mode targeting Python 3.10.

### Pre-commit Hooks

Pre-commit hooks run automatically on every commit and check:

- Code formatting (Ruff)
- Linting (Ruff)
- Type checking (Pyright)
- Security scanning (Bandit)
- Spelling (codespell)
- File hygiene (trailing whitespace, end-of-file, large files, merge conflicts)

If a hook fails, the commit is rejected. Fix the issues and commit again.

## Code Standards

- **Cyclomatic complexity**: All functions must have complexity ≤ 10 (enforced by Ruff McCabe)
- **Line length**: 88 characters
- **Imports**: Always at the top of the file, sorted by Ruff isort
- **Type annotations**: Pyright standard mode — annotate function signatures and public APIs

## Auto-Generated Files

These files are generated from protocol specifications and must not be edited manually:

- `packages/lifx-emulator-core/src/lifx_emulator/protocol/packets.py`
- `packages/lifx-emulator-core/src/lifx_emulator/protocol/protocol_types.py`
- `packages/lifx-emulator-core/src/lifx_emulator/products/registry.py`

To regenerate:

```bash
uv run python -m lifx_emulator.protocol.generator
uv run python -m lifx_emulator.products.generator
```

## Running the Emulator

```bash
# Start with one color light
uv run lifx-emulator --color 1

# Start with API dashboard
uv run lifx-emulator --color 2 --api

# Full CLI reference
uv run lifx-emulator --help
```

## Documentation

Documentation is built with MkDocs:

```bash
# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Architecture

See [docs/architecture/overview.md](docs/architecture/overview.md) for the layered architecture, packet flow, and design patterns.
