"""
Advanced Harness架构 - 弱模型增强模块
基于DSPy/LangGraph/MemGPT最佳实践设计

功能：
1. Self-Correction - 输出自我校验与修正
2. Chain-of-Thought - 推理链增强
3. Memory Management - 上下文记忆管理
4. Tool Fusion - 工具协同调用
5. Reflection - 自我反思机制
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class ReflectionResult(Enum):
    """反思结果"""
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


@dataclass
class QualityGate:
    """质量门禁"""
    name: str
    check_fn: Callable[[str], bool]
    severity: str = "medium"
    auto_fix: bool = False


@dataclass
class HarnessConfig:
    """Harness配置"""
    enable_self_correction: bool = True
    enable_cot: bool = True
    enable_memory: bool = True
    max_retries: int = 3
    quality_gates: List[QualityGate] = field(default_factory=list)


class AdvancedHarness:
    """
    高级Harness - 弱模型增强

    核心思想：
    - 不是让模型做对所有事，而是让模型能够发现并修正错误
    - 通过外部校验机制弥补模型能力不足
    - 合理的上下文管理让有限上下文发挥最大价值
    """

    def __init__(self, config: HarnessConfig = None):
        self.config = config or HarnessConfig()
        self._memory: List[Dict] = []
        self._correction_history: List[Dict] = []

    def execute_with_harness(
        self,
        task: str,
        llm_call: Callable[[str], str],
        context: str = ""
    ) -> Dict[str, Any]:
        """
        使用Harness执行任务

        Args:
            task: 任务描述
            llm_call: LLM调用函数
            context: 上下文

        Returns:
            执行结果和元数据
        """
        result = {
            "task": task,
            "initial_output": None,
            "reflection_output": None,
            "final_output": None,
            "corrections": [],
            "reflections": [],
            "success": False
        }

        # Step 1: 构建增强Prompt
        enhanced_prompt = self._build_enhanced_prompt(task, context)

        # Step 2: 初始生成
        try:
            initial_output = llm_call(enhanced_prompt)
            result["initial_output"] = initial_output
        except Exception as e:
            result["error"] = str(e)
            return result

        # Step 3: 自我反思（如果启用）
        if self.config.enable_self_correction:
            reflection = self._reflect(initial_output, task, context)
            result["reflections"].append(reflection)

            if reflection["result"] == ReflectionResult.NEEDS_REVISION.value:
                # 需要修正
                revised_output = self._correct(
                    initial_output,
                    reflection["feedback"],
                    llm_call,
                    task
                )
                result["corrections"].append({
                    "original": initial_output,
                    "revised": revised_output,
                    "feedback": reflection["feedback"]
                })
                result["reflection_output"] = revised_output
                result["final_output"] = revised_output
            else:
                result["final_output"] = initial_output
        else:
            result["final_output"] = initial_output

        # Step 4: 质量门禁检查
        if self.config.quality_gates:
            gate_results = self._run_quality_gates(result["final_output"])
            result["gate_results"] = gate_results
            result["success"] = all(g["passed"] for g in gate_results)
        else:
            result["success"] = True

        # Step 5: 更新记忆
        if self.config.enable_memory:
            self._update_memory(task, result["final_output"], result["success"])

        return result

    def _build_enhanced_prompt(self, task: str, context: str) -> str:
        """构建增强Prompt"""
        parts = []

        # 添加CoT指令（如果启用）
        if self.config.enable_cot:
            cot_instruction = """
[推理增强]
在回答之前，请先思考：
1. 这个任务的核心要求是什么？
2. 我需要调用哪些知识/工具？
3. 我的回答是否满足要求？
请先思考再回答。
"""
            parts.append(cot_instruction)

        # 添加任务
        parts.append(f"[任务]\n{task}")

        # 添加上下文
        if context:
            # 如果有记忆，添加相关上下文
            relevant_memory = self._get_relevant_memory(task)
            if relevant_memory:
                parts.append(f"[相关记忆]\n{relevant_memory}")
            parts.append(f"[上下文]\n{context}")

        # 添加输出格式要求
        parts.append("""
[输出要求]
- 回答要准确、完整
- 如有不确定，明确说明
- 结构化输出（使用编号、列表等）
""")

        return "\n\n".join(parts)

    def _reflect(self, output: str, task: str, context: str) -> Dict:
        """
        自我反思 - 检查输出质量

        Returns:
            反思结果和反馈
        """
        reflection_prompt = f"""你是质量审核员。请检查以下输出的质量：

[原始任务]
{task}

[上下文]
{context}

[待审核输出]
{output}

