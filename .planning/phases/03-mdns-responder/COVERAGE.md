# API Coverage — python-zeroconf closeout

> Full public-operation coverage for the Phase 3 selection spike. This matrix describes candidate evaluation, not production integration.

| capability | decision | reason |
|---|---|---|
| `AsyncZeroconf` construction/startup | INTEGRATE | Required to prove explicit-interface startup, daemon coexistence and startup failure reporting. |
| `async_register_service` and returned announcement awaitable | INTEGRATE | Required for initial fleet ownership, partial-start cleanup and surfaced registration/announcement failures. |
| `async_update_service` | INTEGRATE | Required for the retained public removal/restoration route and surfaced update failures. |
| `async_unregister_service` | INTEGRATE | Required for removal ownership and surfaced unregistration failures. |
| `async_update_interfaces` | INTEGRATE | Required to measure the public explicit-interface operation and its surfaced failures; it is not treated as a health check. |
| `async_wait_for_start` / `started` | INTEGRATE | Required to preserve the measured distinction between lifecycle startup and network health under D-08. |
| `async_close` | INTEGRATE | Required for owned cleanup, retry gating and surfaced close failures. |
| `ServiceInfo` public record construction | INTEGRATE | Required for executable A/AAAA, TXT, service identity, address override/fallback and configuration-fit evidence. |
| Service browser/listener consumer APIs | OPT-OUT | The pristine `lifx-async` client remains the discovery oracle; Phase 3 does not add a second consumer implementation. |
| Private listener/engine/socket internals | OPT-OUT | D-08 and D-10 reject private access, monkey-patching, forks and a listener-health watchdog for the supported contract. |
| IPv6 mDNS multicast APIs | OPT-OUT | The locked phase scope uses IPv4 mDNS multicast; advertised Thread endpoints remain IPv6 records. |
| Automatic interface/address selection | OPT-OUT | The user requires explicit interface/address selection and rejects automatic selection. |

The closeout runner must fail validation if an `INTEGRATE` row lacks a demonstrated, failed or explicitly untested case with an acquisition step. An `OPT-OUT` row cannot be used as evidence for go beyond the stated boundary.
