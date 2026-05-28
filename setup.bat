@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  COMAC-LocalAI-Windows — 部署初始化脚本（内网验证模式）
REM
REM  用途：
REM    - 内网机器（无网）: 检查所有组件就绪，启动服务
REM    - 有网机器（首次）: 运行 pre-deploy.bat 完成全部初始化
REM
REM  模型: qwen:7b-q4_K_M | Python 3.11+ | Windows 10+
REM ============================================================================

title COMAC AI - 部署初始化

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ============================================================================
REM  步骤 1: 检查 Python 运行时（必须是系统 Python，Embeddable 不可用）
REM ============================================================================
echo.
echo ==============================================================
echo   [1/7] 检查 Python 运行环境
echo ==============================================================

set "CHECK_PY="
set "CHECK_PY_VER="

where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "CHECK_PY_VER=%%v"
    if defined CHECK_PY_VER (
        if !CHECK_PY_VER! GEQ 11 (
            set "CHECK_PY=python"
            echo   [OK] 发现系统 Python 3.!CHECK_PY_VER!
        )
    )
)

if not defined CHECK_PY (
    REM 尝试使用内置 Python 安装包
    if exist "%SCRIPT_DIR%tools\python-3.11.8-amd64.exe" (
        echo         未找到系统 Python，使用内置安装包...
        echo         安装到 %LOCALAPPDATA%\Programs\Python\Python311
        "%SCRIPT_DIR%tools\python-3.11.8-amd64.exe" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0
        if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set "CHECK_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
            echo   [OK] Python 3.11 已安装
        ) else (
            echo   [错误] Python 安装失败
            pause
            exit /b 1
        )
    ) else (
        echo   [错误] 未找到 Python 3.11+
        echo.
        echo   本项目需要 Python 3.11 或更高版本。
        echo.
        echo   请在有网机器下载安装：
        echo   https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
        echo.
        echo   安装时请务必勾选: "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
)

REM 验证 .venv 的 Python 版本与系统 Python 一致
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    for /f "delims=" %%v in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import sys; print(sys.version_info[1])" 2^>nul') do set "VENV_PY_VER=%%v"
    if defined VENV_PY_VER (
        if not "!VENV_PY_VER!"=="!CHECK_PY_VER!" (
            echo.
            echo   [错误] .venv 版本 (!VENV_PY_VER!) 与系统 Python 版本 (!CHECK_PY_VER!) 不匹配
            echo.
            echo   请在同一台机器上创建 .venv，或删除 .venv 后重新运行 pre-deploy.bat
            echo.
            pause
            exit /b 1
        )
        echo   [OK] .venv Python 版本匹配（3.!VENV_PY_VER!）
    )
)

REM ============================================================================
REM  步骤 2: 验证 .venv 依赖完整性
REM ============================================================================
echo ==============================================================
echo   [2/7] 验证 .venv 依赖
echo ==============================================================

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo   [错误] .venv 不存在
    echo.
    echo   请先在有网机器运行 pre-deploy.bat 创建完整环境：
    echo   1. 将本项目复制到有网机器
    echo   2. 双击运行 pre-deploy.bat
    echo   3. 等待初始化完成（约 10-20 分钟）
    echo   4. 将整个项目目录复制到内网机器
    echo.
    pause
    exit /b 1
)

set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM 快速验证核心依赖
"%VENV_PY%" -c "import gradio; import ollama; import pandas; import docx; import pptx; import openpyxl; import pdfplumber; import pymupdf; import jinja2; import numpy; import colorama; print('OK')" 2>nul
if errorlevel 1 (
    echo   [错误] .venv 依赖不完整
    echo.
    echo   请在有网机器重新运行 pre-deploy.bat
    echo.
    pause
    exit /b 1
)
echo   [OK] .venv 依赖完整
echo.

REM ============================================================================
REM  步骤 3: 提取内置 Ollama
REM ============================================================================
echo ==============================================================
echo   [3/7] 初始化内置 Ollama
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
    if errorlevel 1 (
        echo   [错误] Ollama 提取失败
        pause
        exit /b 1
    )
    echo   [OK] Ollama 提取完成
)

REM ============================================================================
REM  步骤 4: 安装 Visual C++ Redistributable
REM ============================================================================
echo ==============================================================
echo   [4/7] 安装 Visual C++ 运行时
echo ==============================================================

