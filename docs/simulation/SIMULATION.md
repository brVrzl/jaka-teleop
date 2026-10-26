# Simulation

## English

Run the headless smoke without devices:

```bash
.venv/bin/embodied-lab sim smoke
./scripts/run_quest_jaka_sim_demo.sh --help
```

The maintained model is `assets/jaka_rh56_visual_coacd.xml`. Quest simulation
uses the same accepted-target boundary as the physical adapter, but it does
not imply physical calibration or sim-to-real equivalence. The interactive
viewer is `tools/debug_mujoco_jaka_rh56_viewer.py`; it is an offline viewer,
not a hardware controller.

## 中文

无设备运行 headless smoke：

```bash
.venv/bin/embodied-lab sim smoke
./scripts/run_quest_jaka_sim_demo.sh --help
```

当前维护的模型是 `assets/jaka_rh56_visual_coacd.xml`。Quest 仿真与物理适配器共用 accepted-target boundary，
但不代表真机标定或 sim-to-real 等价。交互 viewer 是 `tools/debug_mujoco_jaka_rh56_viewer.py`；它是离线
viewer，不是硬件 controller。

## Thor display selection / Thor 显示模式

默认使用已有的 `~/.venvs/embodied-hand-lab/bin/python`（可用 `--python` 覆盖）。
`monitor` 通过 `loginctl` 查找 seat0 活跃实体桌面，检查 X11 授权及启用的
显示输出；不会把 SSH 转发的 DISPLAY 当作实体桌面。支持 X11 或已有的
XWayland DISPLAY，不会启动新桌面或 Xvfb。需要 `loginctl`、`xwininfo`、`xrandr`。

```bash
# 首次只读环境检查
loginctl list-sessions
ls /sys/class/drm
nvidia-smi
./scripts/run_quest_jaka_sim_demo.sh --help

# 旧 RH56 live；默认 Thor 实体显示器，左 Index 控制 arm、左 Grip 控制 hand
./scripts/run_quest_jaka_sim_demo.sh --duration-sec 180 \
  --report /tmp/rh56-live.json --output /tmp/rh56-live.raw.jsonl

# 无交互窗口；离屏渲染使用 EGL（不会启动 viewer）
./scripts/run_quest_jaka_sim_demo.sh --display-mode headless --duration-sec 30 \
  --report /tmp/rh56-headless.json --output /tmp/rh56-headless.raw.jsonl

# 显式 SSH X11 转发；先在客户端使用 ssh -X/-Y 登录
./scripts/run_quest_jaka_sim_demo.sh --display-mode forward

# 历史 RH56 replay（离线证据，不是实际设备验收）
./scripts/run_quest_jaka_sim_demo.sh --display-mode headless \
  --recording /path/to/recording.raw.jsonl --report /tmp/rh56-replay.json
```

SSH 用户与桌面用户不同且授权失败时，可由桌面用户通过终端仅授权指定本机用户：
`DISPLAY=<实体桌面> XAUTHORITY=<桌面授权文件> xhost +SI:localuser:user01`。
撤销使用 `xhost -SI:localuser:user01`，桌面重启后需重新核验。
不要使用全局 `xhost +`，不要修改显示管理器或复制密码到脚本中。
启动脚本不修改桌面访问权限；也可显式传入已有的 `--xauthority PATH`。

`xrandr` 已启用输出、窗口 `IsViewable`/位置、真实根窗口截图或录屏需要交叉验证。
这些证据表明窗口位于实体输出的桌面上，不能单独证明显示器面板实际发光或操作者看到画面。
真实输入验收还需要有效 HTS/Head/CTRL、Clutch 转换、AcceptedArmTarget、实际
arm/hand 关节反馈与 viewer 更新统计；合成测试和 replay 不能替代。

Live 与 replay 的 `.events.jsonl` 按控制 tick 持续写入，包含实际仿真关节和命令；
内存诊断仍只保留最近 128 tick，因此报告中的部分延迟统计是末段窗口，不是全程统计。
请为每次运行指定新的输出文件名，保留原始 raw JSONL。

## XRobo native + DH proxy

原生字段和真实采集限制见[XRobo输入契约](../motion_input/XROBO_NATIVE.md)。

这是**simulation-only experimental** 输入，不授予真机控制权，tracking与源连续性仍未验证。
输入为 PC Service native SDK 的 JSON 回调记录，不是 UDP9000/RTOUCH。
使用已有脚本选择 `--profile dh-proxy --input-mode xrobo-native-experimental`；
提供 `--recording` 为回放；否则需 `--xrobo-sdk` 接收本机PC Service真实回调。右 Grip 是唯一共同 Clutch，
右 Trigger 越深越闭合；B 停止。释放、断流和重新接管保持上次安全意图，
重新捕获 Trigger 参考而不追赶间断期间的变化。XRobo 不自动重锚，必须释放再按。

