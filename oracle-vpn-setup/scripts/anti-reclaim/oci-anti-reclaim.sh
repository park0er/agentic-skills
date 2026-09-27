#!/usr/bin/env bash
# Oracle Cloud Always Free 实例防回收：制造真实的 CPU + 内存负载
#
# 政策依据（Oracle 官方文档 "Reclamation of Idle Compute Instances"）：
#   7 天窗口内，CPU 95 分位 <20% 且 网络 <20% 且 内存 <20%（内存仅 A1 机型）
#   三者同时成立才会被回收 —— 只要任意一项稳定过 20% 就安全。
#
#   "95 分位 < 20%" = 低于 20% 的采样占 95%，即只有 <5% 的时间在 20% 以上。
#   所以要安全，需要 >5% 的采样点过线 = 168h × 5% = 8.4 小时 / 每 7 天。
#
# 用法：oci-anti-reclaim.sh [持续秒数] [每核CPU负载%] [每worker内存MB]
#   默认：7200 30 1280  →  2 小时，CPU ~30%，每核 1 个 worker × 1280M 内存
#   内存参数传 0 = 只压 CPU（E2.1.Micro 用：E2 不考核内存，且只有 1G）
#
# 为什么内存设 2.5G：A1 有 12G，2.5G ≈ 20.8%，刚好跨过内存那条线。
#   这样 CPU 和内存两项同时达标，比只赌 CPU 稳。

set -euo pipefail

DURATION="${1:-7200}"
CPU_LOAD="${2:-30}"
MEM_MB_PER_WORKER="${3:-1280}"

log() { echo "[$(date '+%F %T')] $*"; }

[[ $EUID -ne 0 ]] && { echo "需要 root 权限"; exit 1; }

if pgrep -x stress-ng >/dev/null 2>&1; then
    log "stress-ng already running, skip this trigger"
    exit 0
fi

command -v stress-ng >/dev/null 2>&1 || {
    log "安装 stress-ng ..."
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq stress-ng
}

WORKERS="$(nproc)"
MEM_TOTAL_MB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 ))
MEM_PCT=$(awk -v a="$((MEM_MB_PER_WORKER * WORKERS))" -v b="$MEM_TOTAL_MB" 'BEGIN{printf "%.1f", a*100/b}')

log "开始：时长=${DURATION}s  每核CPU负载=${CPU_LOAD}%  worker数=${WORKERS}"
log "内存：${WORKERS} × ${MEM_MB_PER_WORKER}M = $((MEM_MB_PER_WORKER * WORKERS))M / ${MEM_TOTAL_MB}M (${MEM_PCT}%)"

ARGS=(--cpu "$WORKERS" --cpu-load "$CPU_LOAD" --timeout "${DURATION}s" --metrics-brief)
if [[ "$MEM_MB_PER_WORKER" -gt 0 ]]; then
    ARGS+=(--vm "$WORKERS" --vm-bytes "${MEM_MB_PER_WORKER}M" --vm-keep)
fi
stress-ng "${ARGS[@]}"

log "结束"
