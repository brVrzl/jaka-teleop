"""PGE integrated-controller manual 3.2 register contract (not RH56 data).

JAKA's Modbus RTU TIO command interface appends CRC. These payloads deliberately
contain slave address + PDU only. No serial port is opened by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

INITIALIZE = 0x0100
FORCE = 0x0101
POSITION = 0x0103
SPEED = 0x0104
FEEDBACK_REGISTERS = {"initialization": 0x0200, "grip": 0x0201, "position": 0x0202}


def write_command(slave_id: int, register: int, value: int) -> bytes:
    """Return exactly six bytes; never include a second CRC or ASCII hex."""
    if type(slave_id) is not int or not 1 <= slave_id <= 247:
        raise ValueError("slave_id must be an integer in [1, 247]; broadcast is prohibited")
    limits = {INITIALIZE: (1, 1), FORCE: (20, 100), POSITION: (0, 1000), SPEED: (1, 100)}
    if register not in limits:
        raise ValueError("register is outside the supported PGE command set")
    low, high = limits[register]
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"register 0x{register:04x} value must be an integer in [{low}, {high}]")
    return struct.pack(">BBHH", slave_id, 6, register, value)


@dataclass(frozen=True)
class Feedback:
    initialization: int
    grip: int
    position_permille: int
    host_query_monotonic_ns: int
    # SDK SignInfo exposes neither device sample timestamp nor bus-read success.
    freshness_verified: bool = False

    @classmethod
    def from_registers(cls, values: dict[str, int], query_ns: int) -> "Feedback":
        initial, grip, position = (values[k] for k in ("initialization", "grip", "position"))
        if any(type(v) is not int for v in (initial, grip, position)):
            raise ValueError("DH feedback must contain integer register values")
        if initial not in (0, 1, 2) or grip not in (0, 1, 2, 3) or not 0 <= position <= 1000:
            raise ValueError("DH feedback register value is outside the documented range")
        return cls(initial, grip, position, query_ns)
