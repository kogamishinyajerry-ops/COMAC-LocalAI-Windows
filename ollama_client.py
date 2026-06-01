import ollama
from typing import Optional, List, Dict, Any
import subprocess
from pathlib import Path
import re
import os
import platform


def _is_oom_error(e: Exception) -> bool:
    """判断是否为显存/内存不足错误"""
    msg = str(e).lower()
    oom_keywords = [
        'cuda', 'out of memory', 'oom', 'memory',
        'failed to allocate', 'allocation failure',
        'buffer for kv', 'kv cache',
    ]
    return any(k in msg for k in oom_keywords)


def _human_readable_error(e: Exception, operation: str = "生成") -> str:
    """将异常转换为用户友好的错误消息"""
    if _is_oom_error(e):
        return (
            f"[资源不足] {operation}失败：显存/内存不足。"
            "建议：关闭其他占用显存的程序，或减少并发请求。"
        )
    msg = str(e)
    # 去掉冗长的路径和内部细节
    if 'ConnectionError' in type(e).__name__ or 'connect' in msg.lower():
        return f"[连接失败] 无法连接 Ollama 服务，请确认 Ollama 已启动。"
    if 'timeout' in msg.lower():
        return f"[超时] {operation}超时，请稍后重试。"
    # 截断过长的错误信息
    if len(msg) > 120:
        msg = msg[:120] + "..."
    return f"[错误] {operation}失败：{msg}"

# 模型名称常量 - 从 config.py 集中管理
from config import (
    MODEL_DOC, MODEL_EMBED,
    DEFAULT_NUM_PREDICT, DEFAULT_NUM_CTX,
    OLLAMA_HOST,
)
IS_WINDOWS = platform.system() == "Windows"

# OCR 工具路径
OLLAMA_DOC_MODELS = Path.home() / "ollama-doc-models"
OCR_BINARY = OLLAMA_DOC_MODELS / "ocrtext"
PDFOCR_SCRIPT = OLLAMA_DOC_MODELS / "pdfocr.sh"

# 允许的操作目录
ALLOWED_DIRS = [
    Path.home(),
    Path("/tmp"),
    Path.cwd(),
]


class PathValidationError(Exception):
    """路径验证失败异常"""
    pass


