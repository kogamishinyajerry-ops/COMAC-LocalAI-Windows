@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows 部署初始化脚本
REM  支持在线（ollama pull）和离线（本地 GGUF）两种模式
REM  模型: qwen:7b-q4_K_M
REM  环境: Windows 10 x64, 空气隔离内网
REM ============================================================================

title COMAC AI - 部署初始化

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  步骤 1: 检查 Python 环境
REM ============================================================================
echo.
echo ==============================================================
echo   [1/6] 检查 Python 环境
echo ==============================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo   [错误] Python 未安装
    echo   请安装 Python 3.9+: https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
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
echo ==============================================================
echo   [2/6] 检查 Ollama 服务
echo ==============================================================

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
    echo         启动 Ollama 服务...
    start /B ollama serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,15) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [错误] Ollama 启动失败，请查看 logs\ollama.log
    pause
    exit /b 1
)

:ollama_ok
echo   [OK] Ollama 服务运行中
echo.

REM ============================================================================
REM  步骤 3: 下载/准备 qwen:7b-q4_K_M 模型
REM ============================================================================
echo ==============================================================
echo   [3/6] 准备 qwen:7b-q4_K_M 模型
echo ==============================================================

REM 检查是否已有 qwen 模型（支持多种命名方式）
ollama list 2>nul | findstr /I "qwen" >nul
if not errorlevel 1 (
    echo   [OK] qwen 模型已存在，跳过下载
    goto :model_done
)

REM 检查是否有本地 GGUF 文件（离线部署模式）
if exist "ollama-models\*.gguf" (
    echo         发现本地 GGUF 文件，选择离线模式
    for %%f in ("ollama-models\*.gguf") do (
        echo         使用: %%~nxf
        if exist "ollama-models\Modelfile" (
            echo         使用 Modelfile 创建模型...
            ollama create qwen:7b-q4_K_M -f "ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [错误] 模型创建失败
                echo   请检查: 1) GGUF 文件是否完整  2) Modelfile 是否正确
                pause
                exit /b 1
            )
            echo   [OK] qwen:7b-q4_K_M 模型创建成功
        ) else (
            echo   [错误] 缺少 Modelfile
            echo   请在 ollama-models\ 目录下放置 Modelfile
            pause
            exit /b 1
        )
    )
    goto :model_done
)

REM 在线模式：直接 ollama pull
echo         在线模式，正在下载 qwen:7b-q4_K_M（约 4.7GB）...
echo         此过程需要互联网连接，如在空气隔离内网请准备好本地 GGUF 文件
echo.

ollama pull qwen:7b-q4_K_M
if errorlevel 1 (
    echo.
    echo   [错误] 模型下载失败
    echo   请检查网络连接，或准备本地 GGUF 文件放入 ollama-models\ 目录
    pause
    exit /b 1
)
echo   [OK] qwen:7b-q4_K_M 模型下载完成

:model_done
echo.

REM ============================================================================
REM  步骤 4: 下载 nomic-embed-text（向量嵌入模型）
REM ============================================================================
echo ==============================================================
echo   [4/6] 准备向量嵌入模型
echo ==============================================================

ollama list 2>nul | findstr /C:"nomic-embed-text" >nul
if not errorlevel 1 (
    echo   [OK] nomic-embed-text 已存在
) else (
    echo         正在下载 nomic-embed-text（约 274MB）...
    echo         此模型用于 RAG 知识库问答，如不需要可跳过
    ollama pull nomic-embed-text
    if errorlevel 1 (
        echo   [警告] nomic-embed-text 下载失败，RAG 功能将不可用
        echo         如需 RAG 功能，请手动运行: ollama pull nomic-embed-text
    ) else (
        echo   [OK] nomic-embed-text 就绪
    )
)
echo.

REM ============================================================================
REM  步骤 5: 安装 Python 依赖
REM ============================================================================
echo ==============================================================
echo   [5/6] 安装 Python 依赖
echo ==============================================================

REM 创建虚拟环境
if not exist ".venv" (
    echo         创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo   [错误] 虚拟环境创建失败
        echo   请尝试以管理员身份运行
        pause
        exit /b 1
    )
)

set "PIP=.venv\Scripts\pip.exe"
set "PYTHON=.venv\Scripts\python.exe"

echo         升级 pip...
"%PIP%" install --upgrade pip -q 2>nul

REM 优先使用本地 wheel 包（内网隔离模式）
if exist "python-wheels" (
    echo         使用本地 wheel 包（内网模式）...
    "%PIP%" install --no-index --find-links="python-wheels" -r requirements.txt
) else (
    echo         从 PyPI 安装依赖（需要互联网）...
    "%PIP%" install -r requirements.txt
)

if errorlevel 1 (
    echo.
    echo   [错误] 依赖安装失败
    echo   建议: 检查 python-wheels 目录是否存在，或检查网络连接
    pause
    exit /b 1
)
echo   [OK] 依赖安装完成
echo.

REM ============================================================================
REM  步骤 6: 初始化配置
REM ============================================================================
echo ==============================================================
echo   [6/6] 初始化配置
echo ==============================================================

REM 设置 Ollama 优化参数
set "OLLAMA_NUM_PARALLEL=1"
set "OLLAMA_MAX_LOADED_MODELS=1"
set "OLLAMA_KEEP_ALIVE=5m"

REM 创建运行时目录
for %%d in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~d" mkdir "%%~d"
)

REM 生成初始 .env 配置
if not exist ".env" (
    echo         生成配置文件 .env ...
    (
        echo # COMAC AI 配置文件
        echo # 请修改以下密码为空闲内网使用
        echo GRADIO_USER=admin
        echo GRADIO_PASS=change_me_123
        echo COMAC_MODEL=qwen:7b-q4_K_M
        echo COMAC_EMBED_MODEL=nomic-embed-text
    ) > .env
    echo   [OK] .env 配置文件已生成，请及时修改密码
)

echo   [OK] 配置完成
echo.

REM ============================================================================
REM  完成
REM ============================================================================
echo ==============================================================
echo   部署初始化完成！
echo ==============================================================
echo.
echo   下一步:
echo   1. 修改 .env 中的 GRADIO_PASS 密码
echo   2. 运行 start.bat 启动服务
echo   3. 访问 http://localhost:7860
echo.
echo   模型: qwen:7b-q4_K_M
echo   认证: admin / (请修改 .env)
echo.
pause
