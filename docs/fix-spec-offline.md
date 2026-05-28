# COMAC-LocalAI-Windows 离线部署闭环 — 修复规格文档

> **版本**: 1.0  
> **日期**: 2025-07-03  
> **适用范围**: `COMAC-LocalAI-Windows` 项目（空气隔离内网 Windows 10 离线部署闭环）  
> **优先级**: 全部 P0  
> **原始需求来源**: 用户审查报告 + 8 项最小修补清单 + 附加审查发现  

---

## 1. 概述

本文档以结构化 JSON Schema 风格描述每个修复项的**目标、涉及文件、当前状态、期望状态、验收标准**，并标注依赖关系与可并行度。

### 1.1 修复项总览

| ID | 标题 | 类别 | 依赖 |
|----|------|------|------|
| F01 | 新增 `install-offline.bat` 安装闭环脚本 | 离线部署 | F03, F06 |
| F02 | `build-offline-package.bat` 复制脚本/文档到 bundle 根目录 | 离线部署 | F01 |
| F03 | `install-offline.bat` 负责创建 `.venv` 并离线安装依赖 | 离线部署 | — |
| F04 | 修复 `requirements.lock.txt` 生成方式（临时 venv 冻结） | 构建工具 | — |
| F05 | 全仓删除 Embeddable Python 相关说明 | 文档一致性 | — |
| F06 | 全仓统一模型文件名为 `qwen2.5-7b-instruct-q4_k_m.gguf` | 文档一致性 | — |
| F07 | RAG 文档支持与索引逻辑对齐 | 功能一致性 | — |
| F08 | `opencode.bat` 增加 `OLLAMA_MODELS` + 独立端口 | 运行时 | — |
| F09 | 修复 `ExcelParser` 对 `.csv` 文件的解析错误 | Bug修复 | — |
| F10 | 修复 `verify_offline.py` 过时 API 和 Linux 风格消息 | 验证工具 | — |
| F11 | README 合规性修复（删除"内部使用，请勿外传"） | 合规 | — |

### 1.2 依赖关系图

```
F03 ──→ F01 ──→ F02
                  
F04 (独立)
F05 (独立)
F06 (独立)
F07 (独立)
F08 (独立)
F09 (独立)
F10 (独立)
F11 (独立)
```

除 F01→F02→F03 构成串行链外，其余 8 项均可并行实施。

---

## 2. 修复规格

---

### F01: 新增 `install-offline.bat` 安装闭环脚本

```json
{
  "id": "F01",
  "priority": "P0",
  "category": "offline_deployment",
  "depends_on": ["F03", "F06"],
  "blocked_by": [],
  "title": "新增 install-offline.bat — 离线包一键安装脚本"
}
```

#### 目标

为 `offline_bundle/` 提供完整的离线安装脚本，使内网 Windows 10 机器在完全断网条件下可通过双击完成从零到运行的完整闭环。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `install-offline.bat`（新文件，项目根目录） | **新增** |
| `build-offline-package.bat` | **修改**（见 F02） |

#### 当前状态

- `build-offline-package.bat` 第 395 行注释："然后运行 install-offline.bat（将在后续版本提供）" — 该脚本**不存在**
- `setup.bat` 要求 `.venv` 已预建（由 `pre-deploy.bat` 在有网机器上完成），不适用于离线包场景
- `start.bat` 同样要求 `.venv` 已存在
- 离线包 `offline_bundle/` 包含所有原材料（Python 安装程序、Ollama zip、wheel 包、GGUF 模型、应用代码），但缺少将它们串联起来的安装脚本

#### 期望状态

`install-offline.bat` 应执行以下 7 个步骤：

```
[1/7] 检测/安装 Python 3.11
      - 检查系统 PATH 中是否有 Python 3.11+
      - 若无，使用 tools\python-3.11.8-amd64.exe 静默安装到 %LOCALAPPDATA%\Programs\Python\Python311
      - 将安装路径加入当前会话 PATH

[2/7] 创建 .venv 虚拟环境
      - 使用检测到的 Python 执行: python -m venv .venv
      - 无需预存 .venv（区别于 setup.bat）

[3/7] 离线安装 Python 依赖
      - 使用 .venv\Scripts\pip install --no-index --find-links="python-wheels" -r requirements.lock.txt
      - 验证核心依赖可导入

[4/7] 解压内置 Ollama
      - 从 tools\ollama-windows-amd64.zip 解压到 tools\ollama\
      - 安装 VC++ Redistributable（如存在）

[5/7] 创建 Ollama 模型
      - 启动 Ollama 服务
      - 执行 ollama create qwen:7b-q4_K_M -f ollama-models\Modelfile

[6/7] 生成 .env 配置文件
      - 随机 16 位密码
      - 写入 GRADIO_USER / GRADIO_PASS / COMAC_MODEL / COMAC_EMBED_MODEL / OLLAMA_HOST

[7/7] 启动服务
      - 设置 OLLAMA_MODELS 环境变量指向项目内 ollama-cache/
      - 启动 Ollama serve（后台）
      - 启动 Gradio（前台，start.bat 逻辑）
```

#### 验收标准

| # | 条件 |
|---|------|
| AC-F01-1 | 在干净 Windows 10（无 Python、无 Ollama）上，将 `offline_bundle/` 复制到本地，双击 `install-offline.bat`，15 分钟内完成全部安装 |
| AC-F01-2 | 脚本执行过程中任何步骤失败应明确报错并暂停，不静默跳过关键步骤 |
| AC-F01-3 | 完成后浏览器自动打开 `http://localhost:7860`，使用生成的密码可登录 |
| AC-F01-4 | 脚本支持"断点续传"语义——若某步骤已完成（如 .venv 已存在且依赖完整），应跳过而非重复执行 |
| AC-F01-5 | 脚本头部包含清晰的注释说明（中文），包括用途、前置条件、预计耗时 |

---

### F02: `build-offline-package.bat` 复制脚本/文档到 bundle 根目录

```json
{
  "id": "F02",
  "priority": "P0",
  "category": "offline_deployment",
  "depends_on": ["F01"],
  "blocked_by": [],
  "title": "build-offline-package.bat 复制 install-offline.bat / start.bat / opencode.bat / README / manifest 到 offline_bundle 根目录"
}
```

#### 目标

确保离线包根目录包含内网用户所需的所有入口脚本和文档，使 `offline_bundle/` 成为自描述的自解压式部署包。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `build-offline-package.bat` | **修改**（新增步骤 9e: 复制脚本/文档） |

#### 当前状态

`build-offline-package.bat` 当前复制内容：

| 步骤 | 内容 | 目标位置 |
|------|------|----------|
| 6a-6c | 工具文件（Ollama zip, Python installer, VC++） | `offline_bundle\tools\` |
| 7 | Python wheel 包 | `offline_bundle\python-wheels\` |
| 8 | requirements.lock.txt | `offline_bundle\` |
| 9a-9d | 应用代码 (.py, 子目录) | `offline_bundle\app\` |
| 10 | ollama-models | `offline_bundle\ollama-models\` |
| 11 | manifest.sha256 | `offline_bundle\` |

**缺失**：`install-offline.bat`、`start.bat`、`opencode.bat`、`README.md`、`DEPLOY.md` 未复制到 `offline_bundle/` 根目录。

#### 期望状态

在步骤 9（复制应用代码）之后、步骤 10（复制 ollama-models）之前，新增步骤 9e：

```bat
REM 9e. 复制部署脚本和文档到 bundle 根目录
copy "%SCRIPT_DIR%\install-offline.bat"  "%BUNDLE_DIR%\"  >nul
copy "%SCRIPT_DIR%\start.bat"            "%BUNDLE_DIR%\"  >nul
copy "%SCRIPT_DIR%\opencode.bat"         "%BUNDLE_DIR%\"  >nul
copy "%SCRIPT_DIR%\README.md"            "%BUNDLE_DIR%\"  >nul
copy "%SCRIPT_DIR%\DEPLOY.md"            "%BUNDLE_DIR%\"  >nul
```

同时更新步骤 12（统计与完成提示）的描述，反映新增的根目录文件。

#### 验收标准

| # | 条件 |
|---|------|
| AC-F02-1 | 构建后 `offline_bundle\` 根目录包含 `install-offline.bat`、`start.bat`、`opencode.bat`、`README.md`、`DEPLOY.md` |
| AC-F02-2 | 构建后 `offline_bundle\manifest.sha256` 包含上述文件的 SHA-256 记录 |
| AC-F02-3 | 构建完成提示输出正确列出所有根目录文件 |

---

### F03: `install-offline.bat` 负责创建 `.venv` 并离线安装

```json
{
  "id": "F03",
  "priority": "P0",
  "category": "offline_deployment",
  "depends_on": [],
  "blocked_by": [],
  "title": "install-offline.bat 负责创建 .venv 并从 python-wheels 离线安装，不要求 .venv 预存在"
}
```

#### 目标

打破当前 `.venv` 必须预存在的强约束——内网机器应能从零创建虚拟环境。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `install-offline.bat` | **新增**（见 F01） |

#### 当前状态

现有离线安装路径要求：
- `setup.bat` 第 95 行：若 `.venv\Scripts\python.exe` 不存在，直接报错退出，提示"请先在有网机器运行 pre-deploy.bat"
- `start.bat` 第 28 行：同样检查 `.venv`，不存在则报错退出
- 项目文档（README、DEPLOY.md）描述的流程均假设 `.venv` 已由有网机器预建

#### 期望状态

`install-offline.bat` 中的步骤 [2/7] 和 [3/7] 实现：
1. 检测到 Python 3.11+ 后，执行 `python -m venv .venv` 创建虚拟环境
2. 使用 `--no-index --find-links="python-wheels"` 从本地 wheel 包离线安装所有依赖
3. 验证核心依赖可导入后继续
4. **不依赖**预存的 `.venv` 或互联网连接

#### 注意事项

- `pip install --no-index --find-links` 要求 `python-wheels/` 中包含**所有传递依赖**的 wheel 包。`build-offline-package.bat` 第 209 行的 `pip download` 命令已使用 `--platform win_amd64 --python-version 3.11 --only-binary=:all:`，理论上覆盖完整依赖树，但需验证。
- 如果某些包有平台特定的 C 扩展（如 `pymupdf`），需确保离线包中的 wheel 与内网机器的 Windows 版本和架构兼容。

#### 验收标准

| # | 条件 |
|---|------|
| AC-F03-1 | 删除 `.venv` 目录后，运行 `install-offline.bat`，能成功创建 `.venv` 并安装所有依赖 |
| AC-F03-2 | `install-offline.bat` 不调用任何网络资源（pip install 使用 `--no-index`） |
| AC-F03-3 | 安装完成后，`.venv\Scripts\python.exe -c "import gradio; import ollama; import pandas; print('OK')"` 输出 OK |

---

### F04: 修复 `requirements.lock.txt` 生成方式

```json
{
  "id": "F04",
  "priority": "P0",
  "category": "build_tooling",
  "depends_on": [],
  "blocked_by": [],
  "title": "用临时 venv 冻结真实依赖替代当前 pip freeze 过滤方案"
}
```

#### 目标

使 `requirements.lock.txt` 精确反映 `requirements.txt` 在干净环境中的解析结果，而非宿主机的全局 pip 状态。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `build-offline-package.bat`（步骤 8） | **重写** |

#### 当前状态

`build-offline-package.bat` 第 229-268 行（步骤 8）的当前逻辑：

```bat
REM 8a: pip freeze 全局环境 → 临时文件
REM 8b: 手动解析 requirements.txt 提取包名
REM 8c: PowerShell 过滤 freeze 输出，只保留 requirements.txt 中的包
```

**问题**：
1. `pip freeze` 捕获的是**宿主机全局环境**的所有包，可能包含与项目无关的依赖
2. 手动解析 `requirements.txt` 提取包名容易出错（`>` `<` `~` `!` `;` 等操作符边界情况）
3. 过滤逻辑粗糙——只比较包名前缀，如 `gradio` 和 `gradio-client` 可能混淆

#### 期望状态

替换为以下逻辑：

```bat
REM 步骤 8: 在临时 venv 中安装依赖并冻结
echo [构建] 正在生成 requirements.lock.txt（临时 venv）...

REM 8a: 创建临时 venv
python -m venv "%TEMP%\_comac_lock_venv" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 临时 venv 创建失败
    pause
    exit /b 1
)

REM 8b: 在临时 venv 中安装 requirements.txt
"%TEMP%\_comac_lock_venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt" --quiet >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 临时 venv 依赖安装失败
    rmdir /s /q "%TEMP%\_comac_lock_venv" >nul 2>&1
    pause
    exit /b 1
)

REM 8c: 从临时 venv 冻结 → requirements.lock.txt
"%TEMP%\_comac_lock_venv\Scripts\pip.exe" freeze > "%BUNDLE_DIR%\requirements.lock.txt" 2>&1
if %errorlevel% neq 0 (
    echo [错误] pip freeze 失败
    rmdir /s /q "%TEMP%\_comac_lock_venv" >nul 2>&1
    pause
    exit /b 1
)

REM 8d: 清理临时 venv
rmdir /s /q "%TEMP%\_comac_lock_venv" >nul 2>&1

echo [OK]   requirements.lock.txt 已生成
```

#### 验收标准

| # | 条件 |
|---|------|
| AC-F04-1 | `requirements.lock.txt` 仅包含 `requirements.txt` 中列出的包及其传递依赖，不含宿主机其他项目依赖 |
| AC-F04-2 | `requirements.lock.txt` 中每个包的版本号精确（`==X.Y.Z`），可用于 `pip install --no-index` |
| AC-F04-3 | 临时 venv 在步骤完成后被完全清理，无残留 |
| AC-F04-4 | 生成过程在网络可用环境中运行（因为需要 pip install 下载），这符合 `build-offline-package.bat` 的设计前提 |

---

### F05: 全仓删除 Embeddable Python 相关说明

```json
{
  "id": "F05",
  "priority": "P0",
  "category": "documentation_consistency",
  "depends_on": [],
  "blocked_by": [],
  "title": "全仓统一 Python 安装包路线 — 删除所有 Embeddable Python 引用"
}
```

#### 目标

项目统一使用完整的 Python 安装程序（`python-3.11.8-amd64.exe`），删除所有 Python Embeddable（`python-*-embed-amd64.zip`）的引用，避免用户混淆和部署失败。

#### 涉及文件

| 文件 | 操作 | 具体位置 |
|------|------|----------|
| `下载指南.md` | **修改** | 第 31-42 行（第三步：下载 Python Embeddable）、第 74 行（解压 Python Embeddable） |
| `下载完整包.bat` | **修改** | 第 63-83 行（下载 Python Embeddable 步骤 [3/4]） |
| `setup.bat` | **修改** | 第 21 行注释（"必须是系统 Python，Embeddable 不可用"） |

#### 当前状态

**`下载指南.md`** 第 31-42 行：
```markdown
### 第三步：下载 Python Embeddable（约 25MB）

下载地址：https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip
...
    └── python-3.11.8-embed-amd64.zip   ← 放入此文件
```

第 74 行：
```
- 解压 Python Embeddable 到 `tools/python/`
```

**`下载完整包.bat`** 第 63-83 行：
```bat
:: 下载 Python Embeddable
echo [3/4] 下载 Python Embeddable（约 25MB）...
echo 下载: python-3.11.8-embed-amd64.zip
```

**`setup.bat`** 第 21 行：
```bat
REM  步骤 1: 检查 Python 运行时（必须是系统 Python，Embeddable 不可用）
```

#### 期望状态

| 文件 | 变更 |
|------|------|
| `下载指南.md` | 第三步替换为"下载 Python 安装程序"，指向 `python-3.11.8-amd64.exe`（约 25MB），放置到 `tools/`；删除所有 embed 相关描述 |
| `下载完整包.bat` | 步骤 [3/4] 替换为下载 `python-3.11.8-amd64.exe`（而非 embed 版本） |
| `setup.bat` | 第 21 行注释去掉 "Embeddable 不可用"，改为 "必须是系统 Python 3.11+（完整安装版）" |

#### 验收标准

| # | 条件 |
|---|------|
| AC-F05-1 | `rg -i embeddable` 在项目源码（排除 `.venv/` 和 `tools/python/`）中无匹配结果 |
| AC-F05-2 | `下载指南.md` 中 Python 安装指引指向 `python-3.11.8-amd64.exe` 而非 embed 版本 |
| AC-F05-3 | `下载完整包.bat` 中下载的是完整安装程序而非 embed 版本 |
| AC-F05-4 | `setup.bat` 注释不再提及 Embeddable |

---

### F06: 全仓统一模型文件名

```json
{
  "id": "F06",
  "priority": "P0",
  "category": "documentation_consistency",
  "depends_on": [],
  "blocked_by": [],
  "title": "全仓统一模型文件名为 qwen2.5-7b-instruct-q4_k_m.gguf"
}
```

#### 目标

消除仓库中 GGUF 模型文件名的变体（缺 `-instruct-` 后缀），统一使用 `qwen2.5-7b-instruct-q4_k_m.gguf`。

#### 涉及文件

| 文件 | 操作 | 具体位置 |
|------|------|----------|
| `下载指南.md` | **修改** | 第 53 行 `qwen2.5-7b-q4_K_M` → `qwen2.5-7b-instruct-q4_k_m`；第 55 行 `qwen2.5-7b-q4_k_m.gguf` → `qwen2.5-7b-instruct-q4_k_m.gguf`；第 63 行同上 |
| `下载完整包.bat` | **修改** | 第 89 行 `qwen2.5-7b-q4_k_m.gguf` → `qwen2.5-7b-instruct-q4_k_m.gguf` |

#### 当前状态

**一致性审计结果**：

| 文件 | 当前值 | 是否正确 |
|------|--------|----------|
| `ollama-models/Modelfile` 第 16 行 | `FROM ./qwen2.5-7b-instruct-q4_k_m.gguf` | ✅ |
| `download-model.bat` 多处 | `qwen2.5-7b-instruct-q4_k_m.gguf` | ✅ |
| `README.md` 第 51/56 行 | `qwen2.5-7b-instruct-q4_k_m.gguf` | ✅ |
| `DEPLOY.md` 第 124 行 | `qwen2.5-7b-instruct-q4_k_m.gguf` | ✅ |
| `setup.bat` 第 224 行 | `qwen2.5-7b-instruct-q4_k_m.gguf` | ✅ |
| **`下载指南.md`** 第 53 行 | `qwen2.5-7b-q4_K_M` | ❌ 缺 `-instruct-` |
| **`下载指南.md`** 第 55/63 行 | `qwen2.5-7b-q4_k_m.gguf` | ❌ 缺 `-instruct-` |
| **`下载完整包.bat`** 第 89 行 | `qwen2.5-7b-q4_k_m.gguf` | ❌ 缺 `-instruct-` |

#### 期望状态

上述 ❌ 项全部修正为 `qwen2.5-7b-instruct-q4_k_m.gguf`。

注意区分两种命名：
- **GGUF 文件名**（磁盘上的文件）：`qwen2.5-7b-instruct-q4_k_m.gguf`（小写，HuggingFace 惯例）
- **Ollama 模型标签**（`ollama list` 显示的名称）：`qwen:7b-q4_K_M`（Ollama 命名惯例）——此标签**无需修改**，已全局一致

#### 验收标准

| # | 条件 |
|---|------|
| AC-F06-1 | `rg -i "qwen.*q4_k_m" --glob="*.{bat,md,txt,py,json}"` 在项目源码中（排除 `.venv/` 和 `tools/python/`）所有 GGUF 文件名引用均为 `qwen2.5-7b-instruct-q4_k_m.gguf` |
| AC-F06-2 | `ollama-models/Modelfile` 中的 `FROM` 行仍为 `./qwen2.5-7b-instruct-q4_k_m.gguf`（不变） |

---

### F07: RAG 文档支持与实际索引逻辑对齐

```json
{
  "id": "F07",
  "priority": "P0",
  "category": "functional_consistency",
  "depends_on": [],
  "blocked_by": [],
  "title": "RAG 索引逻辑与文档支持声明对齐 — 方案A：仅支持 .md/.txt/.pdf"
}
```

#### 目标

消除 `app.py` 声明的支持格式列表与 `ollama_rag.py` 实际索引能力之间的不一致。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `ollama_rag.py` | **修改**（若选择扩展索引能力）或在注释中明确范围 |
| `app.py` | **审查**（确认 SUPPORTED_FORMATS 声明与 RAG 索引逻辑一致） |

#### 当前状态

**`ollama_rag.py`** `index_file()` 方法（第 242-268 行）仅支持三种格式：

```python
if path.suffix == '.md':
    content = path.read_text(encoding='utf-8')
