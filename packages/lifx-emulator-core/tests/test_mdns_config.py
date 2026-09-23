"""Immutable advertisement configuration and bind-dependent validation."""

import inspect
import ipaddress
from dataclasses import FrozenInstanceError, replace

import pytest
from lifx_emulator.factories import factory
from test_mdns_responder import make_server, parse_records, raw_query

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


async def test_mdns_wildcard_preflight():
    device = factory.create_color_light(serial="d073d5000200")
    server = make_server([device], bind_address="0.0.0.0")
    try:
        with pytest.raises(ValueError, match="d073d5000200"):
            await server.start()
        assert server.ipv4_endpoint is None
        assert server._mdns is None
    finally:
        await server.stop()


async def test_mdns_invalid_add_has_no_membership_side_effects():
    server = make_server([], bind_address="0.0.0.0")
    device = factory.create_color_light()
    with pytest.raises(ValueError):
        server.add_device(device)
    assert server.get_all_devices() == []


async def test_mdns_mixed_records():
    wifi = factory.create_color_light(serial="d073d5000201", mdns_address="127.0.0.2")
    thread = factory.create_color_light(
        serial="d073d5000202", connectivity="thread", mdns_address="fd00::1"
    )
    hidden = factory.create_color_light(serial="d073d5000203", mdns_enabled=False)
    server = make_server([wifi, thread, hidden])
    try:
        await server.start()
        replies = await raw_query(722)
        records = [r for packet, _ in replies for r in parse_records(packet)[1]]
        for device, kind, address in [(wifi, 1, "127.0.0.2"), (thread, 28, "fd00::1")]:
            host = f"{device.state.serial}.local."
            assert any(
                r[0] == host
                and r[1] == kind
                and r[4] == ipaddress.ip_address(address).packed
                for r in records
            )
            assert not any(
                r[0] == host and r[1] == (28 if kind == 1 else 1) for r in records
            )
            direct = await raw_query(723, host, kind)
            assert any(
                r[0] == host and r[1] == kind
                for packet, _ in direct
                for r in parse_records(packet)[1]
            )
        assert not any(hidden.state.serial in str(r) for r in records)
    finally:
        await server.stop()


@pytest.mark.parametrize(
    "changes", [{"mdns_enabled": False}, {"mdns_address": "127.0.0.2"}]
)
def test_wholesale_network_replacement_is_immutable(changes):
    device = factory.create_color_light()
    with pytest.raises(ValueError, match="immutable"):
        device.state.network = replace(device.state.network, **changes)
