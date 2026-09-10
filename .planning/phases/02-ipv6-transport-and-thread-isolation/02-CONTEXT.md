# Phase 2: IPv6 Transport and Thread Isolation - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a native, default-on IPv6 UDP endpoint alongside the stock server's compatible IPv4 endpoint; carry address-family identity through routing so Thread devices accept only exact IPv6 unicast; expose live endpoints; and repair the task-lifetime and target-serial defects that would otherwise be multiplied by the second transport.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `02-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `02-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Separate IPv4 and V6-only IPv6 UDP sockets in the stock core server, enabled by default on one logical port
- Per-datagram address-family propagation and connectivity-aware target resolution
- Side-effect-free rejection of non-IPv6-unicast traffic aimed at Thread devices
- WiFi request/reply support over both address families with unchanged IPv4 behaviour
- Public exposure of effective IPv4 and IPv6 endpoints
- Strong task tracking in core `server.py` and app `event_bridge.py`
- Exact target-serial representation in activity events
- Unit, integration, concurrency and regression tests for the seven requirements

**Out of scope (from SPEC.md):**
- mDNS/DNS-SD discovery or multicast socket handling — Phase 3 owns responder behaviour
- CLI flags, YAML configuration and standalone-app defaults for IPv6 — Phase 4 owns configuration surfaces
- Device-create or device-info API changes — Phase 5 owns management API exposure
- Changes to the sibling `lifx-async` repository, including deleting `_Ipv6EmulatedLifxServer` — Phase 6 owns oracle integration and removal
- IPv6 multicast LIFX discovery — Thread devices are unicast-only and no known client requires it
- Dashboard changes — explicitly deferred from this milestone
- Thread latency or bandwidth simulation — existing scenarios already cover response delay

</spec_lock>

<decisions>
## Implementation Decisions

### Transport Ownership and Compatibility
- **D-01:** `server.transport` remains the IPv4 transport alias. Existing callers must not see it become a mapping or point at the most recently created transport. — **Reversibility:** costly — reinterpreting an existing public attribute would break direct library callers and tests.
- **D-02:** Add public `ipv4_endpoint` and `ipv6_endpoint` properties. Each returns the live effective `(host, port)` tuple while its endpoint is running and `None` otherwise. — **Reversibility:** costly — the property names and return contract become published library API.
- **D-03:** Each receiving protocol instance owns the transport used for replies. The per-datagram path carries that transport forward; response code must not reselect a socket from global server state or infer a family from the peer-address tuple.
- **D-04:** Keep the raw IPv6 asyncio transport internal. The supported public inspection surface is `ipv6_endpoint`, not `server.ipv6_transport`.

### Family-Routing Contract
- **D-05:** Represent per-datagram network identity with one immutable context value containing the address family, peer address and receiving transport.
- **D-06:** `DeviceManager` receives only the parsed header and address family. Peer and transport details stay in the server layer; device routing does not depend on asyncio transport objects.
- **D-07:** Extend `resolve_target_devices()` with an optional family argument defaulting to `AF_INET`. This preserves existing direct calls as the legacy IPv4 path while making server calls explicitly family-aware. — **Reversibility:** costly — the default and parameter semantics become part of the public `IDeviceManager` contract.
- **D-08:** Preserve the existing device-list return type. Transport-ineligible Thread targets are filtered out; `DeviceManager` emits the reason at debug level where it has both connectivity and target context. Do not add rejected-target result objects or metrics.

### Startup and Rollback Lifecycle
- **D-09:** Bind IPv4 first. Its actual bound port is the effective shared port, including when the requested port is `0`; IPv6 then binds to the same number.
- **D-10:** Startup is atomic. If IPv6 construction or bind fails after IPv4 succeeds, close every partial resource, clear live endpoint state and re-raise the original exception unchanged. Cancellation follows the same rollback path; do not fall back to IPv4-only operation.
- **D-11:** Calling `start()` while already running is an idempotent no-op with a debug log. It does not replace or duplicate either endpoint.
- **D-12:** `stop()` first prevents new datagrams, waits for tracked work according to D-16, closes both transports, waits until both report closure, then clears live endpoint state before returning. Repeated `stop()` remains safe.

### Task Tracking and Failures
- **D-13:** Build one reusable internal background-task tracker and give each owning component its own instance. `server.py`, `event_bridge.py` and the later Phase 3 responder may share the utility but not one global task collection.
- **D-14:** The tracker accepts a coroutine plus an operation label, creates the task and retains it atomically. If no running event loop exists, close the coroutine and log the scheduling failure so no un-awaited-coroutine warning is emitted.
- **D-15:** A done callback retrieves task exceptions, removes the task and logs failures at error level with the operation label. Expected cancellation is logged at debug level. Do not add a degraded-server health state in this phase.
- **D-16:** Shutdown stops accepting new work, allows tracked tasks up to five seconds to complete while required transports remain usable, then cancels and awaits the remainder before transport closure. Tracking collections must be empty when shutdown returns.

