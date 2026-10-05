# Troubleshooting Guide

Solutions to common problems when using the LIFX Emulator.


## Port Conflicts and Resolution

### Port Already in Use

**Problem:** Server fails to start with "Address already in use"

```
OSError: [Errno 48] Address already in use
```

**Causes:**

- Another emulator instance is running
- Another application is using port 56700
- Previous test didn't clean up properly

**Solutions:**

1. **Find what's using the port:**
   ```bash
   # Linux/macOS
   lsof -i :56700
   netstat -an | grep 56700

   # Windows
   netstat -ano | findstr :56700
   ```

2. **Kill the process:**
   ```bash
   # Linux/macOS
   kill <PID>

   # Windows
   taskkill /PID <PID> /F
   ```

3. **Use dynamic port allocation (best for tests):**
   ```python
   from lifx_emulator import EmulatedLifxServer, create_color_light
   from lifx_emulator.devices import DeviceManager
   from lifx_emulator.repositories import DeviceRepository

   device = create_color_light("d073d5000001")

   # Let the OS assign an available port
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
   )
   await server.start()
   # server.port stays 0; the assigned port is in ipv4_endpoint
   print(f"Server running on port {server.ipv4_endpoint[1]}")
   ```

4. **Use port offset in parallel tests (pytest-xdist):**
   ```python
   import pytest

   from lifx_emulator import EmulatedLifxServer, create_color_light
   from lifx_emulator.devices import DeviceManager
   from lifx_emulator.repositories import DeviceRepository


   @pytest.fixture
   async def emulator(worker_id):
       # worker_id is "master" without xdist, otherwise "gw0", "gw1", ...
       worker_num = 0 if worker_id == "master" else int(worker_id[2:]) + 1
       port = 56700 + worker_num

       device = create_color_light(f"d073d5{worker_num:06d}")
       server = EmulatedLifxServer(
           [device], DeviceManager(DeviceRepository()), "127.0.0.1", port
       )
       async with server:
           yield server
   ```

5. **Wait between tests:**
   ```python
   import asyncio

   await server.stop()
   await asyncio.sleep(0.1)  # Let OS release the port
   ```

### Port Permission Denied

**Problem:** Cannot bind to port (Linux/macOS)

```
PermissionError: [Errno 13] Permission denied
```

**Cause:** Ports below 1024 require root privileges

**Solutions:**

1. **Use port >= 1024 (recommended):**
   ```python
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
   )
   ```

2. **Don't run as root** (security risk)

## Discovery Failures and Debugging

### Client Cannot Find Emulated Devices

**Problem:** LIFX client library discovers nothing

**Diagnostic checklist:**

1. **Check emulator is running:**
   ```bash
   lifx-emulator --verbose
   ```
   Should show: `Starting LIFX Emulator on 127.0.0.1:56700`

2. **Check bind address:**
   ```python
   # only localhost (the default)
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
   )

   # all interfaces
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "0.0.0.0", 56700
   )
   ```

   From the CLI, use `lifx-emulator --bind 0.0.0.0`.

3. **Check firewall:**

   - **Windows:** Allow Python through Windows Firewall
   - **macOS:** System Preferences → Security & Privacy → Firewall → Allow Python
   - **Linux:**
     ```bash
     sudo ufw allow 56700/udp
     ```

4. **Check client port:**

   - Ensure client is looking on the correct port
   - Default LIFX port is 56700
   - If using custom port, client must match

5. **Network isolation:**

   - Docker containers need `--network host` or proper port mapping
   - VMs need bridged networking
   - WSL2 may need port forwarding

6. **Enable verbose logging:**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Discovery Works, but Device Not Responding

**Problem:** Client sees device but times out on commands

**Solutions:**

1. **Check target serial:**

   ```python
   device = create_color_light("d073d5000001")
   print(f"Device serial: {device.state.serial}")
   # Client must target this exact serial
   ```

2. **Check tagged packets:**

   - Broadcast packets have `tagged=True` in header
   - Unicast packets have `tagged=False` and specific target
   - Emulator routes based on target field

3. **Check ack_required and res_required flags:**

   ```python
   # Client should set these flags appropriately
   # ack_required=True → Device sends acknowledgment
   # res_required=True → Device sends state response
   ```

