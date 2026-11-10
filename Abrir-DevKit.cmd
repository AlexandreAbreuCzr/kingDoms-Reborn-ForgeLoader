@echo off
cd /d "%~dp0"
python modkit\wizard.py
if errorlevel 1 pause
