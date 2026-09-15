@echo off
:: ============================================================
:: JARVIS GUI Launcher Script
:: ============================================================
cd /d "%~dp0"

:: Check if configuration already exists to avoid looping setup
if not exist "jarvis_config.json" (
    echo [JARVIS] First-time setup required. Launching setup...
    call setup_jarvis.bat
)

:: Launch using pythonw to suppress the console window
start "" pythonw -m jarvis.gui
exit