class CleanResponse:
    """Qwen3-4B 响应后处理：清理自问自答、重复段落、冗余前缀"""
    
    # 需要移除的行模式 (正则)
    _REMOVE_PATTERNS = [
        r'^（注：.*?）\s*$',           # 中文括号注释
        r'^\(注：.*?\)\s*$',           # 英文括号注释
        r'^答案[：:].*',               # "答案："前缀
        r'^最终答案[：:].*',           # "最终答案："前缀
        r'^综上[，,].*',              # "综上，"前缀
        r'^这个数据是否准确[？?]',      # 自问
        r'^这句话是否(准确|正确)[？?]',     # 自问变体
        r'^C919的航程[是为].*',        # 高频重复模式
        r'^（注：.*$',                # 注：开头行
        r'^\(注：.*$',                # 注：开头行(英文)
        r'^.*的(研制|发展|生产).*(目标|背景|意义|过程|成果|影响).*[？?]$',  # 自问QA模式
        r'^但需注意，实际.*?$',         # "但需注意" 啰嗦开头
        r'^不过，也有.*?$',            # "不过，也有" 啰嗦开头
    ]
    
    # 需要截断的模式 (匹配后只保留该行之前的内容)
    _TRUNCATE_PATTERNS = [
        r'^.*的(研制|发展).*(目标|背景|意义).*[？?]',  # 自问QA开始
        r'^C919.*的研制(目标|背景|意义)',              # 变体
        r'^这句话是否(准确|正确)[？?]',               # 自我审查
        r'^你的这句话.*[？?]',                         # 自我审查变体
        r'^\*\*修改后[：:]\*\*',                      # "**修改后：**" 自我修改开始
        r'^\*\*修改说明[：:]\*\*',                    # "**修改说明：**" 
        r'^你的这句话.*[。.]$',                        # "你的这句话..." 自我审查
    ]
    
    # 需要从行尾移除的括号注释
    _STRIP_PARENS = [
        (r'（注：.*?）$', ''),         # 中文括号注释
        (r'\(注：.*?\)$', ''),         # 英文括号注释
    ]
    
    @classmethod
    def clean(cls, text: str) -> str:
        """清理模型输出"""
        if not text:
            return text
        
        lines = text.strip().split('\n')
        cleaned = []
        seen = set()  # 用于去重
        
        for line in lines:
            line = line.strip()
            if not line:
                if cleaned and cleaned[-1]:
                    cleaned.append('')
                continue
            
            # 检查截断模式 - 遇到自问QA开始就停止
            should_truncate = False
            for pattern in cls._TRUNCATE_PATTERNS:
                if re.match(pattern, line):
                    should_truncate = True
                    break
            
            if should_truncate:
                break  # 停止处理后续行
            
            # 检查是否匹配移除模式
            should_skip = False
            for pattern in cls._REMOVE_PATTERNS:
                if re.match(pattern, line):
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # 从行尾去除括号注释
            for pattern, replacement in cls._STRIP_PARENS:
                line = re.sub(pattern, replacement, line).strip()
            
            # 去重：跳过已出现的行
            normalized = line.strip().strip('。. ')
            if normalized and normalized in seen:
                continue
            if normalized:
                seen.add(normalized)
            
            cleaned.append(line)
        
        # 移除尾部空行
        while cleaned and not cleaned[-1]:
            cleaned.pop()
        
        # 全文级重复检测：如果 cleaned 结果是多行重复，只保留第一段
        result = '\n'.join(cleaned)
        
        # 检测重复：按句号拆分，取前 N 句中的第一个有意义段落
        sentences = re.split(r'[。！？]', result)
        if len(sentences) > 3:
            # 检查是否有大量重复句子
            unique_sentences = []
            seen_sent = set()
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                # 检测自我审查模式
                if re.search(r'(这个|这句|该).*(数据|说法|回答|表述|句子).*(是否|对不对|准确|正确|可靠)', s):
                    break  # 遇到自我审查，停止
                if s in seen_sent:
                    continue
                seen_sent.add(s)
                unique_sentences.append(s)
            
            # 如果大部分句子是重复的，只保留前几个不重复的
            if len(unique_sentences) < len(sentences) * 0.4:
                result = '。'.join(unique_sentences[:3]) + ('。' if unique_sentences[:3] else '')
                return result
        
        # 如果清理后变空，返回原文
        if not result.strip():
            return text
        
        # 如果清理后仍很长 (chat 循环)，只取第一段
        MAX_CLEAN_CHARS = 500
        if len(result) > MAX_CLEAN_CHARS:
            # 找到第一个有意义的段落断点
            first_break = len(result)
            for sep in ['\n\n', '\n', '。', '；']:
                pos = result.find(sep)
                if 50 < pos < first_break:
                    first_break = pos + len(sep)
            
            if first_break < len(result):
                result = result[:first_break].strip()
        
        return result


class OllamaClient:
    def __init__(self, model: str = MODEL_DOC):
        self.model = model
        self._verify_connection()

    def _verify_connection(self):
        try:
            ollama.list()
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
        temperature: float = None,
        num_predict: int = 1024,
        enable_thinking: bool = True,
    ) -> str:
        """
        使用Ollama模型生成文本。

        Args:
            prompt: 输入提示词
            system: 系统提示词（可选）
            stream: 是否流式输出
            temperature: 温度参数（默认根据模型自动设置）
            num_predict: 最大生成token数
            enable_thinking: 是否启用 Qwen3 Thinking 模式（深度思考，默认关闭）

        Returns:
            生成的文本内容
        """
        if not prompt or not prompt.strip():
            return "[错误] 输入不能为空"

        # Qwen3-4B 优化温度: 0.5 (平衡准确性与防重复)
        if temperature is None:
            temperature = 0.5

        options = {
            "temperature": temperature,
            "num_predict": num_predict,
            # num_gpu 由 Modelfile 控制，不硬编码
        }
        
        # Qwen3 Thinking 模式: 开启后模型先内部推理再输出
        if enable_thinking:
            options["enable_thinking"] = True
            # Thinking 模式下增加输出长度以容纳思考内容
            options["num_predict"] = max(num_predict, 2048)

        try:
            if system:
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    system=system,
                    options=options,
                    stream=stream
                )
            else:
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options=options,
                    stream=stream
                )
            return CleanResponse.clean(response['response'])
        except Exception as e:
            raise RuntimeError(_human_readable_error(e, "文本生成")) from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = None,
        enable_thinking: bool = True,
    ) -> str:
        """
        使用Ollama模型进行对话。

        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            system: 系统提示词（可选）
            temperature: 温度参数（默认根据模型自动设置）
            enable_thinking: 是否启用 Qwen3 Thinking 模式

        Returns:
            模型回复的文本内容
        """
        if temperature is None:
            temperature = 0.5

        if system:
            full_messages = [{"role": "system", "content": system}] + messages
        else:
            full_messages = messages

        try:
            opts = {
                "temperature": temperature,
                "num_predict": 512,
                "num_ctx": DEFAULT_NUM_CTX,
            }
            if enable_thinking:
                opts["enable_thinking"] = True
                opts["num_predict"] = 2048
            
            response = ollama.chat(
                model=self.model,
                messages=full_messages,
                options=opts,
                stream=False
            )
            return CleanResponse.clean(response['message']['content'])
        except Exception as e:
            raise RuntimeError(_human_readable_error(e, "对话生成")) from e

    def embeddings(self, prompt: str) -> List[float]:
        """获取文本的embedding向量"""
        try:
            response = ollama.embeddings(
                model=self.model,
                prompt=prompt
            )
            return response.get('embedding', [])
        except Exception as e:
            print(f"[OllamaClient] Embedding failed: {e}")
            return []

    def is_model_available(self) -> bool:
        """检查当前模型是否在实际加载列表中"""
        try:
            available = self.list_models()
            return self.model in available
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            response = ollama.list()
            # ollama.list() returns ListResponse with .models attribute (not a plain dict)
            model_list = getattr(response, 'models', []) or []
            return [getattr(m, 'model', str(m)) for m in model_list]
        except Exception:
            return []

