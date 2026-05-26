@echo off
chcp 65001 >nul 2>&1
setlocal

REM ============================================================================
REM  GGUF 模型下载工具（辅助工具）
REM  推荐方式: pre-deploy.bat（会自动下载模型）
REM  本工具用于: pre-deploy.bat 下载失败时的手动补救
REM ============================================================================

title COMAC AI - 下载 Qwen 模型

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================
echo   Qwen2.5-7B GGUF 模型下载工具
echo ==============================================================
echo.
echo   推荐使用 pre-deploy.bat（会自动下载模型）
echo   本工具用于 pre-deploy.bat 失败时的手动补救
echo.

if exist "ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf" (
    echo   [OK] 模型文件已存在: ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf
    pause
    exit /b 0
)

echo   请选择下载方式：
echo.
echo   方式 1: HuggingFace CDN 下载（推荐，直链）
echo.
echo   方式 2: 浏览器手动下载
echo.
echo ==============================================================
echo.

set /p CHOICE="请选择 (1/2): "

if "%CHOICE%"=="1" goto :hf_download
if "%CHOICE%"=="2" goto :manual
echo   无效选择
pause
exit /b 1

:hf_download
echo.
echo   正在下载 GGUF 文件（约 4.5 GB）...
echo   目标: ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf
echo.

if not exist "ollama-models" mkdir "ollama-models"

set "HF_URL=https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
set "DEST=ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf"

curl -L -C - -o "%DEST%" "%HF_URL%"
if errorlevel 1 (
    echo.
    echo   [错误] 下载失败，请使用方式 2 手动下载
    pause
    exit /b 1
)

for %%a in ("%DEST%") do set "SIZE=%%~za"
if defined SIZE (
    echo.
    echo   下载完成！文件大小: %SIZE% 字节
)
echo.
echo   下一步: 双击 pre-deploy.bat 或 setup.bat
pause
exit /b 0

:manual
echo.
echo ==============================================================
echo   手动下载步骤
echo ==============================================================
echo.
echo   1. 浏览器访问:
echo.
echo      https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
echo.
echo   2. 点击文件列表中的:
echo.
echo      qwen2.5-7b-instruct-q4_k_m.gguf
echo.
echo   3. 点击下载按钮（约 4.5 GB）
echo.
echo   4. 将下载的文件放入本项目的:
echo.
echo      ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf
echo.
echo   5. 运行 pre-deploy.bat 或 setup.bat
echo.
echo   直链（可复制到下载工具）:
echo   %HF_URL%
echo.
pause
