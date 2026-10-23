# 首次安装与 Thor 部署

[首页](../../README.md) · [配置](../configuration/CONFIGURATION.md) · [English](#english)

先完成离线安装，再检查网络与设备，最后按真机流程启用动作。安装 Python 包、构建 native worker、
`--help` 和 `doctor` 不会连接或初始化执行器；下载依赖需要网络。

## 1. 检查系统前置条件

需要 Git、Python 3.10+ 及 `venv`。JAKA native 组件需要 Linux、C++17 编译器和 CMake 3.20+。
GPU 不是 headless smoke 的必需条件；交互 viewer 和 EGL 渲染需要系统提供可用的 OpenGL/EGL。

```bash
uname -m
cat /etc/os-release
python3 --version
git --version
cmake --version
c++ --version
id
ip -brief address
ip route
```

在 Thor 上另检查 `cat /etc/nv_tegra_release` 和 `nvidia-smi`。本轮首次部署已在
Ubuntu 24.04、aarch64、L4T 39.2、Python 3.12、CMake 3.28 和 GCC 13 的新用户环境中运行。
NVIDIA 驱动、内核、EGL 和网络属于系统前置条件；不要复制旧用户的虚拟环境或为了安装项目重装这些组件。
`nvidia-smi` 的 CUDA 版本字段也不表示 CUDA 编译工具链已经安装。

若基础工具缺失，由管理员通过本机的软件源安装，例如 Ubuntu 上的 `git python3-venv build-essential cmake`。
仅在实际需要时安装缺少的包；无 sudo 权限不妨碍使用已安装的系统工具创建个人环境。

## 2. Clone 并创建自己的环境

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/brVrzl/embodied-hand-lab.git
cd embodied-hand-lab
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[simulation]'
```

若目录已存在，先执行 `git status --short --branch` 和 `git remote -v`，确认身份和未提交修改；不要覆盖旧 checkout。
本教程在仓库根目录执行命令，使用 `.venv/bin/python`，不依赖 shell alias 或旧用户绝对路径。
也可把环境建在自己的 `~/.venvs/embodied-hand-lab`；将示例中的 `.venv/bin/` 替换成该路径。
脚本提供 `--python` 时显式指定解释器，例如：

```bash
./scripts/run_quest_jaka_sim_demo.sh --help
# 使用仓库外环境时，在实际运行参数中加入：
# --python "$HOME/.venvs/embodied-hand-lab/bin/python"
```

### 按角色安装

| 角色 | 在仓库根目录执行 | 额外系统/设备条件 |
| --- | --- | --- |
| CLI、配置与数据结构检查 | `.venv/bin/python -m pip install -e .` | 无设备 |
| 离线仿真、Quest 仿真 | `.venv/bin/python -m pip install -e '.[simulation]'` | viewer 另需图形会话 |
| 遥操作及双相机采集 | `.venv/bin/python -m pip install -e '.[simulation,hardware,realsense,dataset-collection]'` | JAKA SDK、相机权限、现场确认 |
| 开发与完整测试依赖 | `.venv/bin/python -m pip install -e '.[dev]'` | 可能下载较多科学计算包 |
| 数据集导出 | `.venv/bin/python -m pip install -e '.[dataset-export]'` | 按[数据集文档](../data/DATASET.md)操作 |
| 资产处理 | `.venv/bin/python -m pip install -e '.[asset-tools]'` | 与遥操作分开安装 |

`hardware` 目前包含 RH56 等串口依赖；安装它不会打开串口，也不表示 DH 应通过 USB 串口连接。
`realsense` 安装 Python SDK，不自动安装系统 udev 规则。训练依赖走 [ACT](../training/ACT.md) 或
[π0.5](../training/PI05.md) 的独立步骤，只有需要训练源码时才执行：

```bash
git submodule update --init --recursive
scripts/check_training_dependencies.sh --help
```

## 3. 先完成离线检查

```bash
.venv/bin/embodied-lab --help
.venv/bin/embodied-lab doctor
.venv/bin/embodied-lab sim smoke
mkdir -p outputs/onboarding
.venv/bin/embodied-lab doctor --output outputs/onboarding/doctor.json
```

验收点：CLI 能打印帮助；doctor 报告区分必需与可选能力；smoke 输出 `status: passed` 和
`hardware_connections_attempted: false`。doctor 不探测网络中的控制柜，也不打开相机、串口或 Quest socket。
smoke 使用现有 RH56 仿真模型，因此不证明当前 DH 安装的 TCP、负载或碰撞几何正确。
已有录制输入的 replay 用法见[仿真](../simulation/SIMULATION.md)，不要把随机生成的输入称为现场录制。

如需运行测试：

```bash
.venv/bin/python -m pip install -e '.[dev,dataset-collection]'
.venv/bin/python -m pytest -q
```

测试所需科学计算包由 `dev` 提供，数据采集测试另需 `dataset-collection`。缺少可选训练包不应通过连接真机来“修复”。

## 4. 构建 JAKA native 组件

仓库已包含 JAKA SDK 2.2.7 的头文件及 Linux aarch64/x86_64 动态库，见
[`third_party/jaka_sdk`](../../third_party/jaka_sdk)。无需寻找旧用户目录中的 SDK。
SDK 版本不是控制柜固件版本；二者的兼容性须按实际控制柜与厂商说明核对。

```bash
cmake -S native/jaka_servo_worker -B build/jaka_servo_worker
cmake --build build/jaka_servo_worker -j2
cmake -S native/jaka_readonly_diagnostic -B build/jaka_readonly_diagnostic
cmake --build build/jaka_readonly_diagnostic -j2
ldd build/jaka_servo_worker/jaka_servo_worker
ldd build/jaka_readonly_diagnostic/jaka_readonly_diagnostic
build/jaka_readonly_diagnostic/jaka_readonly_diagnostic --help
build/jaka_readonly_diagnostic/jaka_readonly_diagnostic \
  --mode dry-run --robot-ip 192.0.2.1
```

`ldd` 不应出现 `not found`，`libjakaAPI.so` 应来自当前 checkout 对应架构的 SDK。
`192.0.2.1` 是仅用于 dry-run 的文档地址，不是现场控制柜 IP。dry-run 不构造 SDK client。
不要为了检查安装运行会使能机器人或进入 servo 模式的程序；实际只读连接见[真机操作](../operation/REAL_ROBOT.md)。

## 5. 建立本机配置和设备清单

按[配置文档](../configuration/CONFIGURATION.md)从示例建立忽略的本机 YAML：

```bash
mkdir -p configs/local
cp configs/data_collection/thor.example.yaml configs/local/thor.yaml
# 先编辑为本机实际值；示例中的缺项不能直接用于运动
.venv/bin/embodied-lab doctor --runtime-config configs/local/thor.yaml
```

本机配置至少要核对：机器人 IP 与回传 IP、机器人专用网卡、Quest 主机地址与允许来源、末端类型、
两台 D435 的 SDK 序列号与角色、数据及日志目录、CPU 亲和性、任务名称和操作者。

按以下顺序检查，单个设备受阻时继续其他项：

1. **网络**：先记录 `ip route`、`ip -brief address` 和 `SSH_CONNECTION`，区分管理接口与机器人接口。
   已有正确路由时无需运行配置脚本；不要清空接口地址。使用 `setup_jaka_lan2_route.sh` 前阅读其 `--help`。
2. **JAKA**：先用只读诊断器；收集实际机型、控制柜/固件/SDK/TIO 版本、状态、关节、TCP、工具/用户坐标系及告警。
   `Mini2` 配置文件名不能代替机型与运动学比对。换装 DH 后需重新核对 TCP、负载和末端碰撞几何。
3. **Quest**：确认安装包名称与版本、发送端源码及构建来源，先跑[仅输入 gate](../motion_input/QUEST_CONTROLLER_TRANSPORT_HOST.md)。
   仓库没有可直接安装的 Quest APK，不能假定已有应用包含右手 Touch 位姿。保留抓包/日志核对协议，再做仿真。
4. **DH**：当前优先链路为 `Thor → 网络 → JAKA SDK → 末端 TIO → 电爪`。
   铭牌型号、供电、针脚、串口电平/协议及固件必须按实物和对应厂商资料确认；不复用 RH56 的 CH341 配置。
   示教器设置须对应已确认的控制器版本，不照抄未经核实的菜单。
5. **双 D435**：用 RealSense SDK 枚举序列号，不把 Linux USB 标识当成 SDK serial。
   分别遮挡/观察画面确认 `workspace` 与 `wrist`，再同时读取两台 RGB 和 depth，并检查时间戳、丢帧及正常释放。
   所有相机由同一操作者调度，避免 viewer 与采集进程争用。

相机诊断入口为 `tools/check_realsense_stream.py --help`；只有明确执行相机检查命令才打开设备。
若 SDK 报权限错误，按所用 librealsense 版本安装厂商 udev 规则并重新连接设备；不要把整个 `/dev` 改为全员可写。

最后进入[遥操作](../operation/TELEOPERATION.md)与[采集](../data/DATA_COLLECTION.md)，先仿真与短时检查，
再在现场安全条件满足时执行受限真机动作。数据先进入 staging，经人工审核后再转为训练数据。

### 可选：Quest 的 ADB 检查

ADB 用于确认安装应用/版本、读取日志和安装已明确来源的 APK，不是接收 Quest UDP 的必要依赖。
Ubuntu 上优先由管理员安装系统 `adb` 包；随后运行 `adb version` 与 `adb devices -l`。
头显需连接数据 USB、开启相应开发者功能，并在头显内确认该主机的调试授权；设备列表为空不等于 UDP 应用没有运行。

本轮无免密 sudo，因此把 Ubuntu 的 adb 及配套运行库解包到个人目录
`~/.local/opt/embodied-lab-adb`，通过进程局部的库路径运行，已验证版本 34.0.4；没有改系统库或其他用户环境。
这只是本机的可选安装方式，具体路径及当前设备访问结果见[部署记录](DEVICE_STATUS.md)。
不要把未经确认的 TCP 5555 连接当成设备已经授权，也不要为了 ADB 操作改变机器人专用网络。

若插线后 `adb devices` 为空，先执行 `lsusb` 并检查 **Thor 端口角色**。
本轮接线时 Thor 的 `/sys/class/usb_role/*/role` 显示 `device`，UDC 状态为 `configured`，
`usb0`/`l4tbr0` 上线但 `lsusb` 没有 Quest：这是 Thor 自身设备模式端口被连接，不能据此枚举头显作为 USB 设备。
应把 Quest 数据线改接 Thor 的 **USB host 口**，例如目前两台 D435 所在 USB hub 的空闲口，
再查 `lsusb`、`adb devices -l` 和头显调试授权提示。只换空闲口，不拔正在采集的相机，也不禁用系统 USB gadget 服务。
`unauthorized` 表示需要头显确认主机；完全没有 USB 枚举则继续检查 host 口、数据线和连接，不能只重试 ADB。


## English

Start with Git, Python 3.10+ and `venv`. Linux JAKA native builds require CMake 3.20+ and a C++17 compiler.
Use a new per-user environment; existing NVIDIA drivers, kernel, EGL and networking are system prerequisites, not files to copy from another user.
The Thor onboarding checks have run on Ubuntu 24.04/aarch64, L4T 39.2, Python 3.12, CMake 3.28 and GCC 13.

```bash
git clone https://github.com/brVrzl/embodied-hand-lab.git
cd embodied-hand-lab
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[simulation]'
.venv/bin/embodied-lab --help
.venv/bin/embodied-lab doctor
.venv/bin/embodied-lab sim smoke
```

For teleoperation and collection, add `simulation,hardware,realsense,dataset-collection` extras.
Use `dev` for development, `dataset-export` for conversion and `asset-tools` for asset processing.
Training has separate [ACT](../training/ACT.md) and [π0.5](../training/PI05.md) setup paths; do not initialize training submodules for ordinary teleoperation.

The two CMake builds in step 4 use the bundled SDK 2.2.7 and select the host architecture.
Check both with `ldd`; no dependency should be missing. Native diagnostic `--help` and `--mode dry-run` are offline.
Package installation downloads dependencies but never initializes an actuator.

Use [machine configuration](../configuration/CONFIGURATION.md) before device access.
Preserve the management/SSH route. Verify the real robot model, firmware, TIO, TCP, payload and collision geometry before motion.
The repository has no installable Quest APK: establish the sender source, app version and actual payload using the
[input-only gate](../motion_input/QUEST_CONTROLLER_TRANSPORT_HOST.md) before simulation.
The DH gripper is connected to the JAKA tool TIO, not a Thor USB serial port.
Assign both D435 roles using SDK serials and actual images, then check simultaneous RGB-D capture.
Continue with [physical operation](../operation/REAL_ROBOT.md), [teleoperation](../operation/TELEOPERATION.md) and
[review-first collection](../data/DATA_COLLECTION.md) only after their prerequisites are met.
