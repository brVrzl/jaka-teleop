# Quest 右 Touch：输入、发送端与离线遥操作

[旧 CTRL/HTS 路径](QUEST_CONTROLLER_TRANSPORT_HOST.md)仍保持原语义：左手 index 接管机械臂，左 grip 接管 RH56，右手 HTS 骨骼提供姿态。**它不是右 Touch 位姿协议。** 新模式 `right-touch-v1` 只使用右控制器与真实头部位姿，不需要手部骨骼。

## 验证边界与现用发送端候选

已找到公开候选源码 [`brVrzl/hand-tracking-streamer`](https://github.com/brVrzl/hand-tracking-streamer/tree/5b8eac7e30ce12481b89b123099693bc658bc578)：`feature/mixed-input-log-probe` 分支包含 `LeftControllerPacketSender.cs`、`LeftControllerPacket.cs`、现有菜单和 `CommandLineAndroidBuild.cs`；其 CTRL v1 编码与现场收到的格式匹配。该 commit 的项目版本为 Unity **6000.0.65f1**，应用配置为 **1.1.0 / versionCode 7**、包名 `com.brvrzl.handtrackingstreamer.mixedprobe`。这些是**源码配置值，尚不是现场已装 APK 的已验证身份**。该仓库 main 的捆绑 APK 与此分支不是同一构建交付物，GitHub Releases 为空。

现场已收到旧 CTRL + HTS wrist/landmarks/head。20 秒记录的 501 条 CTRL 全部 `connected=0,active=0,tracked=0,index=0,grip=0`，没有 RTOUCH；只能证明旧 UDP 传输到达，未证明控制器追踪或按键可用。原始证据在本机 `outputs/thor-onboarding/quest-input-second-raw.jsonl`（不进 Git）。

主机 parser、时序／跟踪失效、Grip 接管／重新捕获和共用 MuJoCo target 管线已做离线测试及合成输入 replay。发送端采用对上述固定 commit 的[最小扩展补丁与构建步骤](../../quest_sender/README.md)，复用已有 Unity 工程、Meta SDK、IP/端口数字键盘、保存配置和启停菜单，**没有另造一套应用**。Mac 已通过 21 项 EditMode 测试并完成 Android build、独立包普通安装；**HTS IP 输入仍阻塞真实 RTOUCH 流；操作者现优先选择 XRobo 原生只读验收，其缺失字段不得直接包装为 RTOUCH**，见[当前接力记录](../setup/MAC_QUEST_HANDOFF.md)。

DH 工具身份、TCP、负载、碰撞几何及可确认时效的夹爪反馈未完成实物核验，`tools/quest_jaka_hardware.py` 会在任何硬件 I/O 前拒绝 `right-touch-v1`。手写 `verified` 布尔不能绕过这个边界。仿真使用所选 YAML 的模型；默认 RH56 模型不代表 DH 适配通过。右 Touch 不允许写入旧 RH56 的 12-D episode。

## 获取、构建、安装与填写主机地址

在具备 Unity 6000.0.65f1、Android Build Support/SDK/NDK/OpenJDK 并完成 Editor 授权的构建电脑上，按 [quest_sender/README.md](../../quest_sender/README.md) clone 固定源码、应用 `right-touch-v1.patch`、运行 EditMode 测试和已有 `CommandLineAndroidBuild.BuildApk`。不复用旧用户 Library 缓存，不安装 main 的旧 APK冒充新发送端。

先在 Quest 启用开发者模式，USB 接到有 Android Platform Tools 的电脑，并在头显内确认 USB 调试授权。先检查原应用身份：

```bash
adb devices -l
adb shell pm list packages -3
# 先查看候选包是否存在；若不存在，以列表里的实际包名核对。
adb shell dumpsys package com.brvrzl.handtrackingstreamer.mixedprobe
adb shell pm path com.brvrzl.handtrackingstreamer.mixedprobe
```

记录现场 `versionName`、`versionCode`、包名、安装来源，再与源码配置比对。`unauthorized` 需要头显内授权；列表为空先检查开发者模式、数据线及 USB 权限。旧包及本轮新包身份已通过 ADB 核实，详见[当前接力记录](../setup/MAC_QUEST_HANDOFF.md)。

补丁构建使用独立包名 `com.brvrzl.handtrackingstreamer.righttouch`，版本 `1.1.0-righttouch-v1`，保留原应用：

```bash
adb install -r /absolute/path/to/hand_tracking_streamer/build/right_touch_v1.apk
adb shell monkey -p com.brvrzl.handtrackingstreamer.righttouch -c android.intent.category.LAUNCHER 1
adb shell dumpsys package com.brvrzl.handtrackingstreamer.righttouch
adb logcat -s Unity
```

在已有头显菜单中：

1. Protocol 选 **UDP**，将 IP 输入框填为 Thor 在 Quest 网络中可达的 IPv4（不是机器人 IP，也不是广播地址），Port 填主机接收端口，例如 `9000`。
2. Hand mode 新选项选 **Right Touch (RTOUCH v1)**。该模式不要求手骨骼、HTS head toggle 或左控制器；内部发送真实头部 pose 用于参考捕获，同时停用 HTS hand/head 流。
3. 首次输入测试关闭不必要的 host→Quest video，点击已有 **Start Streaming**。IP、端口和模式复用原应用的保存逻辑。
4. 观察右侧 HUD/`adb logcat` 的 RTOUCH TX、右手／头部 tracking、Grip/Trigger。**TX 计数不证明主机收到**；还要核对主机 `valid_pose_packets`。
5. 右 **B** 停止并返回菜单；原左 Menu 仍能停止。改地址时先停止、填写后重新开始。网络重连、焦点变化或 tracking origin 变化都会更换 session，主机要求重新释放 Grip。

菜单扩展已构建并安装，实际头显交互与真实输入仍待现场验收。没有控制器射线时先使用原工程已有菜单交互完成配置；不要修改 tracking 有效性来绕过问题。UDP 无 ACK，连接验证以主机接收为准；故障检查同网、路由、防火墙和 AP 客户端隔离。

## 先只看真实输入

激活新用户自己的 venv，在仓库根目录运行（不需要 MuJoCo 或硬件 SDK）：

```bash
python tools/quest_controller_transport_gate.py --input-mode right-touch-v1 \
  --bind 0.0.0.0 --port 9000 --project-ip "$HOST_IPV4" \
  --allowed-sender "$QUEST_IPV4" --duration-sec 30 --required-data-timeout-sec 20
```

输出包含 canonical `position_m`、`orientation_xyzw`、`grip`、`trigger`、`gripper_engaged`、`gripper_release_required`、session/sequence、掉包、重排和 stale。原始 UDP 和报告保存在 `logs/quest_transport_gate/`。在限定时间内没有有效右控制器和头部姿态时返回失败，不要求 RH56、HTS 或骨骼。

输入预览不报告机械臂接管状态；`gripper_engaged` 仅表示 Trigger 电爪意图通道。该通道仍在失效后要求 Grip 释放再按下，不会因机械臂自动恢复而改变夹爪目标。机械臂状态以 session 的 `arm_clutch_state` 为准。

机械臂检查：启动时先释放 Grip 再按下；同一 RTOUCH 连续性代次内短断流先 HOLD，在最后有效样本后的两倍 clutch stale 时间内（当前 300 ms），可信新帧仍明确按住 Grip 且机械臂状态安全时自动重新锚定。恢复首帧相对运动为零，不追赶丢失期间的手柄运动。真机还要求 native STOPPED_READY、新鲜 observation/worker 时间及无错误，不绕过 braking/watchdog。长断流、显式追踪无效、未知按键、源时钟异常、session/recenter、报警或硬停止不能自动恢复。详见[架构](../architecture/SYSTEM_ARCHITECTURE.md)。头部朝向仍只在参考捕获时用于水平参考。

## 仿真和操作映射

先在上一节确认输入，再运行已有仿真入口：

```bash
python tools/quest_jaka_mujoco_sim.py live-6dof --input-mode right-touch-v1 \
  --project-ip "$HOST_IPV4" --allowed-sender "$QUEST_IPV4" \
  --duration-sec 30 --no-viewer
```

需要图形预览时使用 `--viewer` 并确保当前用户图形会话可用。原始记录可离线复走：

```bash
python tools/quest_jaka_mujoco_sim.py replay-6dof PATH_TO_RAW.hts.jsonl \
  --input-mode right-touch-v1 --report logs/right_touch_replay.json
```

- **右 Grip**：`>=0.75` 接管，`<=0.55` 暂停；首次、重连、tracking 失效后必须观察释放再按下。重新按下捕获当前控制器与权威机械臂状态，复用原 SE(3) 映射、滤波、continuation IK、可行性检查及 `AcceptedArmTarget`，没有另建 JAKA 运动链路。
- **右 Trigger**：方向为 `0=开、1=闭` 的闭合比例；5%/95% 端点死区；与 Grip 接管时的 Trigger 值做相对变化；目标变化最大 `1.0/s`。只在 Grip 接管期间更新。每次重新接管不会把当前 Trigger 绝对值立即写给电爪。
- **夹爪初始化**：主机 input 层没有初始化或写设备行为。`RightTouchInput.seed_gripper_from_measured()` 必须先由已验证的新鲜反馈明确设置；未设置时 `gripper_target_normalized=null`。该字段是命令意图，不是反馈，也不是已执行动作。DH SDK 缓存读数的时效未被验证时不得用来自动播种。
- **暂停／断流／退出**：Grip 松开暂停机械臂并保持夹爪意图；丢追踪、session 改变、重排、旧 session 不会自动松爪。Ctrl-C 停止主机输入／仿真。现场急停依真实机械臂流程；发送端退出不能被当作替代急停。

## RTOUCH v1 线协议

每 UDP datagram 一行、严格 UTF-8、最多 2048 bytes、固定字段顺序，无额外字段；可有一个末尾 LF：

```text
RTOUCH,v=1,session=1,seq=1,t_ns=20000000,connected=1,active=1,tracked=1,head_tracked=1,index=0,grip=0,px=0,py=0,pz=0,qx=0,qy=0,qz=0,qw=1,hpx=0,hpy=1.6,hpz=0,hqx=0,hqy=0,hqz=0,hqw=1
```

| 字段 | 定义 |
| --- | --- |
| `v` | 协议版本，固定 1；不改变 CTRL v1 |
| `session` | 随机 uint64；应用启动、失去／恢复焦点、tracking origin 改变时更新 |
| `seq` | session 内递增 uint64；重复／倒序包不替换有效样本也不刷新时效 |
| `t_ns` | 发送端 monotonic 纳秒；只比较同一 session 内顺序，不与主机时间相减 |
| `connected/active/tracked` | 右控制器连接、应用焦点且按键有效、位置与旋转均 tracked，均为 0/1 |
| `head_tracked` | 同 tracking origin 的真实头部位置和旋转均有效 |
| `index/grip` | 右 Trigger／Grip analog，有限数 `[0,1]` |
| `p*/q*` | Unity 右控制器 **grip pose**，米与单位 quaternion **xyzw** |
| `hp*/hq*` | 同一空间的真实头部 pose，用于现有 head-yaw reference；不是合成骨骼 |

Unity 为左手系：+X 右、+Y 上、+Z 前。主机只做一次基变换：`(x,y,z) → (x,y,-z)`，`(qx,qy,qz,qw) → (-qx,-qy,qz,qw)`，得到原系统的 OpenXR 风格右手系（前方 -Z）。其后沿既有 YAML 的 operator→robot basis；不要在发送端再翻转 Z。无效 quaternion/NaN/Inf/错误版本/字段乱序直接拒绝。

主机 freshness 只用收到 UDP 时的本地 monotonic 时间，默认 150 ms；原机械臂 watchdog、限位与清理逻辑保留。来源时钟不前进、显著暂停或接收空档要求重新释放接管。长断流不会把缓冲中的旧位姿变成新目标。
