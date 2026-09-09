# Stack Research

**Domain:** Thread-device emulation — asyncio mDNS/DNS-SD responder + portable IPv6 UDP transport, added to an existing Python asyncio LIFX LAN protocol emulator
**Researched:** 2026-09-09
**Confidence:** HIGH for the core recommendation (zeroconf) and its threading model; MEDIUM for macOS x86_64 PyApp packaging behaviour and Python 3.14 real-world maturity

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `zeroconf` | 0.151.3 (verified via PyPI JSON, released 2026-08-30) | asyncio mDNS/DNS-SD responder (`AsyncZeroconf` + `AsyncServiceInfo`) for `_lifx._udp.local` | Its `AsyncEngine` wires each socket into the *caller's* running event loop with `loop.create_datagram_endpoint(lambda: AsyncListener(self.zc), sock=sock)` (verified by reading `_engine.py` source) — the identical asyncio `DatagramProtocol` pattern `EmulatedLifxServer` already uses. Because the emulator already runs one asyncio loop (uvicorn + the UDP server share it), `AsyncZeroconf()` detects that running loop via `get_running_loop()` and attaches directly to it instead of spinning up its own background thread (that thread path — `Zeroconf._start_thread()` — is only taken when *no* loop is already running, e.g. bare synchronous scripts). This satisfies the project's "no threads in the packet path" constraint. It also already solves the two hardest parts of this problem correctly: coexisting with an OS mDNS responder already bound to :5353 (`SO_REUSEADDR` + `SO_REUSEPORT`-if-available on every socket, verified in `_utils/net.py`), and constructing standards-correct PTR/SRV/TXT/A/AAAA wire bytes with the mDNS cache-flush bit, which is exactly what `lifx-async`'s hand-rolled parser expects. |
| stdlib `socket` (`AF_INET6`, `IPV6_V6ONLY`) + `struct` | n/a (CPython 3.10–3.14 stdlib) | The new **IPv6 LAN-protocol transport socket** (not mDNS — this is the second UDP socket that carries LIFX packets to Thread devices) | This is a separate concern from mDNS: it must be a plain `AF_INET6`/`SOCK_DGRAM` socket with `IPV6_V6ONLY=1` set *before* bind, wrapped the same way the existing IPv4 socket is (`loop.create_datagram_endpoint(sock=preconfigured_sock)`), reusing the existing `LifxProtocol`. No third-party library adds value here — this is exactly the same pattern already in `server.py`, just on a second address family. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ifaddr` | `>=0.1.7` (pulled in transitively by `zeroconf`; do not pin it directly) | Network interface enumeration used internally by `zeroconf` to discover local addresses when `InterfaceChoice.All`/`Default` is used | Always present once `zeroconf` is added — it is `zeroconf`'s *only* runtime dependency (confirmed via PyPI JSON `requires_dist`), pure Python, no compiled extension. Do not scope interface discovery yourself; if the config asks for an explicit advertise address, pass an explicit interface list to `AsyncZeroconf(interfaces=[...])` rather than fighting `ifaddr`'s auto-detection. |

### Development Tools

No new dev tooling is required. Continue using the existing `pytest` + `pytest-asyncio` 1.3.x (`asyncio_mode = "auto"`) stack already configured in both packages' `pyproject.toml`.

## Installation

```bash
# Core library only — the responder and the IPv6 socket both live in
# lifx_emulator (packages/lifx-emulator-core), next to EmulatedLifxServer,
# not in the standalone app package. The app package has zero new dependencies.
uv add zeroconf --package lifx-emulator-core

