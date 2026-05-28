@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM =============================================================================
REM COMAC-LocalAI-Windows — 离线包构建脚本
REM 在有网机器上运行，生成 offline_bundle/ 完整离线包
REM 使用方法：双击 build-offline-package.bat 或在 CMD 中运行
REM =============================================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "BUNDLE_DIR=%SCRIPT_DIR%\offline_bundle"

echo.
echo ============================================================
echo   COMAC-LocalAI-Windows — 离线包构建脚本
echo   目标目录: %BUNDLE_DIR%
echo ============================================================
echo.

REM =============================================================================
REM 步骤 1：检查 Python 3.11+
REM =============================================================================
echo [检查] 正在检查 Python 3.11+ ...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python。请安装 Python 3.11+
    echo        下载链接：https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%D in ('python --version 2^>^&1') do set "PY_VERSION=%%D"
for /f "tokens=1 delims=." %%D in ("!PY_VERSION!") do set "PY_MAJOR=%%D"
for /f "tokens=2 delims=." %%D in ("!PY_VERSION!") do set "PY_MINOR=%%D"

if !PY_MAJOR! lss 3 (
    echo [错误] Python 版本过低: !PY_VERSION!，需要 Python 3.11+
    echo        当前主版本: !PY_MAJOR!，需要 3.x
    pause
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 11 (
    echo [错误] Python 版本过低: !PY_VERSION!，需要 Python 3.11+
    echo        当前: 3.!PY_MINOR!，需要 ≥ 3.11
    pause
    exit /b 1
)

echo [OK]   Python !PY_VERSION! 已就绪

REM =============================================================================
REM 步骤 2：检查 Ollama 安装包
REM =============================================================================
echo [检查] 正在检查 tools\ollama-windows-amd64.zip ...

if not exist "%SCRIPT_DIR%\tools\ollama-windows-amd64.zip" (
    echo [错误] 未找到 tools\ollama-windows-amd64.zip
    echo        请先从 https://ollama.com/download/windows 下载
    echo        将下载的 OllamaSetup.exe 重命名或直接放置
    echo        ollama-windows-amd64.zip 到 tools\ 目录
    pause
    exit /b 1
)

echo [OK]   tools\ollama-windows-amd64.zip 已就绪

REM =============================================================================
REM 步骤 3：检查 Python 安装程序
REM =============================================================================
echo [检查] 正在检查 tools\python-3.11.8-amd64.exe ...

if not exist "%SCRIPT_DIR%\tools\python-3.11.8-amd64.exe" (
    echo [提示] 未找到 tools\python-3.11.8-amd64.exe
    echo        这是内网机器上安装 Python 3.11.8 所需的离线安装包
    echo.
    echo        请从以下地址下载并放置到 tools\ 目录：
    echo        https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    echo.
    echo        按任意键继续（将跳过 Python 安装包复制）...
    pause >nul
    set "PYTHON_INSTALLER_MISSING=1"
) else (
    echo [OK]   tools\python-3.11.8-amd64.exe 已就绪
    set "PYTHON_INSTALLER_MISSING=0"
)

REM =============================================================================
REM 步骤 4：检查 Ollama 模型文件
REM =============================================================================
echo [检查] 正在检查 ollama-models\ 目录 ...

if not exist "%SCRIPT_DIR%\ollama-models\Modelfile" (
    echo [错误] 未找到 ollama-models\Modelfile
    echo        请确保 ollama-models\ 目录下有 Modelfile
    pause
    exit /b 1
)

set "GGUF_COUNT=0"
for %%D in ("%SCRIPT_DIR%\ollama-models\*.gguf") do set /a GGUF_COUNT+=1

if !GGUF_COUNT! equ 0 (
    echo [提示] ollama-models\ 下未找到 .gguf 模型文件
    echo        模型权重文件需要手动下载并放入 ollama-models\ 目录
    echo.
    echo        按任意键继续（将只复制 Modelfile）...
    pause >nul
) else (
    echo [OK]   找到 !GGUF_COUNT! 个 .gguf 模型文件
)

echo [OK]   ollama-models\Modelfile 已就绪

REM =============================================================================
REM 步骤 5：创建离线包目录结构
REM =============================================================================
echo.
echo [构建] 正在创建离线包目录结构 ...

if exist "%BUNDLE_DIR%" (
    echo [清理] 删除旧的 offline_bundle\ ...
    rmdir /s /q "%BUNDLE_DIR%"
)

mkdir "%BUNDLE_DIR%"                     >nul 2>&1
mkdir "%BUNDLE_DIR%\tools"               >nul 2>&1
mkdir "%BUNDLE_DIR%\ollama-models"       >nul 2>&1
mkdir "%BUNDLE_DIR%\python-wheels"       >nul 2>&1
mkdir "%BUNDLE_DIR%\app"                 >nul 2>&1

echo [OK]   目录结构已创建

REM =============================================================================
REM 步骤 6：复制工具文件
REM =============================================================================
echo [构建] 正在复制工具文件 ...

REM 6a. 复制 Ollama zip
echo        复制 ollama-windows-amd64.zip ...
copy "%SCRIPT_DIR%\tools\ollama-windows-amd64.zip" "%BUNDLE_DIR%\tools\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 复制 ollama-windows-amd64.zip 失败
    pause
    exit /b 1
)
echo        [OK]   ollama-windows-amd64.zip

