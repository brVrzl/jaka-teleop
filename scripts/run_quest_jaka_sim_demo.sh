#!/usr/bin/env bash
# Thin, simulation-only wrapper around the maintained live/replay entrypoint.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

CONFIG="configs/sim/quest_hts_jaka_mini2_live_demo.yaml"
INPUT_MODE="hts-ctrl-v1"
PROFILE="rh56"
BIND_HOST="0.0.0.0"
UDP_PORT="9000"
PROJECT_IP=""
ALLOWED_SENDER=""
DURATION_SEC="600"
REPLAY_DURATION=""
LOG_DIR=""
RECORDING=""
REPORT=""
OUTPUT=""
EVENTS=""
ARM_EMITTED_EVENTS=""
ARM_OUTPUT_MODE="shaped-500hz"
TELEMETRY_HZ="2"
VIEWER_FLAG="--viewer"
IK_DEBUG_FLAG=""
PYTHON_BIN="${HOME}/.venvs/embodied-hand-lab/bin/python"
DISPLAY_MODE="monitor"
DESKTOP_DISPLAY=""
DESKTOP_XAUTHORITY=""

usage() {
  cat <<'EOF'
用法：
  ./scripts/run_quest_jaka_sim_demo.sh [选项]

simulation-only Quest 3 -> JAKA Mini2 MuJoCo 6D 相对遥操作演示。
本脚本只调用 tools/quest_jaka_mujoco_sim.py live/replay-6dof，不包含真机后端。

选项：
  --log-dir DIR           新建带时间戳的报告/事件/原始输入文件
  --profile NAME          rh56（默认）或 dh-proxy（仿真近似模型）
  --input-mode MODE       hts-ctrl-v1 / right-touch-v1 / xrobo-native-experimental
  --recording PATH        读取已有 raw JSONL（离线 replay；默认 live UDP）
  --config PATH           演示 YAML（默认 configs/sim/quest_hts_jaka_mini2_live_demo.yaml）
  --bind HOST             UDP bind host（默认 0.0.0.0）
  --port PORT             Quest/CTRL 共用 UDP 端口（默认 9000）
  --project-ip IPV4       显示给 Quest 操作者填写的主机 IPv4（默认由正式入口探测）
  --allowed-sender IPV4   只接受指定 Quest IPv4（默认不限制）
  --duration-sec SEC      live 最长运行时间（演示默认 600；正式 CLI 默认 180）
  --report PATH           最终 JSON 报告路径（默认时间戳路径）
  --output PATH           原始 UDP JSONL 记录路径（默认时间戳路径）
  --events PATH           每控制 tick 的 JSONL 事件路径（默认由 report 派生）
  --arm-emitted-events PATH  125 Hz arm emitted JSONL（仅 JAKA-equivalent 模式）
  --arm-output-mode MODE  shaped-500hz（默认）或 jaka-equivalent-125hz
  --telemetry-hz HZ       终端状态输出频率（默认 2；0 关闭）
  --ik-debug              显示可选 joint/IK/奇异性/continuation 诊断
  --display-mode MODE     monitor（默认实体桌面）、headless 或 forward（SSH X11）
  --viewer                打开 MuJoCo viewer（演示默认）
  --no-viewer             仅用于无图形环境的启动/接收检查
  --display DISPLAY       viewer 使用的 X11 display（SSH 下可指定，例如 :1）
  --xauthority PATH       viewer 使用的 Xauthority 文件
  --python PATH           Python 解释器（默认 ~/.venvs/embodied-hand-lab/bin/python）
  -h, --help              显示本帮助

MuJoCo model、HTS/controller stale timeout、滤波、IK 与 clutch 阈值均由
--config 指向的当前正式 YAML 管理；当前入口没有 log-level 或键盘 clutch 模式。
EOF
}

