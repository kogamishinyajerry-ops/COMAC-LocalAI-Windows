# COMAC 离线AI文档处理平台 (Windows 低配版)

面向 16GB RAM Windows 10 终端的离线 AI 文档处理工具。

## 硬件要求

| 项目 | 最低要求 |
|------|----------|
| 操作系统 | Windows 10 x64 |
| 内存 | 16GB RAM |
| CPU | Intel Xeon / Core i7+ |
| GPU | 无要求 (纯CPU推理) |
| 磁盘 | 10GB 可用空间 |

## 模型策略

单一 7B 模型 — Qwen2.5-7B-Instruct Q4_K_M (~4.7GB)，纯 CPU 推理。

## 功能

- 文档摘要、润色、格式转换
- 模板智能填充
- 批量文档处理
- 敏感信息检测
- RAG 智能问答
- 知识图谱构建
- 多Agent协作 (5角色)

## 快速开始

```bash
# 1. 安装 Ollama (https://ollama.com/download/windows)
# 2. 下载 GGUF 模型到 ollama-models/
# 3. 运行部署脚本
setup.bat
# 4. 启动
start.bat
```

访问 http://localhost:7860

## 依赖

- Python 3.9+
- Ollama (Windows)
- Gradio
- python-pptx, python-docx, openpyxl

## 许可证

内部使用，请勿外传。
