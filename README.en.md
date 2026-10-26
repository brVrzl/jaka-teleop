# jaka-teleop

**JAKA Robot Teleoperation & Demonstration**

**Quest input, guarded robot teleoperation, and review-first RGB-D datasets.**

[中文首页](README.md) · [Installation](docs/setup/INSTALLATION.md#english) · [Configuration](docs/configuration/CONFIGURATION.md) · [Documentation](docs/README.md#english)

![Actual MuJoCo rendering of the repository JAKA/RH56 model on Thor](docs/media/simulation.png)

This image was rendered from the repository model after an offline simulation step on Thor.
It depicts the historical RH56 model, not a verified physical DH installation or a completed hardware demonstration.

[Actual simultaneous D435 recording (5 seconds)](docs/media/dual-d435-check.mp4) · [Deployment evidence and open items](docs/setup/DEVICE_STATUS.md).
The left view is workspace and the right is the user-confirmed wrist camera. The recording contains no robot state and is not a DH teleoperation demo.

The project connects validated Quest input to a shared relative-pose, filtering, IK and feasibility pipeline.
An immutable `AcceptedArmTarget` feeds either MuJoCo or the JAKA joint adapter.
The physical adapter does not follow simulation `qpos` or run a second IK solver.
RGB-D, robot state, actions and timing can be recorded as episodes for review before dataset promotion.

## Start without hardware

```bash
git clone https://github.com/brVrzl/jaka-teleop.git
cd jaka-teleop
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[simulation]'
.venv/bin/embodied-lab --help
.venv/bin/embodied-lab doctor
.venv/bin/embodied-lab sim smoke
```

Python 3.10+ is required. Help, `doctor`, offline replay and smoke do not connect to actuators.
Use the [installation guide](docs/setup/INSTALLATION.md#english) for system prerequisites, native builds and role-specific extras.
Training submodules and model weights are not required for this quick start.

| Task | Entry |
| --- | --- |
| Configure a new machine | [Configuration](docs/configuration/CONFIGURATION.md) |
| Simulate or replay | [Simulation](docs/simulation/SIMULATION.md) |
| Inspect Quest transport | [Right Touch](docs/motion_input/RIGHT_TOUCH.md), [legacy input gate](docs/motion_input/QUEST_CONTROLLER_TRANSPORT_HOST.md) |
| Check and operate physical hardware | [Real robot](docs/operation/REAL_ROBOT.md), [teleoperation](docs/operation/TELEOPERATION.md), [safety](docs/safety/REAL_HARDWARE_SAFETY.md) |
| Collect and review episodes | [Collection](docs/data/DATA_COLLECTION.md), [datasets](docs/data/DATASET.md) |
| Train | [ACT](docs/training/ACT.md), [π0.5](docs/training/PI05.md) |

The maintained simulation asset uses JAKA/RH56 geometry. The user confirmed a physical Mini2/MiniCab with App 1.7.2.25 and controller 1.7.2_49; DH tool geometry and effective Servo/TIO firmware remain unverified.
The current Thor installation has a DH parallel gripper connected through the JAKA tool TIO, and no RH56.
The user reports the DH nameplate as PGE-50-26-O-S-M1; specifications, wiring, power, TCP and payload still need verification before physical operation; do not reuse the RH56 USB/CH341 settings.
Both D435 cameras completed simultaneous RGB and RGB-D checks; their roles are recorded in the deployment evidence.
JAKA completed a 5-second read-only check after LAN2 configuration, with no API errors and no power-on or enable action.
Eight computed SDK/MJCF flange poses agree; this does not validate the physical DH TCP or payload.
Real Quest HTS/CTRL traffic was received, but controller tracking/connection flags remained false and no RTOUCH payload arrived.
Touch pose acceptance remains incomplete.

Keep local machine settings in ignored `configs/local/`, and generated data and logs outside tracked source.
See [third-party notices](THIRD_PARTY_NOTICES.md) for bundled sources and assets.
