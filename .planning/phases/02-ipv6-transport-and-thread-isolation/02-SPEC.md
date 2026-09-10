# Phase 2: IPv6 Transport and Thread Isolation — Specification

**Created:** 2026-09-10
**Ambiguity score:** 0.07 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

The stock `EmulatedLifxServer` listens on IPv4 and IPv6 using one logical UDP port, routes each datagram with its address-family identity intact, and makes Thread devices reachable only by IPv6 unicast addressed to their serial while preserving existing WiFi behaviour and eliminating the two known asynchronous/serial defects.

## Background

`EmulatedLifxServer.start()` currently creates one IPv4 asyncio datagram endpoint from `bind_address` and `port`, and the nested `LifxProtocol` stores it in a single `server.transport`. The protocol callback passes only `data` and `addr` to `handle_packet()`, so the server and `DeviceManager.resolve_target_devices()` cannot distinguish IPv4 from IPv6. Consequently, the stock server cannot model a Thread bulb's IPv6-only reachability; `lifx-async` carries a temporary `_Ipv6EmulatedLifxServer` subclass that constructs a V6-only socket before binding.

The packet path also schedules fire-and-forget tasks in `server.py` and `event_bridge.py` without strong references, allowing garbage collection to cancel work under load. Separately, received activity derives an untagged target with `header.target.hex().rstrip("0000")`, which can truncate a valid device serial ending in zero. Phase 1 already supplies immutable per-device `connectivity`, so Phase 2 can enforce transport isolation without changing device identity or packet formats.

## Requirements

1. **NET-01 — Native dual-family server**: A stock server binds separate IPv4 and `AF_INET6` UDP sockets on one effective port, with the IPv6 socket enabled by default at `::1` and `IPV6_V6ONLY=1` set before bind.
   - Current: `start()` creates one endpoint from the IPv4 default `127.0.0.1`; direct users need a subclass to construct and configure an IPv6 socket.
   - Target: Default startup retains the existing IPv4 endpoint and adds a configurable IPv6 endpoint on Linux, macOS and Windows. A non-zero requested port is shared by both sockets; `port=0` selects one effective ephemeral port and binds both sockets to it. Startup is atomic, repeated `start()` creates no duplicate sockets, and repeated `stop()` is safe.
   - Acceptance: On supported CI hosts, both sockets are bound to the same effective port, the IPv6 socket reports `AF_INET6` and `IPV6_V6ONLY == 1`, `port=0` exposes a non-zero shared port, a forced second-bind failure leaves no socket open, repeated start does not add endpoints, and repeated stop raises no error.

2. **NET-02 — Family-aware routing**: Every received datagram retains its address family through protocol receipt, packet handling and target resolution.
   - Current: `LifxProtocol.datagram_received()` calls `handle_packet(data, addr)`, and `DeviceManager.resolve_target_devices()` receives only the parsed header.
   - Target: Target resolution receives the originating address family through a public manager contract; interleaved IPv4 and IPv6 datagrams cannot overwrite, infer or share family state, and the server does not reach into a device private method to decide transport eligibility.
   - Acceptance: A mixed-family concurrent test proves that every resolved target is evaluated against the family of its own datagram and that no class-level, server-global or last-packet family state can cross-contaminate another packet.

3. **NET-03 — Side-effect-free Thread isolation**: A Thread device processes only an IPv6 unicast packet whose untagged target is its exact serial.
   - Current: Tagged or all-zero targets resolve to every device, and a specific target resolves without considering the receiving socket or device connectivity.
   - Target: IPv4 packets, tagged packets, all-zero/broadcast packets and packets for another serial never reach a Thread device. Rejection occurs before acknowledgement, response generation, receive/send statistics, scenario evaluation or activity-observer notification; debug logging is the only permitted trace.
   - Acceptance: Repeating and concurrently interleaving accepted IPv6-unicast packets with each rejected shape yields replies and side effects only for accepted packets: rejected packets produce zero datagrams, zero acknowledgements, zero packet-statistic changes and zero activity events.

