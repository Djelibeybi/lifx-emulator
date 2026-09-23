# Phase 3: mDNS Responder - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Transcription:** Spelling normalised in quoted user responses; meaning preserved.

**Date:** 2026-09-22; runtime failure scope amended 2026-09-23
**Phase:** 03-mdns-responder
**Areas discussed:** Library configuration; failure visibility and recovery; spike execution; supported runtime failure detection

## Runtime failure scope amendment — 2026-09-23

| Option | Description | Selected |
|--------|-------------|----------|
| Upstream failure callback | Preserve direct listener-loss notification by obtaining an upstream public API and release; alternatively maintain a patch/fork/vendor copy. | |
| Responsiveness watchdog | Treat repeated unanswered discovery probes as failure; requires false-positive and timing policy. | |
| Narrow the guarantee | Handle failures surfaced by supported operations without guaranteeing silent listener-loss detection. | Yes |

**Discussion:** The user asked what an upstream callback would look like and pointed out that it depends on upstream acceptance or vendoring. The initial callback recommendation understated that dependency. The revised recommendation was to narrow D-08 for the emulator's test-oriented use case.

**User's choice:** “I think that's better for this use-case which is non-production and test-oriented, so well suited for others to report things like this”. This accepts the narrower guarantee. Startup failure, observable runtime errors, owned cleanup and explicit retry remain covered; silent listener loss is an accepted detection limitation. No watchdog, private inspection or library fork/patch is selected.

**Recorded consequence:** D-08 retains fleet-dependent handling of observed failures. `running` is lifecycle status rather than a fresh network-health assertion. The detection decision is resolved; remaining spike evidence and the explicit MDNS-10 go/no-go are not waived.

## Library configuration

### Where should mDNS configuration live?

| Option | Description |
|--------|-------------|
| 1 | Alongside existing device and server settings (recommended) |
| 2 | Centralised on server in a mapping keyed by serial |

**User’s choice / recorded decision:** 1: Device settings in factories; server controls mDNS enablement.

### Which argument names do you prefer?

| Option | Description |
|--------|-------------|
| 1 | Explicit mDNS names (recommended) |
| 2 | Shorter names: server mdns; factories advertise_mdns and advertise_address |

**User’s choice / recorded decision:** 1: Server mdns_enabled=False; factories mdns_enabled=True and mdns_address=None.

### When should invalid device settings raise an error?

| Option | Description |
|--------|-------------|
| 1 | As early as possible (recommended) |
| 2 | All validation when attached to a server |

**User’s choice / recorded decision:** 1: Factories reject invalid addresses, wrong address families and Thread opt-out immediately. Server startup validates bind-dependent settings; device addition validates before registration.

### Should a device's mDNS settings be changeable after creation?

| Option | Description |
|--------|-------------|
| 1 | Fixed at creation (recommended) |
| 2 | Changeable while unregistered |

**User’s choice / recorded decision:** 1: Fixed at creation. Remove and recreate a device to change its advertised address or WiFi opt-out.

## Failure visibility and recovery

### How should callers detect mDNS failure?

| Option | Description |
|--------|-------------|
| 1 | Status properties plus logging (recommended) |
| 2 | Status properties, logging and a callback |
| 3 | Logging only |

**User’s choice / recorded decision:** 1: Read-only mdns_status (disabled, stopped, running, failed) and mdns_error properties, plus failure logging.

### How should a WiFi-only server recover after mDNS startup fails?

| Option | Description |
|--------|-------------|
| 1 | Explicit mDNS retry (recommended) |
| 2 | Full server restart |
| 3 | Automatic retry with bounded backoff |

**User’s choice / recorded decision:** 1: Explicit await server.retry_mdns() without interrupting LIFX traffic.

### If enabled mDNS has failed, what happens when a caller adds a Thread device?

| Option | Description |
|--------|-------------|
| 1 | Reject the addition (recommended) |
| 2 | Retry mDNS during addition and add only on success |

**User’s choice / recorded decision:** 1: Reject the addition before changing the fleet, explaining that mDNS must be recovered first. Intentionally disabled mDNS remains supported.

### If mDNS fails after successful startup, how should the server respond?

| Option | Description |
|--------|-------------|
| 1 | Apply the same fleet rule (recommended) |
| 2 | Keep LIFX running for every fleet and allow explicit retry |

**User’s choice / recorded decision:** 1: Apply the same fleet rule. WiFi-only continues with failed status; Thread-only or mixed fleets shut down cleanly and retain failure details.

## Spike execution

### Should the spike test running lifx-emulator and lifx-async on different machines or VMs?

**User’s choice / recorded decision:** Only if the additional four-hour extension is warranted under the agreed documentation-backed evidence criterion, and time permits after required evidence, define/build the VM and run cross-machine feasibility tests. This work must not occur within the initially budgeted four hours and does not itself automatically justify an extension. Use separate hosts on the same multicast-capable network.

**User’s wording:** If time permits, we should test the feasibility of running lifx-emulator and lifx-async on different machines/VMs

**Later correction (takes precedence):** This should only occur if the additional 4 hours are warranted. It should not happen in the initially budgeted 4 hours

### What should the cross-machine check demonstrate?

| Option | Description |
|--------|-------------|
| 1 | Discovery and control (recommended) |
| 2 | Discovery only |

**User’s choice / recorded decision:** 1: Discovery, state queries and light control through advertised endpoints.

