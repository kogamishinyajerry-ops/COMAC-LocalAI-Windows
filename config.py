"""
COMAC 离线AI文档处理平台 - Windows 低配配置
目标终端: 16GB RAM, NVIDIA GRID RTX6000-1Q, Xeon Gold 6242R
策略: 单一 7B Q4_K_M 模型, CPU 推理
"""
import os
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# 模型常量 — 单一 7B 模型策略
# =============================================================================
MODEL_COMAC = os.environ.get("COMAC_MODEL", "qwen:7b-q4_K_M")
MODEL_EMBED = os.environ.get("COMAC_EMBED_MODEL", "nomic-embed-text")

# 统一别名: 所有模块都引用 MODEL_DOC
MODEL_DOC = MODEL_COMAC

# =============================================================================
# Ollama 性能参数 (低配优化)
# =============================================================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "localhost:11434")
OLLAMA_NUM_PARALLEL = 1       # 单线程推理 (CPU 瓶颈)
OLLAMA_MAX_LOADED_MODELS = 1  # 只加载一个模型
OLLAMA_KEEP_ALIVE = "5m"      # 5分钟无请求后卸载

# 推理参数
DEFAULT_NUM_CTX = 8192        # 上下文窗口
DEFAULT_NUM_PREDICT = 2048    # 最大生成长度
