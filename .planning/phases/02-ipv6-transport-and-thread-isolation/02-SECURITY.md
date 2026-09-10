---
phase: "02"
slug: "ipv6-transport-and-thread-isolation"
status: verified
threats_total: 20
threats_closed: 20
threats_open: 0
asvs_level: 1
security_block_on: high
register_authored_at_plan_time: true
created: "2026-09-11"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| UDP socket → protocol callback | Untrusted IPv4 and IPv6 datagrams enter parsing and scheduling. | LIFX headers, payloads, peer addresses, address family |
| Scheduled coroutine → owner lifecycle | Admitted work must remain retained, bounded and observable through shutdown. | Packet processing and persistence coroutines |
| Header bytes → activity/log surface | Untrusted target bytes become operator-visible text only after validation. | Target serial and packet metadata |
| UDP/device callbacks → WebSocket bridge | Packet-driven synchronous events fan out into asynchronous broadcasts. | Activity and device-state event dictionaries |
| WebSocket bridge → FastAPI lifespan | Slow or failed clients must not make background work unbounded or outlive the app. | Bounded queued broadcasts and shutdown signals |
| Parsed target → device manager | Untrusted packet identity is matched against device connectivity and serial. | Tagged flag, target bytes, IPv4/IPv6 family |
| Protocol context → response transport | The receiving endpoint determines the socket and family used for replies. | Frozen transport, peer address and family |
| Host network stack → bind lifecycle | Socket allocation and family availability determine whether a complete server becomes live. | Bind addresses, ports, socket options and errors |
| Shutdown coordinator → handlers/transports | Ordering determines whether accepted work finishes and resources close. | Admission state, tasks, transports and close events |
| Phase source → dependency supply chain | Package installation could introduce unreviewed code. | `pyproject.toml` and `uv.lock` |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Denial of service | `LifxProtocol.datagram_received` / `BackgroundTaskTracker` | high | mitigate | Owner-local strong task references, bounded packet admission before allocation, explicit shutdown drain/cancel, overload counter, and forced-GC/flood tests. | closed |
| T-02-02 | Tampering | Target rendering in `handle_packet` | medium | mitigate | Complete-header and declared-size validation precedes `_format_target()`, which emits `target[:6].hex()` or the explicit broadcast label; exact trailing-zero tests pass. | closed |
| T-02-03 | Repudiation | Background task failures | medium | mitigate | `_on_done()` retrieves each non-cancelled outcome exactly once and logs the owner and stable operation label; failure and cancellation tests pass. | closed |
| T-02-04 | Denial of service | Tracker shutdown | high | mitigate | Admission stops first, grace is bounded, remaining work is cancelled and awaited even when shutdown is cancelled, and reopen requires an empty tracker. | closed |
| T-02-SC | Tampering | Package installation in Plans 02-01 and 02-02 | low | accept | Both plans used existing standard-library/project primitives; `pyproject.toml` and `uv.lock` are unchanged across the Phase 2 implementation range. | closed |
| T-02-05 | Denial of service | Event bridge callback fan-out | high | mitigate | One finite `WebSocketEventQueue` reserves capacity before event-coroutine construction and uses a fixed worker pool with observable drop-newest overload accounting. | closed |
| T-02-06 | Repudiation | Failed WebSocket broadcast | medium | mitigate | Stable operation labels flow through the queue worker; broadcast failures are retrieved/logged and deterministic failure-path tests leave no orphaned work. | closed |
| T-02-07 | Tampering | Bridge tracker ownership | medium | mitigate | FastAPI owns and injects one queue across adapters; direct-construction fallbacks remain owner-local and no global mutable task collection exists. | closed |
| T-02-08 | Denial of service | FastAPI shutdown | high | mitigate | Lifespan stops the periodic producer, closes bridge admission, applies a five-second drain bound, cancels workers when required and finishes with no pending work. | closed |
| T-02-03-01 | Spoofing | `DeviceManager.resolve_target_devices` | high | mitigate | Thread eligibility requires exact untagged IPv6 unicast before processing or side effects; the complete negative decision table and real-loopback tests pass. | closed |
| T-02-03-02 | Tampering | `_DatagramContext` | medium | mitigate | A frozen context captures the receiving protocol's family, peer and transport; downstream acknowledgement and response paths use that transport. | closed |
| T-02-03-03 | Information disclosure | Rejection DEBUG logs | low | accept | Per-rejection rationale contains emulator connectivity/target context only, is disabled at normal log levels, and is required for deterministic routing diagnostics. | closed |
| T-02-03-04 | Denial of service | Packet parsing and dispatch | medium | mitigate | Short, malformed and declared-size-mismatched datagrams are rejected before target resolution/dispatch with bounded counter effects; ineligible devices never enter processing. | closed |
| T-02-03-SC | Tampering | Package installation in Plan 02-03 | low | accept | The plan added no dependency and left the locked project dependency graph unchanged. | closed |
| T-02-04-01 | Spoofing | Thread target handling | high | mitigate | Kernel-backed loopback tests prove only exact untagged IPv6 unicast reaches a Thread device; IPv4, tagged, broadcast, zero and mismatched targets stay silent. | closed |
| T-02-04-02 | Tampering | IPv6 socket configuration | high | mitigate | `IPV6_V6ONLY=1` is set before bind and the live socket option is asserted by the real-loopback test. | closed |
| T-02-04-03 | Denial of service | Atomic startup and retry | medium | mitigate | A lifecycle lock protects provisional bind/commit, every partial pair is rolled back, and only port-zero IPv6 collisions retry with a five-attempt bound. | closed |
| T-02-04-04 | Denial of service | Shutdown closure waits | medium | mitigate | Admission stops before task drainage, each endpoint closure wait is bounded, old task generations are tracked, and public endpoint state is cleared deterministically. | closed |
| T-02-04-05 | Information disclosure | Configurable network exposure | medium | mitigate | IPv4 and IPv6 defaults remain loopback-only (`127.0.0.1` and `::1`); alternate exposure requires explicit caller-selected bind addresses used verbatim. | closed |
| T-02-04-SC | Tampering | Package installation in Plan 02-04 | low | accept | The plan added no dependency and left the locked project dependency graph unchanged. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count towards `threats_open`.*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party).*

