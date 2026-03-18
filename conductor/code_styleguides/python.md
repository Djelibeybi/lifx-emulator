# Python Code Style Guide

Based on existing project configuration (ruff, pyright, pre-commit hooks).

## Formatting

- **Line length**: 88 characters
- **Indent**: 4 spaces
- **Quotes**: Double quotes
- **Formatter**: Ruff (`ruff format`)

## Linting

Enforced by Ruff with these rule sets:

| Code | Category |
| --- | --- |
| `E` | pycodestyle errors |
| `F` | pyflakes |
| `I` | isort (import sorting) |
| `N` | pep8-naming |
| `W` | pycodestyle warnings |
| `UP` | pyupgrade |

## Complexity Limits

- **Cyclomatic complexity**: max 10 (McCabe)
- **Function arguments**: max 5
- **Branches per function**: max 12
- **Statements per function**: max 50

## Type Checking

- **Pyright** in `standard` mode
- Target Python version: 3.10
- All public functions should have type annotations

## Imports

- All imports at the top of the file
- Sorted by isort (enforced by Ruff `I` rules)
- Group order: stdlib, third-party, local

## Package Management

- Use `uv` exclusively
- `uv add <package>` to add dependencies
- `uv sync` to synchronize
- `uv run <command>` to execute

## Testing

- Framework: `pytest` with `pytest-asyncio`
- Async mode: `auto` (all async tests run automatically)
- Coverage: branch coverage with `--cov-branch`
- Test files: `test_*.py` in `packages/*/tests/`
- Test naming: `test_*` functions, `Test*` classes

## Security

- Bandit scans run on every commit via pre-commit hooks
- No secrets in code (enforced by `detect-private-key` hook)
