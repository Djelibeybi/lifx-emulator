# Product Guidelines

## Voice and Tone

Professional and technical. Documentation, error messages, and UI text should be clear, precise, and assume familiarity with networking and IoT concepts.

## Design Principles

1. **Protocol fidelity first** — Emulated devices must behave exactly like real LIFX hardware. If a real device sends a specific response format, the emulator must match it byte-for-byte. Deviations from the protocol specification are bugs.

2. **Developer experience** — Clear APIs, good defaults, minimal configuration. A developer should be able to start emulating devices with a single command. Product-specific defaults (zone counts, tile dimensions, firmware versions) come from the specs system so users don't need to configure them manually.

## Terminology

- Use "large matrix device" or "chained matrix device" — never "wide tile device"
- Use "multizone" for linear LED strips (LIFX Z, Beam, Neon, String)
- Use "matrix" for 2D LED panels (LIFX Tile, Ceiling, Candle, Luna)
