# XRobo PC Service 部署与恢复

本页是 Thor 上 XRobo 通信的维护入口。只启动官方通信服务和现有只读观察器，
不启动 JAKA 执行器、RobotDemo 或电爪。原生数据的 tracking/连续性限制见
[输入契约](../motion_input/XROBO_NATIVE.md)，仿真见[Simulation](../simulation/SIMULATION.md#xrobo-native--dh-proxy)。

## 四个层次与端口

| 层次 | 实际职责 | 是否需要长期运行 |
| --- | --- | --- |
| Quest Connect | Quest → `RoboticsServiceProcess` 的 TCP **63901**；手填 IP 直接连接 | 使用 XRobo 时 PC Service 必须运行 |
| 控制器传输 | 同一 TCP 连接承载 Tracking JSON；Quest 必须开启 Controller、Head、Send，右手柄须唤醒 | 需要数据时开启 Send |
| Thor 输入/转换 | SDK 经本机 **127.0.0.1:60061 TCP/gRPC** 接收 PC Service 回调；已有 `XRoboNativeReceiver` 供观察器/仿真复用 | 观察或仿真时运行一个所需接收器 |
| JAKA 执行 | 独立的真机入口、安全门控与 AcceptedArmTarget 消费端 | 通信检查不需要，本流程不启动 |

Quest 的 **Network → PC Service** 填 Thor 的 **10.24.1.68**，不是机器人地址。
此版本无须填端口；若界面要求端口，使用 TCP **63901**。开启 Head、Controller、Send，关闭 Hand。
`10.24.1.68/16` 在 `wlP1p1s0`；`192.168.71.19/24` 属于 `enP2p1s0`，
只有该接口仍有此地址且 Quest 可路由到它时才可使用。每次以 `ip -brief address` 为准。

当前 PC Service 的发现广播是 **Thor → UDP 29888**，约每 5 秒一次，源端口动态分配；
Thor 不需要监听 UDP 29888。旧交接记录中的 50087 不是本部署的端口。
手填 IP 的 Connect 不依赖发现广播。UDP **9000** 属于 HTS/RTOUCH/Trossen 接收器，
9001 ACK 属于 Trossen；9000 无监听不能诊断 XRobo。

源码核对依据：[Quest TcpHandler](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client-Quest/blob/05ad3f081e64c400d8eda34c0efdf711c47f6b3a/Assets/Scripts/Network/TcpHandler.cs)、
[PC TCP worker](https://github.com/XR-Robotics/XRoboToolkit-PC-Service/blob/6386009475369615fa984bca0a6e9902cd81eb2a/RoboticsService/DeviceConnectionManager/Manage/TCPConnectionManage/tcpserverworker.cpp)、
[协议常量与封包](https://github.com/XR-Robotics/XRoboToolkit-PC-Service/blob/6386009475369615fa984bca0a6e9902cd81eb2a/RoboticsService/DeviceConnectionManager/Manage/Manage_global.h)。
Connect 首先建立 TCP，客户端随后发送 `0x19`（`SN|-1`）与 `0x6c` 版本消息，
以 `0x23` 心跳维持连接。封包为 `0x3f + cmd + uint32长度 + payload + uint64时间戳 + 0xa5`（小端）。
Quest 的 WORKING/连接完成状态基于 socket 建立及版本消息发送，不是 UDP ACK，
也不能证明 Controller 数据已到达。Tracking JSON 由 PC Service 转发给 SDK 回调。
正常局域网通信无需外部互联网、登录云服务或修改 RTC/WAN 配置；首次准备安装包和依赖另计。

## 已有安装与新设备部署

Thor 使用官方 **headless arm64 PC Service v1.0.0** 的用户目录解包副本：

```text
~/.cache/embodied-hand-lab-xrobo/unpacked/opt/apps/roboticsservice/
  RoboticsServiceProcess
  setting.ini
  SDK/arm64/libPXREARobotSDK.so
~/.cache/embodied-hand-lab-xrobo/icu70/usr/lib/aarch64-linux-gnu/
```

`/opt/apps/roboticsservice/runService.sh` 不存在于当前系统安装路径。
解包目录内虽有官方 `runService.sh`，但它直接后台启动且没有补入本机所需 ICU70 路径。
本仓库脚本使用相同二进制、工作目录、Qt 插件和 SDK 库，仅补充局部 ICU 路径与进程管理，
不系统安装旧 ICU、不更改全局动态库路径。不要同时运行官方后台脚本与本服务。

新设备先从[官方发布页](https://github.com/XR-Robotics/XRoboToolkit-PC-Service/releases/tag/v1.0.0)
取得对应架构的包；Thor 对应 `XRoboToolkit-PC-Service-headless_1.0.0.0_arm64.deb`。
离线传入经核验的官方包及其依赖，使用
`dpkg-deb -x /path/to/official-arm64.deb /path/to/unpacked` 解包。
保留完整 `lib/`、`plugins/`、`SDK/`、`setting.ini`，不要只复制可执行文件。
在需要 ICU70 的系统上，同样局部解包对应架构的 Ubuntu libicu70 官方包；
已有安装可直接复用。配置示例针对 Thor aarch64；其他架构应先核对 SDK 目录和依赖，不能直接套用。
本脚本使用 bash、systemd 用户管理器、iproute2、procps、ldd 和基础文本工具，无需 tcpdump。

### 注册用户服务（不会启用开机自启）

在实际运行服务的账户下，从仓库根目录执行。不要跨账户启动第二个副本。

```bash
mkdir -p ~/.config/jaka-teleop ~/.config/systemd/user
# 已有配置时保留它；首次复制后编辑三个绝对路径，不能用 ~ 或 $HOME。
test -e ~/.config/jaka-teleop/xrobo-pc.env || \
  cp configs/xrobo-pc.env.example ~/.config/jaka-teleop/xrobo-pc.env
# XROBO_REPO 指向当前仓库；另外两项指向服务和 ICU 目录。
${EDITOR:-nano} ~/.config/jaka-teleop/xrobo-pc.env
ln -s "$(pwd)/configs/systemd/xrobo-pc.service" ~/.config/systemd/user/xrobo-pc.service
systemctl --user daemon-reload
bash scripts/xrobo_pc_service.sh start
```

若 symlink 已存在，核对 `readlink -f ~/.config/systemd/user/xrobo-pc.service`，正确则跳过 `ln`。
配置文件是本机可信的 `KEY=value` 路径配置，脚本会读取它；不要放令牌或密码，不提交本机配置。
服务 unit 与仓库保持链接，移动仓库后需更新链接和 `XROBO_REPO`。

## 日常检查、启动、停止

从仓库根目录执行：

```bash
bash scripts/xrobo_pc_service.sh status
bash scripts/xrobo_pc_service.sh start
bash scripts/xrobo_pc_service.sh logs
bash scripts/xrobo_pc_service.sh stop
```

`status` 一条命令检查部署路径、缺失动态库、必要配置、服务状态、相关进程、端口、网卡和路由。
两个 TCP 端口必须由本 unit 的 MainPID 持有；不就绪返回非零。
`start` 可重复执行，正常运行时保留同一 PID；存在未托管的 PC Service 或端口冲突时拒绝另开实例。
启动失败保留 systemd 日志并返回非零，端口在 5 秒内未就绪也报错，不静默重试或切换协议。
`stop` 仅停止本 unit；发现其他账户/手工实例会报告，不批量 kill。

`run` 子命令以前台 `exec` 方式运行同一二进制，可用于不用 systemd 的交互诊断：
先确认托管服务已停止，再 `bash scripts/xrobo_pc_service.sh run`，Ctrl-C 停止。
它同样检查重复进程、依赖和端口；其状态不算 systemd 托管就绪。

日志分两处：

- 启动、动态库、退出错误：`journalctl --user -u xrobo-pc.service -n 60 --no-pager`。
- 上游 Qt 通信日志：`~/.local/share/PICOBusinessSuitData/log/YYYYMMDD.txt`
  （设置 XDG_DATA_HOME 时在对应目录）。例如
  `tail -n 60 ~/.local/share/PICOBusinessSuitData/log/$(date +%Y%m%d).txt`。
  `setting.ini` 的 `[Log] logToFile=1` 控制文件输出；不要直接贴出含身份或令牌的完整配置。

### Thor 重启后

登录同一账户，进入仓库，先 `status`，再 `start`；随后在 Quest 重新 Connect 并开启 Send。
观察器/仿真不会自动恢复，按任务需要单独启动，不自动恢复机器人执行会话。

本次只注册并启动用户服务，**未 enable，未开启 linger**，也不设置崩溃自动重启。
确认部署稳定后，可由操作者自行选择 `systemctl --user enable xrobo-pc.service`，
这会在用户管理器启动时拉起通信服务；通常需要该账户登录。
无人登录也要开机运行时才另行评估 `loginctl enable-linger "$USER"`（可能需要管理员），
不要把注册用户 unit 误认为已经具备无人登录的开机恢复。
撤销可选自启用 `systemctl --user disable xrobo-pc.service`。

## 证明控制器帧到达（只读）

先确保没有其他本轮观察器在写同一文件，为每轮使用新目录：

```bash
capture_dir=$(mktemp -d /tmp/xrobo-input.XXXXXX)
PYTHONPATH=src ~/.venvs/embodied-hand-lab/bin/python -u tools/xrobo_input_observer.py \
  --sdk "$HOME/.cache/embodied-hand-lab-xrobo/unpacked/opt/apps/roboticsservice/SDK/arm64/libPXREARobotSDK.so" \
  --log "$capture_dir/raw.jsonl" --duration 60 | tee "$capture_dir/status.log"
```

其他设备把 Python 换成自己的已安装项目环境，SDK 路径换成配置中的实际位置。
观察器调用既有 PXREAInit/Deinit 与回调，不发送设备控制或机器人命令。
原始记录以独占创建方式打开，已有文件会报错，不覆盖历史数据。
`sdk_event=4` 只证明本机 SDK 连上 PC Service；`16` 是设备发现；
**`33554432` 且 raw_payload.functionName=Tracking** 才是应用状态数据。
终端应出现 `status=receiving`、递增的 `local_callback_sequence`、约 90 Hz 的回调和新鲜 age。
分别移动右手、按 Grip/Trigger，核对 `current_frame.right_controller` 的 pose/grip/trigger 确实变化。
关闭 Send 后应变为 stale、`current_frame=null`，重新开启应恢复新帧。
本地序号不是 Quest 源序号；持续回调不等于控制器有效追踪，原生缺失字段及真机禁用边界仍保持。

## Connect 失败按层排查

1. **无进程/端口**：先 `status`/`start`，看两个日志位置。缺库用 status 的 ldd 输出定位，
   不靠重装系统依赖。重复实例查看进程的账户和原启动方式，先由原会话正常停止。
2. **服务存活但无 TCP 63901**：查上游 `tcp server listen failed`、端口冲突、
   实际 `setting.ini` 的 `[TCP] TcpBindPort`。当前维护脚本检查默认 63901/60061，
   自定义端口需先核对客户端与部署配置；不要反复 restart。
3. **Quest 无法 Connect**：核对 Quest 所在 WLAN 和 Thor 当前 IPv4；执行
   `ip route get <Quest当前IP>`、`ping -c 3 <Quest当前IP>`、
   `ss -ntp '( sport = :63901 )'`。ping 只证明 IP 可达，不能证明 TCP 可达。
   `*:63901` 是所有本地地址监听，60061 只绑定 loopback 是正常的。
   没有 Quest ESTAB 时检查 AP 客户端隔离、路由及防火墙，而非 SDK 或 JAKA。
   防火墙只读检查可能需管理员：`sudo nft list ruleset`；无权限就标明未核查，不能声称已放行。
   不直接关闭防火墙或改路由。发现广播失败时可先手填 IP，不要求外网恢复。
4. **TCP 已连而无帧**：检查 Quest Head/Controller/Send、前台焦点和手柄唤醒。
   SDK 端检查 60061、实际 SDK 库路径和观察器日志。现有接收器已为 localhost 设置
   `no_grpc_proxy`，勿让本机 gRPC 经过 HTTP 代理。没有 Tracking 不能声称数据恢复。
5. **有帧但手柄不变/全零**：核对右手柄连接、活动状态和应用选择，按键与姿态需实际变化。
   不把缓存位姿、Head 变化、SDK TestDevice 标签或回调频率当作右手有效追踪证明。

上游偶尔报告 `/tmp/RoboticsServiceProcess_Single_Name` 的 local-server 错误：
先核对跨账户进程和 TCP/SDK 实际状态。历史其他账户残留 socket 可能不可删除，
它本身不证明 TCP 失败；不要删除别人的锁/socket，也不要因此修改运动安全检查。
