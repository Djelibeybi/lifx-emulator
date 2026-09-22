# Phase 3 packet-grouping amendment

**Approved:** 2026-09-23, by the user's agreement with the recommendation to replace the one-packet-per-device requirement.
**Status:** Direct local zeroconf re-evaluation found all 100 devices with correct records and representative control. Question echo on continuation packets and remaining gates keep the choice provisional. See [03-ZEROCONF-REEVALUATION.md](03-ZEROCONF-REEVALUATION.md).

## Current contract

MDNS-03 and AC-04 require complete, correct discovery of every eligible advertised device. Each device retains its own identity, PTR/SRV/TXT associations, hostname, actual LIFX port and matching-family address. Replies may aggregate multiple devices, and discovery may accumulate records across multiple packets. Packet count, packet order and device-to-packet boundaries are not acceptance criteria.

A fleet must not lose devices or acquire an artificial size limit because its records exceed one datagram. Existing benchmark populations of 1, 10 and 100 remain evidence samples, not a supported-device cap. Missing records or devices caused by truncation still fail completeness. Legacy-unicast protocol behaviour, explicit advertised addresses, Thread AAAA-only/WiFi A-only records, lifecycle, coexistence and packaging requirements remain in force.

The earlier whole-fleet-single-packet assumption and the subsequent one-packet-per-device rule are both superseded. The client accumulates DNS records across packets. [RFC 6762 section 6.4](https://www.rfc-editor.org/rfc/rfc6762.html#section-6.4) recommends aggregation where possible; aggregation alone is not a protocol failure or evidence of lost devices.

## Effect on existing results

- Zeroconf's mixed-fleet packet-count rejection no longer disqualifies it. Reopen zeroconf first under the existing candidate preference/order. Do not infer complete public-client discovery merely from the two observed datagrams or convert historical diagnostic observations into a new pass.
- The direct lifx-async prototype and its macOS/recovery limitations remain useful historical evidence. It is not the selected foundation, and its socket limitations must not be attributed to zeroconf without evidence.
- Avahi and Ciao source findings about aggregation alone no longer disqualify those approaches. Their observed source paths for dropping/truncating legacy-unicast records remain relevant completeness risks, not completed candidate tests or automatic approvals. This amendment does not add a new candidate implementation effort.
- `03-01-EVIDENCE.json`, its rendered Markdown, frozen inputs and test results remain unchanged records of the old contract. The old validator's acceptance is not validation of the amended contract. This document governs the interpretation of those historical decisions.
- Historical plan, research, pattern, review, summary and extension documents carry a supersession notice. Their original conclusions are preserved for traceability, not instructions to enforce packet isolation again.

## Continuation boundary

The user's no-local-or-CI-harness-work condition remains in force. This approval changes the requirement and candidate eligibility; it does not authorise harness changes, a fresh timed spike, production integration, VM provisioning or a merge. Do not resume the old plan's harness-building steps automatically.

The next evaluation must establish complete discovery against the amended contract, using existing evidence where it actually proves the criterion and direct checks where needed. Any remaining evidence gap must remain explicit. MDNS-10 and the remaining Phase 3 requirements stay incomplete until a supported foundation decision is recorded.

On 2026-09-23 the user subsequently authorised the proposed direct 100-device experiment. That bounded task is complete and recorded in `03-ZEROCONF-REEVALUATION.md`; the no-harness-work condition was retained.
