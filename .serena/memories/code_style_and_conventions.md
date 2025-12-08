# Code Style and Conventions

## Code Quality Standards
- **Test Coverage**: 95% target (80% minimum enforced by CI)
- **Code Complexity**: All functions ≤10 (McCabe complexity)
- **Type Checking**: Pyright in standard mode (strict type hints required)
- **Python Version**: 3.11+ (target version in configs)

## Formatting Standards (Ruff)
- **Line Length**: 88 characters
- **Indent Width**: 4 spaces
- **Quote Style**: Double quotes
- **Indent Style**: Spaces (never tabs)
- **Docstring Formatting**: Code blocks in docstrings are formatted
- **Docstring Line Length**: Dynamic (follows outer line length)

## Linting Rules (Ruff)
- **Selected Rules**: E (errors), F (pyflakes), I (import sorting), N (naming), W (warnings), UP (pyupgrade)
- **Max Complexity**: 10 (McCabe)
- **Max Arguments**: 5 per function
- **Max Branches**: 12 per function
- **Max Statements**: 50 per function

## Import Organization
```python
"""Module docstring first."""

from __future__ import annotations  # Always use for forward references

import asyncio  # Standard library imports
import logging
from typing import Any  # Type-related imports

from lifx_emulator.constants import CONSTANT  # Internal imports (absolute)
from lifx_emulator.devices.states import DeviceState  # Grouped by module

logger = logging.getLogger(__name__)  # Module-level logger

# Forward declaration for type hinting
TYPE_CHECKING = False
if TYPE_CHECKING:
    from lifx_emulator.devices.persistence import DevicePersistenceAsyncFile
```

## Documentation Standards
- **Module Docstrings**: Brief description at top of every module
- **Class Docstrings**: Describe purpose and key responsibilities
- **Method Docstrings**: Not required for simple/self-documenting methods
- **Complex Logic**: Add inline comments where logic isn't self-evident
- **Type Hints**: Required for all function signatures and class attributes

## Naming Conventions
- **Modules/Packages**: `lowercase_with_underscores`
- **Classes**: `PascalCase` (e.g., `EmulatedLifxDevice`, `DeviceManager`)
- **Functions/Methods**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private Members**: `_leading_underscore` for internal use
- **Type Variables**: `T`, `KT`, `VT` or descriptive `DeviceT`

## Error Handling
- Use specific exception types (not bare `except:`)
- Log exceptions with context using logger
- Validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees

## Testing Conventions
- **Test Files**: `test_*.py` in `tests/` directory
- **Test Classes**: `Test*` (optional, use for grouping)
- **Test Functions**: `test_*`
- **Async Tests**: Use `async def test_*()` with pytest-asyncio
- **Fixtures**: In `conftest.py` for shared setup
- **Coverage**: Aim for 95%, minimum 80%

## Git Commit Messages
- **Format**: Conventional Commits (enforced by commitizen)
- **Types**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `ci:`
- **Scopes**: `core`, `api`, `cli`, `docs`, `deps`
- **Examples**:
  - `feat(core): add multizone framebuffer support`
  - `fix(api): validate device serial format in POST /api/devices`
  - `chore(deps): update ruff to 0.14.2`
  - `docs: update installation guide with uv tool install`

## Commit Flags
- Always use `--no-gpg-sign` when committing (per user instructions)

## Pre-commit Hooks
The project uses pre-commit hooks that run automatically:
1. Trailing whitespace removal
2. End-of-file fixer
3. YAML/TOML/JSON validation
4. Conventional commit message validation (commitizen)
5. uv lock file sync
6. Ruff formatting
7. Ruff linting with auto-fix
8. Bandit security checks
9. Codespell spell checking
10. YAML formatting

**Note**: Pyright is configured but marked as `manual` stage (run explicitly)
