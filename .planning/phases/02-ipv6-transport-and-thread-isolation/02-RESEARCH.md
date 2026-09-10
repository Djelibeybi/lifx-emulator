# Phase 2: IPv6 Transport and Thread Isolation - Research

**Researched:** 2026-09-10
**Domain:** Cross-platform asyncio UDP lifecycle, address-family routing, and background-task ownership
**Confidence:** HIGH for repository integration and locked contracts; MEDIUM for unexecuted Linux/Windows platform behaviour

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

<!-- DATA_7Q3M9K2P_START -->
Add a native, default-on IPv6 UDP endpoint alongside the stock server's compatible IPv4 endpoint; carry address-family identity through routing so Thread devices accept only exact IPv6 unicast; expose live endpoints; and repair the task-lifetime and target-serial defects that would otherwise be multiplied by the second transport.

#### Transport Ownership and Compatibility
- **D-01:** `server.transport` remains the IPv4 transport alias. Existing callers must not see it become a mapping or point at the most recently created transport. — **Reversibility:** costly — reinterpreting an existing public attribute would break direct library callers and tests.
- **D-02:** Add public `ipv4_endpoint` and `ipv6_endpoint` properties. Each returns the live effective `(host, port)` tuple while its endpoint is running and `None` otherwise. — **Reversibility:** costly — the property names and return contract become published library API.
- **D-03:** Each receiving protocol instance owns the transport used for replies. The per-datagram path carries that transport forward; response code must not reselect a socket from global server state or infer a family from the peer-address tuple.
- **D-04:** Keep the raw IPv6 asyncio transport internal. The supported public inspection surface is `ipv6_endpoint`, not `server.ipv6_transport`.

#### Family-Routing Contract
- **D-05:** Represent per-datagram network identity with one immutable context value containing the address family, peer address and receiving transport.
- **D-06:** `DeviceManager` receives only the parsed header and address family. Peer and transport details stay in the server layer; device routing does not depend on asyncio transport objects.
- **D-07:** Extend `resolve_target_devices()` with an optional family argument defaulting to `AF_INET`. This preserves existing direct calls as the legacy IPv4 path while making server calls explicitly family-aware. — **Reversibility:** costly — the default and parameter semantics become part of the public `IDeviceManager` contract.
- **D-08:** Preserve the existing device-list return type. Transport-ineligible Thread targets are filtered out; `DeviceManager` emits the reason at debug level where it has both connectivity and target context. Do not add rejected-target result objects or metrics.

#### Startup and Rollback Lifecycle
- **D-09:** Bind IPv4 first. Its actual bound port is the effective shared port, including when the requested port is `0`; IPv6 then binds to the same number.
- **D-10:** Startup is atomic. If IPv6 construction or bind fails after IPv4 succeeds, close every partial resource, clear live endpoint state and re-raise the original exception unchanged. Cancellation follows the same rollback path; do not fall back to IPv4-only operation.
- **D-11:** Calling `start()` while already running is an idempotent no-op with a debug log. It does not replace or duplicate either endpoint.
- **D-12:** `stop()` first prevents new datagrams, waits for tracked work according to D-16, closes both transports, waits until both report closure, then clears live endpoint state before returning. Repeated `stop()` remains safe.

#### Task Tracking and Failures
- **D-13:** Build one reusable internal background-task tracker and give each owning component its own instance. `server.py`, `event_bridge.py` and the later Phase 3 responder may share the utility but not one global task collection.
- **D-14:** The tracker accepts a coroutine plus an operation label, creates the task and retains it atomically. If no running event loop exists, close the coroutine and log the scheduling failure so no un-awaited-coroutine warning is emitted.
- **D-15:** A done callback retrieves task exceptions, removes the task and logs failures at error level with the operation label. Expected cancellation is logged at debug level. Do not add a degraded-server health state in this phase.
- **D-16:** Shutdown stops accepting new work, allows tracked tasks up to five seconds to complete while required transports remain usable, then cancels and awaits the remainder before transport closure. Tracking collections must be empty when shutdown returns.
<!-- DATA_7Q3M9K2P_END -->

[VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:12-13,44-66`]

### the agent's Discretion

<!-- DATA_4R8V1H6N_START -->
- Exact internal names and module placement for the immutable datagram context and reusable task tracker
- Exact debug/error log wording, provided rejection and task labels retain useful context
- Test-file organisation and helper factoring
- Whether endpoint properties use a small internal type alias, provided their public values remain `(host, port) | None`
<!-- DATA_4R8V1H6N_END -->

[VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:68-72`]

### Deferred Ideas (OUT OF SCOPE)

<!-- DATA_6T2C9W5J_START -->
None — discussion stayed within phase scope.
<!-- DATA_6T2C9W5J_END -->

[VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:147-147`]
</user_constraints>

<phase_requirements>
## Phase Requirements

<!-- DATA_3P7X8D1L_START -->
| ID | Description | Research Support |
|----|-------------|------------------|
| NET-01 | `EmulatedLifxServer` binds a second `AF_INET6` UDP socket with `IPV6_V6ONLY=1` set before bind, defaulting to `::1` with a configurable address, alongside the unchanged IPv4 socket, on Linux, macOS and Windows | Atomic two-bind sequence, explicit socket-option ordering, shared ephemeral-port handling, closure barrier, and platform tests |
| NET-02 | Every received datagram carries its address family from the protocol callback through `handle_packet()` into `DeviceManager` target resolution, without the server reaching into device private methods | Immutable datagram context and public manager signature change |
| NET-03 | A Thread device processes a packet only if it arrived on the IPv6 socket and is addressed to its serial with `tagged=0`; any other packet aimed at it is dropped before acknowledgement, response, statistics or activity-log side effects fire (debug logging only) | Connectivity-aware target matrix and resolve-before-side-effects ordering |
| NET-04 | A WiFi device answers on both the IPv4 and IPv6 sockets, so existing IPv6 e2e tests keep passing | Per-protocol reply transport and dual-family loopback matrix |
| NET-05 | The stock server exposes its IPv6 endpoint (bind address and port) so `lifx-async` can delete its `_Ipv6EmulatedLifxServer` conftest subclass | Atomic live endpoint properties derived from socket `sockname` |
| HYG-01 | Fire-and-forget tasks in `server.py` and `event_bridge.py` are tracked with strong references and done callbacks, following the existing `_track_save_task` pattern | Reusable owner-local task tracker, exception retrieval, five-second drain, forced-GC tests |
| HYG-02 | The activity-log serial truncation at `server.py:375` (`rstrip("0000")`) is fixed to use the first six target bytes, with a regression test for a serial ending in zero | One canonical target formatter and trailing-zero/broadcast/short-packet matrix |
<!-- DATA_3P7X8D1L_END -->

[VERIFIED: `.planning/REQUIREMENTS.md:25-29,62-63`]
</phase_requirements>

## Summary

Implement Phase 2 as three bounded foundations followed by integration: first introduce a reusable background-task owner and a canonical target/address formatter; second make server startup an atomic two-endpoint transaction; third thread an immutable datagram context through packet processing while exposing only the address family to `DeviceManager`. The current server has one mutable global transport, schedules packet work without retaining tasks, records receive statistics and activity before target resolution, and closes its transport without awaiting `connection_lost()`. Those exact seams must change together or concurrent IPv4/IPv6 traffic will cross-route replies or leak side effects. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:180-209,211-338,338-449,544-555`]

Use the IPv4 bind as the port allocator. Keep it open, read its effective `sockname`, then create an explicit `AF_INET6` datagram socket, set `IPV6_V6ONLY` to `1`, bind it to `(::1, effective_port)`, make it non-blocking, and transfer it to `create_datagram_endpoint(sock=...)`. Publish `server.transport`, both endpoint properties, and protocol acceptance only after both endpoints exist. On any exception or cancellation, close all raw/transport-owned resources, await closure where possible without masking the original failure, clear live state, and re-raise the original object. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:45-60`] [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

Resolve targets immediately after a complete header is parsed and before receive counters, activity notifications, scenario lookup, acknowledgements, or device processing. `DeviceManager` should retain its list return contract and apply the matrix: WiFi is eligible on both families; Thread is eligible only when `family == AF_INET6`, `tagged` is false, the target is non-zero, and the first six target bytes match the device serial. A zero eligible-target result returns silently apart from manager debug logging. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:24-37`] [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:268-290`]

**Primary recommendation:** Plan one hygiene wave, one atomic transport-lifecycle wave, one routing/isolation wave, and one real-loopback/concurrency verification wave; do not add the second protocol before the task and serial foundations are correct. [VERIFIED: `.planning/ROADMAP.md:66-67`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| IPv4/IPv6 socket creation and lifecycle | API / Backend transport layer | OS networking | `EmulatedLifxServer` owns endpoints; the OS owns bind and `V6ONLY` semantics. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:544-555`] |
| Per-datagram family and reply ownership | API / Backend transport layer | — | Family, peer, and receiving transport enter through `DatagramProtocol`; none belongs in device state. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-52`] |
| Thread/WiFi target eligibility | API / Backend domain routing | Transport layer | `DeviceManager` owns device lookup/connectivity; the server passes only header and family. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:52-54`] |
| Packet effects and replies | API / Backend device processing | Transport layer | Device handlers produce replies; the datagram context supplies the only valid return transport. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:259-336`] |
| Background task lifetime | API / Backend lifecycle utility | FastAPI application lifespan | Each owner retains its own tasks; the server and event bridge share code, not collections. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] |
| Effective endpoint inspection | Public core-library API | OS networking | Properties expose normalised `(host, port)` values read from live socket `sockname`; raw IPv6 transport stays private. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:45-48`] |
| WebSocket broadcasts | Frontend server / FastAPI | Core task utility | Synchronous observers schedule async broadcasts; FastAPI lifespan must drain the bridge-owned tracker. [VERIFIED: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:65-76,204-218`] |

## Project Constraints (from supplied AGENTS.md instructions)

- Use Australian English spelling. [VERIFIED: user-supplied AGENTS.md instructions]
- Use `uv` exclusively for Python dependency management and execution; run tests as `uv run pytest`. [VERIFIED: user-supplied AGENTS.md instructions]
- Keep all imports at the top of Python files. Existing function-local imports in touched files are pre-existing, but new imports must not add to that pattern. [VERIFIED: user-supplied AGENTS.md instructions] [VERIFIED: `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:56-58,107-108,264-264`]
- Do not ignore an observed problem, uncommitted files, or failing tests. The focused baseline is green but emits un-awaited-coroutine warnings that HYG-01 must remove rather than merely suppress. [VERIFIED: focused pytest run on 2026-09-10]
- Use signed, signed-off commits (`git commit -s` with configured GPG key). [VERIFIED: user-supplied AGENTS.md instructions]
- The phase adds no dependency, changes no generated protocol/product file, targets Python 3.10–3.14, uses Ruff/Pyright, and retains complexity at 10 or below. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:77-85`] [VERIFIED: `pyproject.toml:23-55`]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `asyncio` | Standard library, Python 3.10–3.14 | Datagram protocols/transports, task scheduling, non-cancelling bounded waits | Already used throughout the packet path and required by the phase; no new runtime abstraction is needed. [VERIFIED: `pyproject.toml:52-75`] |
| Python `socket` | Standard library, Python 3.10–3.14 | Explicit `AF_INET6` socket construction, `IPV6_V6ONLY`, bind, `sockname`, non-blocking mode | It is the only layer that permits `V6ONLY` to be set before bind and can then transfer ownership to asyncio. [CITED: https://docs.python.org/3.14/library/socket.html] [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint] |
| Python `dataclasses` | Standard library, Python 3.10–3.14 | Frozen per-datagram context | The repository already uses dataclasses and Phase 2 locks one immutable context value. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:24-39,90-112`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | `>=8.4.2`; live environment 9.0.3 | Unit, lifecycle, real-loopback, concurrency, and regression tests | All Phase 2 verification. [VERIFIED: `pyproject.toml:8-16,58-75`] [VERIFIED: `uv run pytest --version`, 2026-09-10] |
| pytest-asyncio | `>=0.24.0`; live plugin 1.3.0 | Function-scoped event-loop tests | Existing config uses automatic asyncio mode and function-scoped loops. [VERIFIED: `pyproject.toml:12-15,74-75`] [VERIFIED: focused pytest run on 2026-09-10] |
| Ruff / Pyright | Ruff `>=0.14.2` (live 0.15.9); Pyright `>=1.1.407` (live 1.1.408) | Formatting/lint, import ordering, complexity, and Python 3.10 type compatibility | Run per implementation task and at phase gate. [VERIFIED: `pyproject.toml:11-16,23-55`] [VERIFIED: local CLI probes, 2026-09-10] |

### Alternatives Considered

Locked decisions remove architectural alternatives; the table records only why they must not enter plans. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:44-66`]

