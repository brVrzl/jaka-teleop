#!/usr/bin/env python3
"""Read-only XRobo native SDK callback capture (Linux/Windows SDK required).

Logs SDK application JSON events, not wire datagrams or polling-cache reads.
No robot commands or SDK device-control calls are made.
"""
import argparse
from collections import deque
import ctypes as C
import json
import math
from pathlib import Path
import threading
import time


class DeviceState(C.Structure):
    # PXREARobotSDK.h from PC-Service v1.0.0.
    _fields_ = [('device_id', C.c_char * 32), ('state_json', C.c_char * 16352)]


def parse_tracking(raw):
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
    return {'right_controller': right, 'position_m': pose[:3],
            'orientation_xyzw': pose[3:], 'head': value.get('Head'),
            'app_state': value.get('appState'), 'input_device': value.get('Input'),
            'source_time_stamp_ns': value.get('timeStampNs'),
            'source_predict_time_us': value.get('predictTime'),
            'missing': [key for key in ('is_tracked', 'status', 'connected') if key not in right],
            'source_sequence': None, 'source_session': None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', type=Path, required=True, help='absolute path to native SDK library')
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--duration', type=float, default=0)
    p.add_argument('--timeout', type=float, default=.15)
    args = p.parse_args()
    if args.duration < 0 or args.timeout <= 0:
        p.error('duration must be nonnegative; timeout must be positive')
    sdk = C.CDLL(str(args.sdk.resolve()))
    callback_type = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_int, C.c_void_p)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    last = None
    sequence = 0
    latest = None
    times = deque()
    start = time.monotonic()
    with args.log.open('x') as log:
        @callback_type
        def callback(context, kind, status, data):
            nonlocal last, sequence, latest
            received = time.monotonic()
            if kind != 1 << 25:
                print(json.dumps({'sdk_event': kind, 'status': status,
                                  'host_callback_monotonic_s': received}), flush=True)
                if kind in (1 << 3, 1 << 5):
                    with lock:
                        latest = None
                return
            state = C.cast(data, C.POINTER(DeviceState)).contents
            try:
                raw = state.state_json.decode('utf-8')
                frame = parse_tracking(raw)
                source = state.device_id.decode('utf-8')
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                print(json.dumps({'rejected': str(exc), 'host_callback_monotonic_s': received}), flush=True)
                return
            with lock:
                sequence += 1
                log.write(json.dumps({'host_callback_monotonic_s': received,
                                     'sdk_device_id': source, 'local_callback_sequence': sequence,
                                     'raw_payload': raw}) + '\n')
                log.flush()
                if frame is not None:
                    last = received
                    latest = frame
                    times.append(received)
                    while times and received - times[0] > 1:
                        times.popleft()

        sdk.PXREAInit.argtypes = [C.c_void_p, callback_type, C.c_uint]
        sdk.PXREAInit.restype = C.c_int
        sdk.PXREADeinit.argtypes = []
        sdk.PXREADeinit.restype = C.c_int
        result = sdk.PXREAInit(None, callback, 0xffffffff)
        if result != 0:
            raise RuntimeError(f'PXREAInit failed: {result}')
        try:
            while not args.duration or time.monotonic() - start < args.duration:
                time.sleep(.5)
                with lock:
                    now = time.monotonic()
                    age = None if last is None else now - last
                    while times and now - times[0] > 1:
                        times.popleft()
                    fresh = latest is not None and age is not None and age <= args.timeout
                    print(json.dumps({'status': 'receiving' if fresh else 'stale' if last else 'waiting',
                                      'local_callback_sequence': sequence, 'age_s': age,
                                      'tracking_callbacks_hz_1s': len(times),
                                      'current_frame': latest if fresh else None}), flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            sdk.PXREADeinit()


if __name__ == '__main__':
    main()
