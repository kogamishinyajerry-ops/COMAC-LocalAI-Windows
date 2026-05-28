@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================================
REM  ????????????? Python wheel ???? python-wheels\
REM  ???????pip install --no-index --find-links="python-wheels" ??????
REM  ????????pre-deploy.bat??pip install ??????????????
REM ============================================================================

title COMAC AI - ???????? wheel ??

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where python >nul 2>&1
if errorlevel 1 (
    echo   [????] ¦Ä??? Python???????? Python 3.11+
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info[1])" 2^>nul') do set "PY_VER=%%v"
echo   ??? Python 3.!PY_VER!
echo.

echo ==============================================================
echo   ???????? wheel ????? 5-10 ?????
echo ==============================================================
echo.

set "WHEEL_DIR=%SCRIPT_DIR%python-wheels"
mkdir "%WHEEL_DIR%" 2>nul

echo   ?????§µ?pip ????????????§Õ?????????...
python -m pip download -r "%SCRIPT_DIR%requirements.txt" ^
    --dest "%WHEEL_DIR%" ^
    --platform win_amd64 ^
    --python-version 3.!PY_VER! ^
    --only-binary=:all: ^
    --quiet 2>nul

echo.
echo ==============================================================
echo   ???????
echo.

set "CNT=0"
for %%f in ("%WHEEL_DIR%\*.whl") do set /a CNT+=1
if !CNT! GTR 0 (
    echo   python-wheels\ ?? !CNT! ?????
    echo.
    echo   ??????????:
    echo   .venv\Scripts\pip install --no-index --find-links="python-wheels" -r requirements.txt
) else (
    echo   [????] ????????????????
)
echo ==============================================================
echo.
pause
