# Phase 4: CLI and Configuration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-24
**Phase:** 04-cli-and-configuration
**Areas discussed:** Server-level mDNS address, mDNS event shape, Core observer hook, run() decomposition layout

Requirements were locked by `04-SPEC.md` (8 requirements), so only implementation decisions were discussed.

---

## Server-level mDNS address

**Q1: How should `--mdns-ipv4-address` / `--mdns-ipv6-address` reach devices without their own `mdns_address`?**

| Option | Description | Selected |
|--------|-------------|----------|
| Core server fallback | Optional per-family parameters on `EmulatedLifxServer`, used by `resolve_address()` before the bind address | ✓ |
| App writes it into each device | App passes the family default as `mdns_address=` when it creates each device; no core change | |

**Q2: Advertised address set but mDNS ends up off?**

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and start | Log a WARNING that the address is ignored; start | ✓ |
| Imply --mdns | Any advertised-address setting turns mDNS on | |
| Fail startup | Exit non-zero naming the conflicting option | |

**Q3: Can the server-level addresses be changed or read after construction?**

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed, read-only properties | Validated in `__init__`, exposed read-only | ✓ |
| Fixed, private | Constructor only, no accessor | |
| Mutable at runtime | Setter re-advertises affected devices | |

---

## mDNS event shape

**Q1: How do mDNS events fit the `ActivityEvent` schema?**

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse schema + additive `kind` | `direction: "mdns"`, `packet_type: 0`, label in `packet_name`, plus optional `kind` | ✓ |
| Reuse schema, no new field | Consumers tell the events apart by `direction == "mdns"` | |
| New event model | Separate `MdnsEvent` in a union; `packet_type` optional | |

**Q2: Responder-level event fields and failure reason?**

| Option | Description | Selected |
|--------|-------------|----------|
| device=None, reason in packet_name | `addr` = bind addresses; `"mDNS failed: <summary>"` | ✓ |
| Add optional `detail` field | Fixed label plus a new `detail` field | |
| You decide | Leave it to planning | |

**Q3: Events after `retry_mdns()` recovery?**

| Option | Description | Selected |
|--------|-------------|----------|
| started + registered per device | Recovery looks like a fresh start | ✓ |
| started only | One event only | |
| You decide | Follow the reconcile path | |

---

## Core observer hook

**Q1: How does the core emit mDNS lifecycle events?**

| Option | Description | Selected |
|--------|-------------|----------|
| Optional `on_mdns_event` method | Called via `getattr`; lands in the `ActivityLogger` deque | ✓ |
| Reuse `on_packet_sent` | Send mDNS events through the packet callback | |
| Separate mDNS listener | New listener registered on the server; the app bridges it | |

**Q2: Event type passed to `on_mdns_event`?**

| Option | Description | Selected |
|--------|-------------|----------|
| PacketEvent + `kind` field | Add `kind: str = "lifx"` to `PacketEvent` | ✓ |
| New MdnsEvent dataclass | Dedicated type, converted in `ActivityLogger` | |

**Notes:** Settled defaults, accepted by moving on: observer exceptions are isolated and logged; mDNS events are excluded from LIFX packet stats; responder vs server emitter placement is left to Claude.

---

## run() decomposition layout

**Q1: Where do the helpers extracted from `run()` live?**

| Option | Description | Selected |
|--------|-------------|----------|
| New app modules | e.g. `lifx_emulator_app/startup/`; thin `run()` | ✓ |
| Private helpers in `__main__.py` | Smallest diff, file stays large | |
| Two-step: split in place, then move | Extract in place first, then move | |

**Q2: What do the helpers consume after the merge?**

| Option | Description | Selected |
|--------|-------------|----------|
| Typed frozen settings object | Resolved values plus provenance (e.g. `mdns` tri-state source) | ✓ |
| Keep the merged dict | Existing `dict` from `merge_config()` | |
| Re-validate as EmulatorConfig | Pydantic model; errors name YAML keys | |

**Q3: When do the pre-bind checks run?**

| Option | Description | Selected |
|--------|-------------|----------|
| One preflight after devices are built | Collects every problem, exits non-zero before binding | ✓ |
| Split across layers | Pydantic, settings builder and core `start()` | |

**Q4: How is R1 equivalence proven?**

| Option | Description | Selected |
|--------|-------------|----------|
| Golden snapshot committed first | Inline constants captured before the refactor | ✓ |
| Old-vs-new side-by-side test | Keep a copy of the old path in the test | |

---

## Claude's Discretion

- Responder vs server emitter placement for each lifecycle event
- Startup module, helper and settings dataclass names
- `packet_name` wording and `addr` formatting for responder-level events
- Whether `--thread-product` pre-checks Thread capability
- How the preflight failure exits non-zero (research must verify cyclopts' handling of `return False`)

## Deferred Ideas

None.
