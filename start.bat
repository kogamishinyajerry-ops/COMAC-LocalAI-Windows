@echo off
chcp 65001 >nul 2>&1
setlocal

REM ============================================================================
REM  COMAC-LocalAI-Windows 启动脚本（内网一键部署版）
REM  模型: qwen:7b-q4_K_M
REM  环境: Windows 10 x64, 16GB RAM, 空气隔离内网
REM ============================================================================

title COMAC AI - 智能文档处理平台

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================
echo    COMAC 离轴线AI文档处理平台
echo    Windows 内网一键部署版
echo ==============================================================
echo.

REM ============================================================================
REM  0. 检查 .venv 和目录
REM ============================================================================
echo [0/4] 检查运行环境...

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo   [错误] .venv 不存在
    echo   请先在有网机器运行 pre-deploy.bat
    echo   或将完整项目目录从有网机器复制过来
    pause
    exit /b 1
)
echo         [OK] .venv 存在

for %%d in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~dd" mkdir "%%~dd" 2>nul
)
echo         [OK] 目录就绪
echo.

REM ============================================================================
REM  1. 启动 Ollama 服务
REM ============================================================================
echo [1/4] 检查 Ollama 服务...

set "OLLAMA_HOST=localhost:11434"
set "OLLAMA_BIN=tools\ollama\ollama.exe"

REM 优先使用内置 Ollama，否则尝试系统 PATH
if exist "%OLLAMA_BIN%" (
    set "OLLAMA_CMD=%OLLAMA_BIN%"
) else (
    set "OLLAMA_CMD=ollama"
)

curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
if not errorlevel 1 goto :ollama_ok

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul

echo         Ollama 未运行，正在启动...
if exist "%OLLAMA_BIN%" (
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
) else (
    start /B "" ollama serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
)

REM 等待 Ollama 启动（最多 30 秒）
for /L %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
    if not errorlevel 1 goto :ollama_ok
)

echo.
echo   [错误] Ollama 启动失败
echo   请运行 setup.bat 重新初始化
echo   日志: logs\ollama.log
pause
exit /b 1

:ollama_ok
echo         [OK] Ollama 服务运行中
echo.

REM ============================================================================
REM  2. 验证 qwen:7b-q4_K_M 模型
REM ============================================================================
echo [2/4] 验证模型 (qwen:7b-q4_K_M)...

REM 尝试匹配 qwen 相关模型
%OLLAMA_CMD% list 2>nul | findstr /I "qwen" >nul
if errorlevel 1 (
    echo.
    echo   [错误] qwen 模型未找到
    echo   请先运行 setup.bat 初始化模型
    pause
    exit /b 1
)
echo         [OK] qwen 模型就绪
echo.

REM ============================================================================
REM  3. 检查 Gradio 认证（从 .env 读取）
REM ============================================================================
echo [3/4] 检查访问认证...

if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (.env) do (
        if "%%a"=="GRADIO_USER" set "GRADIO_USER=%%b"
        if "%%a"=="GRADIO_PASS" set "GRADIO_PASS=%%b"
    )
)

if defined GRADIO_USER if defined GRADIO_PASS (
    echo         [OK] 认证已配置 (用户: %GRADIO_USER%)
    if "!GRADIO_PASS!"=="change_me_123" (
        echo         [警告] 密码仍为默认值，请修改 .env 中的 GRADIO_PASS
    )
) else (
    echo         [警告] 未找到认证信息
    echo         请在 .env 中设置 GRADIO_USER 和 GRADIO_PASS
)
echo.

REM ============================================================================
REM  4. 启动 Gradio Web UI
REM ============================================================================
echo [4/4] 启动 Gradio UI...

REM 设置 Ollama 优化环境变量
set "OLLAMA_NUM_PARALLEL=1"
set "OLLAMA_MAX_LOADED_MODELS=1"
set "OLLAMA_KEEP_ALIVE=5m"

REM 清理 7860 端口旧进程
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":7860.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM 启动应用
echo         启动中（首次运行可能需要 10-20 秒）...
start "COMAC AI" .venv\Scripts\python.exe app.py

REM 等待 Gradio 启动
for /L %%i in (1,1,20) do (
    timeout /t 2 /nobreak >nul
    curl -s --connect-timeout 3 "http://localhost:7860" >nul 2>&1
    if not errorlevel 1 goto :gradio_ok
)

echo.
echo         Gradio 启动较慢，请稍后访问: http://localhost:7860
goto :launch_done

:gradio_ok
echo         [OK] Gradio 已就绪
start http://localhost:7860

:launch_done
echo.
echo ==============================================================
echo    部署成功！
echo.
echo    访问地址: http://localhost:7860
if defined GRADIO_USER echo    登录用户: %GRADIO_USER%
echo.
echo    停止服务: 关闭此窗口或任务管理器结束 python.exe
echo ==============================================================
echo.

REM --------------------------------------------------------------------------
REM 自动注册 opencode 到用户 PATH（静默，仅首次注册）
REM --------------------------------------------------------------------------
powershell -NoProfile -Command ^
    "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); " ^
    "if ($p -notlike '*%~dp0*') { " ^
    "    [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';%~dp0;'), 'User'); " ^
    "    Write-Host ''; " ^
    "    Write-Host '---'; " ^
    "    Write-Host '附: 终端 AI 对话已就绪'; " ^
    "    Write-Host ''; " ^
    "    Write-Host '  从现在起，在任意目录打开 PowerShell'; " ^
    "    Write-Host '  直接输入 opencode 即可启动 AI 对话'; " ^
    "    Write-Host ''; " ^
    "    Write-Host '  如果当前已打开 PowerShell，'; " ^
    "    Write-Host '  请关闭后重新打开即可生效'; " ^
    "    Write-Host '---'; " ^
    "    Write-Host '' } " >nul

pause