请检查：
1. 输出是否回答了任务要求？
2. 是否有事实错误或逻辑问题？
3. 是否有遗漏的重要信息？
4. 格式是否规范？

请用JSON格式回复：
{{"result": "approved/needs_revision/rejected", "feedback": "具体反馈", "confidence": 0.0-1.0}}
"""

        # 注意：这里应该调用LLM，但为了避免循环调用，我们使用规则判断
        # 实际使用时应该调用LLM进行反思

        # 简化版规则判断
        feedback_parts = []

        # 检查长度
        if len(output) < 50:
            feedback_parts.append("输出过短，可能未完整回答")
        elif len(output) > 10000:
            feedback_parts.append("输出过长，可能过于冗余")

        # 检查是否为空
        if not output or output.strip() == "":
            feedback_parts.append("输出为空")

        # 检查是否有"不确定"等否定词
        uncertain_words = ["不知道", "不清楚", "无法确定", "可能"]
        if any(word in output for word in uncertain_words):
            feedback_parts.append("输出包含不确定表述")

        if feedback_parts:
            return {
                "result": ReflectionResult.NEEDS_REVISION.value,
                "feedback": "; ".join(feedback_parts),
                "confidence": 0.7
            }
        else:
            return {
                "result": ReflectionResult.APPROVED.value,
                "feedback": "输出质量良好",
                "confidence": 0.9
            }

    def _correct(
        self,
        output: str,
        feedback: str,
        llm_call: Callable[[str], str],
        task: str
    ) -> str:
        """
        根据反馈修正输出

        Args:
            output: 原始输出
            feedback: 反思反馈
            llm_call: LLM调用
            task: 原始任务

        Returns:
            修正后的输出
        """
        correction_prompt = f"""请根据反馈修正以下输出：

[原始任务]
{task}

[原始输出]
{output}

[审核反馈]
{feedback}

请修正输出中的问题，生成改进版本。
直接输出修正后的内容，不要解释。
"""

        try:
            corrected = llm_call(correction_prompt)
            return corrected
        except Exception as e:
            # 修正失败时返回原始输出
            return output

    def _run_quality_gates(self, output: str) -> List[Dict]:
        """运行质量门禁"""
        results = []

        for gate in self.config.quality_gates:
            try:
                passed = gate.check_fn(output)
                results.append({
                    "name": gate.name,
                    "passed": passed,
                    "severity": gate.severity
                })

                # 如果启用自动修复且未通过
                if not passed and gate.auto_fix:
                    # 触发自动修复逻辑
                    pass

            except Exception as e:
                results.append({
                    "name": gate.name,
                    "passed": False,
                    "error": str(e),
                    "severity": gate.severity
                })

        return results

    def _get_relevant_memory(self, task: str, max_chars: int = 2000) -> str:
        """获取相关记忆"""
        if not self._memory:
            return ""

        # 简单关键词匹配
        task_words = set(re.findall(r'\w+', task.lower()))

        scored_memory = []
        for mem in self._memory:
            mem_words = set(re.findall(r'\w+', mem.get("task", "").lower()))
            # 计算重叠度
            overlap = len(task_words & mem_words)
            if overlap > 0:
                scored_memory.append((overlap, mem))

        # 按相关度排序
        scored_memory.sort(key=lambda x: x[0], reverse=True)

        # 构建相关记忆文本
        result = []
        total_chars = 0
        for _, mem in scored_memory[:3]:
            mem_text = f"- {mem['task']}: {mem['output'][:200]}"
            if total_chars + len(mem_text) > max_chars:
                break
            result.append(mem_text)
            total_chars += len(mem_text)

        return "\n".join(result) if result else ""

    def _update_memory(self, task: str, output: str, success: bool):
        """更新记忆"""
        self._memory.append({
            "task": task,
            "output": output,
            "success": success,
            "timestamp": None  # 实际使用时应记录时间戳
        })

        # 保持记忆在合理范围
        if len(self._memory) > 100:
            self._memory = self._memory[-100:]

    def get_correction_history(self) -> List[Dict]:
        """获取修正历史"""
        return self._correction_history


class ChainOfThought:
    """
    推理链增强 - 引导模型进行结构化推理

    使用方式：
    cot = ChainOfThought()
    result = cot.think("分析这个问题", llm_call)
    """

    def think(
        self,
        problem: str,
        llm_call: Callable[[str], str],
        mode: str = "standard"
    ) -> Dict[str, Any]:
        """
        执行推理

        Args:
            problem: 问题描述
            llm_call: LLM调用
            mode: 推理模式 (standard/detailed/step_by_step)

        Returns:
            推理结果和过程
        """
        if mode == "standard":
            prompt = self._standard_prompt(problem)
        elif mode == "detailed":
            prompt = self._detailed_prompt(problem)
        elif mode == "step_by_step":
            prompt = self._step_by_step_prompt(problem)
        else:
            prompt = self._standard_prompt(problem)

        try:
            result = llm_call(prompt)
            return {
                "problem": problem,
                "mode": mode,
                "result": result,
                "success": True
            }
        except Exception as e:
            return {
                "problem": problem,
                "mode": mode,
                "error": str(e),
                "success": False
            }

    def _standard_prompt(self, problem: str) -> str:
        return f"""请分析并回答以下问题：

