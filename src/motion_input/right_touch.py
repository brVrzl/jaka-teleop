"""RTOUCH v1 input: right Touch pose/buttons, with no hand skeleton dependency.

Coordinates on the wire are Unity world-space metres and xyzw quaternions.
Only this boundary performs the Unity -> canonical OpenXR basis conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .clutch import AnalogClutchSample
from .controller_protocol import ControllerPacket, ControllerPacketError
from .controller_provider import ControllerProvider
from .frames import unity_to_openxr_pose
from .hts_canonical import CanonicalQuestState, QuestHandObservation, QuestHeadObservation
from .hts_transport import ReceivedHtsDatagram
from .model import Pose6D, Side, TrackingState

RIGHT_TOUCH_MODE = "right-touch-v1"
LEGACY_MODE = "hts-ctrl-v1"
_FIELDS = ("v", "session", "seq", "t_ns", "connected", "active", "tracked",
           "head_tracked", "index", "grip", "px", "py", "pz", "qx", "qy", "qz", "qw",
           "hpx", "hpy", "hpz", "hqx", "hqy", "hqz", "hqw")
_FLOAT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_UINT = re.compile(r"[0-9]+\Z")


@dataclass(frozen=True, slots=True)
class RightTouchPacket(ControllerPacket):
    head_tracked: bool
    pose: Pose6D
    head_pose: Pose6D


def parse_right_touch_datagram(payload: bytes) -> RightTouchPacket:
    """Strict fixed-order bounded UTF-8 frame; never repairs invalid rotations."""
    if not payload or len(payload) > 2048:
        raise ControllerPacketError("RTOUCH datagram must contain 1..2048 bytes")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ControllerPacketError("RTOUCH is not UTF-8") from exc
    parts = text.removesuffix("\n").split(",")
    if parts[0] != "RTOUCH" or len(parts) != len(_FIELDS) + 1:
        raise ControllerPacketError("RTOUCH v1 requires exactly 24 ordered fields")
    values: dict[str, str] = {}
    for key, part in zip(_FIELDS, parts[1:], strict=True):
        name, sep, value = part.partition("=")
        if name != key or not sep or not value:
            raise ControllerPacketError(f"RTOUCH expected field {key}")
        values[key] = value

    def uint(name: str) -> int:
        raw = values[name]
        if _UINT.fullmatch(raw) is None or len(raw) > 20 or int(raw) > 2**64 - 1:
            raise ControllerPacketError(f"RTOUCH {name} must be uint64")
        return int(raw)

    def boolean(name: str) -> bool:
        if values[name] not in ("0", "1"):
            raise ControllerPacketError(f"RTOUCH {name} must be 0 or 1")
        return values[name] == "1"

    def number(name: str) -> float:
        if _FLOAT.fullmatch(values[name]) is None:
            raise ControllerPacketError(f"RTOUCH {name} must be a finite number")
        value = float(values[name])
        if not math.isfinite(value):
            raise ControllerPacketError(f"RTOUCH {name} must be finite")
        return value

    if uint("v") != 1:
        raise ControllerPacketError("unsupported RTOUCH version")
    index, grip = number("index"), number("grip")
    if not 0 <= index <= 1 or not 0 <= grip <= 1:
        raise ControllerPacketError("RTOUCH analog values must be in [0,1]")

    def pose(prefix: str) -> Pose6D:
        try:
            return unity_to_openxr_pose(Pose6D(
                tuple(number(prefix + name) for name in ("px", "py", "pz")),
                tuple(number(prefix + name) for name in ("qx", "qy", "qz", "qw")),
            ))
        except ValueError as exc:
            raise ControllerPacketError(f"RTOUCH invalid pose: {exc}") from exc

    return RightTouchPacket(1, uint("session"), uint("seq"), uint("t_ns"),
                            boolean("connected"), boolean("active"), boolean("tracked"),
                            index, grip, boolean("head_tracked"), pose(""), pose("h"))


class RightTouchInput:
    """Ordered raw pose/buttons. The shared session owns the sole Grip clutch."""
    def __init__(self, *, stale_after_s: float = 0.15, released_at: float = 0.55) -> None:
        self.provider = ControllerProvider(stale_after_s=stale_after_s,
                                           source_pause_after_s=stale_after_s)
        self.released_at = released_at
        self._session: int | None = None
        self._continuity_generation = 0
        self._host_sequence = 0
        self._accepted_packet: RightTouchPacket | None = None
        self.malformed = 0
        self.error: str | None = None
        self.canonical: CanonicalQuestState | None = None
        self.arm_sample = AnalogClutchSample(0, 0, 0, valid=False)
        self.trigger_sample = self.arm_sample
        self.session_changed = False
        self.last_state = self.provider.snapshot(now_monotonic_ns=0)

    def ingest(self, datagram: ReceivedHtsDatagram) -> bool:
        self.session_changed = False
        self.error = None
        try:
            packet = parse_right_touch_datagram(datagram.payload)
        except ControllerPacketError as exc:
            self._continuity_generation += 1
            self.malformed += 1
            self.error = str(exc)
            self.provider.invalidate("malformed_right_touch")
            self.poll(datagram.receive_monotonic_ns)
            return False
        previous = self.provider.snapshot(now_monotonic_ns=datagram.receive_monotonic_ns)
        state = self.provider.update(packet, host_receive_monotonic_ns=datagram.receive_monotonic_ns)
        accepted = state.accepted_count > previous.accepted_count
        if accepted:
            self.session_changed = self._session != packet.session_id
            if (self.session_changed or not packet.facts_valid
                    or (state.source_interval_ns is not None and
                        (state.source_interval_ns <= 0 or state.source_interval_ns > 2 * self.provider.stale_after_ns))
                    or (self._accepted_packet is not None
                        and self._accepted_packet.grip_trigger > self.released_at
                        and packet.grip_trigger <= self.released_at)):
                self._continuity_generation += 1
            if self.session_changed:
                self._session = packet.session_id
            if state.source_interval_ns is not None and state.source_interval_ns <= 0:
                self.provider.invalidate("source_clock_not_forward")
            self._accepted_packet = packet
            self._host_sequence += 1
        self.poll(datagram.receive_monotonic_ns)
        if accepted:
            self.canonical = self._canonical(packet, datagram.receive_monotonic_ns)
        return accepted and self.error is None

    def poll(self, now_ns: int) -> None:
        state = self.provider.snapshot(now_monotonic_ns=now_ns)
        self.last_state = state
        packet = self._accepted_packet
        if packet is None or state.host_receive_monotonic_ns is None:
            return
        valid = state.controller_valid
        sample = AnalogClutchSample(packet.grip_trigger, state.host_receive_monotonic_ns,
                                   self._host_sequence, valid=valid,
                                   source_timestamp_ns=packet.source_timestamp_ns,
                                   continuity_generation=self._continuity_generation)
        self.arm_sample = sample
        self.trigger_sample = AnalogClutchSample(packet.index_trigger,
            state.host_receive_monotonic_ns, self._host_sequence, valid=valid,
            source_timestamp_ns=packet.source_timestamp_ns,
            continuity_generation=self._continuity_generation)

    def _canonical(self, packet: RightTouchPacket, receive_ns: int) -> CanonicalQuestState:
        valid = self.last_state.controller_valid
        right = QuestHandObservation(Side.RIGHT,
            TrackingState.TRACKING if valid else TrackingState.NOT_TRACKING,
            valid, receive_ns, packet.source_timestamp_ns, packet.sequence_number,
            self._host_sequence, 0.0, packet.pose, "right_touch_grip", joints=())
        left = QuestHandObservation(Side.LEFT, TrackingState.DISCONNECTED, False,
                                   None, None, None, None, None, None, "left_wrist")
        head = QuestHeadObservation(packet.head_tracked and packet.active, receive_ns,
            packet.source_timestamp_ns, packet.sequence_number, 0.0, packet.head_pose, 1.0)
        return CanonicalQuestState(receive_ns, packet.source_timestamp_ns, self._host_sequence,
            "quest_world", head, left, right,
            {"input_mode": RIGHT_TOUCH_MODE, "session": packet.session_id,
             "pose_semantic": "controller_grip_pose", "hand_skeleton_present": False})

    def summary(self, now_ns: int) -> dict[str, object]:
        self.poll(now_ns)
        state, packet = self.last_state, self._accepted_packet
        return {"input_mode": RIGHT_TOUCH_MODE, "ctrl_packets": state.packet_count,
            "accepted_packets": state.accepted_count, "malformed_ctrl": self.malformed,
            "controller_valid": state.controller_valid, "controller_stale": state.stale,
            "session": None if packet is None else packet.session_id,
            "seq": None if packet is None else packet.sequence_number,
            "source_t_ns": None if packet is None else packet.source_timestamp_ns,
            "sample_age_ms": None if state.sample_age_ns is None else state.sample_age_ns / 1e6,
            "position_m": None if packet is None else packet.pose.position_m,
            "orientation_xyzw": None if packet is None else packet.pose.orientation_xyzw,
            "grip": None if packet is None else packet.grip_trigger,
            "trigger": None if packet is None else packet.index_trigger,
            "head_valid": bool(packet and packet.head_tracked),
            "gap_events": state.gap_event_count,
            "duplicates": state.duplicate_count, "reorders": state.reorder_count,
            "new_sessions": state.new_session_count, "active_fault": state.active_fault,
            "safety": "input_only_no_robot_targets"}
