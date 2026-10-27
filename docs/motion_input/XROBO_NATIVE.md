# XRobo Quest 原生只读输入契约

服务部署、端口、重启恢复与 Connect 分层排查见[XRobo PC Service](../setup/XROBO_SERVICE.md)。

2026-10-26 Mac 补测，使用原版 XRoboToolkit-Quest v1.0.1 / PC Service v1.0.0。
这是已观察到的原生事实及限制，不是 RTOUCH validity 或机器人控制授权。
未修改 Unity、SDK 观察器或 Thor 控制链。

## 数据来源与字段

`tools/xrobo_input_observer.py` 记录原生 SDK 的 Tracking JSON 回调。
`raw_payload` 是 SDK envelope；其中 `value` 需再解析一次 JSON。
这不是 TCP datagram 原始抓包，也不是主机轮询缓存。

| 字段 | 实际来源 / 用途 | 限制 |
| --- | --- | --- |
| `Controller.right.pose` | 源端 controller visual 的 Unity world position / rotation；字符串 `x,y,z,qx,qy,qz,qw`，位置为米 | 失去连接或 pose 后 visual 可停留旧值；非零和单位 quaternion 不证明 tracking 有效 |
| `Controller.right.grip` | Unity XR `CommonUsages.grip`，0–1 | 上游忽略 TryGetFeatureValue 成功标志；0 也可能是读取失败默认值 |
| `Controller.right.trigger` | 独立的 `CommonUsages.trigger`，0–1 | 同上；连续模拟量，不与 Grip 合并 |
| `Controller.right.secondaryButton` | 右 Touch B，布尔 | 按下/释放已实测；不赋予 tracking 或 Clutch 授权 |
| `Head.pose` / `Head.status` | `Hmd.TryGetRootPose` 成功时传 world pose 并写 status=3，失败写0 | 3 是 XRobo 的常量映射，不是右控制器有效性 |
| `appState.focus` | 源端 `Application.isFocused` | 本轮实际收到的帧均为 true；暂停/失焦期间可能直接无回调 |
| `Input` | 源端优先判断任一 hand visual 可见，其次 controller connected | 本轮全部为2，同时存在真实 Touch 按键变化；不得把2解释成右控制器必定无效，也不得把1解释成 tracked |
| `timeStampNs` | 源端 UTC：DateTime.UtcNow 与 Unix epoch 差值换算 | 墙钟、非 monotonic；名称不保证纳秒精度；源码异常分支还可能使用 ticks，需独立识别异常 |
| `predictTime` | 源端 `Time.unscaledTimeAsDouble * 1e6`，应用 elapsed 微秒 | 不是 packet seq；重启下降可观测，但不能据此伪造源 session |
| `host_callback_monotonic_s` | Thor 观察器进入 SDK 回调时的主机 monotonic 时间 | 只用于主机 age / 停流判断，不是设备采样时间 |
| `local_callback_sequence` | 观察器本地计数 | 不是源 seq，不能据此判断源数据重复或源 session 连续 |
| `sdk_device_id` | SDK 的 `TestDevice` 标签 | 不是 Quest 或右手柄硬件序列号 |

原版流中 **右侧 IsConnected、IsPoseValid、独立位置/方向 tracking 标志、源 session、
源 seq、tracking origin / recenter 代次均缺失，保留 unknown**。
不得从非零 pose、按钮、时间递增、SDK 标签或主机计数补造这些字段。
观察器的 receiving 仅表示最近收到可解析回调；stale 后 `current_frame=null`，
不代表它已经验证 receiving 帧具有真实 tracking。

## 坐标与实际 SDK 语义

固定源码 `XR-Robotics/XRoboToolkit-Unity-Client-Quest` commit
`05ad3f081e64c400d8eda34c0efdf711c47f6b3a`，Meta 依赖72.0.0：

