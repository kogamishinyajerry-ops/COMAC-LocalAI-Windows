#!/bin/bash
#==============================================================================
# COMAC 离线AI文档处理平台 - 一键启动脚本 v2.0
#
# 功能：
#   1. 检查/启动Ollama服务
#   2. 检查模型可用性
#   3. 设置Python虚拟环境
#   4. 启动Obsidian双向同步服务
#   5. 启动Gradio主界面
#
# 适用：物理断网环境快速部署
#==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 配置
OLLAMA_HOST="${OLLAMA_HOST:-localhost:11434}"
GRADIO_PORT="${GRADIO_PORT:-7860}"
VAULT_PATH="${VAULT_PATH:-}"

# 日志
LOG_FILE="$SCRIPT_DIR/startup.log"

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_banner() {
    log ""
    log "${CYAN}================================================${NC}"
    log "${CYAN}  COMAC 离线AI文档处理平台 v2.0${NC}"
    log "${CYAN}  双向同步 · 知识积累 · 一键部署${NC}"
    log "${CYAN}================================================${NC}"
    log ""
}

# 检查命令
check_cmd() {
    if command -v "$1" &> /dev/null; then
        log "  ${GREEN}✓${NC} $1"
        return 0
    else
        log "  ${RED}✗${NC} $1 (not found)"
        return 1
    fi
}

#==============================================================================
# 1. 系统检查
#==============================================================================
step_system() {
    log "${BOLD}[1/6] 系统检查${NC}"

    local missing=0

    for cmd in python3 curl git; do
        check_cmd "$cmd" || ((missing++))
    done

    if [ $missing -gt 0 ]; then
        log "${RED}缺少 $missing 个系统依赖${NC}"
        return 1
    fi

    log "  系统检查完成"
    return 0
}

#==============================================================================
# 2. Ollama服务
#==============================================================================
step_ollama() {
    log "${BOLD}[2/6] Ollama服务${NC}"

    # 检查服务
    if curl -s --connect-timeout 3 "http://$OLLAMA_HOST/api/version" > /dev/null 2>&1; then
        log "  ${GREEN}✓${NC} Ollama服务运行中"
    else
        log "  ${YELLOW}⚠${NC} Ollama未运行，尝试启动..."

        if command -v ollama &> /dev/null; then
            log "    启动Ollama服务..."
            (nohup ollama serve > "$SCRIPT_DIR/ollama.log" 2>&1 &) || true
            sleep 5

            if curl -s --connect-timeout 5 "http://$OLLAMA_HOST/api/version" > /dev/null 2>&1; then
                log "  ${GREEN}✓${NC} Ollama服务已启动"
            else
                log "  ${RED}✗${NC} Ollama启动失败，见 ollama.log"
            fi
        else
            log "  ${RED}✗${NC} Ollama未安装"
            log "    安装: curl -fsSL https://ollama.com/install.sh | sh"
        fi
    fi

    # 检查模型
    log "  检查模型..."
    MODELS=("qwen-doc" "qwen3-fast" "deepseek-doc")
    for model in "${MODELS[@]}"; do
        if ollama list 2>/dev/null | grep -q "$model"; then
            log "    ${GREEN}✓${NC} $model"
        else
            log "    ${YELLOW}⚠${NC} $model (未安装)"
            log "       安装: ollama pull $model"
        fi
    done
}

#==============================================================================
# 3. Python环境
#==============================================================================
step_python() {
    log "${BOLD}[3/6] Python环境${NC}"

    if [ ! -d ".venv" ]; then
        log "  创建虚拟环境..."
        python3 -m venv .venv
        log "  ${GREEN}✓${NC} 虚拟环境已创建"
    else
        log "  ${GREEN}✓${NC} 虚拟环境已存在"
    fi

    PIP_CMD="$SCRIPT_DIR/.venv/bin/pip"
    PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python"

    # 升级pip
    log "  升级pip..."
    $PIP_CMD install -q --upgrade pip

    # 安装依赖
    log "  安装Python依赖..."
    $PIP_CMD install -q -r requirements.txt

    if [ $? -eq 0 ]; then
        log "  ${GREEN}✓${NC} 依赖安装完成"
    else
        log "  ${RED}✗${NC} 依赖安装失败"
        return 1
    fi

    # 检查LlamaIndex
    if $PYTHON_CMD -c "import llama_index" 2>/dev/null; then
        log "  ${GREEN}✓${NC} LlamaIndex已安装"
    else
        log "  ${YELLOW}⚠${NC} LlamaIndex未安装，RAG功能不可用"
    fi

    # 检查watchdog
    if $PYTHON_CMD -c "import watchdog" 2>/dev/null; then
        log "  ${GREEN}✓${NC} Watchdog已安装（文件监控）"
    else
        log "  ${YELLOW}⚠${NC} Watchdog未安装，使用轮询模式"
    fi
}

#==============================================================================
# 4. 工作目录
#==============================================================================
step_directories() {
    log "${BOLD}[4/6] 工作目录${NC}"

    dirs=("temp/uploads" "temp/outputs" "templates" "vector_index" "logs")

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log "  ${GREEN}✓${NC} $dir"
    done

    # 初始化Git仓库（如果没有）
    if [ ! -d ".git" ]; then
        log "  初始化Git仓库..."
        git init -q
        echo -e "\n# Python\n.venv/\n__pycache__/\n*.pyc\nvector_index/\nlogs/\n*.log\n\n# IDE\n.vscode/\n.idea/\n\n# OS\n.DS_Store\n*.swp\n\n# Temp\ntemp/uploads/*\ntemp/outputs/*\n!temp/uploads/.gitkeep\n!temp/outputs/.gitkeep\n" > .gitignore
        log "  ${GREEN}✓${NC} Git仓库已初始化"
    fi
}

#==============================================================================
# 5. Obsidian同步（可选）
#==============================================================================
step_obsidian() {
    log "${BOLD}[5/6] Obsidian同步${NC}"

    if [ -z "$VAULT_PATH" ]; then
        log "  ${YELLOW}⚠${NC} 未设置VAULT_PATH，跳过Obsidian集成"
        log "  如需启用: VAULT_PATH=/path/to/vault ./start.sh"
        return 0
    fi

    if [ ! -d "$VAULT_PATH" ]; then
        log "  ${YELLOW}⚠${NC} Vault不存在: $VAULT_PATH"
        log "  跳过Obsidian同步"
        return 0
    fi

    log "  ${GREEN}✓${NC} Vault: $VAULT_PATH"

    # 创建AI-Processed文件夹
    AI_FOLDER="$VAULT_PATH/AI-Processed"
    mkdir -p "$AI_FOLDER"
    log "  ${GREEN}✓${NC} AI-Processed文件夹已创建"

    # 启动Obsidian同步服务
    log "  启动Obsidian同步服务..."
    cat > "$SCRIPT_DIR/obsidian_watcher.py" << PYEOF
#!/usr/bin/env python3
"""Obsidian文件监控服务 - 自动生成，路径动态计算"""
import sys
import os
from pathlib import Path

# 动态计算项目根目录
SCRIPT_DIR = Path("$SCRIPT_DIR")
sys.path.insert(0, str(SCRIPT_DIR))

from obsidian_sync import ObsidianSyncEngine
import time

vault = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Obsidian Vault")
index_path = str(SCRIPT_DIR / "vector_index")

print(f"Starting Obsidian sync for: {vault}")

engine = ObsidianSyncEngine(
    vault_path=vault,
    ai_index_path=index_path,
    watch_enabled=True,
    poll_interval=5.0
)

try:
    engine.start_watch()
    print("Obsidian sync running. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\\nStopping...")
    engine.stop_watch()
PYEOF

    nohup "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/obsidian_watcher.py" "$VAULT_PATH" > "$SCRIPT_DIR/obsidian_sync.log" 2>&1 &
    log "  ${GREEN}✓${NC} Obsidian同步服务已启动"
}

#==============================================================================
# 6. 启动Gradio
#==============================================================================
step_gradio() {
    log "${BOLD}[6/6] 启动Gradio${NC}"

    # 检查端口
    if lsof -Pi :$GRADIO_PORT -sTCP:LISTEN -t > /dev/null 2>&1; then
        log "  ${YELLOW}⚠${NC} 端口$GRADIO_PORT已被占用"
        log "  尝试关闭现有进程..."
        lsof -Pi :$GRADIO_PORT -sTCP:LISTEN -t | xargs kill 2>/dev/null || true
        sleep 2
    fi

    # 启动
    log "  启动Gradio服务..."
    cd "$SCRIPT_DIR"

    nohup "$SCRIPT_DIR/.venv/bin/python" app.py > "$SCRIPT_DIR/app.log" 2>&1 &

    sleep 3

    # 检查
    if curl -s --connect-timeout 5 "http://localhost:$GRADIO_PORT" > /dev/null 2>&1; then
        log "  ${GREEN}✓${NC} Gradio已启动: http://localhost:$GRADIO_PORT"
    else
        log "  ${YELLOW}⚠${NC} 等待服务启动..."
        sleep 5
        if curl -s --connect-timeout 5 "http://localhost:$GRADIO_PORT" > /dev/null 2>&1; then
            log "  ${GREEN}✓${NC} Gradio已启动: http://localhost:$GRADIO_PORT"
        else
            log "  ${RED}✗${NC} Gradio启动失败，见 app.log"
        fi
    fi
}

#==============================================================================
# 主流程
#==============================================================================
main() {
    log_banner

    # 解析参数
    for arg in "$@"; do
        case $arg in
            VAULT_PATH=*)
                VAULT_PATH="${arg#*=}"
                export VAULT_PATH
                ;;
            PORT=*)
                GRADIO_PORT="${arg#*=}"
                ;;
            --help|-h)
                echo "用法: $0 [VAULT_PATH=/path/to/vault] [PORT=7860]"
                echo ""
                echo "示例:"
                echo "  $0                              # 不启用Obsidian"
                echo "  VAULT_PATH=~/Vault $0          # 启用Obsidian同步"
                echo "  $0 VAULT_PATH=~/Vault PORT=8080"
                exit 0
                ;;
        esac
    done

    # 执行各步骤
    step_system || exit 1
    step_ollama
    step_python || exit 1
    step_directories
    step_obsidian
    step_gradio

    # 完成
    log ""
    log "${CYAN}================================================${NC}"
    log "${GREEN}${BOLD}  启动完成！${NC}"
    log "${CYAN}================================================${NC}"
    log ""
    log "  Gradio界面:  http://localhost:$GRADIO_PORT"
    log "  日志文件:    $SCRIPT_DIR/app.log"
    log "  Ollama日志:  $SCRIPT_DIR/ollama.log"
    log ""
    log "  使用示例:"
    log "    # Python调用"
    log "    cd $SCRIPT_DIR && source .venv/bin/activate"
    log "    python -c 'from comac_assistant import *; print(COMACAssistant().get_status())'"
    log ""
    log "    # 启用Obsidian同步"
    log "    VAULT_PATH=~/Vault $0"
    log ""
    log "${CYAN}================================================${NC}"
    log ""
}

main "$@"
