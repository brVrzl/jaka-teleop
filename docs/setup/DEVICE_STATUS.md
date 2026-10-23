# Thor 新用户部署与设备验证状态

这是 2026-10-23 在当前 `user01` 环境实际执行的记录。离线、计算查询、相机采集与执行器动作分开描述。
[安装](INSTALLATION.md) · [JAKA 首次连接](../operation/REAL_ROBOT.md) · [右 Touch](../motion_input/RIGHT_TOUCH.md) · [DH/TIO](../operation/DH_TIO.md)

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

下一步依次完成：版本和线缆核对 → 可验证DH读回 → Quest新协议APK构建安装及真实右Touch输入 →
新工具TCP/负载/碰撞几何 → 操作者准备后的有限夹爪动作与低速短程机械臂试验 → 联合拾放与独立7维episode验收。
当前准备工作不构成执行器动作授权。

Quest 的 Mac USB 调试、构建与安装见[Mac 交接清单](MAC_QUEST_HANDOFF.md)。