问题：{problem}

在回答之前，先简要说明你的推理思路。"""

    def _detailed_prompt(self, problem: str) -> str:
        return f"""请详细分析以下问题：

问题：{problem}

请按以下步骤分析：
1. 理解问题的核心要求
2. 识别关键信息和条件
3. 制定解题思路
4. 执行分析
5. 给出结论

请严格按照以上步骤进行推理。"""

    def _step_by_step_prompt(self, problem: str) -> str:
        return f"""让我们一步步分析：

问题：{problem}

步骤1：...
步骤2：...
步骤3：...

请完成这个推理过程。"""


class ToolFusion:
    """
    工具融合 - 协调多个工具的调用

    使用方式：
    fusion = ToolFusion()
    fusion.register("search", search_function)
    fusion.register("calculate", calc_function)
    result = fusion.execute("复合任务", llm_router)
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, str] = {}

    def register(self, name: str, func: Callable, description: str = ""):
        """注册工具"""
        self.tools[name] = func
        self.tool_descriptions[name] = description or f"Tool: {name}"

    def execute(
        self,
        task: str,
        llm_router: Callable[[str, List[str]], str]
    ) -> Dict[str, Any]:
        """
        执行融合任务

        Args:
            task: 任务描述
            llm_router: LLM路由函数（决定调用哪个工具）

        Returns:
            执行结果
        """
        # 1. LLM决定使用哪些工具
        tool_names = list(self.tools.keys())
        decision_prompt = f"""任务：{task}

可用工具：{', '.join(tool_names)}

请决定使用哪些工具（可多选）来完成任务。
只用JSON格式回答：{{"tools": ["tool1", "tool2"], "reasoning": "原因"}}
"""

        try:
            decision = llm_router(decision_prompt, [])
            # 解析decision（实际应该让LLM输出JSON）
            decision_data = json.loads(decision) if decision.startswith("{") else {"tools": [], "reasoning": ""}
        except:
            decision_data = {"tools": [], "reasoning": ""}

        # 2. 执行工具
        results = {}
        for tool_name in decision_data.get("tools", []):
            if tool_name in self.tools:
                try:
                    results[tool_name] = self.tools[tool_name]()
                except Exception as e:
                    results[tool_name] = {"error": str(e)}

        # 3. 整合结果
        return {
            "task": task,
            "tools_used": list(results.keys()),
            "results": results,
            "reasoning": decision_data.get("reasoning", "")
        }


def quick_demo():
    """快速演示"""
    print("\n" + "="*50)
    print("Advanced Harness - 演示")
    print("="*50 + "\n")

    # 模拟LLM调用
    def mock_llm(prompt):
        return f"这是AI的模拟回复，任务：{prompt[:50]}..."

    # 创建Harness
    harness = AdvancedHarness(HarnessConfig(
        enable_self_correction=True,
        enable_cot=True,
        enable_memory=True
    ))

    # 添加质量门禁
    harness.config.quality_gates.append(QualityGate(
        name="长度检查",
        check_fn=lambda x: 50 < len(x) < 5000,
        severity="medium"
    ))

    # 执行任务
    result = harness.execute_with_harness(
        task="总结这份技术文档的要点",
        llm_call=mock_llm,
        context="这是一份关于AI技术的文档..."
    )

    print("执行结果:")
    print(f"  成功: {result['success']}")
    print(f"  反思次数: {len(result['reflections'])}")
    print(f"  修正次数: {len(result['corrections'])}")

    # CoT演示
    print("\n推理链演示:")
    cot = ChainOfThought()
    cot_result = cot.think("为什么天空是蓝色的？", mock_llm, mode="detailed")
    print(f"  结果: {cot_result['result'][:50]}...")

    print("\n" + "="*50)
    print("演示完成")
    print("="*50 + "\n")


if __name__ == "__main__":
    quick_demo()