class PathValidator:
    """
    路径验证器 - 防止路径遍历攻击
    """

    @staticmethod
    def validate_path(file_path: str, operation: str = "read") -> Path:
        """
        验证文件路径是否安全

        Args:
            file_path: 待验证的路径
            operation: 操作类型 ("read", "write", "execute")

        Returns:
            Path: 验证通过的Path对象

        Raises:
            PathValidationError: 路径验证失败
        """
        path = Path(file_path).resolve()

        # 1. 检查路径遍历攻击
        if ".." in Path(file_path).parts:
            raise PathValidationError(f"路径遍历攻击检测: {file_path}")

        # 2. 检查是否在允许的目录内
        is_allowed = False
        for allowed_dir in ALLOWED_DIRS:
            try:
                path.relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise PathValidationError(
                f"路径不在允许范围内: {file_path}\n"
                f"允许的目录: {[str(d) for d in ALLOWED_DIRS]}"
            )

        # 3. 检查文件是否存在（读取操作时）
        if operation == "read" and not path.exists():
            raise PathValidationError(f"文件不存在: {file_path}")

        # 4. 检查是否是常规文件
        if operation in ["read", "write"] and not path.is_file():
            raise PathValidationError(f"不是常规文件: {file_path}")

        return path

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，去除危险字符
        """
        # 移除路径遍历字符
        filename = filename.replace("..", "")
        # 移除其他危险字符
        dangerous_chars = ['<', '>', '|', '&', ';', '$', '`', '\n', '\r', '\0']
        for char in dangerous_chars:
            filename = filename.replace(char, "_")
        return filename.strip()


class ModelRouter:
    """单模型路由 — 所有任务统一使用 qwen3:4b-q4_K_M"""

    def __init__(self):
        self.client = OllamaClient(MODEL_DOC)

    def route(self, task_type: str, prompt: str, system: str = None) -> str:
        """
        所有任务类型统一由 7B 模型处理。
        通过不同的 system prompt 区分任务风格。
        """
        return self.client.generate(prompt, system)  # 默认用主力


class TaskOrchestrator:
    """
    任务编排器 - 负责任务理解、分解、调度
    作为系统的主入口，调用 qwen-doc 作为主模型
    """

    SYSTEM_PROMPT = """你是一个智能文档处理助手。你的职责是：
1. 理解用户需求
2. 将复杂任务分解为简单步骤
3. 选择合适的工具和模型
4. 协调多模型协作

可用功能：
- summarize: 文档摘要
- polish: 文字润色
- table: 表格处理
- format_convert: 格式转换
- batch_process: 批量处理
- sensitive_check: 敏感信息检测
- ocr: 图文识别
- compare: 对比分析
- reasoning: 复杂推理

