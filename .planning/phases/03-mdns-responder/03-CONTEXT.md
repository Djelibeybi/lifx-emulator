# Phase 3: mDNS Responder - Context

**Amended 2026-09-23:** Packet grouping is unrestricted subject to complete-fleet discovery; zeroconf re-evaluation is pending. See [03-PACKET-GROUPING-AMENDMENT.md](03-PACKET-GROUPING-AMENDMENT.md).

**Accepted compatibility exception (2026-09-23):** Zeroconf continuation replies may omit the question section for the tested `lifx-async` client. This does not block candidate selection and requires no client/library patch; it is not a claim of full RFC conformance. All other protocol and evidence requirements remain in force. See [03-ZEROCONF-REEVALUATION.md](03-ZEROCONF-REEVALUATION.md).

**Gathered:** 2026-09-22
**Status:** Ready for spike planning; detailed responder planning awaits go/no-go

<domain>
## Phase Boundary

Add opt-in core mDNS discovery for emulated WiFi and Thread devices. Plan the implementation-selection spike first; the remaining responder work depends on its evidence and decision.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** Downstream agents MUST read `.planning/phases/03-mdns-responder/03-SPEC.md` before planning or implementing. Requirements are not duplicated in the decisions below.

**In scope (from SPEC.md):**

- Core responder and configuration surface required to enable it and supply advertisement settings.
- Complete discovery of every advertised device from correctly associated DNS-SD records, with legacy-unicast response behaviour; packet aggregation and multiple reply packets are permitted.
- Address validation, WiFi opt-out, live device membership and non-displacing event listeners.
- Conditional startup failure, shutdown ownership, the implementation-selection spike and focused discovery tests.
- Corrections to MDNS-03 and Phase 3 roadmap criteria accompanying this specification.

**Out of scope (from SPEC.md):**

- Dropping eligible devices or imposing a fleet-size limit because their combined records exceed one packet. Packet aggregation itself is permitted.
- CLI flags, YAML, export-config and standalone default enablement — Phase 4.
- Management API models and validation responses — Phase 5.
- Dashboard controls — excluded from this milestone.
- Full sibling-suite migration and removal of its IPv6 test subclass — Phase 6; the spike's client discovery check remains in scope here.
- Border-router topology, delayed reappearance and stale-advertisement timing — deferred by the milestone.
- IPv6 mDNS multicast and IPv6 tagged LIFX discovery — excluded by the milestone.
- Automatic interface/address selection and advertised link-local addresses — rejected during this interview.
- Changes to the existing IPv6 transport default, generated protocol files or unrelated local configuration changes.

**Discussion refinement:** The user expanded the spike's candidate comparison to consider extending or augmenting existing `lifx-async` mDNS code before an entirely new responder. This refines MDNS-10's comparison without relaxing any acceptance criteria. The optional cross-machine experiment is extension-only feasibility work, not a new required acceptance gate.
</spec_lock>

<decisions>
## Implementation Decisions

### Library configuration

- **D-01:** Keep device advertisement settings in existing factories and server enablement in `EmulatedLifxServer`, preserving existing calls.
- **D-02:** Server argument: `mdns_enabled=False`. Factory arguments: `mdns_enabled=True` and `mdns_address=None`. Device advertisement settings apply when server mDNS is enabled; `None` uses the spec's concrete bind-address fallback.
- **D-03:** Validate as early as possible. Factories reject invalid addresses, wrong families and Thread opt-out immediately. Server startup checks bind-dependent settings; adding a device checks them before registration.
- **D-04:** Device mDNS settings are fixed at creation, like connectivity. Changing the address or WiFi opt-out requires removing and recreating the device.

### Failure visibility and recovery

- **D-05:** Expose read-only `mdns_status` with `disabled`, `stopped`, `running` and `failed` states, plus `mdns_error`; log failures. No status callback was selected.
- **D-06:** Provide explicit `await server.retry_mdns()` to recover failed mDNS on a functioning WiFi-only server without interrupting LIFX traffic. Automatic retries were not selected.
- **D-07:** When enabled mDNS has failed, reject Thread device additions before changing fleet membership, explaining that mDNS must recover first. Intentionally disabled mDNS remains supported.
- **D-08:** Apply the fleet-dependent failure policy to runtime failure too: WiFi-only continues serving LIFX with failed mDNS status; Thread-only and mixed fleets shut down cleanly and retain the failure details.

### Spike candidates and evidence

