# Phase 2: IPv6 Transport and Thread Isolation - Pattern Map

**Mapped:** 2026-09-10
**Files analysed:** 11 new/modified files
**Analogues found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analogue | Match Quality |
|---|---|---|---|---|
| `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` | utility | event-driven | `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` | role/data-flow match |
| `packages/lifx-emulator-core/src/lifx_emulator/server.py` | service | request-response, event-driven | same file | exact modification |
| `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` | service | request-response | same file | exact modification |
| `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` | model/service | event-driven | same file | exact modification |
| `packages/lifx-emulator/src/lifx_emulator_app/api/app.py` | config/provider | event-driven | same file | exact modification |
| `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` | service | event-driven, pub-sub | same file | exact modification |
| `packages/lifx-emulator-core/tests/test_background_tasks.py` | test | event-driven | `packages/lifx-emulator-core/tests/test_server.py` | test-style match |
| `packages/lifx-emulator-core/tests/test_server.py` | test | request-response, event-driven | same file | exact modification |
| `packages/lifx-emulator-core/tests/test_device_manager.py` | test | request-response | same file | exact modification |
| `packages/lifx-emulator-core/tests/test_ipv6_transport.py` | test | request-response | `packages/lifx-emulator-core/tests/test_server.py` | test-style match |
| `packages/lifx-emulator/tests/test_websocket.py` | test | event-driven, pub-sub | same file | exact modification |

All named existing analogue paths were verified with `git ls-files`. The three new paths do not yet exist and therefore are not tracked: `background_tasks.py`, `test_background_tasks.py`, and `test_ipv6_transport.py`.

## Pattern Assignments

### `packages/lifx-emulator-core/src/lifx_emulator/background_tasks.py` (utility, event-driven)

**Analogue:** `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py`

**Imports and logger pattern** (lines 3-14, 27):

```python
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)
```

**Strong-reference core** (lines 83-84, 189-196):

```python
self.background_save_tasks: set[asyncio.Task] = set()

def _track_save_task(self, task: asyncio.Task) -> None:
    self.background_save_tasks.add(task)
    task.add_done_callback(self.background_save_tasks.discard)
```

Generalise this exact owner-local set pattern into `BackgroundTaskTracker`. Add the locked behaviour absent from the analogue: accept a coroutine plus operation label, close the coroutine when admission/no-loop scheduling fails, retrieve exceptions in the done callback, distinguish cancellation, and implement five-second `asyncio.wait()` followed by cancel/`gather(return_exceptions=True)`.

### `packages/lifx-emulator-core/src/lifx_emulator/server.py` (service, request-response/event-driven)

**Analogue:** existing `server.py`; retain its dependency-injection, statistics, activity, and packet-processing structure.

**Imports and construction pattern** (lines 3-23, 121-139):

```python
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

class EmulatedLifxServer:
    def __init__(self, devices, device_manager, bind_address="127.0.0.1", ...):
        self._device_manager = device_manager
        self.bind_address = bind_address
        self.port = port
        self.transport = None
```

Keep `transport` as the IPv4 alias. Add the IPv6 bind address, private IPv6 transport/protocol state, private live endpoint tuples, and the owner-local tracker here. Put all new imports at module top.

**Protocol callback seam** (lines 180-209):

```python
class LifxProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        self.server.transport = transport

    def datagram_received(self, data, addr):
        if self.loop:
            self.loop.call_soon(
                self.loop.create_task, self.server.handle_packet(data, addr)
            )
```

Copy the nested protocol shape, but parameterise it with immutable family identity and admission state. Each instance retains its own transport and builds a frozen datagram context. Only the IPv4 startup commit assigns `server.transport`; schedule packet handling through the tracker with a useful operation label.

**Reply path** (lines 211-237, 259-311):

```python
response_data = ack_header.pack() + ack_payload
if self.transport:
    self.transport.sendto(response_data, addr)

resp_payload = _pack_payload(resp_packet)
response_data = resp_header.pack() + resp_payload
if self.transport:
    self.transport.sendto(response_data, addr)
```

Preserve response packing/statistics, but replace both global transport reads with `context.transport.sendto(..., context.peer)` so concurrent families cannot cross-route.

**Effect-ordering and exact-target seam** (lines 338-445):

```python
if len(data) < LIFX_HEADER_SIZE:
    logger.warning("Packet too short: %s bytes from %s", len(data), addr)
    self.error_count += 1
    return

header = LifxHeader.unpack(data)
target_str = "broadcast" if header.tagged else header.target.hex().rstrip("0000")
self.activity_observer.on_packet_received(PacketEvent(..., target=target_str))
target_devices = self._device_manager.resolve_target_devices(header)
```

