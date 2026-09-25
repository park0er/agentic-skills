@echo off
REM _check_env.bat — 通用环境检查，供 auth 目录下各 .bat 脚本 call 调用
REM 用法：
REM   call "%~dp0_check_env.bat" check_python
REM   call "%~dp0_check_env.bat" check_playwright
REM
REM check_python  : 检查 Python 并设置 PY 变量（版本 >= 3.9，不满足尝试自动安装）
REM check_playwright : 检查并安装 playwright 包

setlocal enabledelayedexpansion

if "%1"=="check_python" goto :check_python
if "%1"=="check_playwright" goto :check_playwright
echo [runner] _check_env.bat: unknown command: %1 >&2
exit /b 1

:check_python
  set "PY="
  if defined PYTHON_BIN (
    where "%PYTHON_BIN%" >nul 2>nul
    if errorlevel 1 (
      echo [runner] python not found: %PYTHON_BIN% >&2
      exit /b 1
    )
    set "PY=%PYTHON_BIN%"
    goto :check_version
  )

  where py >nul 2>nul && set "PY=py -3"
  if not defined PY where python >nul 2>nul && set "PY=python"
  if not defined PY where python3 >nul 2>nul && set "PY=python3"

  if not defined PY (
    echo [runner] Python not found, attempting auto-install...
    goto :install_python
  )
  goto :check_version

:install_python
  where winget >nul 2>nul
  if not errorlevel 1 (
    echo [runner] winget detected, running: winget install Python.Python.3
    winget install --id Python.Python.3 -e --source winget
    if errorlevel 1 goto :install_failed
    REM 重新探测
    where py >nul 2>nul && set "PY=py -3"
    if not defined PY where python >nul 2>nul && set "PY=python"
    if not defined PY where python3 >nul 2>nul && set "PY=python3"
    if not defined PY (
      echo [runner] Python installed but not found in PATH. Please restart your terminal. >&2
      exit /b 1
    )
    goto :check_version
  )

  where choco >nul 2>nul
  if not errorlevel 1 (
    echo [runner] Chocolatey detected, running: choco install python3
    choco install python3 -y
    if errorlevel 1 goto :install_failed
    where py >nul 2>nul && set "PY=py -3"
    if not defined PY where python >nul 2>nul && set "PY=python"
    if not defined PY where python3 >nul 2>nul && set "PY=python3"
    if not defined PY (
      echo [runner] Python installed but not found in PATH. Please restart your terminal. >&2
      exit /b 1
    )
    goto :check_version
  )

:install_failed
  echo [runner] No supported package manager found (winget/choco). >&2
  echo [runner] Please install Python ^>= 3.9 manually: https://www.python.org/downloads/ >&2
  exit /b 1

:check_version
  for /f "delims=" %%V in ('%PY% -c "import sys; ok=sys.version_info>=(3,9); print(\"ok\" if ok else \"old:%d.%d\" % sys.version_info[:2])"') do set "VER_CHECK=%%V"
  if not "%VER_CHECK%"=="ok" (
    echo [runner] Python version too old: %VER_CHECK:old:=%. Requires ^>= 3.9.
    echo [runner] Attempting upgrade via package manager...
    set "PY="
    goto :install_python
  )
  echo [runner] Python OK: %VER_CHECK%

  endlocal & set "PY=%PY%"
  exit /b 0

:check_playwright
  set "MISSING_PKGS="
  for /f "delims=" %%M in ('%PY% -c "import importlib.util as u;mods={\"playwright\":\"playwright\"};m=[k for k,v in mods.items() if u.find_spec(v) is None];print(\" \".join(m))"') do set "MISSING_PKGS=%%M"
  if defined MISSING_PKGS (
    echo [runner] installing missing packages: %MISSING_PKGS%
    %PY% -m pip install --upgrade pip
    %PY% -m pip install %MISSING_PKGS%
  )

  REM 检查 chromium 是否安装
  %PY% -m playwright install --dry-run chromium >nul 2>nul
  if errorlevel 1 (
    echo [runner] NOTE: playwright chromium not installed. Run:
    echo          %PY% -m playwright install chromium
    echo          ^(Only needed once. Skip if system Chrome is available.^)
  )

  endlocal
  exit /b 0
