# COMAC 离轴线AI文档处理平台 — 内网一键部署检查清单

## 部署前准备

### 方式A：在线部署（目标机器有互联网）

| 序号 | 检查项 | 状态 |
|------|--------|------|
| 1 | Windows 10 x64，已安装 Ollama | ☐ |
| 2 | 磁盘剩余空间 ≥ 10GB | ☐ |
| 3 | 内存 ≥ 16GB | ☐ |
| 4 | 已将项目文件夹复制到目标机器 | ☐ |
| 5 | 已将 `qwen2.5-7b-instruct-q4_k_m.gguf` 放入 `ollama-models/` 目录（如离线模式） | ☐ |

### 方式B：空气隔离内网部署（完全离线）

| 序号 | 检查项 | 状态 |
|------|--------|------|
| 1 | 在有网机器上下载 Qwen2.5-7B-Instruct Q4_K_M GGUF 文件 | ☐ |
| 2 | GGUF 文件已复制到 `ollama-models/` 目录 | ☐ |
| 3 | `ollama-models/Modelfile` 已存在 | ☐ |
| 4 | `ollama-models/qwen2.5-7b-instruct-q4_k_m.gguf` 文件大小约 4.7GB | ☐ |
| 5 | Ollama 已安装（通过 U盘等复制安装包到内网机器） | ☐ |

---

## 部署步骤

### 第一步：运行 setup.bat（仅首次需要）

```
双击 setup.bat
```

**预期输出检查点：**
```
[1/6] 检查 Python 环境 ... [OK]
[2/6] 检查 Ollama 服务 ... [OK]
[3/6] 准备 qwen:7b-q4_K_M 模型 ... [OK]
[4/6] 准备向量嵌入模型 ... [OK/警告]
[5/6] 安装 Python 依赖 ... [OK]
[6/6] 初始化配置 ... [OK]
部署初始化完成！
```

**常见错误及处理：**

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `[错误] Python 未安装` | Python 未安装或未加入 PATH | 安装 Python 3.9+，勾选 "Add to PATH" |
| `[错误] Ollama 未安装` | Ollama 未安装 | 下载 Ollama Windows 版安装 |
| `[错误] qwen 模型未找到` | 模型文件缺失 | 放入 GGUF 到 `ollama-models/`，运行 setup.bat |
| `[错误] 依赖安装失败` | PyPI 无法访问 | 准备 `python-wheels/` 目录，setup.bat 会自动使用 |

### 第二步：修改初始密码

```
# 编辑 .env 文件
notepad .env

# 修改 GRADIO_PASS 为强密码，例如：
GRADIO_PASS=你的强密码
```

**密码安全要求：**
- 至少 8 位
- 包含大小写字母和数字
- 不要使用默认密码 `change_me_123`

### 第三步：运行 start.bat

```
双击 start.bat
```

**预期输出检查点：**
```
[0/4] 检查目录结构 ... [OK]
[1/4] 检查 Ollama 服务 ... [OK]
[2/4] 验证模型 (qwen:7b-q4_K_M) ... [OK]
[3/4] 检查访问认证 ... [OK]
[4/4] 启动 Gradio UI ...
部署成功！
访问地址: http://localhost:7860
```

浏览器将自动打开 http://localhost:7860 ，输入用户名和密码登录。

---

## 部署验证（启动后检查清单）

| 序号 | 验证项 | 方法 | 预期结果 |
|------|--------|------|---------|
| 1 | Gradio UI 可访问 | 浏览器打开 http://localhost:7860 | 显示登录界面 |
| 2 | 登录成功 | 输入 .env 中的用户名/密码 | 进入主界面 |
| 3 | Ollama 连接状态 | 查看 UI 右下角状态 | 🟢 已连接 |
| 4 | 文档摘要功能 | 上传任意 .txt 文件，点击摘要 | 返回摘要内容 |
| 5 | 格式转换功能 | 上传 .docx，转换为 .pdf | 生成转换后文件 |
| 6 | 知识库索引 | 放入 .txt 文件到 docs/，调用 RAG 索引 | 索引成功 |
| 7 | 知识图谱构建 | 输入一段文本，构建图谱 | 显示 Mermaid 图 |
| 8 | Excel 经验表生成 | 输入经验数据，生成报告 | 生成带样式的 Excel |
| 9 | OpenCode TUI | PowerShell 进入项目目录，输入 `opencode.bat`，输入任意问题 | 模型流式返回回答 |

