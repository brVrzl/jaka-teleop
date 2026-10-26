# Thor 新用户部署与设备验证状态

这是在当前 `user01` 环境实际执行的记录（部署 2026-10-23，RH56 仿真追加验收 2026-10-26）。离线、计算查询、相机采集与执行器动作分开描述。
[安装](INSTALLATION.md) · [JAKA 首次连接](../operation/REAL_ROBOT.md) · [右 Touch](../motion_input/RIGHT_TOUCH.md) · [DH/TIO](../operation/DH_TIO.md)

## XRobo experimental live：现场验收未通过（2026-10-26）

本轮实际接通Quest→PC Service→native SDK→同一MuJoCo live循环；原生输入-only
观察到约90 Hz。当前账户HTTP代理曾阻断localhost gRPC，接收器现明确排除本机代理。
新增共享native接收器，观察器/live复用；不构造RTOUCH、不赋予hardware授权，
RH56双Clutch、native安全边界及continuation IK未更改。

首次live出现手指代理约0.26 mm偏移，既有反馈检查中止运行；未放宽检查，
仅提高DH代理位置执行器与对称约束刚度。刚录制输入的事故回放及39项回归通过后
再次运行live-02，日志记录1,632 accepted、IK位置/方向/奇异性拒绝，完整qpos已保存。
这不是功能PASS：**操作者反馈“仿真内机械臂一直没有运动”，且映射关系尚不清楚，
要求当天停止。** 日志与现场观感存在未解释差异，不能用accepted数量或桌面截图覆盖反馈。
后续暂停/恢复、B Stop、应用失焦及操作者无跳变确认未完成；tracking-loss未验收。

证据保留在`outputs/xrobo-live/`：input-local输入-only、live-01失败输入/日志/视频、
incident-replay离线定位、live-02原始SDK回调/全量events/报告/235秒桌面录屏及截图，
窗口属性与display.txt。live/replay来源分别标记；不提交这些原始数据。
相关280项回归通过；随后源时钟异常检查的39项针对性复测通过。
最后增加的退出错误报告与显示文案未再做真人live验收。仿真、录屏与本轮PC Service已结束。

