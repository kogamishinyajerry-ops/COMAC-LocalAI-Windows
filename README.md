# COMAC 离轴线AI文档处理平台（Windows 内网版）

面向 16GB RAM Windows 10 终端的空气隔离内网 AI 文档处理工具。

## 硬件要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10 x64 |
| 内存 | 16GB RAM（纯 CPU 推理） |
| CPU | Intel Xeon / Core i7+ |
| 磁盘 | 8GB 可用空间（含模型约 2.5GB） |
| GPU | 可选（无 GPU 时使用 CPU 推理） |

## 模型策略

**单一 Qwen3-4B 模型** — Qwen3-4B-Instruct Q4_K_M（~2.5GB），性能匹配 Qwen2.5-7B，体积减半，纯 CPU 推理。原生支持 256K 上下文、119 种语言、思考模式。

## 功能模块

- 文档摘要 · 润色 · 格式转换
- 模板智能填充
- 批量文档处理
- 敏感信息检测
- RAG 智能问答
- 知识图谱构建
- 多Agent协作（5角色）

## 快速部署

```bash
# 1. 安装 Ollama（仅部署机需互联网）
#    https://ollama.com/download/windows

# 2. 初始化部署（首次运行）
setup.bat

# 3a. 启动 Web 界面（Gradio）
start.bat
# 访问: http://localhost:7860
# 默认账号: admin（密码见 .env 文件，请及时修改）

# 3b. 启动终端对话（TUI）
opencode                   # 在任意 PowerShell/CMD 中直接输入（首次运行 start.bat 后自动生效）
```

### 空气隔离内网部署（无互联网）

```bash
# 1. 在有网的机器上下载 GGUF 模型文件
#    建议: qwen3-4b-instruct-q4_k_m.gguf
#    下载地址: https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF

# 2. 将以下文件复制到内网机器:
#    - COMAC-LocalAI-Windows/  整个项目目录
#    - qwen3-4b-instruct-q4_k_m.gguf  模型权重文件
#    - ollama-models/Modelfile  模型定义文件

# 3. 将 GGUF 文件放入 ollama-models/ 目录

# 4. 运行 setup.bat（选择离线模式）
setup.bat

# 5. 启动
start.bat
```

## 离线包一键部署（推荐）

对于完全无网的内网 Windows 10 机器，推荐使用离线包方式：

### 第一步：有网机器构建离线包

1. 确保已安装 Python 3.11+
2. 下载 `python-3.11.8-amd64.exe` 放入 `tools/` 目录
3. 下载模型 GGUF 文件放入 `ollama-models/` 目录
4. 双击运行 `build-offline-package.bat`
5. 等待构建完成，得到 `offline_bundle/` 目录

### 第二步：内网机器一键安装

1. 将 `offline_bundle/` 整个目录复制到内网 Windows 10 机器
2. 进入 `offline_bundle/`，双击运行 `install-offline.bat`（首次约 10-15 分钟）
3. 安装完成后运行 `start.bat`
4. 访问 http://localhost:7860

### 安全说明

- 首次部署自动生成随机 16 位管理员密码，请妥善保存
- 默认仅绑定本地 (127.0.0.1)，如需局域网访问请在 `.env` 中设置 `GRADIO_SERVER_NAME=0.0.0.0`
- 强制启用 Gradio 认证，未配置凭据时自动生成临时密码

## 目录结构

```
COMAC-LocalAI-Windows/
├── app.py                  # 主应用（Gradio Web UI）
├── cli_chat.py             # 终端 TUI 对话脚本
├── opencode.bat            # opencode 命令入口（PowerShell 中输入 opencode 即可）
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── setup.bat               # 部署初始化脚本
├── start.bat               # 启动脚本
├── .env                    # 环境变量（密码等，含敏感信息）
├── .gitignore              # Git 忽略规则
│
├── audit/                  # 敏感信息检测
├── batch/                  # 批量处理
├── converters/             # 文档格式转换
├── fillers/                # 模板填充
├── parsers/                # 文档解析
├── presentations/          # 报告生成
├── static/                 # CSS 样式
├── templates/              # Jinja2 模板
│   ├── form/
│   └── report/
│
├── ollama-models/          # Ollama 模型文件（用户自行放置 GGUF）
│   └── Modelfile
│
├── docs/                   # RAG 知识库文档（放入待索引的 txt/md 文件）
├── temp/                   # 运行时上传/输出目录
└── logs/                   # 日志文件
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GRADIO_USER` | `admin` | Web UI 用户名 |
| `GRADIO_PASS` | `change_me_123` | Web UI 密码（**必须修改**） |
| `COMAC_MODEL` | `qwen3:4b-q4_K_M` | 主模型名称 |
| `COMAC_EMBED_MODEL` | `nomic-embed-text` | 向量嵌入模型 |
| `OLLAMA_HOST` | `127.0.0.1:11435` | Ollama 服务地址 |

## 许可证

MIT License — 详见 LICENSE 文件。
