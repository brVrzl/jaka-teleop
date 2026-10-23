from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def validate_runtime_config(document: dict[str, Any]) -> list[str]:
    """Check host settings offline; never infer device identity or apply settings.

    This validates the new machine profile. Historical RH56 profiles remain
    valid without an end_effector section; physical tool verification is owned
    by the selected hardware entry point.
    """
    from ipaddress import IPv4Address

    errors: list[str] = []
    runtime = document.get("runtime")
    if not isinstance(runtime, dict):
        return ["runtime must be a mapping"]
    for key in ("robot_ip", "edg_state_ip", "bind"):
        try:
            value = runtime.get(key)
            if not isinstance(value, str):
                raise ValueError("IPv4 settings require strings")
            address = IPv4Address(value)
            if key != "bind" and (address.is_unspecified or address.is_multicast or str(address) == "255.255.255.255"):
                raise ValueError("robot and feedback addresses must be unicast")
        except (ValueError, TypeError):
            errors.append(f"runtime.{key} must be an explicit IPv4 address")
    sender = runtime.get("allowed_sender")
    if sender is not None:
        try:
            if not isinstance(sender, str):
                raise ValueError("sender requires an IPv4 string")
            address = IPv4Address(sender)
            if address.is_unspecified or address.is_multicast or str(address) == "255.255.255.255":
                raise ValueError("sender must be unicast")
        except (ValueError, TypeError):
            errors.append("runtime.allowed_sender must be an IPv4 address or null")
    port = runtime.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        errors.append("runtime.port must be an integer in [1, 65535]")
    for key in ("config", "worker", "log_dir", "episode_root", "task_name", "operator"):
        if not isinstance(runtime.get(key), str) or not runtime[key].strip():
            errors.append(f"runtime.{key} must be a nonempty string")
    cpu = runtime.get("native_control_cpu")
    if cpu is not None and (type(cpu) is not int or cpu < 0):
        errors.append("runtime.native_control_cpu must be null or a nonnegative integer")
    priority = runtime.get("native_control_realtime_priority", 0)
    if type(priority) is not int or not 0 <= priority <= 99:
        errors.append("runtime.native_control_realtime_priority must be an integer in [0, 99]")
    cameras = document.get("cameras")
    if not isinstance(cameras, dict):
        errors.append("cameras must be a mapping with workspace and wrist roles")
    else:
        serials = []
        for role in ("workspace", "wrist"):
            camera = cameras.get(role)
            if not isinstance(camera, dict) or not isinstance(camera.get("serial"), str) or not camera["serial"].strip() or camera["serial"] != camera["serial"].strip() or camera["serial"].startswith("REPLACE_"):
                errors.append(f"cameras.{role}.serial must be an explicitly selected serial string")
            else:
                serials.append(camera["serial"])
        if len(serials) != len(set(serials)):
            errors.append("workspace and wrist camera serials must be different")
    return errors
