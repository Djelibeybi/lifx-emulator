# Phase 4: CLI and Configuration - Context

**Gathered:** 2026-09-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The standalone `lifx-emulator` app exposes the Phase 1–3 core surface: Thread devices, the IPv6 bind address, mDNS enablement and advertised mDNS addresses, all configurable from CLI flags and YAML. mDNS turns on automatically only when a Thread device is configured, and mDNS advertisement lifecycle events appear in the activity stream. The `run()` coroutine is decomposed first, with unchanged behaviour.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `04-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `04-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- HYG-03 `run()` decomposition as the first plan
- CLI flags `--ipv6-bind`, `--mdns`/`--no-mdns`, `--mdns-ipv4-address`, `--mdns-ipv6-address`, `--thread`, `--thread-product`
- YAML keys on `EmulatorConfig` and `DeviceDefinition` listed in R4, with validation
- The auto-enable rule and the refuse-to-start rule in R5
- Server-level advertised address defaults in R6
- mDNS lifecycle events in the activity log and WebSocket activity topic
- CLI docs for every new flag and key, including a note on AR-06 LAN visibility under `--mdns`
- `lifx-emulator.example.yaml` updated with the new keys

**Out of scope (from SPEC.md):**
- `export-config` changes (CFG-03 dropped)
- Persisting `mdns_enabled` / `mdns_address`
- Per-query mDNS activity events
- Changing the core IPv6 default or adding an IPv6 off switch
- One Thread count flag per device kind
- Management API creation or reporting of Thread devices (Phase 5)
- Dashboard (Svelte) changes to display mDNS events specially
- Changes to generated files (`protocol/packets.py`, `products/registry.py`)

</spec_lock>

<decisions>
## Implementation Decisions

### Server-level advertised address (R6)
- **D-01:** Server-level advertised addresses are a **core** feature: `EmulatedLifxServer` gains optional `mdns_ipv4_address: str | None = None` and `mdns_ipv6_address: str | None = None`. `mdns.resolve_address()` uses the matching-family server default when a device has no `mdns_address`, and falls back to the concrete bind address only when that default is also `None`. A device's own `mdns_address` always wins. With both defaults `None` the core behaves exactly as today (R8). The app passes `--mdns-ipv4-address` / `--mdns-ipv6-address` (and YAML equivalents) straight through; it does **not** write them into each device's `mdns_address`. This keeps the distinction between an explicit device address and an inherited one, and Phase 5 API-created devices inherit the default with no extra work. — **Reversibility:** costly — the constructor parameters and properties become published `lifx-emulator-core` API.
- **D-02:** The server-level addresses are validated in `EmulatedLifxServer.__init__` with the core's `validate_mdns_address` against the matching family, fixed for the server's lifetime, and exposed as read-only `mdns_ipv4_address` / `mdns_ipv6_address` properties. There is no setter or runtime re-advertisement (consistent with Phase 3 D-04). — **Reversibility:** costly — public read-only property names.
- **D-03:** If any advertised-address option (server-level or per-device `mdns_address`) is set but mDNS resolves to off (e.g. a WiFi-only fleet with no `--mdns`), the app logs one `WARNING` saying the address is ignored because mDNS is disabled, and starts normally. Setting an address never turns mDNS on; R5 remains the only enablement rule.

### mDNS activity event shape (R7)
- **D-04:** mDNS lifecycle events reuse the existing activity schema. Every current `ActivityEvent` field keeps its name and type. mDNS events set `direction: "mdns"`, `packet_type: 0`, a human-readable `packet_name` (e.g. `"mDNS registered"`, `"mDNS updated"`, `"mDNS withdrawn"`, `"mDNS started"`, `"mDNS stopped"`), `device` set to the serial for per-device events, and `addr` set to the advertised address. An additive optional `kind` field (`"lifx"` default, `"mdns"` for these events) goes on the API `ActivityEvent` model and the WebSocket payload so consumers can filter without relying on the sentinel. The dashboard renders them through the existing activity rendering (no Svelte change beyond what the existing types need). — **Reversibility:** costly — `kind` and the `direction: "mdns"` value become part of the `/api/activity` and WebSocket contract.
- **D-05:** Responder-level events (started, stopped, failed) have `device` and `target` set to `None` and `addr` set to the IPv4/IPv6 bind addresses. A failure event carries a short reason in `packet_name` as `"mDNS failed: <error summary>"`. The full error stays in the log and in `server.mdns_error`. No new `detail` field.
- **D-06:** After a successful `retry_mdns()` recovery, the events match a fresh start: one "started" event, then one "registered" event per advertised device. "updated" is reserved for a reconcile that changes the data of an existing record.