4. **Enable packet logging:**

   ```bash
   lifx-emulator --verbose
   ```
   This shows all packets sent/received:
   ```
   ← RX Device.GetService from 127.0.0.1:54321 (target=broadcast, seq=1) [no payload]
   → TX Device.StateService to 127.0.0.1:54321 (target=d073d5000001, seq=1) [service=1, port=56700]
   ```

### Devices Discovered Multiple Times

**Problem:** Client sees duplicate devices

**Cause:** Multiple emulator instances or broadcast responses

**Solutions:**

1. **Check for multiple instances:**
   ```bash
   ps aux | grep lifx-emulator
   ```

2. **Use unique serials:**
   ```python
   # Wrong - duplicate serials
   device1 = create_color_light("d073d5000001")
   device2 = create_color_light("d073d5000001")  # Same serial!

   # Right - unique serials
   device1 = create_color_light("d073d5000001")
   device2 = create_color_light("d073d5000002")
   ```

3. **Check network interfaces:**
   - Multiple interfaces may cause duplicate broadcasts
   - Bind to specific interface to avoid this

## Timeout Issues

### Client Operations Timeout

**Problem:** Client commands timeout waiting for response

**Diagnostic steps:**

1. **Increase client timeout:**
   Check your client library documentation for details.

2. **Check response scenarios:**

   Scenarios live on the server's `HierarchicalScenarioManager`, not on the device. List what is configured at each scope:
   ```python
   from lifx_emulator.scenarios import get_device_type

   manager = server.scenario_manager
   print(manager.device_scenarios)  # keyed by serial
   print(manager.type_scenarios)  # keyed by device type
   print(manager.location_scenarios)  # keyed by location label
   print(manager.group_scenarios)  # keyed by group label
   print(manager.global_scenario)

   # The merged scenario that applies to one device
   print(
       manager.get_scenario_for_device(
           serial=device.state.serial,
           device_type=get_device_type(device),
           location=device.state.location_label,
           group=device.state.group_label,
       )
   )
   ```
   A configuration such as `ScenarioConfig(drop_packets={102: 1.0})` drops every SetColor (102) request, so the client times out by design. `drop_packets` matches the incoming request type.

3. **Check async context:**
   ```python
   # Wrong - creating the server does not start it
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
   )
   # ... try to communicate ...

   # Right - the server starts on entry and stops on exit
   async with EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
   ) as server:
       ...  # communicate here
   ```

4. **Network latency:**

   Check whether a delay scenario is configured. `response_delays` is keyed by the outgoing response type, so this delays every StateColor (107), the reply to GetColor and SetColor, by 10 seconds:
   ```python
   ScenarioConfig(response_delays={107: 10.0})  # 10 second delay!
   ```

### Tests Timeout in CI/CD

**Problem:** Tests pass locally but timeout in CI

**Solutions:**

1. **Use dynamic ports:**
   ```python
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
   )
   async with server:
       port = server.ipv4_endpoint[1]  # The port the OS assigned
       ...
   ```

2. **Increase pytest timeout** (requires the `pytest-timeout` plugin):
   ```toml
   # pyproject.toml
   [tool.pytest.ini_options]
   timeout = 30
   ```

3. **Widen test fixture scope:**
   ```python
   import pytest_asyncio


   # Module scope for faster tests: one server per test file
   @pytest_asyncio.fixture(scope="module", loop_scope="module")
   async def emulator():
       ...
   ```
   Tests that use a module- or session-scoped server must run on the same event loop, for example with `@pytest.mark.asyncio(loop_scope="module")`. If they run on a different loop, the server's loop is idle during the test and every request times out.

4. **Check CI resource limits:**

   - CI runners may be slower than local machine
   - Increase timeouts for CI environment
   - Use conditional timeouts:
   ```python
   import os
   TIMEOUT = 10 if os.getenv('CI') else 5
   ```

## Protocol Errors and Interpretation

### Invalid Packet Type Errors

**Problem:** "Unknown packet type" errors

**Cause:** Client sending unsupported packet type

**Solution:**

1. **Check protocol version:**

   - Emulator supports LIFX LAN Protocol (November 2025)
   - See https://github.com/LIFX/public-protocol for specification

2. **Check packet type support:**
   ```python
   from lifx_emulator.protocol.packets import PACKET_REGISTRY
   print(f"Supported packet types: {list(PACKET_REGISTRY.keys())}")
   ```

3. **Enable verbose logging:**
   ```bash
   lifx-emulator --verbose
   ```
   Look for: `← RX Unknown packet type XXX from ...`

