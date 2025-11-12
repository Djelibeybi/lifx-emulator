# Architecture

Deep dive into how the LIFX Emulator works internally.

## Overview

This section explains the internal architecture of the LIFX Emulator. Understanding this helps you:

- Debug issues more effectively
- Contribute to the project
- Extend the emulator for custom use cases
- Understand protocol implementation details

## Prerequisites

Before reading this section, you should:

- Have used the emulator in basic scenarios
- Understand LIFX device types
- Have basic knowledge of networking (UDP)
- Be familiar with Python async/await

## Learning Path

Read these pages in order from high-level to implementation details:

1. **[Architecture Overview](overview/)** - System design and component interaction
1. **[Packet Flow](packet-flow/)** - How packets are received and processed
1. **[Device State](device-state/)** - State management and capabilities
1. **[Protocol Details](protocol/)** - Binary protocol implementation

## Quick Concepts

### Layered Architecture

The emulator uses a layered architecture:

```text
┌─────────────────────┐
│  LIFX Client        │  Your library/app
└──────────┬──────────┘
           │ UDP
┌──────────▼──────────┐
│  Server Layer       │  Packet routing
├─────────────────────┤
│  Device Layer       │  Device logic
├─────────────────────┤
│  Protocol Layer     │  Binary packets
├─────────────────────┤
│  State Layer        │  Device state
└─────────────────────┘
```

### Key Components

- **EmulatedLifxServer**: UDP server that routes packets to devices
- **EmulatedLifxDevice**: Individual virtual device with state and logic
- **LifxHeader**: 36-byte packet header parser/generator
- **Packet Classes**: 44+ packet type implementations
- **DeviceState**: Dataclass holding device state

### Protocol Implementation

The LIFX LAN protocol is a binary UDP protocol. The emulator:

1. Receives UDP packets on port 56700
1. Parses the 36-byte header
1. Routes to target device(s) by serial
1. Unpacks payload to packet object
1. Executes device-specific handler
1. Generates response packet(s)
1. Sends UDP response(s)

## Next Steps

Start with the [Architecture Overview](overview/) for a high-level understanding, then progress through the other pages for deeper details.
