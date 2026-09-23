#!/usr/bin/env python3
"""Diagnose public health signals after closing real spike-owned transports.

Private engine access is used only for fault injection and observation. It is
not a proposed detector or supported integration API. No library is patched.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import threading
from datetime import UTC, datetime
from pathlib import Path

import zeroconf
from mdns_spike_inputs.zeroconf_recovery import RecoveryPrototype
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncZeroconf


async def run_probe():
    owners = []
    loop_errors = []
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()

    def on_error(_loop, context):
        loop_errors.append(
            {
                "message": context.get("message"),
                "exception_type": type(context.get("exception")).__name__,
            }
        )

    def factory():
        owner = AsyncZeroconf(interfaces=["127.0.0.1"], ip_version=IPVersion.V4Only)
        owners.append(owner)
        return owner

    adapter = RecoveryPrototype(factory)
    loop.set_exception_handler(on_error)
    result = {}
    try:
        assert await adapter.retry_mdns([])
        owner = owners[-1]
        zc = owner.zeroconf
        await zc.async_wait_for_start()
        # Diagnostic-only access: close every real transport owned by this
        # disposable instance, without marking Zeroconf itself as shut down.
        transports = list(
            {wrapped.transport for wrapped in [*zc.engine.readers, *zc.engine.senders]}
        )
        assert transports and all(not item.is_closing() for item in transports)
        result["before"] = {
            "started": zc.started,
            "done": zc.done,
            "adapter_status": adapter.mdns_status,
            "transport_count": len(transports),
        }
        for transport in transports:
            transport.close()
        await asyncio.sleep(0.1)
        try:
            await zc.async_wait_for_start(timeout=0.1)
            wait_result = "returned normally"
        except Exception as error:
            wait_result = type(error).__name__
        result["after_transport_close"] = {
            "all_transports_closing": all(t.is_closing() for t in transports),
            "all_socket_fds_closed": all(
                t.get_extra_info("socket").fileno() == -1 for t in transports
            ),
            "started": zc.started,
            "done": zc.done,
            "wait_for_start": wait_result,
            "adapter_status": adapter.mdns_status,
            "adapter_error": adapter.mdns_error,
            "loop_errors": list(loop_errors),
        }
        try:
            await owner.async_update_interfaces(["127.0.0.1"])
            refresh_result = "returned normally"
        except Exception as error:
            refresh_result = type(error).__name__
        result["same_interface_refresh"] = {
            "result": refresh_result,
            "original_transports_still_closed": all(t.is_closing() for t in transports),
            "open_reader_count": sum(
                not w.transport.is_closing() for w in zc.engine.readers
            ),
            "started": zc.started,
        }
    finally:
        await adapter.stop()
        await asyncio.sleep(0.1)
        loop.set_exception_handler(previous_handler)
    result["cleanup"] = {
        "adapter_status": adapter.mdns_status,
        "pending_tasks": len(
            [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        ),
        "threads": [t.name for t in threading.enumerate()],
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = Path(zeroconf.__file__).parent
    result = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "zeroconf": importlib.metadata.version("zeroconf"),
        "scope": "local loopback; transport-close injection, not an OS outage",
        "sha256": {
            name: hashlib.sha256((package / name).read_bytes()).hexdigest()
            for name in ["_listener.py", "_core.py", "_engine.py", "asyncio.py"]
        },
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(
            (
                Path(__file__).parent / "mdns_spike_inputs/zeroconf_recovery.py"
            ).read_bytes()
        ).hexdigest(),
    }
    try:
        result["observations"] = asyncio.run(run_probe())
    except Exception as error:
        result["probe_error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