| Instead of | Could Use | Trade-off |
|------------|-----------|-----------|
| Separate IPv4 and V6-only IPv6 sockets | One dual-stack wildcard IPv6 socket | Rejected: platform defaults differ, the IPv4 compatibility alias would be lost, and the required default is `::1`, not `::`. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:77-81`] |
| Immutable packet-local context | Infer family from address tuple or mutable server state | Rejected: violates D-03/D-05 and fails interleaved traffic isolation. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-53`] |
| Explicit owner-local task tracker | `TaskGroup` spanning component lifetime | `TaskGroup` is structured around a lexical context and is unavailable on Python 3.10; the locked fire-and-forget contract requires owner-local scheduling from synchronous callbacks. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#task-groups] [VERIFIED: `pyproject.toml:52-55`] |
| Protocol closure future/event | Sleep or poll after `transport.close()` | Rejected: transport close is asynchronous and completion is reported by `connection_lost()`. [CITED: https://docs.python.org/3.14/library/asyncio-protocol.html#asyncio.BaseTransport.close] |

**Installation:** None. This phase adds no dependency. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:84-84`]

## Package Legitimacy Audit

Not applicable: no external package is installed or recommended by this phase. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:84-84`]

## Architecture Patterns

### System Architecture Diagram

```text
IPv4 datagram                           IPv6 datagram
127.0.0.1:effective_port                [::1]:effective_port
       |                                       |
       v                                       v
LifxProtocol(AF_INET, transport4)       LifxProtocol(AF_INET6, transport6)
       |                                       |
       +------------- immutable ---------------+
                     DatagramContext
              {family, peer, receive transport}
                              |
                              v
                    parse complete header
                              |
                              v
       DeviceManager.resolve_target_devices(header, family)
                    /                         \
            no eligible target           eligible target(s)
          debug + return only                    |
                                               v
                            receive stats + RX activity event
                                               |
                                               v
                             scenario / ack / device processing
                                               |
                                               v
                              context.transport.sendto(peer)
```

This flow enforces the acceptance ordering: routing rejection precedes every observable effect, while accepted replies use the same transport that received their request. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:24-37,89-100`]

### Recommended Project Structure

The following is a planning recommendation under the explicitly delegated placement discretion, not a claim that the new files already exist. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:68-72`]

```text
packages/lifx-emulator-core/src/lifx_emulator/
├── background_tasks.py             # reusable BackgroundTaskTracker
├── server.py                       # DatagramContext, dual endpoint transaction
└── devices/manager.py              # family-aware target eligibility
packages/lifx-emulator/src/lifx_emulator_app/api/
├── app.py                          # bridge tracker ownership and lifespan drain
└── services/event_bridge.py        # labelled scheduling through injected tracker
packages/lifx-emulator-core/tests/
├── test_background_tasks.py        # tracker unit/concurrency tests
├── test_server.py                  # lifecycle/context/serial tests
├── test_device_manager.py          # routing matrix
└── test_ipv6_transport.py          # real dual-family loopback tests
packages/lifx-emulator/tests/
└── test_websocket.py               # retained broadcasts, failures, shutdown
```

### Component Responsibilities

| Component | Responsibility | Must Not Own |
|-----------|----------------|--------------|
| `BackgroundTaskTracker` | Create/retain labelled tasks, consume outcomes, stop admission, drain five seconds, cancel/await remainder | Sockets, global collections, server health state [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] |
| `LifxProtocol` | Capture fixed family and its own transport; build one context per callback; reject new callbacks during shutdown; signal `connection_lost` | Assigning the global `server.transport` alias [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:45-53,60-60`] |
| `EmulatedLifxServer` | Atomic bind/publish/rollback, own server tracker, parse packet, order effects, route replies via context | Connectivity decisions or tuple-length family inference [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-54`] |
| `DeviceManager` | Apply header shape, exact serial, connectivity, and family eligibility; debug-log filtered Thread targets | Peer address, asyncio transport, acknowledgement or statistics [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:52-54`] |
| FastAPI app/event bridge | Own one bridge tracker instance, inject it into callback adapters, start admission in lifespan, drain it on teardown | Module-global task set [VERIFIED: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:65-76,204-218`] [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] |

### Pattern 1: Atomic Two-Bind Publication

