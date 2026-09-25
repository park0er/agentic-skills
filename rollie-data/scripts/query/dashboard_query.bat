@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PY="

if defined PYTHON_BIN (
  set "PY=%PYTHON_BIN%"
) else (
  where py >nul 2>nul && set "PY=py -3"
  if not defined PY where python >nul 2>nul && set "PY=python"
  if not defined PY where python3 >nul 2>nul && set "PY=python3"
)

if not defined PY (
  echo [runner] python not found
  exit /b 1
)

%PY% "%SCRIPT_DIR%dashboard_query.py" %*
exit /b %errorlevel%