if exist "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" (
    echo         检测到 VC++ 安装包，正在静默安装...
    "%SCRIPT_DIR%tools\ollama\vc_redist.x64.exe" /install /quiet /norestart /log "%SCRIPT_DIR%logs\vc_install.log"
    echo   [OK] VC++ 运行时已安装
) else (
    echo   [提示] 未找到 VC++ 安装包，跳过
)

REM ============================================================================
REM  步骤 5: 启动 Ollama 服务
REM ============================================================================
echo ==============================================================
echo   [5/7] 启动 Ollama 服务
echo ==============================================================

set "OLLAMA_BIN=%SCRIPT_DIR%tools\ollama\ollama.exe"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

REM 检查 Ollama 服务是否已运行
curl -s --connect-timeout 3 "http://localhost:11434/api/version" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Ollama 服务已在运行
) else (
    echo         启动 Ollama 服务（请稍等）...
    start /B "" "%OLLAMA_BIN%" serve > "%SCRIPT_DIR%logs\ollama.log" 2>&1
    for /L %%i in (1,1,20) do (
        timeout /t 2 /nobreak >nul
        curl -s --connect-timeout 3 "http://localhost:11434/api/version" >nul 2>&1
        if not errorlevel 1 goto :ollama_ok
    )
    echo   [警告] Ollama 启动超时，继续...
)
:ollama_ok
echo   [OK] Ollama 服务就绪
echo.

REM ============================================================================
REM  步骤 6: 检查 qwen:7b-q4_K_M 模型
REM ============================================================================
echo ==============================================================
echo   [6/7] 检查 qwen 模型
echo ==============================================================

"%OLLAMA_BIN%" list 2>nul | findstr /C:"qwen:7b-q4_K_M" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] qwen 模型已就绪（Ollama 缓存）
) else (
    if exist "%SCRIPT_DIR%ollama-models\*.gguf" (
        echo         发现本地 GGUF 文件，使用 Modelfile 创建模型（请稍等）...
        if exist "%SCRIPT_DIR%ollama-models\Modelfile" (
            "%OLLAMA_BIN%" create qwen:7b-q4_K_M -f "%SCRIPT_DIR%ollama-models\Modelfile"
            if errorlevel 1 (
                echo   [错误] 模型创建失败
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
        echo   [错误] 未找到 GGUF 模型文件
        echo.
        echo   请在有网机器运行 pre-deploy.bat 下载模型
        echo   或将 qwen2.5-7b-instruct-q4_k_m.gguf 放入 ollama-models\
        pause
        exit /b 1
    )
)
echo.

REM ============================================================================
REM  步骤 7: 初始化配置
REM ============================================================================
echo ==============================================================
echo   [7/7] 初始化配置
echo ==============================================================

REM Ollama 环境变量（当前 CMD 会话生效）
setx OLLAMA_NUM_PARALLEL 1 >nul 2>&1
setx OLLAMA_MAX_LOADED_MODELS 1 >nul 2>&1
setx OLLAMA_KEEP_ALIVE 5m >nul 2>&1

REM 创建运行时目录
for %%D in (
    "temp\uploads"
    "temp\outputs"
    "temp\reports"
    "logs"
    "docs"
) do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)

REM 生成 .env
if not exist ".env" (
    REM 使用 PowerShell 生成随机 16 位密码
    for /f "delims=" %%P in ('powershell -NoProfile -Command "-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 16 | %%{[char]$_})"') do set "RANDOM_PASS=%%P"
    (
        echo # COMAC AI 配置文件
        echo # 首次部署已自动生成随机密码
        echo GRADIO_USER=admin
        echo GRADIO_PASS=!RANDOM_PASS!
        echo COMAC_MODEL=qwen:7b-q4_K_M
        echo COMAC_EMBED_MODEL=nomic-embed-text
        echo OLLAMA_HOST=localhost:11434
    ) > .env
    echo   [OK] .env 已生成
    echo   [重要] 初始密码: !RANDOM_PASS!（请妥善保存）
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
echo   组件状态:
echo   - Python: !CHECK_PY_VER!  (系统)
echo   - .venv:  完整
echo   - Ollama: tools\ollama\ollama.exe
echo   - 模型:   qwen:7b-q4_K_M
echo   - 认证:   admin / (请修改 .env)
echo.
pause
