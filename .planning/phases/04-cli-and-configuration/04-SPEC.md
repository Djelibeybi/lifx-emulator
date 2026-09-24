# Phase 4: CLI and Configuration — Specification

**Created:** 2026-09-24
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

The standalone `lifx-emulator` app can create Thread devices and configure the IPv6 bind, mDNS enablement and advertised mDNS addresses entirely from CLI flags and YAML, turns mDNS on automatically only when a Thread device is present, and reports mDNS advertisement lifecycle events in the activity stream — after `run()` has been decomposed with unchanged behaviour.

## Background

Phases 1–3 delivered the full core surface; the standalone app exposes none of it.

- **Core already provides:** `connectivity`, `mdns_enabled` and `mdns_address` on every factory and `DeviceBuilder.with_connectivity()` / `with_mdns()` (`factories/factory.py`, `factories/builder.py`); immutable `NetworkState` that rejects a Thread device with `mdns_enabled=False` and wrong-family addresses (`devices/states.py:128-138`); `EmulatedLifxServer(..., ipv6_bind_address="::1", mdns_enabled=False)` (`server.py:163-186`); a zeroconf-backed `MdnsResponder` (`mdns.py`) that advertises each device at its own `mdns_address` or else the matching-family bind address, rejecting wildcard binds (`mdns.resolve_address`, `mdns.py:36-50`).
- **IPv6 transport is always on in the core** (Phase 2 D: separate IPv4 and V6-only IPv6 sockets, IPv6 defaulting to `::1`, shipped in `lifx-emulator-core` 3.11.0). This phase does not change that.
- **App today:** `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` `run()` spans lines 580–1146 (~567 lines) and contains no Thread, IPv6 or mDNS options. `config.py` `EmulatorConfig` (`extra="forbid"`) has `bind`, `port`, API, count and `devices[]` keys; `DeviceDefinition` has no `connectivity`, `mdns` or `mdns_address`.
- **Activity:** `PacketEvent` (`devices/observers.py:15-34`) carries an integer LIFX `packet_type`; the WebSocket bridge wraps `ActivityLogger` (`api/services/event_bridge.py`). zeroconf answers queries internally, so the app never observes individual mDNS queries.
- **export-config** is a one-way migration tool from deprecated `--persistent` storage (`__main__.py:383-470`, `docs/cli/configuration.md:85-88`). It is intentionally untouched by this phase (CFG-03 dropped).
- **AR-06 (accepted in Phase 3):** on Linux, zeroconf may answer mDNS on an interface other than the selected one, so advertised records can be visible on a real LAN even with a loopback bind. This drove the "auto-on only with Thread devices" rule below.

## Requirements

1. **R1 — `run()` decomposition (HYG-03)**: `run()` is split into device-construction, storage, server-start and shutdown helpers, with unchanged CLI behaviour, landing as the first plan before any new flag.
   - Current: one ~567-line `run()` coroutine in `__main__.py`.
   - Target: `run()` delegates to named helpers; `run()` and every helper have cyclomatic complexity ≤ 10 and satisfy Ruff `max-args`/`max-branches`/`max-statements` without `# noqa`.
   - Acceptance: `ruff check .` passes with no new suppressions; the existing app test suite passes unchanged; a test shows identical flags produce identical devices (serials, products, order) before and after.

2. **R2 — Server-level CLI flags (CFG-01)**: The CLI accepts `--ipv6-bind ADDR`, `--mdns` / `--no-mdns`, `--mdns-ipv4-address ADDR` and `--mdns-ipv6-address ADDR`.
   - Current: none of these flags exist.
   - Target: `--ipv6-bind` defaults to `::1` and is passed to `EmulatedLifxServer(ipv6_bind_address=...)`; `--mdns`/`--no-mdns` are tri-state (unset = automatic, per R5); each flag appears in `--help` and in `docs/cli/cli-reference.md` / `docs/cli/configuration.md`; CLI values override the matching YAML keys.
   - Acceptance: `lifx-emulator --help` lists all four; a CLI value overrides the YAML value for each; an empty or non-IPv6 `--ipv6-bind`, or a wrong-family `--mdns-ipv4-address` / `--mdns-ipv6-address`, fails with an error naming the flag.

