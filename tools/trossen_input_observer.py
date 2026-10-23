#!/usr/bin/env python3
"""Read-only Trossen JSON/UDP observer. Never imports robot drivers."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import socket
import time


def reject_constant(value):
    raise ValueError(f'nonfinite JSON constant: {value}')


def parse_payload(raw):
    data = json.loads(raw.decode('utf-8'), parse_constant=reject_constant)
    if not isinstance(data, dict) or not isinstance(data.get('right_controller'), dict):
        raise ValueError('missing right_controller object')
    right = data['right_controller']
    if type(right.get('is_tracked')) not in (int, bool) or right['is_tracked'] not in (0, 1):
        raise ValueError('invalid is_tracked')
    fields = {'pose6d': ('x', 'y', 'z', 'ax', 'ay', 'az'),
              'triggers': ('hand_trigger', 'index_trigger'),
              'buttons': ('one', 'two'), 'thumbstick': ('x_axis', 'y_axis')}
    missing = []
    for group, names in fields.items():
        obj = right.get(group, {})
        if not isinstance(obj, dict):
            raise ValueError(f'invalid {group}')
        for name in names:
            if name not in obj:
                missing.append(f'{group}.{name}')
                continue
            value = obj[name]
            if type(value) not in (int, float, bool) or not math.isfinite(value):
                raise ValueError(f'invalid {group}.{name}')
            if group == 'triggers' and not 0 <= value <= 1:
                raise ValueError(f'out of range {group}.{name}')
            if group == 'buttons' and value not in (0, 1):
                raise ValueError(f'invalid button {name}')
    return data, missing


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind', default='0.0.0.0')
    p.add_argument('--port', type=int, default=9000)
    p.add_argument('--ack-port', type=int, default=9001)
    p.add_argument('--allowed-sender', required=True)
    p.add_argument('--timeout', type=float, default=0.15)
    p.add_argument('--duration', type=float, default=0, help='seconds; 0 runs until Ctrl-C')
    p.add_argument('--log', type=Path, required=True)
    args = p.parse_args()
    if args.timeout <= 0 or args.duration < 0:
        p.error('timeout must be positive; duration must be nonnegative')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock, args.log.open('x') as log:
        sock.bind((args.bind, args.port))  # Exclusive owner; no SO_REUSEADDR.
        sock.settimeout(0.05)
        start = time.monotonic()
        last = None
        latest = None
        seq = 0
        times = deque()
        display = start
        try:
            while not args.duration or time.monotonic() - start < args.duration:
                try:
                    raw, source = sock.recvfrom(65535)
                    received = time.monotonic()
                except socket.timeout:
                    raw = None
                if raw is not None and source[0] == args.allowed_sender:
                    try:
                        data, missing = parse_payload(raw)
                    except (ValueError, UnicodeError) as exc:
                        print(json.dumps({'rejected': str(exc), 'source': source}), flush=True)
                    else:
                        seq += 1
                        last = received
                        latest = {'right_controller': data['right_controller'], 'missing': missing}
                        times.append(received)
                        while times and received - times[0] > 1:
                            times.popleft()
                        record = {'host_monotonic_s': received, 'source': source,
                                  'local_receive_sequence': seq, 'raw_payload': raw.decode('utf-8'),
                                  'missing': missing}
                        log.write(json.dumps(record, allow_nan=False) + '\n')
                        log.flush()
                        ack = {'type': 'ack', 'timestamp': int(time.time() * 1000),
                               'frequency_hz': len(times) / min(1, max(received - start, 0.001))}
                        sock.sendto(json.dumps(ack).encode(), (source[0], args.ack_port))
                now = time.monotonic()
                while times and now - times[0] > 1:
                    times.popleft()
                if now >= display:
                    age = None if last is None else now - last
                    fresh = age is not None and age <= args.timeout
                    print(json.dumps({'status': 'receiving' if fresh else 'stale' if last else 'waiting',
                                      'current_frame_valid': fresh, 'last_valid_packet_age_s': age,
                                      'receive_hz_1s': len(times), 'local_receive_sequence': seq,
                                      'current_frame': latest if fresh else None}), flush=True)
                    display = now + 0.5
        except KeyboardInterrupt:
            pass
        print(json.dumps({'received_valid_datagrams': seq, 'log': str(args.log)}), flush=True)


if __name__ == '__main__':
    main()
