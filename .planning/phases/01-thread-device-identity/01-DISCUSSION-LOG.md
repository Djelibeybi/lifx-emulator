# Phase 1: Thread Device Identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-09
**Phase:** 01-thread-device-identity
**Areas discussed:** Connectivity type, Firmware rule placement, Immutability mechanism, Byte fixtures and test layout

---

## Connectivity type

| Option | Description | Selected |
|--------|-------------|----------|
| `Connectivity(str, Enum)` | `WIFI = "wifi"`, `THREAD = "thread"`; mirrors lifx-async; Pydantic-friendly | ✓ |
| Plain lowercase `str` | Validated against `{"wifi", "thread"}` at the write site | |
| `typing.Literal` alias | Typing only, runtime validation at the write site | |

**User's choice:** `Connectivity(str, Enum)`

| Option | Description | Selected |
|--------|-------------|----------|
| `devices/states.py`, exported from `lifx_emulator` and `lifx_emulator.devices` | Beside `NetworkState`, both `__all__` lists | ✓ |
| New `devices/connectivity.py` | Own leaf module re-exported through the barrel | |
| `constants.py` | Next to protocol constants, top-level export only | |

**User's choice:** `devices/states.py` with both exports

| Option | Description | Selected |
|--------|-------------|----------|
| `Connectivity \| str \| None`, default `None` | None = unspecified; strings coerced via `Connectivity(value)` | ✓ |
| `Connectivity \| str`, default `"wifi"` | Explicit string default, None rejected | |
| `Connectivity` only | Enum required, strings raise | |

**User's choice:** `Connectivity | str | None = None`
**Notes:** None

---

## Firmware rule placement

| Option | Description | Selected |
|--------|-------------|----------|
| `specs.yml` `max_firmware` keys; rejection derived | `max_firmware_major/minor` on `ProductSpecs`, 3/50 on pid 55; Thread rejected because ceiling < floor | ✓ |
| `max_firmware` keys plus `thread_capable: false` | Ceiling and a separate boolean on pid 55 | |
| Hard-coded pid 55 checks in `FirmwareConfig` | `_TILE_PID = 55` and inline checks | |

**User's choice:** `specs.yml` `max_firmware` keys with derived rejection

| Option | Description | Selected |
|--------|-------------|----------|
| `FirmwareConfig` class constants | `VERSION_THREAD = (4, 200)` beside `VERSION_EXTENDED` / `VERSION_LEGACY` | ✓ |
| `specs.yml` top-level key | `thread_min_firmware` read by `SpecsRegistry` | |
| `constants.py` | `LIFX_THREAD_MIN_FIRMWARE` next to protocol constants | |

**User's choice:** `FirmwareConfig` class constants

| Option | Description | Selected |
|--------|-------------|----------|
| `FirmwareConfig.get_firmware_version()` with a `connectivity` argument | One precedence chain then floor/ceiling checks | ✓ |
| `DeviceBuilder.build()` after resolution | Builder applies Thread default and validates in a helper | |
| `NetworkState` / `DeviceState` construction | Validate when the state is composed | |

**User's choice:** `FirmwareConfig.get_firmware_version()` with `connectivity`
**Notes:** None

---

## Immutability mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen `NetworkState`, replaced wholesale | `@dataclass(frozen=True)`; `dataclasses.replace()` at build time; facade translates `FrozenInstanceError` to `ValueError` | ✓ |
| Guard in `DeviceState.__setattr__` | Read-only set in the routing facade; direct sub-state write still works | |
| Read-only property on `NetworkState` | `_connectivity` backing field, no setter | |

**User's choice:** Frozen `NetworkState`

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit argument wins; `None` defers to disk | Explicit value overrides saved state with a WARNING on mismatch | ✓ |
| Disk always wins | Saved state authoritative once persistence is on | |
| Mismatch raises | Configuration error, fail fast | |

**User's choice:** Explicit argument wins; `None` defers to disk

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve connectivity first, then derive everything once | New builder step 0 before firmware resolution | ✓ |
| Restore then re-derive | Keep restore at step 11 and add a re-derivation pass | |
| Persist the derived values too | Save firmware and `wifi_signal` alongside connectivity | |

**User's choice:** Resolve connectivity first
**Notes:** Scouting showed `StateRestorer` runs after firmware, `wifi_signal` and the sensor flag are resolved, which motivated the ordering question.

---

## Byte fixtures and test layout

| Option | Description | Selected |
|--------|-------------|----------|
| Inline hex literals in the test module | `bytes.fromhex` constants commented with the capturing commit | ✓ |
| `tests/fixtures/*.bin` files | Binary files via `Path.read_bytes()` | |
| Generate at test time from a copied legacy packer | Frozen copy of today's `pack()` in the test module | |

**User's choice:** Inline hex literals

| Option | Description | Selected |
|--------|-------------|----------|
| Run current `main` once, paste, annotate with commit hash | Fixture commit precedes the `header.py` change | ✓ |
| Hand-derive from the protocol spec | Independent of old code, more error-prone | |

**User's choice:** Run `main` once and paste

| Option | Description | Selected |
|--------|-------------|----------|
| New identity suite plus module-local additions | `test_thread_identity.py` and `test_header.py` plus cases in existing modules | ✓ |
| Single new module for everything | All Phase 1 tests in `test_thread_identity.py` | |
| Spread across existing modules only | No new test files | |

**User's choice:** New identity suite plus module-local additions
**Notes:** None

---

## Claude's Discretion

- Location of the bad-persisted-value WARNING (builder step 0 or restorer helper)
- Name and location of the string-to-enum coercion helper
- How the tile-firmware mirror reads the host version in `EmulatedLifxDevice.__init__`
- Header-template stamping as the single point for bit 3 (research recommendation)
- Test serials and any new `conftest.py` fixtures
- `Connectivity.__str__` and `.value` use in log lines for Python 3.10 compatibility

## Deferred Ideas

- Wiring the `firmware_version` scenario into firmware replies (dead code today)
- Persisting `firmware_version` and `advertised_services`
- A `thread_capable` per-product spec key
