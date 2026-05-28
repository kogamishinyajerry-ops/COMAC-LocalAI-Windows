@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows - Startup Script
REM  Model: qwen:7b-q4_K_M
REM  Environment: Windows 10 x64, 16GB RAM, air-gapped
REM ============================================================================

title COMAC AI - Document Processing Platform

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================
echo    COMAC Local AI Document Processing Platform
echo    Windows Offline Deployment
echo ==============================================================
echo.

REM ============================================================================
REM  0. Check .venv and directories
REM ============================================================================
echo [0/4] Checking runtime environment...

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo   [ERROR] .venv not found - project not initialized
    echo.
    if exist "%SCRIPT_DIR%install-offline.bat" (
        echo   Please run install-offline.bat first to complete setup.
    ) else (
        echo   Please run pre-deploy.bat on an internet-connected machine first.
    )
    pause
    exit /b 1
)
echo         [OK] .venv exists

for %%D in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)
echo         [OK] Directories ready
echo.

REM ============================================================================
REM  1. Start Ollama service
REM ============================================================================
echo [1/4] Checking Ollama service...

set "OLLAMA_HOST=127.0.0.1:11435"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"
set "OLLAMA_BIN=tools\ollama\ollama.exe"

REM Prefer built-in Ollama, fall back to system PATH
if exist "%OLLAMA_BIN%" (
    set "OLLAMA_CMD=%OLLAMA_BIN%"
) else (
    set "OLLAMA_CMD=ollama"
)

powershell -NoProfile -Command "try{$r=iwr "http://%OLLAMA_HOST%/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto :ollama_ok

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul

echo         Ollama not running, starting...
if exist "%OLLAMA_BIN%" (
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
) else (
    start /B "" ollama serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
)

REM Wait for Ollama (up to 30 seconds)
for /L %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    powershell -NoProfile -Command "try{$r=iwr "http://%OLLAMA_HOST%/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
    if not errorlevel 1 goto :ollama_ok
)

echo.
echo   [ERROR] Ollama startup failed
echo   Please run setup.bat to reinitialize
echo   Log: logs\ollama.log
pause
exit /b 1

:ollama_ok
echo         [OK] Ollama service running
echo.

REM ============================================================================
REM  2. Verify qwen:7b-q4_K_M model
REM ============================================================================
echo [2/4] Verifying model (qwen:7b-q4_K_M^)...

%OLLAMA_CMD% list 2>nul | findstr /C:"qwen:7b-q4_K_M" >nul
if errorlevel 1 (
    echo.
    echo   [ERROR] qwen model not found
    echo   Please run setup.bat to initialize the model
    pause
    exit /b 1
)
echo         [OK] qwen model ready
echo.

REM ============================================================================
REM  3. Check Gradio auth (read from .env)
REM ============================================================================
echo [3/4] Checking access authentication...

if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" set "%%A=%%B"
    )
)

if defined GRADIO_USER if defined GRADIO_PASS (
    echo         [OK] Auth configured (user: %GRADIO_USER%^)
    if "%GRADIO_PASS%"=="change_me_123" (
        echo         [WARN] Password is still the default, edit .env to change GRADIO_PASS
    )
) else (
    echo         [WARN] Auth not configured
    echo         Set GRADIO_USER and GRADIO_PASS in .env
)
echo.

REM ============================================================================
REM  4. Start Gradio Web UI
REM ============================================================================
echo [4/4] Starting Gradio UI...

REM Set Ollama optimization env vars
set "OLLAMA_NUM_PARALLEL=1"
set "OLLAMA_MAX_LOADED_MODELS=1"
set "OLLAMA_KEEP_ALIVE=5m"

REM Clean up port 7860 (only kill Python processes)
set "PORT_PID="
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":7860.*LISTENING"') do (
    set "PORT_PID=%%a"
)
if defined PORT_PID (
    for /f "tokens=1" %%n in ('tasklist /FI "PID eq !PORT_PID!" /FO CSV /NH 2^>nul ^| findstr /I "python"') do (
        echo         Port 7860 occupied by Python process (PID=!PORT_PID!^), terminating...
        taskkill /PID !PORT_PID! /F >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
)

REM Launch app
echo         Starting (first run may take 10-20 seconds^)...
start "COMAC AI" .venv\Scripts\python.exe app.py

REM Wait for Gradio
for /L %%i in (1,1,20) do (
    timeout /t 2 /nobreak >nul
    powershell -NoProfile -Command "try{$r=iwr "http://localhost:7860" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
    if not errorlevel 1 goto :gradio_ok
)

echo.
echo         Gradio is starting slowly, please wait and visit: http://localhost:7860
goto :launch_done

:gradio_ok
echo         [OK] Gradio ready
start http://localhost:7860

:launch_done
echo.
echo ==============================================================
echo     Deployment successful!
echo.
echo     Visit: http://localhost:7860
if defined GRADIO_USER echo     Login: %GRADIO_USER%
echo.
echo     To stop: close this window or end python.exe in Task Manager
echo ==============================================================
echo.

REM --------------------------------------------------------------------------
REM Auto-register opencode in user PATH (silent, first-time only)
REM --------------------------------------------------------------------------
powershell -NoProfile -Command ^
    "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); " ^
    "if ($p -notlike '*%~dp0*') { " ^
    "    [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';%~dp0;'), 'User'); " ^
    "    Write-Host ''; " ^
    "    Write-Host '---'; " ^
    "    Write-Host 'Terminal AI chat is ready'; " ^
    "    Write-Host ''; " ^
    "    Write-Host '  Type opencode in any PowerShell to start AI chat'; " ^
    "    Write-Host ''; " ^
    "    Write-Host '  If PowerShell is already open,'; " ^
    "    Write-Host '  close and reopen it for the command to take effect'; " ^
    "    Write-Host '---'; " ^
    "    Write-Host '' } " >nul

pause
