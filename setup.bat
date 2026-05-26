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
REM  步骤 1: 检查 / 安装 Python 运行时
REM ============================================================================
echo.
echo ==============================================================
echo   [1/9] 检查 Python 运行环境
echo ==============================================================

set "FOUND_PY="
set "FOUND_PY_VER="

REM 优先使用内置 Python（tools\python\python.exe = Embeddable 3.11）
REM 注意：Embeddable 无法创建 venv，仅用于 bootstrap
if exist "%SCRIPT_DIR%tools\python\python.exe" (
    set "FOUND_PY=%SCRIPT_DIR%tools\python\python.exe"
    set "FOUND_PY_VER=embed"
    echo   [OK] 发现内置 Python (Embeddable 3.11)
)

REM 查找系统 Python（python.org / Microsoft Store）
if not defined FOUND_PY (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%v in ('python -c "import sys;print(sys.version_info[1])" 2^>nul') do set "SYS_PY_VER=%%v"
        if defined SYS_PY_VER (
            if "!SYS_PY_VER!"=="11" (
                set "FOUND_PY=python"
                set "FOUND_PY_VER=system-3.11"
                echo   [OK] 发现系统 Python 3.11
            )
        )
    )
)

REM 未找到任何 Python
if not defined FOUND_PY (
    echo   [错误] 未找到 Python 运行时
    echo.
    echo   请选择以下方式之一：
    echo.
    echo   方式 A（推荐）: 在有网机器下载 Python 3.11 安装包：
    echo      https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    echo      将安装包重命名为 python-3.11.8-amd64.exe 放入 tools\ 目录
    echo.
    echo   方式 B: 从 Microsoft Store 安装 Python 3.11（需联网）
    echo      在 PowerShell 中运行:  wmic product where "name like '%%Python 3.11%%'" call install
    echo      或在 Microsoft Store 搜索 "Python 3.11"
    echo.
    echo   方式 C: 下载 embeddable 版（无 venv 支持，仅基础功能）
    echo      https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip
    echo      解压到 tools\python\ 后放入 tools\python-embed.zip
    echo.
    pause
    exit /b 1
)

if not "%FOUND_PY_VER%"=="embed" (
    echo         使用系统 Python 创建虚拟环境
) else (
    echo         注意: Embeddable 版无法创建 venv，将使用 --target 模式
)

REM ============================================================================
REM  步骤 2: Bootstrap pip（仅 Embeddable 需要，系统 Python 已有 pip）
REM ============================================================================
echo ==============================================================
echo   [2/9] 准备 pip
echo ==============================================================

if not "%FOUND_PY_VER%"=="embed" (
    echo   [OK] 系统 Python 已有 pip，跳过
    set "PY=%FOUND_PY%"
    set "PIP=pip"
) else (
    REM Embeddable: 启用 site-packages + 引导 pip
    for %%f in ("%SCRIPT_DIR%tools\python\python311._pth" "%SCRIPT_DIR%tools\python\python3._pth") do (
        if exist "%%~ff" (
            set "PTH_FILE=%%~ff"
            goto :found_pth
        )
    )
    :found_pth
    if defined PTH_FILE (
        findstr /R "^import site" "%PTH_FILE%" >nul 2>&1
        if errorlevel 1 (
            echo         启用 site-packages...
            echo import site>> "%PTH_FILE%"
        )
    )

    if not exist "%SCRIPT_DIR%tools\python\Scripts\pip.exe" (
        REM 尝试本地 wheel（download-wheels.bat 预载的）
        for %%w in ("%SCRIPT_DIR%python-wheels\pip-"*.whl) do (
            if exist "%%~fw" (
                echo         发现本地 pip wheel（离线模式）...
                "%FOUND_PY%" -m pip install --no-index --find-links="%SCRIPT_DIR%python-wheels" pip --quiet --force-reinstall 2>nul
                goto :pip_done_embed
            )
        )
        REM Fallback: get-pip.py（需联网约 10MB）
        if exist "%SCRIPT_DIR%tools\pip-wheels\get-pip.py" (
            echo         首次运行，需联网下载 pip（约 10MB）...
            "%FOUND_PY%" "%SCRIPT_DIR%tools\pip-wheels\get-pip.py" --no-warn-script-location >nul 2>&1
        )
        :pip_done_embed
    )
    "%FOUND_PY%" -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo   [错误] pip 安装失败
        pause
        exit /b 1
    )
    echo   [OK] pip 已就绪
    set "PY=%FOUND_PY%"
    set "PIP=%FOUND_PY% -m pip"
)

