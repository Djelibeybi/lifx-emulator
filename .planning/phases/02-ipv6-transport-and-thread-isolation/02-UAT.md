---
status: complete
phase: 02-ipv6-transport-and-thread-isolation
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md]
started: 2026-09-22T09:39:10Z
updated: 2026-09-22T09:39:10Z
---

## Current Test

[testing complete]

All 16 deliverables are automatically covered. The user approved the confirmation summary on 2026-09-22 after the fresh full-suite run and the fixes described below.

## Tests

### 1. Server packet work remains strongly retained across forced garbage collection, replies exactly once, consumes all terminal outcomes, and drains under bounded shutdown.
expected: Server packet work remains strongly retained across forced garbage collection, replies exactly once, consumes all terminal outcomes, and drains under bounded shutdown.
result: pass
source: automated
coverage_id: 02-01/D1
verification: packages/lifx-emulator-core/tests/test_background_tasks.py::TestBackgroundTaskTracker; packages/lifx-emulator-core/tests/test_server.py::TestProtocolClass::test_protocol_datagram_received

### 2. Device persistence uses an owner-local labelled tracker; successful and failed saves execute once without retained work or un-awaited-coroutine warnings.
expected: Device persistence uses an owner-local labelled tracker; successful and failed saves execute once without retained work or un-awaited-coroutine warnings.
result: pass
source: automated
coverage_id: 02-01/D2
verification: packages/lifx-emulator-core/tests/test_device.py::TestDeviceBackgroundPersistence; uv run pytest test_background_tasks.py test_device.py test_async_storage.py test_thread_identity.py (140 passed)

### 3. Unknown warnings, normal RX logs, and PacketEvent activity preserve all 12 serial digits and render tagged/all-zero targets as broadcast.
expected: Unknown warnings, normal RX logs, and PacketEvent activity preserve all 12 serial digits and render tagged/all-zero targets as broadcast.
result: pass
source: automated
coverage_id: 02-01/D3
verification: packages/lifx-emulator-core/tests/test_server.py::TestErrorHandling::test_unknown_target_preserves_all_twelve_hex_digits; packages/lifx-emulator-core/tests/test_server.py::TestErrorHandling::test_unknown_target_broadcast_forms_match_all_surfaces

### 4. Short and header-unparsable datagrams count one receive/error with no type/activity, while payload-unparsable datagrams count receive/type without changing errors or activity.
expected: Short and header-unparsable datagrams count one receive/error with no type/activity, while payload-unparsable datagrams count receive/type without changing errors or activity.
result: pass
source: automated
coverage_id: 02-01/D4
verification: packages/lifx-emulator-core/tests/test_server.py -k 'too_short or unparsable'; Plan 02-01 focused suite (180 passed) and full repository suite (1252 passed)

### 5. All five synchronous event-bridge operation families schedule unchanged WebSocket payloads through injected or adapter-local trackers with exact labels and preserved delegate order.
expected: All five synchronous event-bridge operation families schedule unchanged WebSocket payloads through injected or adapter-local trackers with exact labels and preserved delegate order.
result: pass
source: automated
coverage_id: 02-02/D1
verification: packages/lifx-emulator/tests/test_websocket.py::TestEventBridge; uv run --frozen pytest packages/lifx-emulator/tests/test_websocket.py -q --no-cov -k 'event_bridge or activity_observer or state_change' (12 passed)

### 6. Forced collection loses no device-added broadcast, failures are consumed and logged once, and completed work leaves no retained tasks or un-awaited coroutine warnings.
expected: Forced collection loses no device-added broadcast, failures are consumed and logged once, and completed work leaves no retained tasks or un-awaited coroutine warnings.
result: pass
source: automated
coverage_id: 02-02/D2
verification: packages/lifx-emulator/tests/test_websocket.py::TestEventBridge::test_device_added_bridge_survives_forced_collection; packages/lifx-emulator/tests/test_websocket.py::TestEventBridge::test_activity_delegate_precedes_schedule_and_failure_is_logged_once

### 7. One open app-owned tracker is shared by every adapter; non-lifespan construction accepts work while normal, exceptional, and repeated lifespans stop stats first and drain or cancel all bridge work.
expected: One open app-owned tracker is shared by every adapter; non-lifespan construction accepts work while normal, exceptional, and repeated lifespans stop stats first and drain or cancel all bridge work.
result: pass
source: automated
coverage_id: 02-02/D3
verification: packages/lifx-emulator/tests/test_websocket.py::TestEventBridgeLifespan; uv run --frozen pytest packages/lifx-emulator/tests/test_websocket.py packages/lifx-emulator/tests/test_api.py -q --no-cov (123 passed); uv run --frozen pytest -q --no-cov (1263 passed)

