"""Synthetic Quest packets and shared offline simulation setup."""
from dataclasses import replace
from pathlib import Path

from motion_input import Pose6D, ReceivedHtsDatagram
from quest_jaka_sim import JakaMujocoSimulation, ReplayConfig, SmoothQuestJakaSession
from quest_jaka_sim.simulation import build_viewer_mjcf


def hand_datagram(sequence, timestamp_ns, pose=Pose6D((0, 0, 0), (0, 0, 0, 1)), *, points=None):
    points = [(0, 0, 0)] * 21 if points is None else points
    landmarks = ",".join(str(value) for point in points for value in point)
    position = ",".join(str(value) for value in pose.position_m)
    orientation = ",".join(str(value) for value in pose.orientation_xyzw)
    payload = (f"Right wrist | f = {sequence}:,{position},{orientation}\n"
               f"Right landmarks | f = {sequence}:,{landmarks}").encode()
    return ReceivedHtsDatagram(payload, "127.0.0.1", 9000, timestamp_ns, timestamp_ns)


def head_datagram(sequence, timestamp_ns, orientation=(0, 0, 0, 1)):
    quaternion = ",".join(str(value) for value in orientation)
    payload = f"Head pose | f = {sequence}:,0,0,0,{quaternion}".encode()
    return ReceivedHtsDatagram(payload, "127.0.0.1", 9001, timestamp_ns, timestamp_ns)


def simulation_session(tmp_path: Path, *, input_recovery_timeout_s=None):
    config = replace(
        ReplayConfig.load("configs/sim/quest_hts_jaka_mini2_live_demo.yaml"),
        engagement_schedule_s=(),
    )
    if input_recovery_timeout_s is not None:
        config = replace(config, input_recovery_timeout_s=input_recovery_timeout_s)
    model = build_viewer_mjcf(config.mjcf_path, tmp_path / "viewer.xml")
    return SmoothQuestJakaSession(config, JakaMujocoSimulation(config, mjcf_path=model))
