@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "SKILL_ROOT=%SCRIPT_DIR%..\.."
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

REM -- Entry preflight: skill self-update -------------------------------------
REM Keep this in sync with create_session.sh. 0 continues, 100 means updated and
REM must be propagated; other updater failures do not block session creation.
if "%DIAGNOSE_SKIP_UPDATE%"=="1" goto after_update
%PY% "%SKILL_ROOT%\scripts\updater\check_and_update.py"
set "UPDATER_CODE=%ERRORLEVEL%"
if "%UPDATER_CODE%"=="100" exit /b 100

:after_update
REM Learnings upload is best-effort background work, after updater and before
REM create_session.py to avoid racing with skill directory replacement.
start "" /b %PY% "%SKILL_ROOT%\scripts\learnings\upload.py" >nul 2>nul

%PY% "%SCRIPT_DIR%create_session.py" %*
exit /b %errorlevel%
