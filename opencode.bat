@echo off
chcp 65001 >nul 2>&1
setlocal

REM ============================================================================
REM  OpenCode TUI — 终端 AI 对话
REM  双击此文件即可启动
REM ============================================================================

title OpenCode TUI — COMAC AI

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM --------------------------------------------------------------------------
REM 前置检查：Python 虚拟环境
REM --------------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 尚未完成初始化设置
    echo.
    echo 请先双击运行项目根目录下的 setup.bat
    echo.
    pause
    exit /b 1
)

REM --------------------------------------------------------------------------
REM 前置检查：Ollama 服务
REM --------------------------------------------------------------------------
set "OLLAMA_HOST=localhost:11434"

REM 检测 curl 是否可用（Windows 10+ 内置，旧系统可能没有）
where curl >nul 2>&1
set "CURL=curl"
if errorlevel 1 set "CURL="

REM 优先使用内置 Ollama，否则尝试系统 PATH
if exist "tools\ollama\ollama.exe" (
    set "OLLAMA_BIN=tools\ollama\ollama.exe"
) else (
    set "OLLAMA_BIN=ollama"
)

REM 如果 curl 可用，先尝试检测 Ollama 是否已在运行
if defined CURL (
    curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
    if not errorlevel 1 goto :ollama_ok
)

REM curl 不可用或 Ollama 未运行：尝试启动 Ollama
echo [提示] 正在启动 Ollama AI 服务，请稍等...
if defined CURL (
    start /B cmd /c "\"%OLLAMA_BIN%\" serve > nul 2>&1"
    REM 等待 Ollama 启动（最多 25 秒）
    for /L %%i in (1,1,25) do (
        timeout /t 1 /nobreak >nul
        curl -s --connect-timeout 2 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
) else (
    REM 无 curl：静默启动后直接等待 5 秒（Ollama 自检时间）
    start /B cmd /c "\"%OLLAMA_BIN%\" serve > nul 2>&1"
    timeout /t 5 /nobreak >nul
    echo         Ollama 已启动
)

:ollama_ok

REM --------------------------------------------------------------------------
REM 启动 TUI
REM --------------------------------------------------------------------------
.venv\Scripts\python.exe cli_chat.py %*

if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    echo.
    echo 请确认已双击运行 setup.bat 完成初始化
    echo.
    pause
)
