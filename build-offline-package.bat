@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM =============================================================================
REM COMAC-LocalAI-Windows - Build Offline Deployment Package
REM Target: Python 3.12, Windows 10/11 x64, air-gapped
REM Output: offline_bundle/ directory (copy to USB ¡ú air-gapped machine)
REM =============================================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "BUNDLE_DIR=%SCRIPT_DIR%\offline_bundle"
set "TARGET_PY_VER=3.12"

echo.
echo ============================================================
echo   COMAC-LocalAI-Windows - Build Offline Package
echo   Target Python: %TARGET_PY_VER%
echo   Output: %BUNDLE_DIR%
echo ============================================================
echo.

REM =============================================================================
REM Step 1: Check Python 3.11+
REM =============================================================================
echo [CHECK] Verifying Python 3.11+ ...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%D in ('python --version 2^>^&1') do set "PY_VERSION=%%D"
for /f "tokens=1 delims=." %%D in ("!PY_VERSION!") do set "PY_MAJOR=%%D"
for /f "tokens=2 delims=." %%D in ("!PY_VERSION!") do set "PY_MINOR=%%D"

if !PY_MAJOR! lss 3 (
    echo [ERROR] Python version too old: !PY_VERSION! (need 3.11+)
    pause
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 11 (
    echo [ERROR] Python version too old: !PY_VERSION! (need 3.11+)
    pause
    exit /b 1
)

echo [OK]   Python !PY_VERSION!

REM =============================================================================
REM Step 2: Check Ollama zip
REM =============================================================================
echo [CHECK] Verifying tools\ollama-windows-amd64.zip ...

if not exist "%SCRIPT_DIR%\tools\ollama-windows-amd64.zip" (
    echo [ERROR] tools\ollama-windows-amd64.zip not found
    echo         Download from: https://ollama.com/download/windows
    echo         Rename OllamaSetup.exe output or download the portable zip.
    pause
    exit /b 1
)

echo [OK]   tools\ollama-windows-amd64.zip

REM =============================================================================
REM Step 3: Check Python installer (optional fallback for target machine)
REM =============================================================================
set "PY_INSTALLER=%SCRIPT_DIR%\tools\python-3.12.9-amd64.exe"
echo [CHECK] Verifying Python installer ...

if not exist "%PY_INSTALLER%" (
    echo [WARN]  tools\python-3.12.9-amd64.exe not found
    echo         The offline install can still work if the target machine has Python 3.11+
    echo.
    echo         Recommended: download and place in tools\
    echo         https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
    echo.
    pause >nul
    set "PY_INSTALLER_MISSING=1"
) else (
    echo [OK]   tools\python-3.12.9-amd64.exe
    set "PY_INSTALLER_MISSING=0"
)

REM =============================================================================
REM Step 4: Check ollama-models (GGUF + Modelfile)
REM =============================================================================
echo [CHECK] Verifying ollama-models\ ...

if not exist "%SCRIPT_DIR%\ollama-models\Modelfile" (
    echo [ERROR] ollama-models\Modelfile not found
    pause
    exit /b 1
)

set "GGUF_COUNT=0"
for %%D in ("%SCRIPT_DIR%\ollama-models\*.gguf") do set /a GGUF_COUNT+=1

if !GGUF_COUNT! equ 0 (
    echo [WARN]  No .gguf file found in ollama-models\
    echo         Run download-model.bat to download the model first.
    pause >nul
) else (
    echo [OK]   !GGUF_COUNT! GGUF file(s) found
)

echo [OK]   ollama-models\Modelfile

REM =============================================================================
REM Step 5: Create offline_bundle/ directory
REM =============================================================================
echo.
echo [BUILD] Creating offline_bundle\ directory structure ...

if exist "%BUNDLE_DIR%" (
    echo         Removing existing offline_bundle\ ...
    rmdir /s /q "%BUNDLE_DIR%"
)

mkdir "%BUNDLE_DIR%"                     >nul 2>&1
mkdir "%BUNDLE_DIR%\tools"               >nul 2>&1
mkdir "%BUNDLE_DIR%\ollama-models"       >nul 2>&1
mkdir "%BUNDLE_DIR%\python-wheels"       >nul 2>&1
mkdir "%BUNDLE_DIR%\app"                 >nul 2>&1

echo [OK]   Directory structure created

REM =============================================================================
REM Step 6: Copy binary dependencies
REM =============================================================================
echo [BUILD] Copying binary dependencies ...

REM 6a. Ollama zip
echo         Copying ollama-windows-amd64.zip ...
copy "%SCRIPT_DIR%\tools\ollama-windows-amd64.zip" "%BUNDLE_DIR%\tools\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Copy failed
    pause
    exit /b 1
)
echo         [OK]   ollama-windows-amd64.zip

