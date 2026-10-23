# 数据采集与审核

[安装](../setup/INSTALLATION.md) · [本机配置](../configuration/CONFIGURATION.md) · [数据格式](DATASET.md) · [English](#english)

先验证两台相机，再采集具备真实机器人状态的 episode。相机检查记录、离线仿真记录和真机 episode 是不同证据，
必须保留来源标记；不能用 camera-only 检查证明机械臂或 DH 遥操作通过。

## 1. 配置和角色

沿用 `configs/data_collection/physical_collection.yaml` 的结构，使用自己的本机 YAML。
运行参数在 `runtime`，数据与相机配置在同一文件的 `dataset`、`cameras` 和 `calibration`，不依赖旧用户目录。

- 两台 D435 必须按 **RealSense SDK 序列号** 分配 `workspace` 和 `wrist`，不能按 `/dev/video*` 顺序或 USB 标识分配。
- 核对 `runtime.task_name`、`runtime.operator`、输出目录和是否保存 depth；相机角色需要现场画面确认。
- `production` 保留规范数据行与有界诊断；`diagnostic` 用于短时排查，不能作为训练样本筛选标签。
- 相机、原始采集、审核后的数据和派生训练 view 使用不同输出目录；旧 raw/master 不覆盖。

## 2. 双相机独立检查

安装 `realsense,dataset-collection` extras 后，先查看帮助，再以已填写的本机配置显式打开相机：

```bash
.venv/bin/python tools/check_realsense_stream.py --help
.venv/bin/python tools/check_realsense_stream.py \
  --config configs/local/thor.yaml --duration-sec 5 \
  --snapshot-dir outputs/onboarding/dual-d435
```

输出路径必须尚不存在；不要预先 `mkdir` 该 capture 目录。每次使用新名称，工具在打开相机前原子创建目录，避免覆盖或并发写入已有采集。

该入口并发检查配置中的相机并记录 RGB 视频、时间戳与 metadata；`capture_depth: true` 时保存逐帧原始 depth。
逐台观察/遮挡画面确认角色，再检查同时运行时两路都有连续帧、正确分辨率和时间戳，退出后设备已释放。
深度原始值需结合 metadata 中的 depth scale 使用，彩色深度预览不能替代原始深度数据。
检查期间不要同时启动 RealSense viewer、其他采集脚本或遥操作中的相机进程。

本轮已识别 SDK serial `346522072675` 与 `346222072985`；第一路画面显示桌面工作区，第二路朝向天花板。
用户随后确认 `346222072985` 物理安装在腕部，因此本机将其分配为 `wrist`，`346522072675` 分配为 `workspace`。
迁移到其他现场仍需重做角色确认；序列号存在和配置名称本身不构成验证。
双 RGB/RGB-D 各完成 5 秒并发记录；各路实际帧率与缺帧数据见[部署验证记录](../setup/DEVICE_STATUS.md)。

相机检查的输出只用于设备与时序验证，没有机器人 action/state，不进入训练集。
如果该阶段失败，先修复相机权限、USB 带宽、profile 或配置，不启动执行器来排查。

## 3. 机器人 episode 的前置条件

完成[真机只读检查](../operation/REAL_ROBOT.md)、[遥操作验证](../operation/TELEOPERATION.md)及现场 TCP/负载确认后，
才使用对应入口的 episode 参数。入口帮助提供当前支持的配置和开关：

```bash
.venv/bin/python tools/quest_jaka_hardware.py --help
.venv/bin/python tools/quest_jaka_mujoco_sim.py live-6dof --help
```

现有 RH56 episode/action 约定为六个机械臂通道加六个 RH56 主动执行器通道。
DH 是平行电爪，不能把一个开合量复制成六个 RH56 通道、伪造 RH56 反馈或复用 RH56 训练权重。
新配置用 `dataset.profile: jaka_dh_7d_v1` 区分 DH；现有 RH56 收集器会明确拒绝它，尚不是可用的 DH episode writer。
在 DH episode 语义和反馈链路完整验收前，保留相机检查和 DH 独立诊断日志，明确标记未完成真机 episode 验收。

录制期间关注 camera/control freshness、时间戳、丢帧、队列溢出、停止原因和清理结果。
同步器遵循因果顺序，不用未来相机/控制/力数据倒填较早的数据行；缺失或过期信号保留质量错误。

## 4. 审核后再转数据集

当前 `lerobot_staging_v1` 是 staging 格式。先按实际输出的 root 与 episode ID 生成同步检查和人工 review 页面：

```bash
.venv/bin/embodied-lab dataset sync-staging <staging-root> <episode-id> \
  --camera-tolerance-ms 100 --output outputs/sync-check.json
.venv/bin/embodied-lab dataset review-staging <staging-root> <episode-id> \
  --output outputs/review.html
```

人工核对任务开始/结束、相机角色与遮挡、动作来源、状态有效性、任务成败和异常原因后再记录结论。
以下命令会写入审核决定；不能仅凭“没有异常退出”自动批准：

```bash
.venv/bin/embodied-lab dataset approve-staging <staging-root> <episode-id> \
  --status approved --notes '填写实际审核结论'
.venv/bin/embodied-lab dataset convert-staging <staging-root> <episode-id> <new-output-root>
```

不合格时使用 `--status rejected` 并保留原因。转换需要 `dataset-collection` 中的 Parquet 依赖，输出到新的派生目录。
对于已经完成的 canonical episode，可执行：

```bash
.venv/bin/embodied-lab dataset validate <episode-directory>
.venv/bin/embodied-lab dataset inspect <episode-directory>
.venv/bin/embodied-lab dataset manifest <dataset-root> <manifest.json>
.venv/bin/embodied-lab dataset statistics <manifest.json> <statistics.json>
```

训练视图和导出流程见 [DATASET.md](DATASET.md)。本轮部署不重跑训练、不改变历史审核和数据划分。

## English

Configure explicit SDK serials for `workspace` and `wrist`, task/operator metadata and output roots in one local YAML.
Run the camera-only check above before starting any robot process. It records simultaneous RGB streams, timestamps and metadata;
raw depth is saved when configured. Verify roles from actual images and inspect both streams for continuity and cleanup.
Camera-only output is not a robot episode and is not training-eligible.

The current RH56 episode interface represents six arm plus six active RH56 actuator channels.
Do not relabel this interface as DH, duplicate a gripper scalar into RH56 channels or invent feedback.
DH physical episode acceptance remains separate from camera and gripper diagnostics.

Collection remains review-first. Synchronization is causal and records missing/stale inputs as quality faults.
Generate a staging sync report and HTML review page, record a human approved/rejected decision, then convert approved data to a new root.
Keep raw/master data immutable. Use `validate`/`inspect` for finalized canonical episodes and consult [dataset documentation](DATASET.md) for training views.
