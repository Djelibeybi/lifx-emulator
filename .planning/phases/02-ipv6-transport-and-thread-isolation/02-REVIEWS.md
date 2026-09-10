---
phase: 02
reviewers: [claude, opencode, antigravity]
reviewed_at: 2026-09-10T03:44:18Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md]
models:
  claude: "claude-opus-5 (reasoning=high)"
  opencode: "openrouter/z-ai/glm-5.3 (reasoning=high)"
  antigravity: "gemini-3.8-flash-high"
model_sources:
  claude: "pinned"
  opencode: "pinned"
  antigravity: "pinned"
---

# Cross-AI Plan Review — Phase 02

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Claude Review

I read the four plans against the live source. Here is the review.

---

# Cross-AI Plan Review — Phase 2: IPv6 Transport and Thread Isolation

Verified against the repository at `gsd/phase-02-ipv6-transport-and-thread-isolation`. All `file:line` references below were opened and checked.

---

## 02-01

### Summary

A well-targeted hygiene plan that correctly sequences the two `server.py` defects ahead of the second protocol instance, exactly as the ROADMAP note (`​.planning/ROADMAP.md:88`) requires. The two defects it names are real and I confirmed both. The main weaknesses are an oversized Task 1, a silent behaviour change to unknown-packet logging that no acceptance criterion pins, and an unaddressed interaction between the `packets_received` counter and the short-packet guard that Plan 02-03 will later disturb.

### Strengths

- **The `_track_save_task` claim is accurate.** `devices/device.py:189-196` adds the task to `self.background_save_tasks` and passes `set.discard` directly as the done callback — it never calls `task.exception()` or `task.result()`. The plan's Resolved Decision 2 ("retains and discards but never retrieves exceptions") is exactly right, and Pitfall 7 in RESEARCH.md describes the resulting `Task exception was never retrieved` correctly.
- **The two divergent target renderings are real and the unification is justified.** `server.py:384` renders an unknown-packet target as `header.target.hex()` (16 hex chars, padding included); `server.py:403-404` renders the same field as `header.target.hex().rstrip("0000")`; `devices/manager.py:279-286` routes on `header.target[:6].hex()`. Three renderings of one field, one of which is wrong. One canonical `_format_target` is the right fix.
- **The tracer placement is correct.** Making the *existing* IPv4 path the tracer (rather than a throwaway spike) means the retention pattern is proven in production code before Plan 02-04 copies it into a second protocol.

### Concerns

**HIGH — `packets_received` semantics for short and unparsable packets are unpinned, and the existing test asserts nothing.**
`server.py:342` does `self.packets_received += 1` *before* the `len(data) < LIFX_HEADER_SIZE` guard at `server.py:344`. Plan 02-01 says only "Preserve the short-header guard before unpacking/activity" and is silent on the counter. Plan 02-03 then moves all statistics to *after* target resolution — which necessarily changes short-packet and unpack-failure counting, since neither path ever reaches resolution. Nothing in AC-13/AC-14 or either plan states the intended post-change value. The regression is invisible today: `test_server.py:83-89` (`test_handle_packet_too_short`) calls `handle_packet` and makes **no assertion at all**. Pin the intended semantics in 02-01 and add the missing assertions to that test while you are in the file.

**MEDIUM — the unknown-packet log format changes silently.**
Routing `server.py:384` through `_format_target` changes that log line from 16 hex characters to 12 (and introduces `broadcast` for an all-zero untagged target, which that line currently renders as `0000000000000000`). That is arguably the correct outcome, but it is an operator-visible output change with no acceptance criterion and no named test. The plan's AC list only covers `PacketEvent.target` and "RX logging".

**MEDIUM — Task 1 is oversized for one atomic commit.**
Task 1 creates `background_tasks.py`, rewires `LifxProtocol.datagram_received`, adds `_format_target` and rewires three call sites, modifies `start()`/`stop()` for admission and drain, and authors two test suites (a seven-terminal-path tracker matrix plus a forced-GC server tracer). The plan's own `confidence: low` and `36000` token estimate reflect this. The tracker unit matrix is cleanly separable from the server tracer and should be its own task, so a tracker bug does not block the serial fix.

**LOW — `start()`/`stop()` are edited twice.**
02-01 Task 1 modifies them "only enough to open tracker admission… drain… then close the transport"; 02-04 Task 1/2 then rewrites both entirely. Sequential, so no merge conflict, but it is duplicated authoring and the 02-01 version's drain-then-close ordering has to be re-derived in 02-04.

**LOW — tracker reuse after `shutdown()` is unspecified.**
The contract lists `start_accepting()`, `stop_accepting()` and `shutdown(timeout)`. Nothing says whether `start_accepting()` after `shutdown()` is legal. 02-02's lifespan implies a single open→drain cycle, but `create_api_app` is called once per test and 02-04's `stop()`/`start()` idempotency tests will exercise restart. Specify it.

### Suggestions

1. Split Task 1 into `1a: BackgroundTaskTracker + unit matrix` and `1b: server adoption + _format_target + tracer`, keeping the tracer-gate semantics on 1b.
2. Add an explicit acceptance criterion for post-change `packets_received` / `error_count` on the short-packet and unpack-failure paths, and add the assertions to `test_handle_packet_too_short` (currently assertion-free).
3. Add the unknown-packet-log format change to the AC list with a named test, or explicitly exclude `server.py:384` from the unification and say why.

### Risk Assessment

**MEDIUM.** The mechanism is right and the defects are real; the risk is unpinned statistical side effects that Plan 02-03 will then move again, plus a large single commit.

---

## 02-02

### Summary

Correctly scoped and correctly targeted — I verified every seam it names. The design is sound, but one specific decision (`accepting=False` with `start_accepting()` only in the FastAPI lifespan) collides with how this repository's tests actually build the app, and would silently drop every WebSocket broadcast in the two largest app test modules.

### Strengths

