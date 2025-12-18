"""
LangChain Integration - Use Cape with LangChain agents.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from cape.registry.registry import CapeRegistry
from cape.runtime.runtime import CapeRuntime

logger = logging.getLogger(__name__)


class CapeToolInput(BaseModel):
    """Input schema for Cape tool."""
    query: str = Field(description="The user's request to process")


class CapeTool:
    """
    LangChain-compatible tool for Cape execution.

    Can be used with any LangChain agent.
    """

    def __init__(
        self,
        cape_id: str,
        runtime: CapeRuntime,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.cape_id = cape_id
        self.runtime = runtime

        cape = runtime.registry.get(cape_id) if runtime.registry else None

        self.name = name or cape_id
        self.description = description or (cape.description if cape else f"Execute {cape_id}")
        self.args_schema = CapeToolInput

    def _get_input_field(self) -> str:
        """Get the primary input field name from Cape schema."""
        cape = self.runtime.registry.get(self.cape_id) if self.runtime.registry else None
        if cape and cape.interface.input_schema.required:
            return cape.interface.input_schema.required[0]
        return "input"

    def _run(self, query: str) -> str:
        """Execute synchronously."""
        field_name = self._get_input_field()
        result = self.runtime.execute_sync(
            cape_id=self.cape_id,
            inputs={field_name: query},
        )

        if result.success:
            return str(result.output)
        else:
            return f"Error: {result.error}"

    async def _arun(self, query: str) -> str:
        """Execute asynchronously."""
        field_name = self._get_input_field()
        result = await self.runtime.execute(
            cape_id=self.cape_id,
            inputs={field_name: query},
        )

        if result.success:
            return str(result.output)
        else:
            return f"Error: {result.error}"


class CapeRouterTool:
    """
    LangChain tool that automatically routes to best Cape.
    """

    name: str = "cape_router"
    description: str = """Route requests to specialized capabilities.
Use this when you need to:
- Process documents (PDF, DOCX, etc.)
- Analyze code
- Transform data
- Execute specialized tasks

Input should be the user's complete request.
"""
    args_schema: Type[BaseModel] = CapeToolInput

    def __init__(self, registry: CapeRegistry, runtime: CapeRuntime):
        self.registry = registry
        self.runtime = runtime

    def _get_input_field(self, cape) -> str:
        """Get the primary input field name from Cape schema."""
        if cape and cape.interface.input_schema.required:
            return cape.interface.input_schema.required[0]
        return "input"

    def _run(self, query: str) -> str:
        """Route and execute synchronously."""
        # Find best match
        match = self.registry.match_best(query, threshold=0.3)

        if not match:
            return f"No suitable capability found for: {query}"

        # Get correct input field name
        field_name = self._get_input_field(match)

        # Execute
        result = self.runtime.execute_sync(
            cape_id=match.id,
            inputs={field_name: query},
        )

        if result.success:
            return f"[{match.id}] {result.output}"
        else:
            return f"[{match.id}] Error: {result.error}"

    async def _arun(self, query: str) -> str:
        """Route and execute asynchronously."""
        match = self.registry.match_best(query, threshold=0.3)

        if not match:
            return f"No suitable capability found for: {query}"

        # Get correct input field name
        field_name = self._get_input_field(match)

        result = await self.runtime.execute(
            cape_id=match.id,
            inputs={field_name: query},
        )

        if result.success:
            return f"[{match.id}] {result.output}"
        else:
            return f"[{match.id}] Error: {result.error}"


class CapeToolkit:
    """
    Toolkit for creating LangChain tools from Capes.

    Usage:
        toolkit = CapeToolkit(capes_dir="./capes")
        tools = toolkit.get_tools()

        # Use with agent
        agent = create_react_agent(llm, tools, prompt)
    """

    def __init__(
        self,
        capes_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        include_router: bool = True,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ):
        self.registry = CapeRegistry(
            capes_dir=capes_dir,
            skills_dir=skills_dir,
        )

        # Create adapter factory for LLM execution
        adapter_factory = self._create_adapter_factory(openai_api_key, openai_base_url)

        self.runtime = CapeRuntime(
            registry=self.registry,
            adapter_factory=adapter_factory,
        )
        self.include_router = include_router

        # Register built-in tools
        self._register_builtin_tools()

    def _create_adapter_factory(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Create adapter factory for LLM execution."""
        import os

        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        base_url = base_url or os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            return None  # No adapter factory if no API key

        def factory(model_name: str):
            """Create adapter for model."""
            from cape.adapters.openai import OpenAIAdapter
            from cape.adapters.base import AdapterConfig

            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                return None

            config = AdapterConfig(
                model_name="gpt-4-turbo",
                temperature=0.0,
                max_tokens=4096,
            )
            return OpenAIAdapter(config=config, client=client)

        return factory

    def _register_builtin_tools(self):
        """Register built-in tools for cape execution."""
        try:
            from cape.tools.search import search_web, search_news, search
            self.runtime.register_tool("search", search)
            self.runtime.register_tool("web_search", search_web)
            self.runtime.register_tool("news_search", search_news)
            logger.info("Registered built-in tools: search, web_search, news_search")
        except ImportError as e:
            logger.warning(f"Could not import built-in tools: {e}")

    def get_tools(self) -> List[Any]:
        """
        Get LangChain-compatible tools.

        Returns:
            List of tool objects
        """
        tools = []

        # Add router tool
        if self.include_router:
            tools.append(CapeRouterTool(self.registry, self.runtime))

        # Add individual Cape tools
        for cape in self.registry.all():
            tools.append(CapeTool(
                cape_id=cape.id,
                runtime=self.runtime,
                name=f"cape_{cape.id.replace('-', '_')}",
                description=cape.description,
            ))

        return tools

    def get_router_tool(self) -> CapeRouterTool:
        """Get just the router tool."""
        return CapeRouterTool(self.registry, self.runtime)


