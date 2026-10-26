# Simulation

## English

Run the headless smoke without devices:

```bash
.venv/bin/embodied-lab sim smoke
./scripts/run_quest_jaka_sim_demo.sh --help
```

The maintained model is `assets/jaka_rh56_visual_coacd.xml`. Quest simulation
uses the same accepted-target boundary as the physical adapter, but it does
not imply physical calibration or sim-to-real equivalence. The interactive
viewer is `tools/debug_mujoco_jaka_rh56_viewer.py`; it is an offline viewer,
not a hardware controller.

## 中文

无设备运行 headless smoke：

```bash
.venv/bin/embodied-lab sim smoke
./scripts/run_quest_jaka_sim_demo.sh --help
```

当前维护的模型是 `assets/jaka_rh56_visual_coacd.xml`。Quest 仿真与物理适配器共用 accepted-target boundary，
但不代表真机标定或 sim-to-real 等价。交互 viewer 是 `tools/debug_mujoco_jaka_rh56_viewer.py`；它是离线
viewer，不是硬件 controller。

## Thor display selection / Thor 显示模式

默认使用已有的 `~/.venvs/embodied-hand-lab/bin/python`（可用 `--python` 覆盖）。
`monitor` 通过 `loginctl` 查找 seat0 活跃实体桌面，检查 X11 授权及启用的
显示输出；不会把 SSH 转发的 DISPLAY 当作实体桌面。支持 X11 或已有的
XWayland DISPLAY，不会启动新桌面或 Xvfb。需要 `loginctl`、`xwininfo`、`xrandr`。

```bash
# 首次只读环境检查
loginctl list-sessions
ls /sys/class/drm
nvidia-smi
./scripts/run_quest_jaka_sim_demo.sh --help

# 旧 RH56 live；默认 Thor 实体显示器，左 Index 控制 arm、左 Grip 控制 hand
./scripts/run_quest_jaka_sim_demo.sh --duration-sec 180 \
  --report /tmp/rh56-live.json --output /tmp/rh56-live.raw.jsonl

# 无交互窗口；离屏渲染使用 EGL（不会启动 viewer）
./scripts/run_quest_jaka_sim_demo.sh --display-mode headless --duration-sec 30 \
  --report /tmp/rh56-headless.json --output /tmp/rh56-headless.raw.jsonl

# 显式 SSH X11 转发；先在客户端使用 ssh -X/-Y 登录
./scripts/run_quest_jaka_sim_demo.sh --display-mode forward

# 历史 RH56 replay（离线证据，不是实际设备验收）
./scripts/run_quest_jaka_sim_demo.sh --display-mode headless \
  --recording /path/to/recording.raw.jsonl --report /tmp/rh56-replay.json
```

SSH 用户与桌面用户不同且授权失败时，可由桌面用户通过终端仅授权指定本机用户：
`DISPLAY=<实体桌面> XAUTHORITY=<桌面授权文件> xhost +SI:localuser:user01`。
撤销使用 `xhost -SI:localuser:user01`，桌面重启后需重新核验。
不要使用全局 `xhost +`，不要修改显示管理器或复制密码到脚本中。
启动脚本不修改桌面访问权限；也可显式传入已有的 `--xauthority PATH`。

`xrandr` 已启用输出、窗口 `IsViewable`/位置、真实根窗口截图或录屏需要交叉验证。
这些证据表明窗口位于实体输出的桌面上，不能单独证明显示器面板实际发光或操作者看到画面。
真实输入验收还需要有效 HTS/Head/CTRL、Clutch 转换、AcceptedArmTarget、实际
arm/hand 关节反馈与 viewer 更新统计；合成测试和 replay 不能替代。

Live 与 replay 的 `.events.jsonl` 按控制 tick 持续写入，包含实际仿真关节和命令；
内存诊断仍只保留最近 128 tick，因此报告中的部分延迟统计是末段窗口，不是全程统计。
请为每次运行指定新的输出文件名，保留原始 raw JSONL。