---

## 两种使用方式

部署完毕后，有两种方式使用 AI 能力：

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

## 卸载方法

---

## 故障排查

### 症状：Ollama 连接显示 🔴 未连接

```bash
# 手动检查 Ollama 状态
ollama list

# 重启 Ollama
ollama serve

# 在新窗口验证
curl http://localhost:11434/api/version
```

### 症状：Gradio 启动报错 "Port 7860 in use"

```bash
# 查找占用进程
netstat -ano | findstr ":7860"

# 结束进程（替换 PID 为实际值）
taskkill /PID <PID> /F

# 重新运行
start.bat
```

### 症状：依赖安装失败（离线环境）

```bash
# 在有网机器上下载 wheels
pip download -r requirements.txt -d python-wheels/

# 复制 python-wheels/ 到目标机器
# setup.bat 会自动优先使用本地 wheels
```

### 症状：模型推理速度极慢

- 正常 CPU 推理速度：约 5-15 tokens/秒
- 16GB 内存运行时，确保无其他大型程序占用内存
- 检查是否有多余的 `OLLAMA_NUM_PARALLEL` 或 `OLLAMA_MAX_LOADED_MODELS` 配置

---

## 打包分发（内网IT部门用）

### 推荐打包步骤

```bash
# 1. 在干净机器上（或使用打包脚本）安装依赖
setup.bat

# 2. 验证所有功能正常运行

# 3. 清理运行时文件（重要！）
rmdir /S /Q temp\uploads 2>nul
rmdir /S /Q temp\outputs 2>nul
rmdir /S /Q logs 2>nul
del /Q task_history.db 2>nul

# 4. 删除 .env 中的密码（接收方会自行设置）
# 或者保留空密码由接收方填写

# 5. 打包项目文件夹（排除 .venv 和 GGUF）
# 如果 GGUF 模型文件需要一起分发:
#    - 复制 qwen2.5-7b-instruct-q4_k_m.gguf 到 ollama-models/
#    - 整体打包

# 6. 最终交付物清单:
#    COMAC-LocalAI-Windows.zip  (含 .venv)
#    qwen2.5-7b-instruct-q4_k_m.gguf  (单独传递，或内网镜像站)
#    deploy.bat  (一键部署脚本，内部IT提供)
```

### 最终交付物检查

| 文件/目录 | 是否包含 | 说明 |
|-----------|---------|------|
| `app.py` | ✅ 必须 | 主程序 |
| `config.py` | ✅ 必须 | 配置文件 |
| `requirements.txt` | ✅ 必须 | 依赖清单 |
| `setup.bat` | ✅ 必须 | 部署脚本 |
| `start.bat` | ✅ 必须 | 启动脚本 |
| `.env` | ✅ 必须 | 含密码，传递后由接收方修改 |
| `.venv/` | ✅ 可选 | 已安装的虚拟环境（不含模型） |
| `ollama-models/*.gguf` | ❌ 单独传递 | 模型文件太大，通过内网镜像或U盘传递 |
| `docs/` | ✅ 可选 | 预置 RAG 知识库文档 |
| `templates/` | ✅ 必须 | Jinja2 模板 |
| `temp/ logs/` | ❌ 排除 | 清理后交付 |

---

## 安全配置建议

| 配置项 | 建议 | 说明 |
|--------|------|------|
| 访问控制 | 仅内网访问，不暴露到外网 | `server_name=localhost` |
| 认证 | 强密码（不少于 12 位） | 修改 `.env` 中的 `GRADIO_PASS` |
| 端口 | 使用非默认端口 | 修改 `app.py` 中的 `server_port` |
| 防火墙 | 限制 7860 端口仅内网 IP 访问 | Windows 防火墙规则 |
| 审计日志 | 开启操作日志 | 定期检查 `logs/` 目录 |