4. **NET-04 — WiFi dual-family compatibility**: A WiFi device answers valid discovery and control traffic received on either socket, using the same address family on which each request arrived.
   - Current: The stock server offers IPv4 only; the temporary `lifx-async` subclass offers IPv6 only.
   - Target: WiFi devices remain reachable through existing IPv4 discovery/control and additionally through IPv6 unicast, with simultaneous traffic isolated to its respective transport. Supplying no new constructor arguments changes no IPv4 packet bytes, routing results, statistics or activity events.
   - Acceptance: Identical valid requests over IPv4 and IPv6 receive equivalent protocol replies from their respective sockets, concurrent requests never cross transports, and the existing exact-byte IPv4 fixtures and server tests remain unchanged and passing.

5. **NET-05 — Effective endpoint exposure**: Callers can inspect the effective IPv4 and IPv6 bind addresses and ports after startup.
   - Current: The server exposes configured `bind_address` and `port` plus one transport, but has no IPv6 endpoint and does not provide a complete effective dual-family endpoint contract.
   - Target: After successful startup, both effective endpoints report the addresses and actual shared port owned by the bound sockets; no half-started endpoint is exposed after startup failure or shutdown.
   - Acceptance: A caller can obtain the IPv6 `(::1, effective_port)` endpoint from the stock server and connect without a subclass, including when constructed with `port=0`; failed startup and completed shutdown do not report a live endpoint.

6. **HYG-01 — Strongly tracked asynchronous work**: Every fire-and-forget task created by `server.py` or `event_bridge.py` remains strongly referenced until completion and is removed by a done callback.
   - Current: packet-handler and WebSocket broadcast coroutines are scheduled without retaining their tasks, unlike the existing device persistence `_track_save_task()` pattern.
   - Target: Each owner tracks its own pending tasks, completed tasks are discarded, and task failures are observed rather than becoming unhandled task exceptions. Tracking does not retain completed tasks indefinitely.
   - Acceptance: Under an interleaved packet/WebSocket flood with forced garbage collection, every scheduled response and broadcast completes exactly once, no task is collected early, failures are surfaced through logging, and all tracking collections drain to empty after completion.

7. **HYG-02 — Exact activity target serials**: Received activity preserves an untagged device target as the exact lowercase 12-hex serial represented by the first six header target bytes.
   - Current: `rstrip("0000")` can remove meaningful trailing zeroes from a serial and an untagged all-zero target can become an empty string.
   - Target: Valid non-zero untagged targets always render as exactly 12 lowercase hex characters, including trailing zeroes; tagged or all-zero targets render as `broadcast`; packets shorter than a complete header produce no activity event.
   - Acceptance: Activity logging and `PacketEvent.target` return the complete serial for representative targets ending in `0`, `00` and `0000`, use `broadcast` for both broadcast forms, and emit no event for a short packet.

## Boundaries

**In scope:**
- Separate IPv4 and V6-only IPv6 UDP sockets in the stock core server, enabled by default on one logical port
- Per-datagram address-family propagation and connectivity-aware target resolution
- Side-effect-free rejection of non-IPv6-unicast traffic aimed at Thread devices
- WiFi request/reply support over both address families with unchanged IPv4 behaviour
- Public exposure of effective IPv4 and IPv6 endpoints
- Strong task tracking in core `server.py` and app `event_bridge.py`
- Exact target-serial representation in activity events
- Unit, integration, concurrency and regression tests for the seven requirements

