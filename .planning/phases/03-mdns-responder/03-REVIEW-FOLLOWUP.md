# PR 224 review follow-up — 2026-09-23

Claude's 13 inline comments were published under Djelibeybi's account against `b63e988`. Twelve findings are fixed and hosted CI passed; the user explicitly accepted the confirmed Linux receive-interface limitation on 2026-09-23. Earlier clean review/security/verification reports describe the pre-review checks and do not override these findings.

## Dispositions

| Comment | Finding | Disposition and regression |
|---|---|---|
| [4081630355](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081630355) | Committed removal raises stale discovery error | Preserve deletion result; failure remains observable through status and explicit barrier. `test_committed_removals_survive_degraded_discovery` |
| [4081630571](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081630571) | Retained owner bypasses restart | Finish retained cleanup before opening a new owner; Thread startup cannot skip advertisement. `test_restart_cleans_retained_owner_before_thread_advertisement` |
| [4081630719](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081630719) | Ten-second tombstone misses self-cached PTR | Retain successful service identities until their owner closes, independent of dependency cache TTL. `test_readd_after_wire_ttl_with_delayed_self_cached_ptr` uses a real delayed multicast answer and re-adds after 10.1 seconds. |
| [4081630859](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081630859) | Goodbye for a name never owned | Track ownership after the first public registration stage succeeds. A failed probe is never unregistered; a failed second-stage announcement is cleaned up. Two dedicated ownership regressions. |
| [4081630970](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081630970) | Retry cancellation closes LIFX | Initial-start rollback is owned by `start`; cancellation of WiFi retry cleans only mDNS. `test_cancelled_retry_preserves_lifx_and_real_failure` |
| [4081631134](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631134) | Caller cancellation becomes retained error | Do not record CancelledError as a supported failure. `test_start_cancellation_is_not_a_retained_failure` |
| [4081631316](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631316) | Worker cancellation cancels innocent waiters | Barrier waits for completion without raising the worker's cancellation; interrupted work produces MdnsUpdateError. Committed deletions retain results. |
| [4081631451](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631451) | Packet admission continues during teardown | Close both protocol admission paths before draining mDNS. `test_stop_closes_packet_admission_before_mdns_drain` |
| [4081631588](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631588) | Serial per-change reconciliation backlog | One owned worker consumes the latest lazy snapshot; synchronous bursts build one fleet snapshot and probe concurrently. `test_burst_adds_share_one_reconciliation` |
| [4081631743](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631743) | Linux receive-interface leak | **Confirmed and explicitly accepted by the user.** Isolated Linux reproduction below; documented as AR-06 and in the core README. Public-only zeroconf interface configuration is not a receive security boundary. |
| [4081631876](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081631876) | API listeners survive lifespans | Wiring returns teardown functions; app exit removes listeners and restores callbacks/activity observer it owns. `test_app_lifespans_release_membership_listeners` |
| [4081632001](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081632001) | Retained traceback grows; retry shows stale failure | Raise fresh barrier errors chained to the stored cause, observe task completion without re-raising its exception, and replace last supported failure. Two dedicated regressions. |
| [4081632121](https://github.com/Djelibeybi/lifx-emulator/pull/224#discussion_r4081632121) | Published dependency exact pin | User approved `zeroconf>=0.151.3`; uv.lock remains 0.151.3. Intel packaging derives its exact verification version from the frozen workspace rather than a second literal. |

## Linux scope reproduction

`03-review-evidence/linux-interface-scope.py` uses zeroconf 0.151.3 in an isolated Linux Docker network. The responder joins loopback only. A separate socket represents the host daemon joining the other interface; an ephemeral client sends a legacy-unicast query through that interface. Result:

```json
{"unexpected_reply": true, "query_id_matches": true, "contains_loopback_identity": true}
```

The output omits private addresses. The container published no ports and was removed after execution. Home Assistant likewise configures public `interfaces`/`ip_version` and adds no receive-scope restriction in its zeroconf wrapper; that is a code inspection, not a live Home Assistant reproduction. Its documentation describes choosing broadcast interfaces.

The user chose “Document and accept the limitation” on 2026-09-23. No private dependency access or socket patch is added. AR-06 records that selected interfaces do not guarantee receive isolation; the core README documents the observable behaviour and external isolation option. This is acceptance of the reproduced limitation, not a claim that the leak has been fixed.

## Validation

- Seven initial lifecycle regressions failed against the original code and passed after fixes.
- Combined lifecycle, responder and WebSocket suite: 99 passed.
- Expanded deterministic review suite: 10 passed; delayed-cache wire regression passed separately in 13.13 seconds.
- Configured Pyright: zero errors.
- Full Python 3.10 suite: 1,486 passed, four environment-gated integration skips, 95% coverage. Hosted CI [35862702391](https://github.com/Djelibeybi/lifx-emulator/actions/runs/35862702391) passed at a1308f9: all ten Python/OS jobs, both required production integrations, code quality, spike evidence and Intel PyApp packaging. This closes the validation gate for the twelve fixes; the Linux receive-scope decision is closed by explicit acceptance AR-06.
