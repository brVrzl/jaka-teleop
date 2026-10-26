# Mac / Quest 右 Touch 交接

## 当前接力：阶段二发送端（2026-10-26）

**本轮最新取舍：操作者已明确接受“成熟应用原生协议只读验收”，缺失字段如实列出，
不要求把本轮原生流算作完整 RTOUCH 通过。现优先使用已装 XRoboToolkit-Quest，暂停扩展 HTS UI。
下文 RTOUCH 构建/接入步骤保留为候选后续流程，不代表该协议已实机通过。**

旧 HTS/CTRL → JAKA/RH56 实体显示器仿真已经由操作者确认通过，见
[实际证据](DEVICE_STATUS.md#rh56-实体显示器仿真验收2026-10-26)。
集成分支为 `work/jaka-teleop-sim-integration`。文档入口优化、Thor onboarding、
recovery 和 test-prune 已全部包含，无需重复合并；不合并独立研究分支。

**Mac Codex 负责 Quest USB/ADB、发送端构建和真实输入；Thor Codex 负责 host
控制会话、MuJoCo 和 DH 仿真。不要同时修改 host 的 RightTouchInput/Clutch/IK。**
本任务不授权 JAKA 或 DH 实物动作，不升级 Quest 固件，不卸载已有应用或清除应用数据。

可直接交给 Mac Codex 的工作顺序：

1. 检查现有工作区/未提交修改，fetch 集成分支；有其他任务改动时用独立 worktree。
   保留旧分支，不 reset、不 force push。以本节为当前任务，后文 10-23 状态仅作历史证据。
2. 用已有 `~/Library/Android/sdk/platform-tools/adb` 检查 `devices -l`、前台包名、
   已装 HTS/XRobo/Trossen 包版本及日志，确认旧应用是否真的包含 Right Touch 模式。
   不凭相同版本号推定 APK 来源。用终端/现有投屏能力操作，不要求 Thor 鼠标键盘。
3. 盘点 Unity Hub、Unity 6000.0.65f1、Android Build Support/SDK/NDK/OpenJDK 和
   Editor 授权。复用现有环境；缺 Editor/许可时报告准确缺项，不擅自升级工程或伪造构建成功。
4. 优先按 [现有发送端说明](../../quest_sender/README.md) 在独立 checkout 应用
   `quest_sender/right-touch-v1.patch`，复用 pinned `5b8eac7` 的工程、菜单、UDP socket。
   Thor 已重新拉取该提交并通过 `git apply --check`，但没有 Unity 编译或 APK 验收。
   执行 EditMode 测试和 Android build，保留日志。若必须修补，修改该补丁并报告具体编译错误，
   不另建完整发送端框架，不更换坐标契约或削弱 validity。
5. 构建成功后核对独立包 `com.brvrzl.handtrackingstreamer.righttouch`，保留所有旧包，
   安装并打开 Right Touch 模式，目标 Thor `10.24.1.68:9000` UDP。首次开发者授权等
   系统确认若必须用户处理，请准确指出一次，不绕过平台权限。
6. 通知 Thor 启动已有 input-only 接收器，记录真实 RTOUCH：右控制器位置/旋转、
   Head、connected/active/tracked、Grip/Trigger、源 session/seq/t_ns。
   分别检查释放、按住、遮挡、后台/恢复、停流/重启和 recenter；session 不连续应可观测。
   不用主机序号冒充源序号，不从 Grip 或位姿变化推断 tracked。
7. 返回包名/版本、构建测试结果、发送端实际菜单、真实包样例、原始记录路径及未完成项。
   无法构建时明确卡在何处；XRobo 缺字段的流不能直接包装为有效 RTOUCH。

Thor 的只读接收入口（先确认 9000 未占用；为每次运行使用新的输出文件）：

```bash
cd /home/user01/projects/embodied-hand-lab
PYTHONPATH=src ~/.venvs/embodied-hand-lab/bin/python tools/quest_controller_transport_gate.py \
  --input-mode right-touch-v1 --project-ip 10.24.1.68 --port 9000 \
  --duration-sec 60 --required-data-timeout-sec 45 \
  --report /tmp/right-touch-input.json --raw-log /tmp/right-touch-input.raw.jsonl \
  --log /tmp/right-touch-input.log
```

有效真实发送端确认后再接入统一 Grip 会话及 DH 仿真；阶段二联合仿真通过前不进入阶段三。

### 最新补充：XRobo 右 Touch 已唤醒并完成重启恢复（2026-10-26）

本轮继续使用原版XRobo Quest v1.0.1，未继续修HTS、未修改Unity/Thor控制链。
右手柄系统id `3a04abe84951aa41`，配对连接仍在、初始为asleep/inactive；
操作者唤醒后系统为CONNECTED_ACTIVE / POSITION，收到真实位姿及按键变化。
无需重配对；不能据此回溯证明历史30,328全零帧的唯一原因。

新的`native-20261026-02`共31,142条SDK Tracking回调；独立动作窗口4,565帧：
Grip、Trigger均覆盖0–1，仅Grip612帧/仅Trigger289帧，Grip保持4.840秒，
B按下317帧并有按下/释放沿，三轴移动及旋转已记录。
关闭Send产生12.299秒空档，观察器stale时frame为空，重新开启后有真实输入。
ADB退出/重启PID22548→28566后，新进程5,498帧含实际变化的位姿及Grip/Trigger/B，
xyz全零帧0，本次没有重复历史全零现象。这个结果不等于自动重连和tracking安全门已通过。

头动时Head变化而Controller输出完全不变；源码表明两者均为Unity world，
但visual可冻结旧值，故尚不能认证静止控制器保持有效追踪或跨recenter的稳定连续性。
recenter有实际Unity事件日志，原版JSON仍无对应代次，也无右IsConnected/IsPoseValid、
严格tracking标志、源session/seq。已转换右手坐标，接收端不得再次翻Z。
**IsPoseValid虽真实可读取，但当前Meta provider未独立检查位置追踪质量，不能当作严格tracked。**
真正断开右手柄测试由操作者取消，没有取电池确认，标记未执行，不再追加手动操作。

完整字段契约、实测边界、源码来源与后续事项见
[XRobo原生输入记录](../motion_input/XROBO_NATIVE.md)。
Thor证据：`/home/thor/.cache/embodied-hand-lab-xrobo/native-20261026-02/`；
Mac副本：`/Users/wujunqi/Documents/Codex/2026-10-26/mac-brvrzl-jaka-teleop-quest-3-2/outputs/xrobo-minimal-20261026-02/`。
原始JSONL、状态、事件、统计、样例已复制并核对SHA256，未进Git；历史native-01及APK保留。
本轮无新APK/Unity build；原版同包更新存在Editor2021.3.45f2缺失及签名不同的前置限制。
本轮Quest应用、观察器和PC Service已停止，没有实物动作；Thor离线仿真无需等待后续补字段。

### 前轮执行结果：XRobo 原生基础输入已证实，当时重连待补（2026-10-26）

ADB Quest 3 `2G97C5ZJ2901FK` 已授权；Android 14 / API 34，Horizon 分支
`releases-oculus-14.0-v207`，属性显示名 `2.7.0`，SystemUX `207.0.0.191.1234`，
firmware `52433670032200520`。Quest `10.24.0.3/16` 实测可达 Thor `10.24.1.68`，
Thor Wi-Fi 地址已通过 SSH 核对。原 RH56/JAKA 仿真没有重复运行，未执行任何实物动作。

| 实装包 | versionName / code |
| --- | --- |
| `com.wengmister.handtrackingstreamer` | `1.1.0` / `7` |
| `com.brvrzl.handtrackingstreamer.mixedprobe` | `1.1.0` / `7` |
| `com.xrobotoolkit.client.quest` | `1.0.1` / `1` |
| `com.DefaultCompany.vr_controller` | `1.0` / `11` |
| `com.brvrzl.handtrackingstreamer.righttouch` | `1.1.0-righttouch-v1` / `7`，本轮普通安装后同包更新 |

旧 mixedprobe 实际菜单仅 Left/Right/Both Hand，没有 Right Touch；两个旧 HTS APK
均无 RTOUCH 编码标识。所有旧应用和数据保留。

#### 当前采用：XRoboToolkit-Quest 原生只读输入

复用既有 Quest v1.0.1 及 Thor PC Service v1.0.0 / native SDK，未升级应用或新造协议。
Quest 用右 Touch Trigger 操作菜单，连接 `10.24.1.68`，开启 Head、Controller、Send，Hand 关闭。
Thor 使用已有 `tools/xrobo_input_observer.py`；只调用 SDK 初始化、接收 JSON 回调和释放，
没有设备控制或机器人目标。一次采集保存 74,266 条 Tracking 回调，首末跨度 1,037.474 秒，
连续收到数据时约 90 Hz。它们是 **SDK 应用 JSON 回调，不是原始 TCP datagram**。

受控动作窗口 9,705 帧 / 107.884 秒：右 Grip、Trigger 均覆盖 0–1，
分别有 743 帧“只按 Grip”、475 帧“只按 Trigger”（另一输入 <0.1）；
B 键 true 235 帧、false 9,470 帧。位置三个分量和旋转均明显变化，
quaternion norm 范围 0.999999917–1.000000125。
Head pose 随操作者头部运动变化；关闭 Send 产生 10.204 秒实际回调空档，
观察器 stale 时 `current_frame=null`，恢复 Send 后重新收到新回调。

**失焦/重启恢复尚未通过右 Touch 验收。** 后台后重开时 Quest 进程从 9864 换为 17704，
重新启用 Send 后回调恢复约 90 Hz，但新进程阶段 30,328 帧右控制器位置/扳机全零。
操作者随后明确报告右手柄 `not connected`。因此不能把持续回调当作控制器仍有效，
也不能声称右 Touch 已成功自动重连。右手柄连接恢复后需再做这项短测试。

当前原生协议缺右控制器独立 `connected/active/tracked`、源 session/seq/recenter generation。
`timeStampNs` 是源 UTC，`predictTime` 是源应用 elapsed 微秒；重启时后者下降可见，
不能把本地回调序号或 SDK `TestDevice` 标签冒充源序号/session/设备序列号。
遮挡、recenter 已由操作者执行，但缺少这些标志，**尚不能认证对应 tracking/连续性安全语义**；
重复、过期、无效源数据拒绝及统一参考空间也尚未通过。Head 使用 root pose，Controller
使用 visual world transform；主机不得再次翻转上游已转换的 Z，也不能直接包装为有效 RTOUCH。

本次 Thor 原始回调、状态和事件：
`~/.cache/embodied-hand-lab-xrobo/native-20261026-01/` 下的
`raw.jsonl`、`status.log`、`events.jsonl`、`controls-motion-summary.json`、
`head-continuity-summary.json`、`final-summary.json`、`real-samples.json`。
Mac 已保存完整副本到本轮证据目录 `xrobo-native/`。采集器按 1,200 秒上限自然退出，
本轮 PC Service 已停止，Quest XRobo 已 force-stop，未清除数据。

#### 已保留的 RTOUCH 候选构建

独立 worktree 基线 `0a14ad3`，分支 `work/mac-quest-righttouch-20261026`；
固定发送端 `5b8eac7` 在独立 checkout 应用现有补丁，保留原工作区/旧 checkout。
本轮恢复 Unity Hub 3.22.4、Editor 6000.0.65f1 (`a18e2220bd50`)、Android Build Support、
NDK r27c 27.2.12479018、OpenJDK 17.0.9+9；SDK 含 API32/36、Build Tools36.0.0、
command-line tools16.0 和 CMake3.22.1。Editor 位于
`/Applications/Unity/Unity.app/Contents/MacOS/Unity`，未升级项目/包，未复用旧 Library。

操作者登录后 Unity Personal 授权正常。EditMode 两次 **21/21 通过，退出码0**；
首次无许可退出198、构建缺 CMake、Java 不接受 `HTTPS_PROXY=socks5h://...` 的完整日志均保留。
补齐 CMake 并为构建进程使用已有 HTTP 代理后，`android-build-03.log` 构建成功。
真机发现手部 UI 的 `FromOVRHandDataSource.UpdateDataPoses` 空引用：
项目编译定义为 `ISDK_OPENXR_HAND`，运行配置却被初次导入置为 OVR。
补丁仅新增5行构建配置，在 BuildApk 中明确设置并保存 `OVRHandSkeletonVersion.OpenXR`。
`editmode-03.xml` 再次21/21通过，`android-build-04.log` 构建成功，退出码0；
同包更新后日志确认 OpenXR，手部射线恢复，实际菜单已看到 Right Touch (RTOUCH v1)。

最终候选 `right_touch_v1.apk`：68,881,517 bytes，独立包及版本如表，min/target SDK32，
APK v2 签名验证通过。SHA256
`8afef4822d01f71704bd206f3c5a180df62b93cfa2bff71055d03c8e284d58c6`。
**HTS IP 输入仍不能完成，默认广播地址使 RTOUCH 无法开始，未继续扩展此 UI。**
Thor `gate-01`、`gate-02` 均因无真实有效 RTOUCH 超时 FAIL；没有 RTOUCH 样例或协议通过结论。
输入-only gate 快照和日志在 `~/.cache/jaka-teleop-righttouch-20261026`。

本轮 Mac 证据（全部不进 Git）：
`/Users/wujunqi/Documents/Codex/2026-10-26/mac-brvrzl-jaka-teleop-quest-3-2/outputs/quest-righttouch-20261026/`。
包括 APK 身份/manifest/签名、EditMode/Android完整日志、实际菜单与 XRobo 运行截图、
原生回调副本及摘要。Thor `thor` SSH 可用，`thor-user01` 登录被拒，未改动其私有工作区。
未修改 RightTouchInput、ArmClutchMachine、SmoothQuestJakaSession、IK 或 DH 输出链。
后续 Thor 先恢复右 Touch 连接并补重启恢复检查，再决定原生输入的真实 validity/连续性和
统一参考空间如何满足现有安全边界；Grip 共同 Clutch / Trigger 连续夹爪语义仍由 Thor 控制层实现。

MQDH 接近传感器原为 Enabled，本轮约15:02曾临时 Disabled for 2 hours；
没有把该设置等同于摘下持续追踪通过，正常使用前在 Device Actions 核对并 Enable。

## 历史收工状态（2026-10-23）

用户要求今天结束，已停止 Thor 本轮 SDK 观察器和 RoboticsServiceProcess；未发送任何 JAKA/DH 指令。
收工时 USB 已断开，adb 无法停止 Quest 应用或恢复接近传感器；最后已知设置仍为 Disable For 8 Hours。
下次连接先检查 MQDH 的 Proximity Sensor，恢复正常使用选 Enable；Cast 停止后的状态未再次确认。

Trossen 因下述实际键盘失败切换到现成 XRobo，未编译或修改 Unity 发送端。
XRobo Quest [v1.0.1](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client-Quest/releases/tag/v1.0.1)，
commit `05ad3f081e64c400d8eda34c0efdf711c47f6b3a`，包 `com.xrobotoolkit.client.quest` 1.0.1/code 1；
APK SHA256 `c8a077451e7f6b66ca688668d7b32f5a6a6c19a8c0fa4657f2e1344493c174df`。
普通安装，所有旧包保留。应用 Network → PC Service 填 `10.24.1.68`，开启 Head、Controller、Send，关闭 Hand。

Thor 实际 TCP 63901 收到 Quest `10.24.0.3` 输入。固定快照 29,938 帧 / 332.778 秒，约 90 Hz，
最大 SDK 回调间隔 77.8 ms；右位置与四元数确实变化。Grip/Trigger 均覆盖 0–1，
分别有 411 帧仅 Grip >0.5、545 帧仅 Trigger >0.5（另一输入 <0.1）。这证明独立真实输入，不证明完整 tracking 可靠性。
用户确认摘下后单独计时，仅记录 **60.04 秒 / 5,180 帧** 即收工，**没有完成 5 分钟验收**。
轴向、遮挡/休眠、后台、断网重连、头显移动和 recenter 尚未完成受控验收。

原始记录在 Thor `~/.cache/embodied-hand-lab-xrobo/{raw-01,raw-02}.jsonl`、`status-02.log`、
`unworn-start.json`；Mac `outputs/mac-quest/xrobo-snapshot-02.jsonl` 保存固定快照。
维护入口 `tools/xrobo_input_observer.py` 已部署并实际运行：每个 SDK JSON 回调记录一次原始 payload、
host_callback_monotonic_s、本地回调序号和 SDK device id；不是原始 TCP 数据报，也不是 SDK 缓存轮询。
SDK 的 `TestDevice` 是上游写死的名称，不能当作真实设备序列号。150 ms 无新帧显示 stale/current_frame=null。
六项观察器解析测试通过；断流失效的真实端到端验收待补。

协议：位置米、四元数 xyzw；上游已将 Unity 的位置 z 和 quaternion z/w 取反转为右手系，接收端不能再重复转换。
Head 有 status；右控制器没有 is_tracked/status/connected，观察器明确列缺失。
timeStampNs 为源 UTC 时钟，predictTime 为源应用 elapsed 微秒；没有源 seq/session/recenter generation。
头部使用 root pose、控制器使用 visual world transform，同一参考空间须用实际 head-motion/recenter 测试确认。
因此仅完成只读解析，**尚未接入 RightTouchInput 或目标生成**。下一小步是先完成上述测试，
再决定是否给 XRobo 最小补充真实 controller validity、统一参考和源 session/seq，随后局部接入既有 canonical/clutch 路径；
不能伪造有效性或把本地序号冒充源序号。真机输出限制不变，DH 新鲜反馈等原验收仍需完成。

### XRobo Thor 重启入口

使用可登录的 `thor` 账户，不改变 user01 私有目录。官方 PC Service headless arm64 v1.0.0
commit `6386009475369615fa984bca0a6e9902cd81eb2a`，deb SHA256
`532c605dfa1a02b05b7c285b856c91771c78623cded30ef5b16ea371de49ed5f`。
已在缓存目录解包，另局部解包 Ubuntu libicu70 70.1-2ubuntu1，未系统安装或改全局库。
两个 Thor 终端分别执行（日志必须用新文件名）：

```bash
cd ~/.cache/embodied-hand-lab-xrobo/unpacked/opt/apps/roboticsservice
export LD_LIBRARY_PATH="$PWD:$PWD/lib:$PWD/SDK/arm64:$HOME/.cache/embodied-hand-lab-xrobo/icu70/usr/lib/aarch64-linux-gnu"
export QT_PLUGIN_PATH="$PWD/plugins"
./RoboticsServiceProcess
```

```bash
cd ~/.cache/embodied-hand-lab-xrobo
python3 xrobo_input_observer.py \
  --sdk "$PWD/unpacked/opt/apps/roboticsservice/SDK/arm64/libPXREARobotSDK.so" \
  --log "$PWD/raw-NEW.jsonl"
```

Mac 通过 `ssh thor` 启动/观察即可。XRobo 使用 TCP 63901 和 UDP 50087 发现，不套用 Trossen UDP9000 协议。
下面保留 Trossen 的安装、失败证据和可复用入口；其零收包状态不代表 XRobo 状态。

[设备记录](DEVICE_STATUS.md) · [现有右 Touch 接口](../motion_input/RIGHT_TOUCH.md) · [备用发送端补丁](../../quest_sender/README.md)

本轮优先使用现成 Trossen APK，只观察输入，不运行机器人 demo，不向 JAKA / DH 发命令。
只有实测证明现成方案不能满足要求后才评估 XRoboToolkit 或最小发送端补丁；Unity 自编译暂缓。

## 工作区与安装

尚未合并 main，新克隆必须指定工作分支：

```bash
git clone --single-branch --branch work/jaka-teleop-recovery \
  https://github.com/brVrzl/jaka-teleop.git
cd jaka-teleop
```

2026-10-23 Mac 新工作区 `/Users/wujunqi/embodied-hand-lab`，起点 `d50f0b3`，初始干净。
已有 adb：`~/Library/Android/sdk/platform-tools/adb`。USB 授权由用户完成。
实际设备 Quest 3 (`eureka`)，Horizon `207.0.0.190.429`，Android 14，build `52433670032200520` / `UP1A.231005.007.A1`。
两个旧发送包均保留数据：`com.brvrzl.handtrackingstreamer.mixedprobe`、
`com.wengmister.handtrackingstreamer`，均 `versionName=1.1.0, versionCode=7`。
系统不支持 `cmd package get-install-source`；dumpsys 显示 installerPackageName=null，不能推定 APK 源码身份。
完整第三方应用清单与设备属性在忽略目录 `outputs/mac-quest/`。

Trossen 来源：[上游仓库](https://github.com/TrossenRobotics/trossen_vr)，固定
`d8b0def97f1633d3760556b136d6ad04799a9393`，`assets/VR_Teleop.apk`。
SHA256：`3f352857f8b3f07cae9f9ec1d160d070374968e0d70bd254549b09e841f7c72a`。
包 `com.DefaultCompany.vr_controller`，版本 `1.0` / code `11`；安装前包不存在，使用普通 `adb install` 成功，未用卸载或覆盖。
本地 APK 在 `~/.cache/trossen_vr/assets/VR_Teleop.apk`，不入 Git。
[官方操作说明](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/trossen_vr.html)。

## 不佩戴运行与投屏

Mac 已通过 Homebrew 安装 MQDH 6.5.2，用户完成 Meta 登录。
Device Manager → 当前 Quest → Device Actions → Proximity Sensor 原为 **Enabled**，
本轮选择 **Disable → For 8 Hours**，界面确认 Disabled for 8 hours；随后打开 Cast 并看到实际头显画面。
Settings → General 未看到连接时自动禁用接近传感器选项，未声称已配置自动项。
恢复方法：Device Actions → Proximity Sensor → **Enable**；当前普通 Android 超时设置未改动。
停止 Cast 后重新核对开关，不能假定状态保持。保持空间跟踪，稳定放置头显、摄像头朝向右控制器活动区域。

**设置和投屏已完成，不佩戴持续有效位姿验收仍未完成。**
已读取 Android `screen_off_timeout=86400000`（24 小时），未改写；这不是已验证的 Horizon 接近休眠时限。
应在 MQDH/头显核对实际相关时限；至少测 5 分钟，若原有效休眠时限更长则覆盖它。不能用 5 分钟替代 24 小时设置的完整覆盖结论。

## Mac 只读接收

当前 Mac `10.24.0.89`，Quest `10.24.0.3/16`；Quest ping Mac 两包成功。
启动前 9000/9001 无占用。地址变化后重新核对。应用 Robot PC IP Address 填 Mac 地址并 Connect。
接收器只有标准库，不安装 Trossen 机器人库：

```bash
python3 tools/trossen_input_observer.py --bind 10.24.0.89 \
  --allowed-sender 10.24.0.3 --log outputs/mac-quest/trossen-raw-NEW.jsonl
```

日志文件必须是新路径，避免覆盖现场记录。Ctrl-C 停止。一个 UDP 9000 只能有一个对应协议的进程。
不要同时运行旧 HTS/RTOUCH gate。`--duration 360` 可限定观察秒数，默认一直运行。

协议已按固定上游 `src/network_manager.cpp`、`include/trossen_vr/vr_conversions.hpp`、
`src/vr_conversions.cpp` 核对：数据为 UDP 9000 JSON；每个校验通过的数据报回复来源 IP 的 UDP 9001：
`{"type":"ack","timestamp":<host Unix 毫秒>,"frequency_hz":<接收频率>}`。
ACK 时间是主机时间，不是采样时间。

- `right_controller.pose6d`: x/y/z（上游声明米）；ax/ay/az 是旋转向量（轴 × 弧度），不是 Euler 角。
- `is_tracked` 原样显示；`triggers.hand_trigger` 与 `triggers.index_trigger` 分开显示。
  不照搬上游 SDK 的 Grip < 0.9 时强行将 is_tracked 置 0 的处理。
- `buttons.one/two`、`thumbstick.x_axis/y_axis` 以及收到的其他右控制器字段原样保留。
- 缺失字段显式列入 missing。原始 JSON 不增补头部、源序号、源时钟或 session。
- 每次实际 recvfrom 成功且校验通过才写一行：host_monotonic_s、source、local_receive_sequence、raw_payload、missing。
  本地序号/时间仅描述接收事件，不提供源端重复、乱序或旧缓存的可检测保证。
- 状态每 0.5 秒显示一次，不写成新样本。默认 150 ms 无有效报文则 current_frame=null、current_frame_valid=false；
  receiving/current_frame_valid 只表示校验通过且新鲜的报文，不证明 tracking 字段或位姿物理可靠。

## 验收与下一步

当前准备验证：APK 安装与身份检查、同网 ping、合成解析/ACK/超时失效检查已通过。
**真实右 Touch 收包与动作验收待完成，不因应用启动或合成测试而判通过。**
用户实测反馈 IP 输入框点击/Touch 输入无法编辑。重启并用右控制器射线点击后仍不弹键盘：
18:25:36 系统 ImeTracker 报 `PHASE_IME_ON_SHOW_SOFT_INPUT_TRUE` failed，18:25:37 Unity 报
`Timeout while waiting for keyboard to become visible`。投屏确认默认 IP `192.168.0.220`、Disconnected。
日志 `outputs/mac-quest/trossen-keyboard-failure.log`；Mac 实际收到 0 个有效数据报，观察进程已停止。
这是当前固件上的地址输入阻碍，不能推断 Trossen tracking 不可用；没有修改或卸载 Trossen。
需要逐项记录动作时间、原始日志区间和观察：平移/旋转轴向；Grip/Index 独立；静止持续发送与停止后的失效；
摘下头显长时运行；遮挡/手柄休眠；后台；断网/重连；手柄不动时移动头显；recenter。

当前 RTOUCH 接口依赖真实头部参考、源 session/seq/time 和独立有效性。Trossen 上游仅声明 robot coordinate system，
未提供足够可核对的轴映射；不能把其旋转向量套成 Unity quaternion，也不能伪造头部或源时间满足现有接口。
实测明确坐标、参考与缺失字段后，再局部适配 `src/motion_input/right_touch.py` 的输入边界/共用 canonical 路径，
复用既有 clutch 与 target generation；真机输出限制保持。由于上述实测键盘阻碍，已继续验证 XRobo 现成候选；未修改发送端。

## Thor 入口

`thor-user01` 密钥登录失败；已有 `thor` 账户登录成功，但无权访问 `/home/user01/projects/embodied-hand-lab`，未改变权限。
Thor 的 9000/9001 当前查询无监听。Mac 输入验收后，可由 user01 的 Thor Agent 更新工作分支并执行：

```bash
cd ~/projects/embodied-hand-lab
git status --short --branch
# 保留本地修改；在工作分支且干净时更新
git pull --ff-only origin work/thor-onboarding-quest-dh
source ~/.venvs/embodied-hand-lab/bin/activate
ss -lunp | grep -E ':9000|:9001' || true
python tools/trossen_input_observer.py --bind 10.24.1.68 \
  --allowed-sender 10.24.0.3 --log outputs/thor-onboarding/trossen-raw-NEW.jsonl
```

先停止其他 9000 接收进程，再将 Quest 目标改成 `10.24.1.68`；ACK 返回 Quest:9001。
上述入口只观察输入，尚非现有仿真的输入适配完成声明。没有向 Thor 转发合成帧冒充 Quest 验收。
JAKA/DH 后续仍需真实 DH 新鲜反馈、TCP/负载/碰撞模型与既有安全验收，不在本次输入观察授权内。