elif path.suffix == '.txt':
    content = path.read_text(encoding='utf-8')
elif path.suffix == '.pdf':
    # pdfplumber 解析
else:
    # fallback: read_text, 失败则返回 0
```

`index_documents()` 方法（第 330 行）的文件匹配模式：
```python
patterns = ['*.md', '*.txt', '*.pdf']
```

**`app.py`** 第 75 行 `SUPPORTED_FORMATS` 声明：
```python
SUPPORTED_FORMATS = [".docx", ".pdf", ".pptx", ".xlsx", ".txt", ".md", ".csv"]
```

**不一致点**：`SUPPORTED_FORMATS` 声称支持 7 种格式，但 RAG 索引实际只能处理 3 种（.md/.txt/.pdf）。

> **备注**：之前 `system_design.md`（P1-9 修复）已将 `.doc`/`.ppt`/`.xls`移除并增加了 `.md`/`.csv`，但 `ollama_rag.py` 的 `index_file()` 不支持 `.docx`/`.pptx`/`.xlsx`/`.csv`。

#### 期望状态（方案 A：收缩 RAG 声明）

保持 `ollama_rag.py` 的索引能力不变（.md/.txt/.pdf），在 RAG Tab 的 Markdown 说明中明确仅支持这三种格式，并对非 RAG 功能（文档摘要/转换/批量处理）单独使用 `SUPPORTED_FORMATS`。

具体修改：
1. `app.py` RAG Tab Markdown（约第 863 行）明确写：**RAG 索引支持**: `.md`, `.txt`, `.pdf`
2. `SUPPORTED_FORMATS` 保持 7 种格式不变（仅用于文件上传白名单，非 RAG 专属）
3. 在 `index_docs()` 函数（F01 关联功能）中添加格式过滤，跳过不支持的格式并打印提示

#### 备选方案（方案 B：扩展索引能力）

通过 `ParserFactory` 使 `ollama_rag.py` 支持 `.docx/.pptx/.xlsx/.csv`：
```python
# ollama_rag.py index_file() 中增加：
else:
    try:
        from parsers.parser_factory import ParserFactory
        doc = ParserFactory.parse(file_path)
        content = doc.content
    except Exception as e:
        print(f"[RAG] ...")
        return 0
