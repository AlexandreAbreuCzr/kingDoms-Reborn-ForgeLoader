@echo off
where python.exe >nul 2>nul
if errorlevel 1 (
    echo A ferramenta de reparo precisa de Python 3.10 ou superior.
    pause
    exit /b 1
)
python.exe "%~dp0Ferramentas\repair_save_players.py" gui
if errorlevel 1 pause