**What:** Treat startup as a transaction with local variables until both transports and protocols exist. Bind IPv4 first, derive `effective_port` from its `sockname`, then construct/configure/bind/adopt IPv6. Activate both protocols and publish public state only at commit. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:57-60`]

**Critical ownership boundary:** before `create_datagram_endpoint(sock=raw_v6)` succeeds, local code owns and must close `raw_v6`; after success, the returned transport owns the socket and must be closed instead. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

**Port semantics:** preserve `server.port` as the configured/requested value for backwards compatibility; retain a private requested port and a private effective port. When `port=0` succeeds, update every device's advertised UDP port to the effective value, and make `add_device()` use the effective value while running. This avoids advertising port zero without redefining the existing configured attribute. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:136-162,451-462`] [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py:27-44`]

**Rollback:** catch `BaseException` around startup so cancellation follows the same cleanup path; suppress/log cleanup errors so a bind error or `CancelledError` is re-raised unchanged. Clear aliases, endpoint tuples, protocols, and effective port after cleanup. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:58-60`]

### Pattern 2: Immutable Datagram Context

Use a frozen dataclass containing `socket.AddressFamily`, the family-shaped peer address, and the receiving `asyncio.DatagramTransport`. Construct it in `datagram_received()` from protocol-owned fields and pass the context through `handle_packet()`, `_send_ack()`, and `_process_device_packet()`. Do not store a current family or current reply transport on the server. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-53`]

The address annotation must accept both the IPv4 `(host, port)` and IPv6 `(host, port, flowinfo, scope_id)` forms; normalise only public endpoints to the first two fields. [CITED: https://docs.python.org/3.14/library/socket.html#socket-families]

### Pattern 3: Resolve Before Effects

After length validation and `LifxHeader.unpack()`, call `resolve_target_devices(header, context.family)`. If the result is empty, return before incrementing `packets_received`, updating per-type counters, parsing/evaluating scenario payloads, notifying observers, or sending acknowledgements. This placement is required because the current code performs all receive-side effects before resolution. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:338-445`] [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:29-32`]

The manager matrix should be explicit and readable:

| Header/connectivity case | AF_INET | AF_INET6 |
|--------------------------|---------|----------|
| WiFi exact untagged serial | include | include |
| WiFi tagged or all-zero broadcast | include | include |
| Thread exact untagged serial | filter with debug | include |
| Thread tagged broadcast | filter with debug | filter with debug |
| Thread all-zero target | filter with debug | filter with debug |
| Wrong serial | no match | no match |

The values `"wifi"` and `"thread"` are the complete current connectivity domain. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:49-58`]

<!-- DATA_9N1B6F4S_START -->
```python
class Connectivity(str, Enum):
    WIFI = "wifi"
    THREAD = "thread"
```
<!-- DATA_9N1B6F4S_END -->

[VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/states.py:49-58`]

### Pattern 4: Owner-Local Background Task Tracker

One reusable tracker should expose synchronous `schedule(coroutine, label)`, admission control, a read-only pending count for tests/diagnostics, and async `shutdown(timeout=5.0)`. `schedule` obtains the running loop before creating a task, closes the already-created coroutine on no loop or closed admission, adds the task to its set immediately, and installs a labelled callback. The callback checks cancellation, retrieves `task.exception()`, logs failures, and discards in `finally`. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] [CITED: https://docs.python.org/3.14/library/asyncio-task.html#creating-tasks]

Use `asyncio.wait(snapshot, timeout=5.0)` for the grace period because it returns pending tasks without cancelling them. Then cancel every pending task and `await asyncio.gather(*pending, return_exceptions=True)`. Do not implement the grace period as `wait_for(gather(...))`: `wait_for` cancels its awaitable on timeout and may exceed the nominal timeout while cancellation completes, obscuring the required two-stage lifecycle. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#asyncio.wait] [CITED: https://docs.python.org/3.14/library/asyncio-task.html#asyncio.wait_for]

The event bridge tracker should be instantiated in `create_api_app()`, passed to all synchronous callback adapters, opened at lifespan start, and shut down in `finally` after the periodic broadcaster stops. This fixes the current no-loop coroutine leak and provides a real application shutdown owner. [VERIFIED: `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:30-40,67-79,117-161,314-316`] [VERIFIED: `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:65-76,204-218`]

The existing device save-task set retains tasks but does not consume failures. Because the shared utility now exists and project instructions prohibit ignoring observed defects, Phase 2 adopts one owner-local tracker in `EmulatedLifxDevice` as part of Plan 02-01. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:81-84,169-196`] [VERIFIED: user-supplied AGENTS.md instructions]

### Pattern 5: Protocol Closure Barrier

