# Phase 3: mDNS Responder - Pattern Map

**Mapped:** 2026-09-22  
**Scope:** MDNS-10 four-hour implementation-selection spike only; do not plan responder production changes.  
**Files analysed:** 5 proposed artefacts; **analogs found:** 5/5.

## File Classification

| New/modified file | Role | Data flow | Closest tracked analog | Match |
|---|---|---|---|---|
| `scripts/spike_mdns_candidates.py` | utility / spike harness | datagram, batch | `packages/lifx-emulator-core/tests/test_ipv6_transport.py` | role-match |
| `packages/lifx-emulator-core/tests/test_mdns_spike_datagrams.py` | test | datagram / request-response | `packages/lifx-emulator-core/tests/test_ipv6_transport.py` | exact flow |
| `packages/lifx-emulator-core/tests/test_mdns_spike_socket_failures.py` | test | event-driven / failure | `packages/lifx-emulator-core/tests/test_server.py` | exact flow |
| `docs/evidence/phase-03-mdns-spike.md` | evidence | batch / transform | sibling `lifx-async` mDNS source | partial |
| `.github/workflows/ci.yml` (only if a focused job is justified) | config | batch | `.github/workflows/ci.yml` | exact |

## Pattern Assignments

### `scripts/spike_mdns_candidates.py` (utility, datagram/batch)

**Analog:** sibling tracked source `../lifx-async/src/lifx/network/discovery/mdns/transport.py`.

Use an async context-managed candidate runner, explicit socket construction, and cleanup-on-error. Do **not** use its automatic route/interface selection: Phase 3 explicitly rejects automatic address selection.

```python
# transport.py:94-101, 131-148, 197-217
async def __aenter__(self):
    await self.open(); return self
...
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((local_address, 0))
...
except BaseException as e:
    if datagram_transport is not None: datagram_transport.close()
    elif sock is not None: sock.close()
    raise LifxNetworkError(...) from e
```

Record each candidate's installed version, command, wall/active time, 1/10/100 fleet result, RSS/CPU measurement method, and each unmet criterion. The harness is evidence tooling: use isolated uv-managed candidate dependencies and preserve the production dependency graph. Importing existing core code for the experiment is permitted; integrating a production responder is deferred.

### `packages/lifx-emulator-core/tests/test_mdns_spike_datagrams.py` (test, datagram/request-response)

**Analog:** `packages/lifx-emulator-core/tests/test_ipv6_transport.py`.

```python
# test_ipv6_transport.py:31-43, 66-75, 120-146
class _ClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.received = asyncio.Queue()
        self.closed = asyncio.Event()
    def datagram_received(self, data, addr): self.received.put_nowait((data, addr))
...
transport, _ = await loop.create_datagram_endpoint(
    lambda: protocol, local_addr=(host, 0), family=family
)
...
await asyncio.wait_for(protocol.received.get(), timeout=1.0)
...
finally:
    transport.close()
    await asyncio.wait_for(protocol.closed.wait(), timeout=1.0)
```

Keep injection hermetic: bind loopback/ephemeral ports, parse real datagrams, assert one complete response per device and legacy-unicast source destination/ID. A multicast integration remains separately marked as environment evidence; the existing skip pattern is `test_ipv6_transport.py:15-28` and must never convert a skip into a pass.

### `packages/lifx-emulator-core/tests/test_mdns_spike_socket_failures.py` (test, event-driven failure)

**Analog:** `packages/lifx-emulator-core/tests/test_server.py`.

```python
# test_server.py:505-525, 624-638
fake_loop.create_datagram_endpoint = AsyncMock(side_effect=create_endpoint)
with patch("lifx_emulator.server.asyncio.get_running_loop", return_value=fake_loop):
    await server.start()
...
with pytest.raises(OSError) as caught:
    await server.start()
assert ipv4_transport.closed
assert server.ipv4_endpoint is None
```

Use `AsyncMock`, fake transports and patched sockets to distinguish simulated Windows socket-branch evidence from Ubuntu/macOS integration. This spike test may exercise a candidate adapter only; it must not assert a future responder API.

### `docs/evidence/phase-03-mdns-spike.md` (evidence, batch/transform)

**Analog:** sibling tracked source `../lifx-async/src/lifx/network/discovery/mdns/discovery.py`.

The evidence table must treat multiple packets as a valid discovery input. `_LifxRecordCache` is explicitly an accumulator (`discovery.py:281-284`); its packet merge entry point is `add_packet(records, source_ip)` (`discovery.py:707-724`). Cite exact candidate source/package lines beside every conclusion. Separate: demonstrated local result, Ubuntu/macOS CI result, macOS x86_64 PyApp evidence, simulated Windows result, and untested status. End with an explicit go/no-go/provisional decision and the four-hour active-work/CI-queue accounting.

### `.github/workflows/ci.yml` (config, batch)

**Analog:** `.github/workflows/ci.yml`.

```yaml
# ci.yml:71-101
test:
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest]
      python-version: ['3.10', '3.11', '3.12', '3.13', '3.14']
...
    - run: uv sync --frozen
    - run: uv run --frozen pytest --cov-fail-under=80
```

Use the existing matrix if focused CI is warranted after the local spike; do not change it merely to create a spike. Packaging evidence follows the separate release workflow: macOS Intel is `macos-15-intel` / `x86_64-apple-darwin` (`release-binaries.yml:30-33`) and its PyApp build inputs are `PYAPP_*` plus `CARGO_BUILD_TARGET` (`release-binaries.yml:73-89`).

## Shared Patterns

### uv-managed execution

Root workspace test configuration names core/application source roots (`pyproject.toml:1-15, 58-63`). CI installs with `uv sync --frozen` before `uv run --frozen pytest` (`ci.yml:97-101`). Isolated candidate dependencies and their reproducible resolution belong to spike execution; production dependency changes await selection.

### Datagram lifecycle and evidence quality

Use real loopback sockets for protocol facts, then close transports and await `connection_lost` (`test_ipv6_transport.py:139-149`). Use mocks for deterministic socket failures (`test_server.py:604-638`). State which kind of evidence each result is. Experiments are the purpose of spike execution, not this planning run. VM work is extension-only; production responder implementation awaits the selection decision.

## No Analog Found

| File | Reason |
|---|---|
| A production responder module | Intentionally deferred until MDNS-10 records a justified decision. |

## Metadata

**Analog search scope:** core UDP tests/server, sibling `lifx-async` mDNS transport/cache, CI and PyApp workflow.  
**Tracked-source gate:** verified for every named analog, including from the sibling repository root.  
**Files scanned:** 8.  
**Pattern extraction date:** 2026-09-22.
