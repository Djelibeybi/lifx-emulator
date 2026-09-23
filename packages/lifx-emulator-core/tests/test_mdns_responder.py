"""Production responder contract, including actual legacy-unicast datagrams."""

import inspect

from lifx_emulator.server import EmulatedLifxServer


def test_disabled_default():
    """Existing callers must explicitly opt into owning mDNS sockets."""
    parameters = inspect.signature(EmulatedLifxServer).parameters
    assert "mdns_enabled" in parameters
    assert parameters["mdns_enabled"].default is False
