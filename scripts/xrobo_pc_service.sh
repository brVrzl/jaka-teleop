#!/usr/bin/env bash
# Manage only the upstream XRobo PC Service; never start a robot executor.
set -euo pipefail
unit=xrobo-pc.service
config="$HOME/.config/jaka-teleop/xrobo-pc.env"

load_config() {
    [[ -r "$config" ]] || { echo "Missing $config; see docs/setup/XROBO_SERVICE.md" >&2; return 1; }
    # Trusted, machine-local paths; use the same KEY=value syntax as EnvironmentFile.
    # shellcheck source=/dev/null
    source "$config"
    : "${XROBO_SERVICE_DIR:?Set XROBO_SERVICE_DIR in $config}"
    : "${XROBO_ICU_DIR:?Set XROBO_ICU_DIR in $config}"
    export LD_LIBRARY_PATH="$XROBO_SERVICE_DIR:$XROBO_SERVICE_DIR/lib:$XROBO_SERVICE_DIR/SDK/arm64:$XROBO_ICU_DIR"
    export QT_PLUGIN_PATH="$XROBO_SERVICE_DIR/plugins"
    export QT_QML_PATH="$XROBO_SERVICE_DIR/qml"
}

check_files() {
    [[ "$XROBO_SERVICE_DIR" = /* && "$XROBO_ICU_DIR" = /* ]] || { echo 'Use absolute deployment paths' >&2; return 1; }
    [[ -x "$XROBO_SERVICE_DIR/RoboticsServiceProcess" && -r "$XROBO_SERVICE_DIR/setting.ini" &&
       -r "$XROBO_SERVICE_DIR/SDK/arm64/libPXREARobotSDK.so" && -d "$XROBO_ICU_DIR" ]] || {
        echo 'Missing service executable, setting.ini, arm64 SDK or ICU directory' >&2; return 1;
    }
    local deps
    deps=$(ldd "$XROBO_SERVICE_DIR/RoboticsServiceProcess" "$XROBO_SERVICE_DIR/SDK/arm64/libPXREARobotSDK.so") || return
    if [[ "$deps" = *'not found'* ]]; then
        echo "$deps" >&2
        return 1
    fi
}

ports_ready() {
    local pid
    pid=$(systemctl --user show "$unit" -p MainPID --value)
    [[ "$pid" != 0 && -n "$pid" ]] || return 1
    ss -lntp 'sport = :63901' | grep -q "pid=$pid," &&
        ss -lntp 'sport = :60061' | grep -q "pid=$pid,"
}

case "${1:-status}" in
    run)
        load_config
        check_files
        if [[ -n "$(ps -C RoboticsServiceProcess -o pid=)" ]]; then
            echo 'RoboticsServiceProcess already exists; refusing a duplicate instance' >&2
            exit 1
        fi
        if [[ -n "$(ss -H -lnt '( sport = :63901 or sport = :60061 )')" ]]; then
            echo 'XRobo TCP port already occupied (63901/60061); inspect ss -lntup' >&2
            exit 1
        fi
        cd "$XROBO_SERVICE_DIR"
        exec ./RoboticsServiceProcess
        ;;
    start)
        if ! systemctl --user start "$unit"; then
            journalctl --user -u "$unit" -n 30 --no-pager
            exit 1
        fi
        for ((attempt=0; attempt<25; attempt++)); do
            if ports_ready; then
                echo 'XRobo PC Service ready: TCP 63901, local SDK TCP 60061'
                exit 0
            fi
            systemctl --user is-active --quiet "$unit" || break
            sleep .2
        done
        journalctl --user -u "$unit" -n 30 --no-pager
        echo 'XRobo is not ready; see journal above and run status' >&2
        exit 1
        ;;
    stop)
        systemctl --user stop "$unit"
        if [[ -n "$(ps -C RoboticsServiceProcess -o pid=)" ]]; then
            echo 'An unmanaged RoboticsServiceProcess remains; inspect its owner, do not kill unrelated sessions' >&2
            exit 1
        fi
        ;;
    status)
        result=0
        if load_config; then
            printf 'Config: %s\nService directory: %s\nICU directory: %s\n' "$config" "$XROBO_SERVICE_DIR" "$XROBO_ICU_DIR"
            check_files || result=1
            # Print only operational settings, never RTC tokens or identities.
            awk '/^\[/ {section=$0}
                section=="[ProtocolType]" && /^Protocol=/ ||
                section=="[TCP]" && /^(TcpBindPort|BroadCastSendPort)=/ ||
                section=="[Service]" && /^runAsService=/ ||
                section=="[Log]" && /^logToFile=/ {print section, $0}' "$XROBO_SERVICE_DIR/setting.ini"
        else
            result=1
        fi
        systemctl --user show "$unit" -p LoadState -p ActiveState -p SubState -p MainPID -p ExecMainStatus -p UnitFileState
        ps -C RoboticsServiceProcess -o user,pid,ppid,etime,args || true
        pgrep -af 'python[^ ]* .*tools/(xrobo_input_observer|quest_jaka_mujoco_sim|quest_jaka_hardware)\.py' || true
        ss -lntup '( sport = :63901 or sport = :29888 or sport = :60061 or sport = :9000 )'
        ip -brief address
        ip route
        echo 'Firewall rules require privileged read access: sudo nft list ruleset (not changed here).'
        echo "Upstream log directory: ${XDG_DATA_HOME:-$HOME/.local/share}/PICOBusinessSuitData/log"
        ports_ready || result=1
        echo 'Ready ports do not prove Quest handshake or controller frames. See the input-only observer in docs/setup/XROBO_SERVICE.md.'
        exit "$result"
        ;;
    logs)
        exec journalctl --user -u "$unit" -n 60 --no-pager
        ;;
    *) echo "Usage: $0 {status|start|stop|logs|run}" >&2; exit 2 ;;
esac
