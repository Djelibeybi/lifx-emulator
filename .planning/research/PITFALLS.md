# Pitfalls Research

**Domain:** mDNS/DNS-SD responder + IPv6 UDP transport + Thread-device emulation, added to an existing cross-platform Python asyncio LIFX emulator
**Researched:** 2026-09-09
**Confidence:** HIGH for asyncio/repo-specific pitfalls (verified directly against this codebase and the sibling `lifx-async` probe/transport); MEDIUM-HIGH for platform mDNS/OS-daemon behaviour (corroborated across multiple independent sources but not re-tested against every OS version in this session); MEDIUM for Windows-specific claims (no Windows CI in this repo's matrix, so these are documented behaviour, not locally verified)

## Critical Pitfalls

### Pitfall 1: Binding UDP 5353 to receive multicast queries silently loses replies to the OS's own mDNS daemon ("unicast-stealing")

**What goes wrong:**
A responder that wants to see multicast PTR queries for `_lifx._udp.local` must bind port 5353 and join `224.0.0.251`. On any developer or CI machine that already runs a system mDNS resolver — `mDNSResponder` on macOS, `Bonjour`/`dnscache`-adjacent services or the native Windows mDNS responder on Windows, `avahi-daemon` on most Linux desktops — that daemon already owns 5353. Two sockets can both bind 5353 with `SO_REUSEADDR`/`SO_REUSEPORT`, but the kernel's delivery of a given multicast datagram to "the other" socket in the group is platform- and load-dependent, not guaranteed to fan out to every listener. In practice, unicast replies and even queries can go to whichever daemon owns the port first, and the emulator's socket sees nothing, with no error raised anywhere.

This project's sibling repo, `lifx-async`, hit this from the client side and named it directly: its `MdnsTransport` docstring documents "the mDNSResponder unicast-stealing bug" — binding to 5353 "silently takes the unicast responses and causes devices to be missed" (`src/lifx/network/discovery/mdns/transport.py:10-13`). Its `.planning/scripts/ipv6_thread_probe.py` stage 2 (`stage_ports`) exists specifically to measure this: it runs discovery twice, once from an ephemeral port (current, fixed behaviour) and once from a `_LegacyMdnsTransport` bound to 5353 with `SO_REUSEPORT` (the reproduced pre-fix behaviour), and reports the set difference in devices found as direct evidence of the bug.

**Why it happens:**
RFC 6762 §6.7 defines "legacy unicast" queries: a query sent from a port other than 5353 gets a plain unicast reply straight back to the querier's address:port instead of a multicast reply to 224.0.0.251:5353. `lifx-async`'s client exploits this deliberately — it always sends from an ephemeral port so replies bypass 5353 (and therefore bypass the system daemon) entirely (`transport.py:1-21`). This project's emulator is on the *responder* side of that same exchange: it must still bind 5353 to see the incoming multicast query in the first place (a legacy-unicast query is still sent *to* 224.0.0.251:5353, only the reply path changes), so the emulator cannot avoid the contested port the way the client did.

**How to avoid:**
- Bind 5353 with `SO_REUSEADDR` (all platforms) and `SO_REUSEPORT` where available (Linux, macOS; not on Windows — see Pitfall 2) so the emulator can coexist with a running system daemon rather than failing to bind at all.
- Detect the *query's source port*, not just its destination: if it did not arrive from 5353 (i.e. it is a legacy-unicast query per RFC 6762 §6.7), reply with a **unicast** UDP packet addressed to the querier's source IP:port. This is a plain `sendto()`, not multicast, so it never touches the contested port on the sending side and cannot be "stolen" — this exactly mirrors why `lifx-async`'s query-side fix works.
- For genuine multicast queries (source port 5353), reply multicast to 224.0.0.251:5353 per RFC 6762 §6.1, but do not assume the local machine's own system daemon will forward it faithfully in test environments — treat local multicast reception as best-effort, not authoritative, in the emulator's own test suite (see Pitfall 2 for how `lifx-async`'s test fixtures work around exactly this).
- Never make the emulator's default port-5353 bind fail the whole server startup: if 5353 cannot be bound (`OSError: Address already in use` with `SO_REUSEADDR`/`SO_REUSEPORT` already applied and still rejected — happens on some locked-down macOS or Windows configurations), log a warning and disable mDNS rather than crash the emulator, since IPv4/WiFi device emulation must keep working with defaults unchanged (a hard PROJECT.md constraint).

**Warning signs:**
- A test or manual run that queries the emulator from an ephemeral port (matching `lifx-async`'s own transport) never receives a PTR/SRV/TXT/address reply, while the same query bound to 5353 with `SO_REUSEPORT` *does* get an answer that arrived by multicast instead of unicast — that split is precisely what `stage_ports` measures and reports as `VERDICT: binding 5353 loses devices`.
- CI is green locally on a machine with no `avahi`/`mDNSResponder` running, but flaky or red on a developer's laptop or a self-hosted runner where one is running.

**Phase to address:**
mDNS responder core phase — this must be designed in from the first line of the responder's receive-and-reply path, not patched on afterward. Verification phase should run `lifx-async`'s ported/adapted `ipv6_thread_probe.py` `stage_ports`-style ephemeral-vs-5353 comparison against the emulator as an acceptance check.

---

### Pitfall 2: Platform socket-option divergence for the 5353 bind (SO_REUSEPORT absence on Windows, SO_EXCLUSIVEADDRUSE semantics, Linux/macOS multicast-with-REUSEPORT subtleties)

**What goes wrong:**
Code written and tested only on macOS/Linux (this project's actual CI matrix) that unconditionally calls `socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)` will raise `AttributeError` on Windows, where `SO_REUSEPORT` does not exist as a Python socket constant at all. Conversely, code that only sets `SO_REUSEADDR` on Windows gets *different* semantics than on POSIX: on Windows, `SO_REUSEADDR` allows a socket to bind a port another socket has already bound **even without both being multicast**, which is a security-relevant behaviour difference from POSIX (Microsoft's own guidance recommends `SO_EXCLUSIVEADDRUSE` for anything that isn't deliberately sharing a multicast port). The existing `lifx-async` legacy transport reproduction (`_LegacyMdnsTransport`) already handles the `AttributeError`/`OSError` split correctly (`try: sock.setsockopt(..., SO_REUSEPORT, 1) except (AttributeError, OSError): pass`), which is the pattern to copy — most first attempts at this in the wild do not guard both exception types and fail hard on Windows or on Linux kernels/containers where `SO_REUSEPORT` is present but rejected (e.g. some seccomp-restricted containers).

**Why it happens:**
`SO_REUSEPORT` is a BSD/Linux-only socket option; it was never exposed on Windows because Windows' `SO_REUSEADDR` already provides overlapping (looser) behaviour for the multicast case. A developer testing only on their own machine (typically macOS, per this repo's CLAUDE.md dev conventions) will not discover the Windows gap until the PyApp Windows binary or a Windows user actually runs the mDNS responder.

**How to avoid:**
- Always guard `SO_REUSEPORT` with `try/except (AttributeError, OSError): pass`, exactly as `_LegacyMdnsTransport` does.
- Always set `SO_REUSEADDR` unconditionally (it exists on all three platforms and is required on POSIX for multicast port sharing, and is the closer Windows equivalent).
- Do not use `SO_EXCLUSIVEADDRUSE` on the mDNS responder's socket on Windows — that would prevent the coexistence with Bonjour/Windows' own mDNS responder that `SO_REUSEADDR` is meant to enable here; reserve `SO_EXCLUSIVEADDRUSE` (if ever needed) for the emulator's *unicast* LIFX-protocol socket, which does not need port sharing.
- Treat "cannot bind 5353 on this platform" as a soft failure (see Pitfall 1) rather than an assumption that at least one of the three socket-option combinations will always succeed.

**Warning signs:**
- CI is green (Ubuntu + macOS only, per this repo's actual CI matrix) while the Windows PyApp binary silently has no mDNS responder, discovered only when a Windows user files an issue.
- Any code review that finds an unguarded `socket.SO_REUSEPORT` reference outside the existing test-only `_LegacyMdnsTransport`-style reproduction.

**Phase to address:**
mDNS responder core phase for the socket-option guard itself; verification phase should include a Windows-targeted unit test that monkeypatches `socket.SO_REUSEPORT` to be absent (simulating Windows) and asserts the responder still starts, since there is no Windows CI runner to catch this directly.

---

### Pitfall 3: `IPV6_V6ONLY` set after bind raises `EINVAL` on macOS — and the platform defaults for V6ONLY differ, which is why this project chose two sockets over one dual-stack socket

**What goes wrong:**
`socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)` must be called **before** `bind()`. Calling it after — which is easy to do accidentally if socket construction and bind are separated across two functions, or if `asyncio.loop.create_datagram_endpoint(local_addr=...)` is used (which binds internally, giving the caller no window to set the option first) — raises `OSError: [Errno 22] Invalid argument` on macOS. This project's own `lifx-async` test fixture already discovered and documents this exact failure mode: `tests/conftest.py:302-317`'s `_Ipv6EmulatedLifxServer.start()` docstring states it is "verified on this project's development machine" and exists *specifically* because the stock `EmulatedLifxServer.start()` in this emulator hands `local_addr=` straight to `create_datagram_endpoint`, which "binds inside itself... so there is no moment between socket creation and bind for a caller to reach." That fixture is exactly the workaround this milestone is meant to make unnecessary by moving the same pattern into the emulator itself.

Separately, the three platforms disagree on what `IPV6_V6ONLY` defaults to on a freshly-created `AF_INET6` socket: Windows defaults it **on** (v6-only, no implicit dual-stack), while Linux and macOS default it **off** (dual-stack, an IPv6 socket bound to `::` also accepts IPv4-mapped traffic unless told not to). Code that never sets the option explicitly will therefore behave differently per platform by accident — which is precisely the ambiguity this milestone's decision to use a "separate `AF_INET6` `V6ONLY` socket, default `::1`" is designed to remove (PROJECT.md Key Decisions).

**Why it happens:**
`asyncio.loop.create_datagram_endpoint(local_addr=...)` is the idiomatic, and far more common, way to open a UDP endpoint in asyncio code — it is what the existing `EmulatedLifxServer.start()` already does for the IPv4 socket (`server.py:515-520`). That idiom is fine for IPv4 and for any IPv6 use that is happy with the platform default, but it removes the one narrow window (`socket()` → `setsockopt(IPV6_V6ONLY)` → `bind()`) needed for explicit, cross-platform-identical V6ONLY control. A developer who reaches for the same idiom used elsewhere in this file for the new IPv6 socket will reproduce the bug the `lifx-async` fixture had to work around.

**How to avoid:**
- Mirror `_Ipv6EmulatedLifxServer.start()` exactly: create a bare `socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)`, call `setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)`, *then* `bind((bind_address, port))`, `setblocking(False)`, and only then hand the pre-bound socket to `loop.create_datagram_endpoint(sock=sock)` (never `local_addr=` for this socket).
- Wrap the whole sequence in a `try/except` that closes the raw socket on any failure before re-raising — an unbound or partially-configured socket that is never closed leaks a file descriptor, which the reference fixture already gets right (`except Exception: sock.close(); raise`).
- Do not delete `lifx-async`'s `_Ipv6EmulatedLifxServer` conftest subclass until the emulator's own native IPv6 socket path has been verified with the same "set-before-bind" ordering — the PROJECT.md requirement that `lifx-async` can retire that subclass is itself the acceptance signal that this was done correctly.

**Warning signs:**
- `OSError: [Errno 22] Invalid argument` on macOS specifically (Linux is more permissive about setting `IPV6_V6ONLY` post-bind in some kernel versions, which can mask the bug in local Linux-only testing and let it ship broken for macOS users and the macOS CI leg).
- Any new code path for the IPv6 socket that calls `create_datagram_endpoint(local_addr=...)` instead of `create_datagram_endpoint(sock=...)`.

**Phase to address:**
Core transport phase (the IPv6 socket itself, before mDNS or Thread routing is layered on). Verification: a unit test that asserts `IPV6_V6ONLY` is `1` on the bound socket's `getsockopt`, run on both CI legs (Linux and macOS), since the failure is macOS-specific and would otherwise pass silently on the Linux CI leg alone.

---

### Pitfall 4: DNS message construction bugs specific to legacy-unicast replies — echoing the query ID, dropping the cache-flush bit, low TTL, and not assuming compression pointers are safe

**What goes wrong:**
A hand-rolled DNS/mDNS responder (the project's stated preference over a dependency such as `zeroconf`, per PROJECT.md constraints — "research decides") that is only tested against genuine multicast queries will get the **legacy-unicast reply path wrong in at least four independent ways**, each of which `lifx-async`'s client-side parser (`discovery.py`) is written defensively enough to simply drop rather than crash on — meaning a bug here manifests as "the client silently never finds the device" rather than a visible protocol error:

1. **Query ID not echoed.** Ordinary mDNS responses set the DNS header ID to 0 and multicast queriers ignore it (RFC 6762 §18.1). A **legacy**-unicast reply, however, is read by an ordinary unicast DNS-style resolver expectation and RFC 6762 §6.7 requires it to repeat the ID field from the query. Getting this wrong produces a reply the querier's transaction matching silently discards.
2. **Cache-flush bit set on a legacy-unicast answer.** RFC 6762 §10.2's cache-flush bit ("this is the complete, authoritative rrset, flush anything older") applies to the shared multicast cache model; RFC 6762 §6.7 explicitly says it **must not** be set on legacy-unicast responses, because the receiving software has no multicast cache to flush and may misinterpret the bit as a spurious high-order bit set on the record class.
3. **TTL too high on a legacy-unicast answer.** RFC 6762 §6.7 recommends TTLs no greater than ten seconds on legacy-unicast responses specifically, because a non-participating resolver has no mDNS cache-coherency mechanism and would otherwise hold a stale answer for the record's full (typically much longer, e.g. 120s/4500s) mDNS TTL.
4. **Assuming DNS name-compression pointers work identically in every reply.** Standard DNS/mDNS compression pointers are 14-bit backward offsets into *the current message*; a responder that builds the PTR/SRV/TXT/A/AAAA answer set incrementally and reuses a pointer computed against one message's layout inside a differently-laid-out message (e.g. because the legacy-unicast reply omits the question-section echo that a normal multicast reply doesn't need, per RFC 6762 §6) will emit a corrupt pointer that either points at the wrong bytes or exceeds the message being built. The safe rule is: compute compression pointers fresh per message, and only ever point backward within that exact message's byte stream.

On the answer/additional placement question specifically: DNS-SD convention (RFC 6763) places the PTR record in the Answer section and the SRV, TXT and A/AAAA records for the resolved instance in the Additional section (a resolver that recognises the pattern can skip the follow-up SRV/TXT/address queries entirely). `lifx-async`'s own cache is written defensively against a responder that gets this wrong or splits records across packets — `_LifxRecordCache.add_packet()`'s docstring explicitly anticipates "TXT in one packet, the AAAA for its SRV target in a later one" — but relying on the client's tolerance is not a substitute for placing the records where RFC 6763 §12 expects them; other, less defensive clients will simply issue redundant follow-up queries or fail to resolve at all.

**Why it happens:**
Most mDNS responder code (and most tutorials) is written and tested against the "everyone participates in mDNS properly and only ever does multicast" case, because that is what `dns-sd`/`avahi-browse` and typical smart-home clients do. The legacy-unicast path exists specifically for embedded/constrained clients like `lifx-async`'s discovery transport that deliberately avoid the port-5353 contention (Pitfall 1) — so it is the *less-travelled, less-tested* code path, and is exactly the path this milestone's actual, stated client depends on.

**How to avoid:**
- Implement the legacy-unicast branch as a genuinely separate code path (not a flag on the normal multicast-reply builder) with its own tests: echo query ID, clear cache-flush bit on every record, cap TTL at ≤10s, reply unicast to the querier's source address:port.
- Cap or otherwise bound the number of service instances answered for in one PTR sweep so the reply message stays well under a conservative MTU-safe size (~1200-1400 bytes is the practical ceiling most mDNS stacks assume even though RFC 6762 §17 raises the classic 512-byte DNS limit); when there are more instances than fit, split across multiple response packets rather than setting the truncation (TC) bit, since RFC 6762's TC-bit-driven multi-packet-query flow is for queriers, not the simpler multi-packet-response case a responder can just do unconditionally.
- Build every reply message fresh (own buffer, own compression-pointer table) per query — never share compressed-name state across messages sent for different queries or different transports (multicast vs legacy-unicast).
- Test against `lifx-async`'s own `tests/test_network/test_mdns/test_discovery.py:44` `_txt()` fixture shapes directly (per PROJECT.md Context) so the TXT string layout (`id=`, `p=`, `fw=`, `tm=`) and AAAA-only Thread instance shape match exactly what the acceptance oracle expects, not just what looks reasonable.

**Warning signs:**
- The client resolves the device correctly when queried standalone with a debugging tool (`dns-sd`, `avahi-browse`) but never resolves it through `lifx-async`'s actual discovery path, which is the legacy-unicast one — that split points straight at this pitfall.
- Any test that only exercises the multicast-reply path and never asserts on a captured legacy-unicast reply's header ID, cache-flush bit, or TTL.

**Phase to address:**
mDNS responder core phase for the wire-format work; verification phase should capture and assert on raw reply bytes for both the multicast and legacy-unicast paths, not just on whether the client eventually resolves the device (a passing high-level test can hide a wrong TTL or cache-flush bit that happens not to matter to this one client).

---

### Pitfall 5: Untracked fire-and-forget asyncio tasks will get worse, not better, once mDNS and IPv6 add more concurrent packet paths

**What goes wrong:**
This repo already has a documented, unfixed bug of exactly this shape: `LifxProtocol.datagram_received()` in `server.py:174-180` schedules packet handling via `loop.call_soon(loop.create_task, ...)` or a bare `asyncio.create_task(...)` **without retaining a reference**, and `event_bridge.py`'s `_schedule_async` does the same for every WebSocket broadcast. Per `.planning/codebase/CONCERNS.md`, this is a real, already-observed asyncio caveat: "under GC pressure asyncio may collect a pending task before it runs... dropping a packet response or a broadcast with no log." Adding a second `DatagramProtocol` instance for the new IPv6 socket, and a *third* for the mDNS responder's own socket, means the same unretained-task pattern — if simply copy-pasted from the existing IPv4 `LifxProtocol` — now exists in three places instead of one, tripling the exposure to this exact GC-eligibility race, right as this milestone adds more total datagram traffic (Thread ack RTTs, mDNS query/response, IPv6 unicast) for it to bite on.

**Why it happens:**
The existing `EmulatedLifxServer.LifxProtocol.datagram_received()` is the obvious, closest example to copy when writing a new `DatagramProtocol` subclass for the IPv6 or mDNS socket — and it already has the bug. Code review that only checks "does the new code follow the existing pattern" will pass, because it does; the existing pattern is itself wrong.

**How to avoid:**
- Do not copy `LifxProtocol.datagram_received()` verbatim for the new sockets. Instead, fix the pattern once (add a `set[asyncio.Task]` on `EmulatedLifxServer`, `add_done_callback` to discard on completion, mirroring the already-correct `_track_save_task` pattern in `devices/device.py` and `_track_task` in `scenarios/persistence.py` per CONCERNS.md) and have all three protocols (IPv4, IPv6, mDNS) route through the same tracked-task helper.
- Treat this as a prerequisite refactor for the core transport phase rather than technical debt to defer — the whole point of adding two more concurrent socket paths is undermined if all three inherit an already-known task-loss bug.

**Warning signs:**
- Intermittent, non-reproducible test failures where a response is expected but never arrives, especially under `pytest-xdist` or CI load where GC pressure is higher than on a quiet developer machine.
- `grep -rn "create_task\|call_soon" packages/lifx-emulator-core/src/lifx_emulator/server.py` finding more than one un-tracked call site after this milestone lands.

**Phase to address:**
Core transport phase, as a fix applied once and reused, before mDNS or Thread-specific code is layered on top of the same protocol-scheduling pattern.

---

### Pitfall 6: Setting the Thread bit on data replies but forgetting acks and StateUnhandled — and the same class of "forgot one code path" bug for firmware override and persistence

**What goes wrong:**
The Thread `thread_connection` flag is frame-address flags byte, bit 3 (PROJECT.md Context, `header.py:144,209` on the `lifx-async` side). This emulator's own `LifxHeader.pack()`/`unpack()` (`packages/lifx-emulator-core/src/lifx_emulator/protocol/header.py:74-97,116-138`) currently only reads/writes bits 0-1 of that byte (`res_required`, `ack_required`) — bit 3 does not exist as a field yet. Adding it only where the "normal" packet-response path constructs a header (`EmulatedLifxDevice.process_packet()`/`_create_response_header()`) is the easy 80% fix — but this repo has **two other header-construction call sites that are easy to miss**:

1. `EmulatedLifxServer._send_ack()` (`server.py:182-217`) builds the acknowledgement header (`Device.Acknowledgement`, type 45) via `device._create_response_header(...)`. If that helper is the one place the Thread bit is set from device state, this is already fine — but if the bit is instead threaded through as an explicit parameter on the "normal" response path only, acks will silently come back without it, and `lifx-async`'s acceptance requirement — "observe `thread_connection` true on **every** reply" (PROJECT.md Active requirements) — fails specifically on the packet type most likely to be spot-checked last.
2. `StateUnhandled` (type 223) responses, which switches already return for unhandled Light/MultiZone/Tile packet types via the same general response-construction path the device's other handlers use — but any new code that constructs `StateUnhandled` as a one-off exception path (rather than routing through the same `_create_response_header()` used everywhere else) will reproduce the same gap for that specific packet type. Since PROJECT.md's Active requirements explicitly call out both acks *and* StateUnhandled as places the bit must be set, this is a called-out risk, not a theoretical one.

The safest structural answer is to set the Thread bit in exactly **one** place — the shared `_create_response_header()` helper every response path already funnels through — and never construct a `LifxHeader` for an outgoing packet by any other route. A grep for `LifxHeader(` outside that helper after this milestone lands is the concrete regression check.

The same "forgot one code path" risk shape repeats for two other Active requirements:
- **Firmware override interaction**: enabling Thread sets host firmware to 4.200 "unless a scenario overrides firmware" (PROJECT.md Active). The existing `firmware_version` scenario field must be checked *after* connectivity is applied, not before, or a scenario applied before a device is switched to Thread will be silently clobbered by the Thread default, and vice versa if applied after. Because scenario resolution is cached per-device (`_cached_scenario`, flagged as fragile in CONCERNS.md — "correctness depends on every writer remembering to call `server.invalidate_all_scenario_caches()`"), a connectivity change that does not also invalidate that cache will leave a device serving a stale firmware value until something else happens to invalidate it.
- **Persistence round-trip**: `DeviceState` gets a new `connectivity` field; `serialize_device_state`/`load_device_state`, `export-config`, and `_device_state_to_yaml_dict` (already flagged in CONCERNS.md as complexity-61-adjacent code in `__main__.py:230`) must all be updated together. A field added to the dataclass but missed in one of the three (de)serialisation paths does not fail loudly — it fails as "connectivity silently resets to `wifi` after an emulator restart," which is exactly the kind of regression that only shows up in a long-running test fixture or a user's second `lifx-emulator` invocation, not in a unit test that only exercises the in-memory device.

**Why it happens:**
This codebase already has multiple response-construction and (de)serialisation call sites by design (ack fast-path vs normal response path vs StateUnhandled vs three-way persistence), which is efficient for the existing protocol but means any new per-device flag has to be threaded through all of them explicitly — there is no single choke point today other than `_create_response_header()`, and even that one is reached into as a "private" method from outside `EmulatedLifxDevice` already (CONCERNS.md "Server reaches into device/manager privates").

**How to avoid:**
- Set the Thread bit inside `_create_response_header()` itself (reading `device.state.connectivity` or equivalent), not as a parameter each call site must remember to pass, and audit every `LifxHeader(` construction site to confirm none bypasses it.
- Add an explicit test that asserts `thread_connection` is true on: a normal `StateColor`-style response, an `Acknowledgement`, and a `StateUnhandled` — from the same Thread-connectivity device in one test, not three separate tests that could each individually pass with a partial fix.
- Resolve `connectivity` → firmware-default before scenario firmware override is applied, invalidate the device's cached scenario whenever connectivity changes (mirroring the existing `invalidate_all_scenario_caches()` call pattern used for scenario mutations), and add a test that sets connectivity and *then* a conflicting `firmware_version` scenario, asserting the scenario wins.
- Add `connectivity` to the same three (de)serialisation paths in the same commit — `devices/persistence.py`'s serialise/load pair and `__main__.py`'s `_device_state_to_yaml_dict` — and add a round-trip test (write, restart-simulate by reloading from storage, assert `connectivity` unchanged) as part of that commit, not as a follow-up.

**Warning signs:**
- Manual UAT (per `lifx-async`'s Phase 14 evidence pattern) shows the Thread bit true on `GetColor`/`SetColor` replies but the client's own acceptance check (PROJECT.md: "observe `thread_connection` true on every reply") still fails intermittently — check whether the failing samples correlate with ack or StateUnhandled packets specifically.
- `grep -n "LifxHeader(" packages/lifx-emulator-core/src/lifx_emulator/` returning more than the one expected construction site after implementation.

**Phase to address:**
Core transport / device-emulation phase for the header-bit and firmware/persistence wiring; verification phase should include the multi-packet-type Thread-bit assertion described above as an explicit UAT/test item, since PROJECT.md already calls this out as a named requirement rather than an implicit one.

---

### Pitfall 7: A Thread device must never answer over IPv4 or to a broadcast/tagged query — but "silently drop" is easy to implement as "silently drop after already doing the work"

**What goes wrong:**
PROJECT.md's Active requirements state a Thread device "processes a packet only if it arrived on the emulator's IPv6 socket and is addressed to its serial (`tagged=0`); IPv4 packets and tagged/broadcast packets addressed to it are silently dropped." The naive implementation point to add this check is inside `EmulatedLifxServer._process_device_packet()` or inside `EmulatedLifxDevice.process_packet()`, i.e. *after* `DeviceManager.resolve_target_devices(header)` has already selected the Thread device as a broadcast target and *after* any scenario-drop / ack fast-path logic has already run for it. If the check is added in the wrong place, two distinct real bugs result:
1. **The Thread device still answers `GetService`/`StateService` over IPv4 broadcast** if the "which socket did this arrive on" information is not threaded all the way from the transport layer (which socket's `LifxProtocol.datagram_received()` fired) down to the per-device routing decision — `handle_packet()` today has no concept of "which local socket received this" at all, since there has only ever been one. Adding a second (IPv4) and third (mDNS) socket without carrying that provenance through `handle_packet(data, addr)` risks a Thread device leaking its `StateService` reply over the wire that real Thread bulbs never touch, which is precisely the hardware-observed behaviour ("Thread bulbs have no IPv4 address and do not answer IPv4 broadcast," PROJECT.md Context) this milestone exists to reproduce faithfully.
2. **Statistics/activity-log/ack side effects still fire for a "dropped" packet.** `_process_device_packet()` currently does the scenario drop-check ("Check if packet should be dropped BEFORE sending any ack... so that `drop_packets` suppresses all responses including acknowledgements," `server.py:245-251`) *before* the ack fast-path — the Thread connectivity/socket-origin check needs the same ordering discipline, or a Thread device will send an ack (or increment `packets_sent`, or emit a `PacketEvent` to the activity log/WebSocket) for a packet it is specified to treat as if it never arrived at all.

**Why it happens:**
`EmulatedLifxServer.handle_packet()` is a single entry point today because there has only ever been one socket; the routing/target-resolution/ack/response pipeline was designed with no notion of "packets can arrive on more than one socket with different rules per socket." Retrofitting socket-origin awareness into that pipeline is the actual hard part of this requirement, not the connectivity check itself, which is a one-line `if` once the origin is available.

**How to avoid:**
- Thread socket-origin information through explicitly: have each `LifxProtocol` instance (IPv4, IPv6) pass its own socket-family identity into `handle_packet()` (e.g. `handle_packet(data, addr, family=socket.AF_INET)`), and apply the Thread-device filter (`device.connectivity == "thread"` requires `family == AF_INET6` and `not header.tagged`) as an early, silent `return` in `handle_packet()` or `resolve_target_devices()` — before any ack fast-path, before any activity-log/stats side effect, mirroring exactly where the existing `drop_packets` scenario check already sits for the same reason.
- Write a test that sends a tagged `GetService` broadcast to a Thread device's serial over the IPv4 socket and asserts **zero** side effects: no response sent, `packets_sent`/`packets_sent_by_type` unchanged, no `PacketEvent` emitted, no ack — not just "no response packet observed by the test's own socket," which would pass even if an ack fired that the test never listened for.
- Confirm this filter also correctly still lets a *unicast, untagged* query addressed to a Thread device's serial through on the IPv6 socket — the two conditions (`family`, `tagged`) must be checked independently, since a broadcast (tagged) query can still arrive on the IPv6 socket if a future milestone adds IPv6 multicast discovery (explicitly out of scope for now, but the filter should not accidentally assume "IPv6 socket implies fine" without also checking `tagged`).

**Warning signs:**
- A test that broadcasts `GetService` over IPv4 and asserts "no `StateService` from the Thread device's serial in the responses list" passes, but a packet capture (or the activity log) shows the device's ack or `packets_sent` counter incremented anyway.
- The mDNS-only discovery acceptance test (PROJECT.md: `discover_mdns()` an emulated Thread device) passes even though a *separate*, direct-broadcast-based UDP discovery test was never written to confirm the negative case.

**Phase to address:**
Core transport / device-routing phase, once both sockets exist — this cannot be verified in isolation before the IPv6 socket lands, so plan it as a distinct verification step immediately after both sockets are live, not folded into the mDNS responder phase where it is easy to assume "mDNS is the only discovery path so IPv4 broadcast doesn't matter."

---

### Pitfall 8: Two known repo bugs get worse, not better, once Thread devices exist — the `rstrip("0000")` serial truncation and the unenforced complexity limit against a monolithic `run()`

**What goes wrong:**
Two pre-existing, documented issues in `.planning/codebase/CONCERNS.md` interact directly with this milestone's new surface area:

1. **`server.py:375`**: `target_str = "broadcast" if header.tagged else header.target.hex().rstrip("0000")` uses `str.rstrip`, which strips a **character set** ("0" and any of the four "0000" characters, all zero anyway), not a suffix — so any serial whose hex representation ends in one or more literal `0` digits gets truncated in the RX debug log and in the `PacketEvent.target` pushed to `/api/activity` and the WebSocket `activity` topic (already verified: `d073d5000100` → `"d073d50001"` incorrectly, per CONCERNS.md). Thread devices are created with the same serial-assignment scheme as WiFi devices (per-device `connectivity`, not a new serial namespace), so this bug applies to Thread serials exactly as much as WiFi ones — it is not made worse in kind, but this milestone adds a whole new observability surface (the mDNS TXT `id=` field, which must carry the *correct, untruncated* serial) built adjacent to a log path that already gets this wrong. A likely mistake is copying the same truncation pattern into new mDNS-related logging or into a Thread-specific debug log line, doubling the bug's footprint instead of fixing it once.
2. **Complexity limit is documented but not enforced** (CONCERNS.md: `C901`/`PLR09xx` are configured in `pyproject.toml` but never added to `select`, so `uv run ruff check --select C901,PLR0913,PLR0912,PLR0915 packages/` currently reports 49 violations that CI does not catch) **against** `run()` in `packages/lifx-emulator/src/lifx_emulator_app/__main__.py:580-1145`, already measured at cyclomatic complexity 61, 26 parameters, 197 statements. This milestone's own Active requirements list four new CLI-config surfaces that all land in or near this function: a `connectivity` CLI flag, IPv6 bind-address/port configuration, mDNS enable/disable, and the interaction between all of the above and existing device-creation flags for eight device flavours. Every one of those additions is a parameter or branch added to the single worst-offending function in the codebase, and because `C901` is not actually enforced, none of them will be caught by CI even though `CLAUDE.md` and the CI step name both claim it is.

**Why it happens:**
Both are "the existing code already does this, so it looks like the safe pattern to extend" traps: the log line already at `server.py:375` is the closest existing example for any new "log this serial" code; `run()` is already the single place every CLI flag is wired up, so it is the path of least resistance for a fourth or fifth new flag, and the enforcement gap (`C901` configured but not selected) means nothing stops it locally or in CI.

**How to avoid:**
- Fix `server.py:375` to `header.target[:6].hex()` (the documented fix in CONCERNS.md) in the same phase that adds any new serial-carrying log line for mDNS or IPv6, so there is exactly one correct pattern in the codebase to copy from, not two divergent ones.
- Do not add the new CLI flags for connectivity/IPv6/mDNS as more parameters to `run()`. Given this milestone's own roadmap preference ("Horizontal layers... CLI/config, then API" — PROJECT.md Key Decisions) is already going to touch `__main__.py` directly, treat this as the forcing function to extract `_build_devices_from_flags()`/`_start_servers()` (the exact refactor CONCERNS.md already recommends) rather than adding a 27th, 28th, 29th parameter to the existing 26-parameter function. This is materially cheaper to do now, before three more flags land, than after.
- Separately: actually add `"C90"` to `pyproject.toml`'s `[tool.ruff.lint] select` (with `per-file-ignores` for the generated `products/registry.py`/`protocol/packets.py`) as part of this milestone's own quality gate, since it is the one CI change that would have caught both the pre-existing `run()` problem and any new complexity this milestone adds to it, and CONCERNS.md already specifies the exact fix.

**Warning signs:**
- Any new `logger.debug`/`logger.info` call in mDNS or IPv6 code that formats a serial with `.rstrip(...)` instead of `[:6].hex()` or an equivalent explicit-length slice.
- `run()`'s statement/branch/parameter count increasing further in a diff for this milestone without a corresponding extraction commit.

**Phase to address:**
Repo-hygiene fix (the `rstrip` bug) belongs in whichever phase first adds new mDNS/Thread logging, as a one-line fix alongside it. The `run()` complexity and the `C901` enforcement gap belong in the CLI-config phase specifically, ahead of adding the new flags, per the "Horizontal layers" roadmap decision already recorded in PROJECT.md.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Skip the legacy-unicast reply path, always multicast every mDNS reply | Simpler responder, one code path | Breaks the actual client (`lifx-async` queries from an ephemeral port specifically to avoid port 5353); Pitfall 1 makes this fail silently, not loudly | Never — this is the one path the stated acceptance oracle actually uses |
| Bind the mDNS socket to `INADDR_ANY`/`::` unconditionally, ignoring configurability | Fast to ship | Cannot be tuned per-CI-runner if a future runner's loopback multicast is restricted; also conflicts with "default behaviour unchanged for existing users" if it changes default port bindings elsewhere | Acceptable only for the mDNS socket specifically (it must be 5353/224.0.0.251 to be useful at all); never acceptable for the existing IPv4 LIFX socket, whose default bind address/port must stay unchanged |
| Add `connectivity` only to the in-memory `DeviceState` and defer persistence wiring to a "later" API phase | Faster first PR | Exactly the CONCERNS.md-flagged pattern (`advertised_services` PR #156 is cited as the closest precedent and *did* wire persistence at the same time) — deferring it means a demo works but a restarted emulator silently reverts every Thread device to WiFi | Never — persistence should land in the same phase as the field, per the existing `advertised_services` precedent |
| Copy `LifxProtocol.datagram_received()`'s untracked-task pattern for the new IPv6/mDNS protocols to "match the existing style" | Consistent-looking code, fast | Triples the exposure to the documented GC-eligible-task-loss bug (CONCERNS.md) right as more concurrent traffic (mDNS + IPv6 + existing IPv4) is added | Never — fix the pattern once, in the core transport phase, before duplicating it |
| Leave `C901`/complexity linting unenforced and just "be careful" adding new CLI flags to `run()` | No pyproject.toml/CI changes needed | Already measured at complexity 61 before this milestone; every new flag makes the eventual required refactor larger and riskier | Acceptable only if the CLI-config phase explicitly schedules the `run()` extraction refactor as its first task, before flags are added — otherwise never |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| `lifx-async`'s `MdnsTransport` (the acceptance oracle) | Assuming it joins the multicast group and listens passively like a normal responder-discovery tool | It never joins the group and only sends legacy-unicast queries from an ephemeral port, expecting a direct unicast reply (`transport.py` docstring) — the emulator's responder must implement the RFC 6762 §6.7 legacy-unicast reply path or this specific client will never discover anything, even though a generic `dns-sd`/`avahi-browse` test would work fine |
| System mDNS daemons (`mDNSResponder`, `avahi-daemon`, Windows' native mDNS) | Treating "socket bound successfully" as proof the responder will see every query | `SO_REUSEADDR`/`SO_REUSEPORT` binding *coexisting* with a system daemon does not guarantee every multicast packet is delivered to both sockets — verify with an actual query/reply round-trip in tests, not just a successful `bind()` |
| GitHub Actions runners (Ubuntu, macOS — this repo's actual CI matrix) | Assuming CI has no multicast capability at all and skipping mDNS tests entirely, or assuming it behaves exactly like a real LAN | GitHub-hosted runners' loopback interface (`lo`/`lo0`) does support multicast; tests can bind the mDNS socket to `0.0.0.0`/`INADDR_ANY` (or the group address itself — never to a bare unicast/loopback address as the bind target, since that filters out the multicast-destined packets at the socket layer) and join `224.0.0.251` with the interface explicitly pinned to loopback, giving a hermetic, real-multicast test that never depends on the runner's actual LAN |
| `HierarchicalScenarioManager`'s per-device cache (`_cached_scenario`) | Changing `connectivity` (and therefore the effective firmware default) without invalidating the device's cached scenario resolution | Call the existing `invalidate_all_scenario_caches()` (or a per-device equivalent) whenever `connectivity` changes, exactly as the `ScenarioService` API path already does for scenario mutations (CONCERNS.md "Scenario cache invalidation is manual") |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| One `asyncio.create_task` per received mDNS query with no bound on concurrent in-flight replies | Fine with one or two test clients; under a broadcast storm or a misbehaving test that retransmits queries aggressively (RFC 6762 §5.2 retransmission at 1s/3s intervals, multiplied by however many client instances run in a test suite), unbounded concurrent reply-building tasks pile up on the single-threaded event loop | Use the same tracked-task-set pattern recommended for Pitfall 5's fix, and consider a cheap per-source-address debounce (a query from the same address within a very short window is very likely a duplicate/retransmission per RFC 6762 §5.2, which explicitly tolerates and expects deduplication) | Noticeable once test suites run mDNS discovery in parallel across `pytest-xdist` workers against a shared emulator instance, or once more than a handful of emulated devices each add their own AAAA/TXT records to a single PTR sweep response |
| Building a full DNS-SD PTR+SRV+TXT+A/AAAA answer set per device inline, per query, with no memoisation | Fine for the current handful of devices in a typical test fixture; response-building cost scales linearly with device count on every single query, unlike the existing per-packet LIFX pack/unpack cost which CONCERNS.md already flags as reflection-driven and CPU-bound | Precompute the static parts of each device's record set (name, TXT string, product/firmware) when connectivity or firmware changes, not on every query; this mirrors the "Reflection-driven pack/unpack on every packet" performance note already in CONCERNS.md, which recommends the same precompute-once approach for the existing protocol layer | Matters once a test scenario emulates a larger device fleet (this repo's own hardware evidence references an 8-device Thread fleet) and mDNS sweeps happen frequently in a test loop |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Binding the mDNS responder or the new IPv6 socket to a non-loopback address by default | Same class of issue CONCERNS.md already flags for the management API ("Management API is unauthenticated and can bind to all interfaces") — an mDNS responder that joins 224.0.0.251 on a real network interface by default will advertise every emulated device (including a "Thread" device whose entire point is to look real) to the actual LAN, which is surprising for a testing tool and could confuse real client software on the same network | Keep the IPv6 socket's documented default (`::1`, per PROJECT.md) and make the mDNS responder's bind interface explicitly configurable but defaulting to loopback-only or an explicit opt-in flag for LAN-wide advertisement, consistent with the emulator's existing `127.0.0.1` default for both the LIFX UDP socket and the management API |
| Trusting TXT/SRV content from a locally-generated response without bounding record counts or string lengths | Low risk for a responder emulator specifically (it only ever answers for its own emulated devices, not arbitrary network input) — but if the responder ever *echoes* or forwards any part of an incoming query into its reply without validation (e.g. reflecting a malformed question section back), it inherits the reflection/amplification concern documented for real-world mDNS misconfiguration (mDNS is a well-known reflection/amplification vector when a responder answers WAN-sourced queries) | Never answer a query whose source address is not link-local/private, and never build a reply from unvalidated attacker-controlled input — always build replies purely from the emulator's own device state, matching how the existing LIFX packet handlers already only ever emit protocol-generated response objects, never echoed request bytes |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Silently disabling mDNS or the IPv6 socket on bind failure with only a DEBUG-level log line | A user (or CI job) troubleshooting "why can't `lifx-async` discover my Thread device" has no visible signal that mDNS never actually started | Log the mDNS/IPv6 bind failure at WARNING (matching the existing convention CONCERNS.md documents for malformed-packet handling — "packets shorter than 36 bytes are handled at WARNING without traceback" is the right severity level to mirror), and surface it in `/api/monitoring` or the CLI's startup banner so it is visible without reading logs |
| Making `connectivity` a write-once, create-time-only field with no clear error when a client tries to change it later | A user experimenting via the API who tries `PATCH`-ing a live device's connectivity gets either a silent no-op or a confusing generic error | If connectivity is deliberately immutable after creation (mirroring the real hardware fact PROJECT.md documents — "A radio is either WiFi or Thread and cannot change without a firmware crossgrade"), return an explicit, named validation error from the API rather than ignoring the field or allowing a partial update that leaves the header bit and TXT record disagreeing with each other |

## "Looks Done But Isn't" Checklist

- [ ] **Thread bit on every reply**: Verify it explicitly on `StateColor`/similar data replies, `Acknowledgement` (type 45), and `StateUnhandled` (type 223) from the *same* device in one test — Pitfall 6 shows why testing only the first is not sufficient.
- [ ] **mDNS legacy-unicast path**: Verify by asserting on captured raw reply bytes (header ID echoed, cache-flush bit clear, TTL ≤10s) — a test that only checks "the client eventually resolved the device" can pass with a wrong TTL or cache-flush bit that this one client's parser happens to tolerate.
- [ ] **`connectivity` persistence round-trip**: Verify by writing a device to disk, restarting/reloading storage, and asserting `connectivity` survives — not just that the field exists on the in-memory dataclass.
- [ ] **Thread device IPv4/broadcast isolation**: Verify by asserting *zero* observable side effects (no response, no ack, no `packets_sent` increment, no activity-log/WebSocket event) for a broadcast sent over IPv4 to a Thread device's serial — not just "no response packet returned to the test's own socket."
- [ ] **IPV6_V6ONLY actually set**: Verify with `sock.getsockopt(IPPROTO_IPV6, IPV6_V6ONLY)` in a test on the macOS CI leg specifically, since the failure mode (`EINVAL` on set-after-bind) is macOS-specific and can silently pass on Linux.
- [ ] **CI mDNS tests don't depend on the runner's real LAN**: Verify by running the mDNS test suite with the runner's outbound network access disabled/sandboxed (or simply confirming it passes identically whether or not the CI job has LAN egress) — a test that happens to pass because it silently found a real device or a real system mDNS daemon on the runner is not testing the emulator.
- [ ] **Windows socket-option guard**: Verify with a test that monkeypatches away `socket.SO_REUSEPORT` (simulating Windows) and confirms the mDNS responder still starts, since there is no Windows CI leg to catch a missing guard directly.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Pitfall 1 (5353 unicast-stealing) discovered after mDNS responder ships | MEDIUM | Add the legacy-unicast branch as a follow-up patch (source-port detection + unicast `sendto()` reply); no wire-format change needed, only routing logic — existing multicast-path tests should be unaffected |
| Pitfall 3 (V6ONLY set after bind) discovered after IPv6 socket ships | LOW | Swap the bind sequence to match `_Ipv6EmulatedLifxServer.start()` exactly; this is a contained, single-function fix with no data-model impact |
| Pitfall 6 (Thread bit missing on acks/StateUnhandled) discovered after release | LOW–MEDIUM | Move the bit-setting logic into `_create_response_header()` if it currently lives elsewhere; audit and fix any bypassing `LifxHeader(` construction sites; no persisted-data migration needed since the bit is set per-response, not stored |
| Pitfall 6 (persistence round-trip gap for `connectivity`) discovered after release, with existing persisted device files already lacking the field | LOW | Default the field to `"wifi"` on load when absent from a persisted JSON file (the same forward-compatible pattern any newly-added `DeviceState` field should already use); no destructive migration required since `wifi` is the correct default for every pre-existing persisted device |
| Pitfall 7 (Thread device answered IPv4 broadcast) discovered after release | MEDIUM | Requires threading socket-origin through `handle_packet()` if that plumbing was skipped initially — this is the costliest pitfall to retrofit because it touches the shared entry point every packet already flows through; strongly prefer catching this before release via the explicit negative test in the checklist above |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| 1. Port 5353 unicast-stealing | mDNS responder core | Ported `ipv6_thread_probe.py`-style ephemeral-vs-5353 comparison run against the emulator |
| 2. Cross-platform socket-option divergence | mDNS responder core | Unit test with `SO_REUSEPORT` monkeypatched absent (Windows simulation) |
| 3. IPV6_V6ONLY set-after-bind / dual-stack defaults | Core transport | `getsockopt(IPV6_V6ONLY)` assertion on macOS CI leg specifically |
| 4. DNS message construction (legacy-unicast ID/cache-flush/TTL/compression) | mDNS responder core | Raw-byte assertions on captured replies for both multicast and legacy-unicast paths |
| 5. Untracked fire-and-forget tasks (new IPv6/mDNS protocols) | Core transport (fix once, before duplicating the pattern) | Code review grep for un-tracked `create_task`/`call_soon` across all three protocols |
| 6. Thread bit on acks/StateUnhandled; firmware override ordering; persistence round-trip | Core transport / device-emulation | Multi-packet-type Thread-bit test; scenario-override-wins test; storage round-trip test |
| 7. Thread device IPv4/broadcast leakage | Core transport / device-routing (after both sockets exist) | Explicit negative test: broadcast over IPv4 to a Thread serial, assert zero side effects |
| 8. `rstrip` serial bug reused; `run()` complexity/enforcement gap | Repo hygiene (fold into whichever phase first touches serial logging); CLI-config phase (ahead of new flags) | Fixed `header.target[:6].hex()` reused in any new log line; `C901` added to `ruff` `select` and passing; `run()` extraction landed before new flags |

## Sources

- `lifx-async` `.planning/scripts/ipv6_thread_probe.py` (docstring, `_LegacyMdnsTransport`, `stage_ports`) — direct evidence and reproduction of the mDNSResponder unicast-stealing bug, sibling repo, read directly
- `lifx-async` `src/lifx/network/discovery/mdns/transport.py` — documents the ephemeral-port legacy-unicast design and names the port-5353-contention bug explicitly, read directly
- `lifx-async` `src/lifx/network/discovery/mdns/discovery.py` — client-side rejection rules (link-local without zone, malformed TXT, byte-incomplete owners, TXT/SRV RR-per-owner caps), read directly
- `lifx-async` `tests/conftest.py:280-359` (`_Ipv6EmulatedLifxServer`) — verified macOS `EINVAL` on `IPV6_V6ONLY` set after bind, read directly
- This repo's `.planning/codebase/CONCERNS.md` and `packages/lifx-emulator-core/src/lifx_emulator/server.py`/`protocol/header.py` — repo-specific bugs (`rstrip` truncation, untracked tasks, `run()` complexity, scenario-cache invalidation), read directly
- RFC 6762, Multicast DNS — §6.7 legacy unicast (ID echo, cache-flush bit prohibition, TTL ≤10s recommendation), §5.2 (query retransmission/deduplication), §10.2 (cache-flush semantics), §17-18 (message size, header fields) — [rfc-editor.org/rfc/rfc6762](https://www.rfc-editor.org/rfc/rfc6762.html)
- RFC 6763, DNS-Based Service Discovery — §12 answer/additional section placement convention for PTR/SRV/TXT/address records
- Microsoft Learn, "Using SO_REUSEADDR and SO_EXCLUSIVEADDRUSE" — Windows socket-reuse semantics differing from POSIX, and the multicast exception where both are delivered — [learn.microsoft.com/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse)
- Python bug tracker / CPython PR, bpo-29883 / gh-74069 — Windows `ProactorEventLoop` UDP support added in Python 3.8, confirming this project's Python 3.10+ floor is unaffected by the historical Proactor UDP gap — [github.com/python/cpython/issues/74069](https://github.com/python/cpython/issues/74069), [bugs.python.org/issue29883](https://bugs.python.org/issue29883)
- Avahi issue tracker, "Detected another IPv4 mDNS stack running on this host" and related SO_REUSEADDR discussion — confirms `avahi-daemon` explicitly sets `SO_REUSEADDR` to permit (but warns against relying on) multiple concurrent mDNS responders — [github.com/avahi/avahi/issues/348](https://github.com/avahi/avahi/issues/348)
- `docker/for-mac` issue #5335, "M1 Mac address already in use port 53 by mDnsResponder" — corroborating evidence of macOS `mDNSResponder` port contention with third-party software binding mDNS-adjacent ports — [github.com/docker/for-mac/issues/5335](https://github.com/docker/for-mac/issues/5335)

---
*Pitfalls research for: mDNS/DNS-SD responder + IPv6 UDP transport + Thread-device emulation, LIFX emulator*
*Researched: 2026-09-09*
