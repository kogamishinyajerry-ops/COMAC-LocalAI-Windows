# 离线模型工作站整合说明

本文档说明如何将 `~/ollama-doc-models/` 离线模型工作站与本培训项目整合。

---

## 1. 模型包内容

| 模型 | 用途 | 特点 |
|------|------|------|
| `qwen-doc` | 主力模型 | Qwen2.5-32B, 32K ctx, temp 0.3。总结/润色/表格 |
| `qwen3-fast` | 快速档 | Qwen3-30B-A3B, 亚秒级响应。批量短任务 |
| `deepseek-doc` | 推理档 | DeepSeek-R1, temp 0.6。逻辑重组/多步抽取 |

## 2. OCR 工具

| 工具 | 用途 |
|------|------|
| `ocrtext` | macOS Vision OCR，对图片进行中文识别 |
| `pdfocr.sh` | PDF→文本，自动判断文字层/扫描件 |

---

## 3. 整合配置

### 3.1 模型路由

`ollama_client.py` 已配置模型路由：

```python
from ollama_client import ModelRouter, OCRProcessor

router = ModelRouter()

# 文档摘要 → qwen-doc
summary = router.route("summarize", "总结以下文档...")

# 快速任务 → qwen3-fast
quick_result = router.route("fast", "翻译这句话...")

# 逻辑推理 → deepseek-doc
logic_result = router.route("logic", "分析这个逻辑...")
```

### 3.2 OCR 处理

```python
from ollama_client import OCRProcessor

ocr = OCRProcessor()

# 图片 OCR
text = ocr.ocr_image("screenshot.png")

# PDF 转文本（自动判断）
text = ocr.pdf_to_text("document.pdf")
```

---

## 4. 模型调用示例

### 4.1 直接调用

```python
from ollama_client import OllamaClient, MODEL_DOC, MODEL_FAST, MODEL_DEEP

# 主力模型（文档处理）
client = OllamaClient(MODEL_DOC)
result = client.generate("总结这份文档的要点")

# 快速模型（批量任务）
fast_client = OllamaClient(MODEL_FAST)
result = fast_client.generate("翻译这段文字")

# 推理模型（复杂分析）
deep_client = OllamaClient(MODEL_DEEP)
result = deep_client.generate("分析这个流程的逻辑问题")
```

### 4.2 带系统提示

```python
client = OllamaClient(MODEL_DOC)
result = client.generate(
    prompt="请总结这份技术报告",
    system="你是一个专业的技术文档助手，擅长提取关键信息。"
)
```

---

## 5. 验证模型状态

```bash
# 检查三个模型是否可用
ollama list | grep -E "qwen-doc|qwen3-fast|deepseek-doc"

# 验证 Ollama 服务
curl 127.0.0.1:11435/api/version

# 验证 OCR 工具
~/ollama-doc-models/ocrtext --help 2>/dev/null || echo "OCR OK"
~/ollama-doc-models/pdfocr.sh <任意pdf> | head
```

---

## 6. 注意事项

### 6.1 温度设置

| 模型 | 温度 | 说明 |
|------|------|------|
| qwen-doc | 0.3 | 适合稳定的总结输出 |
| qwen3-fast | 0.3 | 快速档低温 |
| deepseek-doc | 0.6 | **必须 ≥0.5**，否则会卡死 |

### 6.2 模型权重

- 模型权重 (~56GB) 在 `~/.ollama/models/`
- 不在本项目目录内
- 迁移时运行 `setup.sh` 重新下载

### 6.3 中文文件名

处理含全角字符的中文文件名时，请使用完整路径而非手动输入。

---

## 7. OpenCode Provider 配置（可选）

如需让 OpenCode 使用本地模型，在 `~/.config/opencode/opencode.json` 合并：

```json
{
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://127.0.0.1:11435/v1" },
      "models": {
        "qwen-doc": { "name": "qwen-doc (文档主力)" },
        "qwen3-fast": { "name": "qwen3-fast (快速)" },
        "deepseek-doc": { "name": "deepseek-doc (推理)" }
      }
    }
  }
}
```

> 注意：这三个变体是为文档工作调的（低温、32K），不适合直接当编码 agent 后端。

---

## 8. 多Agent协作系统

### 8.1 Agent团队架构

| Agent | 名称 | 职责 |
|-------|------|------|
| 主编Agent | 张明 | 任务协调、计划制定、最终审核 |
| 校审Agent | 李华 | 文字校对、敏感检测、格式规范 |
| 可视化Agent | 王芳 | 图表设计、PPT制作、HTML报告 |
| 文档Agent | 陈静 | 文档解析、格式转换、内容提取 |
| 知识管理Agent | 刘伟 | 知识检索、文档比对、归档管理 |

### 8.2 使用示例

```python
from multi_agent import MultiAgentOrchestrator, AgentRole

# 初始化团队
orch = MultiAgentOrchestrator()

# 获取团队状态
status = orch.get_team_status()
for agent in status['agents']:
    print(f"{agent['name']} ({agent['role']})")

# 主编处理任务
chief = orch.agents[AgentRole.CHIEF_EDITOR]
result = chief.client.generate("帮我审查这份文档...")

# 校审检查敏感信息
proof = orch.agents[AgentRole.PROOFREADER]
```

### 8.3 任务管理

```python
from task_manager import TaskState, task_manager

# 查看任务状态
tasks = task_manager.get_all_tasks()
for t in tasks:
    print(f"{t.description}: {t.state.value}")

# 取消任务
task_manager.cancel_task(task_id)
```

---

## 9. 下一步

1. 确保 Ollama 服务运行中：`ollama serve`
2. 确认模型已加载：`ollama list`
3. 启动 Gradio UI：`python app.py`
4. 访问：http://localhost:7860
5. 或使用 OpenCode CLI 调用 `multi_agent.py`