require_value() {
  if [[ $# -lt 2 || -z "${2-}" ]]; then
    echo "缺少参数值：${1}" >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log-dir) require_value "$@"; LOG_DIR="$2"; shift 2 ;;
    --profile) require_value "$@"; PROFILE="$2"; shift 2 ;;
    --input-mode) require_value "$@"; INPUT_MODE="$2"; shift 2 ;;
    --recording) require_value "$@"; RECORDING="$2"; shift 2 ;;
    --config) require_value "$@"; CONFIG="$2"; shift 2 ;;
    --bind) require_value "$@"; BIND_HOST="$2"; shift 2 ;;
    --port) require_value "$@"; UDP_PORT="$2"; shift 2 ;;
    --project-ip) require_value "$@"; PROJECT_IP="$2"; shift 2 ;;
    --allowed-sender) require_value "$@"; ALLOWED_SENDER="$2"; shift 2 ;;
    --duration-sec) require_value "$@"; DURATION_SEC="$2"; REPLAY_DURATION="$2"; shift 2 ;;
    --report) require_value "$@"; REPORT="$2"; shift 2 ;;
    --output) require_value "$@"; OUTPUT="$2"; shift 2 ;;
    --events) require_value "$@"; EVENTS="$2"; shift 2 ;;
    --arm-emitted-events) require_value "$@"; ARM_EMITTED_EVENTS="$2"; shift 2 ;;
    --arm-output-mode) require_value "$@"; ARM_OUTPUT_MODE="$2"; shift 2 ;;
    --telemetry-hz) require_value "$@"; TELEMETRY_HZ="$2"; shift 2 ;;
    --ik-debug) IK_DEBUG_FLAG="--ik-debug"; shift ;;
    --display-mode) require_value "$@"; DISPLAY_MODE="$2"; shift 2 ;;
    --viewer) VIEWER_FLAG="--viewer"; shift ;;
    --no-viewer) DISPLAY_MODE="headless"; shift ;;
    --display) require_value "$@"; DESKTOP_DISPLAY="$2"; shift 2 ;;
    --xauthority) require_value "$@"; DESKTOP_XAUTHORITY="$2"; shift 2 ;;
    --python) require_value "$@"; PYTHON_BIN="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$1" >&2; usage >&2; exit 2 ;;
  esac
done

case "${PROFILE}" in
  rh56) ;;
  dh-proxy) CONFIG="configs/sim/quest_jaka_dh_proxy.yaml" ;;
  *) echo "未知 profile：${PROFILE}" >&2; exit 2 ;;
esac
if [[ "${INPUT_MODE}" == "xrobo-native-experimental" && -z "${RECORDING}" ]]; then
  echo "XRobo 当前仅开放未验证的原生回调 replay；实时输入请用 xrobo_input_observer.py。" >&2
  exit 2
fi
if [[ "${PROFILE}" == "dh-proxy" && "${INPUT_MODE}" == "hts-ctrl-v1" ]]; then
  echo "dh-proxy 需要右 Touch 或 XRobo 实验输入；旧 HTS/RH56 双 clutch 请用 rh56。" >&2
  exit 2
fi

cd "${REPO_ROOT}"

if [[ -n "${LOG_DIR}" ]]; then
  mkdir -p "${LOG_DIR}"
  RUN_PREFIX="${LOG_DIR}/$(date +%Y%m%dT%H%M%S)-$$"
  REPORT="${REPORT:-${RUN_PREFIX}.json}"
  EVENTS="${EVENTS:-${RUN_PREFIX}.events.jsonl}"
  [[ -z "${RECORDING}" ]] && OUTPUT="${OUTPUT:-${RUN_PREFIX}.raw.jsonl}"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python 不可执行：${PYTHON_BIN}" >&2
  echo "请使用已有 ~/.venvs/embodied-hand-lab，或使用 --python 指定解释器。" >&2
  exit 2
fi
if [[ ! -f "${CONFIG}" ]]; then
  echo "配置文件不存在：${CONFIG}" >&2
  exit 2
fi