Give each protocol a completion future/event set by `connection_lost()`. `stop()` first flips both protocol admission flags, then drains the server tracker while transports remain send-capable, closes both transports, awaits both closure signals, and only then clears public endpoint state. Repeated stop returns immediately when there is no committed live pair. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:60-66`] [CITED: https://docs.python.org/3.14/library/asyncio-protocol.html#asyncio.BaseTransport.close]

### Anti-Patterns to Avoid

- **Second protocol writes `server.transport`:** current `connection_made()` does this and an IPv6 instance would silently replace the required IPv4 alias. Protocols must retain their own transport. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:180-198`]
- **Infer family from `len(addr)`:** IPv6 tuples often have four fields, but family is already known at socket creation and must be carried explicitly. [CITED: https://docs.python.org/3.14/library/socket.html#socket-families] [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-53`]
- **Publish after the first bind:** this exposes a half-started service and allows datagrams before routing state is committed. Keep protocols inactive and state local until both binds succeed. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:20-22,39-42`]
- **Catch only `Exception` during startup:** cancellation must roll back too; catch `BaseException`, clean up without masking, then bare-raise. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:58-58`]
- **Record receive activity before routing:** the present ordering violates side-effect-free Thread rejection. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:338-430`]
- **Use `rstrip("0000")`:** `rstrip` removes any run of characters in its argument, not a fixed suffix, and therefore truncates legitimate serial zeroes. Slice `header.target[:6].hex()` after testing tagged/all-zero broadcast. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:401-405`] [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:279-286`]
- **Patch a scheduler while creating real coroutine objects:** current WebSocket unit tests do this and emit un-awaited-coroutine warnings. Inject a fake tracker that closes/records coroutines or run the tracker on the event loop. [VERIFIED: `packages/lifx-emulator/tests/test_websocket.py:267-329`] [VERIFIED: focused pytest run on 2026-09-10]
- **Format IPv6 as raw `host:port`:** `[::1]:56700` is unambiguous; `::1:56700` is not. Preserve the current IPv4 string while adding bracketed IPv6 formatting. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:239-255,316-334,407-425`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dual-family multiplexing | Tuple-shape inference or one mutable current-family field | Two stdlib sockets plus immutable context | The socket/protocol already has authoritative family identity; mutable inference races. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-53`] |
| IPv6-only enforcement | Platform-default guessing | `socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)` before bind | Linux's default can be false while Windows defaults true; explicit configuration gives parity. [CITED: https://man7.org/linux/man-pages/man2/IPV6_V6ONLY.2const.html] [CITED: https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ipv6-socket-options] |
| Task retention | Bare `create_task`, callback handles, or a module-global set | Reusable owner-local tracker | The event loop keeps weak task references; completion and exception retrieval need ownership. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#creating-tasks] |
| Shutdown timeout | Sleep loops | `asyncio.wait` then explicit cancel/gather | `wait` provides pending tasks without implicit cancellation. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#asyncio.wait] |
| Socket closure detection | Fixed delay | Protocol `connection_lost()` signal | Transport close completes asynchronously and reports through the protocol. [CITED: https://docs.python.org/3.14/library/asyncio-protocol.html#asyncio.BaseTransport.close] |
| Target rendering | String trimming | `target[:6].hex()` plus explicit broadcast predicate | The wire target is eight bytes containing a six-byte serial and two padding bytes. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:279-286`] |

**Key insight:** the hard part is not opening an IPv6 socket; it is preserving ownership and effect ordering from socket receipt through shutdown. The stdlib already supplies every primitive required, so new abstractions should encode project policy rather than reimplement networking. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

## Test Architecture

Project Nyquist validation is explicitly disabled, so the formal `Validation Architecture` section is omitted; the phase still requires comprehensive tests and should use the following implementation test map. [VERIFIED: `.planning/config.json:15-17`] [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:56-64`]

### Test Layers

| Layer | Location | What it proves |
|-------|----------|----------------|
| Pure unit | `test_background_tasks.py`, `test_device_manager.py` | Tracker retention/outcomes and complete connectivity × family × target-shape matrix without sockets. [VERIFIED: `packages/lifx-emulator-core/tests/test_device_manager.py:92-172`] |
| Protocol unit | `test_server.py` | Two protocol instances capture distinct family/transport contexts, reply through the receiving transport, format targets/addresses, and stop admission. [VERIFIED: `packages/lifx-emulator-core/tests/test_server.py:345-389`] |
| Lifecycle simulation | `test_server.py` | Call order (`V6ONLY` before bind), exact exception propagation, cancellation rollback, delayed closure, idempotent start/stop, and no half-published endpoints. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:89-103`] |
| Real loopback integration | new `test_ipv6_transport.py` or `test_integration.py` | Actual AF_INET/AF_INET6 sockets share a `port=0` allocation, V6ONLY reads back 1, WiFi answers both, Thread answers only exact IPv6 unicast. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:89-100`] |
| Concurrency/GC | core and app tests | Interleaved families cannot cross transports; blocked tasks survive `gc.collect()`; bridge/server sets drain; failures are logged once. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:93-100`] |
| Regression | existing full suites | Existing IPv4 packets, direct manager calls, WebSocket behaviour, and 80% global gate remain green. [VERIFIED: `pyproject.toml:58-75`] [VERIFIED: `.github/workflows/ci.yml:72-105`] |

### Requirement-to-Test Matrix

