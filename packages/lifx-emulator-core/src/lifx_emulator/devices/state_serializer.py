"""Shared serialization logic for device state."""

from __future__ import annotations

from typing import Any

from lifx_emulator.protocol.protocol_types import Button as ButtonStruct
from lifx_emulator.protocol.protocol_types import (
    ButtonAction,
    ButtonBacklightHsbk,
    ButtonGesture,
    ButtonTarget,
    ButtonTargetType,
    LightHsbk,
)
from lifx_emulator.protocol.serializer import decode_enum


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


def serialize_backlight(backlight: ButtonBacklightHsbk) -> dict[str, int]:
    """Serialize ButtonBacklightHsbk to dict."""
    return {
        "hue": backlight.hue,
        "saturation": backlight.saturation,
        "brightness": backlight.brightness,
        "kelvin": backlight.kelvin,
    }


def deserialize_backlight(data: dict[str, int]) -> ButtonBacklightHsbk:
    """Deserialize dict to ButtonBacklightHsbk."""
    return ButtonBacklightHsbk(
        hue=data["hue"],
        saturation=data["saturation"],
        brightness=data["brightness"],
        kelvin=data["kelvin"],
    )


def serialize_button(button: ButtonStruct) -> dict[str, Any]:
    """Serialize a Button struct (gesture/target actions) to dict."""
    return {
        "actions_count": button.actions_count,
        "actions": [
            {
                "gesture": int(action.gesture),
                "target_type": int(action.target_type),
                "target": action.target.data.hex(),
            }
            for action in button.actions
        ],
    }


def deserialize_button(data: dict[str, Any]) -> ButtonStruct:
    """Deserialize dict to a Button struct."""
    return ButtonStruct(
        actions_count=data["actions_count"],
        actions=[
            ButtonAction(
                gesture=decode_enum(ButtonGesture, action["gesture"]),
                target_type=decode_enum(ButtonTargetType, action["target_type"]),
                target=ButtonTarget(data=bytes.fromhex(action["target"])),
            )
            for action in data["actions"]
        ],
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
        # Serialize tile framebuffers (non-visible framebuffers 1-7)
        state_dict["tile_framebuffers"] = [
            {
                "tile_index": fb.tile_index,
                "framebuffers": {
                    str(fb_idx): [serialize_hsbk(c) for c in colors]
                    for fb_idx, colors in fb.framebuffers.items()
                },
            }
            for fb in device_state.tile_framebuffers
        ]

    if device_state.has_buttons:
        # Button.Set (906) rewrites the per-button action list and
        # Button.SetConfig (910) the haptic/backlight config, so both are
        # mutable client-visible state and both must survive a restart.
        buttons_state = device_state.buttons_state
        state_dict["buttons_config"] = {
            "haptic_duration_ms": buttons_state.haptic_duration_ms,
            "backlight_on": serialize_backlight(buttons_state.backlight_on),
            "backlight_off": serialize_backlight(buttons_state.backlight_off),
            "buttons": [serialize_button(b) for b in buttons_state.buttons],
        }

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

    # Deserialize tile framebuffers if present (for backwards compatibility)
    if "tile_framebuffers" in state_dict:
        from lifx_emulator.devices.states import TileFramebuffers

        deserialized_fbs = []
        for fb_dict in state_dict["tile_framebuffers"]:
            tile_fb = TileFramebuffers(tile_index=fb_dict["tile_index"])
            # Deserialize each framebuffer's colors
            for fb_idx_str, colors_list in fb_dict["framebuffers"].items():
                fb_idx = int(fb_idx_str)
                tile_fb.framebuffers[fb_idx] = [
                    deserialize_hsbk(c) for c in colors_list
                ]
            deserialized_fbs.append(tile_fb)
        state_dict["tile_framebuffers"] = deserialized_fbs

    # Deserialize button config if present. Each key is optional: a hand-edited
    # or older state file must fall back to defaults rather than crash.
    if "buttons_config" in state_dict:
        config = state_dict["buttons_config"]
        if "backlight_on" in config:
            config["backlight_on"] = deserialize_backlight(config["backlight_on"])
        if "backlight_off" in config:
            config["backlight_off"] = deserialize_backlight(config["backlight_off"])
        if "buttons" in config:
            config["buttons"] = [deserialize_button(b) for b in config["buttons"]]

    return state_dict