# Select the physical seat explicitly; an SSH-forwarded DISPLAY must never
# silently become the monitor destination. Reuse existing authorization only.
case "${DISPLAY_MODE}" in
  headless)
    VIEWER_FLAG="--no-viewer"
    DESKTOP_DISPLAY=""
    DESKTOP_XAUTHORITY=""
    ;;
  forward)
    DESKTOP_DISPLAY="${DESKTOP_DISPLAY:-${DISPLAY-}}"
    DESKTOP_XAUTHORITY="${DESKTOP_XAUTHORITY:-${XAUTHORITY-}}"
    if [[ -z "${SSH_CONNECTION-}" || ! "${DESKTOP_DISPLAY}" =~ ^(localhost|127\.0\.0\.1):[0-9]+ ]]; then
      echo "forward 需要 SSH X11 转发 DISPLAY（使用 ssh -X/-Y）。" >&2
      exit 2
    fi
    ;;
  monitor)
    physical_session=""
    physical_display=""
    while read -r session_id _; do
      [[ -n "${session_id}" ]] || continue
      properties="$(loginctl show-session "${session_id}" -p Active -p Remote -p Seat -p Display -p Leader -p User 2>/dev/null)" || continue
      if [[ "${properties}" == *"Active=yes"* && "${properties}" == *"Remote=no"* && "${properties}" == *"Seat=seat0"* ]]; then
        physical_session="${session_id}"
        while IFS='=' read -r name value; do
          case "${name}" in
            Display) physical_display="${value}"; DESKTOP_DISPLAY="${DESKTOP_DISPLAY:-${value}}" ;;
            User) desktop_uid="${value}" ;;
          esac
        done <<< "${properties}"
        break
      fi
    done < <(loginctl list-sessions --no-legend 2>/dev/null)
    if [[ -z "${physical_session}" ]]; then
      echo "未找到 seat0 活跃实体桌面；headless 请显式选择 --display-mode headless。" >&2
      exit 2
    fi
    if [[ "${desktop_uid}" == "$(id -u)" ]]; then
      while IFS= read -r desktop_pid; do
        [[ -r "/proc/${desktop_pid}/environ" ]] || continue
        while IFS='=' read -r name value; do
          case "${name}" in
            DISPLAY) DESKTOP_DISPLAY="${DESKTOP_DISPLAY:-${value}}" ;;
            XAUTHORITY) DESKTOP_XAUTHORITY="${DESKTOP_XAUTHORITY:-${value}}" ;;
          esac
        done < <(tr '\0' '\n' < "/proc/${desktop_pid}/environ")
      done < <(pgrep -u "$(id -u)" -x gnome-shell || true)
    fi
    if [[ -n "${physical_display}" && "${DESKTOP_DISPLAY}" != "${physical_display}" ]]; then
      echo "monitor DISPLAY 必须匹配 seat0 桌面 ${physical_display}。" >&2
      exit 2
    fi
    if [[ ! "${DESKTOP_DISPLAY}" =~ ^:[0-9]+(\.[0-9]+)?$ ]]; then
      echo "monitor 需要实体桌面的本地 X11/XWayland DISPLAY。" >&2
      exit 2
    fi
    ;;
  *) echo "未知 display mode：${DISPLAY_MODE}" >&2; exit 2 ;;
esac

if [[ "${VIEWER_FLAG}" == "--viewer" ]]; then
  if [[ -n "${DESKTOP_XAUTHORITY}" && ! -r "${DESKTOP_XAUTHORITY}" ]]; then
    echo "Xauthority 不可读：${DESKTOP_XAUTHORITY}" >&2
    exit 2
  fi
  if ! env DISPLAY="${DESKTOP_DISPLAY}" XAUTHORITY="${DESKTOP_XAUTHORITY}" xwininfo -root >/dev/null; then
    echo "无法访问 ${DISPLAY_MODE} 桌面 ${DESKTOP_DISPLAY}；请用桌面所属用户启动或提供已授权的 --xauthority，禁止使用 xhost +。" >&2
    exit 2
  fi
  if [[ "${DISPLAY_MODE}" == "monitor" ]] && ! env DISPLAY="${DESKTOP_DISPLAY}" XAUTHORITY="${DESKTOP_XAUTHORITY}" xrandr --current | grep -Eq ' connected (primary )?[0-9]+x[0-9]+\+'; then
    echo "实体桌面没有已启用的显示输出。" >&2
    exit 2
  fi
fi