# No dev dependency additions needed — testing uses stdlib + existing pytest-asyncio
```

**Package placement rationale:** `EmulatedLifxServer`, `DeviceManager`, and `DeviceState` (where `connectivity` will live) are all in `lifx-emulator-core`. The mDNS responder needs live read access to every registered device's serial, product id, firmware and connectivity to build TXT/SRV/A/AAAA records, and it must start/stop in lock-step with `EmulatedLifxServer.start()`/`.stop()`. Putting `zeroconf` in the app package (`lifx-emulator`) would force an awkward callback or event bus between the two packages for no benefit — the app package already just imports and starts `EmulatedLifxServer` from core (see `CLAUDE.md` import guidelines). Keep the new dependency where the new capability lives: core.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `zeroconf` (`AsyncZeroconf`/`AsyncServiceInfo`) | Hand-rolled `asyncio.DatagramProtocol` responder, stdlib `struct` message packing, manual `IP_ADD_MEMBERSHIP`/`SO_REUSEPORT` handling | Only if the project needed byte-for-byte control over *malformed* or edge-case mDNS replies for scenario-engine fault injection (e.g. truncated TXT, wrong cache-flush bit, legacy-unicast replies) that `zeroconf`'s high-level `ServiceInfo` API cannot produce. `lifx-async`'s own test fixtures already exercise several such malformed cases against a hand-rolled *client* parser — if a later phase needs the emulator to *emit* similarly malformed mDNS records for scenario testing, a thin hand-rolled encoder (mirroring `lifx-async`'s `dns.py` builder functions, which are stdlib-only and already known-correct against the same client) is the right escape hatch for those specific malformed-packet scenarios, layered *behind* `zeroconf` for the well-formed default path rather than replacing it. Do not hand-roll the *whole* responder up front — RFC 6762 probing/announcing/cache-flush/coexistence-with-mDNSResponder is exactly the class of bug-prone protocol code this project already avoids reinventing (see how `packets.py`/`products/registry.py` are generated rather than hand-maintained). |
| `zeroconf` | `python-zeroconf`'s dead fork `aiozeroconf` | Never. Last released 0.1.8 on 2018-11-14 (verified via PyPI JSON), predates `zeroconf`'s own native `AsyncZeroconf`/`AsyncServiceInfo` (added directly upstream), unmaintained for 7+ years, no Python 3.10+ support claim. It existed only because `zeroconf` was sync-only at the time; that gap has been closed upstream for years. |
| `zeroconf` | `dnslib` (0.9.26, released 2025-03-03) or `dnspython` (2.8.0, `requires-python>=3.10`) for message packing only | Neither is a responder — both are wire-format toolkits (encode/decode DNS messages, in `dnspython`'s case mainly as a *resolver* client and zone-file toolkit). Using either would still require hand-building the multicast socket lifecycle, probing/announcing, cache-flush semantics and OS-coexistence handling that `zeroconf` already provides. They are worth keeping in mind only as reference implementations for wire-format edge cases (`dnslib`'s bit-level encoder is a reasonable model if a later phase needs the hand-rolled malformed-packet escape hatch above) — not as the responder's foundation. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `aiozeroconf` | Dead since 2018 (see above); no Python 3.10–3.14 support; functionality fully absorbed into `zeroconf` itself | `zeroconf`'s `AsyncZeroconf`/`AsyncServiceInfo` |
| A synchronous `Zeroconf()` (non-async) instance inside the emulator's event loop | Constructing plain `Zeroconf()` without a running loop makes it spin up its own background thread + its own private event loop (`Zeroconf._start_thread()`), which is exactly the "threads in the packet path" pattern the project constraint rules out, and would desynchronise the responder's device snapshot from the same-loop `DeviceManager` state | `AsyncZeroconf()` constructed *after* the emulator's own event loop is already running (e.g. inside `EmulatedLifxServer.start()` or a sibling `start()` coroutine), so it attaches to that loop directly |
| `loop.create_datagram_endpoint(local_addr=("::1", port))` for the new IPv6 LIFX transport socket | `local_addr` gives asyncio no chance to set `IPV6_V6ONLY` before bind; on macOS, `IPV6_V6ONLY` must be set *before* `bind()` or the call raises `EINVAL` — asyncio's `local_addr` path binds internally and only exposes the socket afterwards, so the flag cannot be applied in time. Windows already defaults `V6ONLY=1` and Linux/macOS default it *off*, so relying on OS defaults silently makes the socket dual-stack on two of your three CI platforms — the opposite of the "separate `AF_INET6` V6ONLY socket" decision already locked in `PROJECT.md` | Build the `socket.socket(AF_INET6, SOCK_DGRAM)` yourself, call `setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)` before `bind()`, then hand it to `create_datagram_endpoint(protocol_factory, sock=configured_sock)`. This is portable across Linux, macOS and Windows (SelectorEventLoop and ProactorEventLoop both accept a pre-bound UDP socket via `sock=`) |
| Binding the mDNS responder to `::`/dual-stack for both IPv4 and IPv6 mDNS in one socket | Out of scope per `PROJECT.md` (the responder only needs to answer the IPv4 multicast group `224.0.0.251:5353`; `ff02::fb` is explicitly deferred) — and `zeroconf`'s own dual-stack handling (`IPVersion.All`) adds `disable_ipv6_only_or_raise()` complexity this milestone does not need | Construct `AsyncZeroconf(ip_version=IPVersion.V4Only)` (or the default, which already only opens the v4 multicast socket unless told otherwise) — matches the milestone's explicit v4-multicast-only scope |
| Vendoring/pinning `ifaddr` directly in `pyproject.toml` | It is a transitive dependency of `zeroconf`; pinning it independently only risks a version mismatch with what `zeroconf` was tested against | Let `uv` resolve it transitively; only touch it if a `uv.lock` conflict ever surfaces |

## Stack Patterns by Variant

**If the device is a Thread device (IPv6-unicast-only, per `PROJECT.md`):**
- Build its `AsyncServiceInfo` with `addresses=[socket.inet_pton(socket.AF_INET6, advertise_addr)]` and nothing else.
- Verified in `zeroconf`'s `ServiceInfo.__init__`: address bytes are classified purely by length (16 bytes → `_ipv6_addresses`, 4 bytes → `_ipv4_addresses`); there is *no* code path that force-derives or requires a companion A record. Passing only a 16-byte entry produces an AAAA-only DNS-SD answer, exactly what `PROJECT.md` requires ("Thread devices are advertised with an AAAA record only").
- Because Thread devices are advertised by design, do not honour the WiFi mDNS opt-out flag for them.

**If the device is a WiFi device:**
- Build its `AsyncServiceInfo` with `addresses=[socket.inet_pton(socket.AF_INET, advertise_addr)]` only, unless mDNS advertisement has been disabled for it (the milestone's opt-out applies to WiFi only).

**If TXT content needs to match `lifx-async`'s parser exactly:**
- Pass `properties={"id": serial, "p": str(product_id), "fw": f"{major}.{minor}", "tm": "2" if thread else "1"}` (plain `str`/`dict`, not pre-packed bytes). `zeroconf`'s `_set_properties()` (verified source) encodes each `key=value` pair as `bytes((len(item),)) + item`, one length-prefixed string per key — this is byte-identical to the length-prefixed-string TXT format `lifx-async`'s `parse_txt_record()` already parses (`dns.py:219`), including its `key, _, value = txt_str.partition("=")` split. No custom TXT encoder is needed.
- `_validate_txt_id` in `lifx-async` requires exactly 12 lowercase hex chars with the unicast bit clear (`raw[0] & 0x01 == 0`) — pass the serial as the plain 12-hex-char string already used for `Serial`, lower-cased; do not add separators.

**If many devices need to be advertised at once (the common case — the emulator typically runs several devices in one process):**
- Register one `AsyncServiceInfo` per device (unique instance name, e.g. `f"{serial}.{LIFX_MDNS_SERVICE}"`) against a single shared `AsyncZeroconf()` instance via repeated `await aiozc.async_register_service(info)` calls. This is `zeroconf`'s primary supported use case (a single responder fielding many service instances of the same `_type._proto` from one process) — no per-device `AsyncZeroconf` instances are needed, and creating one per device would each try to bind its own copy of the same multicast socket for no benefit.

**If a later phase needs to inject malformed mDNS records for the scenario engine (out of scope for this milestone but flagged for roadmap awareness):**
- Do not extend `zeroconf` itself. Write a small stdlib-only encoder (mirroring `lifx-async`'s existing `dns.py` builder pattern) that runs *before* `zeroconf`'s socket layer only for the specific malformed cases a scenario requests, and let `zeroconf` handle every well-formed reply. Keep this decision for the scenario-engine phase, not this one.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `zeroconf==0.151.3` | CPython 3.10–3.15 (per published wheel matrix, verified via PyPI file list) | Covers the project's full 3.10–3.14 CI matrix with room to spare; 3.14 wheels exist (`cp314`/`cp314t`) but 3.14 is a very recent release — treat as MEDIUM confidence until it has run through this project's own CI a few times. |
| `zeroconf==0.151.3` | `pydantic>=2.0.0`, `fastapi>=0.115.0`, `uvicorn>=0.34.0`, `cyclopts>=4.2.0` | No overlapping transitive dependencies; `zeroconf`'s only runtime dependency (`ifaddr`) does not intersect with anything already in either package's dependency tree — no resolver conflicts expected. |
| `zeroconf==0.151.3` (PyApp standalone binaries) | macOS wheels are **`arm64`-only** (`macosx_11_0_arm64`); there is no macOS `x86_64` wheel for any supported CPython version (verified via the full PyPI file listing) | The project's release workflow builds PyApp binaries for macOS `x86_64` **and** `arm64` (`CLAUDE.md`/`STACK.md` codebase docs). On the `x86_64` leg, `uv`/`pip` will fall back to the sdist and compile `zeroconf`'s optional Cython extension from source, which needs a C toolchain and Cython available in that build environment — confirm this on macOS-x86_64 CI/build hosts, or force zeroconf's pure-Python fallback path (it explicitly supports running without the compiled extension) if a toolchain is unavailable there. **Flag this for phase-level validation before relying on it in the release pipeline.** |
| `zeroconf` async engine (`loop.create_datagram_endpoint(sock=...)`) | Linux `SelectorEventLoop`/`asyncio`, macOS `SelectorEventLoop`/`asyncio`, Windows `ProactorEventLoop` (asyncio default since 3.8) and `SelectorEventLoop` | All three platforms accept a pre-bound `sock=` UDP socket into `create_datagram_endpoint`; this is the same mechanism the project's own IPv6 transport socket should use (see "What NOT to Use" above for why `local_addr=` is the wrong choice on all three, not just one). Windows historically had rougher UDP support under `ProactorEventLoop` in older CPython releases; current CPython (3.10+, the project's floor) supports UDP under both Windows event loop policies, but multicast-specific behaviour is comparatively less exercised in the wild than on POSIX — treat Windows as the platform most worth explicit CI coverage for the mDNS responder specifically. |

## Sources

- PyPI JSON API (`pypi.org/pypi/zeroconf/json`, `.../0.151.3/json`, `.../dnspython/json`, `.../dnslib/json`, `.../aiozeroconf/json`) — HIGH confidence, authoritative version/dependency/release-date/wheel-matrix data, fetched live 2026-09-09
- `python-zeroconf` GitHub source, read directly (`_core.py`, `_engine.py`, `_utils/net.py`, `_services/info.py`, `asyncio.py`) — HIGH confidence, verified the exact threading model, socket-option sequencing, and `ServiceInfo`/TXT encoding behaviour by reading the implementation rather than relying on docs summaries
- `python-zeroconf` GitHub repo README (`github.com/python-zeroconf/python-zeroconf`) — MEDIUM confidence, general project positioning (Bonjour/Avahi coexistence claims, supported Python versions)
- `/Volumes/External/Developer/Djelibeybi/lifx-async/src/lifx/network/discovery/mdns/dns.py` and `discovery.py` (required reading) — HIGH confidence, the exact TXT/wire-format contract the responder must satisfy, read directly from the client repo
- `/Volumes/External/Developer/Djelibeybi/lifx-emulator/.planning/PROJECT.md`, `.planning/codebase/STACK.md`, both packages' `pyproject.toml` (required reading) — HIGH confidence, existing project constraints and dependency footprint
- `packages/lifx-emulator-core/tests/test_server.py` (read directly) — HIGH confidence, confirms the existing repo convention of testing `DatagramProtocol.datagram_received()` by direct method call rather than real sockets; the same pattern should be used for the mDNS responder's unit tests (construct the `AsyncListener`/responder protocol, call `.datagram_received(raw_query_bytes, ("127.0.0.1", 5353))` directly, assert on a fake transport's `sendto` calls — no multicast group join or real network I/O needed in tests)
- Python `docs.python.org/3/library/asyncio-platforms.html` — LOW confidence for UDP/multicast specifics (page does not document UDP/IPv6/multicast differences between event loop implementations in detail; Windows-specific UDP maturity claims above are general knowledge, not verified against a primary source, and should be spot-checked with a real Windows CI run before being treated as settled)

---
*Stack research for: Thread-device mDNS/DNS-SD emulation, IPv6 UDP transport*
*Researched: 2026-09-09*
