# Zeroconf recovery prototype

## Scope and authority

The user's “Ok” approved the recommended bounded recovery prototype following the targeted continuation. This is a new, case-bounded follow-up, not unused time from the exhausted 60-minute allowance. The user-authorised lifting of the harness restriction remains in force. No production integration or dependency change is included.

The prototype owns a fresh `AsyncZeroconf` instance for each explicit attempt. It awaits registration and its returned announcement awaitable, closes the whole instance after a partial failure, preserves failed status/error, and only starts another instance after previous cleanup succeeds. It serialises lifecycle operations and exposes read-only status/error. Thread admission is a guard to call before membership changes; it is not integrated into the production server.

## Measured result

Local macOS, Python 3.14.7, zeroconf 0.151.3 and the pristine lifx-async checkout at `48b7efbff59656499373b13ef17e3008d125feb5`:

- Injected construction failure leaves failed status and permits explicit retry.
- Injected failure before the second registration closes the real responder after the first registration. A fresh public client discovers neither test identity afterwards.
- Explicit retry with a fresh responder registers both original identities; the pristine public client discovers both.
- 245 background WiFi `get_power()` requests succeed with matching values and no errors; 95 complete during the partial-failure/cleanup observation. Additional requests after runtime failure and retry also succeed. The LIFX endpoint remains unchanged.
- Injected runtime failure shuts down real Thread-only and mixed servers, closes both endpoint families and retains failed status/error.
- Final inventory has no pending async tasks and only `MainThread`.

Raw evidence is in `03-recovery-evidence/local-macos.json`, including SHA-256 fingerprints of the exact runner and adapter. The input oracle checkout was verified clean at the pinned revision before execution. The existing candidate manifest is unchanged.

55 focused tests pass (43 previous plus 12 recovery cases). New cases cover construction, partial registration at three positions, announcement failure, cancellation, failed cleanup blocking new ownership, disabled mode, concurrent retries, read-only state and the WiFi/Thread/mixed failure policy. CI now runs the whole focused test directory. The live recovery probe is local evidence; it is not added to hosted execution or claimed as cross-platform recovery proof.

## Important limits

**This proves recovery after a reported failure, not detection of a real listener failure.** Faults are injected at the adapter boundary without modifying zeroconf. Construction failure is simulated before allocation; constructor-internal partial-allocation cleanup is not established. Thread/mixed tests exercise the real server shutdown policy but not live Thread advertisements/control during failure.

Inspection of the installed pinned zeroconf source found `AsyncListener.connection_lost` has an empty body, while `error_received` logs errors. No supported runtime listener-failure notification is demonstrated here. The prototype's `runtime_failure` entry point must not be presented as library-provided detection. Resolving that integration is still necessary for D-08; private listener patches are outside the accepted design.

Cancellation evidence covers a single cancellation during registration, not repeated cancellation or an indefinitely hanging close. Production membership admission must execute atomically with membership changes. This spike guard does not establish that integration.

Two initial local attempts exposed probe errors: the server's default bind is loopback, and connectivity resides on `device.state`. Both were corrected before the retained run. No initial timeout or failed attempt is counted as candidate success.

## Reproduction

Use a clean checkout of lifx-async at the pinned revision in `/tmp/lifx-mdns-oracle-12a71bd`:

```sh
UV_CACHE_DIR=/tmp/lifx-review-uv uv run --frozen \
  --with zeroconf==0.151.3 --with /tmp/lifx-mdns-oracle-12a71bd \
  python scripts/spike_mdns_recovery.py --output /tmp/lifx-recovery.json
UV_CACHE_DIR=/tmp/lifx-review-uv uv run --frozen \
  pytest scripts/mdns_spike_tests -q --no-cov
```

The runner retains failures and exits nonzero if measured criteria fail. It uses synthetic test identities and closes its owned resources. Production source, project dependency manifests and lockfile remain unchanged.

## Decision

Zeroconf remains the preferred provisional foundation. Partial-startup cleanup and explicit recovery now have concrete evidence. The next decision is how to satisfy runtime failure detection through a supported API or an explicitly agreed observable-health contract. Do not begin production integration or declare MDNS-10 complete from these results. Candidate-specific malformed/flood behaviour, Windows simulation and full configuration/interface enforcement also remain outstanding from the preceding continuation.