- `QuestTrackingDataSource.GetHeadsetPose` 调用 Hmd.TryGetRootPose；Meta Hmd.cs
  会调用 TrackingToWorldTransformer.ToWorldPose，并非直接返回原始 tracking-space 数值。
- Controller visual 也由 Controller.TryGetPose 的 world pose 更新；Main.unity 的 Head、
  右 Controller 和 visual 来自同一个 OVRInteractionComprehensive prefab 实例。
  源码支持两者处于 Unity world 的结论；跨重启/recenter 的稳定连续性仍无传输保证。
- XRobo 对 Head 和 Controller 都已执行 `p.z=-p.z; q.z=-q.z; q.w=-q.w`，
  输出为右手坐标。接收端不得再次翻转 Z；quaternion `q` 与 `-q` 等价。
- `Controller.IsConnected = IsDataValid && IsConnected`，provider 的连接位来自
  `OVRInput.GetConnectedControllers()` 对对应手柄的 mask，属于应用 SDK 状态，
  不等同于 Android 系统底层无线配对连接。
- `Controller.IsPoseValid = IsDataValid && RootPoseOrigin != None`；当前
  FromOVRControllerDataSource 在 connected 后直接设置 RawTrackedPose，
  没有独立检查位置/方向追踪质量。因此该属性确实可读取，但不能重命名为严格 tracked。
- `OVRControllerVisual.HandleUpdated` 在断连/pose 不可用时隐藏 helper 并返回，
  不清除 visual transform。原版发送端仍读取 transform，存在持续发送旧位置的风险。
- Meta `OVRDisplay` 通过 `OVRPlugin.GetLocalTrackingSpaceRecenterCount()` 变化触发
  `RecenteredPose`。本轮 Unity logcat 确实出现 `Recenter event detected`；
  原版 XRobo 没有把该事件或 tracking origin 代次写入原生 JSON。

如后续补字段，只能读取上述真实 SDK 属性、在源应用生成 session/seq，并绑定真实
运行时 origin/recenter 事件；事件无法覆盖的范围继续 unknown。不要用位姿跳变猜代次。
本轮没有构建这个扩展，也没有声称字段已经实装。

## 2026-10-26 补测结果

Quest ADB `2G97C5ZJ2901FK`；右硬件 id `3a04abe84951aa41`，系统标为 Right，
电池70%。开始时配对仍在、connected 但 asleep/inactive；操作者按 B/Trigger 并移动后，
系统快照为 CONNECTED_ACTIVE / TrackingStatus POSITION，Tracking 日志也有真实 IMU 输入。
本轮不需重配对。能确定本次需唤醒，不能回溯确定历史30,328全零帧的唯一故障原因。

新采集 `native-20261026-02` 共31,142回调，首末跨度710.639秒，包含休眠、
重连、停流和重启空档，不能用全程平均值宣称持续90Hz。稳定按键窗口约90Hz：

| 场景 | 真实记录 | 结论 |
| --- | --- | --- |
| Grip / Trigger / B / 移动 | 4,565帧 / 50.730秒；Grip、Trigger均0–1；仅Grip612帧、仅Trigger289帧；Grip>0.9最长4.840秒；Trigger中间模拟量169帧、三位小数250种；B按下317/释放4,248帧，1次上升/下降沿 | 原生独立输入已证实 |
| 三轴平移、手腕旋转 | xyz跨度0.277/0.354/0.345米；相对首帧最大旋转146.065度；quaternion norm约1 | 操作者做了各方向移动与旋转；未做逐轴标定或硬件时间同步 |
| 仅头部运动 | 4,456帧，Head xyz跨度0.249/0.139/0.330米、旋转78.671度；Controller pose字符串全窗只有1种 | 未看到头动直接改变输出的Controller world pose；不能排除visual冻结，不能认证静止控制器仍有效追踪 |
| recenter | 操作者确认，17:50:22.058 Quest Unity日志记录真实recenter事件；Head/Controller前后值保留在statistics.json | 操作包含拿起再放回手柄，不能仅用前后差推定纯origin刚体变换；原生流缺事件/代次，连续性认证未通过 |
| 停止 Send 后恢复 | 最大回调空档12.299秒，stale时frame为空；恢复后有实际位姿与Grip/Trigger变化 | 主机停流过期与重新接收已证实 |
| 应用退出/重启 | ADB PID22548→28566；38.177秒空档；predictTime 647423972.100→36894750.550微秒 | 新进程重新启用原生发送后恢复；不是自动后台重连保证 |
| 重启后右控制器 | 新进程区间5,498帧 / 61.826秒；1,512种pose，Grip/Trigger均0–1、B按下70帧；xyz全零帧0 | 本轮恢复成功，没有重复历史全零现象；非零计数仅描述数据，不作为validity规则 |
| 真正断开右手柄/恢复 | 操作者取消取电池测试，没有确认取出电池 | 未执行，不声称通过；普通休眠/唤醒记录仍保留 |

