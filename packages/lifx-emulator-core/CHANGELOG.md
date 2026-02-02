# CHANGELOG

<!-- version list -->

## v3.2.0 (2026-02-02)

### Bug Fixes

- **tests**: Replace flaky probabilistic drop rate tests with deterministic mocks
  ([`5070d6e`](https://github.com/Djelibeybi/lifx-emulator/commit/5070d6e88495dfeffaffb8f54f6eb5e6098d0f43))

### Features

- **core**: Wire partial_responses scenario through packet handlers
  ([`a799dba`](https://github.com/Djelibeybi/lifx-emulator/commit/a799dba3f2d04501dd5b0694359e3e71e2ed5bbb))


## v3.1.1 (2026-02-01)

### Bug Fixes

- **tests**: Relax timing threshold in test_no_delay_by_default
  ([`dd1b416`](https://github.com/Djelibeybi/lifx-emulator/commit/dd1b4162e7b6111a13818aad0450f15367c7c9ac))


## v3.1.0 (2026-01-11)

### Features

- Add Python 3.10 support
  ([`c19eee5`](https://github.com/Djelibeybi/lifx-emulator/commit/c19eee5181fc3e0e3b4ef9fc3e6d47308dce7a0f))


## v3.0.3 (2025-11-27)

### Bug Fixes

- **core**: Update device port to match server port when adding devices
  ([`db68eef`](https://github.com/Djelibeybi/lifx-emulator/commit/db68eefa764d8c98054ada19eabd6e06440f886b))


## v3.0.2 (2025-11-27)

### Bug Fixes

- **core**: Add missing pydantic dependency to lifx-emulator-core
  ([`7cd2309`](https://github.com/Djelibeybi/lifx-emulator/commit/7cd230948285706c3d31ed5478e2e271ed134033))


## v3.0.1 (2025-11-26)

### Bug Fixes

- Adjust uv build for new monorepo layout
  ([`a0d5b7c`](https://github.com/Djelibeybi/lifx-emulator/commit/a0d5b7c1c1ab5659acc8554931f6c441654add05))


## v3.0.0 (2025-11-26)

### Refactoring

- Split into monorepo with separate library and CLI packages
  ([`402fe6e`](https://github.com/Djelibeybi/lifx-emulator/commit/402fe6e6c42e4fb730d076cd4dd0bfe7743b2c57))

### Breaking Changes

- The project is now split into two packages:


## v2.4.0 (2025-11-26)

- Initial Release