def create_langchain_agent(
    capes_dir: Optional[Path] = None,
    skills_dir: Optional[Path] = None,
    llm: Optional[Any] = None,
    agent_type: str = "react",
) -> Any:
    """
    Create a LangChain agent with Cape tools.

    Args:
        capes_dir: Directory with Cape definitions
        skills_dir: Directory with Skills to import
        llm: LangChain LLM (defaults to ChatOpenAI)
        agent_type: Type of agent to create ("react" or "tool-calling")

    Returns:
        LangGraph CompiledGraph agent
    """
    try:
        from langgraph.prebuilt import create_react_agent
        from langchain_core.tools import StructuredTool
    except ImportError:
        raise ImportError("langgraph required. Install with: pip install langgraph langchain-openai")

    # Default LLM
    if llm is None:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)

    # Create toolkit
    toolkit = CapeToolkit(capes_dir=capes_dir, skills_dir=skills_dir)

    # Convert to LangChain tools
    lc_tools = []
    for tool in toolkit.get_tools():
        lc_tool = StructuredTool.from_function(
            func=tool._run,
            coroutine=tool._arun,
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
        )
        lc_tools.append(lc_tool)

    # Build system prompt
    capabilities = "\n".join(
        f"- **{c.id}**: {c.description[:80]}..."
        for c in toolkit.registry.all()
    )

    system_prompt = f"""你是一个智能助手，能够使用多种专业能力来帮助用户。

## 核心原则
1. **语言一致性**：始终使用用户的语言回复
2. **直接回答**：简单问候或闲聊直接回复，无需工具
3. **基于结果回答**：使用工具后，必须基于返回结果生成人类友好的回答

## 可用能力
{capabilities}

## 工具使用指南

### cape_web_search - 网页搜索（主要工具）
用于：天气、新闻、实时信息、事实查询
- 天气："杭州天气" → query="杭州天气"
- 新闻："AI最新进展" → query="AI 最新进展 2024"
- 事实："特斯拉股价" → query="特斯拉股价"

## 关键：处理工具返回结果

工具会返回 JSON 格式数据，包含：
- `results`: 搜索结果列表（title, url, snippet）
- `answer`: AI 生成的摘要（如有）
- `summary`: 结果概要

**你必须：**
1. 解析工具返回的 JSON 数据
2. 提取关键信息（answer 或 results 中的内容）
3. 用自然语言组织成人类友好的回答
4. 不要直接输出原始 JSON

**示例：**
工具返回: {{"answer": "杭州今天18°C，晴", "results": [...]}}
你的回答: "杭州今天天气晴朗，气温约18°C，适合外出。"

## 禁止行为
- 不要说"无法获取信息"当工具已返回结果时
- 不要输出原始 JSON 给用户
- 不要在有结果时说"搜索失败"
"""

    # Create ReAct agent using langgraph
    agent = create_react_agent(
        model=llm,
        tools=lc_tools,
        prompt=system_prompt,
    )

    return agent
