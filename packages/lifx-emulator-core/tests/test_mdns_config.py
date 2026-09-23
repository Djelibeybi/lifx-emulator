"""Immutable advertisement configuration and bind-dependent validation."""

import inspect
from dataclasses import FrozenInstanceError

import pytest
from lifx_emulator.factories import factory

FACTORIES = [
    getattr(factory, name) for name in dir(factory) if name.startswith("create_")
]


@pytest.mark.parametrize("create", FACTORIES)
def test_factory_mdns_contract(create):
    params = inspect.signature(create).parameters
    assert "mdns_enabled" in params
    assert params["mdns_enabled"].default is True
    assert params["mdns_address"].default is None


@pytest.mark.parametrize(
    "connectivity,address",
    [
        ("wifi", "127.0.0.1"),
        ("thread", "::1"),
        ("thread", "fd00:0:0:0::1"),
        ("thread", "2001:db8::1"),
    ],
)
def test_factory_valid_immutable(connectivity, address):
    device = factory.create_color_light(connectivity=connectivity, mdns_address=address)
    assert device.state.mdns_enabled is True
    with pytest.raises(ValueError):
        device.state.mdns_address = "127.0.0.2"
    with pytest.raises(FrozenInstanceError):
        device.state.network.mdns_enabled = False


@pytest.mark.parametrize(
    "connectivity,address",
    [
        ("wifi", ""),
        ("wifi", "bad"),
        ("wifi", "0.0.0.0"),
        ("wifi", "::1"),
        ("wifi", "169.254.1.2"),
        ("wifi", "224.0.0.1"),
        ("thread", "::"),
        ("thread", "127.0.0.1"),
        ("thread", "fe80::1"),
        ("thread", "fe80::1%en0"),
        ("thread", "::1%lo0"),
        ("thread", "ff02::1"),
    ],
)
def test_invalid_mdns_address(connectivity, address):
    with pytest.raises(ValueError):
        factory.create_color_light(connectivity=connectivity, mdns_address=address)


def test_thread_opt_out_rejected():
    with pytest.raises(ValueError):
        factory.create_color_light(connectivity="thread", mdns_enabled=False)
