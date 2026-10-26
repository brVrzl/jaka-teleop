# jaka-teleop architecture

JAKA Robot Teleoperation & Demonstration maintains one live arm-target path:

```text
Quest RTOUCH v1 (right Grip + controller/head poses)
  -> motion_input.RightTouchInput / ControllerProvider (protocol facts)
  -> quest_jaka_sim.LiveQuestControllerRouter (routing only)
  -> SmoothQuestJakaSession
       -> motion_input.ArmClutchMachine (sole arm engagement authority)
       -> LatchedHeadYawArmMapper (reference, relative SE(3), filtering)
       -> SharedJakaTargetGenerator (continuation IK, joint/workspace/collision checks)
  -> immutable AcceptedArmTarget
       -> MuJoCo output adapter / JakaMujocoSimulation
       -> JakaAcceptedJointTargetAdapter -> native joint worker -> JAKA
```

`tools/quest_jaka_mujoco_sim.py live-6dof/replay-6dof` and
`tools/quest_jaka_hardware.py` construct this shared session. Hardware does not
follow simulation qpos, remap frames, or repeat IK. Its native worker retains
output limits, freshness watchdogs and controlled stopping. Hardware lifecycle,
status reception, process cleanup and device authorization belong in the
hardware entry point; viewer, simulation stepping and replay scheduling belong
in the simulation entry point. They are separate responsibilities.

`simulation.py` owns the model, authoritative joint state and feasibility
solver. `JakaMujocoSimulation` extends that solver with the plant; it is not a
second IK implementation. `smooth_session.py` coordinates references, mapping,
accepted targets, hand output and diagnostics. Moving these files wholesale
would not remove a duplicate implementation.

## Input loss and reference recovery

The arm uses the existing TRACKING_FAULT hold and REFERENCE_CAPTURE states;
there is no parallel recovery coordinator. Loss emits no new AcceptedArmTarget.
The existing disengaged heartbeat keeps the last safe target and lets native
controlled stopping proceed; it does not disable watchdogs.

Automatic reference capture requires all of the following:

- Previously engaged Grip, a newer valid sample with Grip above its press
  threshold, and the same trusted input continuity generation.
- At most twice the clutch stale interval since the last valid engaged sample
  (300 ms with the maintained 150 ms setting). This short recovery window is
  distinct from the existing persistent input-loss timeout.
- Valid current wrist/head poses. Capture uses the new raw pose, clearing the
  interpolation buffer so motion during the gap is not replayed.
- An authoritative simulation plant, or fresh physical joint measurements with
  native HOLDING state with CONNECTED, EDG_ACTIVE and STOPPED_READY, no error, no braking and no
  acceleration hold. Physical observation and worker ages must be no greater
  than the clutch stale interval. The feasibility solver still checks capture.

A successful capture resets the mapper and continuation reference: the first
relative transform is identity, then normal filtering and IK resume. If native
braking is not complete within the short window, automatic recovery is refused.
Release/repress remains available through the existing guarded control path.

`RightTouchInput` increments a host continuity generation when it observes a
session change, explicit invalid controller facts, malformed data, a source
clock discontinuity or a Grip release. This is derived transport evidence,
not an invented source sequence or controller validity. It also preserves
invalidations/releases received between control ticks. Recenter/focus/restart
must change the sender session, as specified by the RTOUCH sender patch.
Unsignalled source discontinuities cannot be inferred reliably from poses.

XRobo/legacy HTS does not provide equivalent controller validity and source
continuity. It does **not** receive a synthetic continuity generation and
retains release/reclutch recovery. Synthetic tests are labelled explicitly;
recorded unknown/invalid controls are not upgraded into valid controls.

Trigger gripper intention has its own release gate, relative reference,
measured initialization and rate limit in `RightTouchInput`. Arm recovery never
opens, seeds or resumes the gripper automatically. The input-only preview
reports `gripper_engaged`, not an authoritative arm clutch. RH56 skeleton
retargeting and its independent hand clutch remain separate.

## Retained and removed paths

| Code | Responsibility / decision |
| --- | --- |
| `motion_input` | Canonical protocol, timestamps, ordering, input facts and arm/hand clutch primitives. |
| `quest_jaka_sim/clutch.py` | Import-only compatibility exports; no state machine implementation. Retained for current public imports. |
| `teleoperation.accepted_target`, `jaka.quest_adapter`, `runtime`, `wire`, `output_feasibility` | Maintained output contract, transport and native lifecycle. |
| `teleoperation.processing.ClutchController` | Separate Cartesian processing prototype with its own tests; not called by the maintained Quest/JAKA path. Not adopted as a second live clutch. |
| `QuestJakaReplaySession` | Older `replay` CLI experiment, still has a real caller and tests; retained, not the live control path. Use `replay-6dof` for shared-path verification. |
| `teleop_rearchitecture.cpp_shaping` | Retained offline bindings to native shaping contracts and tests. |
| Former `teleop_rearchitecture.engagement` | Removed unused Python coordinator whose only callers were its tests. Native first-output continuity regression retained in `test_teleop_shaping_cpp.py`. |
| Former RightTouch arm release/engaged gate | Removed from arm sample authorization; retained and named only as the independent gripper gate. |
| Former session controller/wrist arm prefault checks | Consolidated into ArmClutchMachine; session still owns reference and target work. |

The RH56 workflows, model assets and raw/master datasets are retained. Episode
materializers produce derived views without rewriting source rows or videos.

## Mapper dependency decision

[teleopro_core](https://github.com/sdua078/teleopro/tree/main/teleopro_core)
provides pose mapping and input-loss reanchoring. Its `Teleop.update` reanchors
to the mapper's last target; its mapper also owns engagement and rate/workspace
limits. It does not supply this system's native readiness, session validity or
AcceptedArmTarget/continuation IK contract. Replacing the current mapper would
still require those gates plus adaptation of head-yaw and per-axis mapping,
while adding another engagement/limit owner. Keep the existing mapper; no new
library or adapter is needed for this recovery behavior.

## Offline validation

Run with the project's development environment; no hardware is needed:

```bash
python -m pytest -q tests/test_quest_jaka_shared_pipeline.py \
  tests/test_quest_live_controller_sim.py tests/test_precision_dual_clutch.py
python -m pytest -q tests/test_teleop_shaping_cpp.py tests/test_native_jaka_servo_worker.py
PYTHONPATH=src python tools/quest_jaka_mujoco_sim.py replay-6dof RECORDING.jsonl \
  --report /tmp/jaka-replay.json --events /tmp/jaka-replay.jsonl
```

Real recordings with invalid controllers should produce zero accepted targets;
this rejection is not evidence of successful automatic recovery or physical
acceptance. Use the labelled synthetic interruption cases to verify short/long
gaps, movement during loss, release, session/recenter, stale frames, explicit
tracking faults, hard stops, native freshness and gripper hold.