- **Every named seam exists as described.** `_schedule_async` is exactly the bare scheduler at `event_bridge.py:30-40` (`loop.create_task(coro)` with no retention, `RuntimeError` → warning). `create_api_app` constructs `WebSocketManager` and `StatsBroadcaster` at `app.py:65-66`, defines `lifespan` at `app.py:68-76`, and wires all three adapters at `app.py:207-218`. Injection at those points is the right shape.
- **The un-awaited-coroutine warning the plan promises to eliminate is real.** `test_websocket.py:290-297` patches `event_bridge._schedule_async` while `observer.on_packet_received(event)` constructs a real `AsyncMock()` coroutine that is then never awaited or closed. Replacing the patch with an injected recording tracker that closes captured coroutines is the correct fix, not a suppression.
- **`StatsBroadcaster` is correctly left out of scope.** It already holds `self._task` (`event_bridge.py:200`) and cancels-and-awaits in `stop()` (`event_bridge.py:222-233`), so it is not a HYG-01 gap. Draining the bridge tracker *after* `stats_broadcaster.stop()` (plan Task 2) is also the right order, since the broadcast loop can enqueue work.

### Concerns

**HIGH — `accepting=False` breaks the app's actual test-client pattern.**
Task 2 specifies `BackgroundTaskTracker("websocket-event-bridge", accepting=False)` with `start_accepting()` inside the lifespan. But `test_websocket.py:23-26` returns `TestClient(app)` **without** a context manager, and `test_api.py:31` does the same. Starlette only runs lifespan under `with TestClient(app)`. So for the entirety of `test_websocket.py` and `test_api.py`, admission is never opened and, per D-14, every scheduled broadcast coroutine is closed and logged as a refusal — silently. Tests that inject a fake tracker will still pass, which makes the breakage invisible in exactly the suite meant to catch it. (`test_cli_validation.py` does use `with TestClient(app)` throughout, so the failure mode is inconsistent across the app package.) Either default `accepting=True` and let the lifespan own only `shutdown()`, or call `start_accepting()` at `create_api_app` time and treat the lifespan as the drain boundary only.

**MEDIUM — required `task_tracker` parameters are a breaking signature change.**
`wire_device_events(device_manager, ws_manager)`, `WebSocketActivityObserver(ws_manager, inner_observer=None)` and `WebSocketStateChangeObserver(ws_manager)` are importable public symbols of the app package. Making `task_tracker` required breaks any embedder. The plan's prohibition on implicitly creating a tracker inside an observer is sound, but a keyword-only `task_tracker: BackgroundTaskTracker | None = None` that falls back to an owner-local instance (with a debug log noting it is not lifespan-drained) preserves compatibility without a global collection. At minimum, record the break.

**MEDIUM — a tracker is created per `create_api_app()` call and never drained without a lifespan.**
Every test that calls `create_api_app(server)` mints a tracker. Under `accepting=False` these are inert; if the first concern is fixed by flipping to `accepting=True`, they become live-but-never-drained. Whichever way it goes, the plan should say what happens to a tracker whose lifespan is never entered.

**LOW — the five operation families are complete, but the label contract is loose.**
The plan requires labels "including the operation plus serial, direction, or packet type where available", and Task 1's AC asserts labels. Without a stated format the assertions and the implementation can drift. A one-line convention (e.g. `"<operation>:<serial|direction|pkt_type>"`) would make the tests meaningful.

### Suggestions

1. Change the admission model: `accepting=True` at construction, lifespan owns `shutdown(timeout=5.0)` only — or keep `accepting=False` and add `start_accepting()` in `create_api_app`, plus a regression test that a non-context-managed `TestClient(app)` still broadcasts.
2. Make `task_tracker` keyword-only with a `None` fallback, or add a note to the plan that this is a deliberate breaking change to three public app symbols.
3. Fix a label format string in the plan text so Task 1's label assertions are unambiguous.

### Risk Assessment

**MEDIUM.** Sound design against verified seams, with one concrete decision that will silently disable the behaviour under test in the module the plan is written to fix.

---

## 02-03

### Summary

Architecturally the strongest of the four — the assumption-delta block and the barrier-interleaved cross-route invariant are exactly the right proofs for D-03/D-05. Two problems undercut it: Task 1 knowingly breaks a Phase 1 test that its own verify command does not run (and misattributes the cause), and the `handle_packet` signature change is a breaking public-API change typed with a private class, with none of the compatibility care D-01 lavishes on `server.transport`.

### Strengths

- **The reply-transport pitfall is real and precisely located.** `_send_ack` reads `if self.transport: self.transport.sendto(response_data, addr)` (`server.py:235-236`) and `_process_device_packet` does the same in its response loop (`server.py:303-304`). With two protocols, `connection_made` (`server.py:184-186`) assigns `self.server.transport` unconditionally, so the last endpoint created wins and IPv4 replies would leave the IPv6 socket. Threading the context to both send sites is the correct fix.
- **The effect-ordering pitfall is real.** Statistics (`server.py:342`, `server.py:359`), RX logging (`server.py:407-414`) and `activity_observer.on_packet_received` (`server.py:417-427`) all execute *before* `resolve_target_devices` at `server.py:430`. NET-03's "before … statistics or activity-log side effects" genuinely requires this reordering.
- **The manager change is minimal and preserves the contract.** `resolve_target_devices` (`manager.py:268-290`) already returns a plain list and already uses `header.target[:6].hex()`. Adding `family: socket.AddressFamily = socket.AF_INET` to both `IDeviceManager` (`manager.py:98`) and the implementation, with post-selection filtering, is a small diff. The four existing no-family call sites (`test_device_manager.py:110,132,154,171`) all use WiFi devices and remain valid.

### Concerns