| Requirement | Minimum deterministic tests |
|-------------|-----------------------------|
| NET-01 | Default dual bind; explicit non-zero port; `port=0`; setsockopt-before-bind fake socket; second-bind failure; cancellation during second creation; start twice; stop twice; delayed `connection_lost`; Linux/macOS real socket read-back; simulated Windows universal call path. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:18-22,89-92`] |
| NET-02 | Create IPv4 and IPv6 protocols with distinct fake transports; inject interleaved datagrams; assert each manager call receives its packet's family and each send uses its packet's transport. Include a barrier so both handlers are concurrently alive. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:24-27,93-93`] |
| NET-03 | Parameterise Thread requests: accepted exact IPv6 untagged, IPv4 exact, IPv4/IPv6 tagged, IPv4/IPv6 all-zero, and wrong serial. Set both ack/response flags; snapshot all counters/activity and spy scenario/device methods. Repeat and interleave to prove zero rejected effects. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:29-32,94-96`] |
| NET-04 | Send the same WiFi GetColor/GetService request through real IPv4 and IPv6 client sockets; compare decoded replies and family-local source/destination; retain current exact-byte IPv4 fixtures unchanged. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:34-37,97-98`] |
| NET-05 | Assert properties are `None` before start, both normalised two-tuples only after complete start, same non-zero port for `port=0`, remain unpublished during blocked second bind, and return `None` after failure/stop. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:39-42,99-99`] |
| HYG-01 | Block N scheduled operations on an event, call `gc.collect()`, assert N retained, release and assert exactly-once completion/empty set; separately force exception, cancellation, no-running-loop, grace-period completion, timeout cancellation, and FastAPI lifespan shutdown. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:44-47,100-100`] |
| HYG-02 | Target serials ending `0`, `00`, and `0000`; tagged non-zero; untagged all-zero; short packet. Assert both logger output and `PacketEvent.target`; short input adds no event. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:49-52,101-102`] |

### Reliable Real-Socket Technique

Use non-blocking client sockets and `await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), timeout)` rather than blocking `recvfrom()` plus arbitrary sleeps. Bind separate AF_INET and AF_INET6 clients, use the normalised endpoint properties as destinations, and assert the IPv6 client destination expands to a four-tuple only at the socket boundary. `wait_for` is appropriate for negative receive assertions; the tracker grace period should use `wait` instead. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#working-with-socket-objects-directly] [CITED: https://docs.python.org/3.14/library/asyncio-task.html#asyncio.wait_for]

### Baseline and Commands

- Focused baseline: `100 passed` for `test_server.py`, `test_device_manager.py`, and `test_websocket.py` on macOS/Python 3.14.7, but seven warnings include real un-awaited bridge/AsyncMock coroutines. Treat warning elimination as HYG-01 acceptance, not as a green baseline exemption. [VERIFIED: focused pytest run on 2026-09-10]
- Per task: `uv run --frozen pytest <changed test files> -q`. [VERIFIED: user-supplied AGENTS.md instructions]
- Per wave: `uv run --frozen pytest packages/lifx-emulator-core/tests/test_server.py packages/lifx-emulator-core/tests/test_device_manager.py packages/lifx-emulator-core/tests/test_ipv6_transport.py packages/lifx-emulator/tests/test_websocket.py`. [VERIFIED: recommended phase test set based on existing paths]
- Phase gate: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, and `uv run --frozen pytest --cov-fail-under=80`. [VERIFIED: `.github/workflows/ci.yml:54-65,97-105`]

## Common Pitfalls

### Pitfall 1: Asyncio Socket Ownership Changes Mid-Call

**What goes wrong:** rollback double-closes the raw socket or leaks the adopted socket. **Why:** ownership transfers to the transport only after successful endpoint creation. **Avoidance:** keep separate raw-socket and returned-transport locals, null the raw owner after adoption, and clean only the current owner. **Warning sign:** file-descriptor growth, `Bad file descriptor`, or bind reuse failure after a forced second-endpoint error. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

### Pitfall 2: Cleanup Masks the Original Bind Error

**What goes wrong:** the caller receives a cleanup exception instead of the platform socket error or cancellation. **Why:** awaiting closure inside `except` can raise before the bare `raise`. **Avoidance:** cleanup helpers log/suppress their own errors and the outer handler re-raises the captured original unchanged. **Warning sign:** a rollback test compares exception identity and fails. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:58-58`]

### Pitfall 3: Half-Started Protocol Accepts Traffic

**What goes wrong:** IPv4 datagrams arrive between the first and second bind and observe incomplete global state. **Why:** `create_datagram_endpoint` starts delivery before `start()` returns. **Avoidance:** construct protocols with admission disabled and activate both only at commit. **Warning sign:** a test holding the second bind sees handler calls or non-`None` endpoint properties. [CITED: https://docs.python.org/3.14/library/asyncio-protocol.html#protocols]

### Pitfall 4: Reply Transport Re-Selection

**What goes wrong:** concurrent IPv4 and IPv6 requests reply on whichever transport was assigned last. **Why:** `_send_ack` and `_process_device_packet` currently read `self.transport`. **Avoidance:** pass the immutable context all the way to both send sites. **Warning sign:** one fake transport receives both families' sends. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:211-234,259-307`]

### Pitfall 5: Eligibility Happens After Observation

**What goes wrong:** a rejected Thread packet still increments server counters or appears in activity/WebSocket streams. **Why:** current stats and observer calls precede manager resolution. **Avoidance:** resolve immediately after header parse; empty result returns before all effects. **Warning sign:** a no-response test passes while counters or activity still change. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:338-430`]

### Pitfall 6: Graceful Shutdown Closes the Reply Socket Too Soon

**What goes wrong:** delayed/scenario responses are retained as tasks but cannot send during their grace period. **Why:** closing transports before tracker drain invalidates their context transport. **Avoidance:** stop protocol admission, drain/cancel tasks, then close transports. **Warning sign:** tasks finish but no datagrams are emitted during shutdown. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:60-66`]

### Pitfall 7: Completed Task Exceptions Stay Unobserved

**What goes wrong:** the strong set fixes garbage collection but exceptions still produce `Task exception was never retrieved`. **Why:** `set.discard` alone does not call `exception()` or `result()`. **Avoidance:** retrieve the outcome before discarding and distinguish expected cancellation. **Warning sign:** tests pass with event-loop warning output. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#asyncio.Task.exception]

### Pitfall 8: Port Zero Is Shared Incorrectly

**What goes wrong:** independently binding both sockets to port zero gives two different ports; leaving device state at zero makes StateService unusable. **Why:** port zero is allocated per bind. **Avoidance:** bind IPv4 first, read its allocated port, bind IPv6 to that number, and update device advertised ports only after commit. **Warning sign:** endpoint ports differ or StateService reports zero. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:57-58`] [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py:27-44`]

## Code Examples

These examples show verified stdlib patterns; exact internal class/method names remain the planner's implementation choice. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:68-72`]

### Pre-bind V6-only Socket Adoption

<!-- DATA_5K8R2V7M_START -->
`IPV6_V6ONLY` must be set before bind; the implementation must not rely on platform dual-stack defaults.

The default IPv6 bind is loopback `::1`, never wildcard `::`; the existing IPv4 default remains `127.0.0.1`.
<!-- DATA_5K8R2V7M_END -->

[VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:77-80`]

```python
owned_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
try:
    owned_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    owned_socket.bind((ipv6_bind_address, effective_port))
    owned_socket.setblocking(False)
    ipv6_transport, ipv6_protocol = await loop.create_datagram_endpoint(
        protocol_factory,
        sock=owned_socket,
    )
except BaseException:
    owned_socket.close()
    raise
```

Source pattern: the sibling oracle uses this exact option → bind → non-blocking → asyncio order and closes on partial failure. [VERIFIED: `../lifx-async/tests/conftest.py:302-336`] [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

The production implementation must refine the example's ownership handling once a transport exists; after adoption, close the transport rather than the raw socket. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint]

### Strong Fire-and-Forget Retention

```python
background_tasks = set()
task = asyncio.create_task(some_coro())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

This is the official minimum retention pattern; Phase 2 must add labelled exception retrieval and shutdown semantics around it. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#creating-tasks]

### Exact Serial Extraction

<!-- DATA_1J9P4C6X_START -->
```python
if header.tagged or header.target == b"\x00" * 8:
    # Broadcast to all devices
    target_devices = self._device_repository.get_all()
else:
    # Specific device - convert target bytes to serial string
    # Target is 8 bytes: 6-byte MAC + 2 null bytes
    target_serial = header.target[:6].hex()
```
<!-- DATA_1J9P4C6X_END -->

[VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:279-286`]

Use the same explicit tagged/all-zero predicate and `header.target[:6].hex()` in one shared formatting helper so unknown-packet logging, normal RX logging, activity events, and routing cannot disagree. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:382-405`] [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:279-286`]

## State of the Art

| Old Approach | Current Recommended Approach | When Changed | Impact |
|--------------|------------------------------|--------------|--------|
| `local_addr=` lets asyncio create the only UDP socket | Explicit IPv6 socket configured before bind and adopted with `sock=` | Required by this phase; `sock=` supported for datagrams on Windows since Python 3.8 | Cross-platform explicit V6-only behaviour and one shared port. [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint] |
| Bare `create_task()` for background work | Strong owner-local set plus done callback and lifecycle drain | Official current asyncio guidance | Prevents premature collection and consumes failures. [CITED: https://docs.python.org/3.14/library/asyncio-task.html#creating-tasks] |
| One mutable reply transport | Immutable receive context | Locked Phase 2 design | Makes interleaved family routing race-free. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:45-53`] |
| Close and return | Close and await protocol `connection_lost()` | Locked Phase 2 lifecycle | Endpoint properties describe genuinely live state only. [CITED: https://docs.python.org/3.14/library/asyncio-protocol.html#asyncio.BaseTransport.close] |

**Deprecated/outdated:** relying on the OS default for `IPV6_V6ONLY` is invalid for this phase because Linux's default is configurable and commonly false while Windows defaults true. [CITED: https://man7.org/linux/man-pages/man2/IPV6_V6ONLY.2const.html] [CITED: https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ipv6-socket-options]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | None. Recommendations derive from locked decisions, source files opened this session, official documentation, and explicit local probes. | — | — |

## Resolved Decisions

1. **RESOLVED — Windows verification uses universal simulation plus real Linux/macOS coverage.**
   - Evidence: Microsoft documents `IPV6_V6ONLY` support and Python documents datagram `sock=` support on Windows since 3.8, but this repository has no Windows CI runner. [CITED: https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ipv6-socket-options] [CITED: https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint] [VERIFIED: `.github/workflows/ci.yml:72-81`]
   - Resolution: Phase 2 accepts universal fake socket/loop call-order tests together with real Linux and macOS CI. Live Windows runtime evidence remains deferred to the already-recorded later manual/Phase 6 verification; atomic startup is not weakened and no IPv4-only fallback is introduced. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:77-85`] [VERIFIED: `.planning/STATE.md:85-87`]

2. **RESOLVED — Device persistence scheduling migrates to the shared owner-local tracker.**
   - Evidence: the existing device tracker strongly retains and discards tasks but never retrieves exceptions, while project instructions require observed problems to be addressed. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:169-196`] [VERIFIED: `.planning/REQUIREMENTS.md:62-62`] [VERIFIED: user-supplied AGENTS.md instructions]
   - Resolution: Phase 2 includes the bounded device persistence migration in Plan 02-01. `EmulatedLifxDevice` receives its own instance of the shared tracker, preserving persistence data and timing while ensuring save-task exceptions are observed rather than deferred. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-01-PLAN.md:149-181`]

## Environment Availability

| Dependency | Required By | Available | Version / Evidence | Fallback |
|------------|-------------|-----------|--------------------|----------|
| `uv` | All Python commands | ✓ | 0.12.7 [VERIFIED: local CLI probe, 2026-09-10] | None; project mandates uv |
| Python | Runtime/type floor | ✓ | 3.14.7 locally; project/CI target 3.10–3.14 [VERIFIED: local CLI probe, 2026-09-10] [VERIFIED: `.github/workflows/ci.yml:80-94`] | CI matrix supplies other versions |
| IPv4 loopback UDP | Dual bind | ✓ | Bound `127.0.0.1:58067` in local probe [VERIFIED: privileged local socket probe, 2026-09-10] | None |
| IPv6 loopback UDP | Dual bind | ✓ | Bound `[::1]:58067` with `IPV6_V6ONLY == 1` beside IPv4 [VERIFIED: privileged local socket probe, 2026-09-10] | Atomic startup must fail; no IPv4-only fallback |
| asyncio adoption/closure | Lifecycle | ✓ | Two pre-bound same-port sockets adopted; both closure callbacks completed and transports reported closing [VERIFIED: privileged local asyncio probe, 2026-09-10] | Unit fakes for failure paths |
| Linux CI | Cross-platform acceptance | ✓ configured, not run locally | Ubuntu latest × Python 3.10–3.14 [VERIFIED: `.github/workflows/ci.yml:72-101`] | GitHub CI |
| macOS CI | Cross-platform acceptance | ✓ configured | macOS latest × Python 3.10–3.14 [VERIFIED: `.github/workflows/ci.yml:72-101`] | Local macOS probe |
| Windows CI | Cross-platform acceptance | ✗ | No Windows matrix row [VERIFIED: `.github/workflows/ci.yml:72-81`] | Fake-socket unit tests plus manual verification |

**Missing dependencies with no fallback:** None for local implementation. Windows live verification is an evidence gap, not a build blocker. [VERIFIED: environment probes and CI inspection, 2026-09-10]

**Missing dependencies with fallback:** Windows CI — use platform-independent implementation, simulated call-order/error tests, and a recorded manual check. [VERIFIED: `.planning/STATE.md:85-87`]

## Security Domain

Security enforcement is enabled because `.planning/config.json` does not set `security_enforcement` to false. [VERIFIED: `.planning/config.json:1-56`]

### Applicable ASVS Categories

The table uses the category labels required by the GSD research contract. OWASP identifies these as authentication, session management, access control, validation/sanitisation/encoding, and stored cryptography in ASVS 4.0.3; ASVS 5.0 has renumbered chapters, so plans should cite the ASVS version when adding formal controls. [CITED: https://devguide.owasp.org/en/06-verification/01-guides/03-asvs/] [CITED: https://owasp.org/www-project-application-security-verification-standard/]

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No identity/authentication surface changes in this UDP transport phase. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:54-73`] |
| V3 Session Management | no | UDP datagrams are connectionless and this phase introduces no application session. [VERIFIED: phase architecture and boundaries] |
| V4 Access Control | yes, domain-level | Enforce Thread eligibility in `DeviceManager` before all effects; never trust packet target alone. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:29-32`] |
| V5 Input Validation | yes | Reject short headers before unpack, preserve exact target bytes, and resolve only recognised family/connectivity combinations. [VERIFIED: `packages/lifx-emulator-core/src/lifx_emulator/server.py:338-380`] |
| V6 Cryptography | no | No encryption, key, credential, or cryptographic protocol changes are in scope. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:54-73`] |

