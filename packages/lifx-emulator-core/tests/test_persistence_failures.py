"""Storage failure and rollback boundaries."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from lifx_emulator.background_tasks import BackgroundTaskTracker
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.devices.persistence import (
    DevicePersistenceAsyncFile,
    DevicePersistenceError,
)
from lifx_emulator.factories import create_color_light, create_device
from lifx_emulator.repositories import DeviceRepository


@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_failed_atomic_replace_preserves_original(tmp_path, cleanup_fails):
    storage = DevicePersistenceAsyncFile(tmp_path)
    serial = "d073d5000001"
    storage._write_state(serial, {"power_level": 65535})
    original = storage._device_path(serial).read_bytes()
    unlink = Path.unlink

    def cleanup(path, *args, **kwargs):
        if cleanup_fails:
            raise OSError("cleanup unavailable")
        return unlink(path, *args, **kwargs)

    with (
        patch.object(Path, "replace", side_effect=OSError("replace unavailable")),
        patch.object(Path, "unlink", cleanup),
        pytest.raises(DevicePersistenceError, match="Failed to write"),
    ):
        storage._write_state(serial, {"power_level": 0})
    assert storage._device_path(serial).read_bytes() == original
    assert (
        storage._device_path(serial).with_suffix(".json.tmp").exists() == cleanup_fails
    )
    await storage.shutdown()


async def test_explicit_flush_retains_failed_snapshot_for_retry(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path, debounce_ms=10_000)
    state = create_color_light("d073d5000001").state
    assert not await storage.flush_device_state(state.serial)
    await storage.save_device_state(state)
    with (
        patch.object(
            storage,
            "_write_state",
            side_effect=DevicePersistenceError([state.serial], "unavailable"),
        ),
        pytest.raises(DevicePersistenceError),
    ):
        await storage.flush_device_state(state.serial)
    assert state.serial in storage.pending
    assert await storage.flush_device_state(state.serial)
    assert storage.load_device_state(state.serial) is not None
    await storage.shutdown()


@pytest.mark.parametrize("rollback_fails", [False, True])
async def test_bulk_staging_failure_restores_files_or_reports_rollback(
    tmp_path, rollback_fails
):
    storage = DevicePersistenceAsyncFile(tmp_path)
    first, second = "d073d5000001", "d073d5000002"
    for serial in (first, second):
        storage._write_state(serial, {"serial": serial})
    replace = Path.replace

    def fail_second(path, target):
        if path.name == f"{second}.json":
            raise OSError("second rename unavailable")
        if rollback_fails and path.suffix == ".deleting":
            raise OSError("rollback unavailable")
        return replace(path, target)

    with patch.object(Path, "replace", fail_second):
        with pytest.raises(DevicePersistenceError) as caught:
            await storage.delete_device_states([first, second])
    assert second in caught.value.failed_serials
    assert (first in caught.value.failed_serials) == rollback_fails
    assert storage._device_path(first).exists() != rollback_fails
    assert storage._device_path(second).exists()
    await storage.shutdown()


async def test_bulk_delete_refuses_invalid_serial_and_existing_staging(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path)
    with pytest.raises(DevicePersistenceError, match="Cannot delete"):
        await storage.delete_device_states(["../outside"])
    serial = "d073d5000001"
    storage._write_state(serial, {})
    staged = storage._device_path(serial).with_suffix(".json.deleting")
    staged.write_text("previous transaction")
    with pytest.raises(DevicePersistenceError, match="staging path already exists"):
        await storage.delete_device_states([serial])
    assert storage._device_path(serial).exists()
    assert staged.read_text() == "previous transaction"
    await storage.shutdown()


async def test_staged_cleanup_failure_cannot_resurrect_device(tmp_path, caplog):
    storage = DevicePersistenceAsyncFile(tmp_path)
    serial = "d073d5000001"
    storage._write_state(serial, {})
    with patch.object(Path, "unlink", side_effect=OSError("cleanup unavailable")):
        assert await storage.delete_device_states([serial]) == 1
    assert storage.list_devices() == []
    assert "Failed to remove staged state" in caplog.text
    await storage.shutdown()


async def test_shutdown_waits_for_retained_storage_work(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path)
    completed = asyncio.Event()

    async def work():
        await asyncio.sleep(0)
        completed.set()

    storage._track_task(asyncio.create_task(work()))
    await storage.shutdown()
    assert completed.is_set()
    assert not storage.background_tasks


async def test_tracker_capacity_and_reopen_guards_close_rejected_coroutines():
    with pytest.raises(ValueError, match="positive"):
        BackgroundTaskTracker("test", max_pending=0)
    tracker = BackgroundTaskTracker("test", max_pending=1)
    blocked = asyncio.Event()
    task = tracker.schedule(blocked.wait(), "held")
    rejected = blocked.wait()
    assert tracker.schedule(rejected, "excess") is None
    assert rejected.cr_frame is None
    tracker.stop_accepting()
    with pytest.raises(RuntimeError, match="pending"):
        tracker.start_accepting()
    blocked.set()
    await tracker.shutdown()
    assert task is not None and task.done()
    tracker.start_accepting()
    assert tracker.accepting


async def test_device_observer_failure_does_not_undo_committed_state(caplog):
    device = create_color_light("d073d5000001")

    def fail_observer(*args):
        raise ValueError("observer unavailable")

    device.on_state_changed = fail_observer
    device.apply_state_mutation(
        lambda state: setattr(state, "power_level", 0), change_type=-1
    )
    assert device.state.power_level == 0
    assert "observer unavailable" in caplog.text
    with pytest.raises(RuntimeError, match="without storage"):
        await device._persist_state(device.state, durable=True)


async def test_serial_symlink_cannot_delete_outside_storage(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path / "states")
    protected = tmp_path / "protected.json"
    protected.write_text("protected data")
    serial = "d073d5000001"
    (storage.storage_dir / f"{serial}.json").symlink_to(protected)
    with pytest.raises(DevicePersistenceError, match="escapes"):
        await storage.delete_device_state(serial)
    assert protected.read_text() == "protected data"
    await storage.shutdown()


@pytest.mark.parametrize("bulk", [False, True])
async def test_invalid_storage_deletion_result_reopens_device(bulk):
    class InvalidStorage:
        async def delete_device_state(self, serial):
            return None

        async def delete_device_states(self, serials):
            return True

    manager = DeviceManager(DeviceRepository())
    device = create_color_light("d073d5000001")
    manager.add_device(device)
    with pytest.raises(TypeError, match="must return"):
        if bulk:
            await manager.remove_all_devices(True, InvalidStorage())
        else:
            await manager.remove_device(device.state.serial, InvalidStorage())
    assert manager.get_device(device.state.serial) is device
    assert device._background_tasks.accepting


async def test_explicit_initial_persistence_writes_device_state(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path)
    device = create_device(
        product_id=91,
        serial="d073d5000001",
        storage=storage,
        persist_initial_state=True,
    )
    await device.close()
    await storage.shutdown()
    assert storage.load_device_state(device.state.serial) is not None


async def test_closed_device_rejects_durable_mutation(tmp_path):
    storage = DevicePersistenceAsyncFile(tmp_path)
    device = create_color_light("d073d5000001", storage=storage)
    await device.close()
    original = device.state.label
    with pytest.raises(RuntimeError, match="admission is closed"):
        device.apply_state_mutation(
            lambda state: setattr(state, "label", "rejected"),
            change_type="label",
            durable=True,
        )
    assert device.state.label == original
    await storage.shutdown()
