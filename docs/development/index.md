# Developer Documentation

> Practical guide for developers working on the lifx-emulator codebase

## Welcome

This section provides developer-focused documentation for navigating and contributing to the lifx-emulator project. Whether you're fixing a bug, adding a feature, or just exploring the codebase, this guide will help you get oriented quickly.

## Quick Links

### Essential Reading
- **[Code Navigation Guide](code-navigation.md)** - Navigate the codebase efficiently
- **[Architecture Overview](../architecture/overview.md)** - Understand system design
- **[Architecture Decisions](../architecture/decisions.md)** - Design rationale and ADRs
- **[Testing Guide](../guide/integration-testing.md)** - Writing and running tests

### Quick Start
- [Installation](../getting-started/installation.md) - Set up your development environment
- [Best Practices](../guide/best-practices.md) - Code quality standards

## Understanding the Architecture

Before diving into development, understand the system design:

- **[Architecture Overview](../architecture/overview.md)** - System layers and component interaction
- **[Architecture Decisions](../architecture/decisions.md)** - 15 ADRs explaining design choices
- **[Packet Flow](../architecture/packet-flow.md)** - How packets are processed
- **[Protocol Details](../architecture/protocol.md)** - Binary protocol implementation
- **[Device State](../architecture/device-state.md)** - State management internals

This Development section focuses on **navigating and modifying the codebase**, not architectural theory.

---

## Code Navigation Guide

**Purpose**: Help you find your way around the codebase quickly

**What's inside**:
- Package structure and file organization (13.6k LOC core library)
- Entry points and main exports
- Layer architecture (Network → Domain → Repository → Persistence)
- Common code paths and module dependencies
- Quick command reference for development

**When to use**:
- First time exploring the codebase
- Looking for where specific functionality lives
- Understanding how modules relate to each other
- Finding test files or documentation

**[Read the Code Navigation Guide →](code-navigation.md)**

---

## Getting Started as a Developer

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/Djelibeybi/lifx-emulator.git
cd lifx-emulator

# Install dependencies (uses uv package manager)
uv sync

# Activate virtual environment
source .venv/bin/activate

# Verify installation
pytest --version
pyright --version
ruff --version
```

### 2. Run Tests
```bash
# Run all tests (764 tests)
pytest

# Run with coverage report
pytest --cov=lifx_emulator --cov=lifx_emulator_app --cov-report=html

# Run specific module tests
pytest packages/lifx-emulator-core/tests/test_device.py -v

# Run specific test
pytest packages/lifx-emulator-core/tests/test_device.py::test_process_packet -v
```

### 3. Code Quality Checks
```bash
# Lint and auto-fix
ruff check --fix .

# Type checking
pyright

# Run all quality checks (mimics CI)
ruff check . && pyright && pytest
```

### 4. Run the Emulator
```bash
# As module
python -m lifx_emulator_app

# As installed command
lifx-emulator --api --verbose

# With custom devices
lifx-emulator --color 2 --multizone 1 --tile 1 --api
```

### 5. Build Documentation
```bash
# Serve locally (live reload)
uv run mkdocs serve

# Build static site
uv run mkdocs build

