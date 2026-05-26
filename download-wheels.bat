@echo off
chcp 65001 >nul 2>&1
title COMAC AI - 下载离线依赖包

REM ============================================================================
REM  此脚本在有网络的机器上运行一次，将所有依赖下载到 python-wheels\
REM  下载完成后，整个 python-wheels 文件夹可一起打包，内网机器即可离线安装
REM ============================================================================

echo.
echo ==============================================================
echo   正在下载 Python 依赖包到 python-wheels\
echo   此过程需要互联网连接
echo ==============================================================
echo.

set "WHEEL_DIR=%~dp0python-wheels"
mkdir "%WHEEL_DIR%" 2>nul

REM 下载所有依赖（包含平台相关轮子）
pip download -r "%~dp0requirements.txt" ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --only-binary=:all: ^
    --python-version 3.11 ^
    --no-deps

if errorlevel 1 (
    echo.
    echo [警告] 部分平台专属包下载失败，尝试下载通用包...
    pip download -r "%~dp0requirements.txt" --dest "%WHEEL_DIR%" --no-deps
)

echo.
echo ==============================================================
echo   下载完成！
echo.
echo   python-wheels\ 目录已包含所有依赖包
echo   将整个目录和项目一起打包，传输到内网机器后
echo   setup.bat 会自动使用本地包，无需互联网
echo ==============================================================
echo.
echo   当前 python-wheels\ 内容：
dir /b "%WHEEL_DIR%" | find /c /v ""
echo   个文件
dir /b "%WHEEL_DIR%"
echo.
pause