**Out of scope:**
- mDNS/DNS-SD discovery or multicast socket handling — Phase 3 owns responder behaviour
- CLI flags, YAML configuration and standalone-app defaults for IPv6 — Phase 4 owns configuration surfaces
- Device-create or device-info API changes — Phase 5 owns management API exposure
- Changes to the sibling `lifx-async` repository, including deleting `_Ipv6EmulatedLifxServer` — Phase 6 owns oracle integration and removal
- IPv6 multicast LIFX discovery — Thread devices are unicast-only and no known client requires it
- Dashboard changes — explicitly deferred from this milestone
- Thread latency or bandwidth simulation — existing scenarios already cover response delay

## Constraints

- Python 3.10–3.14 compatibility is required across Linux, macOS and Windows; platform-specific socket-option branches must be covered even where no Windows CI runner exists.
- `IPV6_V6ONLY` must be set before bind; the implementation must not rely on platform dual-stack defaults.
- The default IPv6 bind is loopback `::1`, never wildcard `::`; the existing IPv4 default remains `127.0.0.1`.
- Both address families form one logical LIFX service and therefore use one effective UDP port, including when the requested port is zero.
- The existing public IPv4 behaviour and wire bytes remain backwards compatible.
- Packet processing remains asyncio-based with no threads in the packet path.
- Transport eligibility belongs in the public `DeviceManager` routing contract; the network server must not use a device private method to resolve targets.
- This phase adds no dependency and edits no generated protocol or product-registry file.
- Project conventions remain mandatory: Ruff, Pyright standard, cyclomatic complexity ≤ 10, Australian English and the existing test/coverage gates.

## Acceptance Criteria

- [ ] **AC-01:** Default startup binds the unchanged IPv4 endpoint and an `AF_INET6` endpoint at `::1` on the same effective port.
- [ ] **AC-02:** The IPv6 socket reports `IPV6_V6ONLY == 1`, with the option set before bind on every platform path.
- [ ] **AC-03:** With `port=0`, both sockets use one non-zero effective ephemeral port exposed to callers.
- [ ] **AC-04:** Startup is atomic on bind failure, repeated `start()` creates no duplicate endpoints, and repeated `stop()` is safe.
- [ ] **AC-05:** Concurrent mixed-family datagrams retain their own family through `handle_packet()` and public `DeviceManager` target resolution.
- [ ] **AC-06:** An exact, untagged IPv6-unicast request to a Thread serial receives its normal reply on IPv6.
- [ ] **AC-07:** IPv4, tagged, all-zero/broadcast and wrong-target packets cause no Thread acknowledgement, response, statistics change, scenario side effect or activity event.
- [ ] **AC-08:** Repeated rejected packets remain side-effect-free when interleaved with accepted packets.
- [ ] **AC-09:** WiFi devices answer equivalent valid requests over both IPv4 and IPv6, returning each reply on the request's family.
- [ ] **AC-10:** Existing exact-byte IPv4 fixtures and discovery/control behaviour remain unchanged for callers supplying no new options.
- [ ] **AC-11:** Effective IPv4 and IPv6 endpoints are inspectable after startup, including `port=0`, and no live endpoint is exposed after failed startup or shutdown.
- [ ] **AC-12:** Forced garbage collection during a packet/WebSocket flood loses no scheduled response or broadcast; failures are logged and tracking collections drain to empty.
- [ ] **AC-13:** Untagged targets ending in zero render as exactly 12 lowercase hex characters from the first six bytes.
- [ ] **AC-14:** Tagged and all-zero targets render as `broadcast`; packets shorter than a complete header produce no activity event.
- [ ] **AC-15:** Phase 2 changes only `lifx-emulator`; the sibling `lifx-async` subclass remains untouched for Phase 6.

## Edge Coverage