### Core observer hook (R7, R8)
- **D-07:** The core emits mDNS events through a new optional observer method `on_mdns_event(event)`, implemented on `ActivityLogger`, `NullObserver` and the app's `WebSocketActivityObserver`. The server calls it via `getattr(observer, "on_mdns_event", None)`, so third-party `ActivityObserver` implementations that define only the two packet methods keep working unchanged. The events go into the same `ActivityLogger` deque that `/api/activity` reads, and the WebSocket decorator forwards them on the activity topic. Library users with the default `ActivityLogger` see mDNS events once they enable mDNS; with mDNS off (the default) no events are produced. — **Reversibility:** costly — a new optional method on a published observer protocol.
- **D-08:** The event type is the existing `PacketEvent` dataclass with a new field `kind: str = "lifx"`. mDNS events are constructed with `kind="mdns"`, `direction="mdns"` and `packet_type=0`. The addition is backwards compatible for existing constructors and keeps one type in the logger deque and a one-to-one mapping to the API `ActivityEvent`.
- **D-09:** Settled defaults: every `on_mdns_event` call is wrapped so an observer exception is logged and never stops mDNS or LIFX serving (the SPEC's failing-WebSocket-consumer backstop). mDNS events do not increment the LIFX packet statistics (`packets_received_by_type`, `packets_sent_by_type`).

### `run()` decomposition and startup flow (R1, R5, R6)
- **D-10:** The helpers extracted from `run()` move into new focused app modules beside `config.py`, for example a `lifx_emulator_app/startup/` package with modules for device construction, storage setup, and server start/shutdown (exact names at planner discretion). `__main__.py` keeps the cyclopts command definitions and a thin `run()` that delegates. HYG-03 is still the first plan and adds no new flags.
- **D-11:** `_load_merged_config()` (or its replacement) returns a typed frozen settings object (e.g. a `RunSettings` dataclass) instead of the current `dict`. It carries the resolved values plus provenance for the options where it matters, in particular whether `mdns` came from a CLI flag, from YAML or from neither (the R5 tri-state). Helpers take this object, which lets Pyright check every key and lets errors name the CLI flag (`--ipv6-bind`) or the YAML key (`ipv6_bind`) according to where the value came from.
- **D-12:** All pre-bind checks run in one preflight step after the devices are constructed and before any socket, storage or API task is opened. The preflight covers the R5 refuse-to-start check (explicit `--no-mdns` / `mdns: false` with Thread devices), the R6 wildcard-bind check (a wildcard bind with no server-level address for an advertised device's family) and the D-03 warning. It collects every problem, i.e. all Thread serials and every device lacking an address, into one error message, then exits non-zero. Field-local problems that YAML alone decides (unknown key, Thread `mdns: false` on a device, wrong-family `mdns_address`, unknown `connectivity`) still fail in the Pydantic models, per R4.
- **D-13:** R1 equivalence is proven with a golden snapshot committed **before** `run()` is touched (same approach as Phase 1 D-11/D-12). The snapshot records (serial, product, firmware, connectivity, order) for a matrix of legacy flag and YAML combinations as inline test constants, and the refactored code must reproduce them exactly. `--thread` devices take serials after all existing count-flag kinds, so legacy serials never shift (P3).

### Claude's Discretion
- Whether the responder or the server raises each mDNS lifecycle event, provided the counts in R7 and D-06 hold.
- Exact module and helper names under the new app startup package, and the name and fields of the settings dataclass.
- Exact `packet_name` wording for each lifecycle action, and how `addr` formats multiple bind addresses for responder-level events.
- Whether `--thread-product` checks up front that the product is Thread-capable, or relies on the core's existing firmware ceiling and factory errors, provided the error names the product ID (R3).
- How to make the preflight failure exit non-zero. Research must verify whether cyclopts turns `run()` returning `False` into a non-zero exit code; the current error paths `print(...)` and `return False`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** Paths are relative to the repository root.

### Requirements and prior decisions
- `.planning/phases/04-cli-and-configuration/04-SPEC.md` — locked requirements (R1–R8), boundaries, acceptance criteria, edge and prohibition coverage. MUST read before planning.
- `.planning/phases/03-mdns-responder/03-CONTEXT.md` — Phase 3 decisions D-01..D-08 (opt-in server mDNS, fixed device settings, `mdns_status`, `retry_mdns`, fleet-dependent failure policy).
- `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md` — IPv6 always on, atomic startup/rollback (D-09/D-10), task tracker (D-13..D-16).
- `.planning/phases/01-thread-device-identity/01-CONTEXT.md` — `Connectivity` enum and coercion (D-01..D-03), golden byte-fixture approach (D-11/D-12).
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` — note that REQUIREMENTS/ROADMAP still carry pre-spec wording (`advertise_address`, CFG-03, per-query CFG-05). SPEC.md supersedes them (see SPEC "Follow-ups for planning artifacts").

### Core surface to extend
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` — `EmulatedLifxServer.__init__` (`ipv6_bind_address`, `mdns_enabled`, `activity_observer`), mDNS start/stop/retry and `resolve_address` call sites.
- `packages/lifx-emulator-core/src/lifx_emulator/mdns.py` — `resolve_address()` (D-01 fallback change), `MdnsResponder` start/reconcile/stop (event emission points).
- `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` — `PacketEvent`, `ActivityObserver`, `ActivityLogger`, `NullObserver` (D-07/D-08).
- `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py` — `coerce_connectivity` (line 70) and `validate_mdns_address` (line 91), which the app reuses for validation.
- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py`, `factories/builder.py` — `connectivity`, `mdns_enabled`, `mdns_address` factory arguments.

### App surface to change
- `packages/lifx-emulator/src/lifx_emulator_app/__main__.py` — `run()` (lines 580–1146), `_load_merged_config()` (line 472), count-flag device construction and serial sequence.
- `packages/lifx-emulator/src/lifx_emulator_app/config.py` — `EmulatorConfig`, `DeviceDefinition` (`extra="forbid"`), `merge_config`, `resolve_config_path`.
- `packages/lifx-emulator/src/lifx_emulator_app/api/models.py` — `ActivityEvent` (additive `kind`).
- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` — `WebSocketActivityObserver` (forward `on_mdns_event`).
- `packages/lifx-emulator/frontend/src/lib/types.ts` — `ActivityEvent.direction` is typed `'rx' | 'tx'` and may need widening. `ActivityLog.svelte` renders `direction.toUpperCase()`.
- `docs/cli/cli-reference.md`, `docs/cli/configuration.md`, `docs/cli/websocket-api.md`, `lifx-emulator.example.yaml` — docs and example to update.

### Tests to preserve and extend
- `packages/lifx-emulator/tests/test_cli.py`, `test_cli_validation.py`, `test_config.py`, `test_websocket.py`, `test_api.py` — existing app suites that must pass unchanged.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `coerce_connectivity` / `validate_mdns_address` (`devices/states.py`): the single source of validation rules for YAML, CLI and the new server-level addresses.
- `ActivityLogger` deque plus `server.get_recent_activity()`: `/api/activity` already reads from it, so mDNS events stored there need no router change.
- `WebSocketActivityObserver` (`event_bridge.py`): a decorator over `ActivityLogger` that already fans activity out to the WS topic with isolated consumers (Phase 3).
- `DeviceLifecycleListener` / `IDeviceLifecycleSource` (`devices/manager.py`): an existing non-displacing listener pattern that the responder already uses for membership changes.

### Established Patterns
- `EmulatorConfig` / `DeviceDefinition` use `extra="forbid"`, and validators follow the `msg = ...; raise ValueError(msg)` style.
- CLI overrides YAML through `merge_config`; `devices` and `scenarios` are carried separately from CLI kwargs.
- CLI error paths currently `print()` and `return False`. Whether that exits non-zero is unverified (see Discretion).
- Complexity ≤ 10 and no `# noqa`: extract `_helper()` functions rather than suppressing.

### Integration Points
- `EmulatedLifxServer(...)` construction in `run()`: add `mdns_enabled`, `ipv6_bind_address`, `mdns_ipv4_address`, `mdns_ipv6_address`.
- The count-flag device loop in `run()`: add `--thread` after the existing kinds so serials don't shift.
- Shutdown sequence (API task, then server/mDNS, then storage flush): order must stay unchanged and be asserted by a test.

</code_context>

<specifics>
## Specific Ideas

- The golden-snapshot approach deliberately mirrors Phase 1's byte-fixture commit: the evidence commit comes before the behaviour-preserving refactor in history.
- mDNS events should look like ordinary rows in the existing dashboard activity log (`MDNS` in the direction column), not a new UI.

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within the phase scope. (API reporting of the server-level advertised addresses via the D-02 properties is Phase 5 work that already exists on the roadmap.)

</deferred>

---

*Phase: 04-cli-and-configuration*
*Context gathered: 2026-09-24*
