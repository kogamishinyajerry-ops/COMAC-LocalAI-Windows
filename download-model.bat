@echo off
chcp 65001 >nul 2>&1
setlocal

REM ============================================================================
REM  Qwen3-4B GGUF 家?ㄣ
REM  崩よ: pre-deploy.bat ?ЧΘ┮Τ﹍て
REM  セ庎セ: ?ノも塚? GGUF 家ゅン ollama-models/
REM ============================================================================

title COMAC AI - ? Qwen3-4B 家

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ==============================================================
echo   Qwen3-4B GGUF 家?ㄣ
echo ==============================================================
echo.
echo   崩钡漙︽ pre-deploy.bat ?ЧΘ场﹍て
echo   セㄣノも塚? GGUF ゅン ollama-models/ ヘ?
echo.

if exist "ollama-models\qwen3-4b-instruct-q4_k_m.gguf" (
    echo   [OK] GGUF ゅン: ollama-models\qwen3-4b-instruct-q4_k_m.gguf
    pause
    exit /b 0
)

echo   ????よΑ:
echo.
echo   よΑ 1: HuggingFace CDN ?? (崩? 2.5GB)
echo.
echo   よΑ 2: も塚? (も塚 HuggingFace 蔍嬶?)
echo.
echo ==============================================================
echo.

set /p CHOICE="?橾?? (1/2): "

if "%CHOICE%"=="1" goto :hf_download
if "%CHOICE%"=="2" goto :manual
echo   橾朴
pause
exit /b 1

:hf_download
echo.
echo   タ熛 HuggingFace ? GGUF ゅン (? 2.5 GB)...
echo   ヘ?: ollama-models\qwen3-4b-instruct-q4_k_m.gguf
echo.

if not exist "ollama-models" mkdir "ollama-models"

set "HF_URL=https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF/resolve/main/Qwen_Qwen3-4B-GGUF-q4_k_m.gguf"
set "DEST=ollama-models\qwen3-4b-instruct-q4_k_m.gguf"

curl -L -C - -o "%DEST%" "%HF_URL%"
if errorlevel 1 (
    echo.
    echo   [ア?] 塚?ア????よΑ 2 も塚?
    pause
    exit /b 1
)

for %%a in ("%DEST%") do set "SIZE=%%~za"
if defined SIZE (
    set /a SIZE_MB=%SIZE% / 1048576
    echo.
    echo   ?ЧΘゅン: !SIZE_MB! MB
)
echo.
echo   ?˙?: 漙︽ pre-deploy.bat ┪ setup.bat
pause
exit /b 0

:manual
echo.
echo ==============================================================
echo   も塚??
echo ==============================================================
echo.
echo   1. ゴ???竟??:
echo.
echo      https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF
echo.
echo   2. ?ゅン (? 2.5 GB):
echo.
echo      qwen3-4b-instruct-q4_k_m.gguf
echo.
echo   3. ??ゅン:
echo.
echo      ollama-models\qwen3-4b-instruct-q4_k_m.gguf
echo.
echo   4. 漙︽ pre-deploy.bat ┪ setup.bat
echo.
echo   ?:
echo   %HF_URL%
echo.
pause
