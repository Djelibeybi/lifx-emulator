---
status: complete
phase: 01-thread-device-identity
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md]
started: 2026-09-09T09:25:00Z
updated: 2026-09-09T23:19:17Z
---

## Current Test

[testing complete]

Single confirmation checkpoint: all 28 deliverables were classified as
automatically covered (human_judgment: false, every verification ref passing
in the latest run: 1229 tests, ruff, pyright clean). User response: "approved".

## Tests

### 1. Connectivity enum and factory argument (01-01 D1, CONN-01)
expected: `Connectivity` enum, `coerce_connectivity()`, and a `connectivity` argument on `create_device()` and `DeviceBuilder`; default `wifi`, `ValueError` on invalid strings
result: pass
source: automated
coverage_id: 01-01/D1

### 2. Connectivity and wifi_signal immutable (01-01 D2)
expected: `connectivity` and `wifi_signal` cannot be reassigned after construction; the `ValueError` names the refused attribute
result: pass
source: automated
coverage_id: 01-01/D2

### 3. Header bit 3 pack/unpack (01-01 D3, HDR-01)
expected: `LifxHeader.thread_connection` packs and unpacks frame-address bit 3, defaults False, leaves reserved bits untouched, and shows in repr
result: pass
source: automated
coverage_id: 01-01/D3

### 4. Thread device sets bit 3 on every reply (01-01 D4, HDR-02, HDR-03)
expected: A Thread device sets bit 3 on `StateColor`, both acknowledgement helper outputs and `StateUnhandled`; a WiFi device never does
result: pass
source: automated
coverage_id: 01-01/D4

### 5. WiFi wire output unchanged (01-01 D5, HDR-03)
expected: `StateService`, `StateColor`, `Acknowledgement`, `StateUnhandled` and a plain header round trip are byte-for-byte identical to the pre-phase fixtures
result: pass
source: automated
coverage_id: 01-01/D5

### 6. Terminal-firmware ceiling in product specs (01-02 D1, CONN-02)
expected: `ProductSpecs` gains `max_firmware_major/minor` with `has_max_firmware_specs` type-checked on both fields; `get_max_firmware_version()` mirrors the default accessor
result: pass
source: automated
coverage_id: 01-02/D1

### 7. Tile defaults to and is capped at 3.50 (01-02 D2, CONN-02)
expected: Product 55 defaults to firmware (3, 50); explicit (3, 50) accepted, (3, 51) raises naming both values
result: pass
source: automated
coverage_id: 01-02/D2

### 8. Thread default and floor 4.200 (01-02 D3, CONN-02)
expected: A Thread device with no explicit firmware resolves to (4, 200) overriding any product default; explicit at or above the floor is accepted, below raises
result: pass
source: automated
coverage_id: 01-02/D3

### 9. Thread-on-Tile rejected by arithmetic (01-02 D4, CONN-02)
expected: Thread on product 55 raises naming both the floor and the ceiling; floor is checked before ceiling; an explicit override does not bypass the ceiling
result: pass
source: automated
coverage_id: 01-02/D4

### 10. Registry-wide Thread acceptance (01-02 D5, CONN-02)
expected: Every product in the registry other than 55 accepts `connectivity="thread"`
result: pass
source: automated
coverage_id: 01-02/D5

### 11. Extended multizone still granted on Thread (01-02 D6)
expected: `extended_multizone=False` with `connectivity="thread"` still reports extended multizone because the Thread firmware clears the product threshold
result: pass
source: automated
coverage_id: 01-02/D6

### 12. SKY-effect tests migrated to product 185 (01-02 D7)
expected: The two SKY-effect restriction tests pass unchanged on product 185 instead of 55
result: pass
source: automated
coverage_id: 01-02/D7

### 13. WiFi firmware resolution unchanged (01-02 D8)
expected: WiFi devices still resolve 3.70 (extended multizone), 2.60 (non-extended) and any `specs.yml` default
result: pass
source: automated
coverage_id: 01-02/D8

