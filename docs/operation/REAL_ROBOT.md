# JAKA 首次连接与真机操作边界

[安装](../setup/INSTALLATION.md) · [安全约束](../safety/REAL_HARDWARE_SAFETY.md) · [遥操作](TELEOPERATION.md) · [English](#english)

本页把网络、只读诊断和物理动作分开。只读连接不要求使能机械臂，不应自动清除告警、上电、进入 servo、
改 TCP/负载或初始化电爪。所有真机动作需满足现场条件并明确选择对应入口。

## 1. 先核对设备与接线

本轮由用户提供的铭牌与版本页信息如下；迁移现场时重新核对，不把文件名当设备识别：

| 项目 | 已取得的现场信息 |
| --- | --- |
| 机械臂 | Mini2，S/N `MC21200647` |
| 控制柜 | MiniCab，S/N `CABm11007100` |
| App | `1.7.2.25` |
| 控制器 | `1.7.2_49_X64_minicab` |
| PSCB | `03_18PR` |
| Servo / TIO | 下电状态显示 `0.0` / `0.0_0.0`，不能作为有效固件版本 |

SDK 版本由诊断器单独输出，不能代替控制器版本。仓库中的 `Mini2` 与 `minicobo` 命名保留，
实物已确认 Mini2，运动学匹配还需看下面的计算核对和实际标定边界。

随仓库的 [SDK 2.2.7 发布说明](<../../third_party/jaka_sdk/v2.2.7/SDK V2.2.7 Release Notes.pdf>)
要求控制器至少为 `1_7_2_28`，当前 `_49` 满足这一最低版本条件。说明中的 PSCB 参考版本为 `03_17_PR`，
现场是 `03_18PR`；MiniCobo servo 参考版本为 `R3214_MINICOBO`，现场有效 servo/TIO 版本尚未取得。
因此只读调用成功不等于所有固件组合和运动模式已经验收，也不为读取版本擅自上电。

运动前的模型核对至少包括：关节数量/顺序/方向/零位、连杆尺寸、法兰与基座坐标系、关节限位、
同一静止姿态下 SDK 关节读数与模型 FK/TCP 的对比。改文件名不能完成这个核对。
换装 DH 后，旧 RH56 的 TCP、负载与碰撞几何均不能直接作为当前配置。

## 2. 不知道控制柜 IP 时，先查地址

**不知道 IP 时不要直接照抄历史地址。** 先查实际端口及地址方式，再决定是否需要设置静态地址。
本轮确认 LAN2 原先为自动 IP、直连 Thor 的链路没有 DHCP 服务；现场人员随后完成了下述静态配置。

优先使用已连接的示教器：先记录其 App/控制器版本，再打开对应版本的网络设置页面，
查看**实际接线端口**的地址、掩码和 DHCP/固定方式。只读取，不点击保存。
可将该页、版本页与控制柜端口标签拍照交给部署人员核对；不要包含账户密码。

使用厂商软件时，先确认软件与控制器版本匹配。本机已确认是 **JAKA App 1.7.2.25 / 控制器 1.7.2**，
优先使用 App 随附帮助与 [JAKA 1.7.2 官方文档](https://www.jaka.com/docs/legacy172/guide/1.7.2/SDK/Cpp.html)。
按该版本实际界面的设备连接列表和网络设置查找控制柜，并以铭牌/序列号核对目标，不能按列表顺序选择。
不要把 Coboπ 3.x 的登录菜单、默认 LAN1/Wi-Fi 设置直接套用到本机；软件列表为空也不能证明控制柜故障。

没有可用示教器连接时，在**已确认是机器人专用的以太网接口**上依次做以下只读排查：

```bash
ROBOT_IFACE=enP2p1s0  # 先通过现场网线和接口核对；不是所有 Thor 都使用此名称
ip -brief link show dev "$ROBOT_IFACE"
ip -brief address show dev "$ROBOT_IFACE"
ip -s link show dev "$ROBOT_IFACE"
ip neigh show dev "$ROBOT_IFACE"
```

- 没有 carrier：检查控制柜是否启动、线缆与端口灯，不重置主机网络。
- 控制柜经 DHCP 路由器/交换网络接入：按控制柜 MAC 查询该 DHCP 服务的租约，再核对设备身份。
- 有 carrier、同网段地址未知：若系统已安装 `arp-scan`，可由管理员执行
  `sudo arp-scan --interface="$ROBOT_IFACE" --localnet`，只发现该专用链路当前子网的邻居。
  这不会改变控制柜配置；不要在公司管理网络上无差别扫描。
- 可选的被动观察为 `sudo timeout 15 tcpdump -eni "$ROBOT_IFACE" 'arp or (udp and (port 67 or port 68))'`，
  用于观察控制柜是否广播 ARP 或请求 DHCP，不发送运动命令。

`ip neigh` 不是完整设备清单，`arp-scan --localnet` 也不会发现所有未知子网。
若控制柜地址属于另一子网或直连 DHCP 端口没有服务器，仍需示教器/匹配版本的厂商工具确认。
不要盲扫多个网段、恢复出厂、重启网络或更换控制柜 IP 来碰运气。

### 已取得 IP 后，检查主机路由

从本机 YAML 或现场示教器取得实际控制柜地址，以下变量须替换为已确认值：

```bash
ROBOT_IP=192.168.71.50  # 本轮已由现场人员设置并验证；其他现场须先核对
ip -brief address
ip route
printf '%s\n' "${SSH_CONNECTION:-local-session}"
ip route get "$ROBOT_IP"
ping -c 3 -W 1 "$ROBOT_IP"
ip neigh show
./scripts/setup_jaka_lan2_route.sh --help
```

路由必须指向机器人专用接口及其源地址。SSH 管理流量若走另一接口，不要修改那条路径。
已有正确地址和路由时不运行网络配置脚本。ping 无响应本身不能断言控制柜故障；结合链路、ARP、
控制柜所接端口和示教器显示的 IP 检查。

### 本轮直连 LAN2 的实际配置步骤

本机机器人专用接口为 `enP2p1s0`、地址 `192.168.71.19/24`，SSH 管理走
`wlP1p1s0` 的 `10.24.1.68`。先前 ping/ARP 和 SDK 登录失败的原因是 LAN2 使用自动 IP，
而直连链路没有 DHCP 服务。解决时保留了 Thor 的已有地址、路由和 Wi-Fi 管理连接：

1. 现场人员确认网线接在 **LAN2**，并在网络设置页确认它此前为自动获取 IP。
2. 在机械臂未上电、未使能状态，现场人员将这个端口改为静态地址：`192.168.71.50`，掩码 `255.255.255.0`。
3. 本次界面不允许网关为空或首位为 0，因此填写同子网的 `192.168.71.1` 作为占位值。
   现场没有这个路由器；Thor 与控制柜的同子网通信不经过网关。**这不是通用网关推荐，也不提供外网访问。**
   有实际路由器的现场应按网络管理员提供的值填写，界面允许为空时不需伪造网关。
4. 现场保存后等待网络配置生效，再从 Thor 检查 `ip route get 192.168.71.50`、ping 与邻居信息。
5. 将本地 YAML 的 `runtime.robot_ip` 设为 `192.168.71.50`、`runtime.edg_state_ip` 设为 `192.168.71.19`，
   然后执行下节的有界只读诊断。此后 5 秒内完成 50 个周期、全部 API 返回 0。

此流程不自动修改控制柜或主机网络。IP、端口和网关输入约束来自本次现场确认，其他型号/版本须重新核对。

## 3. 运行已构建的只读诊断器

先完成[构建与动态链接检查](../setup/INSTALLATION.md#4-构建-jaka-native-组件)，再执行：

```bash
mkdir -p outputs/onboarding
build/jaka_readonly_diagnostic/jaka_readonly_diagnostic \
  --mode connected --robot-ip "$ROBOT_IP" \
  --duration-s 5 --poll-hz 10 --slow-poll-hz 1 \
  --metrics-file outputs/onboarding/jaka-readonly.json \
  --sample-stream-file outputs/onboarding/jaka-readonly.jsonl
```

这是显式设备连接；默认 `dry-run`、`fake` 和 `--help` 都不连接。检查退出码和 JSON 中每项调用的返回码，
不能仅以文件存在判为成功。登录失败时没有状态读数，所有 unavailable 值都不能解释成“零”或“正常”。

核对 SDK 版本、关节（rad）、TCP 与工具/用户坐标系（mm、RPY rad）、工具/用户 ID、程序状态、
上电/使能、servo、急停、碰撞与故障信息。扩展只读项还包括负载/质心、安装角、TIO 电压和管脚功能、
两路 RS485 模式及通信参数；控制器不支持的接口须保留原始错误码，不写配置来使其通过。
机器人铭牌、控制器固件和 TIO 固件若没有可靠读取接口，仍需现场记录，不能从 SDK version 推断。

本轮只读连接显示机械臂未上电、未使能、无告警。另将 8 组输入关节值交给 SDK `kine_forward` 纯计算接口，
与 MJCF 法兰 FK 比较，最大位置差 `0.000871 mm`、旋转差 `0.000298°`（工具与用户坐标 ID 均为 0）。
这支持当前法兰运动学计算的一致性，**没有移动机械臂，不证明物理零位、关节限位、DH TCP、负载或碰撞几何已标定**。
完整现场结果与剩余核验见[部署记录](../setup/DEVICE_STATUS.md)。

## 4. 按现场 1.7.2 版本核对示教器与 SDK

本机优先参考 [JAKA 1.7.2 C++ SDK 文档](https://www.jaka.com/docs/legacy172/guide/1.7.2/SDK/Cpp.html)
及 [1.7.2 大寰夹爪插件说明](https://www.jaka.com/docs/legacy172/guide/1.7.2/dh/index.html)。
Coboπ `cobo/330` 属于不同文档分支，不能当成本机已验证菜单。

| 要核对的项目 | 现场读取与核对方式 |
| --- | --- |
| 控制柜通信地址 | 在本机 App 网络设置核对实际 LAN2 的地址/掩码/自动或固定方式；本次修改步骤见上节 |
| 软件版本 | 记录本机 App 版本页显示的控制器、PSCB、Servo、TIO；下电时的零值保留为未核实 |
| 工具/用户坐标系 | 将当前工具/用户 ID、平移和旋转与 SDK 只读结果对照；不能把默认零 TCP 当成 DH TCP |
| 负载与安装角 | 将 App 中质量、法兰坐标下质心与安装角和 SDK 结果核对；电爪、转接件和线缆均需计入 |
| DH/TIO 通信 | 按匹配版本的插件说明及 [DH 专项文档](DH_TIO.md)核对；先读取，不改供电/通道 |

官方 1.7.2 插件文档确实给出了 `App → 设置 → 系统设置 → 附加程序` 的安装入口，
并区分 TIO 与控制柜 RS485 路径；这不证明现场已经安装该插件，也不要求为了本项目另行安装。
不要同时运行插件、示教器调试和本机 SDK 电爪控制，以免争用同一 TIO。

TCP 标定和负载自动辨识可能产生运动，不属于只读检查。网络配置由现场人员另行完成；
软件不会自动写入 TCP、负载、安装、碰撞、安全或 TIO 电压设置。

## 5. 进入遥操作前

确认末端安装牢固、TCP/负载/碰撞几何匹配实际 DH、工作空间清空、急停可用、现场人员能停止动作，
并明确本次有界时长。先完成 Quest 仅输入验证及同配置仿真，再查看维护入口的参数：

```bash
./scripts/run_quest_jaka_bounded_teleop.sh --help
./scripts/run_quest_jaka_rh56_teleop.sh --help
./scripts/run_quest_rh56_hand_test.sh --help
```

当前没有 RH56 时，不启动联合 RH56 入口或复用其串口配置。DH 通过 JAKA TIO，不能靠修改 `rh56_device`
得到 DH 控制。DH 的接线、通信模式与受控命令见 [DH/TIO 专项说明](DH_TIO.md)。
输入、目标、实际状态和停止原因须保留在日志；不把 simulation/fake 判定写成 physical PASS。

碰撞、控制器告警、急停、SDK/传输错误、watchdog/liveness 失效、非法命令或硬限位、末端协议故障、
退出清理不确定都要求停止。候选目标不可行时只拒绝新目标并保持安全目标；这不允许绕过硬停止或放宽限位。

## English

The user confirmed a Mini2 arm (`MC21200647`) and MiniCab (`CABm11007100`), App 1.7.2.25 and controller 1.7.2_49_X64_minicab.
The controller meets the bundled SDK 2.2.7 minimum version. PSCB is 03_18PR; the zero Servo/TIO displays while unpowered do not establish valid firmware versions.
Check joint conventions, link dimensions, limits and stationary FK/TCP agreement. Replacing RH56 with DH also requires current TCP, payload and collision geometry.

Preserve the management route. Use `ip route get` and neighbor information with the actual pendant-confirmed controller IP.
LAN2 initially used automatic addressing on a direct link without DHCP. The operator configured `192.168.71.50/24`; the existing Thor interface and SSH route were preserved.
The interface required a nonempty gateway, so `192.168.71.1` was used only as a same-subnet placeholder, not an actual router.
The subsequent 5-second read-only check completed 50 cycles with zero API errors. The arm remained unpowered and disabled, without alarms.
Eight computed SDK/MJCF flange poses agreed within 0.000871 mm and 0.000298 degrees; no physical motion or DH tool calibration was performed.

Build and link-check the diagnostic first, then explicitly select `--mode connected` using the bounded command above.
Read individual return codes and availability flags. The diagnostic does not power on, enable, move, clear alarms or write tool/TIO settings.
Unsupported fields remain unavailable; SDK version does not establish controller or TIO firmware.

Use the matching [official JAKA 1.7.2 SDK documentation](https://www.jaka.com/docs/legacy172/guide/1.7.2/SDK/Cpp.html) and [DH plugin guide](https://www.jaka.com/docs/legacy172/guide/1.7.2/dh/index.html).
Do not substitute Coboπ 3.x menus or trigger calibration/payload-identification motion during read-only bring-up.
Proceed to [teleoperation](TELEOPERATION.md) only after the operator prerequisites and [safety procedure](../safety/REAL_HARDWARE_SAFETY.md) are satisfied.
