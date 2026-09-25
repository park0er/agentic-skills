@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%_check_env.bat" check_python
if errorlevel 1 exit /b 1

call "%SCRIPT_DIR%_check_env.bat" check_playwright

%PY% "%SCRIPT_DIR%check_cookies.py" %*
exit /b %errorlevel%
