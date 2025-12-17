"""
Claude Adapter - Adapter for Anthropic Claude models.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from cape.adapters.base import AdapterConfig, AdapterResponse, BaseAdapter

if TYPE_CHECKING:
    from cape.core.models import Cape
    from cape.runtime.context import ExecutionContext

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseAdapter):
    """
    Adapter for Anthropic Claude models.

    Supports:
    - Messages API
    - Tool use
    - System prompts

    This adapter can also import Claude Skills and use them as prompts.

    Usage:
        adapter = ClaudeAdapter(config=AdapterConfig(model_name="claude-3-opus-20240229"))
        response = await adapter.execute(prompt, context)
    """

    # Cost per 1K tokens (approximate)
    COSTS = {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    }

    def __init__(self, config: Optional[AdapterConfig] = None, client: Any = None):
        super().__init__(config)
        self._client = client

        if not config:
            self.config = AdapterConfig(model_name="claude-3-sonnet-20240229")

    @property
    def name(self) -> str:
        return "claude"

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic()
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        return self._client

    async def execute(
        self,
        prompt: str,
        context: "ExecutionContext",
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AdapterResponse:
        """Execute with Claude API."""
        kwargs = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add system prompt
        if self.config.system_prompt:
            kwargs["system"] = self.config.system_prompt

        # Add tools if provided
        if tools and self.config.tools_enabled:
            kwargs["tools"] = tools

        try:
            response = await self.client.messages.create(**kwargs)

            # Extract content
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    })

            # Calculate tokens and cost
            usage = response.usage
            total_tokens = usage.input_tokens + usage.output_tokens
            cost = self.estimate_cost(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )

            return AdapterResponse(
                content=content,
                tokens=total_tokens,
                cost=cost,
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def build_tools(self, cape: "Cape") -> List[Dict[str, Any]]:
        """Build Claude tool definitions."""
        tools = []

        for tool_name in cape.execution.tools_allowed:
            tool_def = {
                "name": tool_name,
                "description": f"Execute {tool_name}",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
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
        costs = self.COSTS.get(model, self.COSTS["claude-3-sonnet-20240229"])

        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return input_cost + output_cost

    def apply_skill_prompt(self, skill_body: str):
        """
        Apply a Claude Skill's prompt as system prompt.

        This allows importing Claude Skills and using their
        instructions directly.
        """
        self.config.system_prompt = skill_body

    @classmethod
    def from_cape_config(cls, cape: "Cape") -> "ClaudeAdapter":
        """Create adapter from Cape's Claude adapter config."""
        adapter_config = cape.get_adapter("claude") or {}

        config = AdapterConfig(
            model_name=adapter_config.get("model", "claude-3-sonnet-20240229"),
            temperature=adapter_config.get("temperature", 0.0),
            max_tokens=adapter_config.get("max_tokens", 4096),
            system_prompt=adapter_config.get("system_prompt"),
        )

        return cls(config=config)

    @classmethod
    def from_skill(cls, skill_body: str, model: str = "claude-3-sonnet-20240229") -> "ClaudeAdapter":
        """
        Create adapter from a Claude Skill's body content.

        This preserves the original skill prompt for use with Cape.
        """
        config = AdapterConfig(
            model_name=model,
            system_prompt=skill_body,
        )
        return cls(config=config)
