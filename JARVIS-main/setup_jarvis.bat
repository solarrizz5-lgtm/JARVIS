@echo off
:: ============================================================
:: JARVIS Environment & Dependency Setup Script
:: ============================================================

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

echo ============================================================
echo [JARVIS] Initializing Environment and System Checks...
echo ============================================================

python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [JARVIS] Python not found. Installing Python 3.11.9 automatically...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%temp%\python_installer.exe'"
    start /wait "" "%temp%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0
    del "%temp%\python_installer.exe"
    set "PATH=%PATH%;C:\Program Files\Python311\;C:\Program Files\Python311\Scripts\"
) else (
    echo [JARVIS] Python runtime detected.
)

set "CONFIG_PATH=%~dp0jarvis_config.json"

:: Check for OpenRouter API Key
if "%OPENROUTER_API_KEY%"=="" (
    echo.
    echo ============================================================
    echo [JARVIS CONFIGURATION] OPENROUTER_API_KEY not detected!
    echo ============================================================
    echo To use Nemotron via OpenRouter, get your key at: https://openrouter.ai/
    echo ============================================================
    echo.
    set "OR_USER_KEY="
    set /p "OR_USER_KEY=Paste your OpenRouter API Key here (or press Enter to skip): "
    
    if defined OR_USER_KEY (
        for /f "tokens=*" %%a in ("%OR_USER_KEY%") do set "OR_USER_KEY=%%a"
        setx OPENROUTER_API_KEY "%OR_USER_KEY%" >nul
        set "OPENROUTER_API_KEY=%OR_USER_KEY%"
        
        python -c "import json, os; path=r'%CONFIG_PATH%'; data = json.load(open(path)) if os.path.exists(path) else {'model_name': 'nvidia/nemotron-3-ultra-550b-a55b:free'}; data['openrouter_api_key'] = r'%OR_USER_KEY%'; json.dump(data, open(path, 'w'), indent=4)"
        echo [JARVIS] OpenRouter API Key saved successfully!
    )
)

:: Check for Google Gemini API Key
if "%GEMINI_API_KEY%"=="" (
    echo.
    echo ============================================================
    echo [JARVIS CONFIGURATION] GEMINI_API_KEY not detected!
    echo ============================================================
    echo To use Google Gemini models, get your free key at: https://aistudio.google.com/
    echo ============================================================
    echo.
    set "GEM_USER_KEY="
    set /p "GEM_USER_KEY=Paste your Gemini API Key here (or press Enter to skip): "
    
    if defined GEM_USER_KEY (
        for /f "tokens=*" %%a in ("%GEM_USER_KEY%") do set "GEM_USER_KEY=%%a"
        setx GEMINI_API_KEY "%GEM_USER_KEY%" >nul
        set "GEMINI_API_KEY=%GEM_USER_KEY%"
        
        python -c "import json, os; path=r'%CONFIG_PATH%'; data = json.load(open(path)) if os.path.exists(path) else {'model_name': 'nvidia/nemotron-3-ultra-550b-a55b:free'}; data['gemini_api_key'] = r'%GEM_USER_KEY%'; json.dump(data, open(path, 'w'), indent=4)"
        echo [JARVIS] Gemini API Key saved successfully!
    )
)

echo.
echo [JARVIS] Upgrading pip and checking project dependencies...
python -m pip install --upgrade pip --quiet

if exist "requirements.txt" (
    python -m pip install -r requirements.txt --quiet
) else (
    python -m pip install requests pyautogui pyttsx3 sounddevice numpy SpeechRecognition Pillow keyboard pywin32 --quiet
)

echo.
echo ============================================================
echo [JARVIS] Setup complete! You can now run 'run_jarvis_gui.bat'.
echo ============================================================
echo.
pause