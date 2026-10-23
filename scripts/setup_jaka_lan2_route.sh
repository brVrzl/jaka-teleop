#!/usr/bin/env bash
set -euo pipefail

IFACE="${IFACE:-}"
PC_IP="${PC_IP:-}"
JAKA_IP="${JAKA_IP:-}"
EXECUTE=0

for arg in "$@"; do
  case "${arg}" in
    --execute)
      EXECUTE=1
      ;;
    --help|-h)
      cat <<'EOF'
Usage:
  IFACE=<dedicated-interface> PC_IP=<host-ipv4> JAKA_IP=<robot-ipv4> \
    ./scripts/setup_jaka_lan2_route.sh [--execute]

First inspect: ip -brief address; ip route; ip route get <robot-ipv4>.
All three values are required: there is no machine-specific default.
Dry-run is the default. Execution adds a /32 host address only if absent,
then adds a robot /32 route only if the existing route does not already use
that interface/source. It never flushes addresses or replaces routes.
A conflicting existing /32 route causes ip route add to fail for review.
Execution refuses the interface carrying the current SSH management session.
No change is necessary when the existing route is already correct.

EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      exit 2
      ;;
  esac
done

if [[ ! "${IFACE}" =~ ^[A-Za-z0-9_.:-]+$ ]]; then
  echo "Invalid interface name: ${IFACE}" >&2
  exit 2
fi

validate_ipv4() {
  local value="$1"
  local first second third fourth extra
  [[ "$value" =~ ^(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})$ ]] || return 1
  IFS=. read -r first second third fourth extra <<<"${value}"
  if [[ -n "${extra:-}" ]]; then
    return 1
  fi
  for octet in "${first:-}" "${second:-}" "${third:-}" "${fourth:-}"; do
    if [[ ! "${octet}" =~ ^[0-9]{1,3}$ ]] \
      || (( 10#${octet} < 0 || 10#${octet} > 255 )); then
      return 1
    fi
  done
}

if ! validate_ipv4 "${PC_IP}"; then
  echo "Invalid PC_IP: ${PC_IP}" >&2
  exit 2
fi
if ! validate_ipv4 "${JAKA_IP}"; then
  echo "Invalid JAKA_IP: ${JAKA_IP}" >&2
  exit 2
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "The Linux ip command is required." >&2
  exit 2
fi
ip link show dev "${IFACE}" >/dev/null

ROUTE="$(ip -4 route get "${JAKA_IP}" 2>/dev/null || true)"
if [[ " ${ROUTE} " == *" dev ${IFACE} "* && " ${ROUTE} " == *" src ${PC_IP} "* ]]; then
  printf 'Existing route is correct; no changes needed: %s\n' "${ROUTE}"
  exit 0
fi

if [[ -n "${SSH_CONNECTION:-}" ]]; then
  read -r SSH_CLIENT_IP SSH_CLIENT_PORT SSH_SERVER_IP SSH_SERVER_PORT <<<"${SSH_CONNECTION}"
  if [[ "${PC_IP}" == "${SSH_SERVER_IP}" ]]; then
    echo "Refusing to reuse this SSH session's local address on ${IFACE}: ${PC_IP}" >&2
    exit 2
  fi
  # The bound server address also protects asymmetric/policy-routed sessions.
  while read -r _ _ family address _; do
    if [[ "${address%/*}" == "${SSH_SERVER_IP}" ]]; then
      echo "Refusing to modify the interface bound to this SSH session: ${IFACE}" >&2
      exit 2
    fi
  done < <(ip -o addr show dev "${IFACE}")
  MANAGEMENT_ROUTE="$(ip route get "${SSH_CLIENT_IP}")"
  if [[ " ${MANAGEMENT_ROUTE} " == *" dev ${IFACE} "* ]]; then
    echo "Refusing to modify the interface carrying this SSH session: ${IFACE}" >&2
    exit 2
  fi
fi

HAS_ADDRESS=0
while read -r _ _ _ address _; do
  if [[ "${address%/*}" == "${PC_IP}" ]]; then HAS_ADDRESS=1; fi
done < <(ip -o -4 addr show dev "${IFACE}")

if [[ "${EXECUTE}" -ne 1 ]]; then
  printf 'Dry run; existing addresses and routes will be preserved.\n'
  if [[ "${HAS_ADDRESS}" -eq 0 ]]; then
    printf '  sudo ip addr add %q dev %q\n' "${PC_IP}/32" "${IFACE}"
  fi
  printf '  sudo ip link set %q up\n' "${IFACE}"
  printf '  sudo ip route add %q dev %q src %q\n' "${JAKA_IP}/32" "${IFACE}" "${PC_IP}"
  exit 0
fi

if [[ "${HAS_ADDRESS}" -eq 0 ]]; then
  sudo ip addr add "${PC_IP}/32" dev "${IFACE}"
fi
sudo ip link set "${IFACE}" up
sudo ip route add "${JAKA_IP}/32" dev "${IFACE}" src "${PC_IP}"
ip route get "${JAKA_IP}"