echo "SAFETY=SIMULATION_ONLY；不会导入、初始化或连接 JAKA / Inspire RH56DFX 真机 SDK"
ENTRY="live-6dof"
[[ -n "${RECORDING}" ]] && ENTRY="replay-6dof"
echo "ENTRY=tools/quest_jaka_mujoco_sim.py ${ENTRY}"
echo "CONFIG=${CONFIG}"
echo "ARM_OUTPUT=${ARM_OUTPUT_MODE}"
echo "DISPLAY_MODE=${DISPLAY_MODE}"
if [[ -z "${RECORDING}" ]]; then
echo "QUEST_UDP=${PROJECT_IP:-<自动探测>}:${UDP_PORT}（unicast；host bind=${BIND_HOST}）"
[[ "${VIEWER_FLAG}" == "--viewer" ]] && echo "VIEWER_X11=DISPLAY=${DESKTOP_DISPLAY} XAUTHORITY=${DESKTOP_XAUTHORITY:-<未设置>}"
if [[ "${INPUT_MODE}" == "hts-ctrl-v1" ]]; then
echo "请先在 Quest 端打开带 CTRL sidecar 的 Hand Tracking Streamer，开启右手、Head Pose、Debug Info，确认 CTRL sender 后 Start Streaming。"
echo "左控制器：INDEX=机械臂 hold-to-run/reference capture；GRIP=仿真 RH56 手；不是空格键。"
fi
fi
[[ "${VIEWER_FLAG}" == "--viewer" && -n "${RECORDING}" ]] && echo "VIEWER_X11=DISPLAY=${DESKTOP_DISPLAY}"
if [[ "${INPUT_MODE}" != "hts-ctrl-v1" ]]; then
  echo "右 Grip=arm+平行夹爪唯一 clutch；右 Index=连续闭合意图。XRobo 原生 replay 未验证 tracking/连续性。"
fi
echo "连续性：MuJoCo 入口沿完整 6D SE(3) 目标分段推进；奇异/限位拒绝时保持 index 并把手退回即可恢复，硬 gate 不变。"

CMD=("${PYTHON_BIN}" tools/quest_jaka_mujoco_sim.py "${ENTRY}")
if [[ -n "${RECORDING}" ]]; then
  if [[ -n "${OUTPUT}" ]]; then
    echo "replay 不写原始输入；不要同时使用 --recording 和 --output。" >&2
    exit 2
  fi
  if [[ -n "${IK_DEBUG_FLAG}" ]]; then
    echo "--ik-debug 仅用于 live。" >&2
    exit 2
  fi
  CMD+=("${RECORDING}")
  [[ -n "${REPLAY_DURATION}" ]] && CMD+=(--duration-sec "${REPLAY_DURATION}")
  [[ "${VIEWER_FLAG}" == "--viewer" ]] && CMD+=(--viewer)
else
  CMD+=(--bind "${BIND_HOST}" --port "${UDP_PORT}"
    --duration-sec "${DURATION_SEC}" --telemetry-hz "${TELEMETRY_HZ}" "${VIEWER_FLAG}")
  [[ -n "${PROJECT_IP}" ]] && CMD+=(--project-ip "${PROJECT_IP}")
  [[ -n "${ALLOWED_SENDER}" ]] && CMD+=(--allowed-sender "${ALLOWED_SENDER}")
fi
CMD+=(--config "${CONFIG}" --input-mode "${INPUT_MODE}" --arm-output-mode "${ARM_OUTPUT_MODE}")
[[ -n "${REPORT}" ]] && CMD+=(--report "${REPORT}")
[[ -n "${OUTPUT}" ]] && CMD+=(--output "${OUTPUT}")
[[ -n "${EVENTS}" ]] && CMD+=(--events "${EVENTS}")
[[ -n "${ARM_EMITTED_EVENTS}" ]] && CMD+=(--arm-emitted-events "${ARM_EMITTED_EVENTS}")
[[ -n "${IK_DEBUG_FLAG}" ]] && CMD+=("${IK_DEBUG_FLAG}")

# exec keeps one foreground process, so Ctrl-C/window close reaches the Python
# finally blocks that stop the receiver thread and close the viewer/socket.
ENVIRONMENT=(PYTHONPATH=src)
if [[ "${DISPLAY_MODE}" == "headless" ]]; then
  ENVIRONMENT=(-u DISPLAY -u XAUTHORITY PYTHONPATH=src MUJOCO_GL=egl)
fi
[[ -n "${DESKTOP_DISPLAY}" ]] && ENVIRONMENT+=(DISPLAY="${DESKTOP_DISPLAY}")
[[ -n "${DESKTOP_XAUTHORITY}" ]] && ENVIRONMENT+=(XAUTHORITY="${DESKTOP_XAUTHORITY}")
exec env "${ENVIRONMENT[@]}" "${CMD[@]}"
