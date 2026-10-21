@echo off
rem HeyClone Windows installer (launcher for install.py)
setlocal
set "ROOT=%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python "%ROOT%\install.py" %*
    exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%ROOT%\install.py" %*
    exit /b %errorlevel%
)

echo Python 3.9+ is required. Install it from https://www.python.org and re-run.
exit /b 1
