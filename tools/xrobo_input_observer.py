#!/usr/bin/env python3
"""Read-only XRobo native SDK callback capture (Linux/Windows SDK required).

Logs SDK application JSON events, not wire datagrams or polling-cache reads.
No robot commands or SDK device-control calls are made.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import time


from motion_input.xrobo import parse_tracking


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', type=Path, required=True, help='absolute path to native SDK library')
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--duration', type=float, default=0)
    p.add_argument('--timeout', type=float, default=.15)
    args = p.parse_args()
    if args.duration < 0 or args.timeout <= 0:
        p.error('duration must be nonnegative; timeout must be positive')
    from motion_input.xrobo import XRoboNativeInput
    from motion_input.xrobo_native import XRoboNativeReceiver
    worker = XRoboNativeReceiver(args.sdk, args.log)
    source = XRoboNativeInput(args.timeout)
    start = time.monotonic()
    next_status = start
    times = deque()
    worker.start()
    try:
        while not args.duration or time.monotonic() - start < args.duration:
            worker.raise_if_failed()
            for packet in worker.drain():
                source.ingest(packet.payload.decode(), packet.receive_monotonic_ns)
                times.append(packet.receive_monotonic_ns)
            now = time.monotonic_ns()
            while times and now - times[0] > 1_000_000_000:
                times.popleft()
            if time.monotonic() >= next_status:
                age = None if source.received_ns is None else (now-source.received_ns)/1e9
                fresh = source.frame is not None and age is not None and 0 <= age <= args.timeout
                print(json.dumps({'status':'receiving' if fresh else 'stale' if age else 'waiting',
                    'local_callback_sequence':worker.sequence, 'age_s':age,
                    'tracking_callbacks_hz_1s':len(times),
                    'preview_rejection':source.preview_rejection(now),
                    'current_frame':source.frame if fresh else None}), flush=True)
                next_status = time.monotonic() + .5
            time.sleep(.005)
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()


if __name__ == '__main__':
    main()