### Malformed Packet Errors

**Problem:** "Failed to unpack ..." warnings, for example `Failed to unpack Light.SetColor (type 102) from 127.0.0.1:54321: ...`

**Causes:**

- Incorrect header format
- Wrong packet structure
- Byte order issues

**Solutions:**

1. **Check header format:**

   - Header is exactly 36 bytes
   - Target field is 8 bytes (6-byte serial + 2 null bytes)
   - Packet type in bytes 32-33 (little-endian)

2. **Verify packet structure:**
   ```python
   from lifx_emulator.protocol.packets import Light

   # Check expected structure
   print(f"GetColor packet type: {Light.GetColor.PKT_TYPE}")

   # Check payload size
   packet = Light.GetColor()
   data = packet.pack()
   print(f"Payload size: {len(data)} bytes")
   ```

3. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

### Acknowledgment Not Received

**Problem:** Client expects ack but doesn't receive it

**Causes:**

- `ack_required` flag not set in header
- Request dropped by scenario configuration
- Acknowledgement delayed by scenario configuration
- Network issues

**Solutions:**

1. **Check ack_required flag:**
   ```python
   # Client must set ack_required=True in header
   # Emulator automatically sends Acknowledgment (type 45)
   ```

2. **Check scenarios:**

   `drop_packets` matches the incoming request type, and a dropped request gets no acknowledgement either. `response_delays` matches the outgoing packet type, so it can delay the acknowledgement itself:
   ```python
   from lifx_emulator.scenarios import ScenarioConfig

   # Drops every SetColor (102) request: no ack and no StateColor
   ScenarioConfig(drop_packets={102: 1.0})

   # Delays every Acknowledgement (45) by 2 seconds
   ScenarioConfig(response_delays={45: 2.0})
   ```
   Putting `45` in `drop_packets` does not suppress acknowledgements, because clients never send packet type 45.

3. **Enable verbose logging:**
   ```bash
   lifx-emulator --verbose
   ```
   Look for: `→ TX Device.Acknowledgement to ...`

## Performance Problems

### Slow Test Execution

**Problem:** Tests take too long to run

**Solutions:**

1. **Use appropriate fixture scopes:**
   ```python
   # Bad - function scope (starts server for each test)
   @pytest.fixture
   async def emulator():
       ...

   # Good - module scope (starts once per file)
   @pytest.fixture(scope="module")
   async def emulator():
       ...
   ```

2. **Run tests in parallel:**
   ```bash
   pip install pytest-xdist
   pytest -n auto
   ```

3. **Reduce device count:**
   ```python
   # Use only devices you need
   # Wrong - creating 100 devices for a simple test
   devices = [create_color_light(f"d073d5{i:06d}") for i in range(100)]

   # Right - one device is enough
   device = create_color_light("d073d5000001")
   ```

4. **Remove unnecessary delays:**
   ```python
   # Don't do this
   await asyncio.sleep(1)  # Waiting "just in case"

   # The emulator responds instantly (no need to wait)
   ```

5. **Profile your tests:**
   ```bash
   pytest --durations=10
   ```

### High Memory Usage

**Problem:** Emulator consuming too much memory

**Causes:**

- Too many devices
- Large tile/zone counts
- Memory leak in test code

**Solutions:**

1. **Limit device count:**
   ```python
   # Each device uses ~1-5 MB
   # 1000 devices = ~5 GB

   # Use only what you need
   devices = [create_color_light(f"d073d5{i:06d}") for i in range(10)]
   ```

2. **Clean up properly:**
   ```python
   # Ensure server stops and releases resources
   async with server:
       ...  # tests
   # Cleanup happens automatically
   ```

3. **Check for test isolation issues:**
   ```python
   # Are you accumulating state?
   # Use fresh fixtures for each test
   ```

### Packet Loss Under Load

**Problem:** Packets dropped at high throughput

**Causes:**
- OS UDP buffer limits
- CPU saturation
- Network congestion

**Solutions:**

1. **Increase OS UDP buffer:**
   ```bash
   # Linux
   sudo sysctl -w net.core.rmem_max=26214400
   sudo sysctl -w net.core.rmem_default=26214400
   ```

2. **Reduce packet rate:**
   ```python
   # Add small delays between packets
   for i in range(1000):
       await send_packet()
       await asyncio.sleep(0.001)  # 1ms delay
   ```

