"""Single-owner JAKA SDK v2.2.7 C ABI for DH commissioning.

Use outside the arm servo thread. SDK calls may block; this is not a realtime
transport. No connect, initialize, supply, pin, channel or signal setup on import.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import dataclass
import fcntl
import ipaddress
from pathlib import Path
import platform
import time
import threading

from .protocol import FEEDBACK_REGISTERS, Feedback, write_command


class SignInfo(C.Structure):
    _fields_ = [("sig_name", C.c_char * 20), ("chn_id", C.c_int), ("sig_type", C.c_int),
                ("sig_addr", C.c_int), ("value", C.c_int), ("frequency", C.c_int)]


class ModRtuComm(C.Structure):
    _fields_ = [(name, C.c_int) for name in ("chn_id", "slaveId", "baudrate", "databit", "stopbit", "parity")]


@dataclass(frozen=True)
class TioConfig:
    robot_ip: str
    model: str
    channel: int
    slave_id: int
    baudrate: int
    parity: int
    signals: dict[str, str]
    hardware_confirmed: bool
    framing_confirmed: bool
    firmware_version: str

    @classmethod
    def from_mapping(cls, value: dict) -> "TioConfig":
        required = ("robot_ip", "model", "channel", "slave_id", "baudrate", "parity", "signals",
                    "hardware_confirmed", "framing_confirmed", "firmware_version")
        missing = [key for key in required if key not in value or value[key] is None]
        if missing:
            raise ValueError("DH configuration missing: " + ", ".join(missing))
        result = cls(**{key: value[key] for key in required})
        ipaddress.IPv4Address(result.robot_ip)
        if result.model != "PGE-50-26-O-S-M1":
            raise ValueError("this profile requires confirmed integrated-controller PGE-50-26-O-S-M1; do not substitute PGE-5-26")
        if type(result.channel) is not int or result.channel not in (0, 1):
            raise ValueError("channel is SDK index 0 (RS485H) or 1 (RS485L)")
        write_command(result.slave_id, 0x0103, 0)  # Validate ID without sending.
        if type(result.baudrate) is not int or result.baudrate not in (4800, 9600, 19200, 38400, 57600, 115200):
            raise ValueError("baudrate is outside the PGE manual's supported values")
        if type(result.parity) is not int or result.parity not in (78, 79, 69):
            raise ValueError("parity must be ASCII N=78, O=79 or E=69")
        if not isinstance(result.signals, dict) or set(result.signals) != set(FEEDBACK_REGISTERS):
            raise ValueError("signals must name initialization, grip, and position")
        names = list(result.signals.values())
        if any(not isinstance(n, str) or not n.isascii() or not n.replace('_', '').isalnum() or len(n) >= 20 for n in names):
            raise ValueError("TIO signal names require 1..19 ASCII letters/digits/underscores")
        if len(set(names)) != 3:
            raise ValueError("feedback signal names must be distinct")
        if type(result.hardware_confirmed) is not bool or type(result.framing_confirmed) is not bool:
            raise ValueError("confirmation fields must be YAML booleans")
        return result

    def require_hardware_confirmation(self) -> None:
        if not self.hardware_confirmed or not isinstance(self.firmware_version, str) or not self.firmware_version.strip():
            raise ValueError("confirm actual model/drive, cable pinout, V3 TIO, supply, firmware and exclusive bus ownership first")


class JakaTio:
    def __init__(self, config: TioConfig, sdk_library: Path):
        config.require_hardware_confirmation()
        self.config, self.sdk_library = config, sdk_library
        self._sdk = None
        self._handle = C.c_int(-1)
        self._lock = None
        self._last_write = 0.0
        self._faulted = False
        self._connected = False
        self._owner_thread = None

    def __enter__(self) -> "JakaTio":
        # One owner across local processes, including separate CLI invocations.
        self._lock = open(f"/tmp/embodied-lab-tio-{self.config.robot_ip}.lock", "a+")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._sdk = C.CDLL(str(self.sdk_library))
            handle = C.POINTER(C.c_int)
            signatures = {
                "create_handler": [C.c_char_p, handle, C.c_int],
                "destory_handler": [handle],
                "get_tio_vout_param": [handle, handle, handle],
                "get_tio_pin_mode": [handle, C.c_int, handle],
                "get_rs485_chn_mode": [handle, C.c_int, handle],
                "get_rs485_chn_comm": [handle, C.POINTER(ModRtuComm)],
                "get_rs485_signal_info": [handle, C.POINTER(SignInfo), handle],
                "send_tio_rs_command": [handle, C.c_int, C.POINTER(C.c_uint8), C.c_int],
            }
            for name, signature in signatures.items():
                function = getattr(self._sdk, name)
                function.argtypes, function.restype = signature, C.c_int
            self._check(self._sdk.create_handler(self.config.robot_ip.encode("ascii"), C.byref(self._handle), 0), "create_handler")
            self._connected = True
            self._owner_thread = threading.get_ident()
            self._check_configuration()
            return self
        except BaseException:
            self.close()
            raise

    def _check(self, code: int, operation: str) -> None:
        if code != 0:
            self._faulted = True
            raise RuntimeError(f"JAKA {operation} failed: {code}; no automatic retry or gripper release")

    def _call(self, name: str, *args) -> None:
        if not self._connected:
            raise RuntimeError("TIO owner is not connected")
        if threading.get_ident() != self._owner_thread:
            raise RuntimeError("TIO owner must be used by its connecting thread only")
        if self._sdk is None or self._handle.value < 0:
            raise RuntimeError("TIO owner is not connected")
        self._check(getattr(self._sdk, name)(C.byref(self._handle), *args), name)

    def _check_configuration(self) -> None:
        enabled, voltage, pin, mode = (C.c_int(-1) for _ in range(4))
        self._call("get_tio_vout_param", C.byref(enabled), C.byref(voltage))
        self._call("get_tio_pin_mode", 1 if self.config.channel == 0 else 2, C.byref(pin))
        self._call("get_rs485_chn_mode", self.config.channel, C.byref(mode))
        comm = ModRtuComm(); comm.chn_id = self.config.channel
        self._call("get_rs485_chn_comm", C.byref(comm))
        if (enabled.value, voltage.value, mode.value) != (1, 0, 0):
            raise ValueError("TIO must already have enabled 24V supply and Modbus RTU mode; nothing was changed")
        if pin.value != (0xFF if self.config.channel == 0 else 1):
            raise ValueError("TIO pins are not already multiplexed for the selected RS485 channel")
        if (comm.slaveId, comm.baudrate, comm.databit, comm.stopbit, comm.parity) != (
            self.config.slave_id, self.config.baudrate, 8, 1, self.config.parity
        ):
            raise ValueError("TIO communication settings do not match the confirmed DH profile; nothing was changed")

    def read_feedback(self) -> Feedback:
        # Official SDK example allocates 256 entries. This getter only reads the
        # controller signal cache: no add/update/delete or device initialization.
        # v2.2.7 uses count as input capacity and output total; zero copies no entries.
        signals, count = (SignInfo * 256)(), C.c_int(256)
        self._call("get_rs485_signal_info", signals, C.byref(count))
        if not 0 <= count.value <= 256:
            self._faulted = True
            raise RuntimeError("invalid TIO signal count")
        if any(not bytes(s.sig_name) or len(bytes(s.sig_name)) >= 20 for s in signals[:count.value]):
            self._faulted = True
            raise RuntimeError("TIO signal inventory contains invalid empty/unterminated names; values are unavailable")
        values = {}
        for key, expected_name in self.config.signals.items():
            matches = [s for s in signals[:count.value] if bytes(s.sig_name).decode("ascii") == expected_name]
            if len(matches) != 1:
                raise ValueError(f"preconfigured TIO signal missing/duplicated: {expected_name}")
            signal = matches[0]
            if (signal.chn_id, signal.sig_type, signal.sig_addr) != (self.config.channel, 3, FEEDBACK_REGISTERS[key]):
                raise ValueError(f"TIO signal definition mismatch: {expected_name}")
            values[key] = signal.value
        return Feedback.from_registers(values, time.monotonic_ns())

    def write(self, register: int, value: int, *, authorize_motion: bool) -> None:
        if authorize_motion is not True or not self.config.framing_confirmed:
            raise ValueError("explicit motion authorization and verified firmware framing are required")
        if self._faulted:
            raise RuntimeError("TIO fault latched; close and inspect before starting a new owner")
        payload = write_command(self.config.slave_id, register, value)
        now = time.monotonic()
        if now - self._last_write < 0.25:
            raise RuntimeError("TIO writes are limited to 4 Hz; do not call from the arm servo loop")
        data = (C.c_uint8 * len(payload)).from_buffer_copy(payload)
        self._call("send_tio_rs_command", self.config.channel, data, len(payload))
        self._last_write = time.monotonic()

    def close(self) -> None:
        try:
            if self._sdk is not None and self._connected:
                self._check(self._sdk.destory_handler(C.byref(self._handle)), "destory_handler")
        finally:
            self._sdk = None
            self._connected = False
            self._owner_thread = None
            self._handle.value = -1
            if self._lock is not None:
                self._lock.close()
                self._lock = None
        # No open, zero target, power change, or motor command on exit.

    def __exit__(self, *unused) -> None:
        self.close()


def bundled_sdk(root: Path) -> Path:
    architecture = {"aarch64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
    if architecture is None:
        raise ValueError("the bundled JAKA SDK supports Linux aarch64 and x86_64 only")
    return root / f"third_party/jaka_sdk/v2.2.7/linux/python3/{architecture}-linux-gnu/libjakaAPI.so"
