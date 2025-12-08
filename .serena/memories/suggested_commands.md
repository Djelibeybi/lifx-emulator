# Suggested Commands

## Environment Setup

### Install Dependencies
```bash
uv sync
```
Installs all dependencies (dev and prod) and creates virtual environment.

### Activate Virtual Environment
```bash
source .venv/bin/activate
```

## Testing

### Run All Tests
```bash
pytest
```
Runs tests for both packages with coverage reporting.

### Run Library Tests Only
```bash
pytest packages/lifx-emulator-core/tests/
```

### Run Standalone Package Tests Only
```bash
pytest packages/lifx-emulator/tests/
```

### Run Specific Test File
```bash
pytest packages/lifx-emulator-core/tests/test_device.py
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests with Coverage Report
```bash
pytest --cov=lifx_emulator --cov=lifx_emulator_app --cov-report=html
```

## Code Quality

### Lint Code (Ruff)
```bash
ruff check .
```

### Lint with Auto-fix
```bash
ruff check --fix .
```

### Format Code (Ruff)
```bash
ruff format .
```

### Type Check (Pyright)
```bash
pyright
```

### Run All Quality Checks
```bash
ruff check --fix . && ruff format . && pyright && pytest
```

## Running the Emulator

### Run CLI (Development)
```bash
python -m lifx_emulator_app
```

### Install and Run as Tool
```bash
uv tool install lifx-emulator
lifx-emulator
```

### Run with API Server
```bash
lifx-emulator --api
```

### Run with Custom Configuration
```bash
lifx-emulator --color 2 --multizone 1 --tile 1 --api --verbose
```

### List Available Products
```bash
lifx-emulator list-products
```

### Create Devices by Product ID
```bash
lifx-emulator --product 27 --product 32 --product 55
```

## Documentation

### Build Documentation
```bash
mkdocs build
```

### Serve Documentation Locally
```bash
mkdocs serve
```
Opens at http://localhost:8000

### Deploy Documentation (GitHub Pages)
```bash
mkdocs gh-deploy
```

## Pre-commit

### Install Pre-commit Hooks
```bash
pre-commit install
```

### Run Pre-commit on All Files
```bash
pre-commit run --all-files
```

### Update Pre-commit Hooks
```bash
pre-commit autoupdate
```

## Git Operations

### Create Feature Branch
```bash
git checkout -b feat/my-feature
```

### Commit Changes (with conventional commits)
```bash
git add .
git commit -m "feat(core): add new feature" --no-gpg-sign
```

### Push Branch
```bash
git push -u origin feat/my-feature
```

## Building and Publishing

### Build Core Library
```bash
uv build --package lifx-emulator-core
```

### Build Standalone Package
```bash
uv build --package lifx-emulator
```

### Update Lock File
```bash
uv lock
```

### Upgrade Specific Package
```bash
uv lock --upgrade-package <package-name>
```

## System Commands (Linux)

### List Files
```bash
ls -la
```

### Search Files by Name
```bash
find . -name "*.py"
```

### Search Code Content
```bash
grep -r "pattern" packages/
```

### Check Disk Usage
```bash
du -sh packages/*/
```

### Monitor Processes
```bash
ps aux | grep python
```

## Development Workflow

### Complete Task Checklist
When completing a task, run these in order:
1. `ruff check --fix .` - Fix linting issues
2. `ruff format .` - Format code
3. `pyright` - Check types
4. `pytest` - Run tests and ensure coverage ≥80%
5. `git add .` - Stage changes
6. `git commit -m "type(scope): message" --no-gpg-sign` - Commit with conventional format
7. Review changes and push if ready

### Quick Quality Check
```bash
ruff check --fix . && ruff format . && pyright
```
