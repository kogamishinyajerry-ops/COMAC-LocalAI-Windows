@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows - Internet Machine Initialization
REM  Model: qwen3:4b-q4_K_M
REM
REM  Usage: Run once on an internet-connected machine for full setup.
REM  After completion, copy the entire project directory to the air-gapped machine.
REM ============================================================================

title COMAC AI - Online Initialization

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  Pre-check: Python
REM ============================================================================
echo.
echo ==============================================================
echo   Welcome to COMAC AI Initialization
echo   Requires internet connection (~20-30 minutes^)
echo ==============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found
    echo   Please install Python 3.11+: https://www.python.org/ftp/python/
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PY_VER=%%v"
if !PY_VER! LSS 11 (
    echo   [ERROR] Python version too low, need 3.11+
    pause
    exit /b 1
)
echo   [OK] Python 3.!PY_VER! ready

REM ============================================================================
REM  Step 1: Create / Update .venv
REM ============================================================================
echo.
echo ==============================================================
echo   [1/6] Creating Python virtual environment
echo ==============================================================

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    for /f "delims=" %%v in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "VENV_VER=%%v"
    if defined VENV_VER (
        if "!VENV_VER!"=="!PY_VER!" (
            echo         .venv exists with matching version (Python 3.!VENV_VER!^)
            echo         Skipping creation, will update dependencies...
            goto :update_deps
        ) else (
            echo         .venv version mismatch, deleting and recreating...
            rmdir /S /Q "%SCRIPT_DIR%.venv" 2>nul
        )
    )
)

echo         Creating .venv...
python -m venv .venv --clear >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] .venv creation failed
    pause
    exit /b 1
)
echo   [OK] .venv created (Python 3.!PY_VER!^)

:update_deps
echo.
echo ==============================================================
echo   [2/6] Installing Python dependencies
echo ==============================================================

echo         Installing all dependencies (~5-10 min^)...
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install --upgrade pip --quiet 2>nul
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo   [ERROR] Dependency install failed, check internet connection
    pause
    exit /b 1
)

REM Verify core dependencies
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import gradio; import ollama; import pandas; print('OK')" 2>nul
if errorlevel 1 (
    echo   [ERROR] Dependency verification failed
    pause
    exit /b 1
)
echo   [OK] Python dependencies installed
echo.

REM ============================================================================
REM  Step 3: Extract Ollama
REM ============================================================================
echo ==============================================================
echo   [3/6] Initializing Ollama
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
    echo   [OK] Ollama extracted
)

REM Install VC++ Redistributable
if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         Installing VC++ Runtime...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ Runtime installed
)

REM ============================================================================
REM  Step 4: Start Ollama service
REM ============================================================================
echo ==============================================================
echo   [4/6] Starting Ollama service
echo ==============================================================

set "OLLAMA_BIN=%SCRIPT_DIR%tools\ollama\ollama.exe"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama service already running
) else (
    echo         Starting Ollama service (port 11435^)...
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
        if not errorlevel 1 goto :ollama_ready
    )
    echo   [WARN] Ollama startup timed out, continuing...
)
:ollama_ready
echo   [OK] Ollama service ready
echo.

REM ============================================================================
REM  Step 5: Download qwen3:4b-q4_K_M model
REM ============================================================================
echo ==============================================================
echo   [5/6] Downloading qwen3:4b-q4_K_M model (~2.5 GB^)
echo ==============================================================

"%OLLAMA_BIN%" list 2>nul | findstr /C:"qwen3:4b-q4_K_M" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen3 model already in Ollama cache
) else (
    if exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo         Local GGUF file found, creating model...
        if exist "%SCRIPT_DIR%ollama-models\Modelfile" (
            "%OLLAMA_BIN%" create qwen3:4b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [ERROR] Model creation failed
                pause
                exit /b 1
            )
            echo   [OK] qwen3:4b-q4_K_M model created
        )
    ) else (
        echo         Downloading from Ollama registry (~2.5 GB^)
        echo         This will take a while, please do not close this window.
        echo.
        "%OLLAMA_BIN%" pull qwen3:4b-q4_K_M
        if errorlevel 1 (
            echo.
            echo   [ERROR] Model download failed
            echo   Check internet connection and re-run pre-deploy.bat
            pause
            exit /b 1
        )
        echo   [OK] qwen3:4b-q4_K_M model downloaded
    )
)
    
    REM Try downloading embedding model (optional, non-blocking)
    echo         Downloading embedding model (optional^)...
    "%OLLAMA_BIN%" pull nomic-embed-text 2>nul
    if errorlevel 1 (
        echo   [INFO] Embedding model nomic-embed-text download failed
        echo         RAG will use main model qwen3:4b-q4_K_M for embeddings.
    ) else (
        echo   [OK] nomic-embed-text downloaded
    )
echo.

REM ============================================================================
REM  Step 6: Initialize configuration
REM ============================================================================
echo ==============================================================
echo   [6/6] Initializing configuration
echo ==============================================================

setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

for %%D in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)

if not exist ".env" (
    REM Generate random 16-char password via PowerShell
    for /f "delims=" %%P in ('powershell -NoProfile -Command "-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 16 | %%{[char]$_})"') do set "RANDOM_PASS=%%P"
    (
        echo # COMAC AI Configuration
        echo # Auto-generated on first deploy
        echo GRADIO_USER=admin
        echo GRADIO_PASS=!RANDOM_PASS!
        echo COMAC_MODEL=qwen3:4b-q4_K_M
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
echo.
echo ==============================================================
echo   Online initialization complete!
echo ==============================================================
echo.
echo   The project directory now contains a complete runtime:
echo   - .venv\                  Python virtual environment (3.!PY_VER!^)
echo   - tools\ollama\          Ollama executable
echo   - Ollama model cache     qwen3:4b-q4_K_M
echo.
echo   Next steps:
echo   1. Edit GRADIO_PASS in .env
echo   2. Copy the entire project directory to the air-gapped machine
echo   3. On the air-gapped machine, run setup.bat to verify
echo   4. Double-click start.bat to launch
echo.
echo   Air-gapped machine Python version requirement: Python 3.!PY_VER! (must match^)
echo.
pause
