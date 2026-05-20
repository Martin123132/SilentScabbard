@echo off
setlocal
cd /d "%~dp0"
echo SilentScabbard setup
echo This keeps local data and tries to keep model storage off C: when possible.
echo If you already installed and just need repair, close this and run REPAIR_INSTALL_WINDOWS.bat.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
echo.
pause
