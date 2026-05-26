@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  此脚本在有网络的机器上运行一次
REM  将所有依赖下载到 python-wheels\，同时更新 tools/pip-wheels/
REM  下载完成后，整个目录打包传到内网机器即可离线使用
REM ============================================================================

title COMAC AI - 下载离线依赖包

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 确定 pip 命令（优先内置 Python，否则系统 Python）
if exist "tools\python\python.exe" (
    set "PY=tools\python\python.exe"
    set "PIP=tools\python\python.exe -m pip"
    echo         使用内置 Python
) else (
    set "PY=python"
    set "PIP=pip"
    echo         使用系统 Python
)

REM 尝试 bootstrap pip（如果内置 Python 没有 pip）
if exist "tools\python\python.exe" (
    if not exist "tools\python\Scripts\pip.exe" (
        echo         尝试引导 pip（首次运行）...
        if exist "tools\pip-wheels\get-pip.py" (
            tools\python\python.exe tools\pip-wheels\get-pip.py --quiet >nul 2>&1
        )
    )
)

echo.
echo ==============================================================
echo   正在下载 Python 依赖包
echo   此过程需要互联网连接（约 5-10 分钟）
echo ==============================================================
echo.

REM --------------------------------------------------------------------------
REM 步骤 1: 下载 get-pip.py（pip 引导工具）
REM --------------------------------------------------------------------------
echo [1/3] 更新 pip 引导工具...

mkdir "tools\pip-wheels" 2>nul
powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'tools\pip-wheels\get-pip.py' -TimeoutSec 30 -UseBasicParsing; Write-Host 'OK' } catch { Write-Host 'SKIP' }"
echo         get-pip.py 已更新
echo.

REM --------------------------------------------------------------------------
REM 步骤 2: 下载 Python wheel 包（平台专用）
REM --------------------------------------------------------------------------
echo [2/3] 下载 Python 依赖包到 python-wheels\（请稍等）...

set "WHEEL_DIR=%SCRIPT_DIR%python-wheels"
mkdir "%WHEEL_DIR%" 2>nul

REM 优先下载平台专用轮子（win_amd64）
"%PIP%" download -r requirements.txt ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --only-binary=:all: ^
    --python-version 3.11 ^
    --no-deps ^
    --quiet

if errorlevel 1 (
    echo         [提示] 部分包下载失败，补充通用轮子...
    "%PIP%" download -r requirements.txt --dest "%WHEEL_DIR%" --no-deps --quiet
)

echo         wheel 包下载完成

REM --------------------------------------------------------------------------
REM 步骤 3: 下载 pip/setuptools/wheel 自身（引导用）
REM --------------------------------------------------------------------------
echo [3/3] 下载 pip 自身到 python-wheels\（离线引导用）...

"%PIP%" download pip setuptools wheel ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --only-binary=:all: ^
    --python-version 3.11 ^
    --no-deps ^
    --quiet

echo.

REM --------------------------------------------------------------------------
REM 完成
REM --------------------------------------------------------------------------
echo ==============================================================
echo   下载完成！
echo.
echo   python-wheels\ 已包含所有依赖包
echo   tools\pip-wheels\ 已包含 get-pip.py
echo.
echo   请将以下目录一起打包传到内网机器：
echo   - python-wheels\      （约数百 MB）
echo   - tools\pip-wheels\ （几 MB）
echo   - tools\python-embed.zip（约 20 MB）
echo   - tools\ollama-windows-amd64.zip（约 2 GB）
echo.
echo   当前 python-wheels\ 内容：
dir /b "%WHEEL_DIR%" 2>nul | findstr /V "^-"
echo         共 ~ 个文件
echo ==============================================================
echo.
pause
