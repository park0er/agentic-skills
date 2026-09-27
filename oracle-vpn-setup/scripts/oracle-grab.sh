#!/bin/bash
# ==============================================================================
# oracle-grab.sh — Oracle Cloud 抢机脚本（任意区域 / 任意 shape，参数化版）
# 源自东京实测版 oracle-a1-grab.sh（2026-08-24 第 131 轮抢到 A1）。
#
# 所有参数走环境变量（先跑 collect-ocids.sh 拿到值）：
#   PROFILE      ~/.oci/config 里的 profile 名（默认 DEFAULT）
#   COMPARTMENT  tenancy OCID（root compartment）
#   SUBNET       public subnet OCID
#   IMAGE        镜像 OCID（A1 用 aarch64，E2 用 x86）
#   ADS          空格分隔的 AD 列表，多 AD 会轮流试
#   SSH_PUB_KEY  SSH 公钥文件路径
#   DISPLAY_NAME 实例名
#   SHAPE        默认 VM.Standard.A1.Flex
#   OCPUS/MEM_GB 仅 Flex shape 用（先查额度！东京账号只有 2/12）
#   BOOT_VOL_GB  默认 50
#   RETRY_INTERVAL 默认 90 秒（60 秒实测会频繁 429）
#
# 前台测一轮:  PROFILE=US COMPARTMENT=... bash oracle-grab.sh
# 后台常驻:    nohup env PROFILE=US ... bash oracle-grab.sh > ~/oracle-grab-US.out 2>&1 &
# 看日志:      tail -n 30 ~/oracle-grab-<PROFILE>.log
# 停止:        pkill -f oracle-grab.sh
# ==============================================================================

set -uo pipefail

PROFILE="${PROFILE:-DEFAULT}"
: "${COMPARTMENT:?set COMPARTMENT}" "${SUBNET:?set SUBNET}" "${IMAGE:?set IMAGE}"
: "${ADS:?set ADS (space separated)}" "${SSH_PUB_KEY:?set SSH_PUB_KEY}" "${DISPLAY_NAME:?set DISPLAY_NAME}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-2}"
MEM_GB="${MEM_GB:-12}"
BOOT_VOL_GB="${BOOT_VOL_GB:-50}"
RETRY_INTERVAL="${RETRY_INTERVAL:-90}"
read -r -a ADS <<< "$ADS"
LOG="$HOME/oracle-grab-${PROFILE}.log"
SUCCESS_FILE="$HOME/oracle-grab-${PROFILE}-success.json"

SHAPE_ARGS=(--shape "$SHAPE")
if [[ "$SHAPE" == *Flex* ]]; then
  SHAPE_ARGS+=(--shape-config "{\"ocpus\": ${OCPUS}, \"memoryInGBs\": ${MEM_GB}}")
fi

# ---------- 预检 ----------
if ! command -v oci >/dev/null 2>&1; then
  echo "错误: 未找到 oci CLI。先 brew install oci-cli 并配置 ~/.oci/config" >&2
  exit 1
fi
if [ ! -f "$SSH_PUB_KEY" ]; then
  echo "错误: SSH 公钥不存在: $SSH_PUB_KEY" >&2
  exit 1
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

notify() {
  # macOS 桌面通知 + 声音
  local msg="$1"
  osascript -e "display notification \"$msg\" with title \"Oracle 抢机\" sound name \"Glass\"" 2>/dev/null || true
}

log "==== 抢机启动 (profile=${PROFILE}) ===="
log "目标: ${SHAPE} ${OCPUS} OCPU / ${MEM_GB}GB, 名称=${DISPLAY_NAME}, 重试间隔=${RETRY_INTERVAL}s"

ATTEMPT=0
RATE_BACKOFF=0
while true; do
  ATTEMPT=$((ATTEMPT+1))
  for AD in "${ADS[@]}"; do
    log "第 ${ATTEMPT} 轮 · AD=${AD} · 尝试 launch..."

    RESULT=$(oci compute instance launch \
      --availability-domain "$AD" \
      --compartment-id "$COMPARTMENT" \
      "${SHAPE_ARGS[@]}" \
      --profile "$PROFILE" \
      --subnet-id "$SUBNET" \
      --image-id "$IMAGE" \
      --assign-public-ip true \
      --display-name "$DISPLAY_NAME" \
      --boot-volume-size-in-gbs "$BOOT_VOL_GB" \
      --ssh-authorized-keys-file "$SSH_PUB_KEY" \
      --wait-for-state RUNNING \
      2>&1)
    RC=$?

    if [ $RC -eq 0 ] && echo "$RESULT" | grep -q '"lifecycle-state": "RUNNING"'; then
      echo "$RESULT" > "$SUCCESS_FILE"
      NEW_IP=$(echo "$RESULT" | grep -o '"public-ip": "[^"]*"' | head -1 | cut -d'"' -f4)
      log "🎉 成功! 实例已 RUNNING。Public IP: ${NEW_IP:-见 $SUCCESS_FILE}"
      log "详情已保存: $SUCCESS_FILE"
      notify "抢到 ${SHAPE}! IP: ${NEW_IP:-见日志}"
      # 多弹几次通知确保看到
      for i in 1 2 3; do sleep 2; notify "${PROFILE} ${SHAPE} 到手 🎉"; done
      exit 0
    fi

    # 分类错误。提取 message 字段(比 head -3 截断准确)
    MSG=$(echo "$RESULT" | grep -o '"message": *"[^"]*"' | head -1 | sed 's/"message": *"//; s/"$//')
    if echo "$RESULT" | grep -qi "Out of host capacity\|OutOfCapacity\|out of capacity"; then
      log "  容量不足 (Out of host capacity),继续等。"
      RATE_BACKOFF=0
    elif echo "$RESULT" | grep -qi "LimitExceeded\|quota\|ServiceLimit"; then
      log "  ⚠️ 配额/限额问题(非容量): ${MSG:-$(echo "$RESULT" | head -1)}"
      log "  可能已用满 Free Tier A1 额度,或已有 A1 实例。请检查控制台。"
      RATE_BACKOFF=0
    elif echo "$RESULT" | grep -qi "TooManyRequests\|429\|Too many requests"; then
      # 指数退避:每次连续 429 递增等待,减轻限流
      RATE_BACKOFF=$(( RATE_BACKOFF + 60 ))
      [ "$RATE_BACKOFF" -gt 300 ] && RATE_BACKOFF=300
      log "  被限流(429),额外退避 ${RATE_BACKOFF}s。"
      sleep "$RATE_BACKOFF"
    elif echo "$RESULT" | grep -qi "timed out\|timeout\|RequestException\|Connection\|Max retries"; then
      # 网络抖动/连接超时:无害,短暂等待后继续(不是抢到,也不是配额问题)
      log "  🌐 网络超时(非 Oracle 错误,那次请求没发到): ${MSG:-connection timeout}。稍后重试。"
      RATE_BACKOFF=0
      sleep 15
    else
      # 真正未知的响应:记完整 message + 首行,便于排查
      log "  ❓ 未知响应: ${MSG:-N/A} | $(echo "$RESULT" | head -1)"
      RATE_BACKOFF=0
    fi
  done
  sleep "$RETRY_INTERVAL"
done
