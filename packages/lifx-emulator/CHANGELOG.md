# CHANGELOG

<!-- version list -->

## v4.3.0 (2026-02-04)

### Bug Fixes

- Address CodeRabbit review feedback
  ([`0bc07f5`](https://github.com/Djelibeybi/lifx-emulator/commit/0bc07f5502d219a17159bdf1ecc0d049c85c2d94))

- **frontend**: Clear pending updates on device removal and store clear
  ([`933d22e`](https://github.com/Djelibeybi/lifx-emulator/commit/933d22e8a6405b42f9839dd3310bc860d5ab9267))

- **security**: Update cookie to 0.7.0 to address CVE
  ([`dcb7460`](https://github.com/Djelibeybi/lifx-emulator/commit/dcb74608b4930422dec22fd098105ec5f74bd6f9))

### Features

- **dashboard**: Add live device visualizer with real-time state updates
  ([`51fbcc0`](https://github.com/Djelibeybi/lifx-emulator/commit/51fbcc0e17bafa51554594c146b884e35f96cfde))

- **visualizer**: Add dynamic grid layout with span-based sizing for matrix devices
  ([`9a7bb7e`](https://github.com/Djelibeybi/lifx-emulator/commit/9a7bb7e82e5fb0e403130b953bcc7024894fdc9c))

### Performance Improvements

- **frontend**: Improve dashboard performance for high-frequency updates
  ([`7433077`](https://github.com/Djelibeybi/lifx-emulator/commit/74330779872b806a5f2d4af6cd5c5899f39e5712))


## v4.2.0 (2026-02-03)

### Bug Fixes

- Address CodeRabbit PR review feedback
  ([`e302407`](https://github.com/Djelibeybi/lifx-emulator/commit/e302407e19f73de9a49361372b5c776b761d61e1))

- Correct $derived usage in ActivityLog.svelte for reactive filtering
  ([`a5e8280`](https://github.com/Djelibeybi/lifx-emulator/commit/a5e82809776e45a3f39f2b789fea3e5ca62185a7))

### Features

- **api**: Add WebSocket endpoint for real-time updates
  ([`b1e9889`](https://github.com/Djelibeybi/lifx-emulator/commit/b1e98893049109cbe3d016c550b16e65d6a6c955))

- **api**: Complete WebSocket real-time event infrastructure
  ([`81cfa6f`](https://github.com/Djelibeybi/lifx-emulator/commit/81cfa6f11dfb7d216b40d6672ba73883841be11a))

- **app**: Add PyApp binary distribution support (Phase 5)
  ([`3c893a8`](https://github.com/Djelibeybi/lifx-emulator/commit/3c893a866b0c0c1a5578bf45146994eec8c37493))

- **dashboard**: Add activity filtering and device toolbar (Phase 3)
  ([`249964a`](https://github.com/Djelibeybi/lifx-emulator/commit/249964ac782c0d38e7af7341302c3cb49d430ce9))

- **dashboard**: Add scenario panel, pagination, and tabbed interface (Phase 4)
  ([`a50951d`](https://github.com/Djelibeybi/lifx-emulator/commit/a50951d805592787ea70a86441e44c781e307c1c))

- **dashboard**: Replace vanilla JS with SvelteKit frontend
  ([`a143c2c`](https://github.com/Djelibeybi/lifx-emulator/commit/a143c2c0aee31a809a027fa010c5046492ecd243))


## v4.1.0 (2026-02-03)

### Features

- **api**: Add device state update, bulk create, and pagination
  ([`1f7bb46`](https://github.com/Djelibeybi/lifx-emulator/commit/1f7bb466ecf70cd8fd6a3e20f23ac49e00b2d709))


## v4.0.1 (2026-02-01)

### Bug Fixes

- **app**: Add products API, populate dashboard dropdown, remove stale TODOs
  ([`c49502a`](https://github.com/Djelibeybi/lifx-emulator/commit/c49502aa74d845b4e413761f081d06d157f27e6f))


## v4.0.0 (2026-02-01)

### Bug Fixes

- **app**: Pad zone_colors to zone_count with default color
  ([`46aed0a`](https://github.com/Djelibeybi/lifx-emulator/commit/46aed0a389bf2c6185fc9f07751fea3fbbf6e8d5))

- **app**: Preserve explicit empty devices/scenarios and truncate zone_colors
  ([`b5c420c`](https://github.com/Djelibeybi/lifx-emulator/commit/b5c420cb1a9bdc3cae3b6a7a373b4251828cfed5))

### Features

- **app**: Add YAML config file support for CLI
  ([`fceb9af`](https://github.com/Djelibeybi/lifx-emulator/commit/fceb9af1da6368a672cd24b58f68b2063b397c23))

### Breaking Changes

- **app**: No devices are created by default anymore.


## v3.1.0 (2026-01-11)

### Features

- Add Python 3.10 support
  ([`c19eee5`](https://github.com/Djelibeybi/lifx-emulator/commit/c19eee5181fc3e0e3b4ef9fc3e6d47308dce7a0f))


## v3.0.2 (2025-12-24)

### Bug Fixes

- **api**: Eliminate XSS vulnerabilities and extract dashboard JavaScript
  ([`8302a09`](https://github.com/Djelibeybi/lifx-emulator/commit/8302a0947b326e73f6c2f15de85986a464a307ad))


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
