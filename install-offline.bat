@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM COMAC-LocalAI-Windows - Offline One-Click Installer
REM Run this on the air-gapped Windows 10 machine.
REM First-time install takes 10-15 minutes.
REM =============================================================================

title COMAC AI - Offline Installer

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ============================================================
echo   COMAC-LocalAI-Windows - Offline One-Click Installer
echo   Target: %SCRIPT_DIR%
echo ============================================================
echo.
echo   This script will set up the complete runtime environment.
echo   Estimated time: 10-15 minutes (depends on disk speed^)
echo.

REM =============================================================================
REM Step 1: Check / Install Python 3.11+
REM =============================================================================
echo ==============================================================
echo   [1/8] Checking Python environment
echo ==============================================================

set "PYTHON_EXE="
set "PYTHON_VER="

REM Check if system already has Python 3.11+
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PYTHON_VER=%%v"
    if defined PYTHON_VER (
        if !PYTHON_VER! GEQ 11 (
            set "PYTHON_EXE=python"
            echo   [OK] System Python 3.!PYTHON_VER! found, skip install
            goto :venv_create
        )
    )
)

REM No system Python 3.11+, try bundled installer (3.11 or 3.12)
set "PY_INSTALLER="
for %%f in ("%SCRIPT_DIR%tools\python-3.1*-amd64.exe") do (
    if exist "%%f" set "PY_INSTALLER=%%f"
)

if not defined PY_INSTALLER (
    echo   [ERROR] No Python found and no installer in tools\
    echo.
    echo   Please install Python 3.11+ manually:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo         Installing Python from bundled installer...
echo         File: %PY_INSTALLER%
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0

REM Try to locate the installed Python
for %%v in (312 311) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
        for /f "delims=" %%V in ('"%PYTHON_EXE%" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PYTHON_VER=%%V"
        echo   [OK] Python 3.!PYTHON_VER! installed
        goto :venv_create
    )
)

echo   [ERROR] Python installation failed.
echo          Install Python 3.11+ manually and re-run this script.
pause
exit /b 1

:venv_create

REM =============================================================================
REM Step 2: Create .venv and install dependencies offline
REM =============================================================================
echo ==============================================================
echo   [2/8] Creating virtual environment and installing dependencies
echo ==============================================================

REM If .venv already exists with matching version, skip
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    for /f "delims=" %%v in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "VENV_VER=%%v"
    if defined VENV_VER (
        if "!VENV_VER!"=="!PYTHON_VER!" (
            echo   [OK] .venv exists with matching version - Python 3.!VENV_VER!
            echo         Verifying dependency integrity...
            "%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import gradio; import ollama; import pandas; print('OK')" 2>nul
            if not errorlevel 1 goto :venv_done
            echo         Dependencies incomplete, will reinstall...
            rmdir /s /q "%SCRIPT_DIR%.venv" 2>nul
        ) else (
            echo         .venv version mismatch - 3.!VENV_VER! vs 3.!PYTHON_VER! - rebuilding...
            rmdir /s /q "%SCRIPT_DIR%.venv" 2>nul
        )
    )
)

echo         Creating .venv...
"%PYTHON_EXE%" -m venv "%SCRIPT_DIR%.venv" --clear >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] .venv creation failed
    pause
    exit /b 1
)
echo   [OK] .venv created

REM Offline install Python dependencies
if not exist "%SCRIPT_DIR%python-wheels\" (
    echo   [ERROR] python-wheels\ directory not found
    echo          The offline bundle is missing dependency wheels.
    echo          Please rebuild with build-offline-package.bat on an internet machine.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%requirements.lock.txt" (
    echo   [ERROR] requirements.lock.txt not found
    echo          The offline bundle is missing the lock file.
    echo          Please rebuild with build-offline-package.bat on an internet machine.
    pause
    exit /b 1
)

echo         Installing Python dependencies offline (~2-5 min^)...
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install --upgrade pip --quiet 2>nul
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install --no-index --find-links="%SCRIPT_DIR%python-wheels" -r "%SCRIPT_DIR%requirements.lock.txt" --quiet --disable-pip-version-check
if errorlevel 1 (
    echo   [ERROR] Dependency install failed
    echo          Check that python-wheels\ contains all required wheels.
    echo          Rebuild the offline bundle on an internet machine if needed.
    pause
    exit /b 1
)

REM Verify core dependencies
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import gradio; import ollama; import pandas; import docx; import pptx; import openpyxl; import pdfplumber; import jinja2; import numpy; print('OK')" 2>nul
if errorlevel 1 (
    echo   [ERROR] Core dependency verification failed
    echo          The requirements.lock.txt may be incomplete.
    pause
    exit /b 1
)
echo   [OK] Python dependencies installed

:venv_done
echo.

REM =============================================================================
REM Step 3: Create runtime directories
REM =============================================================================
echo ==============================================================
echo   [3/8] Creating runtime directories
echo ==============================================================

for %%D in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)
echo   [OK] Runtime directories created
echo.

REM =============================================================================
REM Step 4: Extract Ollama
REM =============================================================================
echo ==============================================================
echo   [4/8] Initializing built-in Ollama
echo ==============================================================

