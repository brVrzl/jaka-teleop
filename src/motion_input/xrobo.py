"""XRobo v1 native JSON facts, not RTOUCH or verified tracking authorization.

The sender has already converted handedness. UTC and application elapsed time
are evidence only; neither is a source sequence/session or a host freshness clock.
"""
from __future__ import annotations
import json
import math


def parse_tracking(raw: str) -> dict | None:
    envelope = json.loads(raw)
    if envelope.get('functionName') != 'Tracking':
        return None
    value = json.loads(envelope['value'])
    right = value['Controller']['right']
    pose = [float(x) for x in right['pose'].split(',')]
    if len(pose) != 7 or not all(math.isfinite(x) for x in pose):
        raise ValueError('invalid right pose')
    for key in ('grip', 'trigger'):
        number = right[key]
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError(f'invalid right {key}')
    for key in ('secondaryButton',):
        if key in right and type(right[key]) is not bool:
            raise ValueError(f'invalid right {key}')
    return {'right_controller': right, 'position_m': pose[:3],
            'orientation_xyzw': pose[3:], 'head': value.get('Head'),
            'app_state': value.get('appState'), 'input_device': value.get('Input'),
            'source_time_stamp_ns': value.get('timeStampNs'),
            'source_predict_time_us': value.get('predictTime'),
            'missing': [key for key in ('is_tracked', 'status', 'connected') if key not in right],
            'controller_connected': None, 'controller_tracked': None,
            'source_sequence': None, 'source_session': None,
            'reference_space_verified': False, 'hardware_authorized': False}


class XRoboNativeInput:
    """Freshness/order diagnostics, retaining unknown source validity explicitly."""
    def __init__(self, stale_after_s: float = .15):
        self.stale_ns = int(stale_after_s * 1e9)
        self.frame = None
        self.received_ns = None
        self.local_callback_count = 0
        self.rejected = 0
        self.reason = 'waiting'
        self.interrupted = False
        self._utc = self._elapsed = None

    def ingest(self, raw: str, received_ns: int) -> bool:
        self.local_callback_count += 1
        self.interrupted = False
        try:
            frame = parse_tracking(raw)
            if frame is None:
                raise ValueError('not_tracking')
            utc, elapsed = frame['source_time_stamp_ns'], frame['source_predict_time_us']
            if (type(utc) is not int or utc <= 0 or type(elapsed) not in (int, float)
                    or not math.isfinite(elapsed) or elapsed < 0):
                raise ValueError('source_time_missing_or_invalid')
            if self.received_ns is not None and received_ns <= self.received_ns:
                raise ValueError('host_time_not_forward')
            if self._utc is not None and utc <= self._utc:
                raise ValueError('source_utc_not_forward')
            restarted = self._elapsed is not None and elapsed < self._elapsed
            if self._elapsed is not None and elapsed == self._elapsed:
                raise ValueError('duplicate_source_elapsed')
            inconsistent_clocks = (self._utc is not None and not restarted and
                abs((utc-self._utc)/1e9 - (elapsed-self._elapsed)/1e6) > .15)
            self.interrupted = bool(restarted or (self._elapsed is not None and
                elapsed - self._elapsed > self.stale_ns / 1000) or (self.received_ns is not None
                and received_ns - self.received_ns > self.stale_ns))
            self._utc, self._elapsed = utc, elapsed
            self.received_ns, self.frame = received_ns, frame
            if inconsistent_clocks:
                raise ValueError('source_clocks_inconsistent')
            self.reason = self.preview_rejection(received_ns)
            if self.reason is not None:
                self.rejected += 1
            return self.reason is None
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self.rejected += 1
            self.frame = None
            self.reason = str(exc)
            self.interrupted = True
            return False

    def preview_rejection(self, now_ns: int) -> str | None:
        """Necessary numeric checks for an UNVERIFIED simulation preview only."""
        f = self.frame
        if f is None:
            return 'no_frame'
        if not 0 <= now_ns - self.received_ns <= self.stale_ns:
            return 'callback_stale'
        if not isinstance(f['app_state'], dict) or f['app_state'].get('focus') is not True:
            return 'app_not_focused'
        head = f['head']
        if not isinstance(head, dict) or head.get('status') != 3 or 'pose' not in head:
            return 'head_invalid'
        try:
            head_pose = [float(x) for x in head['pose'].split(',')]
        except (ValueError, AttributeError):
            return 'head_pose_invalid'
        if (len(head_pose) != 7 or not all(math.isfinite(x) for x in head_pose)
                or abs(sum(x*x for x in head_pose[3:]) ** .5 - 1) > .001):
            return 'head_pose_invalid'
        # Explicit observed disconnect sentinel; passing this is NOT tracking proof.
        if all(x == 0 for x in f['position_m']):
            return 'zero_controller_pose'
        norm = sum(x*x for x in f['orientation_xyzw']) ** .5
        if abs(norm - 1) > .001:
            return 'controller_quaternion_invalid'
        return None
