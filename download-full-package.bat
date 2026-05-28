@echo off

REM =============================================================================
REM COMAC-LocalAI-Windows - Full Package Downloader
REM Run on internet-connected machine to prepare the complete deployment package.
REM After completion, copy the entire directory to the air-gapped machine.
REM =============================================================================

echo ================================================
echo  COMAC-LocalAI-Windows Full Package Downloader
echo ================================================
echo.
echo This script downloads all required components
echo for offline deployment on an air-gapped machine.
echo.

:: Check Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not installed
    echo Install Git: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Check if directory already exists
if exist "COMAC-LocalAI-Windows" (
    echo [WARN] COMAC-LocalAI-Windows directory already exists
    echo Will update to latest version
    cd COMAC-LocalAI-Windows
    git pull
    goto :download_tools
)

:: Clone repository
echo.
echo [1/4] Cloning GitHub repository...
git clone https://github.com/kogamishinyajerry-ops/COMAC-LocalAI-Windows.git
if %errorlevel% neq 0 (
    echo [ERROR] Clone failed
    pause
    exit /b 1
)
cd COMAC-LocalAI-Windows

:download_tools
:: Download Ollama
echo.
echo [2/4] Download Ollama Portable (~2GB)...
echo Visit: https://github.com/ollama/ollama/releases/latest
echo Download: ollama-windows-amd64.zip
echo Save to: %CD%\tools\ollama-windows-amd64.zip
echo.
echo Press Enter to open download page...
pause
start https://github.com/ollama/ollama/releases/latest

echo.
echo After download completes, place ollama-windows-amd64.zip in tools\
echo Then press Enter to continue
pause

:: Check Ollama zip
if not exist "tools\ollama-windows-amd64.zip" (
    echo [WARN] tools\ollama-windows-amd64.zip not found
    echo You can add it manually later
)

:: Download Python installer
echo.
echo [3/4] Download Python Installer (~25MB)...
echo Visit: https://www.python.org/ftp/python/3.11.8/
echo Download: python-3.11.8-amd64.exe
echo Save to: %CD%\tools\python-3.11.8-amd64.exe
echo.
echo Press Enter to open download page...
pause
start https://www.python.org/ftp/python/3.11.8/

echo.
echo After download completes, place python-3.11.8-amd64.exe in tools\
echo Then press Enter to continue
pause

:: Check Python exe
if not exist "tools\python-3.11.8-amd64.exe" (
    echo [WARN] tools\python-3.11.8-amd64.exe not found
    echo You can add it manually later
)

:: Download model
echo.
echo [4/4] Download LLM Model (~4-5GB, optional)...
echo Visit: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main
echo Download: qwen2.5-7b-instruct-q4_k_m.gguf (~4.4GB)
echo Save to: %CD%\ollama-models\
echo.
echo Press Enter to open download page (or type N to skip)...
pause >nul
set "choice="
set /p choice="Open download page? (Y/N): "
if /i "%choice%"=="Y" (
    start https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main
)

:: Done
echo.
echo ================================================
echo   Download preparation complete!
echo ================================================
echo.
echo Next steps:
echo 1. Copy the COMAC-LocalAI-Windows directory to a USB drive
echo 2. On the air-gapped machine, run install-offline.bat
echo 3. Then run start.bat to launch
echo 4. Visit http://localhost:7860 in your browser
echo.
echo If the model was not downloaded, run download-model.bat
echo.
pause