### 8. Interleaved IPv4 and IPv6 datagrams retain their own family through public target resolution and cannot cross reply transports.
expected: Interleaved IPv4 and IPv6 datagrams retain their own family through public target resolution and cannot cross reply transports.
result: pass
source: automated
coverage_id: 02-03/D1
verification: packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_interleaved_families_keep_resolution_and_reply_affinity; packages/lifx-emulator-core/tests/test_server.py::TestProtocolClass::test_protocol_datagram_received

### 9. Thread devices are selected only for exact untagged IPv6 unicast, with rejected traffic producing no processing, counters, activity or replies.
expected: Thread devices are selected only for exact untagged IPv6 unicast, with rejected traffic producing no processing, counters, activity or replies.
result: pass
source: automated
coverage_id: 02-03/D2
verification: packages/lifx-emulator-core/tests/test_device_manager.py::TestTransportAwareTargetResolution; packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_rejected_thread_packets_have_no_observable_side_effects

### 10. WiFi devices remain eligible on both families and reply through the endpoint that received each request.
expected: WiFi devices remain eligible on both families and reply through the endpoint that received each request.
result: pass
source: automated
coverage_id: 02-03/D3
verification: packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting; Plan 02-03 focused regression suite (156 passed)

### 11. Existing direct handler and helper callers retain IPv4 tuple defaults while production protocols own immutable endpoint identity.
expected: Existing direct handler and helper callers retain IPv4 tuple defaults while production protocols own immutable endpoint identity.
result: pass
source: automated
coverage_id: 02-03/D4
verification: packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_legacy_handler_prefers_explicit_transport; packages/lifx-emulator-core/tests/test_server.py::TestDatagramContextRouting::test_legacy_helper_calls_capture_ipv4_alias

### 12. A stock server atomically binds distinct IPv4 and IPv6-only transports on one effective port, with a configurable ::1 IPv6 default and bounded collision rollback.
expected: A stock server atomically binds distinct IPv4 and IPv6-only transports on one effective port, with a configurable ::1 IPv6 default and bounded collision rollback.
result: pass
source: automated
coverage_id: 02-04/D1
verification: packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle; packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_private_ipv6_socket_is_kernel_enforced_v6only

### 13. Public IPv4 and IPv6 endpoint properties expose only a complete live pair and port-zero devices advertise the committed non-zero service port.
expected: Public IPv4 and IPv6 endpoint properties expose only a complete live pair and port-zero devices advertise the committed non-zero service port.
result: pass
source: automated
coverage_id: 02-04/D2
verification: packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_port_zero_updates_live_added_device_service_port; packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_wifi_replies_follow_repeated_interleaved_origin_family

### 14. Shutdown stops admission, drains or cancels tracked work before transport closure, bounds both closure waits and clears all endpoint state.
expected: Shutdown stops admission, drains or cancels tracked work before transport closure, bounds both closure waits and clears all endpoint state.
result: pass
source: automated
coverage_id: 02-04/D3
verification: packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_stop_drains_work_before_closing_endpoints; packages/lifx-emulator-core/tests/test_server.py::TestServerLifecycle::test_stop_bounds_missing_endpoint_closure_signal

### 15. Repeated and interleaved WiFi requests over real IPv4 and IPv6 loopback receive replies only from their originating family.
expected: Repeated and interleaved WiFi requests over real IPv4 and IPv6 loopback receive replies only from their originating family.
result: pass
source: automated
coverage_id: 02-04/D4
verification: packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_wifi_replies_follow_repeated_interleaved_origin_family

### 16. A Thread device answers exact untagged IPv6 unicast and stays externally silent without receive effects for IPv4, broadcast, zero, tagged and mismatched traffic.
expected: A Thread device answers exact untagged IPv6 unicast and stays externally silent without receive effects for IPv4, broadcast, zero, tagged and mismatched traffic.
result: pass
source: automated
coverage_id: 02-04/D5
verification: packages/lifx-emulator-core/tests/test_ipv6_transport.py::test_thread_exact_ipv6_unicast_is_sole_response_path

## Summary

total: 16
passed: 16
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None.

## Verification Evidence

Codex checked base revision `01706c1bb8d56cc2b96938c03cf801df55030f9f` plus the three-file verification fix diff committed with this record. The real IPv6 rejection test now enables activity logging, requests acknowledgements for rejected packets, and proves logging is active with the valid request. Function-local imports in the API app and WebSocket tests were moved to module scope.

- Full workspace suite: 1,400 passed, no skips, 95.34% coverage in 13.99s.
- Ruff lint and format, Pyright and all pre-commit hooks passed.
- All 16 trackable decisions remain honoured.
- No coroutine warnings occurred. One existing Starlette test-client deprecation remains deferred; three CLI deprecation warnings are expected compatibility coverage.
- The four summaries have no top-level measured `commits:` field. Their legacy commit claims are not treated as verified counts or as measured mismatches.
- Existing security evidence records 20 closed threats and zero open threats; this is not a fresh security audit.
