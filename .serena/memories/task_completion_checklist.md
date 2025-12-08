# Task Completion Checklist

When you complete a development task, follow this checklist in order:

## 1. Code Quality Checks

### Linting (Ruff)
```bash
ruff check --fix .
```
- Fixes auto-fixable issues (imports, formatting, etc.)
- Must pass with no errors
- Enforces complexity limits (≤10 McCabe complexity)
- Checks: E (errors), F (pyflakes), I (imports), N (naming), W (warnings), UP (pyupgrade)

### Formatting (Ruff)
```bash
ruff format .
```
- Formats all Python files to match project style
- Line length: 88 characters
- Double quotes, 4-space indentation

### Type Checking (Pyright)
```bash
pyright
```
- Must pass with no type errors
- Standard mode type checking
- All function signatures must have type hints

## 2. Testing

### Run Full Test Suite
```bash
pytest
```
- Must achieve ≥80% coverage (target: 95%)
- All tests must pass
- Includes both packages (core + standalone)

### Coverage Check
- Coverage report automatically generated in terminal
- Check `coverage.xml` for detailed report
- Ensure new code is well-tested

## 3. Pre-commit Hooks (Optional but Recommended)

### Run Pre-commit
```bash
pre-commit run --all-files
```
This runs:
- File format checks (trailing whitespace, EOF, etc.)
- YAML/TOML/JSON validation
- Ruff formatting and linting
- Security checks (Bandit)
- Spell checking (codespell)

## 4. Documentation

### Update Documentation (if needed)
- Add/update docstrings for new classes and complex functions
- Update CLAUDE.md if architecture or workflows changed
- Update relevant docs/ files for user-facing changes
- Rebuild docs locally to verify:
  ```bash
  mkdocs build
  mkdocs serve
  ```

## 5. Git Workflow

### Stage Changes
```bash
git add .
```

### Review Staged Changes
```bash
git status
git diff --staged
```

### Commit with Conventional Format
```bash
git commit -m "type(scope): description" --no-gpg-sign
```

**Commit Types:**
- `feat(core):` - New feature in core library
- `feat(api):` - New feature in API
- `feat(cli):` - New feature in CLI
- `fix(core):` - Bug fix in core library
- `fix(api):` - Bug fix in API
- `chore(deps):` - Dependency updates
- `docs:` - Documentation changes
- `test:` - Test additions or fixes
- `refactor:` - Code refactoring

**Examples:**
```bash
git commit -m "feat(core): add framebuffer support for matrix devices" --no-gpg-sign
git commit -m "fix(api): validate serial format in POST /api/devices" --no-gpg-sign
git commit -m "docs: update persistent storage guide" --no-gpg-sign
git commit -m "test: add coverage for scenario persistence" --no-gpg-sign
```

### Push Changes (if ready)
```bash
git push
```
or for new branches:
```bash
git push -u origin branch-name
```

## 6. Quick Combined Check

### All-in-One Quality Check
```bash
ruff check --fix . && ruff format . && pyright && pytest
```

This runs all quality checks in sequence. If any step fails, the command stops.

## Common Issues and Fixes

### Import Ordering Issues
```bash
ruff check --fix .
```
Ruff automatically sorts imports correctly.

### Type Errors
- Add proper type hints to function signatures
- Use `from __future__ import annotations` for forward references
- Use `TYPE_CHECKING` guard for import-time circular dependencies

### Test Failures
- Run specific test file: `pytest packages/lifx-emulator-core/tests/test_file.py`
- Run with verbose: `pytest -v`
- Check test output for assertion errors

### Coverage Too Low
- Identify uncovered lines in terminal output
- Add tests for uncovered code paths
- Focus on edge cases and error handling

## Notes

- **Always run tests before committing** - Prevents breaking changes
- **Use conventional commits** - Enforced by pre-commit hooks
- **No GPG signing** - Always use `--no-gpg-sign` flag per user config
- **Pre-commit hooks** - Install once with `pre-commit install`, then they run automatically
- **Coverage target** - Aim for 95%, minimum 80% required
