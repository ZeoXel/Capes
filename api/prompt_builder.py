"""
Prompt Builder - 上下文裁剪与拼装器

核心原则：
- Prompt Builder ≠ Prompt Template
- 而是「上下文裁剪与拼装器」
- 不同模型 = 不同投喂策略，State 不变

参考: docs/memory.md
"""

from typing import Optional
from api.state import ConversationState


class PromptBuilder:
    """上下文感知的 Prompt 构建器"""

    # 模型策略配置
    MODEL_STRATEGIES = {
        "claude": {
            "summaries": 3,      # 使用多条摘要
            "recent_turns": 0,   # 不使用最近轮次
            "include_tasks": True,
        },
        "gpt": {
            "summaries": 1,      # 单条摘要
            "recent_turns": 5,   # 最近 5 轮
            "include_tasks": True,
        },
        "gemini": {
            "summaries": 2,      # 中等摘要
            "recent_turns": 3,   # 最近 3 轮
            "include_tasks": True,
        },
        "default": {
            "summaries": 1,
            "recent_turns": 3,
            "include_tasks": True,
        }
    }

    @staticmethod
    def build(state: ConversationState, user_input: str, model: str) -> str:
        """
        根据模型构建上下文增强的 Prompt

        Args:
            state: 对话状态
            user_input: 用户当前输入
            model: 模型名称（如 "gpt-4-turbo", "claude-3-5-sonnet"）

        Returns:
            构建好的 prompt 字符串
        """
        # 检测模型类型
        model_lower = model.lower()
        if "claude" in model_lower:
            return PromptBuilder._build_claude(state, user_input)
        elif "gpt" in model_lower:
            return PromptBuilder._build_gpt(state, user_input)
        elif "gemini" in model_lower:
            return PromptBuilder._build_gemini(state, user_input)
        else:
            return PromptBuilder._build_default(state, user_input)

    @staticmethod
    def _get_facts_text(state: ConversationState) -> str:
        """格式化事实列表"""
        if not state.facts:
            return "无"
        return "\n".join(f"- {f.key}: {f.value}" for f in state.facts)

    @staticmethod
    def _get_tasks_text(state: ConversationState) -> str:
        """格式化任务列表"""
        active_tasks = state.get_active_tasks()
        if not active_tasks:
            return "无"
        return "\n".join(f"- {t.goal}" for t in active_tasks)

    @staticmethod
    def _get_recent_turns_text(state: ConversationState, n: int) -> str:
        """格式化最近对话"""
        turns = state.get_recent_turns(n)
        if not turns:
            return "无"

        lines = []
        for turn in turns:
            role_label = {
                "user": "用户",
                "assistant": "助手",
                "tool": "工具"
            }.get(turn.role, turn.role)
            lines.append(f"{role_label}: {turn.content[:200]}{'...' if len(turn.content) > 200 else ''}")
        return "\n".join(lines)

    @staticmethod
    def _build_default(state: ConversationState, user_input: str) -> str:
        """默认策略：摘要 + 事实 + 任务"""
        summary = state.get_latest_summary() or "这是新对话的开始。"
        facts = PromptBuilder._get_facts_text(state)
        tasks = PromptBuilder._get_tasks_text(state)

        return f"""【对话背景摘要】
{summary}

【已知事实】
{facts}

【当前任务】
{tasks}

【用户输入】
{user_input}"""

    @staticmethod
    def _build_gpt(state: ConversationState, user_input: str) -> str:
        """
        GPT 策略：摘要 + 最近 3-5 轮 + 事实
        GPT 对最近对话有更好的短期记忆
        """
        summary = state.get_latest_summary() or "这是新对话的开始。"
        facts = PromptBuilder._get_facts_text(state)
        recent = PromptBuilder._get_recent_turns_text(state, 5)

        # 如果没有摘要但有最近对话，只用最近对话
        if summary == "这是新对话的开始。" and recent != "无":
            return f"""【最近对话】
{recent}

【已知事实】
{facts}

【用户输入】
{user_input}"""

        return f"""【对话背景】
{summary}

【最近对话】
{recent}

【已知事实】
{facts}

【用户输入】
{user_input}"""

    @staticmethod
    def _build_claude(state: ConversationState, user_input: str) -> str:
        """
        Claude 策略：多条摘要 + 事实 + 任务
        Claude 对长文本理解更好，可以处理多条摘要
        """
        summaries = state.get_all_summaries(3)
        if summaries:
            all_summaries = "\n\n".join(f"[摘要 {i+1}] {s}" for i, s in enumerate(summaries))
        else:
            all_summaries = "这是新对话的开始。"

        facts = PromptBuilder._get_facts_text(state)
        tasks = PromptBuilder._get_tasks_text(state)

        return f"""【对话历程】
{all_summaries}

【已知事实】
{facts}

【当前目标】
{tasks}

【用户输入】
{user_input}"""

    @staticmethod
    def _build_gemini(state: ConversationState, user_input: str) -> str:
        """
        Gemini 策略：中等摘要 + 少量最近轮次
        平衡策略
        """
        summaries = state.get_all_summaries(2)
        if summaries:
            summary_text = "\n".join(summaries)
        else:
            summary_text = "这是新对话的开始。"

        facts = PromptBuilder._get_facts_text(state)
        recent = PromptBuilder._get_recent_turns_text(state, 3)

        return f"""【对话背景】
{summary_text}

【最近交互】
{recent}

【已知信息】
{facts}

【用户输入】
{user_input}"""

    @staticmethod
    def build_tool_context(state: ConversationState) -> dict:
        """
        构建传递给 Tool 的上下文
        Tool 也应该是 context-aware 的组件
        """
        return {
            "summary": state.get_latest_summary(),
            "facts": {f.key: f.value for f in state.facts},
            "current_task": state.get_active_tasks()[0].goal if state.get_active_tasks() else None,
            "session_id": state.session_id,
        }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算 token 数量（粗略：1 token ≈ 4 字符）"""
        return len(text) // 4

    @staticmethod
    def build_with_limit(
        state: ConversationState,
        user_input: str,
        model: str,
        max_tokens: int = 4000
    ) -> str:
        """
        带 token 限制的 prompt 构建
        如果超过限制，逐步裁剪
        """
        prompt = PromptBuilder.build(state, user_input, model)

        if PromptBuilder.estimate_tokens(prompt) <= max_tokens:
            return prompt

        # 超过限制，使用更简洁的版本
        summary = state.get_latest_summary() or "新对话"
        facts = PromptBuilder._get_facts_text(state)

        simple_prompt = f"""【背景】{summary}

【事实】{facts}

【输入】{user_input}"""

        if PromptBuilder.estimate_tokens(simple_prompt) <= max_tokens:
            return simple_prompt

        # 还是太长，只保留事实和输入
        return f"""【事实】{facts}

【输入】{user_input}"""