REM 6b. Python installer (optional)
if "!PY_INSTALLER_MISSING!"=="0" (
    echo         Copying python-3.12.9-amd64.exe ...
    copy "%PY_INSTALLER%" "%BUNDLE_DIR%\tools\" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Copy failed
        pause
        exit /b 1
    )
    echo         [OK]   python-3.12.9-amd64.exe
) else (
    echo         [SKIP] Python installer not available (target machine needs Python pre-installed)
)

REM 6c. VC++ Redistributable
echo         Copying VC++ Redistributable ...

set "VCREDIST_COPIED=0"

REM Try from tools\ollama\ first
if exist "%SCRIPT_DIR%\tools\ollama\vc_redist.x64.exe" (
    copy "%SCRIPT_DIR%\tools\ollama\vc_redist.x64.exe" "%BUNDLE_DIR%\tools\" >nul 2>&1
    if !errorlevel! equ 0 (
        echo         [OK]   vc_redist.x64.exe (from tools\ollama\)
        set "VCREDIST_COPIED=1"
    )
)

REM Try extracting from Ollama zip
if "!VCREDIST_COPIED!"=="0" (
    echo         Extracting vc_redist from ollama zip...
    powershell -NoProfile -Command ^
        "$zip = [System.IO.Compression.ZipFile]::OpenRead('%SCRIPT_DIR%\tools\ollama-windows-amd64.zip');" ^
        "$entry = $zip.Entries | Where-Object { $_.Name -like 'vc_redist*.exe' } | Select-Object -First 1;" ^
        "if ($entry) {" ^
        "  [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, '%BUNDLE_DIR%\tools\vc_redist.x64.exe', $true);" ^
        "  Write-Host '         [OK]   vc_redist.x64.exe (extracted from zip)';" ^
        "} else {" ^
        "  Write-Host '         [WARN] vc_redist not found in zip';" ^
        "}" ^
        "$zip.Dispose()"
    if exist "%BUNDLE_DIR%\tools\vc_redist.x64.exe" set "VCREDIST_COPIED=1"
)

if "!VCREDIST_COPIED!"=="0" (
    echo         [WARN] VC++ Redistributable not found - Ollama may fail to start
    echo                Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
)

echo [OK]   Binary dependencies copied

REM =============================================================================
REM Step 7: Lock dependencies (pip freeze) in temp venv
REM =============================================================================
echo [BUILD] Creating temp venv and generating requirements.lock.txt ...
echo         This may take 2-5 minutes...

set "BUILD_VENV=%SCRIPT_DIR%\.build_venv"

REM Clean up any previous temp venv
if exist "%BUILD_VENV%" rmdir /s /q "%BUILD_VENV%" 2>nul

python -m venv "%BUILD_VENV%" --clear >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create temp venv
    pause
    exit /b 1
)

"%BUILD_VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet 2>nul
"%BUILD_VENV%\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies in temp venv
    rmdir /s /q "%BUILD_VENV%" 2>nul
    pause
    exit /b 1
)

echo [BUILD] Freezing exact dependency versions...
"%BUILD_VENV%\Scripts\pip.exe" freeze > "%BUNDLE_DIR%\requirements.lock.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to generate requirements.lock.txt
    rmdir /s /q "%BUILD_VENV%" 2>nul
    pause
    exit /b 1
)

echo [OK]   requirements.lock.txt generated

REM =============================================================================
REM Step 8: Download Python wheels for TARGET Python 3.12
REM =============================================================================
echo [BUILD] Downloading Python wheels for Python %TARGET_PY_VER% (win_amd64)...
echo         This may take 5-10 minutes...

"%BUILD_VENV%\Scripts\pip.exe" download -r "%BUNDLE_DIR%\requirements.lock.txt" ^
    --dest "%BUNDLE_DIR%\python-wheels" ^
    --platform win_amd64 ^
    --python-version 312 ^
    --only-binary=:all: >nul 2>&1

if %errorlevel% neq 0 (
    echo [WARN]  Some wheels may have failed to download
    echo         Try running again with better internet connection.
)

REM Clean up temp venv
rmdir /s /q "%BUILD_VENV%" 2>nul

REM Count wheels
set "WHEEL_COUNT=0"
for %%D in ("%BUNDLE_DIR%\python-wheels\*.whl") do set /a WHEEL_COUNT+=1
echo [OK]   Downloaded !WHEEL_COUNT! wheel files

REM =============================================================================
REM Step 9: Copy application code
REM =============================================================================
echo [BUILD] Copying application code ...

REM 9a. app.py
copy "%SCRIPT_DIR%\app.py" "%BUNDLE_DIR%\app\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to copy app.py
    pause
    exit /b 1
)
echo         [OK]   app.py

