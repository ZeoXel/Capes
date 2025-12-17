"""
OpenAI Adapter - Adapter for OpenAI models.

Supports tool calling according to OpenAI API specification:
- tools: array of tool definitions
- tool_choice: "none" | "auto" | {"type": "function", "function": {"name": "xxx"}}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from cape.adapters.base import AdapterConfig, AdapterResponse, BaseAdapter

if TYPE_CHECKING:
    from cape.core.models import Cape
    from cape.runtime.context import ExecutionContext

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """
    Adapter for OpenAI models (GPT-4, GPT-3.5, etc.).

    Supports:
    - Chat completions
    - Function/Tool calling (OpenAI tools format)

    Tool format:
        {
            "type": "function",
            "function": {
                "name": "function_name",
                "description": "Function description",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }

    Usage:
        adapter = OpenAIAdapter(config=AdapterConfig(model_name="gpt-4-turbo"))
        response = await adapter.execute(prompt, context, tools=tools)
    """

    # Cost per 1K tokens (approximate)
    COSTS = {
        # GPT models
        "gpt-5": {"input": 0.02, "output": 0.06},
        "gpt-4.1": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        # Gemini models
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006},
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
        # Claude models
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    }

    def __init__(self, config: Optional[AdapterConfig] = None, client: Any = None):
        super().__init__(config)
        self._client = client

        if not config:
            self.config = AdapterConfig(model_name="gemini-2.5-flash")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI()
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    async def execute(
        self,
        prompt: str,
        context: "ExecutionContext",
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AdapterResponse:
        """
        Execute with OpenAI API.

        Args:
            prompt: User prompt
            context: Execution context
            tools: List of tool definitions in OpenAI format

        Returns:
            AdapterResponse with content and tool_calls
        """
        messages = [
            {"role": "system", "content": self.config.system_prompt or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]

        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        # Add tools if provided (按照 API 规范格式)
        if tools and self.config.tools_enabled:
            # Ensure tools are in correct format
            formatted_tools = self._format_tools_for_api(tools)
            if formatted_tools:
                kwargs["tools"] = formatted_tools
                kwargs["tool_choice"] = self._get_tool_choice()

        try:
            response = await self.client.chat.completions.create(**kwargs)

            # Extract content
            message = response.choices[0].message
            content = message.content or ""

            # Extract tool calls
            tool_calls = []
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    tool_call = {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    tool_calls.append(tool_call)

            # Calculate tokens and cost
            usage = response.usage
            total_tokens = usage.total_tokens if usage else 0
            cost = self.estimate_cost(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )

            return AdapterResponse(
                content=content,
                tokens=total_tokens,
                cost=cost,
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _format_tools_for_api(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format tools to OpenAI API specification.

        Expected output format:
        {
            "type": "function",
            "function": {
                "name": "function_name",
                "description": "description",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
        """
        formatted = []
        for tool in tools:
            # Already in correct format
            if tool.get("type") == "function" and "function" in tool:
                formatted.append(tool)
            # Simple format: {"name": "xxx", "description": "xxx"}
            elif "name" in tool:
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", f"Execute {tool['name']}"),
                        "parameters": tool.get("parameters", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                })
        return formatted

    def _get_tool_choice(self) -> Any:
        """Get tool_choice value based on config."""
        choice = self.config.tool_choice
        if choice in ["none", "auto", "required"]:
            return choice
        # Specific function
        if isinstance(choice, str) and choice not in ["none", "auto", "required"]:
            return {
                "type": "function",
                "function": {"name": choice}
            }
        return "auto"

    def build_tools(self, cape: "Cape") -> List[Dict[str, Any]]:
        """Build OpenAI function/tool definitions."""
        tools = []

        for tool_name in cape.execution.tools_allowed:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Execute {tool_name}",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
            tools.append(tool_def)

        return tools

    def estimate_cost(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """Estimate cost based on token usage."""
        model = self.config.model_name
        costs = self.COSTS.get(model, self.COSTS["gpt-3.5-turbo"])

        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return input_cost + output_cost

    @classmethod
    def from_cape_config(cls, cape: "Cape") -> "OpenAIAdapter":
        """Create adapter from Cape's OpenAI adapter config."""
        adapter_config = cape.get_adapter("openai") or {}

        config = AdapterConfig(
            model_name=adapter_config.get("model", "gemini-2.5-flash"),
            temperature=adapter_config.get("temperature", 0.0),
            max_tokens=adapter_config.get("max_tokens", 4096),
            system_prompt=adapter_config.get("system_prompt"),
            tools_enabled=adapter_config.get("tools_enabled", True),
            tool_choice=adapter_config.get("tool_choice", "auto"),
        )

        return cls(config=config)
