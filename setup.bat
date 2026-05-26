@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC 离轴线AI文档处理平台 — 部署初始化脚本
REM  模型: qwen:7b-q4_K_M | 空气隔离内网适用
REM ============================================================================

title COMAC AI - 部署初始化

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  步骤 1: 提取内置 Python Embeddable（离线零依赖）
REM ============================================================================
echo.
echo ==============================================================
echo   [1/9] 初始化内置 Python 环境
echo ==============================================================

if exist "tools\python\python.exe" (
    echo   [OK] Python 内置环境已存在，跳过提取
) else (
    if not exist "tools\python-embed.zip" (
        echo   [错误] tools\python-embed.zip 未找到
        echo   请确保项目完整性，重新下载完整安装包
        pause
        exit /b 1
    )
    echo         提取 Python Embeddable（请稍等）...
    mkdir tools\python 2>nul
    powershell -NoProfile -Command "Expand-Archive -Force 'tools\python-embed.zip' 'tools\python'"
    if errorlevel 1 (
        echo   [错误] Python 提取失败
        pause
        exit /b 1
    )
    echo   [OK] Python 提取完成
)

REM ============================================================================
REM  步骤 2: 启用 site-packages 并 bootstrap pip
REM ============================================================================
echo ==============================================================
echo   [2/9] 安装 pip（离线引导）
echo ==============================================================

set "BUNDLE_PY=tools\python\python.exe"

REM 修改 python3._pth 解除 site-packages 限制
set "PTH_FILE=tools\python\python3._pth"
if exist "%PTH_FILE%" (
    findstr /C:"import site" "%PTH_FILE%" >nul 2>&1
    if errorlevel 1 (
        echo         启用 site-packages...
        echo. >> "%PTH_FILE%"
        echo import site >> "%PTH_FILE%"
    )
)

REM 优先从本地 wheel 安装 pip（离线模式，无需互联网）
if not exist "tools\python\Scripts\pip.exe" (
    echo         尝试从本地 wheel 安装 pip（离线模式）...

    REM 方法1: 使用 pip wheel 文件（推荐）
    if exist "python-wheels\pip-" (
        "%BUNDLE_PY%" -m pip install --no-index --find-links="python-wheels" pip --quiet --force-reinstall 2>nul
    )

    REM 方法2: 使用 get-pip.py（需要互联网，首次运行会下载 pip）
    if not exist "tools\python\Scripts\pip.exe" (
        if exist "tools\pip-wheels\get-pip.py" (
            echo         首次运行，需要联网下载 pip（约 10MB）...
            "%BUNDLE_PY%" "tools\pip-wheels\get-pip.py" --no-warn-script-location >nul 2>&1
        )
    )
)

REM 验证 pip
"%BUNDLE_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [错误] pip 安装失败
    echo   请检查 tools\pip-wheels\get-pip.py 是否完整
    pause
    exit /b 1
)
echo   [OK] pip 已就绪
set "PIP=tools\python\python.exe -m pip"
set "PY=tools\python\python.exe"

REM ============================================================================
REM  步骤 3: 安装 Python 依赖（离线 wheel 包）
REM ============================================================================
echo ==============================================================
echo   [3/9] 安装 Python 依赖
echo ==============================================================

if not exist "python-wheels" (
    echo   [错误] python-wheels\ 目录未找到
    echo.
    echo   请在有网机器上运行 download-wheels.bat 下载离线包：
    echo   1. 在有网机器上解压本项目
    echo   2. 双击运行 download-wheels.bat
    echo   3. 将生成的 python-wheels\ 目录一起打包到项目中
    echo   4. 传到内网机器后重新运行本脚本
    pause
    exit /b 1
)

echo         使用本地 wheel 包（内网模式）...
"%PIP%" install --no-index --find-links="python-wheels" -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo   [错误] 依赖安装失败
    echo   请确认 python-wheels\ 目录已完整包含所有依赖包
    echo   如有疑问，在有网机器重新运行 download-wheels.bat 更新包
    pause
    exit /b 1
)
echo   [OK] Python 依赖安装完成
echo.

REM ============================================================================
REM  步骤 4: 提取内置 Ollama（离线零依赖）
REM ============================================================================
echo ==============================================================
echo   [4/9] 初始化内置 Ollama
echo ==============================================================

if exist "tools\ollama\ollama.exe" (
    echo   [OK] Ollama 已提取，跳过
) else (
    if not exist "tools\ollama-windows-amd64.zip" (
        echo   [错误] tools\ollama-windows-amd64.zip 未找到
        pause
        exit /b 1
    )
    echo         提取 Ollama（请稍等，约数秒）...
    powershell -NoProfile -Command "Expand-Archive -Force 'tools\ollama-windows-amd64.zip' 'tools\ollama'"
    if errorlevel 1 (
        echo   [错误] Ollama 提取失败
        pause
        exit /b 1
    )
    echo   [OK] Ollama 提取完成
)

