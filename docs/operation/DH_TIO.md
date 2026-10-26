# DH 平行电爪：JAKA TIO 接入与验收边界

本轮接线目标是 **Thor → JAKA 控制器／SDK → 末端 TIO → DH**。
RH56 的 CH341、串口和六自由度手指配置不适用。操作者按现场铭牌报告型号为
**PGE-50-26-O-S-M1**（不是 PGE-5-26）；本地配置保留完整型号及序列号。
线缆针脚、供电、TIO 版本及通信条件仍须核实，确认开关保持关闭。

目前提供离线报文校验、TIO 只读配置盘点、控制器缓存信号读取和显式单次命令接口。
**尚未通过现场通信或动作验收，也未开放右 Touch 联合真机控制。**

## 先核实，再接通

使用与现场版本对应的资料：

- [DH PGE 官方产品页](https://www.dh-robotics.com/product/pge)分别列出驱控一体和驱动外置手册，不能混用。
- [PGE 驱控一体操作手册 3.2（250701）](https://www.dh-robotics.com/wp-content/uploads/2022/12/PGE%E7%B3%BB%E5%88%97%E9%A9%B1%E6%8E%A7%E4%B8%80%E4%BD%93%E5%BC%8F-%E4%BA%A7%E5%93%81%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8C_3.2-250701.pdf)：第 2.2、2.3 节是本实现协议依据。
- [JAKA Coboπ 330 设置参考](https://www.jaka.com/docs/cobo/330/guide/9.Settings.html)：末端 I/O 章节仅适用于 V3 TIO，现场版本未知时不能直接照菜单操作。
- [JAKA SDK 官方 C++ 参考](https://www.jaka.com/docs/documents/SDK/Cpp.html)：与仓库 `third_party/jaka_sdk/v2.2.7/linux/c_cpp/inc_of_c/` 头文件一起核对。绑定严格使用 **2.2.7 本地 C ABI**；新在线 C 文档的函数签名可能已经变化。

现场集中核对清单：

1. 拍摄 DH 铭牌完整型号、序列号、驱动形式和线缆标签；确认是否存在外置驱动盒。
2. 用两端对应硬件手册核对航插每一针及线缆转接关系。插头能插入不代表针脚匹配，线标缺失时向厂家确认，不能试电压猜线序。
3. 在示教软件版本／系统信息页记录机器人本体、控制柜、控制器固件、TIO 硬件及固件版本；核对软件版本对应手册。
4. 记录当前电源输出、引脚复用、RS485 通道、模式、从站地址、波特率、数据位、停止位和校验位，确认现有作业、插件和其他主机没有占用工具总线。
5. 由现有只读诊断器读取 TCP、负载、安装姿态、机器人 DH 运动学参数和 TIO 配置；读失败原样保留返回码，不代表某个默认值。对照实际夹爪、转接件、指尖重量及几何，重新核对运动工具配置。
6. 若必须改配置，先保存现状，再逐项提出目标值及手册依据，由现场操作员按已核对版本执行。程序不会自动改供电、引脚、通道、参数或升级固件。

`hardware_confirmed` 只能在以上条件核对完毕后设为 `true`。这只是操作者确认记录，
不会把未知硬件变成已支持硬件；运行时仍读回并比对供电、引脚、Modbus 模式及通信参数。

## 协议与当前能力

本适配仅接受完整型号 **PGE-50-26-O-S-M1**，其他型号必须先核对。
上述驱控一体 3.2 手册第 01 页明确包含 PGE-50-26（50 N、26 mm），不是 5 N 型号。
[DH 官方选型手册（20220624）第 31 页](https://www.dh-robotics.com/wp-content/uploads/2022/06/%E5%A4%A7%E5%AF%B0%E7%94%B5%E5%8A%A8%E5%A4%B9%E7%88%AA%E9%80%89%E5%9E%8B%E6%89%8B%E5%86%8C%E6%96%B0%E7%89%8820220624.pdf)
对应选型码：`O` 不带抱闸、`S` 侧出线、`M1` 为 Modbus RS485＋I/O(NN)。
这不证明现场线缆正确，也不证明机器人 TIO 已设置好；不带抱闸不能作为断电保持方案。
诊断器的 `kinematic_dh_parameters_sdk_raw` 是 Denavit–Hartenberg 运动学参数，
与 DH-Robotics 电爪无关；先核对单位和参数约定再比较模型，程序不自动替换运动学。
下表是协议数值，不是现场配置或默认执行动作：

| 功能 | 保持寄存器地址 | 数值 |
| --- | --- | --- |
| 单向初始化 | `0x0100`（256） | 写 `1`；会寻找限位，属于机械动作 |
| 力参数 | `0x0101`（257） | 20–100，设备百分比，不是牛顿反馈 |
| 目标位置 | `0x0103`（259） | 0–1000，设备归一化刻度，不是毫米 |
| 速度参数 | `0x0104`（260） | 1–100，设备百分比 |
| 初始化状态 | `0x0200`（512） | 0 未初始化，1 已初始化，2 正在初始化 |
| 夹持状态 | `0x0201`（513） | 0 运动，1 到位，2 夹住，3 掉落 |
| 实际位置寄存器 | `0x0202`（514） | 0–1000 |

不开放全行程重标定、Flash 保存、自动初始化设置或未知寄存器。没有杜撰故障寄存器、
制动或“立即停止”命令。开合方向必须现场用已授权有限动作核对后再映射 Trigger，
不能仅由初始化方向寄存器推断。

写命令为二进制 `[从站, 06, 地址高字节, 地址低字节, 数值高字节, 数值低字节]`。
例如位置 500 的离线报文为 `01 06 01 03 01 F4`。在 JAKA 的 **Modbus RTU**
即时指令路径中由控制器添加 CRC，不传 ASCII 十六进制文本，不二次添加 CRC。
SDK 通道索引 `0` 对应界面通道 1／RS485H，`1` 对应通道 2／RS485L。
`framing_confirmed` 需要现场固件支持依据；不能把此格式套到 Raw RS485 透传模式。

### 实际反馈的限制

SDK 2.2.7 的 `get_rs485_signal_info` 中 `array_len` 同时是输入缓冲容量和输出总数；
调用前必须设置为实际数组容量（这里为 256）。传入 0 只得到数量，不会拷贝记录，
不能将预先清零的数组当作设备信号。实现同时拒绝越界数量和空信号名。

该接口返回已定义信号量的**控制器缓存**，并未提供设备采样时间、
每次总线读取结果或缓存新鲜度。主机查询时间不能代替设备采样时间。
因此输出始终注明 `freshness_verified: false`，`action_completed: null`。
即使寄存器看起来已到位、SDK 返回 0，也不能独自作为实物动作完成证据。

官方文档说明信号刷新是异步操作；当前 `status` 不自动添加、修改或刷新信号。
必须先核对现有信号定义及刷新策略，避免覆盖别的工具。若现场固件不能给出可验证的
新鲜反馈，需要厂家提供对应能力／确认方法；在此之前，联合遥操作和包含实际反馈的
episode 验收保持阻塞。**不会把缓存零值写成真实夹爪状态，也不会自动 seed 右 Touch 目标。**

## 新用户配置与命令

机器配置与其他设备共用 `configs/local/thor.yaml`，从
[`thor.example.yaml`](../../configs/data_collection/thor.example.yaml) 复制。
填写 `runtime.robot_ip` 与 `dh_gripper` 节；未知项保留空值，检查会准确列出缺项。
参考手册的通信默认值不能代替现场读取值。

```bash
embodied-lab gripper --help
# 已填写配置后，默认只检查参数和生成报文，不加载SDK或连接硬件：
embodied-lab gripper status --config configs/local/thor.yaml
embodied-lab gripper position --value 500 --config configs/local/thor.yaml
# 只有现场通信条件核对完成后，显式读取控制器缓存：
embodied-lab gripper status --config configs/local/thor.yaml --connect
```

信号名称可以修改，但预定义信号必须分别指向本通道的 FC03 地址 512、513、514。
程序不替你创建信号、不自动改变刷新率。当前适配要求 8 数据位、1 停止位；若现场不同，
先核实依据并扩展适配，不能自动改现场值。

以下是**需要现场动作授权后**才可运行的入口，不属于安装／doctor／只读探测：

```bash
embodied-lab gripper initialize --config configs/local/thor.yaml --connect --authorize-motion
embodied-lab gripper speed --value 10 --config configs/local/thor.yaml --connect --authorize-motion
embodied-lab gripper force --value "$APPROVED_FORCE_PERCENT" --config configs/local/thor.yaml --connect --authorize-motion
embodied-lab gripper position --value 500 --config configs/local/thor.yaml --connect --authorize-motion
```

每次只提交一个命令，不自动循环开合。`APPROVED_FORCE_PERCENT` 需填写已批准的力参数；
协议下限 20% 不是默认安全力值。上面数值仅展示参数语法，实际范围、速度、力值及
初始化方向须在现场确认。首次有限动作应清空夹持区，操作者可随时停机；先观察真实反馈
和实物，再决定下一步。CLI 只报告提交结果，不报告动作完成。

## 所有权、超时与停止

`JakaTio` 持有按机器人 IP 区分的进程锁，并限定在创建它的线程中调用；
本机第二个适配器无法同时占有它。该锁不能阻止示教器、插件或其他机器占用总线，
必须完成现场独占确认。TIO 调用不得进入机械臂实时伺服线程。

所有写入最多 4 Hz，超频直接拒绝、不排队、不重试。SDK 错误（包括超时 `-61`）锁存写入故障，
须退出并排查后重新建立所有者。SDK 调用自身仍可能阻塞，目前没有验证有界的传输截止时间，
因此本实现是 commissioning 接口，不是已验收的实时 worker。

Grip 释放、断流、跟踪失效、重连及进程退出不能发送“松爪”命令。右 Touch 输入模块保持
最后目标、重新接管须重新捕获参考；本接口退出只注销连接，不写位置或供电。
**停止更新不保证正在执行的夹爪动作立即停止，也不保证断电仍能保持物体。**
机械停止和负载保持方式必须按实际设备能力及现场停机流程处理。

## 验收顺序与数据

完成现场识别与通信读回 → 验证真实反馈新鲜度 → 授权单向初始化和有限开合 →
在新 TCP／负载／碰撞几何下低速短程机械臂验证 → 右 Touch 联合遥操作 → 拾放与短 episode。
当前尚无 DH 真机演示视频或已验收 episode。

新数据必须独立于历史 RH56 的 12-D 契约。关节目标路径可定义 6 个机械臂关节（rad）与
1 个夹爪目标（设备归一化刻度）；实际关节、实际夹爪位置、缓存可用性／新鲜度、命令和
测量时间分别保存。这里的缓存查询结果不可充当已验证实际反馈；不得补零伪装 RH56，
也不得直接套用历史 RH56 checkpoint。

## XRobo live 仿真后的真机准备审查（2026-10-26）

本轮实际使用现有 `jaka_readonly_diagnostic` 查询2秒（2 Hz），未上电、使能、
初始化电爪或写任何工具配置。证据：`outputs/xrobo-live/jaka-readonly.json`。
当前机器人 powered/enabled/servo_move 均为 false；工具0的TCP为零偏置，
负载配置0.45 kg、质心(0,0,70) mm。这是控制器配置，未实测确认夹爪、安装件及指尖。
仿真的97 mm代理几何、安装高度和质量分配不能直接写入真机。

TIO读回电源启用/24 V；通道1为Modbus，slave=1、115200、8N1；
`init/gripperstate/gripperpos`分别指向FC03寄存器512/513/514，刷新配置2 Hz，
另有`aa`指向259，均是缓存零值。没有设备采样时间或逐次总线成功凭据，
不能判定电爪未初始化、到位或反馈新鲜。控制器/TIO固件、硬件版本和实际针脚仍未知。
本地DH配置仍为`hardware_confirmed=false`、`framing_confirmed=false`，
离线status明确拒绝缺少`firmware_version`，没有为通过检查填写占位值。

后续逐项验收顺序（每次物理动作须另获明确授权）：

1. **DH单独验收**：确认铭牌、线缆两端针脚、供电、TIO版本及总线独占；
   建立可验证设备采样新鲜度；确认安全停机方式和夹持区清空后，才授权一次初始化。
   再分别授权有限开合，实测0–1000寄存器的开合方向与行程，填写归一化映射。
   保留4 Hz写入上限；独立线程拥有JakaTio，禁止在arm实时servo线程调用。
   通用GripperObservation不能接受当前缓存作为valid测量；尚无已验收实时DH adapter。
2. **JAKA单独受限验收**：实测安装件/TCP、总质量/质心并验证碰撞几何；
   经单独配置授权后核对读回；现场急停可达、工作区清空，授权低速短程动作，
   独立验证HOLD/停机和反馈。此阶段无需依赖未知tracking的XRobo输入。
3. **联合验收**：前两项通过后，先补齐XRobo真实独立tracking证据、源session/seq、
   origin/recenter连续性及失效转换验证；再授权联合受限操作。
   Grip释放只停止新目标，不等同于电爪机械制动；不能用仿真通过代替停机能力确认。

XRobo experimental live始终只输出MuJoCo；不向任何硬件适配器传递实验许可。
