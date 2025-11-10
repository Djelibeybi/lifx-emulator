# Frequently Asked Questions

Common questions about the LIFX Emulator and their answers.

## Quick Answers

### Port conflicts?
→ See [Best Practices - Port Management](guide/best-practices.md#port-management)

### Test too slow?
→ See [Best Practices - Performance](guide/best-practices.md#performance-considerations)

### Discovery not working?
→ See [Troubleshooting - Discovery Failures](reference/troubleshooting.md#discovery-failures-and-debugging)

### Protocol errors?
→ See [Troubleshooting - Protocol Errors](reference/troubleshooting.md#protocol-errors-and-interpretation)

### Need examples?
→ See [Tutorials](tutorials/index.md) and [Examples](tutorials/02-basic.md)

## General Questions

### What is the LIFX Emulator?

The LIFX Emulator is a virtual LIFX device implementation that speaks the LIFX LAN protocol. It allows you to test LIFX client libraries and applications without needing physical LIFX devices.

### Why use the emulator instead of real devices?

**Advantages of the emulator:**

- **Cost:** No need to purchase physical devices (a single LIFX device costs $60-350+)
- **Speed:** Instant device creation, no setup time
- **Availability:** Always available, no dependency on hardware
- **Scalability:** Test with 100+ devices on one machine
- **Control:** Precise control over device state and behavior
- **Error injection:** Simulate network issues, firmware bugs, edge cases
- **Reproducibility:** Consistent test results, no flaky hardware
- **CI/CD:** Run tests in automated pipelines without hardware

**When to use real devices:**

- Testing hardware-specific behavior
- Validating WiFi/network stack issues
- Final integration testing before release
- Testing firmware update mechanisms
- Verifying physical device interactions (buttons, etc.)

See also: [Best Practices - When to Use the Emulator](guide/best-practices.md#when-to-use-the-emulator)

### Why LIFX Emulator vs other testing approaches?

**Comparison with alternatives:**

| Approach | Speed | Accuracy | Setup | Cost | Error Testing |
|----------|-------|----------|-------|------|---------------|
| **LIFX Emulator** | ⚡ Fast | ✅ High | 🟢 Easy | 💰 Free | ✅ Excellent |
| **Mocking** | ⚡⚡ Fastest | ⚠️ Low | 🟢 Easy | 💰 Free | ⚠️ Limited |
| **VCR/Recording** | ⚡ Fast | ✅ High | 🟡 Medium | 💰 Free | ❌ None |
| **Real Devices** | 🐌 Slow | ✅✅ Perfect | 🔴 Hard | 💰💰 Expensive | ❌ Difficult |

**Use the emulator when:**

- Testing LIFX protocol implementation
- Integration testing your application
- Running tests in CI/CD
- Testing error handling and edge cases

**Use mocks when:**

- Unit testing business logic
- Speed is critical
- Testing code that uses LIFX, not the protocol itself

**Use real devices when:**

- Final validation before production release
- Testing hardware-specific features
- Verifying WiFi behavior

### What protocol version is supported?

The emulator implements the **LIFX LAN Protocol** as documented at https://lan.developer.lifx.com.

**Protocol compliance:**

- ✅ Full header support (36 bytes)
- ✅ Device discovery (GetService, StateService)
- ✅ Device messages (label, location, group, power, etc.)
- ✅ Light messages (color, brightness, effects)
- ✅ MultiZone messages (standard and extended)
- ✅ Tile/Matrix messages (Get64, Set64)
- ✅ HEV/Clean messages
- ✅ Infrared messages

**Protocol version:** Compatible with protocol as of November 2025

### How accurate is the emulation?

**What's accurate:**

- ✅ Binary protocol implementation (packet structure, types, serialization)
- ✅ Device state management (color, power, zones, tiles)
- ✅ Packet acknowledgment (ack_required, res_required)
- ✅ Broadcast vs unicast handling
- ✅ Multi-device support
- ✅ Device capabilities (color, multizone, matrix, HEV, infrared)

**What's approximated:**

- ⚠️ Timing (real devices may have different response times)
- ⚠️ Firmware behavior (emulator uses generalized logic)
- ⚠️ Hardware limitations (real devices have memory/CPU constraints)

**What's not emulated:**

- ❌ WiFi/network layer (emulator uses UDP directly)
- ❌ Firmware updates
- ❌ Physical buttons or sensors
- ❌ Actual light output (brightness, color rendering)
- ❌ Power consumption

**Accuracy rating:** ~95% for protocol testing, ~70% for real-world behavior

### Can I use this in production?

**No, the emulator is for testing only.**

**Appropriate uses:**

- ✅ Development and testing
- ✅ CI/CD pipelines
- ✅ Integration tests
- ✅ Demonstrations (with disclaimers)
- ✅ Protocol exploration and learning

**Not appropriate for:**

- ❌ Production control systems
- ❌ Customer-facing deployments
- ❌ Critical infrastructure
- ❌ Safety-critical applications

**Why not production?**

- No reliability guarantees
- May have undiscovered bugs
- Not validated against all edge cases
- No security hardening
- No official support from LIFX

## Performance Questions

### How many devices can I emulate?

**Practical limits:**

- **Typical usage:** 1-10 devices (most common)
- **Stress testing:** 50-100 devices (depends on hardware)
- **Maximum tested:** 500+ devices (on powerful hardware)

**Limiting factors:**

- Available RAM (each device uses ~1-5 MB)
- CPU for packet processing
- Network bandwidth (UDP packet throughput)
- Operating system limits (file descriptors, ports)

**Performance tips:**

- Use a single server with multiple devices (not multiple servers)
- Minimize device state updates
- Use appropriate test fixture scopes
- Run tests in parallel with pytest-xdist

### How many packets per second can it handle?

**Typical performance:**

- **Single device:** ~1,000-10,000 packets/sec
- **10 devices:** ~500-5,000 packets/sec
- **100 devices:** ~100-1,000 packets/sec

**Factors affecting performance:**

- Hardware (CPU, RAM)
- Packet type (simple vs complex)
- Python interpreter (CPython vs PyPy)
- Operating system
- Concurrent clients

**Optimization:**

- Emulator uses asyncio for concurrency
- Packet processing is lightweight
- Most time spent in serialization/deserialization

## Platform Questions

### What platforms are supported?

**Fully supported:**

- ✅ **Linux** (Ubuntu, Debian, Fedora, etc.)
- ✅ **macOS** (Intel and Apple Silicon)
- ✅ **Windows** (Windows 10/11)
- ✅ **WSL** (Windows Subsystem for Linux)

**Requirements:**

- Python 3.11 or newer
- asyncio support
- UDP networking

**Platform-specific notes:**

**Windows:**

- May need `WindowsProactorEventLoopPolicy` for asyncio
- Firewall may prompt for UDP access
- Use dynamic port allocation in tests

**macOS:**

- Works on both Intel and Apple Silicon (M1/M2/M3)
- May need to allow Python through firewall

**WSL:**

- Works well for development and testing
- UDP networking functions correctly
- Port conflicts rare

### Does it work in Docker?

**Yes!** The emulator works great in Docker.

**Example Dockerfile:**

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

EXPOSE 56700/udp

CMD ["lifx-emulator", "--color", "3"]
```

**Docker tips:**

- Expose UDP port 56700 (or your custom port)
- Bind to `0.0.0.0` for container networking
- Use Docker networks for multi-container testing
- Map volumes for persistent storage

See also: [CI/CD Integration Tutorial](tutorials/05-cicd.md#docker-integration)

### Does it work in CI/CD?

**Yes!** Designed specifically for CI/CD.

**Supported CI platforms:**

- ✅ GitHub Actions
- ✅ GitLab CI
- ✅ CircleCI
- ✅ Travis CI
- ✅ Jenkins
- ✅ Azure Pipelines

**CI/CD best practices:**

- Use dynamic port allocation
- Run tests in parallel
- Cache pip/uv dependencies
- Use pytest-xdist for speed
- Set appropriate timeouts

See also: [CI/CD Integration Tutorial](tutorials/05-cicd.md)

## Feature Questions

### Can I emulate specific firmware versions?

**Yes!** Use the `firmware_version` scenario:

```python
device = create_color_light("d073d5000001")

# Emulate firmware version 3.70
device.scenarios = {
    'firmware_version': (3, 70)
}
```

**Use cases:**

- Test version detection logic
- Verify compatibility with old firmware
- Test upgrade/migration code
- Ensure graceful degradation

**Note:** This only changes the *reported* version, not actual behavior.

See also: [Testing Scenarios Guide](guide/testing-scenarios.md#6-custom-firmware-version-firmware_version)

### Does it support firmware updates?

**No.** The emulator does not support firmware update mechanisms.

**Why not:**

- Firmware updates are hardware-specific
- Would require implementing entire update protocol
- Not needed for most testing scenarios
- Real devices needed for firmware testing

### Can I test device discovery?

**Yes!** The emulator fully supports discovery.

**How it works:**

- Emulator responds to GetService (type 2) broadcasts
- Returns StateService with port number
- Clients can discover devices as usual

**Example:**

```python
# Emulator side
device = create_color_light("d073d5000001")
server = EmulatedLifxServer([device], "0.0.0.0", 56700)  # Bind to all interfaces

# Client side (using any LIFX library)
# Discovery will find the emulated device
```

**Discovery tips:**

- Bind to `0.0.0.0` for network-wide discovery
- Bind to `127.0.0.1` for localhost-only discovery
- Ensure firewall allows UDP traffic
- Use correct port (default: 56700)

### Can I test multizone effects?

**Yes!** Multizone effects are supported.

**Available effects:**

- MOVE effect (packet type 510/511)

**Example:**
```python
strip = create_multizone_light("d073d8000001", zone_count=16)

# Device responds to:
# - GetColorZones (502) / SetColorZones (503)
# - GetMultiZoneEffect (510) / SetMultiZoneEffect (511)
# - GetExtendedColorZones (506) / SetExtendedColorZones (512)
```

### Can I test tile patterns?

**Yes!** Tile/matrix devices are fully supported.

**Tile features:**

- Multiple tiles per device (up to 5 or more)
- Get64/Set64 for zone updates
- GetDeviceChain for tile info
- Custom tile dimensions (8x8, 16x8, 5x6)

**Example:**

```python
tiles = create_tile_device("d073d9000001", tile_count=5)

# Each tile has 64 zones (8x8)
# Responds to Get64 (707) and Set64 (715) packets
```

## Troubleshooting Questions

### Why can't my client find the emulated device?

**Common causes:**

1. **Wrong network interface**
   - Solution: Bind to `0.0.0.0` instead of `127.0.0.1`

2. **Port conflict**
   - Solution: Use dynamic port allocation or check for conflicts

3. **Firewall blocking UDP**
   - Solution: Allow Python through firewall (Windows/macOS)

4. **Client looking on wrong port**
   - Solution: Ensure client uses port 56700 (or your custom port)

5. **Emulator not running**
   - Solution: Verify emulator started successfully

See also: [Troubleshooting Guide](reference/troubleshooting.md#discovery-failures-and-debugging)

### Why are my tests slow?

**Common causes:**

1. **Too many devices**
   - Solution: Use only devices you need

2. **Function-scoped fixtures**
   - Solution: Use module or session scope when appropriate

3. **Sequential test execution**
   - Solution: Use pytest-xdist for parallel tests

4. **Unnecessary delays**
   - Solution: Remove artificial sleep() calls

5. **Slow client library**
   - Solution: Profile your client code

See also: [Best Practices - Performance Considerations](guide/best-practices.md#performance-considerations)

### How do I debug protocol issues?

**Debugging techniques:**

1. **Enable verbose logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Use --verbose flag:**
   ```bash
   lifx-emulator --verbose
   ```

3. **Check packet types:**
   ```python
   from lifx_emulator.protocol.packets import Light
   print(f"GetColor: {Light.GetColor.PKT_TYPE}")
   ```

4. **Inspect device state:**
   ```python
   print(f"Device state: {device.state}")
   ```

5. **Use network sniffer:**
   - Wireshark or tcpdump to see actual UDP packets

See also: [Troubleshooting Guide](reference/troubleshooting.md)

### Where do I report bugs?

**Bug reports:**
- 🐛 GitHub Issues: https://github.com/Djelibeybi/lifx-emulator/issues

**Before reporting:**

1. Check existing issues
2. Update to latest version
3. Reproduce with minimal example
4. Collect relevant information:
   - Python version
   - Operating system
   - lifx-emulator version
   - Error messages
   - Minimal reproduction code

**Good bug report includes:**

- Clear description of issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Code example
- Error messages/stack traces

## Version Compatibility

### What Python versions are supported?

**Required:** Python 3.11 or newer

**Tested on:**
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13
- ✅ Python 3.14

**Not supported:**
- ❌ Python 3.10 and older

**Why Python 3.11+?**
- Modern async features
- Performance improvements
- Type hints improvements
- Better error messages

### What are the differences from real devices?

**Protocol differences:**
- ✅ Emulator implements protocol exactly as documented
- ⚠️ Real devices may have firmware quirks
- ⚠️ Real devices may have timing differences

**Behavioral differences:**
- 🔴 Emulator responds instantly (no physical light transition)
- 🔴 Emulator has no memory/CPU constraints
- 🔴 Emulator doesn't model WiFi issues
- 🔴 Emulator doesn't have button inputs

**State differences:**
- ✅ Color, power, zones, tiles: accurate
- ⚠️ Signal strength, WiFi info: stubbed
- ⚠️ Uptime, reboot count: simplified

**Best practice:** Use emulator for protocol testing, real devices for final validation.

## Getting Help

### Where can I find more documentation?

**Documentation sections:**

- 📖 [Getting Started](getting-started/quickstart.md)
- 📖 [Tutorials](tutorials/index.md)
- 📖 [User Guide](guide/index.md)
- 📖 [API Reference](api/index.md)
- 📖 [Troubleshooting](reference/troubleshooting.md)
- 📖 [Glossary](reference/glossary.md)

### How do I contribute?

**Contributions welcome!**

- 🎯 GitHub: https://github.com/Djelibeybi/lifx-emulator

**Ways to contribute:**

- Report bugs
- Suggest features
- Improve documentation
- Submit pull requests
- Help others in issues

### Is there a community?

**Official resources:**

- GitHub Discussions: https://github.com/Djelibeybi/lifx-emulator/discussions
- GitHub Issues: https://github.com/Djelibeybi/lifx-emulator/issues

## Still Have Questions?

If your question isn't answered here:

1. **Check the [Glossary](reference/glossary.md)** for terminology
2. **Read the [Troubleshooting Guide](reference/troubleshooting.md)** for common issues
3. **Browse the [Tutorials](tutorials/index.md)** for usage examples
4. **Search [GitHub Issues](https://github.com/Djelibeybi/lifx-emulator/issues)** for similar questions
5. **Ask in [GitHub Discussions](https://github.com/Djelibeybi/lifx-emulator/discussions)**

We're here to help! 🎉
