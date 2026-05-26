# 离线测试指南

## 断网前快速验证

```bash
cd COMAC-LocalAI-Training
source .venv/bin/activate
python verify_offline.py
```

## 启动步骤

```bash
# 1. 终端1: 启动 Ollama 服务（保持运行）
ollama serve

# 2. 终端2: 启动 Gradio UI
cd COMAC-LocalAI-Training
source .venv/bin/activate
python app.py

# 3. 浏览器访问
http://localhost:7860
```

## 快速功能测试

### 测试1: 文档摘要
1. 上传任意 `.txt` 或 `.docx` 文件
2. 点击 "Generate Summary"
3. 验证返回摘要内容

### 测试2: 敏感信息检测
1. 上传包含以下内容的测试文档:
   - 身份证号: 110101199001011234
   - 手机号: 13800138000
2. 点击 "Sensitive Detection"
3. 验证能检测到敏感信息

### 测试3: 批量处理
1. 上传多个文档
2. 点击 "Batch Summarize"
3. 验证批量处理结果

## 已知限制

| 功能 | 状态 | 说明 |
|------|------|------|
| 文档摘要 | ✅ | 使用 qwen-doc |
| 格式转换 | ✅ | Word/PDF/Excel互转 |
| 敏感检测 | ✅ | 已优化，支持校验位 |
| 智能填充 | ✅ | Jinja2模板引擎 |
| 批量处理 | ✅ | 多线程支持 |
| OCR | ⚠️ | 需要 macOS Vision |
| PPT生成 | ⚠️ | 需要 python-pptx |

## 故障排查

### 模型不响应
```bash
# 检查模型列表
ollama list

# 手动加载模型（如需要）
ollama pull qwen-doc
ollama pull qwen3-fast
ollama pull deepseek-doc
```

### Gradio 启动失败
```bash
# 检查端口占用
lsof -i :7860

# 使用其他端口
python app.py --port 7861
```

### 敏感检测误报
已优化检测逻辑，支持:
- 身份证校验位验证
- 手机号段校验
- 上下文语义判断
- 连号排除

## 文件位置

```
COMAC-LocalAI-Training/
├── app.py                    # Gradio 主应用
├── ollama_client.py          # 模型客户端
├── verify_offline.py         # 验证脚本（本文件）
├── temp/                     # 上传文件临时目录
│   ├── uploads/
│   └── outputs/
└── presentations/            # 演示生成器
```
