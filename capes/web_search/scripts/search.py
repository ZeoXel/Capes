"""
Web Search Script - Performs real web searches using DuckDuckGo.
"""

import json
import sys
from typing import Dict, Any


def _detect_region(query: str) -> str:
    """Detect search region based on query language."""
    # Check if query contains Chinese characters
    for char in query:
        if '\u4e00' <= char <= '\u9fff':
            return "cn-zh"  # China - Chinese
    return "wt-wt"  # Worldwide


def search_web(query: str, max_results: int = 5, region: str = None) -> Dict[str, Any]:
    """
    Perform a web search using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        region: Search region (auto-detected if None)

    Returns:
        Dictionary with search results and summary
    """
    try:
        # Try new ddgs package first
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        results = []

        # Auto-detect region if not specified
        search_region = region or _detect_region(query)

        ddgs = DDGS()
        # Text search with region
        for r in ddgs.text(query, region=search_region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            })

        # Generate summary
        if results:
            summary_parts = []
            for i, r in enumerate(results[:3], 1):
                snippet = r['snippet'][:150] if r['snippet'] else ""
                summary_parts.append(f"{i}. {r['title']}: {snippet}...")

            summary = f"找到 {len(results)} 条相关结果：\n" + "\n".join(summary_parts)
        else:
            summary = f"未找到与 '{query}' 相关的搜索结果。"

        return {
            "success": True,
            "query": query,
            "results": results,
            "summary": summary,
            "result_count": len(results),
        }

    except ImportError:
        return {
            "success": False,
            "error": "Search library not installed. Run: pip install ddgs",
            "query": query,
            "results": [],
            "summary": "搜索功能暂不可用，请安装 ddgs 包。",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "summary": f"搜索出错: {str(e)}",
        }


def search_news(query: str, max_results: int = 5, region: str = None) -> Dict[str, Any]:
    """
    Search for recent news articles.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        results = []

        # Auto-detect region if not specified
        search_region = region or _detect_region(query)

        ddgs = DDGS()
        for r in ddgs.news(query, region=search_region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", r.get("link", "")),
                "snippet": r.get("body", r.get("excerpt", "")),
                "date": r.get("date", ""),
                "source": r.get("source", ""),
            })

        if results:
            summary_parts = []
            for i, r in enumerate(results[:3], 1):
                date_str = f" ({r['date']})" if r.get('date') else ""
                summary_parts.append(f"{i}. [{r.get('source', '未知来源')}]{date_str} {r['title']}")

            summary = f"找到 {len(results)} 条新闻：\n" + "\n".join(summary_parts)
        else:
            summary = f"未找到与 '{query}' 相关的新闻。"

        return {
            "success": True,
            "query": query,
            "results": results,
            "summary": summary,
            "result_count": len(results),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "summary": f"新闻搜索出错: {str(e)}",
        }


if __name__ == "__main__":
    # CLI interface
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python search.py <query> [news]"}))
        sys.exit(1)

    query = sys.argv[1]
    search_type = sys.argv[2] if len(sys.argv) > 2 else "web"

    if search_type == "news":
        result = search_news(query)
    else:
        result = search_web(query)

    print(json.dumps(result, ensure_ascii=False, indent=2))