## Verification Evidence

| Check | Evidence | Result |
|-------|----------|--------|
| Security-focused behavioural suite | `UV_CACHE_DIR=/tmp/lifx-review-uv uv run --frozen pytest` across tracker, persistence, manager, server, real IPv6, Thread identity, WebSocket and API test modules with `--no-cov` | 422 passed; one existing Starlette/httpx deprecation warning |
| Packet admission and overload observability | `BackgroundTaskTracker(max_pending=...)`, pre-allocation capacity check, `packets_dropped_overload`, REST statistics exposure and flood assertions | verified |
| WebSocket fan-out and lifecycle | Finite event queue, fixed workers, pre-construction reservation, drop metric, lifespan drain/cancel and blocked-client flood test | verified |
| Thread routing isolation | Frozen datagram context, manager eligibility table, no-side-effect rejection tests and real IPv4/IPv6 loopback matrix | verified |
| Dual-family socket lifecycle | V6-only pre-bind option, same-port atomic publication, bounded collision retry, endpoint-loss generation rotation and bounded teardown tests | verified |
| Dependency integrity | `git diff --name-only b7c24eb..HEAD -- pyproject.toml uv.lock` returned no paths | verified |

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-SC | No package installation occurred in Plans 02-01 or 02-02, so existing dependency controls remain the appropriate boundary. | Phase 2 plan approval | 2026-09-10 |
| AR-02-02 | T-02-03-03 | DEBUG-only rejection details are required for per-candidate routing diagnosis and contain emulator metadata rather than credentials or user data. | Phase 2 plan approval | 2026-09-10 |
| AR-02-03 | T-02-03-SC | Plan 02-03 changed no dependency or lock file. | Phase 2 plan approval | 2026-09-10 |
| AR-02-04 | T-02-04-SC | Plan 02-04 changed no dependency or lock file. | Phase 2 plan approval | 2026-09-10 |

*Accepted risks do not resurface in future audit runs.*

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-11 | 20 | 20 | 0 | GSD Level 1 security audit |

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-11
