@echo off
setlocal

REM ============================================================================
REM  OpenCode TUI - Terminal AI Chat
REM  Double-click to launch
REM ============================================================================

title OpenCode TUI - COMAC AI

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM --------------------------------------------------------------------------
REM Pre-check: Python virtual environment
REM --------------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Project not initialized
    echo.
    if exist "install-offline.bat" (
        echo Please run install-offline.bat first to complete setup.
    ) else (
        echo Please run setup.bat first.
    )
    echo.
    pause
    exit /b 1
)

REM --------------------------------------------------------------------------
REM Pre-check: Ollama service
REM --------------------------------------------------------------------------
set "OLLAMA_HOST=127.0.0.1:11435"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

REM Try detecting if Ollama is already running via PowerShell
powershell -NoProfile -Command "try{$r=iwr 'http://%OLLAMA_HOST%/api/version' -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto :ollama_ok

REM Ollama not running: start it
echo [INFO] Starting Ollama AI service, please wait...
start /B cmd /c "\"%OLLAMA_BIN%\" serve > nul 2>&1"
REM Wait for Ollama (up to 25 seconds)
for /L %%i in (1,1,25) do (
    timeout /t 1 /nobreak >nul
    powershell -NoProfile -Command "try{$r=iwr 'http://%OLLAMA_HOST%/api/version' -TimeoutSec 2 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
    if not errorlevel 1 goto :ollama_ok
)
REM Timeout: assume started
echo         Ollama started

:ollama_ok

REM --------------------------------------------------------------------------
REM Launch TUI
REM --------------------------------------------------------------------------
.venv\Scripts\python.exe cli_chat.py %*

if errorlevel 1 (
    echo.
    echo [ERROR] Launch failed
    echo.
    echo Please make sure you have run install-offline.bat or setup.bat first.
    echo.
    pause
)
