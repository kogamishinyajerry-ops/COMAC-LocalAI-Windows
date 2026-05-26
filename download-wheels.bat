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

REM 确定使用哪个 pip（优先内置 Python，否则系统 Python）
REM 内置 Python 用于引导 pip（仅这一次），下载用相同的 Python 版本
if exist "%SCRIPT_DIR%tools\python\python.exe" (
    set "PY=%SCRIPT_DIR%tools\python\python.exe"
    echo         使用内置 Python 3.11
) else (
    set "PY=python"
    echo         使用系统 Python
)

REM ============================================================================
REM  引导 pip（如果 tools\python 还没有 pip）
REM ============================================================================
if exist "%SCRIPT_DIR%tools\python\python.exe" (
    if not exist "%SCRIPT_DIR%tools\python\Scripts\pip.exe" (
        echo         首次运行，引导 pip...
        if exist "%SCRIPT_DIR%tools\pip-wheels\get-pip.py" (
            "%PY%" "%SCRIPT_DIR%tools\pip-wheels\get-pip.py" --quiet >nul 2>&1
        )
    )
)

REM 确定下载用的 pip
if exist "%SCRIPT_DIR%tools\python\Scripts\pip.exe" (
    set "PIP=%SCRIPT_DIR%tools\python\Scripts\pip.exe"
) else (
    set "PIP=%PY% -m pip"
)

echo.
echo ==============================================================
echo   正在下载 Python 依赖包（Python 3.11 版本）
echo   此过程需要互联网连接（约 5-10 分钟）
echo ==============================================================
echo.

REM --------------------------------------------------------------------------
REM 步骤 1: 更新 get-pip.py
REM --------------------------------------------------------------------------
echo [1/3] 更新 pip 引导工具...

mkdir "%SCRIPT_DIR%tools\pip-wheels" 2>nul
powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%SCRIPT_DIR%tools\pip-wheels\get-pip.py' -TimeoutSec 30 -UseBasicParsing; Write-Host 'OK' } catch { Write-Host 'SKIP' }"
echo         get-pip.py 已更新
echo.

REM --------------------------------------------------------------------------
REM 步骤 2: 下载 Python wheel 包（含完整依赖）
REM --------------------------------------------------------------------------
echo [2/3] 下载 Python 依赖包到 python-wheels\（请稍等）...

set "WHEEL_DIR=%SCRIPT_DIR%python-wheels"
mkdir "%WHEEL_DIR%" 2>nul

REM 下载所有依赖（pip 自动处理传递依赖）
REM --python-version 3.11 确保下载的 wheel 兼容目标 Python 版本
REM --no-deps: 先不解析依赖，仅下载顶层包（快速）
REM 第二轮: 下载依赖包（由 pip 自动处理）
echo         下载顶层包（约 3 分钟）...
"%PIP%" download -r "%SCRIPT_DIR%requirements.txt" ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --python-version 3.11 ^
    --only-binary=:all: ^
    --no-deps ^
    --quiet 2>nul

REM 第二轮：下载传递依赖（pip 自动解析依赖树）
echo         下载传递依赖（约 3-5 分钟）...
"%PIP%" download -r "%SCRIPT_DIR%requirements.txt" ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --python-version 3.11 ^
    --only-binary=:all: ^
    --quiet 2>nul

REM --------------------------------------------------------------------------
REM 步骤 3: 下载 pip/setuptools/wheel 自身
REM --------------------------------------------------------------------------
echo [3/3] 确认 pip 引导包...

"%PIP%" download pip setuptools wheel ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --python-version 3.11 ^
    --only-binary=:all: ^
    --no-deps ^
    --quiet 2>nul

REM --------------------------------------------------------------------------
REM 完成
REM --------------------------------------------------------------------------
echo.
echo ==============================================================
echo   下载完成！
echo.

REM 统计下载结果
set "WHEEL_COUNT=0"
for %%f in ("%WHEEL_DIR%\*.whl") do set /a WHEEL_COUNT+=1

if %WHEEL_COUNT% GTR 0 (
    echo   python-wheels\ 共 %WHEEL_COUNT% 个文件（约数百 MB）
    echo.
    echo   请将以下目录一起打包传到内网机器：
    echo   - python-wheels\       （含所有依赖包）
    echo   - tools\pip-wheels\    （get-pip.py）
    echo   - tools\python-embed.zip（约 20 MB）
    echo   - tools\ollama-windows-amd64.zip（约 2 GB）
    echo   - .venv\               （如已有）
) else (
    echo   [警告] python-wheels\ 为空，下载可能失败
    echo   请检查网络连接后重新运行
)
echo ==============================================================
echo.
pause