**HIGH — Task 1 breaks a Phase 1 test that Task 1's verify command does not run, and the plan misstates the cause.**
`test_thread_identity.py:1062-1063` calls `device_manager.resolve_target_devices(broadcast_header)` with `tagged=True` against a mixed WiFi/Thread fleet and asserts `len(targets) == 2`. Task 1's own matrix says a Thread device is filtered from a tagged broadcast on **both** families — so after Task 1 that assertion is `1`, and the test fails. Task 1's `<verify>` is `uv run pytest packages/lifx-emulator-core/tests/test_device_manager.py -q --no-cov` only. Per the execution workflow, Task 1 will pass its gate and commit atomically with `test_thread_identity.py` red. Worse, Task 1's action text says to update that test "in Task 2 only when the server context signature requires it" — but the break is caused by Task 1's manager filter, not by any signature. An executor following the text literally will not touch it. Add `test_thread_identity.py` to Task 1's verify command and correct the attribution.

**HIGH — `handle_packet(data, addr)` → `handle_packet(data, context)` is an unmitigated public-API break with a private type.**
`handle_packet` is a documented entry point (`.claude/CLAUDE.md` Architecture → "UDP packet → `EmulatedLifxServer.handle_packet()`"), has no leading underscore, and is called directly with `addr` at roughly two dozen sites in `test_server.py` (e.g. `:89, :114, :144, :178, :208, :269, :298, :417, :442, :476, :504, :538, :565, :606`). D-01 goes to considerable lengths to preserve `server.transport` for direct library callers — this change is strictly larger and gets none of that care, and it forces any external caller to construct `_DatagramContext`, a private name. Either keep `addr` as the second positional with an optional `context`/`family` (defaulting to `AF_INET`, matching D-07's own compatibility logic), or make the context type public. The current design is internally inconsistent with D-01/D-07.

**MEDIUM — removing `server.transport = transport` from `connection_made` directly breaks a named test the plan does not name.**
`test_server.py:348-359` (`test_protocol_connection_made`) constructs `server.LifxProtocol(server)`, calls `connection_made(mock_transport)` and asserts `server.transport == mock_transport`. Task 2 moves that assignment into `start()`. The plan lists `test_server.py` in `<files>` and says protocol tests need contexts, but never names this specific assertion, which must be deleted or re-pointed rather than adapted.

**MEDIUM — complexity headroom in `handle_packet` is one branch.**
`uv run ruff check --select C901 --config 'lint.mccabe.max-complexity=6'` reports `handle_packet` at **9** against the project budget of 10 (`_format_packet_fields` at 10, `__init__` at 7). Adding the family-resolution early return consumes the remaining headroom; anything else fails. No task in 02-03 runs a lint gate — the first ruff invocation in the whole phase is 02-04 Task 3. Add `uv run ruff check <changed files>` to this plan's verification.

**LOW — debug-log amplification on rejected Thread traffic.**
D-08 puts a per-rejection debug log in `DeviceManager` including serial, family, tagged state and rendered target. Under the packet flood the plan itself constructs, with DEBUG enabled, that is one log record per rejected datagram. T-02-13 in the threat register lists this as "mitigate" without noting the amplification. Worth a rate-limit note or an explicit accept.

**LOW — NET-02's "without reaching into device private methods" is not addressed.**
`server.py` calls `device._create_response_header` (`:228`), `device._get_resolved_scenario` (`:276`) and `device._should_handle_packet` (`:294`). SPEC line 83 narrows the requirement to *target resolution*, so this is genuinely out of scope — but no plan says so. A verifier reading `REQUIREMENTS.md:26` verbatim would mark NET-02 incomplete. State the narrowing in the plan.

### Suggestions

1. Add `test_thread_identity.py` to Task 1's verify command; rewrite the mixed-fleet update instruction to attribute the change to the manager filter and specify the new expected target count.
2. Preserve `handle_packet(data, addr, *, family=AF_INET)` (or make the context type public) so the entry point stays callable by existing library users, mirroring D-07's compatibility default.
3. Name `test_protocol_connection_made` explicitly in Task 2's change list.
4. Add a lint gate (`ruff check` on changed files) to this plan's verification, given one branch of complexity headroom.

### Risk Assessment

**MEDIUM-HIGH.** The architecture is correct and well-proven; the risks are a self-inflicted red-suite commit and a breaking public-API change that contradicts the phase's own compatibility posture.

---

## 02-04

### Summary

The lifecycle mechanics — raw-socket-vs-adopted-transport ownership, `BaseException` rollback with bare re-raise, closure barriers, port-zero device-port propagation — are correct and well-grounded in the sibling oracle at `lifx-async/tests/conftest.py:302-336`. What is missing is environmental: the plan treats "an IPv6 loopback socket can be bound at the IPv4-chosen port" as a given, and it is not. Two failure modes follow from that, both of which hit existing users and existing tests rather than new code.

### Strengths

- **The oracle pattern is faithfully reproduced.** `lifx-async/tests/conftest.py:320-336` uses exactly `setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)` → `bind` → `setblocking(False)` → `create_datagram_endpoint(sock=...)` with `sock.close()` on partial failure. The plan's ownership refinement (close the *transport* once adoption succeeds, the raw socket before) is the correct production hardening of that example.
- **D-01 is genuinely load-bearing and the plan honours it.** `lifx-async/tests/conftest.py:643` reads `server.transport.get_extra_info("socket")`. Keeping `transport` as the IPv4 alias and `_ipv6_transport` private is the right call.
- **Port-zero device propagation is real.** `handlers/device_handlers.py:31-32` builds `StateService` from `device_state.port`, and `server.py:158` / `server.py:458` set `device.state.port = self.port` — which is literally `0` under `port=0`. The plan's "update device advertised ports at commit, and make `add_device()` use `_effective_port` while running" fixes a pre-existing latent bug.
- **`stop()`-without-`start()` is already covered.** `test_server.py:335-343` exists; the plan's repeat-safe requirement extends it correctly.

### Concerns

**HIGH — no handling for a host without IPv6, and D-10 forbids a fallback.**
Default-on IPv6 plus atomic startup plus "do not fall back to IPv4-only operation" means that on any host where `socket.socket(AF_INET6, SOCK_DGRAM)` or `bind(("::1", port))` fails — a container with `net.ipv6.conf.all.disable_ipv6=1`, a hardened image, an IPv6-disabled kernel — the stock server no longer starts *at all*, for users who never asked for IPv6. That directly contradicts SPEC constraint line 81 ("The existing public IPv4 behaviour … remain backwards compatible") and Phase 4's CFG-06 ("Library users … see no behaviour change unless they pass the new IPv6 or mDNS options"). The emulator ships as PyApp binaries to user machines, so this is not hypothetical. There is no acceptance criterion, no test, and no requirement for a diagnostic message. This needs an explicit decision surfaced to the user: either an opt-out constructor argument (`ipv6_bind_address: str | None = "::1"`, `None` = IPv4 only), or an accepted, documented hard failure with a message naming the cause.

**HIGH — the shared-port allocation is racy and existing tests do not check the v6 side.**
D-09 has IPv4 allocate the ephemeral port, then binds `[::1]` to that number. IPv4 and V6-only IPv6 sockets occupy separate port spaces, so the OS picks the IPv4 port with no knowledge of what holds `[::1]:N` or `[::]:N`. A collision is a hard, atomic startup failure with no retry. This compounds with the test helpers: `find_free_port()` at `packages/lifx-emulator-core/tests/conftest.py:186-191` (duplicated verbatim at `test_server.py:15-20`) probes **AF_INET only**, so every existing lifecycle test that uses it now silently depends on an unverified v6 port. Across a 10-cell CI matrix this will produce intermittent failures that look like flakes. Add a bounded retry (rebind IPv4 to `0` and try again, N times) for the `port=0` case, and update `find_free_port()` to probe both families.

**MEDIUM — the sibling `_Ipv6EmulatedLifxServer` inherits the new `stop()` but never populates the new live-state fields.**
`lifx-async/tests/conftest.py:302-336` overrides `start()` (setting only `self.transport`) and inherits `stop()` unchanged — the docstring at `:313-316` says so explicitly. Phase 2's `stop()` disables both protocol admissions, drains the tracker and awaits `_ipv4_protocol.wait_closed()` / `_ipv6_protocol.wait_closed()`. On that subclass those fields are `None`. Unless every dereference is guarded, the sibling suite breaks for the whole Phase 2→5 window (removal is Phase 6, per SPEC boundary line 70). AC-15 only asserts the file is *untouched*; untouched is not the same as still working. Add an explicit "subclass overrides `start()`, inherits `stop()`" defensive test to Task 2.

**MEDIUM — Task 3 runs the full suite twice.**
`uv run pytest -q --no-cov` followed by `uv run pytest --cov-fail-under=80 -q` executes 1200+ tests twice, plus `prek run --all-files`. Collapse to one coverage run.

**LOW — AC-02 verification depends on a private attribute.**
Reading `IPV6_V6ONLY` through `server._ipv6_transport` while D-04 keeps it private is acknowledged in the plan, and it matches what `lifx-async/tests/conftest.py:643` already does with `server.transport`. Acceptable, but note that AC-02's proof is therefore not reproducible by an external consumer.

### Suggestions

1. Escalate the IPv6-unavailable-host question to the user before executing this plan. It is a locked-decision consequence (D-10 + default-on) with a real backwards-compatibility cost, and the cheapest resolution — `ipv6_bind_address: str | None` with `None` meaning IPv4-only — costs almost nothing and does not weaken atomicity when IPv6 *is* requested.
2. Add a bounded shared-port retry for `port=0`, and fix `find_free_port()` in both `conftest.py:186` and `test_server.py:15` to probe AF_INET and AF_INET6.
3. Add a Task 2 acceptance criterion: `stop()` is safe on a server whose `start()` was overridden and which therefore has no `_ipv4_protocol`/`_ipv6_protocol`.
4. Drop the duplicate full-suite run in Task 3.

### Risk Assessment

**HIGH.** The socket mechanics are right; the environmental assumptions are not validated, and both gaps land on existing users and existing tests rather than on new code paths.

---

## Cross-Plan Observations

**Dependency ordering is correct and Wave 2 is genuinely parallel-safe.** `02-02` touches only `api/services/event_bridge.py`, `api/app.py`, `tests/test_websocket.py`; `02-03` touches only `devices/manager.py`, `server.py` and three core test modules. With `use_worktrees: true` and `parallelization: true` in `.planning/config.json`, these two worktrees merge cleanly. `background_tasks.py` lands in Wave 1, so both consumers see it.

**The "Artifacts this phase produces" block is duplicated verbatim across all four plans.** It already describes symbols that only 02-04 creates (`ipv6_bind_address`, `_create_ipv6_endpoint`) as artefacts of 02-01. If any plan's design drifts during execution, three stale copies remain. Keep it in 02-04 (or a phase-level file) only.

**HYG-01's stated scope is fully covered, and `StatsBroadcaster` is correctly excluded** — it already holds `self._task` (`event_bridge.py:200`) and cancels-and-awaits at `event_bridge.py:222-233`. No plan claims otherwise; worth stating so a verifier does not flag it.

**No scope creep detected.** The one addition beyond the seven requirements — migrating `EmulatedLifxDevice` persistence to the shared tracker (02-01 Task 2) — is justified by an observed defect and is bounded to one call site.

**Overall risk: MEDIUM-HIGH.** The phase will achieve its goal. Three issues should be resolved before execution starts: the IPv6-unavailable-host decision (02-04), the `accepting=False` / non-lifespan `TestClient` collision (02-02), and the Task 1 verify-command gap that commits a red `test_thread_identity.py` (02-03). The `handle_packet` signature break (02-03) is worth a deliberate decision rather than an implicit one.

---

## OpenCode Review

opencode review failed or returned empty output. stderr:

[spawn error: ETIMEDOUT]

Raw response body:
OpenCode review returned no assistant text (#1936: agent ended its turn with no final message).
Diagnostic: stop reason=tool-calls, output tokens=105
Diagnosis: opencode ran at effort=high and was killed by the outer timeout.

---

## Antigravity Review

# Cross-AI Plan Review: Phase 2 — IPv6 Transport and Thread Isolation

This review evaluates the four implementation plans for Phase 2 against the codebase at `/Volumes/External/Developer/Djelibeybi/lifx-emulator` and the reference client oracle at `/Volumes/External/Developer/Djelibeybi/lifx-async`. All file paths and line citations have been verified directly against repository source files.

---

## 02-01

### Summary
Plan 02-01 establishes the foundational task-lifetime policy (`HYG-01`) and canonical target formatting (`HYG-02`) on the existing IPv4 path prior to creating a second socket. It introduces a reusable owner-local `BackgroundTaskTracker` in `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py`, converts unretained datagram handling in `LifxProtocol.datagram_received` to tracked tasks, replaces the `rstrip("0000")` serial truncation defect in `server.py` with `_format_target()`, and migrates device persistence in `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` to consume task exceptions.

### Strengths
- **Owner-Local Lifecycle Architecture (D-13):** `BackgroundTaskTracker` provides isolated state per component rather than a module-global set, avoiding shared lock contention or cross-component cancellation during component teardown.
- **Coroutines Safely Closed on Refusal (D-14):** At `packages/lifx-emulator-core/src/lifx_emulator/server.py:200-210`, datagram scheduling previously ran bare `create_task`. The tracker pattern explicitly closes passed coroutines when no event loop is running or admission is closed, preventing `RuntimeWarning: coroutine was never awaited` from leaking.
- **Root-Cause Fix for Serial Truncation (HYG-02):** At `packages/lifx-emulator-core/src/lifx_emulator/server.py:404-405`, `target_str = "broadcast" if header.tagged else header.target.hex().rstrip("0000")` stripped legitimate trailing zeroes from serials ending in zero (e.g. `d073d50000000000` became `d073d5`). `_format_target` checks `header.tagged or header.target == b"\x00" * 8` for broadcast and slices `header.target[:6].hex()` for specific serials, preserving exactly 12 lowercase hexadecimal characters.
- **Unconsumed Exception Remediation:** At `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py:189-196`, `_track_save_task` added `task.add_done_callback(self.background_save_tasks.discard)` without calling `task.exception()`. Migrating `_save_state` to the tracker ensures persistence write failures are logged and consumed rather than surfacing as unhandled event-loop warnings.
- **Tracer Execution Order:** Landing task retention and target rendering on IPv4 first ensures that when IPv6 is added in Wave 3, only one correct server scheduling pattern exists.

### Concerns
- **[MEDIUM] Direct protocol test failure if tracker admission defaults closed:**
  - *Location:* `packages/lifx-emulator-core/tests/test_server.py:362-390` (`test_protocol_datagram_received`).
  - *Mechanism:* In `test_server.py`, tests instantiate `protocol = server.LifxProtocol(server)` and immediately call `protocol.datagram_received(packet_data, addr)` without calling `await server.start()`. If `EmulatedLifxServer.__init__` instantiates `BackgroundTaskTracker("server", accepting=False)` (requiring `start()` to open admission), all direct protocol tests in `test_server.py` will discard incoming datagrams.
- **[LOW] Task cancellation during done-callback exception retrieval:**
  - *Location:* `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` (`_on_done` callback).
  - *Mechanism:* In Python asyncio, calling `task.exception()` on a cancelled task raises `asyncio.CancelledError`. If `_on_done` does not guard against `task.cancelled()` before calling `task.exception()`, shutdown cancellation will raise inside the done callback.
- **[LOW] Unhandled `loop.is_closed()` when creating tasks:**
  - *Location:* `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` (`schedule`).
  - *Mechanism:* `asyncio.get_running_loop()` can succeed while the loop is in the process of stopping, causing `loop.create_task(coro)` to raise `RuntimeError("Event loop is closed")`. If `schedule()` does not close `coro` inside a general `except BaseException: coro.close(); raise`, an un-awaited coroutine warning will escape.

### Suggestions
1. Initialize `self._background_tasks = BackgroundTaskTracker("server", accepting=True)` in `EmulatedLifxServer.__init__`, reserving `stop_accepting()` strictly for `server.stop()`.
2. In `BackgroundTaskTracker._on_done(task, operation)`, check `if task.cancelled(): return` prior to invoking `task.exception()`.
3. Wrap `loop.create_task` in `try ... except BaseException: coro.close(); raise` to guarantee coroutine destruction if task creation fails on a closing loop.

### Risk Assessment
**LOW.** The plan addresses isolated hygiene concerns without modifying socket protocols or network wire contracts. All changes are internal to core task scheduling and string formatting.

---

## 02-02

### Summary
Plan 02-02 addresses `HYG-01` in the standalone application package (`packages/lifx-emulator/src/lifx_emulator_app/`). It eliminates the bare `_schedule_async()` helper in `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` and injects an application-owned `BackgroundTaskTracker` into `wire_device_events`, `WebSocketActivityObserver`, and `WebSocketStateChangeObserver`. The tracker's lifecycle and bounded 5-second graceful drain are managed by FastAPI's lifespan in `packages/lifx-emulator/src/lifx_emulator_app/api/app.py`.

### Strengths
- **Elimination of Un-Awaited Coroutine Warnings in Tests:** In `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:30-41`, `_schedule_async` called `loop.create_task(coro)` inside a try/except block. In `packages/lifx-emulator/tests/test_websocket.py:267-320`, unit tests patched `_schedule_async` with a mock while passing real `AsyncMock` coroutines, producing Python un-awaited coroutine warnings. Injecting the tracker replaces arbitrary patching with deterministic task capture.
- **Clean Lifespan Ownership (D-16):** In `packages/lifx-emulator/src/lifx_emulator_app/api/app.py:69-77`, `lifespan` manages background tasks. Adding `try: await stats_broadcaster.stop() finally: await task_tracker.shutdown(timeout=5.0)` guarantees in-flight WebSocket broadcasts are given 5 seconds to drain and are then cancelled before process exit.
- **Diagnostic Transparency:** Exposing `app.state.background_task_tracker` allows test assertions to inspect `pending_count == 0` without fragile `asyncio.sleep()` waits.
- **Operation-Specific Labeling:** Broadcast tasks are labelled with the event type and identifier (e.g. `broadcast_device_added:{serial}`, `broadcast_device_updated:{serial}:{pkt_type}`), pinpointing failing broadcasts in logs.

### Concerns
- **[MEDIUM] Signature breakage with non-default arguments in `WebSocketActivityObserver`:**
  - *Location:* `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:95-106`.
  - *Mechanism:* `WebSocketActivityObserver.__init__(self, ws_manager, inner_observer=None)` has a default argument for `inner_observer`. Adding a required positional parameter `task_tracker` after `inner_observer` creates a Python syntax error (`SyntaxError: non-default argument follows default argument`). Furthermore, existing tests across `packages/lifx-emulator/tests/test_websocket.py` (e.g. lines 216, 230, 245, 262, 280, 312) instantiate `WebSocketActivityObserver` with positional arguments `(mock_ws_manager, mock_inner)`.
- **[LOW] StatsBroadcaster loop unmanaged by tracker:**
  - *Location:* `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py:176-235`.
  - *Mechanism:* `StatsBroadcaster` runs a perpetual loop (`_broadcast_loop`) managed via its own `_task` reference. While the plan correctly notes that `StatsBroadcaster` is stopped prior to tracker drain, its broadcast calls (`await self._ws_manager.broadcast_stats(stats)`) run inline in its loop rather than through `task_tracker`. This is technically sound since it is an awaited loop rather than fire-and-forget, but should be explicitly documented to prevent future contributors from attempting to route it through the short-lived task tracker.

### Suggestions
1. Define `task_tracker` as keyword-only or place it before `inner_observer` with a sensible fallback:
   ```python
   def __init__(
       self,
       ws_manager: WebSocketManager,
       inner_observer: ActivityObserver | None = None,
       *,
       task_tracker: BackgroundTaskTracker | None = None,
   ) -> None:
   ```
   If `task_tracker is None`, create a local fallback tracker to maintain 100% backward compatibility for standalone unit tests.
2. Update `packages/lifx-emulator/tests/test_websocket.py` helper fixtures to supply a dummy or recording `BackgroundTaskTracker` automatically across the suite.

### Risk Assessment
**LOW.** The plan operates entirely within the application layer, decoupling WebSocket broadcast scheduling from global asyncio calls.

---

## 02-03

### Summary
Plan 02-03 implements the core protocol routing and Thread transport isolation requirements (`NET-02`, `NET-03`, `NET-04`). It extends `IDeviceManager.resolve_target_devices` and `DeviceManager.resolve_target_devices` with an optional `family: socket.AddressFamily = socket.AF_INET` parameter (D-07), introduces an immutable `_DatagramContext` containing the socket family, peer address, and originating transport (D-05), reorders packet processing so target resolution precedes all statistics and activity notifications, and anchors all UDP replies to `context.transport` rather than `server.transport` (D-03).

### Strengths
- **Immutability Prevents Cross-Family Contamination (NET-02, D-05):** At `packages/lifx-emulator-core/src/lifx_emulator/server.py:211-235` (`_send_ack`) and lines 259-336 (`_process_device_packet`), responses previously queried `self.transport`. Wrapping `(family, peer, transport)` into a frozen dataclass passed down the call chain guarantees that concurrent IPv4 and IPv6 datagrams never cross-route replies.
- **Side-Effect-Free Thread Isolation (NET-03):** At `packages/lifx-emulator-core/src/lifx_emulator/server.py:342-428`, `packets_received` was incremented, packet types were tallied, and `on_packet_received` was dispatched *before* `resolve_target_devices()` was called. Placing `resolve_target_devices(header, context.family)` immediately after header unpacking ensures that ineligible traffic (such as IPv4 packets or broadcasts aimed at Thread bulbs) returns silently with zero side effects.
- **Strict Matrix Routing in Domain Layer (D-06, D-08):** At `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py:268-290`, Thread devices are retained only if `family == socket.AF_INET6 and not header.tagged and header.target != b"\x00"*8 and header.target[:6].hex() == device.state.serial`. Broadcast packets (`tagged=True` or `target == 0`) filter out Thread devices on both families, fulfilling the LIFX Thread specification.
- **IPv6 Address Formatting:** Introduces bracketed notation (`[::1]:56700`) for IPv6 logging and activity events, preventing ambiguous colons in network address strings.

### Concerns
- **[HIGH] Breaking `server.handle_packet` signature across existing tests:**
  - *Location:* `packages/lifx-emulator-core/src/lifx_emulator/server.py:338` and `packages/lifx-emulator-core/tests/test_server.py`.
  - *Mechanism:* `handle_packet(self, data: bytes, addr: tuple[str, int])` is invoked directly by more than 20 unit tests in `test_server.py` (e.g. lines 89, 114, 144, 178, 208, 269, 298, 417). If `handle_packet` is refactored to require `context: _DatagramContext` instead of accepting an address tuple, all existing tests will raise `TypeError: handle_packet() missing 1 required positional argument: 'context'` unless individually rewritten.
- **[MEDIUM] Signature breakage in direct `_send_ack` and `_process_device_packet` test calls:**
  - *Location:* `packages/lifx-emulator-core/tests/test_thread_identity.py:699, 764, 808, 851, 882`.
  - *Mechanism:* Existing Phase 1 tests directly execute `server._send_ack(device, ack_request, ("::1", 56700))` and `server._process_device_packet(device, header, packet, addr)`. In addition, these tests set `server.transport = recorder`. If `_send_ack` and `_process_device_packet` only inspect `context.transport`, tests passing an address tuple or relying on `server.transport` will fail.
- **[MEDIUM] Regression in `TestMixedFleetThreadAndWifi`:**
  - *Location:* `packages/lifx-emulator-core/tests/test_thread_identity.py:1024-1074`.
  - *Mechanism:* In Phase 1, `TestMixedFleetThreadAndWifi` explicitly asserts `assert len(targets) == 2` for a broadcast query (`tagged=True`) over a manager with 1 WiFi and 1 Thread device. Because Plan 02-03 Task 1 changes `resolve_target_devices` so Thread devices ignore broadcasts, this existing test will fail with `assert 1 == 2`. Task 1 notes that this test should be updated in Task 2, but running the test suite between tasks will yield a failure.

### Suggestions
1. Support backward compatibility in `handle_packet`:
   ```python
   async def handle_packet(
       self,
       data: bytes,
       context_or_addr: _DatagramContext | tuple[str, int],
   ) -> None:
       if isinstance(context_or_addr, _DatagramContext):
           context = context_or_addr
       else:
           # Test fallback: construct synthetic IPv4 context using server.transport
           context = _DatagramContext(
               family=socket.AF_INET,
               peer=context_or_addr,
               transport=self.transport,
           )
   ```
   This prevents breaking existing test harnesses while enforcing `_DatagramContext` on the real protocol path.
2. Similarly allow `_send_ack` and `_process_device_packet` to accept either `_DatagramContext` or synthesize one if passed an address tuple.
3. Update `TestMixedFleetThreadAndWifi` in `test_thread_identity.py` during Task 1 concurrently with the `DeviceManager` changes so the test suite remains green throughout.

### Risk Assessment
**MEDIUM.** The logic correctly implements the required protocol isolation, but changes to core internal methods (`handle_packet`, `_send_ack`, `_process_device_packet`) risk widespread test breakages if backward compatibility helpers are not provided.

---

## 02-04

### Summary
Plan 02-04 completes Phase 2 by implementing the atomic dual-family server lifecycle (`NET-01`, `NET-05`), publishing live endpoint properties (`ipv4_endpoint`, `ipv6_endpoint`), managing protocol closure barriers (`wait_closed`), and proving complete Thread isolation and WiFi dual-family operation on real loopback sockets (`packages/lifx-emulator-core/tests/test_ipv6_transport.py`).

### Strengths
- **True Atomic Dual Bind with `BaseException` Rollback (D-09, D-10):** In `packages/lifx-emulator-core/src/lifx_emulator/server.py:544-550`, `start()` creates IPv4 first, reads the allocated port, and then binds IPv6 to the identical port. Wrapping the startup sequence in `try ... except BaseException:` ensures that cancellations or platform socket errors (such as `EADDRINUSE`) close all intermediate descriptors and re-raise the original error unchanged.
- **Pre-bind `IPV6_V6ONLY` Ordering (NET-01):** Sockets are created via `socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)`, configured with `sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)` prior to `sock.bind()`, made non-blocking, and adopted via `loop.create_datagram_endpoint(sock=...)`. This matches the verified macOS/Linux behavior documented in `/Volumes/External/Developer/Djelibeybi/lifx-async/tests/conftest.py:302-337`.
- **Ephemeral Port Zero Synchronization:** When `port=0`, the allocated ephemeral port from IPv4's `getsockname()` is used for the IPv6 bind and pushed to `device.state.port` across all registered devices. This ensures `StateService` replies from `packages/lifx-emulator-core/src/lifx_emulator/handlers/device_handlers.py:32` advertise the live port rather than `0`.
- **Clean Separation of Public vs Private Surface (D-01, D-02, D-04):** `server.transport` remains the public IPv4 transport alias; `ipv6_endpoint` and `ipv4_endpoint` return `tuple[str, int] | None`; the raw IPv6 transport remains private (`_ipv6_transport`).
- **Comprehensive Loopback Testing:** `test_ipv6_transport.py` exercises real non-blocking `AF_INET` and `AF_INET6` client sockets using `loop.sock_recvfrom` guarded by `asyncio.wait_for`, verifying the Thread bit, dual-family WiFi replies, and side-effect-free Thread drops.

### Concerns
- **[HIGH] Potential hang during `protocol.wait_closed()` with mocked transports:**
  - *Location:* `packages/lifx-emulator-core/src/lifx_emulator/server.py` (`_close_endpoint` and `LifxProtocol.wait_closed`).
  - *Mechanism:* `LifxProtocol.wait_closed()` awaits a future set by `connection_lost()`. In unit tests where `server.transport` is mocked (e.g. `mock_transport = Mock()`), calling `mock_transport.close()` does not invoke `protocol.connection_lost()`. Awaiting `protocol.wait_closed()` without a timeout will deadlock the test runner.
- **[MEDIUM] `test_protocol_connection_made` assertion regression:**
  - *Location:* `packages/lifx-emulator-core/tests/test_server.py:348-360`.
  - *Mechanism:* Line 359 tests `assert server.transport == mock_transport` inside `LifxProtocol.connection_made`. Because D-01 and Plan 02-04 decouple `LifxProtocol.connection_made` from setting `server.transport` (assigning it atomically in `server.start()` instead), `test_protocol_connection_made` will fail unless updated.
- **[LOW] Idempotent start logging:**
  - *Location:* `packages/lifx-emulator-core/src/lifx_emulator/server.py:544` (D-11).
  - *Mechanism:* If `start()` is called while already running, it should log a debug message and return. The plan must ensure it checks both `self.ipv4_endpoint is not None` and `self.ipv6_endpoint is not None` to avoid suppressing a start attempt if the server was left in a half-initialized state.

### Suggestions
1. In `_close_endpoint(transport, protocol)`, wrap the closure wait in a bounded timeout:
   ```python
   if protocol is not None:
       try:
           await asyncio.wait_for(protocol.wait_closed(), timeout=1.0)
       except (asyncio.TimeoutError, Exception):
           logger.debug("Protocol closure wait timed out or failed; proceeding")
   ```
2. Update `test_protocol_connection_made` in `test_server.py` to assert that `LifxProtocol.connection_made` sets `protocol.transport` but does not mutate `server.transport`.
3. In `test_ipv6_transport.py`, explicitly close all test client sockets in a `finally` block or context manager to avoid socket leaks on macOS/Linux test runners.

### Risk Assessment
**MEDIUM.** The core socket mechanics are sound and mirror proven patterns from `lifx-async`. The medium rating reflects the concurrency risks around shutdown barriers (`wait_closed`) and test mock interactions.

---

## Cross-Plan Analysis and Phase Verification

### Dependency Graph and Execution Waves
```text
Wave 1:
  └── 02-01 (BackgroundTaskTracker, _format_target, device persistence)
        │
Wave 2 (parallel):
        ├── 02-02 (FastAPI lifespan, event_bridge injection)
        └── 02-03 (DeviceManager family matrix, _DatagramContext, resolve-before-effects)
              │
Wave 3:
  └── 02-04 (Dual-bind AF_INET6/V6ONLY socket, live endpoints, real loopback tests)
```
- **Ordering Integrity:** The wave structure is logical and strictly adheres to the dependency requirements. Fixing background task tracking (02-01) before proliferating socket protocols (02-04) prevents duplicating broken async patterns.
- **Parallel Independence:** Wave 2 plans (02-02 and 02-03) touch completely disjoint directory trees (`packages/lifx-emulator/` vs `packages/lifx-emulator-core/`), making parallel execution conflict-free.

### Requirements Coverage Matrix

| Requirement | Description | Plans Covering | Status |
| :--- | :--- | :--- | :--- |
| **NET-01** | Dual-bind IPv4 + V6-only IPv6 on shared port | 02-04 | **Covered** |
| **NET-02** | Datagram address-family propagation | 02-03 | **Covered** |
| **NET-03** | Side-effect-free Thread isolation | 02-03, 02-04 | **Covered** |
| **NET-04** | WiFi dual-family request/reply compatibility | 02-03, 02-04 | **Covered** |
| **NET-05** | Public effective endpoint exposure | 02-04 | **Covered** |
| **HYG-01** | Strongly tracked background tasks | 02-01, 02-02, 02-04 | **Covered** |
| **HYG-02** | Exact first-six-byte activity serials | 02-01 | **Covered** |

### Critical Pre-Implementation Checklist
1. **Backward Compatibility Shims:** Ensure `handle_packet`, `_send_ack`, and `_process_device_packet` accept raw address tuples as fallbacks during test suite runs to avoid cascading `TypeError` failures across `test_server.py`.
2. **Shutdown Timeout Guard:** Ensure `protocol.wait_closed()` in `_close_endpoint` cannot hang indefinitely when interacting with mocked transports.
3. **Keyword Arguments for Observer Initialization:** Use `*, task_tracker: BackgroundTaskTracker | None = None` in `WebSocketActivityObserver` and `WebSocketStateChangeObserver` to prevent `SyntaxError` and maintain constructor compatibility.

### Overall Phase Risk Rating
**MEDIUM.** The architectural design is exceptionally clean, adheres directly to locked architectural decisions (D-01 through D-16), and accurately reflects LIFX protocol and Thread hardware behavior. Managing test-suite compatibility during the transition to `_DatagramContext` and ensuring timeout guards on `protocol.wait_closed()` will ensure a seamless implementation.

---

## Consensus Summary

Claude and Antigravity completed full, source-grounded reviews covering all four plans. OpenCode timed out after tool calls without returning assistant text, so its diagnostic stub is preserved above but its verdict is not weighted in this consensus.

### Agreed Strengths

- The dependency order and execution waves are coherent: the IPv4 hygiene tracer lands first, the app and routing work remain parallel-safe, and dual-stack lifecycle work lands last.
- The owner-local background-task tracker and canonical target formatter address verified defects: unretained tasks, unconsumed exceptions, and incorrect target truncation.
- Carrying an immutable per-datagram family/peer/transport context, resolving targets before observable side effects, and sending replies through the originating transport correctly enforce Thread isolation.
- The IPv6 socket mechanics, including pre-bind `IPV6_V6ONLY`, atomic rollback, shared live port, and effective endpoint exposure, are grounded in the sibling `lifx-async` oracle and cover all Phase 2 requirements.

### Agreed Concerns

- Plan 02-03 changes `handle_packet`, `_send_ack`, and `_process_device_packet` call contracts without a clear compatibility strategy. Existing direct callers and many tests pass raw address tuples and rely on `server.transport`; both reviewers recommend preserving a tuple-compatible path or exposing a public context type.
- Plan 02-03 Task 1 changes mixed-fleet broadcast resolution but does not run or update `test_thread_identity.py` in the same atomic task. The task can therefore commit with a known red test before Task 2.
- Closed-by-default tracker admission conflicts with existing direct construction patterns. Core protocol tests call `datagram_received()` without `server.start()`, while app tests often construct `TestClient(app)` without entering the lifespan; scheduled work would be refused unless admission semantics or the tests are changed explicitly.
- The observer/tracker constructor changes in Plan 02-02 need a backward-compatible keyword-only shape. In particular, adding a required argument after the existing defaulted `inner_observer` would be invalid Python, and required parameters would break current call sites.
- Both reviewers identified the existing `test_protocol_connection_made` assertion as a required update when transport ownership moves from `LifxProtocol.connection_made()` to atomic server startup.

### Divergent Views

- Claude rates Plan 02-04 high risk because default-on IPv6 can prevent startup on IPv6-disabled hosts and the IPv4-selected ephemeral port can collide independently in the IPv6 port space. It recommends an explicit compatibility decision and bounded retry. Antigravity rates the socket design medium risk and instead prioritises a timeout around `protocol.wait_closed()` for mocked transports.
- Claude highlights unpinned short-packet statistics semantics and an oversized Plan 02-01 task. Antigravity rates Plan 02-01 low risk and focuses on cancellation-safe exception retrieval and closing coroutines if task creation itself fails.
- For context migration, Claude prefers preserving `handle_packet(data, addr, *, family=AF_INET)` or publishing the context type; Antigravity proposes accepting either the new context or a raw tuple throughout the affected helper chain.
