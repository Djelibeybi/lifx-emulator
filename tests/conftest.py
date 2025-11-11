"""Pytest configuration and shared fixtures for LIFX Emulator tests."""

import socket
import time

import pytest

from lifx_emulator.devices.device import DeviceState
from lifx_emulator.devices.manager import DeviceManager
from lifx_emulator.devices.states import (
    CoreDeviceState,
    GroupState,
    LocationState,
    NetworkState,
    WaveformState,
)
from lifx_emulator.factories import (
    create_color_light,
    create_color_temperature_light,
    create_hev_light,
    create_infrared_light,
    create_multizone_light,
    create_tile_device,
)
from lifx_emulator.protocol.protocol_types import LightHsbk
from lifx_emulator.repositories import DeviceRepository
from lifx_emulator.server import EmulatedLifxServer


@pytest.fixture
def color_hsbk():
    """Standard color value for testing."""
    return LightHsbk(hue=21845, saturation=65535, brightness=32768, kelvin=3500)


@pytest.fixture
def device_state():
    """Basic device state for testing."""
    core = CoreDeviceState(
        serial="d073d5000001",
        label="Test Device",
        power_level=65535,
        color=LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500),
        vendor=1,
        product=27,
        version_major=3,
        version_minor=70,
        build_timestamp=int(time.time()),
    )
    return DeviceState(
        core=core,
        network=NetworkState(),
        location=LocationState(),
        group=GroupState(),
        waveform=WaveformState(),
        has_color=True,
    )


@pytest.fixture
def color_device():
    """Create a standard color light device."""
    return create_color_light("d073d5000001")


@pytest.fixture
def infrared_device():
    """Create an infrared-capable device."""
    return create_infrared_light("d073d5000002")


@pytest.fixture
def hev_device():
    """Create a HEV-capable device."""
    return create_hev_light("d073d5000003")


@pytest.fixture
def multizone_device():
    """Create a multizone device with 16 zones."""
    return create_multizone_light("d073d5000004", zone_count=16)


@pytest.fixture
def extended_multizone_device():
    """Create an extended multizone device with 82 zones."""
    return create_multizone_light(
        "d073d5000005", zone_count=82, extended_multizone=True
    )


@pytest.fixture
def tile_device():
    """Create a chained matrix device with 5 tiles (8x8 each)."""
    return create_tile_device("d073d5000006", tile_count=5)


@pytest.fixture
def single_tile_device():
    """Create a single matrix device (8x8)."""
    return create_tile_device("d073d5000010", tile_count=1)


@pytest.fixture
def multi_tile_device():
    """Create a chained matrix device with 3 tiles (8x8 each)."""
    return create_tile_device("d073d5000011", tile_count=3)


@pytest.fixture
def large_matrix_device():
    """Create a large matrix device (single 16x8 tile with >64 zones)."""
    return create_tile_device(
        "d073d5000012", tile_count=1, tile_width=16, tile_height=8
    )


@pytest.fixture
def white_device():
    """Create a color temperature light device."""
    return create_color_temperature_light("d073d5000007")


@pytest.fixture
def server_with_devices(color_device, multizone_device, tile_device):
    """Create a server with multiple device types."""
    devices = [color_device, multizone_device, tile_device]
    device_manager = DeviceManager(DeviceRepository())
    return EmulatedLifxServer(devices, device_manager, "127.0.0.1", 56700)


@pytest.fixture
def device_with_scenarios():
    """Create a device with test scenarios configured."""
    from lifx_emulator.devices.device import DeviceState, EmulatedLifxDevice
    from lifx_emulator.devices.states import (
        CoreDeviceState,
        GroupState,
        LocationState,
        NetworkState,
        WaveformState,
    )
    from lifx_emulator.scenarios.manager import (
        HierarchicalScenarioManager,
        ScenarioConfig,
    )

    # Create device state
    core = CoreDeviceState(
        serial="d073d5000099",
        label="Test Device",
        power_level=0,
        color=LightHsbk(hue=0, saturation=0, brightness=0, kelvin=3500),
        vendor=1,
        product=27,
        version_major=3,
        version_minor=70,
        build_timestamp=int(time.time()),
    )
    state = DeviceState(
        core=core,
        network=NetworkState(),
        location=LocationState(),
        group=GroupState(),
        waveform=WaveformState(),
        has_color=True,
    )

    # Create scenario manager with test scenarios
    scenario_manager = HierarchicalScenarioManager()
    scenario_manager.set_device_scenario(
        "d073d5000099",
        ScenarioConfig(
            drop_packets={101: 1.0},  # Drop LightGet packets
            response_delays={102: 0.1},  # 100ms delay for SetColor
            malformed_packets=[107],  # Malformed StateColor
            invalid_field_values=[],
            partial_responses=[506],  # Partial multizone response
        ),
    )

    # Create device with scenario manager
    device = EmulatedLifxDevice(state, scenario_manager=scenario_manager)
    return device


def find_free_port():
    """Find an unused port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def integration_port():
    """Module-scoped fixture that provides a free port for integration tests."""
    return find_free_port()


@pytest.fixture(scope="module")
def integration_devices(integration_port):
    """Module-scoped fixture that creates devices."""
    # Create all device types for comprehensive testing
    devices = [
        create_color_light("d073d5000001"),
        create_infrared_light("d073d5000002"),
        create_hev_light("d073d5000003"),
        create_multizone_light("d073d5000004", zone_count=16),
        create_multizone_light("d073d5000005", zone_count=82, extended_multizone=True),
        create_tile_device("d073d5000006", tile_count=5),
        create_color_temperature_light("d073d5000007"),
        create_tile_device(
            "d073d5000008", tile_count=1, tile_width=16, tile_height=8
        ),  # Large tile (>64 zones)
    ]

    # Set all devices to use the same port
    for device in devices:
        device.state.port = integration_port

    # Return devices and port as a tuple
    return devices, integration_port


@pytest.fixture
def integration_server(integration_devices):
    """Function-scoped fixture that creates a server instance."""
    devices, port = integration_devices
    # Return server instance (not started - tests will use 'async with')
    device_manager = DeviceManager(DeviceRepository())
    return EmulatedLifxServer(devices, device_manager, "127.0.0.1", port)


@pytest.fixture
def device_lookup(integration_devices):
    """Function-scoped fixture that provides device lookup by serial."""
    devices, _ = integration_devices
    return {device.state.serial: device for device in devices}
