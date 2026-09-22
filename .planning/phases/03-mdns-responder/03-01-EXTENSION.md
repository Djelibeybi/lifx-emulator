
> **2026-09-23 amendment:** The user approved complete-fleet discovery independent of packet grouping. See [03-PACKET-GROUPING-AMENDMENT.md](03-PACKET-GROUPING-AMENDMENT.md). Earlier packet-count requirements and zeroconf rejection on aggregation alone are superseded. Historical observations and reviews below remain unchanged; they do not establish compliance with the revised contract. Do not resume the old execution steps or change the local/CI harness under this amendment.

# MDNS-10 constrained follow-up

## Authorisation and scope

On 2026-09-23 the user authorised up to 60 additional active minutes, with the explicit condition: “do not spend any time working on the harness, regardless of whether Local or CI”. This authorisation supersedes the original extension-offer restriction for this follow-up only. It does not authorise production integration or relax the protocol and interface requirements.

Investigation started at 2026-09-22T19:23:51Z from clean commit `830f2e9393d2b30e83f0309fe43e05d73182f7d9`. It stopped early: the remaining implementation and verification would require socket/lifecycle work outside the reusable reply builder, including the prohibited harness work. No harness, tests, workflow, candidate inputs, dependencies, or production code were changed. No CI run was requested. The existing evidence ledger remains the historical result, not a claim that these exploratory observations passed its gates.

## Result

**Provisional hold remains.** No macOS portability fix or dynamic recovery proof was obtained. The time allowance is a ceiling, not a requirement to consume the full hour.

Investigation and write-up closed at 2026-09-22T19:28:24Z (4 minutes 33 seconds elapsed); signing and publishing this documentation follow separately. No queue time was deducted.

The candidate overlay `scripts/mdns_spike_inputs/lifx_direct.py` contains an advertisement type and DNS response materialiser. Socket creation and serving belong to the existing spike runner. The production core has no mDNS responder or `retry_mdns()` implementation. Consequently, discovery and cleanup evidence does not demonstrate a reusable responder lifecycle or recovery. Building that lifecycle is substantive implementation, not merely rerunning a missed test.

## macOS investigation

### A source-backed bind-conflict hypothesis

Apple's published [Darwin 25-family socket bind code](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.121.6/bsd/netinet/in_pcb.c#L1017-L1047) rejects some non-multicast binds when an overlapping socket belongs to a different user. `SO_REUSEPORT` alone does not bypass all these checks; multicast-address binds take a different path. This fits the observed combination of a successful group-address bind and a failed concrete-address reply bind.

Apple's [mDNSResponder socket setup](https://github.com/apple-oss-distributions/mDNSResponder/blob/mDNSResponder-2559.80.8/mDNSMacOSX/mDNSMacOSX.c#L2230-L2234) enables `SO_REUSEPORT`. That does not establish permission for every second socket binding pattern. The source versions are published reference code, not a verified match to the hosted runner's installed binaries.

Local read-only process inspection found mDNSResponder running as `_mdnsresponder` and ESPHome's Python process running as the current user. Local `lsof` showed that Python process already holding concrete IPv4 UDP 5353 sockets, including loopback and the selected physical interface. An existing same-user binding could affect Darwin's conflict lookup and help explain why local success differs from hosted macOS. **This remains a hypothesis:** the hosted socket owners/options and kernel lookup were not captured, and no daemon or existing process was stopped.

The earlier ledger's wording that mDNSResponder “prevented” the bind is stronger than the captured evidence warrants. The confirmed hosted observation is `EADDRINUSE` during the scoped reply-source bind; the precise conflicting socket and kernel branch remain unconfirmed.

### Rejected local alternative: group socket plus IP_PKTINFO

The macOS SDK documents `IP_PKTINFO` (26) for selecting a packet's source address/interface. A direct, disposable socket experiment tried replying from a socket bound to `224.0.0.251:5353`, with `IP_BOUND_IF` (25), `SO_REUSEADDR`, and `SO_REUSEPORT`. The destination was an ephemeral socket on the same machine. No discovery query or advertisement was sent to the LAN. Both sockets were closed by context managers after each attempt.

The command used `UV_CACHE_DIR=/tmp/lifx-extension-uv-cache uv run --no-project python` with inline diagnostic code; no reusable test or harness was created or modified. Ancillary data used `struct.pack('=I4s4s', ifindex, local_address, bytes(4))`. It tested source-address selection with index zero and interface selection with the real interface index.

| Local interface | Ancillary selection | Result |
| --- | --- | --- |
| `lo0` | Source address | `EADDRNOTAVAIL` (49) |
| `lo0` | Interface index | `EADDRNOTAVAIL` (49) |
| `en0` | Source address | `EADDRNOTAVAIL` (49) |
| `en0` | Interface index | `EADDRNOTAVAIL` (49) |

The local OS was macOS 27.0 build `26A428`; the existing hosted receipt records Darwin 25.6.0. These local failures do not substitute for hosted evidence.

Apple's [UDP output code](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/netinet/udp_usrreq.c#L1708-L1770) checks whether the bound source address exists before applying the ancillary temporary source. A multicast group is not an assigned local interface address. This source path is consistent with the observed failure and rejects this simple proposed workaround on the tested host.

## Limits and disposition

- No successful new wire response, discovery run, recovery cycle, or production status integration was demonstrated.
- No wildcard fallback, ephemeral response-source port, privileged responder, daemon shutdown, or network reconfiguration was attempted.
- Reading the old CI log hit a local `gh` cache permission failure; no CI/harness repair was undertaken. Reading privileged daemon socket details with `sudo -n` required a password; no password or system modification was requested. Unprivileged socket inventory and an authorised read-only process listing supplied the local observations above.
- Existing source and CI evidence remain unchanged. Zeroconf remains rejected under the per-device packet contract; the direct candidate remains provisional. Neither a production go nor an overall no-go is justified by this follow-up.
- Further progress requires an explicit change in scope: a standalone responder lifecycle and a proven macOS socket strategy, with verification of that implementation. Another general spike extension is not recommended on the present evidence.
