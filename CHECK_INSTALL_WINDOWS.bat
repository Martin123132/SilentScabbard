@echo off
setlocal
cd /d "%~dp0"
echo SilentScabbard install check
echo If this reports missing settings or shortcut, run REPAIR_INSTALL_WINDOWS.bat.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0health-check.ps1"
echo.
pause
