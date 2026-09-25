#!/bin/bash
# ==============================================================================
# a1-status.sh — A1.Flex 抢机进度一览
# 用法: bash a1-status.sh
# ==============================================================================
LOG="$HOME/oracle-a1-grab.log"
SUCCESS_FILE="$HOME/oracle-a1-launch-success.json"

echo "════════════════════════════════════════════"
echo "   🎯 A1.Flex 抢机进度  ($(date '+%m-%d %H:%M'))"
echo "════════════════════════════════════════════"

# 1. 是否已抢到
if [ -f "$SUCCESS_FILE" ]; then
  echo "🎉 已抢到! 详情: $SUCCESS_FILE"
  grep -o '"public-ip": "[^"]*"' "$SUCCESS_FILE" | head -1
  exit 0
fi

# 2. 进程状态
PID=$(pgrep -f 'oracle-a1-grab[^ ]*\.sh' | head -1)
if [ -n "$PID" ]; then
  # 运行时长
  ELAPSED=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')
  echo "状态      : 🟢 运行中 (PID $PID, 已跑 ${ELAPSED:-?})"
else
  echo "状态      : 🔴 未运行! (重启: nohup bash ~/coding/Foundations/AgentSetups/oracle-vpn/oracle-a1-grab.sh > ~/oracle-a1-grab.out 2>&1 &)"
fi

# 3. 统计
if [ -f "$LOG" ]; then
  ATTEMPTS=$(grep -c "尝试 launch" "$LOG")
  CAP=$(grep -c "容量不足" "$LOG")
  RATE=$(grep -c "被限流" "$LOG")
  START=$(head -1 "$LOG" | grep -o '\[.*\]' | tr -d '[]')
  echo "开始时间  : ${START:-?}"
  echo "尝试轮次  : ${ATTEMPTS} 次"
  echo "  └ 容量不足: ${CAP} 次  |  被限流: ${RATE} 次"
  echo ""
  echo "最近 5 条日志:"
  tail -5 "$LOG" | sed 's/^/  /'
else
  echo "⚠️  日志不存在: $LOG"
fi
echo "════════════════════════════════════════════"
echo "提示: 抢到会自动弹 macOS 通知; 无需一直盯着。"
