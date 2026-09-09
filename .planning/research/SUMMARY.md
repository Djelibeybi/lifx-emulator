# Research Summary: Thread-Device Emulation for LIFX Emulator

**Researched:** 2026-09-09
**Scope:** IPv6 transport, mDNS responder, Thread connectivity for LIFX LAN protocol emulator
**Acceptance oracle:** `lifx-async` (sibling repo, Phase 14 evidence)

---

## Executive Summary

Thread-device emulation requires three integrated layers: per-device connectivity state (trivial), IPv6 native transport with unicast-only filtering (medium complexity), and an mDNS/DNS-SD responder (high complexity). The core value is enabling `lifx-async` to exercise Thread discovery and control against the emulator rather than synthetic fixtures.

**Critical decision point:** STACK.md and ARCHITECTURE.md diverge on whether `zeroconf` is viable. STACK.md has source-verified (reading `_engine.py`, `_core.py`) that `zeroconf 0.151.3` uses asyncio attachment to the caller's running loop, not a background thread. ARCHITECTURE.md asserts the opposite based on older understanding. This must be resolved by a spike that tests `zeroconf` against `lifx-async`'s actual `discover_mdns()` before committing to either approach.

Four critical questions remain unconfirmed:
1. Legacy-unicast reply support for ephemeral-port queries (load-bearing for `lifx-async`)
2. Multi-instance advertisement fidelity (each device's TXT and address independent)
3. Coexistence with OS mDNS daemons on port 5353
4. macOS x86_64 PyApp wheel availability

**Risk posture:** Eight documented pitfalls span platform-specific concerns (Windows socket-option divergence, macOS `IPV6_V6ONLY` timing), easy-to-miss implementation details (legacy-unicast DNS wire format), and existing codebase issues (untracked asyncio tasks). The roadmap must front-load critical pitfalls as acceptance gates.

---

## Key Findings

### From STACK.md: Technology Recommendations

- **`zeroconf 0.151.3` threading model:** Source-verified via direct code reading. `_engine.py` uses `loop.create_datagram_endpoint(lambda: AsyncListener(...), sock=...)` with `get_running_loop()` detection. No background thread when an event loop exists.
- **IPv6 transport:** Native `socket.socket(AF_INET6, SOCK_DGRAM)` + `IPV6_V6ONLY=1` before `bind()`, then `create_datagram_endpoint(sock=...)`. Never use `local_addr=` (macOS raises `EINVAL` on set-after-bind).
- **macOS x86_64 PyApp:** No `x86_64` wheel; builds will compile from sdist (C toolchain required). Flag for validation during the CLI/config phase or release.

### From FEATURES.md: Feature Landscape

**Table Stakes:**
- Bit 3 (`thread_connection`) on every reply type (data, acks, StateUnhandled)
- Per-device `connectivity` in factories, CLI, config, API, persistence
- **Legacy-unicast mDNS replies**: the most load-bearing requirement; `lifx-async` never joins the multicast group, so multicast-only responders are invisible to it
- IPv6-unicast-only filtering (drop IPv4 and tagged packets addressed to Thread devices)
- A records for WiFi, AAAA only for Thread
- TXT record exactness (exact sentinel matches for `id=`, `p=`, `fw=`, `tm=2`)

**Differentiators (backlog):** Goodbye packets, per-device advertised IPv6 address, direct A/AAAA queries, scenario mDNS hooks, multi-instance border-router mode.

### From ARCHITECTURE.md: Placement and Patterns

**Four critical patterns:**
1. **Family threading:** Socket family as an explicit parameter through `handle_packet()` to `resolve_target_devices()`, never inferred from device state.
2. **Thread bit placement:** Set once in `_response_header_template`, inherited by acks and StateUnhandled; avoids forgotten paths.
3. **Multi-subscriber events:** List-based listener registry replaces single-slot `on_device_added`/`on_device_removed`.
4. **Responder choice:** DECISION PENDING (the spike gates this).

**Build order (horizontal layers):**
- Phase A: Header bit + connectivity (core identity, no networking)
- Phase B: IPv6 transport + family-aware routing (depends on A; independent of mDNS)
- Phase C: mDNS responder (depends on A; independent of B; **spike gates**)
- Phase D: CLI/config (depends on A, B, C)
- Phase E: API (depends on A)
- Phase F: Assembly + verification against `lifx-async`

### From PITFALLS.md: Critical Risks

| Pitfall | Severity | Key Prevention |
|---------|----------|---|
| Port 5353 contention; legacy-unicast stealing | CRITICAL | Respond via unicast `sendto()` to source IP:port, not multicast |
| Windows lacks `SO_REUSEPORT` | CRITICAL | Guard with `try/except (AttributeError, OSError)` |
| `IPV6_V6ONLY` set after bind (macOS `EINVAL`) | CRITICAL | Set before bind; test on macOS CI |
| DNS legacy-unicast format (ID/cache-flush/TTL/compression) | CRITICAL | Build a separate code path; assert on captured raw bytes |
| Untracked asyncio tasks (tripled with three protocols) | CRITICAL | Fix once; reuse for all three protocols |
| Thread bit on acks/StateUnhandled; persistence round-trip | CRITICAL | Test all response types; add connectivity to all serialisation paths |
| Thread device answers IPv4 broadcast | CRITICAL | Filter before acks/stats/logging side effects |
| `rstrip` serial bug reused; `run()` complexity 61 | MEDIUM | Fix `rstrip` to `[:6].hex()`; extract `_build_devices_from_flags()` |

---

## Reconciliation: The zeroconf Conflict

**Claim divergence:**
- **STACK.md:** "`zeroconf 0.151.3` uses asyncio attachment; no background thread" (source-verified by code reading)
- **ARCHITECTURE.md:** "`zeroconf` spawns a background thread; conflicts with the single-loop constraint" (asserted based on older understanding)

**What STACK.md verified:**
- Read `_engine.py`: `AsyncZeroconf.async_init()` calls `loop.create_datagram_endpoint(lambda: AsyncListener(...), sock=...)`
- The `AsyncListener` is registered directly into the caller's running loop via `get_running_loop()`
- No background thread is spawned when an event loop already exists
- The threading path (`Zeroconf._start_thread()`) is only taken when no loop is running

**What must still be confirmed (the spike gates the decision):**
1. **Legacy-unicast QU reply support:** Can `zeroconf` emit replies with the query ID echoed, cache-flush bit clear, TTL ≤ 10 s, sent unicast to the source address:port? (Load-bearing for `lifx-async`)
2. **Multi-instance fidelity:** Can `zeroconf` advertise multiple devices with unique instance names, per-device TXT, per-device A/AAAA without coercion?
3. **OS daemon coexistence:** Does `zeroconf` reliably receive queries on `224.0.0.251:5353` when the system mDNS daemon is also bound with `SO_REUSEADDR`/`SO_REUSEPORT`?
4. **PyApp wheel:** Does the macOS x86_64 build have a C toolchain for sdist compilation?

**Roadmap decision:**
- **Spike (gates Phase C):** Minimal mDNS responder using `zeroconf 0.151.3`. Single test device. Run against `lifx-async` `discover_mdns()`. Verify the four questions.
  - If the spike succeeds, continue Phase C with `zeroconf`
  - If the spike fails, use a hand-rolled responder (ARCHITECTURE.md Pattern 4 is ready to use; PITFALLS.md pitfalls 1, 2 and 4 are the exact traps to avoid)

---

## Implications for Roadmap

### Phase Structure

**Phase A: Core Device Identity** (~100 lines, LOW risk)
- Add `thread_connection` to `LifxHeader` pack/unpack
- Add `Connectivity` enum + `connectivity` field to `DeviceState.NetworkState`
- Update `DeviceBuilder`, `GetWifiInfoHandler`, serialisers
- Acceptance: Thread-bit and firmware assertions on an in-memory device
- Precedent: `advertised_services` PR #156

**Phase B: IPv6 Transport** (~200 lines + refactor, MEDIUM risk)
- Add family-aware `resolve_target_devices(header, family="inet")` in `DeviceManager`
- Configure the IPv6 socket (AF_INET6, V6ONLY=1 before bind), second `LifxProtocol` instance
- Thread family through `handle_packet()` → `_process_device_packet()` → `_send_ack()`
- **Prerequisite:** Fix the task-tracking pattern (Pitfall 5); reuse for all three protocols
- Risk: macOS `IPV6_V6ONLY` timing (must test on macOS CI)

**Phase C: mDNS Responder** (300–500 lines, MEDIUM-HIGH pre-spike, LOW post-spike)
- **Spike (gates Phase C):** Minimal `zeroconf` responder; test against `lifx-async` `discover_mdns()`
- Multi-listener registry in `DeviceManager` (Pattern 3, ~20 lines)
- Full responder implementation (size depends on spike outcome)
- Risk: Platform socket-option divergence (Pitfall 2 requires guards)

**Phase D: CLI/Config** (~200 lines, LOW risk)
- Extract `_build_devices_from_flags()` from `run()` (Pitfall 8 hygiene)
- Add `connectivity` to `DeviceDefinition`, `EmulatorConfig`, CLI flag, export-config
- Fix the `rstrip` serial bug in new logging
- Precedent: `advertised_services`; the refactor de-risks Pitfall 8

**Phase E: API** (~50 lines, LOW risk)
- Add `connectivity` to `DeviceCreateRequest`, `DeviceInfo`
- Update `device_service.py`, `device_mapper.py`
- Can run alongside Phase D if the roadmap chooses

**Phase F: Assembly and Verification** (integration + cross-repo)
- Delete `_Ipv6EmulatedLifxServer` from `lifx-async` test fixtures
- Run `lifx-async` Thread + mDNS test suites against the emulator
- Acceptance: `discover_mdns()` finds the Thread device; IPv6 e2e tests pass on the stock server

### Confidence Assessment

| Area | Level | Gaps |
|------|-------|------|
| **Features** | HIGH | None; all sourced from `lifx-async` code and Phase 14 evidence |
| **Stack** | HIGH | zeroconf choice pending spike; PyApp x86_64 wheel gap identified with a known workaround |
| **Architecture** | HIGH | All placements grounded in existing codebase precedents |
| **Pitfalls** | HIGH | Platform-specific claims (Windows UDP, macOS V6ONLY) well documented; no Windows CI but not a blocker |
| **IPv6** | HIGH | Requirement derived from `lifx-async`'s own tested fixture |
| **mDNS wire format** | HIGH | All claims cite exact client parser code lines; legacy-unicast is the most referenced |

### Remaining Uncertainties

1. **zeroconf threading model and QU replies:** Resolved by the spike
2. **macOS x86_64 PyApp:** Known gap; validation during the CLI/config phase or release
3. **Windows UDP + multicast:** No Windows CI; not a pre-release blocker

---

## Sources

- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` (this milestone)
- `.planning/PROJECT.md` (user decisions)
- `lifx-async` source: `src/lifx/protocol/header.py`, `src/lifx/network/discovery/mdns/discovery.py`, `src/lifx/network/transport.py`, `tests/conftest.py`, `tests/test_network/test_mdns/test_discovery.py`
- `lifx-async` Phase 14 evidence: `.planning/milestones/v2.0-phases/14-thread-revalidation-and-docs/14-INTERIM-RESULTS.md`
- python-zeroconf 0.151.3 source (`_core.py`, `_engine.py`, `_services/info.py`, `_utils/net.py`)
- RFC 6762 §6.7 (legacy unicast responses), RFC 6763 (DNS-SD)

---

*Summary synthesised: 2026-09-09*