- **D-09:** Evaluate in order: current `python-zeroconf`; extending or augmenting existing `lifx-async` mDNS; an entirely new responder if neither existing implementation is suitable. Stop investigating a candidate once decisive evidence rules it out.
- **D-10:** Prefer `python-zeroconf` when candidates meet the locked requirements, unless evidence demonstrates a material advantage for an alternative. Use public APIs and a small adapter; dependence on private internals, monkey-patching or a maintained fork favours the fallback candidates.
- **D-11:** For `lifx-async` reuse, compare extending that library directly with adapting relevant code into the emulator. Recommend based on coupling, maintenance and compatibility; neither location is preselected.
- **D-12:** Missing required platform or packaging evidence leaves the choice provisional and holds responder implementation. Record the missing evidence and how to obtain it; confirm go/no-go when required checks run. Do not plan the remaining ten requirements in detail before that decision.
- **D-13:** Benchmark mixed fleets of 1, 10 and 100 devices. Prioritise time for `lifx-async` to discover the complete fleet, recording CPU and memory costs. These are benchmark sizes, not supported fleet limits.

### Spike budget and optional cross-machine experiment

- **D-14:** Share an initial four-hour active-work budget across all candidates; record CI queue time separately. An additional four hours is possible only when initial findings show worthwhile implementation depth, performance or feature completeness within Phase 3 scope. At the limit, record findings and unresolved evidence before proceeding.
- **D-15:** Justify any extension with concrete evidence, documentation links and exact line references. For unnumbered documentation pages, provide version-pinned documentation source links and line numbers. The potential availability of extra time alone does not justify using it.
- **D-16:** Only within a warranted extension, and if time remains after required evidence, test separate-machine feasibility: `lifx-async` on the Mac and `lifx-emulator` in a guest on development Proxmox VE host `devproxmox.lot209.xyz`, on the same multicast-capable network.
- **D-17:** The user reports no usable existing guests. Define and build a small Linux VM with its own kernel/network stack; define resources and network configuration before provisioning. **VM definition, provisioning and cross-machine testing must not occur in the initial four hours.**
- **D-18:** The optional experiment must cover discovery, state queries and light control through advertised endpoints. It is not grounds to extend the spike automatically and does not replace required protocol, coexistence or packaging evidence.

### Agent discretion

No explicit discretionary decisions were delegated. Routine internal implementation details remain for research and planning within these decisions; the responder choice remains evidence-gated.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** Paths are relative to the repository root.

### Requirements and prior decisions

- `.planning/phases/03-mdns-responder/03-SPEC.md` — locked requirements and acceptance criteria.
- `.planning/PROJECT.md` — project constraints and sibling-client relationship.
- `.planning/REQUIREMENTS.md` — milestone requirement mapping.
- `.planning/ROADMAP.md` — phase dependencies and boundaries.

### Core integration and packaging

- `packages/lifx-emulator-core/src/lifx_emulator/server.py` — dual-family endpoint lifecycle and server configuration.
- `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` — owned task tracking and bounded shutdown.
- `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` — live membership and existing callback contracts.
- `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` — device configuration and connectivity.
- `packages/lifx-emulator-core/src/lifx_emulator/factories/factory.py` and `packages/lifx-emulator-core/src/lifx_emulator/factories/builder.py` — published factory surfaces.
- `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` — existing WebSocket membership callback consumer.
- `.github/workflows/ci.yml` and `.github/workflows/release-binaries.yml` — platform tests and Intel macOS PyApp build configuration.

### Sibling mDNS implementation

- `../lifx-async/src/lifx/network/discovery/mdns/discovery.py` — discovery oracle and record accumulation.
- `../lifx-async/src/lifx/network/discovery/mdns/dns.py` — DNS code to assess for reuse.
- `../lifx-async/src/lifx/network/discovery/mdns/transport.py` — existing transport to assess.
- `../lifx-async/src/lifx/network/discovery/mdns/types.py` — existing record types.

### Research starting points

- https://python-zeroconf.readthedocs.io/en/latest/api.html — public asyncio API; verify the current release during the spike.
- https://ofek.dev/pyapp/latest/config/distribution/ — packaging distribution configuration.
- https://ofek.dev/pyapp/latest/build/ — PyApp build guidance.

These links are starting points, not completed feasibility evidence or justification for a timebox extension.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets and established patterns

- Server endpoint properties provide a precedent for read-only mDNS status.
- The dual-family server owns sockets and background tasks; preserve its atomic startup, rollback and repeated-lifecycle behaviour.
- Factories already expose connectivity and advertised services; preserve their published argument compatibility.
- DeviceManager currently has single add/remove callbacks. Multi-listener integration must preserve the existing WebSocket consumer and its exception behaviour.
- The sibling client's record cache accumulates records across packets. Reuse must be assessed from source; client discovery code is not assumed to already implement a responder.

### Integration points

Server start/stop and retry, factory/device validation, pre-registration membership checks, non-displacing membership listeners, and the existing packaging workflow are the main connection points.
</code_context>

<specifics>
## Specific Ideas

The initial spike must remain focused on the required implementation-selection evidence. The separate-machine experiment requires a new development VM and is explicitly reserved for a justified extension.
</specifics>

<deferred>
## Deferred Ideas

No additional future-phase capability was adopted. Cross-machine testing remains optional extension-only spike work; full sibling-suite migration stays in Phase 6.
</deferred>

---
*Phase: 03-mdns-responder*
*Context gathered: 2026-09-22*
