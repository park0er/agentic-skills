#!/usr/bin/env bash
# _check_env.sh — 通用环境检查，供 auth 目录下各 .sh 脚本 source 调用
# 用法：
#   source "$(dirname "${BASH_SOURCE[0]}")/_check_env.sh"
#   _check_env_python            # 检查并导出 PYTHON_BIN（版本 >= 3.9，不满足尝试自动安装）
#   _check_env_playwright        # 检查并安装 playwright 包和 chromium 浏览器
#
# 调用后 PYTHON_BIN 变量可直接使用。

_install_python() {
  echo "[runner] Python >= 3.9 not found, attempting auto-install..."

  if command -v brew >/dev/null 2>&1; then
    echo "[runner] Homebrew detected, running: brew upgrade python3 || brew install python3"
    brew upgrade python3 2>/dev/null || brew install python3
    return $?
  fi

  # macOS 但没有 Homebrew，先安装 Homebrew 再安装 Python
  if [[ "$(uname)" == "Darwin" ]]; then
    echo "[runner] macOS detected but Homebrew not found. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if ! command -v brew >/dev/null 2>&1; then
      # Apple Silicon 的 brew 路径在 /opt/homebrew/bin，可能未加入 PATH
      if [[ -x "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
      elif [[ -x "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
      else
        echo "[runner] Homebrew installed but brew not found in PATH. Please restart your shell." >&2
        return 1
      fi
    fi
    echo "[runner] Homebrew ready, running: brew install python3"
    brew install python3
    return $?
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "[runner] apt-get detected, running: sudo apt-get install -y python3"
    sudo apt-get install -y python3
    return $?
  fi

  if command -v yum >/dev/null 2>&1; then
    echo "[runner] yum detected, running: sudo yum install -y python3"
    sudo yum install -y python3
    return $?
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "[runner] dnf detected, running: sudo dnf install -y python3"
    sudo dnf install -y python3
    return $?
  fi

  if command -v pacman >/dev/null 2>&1; then
    echo "[runner] pacman detected, running: sudo pacman -S --noconfirm python"
    sudo pacman -S --noconfirm python
    return $?
  fi

  echo "[runner] No supported package manager found (brew/apt-get/yum/dnf/pacman)." >&2
  echo "[runner] Please install Python >= 3.9 manually: https://www.python.org/downloads/" >&2
  return 1
}

_check_env_python() {
  local bin=""

  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
      echo "[runner] python not found: $PYTHON_BIN" >&2
      return 1
    fi
    bin="$PYTHON_BIN"
  else
    if command -v python3 >/dev/null 2>&1; then
      bin="python3"
    elif command -v python >/dev/null 2>&1; then
      bin="python"
    else
      _install_python || return 1
      # 重新探测
      if command -v python3 >/dev/null 2>&1; then
        bin="python3"
      elif command -v python >/dev/null 2>&1; then
        bin="python"
      else
        echo "[runner] Python installed but not found in PATH. Please restart your shell." >&2
        return 1
      fi
    fi
  fi

  # 版本检查 >= 3.9
  local ver
  ver="$("$bin" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)"
  local major minor
  major="$(echo "$ver" | cut -d. -f1)"
  minor="$(echo "$ver" | cut -d. -f2)"
  if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 9 ]]; }; then
    echo "[runner] Python $ver detected, but >= 3.9 is required. Attempting upgrade..."
    _install_python || return 1
    # 重新探测升级后的版本
    if command -v python3 >/dev/null 2>&1; then
      bin="python3"
    fi
    ver="$("$bin" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)"
    major="$(echo "$ver" | cut -d. -f1)"
    minor="$(echo "$ver" | cut -d. -f2)"
    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 9 ]]; }; then
      echo "[runner] Upgrade failed, still on Python $ver. Please upgrade manually: https://www.python.org/downloads/" >&2
      return 1
    fi
  fi

  echo "[runner] Python $ver OK"
  export PYTHON_BIN="$bin"
}

_check_env_playwright_launch() {
  "$PYTHON_BIN" - <<'PY'
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    browser.close()
PY
}

_check_env_playwright() {
  local missing
  missing="$("$PYTHON_BIN" - <<'PY'
import importlib.util
mods={"playwright":"playwright"}
missing=[pkg for pkg,mod in mods.items() if importlib.util.find_spec(mod) is None]
print(" ".join(missing))
PY
)"
  if [[ -n "$missing" ]]; then
    echo "[runner] installing missing packages: $missing"
    "$PYTHON_BIN" -m pip install --upgrade pip || return 1
    "$PYTHON_BIN" -m pip install $missing || return 1
  fi

  local launch_log
  launch_log="$(mktemp "${TMPDIR:-/tmp}/diagnose-playwright-launch.XXXXXX")"

  if _check_env_playwright_launch >"$launch_log" 2>&1; then
    rm -f "$launch_log"
    return 0
  fi

  if grep -q -E "Executable doesn't exist|playwright install" "$launch_log"; then
    echo "[runner] playwright chromium not ready, installing chromium..."
    if ! "$PYTHON_BIN" -m playwright install chromium; then
      echo "[runner] playwright chromium install failed." >&2
      cat "$launch_log" >&2
      rm -f "$launch_log"
      return 1
    fi

    if _check_env_playwright_launch >"$launch_log" 2>&1; then
      rm -f "$launch_log"
      return 0
    fi

    echo "[runner] playwright chromium still cannot launch after install." >&2
    cat "$launch_log" >&2
    rm -f "$launch_log"
    return 1
  fi

  echo "[runner] playwright chromium cannot launch." >&2
  cat "$launch_log" >&2
  echo "[runner] Please check local browser permissions or run:" >&2
  echo "         $PYTHON_BIN -m playwright install chromium" >&2
  rm -f "$launch_log"
  return 1
}