3. **Check CPU usage:**
   ```bash
   # Monitor while running tests
   htop  # or top on macOS/Linux
   ```

## Platform-Specific Issues

### Windows Issues

**Problem:** Tests fail only on Windows

**Common issues:**

1. **Event loop policy:**

   No change is needed. The default Proactor event loop on Windows supports the UDP sockets the emulator uses. Remove any `asyncio.set_event_loop_policy()` call you added as a workaround: event loop policies are deprecated from Python 3.14.

2. **Firewall prompts:**
   - Windows Defender may prompt to allow Python
   - Allow for private networks
   - Or use 127.0.0.1 binding (no firewall prompt)

3. **Path separators:**
   ```python
   # Use pathlib for cross-platform paths
   from pathlib import Path

   config_path = Path(__file__).parent / "config.yaml"
   ```

4. **Line endings:**
   - Git may convert line endings (CRLF vs LF)
   - Configure `.gitattributes`:
   ```
   *.py text eol=lf
   ```

### macOS Issues

**Problem:** Tests fail only on macOS

**Common issues:**

1. **Firewall blocks UDP:**
   - System Preferences → Security & Privacy → Firewall
   - Click "Firewall Options"
   - Add Python and allow incoming connections

2. **Too many open files:**
   ```bash
   # Check limit
   ulimit -n

   # Increase limit
   ulimit -n 4096
   ```

3. **Gatekeeper blocking Python:**
   ```bash
   # If Python was downloaded (not from App Store)
   xattr -d com.apple.quarantine /path/to/python
   ```

### Linux Issues

**Problem:** Tests fail only on Linux

**Common issues:**

1. **Port binding requires root (ports < 1024):**
   ```python
   from lifx_emulator import EmulatedLifxServer
   from lifx_emulator.devices import DeviceManager
   from lifx_emulator.repositories import DeviceRepository

   # Solution: Use ports >= 1024
   server = EmulatedLifxServer(
       [device], DeviceManager(DeviceRepository()), "127.0.0.1", 56700
   )
   ```

2. **Too many open files:**
   ```bash
   # Check limits
   ulimit -n
   cat /proc/sys/fs/file-max

   # Increase limit temporarily
   ulimit -n 4096

   # Increase permanently (add to /etc/security/limits.conf)
   * soft nofile 4096
   * hard nofile 8192
   ```

3. **SELinux or AppArmor restrictions:**
   ```bash
   # Check SELinux
   getenforce

   # Check AppArmor
   sudo aa-status

   # May need to configure policies for network access
   ```

### WSL (Windows Subsystem for Linux) Issues

**Problem:** Issues specific to WSL

**Common issues:**

1. **Port forwarding:**
   - WSL2 uses virtual network
   - Ports may not be accessible from Windows
   - Workaround: Use `0.0.0.0` binding and Windows firewall rules

2. **Network latency:**
   - WSL2 has slight network overhead
   - May need longer timeouts

3. **File permissions:**
   - Files on Windows filesystem (e.g., /mnt/c/) have weird permissions
   - Use Linux filesystem (e.g., ~/projects/)

## Logging and Debugging Techniques

### Enable Verbose Logging

**Basic logging:**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Emulator-specific logging:**

```python
# Enable only emulator logs
logging.getLogger('lifx_emulator').setLevel(logging.DEBUG)
```

**CLI verbose mode:**

```bash
lifx-emulator --verbose
```

Output (timestamps and field lists trimmed):
```
← RX Device.GetService from 127.0.0.1:54321 (target=broadcast, seq=1) [no payload]
→ TX Device.StateService to 127.0.0.1:54321 (target=d073d5000001, seq=1) [service=1, port=56700]
← RX Light.GetColor from 127.0.0.1:54321 (target=d073d5000001, seq=2) [no payload]
→ TX Light.StateColor to 127.0.0.1:54321 (target=d073d5000001, seq=2) [color=..., power=..., label=...]
```

### Inspect Device State

**During tests:**

```python
import pytest

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest.fixture
async def emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server, device  # Expose device for inspection


async def test_color_change(emulator):
    server, device = emulator

    # ... send SetColor command ...

    # Inspect device state
    print(f"Device color: {device.state.color}")
    print(f"Device power: {device.state.power_level}")
    assert device.state.color.hue == expected_hue
```

### Packet Capture with Wireshark/tcpdump

**Capture UDP packets:**

