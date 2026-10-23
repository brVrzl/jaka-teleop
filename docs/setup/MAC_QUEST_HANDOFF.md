# Mac → Quest 右 Touch 交接

[Thor设备状态](DEVICE_STATUS.md) · [发送端补丁与唯一构建说明](../../quest_sender/README.md) · [主机协议/验收](../motion_input/RIGHT_TOUCH.md)

**Mac负责USB调试、核对现装应用、构建及安装新发送端。Thor继续负责输入接收、仿真和设备诊断。**
Quest通过Wi-Fi向Thor发送，不必占用Thor的USB口。本轮在Thor端遇到设备模式USB口，
且用户没有空闲host口，所以改由Mac连接Quest；无需改Thor的USB模式或拔掉D435。

## 当前已知条件

- 主仓库工作分支：`work/thor-onboarding-quest-dh`，不合并main。
- Thor输入地址：`10.24.1.68:9000/UDP`；当前Quest来源IP：`10.24.0.3`。网络变化后重新核对。
- 现装应用能够发送HTS/CTRL，但已捕获的501条CTRL全部控制器未跟踪，尚无RTOUCH。
- 候选发送端：`brVrzl/hand-tracking-streamer` 的 `feature/mixed-input-log-probe`，固定commit
  `5b8eac7e30ce12481b89b123099693bc658bc578`。不能仅凭报文相似就断言它是已装APK来源。
- 新协议、主机安全回归及合成replay已通过；发送端补丁仅通过应用检查，**尚未经Unity编译或安装**。
- 本交接只验收输入/发送端，不授权JAKA或DH动作。主机右Touch物理输出当前明确关闭。

## 1. 先核对现装应用，不卸载

Mac已有adb则直接使用。否则可使用[Google官方Platform Tools](https://developer.android.com/tools/releases/platform-tools)，
或已有Homebrew时安装[对应cask](https://formulae.brew.sh/cask/android-platform-tools)：

```bash
brew install --cask android-platform-tools
adb version
adb devices -l
adb shell pm list packages -3
```

Quest用数据线连接Mac，保持唤醒，在头显内允许USB调试。`unauthorized`需要头显确认；
列表空则检查数据线/USB连接，不是去修改机器人网络。若Mac连接多个Android设备，每条命令加`-s SERIAL`。

从包列表确认实际应用，先检查候选包（不存在时使用真实包名）：

```bash
adb shell dumpsys package com.brvrzl.handtrackingstreamer.mixedprobe
adb shell pm path com.brvrzl.handtrackingstreamer.mixedprobe
adb shell cmd package get-install-source com.brvrzl.handtrackingstreamer.mixedprobe
```

保留包名、`versionName`、`versionCode`、安装来源结果；安装来源若系统不支持查询则明确记录，不猜。
不要把完整设备日志/凭据上传Git。旧应用保留，用于对照。

## 2. 拉取本轮成果并按固定源码构建

在Mac自己的新目录中执行；若已有checkout，先检查分支/远端/工作区，不覆盖已有修改：

```bash
mkdir -p ~/projects
cd ~/projects
git clone --branch work/thor-onboarding-quest-dh \
  https://github.com/brVrzl/embodied-hand-lab.git embodied-hand-lab-thor
cd embodied-hand-lab-thor
```

然后完整执行[发送端README](../../quest_sender/README.md)的固定源码获取、`git apply --check`、
EditMode测试和Android构建步骤。这里不另维护第二套构建参数。

需要Unity **6000.0.65f1**及Android Build Support、SDK/NDK/OpenJDK；用Unity Hub安装对应版本和模块，
完成Editor自身授权。常见Mac Editor路径是：

```bash
export UNITY_EDITOR="/Applications/Unity/Hub/Editor/6000.0.65f1/Unity.app/Contents/MacOS/Unity"
test -x "$UNITY_EDITOR"
```

路径不存在就从Unity Hub确认实际路径，不改成一个“接近”的Editor版本。
不搬旧用户的Library缓存、不升级Meta/OpenXR依赖来掩盖编译问题。保存真正的EditMode和build日志，
编译失败就修补丁并重新验证；不要创建空APK或仅凭host tests宣布应用通过。

## 3. 安装独立包、填主机地址

构建成功后安装新APK（路径以实际构建输出为准）：

```bash
adb install -r /absolute/path/to/hand_tracking_streamer/build/right_touch_v1.apk
adb shell monkey -p com.brvrzl.handtrackingstreamer.righttouch -c android.intent.category.LAUNCHER 1
adb shell dumpsys package com.brvrzl.handtrackingstreamer.righttouch
```

新包名`com.brvrzl.handtrackingstreamer.righttouch`与旧包不同。菜单设置：UDP、
IP `10.24.1.68`、端口`9000`、Hand mode **Right Touch (RTOUCH v1)**，然后Start Streaming。
Quest要与Thor网络互通；Mac只负责安装，不是UDP目标。若无法点菜单，记录现象并修现有菜单交互，
不要伪造tracking=true。右B停止并返回菜单；Grip释放只暂停主机接管。

## 4. 与Thor联合验收输入

通知Thor操作者“新APK已安装并准备发送”。Thor上先执行纯输入gate（不打开任何执行器）：

```bash
cd ~/projects/embodied-hand-lab
source ~/.venvs/embodied-hand-lab/bin/activate
python tools/quest_controller_transport_gate.py --input-mode right-touch-v1 \
  --bind 10.24.1.68 --port 9000 --project-ip 10.24.1.68 \
  --allowed-sender 10.24.0.3 --duration-sec 60 --required-data-timeout-sec 45
```

检查真实right-controller/head有效、位姿变化、Grip/Trigger、session/sequence，且有`valid_pose_packets`。
释放再按Grip才能接管；松开暂停；遮挡/断流/切回应用后一直握住Grip不能自动恢复。
右B应停止发流，原HTS/RH56模式仍能选回。坐标与仿真验收按[RIGHT_TOUCH](../motion_input/RIGHT_TOUCH.md)，
不直接启动真机遥操作。

## 回传给Thor的交付物

- Mac架构、实际Unity/Android模块版本；源码commit与补丁应用状态。
- 旧/新包名、版本号、安装来源（能查到的部分）。
- 真正的EditMode结果、build日志与APK本地路径；共享APK时使用明确文件链接，不提交大型APK到主仓库。
- Quest头显菜单、有效追踪/按键、暂停/重接管、B停止的实测结果。
- 若修补发送端，回传补丁diff；先保留工作分支，不合并main。

给Mac端协作Agent的任务可以直接表述为：

> 请读取这份交接和仓库AGENTS.md，在当前Mac实际完成步骤1–3，修复并验证固定发送端补丁，
> 保留旧APK；与Thor协调步骤4输入验收。不得控制机器人或电爪，不得将未编译源码、合成数据或TX计数
> 写成Quest端到端通过。源码/构建/安装受阻时给出具体错误和已完成产物，不只输出计划。
