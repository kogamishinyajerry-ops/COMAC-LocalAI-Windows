"""
COMAC 离线AI文档处理平台 - Windows 低配配置
目标终端: 16GB RAM, NVIDIA GRID RTX6000-1Q, Xeon Gold 6242R
策略: 单一 Qwen3-4B Q4_K_M 模型 (性能≈Qwen2.5-7B, 仅 2.5GB), 混合推理
"""
import os
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# 模型常量 — Qwen3-4B Q4_K_M 策略（性能匹配 Qwen2.5-7B，体积减半）
# =============================================================================
MODEL_COMAC = os.environ.get("COMAC_MODEL", "qwen3:4b-q4_K_M")
MODEL_EMBED = os.environ.get("COMAC_EMBED_MODEL", "nomic-embed-text")

# 统一别名: 所有模块都引用 MODEL_DOC
MODEL_DOC = MODEL_COMAC

# =============================================================================
# Ollama 性能参数 (低配优化)
# =============================================================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
OLLAMA_NUM_PARALLEL = 1       # 单线程推理 (CPU 瓶颈)
OLLAMA_MAX_LOADED_MODELS = 1  # 只加载一个模型
OLLAMA_KEEP_ALIVE = "5m"      # 5分钟无请求后卸载

# 推理参数
DEFAULT_NUM_CTX = 32768       # 上下文窗口（Qwen3-4B 原生 256K, 保守设为 32K）
DEFAULT_NUM_PREDICT = 2048    # 最大生成长度
DEFAULT_NUM_GPU = 99           # GPU 层数（99=全部，RTX 4070 8GB 可加载整个 4B 模型）
