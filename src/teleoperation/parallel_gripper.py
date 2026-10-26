"""Device-independent parallel gripper intent. Authorization belongs to the arm session."""
from dataclasses import dataclass
import math
from typing import Protocol


@dataclass(frozen=True)
class GripperCommand:
    closed_fraction: float
    command_monotonic_ns: int
    source_monotonic_ns: int


@dataclass(frozen=True)
class GripperObservation:
    closed_fraction: float | None
    measured_monotonic_ns: int | None
    observed_monotonic_ns: int
    valid: bool
    fault: str | None = None
    source: str = 'unknown'


class ParallelGripperOutput(Protocol):
    def observe(self, now_ns: int) -> GripperObservation: ...
    def submit(self, command: GripperCommand) -> None: ...
    def hold(self) -> None: ...  # Retain intent; does NOT promise a mechanical stop.


class ParallelGripperControl:
    def __init__(self, output: ParallelGripperOutput, *, maximum_rate: float = 1.0,
                 feedback_timeout_s: float = .15):
        if not math.isfinite(maximum_rate) or maximum_rate <= 0:
            raise ValueError('gripper rate must be finite and positive')
        self.output = output
        self.maximum_rate = maximum_rate
        self.feedback_timeout_ns = int(feedback_timeout_s * 1e9)
        self.command: GripperCommand | None = None
        self.observation: GripperObservation | None = None
        self._reference = None
        self._last_ns = None

    def observe(self, now_ns: int) -> GripperObservation:
        o = self.output.observe(now_ns)
        if (not o.valid or o.fault or o.closed_fraction is None
                or not math.isfinite(o.closed_fraction) or not 0 <= o.closed_fraction <= 1
                or o.measured_monotonic_ns is None
                or not 0 <= now_ns - o.measured_monotonic_ns <= self.feedback_timeout_ns):
            raise RuntimeError(f'parallel gripper feedback unavailable: {o}')
        self.observation = o
        return o

    def update(self, *, authorized: bool, capture: bool, trigger: float,
               source_ns: int, now_ns: int) -> None:
        if not authorized:
            self._reference = None
            self._last_ns = None
            self.output.hold()
            return
        if not math.isfinite(trigger) or not 0 <= trigger <= 1:
            raise ValueError('trigger must be in [0,1]')
        if capture or self._reference is None:
            assert self.observation is not None
            target = self.observation.closed_fraction if self.command is None else self.command.closed_fraction
            self._reference = (trigger, target)
            self._last_ns = now_ns
            return  # No command on acquisition, including when Trigger is already held.
        start_trigger, start_target = self._reference
        desired = min(1.0, max(0.0, start_target + trigger - start_trigger))
        current = start_target if self.command is None else self.command.closed_fraction
        step = self.maximum_rate * min(.1, max(0.0, (now_ns - self._last_ns) / 1e9))
        target = current + max(-step, min(step, desired - current))
        self._last_ns = now_ns
        if target != current:
            command = GripperCommand(target, now_ns, source_ns)
            self.output.submit(command)
            self.command = command
