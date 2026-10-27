# 使用文档

[项目首页](../README.md) · [English](#english)

[本轮 Thor 设备验证记录](setup/DEVICE_STATUS.md) · [DH/TIO 适配](operation/DH_TIO.md)

新用户按 **安装 → 本机配置 → 离线检查 → 设备只读确认 → 仿真 → 真机遥操作 → 采集审核** 的顺序推进。
任何真机操作前先阅读[安全边界](safety/REAL_HARDWARE_SAFETY.md)。`doctor` 和帮助命令始终离线。

| 阶段 | 文档 | 结果 |
| --- | --- | --- |
| 首次部署 | [安装与 Thor 部署](setup/INSTALLATION.md) | 自己的环境、CLI、smoke、native 构建 |
| 机器迁移 | [配置](configuration/CONFIGURATION.md) | 本机 YAML、设备角色、输出目录 |
| 了解能力 | [当前能力](CAPABILITIES.md)、[系统架构](architecture/SYSTEM_ARCHITECTURE.md) | 知道各入口与控制边界 |
| 输入确认 | [XRobo 服务部署与排查](setup/XROBO_SERVICE.md)、[Quest 备用传输](motion_input/QUEST_CONTROLLER_TRANSPORT_HOST.md)、[UMIP 协议](motion_input/UMIP_PROTOCOL.md) | 确认实际数据、时效和来源 |
| 离线运行 | [仿真与 replay](simulation/SIMULATION.md) | 不连接执行器的验证 |
| 真机操作 | [设备检查](operation/REAL_ROBOT.md)、[遥操作](operation/TELEOPERATION.md) | 先只读，再执行明确的物理操作 |
| 数据工作流 | [采集](data/DATA_COLLECTION.md)、[数据集](data/DATASET.md) | staging、审核、派生训练 view |
| 训练 | [ACT](training/ACT.md)、[π0.5](training/PI05.md) | 按需安装的独立工作流 |

查命令时使用[入口参考](reference/COMMANDS.md)，查记录字段时使用[日志结构](reference/LOG_SCHEMAS.md)，
遇到问题先看[故障排查](TROUBLESHOOTING.md)。命令参数以当前入口的 `--help` 和对应维护文档为准。

## English

[English project overview](../README.en.md) · [Installation](setup/INSTALLATION.md#english)

Follow installation, local configuration, offline checks, read-only device confirmation, simulation, physical teleoperation and episode review in that order.
Help and `doctor` do not connect to devices. Read the [hardware safety procedure](safety/REAL_HARDWARE_SAFETY.md) before physical operation.

- Setup: [installation](setup/INSTALLATION.md), [configuration](configuration/CONFIGURATION.md), [troubleshooting](TROUBLESHOOTING.md).
- Control: [architecture](architecture/SYSTEM_ARCHITECTURE.md), [Quest transport](motion_input/QUEST_CONTROLLER_TRANSPORT_HOST.md), [UMIP](motion_input/UMIP_PROTOCOL.md), [simulation](simulation/SIMULATION.md), [real robot](operation/REAL_ROBOT.md), [teleoperation](operation/TELEOPERATION.md).
- Data: [collection](data/DATA_COLLECTION.md), [datasets](data/DATASET.md), [ACT](training/ACT.md), [π0.5](training/PI05.md).
- Reference: [capabilities](CAPABILITIES.md), [commands](reference/COMMANDS.md), [log schemas](reference/LOG_SCHEMAS.md).
