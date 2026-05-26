@echo off
chcp 65001 >nul
setlocal

REM ============================================================================
REM  COMAC AI - Windows 低配版启动脚本
REM  模型: 单一 7B Q4_K_M (comac)
REM ============================================================================

title COMAC AI

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ========================================
echo   COMAC 离线AI文档处理平台
echo   Windows 低配版 (7B 单模型)
echo ========================================
echo.

REM ============================================================================
REM  1. 确保 Ollama 运行
REM ============================================================================
echo [1/3] 检查 Ollama 服务...

set "OLLAMA_HOST=localhost:11434"

curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
if not errorlevel 1 goto :ollama_ok

start /B ollama serve > "%SCRIPT_DIR%ollama.log" 2>&1
for /L %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
    if not errorlevel 1 goto :ollama_ok
)
echo   [错误] Ollama 启动失败，请先运行 setup.bat
pause
exit /b 1

:ollama_ok
echo   [OK] Ollama 服务运行中
echo.

REM ============================================================================
REM  2. 检查模型
REM ============================================================================
echo [2/3] 检查模型...
ollama list 2>nul | findstr /C:"comac" >nul
if errorlevel 1 (
    echo   [错误] comac 模型未找到，请先运行 setup.bat
    pause
    exit /b 1
)
echo   [OK] comac 模型就绪
echo.

REM ============================================================================
REM  3. 启动 Gradio
REM ============================================================================
echo [3/3] 启动 Gradio UI...

REM 设置低配优化环境变量
set "OLLAMA_NUM_PARALLEL=1"
set "OLLAMA_MAX_LOADED_MODELS=1"
set "OLLAMA_KEEP_ALIVE=5m"

REM 释放 7860 端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7860.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM 启动应用
echo       启动中...
start "COMAC AI" .venv\Scripts\python.exe app.py

timeout /t 5 /nobreak >nul

curl -s --connect-timeout 5 "http://localhost:7860" >nul 2>&1
if not errorlevel 1 (
    start http://localhost:7860
    echo.
    echo ========================================
    echo   COMAC AI 已启动！
    echo   http://localhost:7860
    echo ========================================
) else (
    echo.
    echo   正在启动，请稍候访问 http://localhost:7860
)

echo.
pause