### Known Threat Patterns for Async UDP Transport

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-family reachability bypass | Elevation of privilege | Immutable authoritative family from protocol/socket; manager-side connectivity filtering before effects. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:47-54`] |
| UDP spoofing / unauthenticated datagrams | Spoofing | Keep default binds on numeric loopback addresses in this phase; validate header length/target and do not expand to wildcard `::`. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:77-83`] |
| Broadcast amplification by Thread devices | Denial of service | Thread targets never answer tagged/all-zero packets on either family. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:29-32`] |
| Task-flood memory retention | Denial of service | Admission stop, observable owner-local set, bounded five-second drain, cancellation, and empty-set postcondition. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md:63-66`] |
| Half-started endpoint exposure | Information disclosure / denial of service | Transactional publish after both binds; full rollback and cleared properties on any failure. [VERIFIED: `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md:20-22,39-42`] |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/02-ipv6-transport-and-thread-isolation/02-CONTEXT.md` — locked implementation and lifecycle decisions. [VERIFIED: repository read]
- `.planning/phases/02-ipv6-transport-and-thread-isolation/02-SPEC.md` and `.planning/REQUIREMENTS.md` — acceptance order, platform matrix, and phase boundaries. [VERIFIED: repository read]
- `packages/lifx-emulator-core/src/lifx_emulator/server.py` — current transport, scheduling, send, effect ordering, serial, and lifecycle seams. [VERIFIED: repository read]
- `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` and `devices/states.py` — current public routing contract and connectivity source of truth. [VERIFIED: repository read]
- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` and `api/app.py` — bridge scheduling and application lifecycle ownership. [VERIFIED: repository read]
- `../lifx-async/tests/conftest.py` and `tests/test_api/test_ipv6_e2e.py` — read-only IPv6 oracle and real client expectations. [VERIFIED: repository read]
- Local macOS socket and asyncio probes — same ephemeral port, V6ONLY read-back, adoption, and closure. [VERIFIED: executed 2026-09-10]

### Secondary (MEDIUM confidence, tier returned by research seam)

- [Python 3.14 event-loop documentation](https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint) — datagram families, `sock=` ownership, Windows support. [CITED: official docs]
- [Python 3.14 transports/protocols](https://docs.python.org/3.14/library/asyncio-protocol.html) — close and `connection_lost` semantics. [CITED: official docs]
- [Python 3.14 tasks](https://docs.python.org/3.14/library/asyncio-task.html) — weak references, strong retention, exception/cancellation/wait semantics. [CITED: official docs]
- [Python 3.14 socket](https://docs.python.org/3.14/library/socket.html) — address families, IPv6 tuple, non-blocking sockets. [CITED: official docs]
- [Microsoft IPPROTO_IPV6 options](https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ipv6-socket-options) — Windows `IPV6_V6ONLY`. [CITED: official docs]
- [Linux IPV6_V6ONLY manual](https://man7.org/linux/man-pages/man2/IPV6_V6ONLY.2const.html) — Linux semantics and configurable default. [CITED: Linux man-pages mirror]
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) — security-category applicability and current stable version. [CITED: official project]

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no dependency addition; exact runtime/tool constraints are in the repository and installed versions were probed.
- Architecture: HIGH — locked context maps directly onto source files opened this session and a working sibling oracle.
- Socket mechanics: MEDIUM overall — official docs plus a successful macOS probe; Linux/macOS CI will verify, but Windows lacks a live runner.
- Pitfalls: HIGH for current-code findings; MEDIUM for cross-platform failure manifestations.
- Test architecture: HIGH — derived from all fifteen locked acceptance criteria, current test infrastructure, and observed baseline warnings.

**Research date:** 2026-09-10
**Valid until:** 2026-10-10 for stdlib/repository patterns; re-check CI runner and Python patch versions at execution.
