@echo off
chcp 65001 >nul 2>&1
setlocal

REM ============================================================================
REM  辅助工具：下载 Python wheel 包到 python-wheels\
REM  主用途：pip install --no-index --find-links="python-wheels" 离线安装
REM  推荐方式：pre-deploy.bat（pip install 直接安装，更可靠）
REM ============================================================================

title COMAC AI - 下载离线 wheel 包

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where python >nul 2>&1
if errorlevel 1 (
    echo   [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PY_VER=%%v"
echo   检测到 Python 3.!PY_VER!
echo.

echo ==============================================================
echo   正在下载 wheel 包（约 5-10 分钟）
echo ==============================================================
echo.

set "WHEEL_DIR=%SCRIPT_DIR%python-wheels"
mkdir "%WHEEL_DIR%" 2>nul

echo   下载中（pip 会自动处理所有传递依赖）...
python -m pip download -r "%SCRIPT_DIR%requirements.txt" ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --python-version 3.!PY_VER! ^
    --only-binary=:all: ^
    --quiet 2>nul

echo.
echo ==============================================================
echo   下载完成
echo.

set "CNT=0"
for %%f in ("%WHEEL_DIR%\*.whl") do set /a CNT+=1
if !CNT! GTR 0 (
    echo   python-wheels\ 共 !CNT! 个文件
    echo.
    echo   离线安装方法:
    echo   .venv\Scripts\pip install --no-index --find-links="python-wheels" -r requirements.txt
) else (
    echo   [警告] 下载失败，请检查网络
)
echo ==============================================================
echo.
pause
