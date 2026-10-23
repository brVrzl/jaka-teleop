# Configuration

## 新主机：一个本地 YAML

```bash
mkdir -p configs/local
cp configs/data_collection/thor.example.yaml configs/local/thor.yaml
# 编辑后离线检查；不会连接设备
embodied-lab doctor --runtime-config configs/local/thor.yaml
```

`configs/local/` 已忽略。继续使用原 `load_yaml` 和 `--runtime-config` 路径，
不隐式合并默认值，不读取旧用户配置。相对路径从仓库根解析；先 `cd` 到仓库。
示例有意留下 IP、相机序列号和工具身份缺项，不能直接用于运动。

| 字段 | 如何填写 |
| --- | --- |
| `runtime.robot_ip` | 示教器实际有线控制器地址；不要默认旧地址仍有效 |
| `runtime.edg_state_ip` / `host_interface` | `ip route get ROBOT_IP` 输出的主机源地址及专用接口；后者供网络配置核对 |
| `runtime.bind` / `port` / `allowed_sender` | Quest能访问的主机地址、UDP端口及明确允许的Quest地址；null不做来源限制 |
| `runtime.quest_input_mode` | 原 `hts-ctrl-v1` 或新 `right-touch-v1`；不能混用报文 |
| `end_effector` / `dh_gripper` | 当前工具身份、实际通信参数和核验记录；不填旧RH56串口。标记不能代替DH运动学模型验收 |
| `cameras.workspace.serial` / `wrist.serial` | SDK枚举后按实际画面确认，不使用USB设备标识或枚举顺序 |
| `cameras.*.capture_depth` | false只保存RGB；true才请求深度。设备支持RGB-D不代表当前episode保存深度 |
| `runtime.native_control_cpu` / `native_control_realtime_priority` | 新主机允许的CPU及实时优先级。null/0避免假设旧CPU或实时权限；真机调度能力需独立检查 |
| `runtime.log_dir` / `episode_root` / `dataset.root` | 日志和数据目录，默认仓库内被忽略目录。外部盘用显式绝对路径 |
| `runtime.task_name` / `operator` | 本次任务与操作者 |

模型路径仍由 `runtime.config` 指向的现有控制YAML中的 `simulation.mjcf_path`
管理；训练权重和外部资源使用各训练profile的现有字段，不放进遥操作依赖。
旧 `physical_collection.yaml` 保留 RH56 工作流及历史示例值。
新 `dataset.profile: jaka_dh_7d_v1` 与旧 RH56 12维隔离；当前旧收集器明确拒绝它，
不得补零或用夹爪命令冒充RH56反馈。新工具实物未验收前不能宣称联合episode完成。

### 网络：先核对，不清空接口

```bash
ip -brief address
ip route
ip route get "$JAKA_IP"
# 仅在确实需要补地址/host route时；不加--execute只显示操作
IFACE="$ROBOT_IFACE" PC_IP="$ROBOT_HOST_IP" JAKA_IP="$JAKA_IP" \
  scripts/setup_jaka_lan2_route.sh
```

脚本无默认网卡/IP；现有正确路由直接退出。需要改变时只添加缺失主机地址和
机器人host route，保留其他地址与路由，并拒绝修改当前SSH管理接口。
已有冲突host route会报错，须先核实，不自动替换。只有确认输出后才加 `--execute`。
当前有线同网段已正确时，SDK连接失败不能靠反复改主机路由解决。

## English

Configuration is grouped by current responsibility:

- `configs/sim/`: Quest/MuJoCo offline and live-simulation profiles;
- `configs/hand/`: RH56 real retargeting and PC-direct operation;
- `configs/perception/`: camera/RGB-D processing;
- `configs/data_collection/`: review-first episode collection;
- `configs/training/shared/physical_bottle.yaml`: task prompt, audited source
  selection, split, and ACT/force views;
- `configs/training/act/`: current ACT view and LeRobot trainer;
- `configs/training/pi05/`: current π0.5 base checkpoint and LoRA settings.

Load configuration through the repository CLI or the documented wrapper. Do
not invent a second config source, silently apply controller settings, or use
historical aliases. Generated datasets, checkpoints, caches, and logs belong
under ignored `outputs/` or `data/training/` paths and are not committed.

Useful read-only checks:

```bash
.venv/bin/embodied-lab doctor
.venv/bin/embodied-lab dataset --help
scripts/check_training_dependencies.sh --help
```

## 中文

配置按当前职责分组：

- `configs/sim/`：Quest/MuJoCo 离线和 live simulation profile；
- `configs/hand/`：RH56 真机 retargeting 和 PC-direct operation；
- `configs/perception/`：相机/RGB-D 处理；
- `configs/data_collection/`：先审核的 episode 采集；
- `configs/training/shared/physical_bottle.yaml`：task prompt、审核源数据选择、split 和 ACT/force view；
- `configs/training/act/`：当前 ACT view 和 LeRobot trainer；
- `configs/training/pi05/`：当前 π0.5 base checkpoint 和 LoRA 设置。

通过仓库 CLI 或文档中的 wrapper 读取配置。不要创建第二套配置来源、静默应用 controller setting，
或使用历史 alias。生成的数据集、checkpoint、cache 和 log 应位于被 Git 忽略的 `outputs/` 或
`data/training/`，不得提交。

可执行的只读检查：

```bash
.venv/bin/embodied-lab doctor
.venv/bin/embodied-lab dataset --help
scripts/check_training_dependencies.sh --help
```
