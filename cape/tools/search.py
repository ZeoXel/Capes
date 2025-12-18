"""
Unified Web Search Tool - Tavily (primary) + DuckDuckGo (fallback).

Provides reliable web search capabilities for cape execution.
Features:
- Tavily as primary provider (optimized for AI agents)
- DuckDuckGo as fallback (no API key required)
- Automatic language/region detection
- Structured results for LLM consumption
"""

import os
import logging
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SearchProvider(Enum):
    """Available search providers."""
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    AUTO = "auto"  # Try Tavily first, fallback to DDG


def _detect_language(query: str) -> str:
    """Detect query language for better search results."""
    # Check for Chinese characters
    for char in query:
        if '\u4e00' <= char <= '\u9fff':
            return "zh"
    # Check for Japanese
    for char in query:
        if '\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff':
            return "ja"
    # Check for Korean
    for char in query:
        if '\uac00' <= char <= '\ud7af':
            return "ko"
    return "en"


def _tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> Dict[str, Any]:
    """
    Search using Tavily API.

    Tavily is optimized for AI agents with:
    - Clean, structured results
    - Optional AI-generated answers
    - Better content extraction
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
        )

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0),
            })

        return {
            "success": True,
            "provider": "tavily",
            "query": query,
            "results": results,
            "answer": response.get("answer"),  # AI-generated answer if available
            "result_count": len(results),
        }

    except ImportError:
        raise ImportError("tavily-python not installed")
    except Exception as e:
        raise RuntimeError(f"Tavily search failed: {e}")


def _ddg_search(
    query: str,
    max_results: int = 5,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search using DuckDuckGo.

    Free, no API key required. Good fallback option.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        # Auto-detect region based on query language
        if region is None:
            lang = _detect_language(query)
            region_map = {
                "zh": "cn-zh",
                "ja": "jp-jp",
                "ko": "kr-kr",
                "en": "wt-wt",
            }
            region = region_map.get(lang, "wt-wt")

        results = []
        ddgs = DDGS()

        for r in ddgs.text(query, region=region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            })

        return {
            "success": True,
            "provider": "duckduckgo",
            "query": query,
            "results": results,
            "result_count": len(results),
        }

    except ImportError:
        raise ImportError("duckduckgo-search not installed")
    except Exception as e:
        raise RuntimeError(f"DuckDuckGo search failed: {e}")


def _ddg_news(
    query: str,
    max_results: int = 5,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """Search news using DuckDuckGo."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        if region is None:
            lang = _detect_language(query)
            region_map = {"zh": "cn-zh", "ja": "jp-jp", "ko": "kr-kr", "en": "wt-wt"}
            region = region_map.get(lang, "wt-wt")

        results = []
        ddgs = DDGS()

        for r in ddgs.news(query, region=region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", r.get("link", "")),
                "snippet": r.get("body", r.get("excerpt", "")),
                "date": r.get("date", ""),
                "source": r.get("source", ""),
            })

        return {
            "success": True,
            "provider": "duckduckgo",
            "query": query,
            "results": results,
            "result_count": len(results),
        }

    except Exception as e:
        raise RuntimeError(f"DuckDuckGo news search failed: {e}")


def search(
    query: str,
    max_results: int = 5,
    provider: SearchProvider = SearchProvider.AUTO,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> Dict[str, Any]:
    """
    Unified search function with automatic provider selection.

    Args:
        query: Search query string
        max_results: Maximum number of results (default: 5)
        provider: Search provider to use (default: AUTO)
        search_depth: Tavily search depth - "basic" or "advanced"
        include_answer: Whether to include AI-generated answer (Tavily only)

    Returns:
        Dictionary with search results and metadata
    """
    errors = []

    # Try Tavily first if AUTO or explicitly requested
    if provider in (SearchProvider.AUTO, SearchProvider.TAVILY):
        try:
            return _tavily_search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
            )
        except ValueError as e:
            # API key not set
            errors.append(f"Tavily: {e}")
            if provider == SearchProvider.TAVILY:
                return {
                    "success": False,
                    "error": str(e),
                    "query": query,
                    "results": [],
                }
        except ImportError as e:
            errors.append(f"Tavily: {e}")
            if provider == SearchProvider.TAVILY:
                return {
                    "success": False,
                    "error": "tavily-python not installed",
                    "query": query,
                    "results": [],
                }
        except Exception as e:
            errors.append(f"Tavily: {e}")
            logger.warning(f"Tavily search failed, trying fallback: {e}")

    # Try DuckDuckGo as fallback
    if provider in (SearchProvider.AUTO, SearchProvider.DUCKDUCKGO):
        try:
            return _ddg_search(query=query, max_results=max_results)
        except ImportError:
            errors.append("DuckDuckGo: duckduckgo-search not installed")
        except Exception as e:
            errors.append(f"DuckDuckGo: {e}")
            logger.warning(f"DuckDuckGo search also failed: {e}")

    # All providers failed
    return {
        "success": False,
        "error": "; ".join(errors) if errors else "No search provider available",
        "query": query,
        "results": [],
    }


def search_web(
    query: str,
    max_results: int = 5,
    provider: str = "auto",
) -> Dict[str, Any]:
    """
    Web search tool for cape execution.

    Args:
        query: Search query string
        max_results: Maximum number of results
        provider: "auto", "tavily", or "duckduckgo"

    Returns:
        Dictionary with search results
    """
    provider_enum = {
        "auto": SearchProvider.AUTO,
        "tavily": SearchProvider.TAVILY,
        "duckduckgo": SearchProvider.DUCKDUCKGO,
    }.get(provider.lower(), SearchProvider.AUTO)

    result = search(
        query=query,
        max_results=max_results,
        provider=provider_enum,
    )

    # Generate summary for LLM consumption
    if result.get("success") and result.get("results"):
        results = result["results"]

        # If Tavily provided an answer, use it
        if result.get("answer"):
            summary = f"AI 摘要: {result['answer']}\n\n"
        else:
            summary = ""

        # Add result summaries
        summary_parts = []
        for i, r in enumerate(results[:3], 1):
            snippet = r.get("snippet", "")[:200]
            summary_parts.append(f"{i}. {r['title']}: {snippet}...")

        summary += f"找到 {len(results)} 条结果:\n" + "\n".join(summary_parts)
        result["summary"] = summary
    else:
        result["summary"] = f"搜索 '{query}' 失败: {result.get('error', '未知错误')}"

    return result


def search_news(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    News search tool for cape execution.

    Uses DuckDuckGo news search (Tavily doesn't have dedicated news endpoint).

    Args:
        query: Search query string
        max_results: Maximum number of results

    Returns:
        Dictionary with news results
    """
    try:
        result = _ddg_news(query=query, max_results=max_results)

        # Generate summary
        if result.get("success") and result.get("results"):
            results = result["results"]
            summary_parts = []
            for i, r in enumerate(results[:3], 1):
                date_str = f" ({r['date']})" if r.get("date") else ""
                source = r.get("source", "未知来源")
                summary_parts.append(f"{i}. [{source}]{date_str} {r['title']}")

            result["summary"] = f"找到 {len(results)} 条新闻:\n" + "\n".join(summary_parts)
        else:
            result["summary"] = f"未找到与 '{query}' 相关的新闻"

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "summary": f"新闻搜索失败: {e}",
        }


# For backwards compatibility
__all__ = ["search", "search_web", "search_news", "SearchProvider"]