REM 9b. Core Python modules
set "TOP_FILES=cli_chat.py comac_assistant.py enhanced_assistant.py ollama_client.py ollama_rag.py config.py report_generator.py knowledge_graph.py knowledge_classifier.py excel_styler.py obsidian_sync.py task_manager.py verify_offline.py verify_deployment.py models.json"
for %%D in (%TOP_FILES%) do (
    if exist "%SCRIPT_DIR%\%%D" (
        copy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\" >nul 2>&1
        echo         [OK]   %%D
    ) else (
        echo         [WARN] %%D not found - skipping
    )
)

REM 9c. Python sub-packages
set "SUB_DIRS=parsers converters fillers batch audit presentations blocks"
for %%D in (%SUB_DIRS%) do (
    if exist "%SCRIPT_DIR%\%%D\" (
        robocopy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\%%D" *.py /s /njh /njs /ndl >nul 2>&1
        if !errorlevel! geq 8 (
            echo [ERROR] Failed to copy %%D\
            pause
            exit /b 1
        )
        echo         [OK]   %%D\
    ) else (
        echo         [WARN] %%D\ not found - skipping
    )
)

REM 9d. Static assets
for %%D in (templates static) do (
    if exist "%SCRIPT_DIR%\%%D\" (
        robocopy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\%%D" /s /njh /njs /ndl >nul 2>&1
        if !errorlevel! geq 8 (
            echo [ERROR] Failed to copy %%D\
            pause
            exit /b 1
        )
        echo         [OK]   %%D\
    ) else (
        echo         [WARN] %%D\ not found - skipping
    )
)

echo [OK]   Application code copied

REM =============================================================================
REM Step 10: Copy ollama-models/
REM =============================================================================
echo [BUILD] Copying ollama-models\ ...

robocopy "%SCRIPT_DIR%\ollama-models" "%BUNDLE_DIR%\ollama-models" /s /njh /njs /ndl >nul 2>&1
if %errorlevel% geq 8 (
    echo [ERROR] Failed to copy ollama-models\
    pause
    exit /b 1
)

echo [OK]   ollama-models\ copied

REM =============================================================================
REM Step 11: Copy deployment scripts and docs
REM =============================================================================
echo [BUILD] Copying deployment scripts ...

set "DEPLOY_FILES=install-offline.bat start.bat opencode.bat README.md requirements.txt"
for %%D in (%DEPLOY_FILES%) do (
    if exist "%SCRIPT_DIR%\%%D" (
        copy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\" >nul 2>&1
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to copy %%D
            pause
            exit /b 1
        )
        echo         [OK]   %%D
    ) else (
        echo         [WARN] %%D not found - skipping
    )
)

echo [OK]   Deployment scripts copied

REM =============================================================================
REM Step 12: Generate manifest.sha256
REM =============================================================================
echo [BUILD] Generating manifest.sha256 ...

powershell -NoProfile -Command ^
    "$bundleDir = '%BUNDLE_DIR%'; " ^
    "Push-Location $bundleDir; " ^
    "Get-ChildItem -Recurse -File | ForEach-Object { " ^
    "    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash; " ^
    "    $relPath = $_.FullName.Substring((Get-Location).Path.Length + 1) -replace '\\', '/'; " ^
    "    \"$hash  $relPath\" " ^
    "} | Out-File 'manifest.sha256' -Encoding UTF8; " ^
    "Pop-Location"

if %errorlevel% neq 0 (
    echo [WARN]  manifest.sha256 generation failed (non-blocking)
) else (
    echo [OK]   manifest.sha256 generated
)

REM =============================================================================
REM Step 13: Summary
REM =============================================================================
echo.
for /f "usebackq tokens=1,2 delims= " %%D in (`powershell -NoProfile -Command ^
    "$size = (Get-ChildItem -Recurse -File '%BUNDLE_DIR%' | Measure-Object -Property Length -Sum).Sum; " ^
    "if ($size -ge 1GB) { '{0:N2} GB' -f ($size/1GB) } " ^
    "elseif ($size -ge 1MB) { '{0:N2} MB' -f ($size/1MB) } " ^
    "else { '{0:N2} KB' -f ($size/1KB) }"`) do set "BUNDLE_SIZE=%%D %%E"

echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo.
echo   Output: %BUNDLE_DIR%
echo   Size:   !BUNDLE_SIZE!
echo.
echo   Package contents:
echo     - tools\          : Ollama + Python installer + VC++
echo     - ollama-models\  : GGUF model + Modelfile
echo     - python-wheels\  : !WHEEL_COUNT! Python wheels (for Python %TARGET_PY_VER%)
echo     - app\            : Application source code
echo     - requirements.lock.txt : Frozen dependency versions
echo     - manifest.sha256       : File integrity checksums
echo.
echo   Deploy to air-gapped machine:
echo     1. Copy entire offline_bundle\ to target machine
echo     2. Target machine needs: Python 3.11+ (3.12 recommended)
echo     3. Run install-offline.bat (double-click)
echo     4. After install, run start.bat
echo     5. Visit http://localhost:7860
echo.
echo ============================================================

pause
exit /b 0
