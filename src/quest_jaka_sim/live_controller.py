"""Explicit Quest input routing into the shared target-generation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from motion_input.clutch import AnalogClutchSample
from motion_input.controller_protocol import ControllerPacketError, parse_controller_datagram
from motion_input.controller_provider import (
    ControllerClutchAdapter,
    ControllerProvider,
    ControllerProviderState,
)
from motion_input.hts_transport import ReceivedHtsDatagram
from motion_input.hts_canonical import CanonicalQuestState
from motion_input.right_touch import LEGACY_MODE, RIGHT_TOUCH_MODE, RightTouchInput


class _PoseBuffer(Protocol):
    def clear(self) -> None: ...


class _SmoothSession(Protocol):
    buffer: _PoseBuffer
    parallel_trigger: AnalogClutchSample

    def ingest_shared_state(self, state: CanonicalQuestState, *, pose_only: bool = False) -> bool: ...

    def ingest(self, datagram: ReceivedHtsDatagram) -> bool: ...

    def set_clutch_samples(
        self,
        *,
        index: AnalogClutchSample,
        grip: AnalogClutchSample,
        left_controller_valid: bool,
        provider: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class LiveRouteResult:
    kind: str
    accepted: bool
    error: str | None = None


class LiveQuestControllerRouter:
    """Select legacy HTS/CTRL or right Touch on the existing UDP socket."""

    def __init__(
        self,
        *,
        stale_after_s: float,
        released_at: float = 0.55,
        input_mode: str = LEGACY_MODE,
    ) -> None:
        if input_mode not in (LEGACY_MODE, RIGHT_TOUCH_MODE):
            raise ValueError(f"unknown Quest input mode {input_mode!r}")
        self.input_mode = input_mode
        self.touch = RightTouchInput(stale_after_s=stale_after_s, released_at=released_at) if input_mode == RIGHT_TOUCH_MODE else None
        self.provider = ControllerProvider(stale_after_s=stale_after_s)
        self.adapter = ControllerClutchAdapter(released_at=released_at)
        self.controller_datagrams = 0
        self.hand_head_datagrams = 0
        self.malformed_controller_datagrams = 0
        self.last_state = self.provider.snapshot(now_monotonic_ns=0)

    def ingest(
        self, datagram: ReceivedHtsDatagram, session: _SmoothSession
    ) -> LiveRouteResult:
        if self.touch is not None:
            accepted = self.touch.ingest(datagram)
            self.last_state = self.touch.last_state
            if accepted and self.touch.canonical is not None:
                if self.touch.session_changed:
                    session.buffer.clear()
                session.ingest_shared_state(self.touch.canonical, pose_only=True)
            self._publish_touch(session)
            return LiveRouteResult("right_touch", accepted, self.touch.error)
        if not datagram.payload.startswith(b"CTRL"):
            self.hand_head_datagrams += 1
            accepted = session.ingest(datagram)
            return LiveRouteResult("hand_head", accepted)
        try:
            packet = parse_controller_datagram(datagram.payload)
        except ControllerPacketError as exc:
            self.malformed_controller_datagrams += 1
            self.provider.invalidate("malformed_ctrl")
            self.last_state = self.provider.snapshot(
                now_monotonic_ns=datagram.receive_monotonic_ns
            )
            self._publish(session, self.last_state)
            return LiveRouteResult("controller", False, str(exc))
        self.controller_datagrams += 1
        self.last_state = self.provider.update(
            packet,
            host_receive_monotonic_ns=datagram.receive_monotonic_ns,
        )
        self._publish(session, self.last_state)
        return LiveRouteResult("controller", True)

    def poll(self, now_monotonic_ns: int, session: _SmoothSession) -> None:
        if self.touch is not None:
            self.touch.poll(now_monotonic_ns)
            self.last_state = self.touch.last_state
            self._publish_touch(session)
            return
        self.last_state = self.provider.snapshot(now_monotonic_ns=now_monotonic_ns)
        self._publish(session, self.last_state)

    def _publish_touch(self, session: _SmoothSession) -> None:
        assert self.touch is not None
        sample = self.touch.arm_sample
        session.parallel_trigger = self.touch.trigger_sample
        disabled_hand = AnalogClutchSample(0.0, sample.host_receive_monotonic_ns,
            sample.sequence_number, valid=False)
        session.set_clutch_samples(index=sample, grip=disabled_hand,
            left_controller_valid=sample.valid, provider="quest_right_touch_udp_v1")

    def telemetry(self) -> dict[str, object]:
        if self.touch is not None:
            state = self.touch.last_state
            return {"controller_provider": "quest_right_touch_udp_v1",
                "controller_datagrams": state.packet_count,
                "malformed_controller_datagrams": self.touch.malformed,
                "controller_valid": state.controller_valid,
                "controller_stale": state.stale,
                "trigger": self.touch.trigger_sample.value}
        state = self.last_state
        packet = state.latest
        return {
            "controller_provider": "quest_ctrl_udp_v1",
            "controller_datagrams": self.controller_datagrams,
            "hand_head_datagrams": self.hand_head_datagrams,
            "malformed_controller_datagrams": self.malformed_controller_datagrams,
            "controller_session": None if packet is None else packet.session_id,
            "controller_sequence": None if packet is None else packet.sequence_number,
            "controller_valid": state.controller_valid,
            "controller_stale": state.stale,
            "controller_invalid_reason": state.invalid_reason,
            "controller_gap_events": state.gap_event_count,
            "controller_missing_sequences": state.missing_sequence_count,
            "controller_duplicates": state.duplicate_count,
            "controller_reorders": state.reorder_count,
            "controller_new_sessions": state.new_session_count,
            "controller_old_session_packets": state.old_session_packet_count,
            "controller_invalid_samples": state.invalid_count,
            "controller_stale_events": state.stale_event_count,
        }

    def _publish(
        self, session: _SmoothSession, state: ControllerProviderState
    ) -> None:
        frame = self.adapter.samples(state)
        session.set_clutch_samples(
            index=frame.index,
            grip=frame.grip,
            left_controller_valid=frame.controller_valid,
            provider=frame.provider_name,
        )
