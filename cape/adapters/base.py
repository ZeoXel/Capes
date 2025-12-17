"""
Base Adapter - Abstract base for model adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cape.core.models import Cape
    from cape.runtime.context import ExecutionContext


@dataclass
class AdapterConfig:
    """Configuration for model adapter."""
    model_name: str = "default"
    temperature: float = 0.0
    max_tokens: int = 4096

    # Custom prompts
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None

    # Tool/function configuration
    tools_enabled: bool = True
    tool_choice: str = "auto"  # auto, required, none

    # Additional model-specific settings
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResponse:
    """Response from adapter execution."""
    content: str
    tokens: int = 0
    cost: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Any = None


class BaseAdapter(ABC):
    """
    Base class for model adapters.

    An adapter translates between Cape definitions and model-specific formats.
    Each model (OpenAI, Claude, local, etc.) has different:
    - Prompt formats
    - Tool/function calling conventions
    - Response structures

    The adapter handles these differences so Capes remain model-agnostic.
    """

    def __init__(self, config: Optional[AdapterConfig] = None):
        self.config = config or AdapterConfig()

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name (e.g., 'openai', 'claude')."""
        pass

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        context: "ExecutionContext",
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AdapterResponse:
        """
        Execute prompt with model.

        Args:
            prompt: The prompt to send
            context: Execution context
            tools: Optional tool definitions

        Returns:
            AdapterResponse with content and metadata
        """
        pass

    def build_prompt(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
    ) -> str:
        """
        Build prompt from Cape definition.

        Args:
            cape: Cape to build prompt for
            inputs: User inputs

        Returns:
            Formatted prompt string
        """
        # Get Cape's adapter config if available
        adapter_config = cape.get_adapter(self.name) or {}

        # Use custom system prompt if configured
        system = adapter_config.get("system_prompt") or self.config.system_prompt
        if not system:
            system = self._default_system_prompt(cape)

        # Format inputs
        inputs_formatted = self._format_inputs(inputs)

        # Build final prompt
        return f"{system}\n\n## Input\n{inputs_formatted}"

    def build_tools(self, cape: "Cape") -> List[Dict[str, Any]]:
        """
        Build tool definitions from Cape.

        Args:
            cape: Cape to build tools for

        Returns:
            List of tool definitions in model-specific format
        """
        if not self.config.tools_enabled:
            return []

        tools = []
        for tool_name in cape.execution.tools_allowed:
            tools.append(self._format_tool(tool_name, cape))

        return tools

    def parse_response(self, response: AdapterResponse) -> Dict[str, Any]:
        """
        Parse adapter response into standard format.

        Args:
            response: Raw adapter response

        Returns:
            Parsed output dictionary
        """
        return {
            "content": response.content,
            "tokens": response.tokens,
            "cost": response.cost,
            "tool_calls": response.tool_calls,
        }

    def _default_system_prompt(self, cape: "Cape") -> str:
        """Build default system prompt."""
        return f"""You are executing the capability: {cape.name}

## Description
{cape.description}

## Instructions
Follow these guidelines when responding:
1. Focus on the specific capability being executed
2. Use any provided tools appropriately
3. Return structured output when possible
4. Be concise but thorough
"""

    def _format_inputs(self, inputs: Dict[str, Any]) -> str:
        """Format inputs as string."""
        lines = []
        for key, value in inputs.items():
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, ensure_ascii=False, indent=2)
            lines.append(f"**{key}**: {value}")
        return "\n".join(lines)

    def _format_tool(self, tool_name: str, cape: "Cape") -> Dict[str, Any]:
        """Format tool definition (override in subclass)."""
        return {
            "name": tool_name,
            "description": f"Tool for {cape.name}",
        }

    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on tokens (override in subclass)."""
        return 0.0
