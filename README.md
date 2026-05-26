# COMAC 离轴线AI文档处理平台（Windows 内网版）

面向 16GB RAM Windows 10 终端的空气隔离内网 AI 文档处理工具。

## 硬件要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10 x64 |
| 内存 | 16GB RAM（纯 CPU 推理） |
| CPU | Intel Xeon / Core i7+ |
| 磁盘 | 10GB 可用空间（含模型约 5GB） |
| GPU | 可选（无 GPU 时使用 CPU 推理） |

## 模型策略

**单一 7B 模型** — Qwen2.5-7B-Instruct Q4_K_M（~4.7GB），纯 CPU 推理。

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
#    建议: qwen2.5-7b-instruct-q4_k_m.gguf
#    下载地址: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

# 2. 将以下文件复制到内网机器:
#    - COMAC-LocalAI-Windows/  整个项目目录
#    - qwen2.5-7b-instruct-q4_k_m.gguf  模型权重文件
#    - ollama-models/Modelfile  模型定义文件

# 3. 将 GGUF 文件放入 ollama-models/ 目录

# 4. 运行 setup.bat（选择离线模式）
setup.bat

# 5. 启动
start.bat
```

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
| `COMAC_MODEL` | `qwen:7b-q4_K_M` | 主模型名称 |
| `COMAC_EMBED_MODEL` | `nomic-embed-text` | 向量嵌入模型 |
| `OLLAMA_HOST` | `localhost:11434` | Ollama 服务地址 |

## 许可证

内部使用，请勿外传。
