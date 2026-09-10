---
phase: "01"
slug: "thread-device-identity"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-09"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| library caller → factory arguments | `connectivity` and `firmware_version` arrive as arbitrary caller-supplied values through `create_device()` and the seven typed factories | Untrusted string / tuple, low sensitivity |
| LIFX client → `LifxHeader.unpack()` | Untrusted 36-byte frame from the network, including frame-address flags bit 3 | Untrusted binary |
| LIFX client → `GetWifiInfo` / `GetHostFirmware` / `GetWifiFirmware` | Untrusted requests reading emulated device state back out over the wire | Public emulated metadata |
| `specs.yml` on disk → `SpecsRegistry.load_from_file()` | Packaged data file parsed with `yaml.safe_load` at import time | Trusted packaged data |
| `~/.lifx-emulator/<serial>.json` on disk → `StateRestorer` | Hand-editable JSON whose `connectivity` value is arbitrary user- or attacker-supplied text | Untrusted text |
| device serial → persisted file path | Serial-derived filename, guarded by `_SERIAL_RE` in `devices/persistence.py` | Path component |
| scenario configuration → reply mutation | `partial_responses` / `malformed_packets` truncate payloads on the reply path | Operator-configured, local |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | `coerce_connectivity()` in `devices/states.py` | low | mitigate | Enum membership via `Connectivity(value)`; non-member raises `ValueError` before `DeviceState` is composed (`states.py:69-85`) | closed |
| T-01-02 | Spoofing | `LifxHeader.unpack()` bit 3 on an inbound frame | low | accept | Inbound bit 3 is unpacked faithfully and never consulted; replies are stamped from device state only | closed |
| T-01-03 | Elevation of Privilege | `DeviceState.__setattr__` `FrozenInstanceError` translation | low | mitigate | Translation narrows to `dataclasses.FrozenInstanceError` and re-raises `ValueError` (`states.py:529-530`); no other `AttributeError` is swallowed | closed |
| T-01-04 | Denial of Service | `EmulatedLifxDevice._response_header_template` | low | accept | Constant-time boolean computed once per device at construction; no per-packet cost | closed |
| T-01-05 | Tampering | `SpecsRegistry.load_from_file()` parsing `max_firmware_*` keys | low | mitigate | Keys read with `.get(...)` defaulting to `None`; `has_max_firmware_specs` requires `isinstance(..., int)` on both (`specs.py:77-91,138`), so partial or non-integer entries degrade to "no ceiling" | closed |
| T-01-06 | Denial of Service | `FirmwareConfig.get_firmware_version()` raising on a valid product | medium | mitigate | Ceiling check gated on `product_id is not None` and a non-`None` accessor (`firmware_config.py:101,149`); `TestThreadOnTileRejectionRegistryWide` asserts the rejected set is exactly `{55}` (`test_thread_identity.py:383-413`) | closed |
| T-01-07 | Information Disclosure | `ValueError` message content | low | accept | Messages carry product IDs and firmware tuples already public in the shipped `specs.yml` | closed |
| T-01-08 | Tampering | seven typed factories in `factories/factory.py` | low | mitigate | Every typed factory forwards `connectivity=connectivity` to `create_device()` (7 sites); the single `coerce_connectivity()` call lives in `builder.py:307`; parametrised test covers all eight entry points | closed |
| T-01-09 | Information Disclosure | `StateWifiInfo` signal on a Thread device | low | mitigate | `wifi_signal` derived at build time from effective connectivity (`builder.py:372-373`); no measured value exists to leak | closed |
| T-01-10 | Spoofing | `StateDeviceChain` per-tile firmware | low | accept | Emulated metadata read from in-process state; already caller-visible via `GetHostFirmware`; carries no authentication meaning | closed |
| T-01-11 | Tampering | `StateRestorer.peek_connectivity()` reading an arbitrary `connectivity` string | medium | mitigate | Builder converts with `Connectivity(saved)` inside `try` / `except ValueError` and degrades to `Connectivity.WIFI` with one `WARNING` (`builder.py:301-330`); no unvalidated string reaches `NetworkState` | closed |
| T-01-12 | Denial of Service | `DeviceBuilder.build()` aborting on a corrupted persisted file | medium | mitigate | Unrecognised enum value is caught; product mismatch returns `None` from the peek; `test_async_storage.py:392` asserts a `"bluetooth"` file still restores every other field | closed |
| T-01-13 | Tampering | serial-to-path mapping in `devices/persistence.py` | high | mitigate | `persistence.py` not modified in this phase (`git diff --stat ba1222d..HEAD` is empty); `_SERIAL_RE` guard intact at `persistence.py:24,95` | closed |
| T-01-14 | Information Disclosure | the new `WARNING` log lines | low | accept | Records name a serial and a connectivity string already present in the persisted file and existing product-mismatch warnings | closed |
| T-01-15 | Tampering | scenario-truncated replies still carrying bit 3 | low | accept | Intended: `partial_responses` / `malformed_packets` mutate payloads, not headers; asserted by test | closed |
| T-01-16 | Tampering | hand-rewritten `<serial>.json` fixture files in `temp_storage.storage_dir` | low | mitigate | Fixtures written through the public `storage_dir` into a pytest `tmp_path`-scoped directory (`test_async_storage.py:215,275`); `_device_path()` remains the only production path-construction route | closed |
| T-01-17 | Tampering | bytes branch in `EmulatedLifxServer` reply packing | low | mitigate | `_pack_payload()` / `_format_packet_fields()` accept `bytes` only from `_apply_error_scenarios()` (`server.py:58,72,95-113`); no new parsing path, header still packed by `LifxHeader.pack()` | closed |
| T-01-18 | Spoofing | recording transport test double assigned to `server.transport` | low | accept | Test-only; opens no socket, binds no port; no production path reaches it | closed |
| T-01-SC | Tampering | npm/pip/cargo installs | low | accept | No package-manager install task in any plan; `uv.lock`, root and package `pyproject.toml` unchanged for the phase (`git diff --stat` empty); Bandit runs via pre-commit and CI | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-01-01 | T-01-02 | Inbound bit 3 is a device-side report; behaviour change for inbound bit-3 frames is out of scope per `01-SPEC.md` Boundaries | Phase 1 plan (cross-AI reviewed) | 2026-09-09 |
| R-01-02 | T-01-04 | Per-device constant computed once; no reply-path cost | Phase 1 plan | 2026-09-09 |
| R-01-03 | T-01-07 | Error messages expose only public product metadata | Phase 1 plan | 2026-09-09 |
| R-01-04 | T-01-10 | Per-tile firmware is emulated metadata with no authentication meaning | Phase 1 plan | 2026-09-09 |
| R-01-05 | T-01-14 | Warning lines add no data not already on disk or in existing warnings | Phase 1 plan | 2026-09-09 |
| R-01-06 | T-01-15 | Honest connectivity reporting under payload-mutating scenarios is the intended behaviour | Phase 1 plan | 2026-09-09 |
| R-01-07 | T-01-18 | Test double only; unreachable from production code | Phase 1 plan | 2026-09-09 |
| R-01-08 | T-01-SC | No packages installed; lockfile untouched | Phase 1 plan (developer decision, round 2 review) | 2026-09-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-09 | 19 | 19 | 0 | execute-phase orchestrator (ASVS L1 grep-depth short-circuit; register authored at plan time) |
| 2026-09-10 | 19 | 19 | 0 | verify-work post-hook (ASVS L1 grep-depth short-circuit; register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-09
