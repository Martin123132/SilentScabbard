@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0set-skin-profile.ps1" -SkinProfile full
echo.
pause
