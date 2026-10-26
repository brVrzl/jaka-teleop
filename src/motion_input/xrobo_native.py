"""Read-only native SDK callbacks shared by input observation and MuJoCo live.

Only PXREAInit/PXREADeinit are exposed. No robot command API is loaded.
"""
import ctypes as C
import json
import os
from pathlib import Path
import queue
import threading
import time

from motion_input.hts_transport import ReceivedHtsDatagram


class DeviceState(C.Structure):
    _fields_ = [('device_id', C.c_char * 32), ('state_json', C.c_char * 16352)]


class XRoboNativeReceiver:
    def __init__(self, sdk_path, log_path, *, capacity=256):
        self.sdk_path, self.log_path = Path(sdk_path), Path(log_path)
        self.queue = queue.Queue(maxsize=capacity)
        self.lock = threading.Lock()
        self.error = None
        self.dropped = 0
        self.sequence = 0
        self.sdk = self.log = None
        self.callback_type = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_int, C.c_void_p)
        self.callback = self.callback_type(self._callback)

    def _callback(self, context, kind, status, data):
        received_ns, unix_ns = time.monotonic_ns(), time.time_ns()
        try:
            with self.lock:
                record = {'host_callback_monotonic_s': received_ns / 1e9,
                          'host_callback_monotonic_ns': received_ns,
                          'host_callback_unix_ns': unix_ns,
                          'sdk_event': kind, 'status': status}
                if kind == 1 << 25:
                    state = C.cast(data, C.POINTER(DeviceState)).contents
                    raw = state.state_json.decode('utf-8')
                    self.sequence += 1
                    record.update(sdk_device_id=state.device_id.decode('utf-8'),
                                  local_callback_sequence=self.sequence, raw_payload=raw)
                else:
                    raw = None
                self.log.write(json.dumps(record) + '\n')
                self.log.flush()
                # Disconnect/service loss becomes an explicitly invalid input,
                # never an invented controller state or a cached last pose.
                if raw is not None or kind in (1 << 3, 1 << 5):
                    packet = ReceivedHtsDatagram((raw or '{}').encode(),
                        'native-sdk-callback', 0, received_ns, unix_ns)
                    try:
                        self.queue.put_nowait(packet)
                    except queue.Full:
                        self.dropped += 1
                        raise RuntimeError('XRobo callback queue overflow; input continuity lost')
        except Exception as exc:
            self.error = exc

    def start(self):
        # This SDK only connects to the local PC Service. gRPC otherwise inherits
        # shell HTTP proxies and may silently never establish its callback stream.
        exclusions = os.environ.get('no_grpc_proxy', os.environ.get('no_proxy', ''))
        os.environ['no_grpc_proxy'] = ','.join(filter(None, [exclusions, '127.0.0.1', 'localhost']))
        self.sdk = C.CDLL(str(self.sdk_path.resolve()))
        self.sdk.PXREAInit.argtypes = [C.c_void_p, self.callback_type, C.c_uint]
        self.sdk.PXREAInit.restype = C.c_int
        self.sdk.PXREADeinit.argtypes = []
        self.sdk.PXREADeinit.restype = C.c_int
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = self.log_path.open('x')
        result = self.sdk.PXREAInit(None, self.callback, 0xffffffff)
        if result != 0:
            self.log.close()
            self.log = None
            raise RuntimeError(f'PXREAInit failed: {result}')

    def drain(self):
        packets = []
        while True:
            try:
                packets.append(self.queue.get_nowait())
            except queue.Empty:
                return packets

    def raise_if_failed(self):
        if self.error is not None:
            raise RuntimeError(f'XRobo input failed: {self.error}') from self.error

    def close(self):
        if self.log is not None:
            self.sdk.PXREADeinit()
            self.log.close()
            self.log = None