请以JSON格式返回任务计划：
{
    "task_type": "主任务类型",
    "sub_tasks": [
        {"step": 1, "action": "动作", "model": "使用模型", "params": {}}
    ],
    "summary": "一句话任务描述"
}"""

    def __init__(self):
        self.client = OllamaClient(MODEL_DOC)  # qwen-doc 作为主模型
        self.router = ModelRouter()

    def parse_task(self, user_input: str) -> Dict:
        """
        理解用户输入，分解任务
        返回任务计划字典
        """
        prompt = f"""{self.SYSTEM_PROMPT}

用户输入：{user_input}

请分析并返回任务计划（仅返回JSON）：
"""
        response = self.client.generate(prompt, num_predict=500)
        return self._parse_json_response(response)

    def _parse_json_response(self, response: str) -> Dict:
        """解析JSON响应"""
        import json
        import re

        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 返回默认计划
        return {
            "task_type": "unknown",
            "sub_tasks": [{"step": 1, "action": "summarize", "model": MODEL_DOC, "params": {}}],
            "summary": response[:100]
        }

    def execute_task(self, user_input: str) -> Dict[str, Any]:
        """
        执行任务的完整流程
        1. 解析任务
        2. 执行子任务
        3. 汇总结果
        """
        # 1. 解析任务
        plan = self.parse_task(user_input)

        # 2. 执行子任务
        results = []
        for sub_task in plan.get("sub_tasks", []):
            step = sub_task.get("step")
            action = sub_task.get("action")
            model = sub_task.get("model", MODEL_DOC)
            params = sub_task.get("params", {})

            try:
                result = self._execute_single_action(action, model, params)
                results.append({
                    "step": step,
                    "action": action,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                results.append({
                    "step": step,
                    "action": action,
                    "status": "failed",
                    "error": str(e)
                })

        # 3. 汇总结果
        return {
            "plan": plan,
            "results": results,
            "success_count": sum(1 for r in results if r["status"] == "success"),
            "failed_count": sum(1 for r in results if r["status"] == "failed")
        }

    def _execute_single_action(self, action: str, model: str, params: Dict) -> str:
        """执行单个动作"""
        prompt = params.get("prompt", "")
        client = OllamaClient(model)
        return client.generate(prompt)


class OCRProcessor:
    """OCR 处理器 — Windows 环境下降级处理"""

    def __init__(self):
        self.ocr_binary = OCR_BINARY
        self.pdfocr_script = PDFOCR_SCRIPT
        self.validator = PathValidator()

    def is_available(self) -> bool:
        if IS_WINDOWS:
            return False
        return self.ocr_binary.exists()

    def _not_available_message(self) -> str:
        if IS_WINDOWS:
            return (
                "[OCR不可用] Windows 环境不支持此功能。\n"
                "请确保 PDF/图片文档已包含可提取的文本层。"
            )
        return "[OCR不可用] 请确保 ocrtext 在 ~/ollama-doc-models/"

    def ocr_image(self, image_path: str) -> str:
        """对图片进行 OCR（带路径验证）"""
        if not self.is_available():
            return self._not_available_message()

        try:
            # 验证路径
            validated_path = self.validator.validate_path(image_path, "read")

            result = subprocess.run(
                [str(self.ocr_binary), str(validated_path)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )
            return result.stdout

        except PathValidationError as e:
            return f"[路径验证失败] {str(e)}"
        except subprocess.CalledProcessError as e:
            return f"[OCR错误] {e.stderr}"
        except Exception as e:
            return f"[OCR异常] {str(e)}"

    def pdf_to_text(self, pdf_path: str, dpi: int = 300) -> str:
        """PDF 转文本（带路径验证）"""
        if not self.pdfocr_script.exists():
            return "[PDF OCR不可用] 请确保 pdfocr.sh 在 ~/ollama-doc-models/"

        try:
            # 验证路径
            validated_path = self.validator.validate_path(pdf_path, "read")

            result = subprocess.run(
                ["/bin/bash", str(self.pdfocr_script), str(validated_path), str(dpi)],
                capture_output=True,
                text=True,
                timeout=300,
                check=True
            )
            return result.stdout

        except PathValidationError as e:
            return f"[路径验证失败] {str(e)}"
        except subprocess.CalledProcessError as e:
            return f"[PDF OCR错误] {e.stderr}"
        except Exception as e:
            return f"[PDF OCR异常] {str(e)}"


def retry(max_retries=3, delay=1):
    def decorator(func):
        from functools import wraps
        import time
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator
