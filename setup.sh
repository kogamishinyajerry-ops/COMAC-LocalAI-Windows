#!/bin/bash
#==============================================================================
# COMAC 离线AI文档处理平台 - 初始化设置脚本 v2.0
#
# 功能：
#   1. 检查系统依赖
#   2. 安装Ollama（如需要）
#   3. 拉取AI模型
#   4. 创建Python虚拟环境
#   5. 安装依赖
#   6. 配置Obsidian同步
#
# 适用：物理断网环境首次部署
#==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

MODELS=("qwen-doc" "qwen3-fast" "deepseek-doc")
EMBED_MODEL="nomic-embed-text"

log() { echo -e "$1"; }

log_banner() {
    log ""
    log "${CYAN}================================================${NC}"
    log "${CYAN}  COMAC 离线AI文档处理平台 - 初始化${NC}"
    log "${CYAN}================================================${NC}"
    log ""
}

#==============================================================================
# 检查系统依赖
#==============================================================================
check_deps() {
    log "${BOLD}[1/7] 检查系统依赖${NC}"

    local missing=()

    for cmd in python3 curl git; do
        if command -v "$cmd" &> /dev/null; then
            log "  ${GREEN}✓${NC} $cmd"
        else
            log "  ${RED}✗${NC} $cmd (missing)"
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log ""
        log "${RED}缺少依赖: ${missing[*]}${NC}"
        log "请先安装以上依赖"
        exit 1
    fi

    log "  系统依赖检查完成"
}

#==============================================================================
# 检查/安装Ollama
#==============================================================================
install_ollama() {
    log "${BOLD}[2/7] Ollama服务${NC}"

    if command -v ollama &> /dev/null; then
        log "  ${GREEN}✓${NC} Ollama已安装: $(ollama --version 2>/dev/null || echo 'unknown')"
    else
        log "  ${YELLOW}⚠${NC} Ollama未安装"

        if [ -f "/Applications/Ollama.app" ]; then
            log "    发现Ollama.app，尝试启动..."
            open -a Ollama || true
            sleep 3
        else
            log "    请安装Ollama:"
            log "    macOS:  curl -fsSL https://ollama.com/install.sh | sh"
            log "    Linux:   curl -fsSL https://ollama.com/install.sh | sh"
            log "    或从 https://ollama.com/download 下载"
        fi
    fi

    # 启动服务
    if ! curl -s --connect-timeout 3 http://localhost:11434/api/version > /dev/null 2>&1; then
        log "    启动Ollama服务..."
        (nohup ollama serve > "$SCRIPT_DIR/ollama.log" 2>&1 &) || true
        sleep 5
    fi

    if curl -s --connect-timeout 5 http://localhost:11434/api/version > /dev/null 2>&1; then
        log "  ${GREEN}✓${NC} Ollama服务运行中"
    else
        log "  ${RED}✗${NC} Ollama服务启动失败"
    fi
}

#==============================================================================
# 拉取模型
#==============================================================================
pull_models() {
    log "${BOLD}[3/7] AI模型${NC}"

    if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        log "  ${YELLOW}⚠${NC} Ollama服务不可用，跳过模型检查"
        return 0
    fi

    log "  检查模型..."
    for model in "${MODELS[@]}"; do
        if ollama list 2>/dev/null | grep -q "^$model "; then
            log "    ${GREEN}✓${NC} $model (已安装)"
        else
            log "    ${YELLOW}⚠${NC} $model (未安装)"
            log "       运行以下命令安装:"
            log "       ollama pull $model"
        fi
    done

    # Embed模型
    if ollama list 2>/dev/null | grep -q "^$EMBED_MODEL "; then
        log "    ${GREEN}✓${NC} $EMBED_MODEL (已安装)"
    else
        log "    ${YELLOW}⚠${NC} $EMBED_MODEL (未安装，用于RAG)"
        log "       运行: ollama pull $EMBED_MODEL"
    fi
}

