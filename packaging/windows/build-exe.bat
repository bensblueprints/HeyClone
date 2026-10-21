@echo off
rem Build a standalone Windows GUI executable for HeyClone (single .exe).
rem Run from anywhere; produces dist\HeyClone.exe in the project root.
setlocal
cd /d "%~dp0..\.."

where python >nul 2>nul || (echo Python 3.9+ is required. & exit /b 1)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name HeyClone --paths . packaging\heyclone_gui_entry.py
if errorlevel 1 exit /b 1

echo.
echo Built: %CD%\dist\HeyClone.exe
