@echo off
chcp 65001 >nul
echo ================================================
echo  COMAC-LocalAI-Windows 一键下载脚本
echo ================================================
echo.
echo 此脚本用于在有网设备上准备完整部署包
echo 完成后请将整个目录拷贝到内网机器
echo.

:: 检查 Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未安装 Git
    echo 请先安装 Git: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: 检查是否已有目录
if exist "COMAC-LocalAI-Windows" (
    echo [警告] COMAC-LocalAI-Windows 目录已存在
    echo 将更新为最新版本
    cd COMAC-LocalAI-Windows
    git pull
    goto :download_tools
)

:: 克隆仓库
echo.
echo [1/4] 克隆 GitHub 仓库...
git clone https://github.com/kogamishinyajerry-ops/COMAC-LocalAI-Windows.git
if %errorlevel% neq 0 (
    echo [错误] 克隆仓库失败
    pause
    exit /b 1
)
cd COMAC-LocalAI-Windows

:download_tools
:: 下载 Ollama
echo.
echo [2/4] 下载 Ollama 便携版（约 2GB）...
echo 请访问: https://github.com/ollama/ollama/releases/latest
echo 下载: ollama-windows-amd64.zip
echo 保存到: %CD%\tools\ollama-windows-amd64.zip
echo.
echo 按回车键打开下载页面...
pause
start https://github.com/ollama/ollama/releases/latest

echo.
echo 下载完成后，将 ollama-windows-amd64.zip 放入 tools\ 目录
echo 然后按回车键继续
pause

:: 检查 Ollama zip
if not exist "tools\ollama-windows-amd64.zip" (
    echo [警告] tools\ollama-windows-amd64.zip 未找到
    echo 可以稍后手动放入
)

:: 下载 Python Embeddable
echo.
echo [3/4] 下载 Python Embeddable（约 25MB）...
echo 请访问: https://www.python.org/ftp/python/3.11.8/
echo 下载: python-3.11.8-embed-amd64.zip
echo 保存到: %CD%\tools\python-3.11.8-embed-amd64.zip
echo.
echo 按回车键打开下载页面...
pause
start https://www.python.org/ftp/python/3.11.8/

echo.
echo 下载完成后，将 python-3.11.8-embed-amd64.zip 放入 tools\ 目录
echo 然后按回车键继续
pause

:: 检查 Python zip
if not exist "tools\python-3.11.8-embed-amd64.zip" (
    echo [警告] tools\python-3.11.8-embed-amd64.zip 未找到
    echo 可以稍后手动放入
)

:: 下载模型
echo.
echo [4/4] 下载 LLM 模型（约 4-5GB，可选）...
echo 请访问: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main
echo 下载: qwen2.5-7b-q4_k_m.gguf（约 4.4GB）
echo 保存到: %CD%\ollama-models\
echo.
echo 按回车键打开下载页面（或输入 N 跳过）...
pause >nul
set "choice="
set /p choice="是否打开下载页面? (Y/N): "
if /i "%choice%"=="Y" (
    start https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main
)

:: 完成
echo.
echo ================================================
echo  下载准备完成！
echo ================================================
echo.
echo 请执行以下操作：
echo 1. 将 COMAC-LocalAI-Windows 整个目录拷贝到移动硬盘
echo 2. 在内网机器上双击运行 setup.bat
echo 3. 双击运行 start.bat 启动服务
echo 4. 浏览器访问 http://localhost:7860
echo.
echo 如果模型未下载，可以在内网机器上运行 download-model.bat
echo.
pause
