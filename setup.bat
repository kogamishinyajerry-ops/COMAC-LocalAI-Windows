@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows - Deployment Initialization Script
REM
REM  Purpose:
REM    - Air-gapped machine: verify all components ready, start services
REM    - Internet machine (first run): run pre-deploy.bat for full init
REM
REM  Model: qwen:7b-q4_K_M | Python 3.11+ | Windows 10+
REM ============================================================================

title COMAC AI - Deployment Initialization

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  Step 1: Check Python runtime (must be system Python 3.11+ full install)
REM ============================================================================
echo.
echo ==============================================================
echo   [1/7] Checking Python runtime
echo ==============================================================

set "CHECK_PY="
set "CHECK_PY_VER="

where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "CHECK_PY_VER=%%v"
    if defined CHECK_PY_VER (
        if !CHECK_PY_VER! GEQ 11 (
            set "CHECK_PY=python"
            echo   [OK] System Python 3.!CHECK_PY_VER! found
        )
    )
)

if not defined CHECK_PY (
    REM Try built-in Python installer
    if exist "%SCRIPT_DIR%tools\python-3.11.8-amd64.exe" (
        echo         System Python not found, using built-in installer...
        echo         Installing to %LOCALAPPDATA%\Programs\Python\Python311
        "%SCRIPT_DIR%tools\python-3.11.8-amd64.exe" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0
        if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set "CHECK_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
            for /f "delims=" %%v in ('"%CHECK_PY%" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "CHECK_PY_VER=%%v"
            echo   [OK] Python 3.!CHECK_PY_VER! installed
        ) else (
            echo   [ERROR] Python installation failed
            pause
            exit /b 1
        )
    ) else (
        echo   [ERROR] Python 3.11+ not found
        echo.
        echo   This project requires Python 3.11 or higher.
        echo.
        echo   Download from:
        echo   https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
        echo.
        echo   Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
)

REM Verify .venv Python version matches system Python
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    for /f "delims=" %%v in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "VENV_PY_VER=%%v"
    if defined VENV_PY_VER (
        if not "!VENV_PY_VER!"=="!CHECK_PY_VER!" (
            echo.
            echo   [ERROR] .venv version (!VENV_PY_VER!^) does not match system Python (!CHECK_PY_VER!^)
            echo.
            echo   Please create .venv on this machine, or delete .venv and re-run.
            echo.
            pause
            exit /b 1
        )
        echo   [OK] .venv Python version matches (3.!VENV_PY_VER!^)
    )
)

REM ============================================================================
REM  Step 2: Verify .venv dependency integrity
REM ============================================================================
echo ==============================================================
echo   [2/7] Verifying .venv dependencies
echo ==============================================================

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    REM .venv missing, try offline install from python-wheels
    if exist "%SCRIPT_DIR%python-wheels\" if exist "%SCRIPT_DIR%requirements.lock.txt" (
        echo         Offline wheels found, creating .venv and installing...
        if defined CHECK_PY (
            "!CHECK_PY!" -m venv "%SCRIPT_DIR%.venv" --clear >nul 2>&1
        ) else (
            python -m venv "%SCRIPT_DIR%.venv" --clear >nul 2>&1
        )
        if errorlevel 1 (
            echo   [ERROR] .venv creation failed
            pause
            exit /b 1
        )
        "%SCRIPT_DIR%.venv\Scripts\pip.exe" install --upgrade pip --quiet 2>nul
        "%SCRIPT_DIR%.venv\Scripts\pip.exe" install --no-index --find-links="%SCRIPT_DIR%python-wheels" -r "%SCRIPT_DIR%requirements.lock.txt" --quiet --disable-pip-version-check
        if errorlevel 1 (
            echo   [ERROR] Offline dependency install failed
            echo          Check that python-wheels\ contains all required wheels.
            pause
            exit /b 1
        )
        echo   [OK] .venv created (offline install^)
    ) else (
        echo   [ERROR] .venv not found
        echo.
        echo   Choose one of the following to create the environment:
        echo   1. Run install-offline.bat (for offline bundle deployment^)
        echo   2. Run pre-deploy.bat on an internet-connected machine
        echo.
        pause
        exit /b 1
    )
)

set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM Quick verify core dependencies
"%VENV_PY%" -c "import gradio; import ollama; import pandas; import docx; import pptx; import openpyxl; import pdfplumber; import pymupdf; import jinja2; import numpy; import colorama; print('OK')" 2>nul
if errorlevel 1 (
    echo   [ERROR] .venv dependencies incomplete
    echo.
    echo   Please re-run pre-deploy.bat on an internet-connected machine.
    echo.
    pause
    exit /b 1
)
echo   [OK] .venv dependencies complete
echo.

