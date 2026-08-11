# CHANGELOG

<!-- version list -->

## v3.8.0 (2026-08-11)

### Bug Fixes

- **devices**: Gate Button packets and apply ButtonSet payloads
  ([`f28404c`](https://github.com/Djelibeybi/lifx-emulator/commit/f28404c6fc328e1b526ccb84c578712e19bda32e))

- **handlers**: Gate Button.Set/SetConfig responses on res_required
  ([`aba1443`](https://github.com/Djelibeybi/lifx-emulator/commit/aba144365e99060576a420a92553e5e42e9f13db))

- **persistence**: Persist button config across save/restore
  ([`2562173`](https://github.com/Djelibeybi/lifx-emulator/commit/25621739a83cb1ee7e84093254b4bbd37597d318))

- **products**: Gate extended multizone and curate new product specs
  ([`87126a7`](https://github.com/Djelibeybi/lifx-emulator/commit/87126a7be990023046fc68bc20a4fe47e89e2ce6))

- **protocol**: Pack enum fields at their declared wire width
  ([`52fdd4f`](https://github.com/Djelibeybi/lifx-emulator/commit/52fdd4ff619ce8d570d9145f9667ad14a93645d2))

- **protocol**: Tolerate undeclared enum values when unpacking
  ([`75d3b6b`](https://github.com/Djelibeybi/lifx-emulator/commit/75d3b6bc9519cc92251e9ddff01e7c0d311ba999))

- **specs**: Default Ceiling 265/266 firmware to 4.10 for Sky
  ([`591ffb1`](https://github.com/Djelibeybi/lifx-emulator/commit/591ffb1aed5eeb1556a202e9ad905ac64732ee6a))

- **specs**: Repair specs.yml YAML + correct Mirror/Path/Spot matrix dims
  ([`b051adb`](https://github.com/Djelibeybi/lifx-emulator/commit/b051adbc962f69d2214ee2f0740df419280c1f48))

### Features

- **devices**: Add ambient-light, button and uplight state + builder seeding
  ([`d36967c`](https://github.com/Djelibeybi/lifx-emulator/commit/d36967c9fba6e01127f434fe4ea0eb25a12dffe3))

- **handlers**: Ambient-light sensor handler (always answers, lux 0 when sensorless)
  ([`66a7d41`](https://github.com/Djelibeybi/lifx-emulator/commit/66a7d41e3b3f3afbcd3f2dc0923d675539889a61))

- **handlers**: Button get/set + config handlers gated on has_buttons
  ([`813a81b`](https://github.com/Djelibeybi/lifx-emulator/commit/813a81b15caf6ff77e2c5e49362c980e070c8dbc))

- **products**: Regenerate registry from upstream
  ([`717c9b2`](https://github.com/Djelibeybi/lifx-emulator/commit/717c9b238c484230911fd15155d038c9b77bc5b9))

- **protocol**: Regenerate + enable Button/Sensor packets (Relay still filtered)
  ([`ad6c3cd`](https://github.com/Djelibeybi/lifx-emulator/commit/ad6c3cd82149d3335add431a2a6628e6572c7bc2))

- **specs**: Add uplight_zone_count for Ceiling + Mirror
  ([`b5ed8d9`](https://github.com/Djelibeybi/lifx-emulator/commit/b5ed8d9b5742511965fab0b6a2a08fa4ba8277bf))

- **tile**: Allow Sky effect on new Ceiling pids 265/266
  ([`b3d95c3`](https://github.com/Djelibeybi/lifx-emulator/commit/b3d95c38c512fd7954608912c0957cc0b1220237))


## v3.7.1 (2026-08-11)

### Bug Fixes

- **security**: Resolve code scanning alerts
  ([`4096a23`](https://github.com/Djelibeybi/lifx-emulator/commit/4096a23d42d74e34e5bc11b07575cb9517c5920e))


## v3.7.0 (2026-06-13)

### Bug Fixes

- Tolerate unknown enum values when decoding packets
  ([`2516180`](https://github.com/Djelibeybi/lifx-emulator/commit/25161802ac99ee0c0fa28619c7f637acc442dd3f))

### Features

- Emit multi-service StateService discovery replies
  ([`91e58a9`](https://github.com/Djelibeybi/lifx-emulator/commit/91e58a9e0fab3f6b4cbb9746bc56d7484d9eb3db))


## v3.6.3 (2026-03-18)

### Bug Fixes

- **dashboard**: Broadcast metadata changes via WebSocket for live updates
  ([`6b933ae`](https://github.com/Djelibeybi/lifx-emulator/commit/6b933aed9fff0ba3231b8e9913160cdac5ae62cf))


## v3.6.2 (2026-02-06)

### Bug Fixes

- **server**: Check drop_packets before sending early ack
  ([`6e3f494`](https://github.com/Djelibeybi/lifx-emulator/commit/6e3f4946cb8ddb8941bcf9fe5a94a7541c72cb8e))


## v3.6.1 (2026-02-06)

### Bug Fixes

- **server**: Skip early ack for packets that will get StateUnhandled
  ([`33ec469`](https://github.com/Djelibeybi/lifx-emulator/commit/33ec469bdf07de4dab6c108c7e10f1889a7f7c9f))


## v3.6.0 (2026-02-04)

### Bug Fixes

- Address CodeRabbit review feedback
  ([`0bc07f5`](https://github.com/Djelibeybi/lifx-emulator/commit/0bc07f5502d219a17159bdf1ecc0d049c85c2d94))

- **tile**: Correct user_x coordinate calculation for tile positioning
  ([`0b7ac27`](https://github.com/Djelibeybi/lifx-emulator/commit/0b7ac27fac318d9850ff53fe65f5675ea20ece9c))

### Features

- **dashboard**: Add live device visualizer with real-time state updates
  ([`51fbcc0`](https://github.com/Djelibeybi/lifx-emulator/commit/51fbcc0e17bafa51554594c146b884e35f96cfde))


## v3.5.0 (2026-02-03)

### Bug Fixes

- Address CodeRabbit PR review feedback
  ([`e302407`](https://github.com/Djelibeybi/lifx-emulator/commit/e302407e19f73de9a49361372b5c776b761d61e1))

### Features

- **api**: Complete WebSocket real-time event infrastructure
  ([`81cfa6f`](https://github.com/Djelibeybi/lifx-emulator/commit/81cfa6f11dfb7d216b40d6672ba73883841be11a))

- **dashboard**: Add scenario panel, pagination, and tabbed interface (Phase 4)
  ([`a50951d`](https://github.com/Djelibeybi/lifx-emulator/commit/a50951d805592787ea70a86441e44c781e307c1c))


## v3.4.0 (2026-02-03)

### Features

- **core**: Add has_chain capability flag to DeviceState
  ([`66c639c`](https://github.com/Djelibeybi/lifx-emulator/commit/66c639c3b76cfc14892119e26f854927bb0155bf))


## v3.3.0 (2026-02-03)

### Bug Fixes

- **device**: Apply error scenarios to unhandled-packet responses
  ([`7571ab7`](https://github.com/Djelibeybi/lifx-emulator/commit/7571ab7a9d9833c1b79e0941d0d348c82ebcf34c))

### Features

- **server**: Send acks immediately before device processing
  ([`3d4ec66`](https://github.com/Djelibeybi/lifx-emulator/commit/3d4ec66388099d2b672483cf85d47f100fe67549))


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