Keep short-packet validation first, then unpack and resolve with `context.family` before statistics, payload/scenario work, logging, acknowledgement, or observer notification. Replace trimming with the manager's established `header.target[:6].hex()` rule plus an explicit `tagged or all-zero` broadcast predicate.

**Lifecycle seam** (lines 544-555):

```python
loop = asyncio.get_running_loop()
self.transport, _ = await loop.create_datagram_endpoint(
    lambda: self.LifxProtocol(self), local_addr=(self.bind_address, self.port)
)

if self.transport:
    self.transport.close()
```

Retain asyncio endpoint creation, but implement startup as a local two-bind transaction: IPv4 first, read its effective port, create an explicit `AF_INET6` socket, set `IPV6_V6ONLY` before bind, bind to that same port, make it non-blocking, and adopt it with `sock=`. Publish both endpoints only after success. Catch `BaseException`, close the current resource owner without masking the original exception, and bare-raise. Shutdown order is admission stop, tracker drain, both transport closes, both `connection_lost` barriers, then clearing public endpoint state.

### `packages/lifx-emulator-core/src/lifx_emulator/devices/manager.py` (service, request-response)

**Analogue:** existing `manager.py`.

**Public protocol pattern** (lines 27-28, 98-107):

```python
@runtime_checkable
class IDeviceManager(Protocol):
    def resolve_target_devices(
        self, header: LifxHeader
    ) -> list[EmulatedLifxDevice]:
        ...
```

Extend both the protocol and concrete method with `family: socket.AddressFamily = socket.AF_INET`; the default preserves direct callers.

**Exact lookup/list-return pattern** (lines 268-290):

```python
if header.tagged or header.target == b"\x00" * 8:
    target_devices = self._device_repository.get_all()
else:
    target_serial = header.target[:6].hex()
    device = self._device_repository.get(target_serial)
    if device:
        target_devices = [device]
return target_devices
```

Keep the plain list contract and exact serial extraction. Filter Thread devices unless all three conditions hold: `family == AF_INET6`, untagged/non-zero target, and exact serial match. WiFi keeps the existing broadcast and exact-target behaviour on either family. Log filtered Thread targets at debug level here, where connectivity and target are both available.

### `packages/lifx-emulator-core/src/lifx_emulator/devices/device.py` (model/service, event-driven)

**Analogue:** its current persistence scheduler (lines 177-196).

```python
loop = asyncio.get_running_loop()
task = loop.create_task(self.storage.save_device_state(self.state))
self._track_save_task(task)

self.background_save_tasks.add(task)
task.add_done_callback(self.background_save_tasks.discard)
```

Replace the hand-managed set with an owner-local `BackgroundTaskTracker` and schedule labelled persistence work through it. This bounded migration follows the repository rule not to leave the observed unconsumed-exception defect behind. Preserve the no-storage early return and serial-specific logging context.

### `packages/lifx-emulator/src/lifx_emulator_app/api/services/event_bridge.py` (service, event-driven/pub-sub)

**Analogue:** existing bridge callbacks and observer adapters.

**Current scheduling seam** (lines 27-40):

```python
logger = logging.getLogger(__name__)

def _schedule_async(coro) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        logger.warning("No running event loop to schedule async task")
```

Replace this bare scheduler with an injected `BackgroundTaskTracker`. Preserve synchronous callback adapters; give every broadcast a stable label and let the tracker close rejected/no-loop coroutines.

**Callback wiring pattern** (lines 67-79):

```python
def on_device_added(device: EmulatedLifxDevice) -> None:
    device_info = DeviceMapper.to_device_info(device)
    _schedule_async(ws_manager.broadcast_device_added(device_info.model_dump()))

def on_device_removed(serial: str) -> None:
    _schedule_async(ws_manager.broadcast_device_removed(serial))
```

Apply the same injected tracker to activity broadcasts (lines 117-161) and state-change broadcasts (lines 314-316). Do not introduce a module-global task collection.

### `packages/lifx-emulator/src/lifx_emulator_app/api/app.py` (provider/config, event-driven)

**Analogue:** FastAPI factory-owned WebSocket manager and broadcaster (lines 65-76, 204-218).

```python
ws_manager = WebSocketManager(server)
stats_broadcaster = StatsBroadcaster(server, ws_manager)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    stats_broadcaster.start()
    yield
    await stats_broadcaster.stop()
```

Instantiate one bridge tracker alongside these application-owned services, inject it into every bridge adapter, open admission at lifespan startup, and shut it down in a `finally` block after stopping the periodic broadcaster. Store only diagnostics needed by tests in `app.state`.

### Core tests: `test_background_tasks.py`, `test_server.py`, `test_ipv6_transport.py`

**Analogue:** `packages/lifx-emulator-core/tests/test_server.py`.

