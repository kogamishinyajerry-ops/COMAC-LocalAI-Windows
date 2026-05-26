@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC AI - Windows 低配版部署脚本
REM  模型: 单一 7B Q4_K_M (comac)
REM  环境: Win10, 16GB RAM, 无网络
REM ============================================================================

title COMAC AI - Windows 部署

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  步骤 1: 检查 Python
REM ============================================================================
echo.
echo ========================================
echo   [1/5] 检查 Python 环境
echo ========================================

python --version >nul 2>&1
if errorlevel 1 (
    echo   [错误] Python 未安装
    echo   请安装 Python 3.9+ https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   [OK] Python 可用

python -m pip --version >nul 2>&1
if errorlevel 1 (
    python -m ensurepip --upgrade >nul 2>&1
)
echo   [OK] pip 可用
echo.

REM ============================================================================
REM  步骤 2: 检查 Ollama
REM ============================================================================
echo ========================================
echo   [2/5] 检查 Ollama 服务
echo ========================================

where ollama >nul 2>&1
if errorlevel 1 (
    echo   [错误] Ollama 未安装
    echo   请安装: https://ollama.com/download/windows
    pause
    exit /b 1
)
echo   [OK] Ollama 已安装

set "OLLAMA_HOST=localhost:11434"

curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
if errorlevel 1 (
    echo       启动 Ollama 服务...
    start /B ollama serve > "%SCRIPT_DIR%ollama.log" 2>&1
    for /L %%i in (1,1,15) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [错误] Ollama 启动失败
    pause
    exit /b 1
)
:ollama_ok
echo   [OK] Ollama 服务可用
echo.

REM ============================================================================
REM  步骤 3: 创建模型
REM ============================================================================
echo ========================================
echo   [3/5] 创建 comac 模型 (7B)
echo ========================================

ollama list 2>nul | findstr /C:"comac" >nul
if errorlevel 1 (
    echo       创建 comac 模型...
    if exist "ollama-models\Modelfile" (
        ollama create comac -f "ollama-models\Modelfile"
        if errorlevel 1 (
            echo   [错误] 模型创建失败
            echo   请确保 GGUF 文件在 ollama-models\ 目录下
            pause
            exit /b 1
        )
        echo   [OK] comac 模型创建成功
    ) else (
        echo   [错误] 未找到 ollama-models\Modelfile
        pause
        exit /b 1
    )
) else (
    echo   [OK] comac 模型已存在
)
echo.

REM 嵌入模型
ollama list 2>nul | findstr /C:"nomic-embed-text" >nul
if errorlevel 1 (
    echo       拉取 nomic-embed-text...
    ollama pull nomic-embed-text
    if errorlevel 1 (
        echo   [警告] nomic-embed-text 拉取失败，RAG 将不可用
    ) else (
        echo   [OK] nomic-embed-text 就绪
    )
) else (
    echo   [OK] nomic-embed-text 已存在
)
echo.

REM ============================================================================
REM  步骤 4: 安装 Python 依赖
REM ============================================================================
echo ========================================
echo   [4/5] 安装 Python 依赖
echo ========================================

if not exist ".venv" (
    echo       创建虚拟环境...
    python -m venv .venv
)

set "PIP=.venv\Scripts\pip.exe"
set "PYTHON=.venv\Scripts\python.exe"

echo       安装依赖...
"%PIP%" install --upgrade pip -q

if exist "python-wheels" (
    "%PIP%" install --no-index --find-links="python-wheels" -r requirements.txt
) else (
    "%PIP%" install -r requirements.txt
)

if errorlevel 1 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo   [OK] 依赖安装完成
echo.

REM ============================================================================
REM  步骤 5: 优化配置
REM ============================================================================
echo ========================================
echo   [5/5] 优化配置
echo ========================================

set "OLLAMA_NUM_PARALLEL=1"
set "OLLAMA_MAX_LOADED_MODELS=1"
set "OLLAMA_KEEP_ALIVE=5m"

for %%d in (temp\uploads temp\outputs logs) do (
    if not exist "%%d" mkdir "%%d"
)

echo   [OK] 配置完成
echo.

echo ========================================
echo   部署完成！
echo ========================================
echo.
echo   启动方式: 运行 start.bat
echo   或手动: .venv\Scripts\python.exe app.py
echo   访问:   http://localhost:7860
echo.
pause
