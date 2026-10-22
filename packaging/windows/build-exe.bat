@echo off
rem Build a standalone Windows GUI executable for HeyClone (single .exe).
rem Run from anywhere; produces dist\HeyClone.exe in the project root.
setlocal
cd /d "%~dp0..\.."

where python >nul 2>nul || (echo Python 3.9+ is required. & exit /b 1)

python -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python -m pip install -r packaging\requirements-build.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python -c "from heyclone.avatar.opencv import load_face_detector; load_face_detector()"
if errorlevel 1 exit /b 1
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name HeyClone --paths . --collect-all customtkinter --collect-all cv2 packaging\heyclone_gui_entry.py
if errorlevel 1 exit /b 1

echo.
echo Built: %CD%\dist\HeyClone.exe