if exist "%SCRIPT_DIR%tools\ollama\ollama.exe" (
    echo   [OK] Ollama already extracted
) else (
    if not exist "%SCRIPT_DIR%tools\ollama-windows-amd64.zip" (
        echo   [ERROR] tools\ollama-windows-amd64.zip not found
        echo          The offline bundle is missing the Ollama package.
        pause
        exit /b 1
    )
    echo         Extracting Ollama (~1-2 min^)...
    powershell -NoProfile -Command "Expand-Archive -Force '%SCRIPT_DIR%tools\ollama-windows-amd64.zip' '%SCRIPT_DIR%tools\ollama'"
    if errorlevel 1 (
        echo   [ERROR] Ollama extraction failed, check disk space.
        pause
        exit /b 1
    )
    echo   [OK] Ollama extracted
)

REM =============================================================================
REM Step 5: Install VC++ Redistributable
REM =============================================================================
echo ==============================================================
echo   [5/8] Installing Visual C++ Runtime
echo ==============================================================

if exist "%SCRIPT_DIR%tools\vc_redist.x64.exe" (
    echo         Installing VC++ Runtime silently...
    "%SCRIPT_DIR%tools\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ Runtime installed
) else if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         Installing VC++ Runtime silently...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ Runtime installed
) else (
    echo   [INFO] VC++ Runtime not found, skipped
    echo         If Ollama fails to start, install VC++ Redistributable manually.
)
echo.

REM =============================================================================
REM Step 6: Start Ollama service
REM =============================================================================
echo ==============================================================
echo   [6/8] Starting Ollama service
echo ==============================================================

set "OLLAMA_BIN=%SCRIPT_DIR%tools\ollama\ollama.exe"
set "OLLAMA_HOST=127.0.0.1:11435"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

REM Check if port 11435 already has a service
powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama service already running (port 11435^)
    goto :ollama_ready
)

echo         Starting Ollama service (port 11435^)...
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul
start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1

REM Wait for Ollama (up to 40 seconds)
for /L %%i in (1,1,20) do (
    timeout /t 2 /nobreak >nul
    powershell -NoProfile -Command "try{$r=iwr "http://127.0.0.1:11435/api/version" -TimeoutSec 3 -UseBasicParsing;exit 0}catch{exit 1}" >nul 2>&1
    if not errorlevel 1 goto :ollama_ready
)

echo   [WARN] Ollama startup timed out, continuing...
echo         Check logs\ollama.log if later steps fail.
goto :skip_ollama

:ollama_ready
echo   [OK] Ollama service ready (port 11435^)
echo.

REM =============================================================================
REM Step 7: Create qwen3:4b-q4_K_M model
REM =============================================================================
echo ==============================================================
echo   [7/8] Creating qwen3:4b-q4_K_M model
echo ==============================================================

"%OLLAMA_BIN%" list 2>nul | findstr /C:"qwen3:4b-q4_K_M" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen3:4b-q4_K_M model already exists
) else (
    if not exist "%SCRIPT_DIR%ollama-models\Modelfile" (
        echo   [ERROR] ollama-models\Modelfile not found
        echo          The offline bundle is missing the model definition file.
        pause
        exit /b 1
    )
    if not exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo   [ERROR] No .gguf model file found in ollama-models\
        echo.
        echo   Place qwen3-4b-instruct-q4_k_m.gguf in ollama-models\
        echo   Download: https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF
        pause
        exit /b 1
    )

    echo         Creating model from local GGUF file (~1-3 min^)...
    "%OLLAMA_BIN%" create qwen3:4b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
    if errorlevel 1 (
        echo   [ERROR] Model creation failed
        echo          Check that the GGUF filename matches the Modelfile FROM line.
        echo          Expected: qwen3-4b-instruct-q4_k_m.gguf
        pause
        exit /b 1
    )
    echo   [OK] qwen3:4b-q4_K_M model created
)

REM Try to create embedding model (optional, failure is non-blocking)
"%OLLAMA_BIN%" pull nomic-embed-text 2>nul
if errorlevel 1 (
    echo   [INFO] Embedding model nomic-embed-text not available (requires internet^)
    echo         RAG will use main model qwen3:4b-q4_K_M for embeddings.
) else (
    echo   [OK] nomic-embed-text ready
)
echo.

:skip_ollama

REM =============================================================================
REM Step 8: Generate config
REM =============================================================================
echo ==============================================================
echo   [8/8] Generating configuration
echo ==============================================================

REM Set Ollama optimization env vars
setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

if not exist "%SCRIPT_DIR%.env" (
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
    ) > "%SCRIPT_DIR%.env"
    echo   [OK] .env generated
    echo.
    echo   +------------------------------------------------------+
    echo   |  [IMPORTANT] Admin password: !RANDOM_PASS!                  |
    echo   |  Save this password. Edit .env to change it later.   |
    echo   +------------------------------------------------------+
    echo.
) else (
    echo   [OK] .env exists, preserving existing config
)
echo.

REM =============================================================================
REM Done
REM =============================================================================
echo ============================================================
echo   Offline installation complete!
echo ============================================================
echo.
echo   Environment status:
echo   - Python:   3.!PYTHON_VER!
echo   - .venv:    ready
echo   - Ollama:   tools\ollama\ollama.exe (port: 11435^)
echo   - Models:   ollama-cache\
echo   - LLM:      qwen3:4b-q4_K_M
echo   - Auth:     admin / ^(see .env^)
echo.
echo   Next steps:
echo   1. Double-click start.bat to launch the Web UI
echo   2. Visit http://localhost:7860
echo   3. Or type 'opencode' in PowerShell for terminal chat
echo.
echo   Troubleshooting:
echo   - Logs:     logs\ollama.log
echo   - Reinstall: delete .venv and run install-offline.bat again
echo.
echo ============================================================

pause
exit /b 0
