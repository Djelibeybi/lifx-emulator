# API Coverage — python-zeroconf production integration

> Full public-operation coverage for the selected Phase 3 production integration. The 03-02 closeout remains the historical selection evidence; this matrix defines what 03-03 through 03-07 implement or explicitly exclude.

| capability | decision | reason |
|---|---|---|
| `AsyncZeroconf` construction/startup | INTEGRATE | Own one responder lifecycle on the explicit interface and expose startup outcomes. |
| `async_register_service` | INTEGRATE | Register complete immutable `ServiceInfo` snapshots and await both the outer coroutine and its returned announcement awaitable. |
| `async_update_service` | INTEGRATE | Restore a previously owned same-serial service and await both the outer coroutine and its returned announcement awaitable. |
| `async_unregister_service` | INTEGRATE | Remove owned membership and await both the outer coroutine and its returned goodbye awaitable before the completion boundary succeeds. |
| `async_wait_for_start` / `started` | INTEGRATE | Distinguish lifecycle readiness from unpromised listener-health detection under D-08. |
| `async_close` | INTEGRATE | Await the single close coroutine for the owned zeroconf instance at stop/retry. |
| `ServiceInfo` public record construction | INTEGRATE | Construct complete PTR/SRV/TXT/A-or-AAAA snapshots for registration and update. |
| `async_update_interfaces` | OPT-OUT | The interface is immutable for a server lifecycle; explicit retry creates a fresh owner, and this operation must not be represented as a listener-health check. |
| Service browser/listener consumer APIs, including `AsyncServiceBrowser` | OPT-OUT | Pristine `lifx-async` is the discovery oracle; the emulator does not add a second consumer implementation. |
| Resolver APIs, including `AsyncServiceInfo` lookup and `async_get_service_info` | OPT-OUT | Phase 3 owns a responder and validates it through raw DNS and the existing consumer. |
| Private listener, engine and socket internals | OPT-OUT | D-08 and D-10 reject private access, monkey-patching, forks and a listener-health watchdog for the supported contract. |
| IPv6 mDNS multicast APIs | OPT-OUT | The locked phase scope uses IPv4 mDNS multicast while Thread endpoints are advertised as IPv6 records. |
| Automatic interface/address selection | OPT-OUT | The server requires an explicit advertised address or a validated concrete bind fallback. |
| Service-type enumeration and administrative browsing APIs | OPT-OUT | These consumer/admin operations do not participate in `_lifx._udp.local.` registration or discovery validation. |

## Plan mapping

| capability group | plans |
|---|---|
| owner startup, register and close | 03-03, 03-06 |
| update, unregister and retry lifecycle | 03-06 |
| ServiceInfo record construction | 03-03, 03-04 |
| production client and network validation | 03-07 |

## Dependency version gate

The approved and currently latest PyPI release is `zeroconf==0.151.3`. Plan 03-03 rechecks the live latest release immediately before `uv add --package lifx-emulator-core "zeroconf==0.151.3"`; any drift fails the task and returns to the Phase 3 selection gate instead of silently changing the approved dependency.

## Decision coverage

| decisions | disposition | coverage |
|---|---|---|
| D-01–D-04 | production implementation | 03-03 and 03-04 implement the selected public zeroconf responder, immutable configuration and address/record policy; 03-07 validates the observable network behaviour. |
| D-05–D-08 | production implementation | 03-06 implements fleet-sensitive admission, observable failure/retry, bounded ownership and the accepted no-listener-health-promise boundary; 03-07 validates those contracts. |
| D-09–D-15 | historical completion | 03-02 and `03-ZEROCONF-CLOSEOUT.json` already supplied the time-boxed selection, daemon coexistence, packaging, client-oracle and public-operation evidence. The implementation plans consume that go decision without repeating the spike. |
| D-16–D-18 | optional environment, out of scope | The optional VM/cross-machine continuations were not authorised and are not required by the approved go. Plans use real local Ubuntu/macOS networking and Windows simulations only. |

All production zeroconf calls stay within the documented public surface above. An `OPT-OUT` row cannot be used to claim a Phase 3 capability or health guarantee.