**Coverage:** 12/12 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| Idempotency / repetition | R1 / NET-01 | ✅ covered | AC-03–AC-04: shared ephemeral port, no duplicate start, repeat-safe stop |
| Concurrency / effect ordering | R1 / NET-01 | ✅ covered | AC-04: dual bind is atomic and cleans up a partial failure |
| Concurrency / effect ordering | R2 / NET-02 | ✅ covered | AC-05: interleaved datagrams retain per-request family identity |
| Idempotency / repetition | R3 / NET-03 | ✅ covered | AC-07–AC-08: repeated rejected packets remain invisible |
| Concurrency / effect ordering | R3 / NET-03 | ✅ covered | AC-08: accepted and rejected traffic can interleave without side-effect leakage |
| Idempotency / repetition | R4 / NET-04 | ✅ covered | AC-09–AC-10: repeated valid WiFi traffic retains normal family-specific behaviour |
| Concurrency / effect ordering | R4 / NET-04 | ✅ covered | AC-09: simultaneous requests reply only through their originating family |
| Concurrency / effect ordering | R5 / NET-05 | ✅ covered | AC-04 and AC-11: effective endpoints are published only for a complete live bind |
| Idempotency / repetition | R6 / HYG-01 | ✅ covered | AC-12: completion callbacks drain tracking without duplicate completion |
| Concurrency / effect ordering | R6 / HYG-01 | ✅ covered | AC-12: a forced-GC flood loses no scheduled work |
| Empty / degenerate | R7 / HYG-02 | ✅ covered | AC-14: all-zero and short inputs have explicit outcomes |
| Encoding / representation | R7 / HYG-02 | ✅ covered | AC-13: byte-to-text conversion is exactly first-six-byte lowercase hex |

## Prohibitions (must-NOT)

**Coverage:** 0/0 applicable prohibitions resolved · 0 unresolved

No bespoke values, fairness, privacy, transparency or safety prohibition survived the recall-to-precision filter. The candidates were routine transport correctness already captured by AC-01–AC-15. General network-exposure and socket-security concerns are canonical security-review territory and remain owned by `$gsd-secure-phase`, not duplicated here.

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| None | — | — | Pure transport and lifecycle utility; functional negative constraints are explicit acceptance criteria |

## Ambiguity Report

| Dimension | Score | Min | Status | Notes |
|-----------|-------|-----|--------|-------|
| Goal Clarity | 0.95 | 0.75 | ✓ | Dual-family outcome and Thread reachability are measurable |
| Boundary Clarity | 0.94 | 0.70 | ✓ | Emulator-only scope; later mDNS/config/API/oracle work excluded |
| Constraint Clarity | 0.88 | 0.65 | ✓ | Default enablement, port sharing, V6ONLY ordering and side-effect policy locked |
| Acceptance Criteria | 0.92 | 0.70 | ✓ | Fifteen pass/fail checks plus complete edge resolutions |
| **Ambiguity** | **0.07** | ≤0.20 | ✓ | Gate passed after round 1 |

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 1 | Researcher | Is IPv6 default-on or opt-in for direct library users? | Default-on at `::1`; unchanged IPv4 remains alongside it |
| 1 | Researcher | Are rejected Thread packets observable? | No statistics or activity side effects; debug logging only |
| 1 | Researcher | Does Phase 2 modify `lifx-async`? | No; emulator repository only, with sibling removal deferred to Phase 6 |
| Edge probe | Boundary / repetition | What happens at `port=0`, partial startup, repeated start and stop? | One shared effective port; atomic startup; no duplicate starts; repeat-safe stop |
| Edge probe | Concurrency | What survives mixed-family traffic and forced garbage collection? | Per-datagram family isolation, exact side effects, no lost tasks, tracking drains |
| Edge probe | Encoding / empty | How are trailing-zero, broadcast and short targets represented? | Exact first-six-byte lowercase hex; broadcast marker; no short-packet event |
| Prohibition probe | Failure analyst | What could this utility silently become that is undesirable but not forbidden? | No bespoke prohibition; routine correctness is already explicit and canon security is referred |

---

*Phase: 02-ipv6-transport-and-thread-isolation*
*Spec created: 2026-09-10*
*Next step: $gsd-discuss-phase 2 — implementation decisions (how to build what is specified above)*