The existing suite groups behaviour into classes (`TestServerInitialization` line 23, `TestPacketRouting` line 79, `TestServerLifecycle` line 305, `TestProtocolClass` line 345, `TestErrorHandling` line 392, and `TestServerStatsAndActivity` line 848). Follow that organisation and reuse its injected fakes/mocks rather than adding a new test framework.

- `test_background_tasks.py`: parameterise completion, failure, cancellation, no-running-loop, admission-closed, grace completion and timeout cancellation. Hold tasks on an `asyncio.Event`, force `gc.collect()`, and assert retained count then empty count.
- `test_server.py`: extend protocol and lifecycle classes for distinct family contexts/transports, idempotent start/stop, rollback/cancellation, closure barriers, side-effect ordering, endpoint properties, and trailing-zero/broadcast activity targets.
- `test_ipv6_transport.py`: use real IPv4 and IPv6 loopback sockets; assert the stock server's two endpoints share the non-zero effective port, `IPV6_V6ONLY == 1`, WiFi responds family-locally on both, and Thread responds only to exact IPv6 unicast.

### `packages/lifx-emulator-core/tests/test_device_manager.py` (test, request-response)

**Analogue:** existing target-resolution tests (lines 92-172).

```python
targets = device_manager.resolve_target_devices(header)
assert len(targets) == 1
assert targets[0] == device
```

Preserve the existing no-family calls as explicit backwards-compatibility coverage. Add a parameterised matrix over WiFi/Thread, `AF_INET`/`AF_INET6`, exact/tagged/all-zero/wrong targets, asserting the same plain-list result contract and debug logging for filtered Thread candidates.

### `packages/lifx-emulator/tests/test_websocket.py` (test, event-driven/pub-sub)

**Analogue:** existing `TestEventBridge` (line 189), state observer scheduling tests (lines 404-430), and `TestStatsBroadcaster` (line 552).

```python
with patch(
    "lifx_emulator_app.api.services.event_bridge._schedule_async"
) as mock_schedule:
    observer.on_state_changed(device, 102, 1000)
    mock_schedule.assert_called_once()
```

Replace scheduler patching with an injected fake tracker that records labels and closes captured coroutine objects, or exercise the real tracker inside the running loop. Add flood/GC, logged failure, exactly-once completion, and FastAPI lifespan-drain assertions. This avoids the current un-awaited-coroutine warning pattern.

## Shared Patterns

### Owner-local lifecycle ownership

**Sources:** `devices/device.py:83-84,189-196`; `api/app.py:65-76`

Every long-lived owner constructs its own tracker. Components share the tracker class, never a global set. Application lifespan and server shutdown are the drain boundaries.

### Error and cancellation handling

**Sources:** `server.py:340-449`; `event_bridge.py:202-234`

Use module loggers, preserve original startup failures with a bare re-raise after best-effort cleanup, log background task failures with operation labels, and treat expected cancellation as debug-level lifecycle information. Tests must assert the original exception object/type is not replaced by cleanup errors.

### Input validation and effect ordering

**Sources:** `server.py:338-380`; `manager.py:268-290`

Reject an incomplete header before unpacking. For complete packets, resolve family/connectivity eligibility immediately after header parsing. An empty target list returns before statistics, activity, scenario evaluation, acknowledgement or response generation.

### Address and target formatting

**Sources:** `server.py:239-255,401-425`; `manager.py:279-286`

Use `header.target[:6].hex()` for exact lowercase 12-hex serials and explicit tagged/all-zero broadcast detection. Keep IPv4 `host:port`; format IPv6 as `[host]:port`. Public endpoints normalise socket addresses to `(sockname[0], sockname[1])`.

### Dependency injection

**Sources:** `server.py:121-139`; `api/app.py:45-76,204-218`

Continue constructor/factory injection for managers, observers and trackers. This makes family transport ownership, task retention and shutdown deterministic under tests without reaching into asyncio globals.

## No Analogue Found

No file lacks a useful tracked analogue. The three new files have no exact same-role file, but their patterns are directly grounded in tracked source: device task retention for `background_tasks.py`, core server tests for tracker/IPv6 tests, and the existing server lifecycle for real-socket setup.

The sibling `../lifx-async/tests/conftest.py` is a read-only oracle for V6-only socket call ordering, not a planner copy source in this map: it lies outside this repository's tracked-source gate.

## Metadata

**Analogue search scope:** `packages/lifx-emulator-core/src/lifx_emulator`, `packages/lifx-emulator/src/lifx_emulator_app/api`, and their tracked test suites
**Strong analogues read:** 8 tracked files
**Pattern extraction date:** 2026-09-10
**Project constraints applied:** Australian English; Python imports at module top; no new dependency; `uv` for later execution; no source files modified
