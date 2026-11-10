@echo off
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-Mod.ps1" -GamePath "%~dp0.." %*
exit /b %errorlevel%