```bash
# Linux/macOS - tcpdump
sudo tcpdump -i lo -n udp port 56700 -X

# Wireshark
# Filter: udp.port == 56700
```

**Analyze LIFX packets:**
- First 36 bytes: LIFX header
- Bytes 32-33: Packet type (little-endian)
- Remaining bytes: Payload

### Use pytest Debugging

**Drop into debugger on failure:**

```bash
pytest --pdb
```

**Drop into debugger on first failure:**

```bash
pytest -x --pdb
```

**Set breakpoint in test:**

```python
async def test_something(emulator):
    device = ...
    breakpoint()  # Python 3.7+
    # or
    import pdb; pdb.set_trace()
```

### Enable pytest output:**

```bash
# Show print() output
pytest -s

# Show test names as they run
pytest -v

# Both
pytest -sv
```

## Common Error Messages

### "TypeError: 'NoneType' object is not subscriptable" (or requests silently time out)

**Cause:** Attempting to use the server before starting it. Creating an `EmulatedLifxServer` does not bind any sockets, so `server.ipv4_endpoint` is `None` and nothing answers requests.

**Fix:**
```python
from lifx_emulator import EmulatedLifxServer
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository

device_manager = DeviceManager(DeviceRepository())

# Wrong
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
)
port = server.ipv4_endpoint[1]  # TypeError: server not started!

# Right
server = EmulatedLifxServer(
    [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
)
async with server:
    port = server.ipv4_endpoint[1]  # Server is running
    await send_command()
```

### "ValueError: Serial must be exactly 12 ASCII hexadecimal characters"

**Cause:** Serial not 12 hex characters

**Fix:**
```python
# Wrong
device = create_color_light("123")
device = create_color_light("d073d500001")  # 11 chars

# Right
device = create_color_light("d073d5000001")  # 12 chars
```

### "TypeError: Object of type 'bytes' is not JSON serializable"

**Cause:** Trying to serialize device state with bytes

**Context:** Usually happens with custom serialization

**Fix:**
```python
# Convert bytes fields (location_id, group_id, mac_address) to hex strings
location_id = device.state.location_id.hex()
```

### "SyntaxError: 'await' outside async function"

**Cause:** Using async operations outside async context

**Fix:**
```text
# Wrong
def test_device():
    await server.start()  # Can't await in sync function
```

```python
import asyncio


# Right
async def test_device():
    await server.start()  # Now it works

# Or use asyncio.run() outside pytest
def main():
    asyncio.run(async_main())
```

### "DeprecationWarning: There is no current event loop"

**Cause:** Calling `asyncio.get_event_loop()` when no event loop is running. Python 3.10 and later deprecate this, and Python 3.14 raises `RuntimeError` instead.

**Fix:**

- Inside a coroutine, use `asyncio.get_running_loop()`.
- Outside one, start the loop with `asyncio.run(main())` instead of fetching a loop yourself.
- In pytest, write `async def` tests and fixtures and let pytest-asyncio manage the loop. Don't override the `event_loop` fixture: pytest-asyncio 1.0 removed it. To share a server across tests, use `loop_scope` instead:

```python
# In conftest.py
import pytest_asyncio

from lifx_emulator import EmulatedLifxServer, create_color_light
from lifx_emulator.devices import DeviceManager
from lifx_emulator.repositories import DeviceRepository


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer(
        [device], DeviceManager(DeviceRepository()), "127.0.0.1", 0
    )
    async with server:
        yield server
```

Tests that use this fixture need `@pytest.mark.asyncio(loop_scope="session")` so they run on the same loop as the server.

## Getting Help

If you're still stuck after trying these solutions:

1. **Check existing issues:** https://github.com/Djelibeybi/lifx-emulator/issues
2. **Search documentation:** Use the search feature in the docs
3. **Ask in discussions:** https://github.com/Djelibeybi/lifx-emulator/discussions
4. **File a bug report:** https://github.com/Djelibeybi/lifx-emulator/issues/new

**When reporting issues, include:**
- Python version (`python --version`)
- Operating system (Linux/macOS/Windows, version)
- lifx-emulator version (`pip show lifx-emulator`)
- Minimal reproduction code
- Error messages and stack traces
- What you've already tried

## See Also

- [FAQ](../faq.md) - Common questions and answers
- [Best Practices](../guide/best-practices.md) - Patterns and anti-patterns
- [Integration Testing](../guide/integration-testing.md) - pytest patterns
- [Glossary](glossary.md) - Terminology reference