REM 6b. 复制 Python 安装程序（如果有）
if "!PYTHON_INSTALLER_MISSING!"=="0" (
    echo        复制 python-3.11.8-amd64.exe ...
    copy "%SCRIPT_DIR%\tools\python-3.11.8-amd64.exe" "%BUNDLE_DIR%\tools\" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 复制 python-3.11.8-amd64.exe 失败
        pause
        exit /b 1
    )
    echo        [OK]   python-3.11.8-amd64.exe
) else (
    echo        [跳过] python-3.11.8-amd64.exe（未提供，内网机器需自行安装 Python）
)

REM 6c. 处理 VC++ Redistributable
echo        处理 VC++ Redistributable ...

set "VCREDIST_COPIED=0"

REM 尝试 1：从 tools\ollama\ 复制
if exist "%SCRIPT_DIR%\tools\ollama\vc_redist.x64.exe" (
    copy "%SCRIPT_DIR%\tools\ollama\vc_redist.x64.exe" "%BUNDLE_DIR%\tools\" >nul 2>&1
    if !errorlevel! equ 0 (
        echo        [OK]   vc_redist.x64.exe（从 tools\ollama\ 复制）
        set "VCREDIST_COPIED=1"
    )
)

REM 尝试 2：从 ollama zip 中提取
if "!VCREDIST_COPIED!"=="0" (
    echo        正在从 ollama-windows-amd64.zip 中搜索 vc_redist...
    powershell -NoProfile -Command ^
        "$zip = [System.IO.Compression.ZipFile]::OpenRead('%SCRIPT_DIR%\tools\ollama-windows-amd64.zip');" ^
        "$entry = $zip.Entries | Where-Object { $_.Name -like 'vc_redist*.exe' } | Select-Object -First 1;" ^
        "if ($entry) {" ^
        "  [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, '%BUNDLE_DIR%\tools\vc_redist.x64.exe', $true);" ^
        "  Write-Host '        [OK]   vc_redist.x64.exe（从 zip 提取）';" ^
        "} else {" ^
        "  Write-Host '        [提示] zip 中未找到 vc_redist*.exe';" ^
        "}" ^
        "$zip.Dispose()"
    if exist "%BUNDLE_DIR%\tools\vc_redist.x64.exe" set "VCREDIST_COPIED=1"
)

REM 尝试 3：跳过
if "!VCREDIST_COPIED!"=="0" (
    echo        [跳过] VC++ Redistributable 未找到，内网机器可能需要手动安装
    echo              下载链接：https://aka.ms/vs/17/release/vc_redist.x64.exe
)

echo [OK]   工具文件复制完成