# View at http://localhost:8000
```

---

## Development Workflow

### Adding a New Feature

1. **Understand the architecture**
   - Read [Architecture Decisions](../architecture/decisions.md) for context
   - Review [Architecture Overview](../architecture/overview.md) for data flow
   - Check [Code Navigation](code-navigation.md) for file locations

2. **Write tests first** (TDD approach)
   - Add test cases in appropriate `tests/` directory
   - Ensure 95% coverage (minimum 80%)
   - Run `pytest -v` to verify tests fail

3. **Implement the feature**
   - Follow existing patterns and layer boundaries
   - Keep functions under 10 complexity (McCabe)
   - Add type hints for all public APIs
   - Update docstrings

4. **Verify code quality**
   ```bash
   ruff check --fix .        # Lint and format
   pyright                   # Type checking
   pytest --cov              # Test coverage
   ```

5. **Update documentation**
   - Add/update docstrings
   - Update relevant markdown docs
   - Add examples if public API changed

6. **Submit pull request**
   - Use conventional commits (feat:, fix:, docs:, etc.)
   - Reference related issues
   - Ensure CI passes

---

### Fixing a Bug

1. **Reproduce the bug**
   - Write a failing test case
   - Verify it fails: `pytest -v`

2. **Locate the issue**
   - Use [Code Navigation](code-navigation.md) to find relevant code
   - Check [Packet Flow](../architecture/packet-flow.md) for data flow
   - Add debug logging if needed

3. **Fix the bug**
   - Make minimal changes
   - Avoid scope creep
   - Maintain backwards compatibility

4. **Verify the fix**
   ```bash
   pytest -v                 # All tests pass
   pytest --cov              # Coverage maintained
   ruff check . && pyright   # Quality checks pass
   ```

5. **Submit pull request**
   - Use `fix:` prefix in commit message
   - Explain root cause in PR description
   - Reference issue number

---

### Refactoring Code

1. **Establish test coverage**
   - Ensure affected code has >95% coverage
   - Add tests if needed: `pytest --cov=lifx_emulator.module`

2. **Plan the refactoring**
   - Review [Architecture Decisions](../architecture/decisions.md)
   - Don't violate established patterns
   - Consider backwards compatibility

3. **Refactor incrementally**
   - Small, focused changes
   - Run tests after each change
   - Keep commits atomic

4. **Verify no regressions**
   ```bash
   pytest -v                 # All tests still pass
   pytest --cov              # Coverage maintained/improved
   ruff check .              # Complexity within limits
   ```

5. **Update documentation**
   - Revise docstrings
   - Update architecture docs if needed

---

## Code Quality Standards

### Test Coverage
- **Target**: 95% coverage
- **Minimum**: 80% (enforced by CI)
- **Check**: `pytest --cov --cov-report=term-missing`

### Code Complexity
- **Max McCabe complexity**: 10 per function
- **Max arguments**: 5 per function
- **Max branches**: 12 per function
- **Max statements**: 50 per function
- **Check**: `ruff check .` (enforced automatically)

### Type Checking
- **Standard**: Pyright standard mode
- **Target**: Python 3.11+
- **Check**: `pyright`

### Formatting
- **Tool**: Ruff formatter
- **Line length**: 88 characters
- **Quote style**: Double quotes
- **Indent**: 4 spaces
- **Check**: `ruff format --check .`
- **Fix**: `ruff format .`

### Import Organization
- **Order**: stdlib → third-party → local
- **Tool**: Ruff import sorter
- **Check**: `ruff check --select I .`
- **Fix**: `ruff check --select I --fix .`

---

## Common Development Tasks

### Regenerating Auto-Generated Code

**Protocol packets** (DO NOT EDIT `protocol/packets.py`):
```bash
python -m lifx_emulator.protocol.generator
# Downloads LIFX YAML spec and regenerates packets.py
```

**Product registry** (DO NOT EDIT `products/registry.py`):
```bash
python -m lifx_emulator.products.generator
# Downloads products.json from LIFX GitHub
# Regenerates registry.py with all 137+ products
# Updates specs.yml templates for new products
```

### Adding a New Packet Type

1. **Regenerate protocol** (if LIFX added new packet type):
   ```bash
   python -m lifx_emulator.protocol.generator
   ```

2. **Create handler function** in appropriate handler module:
   ```python
   # handlers/light_handlers.py
   def handle_new_packet(
       device: EmulatedLifxDevice,
       packet: NewPacket,
       header: LifxHeader,
   ) -> list[Any]:
       # Implementation
       return [ResponsePacket(...)]
   ```

3. **Register handler** in `handlers/registry.py`:
   ```python
   registry.register(NewPacket.PKT_TYPE, handle_new_packet)
   ```

4. **Add tests** in `tests/test_handlers.py`:
   ```python
   def test_handle_new_packet():
       device = create_color_light()
       packet = NewPacket(...)
       header = create_test_header()
       responses = handle_new_packet(device, packet, header)
       assert len(responses) == 1
       # ... assertions
   ```

### Adding a New Device Type

1. **Add product to specs.yml** (if needed):
   ```yaml
   products:
     99:  # Product ID
       zones: 16
       tile_count: 5
       # ... other specs
   ```

2. **Create factory function** in `factories/factory.py`:
   ```python
   def create_new_device_type(
       serial: str | None = None,
       storage: IDeviceStorageBackend | None = None,
   ) -> EmulatedLifxDevice:
       builder = DeviceBuilder()
       # ... configure builder
       return builder.build()
   ```

3. **Add to `__init__.py` exports**:
   ```python
   __all__ = [
       # ...
       "create_new_device_type",
   ]
   ```

4. **Add CLI argument** in `__main__.py`:
   ```python
   @app.default
   def main(
       # ...
       new_device_type: int = 0,
   ):
       # ... device creation logic
   ```

5. **Add tests**:
   ```python
   def test_create_new_device_type():
       device = create_new_device_type()
       assert device.state.has_new_capability
       # ... assertions
   ```

---

## Debugging Tips

### Enable Verbose Logging
```bash
lifx-emulator --verbose
# Shows all packets sent/received with hex dumps
```

### Inspect Device State
```python
import asyncio
from lifx_emulator import create_color_light

