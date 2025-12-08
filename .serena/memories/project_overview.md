# Project Overview

## Purpose
LIFX Emulator is a comprehensive LIFX device emulator for testing LIFX LAN protocol libraries. It implements the complete binary UDP protocol from https://lan.developer.lifx.com and emulates various LIFX device types without requiring physical hardware.

## Architecture Type
**Monorepo** with two independent packages managed by uv workspace

## Packages

### 1. lifx-emulator-core (Library)
- **PyPI Name**: `lifx-emulator-core`
- **Import Name**: `lifx_emulator`
- **Purpose**: Core emulator library for embedding in other projects
- **Location**: `packages/lifx-emulator-core/`
- **Dependencies**: `pydantic`, `pyyaml`
- **Current Version**: 3.0.3

### 2. lifx-emulator (Standalone)
- **PyPI Name**: `lifx-emulator`
- **Import Name**: `lifx_emulator_app`
- **Purpose**: CLI + HTTP management API for running the emulator
- **Location**: `packages/lifx-emulator/`
- **Dependencies**: `lifx-emulator-core`, `fastapi`, `uvicorn`, `cyclopts`, `rich`

## Key Features
- Complete LIFX LAN protocol support (44+ packet types)
- Multiple device types: color lights, infrared, HEV, multizone strips, matrix tiles, switches
- REST API and web interface for runtime monitoring and management
- Testing scenarios: packet loss, delays, malformed responses
- Persistent storage for device state across restarts
- Product registry with 137+ real LIFX products

## Technology Stack
- **Language**: Python 3.11+ (supports 3.11, 3.12, 3.13, 3.14)
- **Package Manager**: uv (modern Python package manager)
- **Async Framework**: asyncio (native Python async/await)
- **Web Framework**: FastAPI (for HTTP API)
- **Type System**: Pyright in standard mode with full type hints
- **Data Validation**: Pydantic v2
- **Build System**: Hatchling
- **Testing**: pytest with pytest-asyncio, pytest-cov
- **Documentation**: MkDocs with Material theme

## Repository Information
- **License**: UPL-1.0 (Universal Permissive License)
- **Repository**: https://github.com/djelibeybi/lifx-emulator
- **Documentation**: https://djelibeybi.github.io/lifx-emulator/
- **Maintainer**: Avi Miller <me@dje.li>
