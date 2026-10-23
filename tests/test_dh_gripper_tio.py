from __future__ import annotations

import ctypes as C
from dataclasses import replace
import json
from pathlib import Path

import pytest

from dh_gripper.cli import main
from dh_gripper.protocol import FEEDBACK_REGISTERS, FORCE, INITIALIZE, POSITION, SPEED, Feedback, write_command
from dh_gripper.tio import JakaTio, TioConfig


def config(**overrides):
    values = dict(robot_ip="192.0.2.12", model="PGE-50-26-O-S-M1", channel=0, slave_id=1,
                  baudrate=115200, parity=78, firmware_version="test-only",
                  hardware_confirmed=True, framing_confirmed=True,
                  signals=dict(initialization="dh_init", grip="dh_grip", position="dh_position"))
    values.update(overrides)
    return TioConfig.from_mapping(values)


def test_documented_commands_are_binary_big_endian_without_crc():
    assert write_command(1, INITIALIZE, 1) == bytes.fromhex("01 06 01 00 00 01")
    assert write_command(1, POSITION, 500) == bytes.fromhex("01 06 01 03 01 F4")
    assert write_command(1, FORCE, 30) == bytes.fromhex("01 06 01 01 00 1E")
    assert write_command(1, SPEED, 50) == bytes.fromhex("01 06 01 04 00 32")


@pytest.mark.parametrize("slave,register,value", [(0, POSITION, 0), (248, POSITION, 0),
    (1, POSITION, 1001), (1, POSITION, -1), (1, INITIALIZE, 0xA5),
    (1, 0x0300, 1), (1, FORCE, 19), (1, SPEED, 0), (1, POSITION, True)])
def test_rejects_unknown_registers_broadcast_flash_calibration_and_out_of_range(slave, register, value):
    with pytest.raises(ValueError):
        write_command(slave, register, value)


def test_unconfirmed_hardware_fails_before_sdk_load(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CDLL", lambda *a: pytest.fail("SDK must not load"))
    with pytest.raises(ValueError, match="confirm actual"):
        JakaTio(config(hardware_confirmed=False), tmp_path / "missing.so")
    with pytest.raises(ValueError, match="missing: model"):
        config(model=None)


def test_feedback_is_explicitly_unverified_cache_with_no_invented_fault_status():
    feedback = Feedback.from_registers(dict(initialization=1, grip=2, position=450), 123)
    assert feedback.position_permille == 450
    assert not feedback.freshness_verified
    with pytest.raises(ValueError):
        Feedback.from_registers(dict(initialization=1, grip=4, position=450), 123)


class Function:
    def __init__(self, call):
        self.call = call
    def __call__(self, *args):
        return self.call(*args)


class FakeSdk:
    def __init__(self):
        self.operations = []
        self.send_result = 0
        for name in ("create_handler", "destory_handler", "get_tio_vout_param", "get_tio_pin_mode",
                     "get_rs485_chn_mode", "get_rs485_chn_comm", "get_rs485_signal_info", "send_tio_rs_command"):
            setattr(self, name, Function(lambda *args, operation=name: self.call(operation, *args)))
    def call(self, operation, *args):
        self.operations.append(operation)
        if operation == "create_handler": args[1]._obj.value = 1
        elif operation == "get_tio_vout_param": args[1]._obj.value, args[2]._obj.value = 1, 0
        elif operation == "get_tio_pin_mode": args[2]._obj.value = 0xFF
        elif operation == "get_rs485_chn_mode": args[2]._obj.value = 0
        elif operation == "get_rs485_chn_comm":
            comm = args[1]._obj
            comm.slaveId, comm.baudrate, comm.databit, comm.stopbit, comm.parity = 1, 115200, 8, 1, 78
        elif operation == "get_rs485_signal_info":
            capacity = args[2]._obj.value
            args[2]._obj.value = 3
            # Match the SDK's in/out capacity contract: zero returns count only.
            for signal, (key, address), name, value in zip(args[1][:capacity], FEEDBACK_REGISTERS.items(),
                    ["dh_init", "dh_grip", "dh_position"], [1, 1, 1000]):
                signal.sig_name, signal.chn_id, signal.sig_type = name.encode(), 0, 3
                signal.sig_addr, signal.value, signal.frequency = address, value, 3
        elif operation == "send_tio_rs_command": return self.send_result
        return 0


def test_status_is_read_only_and_a_second_local_owner_is_rejected(monkeypatch):
    sdk = FakeSdk()
    monkeypatch.setattr(C, "CDLL", lambda *a: sdk)
    with JakaTio(config(), Path("unused.so")) as owner:
        feedback = owner.read_feedback()
        assert feedback.position_permille == 1000
        with pytest.raises(BlockingIOError):
            with JakaTio(config(), Path("unused.so")): pass
    assert "send_tio_rs_command" not in sdk.operations
    assert all(name.startswith("get_") or name in ("create_handler", "destory_handler") for name in sdk.operations)


def test_write_requires_authorization_and_framing_and_fault_latches(monkeypatch):
    sdk = FakeSdk()
    monkeypatch.setattr(C, "CDLL", lambda *a: sdk)
    with JakaTio(config(), Path("unused.so")) as owner:
        with pytest.raises(ValueError, match="authorization"):
            owner.write(INITIALIZE, 1, authorize_motion=False)
        owner.config = replace(owner.config, framing_confirmed=False)
        with pytest.raises(ValueError, match="framing"):
            owner.write(INITIALIZE, 1, authorize_motion=True)
        owner.config = replace(owner.config, framing_confirmed=True)
        sdk.send_result = -61
        with pytest.raises(RuntimeError, match="-61"):
            owner.write(INITIALIZE, 1, authorize_motion=True)
        sdk.send_result = 0
        with pytest.raises(RuntimeError, match="fault latched"):
            owner.write(POSITION, 1000, authorize_motion=True)
    assert sdk.operations[-1] == "destory_handler"


def test_rate_limit_never_queues_old_commands_or_sends_cleanup_open(monkeypatch):
    sdk = FakeSdk()
    monkeypatch.setattr(C, "CDLL", lambda *a: sdk)
    with JakaTio(config(), Path("unused.so")) as owner:
        owner.write(POSITION, 500, authorize_motion=True)
        with pytest.raises(RuntimeError, match="4 Hz"):
            owner.write(POSITION, 1000, authorize_motion=True)
    assert sdk.operations[-1] == "destory_handler"


def test_cli_dry_run_is_offline(tmp_path, monkeypatch, capsys):
    import yaml
    from dataclasses import asdict
    value = asdict(config(hardware_confirmed=False, framing_confirmed=False))
    address = value.pop("robot_ip")
    path = tmp_path / "machine.yaml"
    path.write_text(yaml.safe_dump({"runtime": {"robot_ip": address}, "dh_gripper": value}))
    monkeypatch.setattr(C, "CDLL", lambda *a: pytest.fail("SDK must not load for dry run"))
    assert main(["position", "--value", "500", "--config", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hardware_connected"] is False
    assert payload["sdk_payload_hex_without_crc"] == "01 06 01 03 01 f4"
