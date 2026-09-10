# Phase 2: IPv6 Transport and Thread Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 02-ipv6-transport-and-thread-isolation
**Areas discussed:** Transport ownership and compatibility, Family-routing contract, Startup and rollback lifecycle, Task tracking and failures

---

## Transport Ownership and Compatibility

### Existing `server.transport` meaning

| Option | Description | Selected |
|--------|-------------|----------|
| IPv4 transport alias | Preserve every existing caller and add a separate IPv6 inspection surface | ✓ |
| Active transport map | Change `transport` to a family-keyed mapping; cleaner internally but breaking | |
| Deprecated compatibility property | Keep an IPv4 compatibility property backed by a new registry and start a deprecation path | |

**User's choice:** IPv4 transport alias

### Effective endpoint API

| Option | Description | Selected |
|--------|-------------|----------|
| Named tuple properties | `ipv4_endpoint` and `ipv6_endpoint` return live `(host, port)` tuples or `None` | ✓ |
| Family lookup method | Use `get_endpoint(family)` for one extensible but less discoverable API | |
| Endpoint value object | Add immutable public objects containing family, host and port | |

**User's choice:** Named tuple properties

### Reply transport selection

| Option | Description | Selected |
|--------|-------------|----------|
| Receiving protocol transport | Carry the protocol instance's transport with each datagram and reply through it | ✓ |
| Server family lookup | Carry only family and look up the current server transport when sending | |
| Address inference | Infer the family from peer-address tuple shape | |

**User's choice:** Receiving protocol transport

### Raw IPv6 transport visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Keep it internal | Expose only `ipv6_endpoint`; retain `server.transport` solely for IPv4 compatibility | ✓ |
| Public `ipv6_transport` | Expose a symmetrical raw transport attribute | |
| Read-only property | Allow raw transport inspection without assignment | |

**User's choice:** Keep it internal

**Notes:** The supported public addition is endpoint inspection, not a second mutable transport attribute.

---

## Family-Routing Contract

### Per-datagram identity carrier

| Option | Description | Selected |
|--------|-------------|----------|
| Immutable datagram context | Carry family, peer address and receiving transport in one packet-local value | ✓ |
| Separate arguments | Pass family, address and transport independently through each method | |
| Protocol instance | Pass `LifxProtocol` through packet logic and read its state there | |

**User's choice:** Immutable datagram context

### Manager context boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Header plus family only | Keep peer and transport in the server; manager resolves transport-eligible devices | ✓ |
| Full datagram context | Give `DeviceManager` peer and asyncio transport details | |
| Two-stage result | Return accepted devices plus structured rejection reasons | |

**User's choice:** Header plus family only

### Existing manager API compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Optional family defaulting to IPv4 | Preserve `resolve_target_devices(header)` callers as the legacy IPv4 path | ✓ |
| Required family argument | Fail closed without explicit family, breaking existing callers and test doubles | |
| New family-aware method | Retain the old method and add a second routing API | |

**User's choice:** Optional family defaulting to IPv4

### Family rejection result

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve device list | Filter ineligible Thread targets and log debug details inside `DeviceManager` | ✓ |
| Resolution object | Return accepted devices and rejection reasons | |
| Accepted/rejected lists | Return both sets for possible later metrics | |

**User's choice:** Preserve device list

**Notes:** Rejection remains deliberately unobservable outside debug logs; no rejected-target metric or result type is introduced.

---

## Startup and Rollback Lifecycle

### Shared-port bind order

| Option | Description | Selected |
|--------|-------------|----------|
| IPv4 first | Bind the compatibility endpoint, obtain the effective port, then bind IPv6; roll back on failure | ✓ |
| IPv6 first | Establish the constrained IPv6 socket before IPv4 | |
| Pre-create both sockets | Configure both manually before handing either to asyncio | |

**User's choice:** IPv4 first

### Repeated `start()`

| Option | Description | Selected |
|--------|-------------|----------|
| Idempotent no-op | Keep current endpoints and log at debug level | ✓ |
| Raise `RuntimeError` | Expose lifecycle misuse while preventing duplicates | |
| Restart atomically | Close and recreate both endpoints | |

**User's choice:** Idempotent no-op

### Deterministic `stop()`

| Option | Description | Selected |
|--------|-------------|----------|
| Await both closures | Finish only after both transports report closure, then clear live state | ✓ |
| Return after `close()` | Match the current lightweight method while release remains asynchronous | |
| Retain last endpoints | Preserve historical values after asynchronous close | |

**User's choice:** Await both closures

### Startup error surface

| Option | Description | Selected |
|--------|-------------|----------|
| Roll back and re-raise original | Clean partial resources and preserve the platform exception | ✓ |
| Wrap as `RuntimeError` | Expose one stable server error type with a chained cause | |
| Fall back to IPv4-only | Keep legacy service running if IPv6 fails | |

**User's choice:** Roll back and re-raise original

**Notes:** An initial stray backtick response to the bind-order question was treated as invalid input; the user then explicitly selected IPv4 first.

---

## Task Tracking and Failures

### Tracking pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Reusable internal tracker | One utility, with a separate tracker instance for each owning component | ✓ |
| Owner-local task sets | Duplicate the persistence pattern in every component | |
| One server-wide tracker | Centralise all core and app background work in one collection | |

**User's choice:** Reusable internal tracker

### Completed task failures

| Option | Description | Selected |
|--------|-------------|----------|
| Consume and context-log | Retrieve exceptions, log the operation label at error, and treat cancellation as debug | ✓ |
| Remove only | Discard tasks and rely on asyncio's default unhandled-exception report | |
| Degraded server state | Surface background failure in later health/statistics calls | |

**User's choice:** Consume and context-log

### Shutdown of in-flight work

| Option | Description | Selected |
|--------|-------------|----------|
| Five-second graceful drain | Stop new work, wait up to five seconds, then cancel and await the remainder | ✓ |
| Unbounded drain | Guarantee completion but risk hanging on configured response delays | |
| Immediate cancellation | Prioritise shutdown speed while intentionally discarding work | |

**User's choice:** Five-second graceful drain

### Scheduling API

| Option | Description | Selected |
|--------|-------------|----------|
| Tracker schedules coroutine | Create and retain atomically; close the coroutine safely when no loop exists | ✓ |
| Track existing task | Let callers create the task before registration | |
| Accept task factories | Defer coroutine construction until a loop is available | |

**User's choice:** Tracker schedules coroutine

**Notes:** Phase 3 may reuse the utility with its own tracker instance; this phase does not introduce shared global task state or a health API.

---

## the agent's Discretion

- Internal class and module names for the datagram context and task tracker
- Exact log wording and labels
- Test-file organisation and helper factoring
- Internal type aliases used to implement the public tuple endpoint properties

## Deferred Ideas

None — discussion stayed within the Phase 2 boundary.
