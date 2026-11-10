@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0KingdomsToolkit.ps1" -Mode Compatibility
set "toolkit_exit=%errorlevel%"
pause
exit /b %toolkit_exit%
