@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows — 有网机器初始化脚本
REM  模型: qwen:7b-q4_K_M
REM
REM  用法: 在有网机器上双击运行一次，完成全部初始化
REM  完成后将整个项目目录复制到内网机器
REM ============================================================================

title COMAC AI - 有网环境初始化

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  前置检查: Python
REM ============================================================================
echo.
echo ==============================================================
echo   欢迎使用 COMAC AI 初始化脚本
echo   此脚本需要互联网连接（约 20-30 分钟）
echo ==============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo   [错误] 未找到 Python
    echo   请先安装 Python 3.11+：https://www.python.org/ftp/python/
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PY_VER=%%v"
if !PY_VER! LSS 11 (
    echo   [错误] Python 版本过低，需要 3.11+
    pause
    exit /b 1
)
echo   [OK] Python 3.!PY_VER! 就绪

REM ============================================================================
REM  步骤 1: 创建 / 更新 .venv
REM ============================================================================
echo.
echo ==============================================================
echo   [1/6] 创建 Python 虚拟环境
echo ==============================================================

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    for /f "delims=" %%v in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "VENV_VER=%%v"
    if defined VENV_VER (
        if "!VENV_VER!"=="!PY_VER!" (
            echo         .venv 已存在且版本匹配（Python 3.!VENV_VER!）
            echo         跳过创建，尝试更新依赖...
            goto :update_deps
        ) else (
            echo         .venv 版本不匹配，删除后重建...
            rmdir /S /Q "%SCRIPT_DIR%.venv" 2>nul
        )
    )
)

echo         创建 .venv（请稍等）...
python -m venv .venv --clear >nul 2>&1
if errorlevel 1 (
    echo   [错误] .venv 创建失败
    pause
    exit /b 1
)
echo   [OK] .venv 创建完成（Python 3.!PY_VER!）

:update_deps
echo.
echo ==============================================================
echo   [2/6] 安装 Python 依赖
echo ==============================================================

echo         安装所有依赖包（约 5-10 分钟，请稍等）...
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install --upgrade pip --quiet 2>nul
"%SCRIPT_DIR%.venv\Scripts\pip.exe" install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo   [错误] 依赖安装失败，请检查网络
    pause
    exit /b 1
)

REM 验证核心依赖
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import gradio; import ollama; import pandas; print('OK')" 2>nul
if errorlevel 1 (
    echo   [错误] 依赖验证失败
    pause
    exit /b 1
)
echo   [OK] Python 依赖安装完成
echo.

REM ============================================================================
REM  步骤 3: 提取 Ollama
REM ============================================================================
echo ==============================================================
echo   [3/6] 初始化 Ollama
echo ==============================================================

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul

if exist "%SCRIPT_DIR%tools\ollama\ollama.exe" (
    echo   [OK] Ollama 已提取
) else (
    if not exist "%SCRIPT_DIR%tools\ollama-windows-amd64.zip" (
        echo   [错误] tools\ollama-windows-amd64.zip 未找到
        pause
        exit /b 1
    )
    echo         提取 Ollama（请稍等）...
    powershell -NoProfile -Command "Expand-Archive -Force '%SCRIPT_DIR%tools\ollama-windows-amd64.zip' '%SCRIPT_DIR%tools\ollama'"
    echo   [OK] Ollama 提取完成
)

REM 安装 VC++ Redistributable
if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         安装 VC++ 运行时...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ 运行时已安装
)

REM ============================================================================
REM  步骤 4: 启动 Ollama 服务
REM ============================================================================
echo ==============================================================
echo   [4/6] 启动 Ollama 服务
echo ==============================================================

set "OLLAMA_BIN=%SCRIPT_DIR%tools\ollama\ollama.exe"

curl -s --connect-timeout 5 "http://localhost:11434/api/version" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama 服务已在运行
) else (
    echo         启动 Ollama 服务（请稍等）...
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://localhost:11434/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ready
    )
    echo   [警告] Ollama 启动超时，继续...
)
:ollama_ready
echo   [OK] Ollama 服务就绪
echo.

REM ============================================================================
REM  步骤 5: 下载 qwen:7b-q4_K_M 模型
REM ============================================================================
echo ==============================================================
echo   [5/6] 下载 qwen:7b-q4_K_M 模型（约 4.5 GB）
echo ==============================================================

"%OLLAMA_BIN%" list 2>nul | findstr /I "qwen" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen 模型已在 Ollama 缓存中
) else (
    if exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo         发现本地 GGUF 文件，创建模型（请稍等）...
        if exist "%SCRIPT_DIR%ollama-models\Modelfile" (
            "%OLLAMA_BIN%" create qwen:7b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [错误] 模型创建失败
                pause
                exit /b 1
            )
            echo   [OK] qwen:7b-q4_K_M 模型创建成功
        )
    ) else (
        echo         正在从 Ollama 官方仓库下载模型（约 4.5 GB）
        echo         此过程较长，请耐心等待，不要关闭此窗口
        echo.
        "%OLLAMA_BIN%" pull qwen:7b-q4_K_M
        if errorlevel 1 (
            echo.
            echo   [错误] 模型下载失败
            echo   请检查网络后重新运行 pre-deploy.bat
            pause
            exit /b 1
        )
        echo   [OK] qwen:7b-q4_K_M 模型下载成功
    )
)
echo.

REM ============================================================================
REM  步骤 6: 初始化配置
REM ============================================================================
echo ==============================================================
echo   [6/6] 初始化配置
echo ==============================================================

setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

for %%d in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~dd" mkdir "%%~dd" 2>nul
)

if not exist ".env" (
    (
        echo # COMAC AI 配置文件
        echo GRADIO_USER=admin
        echo GRADIO_PASS=change_me_123
        echo COMAC_MODEL=qwen:7b-q4_K_M
        echo COMAC_EMBED_MODEL=nomic-embed-text
        echo OLLAMA_HOST=localhost:11434
    ) > .env
    echo   [OK] .env 已生成
    echo   [重要] 请修改 .env 中的 GRADIO_PASS 密码！
) else (
    echo   [OK] .env 已存在
)

REM ============================================================================
REM  完成
REM ============================================================================
echo.
echo ==============================================================
echo   有网初始化完成！
echo ==============================================================
echo.
echo   项目目录已包含完整运行环境：
echo   - .venv\                  Python 虚拟环境（3.!PY_VER!)
echo   - tools\ollama\          Ollama 可执行文件
echo   - Ollama 模型缓存        qwen:7b-q4_K_M
echo.
echo   下一步:
echo   1. 修改 .env 中的 GRADIO_PASS 密码
echo   2. 将整个项目目录复制到内网机器
echo   3. 在内网机器上双击 setup.bat 验证
echo   4. 双击 start.bat 启动服务
echo.
echo   内网机器 Python 版本要求: Python 3.!PY_VER!（必须与本机一致）
echo.
pause
