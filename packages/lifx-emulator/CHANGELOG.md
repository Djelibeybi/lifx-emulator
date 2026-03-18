# CHANGELOG

<!-- version list -->

## v4.4.0 (2026-03-18)

### Bug Fixes

- **frontend**: Add aria-expanded and aria-label to collapse buttons
  ([`8ffc547`](https://github.com/Djelibeybi/lifx-emulator/commit/8ffc547e32a594952f9296ef9850093100460bfe))

- **frontend**: Add fallback for tile width/height in card calculations
  ([`69499ea`](https://github.com/Djelibeybi/lifx-emulator/commit/69499ea3c879fe86145048f2a0e9aa5e219020d3))

- **frontend**: Add full ARIA tab semantics to ScenarioPanel scope tabs
  ([`514f333`](https://github.com/Djelibeybi/lifx-emulator/commit/514f333297e9dde37d5efc8260c8e0ba7c7d397d))

- **frontend**: Add keyboard navigation to tablist
  ([`e0b1a2b`](https://github.com/Djelibeybi/lifx-emulator/commit/e0b1a2bbc73654fa6d791c6bdebc0258776ad01b))

- **frontend**: Derive auto-compact collapsed state from current devices
  ([`9029c55`](https://github.com/Djelibeybi/lifx-emulator/commit/9029c5598b04fa53cb8a956a9174f20014d7a4e6))

- **frontend**: Display products error state in DeviceToolbar
  ([`2cf142a`](https://github.com/Djelibeybi/lifx-emulator/commit/2cf142a657339e9f3f147651b128349f0b73dd3d))

- **frontend**: Explicitly type edge arrays as HsbkColor[]
  ([`e21e837`](https://github.com/Djelibeybi/lifx-emulator/commit/e21e837ba6d006d8ae2aedae81f4a2557a7f06c9))

- **frontend**: Expose isLoading from products store
  ([`2365e6d`](https://github.com/Djelibeybi/lifx-emulator/commit/2365e6d2fb5e1cdfee094ab958e8adccb9c50d29))

- **frontend**: Fix expandAllViz in auto-compact mode
  ([`1a8bd31`](https://github.com/Djelibeybi/lifx-emulator/commit/1a8bd31762a309ca02286bb3ca5260c0be892ca5))

- **frontend**: Guard glow edge extraction against invalid tile dimensions
  ([`bd0a0df`](https://github.com/Djelibeybi/lifx-emulator/commit/bd0a0df528fff732ae6d91bab275ab2667d0b420))

- **frontend**: Handle errors in products store load()
  ([`cda2b4b`](https://github.com/Djelibeybi/lifx-emulator/commit/cda2b4b11fe8d0ad830e1a27d66977d23163cd70))

- **frontend**: Make loaded/loading reactive with $state in products store
  ([`ea671a1`](https://github.com/Djelibeybi/lifx-emulator/commit/ea671a1e835a3ff52ce5d608b334711c6810b59d))

- **frontend**: Use flex-start instead of start for cross-browser compat
  ([`45377db`](https://github.com/Djelibeybi/lifx-emulator/commit/45377db693160cd2637e1d068bcdb14f5a362640))

- **frontend**: Use stable tabpanel ID for aria-controls
  ([`3ea070e`](https://github.com/Djelibeybi/lifx-emulator/commit/3ea070e0e1c352950163b527885ea7cfa0047594))

- **frontend**: Use void for fire-and-forget products.load() call
  ([`efa6214`](https://github.com/Djelibeybi/lifx-emulator/commit/efa621468b3be3960688ec2fcf6f08916ccf5553))

### Features

- **frontend**: Content-based card widths, auto-compact layout, and responsive fixes
  ([`cacd2a4`](https://github.com/Djelibeybi/lifx-emulator/commit/cacd2a4e92e7eac9db9b4c1efa28e185e8b954c6))

- **frontend**: Overhaul visualizer with Oklch color, ambilight glow, and compact layout
  ([`fcc7534`](https://github.com/Djelibeybi/lifx-emulator/commit/fcc753492b34be46c492e6a92758bba5d60dec2a))

### Performance Improvements

- **frontend**: Memoize hsbkToCss() for render loop performance
  ([`d10f39b`](https://github.com/Djelibeybi/lifx-emulator/commit/d10f39b86989f98304df52c607d22dd1e5e2c744))

- **frontend**: Memoize hsbkToLinearRgb for glow calculation performance
  ([`d4e3151`](https://github.com/Djelibeybi/lifx-emulator/commit/d4e3151d30df3e9278d75722ca1cc25f53764f3b))

- **frontend**: Use half-eviction instead of full cache clear
  ([`8ebc522`](https://github.com/Djelibeybi/lifx-emulator/commit/8ebc5229c829c90f61ca9f5dc1c469dd05f1426a))


## v4.3.1 (2026-03-18)

### Bug Fixes

- **dashboard**: Broadcast metadata changes via WebSocket for live updates
  ([`6b933ae`](https://github.com/Djelibeybi/lifx-emulator/commit/6b933aed9fff0ba3231b8e9913160cdac5ae62cf))

### Documentation

- **event-bridge**: Add metadata to _get_change_category return values
  ([`15e2dd1`](https://github.com/Djelibeybi/lifx-emulator/commit/15e2dd10a3a71b8fb242314c71aa34da78e5e1d0))


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