### the agent's Discretion
- Exact internal names and module placement for the immutable datagram context and reusable task tracker
- Exact debug/error log wording, provided rejection and task labels retain useful context
- Test-file organisation and helper factoring
- Whether endpoint properties use a small internal type alias, provided their public values remain `(host, port) | None`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked Scope and Prior Decisions
- `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md` — locked Phase 2 requirements, boundaries, constraints, acceptance criteria and edge coverage
- `.planning/ROADMAP.md` — Phase 2 goal, dependencies, success criteria and Phase 3/6 hand-offs
- `.planning/REQUIREMENTS.md` — canonical NET-01 through NET-05 and HYG-01 through HYG-02 requirement wording
- `.planning/PROJECT.md` — milestone-level Thread decisions, platform constraints and `lifx-async` reference paths
- `.planning/STATE.md` — current phase position, active blockers and cross-phase decisions
- `.planning/phases/01-thread-device-identity/01-CONTEXT.md` — connectivity placement and response-header decisions inherited from Phase 1
- `.planning/phases/01-thread-device-identity/01-SPEC.md` — locked Phase 1 identity contract that family routing consumes

### Emulator Integration Points
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` — current single transport, nested `LifxProtocol`, packet statistics/activity ordering and target formatting defect
- `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` — public `IDeviceManager` and current target-resolution list contract
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` — existing `_track_save_task()` strong-reference pattern and immutable connectivity state consumer
- `packages/lifx-emulator-core/src/lifx_emulator/devices/observers.py` — `PacketEvent` and activity observer contracts
- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` — untracked WebSocket broadcast scheduling that must adopt the shared tracker
- `packages/lifx-emulator-core/tests/test_server.py` — current server/protocol/activity regression surface
- `packages/lifx-emulator-core/tests/test_device_manager.py` — current direct manager-call compatibility surface
- `packages/lifx-emulator/tests/test_websocket.py` — current event-bridge scheduling and broadcast tests

### Client Oracle (read-only in Phase 2)
- `../lifx-async/tests/conftest.py` — temporary `_Ipv6EmulatedLifxServer`, including pre-bind `IPV6_V6ONLY` ordering
- `../lifx-async/tests/test_api/test_ipv6_e2e.py` — existing real-loopback IPv6 discovery and control expectations

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EmulatedLifxServer.LifxProtocol`: one existing protocol implementation can be parameterised with immutable family/transport identity rather than duplicated per family.
- `EmulatedLifxDevice._track_save_task()`: proven strong-reference plus done-callback pattern; the new reusable tracker generalises its lifecycle and exception handling.
- `_Ipv6EmulatedLifxServer` in `lifx-async`: tested reference for explicit `AF_INET6`, pre-bind `IPV6_V6ONLY=1`, non-blocking socket setup and partial-failure cleanup.
- `ActivityLogger` and `PacketEvent`: existing observation surface for proving accepted traffic and exact target text without adding new metrics.

### Established Patterns
- Asyncio `DatagramProtocol` owns UDP callbacks and schedules coroutine packet handling on the running loop.
- `DeviceManager.resolve_target_devices()` is the domain boundary for target selection and already returns a plain list.
- `server.transport` is read and assigned as the sole IPv4 transport throughout existing tests, so compatibility requires preserving that meaning.
- Device connectivity is immutable Phase 1 state; routing should read it without teaching packet handlers about Thread.
- Pytest exercises protocol callbacks directly and real loopback sockets separately; both levels are available for deterministic family and lifecycle coverage.

### Integration Points
- `LifxProtocol.connection_made()` records transport ownership and effective socket information.
- `LifxProtocol.datagram_received()` constructs the immutable per-datagram context before scheduling `handle_packet()`.
- `handle_packet()` must resolve eligible targets before receive statistics and activity notifications can fire for rejected Thread traffic.
- `_send_ack()` and `_process_device_packet()` must send through the context's receiving transport rather than `server.transport`.
- `start()` and `stop()` coordinate dual binds, shared-port publication, task draining, transport closure and endpoint clearing.
- `_schedule_async()` and packet scheduling adopt owner-local instances of the shared task tracker.

</code_context>

<specifics>
## Specific Ideas

- The public surface is deliberately small: retain `server.transport`, add only `ipv4_endpoint` and `ipv6_endpoint`, and keep the raw IPv6 transport private.
- Treat the address family as packet-local immutable data; never infer it from tuple length or retain it as mutable server state.
- Preserve original platform socket errors after complete rollback so callers and cross-platform tests see the real cause.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-ipv6-transport-and-thread-isolation*
*Context gathered: 2026-09-10*
