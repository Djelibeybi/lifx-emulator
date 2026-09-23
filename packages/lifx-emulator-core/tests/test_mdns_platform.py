"""Windows public-owner simulations; these are not real Windows socket evidence."""

import pytest
from lifx_emulator import mdns
from lifx_emulator.factories import create_color_light
from test_mdns_responder import FakeOwner, make_server
from zeroconf import IPVersion


@pytest.mark.parametrize("startup_error", [False, True])
async def test_simulated_windows_public_owner_contract(monkeypatch, startup_error):
    """Model Windows owner success/failure through the public constructor seam."""
    calls = []
    owner = FakeOwner()
    if startup_error:
        owner.failure = ("register", "outer")

    def simulated_windows_owner(*, interfaces, ip_version):
        # Adapter supplies explicit interfaces and delegates all socket reuse
        # decisions to the public dependency; it does not patch sys.platform.
        calls.append((interfaces, ip_version))
        return owner

    monkeypatch.setattr(mdns, "AsyncZeroconf", simulated_windows_owner)
    server = make_server([create_color_light()])
    await server.start()
    assert calls == [(["127.0.0.1"], IPVersion.V4Only)]
    assert server.mdns_status == ("failed" if startup_error else "running")
    await server.stop()
    assert owner.closes == 1
    assert server._device_manager._lifecycle_listeners == []