```

> **推荐方案 A**——理由：RAG 向量索引对非纯文本文档（如 xlsx 的表格数据）效果有限，且当前 ParserFactory 中 `.csv → ExcelParser` 存在 bug（见 F09），不应在此阶段扩大索引范围。先收缩声明、收敛闭环，后续版本再扩展。

#### 验收标准

| # | 条件 |
|---|------|
| AC-F07-1 | RAG Tab UI 中的格式说明与实际 `ollama_rag.py` 的 `index_file()` 支持的格式**完全一致** |
| AC-F07-2 | 若用户上传非 RAG 支持的格式到 RAG Tab，系统给出清晰提示而非静默失败 |
| AC-F07-3 | `SUPPORTED_FORMATS`（文件上传白名单）保持 7 种格式不变，不影响非 RAG 功能 |

---

### F08: `opencode.bat` 增加 `OLLAMA_MODELS` + 独立端口

```json
{
  "id": "F08",
  "priority": "P0",
  "category": "runtime",
  "depends_on": [],
  "blocked_by": [],
  "title": "opencode.bat 设置 OLLAMA_MODELS 并考虑 Ollama 独立端口"
}
```

#### 目标

使 `opencode.bat`（终端 TUI 入口）与 `start.bat`（Gradio Web UI 入口）保持一致的 Ollama 环境变量设置，避免复用系统级 Ollama 服务带来的模型缓存冲突。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `opencode.bat` | **修改** |

#### 当前状态

**`start.bat`**（第 54-56 行）已正确设置：
```bat
set "OLLAMA_HOST=localhost:11434"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"
set "OLLAMA_BIN=tools\ollama\ollama.exe"
```

**`opencode.bat`** 的当前状态：
```bat
set "OLLAMA_HOST=localhost:11434"
REM 没有 OLLAMA_MODELS 设置
REM 没有 OLLAMA_BIN 路径设置
```

**问题**：
1. 如果用户系统中已有 Ollama 服务运行在 11434 端口，`opencode.bat` 会直接使用它，但其模型缓存（`%APPDATA%\ollama\models`）可能不包含 `qwen:7b-q4_K_M`
2. 不设置 `OLLAMA_MODELS` 意味着 TUI 对话依赖系统 Ollama 的模型缓存，与项目自带的 `ollama-cache/` 脱节
3. 不设置 `OLLAMA_BIN` 意味着如果 PATH 中没有 ollama，TUI 无法自动启动项目内置的 Ollama

#### 期望状态

`opencode.bat` 修改为：

```bat
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "OLLAMA_HOST=localhost:11534"
set "OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache"

REM 优先使用内置 Ollama，否则尝试系统 PATH
if exist "tools\ollama\ollama.exe" (
    set "OLLAMA_BIN=tools\ollama\ollama.exe"
) else (
    set "OLLAMA_BIN=ollama"
)
```

**关于独立端口 11534**：将项目内置 Ollama 服务绑定到非标准端口（如 11534），可避免与系统已有 Ollama 服务（11434）冲突。但需同步修改：
- `ollama_rag.py` 中 `OllamaClient` 的连接地址
- `config.py` 中 `OLLAMA_HOST` 默认值
- `start.bat` 中的 `OLLAMA_HOST`

> **建议**：本轮 F08 先行在 `opencode.bat` 中设置 `OLLAMA_MODELS` 和 `OLLAMA_BIN`。端口变更影响面广（需修改 4+ 文件），作为独立变更在下个迭代处理，此处仅添加代码注释标记 TODO。

#### 验收标准

| # | 条件 |
|---|------|
| AC-F08-1 | `opencode.bat` 设置 `OLLAMA_MODELS=%SCRIPT_DIR%ollama-cache`，与 `start.bat` 一致 |
| AC-F08-2 | `opencode.bat` 设置 `OLLAMA_BIN` 优先指向项目内置 Ollama |
| AC-F08-3 | 在未安装系统 Ollama 的机器上，双击 `opencode.bat` 能自动启动项目内置 Ollama 并连接 |
| AC-F08-4 | 代码注释中包含 TODO 标记，注明独立端口方案待后续实施 |

---

### F09: 修复 `ExcelParser` 对 `.csv` 文件的解析错误

```json
{
  "id": "F09",
  "priority": "P0",
  "category": "bug_fix",
  "depends_on": [],
  "blocked_by": [],
  "title": "ParserFactory 将 .csv 映射到 ExcelParser，但 ExcelParser.parse() 用 pd.ExcelFile() 无法处理 CSV"
}
```

#### 目标

修复 `ParserFactory` 中 `.csv → ExcelParser` 映射导致的运行时错误。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `parsers/excel_parser.py` | **修改** |
| `parsers/parser_factory.py` | **审查**（确认映射正确） |

#### 当前状态

**`parsers/parser_factory.py`** 第 15 行：
```python
".csv": ExcelParser(),
```

**`parsers/excel_parser.py`** 第 7 行：
```python
def parse(self, file_path: str) -> Document:
    excel_file = pd.ExcelFile(file_path)  # ❌ pd.ExcelFile() 不支持 .csv
    sheets = {}
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        sheets[sheet_name] = df.to_string()
```

**根因**：`pd.ExcelFile()` 仅支持 `.xls` / `.xlsx` / `.xlsm` / `.xlsb` / `.odf` / `.ods` / `.odt` 格式。对 `.csv` 文件调用会抛出 `ValueError`。

#### 期望状态

在 `ExcelParser.parse()` 中增加格式检测分支：

```python
def parse(self, file_path: str) -> Document:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == '.csv':
        df = pd.read_csv(file_path)
        content = df.to_string()
        return Document(
            content=content,
            metadata={"sheets": ["Sheet1"], "sheet_count": 1},
            format="csv",
            pages=[content]
        )

    excel_file = pd.ExcelFile(file_path)
    sheets = {}
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        sheets[sheet_name] = df.to_string()

    all_content = "\n\n".join(
        f"[{name}]\n{content}" for name, content in sheets.items()
    )

    return Document(
        content=all_content,
        metadata={
            "sheets": excel_file.sheet_names,
            "sheet_count": len(excel_file.sheet_names)
        },
        format="xlsx",
        pages=[all_content]
    )