device = create_color_light()
print(device.state)  # Pretty-prints all state
```

### Test Single Packet
```python
from lifx_emulator.protocol.packets import Light
from lifx_emulator.protocol.header import LifxHeader

packet = Light.Get()
header = LifxHeader(
    target=bytes.fromhex("d073d5000001") + b"\x00\x00",
    source=12345,
    sequence=1,
    pkt_type=Light.Get.PKT_TYPE,
)

responses = device.process_packet(packet, header, ("127.0.0.1", 56700))
print(responses)
```

### Profile Performance
```bash
# Using pytest with profiling
pytest --profile

# Using cProfile
python -m cProfile -s cumtime -m lifx_emulator_app
```

### Check Coverage Gaps
```bash
pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
# Red lines = not covered
```

---

## CI/CD Pipeline

### Automated Checks (GitHub Actions)

Every pull request runs:
1. **Ruff lint check** - Code quality and formatting
2. **Pyright type check** - Type safety validation
3. **Pytest with coverage** - All 764 tests, 95% coverage target
4. **Multi-version testing** - Python 3.11, 3.12, 3.13, 3.14
5. **Documentation build** - Ensures docs compile

**All checks must pass before merge.**

### Building Standalone Binaries

The project uses [PyApp](https://github.com/ofek/pyapp) to create standalone executables that bundle Python and all dependencies into a single binary. Binaries are built automatically on release, but you can build them locally for testing.

**Prerequisites**:
```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Build locally**:
```bash
# Clone PyApp
git clone --depth 1 --branch v0.26.0 https://github.com/ofek/pyapp pyapp

# Build with environment variables
cd pyapp
PYAPP_PROJECT_NAME=lifx-emulator \
PYAPP_PROJECT_VERSION=4.1.0 \
PYAPP_PYTHON_VERSION=3.12 \
PYAPP_EXEC_SPEC=lifx_emulator_app.__main__:main \
cargo build --release

# Binary is at target/release/pyapp
mv target/release/pyapp ../lifx-emulator
chmod +x ../lifx-emulator
```

**Optional: Embed Python distribution** (larger binary, no download on first run):
```bash
PYAPP_DISTRIBUTION_EMBED=1 cargo build --release
```

**Cross-compile for other platforms**:
```bash
# Add target (example: macOS ARM64)
rustup target add aarch64-apple-darwin

# Build for that target
CARGO_BUILD_TARGET=aarch64-apple-darwin cargo build --release
```

**Supported platforms** (built automatically on release):

| Platform | Target | Binary Name |
|----------|--------|-------------|
| Linux x86_64 | `x86_64-unknown-linux-gnu` | `lifx-emulator-linux-x86_64` |
| macOS Intel | `x86_64-apple-darwin` | `lifx-emulator-macos-x86_64` |
| macOS ARM | `aarch64-apple-darwin` | `lifx-emulator-macos-arm64` |
| Windows x86_64 | `x86_64-pc-windows-msvc` | `lifx-emulator-windows-x86_64.exe` |

See [PyApp documentation](https://ofek.dev/pyapp/latest/) for advanced configuration options.

### Semantic Release

The project uses [semantic-release](https://python-semantic-release.readthedocs.io/) with conventional commits:

- `feat:` → Minor version bump (1.x.0)
- `fix:` → Patch version bump (1.0.x)
- `BREAKING CHANGE:` → Major version bump (x.0.0)
- `docs:`, `chore:`, `ci:` → No version bump

**Commit message format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples**:
```bash
feat(core): add HEV device support

Implements HEV Clean device emulation with duration tracking.

Closes #123

fix(api): correct scenario merging precedence

Device-specific scenarios now correctly override type scenarios.

docs(guide): add scenario API examples
```

---

## Project Structure Quick Reference

```
lifx-emulator/
├── packages/
│   ├── lifx-emulator-core/          # Core library (13.6k LOC)
│   │   ├── src/lifx_emulator/
│   │   │   ├── devices/             # Device lifecycle, state, persistence
│   │   │   ├── scenarios/           # Test scenario management
│   │   │   ├── protocol/            # LIFX binary protocol
│   │   │   ├── handlers/            # Packet type handlers
│   │   │   ├── products/            # Product registry
│   │   │   ├── factories/           # Device creation
│   │   │   ├── repositories/        # Storage abstraction
│   │   │   └── server.py            # UDP server
│   │   └── tests/                   # Core library tests
│   │
│   └── lifx-emulator/               # Standalone app (1.6k LOC)
│       ├── src/lifx_emulator_app/
│       │   ├── __main__.py          # CLI entry point
│       │   └── api/                 # HTTP API (FastAPI)
│       └── tests/                   # App/API tests
│
├── docs/                            # MkDocs documentation
│   ├── development/                 # This section
│   ├── architecture/                # System design
│   ├── guide/                       # User guides
│   ├── library/                     # Library API reference
│   ├── cli/                         # CLI/API documentation
│   └── tutorials/                   # Step-by-step tutorials
│
├── pyproject.toml                   # Workspace config (uv)
├── mkdocs.yml                       # Documentation config
└── README.md                        # Project overview
```

---

## Resources

### Internal Documentation
- [Architecture Overview](../architecture/overview.md)
- [Device Types Guide](../guide/device-types.md)
- [Testing Scenarios](../guide/testing-scenarios.md)
- [Integration Testing](../guide/integration-testing.md)
- [Best Practices](../guide/best-practices.md)

### External Resources
- [LIFX LAN Protocol Docs](https://lan.developer.lifx.com)
- [LIFX Products JSON](https://github.com/LIFX/products)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Tools Documentation
- [uv Package Manager](https://github.com/astral-sh/uv)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [Pyright Type Checker](https://github.com/microsoft/pyright)
- [PyApp Binary Builder](https://ofek.dev/pyapp/latest/)
- [MkDocs](https://www.mkdocs.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## Getting Help

### Contribution Guidelines
For detailed contribution information:
- **Code of conduct**: Follow respectful collaboration practices
- **How to submit issues**: Use GitHub Issues with clear descriptions
- **Pull request process**: Use conventional commits, ensure CI passes
- **Development setup**: See [Getting Started](#getting-started-as-a-developer) above

### Questions and Discussion
- **Issues**: [GitHub Issues](https://github.com/Djelibeybi/lifx-emulator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Djelibeybi/lifx-emulator/discussions)

---

## Next Steps

1. **First time here?** Start with [Code Navigation](code-navigation.md)
2. **Planning a feature?** Read [Architecture Decisions](../architecture/decisions.md)
3. **Need to understand data flow?** Check [Packet Flow](../architecture/packet-flow.md)
4. **Ready to code?** Review the [Getting Started](#getting-started-as-a-developer) section above

Happy coding! 🚀