```bash
# 原生输入-only；只接收 SDK 回调，另需已启动的 PC Service
PYTHONPATH=src ~/.venvs/embodied-hand-lab/bin/python tools/xrobo_input_observer.py \
  --sdk /absolute/path/to/libPXREARobotSDK.so \
  --log /tmp/xrobo-new.raw.jsonl --duration 60

# XRobo live（PC Service须先启动，Quest开启Head/Controller/Send，关闭Hand）
./scripts/run_quest_jaka_sim_demo.sh --profile dh-proxy \
  --input-mode xrobo-native-experimental \
  --xrobo-sdk "$HOME/.cache/embodied-hand-lab-xrobo/unpacked/opt/apps/roboticsservice/SDK/arm64/libPXREARobotSDK.so" \
  --duration-sec 180 --log-dir outputs/xrobo-live-demo

# DH + JAKA 原生记录实验回放；默认 Thor 实体显示器
./scripts/run_quest_jaka_sim_demo.sh --profile dh-proxy \
  --input-mode xrobo-native-experimental --recording /path/to/native/raw.jsonl \
  --log-dir outputs/xrobo-replay

# 无窗口回放；--duration-sec 可限制回放前段
./scripts/run_quest_jaka_sim_demo.sh --profile dh-proxy \
  --input-mode xrobo-native-experimental --recording /path/to/native/raw.jsonl \
  --display-mode headless --duration-sec 30 --log-dir outputs/xrobo-headless

# 备用、具有明确源有效性协议的 RTOUCH（仍不代表已通过实机发送端验收）
./scripts/run_quest_jaka_sim_demo.sh --profile dh-proxy --input-mode right-touch-v1 \
  --duration-sec 60 --log-dir outputs/rtouch-sim
```

`--display-mode forward` 仍须显式 SSH X11；所有这些入口均不连接物理执行器。
`--log-dir` 新建带时间戳文件，原始回放记录不被改写。
DH [模型尺寸、惯量与安装假设](../../assets/README.md#dh-pge-50-26-simulation-proxy)
与现场工具不是等价关系。画面显示 DH PROXY、命令闭合比例与实际模拟反馈。
事件的 `parallel_gripper_command` 和 `parallel_gripper_observation` 分开记录；
没有新命令时 command 可为 null，不能据此称设备已机械停止。
部分控制事件为精简记录，不含逐关节 arm `qpos`；实际关节统计须使用带测量的事件。
报告的 `input_frame_count` 是有界历史统计，完整 callback 数请看 `local_callback_count`。

XRobo 的 `controller_connected/tracked`、源 session/sequence 和共同参考空间均为
unknown/unverified；通过数值检查只允许该离线实验。`input_evidence` 保留未知字段，
界面的 preview usability 不是 tracking 证明。重启后全零输入，即使 Head status=3
且回调仍达90 Hz，也不会接管。收到时间倒退、重复、断流或 B 时要求重新明确接管。
真实 XRobo live 还需恢复手柄连接、验证共同坐标空间，并补实际有效性与连续性证据；
在此之前只运行 input-only 和离线仿真，不使用缓存位置伪造新鲜反馈。

### XRobo live接收及证据

PC Service启动命令见[Mac/Thor交接](../setup/MAC_QUEST_HANDOFF.md)。SDK固定连接
本机127.0.0.1:60061；接收器把localhost加入进程的`no_grpc_proxy`，避免SSH环境的
HTTP代理吞掉本机回调流，不修改系统代理或私有账户权限。Quest与PC Service使用
TCP63901，而非UDP9000；日志中的旧UDP参数只适用于HTS/RTOUCH。

`motion_input.xrobo_native.XRoboNativeReceiver`由input-only与live共用，保留SDK原始
JSON、原始callback monotonic ns/秒、host wall time、SDK事件及本地计数。
本地计数不是source seq；native记录可直接交给同入口replay。每个live控制tick写入
`actual_joint_position_rad`和`parallel_gripper_qpos_m`，命令与测量分开。
DH代理实际指间距为`0.0262 + q_left + q_right`米。日志用新文件，拒绝覆盖已有raw/events。

回调队列有界，溢出中止并记录错误；排队超过150 ms的旧输入不会进入控制链。
停流、SDK断开、源时钟异常、B或无效数值触发HOLD；恢复须先明确释放再按Grip，
即使中断不足300 ms也不自动重锚。原版visual可能冻结旧pose，这不能被数值检查可靠发现，
故不宣称tracking-loss安全验收。MuJoCo实验许可仍由会话边界拒绝传入硬件输出。

若仿真错误退出，保留原始输入、全量events及报告中的`runtime_error`，该轮不得算通过。
viewer更新率、accepted目标及暂停行为需结合完整events，不能把有界诊断尾段当全程统计。
