# Phase 2 Deferred Items

## Plan 02-01

status: resolved
resolved_at: 2026-09-22
resolution: Fresh full-suite verification passed 1,400 tests with no coroutine warnings after the bridge lifecycle migration.

- The full-suite verification passed with 1,252 tests but retained seven
  pre-existing un-awaited `WebSocketManager.broadcast_device_added` coroutine
  warnings and three related `AsyncMock` coroutine warnings in the standalone
  app tests. Plan 02-02 explicitly owns migration of `event_bridge.py` and its
  WebSocket tests to `BackgroundTaskTracker`; no app-layer files were changed in
  Plan 02-01.

## Plan 02-03 — Test-client dependency

status: unresolved

- The full-suite verification passed all 1,294 tests but emitted one
  pre-existing `StarletteDeprecationWarning` from FastAPI's test client about
  the future `httpx2` transition. Changing the application test-client
  dependency is outside the family-routing files and requires dependency
  research, so it remains deferred rather than being folded into this plan.
## Plan 02-03 — Expected CLI warnings

status: resolved
resolved_at: 2026-09-22
resolution: Confirmed expected compatibility coverage, not a defect.

- Three CLI tests intentionally exercised the deprecated `--persistent` flag
  and emitted the corresponding product deprecation warning. The tests passed;
  this warning is expected coverage of the compatibility path, not a failure.