3. **R3 — Thread device count flags (CFG-01)**: `--thread N` creates N Thread devices of product `--thread-product PID` (default 91, LIFX Color).
   - Current: count flags create WiFi devices only; no Thread creation from the CLI.
   - Target: `--thread` defaults to 0; created devices have `connectivity == thread` and draw serials from the same sequence as the other count flags; any other Thread product mix or per-device `mdns_address` is YAML-only.
   - Acceptance: `--thread 2` yields two Thread devices of product 91; `--thread 1 --thread-product <valid PID>` yields that product; `--thread 0` creates none; a negative count is rejected; an unknown product ID fails with an error naming the ID; `--thread-product` without `--thread` creates nothing.

4. **R4 — YAML schema (CFG-02)**: `EmulatorConfig` accepts `ipv6_bind`, `mdns` (bool, optional), `mdns_ipv4_address`, `mdns_ipv6_address`, `thread` and `thread_product`; `DeviceDefinition` accepts `connectivity` (`wifi` | `thread`, default `wifi`), `mdns` (bool, default `true`) and `mdns_address`.
   - Current: none of these keys exist; `extra="forbid"` rejects them.
   - Target: all keys validated with `extra="forbid"` retained; the field name is `mdns_address` (matching the core, replacing the requirements' earlier `advertise_address`).
   - Acceptance: a YAML file with every new key loads and runs; an unknown key fails; a Thread device with `mdns: false` fails naming `mdns`; a wrong-family `mdns_address` fails naming `mdns_address`; an unknown `connectivity` fails naming `connectivity`.

5. **R5 — mDNS enablement rule (CFG-04)**: In the standalone app, mDNS turns on automatically if and only if at least one Thread device is configured (by flag or YAML); otherwise it is off unless `--mdns` / `mdns: true` is given.
   - Current: the app never enables mDNS.
   - Target: when mDNS is on, every device is advertised unless it sets `mdns: false` (WiFi only); explicit `--no-mdns` / `mdns: false` with any Thread device configured makes the app exit non-zero before binding any socket, with an error naming the Thread device serials.
   - Acceptance: a WiFi-only fleet with no mDNS option starts with mDNS disabled; the same fleet with `--mdns` advertises every device; a fleet with one Thread device and no mDNS option advertises all devices; a mixed fleet where a WiFi device sets `mdns: false` advertises the others only; `--no-mdns` with a Thread device exits non-zero and no socket is bound.

6. **R6 — Advertised address defaults (CFG-01/CFG-02)**: The server-level `mdns_ipv4_address` / `mdns_ipv6_address` are the advertised address for devices of the matching family that do not set their own `mdns_address`; a device's own `mdns_address` wins.
   - Current: the core falls back to the bind address and rejects wildcard binds; the app has no way to set either.
   - Target: the app supplies the server-level default per family to each device lacking its own address; when neither is set, the core's existing fallback to the concrete bind address applies.
   - Acceptance: a device without `mdns_address` is advertised at the server-level address of its family; a device with `mdns_address` is advertised at its own address; a `0.0.0.0` / `::` bind with the matching server-level address set starts successfully; a wildcard bind with no address for an advertised device's family fails startup with an error naming the device.

7. **R7 — mDNS lifecycle activity (CFG-05, narrowed)**: mDNS advertisement lifecycle events appear in `/api/activity` and on the WebSocket activity topic alongside LIFX packet events.
   - Current: no mDNS events reach the activity observer.
   - Target: events for device record registered, updated and withdrawn, and responder started, stopped and failed; individual mDNS queries and replies are **not** logged (zeroconf owns them).
   - Acceptance: starting with N advertised devices produces exactly N "registered" events plus one "started" event, visible in both `/api/activity` and the WebSocket activity topic; removing a device produces one "withdrawn" event; an injected responder failure produces one "failed" event.

8. **R8 — Library defaults unchanged (CFG-06, narrowed)**: Library users constructing `EmulatedLifxServer` without the new options see no behaviour change.
   - Current: core default `mdns_enabled=False`; IPv6 transport always on at `::1` (Phase 2, released).
   - Target: both defaults unchanged; all new behaviour lives in `lifx_emulator_app`.
   - Acceptance: the existing core test suite passes unchanged; a test asserts `EmulatedLifxServer(devices, manager)` starts with mDNS disabled.

## Boundaries

**In scope:**
- HYG-03 `run()` decomposition as the first plan
- CLI flags `--ipv6-bind`, `--mdns`/`--no-mdns`, `--mdns-ipv4-address`, `--mdns-ipv6-address`, `--thread`, `--thread-product`
- YAML keys on `EmulatorConfig` and `DeviceDefinition` listed in R4, with validation
- The auto-enable rule and the refuse-to-start rule in R5
- Server-level advertised address defaults in R6
- mDNS lifecycle events in the activity log and WebSocket activity topic
- CLI docs for every new flag and key, including a note on AR-06 LAN visibility under `--mdns`
- `lifx-emulator.example.yaml` updated with the new keys

**Out of scope:**
- `export-config` changes (CFG-03 dropped) — it is a migration tool for deprecated persistence; Thread devices are defined in YAML
- Persisting `mdns_enabled` / `mdns_address` — the persistence format is deprecated
- Per-query mDNS activity events — zeroconf answers queries internally; observing them means tapping traffic zeroconf owns
- Changing the core IPv6 default or adding an IPv6 off switch — Phase 2 settled it and it shipped in core 3.11.0
- One Thread count flag per device kind — `--thread` + `--thread-product` covers any product; mixes go in YAML
- Management API creation or reporting of Thread devices, including rejecting a Thread device created via API while mDNS is off — Phase 5 (API-01..03)
- Dashboard (Svelte) changes to display mDNS events specially — beyond the existing activity rendering
- Changes to generated files (`protocol/packets.py`, `products/registry.py`)

## Constraints

- Complexity ≤ 10, Ruff `max-args = 5` (the app's cyclopts `run()` signature follows the existing flag pattern), Pyright standard, no new `# noqa` / `# type: ignore`.
- `EmulatorConfig` and `DeviceDefinition` keep `extra="forbid"`.
- Core library (`lifx_emulator`) gains no app-specific behaviour; mDNS lifecycle events may need a core observer hook, which must stay optional with a no-op default so library behaviour is unchanged (R8).
- Asyncio only in the packet path; Python 3.10–3.14 on Linux/macOS/Windows.
- Australian English in docs and messages; conventional commits with `app-` / `core-` scopes, signed with `-s`.
- Address validation reuses the core's `validate_mdns_address` and `coerce_connectivity` rules rather than re-implementing them.

## Acceptance Criteria

- [ ] `ruff check .` and `pyright` pass with `run()` and all new helpers at complexity ≤ 10 and no new suppressions
- [ ] Existing app and core test suites pass unchanged
- [ ] Identical legacy flags produce identical devices (serials, products, order) before and after the `run()` refactor
- [ ] A run with no devices still logs the existing "no devices" warning and starts
- [ ] Shutdown order (storage flush, then `server.stop()` including mDNS, then API task cancel; `__main__.py:1134-1144`) is unchanged, asserted by a test
- [ ] `lifx-emulator --help` lists `--ipv6-bind`, `--mdns`/`--no-mdns`, `--mdns-ipv4-address`, `--mdns-ipv6-address`, `--thread`, `--thread-product`
- [ ] Each new flag overrides its YAML key; `--no-mdns` overrides `mdns: true` and `--mdns` overrides `mdns: false`
- [ ] An empty or non-IPv6 `--ipv6-bind`, or a wrong-family advertised-address flag, fails with an error naming the flag
- [ ] `--thread 2` creates two Thread devices of product 91; `--thread-product` selects another valid product
- [ ] `--thread 0` creates none; a negative `--thread` is rejected; an unknown `--thread-product` fails naming the ID; `--thread-product` alone creates nothing
- [ ] A YAML file using every new key loads and runs
- [ ] YAML validation errors name the field for: unknown key, Thread `mdns: false`, wrong-family `mdns_address`, empty-string `mdns_address`, unknown `connectivity`
- [ ] `mdns_address: null` is treated as unset; `connectivity` accepts the same casing as the core's `coerce_connectivity`
- [ ] A WiFi-only fleet with no mDNS option starts with mDNS disabled
- [ ] A WiFi-only fleet with `--mdns` advertises every device; with `--no-mdns` it starts normally; no devices plus `--no-mdns` starts
- [ ] Any fleet containing a Thread device, with no mDNS option, advertises every device except WiFi devices set to `mdns: false`
- [ ] `--no-mdns` / `mdns: false` with a Thread device exits non-zero before any socket is bound, naming the Thread serials
- [ ] Devices without `mdns_address` are advertised at the server-level address of their family; a device's own `mdns_address` wins
- [ ] A wildcard bind starts when the matching server-level advertised address is set, and fails naming the device when it is not
- [ ] N advertised devices at startup produce exactly N "registered" events and one "started" event in `/api/activity` and on the WebSocket activity topic
- [ ] Removing an advertised device produces one "withdrawn" event; an injected responder failure produces one "failed" event
- [ ] A failing WebSocket consumer does not stop mDNS or LIFX serving
- [ ] `EmulatedLifxServer(devices, manager)` with no new options starts with mDNS disabled
- [ ] MUST NOT: with no advertised-address option or per-device `mdns_address` set, no record advertises an address other than the loopback bind addresses (`127.0.0.1` / `::1`)
- [ ] MUST NOT: a CLI invocation or YAML file using none of the new keys produces devices differing from today's (serials, products, firmware, WiFi connectivity) or starts mDNS
- [ ] MUST NOT: an invalid Thread definition is ever created as a WiFi device; it errors instead

## Edge Coverage

**Coverage:** 22/22 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | 🧪 backstop | Legacy-flag equivalence test (same devices, serials, order) plus the existing CLI suite |
| empty | R1 | ✅ covered | AC: no devices still warns and starts |
| ordering | R1 | 🧪 backstop | Shutdown-order test (storage flush, then `server.stop()` including mDNS, then API task cancel; `__main__.py:1134-1144`) |
| adjacency | R2 | ✅ covered | AC: each flag overrides YAML; `--mdns`/`--no-mdns` both directions |
| empty | R2 | ✅ covered | AC: empty/non-IPv6/wrong-family address flags fail naming the flag |
| ordering | R2 | ⛔ dismissed | Flag order has no meaning in cyclopts parsing |
| boundary | R3 | ✅ covered | AC: `--thread 0` creates none; negative rejected |
| precision | R3 | ⛔ dismissed | Integer counts only; no precision surface |
| validation (added) | R3 | ✅ covered | AC: unknown `--thread-product` fails naming the ID; `--thread-product` alone creates nothing |
| empty | R4 | ✅ covered | AC: `mdns_address: null` = unset; empty string fails naming the field |
| encoding | R4 | 🧪 backstop | Accept exactly what `validate_mdns_address` accepts; held-out test with a scoped (zone-ID) IPv6 address |
| encoding (added) | R4 | ✅ covered | AC: `connectivity` casing follows `coerce_connectivity`; unknown value names `connectivity` |
| adjacency | R5 | ✅ covered | AC: WiFi-only fleet with `--no-mdns` starts normally |
| empty | R5 | ✅ covered | AC: no devices plus `--no-mdns` starts |
| ordering | R5 | ⛔ dismissed | A Thread device added via API while mDNS is off belongs to Phase 5 (API-03) |
| concurrency | R5 | ⛔ dismissed | The refuse-to-start check runs once at startup, before binding |
| idempotency | R6 | ⛔ dismissed | Address re-resolution on mDNS retry is owned by the Phase 3 responder retry |
| concurrency | R6 | ⛔ dismissed | Addresses are resolved once at startup; no concurrent writers |
| adjacency (implied) | R6 | ✅ covered | AC: wildcard bind starts with the matching server-level address set |
| concurrency | R7 | ✅ covered | AC: N devices → exactly N "registered" events |
| concurrency (added) | R7 | 🧪 backstop | Held-out test: a failing WebSocket consumer does not stop mDNS or LIFX serving (reuses Phase 3 isolated listeners) |
| unclassified | R8 | ✅ covered | AC: core suite unchanged; `EmulatedLifxServer` defaults to mDNS disabled |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| P1: MUST NOT advertise any address other than the loopback bind addresses unless the user sets an advertised-address option or per-device `mdns_address` | R5, R6 | resolved | test |
| P3: MUST NOT change the devices produced by, or start mDNS for, a CLI/YAML setup using none of the new keys | R1, R4, R5 | resolved | test |
| P4: MUST NOT silently create an invalid Thread definition as a WiFi device | R3, R4 | resolved | test |

Canon referral: YAML deserialisation safety is canon — owned by `/gsd-secure-phase` + Bandit (`yaml.safe_load` already in use); not minted here.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Conflicts with Phase 2 IPv6 default and zeroconf resolved     |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | CFG-03 dropped; per-query events and API work excluded        |
| Constraint Clarity | 0.75  | 0.65 | ✓      | Core observer hook must stay optional/no-op                   |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 26 pass/fail criteria including 3 negative                    |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      |                                                              |

## Interview Log

| Round | Perspective     | Question summary | Decision locked |
|-------|-----------------|------------------|-----------------|
| 1 | Researcher | CFG-06 vs the Phase 2 always-on IPv6 default | IPv6 stays always on; CFG-06 covers mDNS only; the CLI/YAML only choose the IPv6 bind address |
| 1 | Researcher | What CFG-05 must show, given zeroconf owns queries | Advertisement lifecycle events only; no per-query events |
| 1 | Researcher | What export-config runs against and is for | Offline migration tool for deprecated persistence → CFG-03 dropped |
| 1 | Researcher | `advertise_address` vs core `mdns_address` | `mdns_address` everywhere |
| 2 | Simplifier | Thread creation from flags | Count flags; then locked as `--thread N` + `--thread-product PID` (default 91) |
| 2 | Boundary Keeper | Server-level advertised address shape | Two family defaults: `--mdns-ipv4-address`, `--mdns-ipv6-address` |
| 2 | Failure Analyst | `--no-mdns` with Thread devices | Refuse to start, non-zero, before binding, naming the devices |
| Probe | Failure Analyst | AR-06 LAN leak with mDNS on by default | mDNS auto-on only when a Thread device is configured; otherwise requires `--mdns` |
| Probe | Boundary Keeper | WiFi devices in a mixed fleet | Advertised by default unless `mdns: false` |
| Probe | Failure Analyst | Edge and prohibition resolutions | 22 edges and P1/P3/P4 accepted as proposed |

## Follow-ups for planning artifacts

**Done 2026-09-24.** REQUIREMENTS.md and ROADMAP.md were aligned with this spec: drop CFG-03 and roadmap success criterion 3; rename `advertise_address` → `mdns_address`; narrow CFG-05 to lifecycle events; replace CFG-04's "on for every device by default" with the Thread-triggered auto-enable rule; narrow CFG-06 and roadmap success criterion 5 to "app auto-enables mDNS when a Thread device is configured; IPv6 is always on (Phase 2)". Phase 5's API-01 and success criteria were also renamed to `mdns_address`.

---

*Phase: 04-cli-and-configuration*
*Spec created: 2026-09-24*
*Next step: /gsd-discuss-phase 4 — implementation decisions (how to build what's specified above)*