REM ============================================================================
REM  Step 3: Extract built-in Ollama
REM ============================================================================
echo ==============================================================
echo   [3/7] Initializing built-in Ollama
echo ==============================================================

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul

if exist "%SCRIPT_DIR%tools\ollama\ollama.exe" (
    echo   [OK] Ollama already extracted
) else (
    if not exist "%SCRIPT_DIR%tools\ollama-windows-amd64.zip" (
        echo   [ERROR] tools\ollama-windows-amd64.zip not found
        pause
        exit /b 1
    )
    echo         Extracting Ollama...
    powershell -NoProfile -Command "Expand-Archive -Force '%SCRIPT_DIR%tools\ollama-windows-amd64.zip' '%SCRIPT_DIR%tools\ollama'"
    if errorlevel 1 (
        echo   [ERROR] Ollama extraction failed
        pause
        exit /b 1
    )
    echo   [OK] Ollama extracted
)

REM ============================================================================
REM  Step 4: Install Visual C++ Redistributable
REM ============================================================================
echo ==============================================================
echo   [4/7] Installing Visual C++ Runtime
echo ==============================================================

if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         VC++ installer found, installing silently...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ Runtime installed
) else (
    echo   [INFO] VC++ installer not found, skipping
)
echo.

REM ============================================================================
REM  Step 5: Start Ollama service
REM ============================================================================
echo ==============================================================
echo   [5/7] Starting Ollama service
echo ==============================================================

set "OLLAMA_BIN=%SCRIPT_DIR%tools\ollama\ollama.exe"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

REM Check if Ollama is already running (dedicated port 11435)
powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama service already running
) else (
    echo         Starting Ollama service (port 11435^)...
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [WARN] Ollama startup timed out, continuing...
)
:ollama_ok
echo   [OK] Ollama service ready
echo.

REM ============================================================================
REM  Step 6: Check qwen:7b-q4_K_M model
REM ============================================================================
echo ==============================================================
echo   [6/7] Checking qwen model
echo ==============================================================

"%OLLAMA_BIN%" list 2>nul | findstr /C:"qwen:7b-q4_K_M" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen model ready (Ollama cache^)
) else (
    if exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo         Local GGUF file found, creating model via Modelfile...
        if exist "%SCRIPT_DIR%ollama-models\Modelfile" (
            "%OLLAMA_BIN%" create qwen:7b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [ERROR] Model creation failed
                pause
                exit /b 1
            )
            echo   [OK] qwen:7b-q4_K_M model created
        ) else (
            echo   [ERROR] Modelfile missing
            pause
            exit /b 1
        )
    ) else (
        echo   [ERROR] No GGUF model file found
        echo.
        echo   Run pre-deploy.bat on an internet machine to download the model,
        echo   or place qwen2.5-7b-instruct-q4_k_m.gguf in ollama-models\
        pause
        exit /b 1
    )
)
echo.

REM ============================================================================
REM  Step 7: Initialize configuration
REM ============================================================================
echo ==============================================================
echo   [7/7] Initializing configuration
echo ==============================================================

REM Ollama env vars (current CMD session)
setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

REM Create runtime directories
for %%D in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)

REM Generate .env
if not exist ".env" (
    REM Generate random 16-char password via PowerShell
    for /f "delims=" %%P in ('powershell -NoProfile -Command "-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 16 | %%{[char]$_})"') do set "RANDOM_PASS=%%P"
    (
        echo # COMAC AI Configuration
        echo # Auto-generated on first deploy
        echo GRADIO_USER=admin
        echo GRADIO_PASS=!RANDOM_PASS!
        echo COMAC_MODEL=qwen:7b-q4_K_M
        echo COMAC_EMBED_MODEL=nomic-embed-text
        echo OLLAMA_HOST=127.0.0.1:11435
    ) > .env
    echo   [OK] .env generated
    echo   [IMPORTANT] Initial password: !RANDOM_PASS! ^(save this^)
) else (
    echo   [OK] .env already exists
)

REM ============================================================================
REM  Done
REM ============================================================================
echo ==============================================================
echo   Deployment initialization complete!
echo ==============================================================
echo.
echo   Next steps:
echo   1. Edit GRADIO_PASS in .env to change the password
echo   2. Double-click start.bat to launch the service
echo   3. Visit http://localhost:7860
echo.
echo   Component status:
echo   - Python: !CHECK_PY_VER!  ^(system^)
echo   - .venv:  ready
echo   - Ollama: tools\ollama\ollama.exe
echo   - Model:  qwen:7b-q4_K_M
echo   - Auth:   admin / ^(edit .env to change^)
echo.
pause
