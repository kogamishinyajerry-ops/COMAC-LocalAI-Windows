# COMAC 离轴线AI文档处理平台 — 内网一键部署指南

## 部署前准备

### 硬件需求
- CPU: 支持 AVX2 指令集（Ollama 运行要求）
- 内存: 16GB+（qwen:7b-q4_K_M 加载需要约 6GB）
- 磁盘: 10GB+ 可用空间（含模型约 5GB）

---

### 1. 安装 Ollama（本项目必须依赖）

Ollama 无法打包进项目，必须单独安装：

**有网机器：**
```
https://ollama.com/download/windows
```

**空气隔离内网机器：**
将安装包通过 U盘复制到内网机器，双击安装。

---

### 2. 安装 Python 3.11（本项目必须依赖）

Python 3.11 用于创建虚拟环境（.venv），Ollama 模型运行不依赖 Python。

**方式 A（推荐）— Python.org 安装程序：**
1. 下载 `python-3.11.8-amd64.exe`（约 25MB）
   ```
   https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
   ```
2. 将安装程序放入本项目 `tools\` 目录，重命名为 `python-3.11.8-amd64.exe`
3. setup.bat 会自动检测并使用

**方式 B — Microsoft Store（需联网安装）：**
在 PowerShell 中运行：
```
winget install Python.Python.3.11
```

**方式 C — 已安装 Python 3.11：**
如果系统已有 Python 3.11（python.org 或 Microsoft Store），setup.bat 会自动检测使用，无需额外操作。

> ⚠️ **Python Embeddable 不支持创建 venv**：如果内网机器只有 Python Embeddable，setup.bat 会提示错误，此时需要安装完整版 Python 3.11。

---

### 3. 准备 python-wheels 离线包（内网离线部署必须）

在**有网的 Windows 机器**上：

```
1. 将项目文件夹复制到有网机器
2. 确认 Python 3.11 已安装（方式 A/B/C 任选）
3. 双击运行 download-wheels.bat（约 5-10 分钟）
4. 等待 python-wheels\ 目录生成约 200+ 个 .whl 文件
5. 将 python-wheels\ 目录一起打包进项目文件夹
6. 传到内网机器
```

> **重要**：download-wheels.bat 必须与目标机器的 Python 版本一致（均为 3.11），否则依赖安装会失败。

---

## 部署步骤

### 有网机器（在线模式）

```
1. 安装 Ollama（下载 ollama-windows-amd64.zip 安装）
2. 安装 Python 3.11（方式 A/B/C 任选）
3. 双击 setup.bat  → 初始化
4. 双击 start.bat  → 启动服务
5. 浏览器打开 http://localhost:7860
```

### 空气隔离内网（离线模式）

```
前提条件：
  - Ollama 已安装
  - Python 3.11 已安装（或 python-3.11.8-amd64.exe 放入 tools\）
  - python-wheels\ 已预装（约数百 MB）
  - qwen2.5 GGUF 模型文件已放入 ollama-models\（约 4.5GB）

部署步骤：
1. 双击 setup.bat  → 初始化（全程离线）
2. 双击 start.bat  → 启动服务
3. 浏览器打开 http://localhost:7860
```

1. 双击 setup.bat         → 初始化（使用本地 wheel 包，无需网络）
2. 双击 start.bat        → 启动服务
3. 浏览器打开 http://localhost:7860
4. 任意 PowerShell 输入 opencode  → TUI 对话
```

**setup.bat 进度显示（7步）：**
```
[1/7] 检查 Python 环境         [OK]
[2/7] 检查 Visual C++ 运行时   [OK/警告]
[3/7] 检查 Ollama 服务         [OK]
[4/7] 准备 qwen:7b-q4_K_M 模型  [OK]
[5/7] 准备向量嵌入模型          [OK/警告]
[6/7] 安装 Python 依赖          [OK]
[7/7] 初始化配置               [OK]
部署初始化完成！
```

---

## 常见错误及处理

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `[错误] Python 未找到` | Python 未安装或未加入 PATH | 下载 Python 3.10: https://www.python.org/ftp/python/ ，安装时勾选 "Add to PATH" |
| `[警告] 未检测到 Visual C++ Redistributable` | 缺少 VC++ 运行时 | 下载 vc_redist.x64.exe: https://aka.ms/vs/17/release/vc_redist.x64.exe |
| `[错误] Ollama 未安装` | Ollama 未安装 | 从 https://ollama.com/download/windows 下载安装 |
| `[错误] 依赖安装失败` | 内网无法访问 PyPI | 在有网机器运行 download-wheels.bat，将 python-wheels\ 目录一起打包 |
| `[错误] 模型创建失败` | GGUF 文件不完整或 Modelfile 缺失 | 确认 ollama-models\ 下有 .gguf 文件和 Modelfile |

---

## 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 x64 (1809+) | Windows 11 |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 10GB 可用空间 | 20GB+（含模型） |
| Python | 3.9+ | 3.10 / 3.11 |
| Ollama | 最新版 | 最新版 |

> Windows 10 1809 以下版本可能缺少内置 `curl`，如遇 Ollama 连接问题请升级 Windows 或安装 Windows Update KB4565500。

---

## 两种使用方式

### 方式一：Web 界面（Gradio）

双击运行 `start.bat`，浏览器自动打开 http://localhost:7860，输入用户名/密码登录。

适合：文档上传、格式转换、知识库管理等需要文件交互的场景。

### 方式二：终端对话（TUI）

首次运行 `start.bat` 后，`opencode` 命令已自动注册到系统 PATH。

**后续使用（任意 PowerShell/CMD 窗口）：**

```
opencode
```

即可进入 OpenCode TUI 终端对话界面，驱动模型为 `qwen:7b-q4_K_M`。

适合：快速提问、文本润色、摘要、代码调试等需要即时交互的场景。

**opencode 内置命令：**

| 命令 | 说明 |
|------|------|
| `/exit`, `/quit` | 退出 TUI |
| `/clear` | 清屏 |
| `/history` | 查看当前对话历史 |
| `/model <模型名>` | 切换模型（运行时切换） |
| `/help` | 显示帮助 |
| `Ctrl+C` | 终止当前生成 |

---

## 部署验证清单

| 序号 | 验证项 | 方法 | 预期结果 |
|------|--------|------|---------|
| 1 | setup.bat 完成 | 双击运行 | 7个步骤全部 [OK] |
| 2 | start.bat 启动 | 双击运行，浏览器打开 | Gradio 界面可访问 |
| 3 | 登录成功 | 输入用户名/密码 | 进入主界面 |
| 4 | Ollama 连接状态 | 查看 Gradio UI 状态 | 🟢 已连接 |
| 5 | opencode TUI | 新开 PowerShell，输入 opencode | TUI 启动成功 |
| 6 | 文档摘要功能 | 上传 .txt 文件，点击摘要 | 返回摘要内容 |
| 7 | 格式转换功能 | 上传 .docx，转换为 .pdf | 生成转换后文件 |
| 8 | 知识库索引 | 放入 .txt 到 docs/，调用 RAG 索引 | 索引成功 |
| 9 | 知识图谱构建 | 输入文本，构建图谱 | 显示 Mermaid 图 |

---

## 卸载方法

1. 停止运行：`taskkill /IM python.exe /F`
2. 删除项目文件夹
3. 删除 Ollama（可选）：控制面板 → 程序和功能 → Ollama
