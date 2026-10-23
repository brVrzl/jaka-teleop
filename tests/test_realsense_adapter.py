from __future__ import annotations

import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from vision_interface.realsense_adapter import (
    RealSenseCamera,
    _build_depth_filters,
    _configure_depth_sensor,
    list_realsense_devices,
    resolve_realsense_config,
)


class _FakeFrame:
    def __init__(
        self,
        data: np.ndarray,
        profile: "_FakeStreamProfile",
        *,
        timestamp_ms: float,
        frame_number: int,
    ) -> None:
        self._data = data
        self.profile = profile
        self._timestamp_ms = timestamp_ms
        self._frame_number = frame_number

    def get_data(self) -> np.ndarray:
        return self._data

    def get_profile(self) -> "_FakeStreamProfile":
        return self.profile

    def get_timestamp(self) -> float:
        return self._timestamp_ms

    def get_frame_timestamp_domain(self) -> str:
        return "global_time"

    def get_frame_number(self) -> int:
        return self._frame_number


class _FakeFrames:
    def __init__(self, rgb: np.ndarray, depth: np.ndarray) -> None:
        self.rgb = _FakeFrame(
            rgb,
            _FakeStreamProfile(fx=100.0, fy=101.0),
            timestamp_ms=1000.0,
            frame_number=10,
        )
        self.depth = _FakeFrame(
            depth,
            _FakeStreamProfile(fx=80.0, fy=81.0),
            timestamp_ms=1000.5,
            frame_number=9,
        )

    def get_color_frame(self) -> _FakeFrame:
        return self.rgb

    def get_depth_frame(self) -> _FakeFrame:
        return self.depth


class _FakePipeline:
    stopped = False

    def start(self, config: object) -> "_FakeProfile":
        return _FakeProfile()

    def wait_for_frames(self, timeout_ms: int) -> _FakeFrames:
        rgb = np.zeros((2, 3, 3), dtype=np.uint8)
        depth = np.array([[1000, 1200, 0], [800, 900, 1100]], dtype=np.uint16)
        return _FakeFrames(rgb, depth)

    def stop(self) -> None:
        _FakePipeline.stopped = True


class _FakeConfig:
    def enable_device(self, serial: str) -> None:
        self.serial = serial

    def enable_stream(self, *args: object) -> None:
        pass


class _FakeAlign:
    def __init__(self, stream: object) -> None:
        pass

    def process(self, frames: _FakeFrames) -> _FakeFrames:
        frames.depth.profile = frames.rgb.profile
        return frames


class _FakeDepthSensor:
    def get_depth_scale(self) -> float:
        return 0.001


class _FakeDevice:
    def first_depth_sensor(self) -> _FakeDepthSensor:
        return _FakeDepthSensor()

    def get_info(self, key: str) -> str:
        return {
            "name": "Intel RealSense D435",
            "serial": "123456",
            "usb": "3.2",
            "firmware": "5.0",
        }[key]


class _FakeProfile:
    def get_device(self) -> _FakeDevice:
        return _FakeDevice()

    def get_stream(self, stream: object) -> "_FakeStreamProfile":
        return _FakeStreamProfile()


class _FakeStreamProfile:
    def __init__(self, *, fx: float = 100.0, fy: float = 101.0) -> None:
        self.fx = fx
        self.fy = fy

    def as_video_stream_profile(self) -> "_FakeVideoProfile":
        return _FakeVideoProfile(fx=self.fx, fy=self.fy)


class _FakeVideoProfile:
    def __init__(self, *, fx: float, fy: float) -> None:
        self.fx = fx
        self.fy = fy

    def get_intrinsics(self) -> SimpleNamespace:
        return SimpleNamespace(
            width=3,
            height=2,
            fx=self.fx,
            fy=self.fy,
            ppx=1.5,
            ppy=1.0,
            model="inverse_brown_conrady",
            coeffs=[0.0] * 5,
        )


class _FakeContext:
    def query_devices(self) -> list[_FakeDevice]:
        return [_FakeDevice()]


def _fake_rs() -> SimpleNamespace:
    return SimpleNamespace(
        pipeline=_FakePipeline,
        config=_FakeConfig,
        align=_FakeAlign,
        context=_FakeContext,
        stream=SimpleNamespace(color="color", depth="depth"),
        format=SimpleNamespace(rgb8="rgb8", z16="z16"),
        camera_info=SimpleNamespace(
            name="name",
            serial_number="serial",
            usb_type_descriptor="usb",
            firmware_version="firmware",
        ),
    )