```

#### 验收标准

| # | 条件 |
|---|------|
| AC-F09-1 | `ExcelParser().parse("test.csv")` 正常返回 `Document`，不抛出 `ValueError` |
| AC-F09-2 | `ExcelParser().parse("test.xlsx")` 行为不变，正常解析多 sheet |
| AC-F09-3 | `ExcelParser().extract_text("test.csv")` 返回正确的 CSV 文本内容 |
| AC-F09-4 | `ParserFactory.parse("any.csv")` 正确路由到 ExcelParser 且解析成功 |

---

### F10: 修复 `verify_offline.py` 过时 API 和 Linux 风格消息

```json
{
  "id": "F10",
  "priority": "P0",
  "category": "bug_fix",
  "depends_on": [],
  "blocked_by": [],
  "title": "verify_offline.py 使用过时 ollama.list() dict 处理逻辑和 Linux 风格错误消息"
}
```

#### 目标

修复验证脚本中的平台不适配问题和过时 API 调用，使其在 Windows 环境下正确运行并输出可操作的错误提示。

#### 涉及文件

| 文件 | 操作 |
|------|------|
| `verify_offline.py` | **修改**（多处） |

#### 当前状态

**问题 1**：第 33 行 — Linux 风格错误消息：
```python
print("   请运行: ollama serve")
```
Windows 上应为 `tools\ollama\ollama.exe serve` 或 `start.bat`

**问题 2**：第 152-153 行 — OCR 工具检查使用 Linux 路径：
```python
ocr_dir = Path.home() / "ollama-doc-models"
ocrtext = ocr_dir / "ocrtext"
pdfocr = ocr_dir / "pdfocr.sh"
```
`pdfocr.sh` 是 Linux shell 脚本，在 Windows 上不可执行。

**问题 3**：第 234 行 — Linux 风格故障排查建议：
```python
print("   - 模型未加载: cd ~/ollama-doc-models && bash setup.sh")
```
Windows 上 `~` 和 `bash` 均不适用。

**问题 4**：第 19 行 — `ollama.list()` 返回值处理可能过时：
```python
models_data = response.get('models', []) or response.get('model_list', [])
```
新版本 `ollama` Python SDK 的 `list()` 返回格式可能已变更（返回 Model 对象列表而非 dict）。

#### 期望状态

| 问题 | 修复方案 |
|------|----------|
| 问题 1 (L33) | 改为 `print("   请运行: tools\\ollama\\ollama.exe serve  或双击 start.bat")` |
| 问题 2 (L152-153) | ① `pdfocr.sh` → `pdfocr.bat`（或删除此检查，因为 Windows 上 OCR 工具链不同）；② 路径改为 Windows 风格 `%USERPROFILE%\\ollama-doc-models` |
| 问题 3 (L234) | 改为 `print("   - 模型未加载: 将 GGUF 文件放入 ollama-models\\ 后运行 setup.bat")` |
| 问题 4 (L19-25) | 增加对新版 ollama SDK 的适配——先尝试 `response.models`（对象列表），回退到 dict 解析 |

#### 验收标准

| # | 条件 |
|---|------|
| AC-F10-1 | `verify_offline.py` 在 Windows 10 上运行时，所有错误提示均为 Windows 风格（反斜杠路径、`.bat`/`.exe` 命令） |
| AC-F10-2 | `check_ollama()` 函数兼容当前 `ollama` Python SDK 版本的 `list()` 返回值格式 |
| AC-F10-3 | OCR 工具检查不引用 `.sh` 脚本路径 |
| AC-F10-4 | 故障排查建议中不出现 `~`、`bash`、`cd` 等 Linux 命令 |

---

### F11: README 合规性修复

```json
{
  "id": "F11",
  "priority": "P0",
  "category": "compliance",
  "depends_on": [],
  "blocked_by": [],
  "title": "仓库公开但 README 标注"内部使用，请勿外传"的合规风险修复"
}
```

#### 目标

消除公开仓库中的矛盾声明——GitHub 仓库公开但 README 末尾写"内部使用，请勿外传"。

#### 涉及文件

| 文件 | 操作 | 具体位置 |
|------|------|----------|
| `README.md` | **修改** | 第 138 行 |
| `app.py` | **修改** | 第 1202 行（Gradio footer） |
| `training-materials/操作手册.md` | **修改** | 第 525 行 |
| `training-materials/培训课件完整版.md` | **修改** | 第 766 行 |

#### 当前状态

| 文件 | 当前文本 |
|------|----------|
| `README.md` L138 | `内部使用，请勿外传。` |
| `app.py` L1202 | `*COMAC AI 文档处理平台 v2.0 \| 中国商飞内部使用 \| 请勿外传*` |
| `training-materials/操作手册.md` L525 | `**内部资料，请勿外传**` |
| `training-materials/培训课件完整版.md` L766 | `*内部资料，请勿外传*` |

#### 期望状态

| 文件 | 替换文本 |
|------|----------|
| `README.md` L138 | 替换为适当的开源许可证声明（如 `MIT License` 或 `Apache 2.0`），或改为 `COMAC 离线 AI 文档处理平台`（中性描述） |
| `app.py` L1202 | `*COMAC AI 文档处理平台 v2.0*` — 删除"中国商飞内部使用 \| 请勿外传" |
| `training-materials/` | 若培训材料为外部发布，删除"内部资料，请勿外传"；若确为内部使用，将文件从公开仓库移除或加入 `.gitignore` |

> **注意**：`training-materials/` 目录下的文件内容涉及大量 COMAC 内部流程描述。建议与项目负责人确认这些文件是否应保留在公开仓库中。

#### 验收标准

| # | 条件 |
|---|------|
| AC-F11-1 | `README.md` 不再包含"内部使用，请勿外传"或类似措辞 |
| AC-F11-2 | `app.py` Gradio footer 不再显示"内部使用"或"请勿外传" |
| AC-F11-3 | `training-materials/` 文件的合规状态已与项目负责人确认并处理 |
| AC-F11-4 | `rg -i "内部使用|请勿外传|内部资料" --glob="*.{md,py}"` 在项目源码中无匹配（或仅限于明确标记为内部文件的 `.gitignore` 条目） |

---

## 3. 实施建议

### 3.1 推荐实施顺序

```
Phase 1 (串行链):  F03 → F01 → F02
Phase 2 (并行):    F04, F05, F06, F07, F08, F09, F10, F11
```

Phase 1 构建离线部署闭环的核心骨架；Phase 2 的所有项目互不依赖，可并行实施。

### 3.2 测试验证策略

1. **F01-F03 集成测试**：在干净 Windows 10 虚拟机上执行完整离线部署流程
2. **F04 独立测试**：在有网机器运行 `build-offline-package.bat`，验证 `requirements.lock.txt` 内容
3. **F05-F06 静态检查**：`rg` 搜索残留引用
4. **F07 功能测试**：在 RAG Tab 上传各格式文件，验证索引行为
5. **F08 环境变量测试**：在无系统 Ollama 的机器上双击 `opencode.bat`
6. **F09 单元测试**：`ExcelParser().parse("test.csv")`
7. **F10 运行测试**：`python verify_offline.py` 全量检查
8. **F11 文档审查**：README.md 人工复查

### 3.3 回滚方案

所有修改均为增量式——不删除现有功能，仅修正和扩展。若某项修复引入新问题，可单独回滚对应文件到修改前版本。

---

> **文档维护者**: Alice (Product Manager)  
> **最后更新**: 2025-07-03  
> **关联文档**: `docs/system_design.md`（P1 修复系统设计）, `DEPLOY.md`（部署指南）, `README.md`