REM ============================================================================
REM  步骤 3: 创建 / 准备 Python 虚拟环境
REM ============================================================================
echo ==============================================================
echo   [3/9] 准备 Python 虚拟环境
echo ==============================================================

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo   [OK] .venv 已存在，跳过
) else (
    if not "%FOUND_PY_VER%"=="embed" (
        REM 系统 Python：标准 venv 创建
        echo         创建 .venv（使用系统 Python）...
        %FOUND_PY% -m venv .venv --clear >nul 2>&1
        if errorlevel 1 (
            echo   [错误] .venv 创建失败
            pause
            exit /b 1
        )
        echo   [OK] .venv 创建完成
    ) else (
        REM Embeddable: 无法创建 venv，提示需要系统 Python 或预置 .venv
        echo   [错误] Embeddable Python 无法创建虚拟环境
        echo.
        echo   请选择以下方案之一：
        echo.
        echo   方案 1（推荐）: 安装 Python 3.11 后重新运行
        echo      将 python-3.11.8-amd64.exe 放入 tools\ 目录
        echo      setup.bat 会自动检测并使用系统 Python 创建 .venv
        echo.
        echo   方案 2: 预置 .venv（从开发机直接拷贝）
        echo      将包含所有依赖的 .venv 目录直接复制到项目根目录
        echo      （无需运行 setup.bat 步骤 3/4）
        echo.
        pause
        exit /b 1
    )
)

REM ============================================================================
REM  步骤 4: 安装 Python 依赖到 .venv
REM ============================================================================
echo ==============================================================
echo   [4/9] 安装 Python 依赖
echo ==============================================================

set "VENV_PIP=%SCRIPT_DIR%.venv\Scripts\pip.exe"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%VENV_PIP%" (
    echo   [错误] .venv 未正确创建
    pause
    exit /b 1
)

REM 验证 .venv 中是否已有依赖（预置 .venv 场景）
"%VENV_PY%" -c "import gradio; import ollama; import pandas; print('OK')" 2>nul
if not errorlevel 1 (
    echo   [OK] .venv 中已有依赖，跳过安装
    goto :deps_skip_install
)

REM .venv 为空，需要安装依赖
if exist "%SCRIPT_DIR%python-wheels" (
    REM 离线模式：使用本地 wheel
    for %%w in ("%SCRIPT_DIR%python-wheels\pip-"*.whl) do (
        if exist "%%~fw" (
            echo         发现本地 wheel 包（离线模式）...
            "%VENV_PIP%" install --no-index --find-links="%SCRIPT_DIR%python-wheels" -r "%SCRIPT_DIR%requirements.txt" --quiet --disable-pip-version-check
            if not errorlevel 1 goto :deps_ok
        )
    )
    REM 有 python-wheels 但没有 pip wheel：尝试在线安装
    echo         尝试在线安装依赖（需要有网）...
    "%VENV_PIP%" install -r "%SCRIPT_DIR%requirements.txt" --quiet --disable-pip-version-check
) else (
    REM 无 python-wheels：必须在线安装
    echo         python-wheels\ 不存在，尝试在线安装（需要有网）...
    "%VENV_PIP%" install -r "%SCRIPT_DIR%requirements.txt" --quiet --disable-pip-version-check
)

:deps_ok
REM 验证核心依赖
"%VENV_PY%" -c "import gradio; import ollama; import pandas; print('OK')" 2>nul
if errorlevel 1 (
    echo   [错误] 依赖安装失败
    echo   请在有网机器运行 download-wheels.bat 下载离线包
    pause
    exit /b 1
)
echo   [OK] Python 依赖安装完成
:deps_skip_install
echo.

REM ============================================================================
REM  步骤 5: 提取内置 Ollama（离线零依赖）
REM ============================================================================
echo ==============================================================
echo   [5/9] 初始化内置 Ollama
echo ==============================================================

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs" 2>nul

