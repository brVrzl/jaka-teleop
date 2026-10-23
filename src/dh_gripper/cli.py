"""Bounded DH commissioning commands, delegated by embodied-lab."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import yaml

from .protocol import FORCE, INITIALIZE, POSITION, SPEED, write_command
from .tio import JakaTio, TioConfig, bundled_sdk


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="embodied-lab gripper", description=(
        "DH PGE via JAKA TIO; offline by default. Connected status reads the controller cache, "
        "not verified-fresh device feedback. No automatic initialization or TIO reconfiguration."))
    parser.add_argument("action", choices=("status", "initialize", "position", "speed", "force"))
    parser.add_argument("--config", type=Path, required=True, help="machine YAML with runtime.robot_ip and dh_gripper section")
    parser.add_argument("--value", type=int, help="position 0..1000, speed 1..100 percent, force 20..100 percent")
    parser.add_argument("--connect", action="store_true", help="explicitly connect to the physical JAKA controller")
    parser.add_argument("--authorize-motion", action="store_true", help="operator has approved this bounded gripper action")
    args = parser.parse_args(argv)
    try:
        raw = yaml.safe_load(args.config.read_text())
        if not isinstance(raw, dict) or not isinstance(raw.get("dh_gripper"), dict):
            raise ValueError("config requires dh_gripper mapping")
        if not isinstance(raw.get("runtime"), dict):
            raise ValueError("config requires runtime.robot_ip")
        if args.action == "initialize" and args.value is not None:
            raise ValueError("initialize always sends single-direction initialization value 1; omit --value")
        config_data = dict(raw["dh_gripper"])
        config_data["robot_ip"] = raw.get("runtime", {}).get("robot_ip")
        config = TioConfig.from_mapping(config_data)
        register = {"initialize": INITIALIZE, "position": POSITION, "speed": SPEED, "force": FORCE}.get(args.action)
        payload = None
        value = 1 if args.action == "initialize" else args.value
        if register is not None:
            payload = write_command(config.slave_id, register, value)
        elif args.value is not None:
            raise ValueError("status does not accept --value")
        if not args.connect:
            print(json.dumps({"validation_level": "offline_command_plan", "hardware_connected": False,
                              "action": args.action, "sdk_payload_hex_without_crc": payload.hex(" ") if payload else None,
                              "action_completed": False}, indent=2))
            return 0
        if register is not None and not args.authorize_motion:
            raise ValueError("--authorize-motion is required before connecting for a write")
        if register is not None and not config.framing_confirmed:
            raise ValueError("verify firmware command framing before connecting for a write")
        from embodiment_core.doctor import repository_root
        with JakaTio(config, bundled_sdk(repository_root())) as owner:
            feedback = owner.read_feedback()
            if register is not None:
                if register != INITIALIZE and feedback.initialization != 1:
                    raise ValueError("cached initialization state is not ready; initialization is a separate approved action")
                owner.write(register, value, authorize_motion=args.authorize_motion)
            print(json.dumps({"validation_level": "sdk_controller_cache", "feedback": asdict(feedback),
                              "command_submitted": register is not None,
                              "action_completed": None, "device_feedback_freshness_verified": False,
                              "note": "SDK success is not evidence of gripper motion or completion; no release is sent on exit"}, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"DH TIO: {exc}", file=sys.stderr)
        return 2
