#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[runner] python not found" >&2
    exit 1
  fi
elif ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[runner] python not found: $PYTHON_BIN" >&2
  exit 1
fi

# ── 入口前置:skill 自升级 ──
# DIAGNOSE_SKIP_UPDATE=1 完全旁路;其他情况调 updater。
# updater 退出码约定:
#   0   — 静默通过(无更新/冷却中/网络失败/拿不到锁),继续正常流程
#   100 — 已升级,stdout 含 {"status":"updated",...},sh 层透传给 agent
#   其它 — 升级流程异常,不阻塞诊断,照常走 create_session.py
if [[ "${DIAGNOSE_SKIP_UPDATE:-0}" != "1" ]]; then
  set +e
  "$PYTHON_BIN" "$SKILL_ROOT/scripts/updater/check_and_update.py"
  UPDATER_CODE=$?
  set -e
  if [[ "$UPDATER_CODE" -eq 100 ]]; then
    exit 100
  fi
fi

# learnings 异步后台上传(详见 docs/coupling-map.md §5)
"$PYTHON_BIN" "$SKILL_ROOT/scripts/learnings/upload.py" </dev/null >/dev/null 2>&1 & disown

exec "$PYTHON_BIN" "$SCRIPT_DIR/create_session.py" "$@"