def test_realsense_camera_reads_rgb_depth_intrinsics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())
    camera = RealSenseCamera({"width": 3, "height": 2, "fps": 30, "warmup_frames": 0})

    frame = camera.capture()
    camera.close()

    assert frame.rgb.shape == (2, 3, 3)
    assert frame.rgb.dtype == np.uint8
    assert frame.depth_m.shape == (2, 3)
    assert frame.depth_m.dtype == np.float32
    np.testing.assert_allclose(frame.depth_m[0, 0], 1.0)
    assert frame.intrinsics.width == 3
    assert frame.intrinsics.height == 2
    assert frame.intrinsics.fx == 100.0
    assert frame.intrinsics.frame_id == "camera_color_optical_frame"
    assert frame.color_frame_number == 10
    assert frame.depth_frame_number == 9
    assert frame.timestamp_skew_ms == 0.5
    assert frame.depth_aligned_to_color is True
    assert _FakePipeline.stopped


def test_unaligned_depth_uses_depth_intrinsics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())
    camera = RealSenseCamera(
        {"width": 3, "height": 2, "fps": 30, "warmup_frames": 0, "align_depth_to_color": False}
    )

    frame = camera.capture()
    camera.close()

    assert frame.intrinsics.fx == 80.0
    assert frame.intrinsics.frame_id == "camera_depth_optical_frame"
    assert frame.depth_aligned_to_color is False


def test_rgb_only_capture_does_not_read_or_align_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())
    camera = RealSenseCamera(
        {
            "width": 3,
            "height": 2,
            "fps": 30,
            "warmup_frames": 0,
            "capture_depth": False,
        }
    )

    frame = camera.capture()
    camera.close()

    assert frame.depth_enabled is False
    assert frame.depth_frame_number == -1
    assert frame.depth_raw_units is not None
    assert frame.depth_raw_units.shape == (1, 1)
    assert frame.timestamps_comparable is False
    assert frame.intrinsics.frame_id == "camera_color_optical_frame"


def test_capture_discards_frames_above_timestamp_skew_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())
    camera = RealSenseCamera(
        {
            "width": 3,
            "height": 2,
            "fps": 30,
            "warmup_frames": 0,
            "max_timestamp_skew_ms": 5.0,
            "sync_retry_frames": 2,
        }
    )
    good = camera._capture_once()
    bad = replace(good, depth_timestamp_ms=good.color_timestamp_ms + 100.0)
    candidates = iter([bad, bad, good])
    monkeypatch.setattr(camera, "_capture_once", lambda: next(candidates))

    frame = camera.capture()
    camera.close()

    assert frame.timestamp_skew_ms == 0.5


def test_resolve_multi_camera_config_requires_explicit_name() -> None:
    config = {
        "width": 640,
        "fps": 30,
        "cameras": {
            "side": {"serial": "111", "frame_id": "side_color"},
            "top": {"serial": "222", "frame_id": "top_color"},
        },
    }

    with pytest.raises(ValueError, match="camera_name is required"):
        resolve_realsense_config(config)
    resolved = resolve_realsense_config(config, camera_name="top")

    assert resolved["serial"] == "222"
    assert resolved["width"] == 640
    assert resolved["camera_name"] == "top"


def test_depth_filters_use_recommended_disparity_order() -> None:
    calls: list[str] = []

    class _Filter:
        def __init__(self, name: str) -> None:
            self.name = name

    rs = SimpleNamespace(
        disparity_transform=lambda to_disparity: _Filter(
            calls.append("depth_to_disparity" if to_disparity else "disparity_to_depth") or calls[-1]
        ),
        spatial_filter=lambda *args: _Filter(calls.append("spatial") or calls[-1]),
        temporal_filter=lambda *args: _Filter(calls.append("temporal") or calls[-1]),
        hole_filling_filter=lambda *args: _Filter(calls.append("hole_filling") or calls[-1]),
    )

    _build_depth_filters(
        rs,
        {
            "use_disparity": True,
            "spatial": {"enabled": True},
            "temporal": {"enabled": True},
            "hole_filling": {"enabled": True},
        },
    )

    assert calls == [
        "depth_to_disparity",
        "spatial",
        "temporal",
        "disparity_to_depth",
        "hole_filling",
    ]


def test_configure_depth_sensor_maps_named_preset() -> None:
    selected: list[tuple[object, float]] = []
    option = object()
    sensor = SimpleNamespace(
        supports=lambda candidate: candidate is option,
        set_option=lambda candidate, value: selected.append((candidate, value)),
    )
    rs = SimpleNamespace(option=SimpleNamespace(visual_preset=option))

    _configure_depth_sensor(rs, sensor, {"visual_preset": "high-accuracy"})

    assert selected == [(option, 3.0)]


def test_list_realsense_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())

    assert list_realsense_devices() == [
        {
            "name": "Intel RealSense D435",
            "serial": "123456",
            "usb_type": "3.2",
            "firmware": "5.0",
        }
    ]