REM =============================================================================
REM 步骤 7：下载 wheel 包
REM =============================================================================
echo [构建] 正在下载 Python wheel 包 ...
echo        这可能需要几分钟，请耐心等待...

python -m pip download -r "%SCRIPT_DIR%\requirements.txt" ^
    --dest "%BUNDLE_DIR%\python-wheels" ^
    --platform win_amd64 ^
    --python-version 3.11 ^
    --only-binary=:all: >nul 2>&1

if %errorlevel% neq 0 (
    echo [错误] pip download 失败
    echo        请检查网络连接，确保可以访问 PyPI
    pause
    exit /b 1
)

REM 统计下载的 wheel 数量
set "WHEEL_COUNT=0"
for %%D in ("%BUNDLE_DIR%\python-wheels\*.whl") do set /a WHEEL_COUNT+=1
echo [OK]   已下载 !WHEEL_COUNT! 个 wheel 包

REM =============================================================================
REM 步骤 8：生成 requirements.lock.txt
REM =============================================================================
echo [构建] 正在生成 requirements.lock.txt ...

REM 8a. 生成完整 pip freeze
python -m pip freeze > "%TEMP%\_comac_freeze_full.txt" 2>&1
if %errorlevel% neq 0 (
    echo [错误] pip freeze 执行失败
    pause
    exit /b 1
)

REM 8b. 提取 requirements.txt 中的包名
> "%TEMP%\_comac_req_pkgs.txt" (
    for /f "usebackq tokens=1 delims=>=<~!; " %%D in ("%SCRIPT_DIR%\requirements.txt") do (
        set "PKG=%%D"
        if not "!PKG!"=="" if not "!PKG!"=="-r" echo !PKG!
    )
)

REM 8c. 使用 PowerShell 过滤：只保留 requirements.txt 中已有的包
powershell -NoProfile -Command ^
    "$reqPkgs = Get-Content '%TEMP%\_comac_req_pkgs.txt' | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ }; " ^
    "$freezeLines = Get-Content '%TEMP%\_comac_freeze_full.txt'; " ^
    "$filtered = $freezeLines | Where-Object { " ^
    "  $pkg = ($_ -split '==')[0].Trim().ToLower(); " ^
    "  $reqPkgs -contains $pkg " ^
    "}; " ^
    "$filtered | Out-File '%BUNDLE_DIR%\requirements.lock.txt' -Encoding UTF8"

if %errorlevel% neq 0 (
    echo [错误] requirements.lock.txt 生成失败
    pause
    exit /b 1
)

REM 清理临时文件
del "%TEMP%\_comac_freeze_full.txt" >nul 2>&1
del "%TEMP%\_comac_req_pkgs.txt"      >nul 2>&1

echo [OK]   requirements.lock.txt 已生成

REM =============================================================================
REM 步骤 9：复制应用代码
REM =============================================================================
echo [构建] 正在复制应用代码 ...

REM 9a. 复制 app.py（主入口）
copy "%SCRIPT_DIR%\app.py" "%BUNDLE_DIR%\app\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 复制 app.py 失败
    pause
    exit /b 1
)
echo        [OK]   app.py

REM 9b. 复制顶层 .py 文件
set "TOP_FILES=comac_assistant.py enhanced_assistant.py ollama_client.py ollama_rag.py config.py report_generator.py knowledge_graph.py knowledge_classifier.py excel_styler.py obsidian_sync.py task_manager.py verify_offline.py"
for %%D in (%TOP_FILES%) do (
    if exist "%SCRIPT_DIR%\%%D" (
        copy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\" >nul 2>&1
        echo        [OK]   %%D
    ) else (
        echo        [提示] %%D 不存在，已跳过
    )
)