#==============================================================================
# 创建虚拟环境
#==============================================================================
setup_venv() {
    log "${BOLD}[4/7] Python虚拟环境${NC}"

    if [ -d ".venv" ]; then
        log "  ${YELLOW}⚠${NC} 虚拟环境已存在"
        log "    删除后重新创建: rm -rf .venv"
    else
        log "  创建虚拟环境..."
        python3 -m venv .venv
        log "  ${GREEN}✓${NC} 虚拟环境已创建"
    fi

    PIP="$SCRIPT_DIR/.venv/bin/pip"
    PY="$SCRIPT_DIR/.venv/bin/python"

    # 升级pip
    log "  升级pip..."
    $PIP install -q --upgrade pip

    # 安装核心依赖
    log "  安装Python依赖..."

    # 分批安装，避免超时
    $PIP install -q 'pip>=23.0' 'setuptools>=65.0' || true

    # 基础依赖
    $PIP install -q \
        'gradio>=4.0.0' \
        'python-docx>=1.0.0' \
        'python-pptx>=0.6.21' \
        'pandas>=2.0.0' \
        'openpyxl>=3.1.0' \
        'pdfplumber>=0.10.0' \
        'PyMuPDF>=1.23.0' \
        'jinja2>=3.1.0' \
        'watchdog>=3.0.0'

    # RAG依赖（可选）
    log "  安装LlamaIndex（可选，用于RAG）..."
    $PIP install -q 'llama-index>=0.10.0' 'llama-index-llms-ollama>=0.1.0' || {
        log "  ${YELLOW}⚠${NC} LlamaIndex安装失败，RAG功能不可用"
        log "    可稍后手动安装: pip install llama-index llama-index-llms-ollama"
    }

    # 验证
    if $PY -c "import gradio" 2>/dev/null; then
        log "  ${GREEN}✓${NC} Gradio已安装"
    fi

    if $PY -c "import llama_index" 2>/dev/null; then
        log "  ${GREEN}✓${NC} LlamaIndex已安装"
    fi
}

#==============================================================================
# 创建目录结构
#==============================================================================
setup_dirs() {
    log "${BOLD}[5/7] 创建目录结构${NC}"

    dirs=(
        "temp/uploads"
        "temp/outputs"
        "temp/test_docs"
        "templates"
        "vector_index"
        "logs"
        "audit"
        "batch"
        "converters"
        "fillers"
        "parsers"
        "presentations"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log "  ${GREEN}✓${NC} $dir"
    done

    # .gitkeep文件
    touch temp/uploads/.gitkeep
    touch temp/outputs/.gitkeep

    log "  目录结构创建完成"
}

#==============================================================================
# Git配置
#==============================================================================
setup_git() {
    log "${BOLD}[6/7] Git配置${NC}"

    if [ -d ".git" ]; then
        log "  ${GREEN}✓${NC} Git仓库已存在"
    else
        log "  初始化Git仓库..."
        git init -q

        cat > .gitignore << 'EOF'
# Python
.venv/
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Virtual environments
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Vector index
vector_index/

# Temp
temp/uploads/*
temp/outputs/*
!temp/uploads/.gitkeep
!temp/outputs/.gitkeep

# Ollama
ollama.log
EOF

        log "  ${GREEN}✓${NC} Git仓库已初始化"
        log "  ${YELLOW}⚠${NC} 请记得首次提交: git add . && git commit -m 'Initial commit'"
    fi
}

#==============================================================================
# Obsidian配置
#==============================================================================
setup_obsidian() {
    log "${BOLD}[7/7] Obsidian配置（可选）${NC}"

    log "  Obsidian集成需要在启动时配置"
    log "  示例: VAULT_PATH=~/Vault ./start.sh"
    log ""
    log "  或在start.sh中设置默认VAULT_PATH环境变量"
}

#==============================================================================
# 完成
#==============================================================================
done_msg() {
    log ""
    log "${CYAN}================================================${NC}"
    log "${GREEN}${BOLD}  初始化完成！${NC}"
    log "${CYAN}================================================${NC}"
    log ""
    log "  下一步："
    log "    1. 确保Ollama服务运行中"
    log "    2. 如需模型，运行: ollama pull <model-name>"
    log "    3. 启动服务: ./start.sh"
    log ""
    log "  快速启动（不启用Obsidian）:"
    log "    ./start.sh"
    log ""
    log "  启用Obsidian同步:"
    log "    VAULT_PATH=~/Vault ./start.sh"
    log ""
    log "${CYAN}================================================${NC}"
    log ""
}

#==============================================================================
# 主流程
#==============================================================================
main() {
    log_banner

    check_deps
    install_ollama
    pull_models
    setup_venv
    setup_dirs
    setup_git
    setup_obsidian
    done_msg
}

main "$@"
