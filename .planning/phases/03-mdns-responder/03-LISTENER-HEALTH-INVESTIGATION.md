# Zeroconf listener-failure detection investigation

## Authority and verdict

On 2026-09-23 the user authorised investigation of supported listener-failure
detection after the bounded recovery prototype. This follow-up does not change
the selected public contract or authorise production integration.

**No supported direct listener-failure notification was found in zeroconf
0.151.3. Its startup checks demonstrably do not detect closed transports.**
PyPI metadata checked during this investigation also reports 0.151.3 as the
latest release. MDNS-10 remains provisional; D-08 is not satisfied by the
existing prototype's explicit `runtime_failure` entry point.

## Source and public API review

The installed pinned distribution was inspected, with source hashes retained in
`03-recovery-evidence/listener-health-local-macos.json`.

- `_listener.py:94`: `connection_lost` has only a docstring. It does not notify
  an owner, update lifecycle state or forward the event to the loop handler.
- `_listener.py:120`: `error_received` logs through `QuietLogger`; it does not
  supply a structured public failure notification. A UDP error also need not
  mean that the receiving transport is permanently unusable.
- `_core.py:489`: `async_wait_for_start` checks the shutdown flag and startup
  future. `_core.py:641` derives `started` from the same startup state.
- `_engine.py:120`: interface refresh reconciles desired interface keys against
  existing wrappers; it is not a listener-health check. The same-interface
  closed-transport case below returned normally without reopening a reader.

The [public API reference](https://python-zeroconf.readthedocs.io/en/latest/api.html)
documents service/record listeners and startup waiting, but no transport-loss
callback. These service listeners report DNS records and discovery changes,
not socket health. Reference source:
[`_listener.py`](https://github.com/python-zeroconf/python-zeroconf/blob/0.151.3/src/zeroconf/_listener.py),
[`_core.py`](https://github.com/python-zeroconf/python-zeroconf/blob/0.151.3/src/zeroconf/_core.py),
[`_engine.py`](https://github.com/python-zeroconf/python-zeroconf/blob/0.151.3/src/zeroconf/_engine.py).
Local retained hashes identify the actual inspected distribution independently
of these version-labelled links.

## Measured diagnostic

`scripts/spike_mdns_listener_health.py` starts the existing recovery adapter
with a real `AsyncZeroconf` on explicit IPv4 loopback, awaits startup, then
closes all of that disposable instance's real asyncio transports. Private
engine access is restricted to fault injection and observation; it is not a
proposed production dependency or detector. No library code is patched.

Local macOS, Python 3.14.7, zeroconf 0.151.3:

| Observation | Result |
| --- | --- |
| Live transports before injection | 2 |
| Both transports closing and socket descriptors closed | True |
| `started` after closure | True |
| `done` after closure | False |
| `async_wait_for_start(timeout=0.1)` | Returned normally |
| Recovery adapter status/error | `running` / null |
| Event-loop exception notifications during closure | None |
| Same-interface `async_update_interfaces` | Returned normally |
| Open readers after interface refresh | 0 |
| Final cleanup | 0 pending tasks, only MainThread |

This is a transport-close diagnostic, not a physical interface outage,
cross-platform recovery proof, multicast responsiveness measurement or a
fleet-control test. It uses an empty fleet to isolate socket lifecycle signals.
The earlier live WiFi/control evidence remains scoped to the recovery prototype.

Reproduce without changing production dependencies:

```sh
UV_CACHE_DIR=/tmp/lifx-review-uv uv run --frozen --with zeroconf==0.151.3 \
  python scripts/spike_mdns_listener_health.py --output /tmp/listener-health.json
```

## Alternatives and recommendation

| Route | Assessment |
| --- | --- |
| Poll `started` or `async_wait_for_start` | Rejected by the measured closed-transport result. |
| Refresh interfaces periodically | Does not detect or repair this same-interface failure; not a substitute for health reporting. |
| Event-loop exception handler or log interception | No notification in this closure case; logs are neither a complete nor stable ownership-aware failure API. |
| Read/patch private listener or engine state | Could observe some closures, but violates the accepted supported-API design and still does not prove network responsiveness. |
| Upstream public transport-failure callback | Best fit for the existing D-08 contract; requires upstream API work and tests, including intentional close versus unexpected loss and partial transport failure. No upstream request has been sent. |
| Independent wire-level health probe | A possible contract change: detect sustained absence of matching fresh responses, not the cause of listener failure. Needs explicit agreement before implementation. |

Recommend an upstream public failure callback if D-08 must retain direct
listener-failure semantics. If the preferred outcome is to proceed without an
upstream dependency, first agree a bounded responsiveness contract. Such a
probe needs fresh query correlation, exact owned identity/record checks,
explicit interface selection, a consecutive-miss threshold, lifecycle
generation ownership and a cancellation-safe shutdown path. Same-instance
cache lookups cannot establish fresh network responsiveness. Packet loss,
local routing, other responders/caches and empty or changing fleets must be
handled explicitly before treating silence as fatal to Thread/mixed fleets.

Neither alternative is implemented by this investigation. Do not turn this
negative result into a go decision or silently weaken D-08.