REM 9c. 复制 Python 子目录
set "SUB_DIRS=parsers converters fillers batch audit presentations blocks"
for %%D in (%SUB_DIRS%) do (
    if exist "%SCRIPT_DIR%\%%D\" (
        robocopy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\%%D" *.py /s /njh /njs /ndl >nul 2>&1
        if !errorlevel! geq 8 (
            echo [错误] 复制 %%D\ 目录失败
            pause
            exit /b 1
        )
        echo        [OK]   %%D\
    ) else (
        echo        [提示] %%D\ 目录不存在，已跳过
    )
)

REM 9d. 复制静态资源和模板（不含 .py 但属于应用的一部分）
for %%D in (templates static) do (
    if exist "%SCRIPT_DIR%\%%D\" (
        robocopy "%SCRIPT_DIR%\%%D" "%BUNDLE_DIR%\app\%%D" /s /njh /njs /ndl >nul 2>&1
        if !errorlevel! geq 8 (
            echo [错误] 复制 %%D\ 目录失败
            pause
            exit /b 1
        )
        echo        [OK]   %%D\
    ) else (
        echo        [提示] %%D\ 目录不存在，已跳过
    )
)

echo [OK]   应用代码复制完成

REM =============================================================================
REM 步骤 10：复制 ollama-models/
REM =============================================================================
echo [构建] 正在复制 ollama-models\ ...

robocopy "%SCRIPT_DIR%\ollama-models" "%BUNDLE_DIR%\ollama-models" /s /njh /njs /ndl >nul 2>&1
if %errorlevel% geq 8 (
    echo [错误] 复制 ollama-models\ 失败
    pause
    exit /b 1
)

echo [OK]   ollama-models\ 复制完成

REM =============================================================================
REM 步骤 11：生成 manifest.sha256
REM =============================================================================
echo [构建] 正在生成 manifest.sha256 ...

powershell -NoProfile -Command ^
    "$bundleDir = '%BUNDLE_DIR%'; " ^
    "Push-Location $bundleDir; " ^
    "Get-ChildItem -Recurse -File | ForEach-Object { " ^
    "    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash; " ^
    "    $relPath = $_.FullName.Substring((Get-Location).Path.Length + 1) -replace '\\', '/'; " ^
    "    \"$hash  $relPath\" " ^
    "} | Out-File 'manifest.sha256' -Encoding UTF8; " ^
    "Pop-Location"

if %errorlevel% neq 0 (
    echo [错误] manifest.sha256 生成失败
    pause
    exit /b 1
)

echo [OK]   manifest.sha256 已生成

REM =============================================================================
REM 步骤 12：统计与完成提示
REM =============================================================================
echo.
echo [统计] 正在计算离线包大小 ...

for /f "usebackq tokens=1,2 delims= " %%D in (`powershell -NoProfile -Command ^
    "$size = (Get-ChildItem -Recurse -File '%BUNDLE_DIR%' | Measure-Object -Property Length -Sum).Sum; " ^
    "if ($size -ge 1GB) { '{0:N2} GB' -f ($size/1GB) } " ^
    "elseif ($size -ge 1MB) { '{0:N2} MB' -f ($size/1MB) } " ^
    "else { '{0:N2} KB' -f ($size/1KB) }"`) do set "BUNDLE_SIZE=%%D %%E"

echo.
echo ============================================================
echo   构建完成！
echo ============================================================
echo.
echo   离线包路径: %BUNDLE_DIR%
echo   离线包大小: !BUNDLE_SIZE!
echo.
echo   包含内容:
echo     - tools\          : Ollama + Python 安装程序 + VC++ Redist
echo     - ollama-models\  : 模型文件（GGUF + Modelfile）
echo     - python-wheels\  : Python 依赖包（!WHEEL_COUNT! 个 wheel）
echo     - app\            : 应用程序代码
echo     - requirements.lock.txt : 锁定的依赖版本
echo     - manifest.sha256       : 所有文件 SHA-256 校验
echo.
echo   下一步:
echo     将 offline_bundle\ 整个目录复制到内网 Windows 10 机器，
echo     然后运行 install-offline.bat（将在后续版本提供）。
echo.
echo     内网机器首次安装预计 10-15 分钟。
echo.
echo ============================================================

pause
exit /b 0
