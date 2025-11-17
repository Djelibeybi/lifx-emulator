"""Shared serialization logic for device state."""

from __future__ import annotations

from typing import Any

from lifx_emulator.protocol.protocol_types import LightHsbk


def serialize_hsbk(hsbk: LightHsbk) -> dict[str, int]:
    """Serialize LightHsbk to dict."""
    return {
        "hue": hsbk.hue,
        "saturation": hsbk.saturation,
        "brightness": hsbk.brightness,
        "kelvin": hsbk.kelvin,
    }


def deserialize_hsbk(data: dict[str, int]) -> LightHsbk:
    """Deserialize dict to LightHsbk."""
    return LightHsbk(
        hue=data["hue"],
        saturation=data["saturation"],
        brightness=data["brightness"],
        kelvin=data["kelvin"],
    )


def serialize_device_state(device_state: Any) -> dict[str, Any]:
    """Serialize DeviceState to dict.

    Note: Accesses state via properties for backward compatibility with composed state.
    """
    state_dict = {
        "serial": device_state.serial,
        "label": device_state.label,
        "product": device_state.product,
        "power_level": device_state.power_level,
        "color": serialize_hsbk(device_state.color),
        "location_id": device_state.location_id.hex(),
        "location_label": device_state.location_label,
        "location_updated_at": device_state.location_updated_at,
        "group_id": device_state.group_id.hex(),
        "group_label": device_state.group_label,
        "group_updated_at": device_state.group_updated_at,
        "has_color": device_state.has_color,
        "has_infrared": device_state.has_infrared,
        "has_multizone": device_state.has_multizone,
        "has_matrix": device_state.has_matrix,
        "has_hev": device_state.has_hev,
    }

    if device_state.has_infrared:
        state_dict["infrared_brightness"] = device_state.infrared_brightness

    if device_state.has_hev:
        state_dict["hev_cycle_duration_s"] = device_state.hev_cycle_duration_s
        state_dict["hev_cycle_remaining_s"] = device_state.hev_cycle_remaining_s
        state_dict["hev_cycle_last_power"] = device_state.hev_cycle_last_power
        state_dict["hev_indication"] = device_state.hev_indication
        state_dict["hev_last_result"] = device_state.hev_last_result

    if device_state.has_multizone:
        state_dict["zone_count"] = device_state.zone_count
        state_dict["zone_colors"] = [
            serialize_hsbk(c) for c in device_state.zone_colors
        ]
        state_dict["multizone_effect_type"] = device_state.multizone_effect_type
        state_dict["multizone_effect_speed"] = device_state.multizone_effect_speed

    if device_state.has_matrix:
        state_dict["tile_count"] = device_state.tile_count
        state_dict["tile_width"] = device_state.tile_width
        state_dict["tile_height"] = device_state.tile_height
        state_dict["tile_effect_type"] = device_state.tile_effect_type
        state_dict["tile_effect_speed"] = device_state.tile_effect_speed
        state_dict["tile_effect_palette_count"] = device_state.tile_effect_palette_count
        state_dict["tile_effect_palette"] = [
            serialize_hsbk(c) for c in device_state.tile_effect_palette
        ]
        state_dict["tile_devices"] = [
            {
                "accel_meas_x": t["accel_meas_x"],
                "accel_meas_y": t["accel_meas_y"],
                "accel_meas_z": t["accel_meas_z"],
                "user_x": t["user_x"],
                "user_y": t["user_y"],
                "width": t["width"],
                "height": t["height"],
                "device_version_vendor": t["device_version_vendor"],
                "device_version_product": t["device_version_product"],
                "firmware_build": t["firmware_build"],
                "firmware_version_minor": t["firmware_version_minor"],
                "firmware_version_major": t["firmware_version_major"],
                "colors": [serialize_hsbk(c) for c in t["colors"]],
            }
            for t in device_state.tile_devices
        ]

    return state_dict


def deserialize_device_state(state_dict: dict[str, Any]) -> dict[str, Any]:
    """Deserialize device state dict (convert hex strings and nested objects)."""
    # Deserialize bytes fields
    state_dict["location_id"] = bytes.fromhex(state_dict["location_id"])
    state_dict["group_id"] = bytes.fromhex(state_dict["group_id"])

    # Deserialize color
    state_dict["color"] = deserialize_hsbk(state_dict["color"])

    # Deserialize zone colors if present
    if "zone_colors" in state_dict:
        state_dict["zone_colors"] = [
            deserialize_hsbk(c) for c in state_dict["zone_colors"]
        ]

    # Deserialize tile effect palette if present
    if "tile_effect_palette" in state_dict:
        state_dict["tile_effect_palette"] = [
            deserialize_hsbk(c) for c in state_dict["tile_effect_palette"]
        ]

    # Deserialize tile devices if present
    if "tile_devices" in state_dict:
        for tile_dict in state_dict["tile_devices"]:
            tile_dict["colors"] = [deserialize_hsbk(c) for c in tile_dict["colors"]]

    return state_dict
