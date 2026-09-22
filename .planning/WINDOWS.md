---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 2
total_count: 3
last_updated: 2026-09-22T17:23:25.430Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | deviation | packages/lifx-emulator-core/src/lifx_emulator/server.py |  | Task 1 corrected draft retry and diagnostics so only IPv6-stage EADDRINUSE can retry a port-zero pair. | fixed |  | 2026-09-10T08:06:07.065Z | 2026-09-10T08:06:48.391Z |
| 2 | 02 | deviation | .planning/phases/02-ipv6-transport-and-thread-isolation/02-04-SUMMARY.md |  | Task 3 was test-only and passed immediately, so no fabricated TDD RED or unrelated GREEN change was introduced. | fixed |  | 2026-09-10T08:06:07.232Z | 2026-09-10T08:06:48.561Z |
| 3 | 03 | unrun-verify | .planning/phases/03-mdns-responder/03-01-EVIDENCE.json |  | Exact-head hosted macOS arm64 could not send the first IPv4 multicast query (errno 65); repeat on a multicast-capable disposable macOS executor. | open |  | 2026-09-22T17:23:25.430Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "02",
    "file": "packages/lifx-emulator-core/src/lifx_emulator/server.py",
    "line": null,
    "description": "Task 1 corrected draft retry and diagnostics so only IPv6-stage EADDRINUSE can retry a port-zero pair.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-10T08:06:07.065Z",
    "resolved_at": "2026-09-10T08:06:48.391Z"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "02",
    "file": ".planning/phases/02-ipv6-transport-and-thread-isolation/02-04-SUMMARY.md",
    "line": null,
    "description": "Task 3 was test-only and passed immediately, so no fabricated TDD RED or unrelated GREEN change was introduced.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-10T08:06:07.232Z",
    "resolved_at": "2026-09-10T08:06:48.561Z"
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "03",
    "file": ".planning/phases/03-mdns-responder/03-01-EVIDENCE.json",
    "line": null,
    "description": "Exact-head hosted macOS arm64 could not send the first IPv4 multicast query (errno 65); repeat on a multicast-capable disposable macOS executor.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-22T17:23:25.430Z",
    "resolved_at": null
  }
]
````