明日从短时输入-only开始，先核对操作者所见屏幕是否为当前MuJoCo窗口、实际输入到达
时刻和停流区间；明确Grip相对接管、Head yaw坐标参考、三轴平移/旋转的对应关系，
再逐轴小幅验证并同步记录用户所见。不要直接重演大幅动作或宣称当前映射已通过。
只读真机配置盘点已完成；现场动作仍禁用，剩余条件与逐项顺序见[DH/TIO](../operation/DH_TIO.md#xrobo-live-仿真后的真机准备审查2026-10-26)。

## XRobo 原生输入与 DH 代理仿真（2026-10-26，Thor）

基于 Mac 分支 `57adf0d` 开发，并已合入最新 `20b872e`；没有重复 RH56 现场验收。通过 `thor` 账户把
`native-20261026-01` 原始证据复制到当前账户，原文件和私有目录权限未变。
Mac 私有目录没有直接访问；分析的是 Thor 留存的同轮原始 SDK 回调。

独立解析全量 74,266 帧，跨度 1,037.474 秒；发现 10.204 秒停流、201.732 秒
重启空档及一次 predictTime 回退。受控动作窗口 9,705 帧，Grip/Trigger 均覆盖
0–1，B=true 235 帧，右控制器 XYZ 跨度约 0.551/0.420/0.401 m。
Head status 全部为3，全程 XYZ 跨度约 0.925/0.675/0.973 m；这些变化不能证明
Head root pose 与 Controller visual world transform 的参考空间已统一。
重启后恰好 30,328 帧右控制器位置/按钮全零，全部被实验准入拒绝。
源 sequence/session/recenter 代次、右控制器独立 validity 仍未知，未补默认真值。

已审阅固定版本的
[QuestTrackingDataSource.cs](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client-Quest/blob/05ad3f081e64c400d8eda34c0efdf711c47f6b3a/Assets/Scripts/Quest/QuestTrackingDataSource.cs)、
[TrackingData.cs](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client-Quest/blob/05ad3f081e64c400d8eda34c0efdf711c47f6b3a/Assets/Scripts/TrackingData.cs) 和
[PC Service 转发](https://github.com/XR-Robotics/XRoboToolkit-PC-Service/blob/6386009475369615fa984bca0a6e9902cd81eb2a/RoboticsService/Business/DeviceManage/devicemanagement.cpp)。
IsConnected/IsPoseValid 没有被当前 Controller JSON 编码；上游已翻转 position Z
及 quaternion Z/W，Thor 不再转换。PC Service 传递原 JSON，不补齐控制器有效性。

| 实际运行 | 输入性质 | 结果 |
| --- | --- | --- |
| 全量输入-only回放 | 原始真实 SDK 回调 | 43,938 帧只满足实验数值条件；30,328 帧全零拒绝；正式硬件授权不可用 |
| 全零段完整 MuJoCo 回放 | 真实断连负面记录 | 30,328 回调；0次接管、0 accepted、无夹爪命令，全部机械臂关节零位移 |
| 20秒统一 Clutch 联合回放 | 明确标注的合成数据 | 932 accepted、3次接管；6个 arm 关节均移动，夹爪模拟闭合比例0–0.85、指间距26.2–4.1 mm |
| 受控动作窗口联合回放 | 真实记录的未验证实验回放 | 704 accepted、2次接管；夹爪模拟比例0–1、指间距26.2–0.2 mm；B stop/断流要求重新接管 |
| 实体桌面联合可视化 | 同一合成20秒回放 | 1,200次viewer更新；保存16秒桌面视频，UNVERIFIED/DH PROXY标识和关节动作可见 |

DH 是[有尺寸来源的代理几何](../../assets/README.md#dh-pge-50-26-simulation-proxy)，
不是实物精确碰撞模型；TCP、安装件、惯量分配仍是假设。
复用同一 ArmClutchMachine/IK/AcceptedArmTarget，删除输入层独立 gripper clutch。
可信 RTOUCH 短断流重锚保留，夹爪捕获新 Trigger 参考不追赶；XRobo 没有连续性代次，
不允许自动重锚。反馈故障在新 arm target 前终止联合会话。旧 RH56 双 Clutch 回归保留。
279项相关测试通过；另补测13种恢复边界中的夹爪保持与重锚行为。

本地证据在 `outputs/xrobo-dh-sim/`，不提交原始记录或生成缓存：
`independent-analysis.json`、`native-input-gate.json`、`native-20261026-01/`、
`real-disconnected-complete.{json,events.jsonl,log}`、`real-controls-final.*`、
`synthetic-unified.*`、`monitor-final.mp4`、`monitor-video-frame.png`、
`mapped-desktop.png`、`mapped-window*.txt`、`xrandr.txt` 和测试日志。
实体 seat0 X11 桌面的启用输出、MuJoCo IsViewable/Fullscreen 属性与真实桌面录屏相符；
此轮没有另做面板光学拍摄或要求操作者确认新模式，不能把桌面证据称为真实 Quest live 验收。

最新补测同样通过授权账户复制 `native-20261026-02`，独立确认31,142回调、
710.639秒跨度、12.299秒停流、38.177秒重启间隔、一次elapsed回退；重启后5,498帧，
全量零XYZ帧为0，Grip/Trigger均0–1，B按下387帧。完整联合回放得到704个accepted
target、8次接管，六关节实际跨度约0.193/0.042/0.368/0.500/0.588/0.832 rad；
夹爪实际模拟闭合比例0–0.9663，代理指间距26.2–1.076 mm。该结果仍是记录回放。
受控动作窗口另在实体桌面完成可视化，保存45秒录屏 `native-02-monitor.mp4`、
`native-02-desktop.png`、`native-02-window.txt`、`native-02-xrandr.txt`；
完整事件为 `native-02-full.events.jsonl`，独立分析与关节指标为
`native-02-independent.json` / `native-02-joint-metrics.json`。合入后相关38项复测通过。
报告内有界诊断计数不是全量帧/tick总数，应以local_callback_count及完整事件日志为准。

**仍未完成：** 动态参考空间验证、独立有效性/源连续性及recenter代次。
Mac 已完成连接恢复和重启补测，不再要求重复配对、取电池或重启；
源码共同Unity world及上游坐标转换已在[原生契约](../motion_input/XROBO_NATIVE.md)中明确，
但静止旧pose不能证明持续tracking。实时联合输入仍关闭，input-only可用；未执行任何
JAKA/DH/RH56物理动作，未改真机安全配置，未把SDK缓存当作夹爪实测。

## RH56 实体显示器仿真验收（2026-10-26）

真实 Quest HTS/Head/CTRL → 原双 Clutch → MuJoCo JAKA/RH56 已实际运行，
操作者确认动作、方向及重新接管验证通过。未连接或命令物理执行器。
180 秒运行收到 2,401 CTRL、9,052 hand/head 数据报；673 个无效 CTRL 样本未获授权。
AcceptedArmTarget 为 2,199，arm/hand 接管次数为 4/2；记录到释放、失效 HOLD、
有效释放后恢复再接管。viewer 更新 10,795 次，约 59.95 Hz。此轮未单独诱发所有
限位/碰撞/硬停止场景；对应安全规则由既有离线回归覆盖，不能称全部已做现场故障注入。

实体 DELL U2419H 的 EDID、DRM connected、Xrandr 1920×1080@60 Hz 输出，
以及全屏 IsViewable MuJoCo 窗口、真实桌面截图/12 秒录屏相互对应。
桌面属于 `thor` 的 seat0 X11 会话，给本机 `user01` 加了限定用户访问授权，
没有切换用户、使用 Xvfb 或开放全局 xhost。操作者也确认实体画面。

原事件文件暴露了只输出内存最后 128 tick 的问题，现已改为逐 tick 落盘，
保留内存有界缓冲。此前 live 的全程关节范围无法从该尾段事件文件恢复；
原始真实 UDP 完整保留。对该录制进行离线回放得到 4,020 tick、2,202 个 accepted、
8 次 IK_POSITION_FAILED；六个 RH56 实际仿真关节运动范围分别为
1.409/0.489/1.325/1.605/1.607/1.607 rad（拇指侧摆、拇指闭合、食/中/无名/小指）。
这是回放测量，不能冒充原 live 的逐关节统计；live 的执行效果由画面、终端及操作者确认。
128 项相关回归通过，另复测实体 viewer 3 秒产生全部 180 条事件。

Thor 本地证据保留于 `outputs/teleop-validation/20261026-rh56/`（不提交生成物）：
`monitor.json`、`monitor.raw.jsonl`、`monitor.log`、`desktop-x11.png`、
`live-desktop.mp4`、`window-info.txt`、`xrandr.txt` 和 `replay-metrics.json`。
[常用启动与回放流程](../simulation/SIMULATION.md)。右 Touch + DH 尚未通过；
此验收不替代新模式或 DH 真机验收。

## 环境与可复现入口

- Ubuntu 24.04.4、aarch64，内核 `6.8.12-1021-tegra`，L4T 39.2。
- NVIDIA Thor，驱动 595.78；`nvidia-smi` 报 CUDA 13.2，但未发现 `nvcc`，不将驱动能力写成已装 CUDA toolkit。
- Python 3.12.3、GCC 13.3、CMake 3.28.3；系统编译工具、GPU 驱动和 EGL 已有，未重装。
- 项目 `~/projects/embodied-hand-lab`；独立 venv `~/.venvs/embodied-hand-lab`，未复用其他用户环境。
- 已安装基础包、MuJoCo、pytest、pyserial、pyrealsense2、OpenCV、PyArrow；回放/导出检查另补 h5py、matplotlib。
- CLI help、doctor、MuJoCo headless smoke、实际 EGL 渲染通过；两个 JAKA native 组件构建和 `ldd` 通过。
- 新用户属于 `video`/`render`，相机采集实测可用；没有免密 sudo。未为绕过限制修改全局权限。
- 新用户 adb 34.0.4 从本机 Ubuntu arm64 软件源下载并解包到 `~/.local/opt/embodied-lab-adb`，无系统覆盖；最初USB未枚举Quest。
  用户连线后发现Thor端为`device`角色（UDC configured、usb0/l4tbr0上线），已定位为设备模式口，
  需换到USB host口后读取APK身份；这与头显是否开启开发者模式是不同问题。

```bash
cd ~/projects/embodied-hand-lab
source ~/.venvs/embodied-hand-lab/bin/activate
embodied-lab --help
embodied-lab doctor --runtime-config configs/local/thor.yaml
embodied-lab sim smoke
```

本地 YAML 和完整日志均被忽略。`ready_offline` 仅表示软件/配置检查通过，不表示设备动作获准。
训练源子模块未初始化，历史数据、训练镜像和权重不在新用户目录；未重跑训练。

## 设备事实

| 设备 | 实际验证 | 尚未验证 |
| --- | --- | --- |
| JAKA | LAN2 静态地址配置后 SDK 登录成功；5 秒、50 次只读周期，所有已调用 API 返回 0；无故障、未上电/使能 | 伺服/TIO有效版本、实际工具 TCP/负载、运动和安全动作验收 |
| Quest | 从 `10.24.0.3` 收到现有 HTS/CTRL，20 秒内 501 CTRL、397手部、982头部包，解析错误0；出现1次stale | 全部CTRL报告控制器未连接/未跟踪/未active，按键为0；没有RTOUCH，不能算右控制器验证；已安装APK来源/版本待核对 |
| DH | 用户提供铭牌 `PGE-50-26-O-S-M1`、S/N `35503152`；官方型号/选型码已核对；TIO供电与通信配置成功读回 | 航插线针脚、TIO版本、真实反馈新鲜度、初始化/开合及联合遥操作 |
| D435工作区 | SDK serial `346522072675`，固件5.15.1.55、USB3.2，画面确认工作区 | 长时负载与最终机器人episode同步 |
| D435腕部 | SDK serial `346222072985`，固件5.15.1.55、USB3.2，用户确认腕部；当前静止姿态朝天花板 | 同上 |
| RH56 | 本轮未连接；原配置、入口及历史数据契约保留 | 本轮不做RH56真机验收 |

不要使用 sysfs 中 `315223123328` / `315223123181` 作为 RealSense 配置序列号；那是另一层 USB 标识。

### JAKA 网络、工具与模型

管理 SSH 使用 Wi-Fi `wlP1p1s0 / 10.24.1.68`，专用有线 `enP2p1s0 / 192.168.71.19/24`。
初始 LAN2 自动获取地址且直连主机无 DHCP，旧候选 `.50` 无响应；没有清空或改写 Thor 网卡。
用户将控制柜 LAN2 设为 `192.168.71.50/24` 后连通。页面不接受空/0网关，因此填 `.1` 作为界面要求的占位，
没有实际路由器；本地同网段通信不使用网关。详见[配置步骤](../operation/REAL_ROBOT.md)。

用户按实物与示教器确认：JAKA Mini 2（S/N `MC21200647`）、MiniCab（`CABm11007100`）；
App `1.7.2.25`，控制器 `1.7.2_49_X64_minicab`，PSCB `03_18PR`。
显示的伺服 `0.0`、`TIO-0.0_0.0` 不作为有效板卡版本；当时机械臂下电，仍需核对。
本地SDK发布说明要求控制器至少`1_7_2_28`，现场49满足此版本下限；这不等于所有功能均已验收。
匹配文档优先参考[JAKA 1.7.2旧版](https://www.jaka.com/docs/legacy172/guide/1.7.2/dh/index.html)，不把Coboπ330菜单当成现场版本。

只读结果：SDK `V2.2.7stable_linux`，关节当前全部0，工具0和用户坐标0均零变换；TCP `[0,-6,766.800003052]` mm，RPY为0。
负载读回 `0.45 kg`，质心 `[0,0,70] mm`，安装角为0。不能据此认定这些设置符合新DH工具。

控制器 Denavit–Hartenberg 参数与模型连杆尺寸有对应关系；另调用 SDK **正运动学计算**比较8组输入，
现有MJCF法兰最大位置差 `0.0008713 mm`、旋转差 `0.0002977°`。这些只是计算查询，无关节运动命令，
不能代替实际关节方向/零位/限位、工具安装与碰撞几何验收；也不能只靠它给实物改型号名称。

TIO读回：24V输出启用；DI/DO/AI模式分别`[0,0,1]`（AI复用RS485L）。SDK通道1（界面通道2）为Modbus RTU、
从站1、115200/8/N/1；通道0为透传模式、从站0。没有写入任何TIO设置，也没有初始化电爪。
已配置RS485L不证明实际线缆接到这组针脚。SDK缓存读数不等于有可验证时间戳的真实电爪反馈。

容量修复后，实际读到现有信号 `init`/512、`gripperstate`/513、`gripperpos`/514 和 `aa`/259，
都在SDK通道1、FC03、频率字段2，缓存值均0。保留全部原定义，没有新增、删除或刷新信号。
这不证明电爪已收到读请求或正在运动。此前 `jaka-tio-inventory.json` 的四条空白记录是SDK输入容量为0
造成的无效结果；有效记录是 `jaka-tio-verified-buffer.json`。已修复接口容量并加入回归测试。

### 双相机短录制

分别检查两台后，再同时运行并保存两种5秒采集；均为640×480、请求30 FPS：

| 模式 | 工作区 | 腕部 | 保存内容 |
| --- | --- | --- | --- |
| RGB-D | RGB约29.98 FPS，RGB帧号缺口0，深度缺口2 | RGB约30.11 FPS，RGB/深度缺口均0 | RGB视频、逐帧原始Z16深度、比例尺、帧号和时间戳 |
| RGB-only | 约30.10 FPS，RGB缺口0 | 约29.97 FPS，RGB缺口0 | RGB视频和时间戳；**不保存深度** |

时间戳域为SDK `global_time`，同时保存主机monotonic/wall时间，不能因此宣称两相机硬同步。
深度比例尺约 `0.001 m/unit`。缺口统计由连续设备帧号计算；不是所有潜在丢帧机制的证明。
默认本地采集配置仍是 `capture_depth: false`，设备支持RGB-D与当前配置保存深度是两件事。

[5秒真实双相机视频](../media/dual-d435-check.mp4)：左工作区、右腕部，压缩预览15 FPS。
这是 camera-only 证据，没有机器人/夹爪反馈，不是拾放演示或训练episode。

## 本机证据与剩余验收

详细证据在仓库忽略目录 `outputs/thor-onboarding/`：

- `doctor-local.json`：离线环境与配置。
- `jaka-readonly.json`：最初登录失败；`jaka-connected.json/jsonl`：连通后的真实只读状态；`jaka-tio-verified-buffer.json`：有效TIO信号盘点。
- `model-comparison.json`、`fk-comparison.json`：静态及纯计算模型对比。
- `quest-input-second.json`、`quest-input-second-raw.jsonl`：真实旧协议输入；包含源地址和收包时间。
- `hts-replay.json`：上述现场HTS的离线 replay，397帧，395 disengaged、1线速度限制拒绝、1接受；不是实物运动。
- `camera-*/`、`dual-rgbd/`、`dual-rgb/`：实际单机/双机短录制、时间戳、预览及摘要。

完整离线测试实际运行 **737 passed**（另有2条现存multiprocessing fork弃用提示）。
初次回归发现测试写死`.venv/bin/python`及可选h5py/matplotlib缺项；已使用当前解释器并补齐依赖后复测。
右Touch合成输入replay为121帧、102 accepted target、2次Grip参考捕获；不当作头显实测。

没有生成DH真机拾放视频或带真实机器人/夹爪反馈的新episode。当前旧12维RH56收集器拒绝
`jaka_dh_7d_v1` profile；没有用补零冒充反馈，也没有用旧checkpoint驱动新夹爪。

下一步依次完成：版本和线缆核对 → 可验证DH读回 → 现成Trossen APK真实右Touch输入验收（Unity自编译暂缓） →
新工具TCP/负载/碰撞几何 → 操作者准备后的有限夹爪动作与低速短程机械臂试验 → 联合拾放与独立7维episode验收。
当前准备工作不构成执行器动作授权。

Quest 的 Mac USB 调试、安装与输入验收见[Mac 交接清单](MAC_QUEST_HANDOFF.md)。

## Mac / Quest 接续（2026-10-23）

收工更新：Trossen 实测键盘无法编辑 IP，转用现成 XRobo Quest 1.0.1/code1（`com.xrobotoolkit.client.quest`）。
Thor `thor` 账户的独立只读服务已实际收到约90Hz右Touch数据，Grip/Trigger独立0–1、位姿变化均有日志。
固定快照29,938帧/332.778秒；用户确认摘下后的独立计时仅60.04秒/5,180帧，未完成5分钟验收。
右控制器tracking有效性字段缺失，坐标参考、遮挡、后台、断网重连、recenter待测，尚未接入RightTouchInput。
收工已停止Thor观察器和服务；USB已断开，未能恢复MQDH proximity，最后已知为禁用8小时。
详细来源、日志、恢复及重启命令见[交接文档顶部](MAC_QUEST_HANDOFF.md)。以下为此前安装阶段记录。

实际 USB 设备为 Quest 3 / eureka，Horizon `207.0.0.190.429`，Android 14，build `52433670032200520`。USB 授权已完成。
旧 `com.brvrzl.handtrackingstreamer.mixedprobe` 与 `com.wengmister.handtrackingstreamer`
均为 1.1.0 / code 7，均保留；不能仅凭版本匹配确定源码来源。
新 Trossen `com.DefaultCompany.vr_controller` 1.0 / code 11 已独立安装成功。
来源、SHA256、完整启动命令和恢复步骤统一见 [Mac 交接](MAC_QUEST_HANDOFF.md)。

Mac `10.24.0.89`、Quest `10.24.0.3` 同网 ping 成功；JSON UDP 9000 / ACK 9001
只读观察入口已准备，原始 tracking 与 Grip 不合并，150 ms 超时清空当前帧。
解析测试及本地合成 UDP 的 ACK/拒绝错误报文/超时检查通过，不作为 Quest 实测。
MQDH 6.5.2 已安装并登录；Proximity Sensor 从 Enabled 改为 Disable → For 8 Hours，Cast 已显示头显画面。
General 设置未看到自动禁用 proximity 的选项。尚未完成不佩戴长时或真实右 Touch 验收。
Android screen_off_timeout 原值 86400000 ms 未改，实际 Horizon 接近休眠时限仍需核对。
用户反馈 Trossen IP 输入框不能编辑，当前尚无真实收包，不据此判定追踪方案失败。
Thor user01 SSH 密钥认证失败；thor 账户可登录，但不访问/更改 user01 私有工作区。
本轮 Thor 尚未收到 Trossen 输入，坐标与现有 RightTouchInput 的适配尚未验证；未发送任何 JAKA/DH 动作。
