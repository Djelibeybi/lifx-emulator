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
   # Let OS assign available port
   server = EmulatedLifxServer([device], "127.0.0.1", 0)
   await server.start()
   print(f"Server running on port {server.port}")
   ```

4. **Use port offset in parallel tests:**
   ```python
   @pytest.fixture
   async def emulator(worker_id):

         port = 56700 + int(worker_num) + 1

       device = create_color_light(f"d073d5{worker_num:06d}")
       server = EmulatedLifxServer([device], "127.0.0.1", port)
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
   server = EmulatedLifxServer([device], "127.0.0.1", 56700)
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
   Should show: `Emulator listening on 127.0.0.1:56700`

2. **Check bind address:**
   ```python
   # only localhost
   server = EmulatedLifxServer([device], "127.0.0.1", 56700)

   # all interfaces
   server = EmulatedLifxServer([device], "0.0.0.0", 56700)
   ```

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
   RX: GetService (2) from ('127.0.0.1', 54321)
   TX: StateService (3) to ('127.0.0.1', 54321)
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
   ```python
   # Are you testing timeouts intentionally?
   device.scenarios = {
       'drop_packets': {102: 1.0},  # Will cause timeouts
   }
   ```

3. **Check async context:**
   ```python
   # Wrong - server has to be started manually
   server = EmulatedLifxServer([device], "127.0.0.1", 56700)
   # ... try to communicate ...

   # Right - server starts automatically
   async with EmulatedLifxServer([device], "127.0.0.1", 56700) as server:
       # ... communicate here ...
   ```

4. **Network latency:**
   ```python
   # Check if delay scenarios are configured
   device.scenarios = {
       'response_delays': {102: 10.0},  # 10 second delay!
   }
   ```

### Tests Timeout in CI/CD

**Problem:** Tests pass locally but timeout in CI

**Solutions:**

1. **Use dynamic ports:**
   ```python
   def get_free_port() -> int:
    """Get a free UDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

   port = get_free_port()
   server = EmulatedLifxServer([device], "127.0.0.1", port)
   ```

2. **Increase pytest timeout:**
   ```python
   # pytest.ini or pyproject.toml
   [tool.pytest.ini_options]
   timeout = 30
   ```

3. **Reduce test fixture scope:**
   ```python
   # Module scope for faster tests
   @pytest.fixture(scope="module")
   async def emulator():
       ...
   ```

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
   Look for: `Unknown packet type: XXX`

### Malformed Packet Errors

**Problem:** "Failed to unpack packet" errors

**Causes:**

- Incorrect header format
- Wrong packet structure
- Byte order issues

**Solutions:**

1. **Check header format:**

   - Header is exactly 36 bytes
   - Target field is 8 bytes (6-byte MAC + 2 null bytes)
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
- Packet dropped by scenario configuration
- Network issues

**Solutions:**

1. **Check ack_required flag:**
   ```python
   # Client must set ack_required=True in header
   # Emulator automatically sends Acknowledgment (type 45)
   ```

2. **Check scenarios:**
   ```python
   # Is ack being dropped?
   device.scenarios = {
       'drop_packets': {45: 1.0},  # Drops acknowledgments!
   }
   ```

3. **Enable verbose logging:**
   ```bash
   lifx-emulator --verbose
   ```
   Look for: `TX: Acknowledgment (45) to ...`

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
       # ... tests ...
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
   ```python
   # Add to conftest.py or test setup
   import sys
   import asyncio

   if sys.platform == 'win32':
       asyncio.set_event_loop_policy(
           asyncio.WindowsProactorEventLoopPolicy()
       )
   ```

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
   # Solution: Use ports >= 1024
   server = EmulatedLifxServer([device], "127.0.0.1", 56700)
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

Output:
```
RX: GetService (2) from ('127.0.0.1', 54321)
TX: StateService (3) to ('127.0.0.1', 54321)
RX: GetColor (101) from ('127.0.0.1', 54321) target=d073d5000001
TX: StateColor (107) to ('127.0.0.1', 54321)
```

### Inspect Device State

**During tests:**

```python
@pytest.fixture
async def emulator():
    device = create_color_light("d073d5000001")
    server = EmulatedLifxServer([device], "127.0.0.1", 56700)
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

### "RuntimeError: Server not running"

**Cause:** Attempting to use server before starting

**Fix:**
```python
# Wrong
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
await send_command()  # Server not started!

# Right
server = EmulatedLifxServer([device], "127.0.0.1", 56700)
async with server:
    await send_command()  # Server is running
```

### "ValueError: Invalid serial format"

**Cause:** Serial number not 12 hex characters

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
import base64

# Convert bytes to base64 string
serial_str = base64.b64encode(device.state.serial_bytes).decode('ascii')
```

### "SyntaxError: 'await' outside async function"

**Cause:** Using async operations outside async context

**Fix:**
```python
# Wrong
def test_device():
    await server.start()  # Can't await in sync function

# Right
async def test_device():
    await server.start()  # Now it works

# Or use asyncio.run()
def test_device():
    asyncio.run(async_main())
```

### "DeprecationWarning: There is no current event loop"

**Cause:** Python 3.10+ changed event loop behavior

**Fix:**
```python
# In conftest.py
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

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
