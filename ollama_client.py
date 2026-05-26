import ollama
from typing import Optional, List, Dict, Any
import subprocess
from pathlib import Path
import re
import os
import platform

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
        num_predict: int = 2048
    ) -> str:
        """
        使用Ollama模型生成文本。

        Args:
            prompt: 输入提示词
            system: 系统提示词（可选）
            stream: 是否流式输出
            temperature: 温度参数（默认根据模型自动设置）
            num_predict: 最大生成token数

        Returns:
            生成的文本内容
        """
        if not prompt or not prompt.strip():
            return "[错误] 输入不能为空"

        # 统一温度 0.3 (单 7B 模型，不区分 deepseek/qwen)
        if temperature is None:
            temperature = 0.3

        options = {
            "temperature": temperature,
            "num_predict": num_predict,
        }

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
        return response['response']

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = None
    ) -> str:
        """
        使用Ollama模型进行对话。

        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            system: 系统提示词（可选）
            temperature: 温度参数（默认根据模型自动设置）

        Returns:
            模型回复的文本内容
        """
        if temperature is None:
            temperature = 0.3
                temperature = 0.3

        if system:
            full_messages = [{"role": "system", "content": system}] + messages
        else:
            full_messages = messages

        response = ollama.chat(
            model=self.model,
            messages=full_messages,
            options={"temperature": temperature},
            stream=False
        )
        return response['message']['content']

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

    def list_models(self) -> List[str]:
        try:
            models = ollama.list()
            return [m['name'] for m in models.get('models', [])]
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
    """单模型路由 — 所有任务统一使用 comac (7B)"""

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
