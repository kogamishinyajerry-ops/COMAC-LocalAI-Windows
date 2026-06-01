# COMAC 离轴线AI文档处理平台 — 部署指南

## 部署架构

本项目采用**两阶段部署**：

```
有网机器（Phase 1）              内网机器（Phase 2）
┌─────────────────────┐          ┌─────────────────────┐
│  pre-deploy.bat     │ ──复制──▶│  setup.bat（验证）  │
│  创建 .venv         │  整个     │  start.bat（启动）   │
│  下载模型           │  项目     │                    │
│  初始化 Ollama      │  目录     │                    │
└─────────────────────┘          └─────────────────────┘
```

- **Phase 1（有网）**：运行一次 `pre-deploy.bat`，完成 .venv 创建、依赖安装、模型下载
- **Phase 2（内网）**：将整个项目目录复制过去，双击 `setup.bat` 验证 + `start.bat` 启动

> ⚠️ **关键要求**：内网机器的 Python 版本必须与 Phase 1 使用的一致（Phase 1 会显示版本号）

---

## Phase 1：有网机器初始化（约 20-30 分钟）

### 前置条件
- Python 3.11+（[下载地址](https://www.python.org/ftp/python/)）
- 互联网连接
- 磁盘空间 10GB+

### 操作步骤

```
1. 将本项目复制到有网机器

2. 双击运行 pre-deploy.bat

3. 等待完成（约 20-30 分钟）:
   [1/6] 创建 Python 虚拟环境
   [2/6] 安装 Python 依赖（gradio、ollama、pandas 等）
   [3/6] 初始化 Ollama
   [4/6] 启动 Ollama 服务
   [5/6] 下载 qwen3:4b-q4_K_M 模型（约 2.5 GB）
   [6/6] 初始化配置

4. 记住屏幕显示的 Python 版本号（例如 Python 3.11）

5. 将整个项目目录复制到 U 盘
```

---

## Phase 2：内网机器部署

### 前置条件
- Python 3.11+（**版本必须与 Phase 1 一致**）
- 内存 16GB+
- 磁盘 10GB+

### 操作步骤

```
1. 将整个项目目录复制到内网机器

2. 确认内网机器的 Python 版本与 Phase 1 一致

3. 双击运行 setup.bat（验证，约 1 分钟）

4. 双击运行 start.bat（启动服务）

5. 浏览器访问 http://localhost:7860
   登录: admin / change_me_123（请立即修改）
```

---

## 组件说明

| 组件 | 大小 | 说明 |
|------|------|------|
| `.venv/` | ~1GB | Python 虚拟环境，含所有依赖 |
| `tools/ollama/` | ~500MB | Ollama 可执行文件 |
| Ollama 模型缓存 | ~2.5GB | qwen3:4b-q4_K_M 模型 |
| `ollama-models/` | 可选 | GGUF 文件（用于离线创建模型） |

---

## 两种使用方式

### 方式一：Web 界面（Gradio）

双击运行 `start.bat`，浏览器打开 http://localhost:7860

### 方式二：终端对话（TUI）

`start.bat` 运行后，`opencode` 命令已自动注册到 PATH。
在任意 PowerShell 窗口输入 `opencode` 即可启动 TUI。

---

## 常见问题

### Q: 内网机器没有 Python 怎么办？

**方案 A（推荐）**：在有网机器上把 Python 安装程序也拷进 U 盘：
```
https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
```
复制到内网机器后双击安装，安装时**务必勾选 Add to PATH**。

**方案 B**：在有网机器用 `winget` 下载离线安装包：
```
winget download --id Python.Python.3.11 -o .\
```

### Q: Python 版本不一致怎么办？

如果内网机器已有 Python 但版本不同，删除 `.venv` 后重新在对应版本的 Python 机器上运行 `pre-deploy.bat`。

### Q: 模型下载失败怎么办？

手动下载 GGUF 文件：
1. 访问 https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF
2. 下载 `qwen3-4b-instruct-q4_k_m.gguf`（约 2.5GB）
3. 放入项目的 `ollama-models/` 目录
4. 运行 `setup.bat`

### Q: Ollama 启动报错？

检查 Visual C++ Redistributable 是否安装：
- 双击运行 `tools\ollama\vc_redist.x64.exe` 手动安装

### Q: .venv 依赖验证失败？

在有网机器运行 `pre-deploy.bat` 重新初始化。

---

## 卸载方法

```
1. 停止服务: taskkill /IM python.exe /F
2. 删除项目目录
3. 删除 Ollama（可选）: 控制面板 → 程序和功能 → Ollama
```