REM ============================================================================
REM  步骤 5: 安装 Visual C++ Redistributable（Ollama 需要）
REM ============================================================================
echo ==============================================================
echo   [5/9] 安装 Visual C++ 运行时
echo ==============================================================

if exist "tools\ollama\vc_redist.x64.exe" (
    echo         检测到 VC++ 安装包，正在静默安装...
    "tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ 运行时已安装
) else (
    echo   [提示] 未找到 VC++ 安装包，跳过
    echo         （如后续运行报错，请手动安装 VC++ Redistributable）
)

REM ============================================================================
REM  步骤 6: 启动 Ollama 服务
REM ============================================================================
echo ==============================================================
echo   [6/9] 启动 Ollama 服务
echo ==============================================================

set "OLLAMA_SERVE=tools\ollama\ollama.exe serve"
set "OLLAMA_HOST=localhost:11434"

REM 检查 Ollama 服务是否已在运行
curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama 服务已在运行
) else (
    echo         启动 Ollama 服务（请稍等）...
    start /B "%OLLAMA_SERVE%" > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [警告] Ollama 启动超时，尝试后台继续...
    echo         （稍后请在 PowerShell 中运行: tools\ollama\ollama.exe serve）
)

:ollama_ok
echo   [OK] Ollama 服务就绪
echo.

REM ============================================================================
REM  步骤 7: 准备 qwen:7b-q4_K_M 模型
REM ============================================================================
echo ==============================================================
echo   [7/9] 准备 qwen:7b-q4_K_M 模型
echo ==============================================================

tools\ollama\ollama.exe list 2>nul | findstr /I "qwen" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen 模型已存在，跳过
) else (
    if exist "ollama-models\*.gguf" (
        echo         发现本地 GGUF 文件，使用离线模式...
        if exist "ollama-models\Modelfile" (
            echo         使用 Modelfile 创建模型（请稍等，首次约1分钟）...
            tools\ollama\ollama.exe create qwen:7b-q4_K_M -f "ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [错误] 模型创建失败，请检查 GGUF 文件和 Modelfile
                pause
                exit /b 1
            )
            echo   [OK] qwen:7b-q4_K_M 模型创建成功
        ) else (
            echo   [错误] 缺少 Modelfile，请检查 ollama-models\ 目录
            pause
            exit /b 1
        )
    ) else (
        echo   [错误] 未找到 GGUF 模型文件
        echo   请将 qwen2.5-7b-instruct-q4_k_m.gguf 放入 ollama-models\ 目录
        echo   或在内网有网的环境运行: tools\ollama\ollama.exe pull qwen:7b-q4_K_M
        pause
        exit /b 1
    )
)
echo.

REM ============================================================================
REM  步骤 8: 准备向量嵌入模型
REM ============================================================================
echo ==============================================================
echo   [8/9] 准备向量嵌入模型（可选）
echo ==============================================================

tools\ollama\ollama.exe list 2>nul | findstr /C:"nomic-embed-text" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] nomic-embed-text 已存在
) else (
    echo   [提示] nomic-embed-text 未找到
    echo         此模型用于 RAG 知识库，如需要请在内网有网时运行:
    echo         tools\ollama\ollama.exe pull nomic-embed-text
    echo         （RAG 功能暂时不可用，不影响其他功能）
)
echo.

REM ============================================================================
REM  步骤 9: 初始化配置
REM ============================================================================
echo ==============================================================
echo   [9/9] 初始化配置
echo ==============================================================

REM 设置 Ollama 优化参数（写入当前用户环境变量）
setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_KEEP_ALIVE=5m

REM 创建运行时目录
for %%d in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~d" mkdir "%%~d" 2>nul
)

REM 生成 .env 配置文件
if not exist ".env" (
    (
        echo # COMAC AI 配置文件
        echo # 请修改以下密码为空闲内网使用
        echo GRADIO_USER=admin
        echo GRADIO_PASS=change_me_123
        echo COMAC_MODEL=qwen:7b-q4_K_M
        echo COMAC_EMBED_MODEL=nomic-embed-text
        echo OLLAMA_HOST=localhost:11434
    ) > .env
    echo   [OK] .env 配置文件已生成
    echo   [重要] 请修改 .env 中的 GRADIO_PASS 密码！
) else (
    echo   [OK] .env 已存在
)

REM ============================================================================
REM  完成
REM ============================================================================
echo ==============================================================
echo   部署初始化完成！
echo ==============================================================
echo.
echo   下一步:
echo   1. 修改 .env 中的 GRADIO_PASS 密码
echo   2. 双击运行 start.bat 启动服务
echo   3. 访问 http://localhost:7860
echo.
echo   内置工具:
echo   - Python: tools\python\python.exe
echo   - Ollama: tools\ollama\ollama.exe
echo   - 模型: qwen:7b-q4_K_M
echo   - 认证: admin / (请修改 .env)
echo.
pause
