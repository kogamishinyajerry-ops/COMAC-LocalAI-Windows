@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows — Qwen2.5-7B GGUF 模型下载脚本
REM  用法: 双击运行即可（需要互联网连接）
REM ============================================================================

title COMAC AI - 下载 Qwen 模型

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================
echo   Qwen2.5-7B Q4_K_M 模型下载工具
echo ==============================================================
echo.
echo   此脚本用于下载 GGUF 模型文件
echo   模型约 4.5 GB，请确保网络稳定
echo.

REM 检查 Ollama 是否可用
set "OLLAMA_EXE="
if exist "tools\ollama\ollama.exe" set "OLLAMA_EXE=tools\ollama\ollama.exe"
if exist "ollama.exe" set "OLLAMA_EXE=ollama.exe"
where ollama >nul 2>&1 && set "OLLAMA_EXE=ollama"

REM 检查模型文件是否已存在
if exist "ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf" (
    echo   [OK] 模型文件已存在: ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf
    echo   无需重新下载
    echo.
    echo   下一步: 双击 setup.bat 完成部署
    pause
    exit /b 0
)

echo   [提示] 未找到 GGUF 模型文件，请选择下载方式：
echo.
echo   方式 1: Ollama 在线拉取（推荐，约 5-10 分钟）
echo           将从 Ollama 官方仓库下载模型
echo.
echo   方式 2: HuggingFace 直接下载（约 10-20 分钟）
echo           使用 curl 从 HuggingFace 下载 GGUF 文件
echo           适合: Ollama 下载速度慢时使用
echo.
echo   方式 3: 手动下载（最稳定）
echo           浏览器访问下载地址，下载后放入 ollama-models\ 目录
echo.
echo ==============================================================
echo.

set /p CHOICE="请选择下载方式 (1/2/3): "

if "%CHOICE%"=="1" goto :ollama_pull
if "%CHOICE%"=="2" goto :hf_download
if "%CHOICE%"=="3" goto :manual
echo   无效选择，请重新运行并输入 1、2 或 3
pause
exit /b 1

:ollama_pull
echo.
echo   正在启动 Ollama 服务并拉取模型...
echo   （如果已有 Ollama 在运行，服务不会被重启）
echo.

if defined OLLAMA_EXE (
    echo   找到 Ollama: %OLLAMA_EXE%
) else (
    echo   [错误] 未找到 Ollama
    echo   请先运行 setup.bat 或安装 Ollama
    pause
    exit /b 1
)

REM 尝试启动 Ollama 服务（如果未运行）
curl -s --connect-timeout 3 "http://localhost:11434/api/version" >nul 2>&1
if errorlevel 1 (
    echo   启动 Ollama 服务...
    start /B "" "%OLLAMA_EXE%" serve >nul 2>&1
    echo   等待 Ollama 启动（约 10 秒）...
    for /L %%i in (1,1,10) do (
        timeout /t 1 /nobreak >nul
        curl -s --connect-timeout 2 "http://localhost:11434/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ready
    )
    echo   [警告] Ollama 启动检测超时，继续尝试...
    :ollama_ready
)

echo   正在拉取 qwen:7b-q4_K_M 模型（约 4.5 GB）...
echo   此过程较长，请耐心等待，不要关闭此窗口
echo.
"%OLLAMA_EXE%" pull qwen:7b-q4_K_M
if errorlevel 1 (
    echo.
    echo   [错误] Ollama pull 失败
    echo   请检查网络连接，或尝试方式 2/3
    pause
    exit /b 1
)

REM 将 Ollama 模型导出为 GGUF 文件到 ollama-models\
echo.
echo   模型拉取成功，正在导出 GGUF 文件到 ollama-models\ ...
if not exist "ollama-models" mkdir "ollama-models"

REM Ollama 的模型文件在用户目录，需要复制出来
set "OLLAMA_MODEL_DIR=%USERPROFILE%\.ollama\models\blobs\"
if exist "%OLLAMA_MODEL_DIR%" (
    for /F "delims=" %%f in ('dir /B /O-D "%OLLAMA_MODEL_DIR%qwen2.5*" 2^>nul') do (
        if not exist "ollama-models\%%f" (
            echo   复制模型文件: %%f
            copy "%OLLAMA_MODEL_DIR%%%f" "ollama-models\" >nul 2>&1
        )
    )
)

echo.
echo ==============================================================
echo   下载完成！
echo ==============================================================
echo.
echo   下一步: 双击 setup.bat 完成部署
echo.
pause
exit /b 0

:hf_download
echo.
echo   正在从 HuggingFace 下载 GGUF 文件...
echo   模型: Qwen/Qwen2.5-7B-Instruct-GGUF
echo   文件: qwen2.5-7b-instruct-q4_k_m.gguf
echo   大小: 约 4.5 GB
echo.

REM 检测 curl 是否可用
curl --version >nul 2>&1
if errorlevel 1 (
    echo   [错误] curl 不可用，请使用方式 3 手动下载
    goto :manual
)

if not exist "ollama-models" mkdir "ollama-models"

REM HuggingFace CDN 下载地址
set "HF_URL=https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
set "DEST=ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf"

echo   开始下载（此过程较长，请耐心等待）...
echo   目标: %DEST%
echo.

curl -L -C - -o "%DEST%" "%HF_URL%"
if errorlevel 1 (
    echo.
    echo   [错误] 下载失败
    echo   请检查网络后重试，或使用方式 3 手动下载
    pause
    exit /b 1
)

for %%a in ("%DEST%") do set "SIZE=%%~za"
if defined SIZE (
    echo.
    echo   下载完成！文件大小: %SIZE% 字节
)

echo.
echo ==============================================================
echo   下载完成！
echo ==============================================================
echo.
echo   下一步: 双击 setup.bat 完成部署
echo.
pause
exit /b 0

:manual
echo.
echo ==============================================================
echo   手动下载步骤
echo ==============================================================
echo.
echo   1. 在浏览器中访问以下地址:
echo.
echo      https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
echo.
echo   2. 点击页面中的文件列表，找到:
echo.
echo      qwen2.5-7b-instruct-q4_k_m.gguf
echo.
echo   3. 点击右侧的下载按钮（约 4.5 GB）
echo.
echo   4. 下载完成后，将文件放入本项目的:
echo.
echo      ollama-models\
echo.
echo      最终路径应为:
echo      ollama-models\qwen2.5-7b-instruct-q4_k_m.gguf
echo.
echo   5. 放好后，双击 setup.bat 完成部署
echo.
echo ==============================================================
echo.
echo   直链下载（可复制到下载工具或浏览器）:
echo   %HF_URL%
echo.
pause