### 14. connectivity on all seven typed factories (01-03 D1, CONN-01)
expected: Every typed factory forwards `connectivity` to the builder; `create_tile_device(connectivity="thread")` raises; invalid strings rejected on every entry point
result: pass
source: automated
coverage_id: 01-03/D1

### 15. wifi_signal derived at build time (01-03 D2)
expected: `wifi_signal` is 0.0 for Thread and -45.0 for WiFi, derived from effective connectivity with no handler change
result: pass
source: automated
coverage_id: 01-03/D2

### 16. Thread identity surface over the wire (01-03 D3, CONN-03)
expected: `GetWifiInfo` reports signal 0.0 and `GetHostFirmware`/`GetWifiFirmware` report (4, 200) on a Thread device; a WiFi device at the same firmware reports identical firmware fields
result: pass
source: automated
coverage_id: 01-03/D3

### 17. Tiles mirror host firmware (01-03 D4)
expected: `StateDeviceChain` reports the device's own resolved host firmware per tile instead of a hard-coded 3.70
result: pass
source: automated
coverage_id: 01-03/D4

### 18. Documented max-args exemption (01-03 D5)
expected: CLAUDE.md carries a scoped exemption for the public factory functions; no `# noqa` added; `pyproject.toml` untouched
result: pass
source: automated
coverage_id: 01-03/D5

### 19. No handler or restorer modified in plan 03 (01-03 D6)
expected: `handlers/` and `state_restorer.py` show no diff across plan 03
result: pass
source: automated
coverage_id: 01-03/D6

### 20. connectivity persistence round trip (01-04 D1, CONN-04)
expected: A Thread device saved and reloaded is still Thread and still sets bit 3; the saved state is read once per `build()`
result: pass
source: automated
coverage_id: 01-04/D1

### 21. Legacy and corrupted files degrade to WiFi (01-04 D2, CONN-04)
expected: A pre-milestone file (missing key) restores silently as WiFi; a corrupted value restores as WiFi with one WARNING; every other field still restores
result: pass
source: automated
coverage_id: 01-04/D2

### 22. Explicit argument wins over saved value (01-04 D3)
expected: An explicit `connectivity` beats the persisted value in both directions with a WARNING naming the serial; a product mismatch contributes no connectivity
result: pass
source: automated
coverage_id: 01-04/D3

### 23. Bit 3 on every reply shape from one Thread multizone device (01-04 D4, HDR-02)
expected: `StateColor`, fast-path acknowledgement through the real server, multi-packet `StateMultiZone` and `StateUnhandled` all carry bit 3
result: pass
source: automated
coverage_id: 01-04/D4

### 24. State64 carries bit 3 on large and chained matrix devices (01-04 D5, HDR-02)
expected: Two `Get64` requests on a single oversized tile and one request on a multi-tile chain all answer with bit 3 set
result: pass
source: automated
coverage_id: 01-04/D5

### 25. Scenario-mutated replies keep bit 3 at device level (01-04 D6, HDR-02)
expected: Packets surviving `partial_responses` truncation and a `malformed_packets` reply still carry bit 3
result: pass
source: automated
coverage_id: 01-04/D6

### 26. Scenario-mutated replies reach the transport (01-04 D7, HDR-03)
expected: `malformed_packets` and `invalid_field_values` replies reach the real server transport with bit 3 set instead of raising before send
result: pass
source: automated
coverage_id: 01-04/D7

### 27. Mixed WiFi and Thread fleet (01-04 D8, HDR-02)
expected: A WiFi and a Thread device in one `DeviceManager` each answer with their own bit, including through the tagged-broadcast path
result: pass
source: automated
coverage_id: 01-04/D8

### 28. WiFi bytes unchanged and CI-equivalent gates green (01-04 D9, HDR-03)
expected: Four WiFi reply shapes byte-identical to fixtures; ruff format, ruff check, pyright, pre-commit and pytest with the 80% coverage gate all pass
result: pass
source: automated
coverage_id: 01-04/D9

## Summary

total: 28
passed: 28
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
