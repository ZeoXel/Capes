"""
Cape Adapters - Model-specific translation layers.

Adapters translate Cape definitions into model-specific formats:
- Claude: System prompts + tool definitions
- OpenAI: Function calling format
- Local: Generic prompts

Each adapter knows how to:
1. Convert Cape interface to model's expected format
2. Build appropriate prompts from Cape description
3. Parse model responses back to Cape output format
"""

from cape.adapters.base import BaseAdapter, AdapterConfig
from cape.adapters.openai import OpenAIAdapter
from cape.adapters.claude import ClaudeAdapter
from cape.adapters.generic import GenericAdapter

__all__ = [
    "BaseAdapter",
    "AdapterConfig",
    "OpenAIAdapter",
    "ClaudeAdapter",
    "GenericAdapter",
]
