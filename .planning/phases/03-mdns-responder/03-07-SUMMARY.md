---
phase: 03-mdns-responder
plan: '07'
subsystem: networking
tags:
- mdns
- asyncio
requires:
- 03-06
provides:
- Production raw-wire and pristine-client integration with platform-specific CI
affects:
- Phase 3 verification
key-files:
  modified:
  - scripts/prepare_mdns_oracle.py
  - packages/lifx-emulator-core/tests/test_mdns_integration.py
  - packages/lifx-emulator-core/tests/test_mdns_platform.py
  - .github/workflows/ci.yml
requirements-completed:
- MDNS-01
- MDNS-02
- MDNS-03
- MDNS-04
- MDNS-05
- MDNS-06
- MDNS-07
- MDNS-08
- MDNS-09
- MDNS-11
coverage:
- id: 03-07
  description: Production raw-wire and pristine-client integration with platform-specific
    CI
  verification:
  - kind: integration
    ref: 'Required-mode local macOS integration: 4 passed, no skips, covering fleets
      0/1/10/100, exact synthetic serial sets, complete records, direct queries, removal/re-add
      and IPv4/IPv6 power. Windows public-owner simulations: 2 passed (not Windows
      execution). Full suite: 1474 passed, 4 environment-gated integration skips;
      those same 4 passed separately in required mode. Root-configured uv run pyright
      and Ruff passed. Core wheel and sdist rebuilt. Hosted Ubuntu/macOS production
      CI passed in run 35846599552 at f8d9f86; all ten Python/OS jobs passed and final verification is 5/5.'
    status: pass
  human_judgment: false
completed: '2026-09-23'
status: complete
---

# Production raw-wire and pristine-client integration with platform-specific CI

## Accomplishments

Production raw-wire and pristine-client integration with platform-specific CI.

## Verification

Required-mode local macOS integration: 4 passed, no skips, covering fleets 0/1/10/100, exact synthetic serial sets, complete records, direct queries, removal/re-add and IPv4/IPv6 power. Windows public-owner simulations: 2 passed (not Windows execution). Full suite: 1474 passed, 4 environment-gated integration skips; those same 4 passed separately in required mode. Root-configured uv run pyright and Ruff passed. Core wheel and sdist rebuilt. Hosted Ubuntu/macOS production CI passed in run 35846599552 at f8d9f86; all ten Python/OS jobs passed and final verification is 5/5.

## Commits

53b08ef (oracle and production tests); 7e7d10b (CI and simulation); 7a482f1 (review fixes to earlier plans).

## Deviations from Plan

Used the repository-configured Pyright invocation (uv run pyright), which checks packages/*/src; the plan literal directory argument overrides include selection and reported 187 test-tree diagnostics, including pre-existing untyped tests. No source diagnostics remain. Scoped live LAN assertions to the synthetic emulator prefix, excluding unrelated physical responder TTLs. Local Thread control used an existing bridge ULA after the VPN address timed out; no interface or route was changed. Automatic approval review twice rejected git push to existing PR224 without explicit user push approval; the user subsequently approved the push and both hosted production jobs passed. Tests cover existing production implementation rather than claiming a new implementation RED cycle.

## Next Phase Readiness

Both hosted production jobs passed and the configured security audit has zero blocking threats. Final verification passed 5/5 and closes the original hosted-evidence gap.

## Self-Check: PASSED

## Hosted follow-up

The first run (35845339733, 721601a) passed all four production cases without skips on each OS but exposed Python 3.10-incompatible loop socket APIs in the raw test helper. Commit 007679a uses DatagramProtocol and explicitly waits for transport closure; all 68 affected tests passed locally under Python 3.10. Commit f8d9f86 records the completed L1 security audit. Run 35846599552 covers the repaired helper. Production responder code is unchanged.
