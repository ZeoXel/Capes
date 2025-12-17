"""
Generic Adapter - Fallback adapter for any LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from cape.adapters.base import AdapterConfig, AdapterResponse, BaseAdapter

if TYPE_CHECKING:
    from cape.core.models import Cape
    from cape.runtime.context import ExecutionContext

logger = logging.getLogger(__name__)


class GenericAdapter(BaseAdapter):
    """
    Generic adapter for any LLM or custom model.

    This adapter works with:
    - LangChain models
    - HuggingFace models
    - Custom inference endpoints
    - Local models (Ollama, etc.)

    Usage:
        # With custom executor
        def my_executor(prompt, **kwargs):
            return {"content": "response", "tokens": 100}

        adapter = GenericAdapter(executor=my_executor)
        response = await adapter.execute(prompt, context)

        # With LangChain
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI()
        adapter = GenericAdapter.from_langchain(llm)
    """

    def __init__(
        self,
        config: Optional[AdapterConfig] = None,
        executor: Optional[Callable] = None,
    ):
        super().__init__(config)
        self._executor = executor

        if not config:
            self.config = AdapterConfig(model_name="generic")

    @property
    def name(self) -> str:
        return "generic"

    async def execute(
        self,
        prompt: str,
        context: "ExecutionContext",
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AdapterResponse:
        """Execute with custom executor."""
        if not self._executor:
            raise ValueError("No executor configured. Set executor in constructor.")

        try:
            # Call executor
            import asyncio
            if asyncio.iscoroutinefunction(self._executor):
                result = await self._executor(prompt, tools=tools, context=context)
            else:
                result = self._executor(prompt, tools=tools, context=context)

            # Handle different result formats
            if isinstance(result, str):
                return AdapterResponse(content=result)
            elif isinstance(result, dict):
                return AdapterResponse(
                    content=result.get("content", ""),
                    tokens=result.get("tokens", 0),
                    cost=result.get("cost", 0.0),
                    tool_calls=result.get("tool_calls", []),
                )
            else:
                # Try to extract content
                if hasattr(result, "content"):
                    return AdapterResponse(content=result.content)
                return AdapterResponse(content=str(result))

        except Exception as e:
            logger.error(f"Generic adapter error: {e}")
            raise

    @classmethod
    def from_langchain(cls, llm: Any) -> "GenericAdapter":
        """
        Create adapter from LangChain LLM.

        Args:
            llm: LangChain BaseLanguageModel instance

        Returns:
            Configured GenericAdapter
        """
        async def executor(prompt: str, **kwargs):
            from langchain.schema import HumanMessage

            response = await llm.ainvoke([HumanMessage(content=prompt)])

            content = response.content if hasattr(response, "content") else str(response)
            tokens = 0

            # Try to get token usage
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("token_usage", {})
                tokens = usage.get("total_tokens", 0)

            return {"content": content, "tokens": tokens}

        return cls(executor=executor)

    @classmethod
    def from_ollama(cls, model: str = "llama2") -> "GenericAdapter":
        """
        Create adapter for Ollama local models.

        Args:
            model: Ollama model name

        Returns:
            Configured GenericAdapter
        """
        import httpx

        async def executor(prompt: str, **kwargs):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=120.0,
                )
                data = response.json()
                return {
                    "content": data.get("response", ""),
                    "tokens": data.get("eval_count", 0),
                }

        config = AdapterConfig(model_name=f"ollama/{model}")
        return cls(config=config, executor=executor)

    @classmethod
    def from_http(
        cls,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> "GenericAdapter":
        """
        Create adapter for HTTP inference endpoint.

        Args:
            endpoint: HTTP endpoint URL
            headers: Optional headers (e.g., auth)

        Returns:
            Configured GenericAdapter
        """
        import httpx

        async def executor(prompt: str, **kwargs):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json={"prompt": prompt, **kwargs},
                    headers=headers or {},
                    timeout=120.0,
                )
                return response.json()

        return cls(executor=executor)
