"""
State Updater - 每轮对话后更新状态

更新流程：
1. 追加 Turn（冷数据）
2. 判断是否需要生成新 Summary（热数据）
3. 抽取 Facts（长期记忆）
4. 更新 Tasks（可选）

参考: docs/memory.md
"""

import re
from typing import Optional, Any
from api.state import ConversationState, Summary, Fact


class StateUpdater:
    """对话状态更新器"""

    # 配置
    SUMMARY_THRESHOLD = 6  # 每 6 轮（3对）生成一次摘要
    SUMMARY_MAX_LENGTH = 150  # 摘要最大长度

    @staticmethod
    async def update_after_turn(
        state: ConversationState,
        user_input: str,
        assistant_response: str,
        cape_id: Optional[str] = None,
        llm_summarizer: Optional[Any] = None
    ) -> ConversationState:
        """
        标准更新流程

        Args:
            state: 当前对话状态
            user_input: 用户输入（原始，非增强版）
            assistant_response: 助手响应
            cape_id: 使用的 Cape ID
            llm_summarizer: LLM 实例用于生成摘要（可选）

        Returns:
            更新后的状态
        """
        # 1. 追加 Turns（保存原始对话，不保存增强后的 prompt）
        state.add_turn("user", user_input)
        state.add_turn("assistant", assistant_response, cape_id)

        # 2. 判断是否需要生成新 Summary
        unsummarized_count = state.get_unsummarized_turn_count()
        if unsummarized_count >= StateUpdater.SUMMARY_THRESHOLD:
            if llm_summarizer:
                await StateUpdater._generate_summary_with_llm(state, llm_summarizer)
            else:
                StateUpdater._generate_simple_summary(state)

        # 3. 抽取 Facts（简单规则 + 可选 LLM）
        StateUpdater._extract_facts_simple(state, user_input, assistant_response)

        return state

    @staticmethod
    def update_sync(
        state: ConversationState,
        user_input: str,
        assistant_response: str,
        cape_id: Optional[str] = None
    ) -> ConversationState:
        """同步版本的更新（不使用 LLM 摘要）"""
        # 1. 追加 Turns
        state.add_turn("user", user_input)
        state.add_turn("assistant", assistant_response, cape_id)

        # 2. 简单摘要
        if state.get_unsummarized_turn_count() >= StateUpdater.SUMMARY_THRESHOLD:
            StateUpdater._generate_simple_summary(state)

        # 3. 抽取 Facts
        StateUpdater._extract_facts_simple(state, user_input, assistant_response)

        return state

    @staticmethod
    async def _generate_summary_with_llm(
        state: ConversationState,
        llm: Any
    ):
        """使用 LLM 生成高质量摘要"""
        # 获取需要摘要的轮次
        start_idx = len(state.turns) - StateUpdater.SUMMARY_THRESHOLD
        recent_turns = state.turns[start_idx:]

        # 构建摘要请求
        turns_text = "\n".join(
            f"{t.role}: {t.content[:300]}{'...' if len(t.content) > 300 else ''}"
            for t in recent_turns
        )

        prompt = f"""请将以下对话压缩为一条简洁的上下文摘要（50-100字），保留关键信息：

{turns_text}

摘要："""

        try:
            # 调用 LLM
            response = await llm.ainvoke(prompt)
            summary_content = response.content if hasattr(response, 'content') else str(response)

            # 清理和截断
            summary_content = summary_content.strip()
            if len(summary_content) > StateUpdater.SUMMARY_MAX_LENGTH:
                summary_content = summary_content[:StateUpdater.SUMMARY_MAX_LENGTH] + "..."

            # 添加摘要
            state.add_summary(
                content=summary_content,
                covers_turns=list(range(start_idx, len(state.turns)))
            )
        except Exception as e:
            # LLM 失败时使用简单摘要
            print(f"[StateUpdater] LLM summary failed: {e}, using simple summary")
            StateUpdater._generate_simple_summary(state)

    @staticmethod
    def _generate_simple_summary(state: ConversationState):
        """生成简单摘要（不使用 LLM）"""
        start_idx = len(state.turns) - StateUpdater.SUMMARY_THRESHOLD
        recent_turns = state.turns[start_idx:]

        # 提取用户问题关键词
        user_queries = [t.content[:50] for t in recent_turns if t.role == "user"]
        topics = ", ".join(user_queries) if user_queries else "多个话题"

        # 构建简单摘要
        summary = f"用户询问了：{topics}"

        # 如果有 cape 使用，记录
        capes_used = set(t.cape_id for t in recent_turns if t.cape_id)
        if capes_used:
            summary += f"。使用了能力：{', '.join(capes_used)}"

        state.add_summary(
            content=summary[:StateUpdater.SUMMARY_MAX_LENGTH],
            covers_turns=list(range(start_idx, len(state.turns)))
        )

    @staticmethod
    def _extract_facts_simple(
        state: ConversationState,
        user_input: str,
        response: str
    ):
        """
        简单的事实抽取（基于规则）

        抽取模式：
        - "我是/我叫 XXX" → user_name
        - "我在做 XXX" → user_project
        - "我使用 XXX" → user_tech_stack

        注意：只从用户输入抽取事实，避免从问句中误抽取
        """
        # 检测是否是问句（跳过问句）
        if "?" in user_input or "？" in user_input or "吗" in user_input or "什么" in user_input:
            return

        # 抽取用户名（只从用户输入抽取）
        name_patterns = [
            r"我(?:是|叫|的名字是)\s*([^\s,，。！？\?]+)",
            r"(?:我是|我叫)\s*([^\s,，。！？\?]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_input)
            if match:
                name = match.group(1).strip()
                # 排除无意义的匹配
                if len(name) >= 2 and len(name) <= 10 and name not in ["你", "我", "他", "她", "它", "谁", "什么"]:
                    state.add_fact("user_name", name, source="user_stated")
                    break

        # 抽取项目信息（从用户输入）
        project_patterns = [
            r"(?:我在做|我正在开发|我的项目是)\s*(.+?)(?:项目|系统|平台|应用)?[,，。！？]",
            r"做一个\s*(.+?)(?:项目|系统|平台|应用)",
        ]
        for pattern in project_patterns:
            match = re.search(pattern, user_input)
            if match:
                project = match.group(1).strip()
                if len(project) <= 50:
                    state.add_fact("user_project", project, source="extracted")
                    break

        # 抽取技术栈（从用户输入）
        tech_patterns = [
            r"(?:使用|用的是|技术栈是)\s*([A-Za-z0-9\s\+\,\.]+)",
        ]
        for pattern in tech_patterns:
            match = re.search(pattern, user_input)
            if match:
                tech = match.group(1).strip()
                if len(tech) <= 100:
                    state.add_fact("tech_stack", tech, source="extracted")
                    break

    @staticmethod
    async def extract_facts_with_llm(
        state: ConversationState,
        user_input: str,
        response: str,
        llm: Any
    ):
        """使用 LLM 进行智能事实抽取（可选增强）"""
        prompt = f"""从以下对话中提取关键事实信息（如果有的话）。
只返回 JSON 格式，无事实则返回空对象 {{}}。

用户: {user_input}
助手: {response}

可能的事实类型：
- user_name: 用户姓名
- user_project: 用户正在做的项目
- user_goal: 用户的目标
- tech_stack: 使用的技术

JSON:"""

        try:
            result = await llm.ainvoke(prompt)
            content = result.content if hasattr(result, 'content') else str(result)

            # 尝试解析 JSON
            import json
            # 提取 JSON 部分
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                facts = json.loads(json_match.group())
                for key, value in facts.items():
                    if value and isinstance(value, str):
                        state.add_fact(key, value, source="llm_extracted")
        except Exception as e:
            print(f"[StateUpdater] LLM fact extraction failed: {e}")

    @staticmethod
    def add_tool_observation(
        state: ConversationState,
        tool_name: str,
        result: str
    ):
        """记录工具调用结果"""
        state.add_tool_turn(tool_name, result[:500])  # 限制长度
