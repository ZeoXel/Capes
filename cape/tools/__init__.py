"""
Cape Tools - Built-in tools for cape execution.

Provides lightweight, reusable tools that can be used by any cape.
"""

from cape.tools.search import (
    search,
    search_web,
    search_news,
    SearchProvider,
)

__all__ = [
    "search",
    "search_web",
    "search_news",
    "SearchProvider",
]
