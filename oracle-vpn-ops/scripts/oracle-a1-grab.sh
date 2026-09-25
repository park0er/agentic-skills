#!/bin/bash
# ==============================================================================
# oracle-a1-grab.sh — Oracle Cloud A1.Flex (ARM) 容量抢占脚本
# ------------------------------------------------------------------------------
# 目标: VM.Standard.A1.Flex, 2 OCPU / 12 GB (本账号当前 A1 额度上限)
#       注: 本账号 A1 免费额度被砍到 2C/12G(非标准 4C/24G)。按 4C24G 抢会被
#       LimitExceeded(400) 硬拒,跟库存无关。若日后提额到 4C24G,再改回 OCPUS/MEM_GB。
# 原理: Free Tier 的 A1 容量长期被抢空,报 "Out of host capacity"。
#       本脚本循环重试 launch,一旦有容量释放立刻抢到,成功后 macOS 弹通知。
#
# 用法:
#   前台测试:  bash oracle-a1-grab.sh
#   后台常驻:  nohup bash oracle-a1-grab.sh > ~/oracle-a1-grab.out 2>&1 &
#   看日志:    tail -f ~/oracle-a1-grab.log
#   停止:      pkill -f oracle-a1-grab.sh
# ==============================================================================

set -uo pipefail

# ---------- 配置 (已采集,可直接用) ----------
COMPARTMENT="ocid1.tenancy.oc1..aaaaaaaamt2d6izfyb6znem55sbkdk7dzan4mvnrwdk2yumq2zpddfsd2poa"
SUBNET="ocid1.subnet.oc1.ap-tokyo-1.aaaaaaaaxb3r2anyiz4hgbnoqmpfmjrt6qzc4imz7lvv3k6yg4fbvkeh5pxq"
IMAGE="ocid1.image.oc1.ap-tokyo-1.aaaaaaaal6ki4uyubrmgd4h633jco7b3vca46ddfvlnbnnt7owadvfmbvy3q"  # Ubuntu 22.04 aarch64
SSH_PUB_KEY="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04.key.pub"

# 东京只有 1 个 AD;若将来多 AD,在此追加,脚本会轮流试
ADS=("xhDy:AP-TOKYO-1-AD-1")

DISPLAY_NAME="parko-vpn-tokyo-a1"
OCPUS=2
MEM_GB=12
BOOT_VOL_GB=50            # 引导盘大小(Free Tier 总量 200GB,现有 E2 已占用一部分)
RETRY_INTERVAL=90         # 每轮基础间隔(秒)。90s 降低 429 限流概率(实测 60s 太频繁)
LOG="$HOME/oracle-a1-grab.log"
SUCCESS_FILE="$HOME/oracle-a1-launch-success.json"

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
  osascript -e "display notification \"$msg\" with title \"Oracle A1 抢机\" sound name \"Glass\"" 2>/dev/null || true
}

log "==== A1.Flex 抢机启动 ===="
log "目标: ${OCPUS} OCPU / ${MEM_GB}GB, 名称=${DISPLAY_NAME}, 重试间隔=${RETRY_INTERVAL}s"

ATTEMPT=0
RATE_BACKOFF=0
while true; do
  ATTEMPT=$((ATTEMPT+1))
  for AD in "${ADS[@]}"; do
    log "第 ${ATTEMPT} 轮 · AD=${AD} · 尝试 launch..."

    RESULT=$(oci compute instance launch \
      --availability-domain "$AD" \
      --compartment-id "$COMPARTMENT" \
      --shape "VM.Standard.A1.Flex" \
      --shape-config "{\"ocpus\": ${OCPUS}, \"memoryInGBs\": ${MEM_GB}}" \
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
      notify "抢到 A1.Flex! IP: ${NEW_IP:-见日志}"
      # 多弹几次通知确保看到
      for i in 1 2 3; do sleep 2; notify "A1.Flex ${OCPUS}C${MEM_GB}G 到手 🎉"; done
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