def test_multicamera_check_rejects_unbounded_duration_and_duplicate_identity(tmp_path) -> None:
    from tools.check_realsense_stream import check_configured_streams
    import yaml

    with pytest.raises(ValueError, match="duration"):
        check_configured_streams("unused", duration_sec=float("nan"), output_dir=str(tmp_path))
    config = tmp_path / "cameras.yaml"
    config.write_text(yaml.safe_dump({"cameras": {
        "workspace": {"serial": "same"}, "wrist": {"serial": "same"}}}))
    with pytest.raises(ValueError, match="unique"):
        check_configured_streams(str(config), duration_sec=1, output_dir=str(tmp_path / "capture"))


@pytest.mark.parametrize("failure_stage", ["configuration", "warmup"])
def test_camera_stops_pipeline_when_construction_fails(monkeypatch, failure_stage) -> None:
    import vision_interface.realsense_adapter as adapter
    _FakePipeline.stopped = False
    monkeypatch.setitem(sys.modules, "pyrealsense2", _fake_rs())
    def fail(*args, **kwargs):
        raise RuntimeError("camera startup failure")
    if failure_stage == "configuration":
        monkeypatch.setattr(adapter, "_configure_depth_sensor", fail)
    else:
        monkeypatch.setattr(RealSenseCamera, "capture", fail)
    with pytest.raises(RuntimeError, match="startup failure"):
        RealSenseCamera({"warmup_frames": 1})
    assert _FakePipeline.stopped


def test_camera_checks_refuse_existing_capture_before_device_access(tmp_path, monkeypatch) -> None:
    import yaml
    import tools.check_realsense_stream as check
    output = tmp_path / "capture"
    output.mkdir()
    original = output / "rgb.mp4"
    original.write_bytes(b"existing capture")
    monkeypatch.setattr(check, "list_realsense_devices", lambda: pytest.fail("must reject output before devices"))
    path = tmp_path / "cameras.yaml"
    path.write_text(yaml.safe_dump({"cameras": {"workspace": {"serial": "abc"}}}))
    with pytest.raises(FileExistsError):
        check.check_configured_streams(str(path), duration_sec=1, output_dir=str(output))
    with pytest.raises(FileExistsError):
        check.check_realsense_stream(duration_sec=1, width=640, height=480, fps=30,
                                    serial="abc", snapshot_dir=str(output))
    assert original.read_bytes() == b"existing capture"


def test_multicamera_record_failure_releases_writer_and_all_cameras(tmp_path, monkeypatch) -> None:
    import time
    import yaml
    import tools.check_realsense_stream as check
    cameras, writers = [], []
    class Camera:
        def __init__(self, cfg):
            self.serial, self.fps = cfg["serial"], 30
            self.closed, self.frames = False, 0
            cameras.append(self)
        def __enter__(self): return self
        def __exit__(self, *args): self.closed = True
        def profile_metadata(self): return {"color": {"nominal_fps": 15}}
        def capture(self):
            time.sleep(0.005)
            self.frames += 1
            if self.serial == "a" and self.frames > 1:
                raise RuntimeError("capture failed")
            return SimpleNamespace(rgb=np.zeros((2, 3, 3), np.uint8), depth_enabled=False,
                host_monotonic_ns=time.monotonic_ns(), host_wall_timestamp_ns=time.time_ns(),
                color_frame_number=self.frames, depth_frame_number=-1, color_timestamp_ms=1,
                depth_timestamp_ms=0, color_timestamp_domain="hardware_clock",
                depth_timestamp_domain="unavailable", depth_scale_m=None)
        def get_intrinsics(self): return SimpleNamespace(to_dict=lambda: {})
    class Writer:
        def __init__(self, path, codec, fps, shape):
            assert fps == 15  # Selected profile, not the requested 30 fps.
            self.released = False
            writers.append(self)
        def isOpened(self): return True
        def write(self, frame): pass
        def release(self): self.released = True
    fake_cv2 = SimpleNamespace(VideoWriter=Writer, VideoWriter_fourcc=lambda *args: 0,
        cvtColor=lambda frame, code: frame, COLOR_RGB2BGR=0, imwrite=lambda *args: True)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(check, "RealSenseCamera", Camera)
    monkeypatch.setattr(check, "list_realsense_devices", lambda: [])
    path = tmp_path / "cameras.yaml"
    path.write_text(yaml.safe_dump({"cameras": {"workspace": {"serial": "a"}, "wrist": {"serial": "b"}}}))
    with pytest.raises(RuntimeError, match="capture failed"):
        check.check_configured_streams(str(path), duration_sec=0.03, output_dir=str(tmp_path / "new"))
    assert len(cameras) == 2 and all(camera.closed for camera in cameras)
    assert writers and all(writer.released for writer in writers)
    assert not (tmp_path / "new" / "summary.json").exists()
