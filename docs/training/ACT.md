# ACT 训练

[安装角色](../setup/INSTALLATION.md#按角色安装) · [数据集](../data/DATASET.md) · [English](#english)

训练是可选流程，不是 Thor 遥操作部署的前置条件。本轮不启动完整训练。
当前 physical-bottle 任务使用两路 RGB、12 维状态和 12 维绝对目标动作：六维 JAKA 加六维 RH56 主动执行器。
DH 平行电爪数据不能直接冒充这个接口；换末端需要独立的数据和动作语义适配。

## 新用户需要取得什么

| 资源 | 来源与检查 |
| --- | --- |
| LeRobot 源码 | `git submodule update --init third_party/lerobot`；版本由 [`training/act/runtime.yaml`](../../training/act/runtime.yaml) 固定 |
| 训练容器 | runtime 文件中的镜像名与 image ID；当前是实验室本地镜像，仓库未提供该镜像的 Dockerfile 或公共 registry 地址 |
| 原始 episode / master | 向数据维护者取得已授权的不可变数据副本，按[数据集流程](../data/DATASET.md)审核/构建；Git 不包含实验数据 |
| ResNet18 初始化权重 | 官方 torchvision `ResNet18_Weights.IMAGENET1K_V1`；入口要求预先缓存并核对其固定校验值 |
| 既有训练 checkpoint | 向实验维护者取得具体产物和配置；不是 clone 或 pip install 的产物 |

容器必须与 runtime 中审计过的 image ID 一致；仅创建同名标签不算复现。
缺少该镜像时应由维护者提供可导入归档或补齐受审查的构建流程，不能跳过镜像检查。
`docker load -i <维护者提供的镜像归档>` 后运行 `scripts/check_lerobot.sh --require-image` 验证。

训练 launcher 使用 `--network none`，所以初始化权重需提前取得。
权重来源为 [torchvision 官方 ResNet18 实现](https://docs.pytorch.org/vision/stable/_modules/torchvision/models/resnet.html)，
可在仓库根目录准备当前入口所需的缓存（仅在需要训练时执行）：

```bash
ACT_CACHE=outputs/training/lerobot_container_home/.cache/torch/hub/checkpoints
mkdir -p "$ACT_CACHE"
curl --fail --location https://download.pytorch.org/models/resnet18-f37072fd.pth \
  --output "$ACT_CACHE/resnet18-f37072fd.pth"
printf '%s  %s\n' \
  f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec \
  "$ACT_CACHE/resnet18-f37072fd.pth" | sha256sum --check
```

这里的校验属于既有训练入口的产物验证要求。使用 `LEROBOT_CONTAINER_HOME` 自定义目录时，将缓存放到该目录下对应位置。
权重和数据不提交到 Git，也不从旧用户私有缓存隐式读取。

## 配置与运行

- `configs/training/shared/physical_bottle.yaml`：任务、审核数据源与固定 split；
- `configs/training/act/physical_bottle.yaml`：ACT 训练 view；
- `configs/training/act/lerobot.json`：trainer 参数；
- `training/act/runtime.yaml`：源码、容器和输出边界。

资源齐备后才运行：

```bash
scripts/check_training_dependencies.sh --require-image
scripts/train_physical_bottle_lerobot.sh strong-act
scripts/evaluate_physical_bottle_nominal52_checkpoints.sh
```

最后一条为离线 teacher-forced checkpoint 评估，不执行真机 rollout。
现有 physical adapter 使用 checkpoint 的完整 action chunk 与 canonical temporal executor，不使用历史 consume-K 行为。
原始/master 数据保持不变，训练 view、日志和 checkpoint 写入独立的忽略目录；不要用旧 RH56 模型直接控制 DH。

## English

ACT is optional and is not required for teleoperation bring-up. The current interface uses two RGB images and 12-D native state/action: six arm plus six active RH56 channels.
DH data is not interchangeable with this interface.

Initialize the pinned LeRobot submodule and obtain the audited container from the environment maintainer.
The repository records its image ID but currently has no Dockerfile or public registry for that local image.
Obtain authorized source episodes/master data separately; neither datasets nor trained checkpoints are included in Git.
The network-disabled launcher also requires the official ResNet18 initialization weights cached at the path above, with the checksum already enforced by the launcher.
Verify resources with `scripts/check_training_dependencies.sh --require-image` before using the training-only commands above.