### Which machines or VMs should the spike use?

| Option | Description |
|--------|-------------|
| 1 | Identify suitable existing hosts during the spike (recommended) |
| 2 | Use specific hosts |

**User’s choice / recorded decision:** 2: devproxmox.lot209.xyz is a Proxmox VE host used for development.

### How should the optional test use the Proxmox host?

| Option | Description |
|--------|-------------|
| 1 | Mac client, Proxmox guest emulator (recommended) |
| 2 | Two Proxmox guests |
| 3 | Both topologies if time permits |

**User’s choice / recorded decision:** 1: Run lifx-async on the Mac and lifx-emulator in a Proxmox guest.

### How should the guest be selected?

| Option | Description |
|--------|-------------|
| 1 | Inspect existing guests first (recommended) |
| 2 | Use a specific guest |

**User’s choice / recorded decision:** There are no usable guests on the host; define and build a new guest.

**User’s wording:** There are no usable guests on the box yet, so we'll have to define and build one

### Which guest type should we plan?

| Option | Description |
|--------|-------------|
| 1 | Small Linux VM (recommended) |
| 2 | Unprivileged Linux container |

**User’s choice / recorded decision:** 1: A small Linux VM with its own kernel and network stack. Define resources and network configuration before building. VM definition, provisioning and cross-machine testing are extension-only work, excluded from the initial four-hour budget.

### How should existing lifx-async mDNS code be considered?

| Option | Description |
|--------|-------------|
| 1 | Evaluate both locations (recommended) |
| 2 | Extend lifx-async directly |
| 3 | Keep runtime code in the emulator |

**User’s choice / recorded decision:** Evaluate candidates in order: python-zeroconf via public APIs and a small adapter; extending or augmenting existing lifx-async mDNS; an entirely new responder only if neither existing implementation is suitable. Compare extending lifx-async directly with adapting its relevant code into the emulator, considering coupling, maintenance and compatibility.

**User’s wording:** If python-zeroconf isn't suitable, the spike should consider extending/augmenting the mDNS implementation that already exists in lifx-async before creating an entirely new implementation. Integration approach: 1.

### Should the original timebox cover all three candidates?

| Option | Description |
|--------|-------------|
| 1 | Shared budget (recommended) |
| 2 | Separate fallback budget |

**User’s choice / recorded decision:** 1: Shared four-hour active-work budget, extendable to eight with documentation-backed justification. Stop investigating a candidate when decisive evidence rules it out.

### What fleet sizes should the spike use for performance comparisons?

| Option | Description |
|--------|-------------|
| 1 | 1, 10 and 100 devices (recommended) |
| 2 | Also include 1,000 devices |
| 3 | User-provided expected fleet size |

**User’s choice / recorded decision:** 1: Benchmark mixed fleets of 1, 10 and 100 devices, comparing discovery latency, CPU and memory. These sizes are benchmarks, not supported fleet limits.

### If candidates trade discovery speed against resource use, which should carry more weight?

| Option | Description |
|--------|-------------|
| 1 | Discovery latency (recommended) |
| 2 | Resource efficiency |
| 3 | No preset priority |

**User’s choice / recorded decision:** 1: Prioritise how quickly lifx-async discovers the complete fleet, while recording CPU and memory costs.

### What timebox should the comparison have?

| Option | Description |
|--------|-------------|
| 1 | Four hours of active work (recommended) |
| 2 | Two hours |
| 3 | Eight hours |

**User’s choice / recorded decision:** Four hours of active work initially, excluding separately recorded CI queue time. Up to eight hours is possible if initial findings show the extra time would be well spent on a deeper, more performant or more feature-complete implementation within Phase 3 scope. The extension rationale requires documentation links and exact line references; for unnumbered pages, use version-pinned documentation source line references.

**User’s wording:** 1 but 3 is possible if 1 reveals evidence that the time would be well spent on creating a deeper, more performant or more feature-complete implementation. Links to and line numbers from the documentation required for this

### If both candidates meet the locked requirements, how should we choose?

| Option | Description |
|--------|-------------|
| 1 | Prefer python-zeroconf (recommended) |
| 2 | Compare measured performance first |
| 3 | Prefer the narrower implementation |

**User’s choice / recorded decision:** 1: Prefer python-zeroconf unless evidence demonstrates a material advantage for a custom responder.

### If a required platform or packaging check cannot run within the spike, what should happen?

| Option | Description |
|--------|-------------|
| 1 | Record a provisional choice; hold implementation (recommended) |
| 2 | Allow conditional implementation |

**User’s choice / recorded decision:** 1: Record a provisional choice and hold implementation. Identify missing evidence and how to obtain it; confirm go/no-go once required checks run.

### If python-zeroconf needs internal API access or patches to meet the requirements, what is acceptable?

| Option | Description |
|--------|-------------|
| 1 | Public APIs and a small adapter (recommended) |
| 2 | Limited private API use |
| 3 | A maintained fork |

**User’s choice / recorded decision:** 1: Public APIs and a small adapter. Reliance on private internals, monkey-patching or a maintained fork favours the custom responder.

## Agent discretion

No explicit discretionary decisions were delegated. Routine details remain for research and planning.

## Deferred ideas

No new future-phase capability adopted. Cross-machine feasibility work is optional and restricted to a justified extension.

## Completion

The user reviewed the combined decisions and selected “Ready for context”: write and commit the phase context and discussion record.
