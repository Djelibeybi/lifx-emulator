"""Regression coverage for protocol edits and durable storage transactions."""

import asyncio
import threading
from unittest.mock import patch

import pytest
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.devices.persistence import (
    DevicePersistenceAsyncFile,
    DevicePersistenceError,
)
from lifx_emulator.factories import create_color_light
from lifx_emulator.protocol.header import LifxHeader
from lifx_emulator.protocol.packets import Device
from lifx_emulator.repositories import DeviceRepository


async def test_durable_commit_preserves_interleaved_protocol_mutation(tmp_path):
    """An acknowledged UDP edit survives a concurrent durable REST mutation."""
    storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
    device = create_color_light("d073d5000001")
    device.storage = storage
    started = threading.Event()
    release = threading.Event()
    original = storage._write_state

    def blocked_write(serial, state):
        started.set()
        if not release.wait(5):
            raise RuntimeError("Test did not release the disk write")
        original(serial, state)

    try:
        with patch.object(storage, "_write_state", side_effect=blocked_write):
            task = device.apply_state_mutation(
                lambda state: setattr(state, "power_level", 0),
                change_type=-1,
                durable=True,
            )
            assert task is not None
            assert await asyncio.to_thread(started.wait, 1)
            device.process_packet(
                LifxHeader(pkt_type=Device.SetLabel.PKT_TYPE),
                Device.SetLabel(label="UDP change"),
            )
            assert device.state.label == "UDP change"
            release.set()
            await task
        await device.close()
        await storage.shutdown()
        saved = storage.load_device_state(device.state.serial)
        assert saved is not None
        assert device.state.label == saved["label"] == "UDP change"
        assert device.state.power_level == saved["power_level"] == 0
    finally:
        release.set()


async def test_failed_durable_candidate_is_never_retried_on_shutdown(tmp_path):
    """A rejected REST candidate must not become durable during a later flush."""
    storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
    device = create_color_light("d073d5000002")
    device.storage = storage
    await storage.save_device_state(device.state)
    with patch.object(
        storage,
        "_write_state",
        side_effect=DevicePersistenceError([device.state.serial], "write failed"),
    ):
        task = device.apply_state_mutation(
            lambda state: setattr(state, "power_level", 0),
            change_type=-1,
            durable=True,
        )
        assert task is not None
        with pytest.raises(DevicePersistenceError):
            await task
    await device.close()
    await storage.shutdown()
    saved = storage.load_device_state(device.state.serial)
    assert saved is not None
    assert device.state.power_level == saved["power_level"] == 65535


@pytest.mark.parametrize("fails", [False, True])
async def test_cancelled_bulk_delete_waits_for_transaction_outcome(tmp_path, fails):
    """Cancellation cannot separate durable deletion from repository removal."""
    storage = DevicePersistenceAsyncFile(tmp_path)
    manager = DeviceManager(DeviceRepository())
    device = create_color_light("d073d5000003", storage=storage)
    manager.add_device(device)
    await device.close()
    await storage.flush_device_state(device.state.serial)
    device.reopen()
    started = threading.Event()
    release = threading.Event()
    original = storage._sync_delete_transaction

    def blocked_delete(serials):
        started.set()
        if not release.wait(5):
            raise RuntimeError("Test did not release deletion")
        if fails:
            raise DevicePersistenceError(serials, "deletion failed")
        return original(serials)

    try:
        with patch.object(storage, "_sync_delete_transaction", blocked_delete):
            removal = asyncio.create_task(manager.remove_all_devices(True, storage))
            assert await asyncio.to_thread(started.wait, 1)
            removal.cancel()
            await asyncio.sleep(0)
            assert not removal.done()
            assert storage.lock.locked()
            release.set()
            if fails:
                with pytest.raises(DevicePersistenceError):
                    await removal
                assert manager.get_device(device.state.serial) is device
                assert storage.load_device_state(device.state.serial) is not None
                assert device._background_tasks.accepting
            else:
                assert await removal == 1
                assert manager.get_device(device.state.serial) is None
                assert storage.load_device_state(device.state.serial) is None
    finally:
        release.set()
        await device.close()
        await storage.shutdown()