头显休眠后曾停回调307.526秒；截图显示唤醒后UI仍为 WORKING、Send勾选，
但 Thor 仍 stale；操作者 Reconnect 并切换 Send 后恢复。不能只信UI的连接提示。
未执行重复/过期/无效源包注入测试；缺少源seq/session/validity，不能宣称这些安全门已通过。

## 证据与后续范围

Thor 完整记录：`/home/thor/.cache/embodied-hand-lab-xrobo/native-20261026-02/`。
Mac 完整副本：
`/Users/wujunqi/Documents/Codex/2026-10-26/mac-brvrzl-jaka-teleop-quest-3-2/outputs/xrobo-minimal-20261026-02/`。

`native/raw.jsonl`、`status.log`、`events.jsonl`、`statistics.json`、`real-samples.json`
及 SHA256SUMS 已完整复制并逐项校验；raw SHA256：
`5b12f62f72ec28e8c421a2484dd7b461404c0f11897a822d2dd75e0cc3d8ea80`。
事件时间是主机请求/操作者确认的时间边界，不是源按键采样事件；统计为离线推断。
`source-evidence.txt` 保存精确源码节选，`quest-full-logcat.txt` 保存系统/Unity事件，
`xrobo-awake.png` 是实际 WORKING / Head+Controller+Send 开启、Hand关闭的画面。
重启后截图为黑屏，单独标注为 `xrobo-restart-capture-black.png`，不作为运行证明。

实际安装包 `com.xrobotoolkit.client.quest` 1.0.1/code1，设备base.apk与缓存原版均为
SHA256 `c8a077451e7f6b66ca688668d7b32f5a6a6c19a8c0fa4657f2e1344493c174df`。
本轮无Unity修改/新APK/构建测试；上游工程要求2021.3.45f2，而本机现有Editor为6000.0.65f1，
未用Unity6打开或升级它。原APK签名与本机已有debug签名不同；后续同包更新需匹配签名，
未卸载原应用或新建第二包来绕过。

Thor 可继续原生离线适配、合成仿真和DH资产工作：读取上述事实，保持缺失状态unknown，
不要将观察器receiving或主机时间/计数变成设备有效性。共同Grip Clutch授权和Trigger夹爪
语义仍由后续控制层实现。源有效性/连续性字段真正实装并验证前，本记录不授予物理输出。
收工时XRobo、此轮观察器和PC Service已停止。历史native-01全零记录、旧APK及应用数据保留；
没有修改RightTouchInput、ArmClutchMachine、SmoothQuestJakaSession、IK或DH输出链，
没有执行JAKA、DH、RH56物理动作。

## Thor实验live接入

原生接收已用于MuJoCo live实验，入口和记录格式见
[Simulation](../simulation/SIMULATION.md#xrobo-native--dh-proxy)。
这不改变上表字段的真实性边界：右控制器tracking/session/seq/recenter继续unknown，
不把数值可用性提升为物理授权；原生SDK不调用任何机器人控制API。
