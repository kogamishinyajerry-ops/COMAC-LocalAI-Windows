# COMAC 离线AI文档处理平台 (Windows 低配版)

## 配置说明

目标终端: 16GB RAM, NVIDIA GRID RTX6000-1Q, Xeon Gold 6242R
策略: 单一 7B Q4_K_M 模型, CPU 推理

## 模型

| 模型名 | 底层 | 量化 | 大小 | 上下文 | 用途 |
|--------|------|------|------|--------|------|
| `comac` | Qwen2.5-7B-Instruct | Q4_K_M | ~4.7GB | 8192 | 统一处理所有任务 |

嵌入模型: `nomic-embed-text` (~0.3GB)

## 多Agent团队

所有 Agent 统一使用 `comac` 模型，通过不同的 System Prompt 区分角色：

| Agent | 名称 | 职责 |
|-------|------|------|
| 主编Agent | 张明 | 任务协调、计划制定、最终审核 |
| 校审Agent | 李华 | 文字校对、敏感检测、格式规范 |
| 可视化Agent | 王芳 | 图表设计、PPT制作、HTML报告 |
| 文档Agent | 陈静 | 文档解析、格式转换、内容提取 |
| 知识管理Agent | 刘伟 | 知识检索、文档比对、归档管理 |

## 性能预估

纯 CPU 推理 (Xeon Gold 6242R 20核):
- 推理速度: 8-12 tokens/s
- 首字延迟: 3-5 秒
- 内存峰值: ~8-9GB (含 8K 上下文)

## 部署

```bash
# 首次部署
setup.bat

# 启动
start.bat

# 或手动
python app.py
```

访问 http://localhost:7860

## 项目结构

```
COMAC-LocalAI-Windows/
├── app.py                    # Gradio UI
├── config.py                 # 单模型配置
├── ollama_client.py          # 模型客户端
├── comac_assistant.py        # 多Agent协作
├── setup.bat                 # 一键部署
├── start.bat                 # 一键启动
├── ollama-models/
│   └── Modelfile             # 7B 模型配置模板
├── parsers/                  # 文档解析
├── converters/               # 格式转换
├── fillers/                  # 智能填充
├── batch/                    # 批量处理
├── audit/                    # 内容审核
└── presentations/            # 演示生成
```
