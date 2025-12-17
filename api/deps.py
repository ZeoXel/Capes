"""
API Dependencies - Shared dependencies for routes.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from cape.registry.registry import CapeRegistry
from cape.runtime.runtime import CapeRuntime
from cape.adapters.openai import OpenAIAdapter
from cape.adapters.base import AdapterConfig


class Settings:
    """Application settings."""

    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.default_model = os.environ.get("DEFAULT_MODEL", "gemini-2.5-flash")

        # Paths
        base_dir = Path(__file__).parent.parent
        self.capes_dir = base_dir / "capes"
        self.skills_dir = base_dir / "skills"

        # CORS
        self.cors_origins = os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()


# Global instances (initialized once)
_registry: Optional[CapeRegistry] = None
_runtime: Optional[CapeRuntime] = None


def get_registry() -> CapeRegistry:
    """Get or create Cape registry."""
    global _registry
    if _registry is None:
        settings = get_settings()
        _registry = CapeRegistry(
            capes_dir=settings.capes_dir,
            skills_dir=settings.skills_dir,
            auto_load=True,
            use_embeddings=True,
        )
    return _registry


def get_runtime() -> CapeRuntime:
    """Get or create Cape runtime."""
    global _runtime
    if _runtime is None:
        settings = get_settings()
        registry = get_registry()

        def adapter_factory(model_name: str):
            """Create adapter for model."""
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
            except ImportError:
                return None

            config = AdapterConfig(
                model_name=model_name or settings.default_model,
                temperature=0.0,
                max_tokens=4096,
            )
            return OpenAIAdapter(config=config, client=client)

        _runtime = CapeRuntime(
            registry=registry,
            adapter_factory=adapter_factory,
        )

        # Register web search tools
        _register_builtin_tools(_runtime)

    return _runtime


def _register_builtin_tools(runtime: CapeRuntime):
    """Register built-in tools for cape execution."""
    from capes.web_search.scripts.search import search_web, search_news

    runtime.register_tool("web_search", search_web)
    runtime.register_tool("news_search", search_news)


def reset_instances():
    """Reset global instances (for testing)."""
    global _registry, _runtime
    _registry = None
    _runtime = None


# Available models configuration
AVAILABLE_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "google",
        "speed": "fast",
        "cost_tier": "low",
        "supports_tools": True,
        "default": True,
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "provider": "google",
        "speed": "medium",
        "cost_tier": "medium",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "speed": "fast",
        "cost_tier": "low",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "speed": "medium",
        "cost_tier": "medium",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "speed": "medium",
        "cost_tier": "medium",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "gpt-4.1",
        "name": "GPT-4.1",
        "provider": "openai",
        "speed": "medium",
        "cost_tier": "medium",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "speed": "medium",
        "cost_tier": "medium",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "speed": "fast",
        "cost_tier": "low",
        "supports_tools": True,
        "default": False,
    },
    {
        "id": "claude-3-haiku-20240307",
        "name": "Claude 3 Haiku",
        "provider": "anthropic",
        "speed": "fast",
        "cost_tier": "low",
        "supports_tools": True,
        "default": False,
    },
]