if exist "%SCRIPT_DIR%tools\ollama\ollama.exe" (
    echo   [OK] Ollama 已提取，跳过
) else (
    if not exist "%SCRIPT_DIR%tools\ollama-windows-amd64.zip" (
        echo   [错误] tools\ollama-windows-amd64.zip 未找到
        pause
        exit /b 1
    )
    echo         提取 Ollama（请稍等）...
    powershell -NoProfile -Command "Expand-Archive -Force '%SCRIPT_DIR%tools\ollama-windows-amd64.zip' '%SCRIPT_DIR%tools\ollama'"
    if errorlevel 1 (
        echo   [错误] Ollama 提取失败
        pause
        exit /b 1
    )
    echo   [OK] Ollama 提取完成
)

REM ============================================================================
REM  步骤 6: 安装 Visual C++ Redistributable
REM ============================================================================
echo ==============================================================
echo   [6/9] 安装 Visual C++ 运行时
echo ==============================================================

if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         检测到 VC++ 安装包，正在静默安装...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ 运行时已安装
) else (
    echo   [提示] 未找到 VC++ 安装包，跳过
    echo         （如后续运行报错，请手动安装 VC++ Redistributable）
)

REM ============================================================================
REM  步骤 7: 启动 Ollama 服务
REM ============================================================================
echo ==============================================================
echo   [7/9] 启动 Ollama 服务
echo ==============================================================

set "OLLAMA_SERVE=%SCRIPT_DIR%tools\ollama\ollama.exe serve"
set "OLLAMA_HOST=localhost:11434"

curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama 服务已在运行
) else (
    echo         启动 Ollama 服务（请稍等）...
    start /B "" "%OLLAMA_SERVE%" > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://%OLLAMA_HOST%/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [警告] Ollama 启动超时，继续...
)

:ollama_ok
echo   [OK] Ollama 服务就绪
echo.

REM ============================================================================
REM  步骤 8: 准备 qwen:7b-q4_K_M 模型
REM ============================================================================
echo ==============================================================
echo   [8/9] 准备 qwen:7b-q4_K_M 模型
echo ==============================================================

REM 路径1: Ollama 缓存中已有（之前用 download-model.bat 拉取过）
"%SCRIPT_DIR%tools\ollama\ollama.exe" list 2>nul | findstr /I "qwen" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen 模型已存在（Ollama 缓存）
) else (
    REM 路径2: 本地 GGUF 文件（离线部署模式）
    if exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo         发现本地 GGUF 文件，使用 Modelfile 创建模型（请稍等）...
        if exist "%SCRIPT_DIR%ollama-models\Modelfile" (
            "%SCRIPT_DIR%tools\ollama\ollama.exe" create qwen:7b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [错误] 模型创建失败，请检查 GGUF 文件和 Modelfile
                pause
                exit /b 1
            )
            echo   [OK] qwen:7b-q4_K_M 模型创建成功
        ) else (
            echo   [错误] 缺少 Modelfile
            pause
            exit /b 1
        )
    ) else (
        REM 路径3: Ollama 在线拉取（内网有网时）
        echo         未找到本地模型，尝试 Ollama 在线拉取（约 4.5 GB）...
        "%SCRIPT_DIR%tools\ollama\ollama.exe" pull qwen:7b-q4_K_M
        if errorlevel 1 (
            echo   [错误] 模型准备失败
            echo   请双击运行 download-model.bat 下载模型
            pause
            exit /b 1
        )
        echo   [OK] qwen:7b-q4_K_M 模型拉取成功
    )
)
echo.

REM ============================================================================
REM  步骤 9: 准备向量嵌入模型 + 初始化配置
REM ============================================================================
echo ==============================================================
echo   [9/9] 初始化配置
echo ==============================================================

"%SCRIPT_DIR%tools\ollama\ollama.exe" list 2>nul | findstr /C:"nomic-embed-text" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] nomic-embed-text 已存在
) else (
    echo   [提示] nomic-embed-text 未找到（不影响其他功能）
    echo         如需 RAG 知识库，请双击运行 download-model.bat
)

REM Ollama 环境变量
setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

REM 创建运行时目录
for %%d in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~dd" mkdir "%%~dd" 2>nul
)

REM 生成 .env
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
echo   - Python: .venv\Scripts\python.exe
echo   - Ollama: tools\ollama\ollama.exe
echo   - 模型: qwen:7b-q4_K_M
echo   - 认证: admin / (请修改 .env)
echo.
pause
